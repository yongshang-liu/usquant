"""SEC companyfacts ingestion with filing versions and conservative as-of selection."""
import argparse
import hashlib
import json
import os
import re
import time
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import urllib.request
from .paper_broker import NoRedirect
from .storage import Store

TAGS = {
    'revenues': ['RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues', 'SalesRevenueNet'],
    'net_income': ['NetIncomeLoss'],
    'operating_income': ['OperatingIncomeLoss'],
    'assets': ['Assets'],
    'liabilities': ['Liabilities'],
    'equity': ['StockholdersEquity', 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'],
    'cash': ['CashAndCashEquivalentsAtCarryingValue'],
    'operating_cash_flow': ['NetCashProvidedByUsedInOperatingActivities'],
    'capital_expenditure': ['PaymentsToAcquirePropertyPlantAndEquipment'],
    'diluted_eps': ['EarningsPerShareDiluted'],
    'diluted_shares': ['WeightedAverageNumberOfDilutedSharesOutstanding'],
}
SCHEMA = '''CREATE TABLE IF NOT EXISTS financial_facts (
id CHAR(64) PRIMARY KEY, symbol VARCHAR(16) NOT NULL, cik VARCHAR(10) NOT NULL,
metric VARCHAR(40) NOT NULL, tag VARCHAR(150) NOT NULL, unit VARCHAR(30) NOT NULL,
period_start VARCHAR(10) NOT NULL, period_end VARCHAR(10) NOT NULL,
filed VARCHAR(10) NOT NULL, accession VARCHAR(30) NOT NULL,
form VARCHAR(12) NOT NULL, value_text VARCHAR(100) NOT NULL, payload TEXT NOT NULL)'''


def iso_date(value):
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError('invalid ISO date')
    return value


def normalize(payload, symbol):
    if not re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,14}', symbol): raise ValueError('invalid symbol')
    cik = str(int(payload['cik'])).zfill(10)
    if len(cik) != 10: raise ValueError('invalid CIK')
    gaap = payload.get('facts', {}).get('us-gaap', {})
    rows = {}
    for metric, tags in TAGS.items():
        for tag in tags:
            for unit, facts in gaap.get(tag, {}).get('units', {}).items():
                if unit not in ('USD', 'USD/shares', 'shares'): continue
                for fact in facts:
                    if fact.get('form') not in ('10-K','10-Q','10-K/A','10-Q/A'): continue
                    end = iso_date(fact['end'])
                    start = iso_date(fact['start']) if fact.get('start') else ''
                    filed = iso_date(fact['filed'])
                    if (start and start > end) or end > filed: raise ValueError('invalid fact dates')
                    if type(fact['val']) is bool: raise ValueError('invalid value')
                    value = Decimal(str(fact['val']))
                    if not value.is_finite(): raise ValueError('nonfinite fact')
                    text = format(value, 'f')
                    if len(text)>100: raise ValueError('value exceeds storage capacity')
                    accession = fact['accn']
                    if not re.fullmatch(r'\d{10}-\d{2}-\d{6}', accession): raise ValueError('invalid accession')
                    meta = dict(symbol=symbol,cik=cik,metric=metric,tag=tag,unit=unit,
                                start=start,end=end,filed=filed,accn=accession,form=fact['form'],
                                value=text,fy=fact.get('fy'),fp=fact.get('fp'),frame=fact.get('frame'))
                    serialized = json.dumps(meta,sort_keys=True,separators=(',',':'))
                    identity = hashlib.sha256(serialized.encode()).hexdigest()
                    rows[identity] = (identity,symbol,cik,metric,tag,unit,start,end,filed,accession,
                                      fact['form'],text,serialized)
    return list(rows.values())


def initialize(store):
    with store.cursor() as cursor: cursor.execute(SCHEMA)
    store.db.commit()


def ingest(store, rows):
    initialize(store)
    added = 0
    try:
        with store.cursor() as cursor:
            for row in rows:
                cursor.execute('SELECT payload FROM financial_facts WHERE id='+store.mark,(row[0],))
                old=cursor.fetchone()
                if old:
                    if old[0] != row[-1]: raise ValueError('fact identity conflict')
                    continue
                cursor.execute('INSERT INTO financial_facts VALUES ('+','.join([store.mark]*13)+')',row)
                added += 1
        store.db.commit()
    except Exception:
        store.db.rollback()
        raise
    return added


def as_of(store, symbol, cutoff):
    """Conservative daily availability: exclude filings on the cutoff day.

    Preserve tags and duration contexts; do not mistake year-to-date for a quarter.
    Same-day ambiguous values are rejected instead of silently choosing a revision.
    """
    iso_date(cutoff)
    initialize(store)
    with store.cursor() as cursor:
        cursor.execute('SELECT payload FROM financial_facts WHERE symbol='+store.mark+
                       ' AND filed < '+store.mark,(symbol,cutoff))
        facts=[json.loads(row[0]) for row in cursor.fetchall()]
    selected={}
    for fact in facts:
        key=(fact['cik'],fact['tag'],fact['unit'],fact['start'],fact['end'])
        prior=selected.get(key)
        if prior is None or (fact['filed'],fact['accn']) > (prior['filed'],prior['accn']): selected[key]=fact
        elif (fact['filed'],fact['accn']) == (prior['filed'],prior['accn']) and fact['value'] != prior['value']:
            raise ValueError('ambiguous same-filing financial values')
    return sorted(selected.values(),key=lambda x:(x['end'],x['tag'],x['start']))


class SECClient:
    def __init__(self, user_agent, snapshot_dir):
        if not re.fullmatch(r'[^\r\n]+\s[^\s@]+@[^\s@]+\.[^\s@]+', user_agent):
            raise ValueError('Set SEC_USER_AGENT to an application name and contact email')
        self.user_agent=user_agent
        self.directory=Path(snapshot_dir)
        self.last_request=0
        self.opener=urllib.request.build_opener(NoRedirect())
    def get(self,url,label):
        if not url.startswith(('https://data.sec.gov/','https://www.sec.gov/')):
            raise ValueError('unsupported SEC host')
        time.sleep(max(0,1-(time.monotonic()-self.last_request)))
        self.last_request=time.monotonic()  # At most one request per second per client.
        req=urllib.request.Request(url,headers={'User-Agent':self.user_agent,'Accept':'application/json'})
        with self.opener.open(req,timeout=30) as response: raw=response.read()
        payload=json.loads(raw,parse_float=Decimal)
        self.directory.mkdir(parents=True,exist_ok=True)
        path=self.directory/(label+'-'+uuid.uuid4().hex+'.json')
        path.write_bytes(raw)
        # The contact email is deliberately omitted from snapshot metadata.
        path.with_suffix('.meta.json').write_text(json.dumps(dict(url=url,
            retrieved_at=datetime.now(timezone.utc).isoformat(),sha256=hashlib.sha256(raw).hexdigest()),indent=2))
        return payload,path


def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description='Free SEC US-GAAP facts; no brokerage operations')
    parser.add_argument('command',choices=['fetch','show'])
    parser.add_argument('--symbols',nargs='+',default=['AAPL','MSFT','NVDA'])
    parser.add_argument('--backend',choices=['sqlite','mysql'],default='sqlite')
    parser.add_argument('--as-of',default=date.today().isoformat())
    args=parser.parse_args()
    # Read simple config values; never execute shell code or print credentials.
    if (root/'.env').exists():
        for line in (root/'.env').read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key,val=line.split('=',1)
                os.environ.setdefault(key.strip(),val.strip().strip('\"').strip("'"))
    (root/'data').mkdir(exist_ok=True)
    store=Store(args.backend,str(root/'data/market.sqlite'))
    try:
        if args.command=='fetch':
            client=SECClient(os.getenv('SEC_USER_AGENT',''),root/'data/sec')
            tickers,_=client.get('https://www.sec.gov/files/company_tickers.json','tickers')
            mapping={row['ticker'].upper():str(row['cik_str']).zfill(10) for row in tickers.values()}
            for symbol in args.symbols:
                symbol=symbol.upper()
                if symbol not in mapping: raise ValueError('symbol missing from SEC mapping: '+symbol)
                cik=mapping[symbol]
                payload,path=client.get('https://data.sec.gov/api/xbrl/companyfacts/CIK'+cik+'.json',symbol)
                if str(int(payload['cik'])).zfill(10) != cik: raise ValueError('CIK mismatch')
                rows=normalize(payload,symbol)
                if not rows: raise ValueError('no supported US-GAAP facts returned')
                print(json.dumps(dict(symbol=symbol,facts=len(rows),inserted=ingest(store,rows),snapshot=str(path))))
        else:
            for symbol in args.symbols:
                print(json.dumps(dict(symbol=symbol,as_of=args.as_of,facts=as_of(store,symbol.upper(),args.as_of)),indent=2))
    finally: store.close()


if __name__=='__main__': main()
