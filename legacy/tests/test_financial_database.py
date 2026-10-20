import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from usquant.storage import Store
from usquant.financial_database import catalog, candidates, run_batch, coverage

class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.store=Store(path=':memory:')
        self.addCleanup(self.store.close)
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path=Path(temp.name)/'directory.json'
        self.payload=dict(fields=['cik','name','ticker','exchange'],data=[
            [1,'One','ONE','NYSE'],[1,'One','ONE.A','NYSE'],[2,'Two','TWO','Nasdaq']])
        self.path.write_text(json.dumps(self.payload))
        catalog(self.store,self.payload,self.path)
    def test_cik_dedup_and_refresh_preserves_absent_issuers(self):
        self.assertEqual(len(candidates(self.store)),2)
        self.payload['data']=[[1,'One renamed','NEW','NYSE']]
        self.path.write_text(json.dumps(self.payload))
        catalog(self.store,self.payload,self.path)
        self.assertEqual(candidates(self.store),[('0000000001','ONE'),('0000000002','TWO')])
        self.assertEqual(coverage(self.store)['discovered_issuers'],2)
    def test_empty_snapshot_resume(self):
        path=self.path
        class Client:
            def get(self,url,label): return dict(cik=int(label),facts={}),path
        result=run_batch(self.store,Client(),limit=1)
        self.assertEqual(result[0]['status'],'no_supported_metrics')
        self.assertEqual(candidates(self.store),[('0000000002','TWO')])
        self.assertEqual(len(candidates(self.store,refresh=True)),2)
    def test_access_failure_stops_and_remains_pending(self):
        class Client:
            def get(self,url,label): raise HTTPError(url,429,'rate limit',None,None)
        self.assertEqual(len(run_batch(self.store,Client())),1)
        self.assertEqual(len(candidates(self.store)),2)

class AnnualPanelTests(unittest.TestCase):
    def test_annual_context_revision_and_missing(self):
        from usquant.fundamentals import normalize, ingest
        from usquant.financial_database import build_panel
        store=Store(path=':memory:'); self.addCleanup(store.close)
        base=dict(end='2023-12-31',filed='2024-02-01',accn='0000000001-24-000001',form='10-K')
        payload=dict(cik=1,facts={'us-gaap':{
            'NetIncomeLoss':{'units':{'USD':[
                dict(base,start='2023-01-01',val=100),
                dict(base,start='2023-10-01',val=30)]}},
            'Assets':{'units':{'USD':[dict(base,val=500)]}}}})
        ingest(store,normalize(payload,'ONE'))
        self.assertEqual(build_panel(store,2010,'2024-02-01'),0)
        self.assertEqual(build_panel(store,2010,'2024-02-02'),1)
        self.assertEqual(build_panel(store,2010,'2024-02-02'),1)
        with store.cursor() as c:
            c.execute('SELECT payload FROM annual_panel')
            row=json.loads(c.fetchone()[0])
        self.assertEqual(row['metrics']['net_income']['value'],'100')
        self.assertEqual(row['metrics']['assets']['value'],'500')
        self.assertIsNone(row['metrics']['revenues']['value'])
        # Two annual contexts cannot be silently combined or treated as one.
        payload['facts']['us-gaap']['NetIncomeLoss']['units']['USD'].append(dict(base,start='2023-01-02',val=99))
        ingest(store,normalize(payload,'ONE'))
        build_panel(store,2010,'2024-02-02')
        with store.cursor() as c:
            c.execute('SELECT payload FROM annual_panel')
            row=json.loads(c.fetchone()[0])
        self.assertEqual(row['metrics']['net_income']['status'],'ambiguous_context')
