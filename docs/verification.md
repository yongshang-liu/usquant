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
- Alpaca pagination, paper orders, and risk checks passed mocked HTTP tests. No real credentials were configured and no brokerage orders were sent.
- The Docker build passed its unit tests. The container completed Python+C++ → MySQL → backtest → report with the same result as the local Mac.
- GitHub Actions passed C++ compilation, tests with MySQL, and the demonstration on the initial upload. Later runs can be inspected in [Actions](https://github.com/yongshang-liu/usquant/actions).
- The private repository excludes credentials, databases, order journals, and build artifacts.

Reproduce locally with `./scripts/verify_mysql.sh`; see README for container build/run commands.

Cross-platform verification exposed insignificant Mac/Linux libm rounding differences in synthetic prices. Stored price comparisons now allow relative/absolute tolerance of `1e-12`, while rejecting substantive conflicts and preserving existing rows. Regression coverage was added.
