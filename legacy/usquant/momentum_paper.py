"""Adjusted-price research simulation; cannot submit orders."""
import argparse
import hashlib
import html
import json
import math
import statistics
import uuid
from dataclasses import asdict
from datetime import date,datetime,timezone
from pathlib import Path
from .alpaca import fetch_daily
from .financial_database import load_env
from .storage import Store
from .paper_broker import PaperBroker


def targets(series,day,cfg):
    candidates=[]
    for symbol,bars in series.items():
        known=[b for b in bars if b.ts[:10]<=day]
        n=cfg['lookback'];skip=cfg['skip'];v=cfg['vol_window']
        if len(known)<max(n+1,v+1):continue
        if (date.fromisoformat(day)-date.fromisoformat(known[-1].ts[:10])).days>4:continue
        score=known[-1-skip].close/known[-1-n].close-1
        returns=[known[i].close/known[i-1].close-1 for i in range(len(known)-v,len(known))]
        vol=statistics.stdev(returns)
        if score>0 and vol>0:candidates.append((score,symbol,vol))
    chosen=sorted(candidates,key=lambda x:(-x[0],x[1]))[:cfg['top_n']]
    scale=sum(1/r[2] for r in chosen)
    weights={r[1]:min(cfg['max_weight'],cfg['gross_limit']*(1/r[2])/scale) for r in chosen}
    return weights,[dict(symbol=s,score=m,volatility=v,weight=weights.get(s,0)) for m,s,v in chosen]


def simulate(series,cfg):
    if cfg.get('mode')!='local-paper':raise ValueError('only local-paper is supported')
    if not 0<cfg['skip']<cfg['lookback'] or cfg['vol_window']<2:raise ValueError('invalid windows')
    if not 0<cfg['max_weight']<=cfg['gross_limit']<=1:raise ValueError('invalid allocation')
    if cfg['initial_cash']<=0 or not 0<=cfg['one_way_cost_bps']<10000:raise ValueError('invalid costs')
    if any(b.adjustment!='all' for bars in series.values() for b in bars):raise ValueError('all-adjusted bars required')
    maps={s:{b.ts[:10]:b for b in bars} for s,bars in series.items()}
    # Conservative common-session calendar; missing bars are audited, never forward filled.
    common=sorted(set.intersection(*[{b.ts[:10] for b in bars} for bars in series.values()]))
    days=[d for d in common if d>=cfg['start']]
    if not days:raise ValueError('no common trading sessions')
    cash=float(cfg['initial_cash']);qty={s:0.0 for s in series};curve=[];trades=[]
    peak=previous=cash;halted=False;pending=None;last_month=None
    cost=cfg['one_way_cost_bps']/10000
    for day in days:
        equity_open=cash+sum(qty[s]*maps[s][day].open for s in series)
        if equity_open<=peak*(1-cfg['max_drawdown']) or equity_open<=previous*(1-cfg['max_daily_loss']):halted=True
        if halted:pending={}
        if pending is not None:
            # Sells precede buys; fractional adjusted units are research accounting only.
            desired={s:(equity_open*pending.get(s,0)/maps[s][day].open) for s in series}
            for symbol in sorted(series,key=lambda s:desired[s]-qty[s]):
                delta=desired[symbol]-qty[symbol];price=maps[symbol][day].open
                if abs(delta*price)<0.01:continue
                if delta>0:delta=min(delta,max(0,cash)/(price*(1+cost)))
                fee=abs(delta*price)*cost;cash-=delta*price+fee;qty[symbol]+=delta
                trades.append(dict(date=day,symbol=symbol,delta=delta,adjusted_price=price,cost=fee))
            pending=None
        equity=cash+sum(qty[s]*maps[s][day].close for s in series)
        peak=max(peak,equity)
        if equity<=peak*(1-cfg['max_drawdown']) or equity<=previous*(1-cfg['max_daily_loss']):halted=True
        curve.append(dict(date=day,equity=equity,cash=cash,drawdown=1-equity/peak,halted=halted))
        # Monthly signal at the FIRST observed session's CLOSE -> following session OPEN.
        month=day[:7]
        if not halted and month!=last_month:pending,_=targets(series,day,cfg)
        last_month=month;previous=equity
    return dict(mode='local-paper',config=cfg,curve=curve,trades=trades,halted=halted,
        common_session_count=len(days),missing_sessions={s:len(set.union(*[set(m) for m in maps.values()])-set(maps[s])) for s in series},
        summary=dict(initial_cash=cfg['initial_cash'],final_equity=curve[-1]['equity'],
                     total_return=curve[-1]['equity']/cfg['initial_cash']-1,
                     max_drawdown=max(r['drawdown'] for r in curve),fills=len(trades)))


def segments(curve,initial_cash=2500):
    results={}
    for name,start,end in [('development','2021-07-01','2023-12-31'),('validation','2024-01-01','2024-12-31'),('retrospective_test','2025-01-01','9999-12-31')]:
        indices=[i for i,r in enumerate(curve) if start<=r['date']<=end]
        if not indices:continue
        first,last=indices[0],indices[-1]
        base=curve[first-1]['equity'] if first else initial_cash
        results[name]=dict(start=curve[first]['date'],end=curve[last]['date'],return_=curve[last]['equity']/base-1)
    return results


def render(result,path):
    summary=result['summary']
    rows=''.join('<tr><td>'+html.escape(k)+'</td><td>'+html.escape(str(v))+'</td></tr>' for k,v in summary.items())
    points=result['curve'];lo=min(p['equity'] for p in points);hi=max(p['equity'] for p in points)
    poly=' '.join(f'{20+960*i/max(1,len(points)-1):.2f},{220-200*(p["equity"]-lo)/max(1,hi-lo):.2f}' for i,p in enumerate(points))
    path.write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><title>USQuant Paper Research</title>
<style>body{font:16px system-ui;max-width:1000px;margin:40px auto;padding:20px;color:#142331}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left}svg{width:100%;background:#f4f7fa}p{line-height:1.6}</style>
<h1>USQuant · Paper Research</h1><p>Fixed-parameter momentum and volatility allocation. Retrospective, eight selected stocks; no order submission. IEX all-adjusted prices and fractional adjusted units. This is research accounting, not an executable historical share ledger or a validated strategy.</p>
<svg viewBox="0 0 1000 250" role="img" aria-label="Simulated account equity"><polyline fill="none" stroke="#176c88" stroke-width="2" points="'''+poly+'"/></svg><p>Equity range: '+f'{lo:.2f}–{hi:.2f}'+'</p><table>'+rows+'</table><h2>Time segments</h2><pre>'+html.escape(json.dumps(result['segments'],indent=2))+'''</pre><p>A drawdown/daily-loss breach permanently stops new exposure and schedules liquidation at the next observed open. This small account may stop early; do not loosen limits to improve results. No untouched holdout is claimed. Data revisions, calendar intersections, survivorship and ticker histories limit conclusions.</p></html>''')


def main():
    root=Path(__file__).resolve().parents[1];load_env(root)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh-data',action='store_true')
    args=parser.parse_args();cfg=json.loads((root/'config/momentum-paper.json').read_text())
    store=Store('mysql')
    try:
        series={}
        for symbol in cfg['symbols']:
            if args.refresh_data:
                bars=fetch_daily([symbol],'2020-01-01T00:00:00Z',datetime.now(timezone.utc).strftime('%Y-%m-%dT00:00:00Z'),'iex','all')
                directory=root/'data/adjusted';directory.mkdir(exist_ok=True)
                text=json.dumps([asdict(b) for b in bars]);digest=hashlib.sha256(text.encode()).hexdigest()
                (directory/(symbol+'-'+digest+'.json')).write_text(text)
                store.ingest(bars)
            series[symbol]=store.load(symbol,'alpaca-iex','all')
            if not series[symbol]:raise ValueError('fetch adjusted data first: '+symbol)
        result=simulate(series,cfg);result['segments']=segments(result['curve'],cfg['initial_cash'])
        latest=min(bars[-1].ts[:10] for bars in series.values())
        weights,scores=targets(series,latest,cfg)
        # Suggestions are not broker orders and must not override the account halt.
        result['latest_signal']=dict(date=latest,weights=weights,scores=scores,
            executable=False,blocked_reason='research-only; account and live data reconciliation required')
        result['data_sha256']=hashlib.sha256(json.dumps({s:[asdict(b) for b in bars] for s,bars in series.items()},sort_keys=True).encode()).hexdigest()
        try:
            broker=PaperBroker();clock=broker.request('/v2/clock');account=broker.request('/v2/account')
            result['broker_check']=dict(mode='alpaca-paper',account_status=account['status'],market_open=clock['is_open'],next_open=clock['next_open'],orders_submitted=0)
        except Exception as exc:result['broker_check']=dict(status='unverified',error_type=type(exc).__name__,orders_submitted=0)
        run_id=uuid.uuid4().hex;store.save_run(run_id,result)
        (root/'reports'/('momentum-'+run_id+'.json')).write_text(json.dumps(result,indent=2,allow_nan=False))
        render(result,root/'reports/momentum-paper.html')
        print(json.dumps(dict(run_id=run_id,**result['summary'],halted=result['halted'],broker=result['broker_check'],report=str(root/'reports/momentum-paper.html'))))
    finally:store.close()

if __name__=='__main__':main()
