# Open-source US equities platform research

Reviewed on October 8, 2026 using official repositories, license files, and release pages. Suitability assessments are engineering judgments for this project. No source code from these frameworks was copied. Release dates alone should not be treated as maintenance evidence; review the chosen version and recent commits before adoption.

| Project | Architecture and scope | License | Assessment for USQuant |
|---|---|---|---|
| [LEAN](https://github.com/QuantConnect/Lean) | Modular C# event engine with Python strategies; data, algorithm, brokerage, backtest, and live components | Apache-2.0 | Strong reference for modular boundaries; direct adoption adds .NET |
| [Backtrader](https://github.com/mementum/backtrader) | Python Cerebro with feeds, strategies, brokers, and analyzers; event-based backtesting and legacy brokerage integrations | GPL-3.0 | Useful execution semantics; verify maintenance and old broker integrations before adoption |
| [vectorbt](https://github.com/polakowo/vectorbt) | NumPy/pandas/Numba vectorized research and parameter sweeps | [Apache-2.0 + Commons Clause](https://github.com/polakowo/vectorbt/blob/master/LICENSE.md) | Fair-code with commercial restrictions; useful for research, not a complete order lifecycle |
| [NautilusTrader](https://github.com/nautechsystems/nautilus_trader) | Rust core and Python control plane; deterministic event-driven simulation and live adapters | LGPL-3.0; separate [trademark policy](https://github.com/nautechsystems/nautilus_trader/blob/develop/TRADEMARK.md) | Strong reference for shared simulation/live models; runtime, broker coverage, and deployment requirements need evaluation |
| [Qlib](https://github.com/microsoft/qlib) | Data processing, features, ML training, experiments, and portfolio research; Cython extensions | MIT | Candidate for later factor/ML research; not a turnkey US brokerage execution system |
| [Alpaca Python SDK](https://github.com/alpacahq/alpaca-py) | Market data, account, trading requests, and streams; not a backtesting engine | [Apache-2.0](https://github.com/alpacahq/alpaca-py/blob/master/LICENSE) | Reference for US market connectivity; USQuant independently implements REST data and paper-order adapters |

These license descriptions reflect the reviewed upstream material. Recheck the exact pinned versions and transitive dependencies before copying or distributing third-party software. USQuant currently depends on none of the six frameworks above.

## MVP decision

Python handles ingestion, validation, storage, strategy orchestration, risk, and reporting. C++17 provides SMA calculations through a C ABI and ctypes. MySQL is the deployment store; SQLite supports offline use. The first engine processes one symbol of daily raw bars, integer shares, cash funding, and long-only positions. Backtesting and local replay share the same engine.

For a future mature execution engine, evaluate NautilusTrader's broker coverage and operations requirements, or LEAN if .NET is acceptable. A C++ requirement alone does not justify rebuilding a full exchange order system.

## Data and simulation boundaries

The [Alpaca market-data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq) distinguishes IEX and SIP coverage and permissions. IEX volume should not be treated as full-market volume. The adapter specifies feed and raw adjustment, handles pagination, and retains CSV snapshots. IEX historical access has been verified for the configured paper account; SIP entitlements remain unverified.

[Alpaca paper trading](https://docs.alpaca.markets/us/docs/paper-trading) does not reproduce every real execution factor. Local replay is simpler still: it does not model order-book queues, partial fills, broker rejections, borrow availability, corporate actions, taxes, or real-time latency. Demonstration results cannot establish live profitability.

Order interface references: [working with orders](https://docs.alpaca.markets/us/docs/working-with-orders) and [lookup by client order ID](https://docs.alpaca.markets/us/reference/getorderbyclientorderid). The adapters are independent implementations, not copied SDK code.
