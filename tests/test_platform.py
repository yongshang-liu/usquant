import json
import math
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from usquant.data import Bar,clean,read_csv,write_csv
from usquant.storage import Store
from usquant.engine import run
from usquant.strategy import sma
from usquant.alpaca import LiveBroker,fetch_daily

ROOT=Path(__file__).resolve().parents[1]

def bars(prices):
    dt=datetime(2024,1,2,tzinfo=timezone.utc)
    return [Bar('SPY',(dt+timedelta(days=i)).isoformat(),v,v+1,v-1,v,100000,'synthetic') for i,v in enumerate(prices)]

def config():
    c=json.loads((ROOT/'config/example.json').read_text())
    c.update(fast=1,slow=2,commission=0,slippage_bps=0)
    return c

class PlatformTests(unittest.TestCase):
    def test_invalid_data(self):
        b=bars([100])[0]
        for bad in (replace(b,close=math.nan),replace(b,open=-1),replace(b,volume=-1),replace(b,volume=1.5),replace(b,ts='2024-01-01'),replace(b,high=99)):
            with self.assertRaises(ValueError): clean([bad])

    def test_duplicates_and_csv(self):
        b=bars([100])[0]
        self.assertEqual(clean([b,b]),[b])
        with self.assertRaises(ValueError): clean([b,replace(b,volume=2)])
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bars.csv'; write_csv(p,[b]); self.assertEqual(read_csv(p),[b])

    def test_storage_transaction_and_idempotency(self):
        s=Store(path=':memory:')
        original=bars([100])[0]
        s.ingest([original]); s.ingest([original])
        # MySQL DOUBLE round trips and Mac/Linux libm may differ by a few ULPs.
        s.ingest([replace(original,open=original.open+1e-13)])
        self.assertEqual(len(s.load('SPY')),1)
        new=bars([100,101])[1]
        with self.assertRaises(ValueError): s.ingest([new,replace(original,volume=2)])
        self.assertEqual(s.load('SPY'),[original]); s.close()

    def test_next_open_no_lookahead(self):
        b=bars([100,102,105,101,99])
        out=run(b,config())
        self.assertEqual(out['fills'][0]['ts'],b[2].ts)
        self.assertEqual(out['fills'][0]['price'],105)
        prefix=run(b[:3],config())
        self.assertEqual(out['equity'][:3],prefix['equity'])
        self.assertEqual(out['fills'][1]['ts'],b[4].ts)

    def test_cash_costs_and_position_limit(self):
        c=config(); c.update(commission=1,slippage_bps=10)
        out=run(bars([100,102,105]),c)
        f=out['fills'][0]
        self.assertLessEqual(f['qty']*f['price'],500)
        self.assertAlmostEqual(out['equity'][-1]['cash'],2500-f['qty']*f['price']-1)
        self.assertGreaterEqual(out['equity'][-1]['cash'],0)

    def test_kill_switch(self):
        c=config(); c['risk']['kill_switch']=True
        out=run(bars([100,102,105]),c)
        self.assertEqual(out['fills'],[]); self.assertTrue(out['summary']['halted'])

    def test_drawdown_latches_and_exits_next_bar(self):
        c=config(); c['risk']['max_drawdown']=.005
        out=run(bars([100,102,105,60,62,110,120]),c)
        self.assertTrue(out['summary']['halted'])
        self.assertEqual([f['side'] for f in out['fills']],['buy','sell'])
        self.assertEqual(out['fills'][1]['ts'],bars([100,102,105,60])[3].ts)

    def test_prior_volume_and_no_zero_volume_fill(self):
        b=bars([100,102,105]); b[1]=replace(b[1],volume=0)
        self.assertEqual(run(b,config())['fills'],[])
        b=bars([100,102,105]); b[2]=replace(b[2],volume=0)
        self.assertEqual(run(b,config())['fills'],[])

    def test_mixed_and_adjusted_series_rejected(self):
        with self.assertRaises(ValueError): run([replace(b,adjustment='all') for b in bars([100,102])],config())
        with self.assertRaises(ValueError): run([bars([100])[0],replace(bars([100,102])[1],symbol='QQQ')],config())

    def test_cpp_python_parity(self):
        for window in (1,3,9):
            a=sma([1.,2.,4.,8.,16.],window)
            b=sma([1.,2.,4.,8.,16.],window,True)
            for x,y in zip(a,b):
                if math.isnan(x): self.assertTrue(math.isnan(y))
                else: self.assertAlmostEqual(x,y)

    def test_intraday_rejected(self):
        b=bars([100,102])
        b[1]=replace(b[1],ts='2024-01-02T01:00:00+00:00')
        with self.assertRaises(ValueError): run(b,config())

    def test_live_blocked(self):
        with self.assertRaises(PermissionError): LiveBroker()
        with self.assertRaises(ValueError): run(bars([100]),config(),mode='live')

    def test_alpaca_pagination_read_only(self):
        import io
        responses=[{'bars':{'SPY':[{'t':'2024-01-02T00:00:00Z','o':100,'h':101,'l':99,'c':100,'v':20}]},'next_page_token':'next'},
                   {'bars':{'SPY':[{'t':'2024-01-03T00:00:00Z','o':101,'h':102,'l':100,'c':101,'v':21}]}}]
        requests=[]
        def response(req,timeout):
            requests.append(req)
            return io.BytesIO(json.dumps(responses.pop(0)).encode())
        with patch.dict('os.environ',{'ALPACA_API_KEY':'fake','ALPACA_SECRET_KEY':'fake'}), patch('urllib.request.urlopen',side_effect=response):
            result=fetch_daily(['SPY'],'2024-01-01T00:00:00Z','2024-01-05T00:00:00Z')
        self.assertEqual(len(result),2)
        self.assertIn('page_token=next',requests[1].full_url)
        self.assertTrue(all(r.get_method()=='GET' and r.full_url.startswith('https://data.alpaca.markets/') for r in requests))

if __name__=='__main__': unittest.main()
