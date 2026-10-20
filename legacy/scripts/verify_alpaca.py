"""Read-only paper-account and historical-data verification; never submits orders."""
import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    # Read simple KEY=value entries without executing the configuration as shell code.
    env_file = ROOT / '.env'
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip().strip('\"').strip("'"))
    missing = [key for key in ('ALPACA_API_KEY', 'ALPACA_SECRET_KEY') if not os.environ.get(key)]
    if missing:
        print('Configure paper-account credentials in local .env first. Do not share keys in chat or GitHub.')
        return 2
    from usquant.paper_broker import PaperBroker
    from usquant.alpaca import fetch_daily
    from usquant.data import write_csv
    from usquant.storage import Store
    from usquant.engine import run
    from usquant.report import render

    account = PaperBroker().request('/v2/account')
    print(json.dumps({'endpoint': 'paper-api.alpaca.markets', 'account_status': account['status'],
                      'orders_submitted': 0}))
    bars = fetch_daily(['SPY'], '2024-01-01T00:00:00Z', '2025-01-01T00:00:00Z', 'iex')
    if not bars:
        raise ValueError('No historical bars returned; check data permissions')
    (ROOT / 'data').mkdir(exist_ok=True)
    (ROOT / 'reports').mkdir(exist_ok=True)
    snapshot = ROOT / 'data' / ('alpaca-' + uuid.uuid4().hex + '.csv')
    write_csv(snapshot, bars)
    store = Store('mysql')
    try:
        store.ingest(bars)
        stored = store.load('SPY', 'alpaca-iex')
        # Restrict this verification run to the downloaded period.
        stored = [b for b in stored if '2024-01-01' <= b.ts < '2025-01-01']
        config = json.loads((ROOT / 'config/example.json').read_text())
        result = run(stored, config, True)
        run_id = uuid.uuid4().hex
        store.save_run(run_id, result)
        (ROOT / 'reports' / (run_id + '.json')).write_text(json.dumps(result, indent=2, allow_nan=False))
        render(result, ROOT / 'reports/latest.html')
        print(json.dumps({'source': 'alpaca-iex', 'bars': len(stored), 'snapshot': str(snapshot),
                          'run_id': run_id, 'report': str(ROOT / 'reports/latest.html'),
                          'summary': result['summary']}, indent=2))
    finally:
        store.close()
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        # Do not dump response bodies, account objects, or credentials.
        print('Verification stopped: ' + type(error).__name__ + '. Check credentials, API access, and MySQL availability.')
        sys.exit(1)
