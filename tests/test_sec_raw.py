import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from usquant.storage import Store
from usquant.sec_raw import ingest_archive

class RawTests(unittest.TestCase):
 def test_preserves_blanks_versions_and_atomicity(self):
  with tempfile.TemporaryDirectory() as temp:
   directory=Path(temp); files={}
   for name in ('sub','num','tag','pre'):
    raw=b'adsh\tcik\tsic\tvalue\nA\t1\t\t001.00\n'
    (directory/(name+'.txt')).write_bytes(raw)
    files[name]={'sha256':hashlib.sha256(raw).hexdigest()}
   meta=dict(batch_id='a'*64,package_year=2010,package_quarter=1,retrieved_at='test',source_url='test',files=files)
   store=Store(path=':memory:'); self.addCleanup(store.close)
   self.assertEqual(ingest_archive(store,directory,meta)['num'],1)
   self.assertTrue(ingest_archive(store,directory,meta)['already_imported'])
   with store.cursor() as c:
    c.execute('SELECT payload FROM raw_sec_num'); row=json.loads(c.fetchone()[0])
   self.assertEqual(row['sic'],''); self.assertEqual(row['value'],'001.00')
   # A late-file validation error rolls back earlier files of the new batch.
   meta['batch_id']='b'*64
   (directory/'pre.txt').write_bytes(b'corrupt')
   with self.assertRaises(ValueError): ingest_archive(store,directory,meta)
   with store.cursor() as c:
    c.execute('SELECT COUNT(*) FROM raw_sec_sub'); self.assertEqual(c.fetchone()[0],1)
