# Verification record

Verified on October 8, 2026 (Asia/Seoul), on macOS ARM64 with Python 3.9.6.

- C++17 indicators compile and match Python SMA across multiple windows, including warm-up NaNs.
- Docker Desktop is installed; Docker Engine 29.8.2 and Compose v5.5.1 were checked.
- MySQL 8.4 is healthy and bound only to `127.0.0.1:3306`. Local passwords are excluded from Git.
- The project virtual environment and PyMySQL RSA authentication dependencies are installed. Real integration exposed a missing cryptography dependency, which was fixed.
- All 21 tests passed without skips, including real MySQL read/write, duplicate ingestion, and rollback checks.
- The MySQL demonstration processed 260 synthetic daily bars and 10 fills, producing final equity of USD 2601.726883 from USD 2500. This is a regression fixture, not investment performance.
- SQLite replay and report generation passed.
- The live CLI and LiveBroker reject execution.
- Alpaca pagination, paper orders, and risk checks passed mocked HTTP tests. Subsequently, real paper-account authentication and historical data retrieval were verified using locally configured credentials. No brokerage orders were sent.
- The Docker build passed its unit tests. The container completed Python+C++ → MySQL → backtest → report with the same result as the local Mac.
- GitHub Actions passed C++ compilation, tests with MySQL, and the demonstration on the initial upload. Later runs can be inspected in [Actions](https://github.com/yongshang-liu/usquant/actions).
- The private repository excludes credentials, databases, order journals, and build artifacts.

Reproduce locally with `./scripts/verify_mysql.sh`; see README for container build/run commands.

Cross-platform verification exposed insignificant Mac/Linux libm rounding differences in synthetic prices. Stored price comparisons now allow relative/absolute tolerance of `1e-12`, while rejecting substantive conflicts and preserving existing rows. Regression coverage was added.

## Real-data verification

On October 8, 2026, the read-only verifier connected successfully to the paper endpoint and retrieved 252 SPY raw daily bars for calendar year 2024 from IEX. A local CSV snapshot was retained, records were validated and ingested into MySQL, and the C++-enabled backtest completed.

The example strategy produced 2 simulated fills, USD 2529.6105025 final equity from USD 2500, 1.18442% total return, and 0.39531% maximum drawdown. These describe this one historical IEX sample and the implemented fill assumptions, not a validated profitable strategy. No brokerage order was submitted. Raw prices do not account for dividends, and IEX is not consolidated US market data. The dataset and run records stay local and are excluded from Git.
