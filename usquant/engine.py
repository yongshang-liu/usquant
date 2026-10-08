import math
from datetime import datetime
from .data import clean
from .strategy import signals
from .risk import RiskLimits

def run(bars, config, native=False, mode='backtest'):
    if mode not in ('backtest','local-paper'): raise ValueError('live execution disabled')
    bars = clean(bars)
    if not bars or len({(b.symbol,b.source,b.adjustment) for b in bars}) != 1:
        raise ValueError('one nonempty symbol/source/adjustment series required')
    times = [datetime.fromisoformat(b.ts) for b in bars]
    if any((b-a).total_seconds() < 20*3600 for a,b in zip(times,times[1:])):
        raise ValueError('daily bars required; intraday or duplicate session rejected')
    if bars[0].adjustment != 'raw': raise ValueError('execution requires raw prices; corporate actions not implemented')
    cash = float(config['initial_cash'])
    fee = float(config['commission'])
    slip = float(config['slippage_bps'])/10000
    if not all(math.isfinite(x) for x in (cash,fee,slip)) or cash <= 0 or fee < 0 or not 0 <= slip < 1:
        raise ValueError('invalid cost/capital configuration')
    limits = RiskLimits(**config['risk'])
    sig = signals(bars,config['fast'],config['slow'],native)
    initial = cash
    peak = previous = cash
    qty = 0
    halted = False
    curve, fills, events = [],[],[]
    for i,b in enumerate(bars):
        opening_equity = cash+qty*b.open
        if limits.halted(opening_equity,peak,previous): halted = True
        # Only information through the PREVIOUS close drives current open orders.
        desired = bool(i and sig[i-1]) and not halted
        price = b.open*(1+slip if desired else 1-slip)
        delta = 0
        if desired and qty == 0:
            budget = min(opening_equity*limits.max_position_fraction,limits.max_order_notional,cash-fee)
            delta = max(0,int(budget/price))
            # Participation uses prior known volume, never current full-day volume.
            delta = min(delta,int(bars[i-1].volume*limits.max_volume_fraction))
        elif not desired and qty > 0:
            delta = -qty
        if delta and b.volume == 0:
            events.append({'ts':b.ts,'reason':'zero volume: no fill'})
            delta = 0
        if delta:
            cash -= delta*price+fee
            qty += delta
            fills.append({'ts':b.ts,'symbol':b.symbol,'side':'buy' if delta>0 else 'sell','qty':abs(delta),'price':price,'commission':fee})
        equity = cash+qty*b.close
        peak = max(peak,equity)
        dd = 1-equity/peak
        if limits.halted(equity,peak,previous): halted = True
        previous = equity
        curve.append({'ts':b.ts,'cash':cash,'qty':qty,'equity':equity,'drawdown':dd,'halted':halted})
    return {'mode':mode,'source':bars[0].source,'synthetic':bars[0].source=='synthetic',
            'config':config,'native':native,'fills':fills,'events':events,'equity':curve,
            'summary':{'initial_cash':initial,'final_equity':curve[-1]['equity'],
                       'total_return':curve[-1]['equity']/initial-1,
                       'max_drawdown':max(p['drawdown'] for p in curve),'fill_count':len(fills),
                       'halted':halted,'open_position':qty}}
