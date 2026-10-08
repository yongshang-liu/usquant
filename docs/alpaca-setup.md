# Free Alpaca paper setup

1. Sign in at https://app.alpaca.markets/account/login or create an account yourself.
2. Select **Paper Trading**. The current workflow requires no funded live account or paid market-data subscription.
3. In the API section, generate **paper-account** keys yourself. Generating new keys may invalidate existing ones; preserve keys used by other applications.
4. Enter the key and secret in the local `.env` entries `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`. Do not alter database passwords. Never paste secrets into chat, documentation, screenshots, or GitHub.
5. Run the read-only verification from the project root:

```sh
./scripts/docker.sh compose up -d --wait mysql
.venv/bin/python scripts/verify_alpaca.py
```

The verifier reads the paper-account status, downloads completed 2024 SPY daily bars from IEX, saves a CSV snapshot, validates and stores them in MySQL, and runs the C++-enabled backtest. It submits **no orders** and does not print credentials or the account object. The resulting HTML replaces the latest report; a separate JSON and database record retain the run.

The first attempt remains pending until credentials are supplied. Receiving data successfully does not establish strategy profitability. IEX covers one exchange rather than the consolidated US market. Broker order testing is a separate step.

Reference: [Alpaca's official paper-trading setup](https://alpaca.markets/learn/start-paper-trading).
