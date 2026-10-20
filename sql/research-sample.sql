-- Start here: sample coverage, not a count of independent observations.
SELECT * FROM research_coverage ORDER BY symbol;
SELECT symbol,ts,open,high,low,close,volume,source,adjustment
FROM research_market_daily WHERE symbol='NVDA' ORDER BY ts DESC LIMIT 20;
-- Original SEC concepts, explicit units, dates and filing versions.
SELECT symbol,taxonomy,tag,label,unit,period_start,period_end,
       value_text,filed,accepted_utc,form,accession
FROM research_financials WHERE symbol='NVDA' AND tag='NetIncomeLoss' AND context_status='ordinary'
ORDER BY period_end DESC,filed DESC LIMIT 30;
-- Count records with available disclosure timestamp; no silent date imputation.
SELECT symbol,COUNT(*) AS observations,
       SUM(accepted_utc IS NULL) AS missing_acceptance_timestamp
FROM research_financials GROUP BY symbol ORDER BY symbol;
