-- Run one statement at a time in Sequel Ace's Query tab.
USE usquant;

-- 1. List tables: bars stores prices; runs stores backtest results.
SHOW TABLES;

-- 2. Inspect columns, types, and the composite primary key.
DESCRIBE bars;

-- 3. Count each dataset. Never mix synthetic and real market data.
SELECT symbol, source, adjustment, COUNT(*) AS bar_count,
       MIN(ts) AS first_bar, MAX(ts) AS last_bar
FROM bars
GROUP BY symbol, source, adjustment;

-- 4. Read ten real SPY bars, newest first.
SELECT ts, open, high, low, close, volume
FROM bars
WHERE symbol = 'SPY' AND source = 'alpaca-iex' AND adjustment = 'raw'
ORDER BY ts DESC
LIMIT 10;

-- 5. Restrict the date range; end is exclusive.
SELECT ts, close, volume
FROM bars
WHERE symbol = 'SPY' AND source = 'alpaca-iex' AND adjustment = 'raw'
  AND ts >= '2024-01-01' AND ts < '2024-02-01'
ORDER BY ts;

-- 6. Summarize the real 2024 series.
SELECT COUNT(*) AS days, MIN(low) AS lowest_price,
       MAX(high) AS highest_price, AVG(volume) AS mean_iex_volume
FROM bars
WHERE symbol = 'SPY' AND source = 'alpaca-iex' AND adjustment = 'raw'
  AND ts >= '2024-01-01' AND ts < '2025-01-01';

-- 7. Turn JSON run summaries into readable columns.
-- Run IDs are random UUIDs; ordering by id does not mean ordering by time.
SELECT id,
       JSON_UNQUOTE(JSON_EXTRACT(payload, '$.summary.initial_cash')) AS initial_cash,
       JSON_UNQUOTE(JSON_EXTRACT(payload, '$.summary.final_equity')) AS final_equity,
       JSON_UNQUOTE(JSON_EXTRACT(payload, '$.summary.fill_count')) AS fill_count
FROM runs
LIMIT 10;
