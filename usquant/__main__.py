import argparse
import json
import math
import uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path
from .data import Bar,read_csv,write_csv
from .storage import Store
from .engine import run
from .report import render

ROOT = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser(description='US equities MVP: read-only data + local execution')
    p.add_argument('command',choices=['demo','ingest','backtest','paper','fetch','live'])
    p.add_argument('--backend',choices=['sqlite','mysql'],default='sqlite')
    p.add_argument('--csv',type=Path)
    p.add_argument('--symbol',default='SPY')
    p.add_argument('--source',default='synthetic')
    p.add_argument('--start')
    p.add_argument('--end')
    p.add_argument('--feed',choices=['iex','sip'],default='iex')
    p.add_argument('--native',action='store_true')
    p.add_argument('--config',type=Path,default=ROOT/'config/example.json')
    a=p.parse_args()
    if a.command=='live': p.error('实盘下单已禁用，必须单独确认并完成实现审查')
    (ROOT/'data').mkdir(exist_ok=True)
    (ROOT/'reports').mkdir(exist_ok=True)
    config=json.loads(a.config.read_text())
    store=Store(a.backend,str(ROOT/'data/market.sqlite'))
    try:
        if a.command=='demo':
            bars=[]
            dt=datetime(2024,1,2,21,tzinfo=timezone.utc)
            for i in range(260):
                while dt.weekday()>4: dt+=timedelta(days=1)
                close=100+i*.035+6*math.sin(i/9)
                op=close+0.25*math.cos(i)
                bars.append(Bar('SPY',dt.isoformat(),op,max(op,close)+1,min(op,close)-1,close,1000000,'synthetic'))
                dt+=timedelta(days=1)
            write_csv(ROOT/'data/synthetic.csv',bars)
            store.ingest(bars)
        elif a.command=='ingest':
            if not a.csv: p.error('--csv required')
            bars=read_csv(a.csv)
            store.ingest(bars)
            print(json.dumps({'validated_bars':len(bars)})); return
        elif a.command=='fetch':
            if not a.start or not a.end: p.error('--start and --end required')
            from .alpaca import fetch_daily
            bars=fetch_daily([a.symbol],a.start,a.end,a.feed)
            # Immutable raw snapshot accompanies normalized database records.
            snapshot=ROOT/'data'/('alpaca-'+uuid.uuid4().hex+'.csv')
            write_csv(snapshot,bars)
            store.ingest(bars)
            print(json.dumps({'bars':len(bars),'snapshot':str(snapshot)})); return
        else:
            bars=store.load(a.symbol,a.source)
        result=run(bars,config,a.native,'local-paper' if a.command=='paper' else 'backtest')
        run_id=uuid.uuid4().hex
        store.save_run(run_id,result)
        (ROOT/'reports'/ (run_id+'.json')).write_text(json.dumps(result,indent=2,allow_nan=False))
        render(result,ROOT/'reports/latest.html')
        print(json.dumps({'run_id':run_id,**result['summary'],'report':str(ROOT/'reports/latest.html')},indent=2))
    finally: store.close()

if __name__=='__main__': main()
