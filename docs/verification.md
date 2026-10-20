# Local LEAN verification — 20 October 2026

Both backtests ran with the actual official ARM64 Docker image, network disabled, no brokerage credentials, and read-only upstream sample data/source mounts. Host is Apple silicon. Container reports LEAN v2.5.0.0 and Python 3.11.9.

| Run | Algorithm | Dates | Orders | Ending equity |
|---|---|---|---|---|
| `20261020-115749-467045-official` | Unmodified upstream BasicTemplateAlgorithm | 7–11 October 2013 | 1 | USD 101,691.92 (initial USD 100,000) |
| `20261020-115820-103816-first` | FirstBacktest learning exercise | 7–11 October 2013 | 1 | USD 2,506.39 (initial USD 2,500) |

The exercise logged a signal at 7 October 2013 09:31 New York time, Submitted and Filled events for 3 SPY shares, a USD 1 modelled fee, and final portfolio value. The result JSON contained statistics and orders; the launcher returned success only after inspecting output artifacts. All 11 data requests succeeded in both completed runs. These are five-day engine/learning checks, not evidence of investment performance; annualized statistics from this tiny sample are not meaningful.

Each result directory contains `config.json`, `provenance.json`, `console.log`, algorithm log, result JSON, summary JSON and order events as emitted by LEAN. Runtime artifacts are local, excluded from GitHub. Source and prebuilt image references are pinned independently; the engine was not compiled locally from the checked-out source. Full upstream unit/regression suites were not run. AMD64 is configured but not locally tested on this ARM machine.

The first exercise initially failed on an enum spelling; it was corrected to `QUANT_CONNECT_BROKERAGE` and rerun successfully. Failed-run logs remain locally for traceability. Static syntax and offline-configuration checks also passed. No broker paper or real orders were sent, and no scheduled process was installed.
