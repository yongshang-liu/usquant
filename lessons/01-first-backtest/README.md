# Lesson 01 — observe a complete LEAN backtest

Run from the repository root:

```sh
python3 scripts/run_lean.py official
python3 scripts/run_lean.py first
```

The first run executes the unchanged upstream BasicTemplateAlgorithm. The second executes `main.py` in this folder. Both use bundled sample SPY minute data. Neither has a network connection or credentials.

## Follow the event sequence

1. `initialize` declares the time range, cash, brokerage model and equity subscription.
2. LEAN's file data feed advances its algorithm clock and delivers a Slice to `on_data`.
3. The first valid SPY bar generates a 20% target. `set_holdings` asks LEAN to determine the required order quantity.
4. Order events reveal status changes and the modelled fill; a target is not itself a filled trade.
5. LEAN updates cash, positions, portfolio value and statistics.
6. `on_end_of_algorithm` records the terminal value. An open final position is not a forced sale.

## Inspect your output

Open the printed `results/YYYYMMDD-HHMMSS-first/` directory. Start with `console.log`, searching for `SIGNAL`, `ORDER`, and `END`. Then find the algorithm result JSON: inspect orders, fills, portfolio equity, fees and statistics. Use the neighboring `provenance.json` to identify the actual image and source checkout. Do not edit the runtime config and assume it affects future runs; the launcher regenerates it.

## Do these exercises yourself

- Before running, estimate how many whole SPY shares USD 500 can buy during the sample.
- Explain why the actual invested fraction can differ from exactly 20%.
- Change the holdings target to 10%; run again and compare order quantities and fees.
- Log `self.portfolio.cash` before and after order events.
- Remove the `_submitted` guard in a copy, run it, and inspect repeated target requests.
- Identify the engine class that determines whether the order is affordable.

Do not extend the date range yet: the bundled sample does not contain a complete historical market database. Do not interpret a five-day sample result as evidence of a profitable strategy.
