-- ---------------------------------------------------------------------------
-- 08_stockout.sql — the OPERATIONAL evidence behind the biggest cell
-- ---------------------------------------------------------------------------
-- Revenue data can tell you a category vanished from one store's baskets. Only
-- the availability table can tell you WHY. This is what turns a hypothesis into
-- an evidential "why" (Ch. 23).
-- ---------------------------------------------------------------------------

-- name: stockout_by_branch_sku
SELECT s.branch_id,
       b.branch_name,
       s.product_id,
       s.product_name,
       COUNT(*)                                                          AS observed_days,
       SUM(CASE WHEN s.in_stock = 0 THEN 1 ELSE 0 END)                   AS days_out_of_stock,
       ROUND(100.0 * SUM(s.in_stock) / COUNT(*), 1)                      AS availability_pct,
       MAX(s.consecutive_days_out)                                       AS longest_outage_days
FROM fact_stockouts s
JOIN dim_branch b ON b.branch_id = s.branch_id
WHERE s.period_key = '2026Q3'
GROUP BY s.branch_id, b.branch_name, s.product_id, s.product_name
HAVING days_out_of_stock > 0
ORDER BY days_out_of_stock DESC, availability_pct ASC
LIMIT 25;

-- name: stockout_daily_incident
-- The incident, day by day, for the two hero SKUs at the affected store.
SELECT s.date,
       s.product_id,
       s.product_name,
       s.in_stock,
       s.consecutive_days_out,
       s.incident_flag
FROM fact_stockouts s
WHERE s.branch_id = 'BR05'
  AND s.period_key = '2026Q3'
  AND s.product_id IN ('PC01', 'PC02')
ORDER BY s.date, s.product_id;

-- name: stockout_daily_revenue
-- Daily Personal Care revenue at the affected store, both periods, so the two
-- years can be plotted on the same day-of-quarter axis.
SELECT d.date,
       f.period_key,
       ROUND(SUM(f.net_revenue), 2) AS net_revenue,
       SUM(f.quantity)              AS units
FROM fact_sales_lines f
JOIN dim_date    d ON d.date_key   = f.date_key
JOIN dim_product p ON p.product_id = f.product_id
WHERE f.branch_id = 'BR05'
  AND p.category = 'Personal Care'
GROUP BY d.date, f.period_key
ORDER BY f.period_key, d.date;

-- name: stockout_incident_vs_rest
-- Is the anomaly confined to the incident window and store, or is it chain-wide?
SELECT CASE WHEN s.branch_id = 'BR05' THEN 'BR05 Mombasa Nyali' ELSE 'Other five stores' END AS scope,
       CASE WHEN s.incident_flag = 1 THEN 'Inside incident window' ELSE 'Rest of quarter' END AS window_flag,
       COUNT(*)                                       AS observations,
       SUM(CASE WHEN s.in_stock = 0 THEN 1 ELSE 0 END) AS days_out_of_stock,
       ROUND(100.0 * SUM(s.in_stock) / COUNT(*), 1)    AS availability_pct
FROM fact_stockouts s
WHERE s.period_key = '2026Q3'
  AND s.product_id IN ('PC01', 'PC02')
GROUP BY scope, window_flag
ORDER BY scope, window_flag;

-- name: stockout_revenue_impact
-- The affected store's Personal Care sales in the SAME calendar window
-- (10 Aug - 20 Sep) in both years — like-for-like, so the incident is isolated
-- from ordinary seasonality.
SELECT f.period_key,
       ROUND(SUM(f.net_revenue), 0)   AS net_revenue,
       SUM(f.quantity)                AS units,
       COUNT(DISTINCT f.invoice_id)   AS orders
FROM fact_sales_lines f
JOIN dim_date d    ON d.date_key  = f.date_key
JOIN dim_product p ON p.product_id = f.product_id
WHERE f.branch_id = 'BR05'
  AND p.category = 'Personal Care'
  AND ((f.period_key = '2025Q3' AND d.date BETWEEN '2025-08-10' AND '2025-09-20')
    OR (f.period_key = '2026Q3' AND d.date BETWEEN '2026-08-10' AND '2026-09-20'))
GROUP BY f.period_key
ORDER BY f.period_key;
