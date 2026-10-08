"""Read-only market-data adapter. There is deliberately no submit_order API."""
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from .data import clean

DATA_URL = 'https://data.alpaca.markets/v2/stocks/bars'

def fetch_daily(symbols, start, end, feed='iex'):
    if feed not in ('iex','sip'): raise ValueError('unsupported feed')
    start_dt = datetime.fromisoformat(start.replace('Z','+00:00'))
    end_dt = datetime.fromisoformat(end.replace('Z','+00:00'))
    if start_dt.tzinfo is None or end_dt.tzinfo is None or start_dt >= end_dt:
        raise ValueError('require timezone-aware start < end')
    if end_dt > datetime.now(timezone.utc): raise ValueError('end must be in the past')
    params = dict(symbols=','.join(symbols),start=start,end=end,timeframe='1Day',
                  adjustment='raw',feed=feed,limit=10000,sort='asc')
    headers = {'APCA-API-KEY-ID':os.environ['ALPACA_API_KEY'],
               'APCA-API-SECRET-KEY':os.environ['ALPACA_SECRET_KEY']}
    rows, seen = [],set()
    while True:
        req = urllib.request.Request(DATA_URL+'?'+urllib.parse.urlencode(params),headers=headers)
        with urllib.request.urlopen(req,timeout=30) as response: payload=json.load(response)
        for symbol, bars in payload.get('bars',{}).items():
            for b in bars:
                rows.append(dict(symbol=symbol,ts=b['t'],open=b['o'],high=b['h'],low=b['l'],close=b['c'],volume=b['v'],source='alpaca-'+feed,adjustment='raw'))
        token = payload.get('next_page_token')
        if not token: break
        if token in seen: raise ValueError('repeated pagination token')
        seen.add(token)
        params['page_token'] = token
    return clean(rows)

class LiveBroker:
    def __init__(self, *args, **kwargs):
        raise PermissionError('Live orders are disabled. Separate user confirmation and implementation review required.')
