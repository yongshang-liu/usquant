"""Resumable SEC issuer inventory and financial coverage audit.

The current ticker directory is a discovery seed, never a historical universe.
Raw companyfacts snapshots preserve all returned standard concepts; the normalized
financial_facts table remains the explicitly documented US-GAAP subset.
"""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from .fundamentals import SECClient, TAGS, as_of, ingest, normalize, initialize as facts_initialize
from .storage import Store


def now():
    return datetime.now(timezone.utc).isoformat()


def initialize(store):
    facts_initialize(store)
    with store.cursor() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS sec_directory_snapshots (
            id CHAR(64) PRIMARY KEY, retrieved_at VARCHAR(40) NOT NULL,
            snapshot_path TEXT NOT NULL, issuer_count INTEGER NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS sec_issuers (
            cik CHAR(10) PRIMARY KEY, name TEXT NOT NULL, symbol VARCHAR(16) NOT NULL,
            listings TEXT NOT NULL, first_seen VARCHAR(40) NOT NULL,
            last_seen VARCHAR(40) NOT NULL, directory_id CHAR(64) NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS sec_import_attempts (
            id CHAR(32) PRIMARY KEY, cik CHAR(10) NOT NULL, started_at VARCHAR(40) NOT NULL,
            finished_at VARCHAR(40) NOT NULL, status VARCHAR(24) NOT NULL,
            snapshot_path TEXT NOT NULL, fact_count INTEGER NOT NULL,
            inserted_count INTEGER NOT NULL, error_code VARCHAR(80) NOT NULL)''')
    store.db.commit()


def catalog(store, payload, path):
    import hashlib
    initialize(store)
    grouped = {}
    required = ['cik', 'name', 'ticker', 'exchange']
    fields = payload['fields']
    if any(x not in fields for x in required):
        raise ValueError('unsupported SEC directory fields')
    for row in payload['data']:
        entry = dict(zip(fields, row))
        cik = str(int(entry['cik'])).zfill(10)
        if len(cik) != 10: raise ValueError('invalid directory CIK')
        issuer = grouped.setdefault(cik, dict(name=entry['name'], listings=[]))
        issuer['listings'].append(dict(symbol=entry['ticker'], exchange=entry['exchange']))
    raw = Path(path).read_bytes()
    identity = hashlib.sha256(raw).hexdigest()
    timestamp = now()
    try:
        with store.cursor() as c:
            c.execute('SELECT id FROM sec_directory_snapshots WHERE id='+store.mark, (identity,))
            if not c.fetchone():
                c.execute('INSERT INTO sec_directory_snapshots VALUES ('+','.join([store.mark]*4)+')',
                          (identity,timestamp,str(path),len(grouped)))
            for cik, issuer in sorted(grouped.items()):
                # Keep the first reported symbol stable across refreshes. Identity is CIK.
                listings = json.dumps(issuer['listings'],sort_keys=True)
                c.execute('SELECT symbol FROM sec_issuers WHERE cik='+store.mark,(cik,))
                old = c.fetchone()
                if old:
                    c.execute('UPDATE sec_issuers SET name='+store.mark+', listings='+store.mark+
                              ', last_seen='+store.mark+', directory_id='+store.mark+' WHERE cik='+store.mark,
                              (issuer['name'],listings,timestamp,identity,cik))
                else:
                    symbol = issuer['listings'][0]['symbol'].upper()
                    c.execute('INSERT INTO sec_issuers VALUES ('+','.join([store.mark]*7)+')',
                              (cik,issuer['name'],symbol,listings,timestamp,timestamp,identity))
        store.db.commit()
    except Exception:
        store.db.rollback()
        raise
    return len(grouped)


def candidates(store, refresh=False):
    with store.cursor() as c:
        c.execute('SELECT cik,symbol FROM sec_issuers ORDER BY cik')
        issuers = c.fetchall()
        # Success means a completed snapshot, including issuers without mapped metrics.
        c.execute("SELECT DISTINCT cik FROM sec_import_attempts WHERE status IN ('success','no_supported_metrics')")
        completed = {r[0] for r in c.fetchall()}
    return [r for r in issuers if refresh or r[0] not in completed]


def run_batch(store, client, limit=None, refresh=False):
    import uuid
    initialize(store)
    targets = candidates(store, refresh)
    if limit is not None: targets = targets[:limit]
    results = []
    for cik, symbol in targets:
        identity = uuid.uuid4().hex
        started = now()
        with store.cursor() as c:
            c.execute('INSERT INTO sec_import_attempts VALUES ('+','.join([store.mark]*9)+')',
                      (identity,cik,started,'','running','',0,0,''))
        store.db.commit()
        status, path, count, added, error = 'success','',0,0,''
        try:
            payload, snapshot = client.get('https://data.sec.gov/api/xbrl/companyfacts/CIK'+cik+'.json',cik)
            path = str(snapshot)
            if str(int(payload['cik'])).zfill(10) != cik: raise ValueError('CIK mismatch')
            rows = normalize(payload,symbol)
            count = len(rows)
            added = ingest(store,rows)
            if not count: status = 'no_supported_metrics'
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
            store.db.rollback()
            status = 'failed'
            # Never persist exception text that might contain request credentials.
            error = 'HTTP_'+str(exc.code) if isinstance(exc,HTTPError) else type(exc).__name__
        with store.cursor() as c:
            c.execute('UPDATE sec_import_attempts SET finished_at='+store.mark+', status='+store.mark+
                      ', snapshot_path='+store.mark+', fact_count='+store.mark+', inserted_count='+store.mark+
                      ', error_code='+store.mark+' WHERE id='+store.mark,
                      (now(),status,path,count,added,error,identity))
        store.db.commit()
        result=dict(cik=cik,symbol=symbol,status=status,facts=count,inserted=added,error=error)
        print(json.dumps(result),flush=True)
        results.append(result)
        # Stop the run on access/rate-limit or network failures; resume explicitly.
        if error in ('HTTP_403','HTTP_429','URLError','TimeoutError'): break
    return results


def coverage(store, start_year=2010):
    initialize(store)
    with store.cursor() as c:
        c.execute('SELECT COUNT(*) FROM sec_issuers')
        issuer_count=c.fetchone()[0]
        c.execute('SELECT status,COUNT(*) FROM sec_import_attempts GROUP BY status')
        attempts=dict(c.fetchall())
        c.execute('''SELECT cik,metric,MIN(period_end),MAX(period_end),COUNT(*)
                     FROM financial_facts WHERE period_end >= '''+store.mark+
                  ' GROUP BY cik,metric ORDER BY cik,metric',(str(start_year)+'-01-01',))
        metrics=[dict(cik=r[0],metric=r[1],earliest_end=r[2],latest_end=r[3],versions=r[4]) for r in c.fetchall()]
    return dict(start_year=start_year,discovered_issuers=issuer_count,attempts=attempts,
                pending_issuers=len(candidates(store)),covered_issuers=len({r['cik'] for r in metrics}),
                metrics=metrics)


def build_panel(store, start_year, cutoff):
    """Annual US-GAAP pilot panel. End-year is not the SEC filing's fiscal-year label.

    Only 10-K duration contexts of 330-400 days qualify. Missing/ambiguous values
    are null with reasons; fiscal transition periods need separate treatment.
    Latest-at-cutoff observations are rebuilt, while raw versions remain intact.
    """
    from datetime import date
    initialize(store)
    with store.cursor() as c:
        c.execute('CREATE TABLE IF NOT EXISTS annual_panel (cik CHAR(10) NOT NULL, period_end VARCHAR(10) NOT NULL, cutoff VARCHAR(10) NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(cik,period_end,cutoff))')
        c.execute('SELECT DISTINCT cik,symbol FROM financial_facts ORDER BY cik,symbol')
        issuers=c.fetchall()
    count=0
    try:
        for cik,symbol in issuers:
            selected=as_of(store,symbol,cutoff)
            annual=[f for f in selected if f['form'] in ('10-K','10-K/A')
                    and f['start'] and 330 <= (date.fromisoformat(f['end'])-date.fromisoformat(f['start'])).days+1 <=400
                    and f['end'] >= str(start_year)+'-01-01']
            ends=sorted({f['end'] for f in annual})
            for end in ends:
                metrics={}
                for metric,tags in TAGS.items():
                    instant=metric in ('assets','liabilities','equity','cash')
                    options=[f for f in selected if f['end']==end and f['metric']==metric
                             and (not f['start'] if instant else f in annual)]
                    # A single tag may still have conflicting duration contexts.
                    chosen=[]
                    for tag in tags:
                        chosen=[f for f in options if f['tag']==tag]
                        if chosen: break
                    if len(chosen)==1:
                        f=chosen[0]
                        metrics[metric]=dict(value=f['value'],unit=f['unit'],tag=f['tag'],
                            start=f['start'],filed=f['filed'],accession=f['accn'],status='observed',
                            alias_count=len({x['tag'] for x in options}))
                    else:
                        metrics[metric]=dict(value=None,status='ambiguous_context' if chosen else 'missing')
                record=dict(cik=cik,symbol=symbol,period_end=end,period_end_year=int(end[:4]),
                            cutoff=cutoff,selection='latest_available_before_cutoff',metrics=metrics)
                with store.cursor() as c:
                    c.execute('DELETE FROM annual_panel WHERE cik='+store.mark+' AND period_end='+store.mark+' AND cutoff='+store.mark,(cik,end,cutoff))
                    c.execute('INSERT INTO annual_panel VALUES ('+','.join([store.mark]*4)+')',
                              (cik,end,cutoff,json.dumps(record,sort_keys=True)))
                count+=1
        store.db.commit()
    except Exception:
        store.db.rollback()
        raise
    return count


def load_env(root):
    path=root/'.env'
    if path.exists():
        for line in path.read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key,value=line.split('=',1)
                os.environ.setdefault(key.strip(),value.strip().strip('\"').strip("'"))


def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['discover','fetch','coverage','panel'])
    parser.add_argument('--backend',choices=['sqlite','mysql'],default='mysql')
    parser.add_argument('--limit',type=int,help='Maximum issuers in this run; omitted means all pending')
    parser.add_argument('--refresh',action='store_true',help='Fetch completed issuers again for new filings')
    parser.add_argument('--start-year',type=int,default=2010)
    args=parser.parse_args()
    if args.limit is not None and args.limit<1: parser.error('--limit must be positive')
    if not 1900<=args.start_year<=datetime.now().year: parser.error('invalid start year')
    load_env(root)
    (root/'data').mkdir(exist_ok=True)
    store=Store(args.backend,str(root/'data/market.sqlite'))
    try:
        initialize(store)
        if args.command=='panel':
            print(json.dumps(dict(annual_rows=build_panel(store,args.start_year,datetime.now().date().isoformat()))))
        elif args.command=='coverage':
            report=coverage(store,args.start_year)
            target=root/'reports/financial-coverage.json'
            target.parent.mkdir(exist_ok=True)
            target.write_text(json.dumps(report,indent=2))
            print(json.dumps({k:v for k,v in report.items() if k!='metrics'}))
            print(str(target))
        else:
            client=SECClient(os.getenv('SEC_USER_AGENT',''),root/'data/sec')
            if args.command=='discover':
                payload,path=client.get('https://www.sec.gov/files/company_tickers_exchange.json','directory')
                print(json.dumps(dict(discovered_issuers=catalog(store,payload,path))))
            else: run_batch(store,client,args.limit,args.refresh)
    finally: store.close()

if __name__=='__main__': main()
