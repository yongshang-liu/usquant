import json
import math
import os
import sqlite3
from dataclasses import asdict
from .data import Bar, clean

SCHEMA = '''CREATE TABLE IF NOT EXISTS bars (
symbol VARCHAR(16) NOT NULL, ts VARCHAR(40) NOT NULL,
open DOUBLE NOT NULL, high DOUBLE NOT NULL, low DOUBLE NOT NULL,
close DOUBLE NOT NULL, volume BIGINT NOT NULL,
source VARCHAR(32) NOT NULL, adjustment VARCHAR(8) NOT NULL,
PRIMARY KEY(symbol,ts,source,adjustment))'''

class Store:
    def __init__(self, backend='sqlite', path='data/market.sqlite'):
        self.backend = backend
        if backend == 'sqlite':
            self.db = sqlite3.connect(path)
            self.mark = '?'
        elif backend == 'mysql':
            import pymysql
            self.db = pymysql.connect(host=os.getenv('MYSQL_HOST','127.0.0.1'),
                port=int(os.getenv('MYSQL_PORT','3306')), user=os.environ['MYSQL_USER'],
                password=os.environ['MYSQL_PASSWORD'], database=os.getenv('MYSQL_DATABASE','usquant'),
                charset='utf8mb4', autocommit=False)
            self.mark = '%s'
        else:
            raise ValueError('unsupported backend')
        with self.cursor() as c:
            c.execute(SCHEMA)
            c.execute('CREATE TABLE IF NOT EXISTS runs (id VARCHAR(40) PRIMARY KEY, payload TEXT NOT NULL)')
        self.db.commit()

    def cursor(self):
        from contextlib import contextmanager
        @contextmanager
        def managed():
            c = self.db.cursor()
            try: yield c
            finally: c.close()
        return managed()

    def ingest(self, bars):
        bars = clean(bars)
        try:
            with self.cursor() as c:
                for b in bars:
                    values = tuple(asdict(b).values())
                    c.execute('SELECT * FROM bars WHERE symbol='+self.mark+' AND ts='+self.mark+' AND source='+self.mark+' AND adjustment='+self.mark,
                              (b.symbol,b.ts,b.source,b.adjustment))
                    old = c.fetchone()
                    if old is not None:
                        same = all(math.isclose(float(a),float(b),rel_tol=1e-12,abs_tol=1e-12)
                                   if 2 <= i <= 5 else a == b
                                   for i,(a,b) in enumerate(zip(old,values)))
                        if not same: raise ValueError('stored duplicate conflict')
                        continue
                    c.execute('INSERT INTO bars VALUES ('+','.join([self.mark]*9)+')',values)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def load(self, symbol, source='synthetic', adjustment='raw'):
        with self.cursor() as c:
            c.execute('SELECT * FROM bars WHERE symbol='+self.mark+' AND source='+self.mark+' AND adjustment='+self.mark+' ORDER BY ts', (symbol,source,adjustment))
            return [Bar(*r) for r in c.fetchall()]

    def save_run(self, run_id, payload):
        with self.cursor() as c:
            c.execute('INSERT INTO runs VALUES ('+self.mark+','+self.mark+')',(run_id,json.dumps(payload,allow_nan=False)))
        self.db.commit()

    def close(self): self.db.close()
