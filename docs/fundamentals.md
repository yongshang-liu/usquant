# SEC financial statement data

USQuant now imports free, publicly available SEC Company Facts for US companies. No paid subscription or API key is required. The contact email required for automated access is configured locally and sent only to SEC in the User-Agent header.

## Run

In local `.env`, configure `SEC_USER_AGENT="USQuant your-email@example.com"`. Do not commit your actual contact details.

```sh
.venv/bin/python -m usquant.fundamentals fetch --backend mysql --symbols AAPL MSFT NVDA
.venv/bin/python -m usquant.fundamentals show --backend mysql --symbols AAPL --as-of 2024-01-01
```

The fetcher retrieves the official ticker/CIK mapping, downloads one companyfacts document per company, saves raw JSON and retrieval-time/hash metadata under `data/sec/`, and ingests selected standard US-GAAP facts into `financial_facts`. Repeated identical facts are idempotent; versions are retained. The client makes at most one request per second. Run one importer at a time because this limit is per process; SEC's total user traffic limit applies across machines. HTTP errors stop the operation without automatic retries or evasion.

## Coverage

| Metric | Meaning |
|---|---|
| revenues | Revenue, with the original alternative XBRL tag retained |
| net_income | Net income/loss |
| operating_income | Operating income/loss |
| assets / liabilities / equity | Balance-sheet totals |
| cash | Cash and cash equivalents |
| operating_cash_flow | Net cash from operating activities |
| capital_expenditure | Payments to acquire property, plant, and equipment |
| diluted_eps / diluted_shares | Diluted earnings per share and weighted-average diluted shares |

Values are stored as decimal text to preserve numeric precision and units. Negative earnings or cash flows are valid. Missing facts stay missing; they are not replaced with zero. The current selection accepts 10-K, 10-Q, and amendments with USD, USD/shares, or shares units. It is a selected fact dataset, not a complete reconstruction of the three statements. Company-specific tags and IFRS are not yet supported.

## Learning in Sequel Ace

Refresh the table list and select **financial_facts**. See [fundamentals.sql](../sql/fundamentals.sql) for verified read-only exercises.

- `period_start` / `period_end`: the accounting period; a balance-sheet fact has an empty start.
- `filed`: filing date, which is later than the accounting period.
- `accession`: SEC filing identifier; it preserves separate submissions and amendments.
- `tag` / `unit`: original concept and unit, retained for audit and comparability.
- `value_text`: the reported number. For numeric SQL calculations, cast to a suitable DECIMAL type rather than sorting it as text.
- `payload`: normalized provenance, including SEC fiscal-year/period labels and optional frame.

A fact count is not a report count. One filing contains many facts and may repeat prior-year comparisons. Fiscal labels refer to the filing and must not be used alone to assign the period of a comparative fact. A 10-Q cash-flow figure can be cumulative year-to-date rather than a standalone quarter. Revenue/equity aliases remain separate; do not add them together. TTM values, financial ratios, and quarter derivation require an additional normalization layer.

## Historical availability

`show --as-of YYYY-MM-DD` uses only facts filed **before** that date, then selects the latest filing version per CIK/tag/unit/start/end. Same-filing conflicting values are rejected. This excludes the cutoff day's filings because the API facts provide a filing date, not an intraday acceptance timestamp.

This is a conservative daily filter, not a guaranteed historical point-in-time database. Today's Company Facts document can contain revised/deleted or retrospectively adjusted facts. Raw snapshots and multiple imported versions improve auditability but do not recreate past source availability. Production historical research requires original filing snapshots/acceptance timestamps and reviewed context normalization. Financial facts have not yet been wired into the trading strategy.

## Verification on October 10, 2026

The real SEC API returned 2,398 AAPL, 2,539 MSFT, and 2,289 NVDA selected fact versions, totaling 7,226 rows stored in MySQL. These counts include historical comparisons, multiple duration contexts, and filing versions. Snapshot files remain local and excluded from Git.

Sources: [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [SEC developer fair-access guidance](https://www.sec.gov/about/developer-resources).
