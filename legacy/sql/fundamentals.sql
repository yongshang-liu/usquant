-- Refresh the table list in Sequel Ace, then select financial_facts.
-- Each row is one disclosed fact/version, NOT one complete financial report.
SELECT symbol, COUNT(*) AS fact_versions, MIN(filed) AS earliest_filing,
       MAX(filed) AS latest_filing
FROM financial_facts
GROUP BY symbol;

-- Balance-sheet assets, as disclosed in filings before the chosen date.
-- Multiple rows may be comparative values or restatements; do not sum them.
SELECT symbol, period_end, filed, value_text, unit, form, accession
FROM financial_facts
WHERE symbol = 'AAPL' AND tag = 'Assets' AND unit = 'USD'
  AND filed < '2026-10-10'
ORDER BY period_end DESC, filed DESC, accession DESC
LIMIT 20;

-- Income statement and cash flow retain start/end duration contexts.
-- A 10-Q may include both a quarter and year-to-date amounts.
SELECT metric, tag, period_start, period_end, filed, value_text, unit
FROM financial_facts
WHERE symbol = 'MSFT'
  AND metric IN ('revenues', 'net_income', 'operating_cash_flow')
  AND period_end >= '2024-01-01' AND filed < '2026-10-10'
ORDER BY period_end DESC, filed DESC
LIMIT 50;
