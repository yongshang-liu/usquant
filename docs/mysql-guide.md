# Learning MySQL with USQuant

MySQL is the database server running in Docker. Sequel Ace is a macOS application that lets you connect to it, browse rows, inspect table definitions, and execute SQL. Python collects and validates data; MySQL persists it; SQL retrieves and summarizes it.

## Connect with Sequel Ace

Use a **Standard / TCP/IP** connection:

| Field | Value |
|---|---|
| Name | USQuant Local |
| Host | 127.0.0.1 |
| Username | usquant |
| Password | MYSQL_PASSWORD from local .env |
| Database | usquant |
| Port | 3306 |

Do not use a socket connection: the server is inside Docker. Start the server from the project root if necessary:

```sh
./scripts/docker.sh compose up -d --wait mysql
```

Keep passwords out of screenshots and Git. The first connection need not save the password; enter it again next time unless you choose to save it in macOS Keychain.

## Understand the existing tables

- `bars`: one daily price record per symbol, timestamp, source, and adjustment. `open`, `high`, `low`, and `close` are prices; `volume` is feed-specific trading volume. `ts` is a normalized UTC timestamp stored as text.
- `financial_facts`: selected SEC financial facts with accounting periods, filing dates, units, and preserved filing versions. See [the financial-data guide](fundamentals.md).
- `runs`: one backtest result per random run ID. `payload` is JSON stored in a TEXT column and contains summary, fills, and equity records. There is no created-at column, so the table cannot reliably identify the latest run by sorting IDs.
- A **row** is one record; a **column** is one attribute. The `bars` primary key is a combination of four columns, which prevents duplicate identities while allowing different sources to coexist.
- Synthetic bars and `alpaca-iex` bars are different datasets. Filter by source before comparing prices or calculating statistics.

## First session: approximately 20 minutes

1. Connect and select the `usquant` database.
2. Click `bars`, then **Structure** to inspect columns and the primary key.
3. Open **Content** to browse rows. Filter `source` to `alpaca-iex` to see actual market data.
4. Open **Query**. Paste one statement at a time from [learning.sql](../sql/learning.sql), then run the selected/current statement using the application's Run control.
5. Begin with `SHOW TABLES` and `DESCRIBE bars`. Next practice `SELECT`, `WHERE`, `ORDER BY`, and `LIMIT`. Finish with `COUNT`, `GROUP BY`, and JSON summary extraction.

The supplied exercises only read existing data. Table cells in the Content view may be editable; use Query for the first session. Practice INSERT/UPDATE/DELETE later with a separate practice table rather than changing collected market data.

## Questions to answer

- How many real SPY bars were stored for 2024? The verified initial import contained 252.
- What dates does each source cover?
- What are the most recent ten closing prices in the imported dataset?
- How many backtest runs exist, and what final equity does each summary report?

The tutorial reports what is stored, not what the market will do. IEX volume is not consolidated US market volume.

Documentation: [Sequel Ace connection types](https://sequel-ace.com/get-started/connection-types.html).
