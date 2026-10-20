import csv
import math
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

@dataclass(frozen=True)
class Bar:
    symbol: str
    ts: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    source: str = 'csv'
    adjustment: str = 'raw'

def clean(rows):
    """Reject malformed data; identical duplicates collapse, conflicts fail closed."""
    result = {}
    for row in rows:
        d = asdict(row) if isinstance(row, Bar) else dict(row)
        d['symbol'] = d['symbol'].upper().strip()
        if not re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,14}', d['symbol']):
            raise ValueError('invalid symbol')
        dt = datetime.fromisoformat(d['ts'].replace('Z', '+00:00'))
        if dt.tzinfo is None:
            raise ValueError('timezone required')
        d['ts'] = dt.astimezone(timezone.utc).isoformat()
        for k in ('open','high','low','close'):
            d[k] = float(d[k])
            if not math.isfinite(d[k]) or d[k] <= 0:
                raise ValueError('invalid price')
        v = float(d['volume'])
        if not math.isfinite(v) or v < 0 or not v.is_integer():
            raise ValueError('invalid volume')
        d['volume'] = int(v)
        if d['low'] > min(d['open'],d['close']) or d['high'] < max(d['open'],d['close']) or d['low'] > d['high']:
            raise ValueError('inconsistent OHLC')
        bar = Bar(**d)
        if bar.adjustment not in ('raw','split','all'):
            raise ValueError('unknown adjustment')
        key = (bar.symbol, bar.ts, bar.source, bar.adjustment)
        if key in result and result[key] != bar:
            raise ValueError('conflicting duplicate')
        result[key] = bar
    return sorted(result.values(), key=lambda b: (b.ts,b.symbol))

def read_csv(path):
    with open(path, newline='') as f:
        return clean(csv.DictReader(f))

def write_csv(path, bars):
    with open(path,'w',newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(Bar.__dataclass_fields__))
        writer.writeheader()
        writer.writerows(asdict(b) for b in bars)
