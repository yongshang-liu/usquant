# LEAN learning path

The objective is to understand and recreate each system layer using LEAN's contracts, while retaining upstream attribution. Work through one verified exercise at a time; do not start by modifying thousands of engine files.

## 1. Run and observe the official algorithm

Run `python3 scripts/run_lean.py official`. Source: `vendor/lean/Algorithm.Python/BasicTemplateAlgorithm.py`. Sample: SPY minute bars for 7–11 October 2013, bundled by upstream for testing, not a modern research dataset. Follow initialization, security subscription, OnData, holdings request and fills. Read the run's `console.log`, result JSON and order-events JSON. This is an engine smoke test, not a performance claim.

## 2. Write the smallest strategy yourself

Read `lessons/01-first-backtest/main.py`, then run `python3 scripts/run_lean.py first`. USD 2,500 initial cash and one 20% SPY holdings target make the control flow easy to follow. Compare the signal time to order-event timestamps. An order request and a filled position are different states.

Exercises: change initial cash; change the target to 10%; log the current cash; explain why the `_submitted` flag is set before requesting holdings; compare whole-share sizing to the holdings percentage. Keep dates within the bundled sample. A market order's fill rules are LEAN's rules, not the previous engine's assumptions.

## 3. Trace the engine source

Read these directories in order:

- `Algorithm/`: QCAlgorithm lifecycle, subscriptions, orders and portfolio API.
- `Common/`: securities, market data, symbol identifiers, orders and portfolio contracts.
- `Engine/DataFeeds/`: subscriptions, trading calendars, time synchronization and data delivery.
- `Engine/TransactionHandlers/`: order processing and brokerage interaction.
- `Common/Securities/`: fill, fee, buying power and portfolio models.
- `Engine/Results/`: logs, charts and result artifacts.
- `Algorithm.Framework/`: Universe → Alpha → Portfolio Construction → Risk Management → Execution.
- `Brokerages/`: available interfaces; external brokerage implementations may live in separate upstream repositories.

Use official regression examples and tests to learn expected behavior. Do not confuse a modelled backtest fill with a broker-confirmed fill.

## 4. Data and MySQL adapters (next)

Build a versioned exporter or custom data reader. First identify the security, exchange timezone, session convention, raw/adjusted prices, mapping and factor files, missing sessions and corporate actions. Preserve original source metadata. Test a tiny exported interval against known source records before importing years of data.

Existing IEX data is single-exchange data. Existing SEC facts are standard entity-wide concepts, not a licensed LEAN fundamental dataset. Financial data must become available at a verified disclosure timestamp, never automatically at period-end. Ticker predecessor/SPAC history needs a deliberate identity mapping. These adapters are not implemented by the first two lessons.

## 5. Indicators and factors

Implement one LEAN indicator example; inspect warm-up and History behavior. Add a fixed-parameter momentum example. Then build a separate financial factor with explicit disclosure availability. Save configuration and data versions; avoid selecting parameters on the final evaluation period.

## 6. Portfolio, risk and evaluation

Use LEAN framework models to separate signal generation, targets, constraints and execution. Add fees, slippage, liquidity constraints and risk stops explicitly. Compare to a suitable benchmark; examine trade logs and inactive periods rather than headline returns alone.

## 7. Broker-paper execution

Only after offline validation, configure a dedicated **paper** brokerage adapter and data feed. Reconcile positions, open orders, restart state, timestamps, duplicate submissions and disconnects. The current launcher cannot enter this mode. No real brokerage permission is inferred from learning or simulation requests.

## 8. Maintenance

Update the upstream submodule deliberately. Record the source revision, image revision, data provenance and regression results. Pin external dependencies; review licenses before copying code. Preserve secrets locally and keep a separate database backup.

## Official references

- https://github.com/QuantConnect/Lean
- https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/algorithm-engine
- https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/overview

## Important: editing the engine vs editing an algorithm

The current Docker launcher runs official prebuilt binaries. Editing `lessons/` changes your Python strategy on the next run. Editing C# files under `vendor/lean/` does **not** rebuild that Docker image. When you reach engine development, follow the pinned upstream `readme.md` and `.vscode/readme.md` for a source build (the checked-out version requires .NET 10). Keep an independently built image identifiable; do not claim it is the same as the official pinned binary. A complete source build and the full upstream regression suite are separate tasks, not implied by passing our example backtests.
