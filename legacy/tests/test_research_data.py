import unittest
from usquant.research_data import fact_rows,filings,initialize,insert_rows
from usquant.storage import Store

class ResearchTests(unittest.TestCase):
 def test_all_tags_units_contexts_and_versions(self):
  base=dict(end='2023-12-31',filed='2024-02-01',accn='0000000001-24-000001',form='10-K',val=1.25)
  payload={'cik':1,'facts':{'us-gaap':{'UnexpectedTag':{'label':'Unexpected','units':{'USD':[base,dict(base,val=2)],'shares':[base]}}}}}
  rows=fact_rows(payload,'ONE','x'*64)
  self.assertEqual(len(rows),3)
  self.assertEqual(rows[0][12],'1.25')
  store=Store(path=':memory:');self.addCleanup(store.close);initialize(store)
  insert_rows(store,'research_facts',rows);insert_rows(store,'research_facts',rows)
  with store.cursor() as c:
   c.execute('SELECT COUNT(*) FROM research_facts');self.assertEqual(c.fetchone()[0],3)
 def test_invalid_financial_dates(self):
  payload={'cik':1,'facts':{'us-gaap':{'A':{'units':{'USD':[dict(end='2024-01-01',filed='2023-01-01',val=1,accn='0000000001-24-000001')] }}}}}
  self.assertEqual(fact_rows(payload,'ONE','x')[0][-2],'review_dates')
 def test_acceptance_is_not_report_date(self):
  store=Store(path=':memory:');self.addCleanup(store.close);initialize(store)
  payload=dict(accessionNumber=['0000000001-24-000001'],form=['10-K'],filingDate=['2024-02-01'],
    reportDate=['2023-12-31'],acceptanceDateTime=['2024-02-01T21:15:00Z'])
  self.assertEqual(filings(store,payload,'ONE','0000000001','x'),1)
  with store.cursor() as c:
   c.execute('SELECT report_date,accepted_utc FROM research_filings');row=c.fetchone()
  self.assertEqual(row,('2023-12-31','2024-02-01T21:15:00+00:00'))
