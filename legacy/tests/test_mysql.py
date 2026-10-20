import json
import os
import unittest
import uuid
from usquant.storage import Store
from usquant.data import Bar

@unittest.skipUnless(os.getenv('USQUANT_TEST_MYSQL')=='1','MySQL service not configured')
class MySQLIntegration(unittest.TestCase):
    def test_roundtrip_and_rollback(self):
        s=Store('mysql')
        source='test-'+uuid.uuid4().hex[:12]
        b=Bar('SPY','2024-01-02T00:00:00+00:00',100,101,99,100,100,source)
        try:
            s.ingest([b]); s.ingest([b])
            self.assertEqual(s.load('SPY',source),[b])
            from dataclasses import replace
            with self.assertRaises(ValueError): s.ingest([replace(b,close=100.5)])
            self.assertEqual(s.load('SPY',source),[b])
        finally:
            with s.cursor() as c: c.execute('DELETE FROM bars WHERE source=%s',(source,))
            s.db.commit(); s.close()

    def test_financial_facts_roundtrip(self):
        from usquant.fundamentals import normalize, ingest, as_of
        from test_fundamentals import fixture
        s=Store('mysql')
        symbol='T'+uuid.uuid4().hex[:12].upper()
        try:
            rows=normalize(fixture(),symbol)
            self.assertEqual(ingest(s,rows),3)
            self.assertEqual(ingest(s,rows),0)
            self.assertEqual(as_of(s,symbol,'2023-05-01'),[])
            self.assertEqual(as_of(s,symbol,'2023-05-02')[0]['value'],'100')
            self.assertEqual(as_of(s,symbol,'2024-05-02')[0]['value'],'90')
        finally:
            with s.cursor() as c: c.execute('DELETE FROM financial_facts WHERE symbol=%s',(symbol,))
            s.db.commit(); s.close()
