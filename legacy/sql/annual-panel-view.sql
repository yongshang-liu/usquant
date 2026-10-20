-- Readable annual panel. Underlying versions and provenance remain unchanged.
CREATE OR REPLACE VIEW annual_panel_readable AS
SELECT cik,
 JSON_UNQUOTE(JSON_EXTRACT(payload, '$.symbol')) AS symbol,
 CAST(SUBSTRING(period_end,1,4) AS UNSIGNED) AS period_end_year,
 CAST(period_end AS DATE) AS period_end,
 CAST(cutoff AS DATE) AS cutoff,
 CAST(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(payload, '$.metrics.revenues.value')), 'null') AS DECIMAL(38,8)) AS revenues,
 CAST(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(payload, '$.metrics.net_income.value')), 'null') AS DECIMAL(38,8)) AS net_income,
 CAST(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(payload, '$.metrics.operating_income.value')), 'null') AS DECIMAL(38,8)) AS operating_income,
 CAST(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(payload, '$.metrics.assets.value')), 'null') AS DECIMAL(38,8)) AS assets,
 CAST(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(payload, '$.metrics.liabilities.value')), 'null') AS DECIMAL(38,8)) AS liabilities,
 CAST(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(payload, '$.metrics.equity.value')), 'null') AS DECIMAL(38,8)) AS equity,
 CAST(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(payload, '$.metrics.cash.value')), 'null') AS DECIMAL(38,8)) AS cash,
 CAST(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(payload, '$.metrics.operating_cash_flow.value')), 'null') AS DECIMAL(38,8)) AS operating_cash_flow,
 CAST(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(payload, '$.metrics.capital_expenditure.value')), 'null') AS DECIMAL(38,8)) AS capital_expenditure,
 CAST(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(payload, '$.metrics.diluted_eps.value')), 'null') AS DECIMAL(38,8)) AS diluted_eps,
 CAST(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(payload, '$.metrics.diluted_shares.value')), 'null') AS DECIMAL(38,8)) AS diluted_shares,
 JSON_UNQUOTE(JSON_EXTRACT(payload, '$.selection')) AS selection
FROM annual_panel;
