# First momentum paper-research pipeline

This is an adjusted-price research simulator with read-only Alpaca paper-account checks. It never submits orders. The live broker remains disabled. The eight-company set was selected retrospectively and is not representative of the US market.

## Rules frozen for the first run

See `config/momentum-paper.json`: USD 2,500 initial cash; positive 126-session momentum excluding the latest 21 sessions; top three names; inverse 20-session return volatility weights, each capped at 20% and aggregate at 60%. Capped excess stays in cash. Compute at the close of the first observed common session each month; rebalance at the next observed common session's open. Model one-way costs at 15 basis points of traded notional (5 commission plus 10 slippage as a combined assumption, not broker-measured costs). Allow fractional adjusted research units; these are not tradable historical share quantities. Position weights can drift between rebalances.

An 8% peak drawdown or 3% daily loss permanently stops new exposure and schedules liquidation at the next observed open. Intraday/gap losses can exceed thresholds. If a halt occurs at the final close, liquidation remains pending. These thresholds apply to this historical simulated account, not the actual paper account.

## Data and limits

Fetch Alpaca IEX `adjustment=all`, preserving existing raw bars. The provider adjusts splits, dividends and spin-offs. Retrospectively adjusted prices are useful for exploratory return accounting but are not a raw-price corporate-action ledger, true point-in-time factor dataset or a realistic order-fill model. No corporate actions are booked as actual shares or cash. Do not send these adjusted prices/quantities to a broker.

Calendar = intersection of the eight observed daily series, not a verified exchange calendar. Missing sessions are excluded rather than filled. SOFI/predecessor history and the hand-picked universe need review. Momentum uses each symbol's own available bar history, with at least 127 observations; stale signals are rejected after four calendar days. The full financial dataset is deliberately not yet used by this price-factor experiment. Disclosure timing and financial-factor definitions require a separate evaluation.

Time labels: development 2021–2023, validation 2024, retrospective test 2025 onward. This is one continuous account and one rule set, without automatic resets or optimization. There is no untouched holdout. Once halted, later periods are inactive and cannot measure out-of-sample signal quality.

## Reproduce

```sh
# Fetch current adjusted snapshots, append to MySQL, run research, inspect paper account.
.venv/bin/python -m usquant.momentum_paper --refresh-data
# Re-run existing local MySQL observations, without fetching market history.
.venv/bin/python -m usquant.momentum_paper
```

Conflicting stored provider revisions fail rather than silently replace records. JSON contains configuration, data hash, fills, curve, calendar gaps, latest theoretical signals, and read-only paper-account status. Latest signals always have `executable=false`; they are not order proposals. The code does not implement an unattended broker strategy loop. No recurring task has been installed.

Reports: local `reports/momentum-paper.html` and UUID JSON files; MySQL `runs` stores the full result. These outputs are excluded from GitHub. New runs need LONGTEXT capacity, so existing MySQL `runs.payload` is expanded in place without deleting results.

## Initial verified result, 20 October 2026

Run `8edfbba6439e480e9ad9813d0faff01f`, 1 July 2021 to 19 October 2026: final simulated equity USD 2,716.64, return 8.67%, maximum drawdown 8.04%, 25 simulated fills. Drawdown halt began 3 December 2021; later validation/test periods were cash and returned zero. This does not validate profitability. Do not loosen the stop merely to improve the chart. Paper account ACTIVE; market closed; zero orders submitted.

Tests cover prefix invariance (future bars do not change earlier orders), close-to-next-open timing, cash and weight limits, risk halt and rejection of raw prices/live mode. Full unit suite: 37 run, two optional legacy MySQL tests skipped. The actual research pipeline and persisted MySQL result were also exercised.

[Alpaca bar adjustment reference](https://docs.alpaca.markets/us/reference/stockbars).
