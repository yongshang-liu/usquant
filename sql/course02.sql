-- 第二课：先选数据库，再检查实际行数；全部为只读语句。
USE usquant;
-- 区分证券、来源和复权口径，不把不同 series 混合。
SELECT symbol,source,adjustment,COUNT(*) AS observations,MIN(ts) AS first_time,MAX(ts) AS last_time
FROM bars GROUP BY symbol,source,adjustment ORDER BY symbol,source,adjustment;
-- 提取课堂小样本，半开区间避免一月/二月边界重复。
SELECT ts,open,high,low,close,volume FROM bars
WHERE symbol='NVDA' AND source='alpaca-iex' AND adjustment='raw'
  AND ts >= '2024-01-01' AND ts < '2024-02-01' ORDER BY ts;
-- 财务数据先保留披露版本，不因期末相同就去重。
SELECT symbol,tag,unit,period_start,period_end,value_text,filed,accepted_utc,accession
FROM research_financials
WHERE symbol='NVDA' AND tag='NetIncomeLoss' AND context_status='ordinary'
ORDER BY period_end,filed,accession LIMIT 50;
-- 计数精确披露时间缺失；缺失不能填成财务期末。
SELECT symbol,COUNT(*) AS facts,SUM(accepted_utc IS NULL) AS missing_acceptance
FROM research_financials GROUP BY symbol ORDER BY symbol;
