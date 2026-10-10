-- Read-only learning queries. Use the usquant database.
SELECT COUNT(*) AS discovered_issuers FROM sec_issuers;
SELECT status, COUNT(*) AS attempts FROM sec_import_attempts GROUP BY status;
SELECT cik, symbol, name, listings FROM sec_issuers ORDER BY cik LIMIT 30;
SELECT cik, metric, MIN(period_end) AS first_period_end,
       MAX(period_end) AS last_period_end, COUNT(*) AS fact_versions
FROM financial_facts WHERE period_end >= '2010-01-01'
GROUP BY cik, metric ORDER BY cik, metric LIMIT 50;
-- Each row is one company-period at one cutoff, not one financial statement.
SELECT cik, period_end, cutoff,
       JSON_UNQUOTE(JSON_EXTRACT(payload, '$.symbol')) AS symbol,
       JSON_UNQUOTE(JSON_EXTRACT(payload, '$.metrics.net_income.value')) AS net_income,
       JSON_UNQUOTE(JSON_EXTRACT(payload, '$.metrics.net_income.status')) AS income_status,
       JSON_UNQUOTE(JSON_EXTRACT(payload, '$.metrics.assets.value')) AS assets
FROM annual_panel ORDER BY cik, period_end LIMIT 50;
-- Observe availability and metric coverage before selecting a research sample.
SELECT SUBSTRING(period_end,1,4) AS period_end_year, COUNT(DISTINCT cik) AS issuers
FROM annual_panel GROUP BY SUBSTRING(period_end,1,4) ORDER BY period_end_year;
