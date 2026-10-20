import unittest
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from usquant.data import Bar
from usquant.momentum_paper import simulate,targets


def fixture():
    start=datetime(2023,1,2,5,tzinfo=timezone.utc);bars=[]
    for i in range(90):
        day=start+timedelta(days=i)
        if day.weekday()>4:continue
        price=100+i*.5+(i%3)*.1
        bars.append(Bar('ONE',day.isoformat(),price,price+1,price-1,price+.2,10000,'test','all'))
    cfg=dict(mode='local-paper',start='2023-01-02',initial_cash=2500,lookback=5,skip=1,vol_window=3,
             top_n=1,max_weight=.2,gross_limit=.6,one_way_cost_bps=15,max_drawdown=.08,max_daily_loss=.03)
    return {'ONE':bars},cfg

class MomentumTests(unittest.TestCase):
    def test_future_changes_cannot_change_past_orders(self):
        series,cfg=fixture();prefix={'ONE':series['ONE'][:35]}
        full=simulate(series,cfg);past=simulate(prefix,cfg)
        self.assertEqual(full['curve'][:35],past['curve'])
        self.assertEqual([r for r in full['trades'] if r['date']<=prefix['ONE'][-1].ts[:10]],past['trades'])
        self.assertGreater(len(full['trades']),0)
    def test_weights_and_next_open(self):
        series,cfg=fixture();cfg['start']=series['ONE'][10].ts[:10]
        result=simulate(series,cfg)
        self.assertEqual(result['trades'][0]['date'],series['ONE'][11].ts[:10])
        weights,_=targets(series,series['ONE'][-1].ts[:10],cfg)
        self.assertLessEqual(sum(weights.values()),.6)
        self.assertLessEqual(max(weights.values()),.2)
        self.assertTrue(all(r['cash']>=-1e-8 for r in result['curve']))
    def test_halt_liquidates_at_following_open(self):
        series,cfg=fixture();cfg['start']=series['ONE'][10].ts[:10]
        series['ONE'][15]=replace(series['ONE'][15],open=50,high=51,low=49,close=50)
        result=simulate(series,cfg)
        self.assertTrue(result['halted'])
        self.assertTrue(all(r['halted'] for r in result['curve'][5:]))
    def test_raw_and_live_rejected(self):
        series,cfg=fixture();cfg['mode']='live'
        with self.assertRaises(ValueError):simulate(series,cfg)
        cfg['mode']='local-paper';series['ONE'][0]=replace(series['ONE'][0],adjustment='raw')
        with self.assertRaises(ValueError):simulate(series,cfg)
