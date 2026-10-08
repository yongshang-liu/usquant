import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from usquant.paper_broker import PaperBroker, NoRedirect
from usquant.risk import RiskLimits

class FakeBroker(PaperBroker):
    def __init__(self):
        self.calls=[]
        self.equity=2500
        self.open_orders=[]
        self.age=0
        self.fail=False
        self.orders={}
    def request(self,path,body=None,data=False):
        self.calls.append((path,body,data))
        if body:
            order=dict(body,status='accepted',id='broker-id')
            self.orders[body['client_order_id']]=order
            if self.fail: raise TimeoutError('unknown result')
            return order
        if path.startswith('/v2/orders:'): return next(iter(self.orders.values()))
        if path=='/v2/account': return dict(id='account',status='ACTIVE',equity=str(self.equity),last_equity='2500',cash='2500',buying_power='5000')
        if path=='/v2/clock': return {'is_open':True}
        if path.startswith('/v2/orders?'): return self.open_orders
        if path=='/v2/positions': return []
        if path.startswith('/v2/assets/'): return {'tradable':True,'asset_class':'us_equity'}
        if data: return {'quote':{'ap':100,'bp':99,'t':(datetime.now(timezone.utc)-timedelta(seconds=self.age)).isoformat()}}
        raise AssertionError(path)

class PaperTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.journal=Path(self.tmp.name)/'paper.sqlite'
        self.broker=FakeBroker()
    def execute(self,qty=1,submit=False,side='buy',client_id='test-1',limits=None):
        return self.broker.execute('SPY',qty,side,client_id,limits or RiskLimits(),self.journal,submit)
    def test_preview_never_posts(self):
        self.assertFalse(self.execute()['submitted'])
        self.assertFalse(any(body for _,body,_ in self.broker.calls))
    def test_submit_and_restart_reconciliation(self):
        self.assertTrue(self.execute(submit=True)['submitted'])
        self.assertTrue(self.execute(submit=True)['reconciled'])
        self.assertEqual(sum(body is not None for _,body,_ in self.broker.calls),1)
        with self.assertRaises(ValueError): self.execute(qty=2,submit=True)
    def test_timeout_does_not_repeat_post(self):
        self.broker.fail=True
        with self.assertRaises(TimeoutError): self.execute(submit=True)
        self.assertTrue(self.execute(submit=True)['reconciled'])
        self.assertEqual(sum(body is not None for _,body,_ in self.broker.calls),1)
    def test_uncertain_submission_blocks_new_id(self):
        self.broker.fail=True
        with self.assertRaises(TimeoutError): self.execute(submit=True)
        with self.assertRaises(PermissionError): self.execute(client_id='new-id',submit=True)
        self.assertEqual(sum(body is not None for _,body,_ in self.broker.calls),1)
    def test_limits_stale_pending_and_short(self):
        with self.assertRaises(PermissionError): self.execute(qty=6)
        with self.assertRaises(PermissionError): self.execute(side='sell')
        self.broker.age=61
        with self.assertRaises(PermissionError): self.execute()
        self.broker.age=0; self.broker.open_orders=[{'id':'other'}]
        with self.assertRaises(PermissionError): self.execute()
    def test_persisted_drawdown_and_kill(self):
        self.execute()
        self.broker.equity=2250
        with self.assertRaises(PermissionError): self.execute()
        self.broker.equity=2500
        with self.assertRaises(PermissionError): self.execute(limits=RiskLimits(kill_switch=True))
    def test_redirect_blocked(self):
        with self.assertRaises(PermissionError): NoRedirect().redirect_request(None,None,302,'',{},'https://api.alpaca.markets')
