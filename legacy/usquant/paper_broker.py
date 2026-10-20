"""One-shot paper execution. Fixed hosts, no redirects, no automatic POST retries."""
import json
import math
import os
import re
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from .risk import RiskLimits

PAPER = 'https://paper-api.alpaca.markets'
DATA = 'https://data.alpaca.markets'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise PermissionError('Broker redirects are forbidden')

class PaperBroker:
    def request(self, path, body=None, data=False):
        headers = {'APCA-API-KEY-ID': os.environ['ALPACA_API_KEY'],
                   'APCA-API-SECRET-KEY': os.environ['ALPACA_SECRET_KEY'],
                   'Content-Type': 'application/json'}
        req = urllib.request.Request((DATA if data else PAPER)+path, headers=headers,
              data=None if body is None else json.dumps(body, allow_nan=False).encode())
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=15) as response:
            return json.load(response)

    def execute(self, symbol, qty, side, client_id, limits, journal, submit=False):
        if not re.fullmatch(r'[A-Z][A-Z0-9.]{0,14}', symbol): raise ValueError('invalid symbol')
        if type(qty) is not int or qty <= 0: raise ValueError('positive integer qty required')
        if side not in ('buy', 'sell'): raise ValueError('invalid side')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}', client_id): raise ValueError('invalid client order id')
        # A write lock serializes all processes sharing the journal, including previews.
        db = sqlite3.connect(str(journal), timeout=20, isolation_level=None)
        try:
            db.execute('CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, intent TEXT, status TEXT, payload TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS peaks (account TEXT PRIMARY KEY, equity REAL)')
            db.execute('BEGIN IMMEDIATE')
            intent = json.dumps([symbol, qty, side])
            old = db.execute('SELECT intent,status,payload FROM orders WHERE id=?', (client_id,)).fetchone()
            if old:
                if old[0] != intent: raise ValueError('client id reused for different intent')
                try:
                    order = self.request('/v2/orders:by_client_order_id?'+urllib.parse.urlencode({'client_order_id':client_id}))
                except urllib.error.HTTPError as error:
                    if error.code == 404: raise RuntimeError('Uncertain prior submission; inspect broker before using another id') from None
                    raise
                db.execute('UPDATE orders SET status=?,payload=? WHERE id=?', (order['status'],json.dumps(order),client_id))
                db.commit()
                return {'mode':'alpaca-paper','reconciled':True,'order':order}
            if db.execute("SELECT id FROM orders WHERE status='uncertain'").fetchone():
                raise PermissionError('reconcile uncertain submission using its original client id first')
            account = self.request('/v2/account')
            clock = self.request('/v2/clock')
            if account['status'] != 'ACTIVE' or any(account.get(k) for k in ('trading_blocked','account_blocked','trade_suspended_by_user')):
                raise PermissionError('account cannot trade')
            if not clock['is_open']: raise PermissionError('regular market session is closed')
            if self.request('/v2/orders?status=open&limit=500'): raise PermissionError('open orders must be reconciled first')
            positions = self.request('/v2/positions')
            asset = self.request('/v2/assets/'+symbol)
            if not asset['tradable'] or asset['asset_class'] != 'us_equity': raise PermissionError('US equity must be tradable')
            quote = self.request('/v2/stocks/'+symbol+'/quotes/latest?feed=iex', data=True)['quote']
            age = (datetime.now(timezone.utc)-datetime.fromisoformat(quote['t'].replace('Z','+00:00'))).total_seconds()
            if not 0 <= age <= 60: raise PermissionError('stale or future quote')
            price = float(quote['ap' if side == 'buy' else 'bp'])
            if not math.isfinite(price) or price <= 0: raise ValueError('invalid quote')
            # US equity MVP uses prices >= $1 and two decimal places.
            if price < 1: raise PermissionError('sub-dollar equities unsupported')
            price = round(price, 2)
            equity, baseline, cash = (float(account[k]) for k in ('equity','last_equity','cash'))
            if not all(math.isfinite(v) and v > 0 for v in (equity,baseline)) or not math.isfinite(cash): raise ValueError('invalid account balances')
            prior = db.execute('SELECT equity FROM peaks WHERE account=?', (account['id'],)).fetchone()
            peak = max(equity, baseline, prior[0] if prior else equity)
            db.execute('INSERT OR REPLACE INTO peaks VALUES (?,?)', (account['id'],peak))
            position = next((p for p in positions if p['symbol'] == symbol), None)
            held = float(position['qty']) if position else 0.0
            if not math.isfinite(held) or held < 0: raise PermissionError('short positions unsupported')
            if side == 'buy':
                if limits.halted(equity, peak, baseline): raise PermissionError('risk halt')
                if qty*price > min(limits.max_order_notional,cash,float(account['buying_power'])): raise PermissionError('order/cash limit')
                if (held+qty)*price > equity*limits.max_position_fraction: raise PermissionError('position limit')
                gross = sum(abs(float(p['market_value'])) for p in positions)
                if not math.isfinite(gross) or gross+qty*price > equity: raise PermissionError('gross exposure limit')
            elif qty > held: raise PermissionError('sell exceeds owned shares')
            order = dict(symbol=symbol,qty=str(qty),side=side,type='limit',time_in_force='day',
                         limit_price=f'{price:.2f}',client_order_id=client_id)
            if not submit:
                db.commit()
                return {'mode':'alpaca-paper','submitted':False,'proposal':order}
            db.execute('INSERT INTO orders VALUES (?,?,?,?)', (client_id,intent,'uncertain',json.dumps(order)))
            db.commit()  # Durable BEFORE network. A timeout never causes an automatic resubmit.
            result = self.request('/v2/orders', body=order)
            db.execute('UPDATE orders SET status=?,payload=? WHERE id=?', (result['status'],json.dumps(result),client_id))
            return {'mode':'alpaca-paper','submitted':True,'order':result}
        finally:
            if db.in_transaction: db.commit()  # Retain observed risk peak after a rejection.
            db.close()

def main():
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description='Alpaca PAPER only; preview by default')
    parser.add_argument('--symbol',default='SPY')
    parser.add_argument('--qty',type=int,required=True)
    parser.add_argument('--side',choices=['buy','sell'],default='buy')
    parser.add_argument('--client-id',required=True)
    parser.add_argument('--submit',action='store_true')
    root=Path(__file__).resolve().parents[1]
    parser.add_argument('--config',type=Path,default=root/'config/example.json')
    args=parser.parse_args()
    (root/'data').mkdir(exist_ok=True)
    limits=RiskLimits(**json.loads(args.config.read_text())['risk'])
    result=PaperBroker().execute(args.symbol,args.qty,args.side,args.client_id,limits,root/'data/paper.sqlite',args.submit)
    print(json.dumps(result,indent=2))

if __name__ == '__main__': main()
