# AI and fintech MySQL research sample

The selected starting sample is NVDA, AMD, MSFT, PLTR, PYPL, V, SOFI and COIN. These are research examples, not a representative market universe or investment recommendations. The earlier archive-only workflow remains available; the user has now explicitly requested a separate MySQL dataset for this sample.

## Sequel Ace entry points

- `research_companies`: ticker, reporting-entity CIK, company name, SIC and research grouping. Grouping is an analyst label, not an official industry classification. One selected security per issuer is assumed; this is not a historical security master.
- `research_market_daily`: daily OHLCV for the selected companies. Feed and adjustment are explicit.
- `research_financials`: **one original concept observation per row**, with independent columns for taxonomy, tag, label, unit, period start/end, filed date, accession, form, precise source value, reporting FY/FP, and available acceptance timestamp. `context_status=review_dates` flags unusual date contexts such as future obligations; retain these but review before treating them as historical performance. No eleven-metric restriction; all standard concepts returned by SEC companyfacts are included from period ends in 2010 onward. Custom concepts, dimensional disclosures and full footnotes are not covered by this API.
- `research_filings`: annual/quarterly report identities, reporting periods and available UTC acceptance times, including historical submission pages.
- `research_sources`: snapshot hashes and local file locations; files include retrieval sidecars. Source observations are content-deduplicated, with original snapshots retained for audit. A stored observation retains its first source reference, rather than every later snapshot association.
- `research_coverage`: counts and observed date boundaries; absence of data is not filled with zeros.

`value_text` intentionally retains exact decimal text. Do not aggregate different tags, units, periods or filing versions. NULL period_start denotes an instant context. Reporting FY belongs to the source filing and is not automatically the fiscal year of the comparative observation. Same-period restatements remain separate rows.

## Acquisition and updates

```sh
.venv/bin/python -m usquant.research_data
# A bounded company update:
.venv/bin/python -m usquant.research_data --symbols NVDA --skip-market
```

SEC requests use the already configured local SEC_USER_AGENT and one request per second. Market requests use local Alpaca credentials and only historical market-data GET endpoints. No brokerage order endpoint is called. Secrets and data snapshots are excluded from GitHub. Source snapshots are stored under `data/research_sources/YYYY-MM-DD/`, separate from quarterly ZIP archives. Keep separate backups of data and the MySQL volume.

Market collection requests 2016 onward through the most recent completed UTC date; actual coverage depends on exchange feed availability and listing history. Default is free **IEX**, a single-exchange feed, not consolidated market prices/volume. OHLCV is unadjusted: stock splits/dividends can produce apparent price jumps. Corporate actions and a verified adjusted series are required before calculating meaningful long-horizon investment returns. Financial observations can predate the security's listing; pre-listing stock prices are not fabricated.

## Joining disclosures and prices

A report period end is not a disclosure time. `accepted_utc` is joined by CIK + accession. When acceptance is missing, use a conservative later-date rule and flag it, rather than assuming period-end availability. Acceptance alone does not guarantee every value currently returned by companyfacts was historically available in exactly this form. The current-source API is not a strict point-in-time archive. Do not claim a leakage-free backtest without checking original report versions and market session timing.

The pipeline commits finance per company. If a later company/market call fails, completed companies remain available; rerun explicitly. A conflicting pre-existing OHLCV row fails rather than silently overwriting provider revisions. No scheduled updates are installed.

Sources: [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [Alpaca historical data sources](https://docs.alpaca.markets/us/docs/historical-stock-data-1).

## Verified initial load (20 October 2026)

Eight companies, 150,507 financial observations (not unique accounting periods), and 12,207 IEX daily bars through 19 October 2026 were stored. A repeated NVDA fact import added zero rows, and the disclosure join preserved the fact row count. The four read-only teaching queries executed successfully in MySQL. Unit suite: 33 tests run, two pre-existing optional MySQL tests skipped; the new database workflow was separately verified against the live local MySQL service.

2,554 observations have no matched exact acceptance timestamp, and 15 have `review_dates` contexts. No timestamps or values were fabricated. Coverage is concept-dependent and should be checked before analysis. The earliest returned market bar is 27 July 2020 for the established companies, 30 September 2020 for PLTR, 30 November 2020 for SOFI and 14 April 2021 for COIN. Provider ticker histories can include predecessor/SPAC securities; SOFI's early history requires explicit security identity review before pairing it with SoFi operating-company financials. The coverage report is local at `reports/research-coverage.json`.
