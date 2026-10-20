# USQuant

A US equities research and paper trading MVP built with Python, C++17, and MySQL. The verified workflow covers data validation, storage, moving-average signals, next-bar execution, risk checks, and persistent JSON/HTML reports. Live trading is disabled.

[Research](docs/research.md) · [Architecture](docs/architecture.md) · [Verification](docs/verification.md) · [GitHub guide](docs/github-guide.md) · [MySQL learning guide](docs/mysql-guide.md) · [SEC fundamentals](docs/fundamentals.md)

## Quick start

Requirements: Python 3.9+ and a C++17 compiler. Run from the repository root:

```sh
python3 scripts/build_cpp.py
python3 -m unittest discover -s tests -v
python3 -m usquant demo --native
python3 -m usquant paper --native
```

Open `reports/latest.html`. Each run also creates `reports/<run_id>.json` and a database `runs` record. Without a configured MySQL service, its integration test is skipped. The offline engine requires no third-party Python packages.

Omit `--native` to use Python indicators. With `--native`, a missing compiled library causes an explicit failure.

## Where the data comes from

The current demonstration uses **260 synthetic daily bars**, generated locally by `usquant/__main__.py`. Closing prices combine a linear trend with a sine wave; opening prices add a small cosine variation. Highs and lows enclose the open/close, and volume is fixed at 1,000,000. The generator skips weekends but does not implement a US exchange holiday calendar. `SPY` is a demonstration label; these are not historical SPY prices.

Synthetic data validates software behavior. Its reported returns are regression fixtures, not evidence of strategy profitability. The `paper` command replays stored historical bars and resets capital on each run; it is not a persistent brokerage simulator.

Real data can enter through a user-provided CSV or the Alpaca historical market-data API. The Alpaca adapter has passed mocked pagination tests and a real read-only check: 252 SPY daily bars for 2024 were downloaded from IEX, stored in MySQL, and backtested with C++ indicators on October 8, 2026.

## CSV ingestion and cleaning

Required columns: `symbol,ts,open,high,low,close,volume`. Optional: `source` (defaults to `csv`) and `adjustment` (defaults to `raw`). Timestamps must include a timezone, for example `2024-01-02T21:00:00+00:00`.

```sh
python3 -m usquant ingest --csv /absolute/path/bars.csv
python3 -m usquant backtest --symbol SPY --source csv --native
python3 -m usquant paper --symbol SPY --source csv --native
```

Cleaning normalizes UTC, sorts records, and merges identical duplicates. Invalid numbers, inconsistent OHLC values, and conflicting duplicates reject the batch. Stored price comparisons allow relative/absolute floating-point tolerance of `1e-12` for cross-platform round trips; other fields are compared exactly, and existing rows are not overwritten. The primary key includes symbol, timestamp, source, and adjustment.

The engine accepts one symbol of completed, raw daily bars per run. Minute bars and incomplete daily bars must not be supplied. Corporate actions are not modeled.

## MySQL setup

MySQL 8.4 is deployed through Docker Compose with a persistent volume and a port bound only to `127.0.0.1`. A local private `.env` already exists on the verified Mac. Do not overwrite it.

On a new machine, copy `.env.example` to `.env` and replace both database passwords with different strong passwords:

```sh
cp .env.example .env
# Edit .env, then export its values:
set -a
. ./.env
set +a
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install '.[mysql]'
python3 scripts/build_cpp.py
docker compose up -d --wait mysql
python3 -m usquant demo --backend mysql --native
USQUANT_TEST_MYSQL=1 python3 -m unittest discover -s tests -v
```

Compose reads `.env` automatically; Python does not. Credentials are not included in reports. `docker compose stop` preserves database data.

## Real historical data: Alpaca

See the [free paper-account setup guide](docs/alpaca-setup.md) for credential configuration and a read-only end-to-end verification script.

Use environment variables for credentials, preferably from a dedicated paper account. IEX is the default feed; SIP access is not assumed. IEX volume is not equivalent to consolidated US market volume.

```sh
export ALPACA_API_KEY='your-key'
export ALPACA_SECRET_KEY='your-secret'
python3 -m usquant fetch --symbol SPY --start 2024-01-01T00:00:00Z --end 2024-04-01T00:00:00Z
python3 -m usquant backtest --symbol SPY --source alpaca-iex --native
```

The adapter requests raw daily bars, handles pagination, preserves a uniquely named CSV snapshot, and ingests validated records. Use a historical end date to avoid incomplete bars. HTTP failures stop the operation. Automatic retry, rate limiting, and streaming ingestion are not implemented. Data is retrieved through the API rather than scraped from web pages.

## Strategy, fills, and risk

Defaults in `config/example.json`: USD 2,500 initial cash, 5/20-day moving averages, integer shares, and long-only positions. A signal calculated at the previous close is executed at the next open. Commission and directional slippage are included.

Entry limits: 20% per-symbol exposure, USD 500 per order, 1% participation based on previously known volume, 8% peak drawdown, and 3% daily loss. A halt stays latched for the replay; existing positions attempt to exit at the next executable open. Zero-volume bars do not fill. Gaps can exceed configured loss thresholds.

Risk-reducing exits bypass entry notional and participation limits. This is a research fill assumption, not a liquidity guarantee. Remaining positions are marked at the final close rather than forcibly liquidated. Results include total return, maximum drawdown, fills, and per-bar equity; Sharpe, benchmark comparison, and out-of-sample evaluation are not implemented.

## Alpaca paper-account execution

The adapter uses only `https://paper-api.alpaca.markets`, rejects redirects, and provides no configurable live endpoint. Preview uses GET requests only; `--submit` sends an order to the paper account:

```sh
python3 -m usquant.paper_broker --symbol SPY --qty 1 --side buy --client-id spy-test-001
python3 -m usquant.paper_broker --symbol SPY --qty 1 --side buy --client-id spy-test-001 --submit
```

Supported scope: regular market hours, integer shares, US equities priced at least USD 1, and DAY limit orders. Entry checks cover cash, order notional, symbol exposure, gross exposure, daily loss, observed peak drawdown, and the kill switch. Selling beyond owned shares is rejected. Any open order blocks new orders. Quotes older than 60 seconds or dated in the future are rejected. The replay volume-participation model does not apply to brokerage execution.

Intent is written to `data/paper.sqlite` before submission. Reusing a client ID queries the broker instead of sending another POST; its parameters cannot change. After a timeout, reconcile using the original ID. An uncertain submission blocks new IDs. If the broker cannot locate the prior order, inspect the paper account manually rather than changing IDs or deleting the journal. The journal stores order state and observed equity peaks, not credentials. `accepted` does not mean `filled`.

This is a one-shot interface. Backtest signals are not yet submitted in an unattended loop. Real paper-account authentication and historical data retrieval have been verified. Order submission remains tested only with mocked HTTP responses; no brokerage order has been sent. Use a dedicated paper account without external concurrent trading. Local locking cannot control other clients, and peak tracking covers only the program's observation period.

## Container workflow

After configuring database passwords:

```sh
docker compose --profile mvp build app
docker compose --profile mvp run --rm app
```

The build compiles C++ and runs unit tests. The application waits for MySQL health, runs the demo, and writes reports to the local `reports/` directory. This full workflow has been verified on the current Mac. Brokerage credentials are not passed into the container by default.

If Docker is not on the terminal path on macOS, use the supplied wrapper:

```sh
./scripts/docker.sh compose up -d --wait mysql
./scripts/verify_mysql.sh
./scripts/docker.sh compose --profile mvp run --rm app
```

The verification script loads local `.env` without printing passwords. Rebuild the app image after changing source code.

## Live trading and remaining work

`python3 -m usquant live` fails explicitly, and `LiveBroker` refuses construction. Configuration and environment variables cannot enable live execution. Implementing it requires separate explicit user approval and review.

Remaining work includes exchange calendars, corporate actions, survivorship bias, continuous strategy scheduling, restart recovery, complete order-state handling, partial fills, ongoing reconciliation, alerts, rate limits, settlement rules, and account restrictions. The example strategy has not been shown to be profitable.

Repository: [yongshang-liu/usquant](https://github.com/yongshang-liu/usquant). Secrets, databases, order journals, and local build artifacts are excluded from Git.

For the multi-company issuer registry, resumable imports, annual pilot panel, and coverage limitations, see [Financial database](docs/financial-database.md). Read-only teaching queries are in [sql/financial-database.sql](sql/financial-database.sql).

For the raw quarterly archive and industry/year classification layers, see [Raw SEC archive](docs/raw-sec-archive.md). This is independent of the experimental research panel.

Financial data currently uses an archive-only workflow: official ZIP files organized by year and quarter, with checksums. Experimental companyfacts data and financial MySQL tables have been removed locally. See [Raw archive](docs/raw-sec-archive.md).

For the explicitly requested eight-company AI/fintech dataset in MySQL, see [Research sample](docs/research-sample.md) and [read-only queries](sql/research-sample.sql). The quarterly raw archive workflow remains separate.
