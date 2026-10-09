-- ---------------------------------------------------------------------------
-- 03_quality_checks.sql — verify the loaded warehouse, don't assume it
-- ---------------------------------------------------------------------------
-- These run AFTER cleaning. Every "should be 0" query returning 0 is the point:
-- the pipeline proves its own inputs are sound before anyone trusts a number.
-- ---------------------------------------------------------------------------

-- name: qc_rows_by_period
SELECT period_key,
       COUNT(*)                     AS line_items,
       COUNT(DISTINCT invoice_id)   AS invoices,
       COUNT(DISTINCT customer_id)  AS customer_ids,
       COUNT(DISTINCT product_id)   AS skus,
       COUNT(DISTINCT date_key)     AS days_traded,
       ROUND(SUM(net_revenue), 2)   AS net_revenue,
       ROUND(SUM(gross_profit), 2)  AS gross_profit
FROM fact_sales_lines
GROUP BY period_key
ORDER BY period_key;

-- name: qc_grain_violations
-- GRAIN TEST: (invoice_id, line_id) must be unique. Expect 0 rows.
SELECT 'duplicate (invoice_id, line_id)' AS check_name, COUNT(*) AS failures
FROM (SELECT invoice_id, line_id FROM fact_sales_lines
      GROUP BY invoice_id, line_id HAVING COUNT(*) > 1);

-- name: qc_invoices_with_multiple_dates
-- One receipt must belong to exactly one trading day. Expect 0 rows.
SELECT 'invoice spanning >1 date' AS check_name, COUNT(*) AS failures
FROM (SELECT invoice_id FROM fact_sales_lines
      GROUP BY invoice_id HAVING COUNT(DISTINCT date_key) > 1);

-- name: qc_referential_integrity
-- Every fact key must resolve to a dimension member. Expect 0 failures.
SELECT 'fact -> dim_branch' AS fk, COUNT(*) AS failures
  FROM fact_sales_lines f LEFT JOIN dim_branch b  ON b.branch_id  = f.branch_id  WHERE b.branch_id  IS NULL
UNION ALL
SELECT 'fact -> dim_date', COUNT(*)
  FROM fact_sales_lines f LEFT JOIN dim_date d    ON d.date_key   = f.date_key   WHERE d.date_key   IS NULL
UNION ALL
SELECT 'fact -> dim_product', COUNT(*)
  FROM fact_sales_lines f LEFT JOIN dim_product p ON p.product_id = f.product_id WHERE p.product_id IS NULL
UNION ALL
SELECT 'fact -> dim_customer (excl. UNKNOWN)', COUNT(*)
  FROM fact_sales_lines f LEFT JOIN dim_customer c ON c.customer_id = f.customer_id
  WHERE c.customer_id IS NULL AND f.customer_id <> 'UNKNOWN';

-- name: qc_unattributed_coverage
SELECT COUNT(*)                                        AS unattributed_lines,
       ROUND(SUM(net_revenue), 2)                      AS unattributed_revenue,
       ROUND(100.0 * SUM(net_revenue) /
             (SELECT SUM(net_revenue) FROM fact_sales_lines), 3) AS pct_of_group_revenue
FROM fact_sales_lines
WHERE customer_id = 'UNKNOWN';

-- name: qc_inferred_members
-- Rows kept in the fact but with no real dimension row get an inferred member
-- so they cannot silently disappear from an inner join.
SELECT p.product_id, p.product_name, COUNT(f.invoice_id) AS lines, ROUND(SUM(f.net_revenue),2) AS net_revenue
FROM dim_product p JOIN fact_sales_lines f ON f.product_id = p.product_id
WHERE p.product_id = 'ZZ99'
GROUP BY p.product_id, p.product_name;
