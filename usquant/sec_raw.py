"""Archive and index SEC quarterly files without accounting transformations."""
import argparse
import csv
import hashlib
import json
import os
import re
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from .financial_database import load_env
from .paper_broker import NoRedirect
from .storage import Store

TABLES=('sub','num','tag','pre')

def initialize(store):
    with store.cursor() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS raw_sec_batches (
            batch_id CHAR(64) PRIMARY KEY, package_year INTEGER NOT NULL,
            package_quarter INTEGER NOT NULL, retrieved_at VARCHAR(40) NOT NULL,
            source_url TEXT NOT NULL, archive_path TEXT NOT NULL, manifest TEXT NOT NULL)''')
        for table in TABLES:
            c.execute('CREATE TABLE IF NOT EXISTS raw_sec_'+table+''' (
                batch_id CHAR(64) NOT NULL, source_row INTEGER NOT NULL,
                adsh VARCHAR(30), cik VARCHAR(10), sic VARCHAR(4),
                filed VARCHAR(16), period VARCHAR(16), payload LONGTEXT NOT NULL,
                PRIMARY KEY(batch_id,source_row))''')
    store.db.commit()


def archive(year,quarter,root,user_agent,extract=False,refresh=False):
    if not re.fullmatch(r'[^\r\n]+\s[^\s@]+@[^\s@]+\.[^\s@]+',user_agent):
        raise ValueError('SEC_USER_AGENT requires an application and contact email')
    url=f'https://www.sec.gov/files/dera/data/financial-statement-data-sets/{year}q{quarter}.zip'
    directory=root/'data/sec_raw'/str(year)/('Q'+str(quarter))
    directory.mkdir(parents=True,exist_ok=True)
    existing=sorted(directory.glob('*/manifest.json'))
    if existing and not refresh:
        manifest=max(existing,key=lambda p: json.loads(p.read_text())['retrieved_at'])
        metadata=json.loads(manifest.read_text())
        path=manifest.parent/'source.zip'
        if hashlib.sha256(path.read_bytes()).hexdigest()!=metadata['batch_id']:
            raise ValueError('stored archive checksum mismatch')
        with zipfile.ZipFile(path) as z:
            if z.testzip() is not None: raise ValueError('invalid ZIP checksum')
            for table in TABLES:
                matches=[n for n in z.namelist() if Path(n).name.lower()==table+'.txt']
                if len(matches)!=1: raise ValueError('invalid archived source files')
                raw=z.read(matches[0])
                if hashlib.sha256(raw).hexdigest()!=metadata['files'][table]['sha256']:
                    raise ValueError('archived file checksum mismatch')
                if extract: (manifest.parent/(table+'.txt')).write_bytes(raw)
        return manifest.parent,metadata
    temp=directory/'download.part'
    request=urllib.request.Request(url,headers={'User-Agent':user_agent})
    sha=hashlib.sha256()
    opener=urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(request,timeout=90) as response, temp.open('wb') as out:
            while True:
                chunk=response.read(1024*1024)
                if not chunk: break
                out.write(chunk); sha.update(chunk)
        identity=sha.hexdigest()
        target=directory/identity
        target.mkdir(exist_ok=True)
        path=target/'source.zip'
        if path.exists():
            if hashlib.sha256(path.read_bytes()).hexdigest()!=identity: raise ValueError('archive checksum mismatch')
            temp.unlink()
        else: temp.replace(path)
        files={}
        with zipfile.ZipFile(path) as z:
            if z.testzip() is not None: raise ValueError('invalid ZIP checksum')
            for table in TABLES:
                matches=[n for n in z.namelist() if Path(n).name.lower()==table+'.txt']
                if len(matches)!=1: raise ValueError('missing or ambiguous source file: '+table)
                raw=z.read(matches[0])
                destination=target/(table+'.txt')
                if destination.exists() and destination.read_bytes()!=raw: raise ValueError('stored source changed')
                if extract: destination.write_bytes(raw)
                files[table]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        metadata=dict(batch_id=identity,package_year=year,package_quarter=quarter,
                      source_url=url,retrieved_at=datetime.now(timezone.utc).isoformat(),files=files)
        manifest=target/'manifest.json'
        if manifest.exists(): metadata=json.loads(manifest.read_text())
        else: manifest.write_text(json.dumps(metadata,indent=2))
        return target,metadata
    finally:
        if temp.exists(): temp.unlink()


def ingest_archive(store,directory,metadata):
    initialize(store)
    identity=metadata['batch_id']
    with store.cursor() as c:
        c.execute('SELECT batch_id FROM raw_sec_batches WHERE batch_id='+store.mark,(identity,))
        if c.fetchone(): return dict(already_imported=True)
    counts={}
    try:
        for table in TABLES:
            path=directory/(table+'.txt')
            if hashlib.sha256(path.read_bytes()).hexdigest()!=metadata['files'][table]['sha256']:
                raise ValueError('source checksum mismatch')
            count=0; pending=[]
            with path.open(encoding='utf-8-sig',newline='') as source:
                reader=csv.DictReader(source,delimiter='\t')
                headers=reader.fieldnames
                if not headers or len(set(headers))!=len(headers): raise ValueError('invalid source headers')
                for count,row in enumerate(reader,1):
                    if None in row or any(v is None for v in row.values()): raise ValueError('invalid source row width')
                    # Preserve every field as its source string, including blanks.
                    pending.append((identity,count,row.get('adsh'),row.get('cik'),row.get('sic'),
                                    row.get('filed'),row.get('period'),json.dumps(row,ensure_ascii=False)))
                    if len(pending)==1000:
                        insert(store,table,pending); pending=[]
                if pending: insert(store,table,pending)
            counts[table]=count
        with store.cursor() as c:
            c.execute('INSERT INTO raw_sec_batches VALUES ('+','.join([store.mark]*7)+')',
                      (identity,metadata['package_year'],metadata['package_quarter'],metadata['retrieved_at'],
                       metadata['source_url'],str(directory/'source.zip'),json.dumps(dict(metadata,row_counts=counts))))
        store.db.commit()
    except Exception:
        store.db.rollback(); raise
    return counts


def insert(store,table,rows):
    if table not in TABLES: raise ValueError('invalid table')
    with store.cursor() as c:
        c.executemany('INSERT INTO raw_sec_'+table+' VALUES ('+','.join([store.mark]*8)+')',rows)


def readable_views(store,directory):
    """Expose every original source field as a separate text column."""
    with store.cursor() as c:
        for table in TABLES:
            with (directory/(table+'.txt')).open(encoding='utf-8-sig',newline='') as source:
                headers=next(csv.reader(source,delimiter='\t'))
            if any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',h) for h in headers):
                raise ValueError('unsupported source column identifier')
            fields=["JSON_UNQUOTE(JSON_EXTRACT(r.payload,'$."+h+"')) AS `"+h+"`" for h in headers]
            c.execute('CREATE OR REPLACE VIEW raw_sec_'+table+'_readable AS SELECT '
                      'b.package_year,b.package_quarter,r.batch_id,r.source_row,'+
                      ','.join(fields)+' FROM raw_sec_'+table+' r JOIN raw_sec_batches b ON b.batch_id=r.batch_id')
    store.db.commit()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-mysql',action='store_true',help='Explicitly extract and import; default only archives ZIP')
    parser.add_argument('--refresh',action='store_true',help='Check SEC for a new source version')
    parser.add_argument('--year',type=int,required=True)
    parser.add_argument('--quarter',type=int,choices=range(1,5),required=True)
    args=parser.parse_args()
    if not 2009<=args.year<=datetime.now().year: parser.error('invalid year')
    root=Path(__file__).resolve().parents[1]; load_env(root)
    directory,metadata=archive(args.year,args.quarter,root,os.getenv('SEC_USER_AGENT',''),extract=args.import_mysql,refresh=args.refresh)
    if not args.import_mysql:
        print(json.dumps(dict(package=f'{args.year}Q{args.quarter}',status='archived',path=str(directory/'source.zip'))))
        return
    store=Store('mysql')
    try:
        result=ingest_archive(store,directory,metadata)
        readable_views(store,directory)
        print(json.dumps(dict(package=f'{args.year}Q{args.quarter}',result=result)))
    finally: store.close()

if __name__=='__main__': main()
