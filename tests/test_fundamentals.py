import unittest
from copy import deepcopy
from usquant.storage import Store
from usquant.fundamentals import normalize,ingest,as_of,SECClient


def fixture():
    return {'cik':320193,'facts':{'us-gaap':{'NetIncomeLoss':{'units':{'USD':[
        dict(start='2023-01-01',end='2023-03-31',filed='2023-05-01',accn='0000320193-23-000001',form='10-Q',val=100),
        dict(start='2023-01-01',end='2023-03-31',filed='2024-05-01',accn='0000320193-24-000001',form='10-Q',val=90),
        dict(start='2023-01-01',end='2023-06-30',filed='2023-08-01',accn='0000320193-23-000002',form='10-Q',val=250)
    ]}}}}}


class FundamentalTests(unittest.TestCase):
    def test_versions_and_conservative_availability(self):
        store=Store(path=':memory:'); self.addCleanup(store.close)
        rows=normalize(fixture(),'AAPL')
        self.assertEqual(ingest(store,rows),3)
        self.assertEqual(ingest(store,rows),0)
        self.assertEqual(as_of(store,'AAPL','2023-05-01'),[])
        self.assertEqual(as_of(store,'AAPL','2023-05-02')[0]['value'],'100')
        self.assertEqual(as_of(store,'AAPL','2024-05-02')[0]['value'],'90')
        # Quarter and YTD contexts remain separate.
        self.assertEqual(len(as_of(store,'AAPL','2024-05-02')),2)
    def test_bad_dates_values_and_identity(self):
        for field,value in [('val',float('nan')),('end','2025-01-01'),('accn','invalid')]:
            data=fixture(); data['facts']['us-gaap']['NetIncomeLoss']['units']['USD'][0][field]=value
            with self.assertRaises(ValueError): normalize(data,'AAPL')
        with self.assertRaises(ValueError): SECClient('not-an-email','unused')
    def test_ambiguous_restatement_rejected(self):
        data=fixture(); f=data['facts']['us-gaap']['NetIncomeLoss']['units']['USD']
        duplicate=deepcopy(f[0]); duplicate['val']=101; f.append(duplicate)
        store=Store(path=':memory:'); self.addCleanup(store.close)
        ingest(store,normalize(data,'AAPL'))
        with self.assertRaises(ValueError): as_of(store,'AAPL','2023-05-02')
