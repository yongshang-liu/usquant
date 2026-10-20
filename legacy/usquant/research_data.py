"""Read-only collection for the eight-company AI/fintech research sample."""
import argparse
import hashlib
import json
import os
import re
from dataclasses import asdict
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from .fundamentals import SECClient
from .financial_database import load_env
from .storage import Store
from .alpaca import fetch_daily

COMPANIES={'NVDA':'AI chips','AMD':'AI chips','MSFT':'Cloud and AI','PLTR':'AI software',
           'PYPL':'Digital payments','V':'Payment network','SOFI':'Digital lending','COIN':'Crypto platform'}


def encoded(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),default=str,ensure_ascii=False)


def initialize(s):
    with s.cursor() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS research_companies (
            symbol VARCHAR(16) PRIMARY KEY, cik CHAR(10) NOT NULL, name TEXT NOT NULL,
            research_group VARCHAR(50) NOT NULL, sic VARCHAR(8), updated_at VARCHAR(40) NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS research_sources (
            id CHAR(64) PRIMARY KEY, symbol VARCHAR(16) NOT NULL, kind VARCHAR(24) NOT NULL,
            path TEXT NOT NULL, retrieved_at VARCHAR(40) NOT NULL, row_count INTEGER NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS research_facts (
            id CHAR(64) PRIMARY KEY, cik CHAR(10) NOT NULL, symbol VARCHAR(16) NOT NULL,
            taxonomy VARCHAR(40) NOT NULL, tag VARCHAR(255) NOT NULL, label TEXT NOT NULL,
            unit VARCHAR(100) NOT NULL, period_start DATE, period_end DATE NOT NULL,
            filed DATE NOT NULL, accession VARCHAR(30) NOT NULL, form VARCHAR(20) NOT NULL,
            value_text VARCHAR(120) NOT NULL, reporting_fy INTEGER, reporting_fp VARCHAR(10),
            frame VARCHAR(40), context_status VARCHAR(40) NOT NULL, source_id CHAR(64) NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS research_filings (
            cik CHAR(10) NOT NULL, accession VARCHAR(30) NOT NULL, symbol VARCHAR(16) NOT NULL,
            form VARCHAR(20) NOT NULL, filed DATE NOT NULL, report_date DATE,
            accepted_utc VARCHAR(40), primary_document TEXT, source_id CHAR(64) NOT NULL,
            PRIMARY KEY(cik,accession))''')
    if s.backend=='mysql':
        with s.cursor() as c:
            for table,name,columns in (
                ('research_facts','facts_company_period','cik,period_end'),
                ('research_facts','facts_report','cik,accession'),
                ('research_facts','facts_symbol','symbol'),
                ('research_filings','filing_symbol','symbol')):
                c.execute('SHOW INDEX FROM '+table)
                if name not in {r[2] for r in c.fetchall()}:
                    c.execute('CREATE INDEX '+name+' ON '+table+' ('+columns+')')
    s.db.commit()


def source(s,symbol,kind,path,count):
    raw=path.read_bytes(); identity=hashlib.sha256(raw).hexdigest()
    with s.cursor() as c:
        c.execute('SELECT id FROM research_sources WHERE id='+s.mark,(identity,))
        if not c.fetchone():
            c.execute('INSERT INTO research_sources VALUES ('+','.join([s.mark]*6)+')',
                      (identity,symbol,kind,str(path),datetime.now(timezone.utc).isoformat(),count))
    return identity


def fact_rows(payload,symbol,source_id):
    cik=str(int(payload['cik'])).zfill(10)
    seen={}
    for taxonomy,concepts in payload.get('facts',{}).items():
        for tag,concept in concepts.items():
            for unit,observations in concept.get('units',{}).items():
                for f in observations:
                    end=date.fromisoformat(f['end'])
                    if end<date(2010,1,1): continue
                    start=date.fromisoformat(f['start']) if f.get('start') else None
                    filed=date.fromisoformat(f['filed'])
                    status='review_dates' if (start and start>end) or end>filed else 'ordinary'
                    if isinstance(f['val'],bool): raise ValueError('invalid financial value')
                    value=Decimal(str(f['val']))
                    if not value.is_finite(): raise ValueError('nonfinite value')
                    text=format(value,'f')
                    if len(text)>120: raise ValueError('value exceeds precision storage')
                    if not re.fullmatch(r'\d{10}-\d{2}-\d{6}',f['accn']): raise ValueError('invalid accession')
                    # Content identity retains differing values and filing contexts without summing them.
                    content=(cik,symbol,taxonomy,tag,concept.get('label') or tag,unit,
                             start.isoformat() if start else None,end.isoformat(),filed.isoformat(),
                             f['accn'],f.get('form',''),text,f.get('fy'),f.get('fp'),f.get('frame'),status)
                    identity=hashlib.sha256(encoded(content).encode()).hexdigest()
                    seen[identity]=(identity,)+content+(source_id,)
    return list(seen.values())


def insert_rows(s,table,rows):
    if table not in ('research_facts','research_filings'): raise ValueError('invalid target')
    if not rows:return
    suffix=' ON DUPLICATE KEY UPDATE '+('id=id' if table=='research_facts' else 'accession=accession') if s.backend=='mysql' else ' ON CONFLICT DO NOTHING'
    sql='INSERT INTO '+table+' VALUES ('+','.join([s.mark]*len(rows[0]))+')'+suffix
    with s.cursor() as c:
        for i in range(0,len(rows),500):c.executemany(sql,rows[i:i+500])


def filings(s,payload,symbol,cik,source_id):
    rows=[]
    for i,acc in enumerate(payload.get('accessionNumber',[])):
        f={key:values[i] for key,values in payload.items() if isinstance(values,list) and len(values)>i}
        if f.get('form') not in ('10-K','10-K/A','10-Q','10-Q/A','20-F','20-F/A','40-F','40-F/A'):continue
        if f['filingDate']<'2010-01-01':continue
        accepted=f.get('acceptanceDateTime') or None
        if accepted:
            parsed=datetime.fromisoformat(accepted.replace('Z','+00:00'))
            if parsed.tzinfo is None: accepted=None
            else:accepted=parsed.astimezone(timezone.utc).isoformat()
        rows.append((cik,acc,symbol,f['form'],f['filingDate'],f.get('reportDate') or None,
                     accepted,f.get('primaryDocument'),source_id))
    insert_rows(s,'research_filings',rows)
    return len(rows)


def collect(s,root,symbols,start,end,market=True):
    initialize(s)
    client=SECClient(os.environ['SEC_USER_AGENT'],root/'data/research_sources'/date.today().isoformat())
    tickers,_=client.get('https://www.sec.gov/files/company_tickers.json','tickers')
    mapping={r['ticker']:r for r in tickers.values()}
    for symbol in symbols:
        entry=mapping[symbol];cik=str(entry['cik_str']).zfill(10)
        submissions,path=client.get('https://data.sec.gov/submissions/CIK'+cik+'.json',symbol+'-submissions')
        if submissions['cik'].zfill(10)!=cik:raise ValueError('submission CIK mismatch')
        with s.cursor() as c:
            c.execute('SELECT cik FROM research_companies WHERE symbol='+s.mark,(symbol,))
            old=c.fetchone()
            if old and old[0]!=cik:raise ValueError('ticker issuer changed; review required')
            if not old:c.execute('INSERT INTO research_companies VALUES ('+','.join([s.mark]*6)+')',
                (symbol,cik,entry['title'],COMPANIES[symbol],submissions.get('sic'),datetime.now(timezone.utc).isoformat()))
        sid=source(s,symbol,'submissions',path,0)
        filings(s,submissions['filings']['recent'],symbol,cik,sid)
        for history in submissions['filings'].get('files',[]):
            if history.get('filingTo','')<'2010-01-01':continue
            name=history['name']
            if not re.fullmatch(r'CIK\d+-submissions-\d+\.json',name):raise ValueError('invalid history name')
            payload,path=client.get('https://data.sec.gov/submissions/'+name,symbol+'-history')
            sid=source(s,symbol,'history',path,0);filings(s,payload,symbol,cik,sid)
        payload,path=client.get('https://data.sec.gov/api/xbrl/companyfacts/CIK'+cik+'.json',symbol+'-facts')
        if str(int(payload['cik'])).zfill(10)!=cik:raise ValueError('facts CIK mismatch')
        sid=source(s,symbol,'facts',path,0);rows=fact_rows(payload,symbol,sid)
        insert_rows(s,'research_facts',rows)
        with s.cursor() as c:c.execute('UPDATE research_sources SET row_count='+s.mark+' WHERE id='+s.mark,(len(rows),sid))
        s.db.commit()
        print(encoded(dict(symbol=symbol,financial_observations=len(rows))),flush=True)
        if market:
            bars=fetch_daily([symbol],start,end,feed='iex')
            if not bars:raise ValueError('no market observations: '+symbol)
            raw=encoded([asdict(b) for b in bars]);sha=hashlib.sha256(raw.encode()).hexdigest()
            directory=root/'data/research_sources'/date.today().isoformat();directory.mkdir(parents=True,exist_ok=True)
            path=directory/(symbol+'-market-'+sha+'.json');path.write_text(raw)
            s.ingest(bars);source(s,symbol,'alpaca-iex-raw',path,len(bars));s.db.commit()
            print(encoded(dict(symbol=symbol,daily_bars=len(bars),first=bars[0].ts,last=bars[-1].ts)),flush=True)


def views(s):
    with s.cursor() as c:
        c.execute('''CREATE OR REPLACE VIEW research_financials AS
            SELECT f.*,d.accepted_utc,d.report_date,d.primary_document
            FROM research_facts f LEFT JOIN research_filings d
            ON d.cik=f.cik AND d.accession=f.accession''')
        c.execute('''CREATE OR REPLACE VIEW research_market_daily AS
            SELECT b.* FROM bars b JOIN research_companies c ON b.symbol=c.symbol
            WHERE b.source='alpaca-iex' AND b.adjustment='raw' ''')
        c.execute('''CREATE OR REPLACE VIEW research_coverage AS
            SELECT c.symbol,c.name,c.research_group,c.cik,
            (SELECT COUNT(*) FROM research_facts f WHERE f.cik=c.cik) AS financial_observations,
            (SELECT COUNT(DISTINCT tag) FROM research_facts f WHERE f.cik=c.cik) AS financial_tags,
            (SELECT COUNT(*) FROM research_filings d WHERE d.cik=c.cik) AS reports,
            (SELECT MIN(period_end) FROM research_facts f WHERE f.cik=c.cik) AS earliest_financial_period,
            (SELECT MAX(period_end) FROM research_facts f WHERE f.cik=c.cik AND context_status='ordinary') AS latest_financial_period,
            (SELECT COUNT(*) FROM bars b WHERE b.symbol=c.symbol AND source='alpaca-iex' AND adjustment='raw') AS daily_bars,
            (SELECT MIN(ts) FROM bars b WHERE b.symbol=c.symbol AND source='alpaca-iex' AND adjustment='raw') AS first_market_timestamp,
            (SELECT MAX(ts) FROM bars b WHERE b.symbol=c.symbol AND source='alpaca-iex' AND adjustment='raw') AS last_market_timestamp
            FROM research_companies c''')
    s.db.commit()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--symbols',nargs='+',choices=COMPANIES,default=list(COMPANIES))
    parser.add_argument('--market-start',default='2016-01-01T00:00:00Z')
    parser.add_argument('--market-end',default=datetime.now(timezone.utc).strftime('%Y-%m-%dT00:00:00Z'))
    parser.add_argument('--skip-market',action='store_true')
    args=parser.parse_args();root=Path(__file__).resolve().parents[1];load_env(root)
    s=Store('mysql')
    try:collect(s,root,args.symbols,args.market_start,args.market_end,not args.skip_market);views(s)
    finally:s.close()

if __name__=='__main__':main()
