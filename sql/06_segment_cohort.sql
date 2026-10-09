-- ---------------------------------------------------------------------------
-- 06_segment_cohort.sql — the cohort evidence behind the retention finding
-- ---------------------------------------------------------------------------
-- Because the same customer IDs appear in both periods, we can measure who came
-- back rather than comparing two unrelated snapshots. This is the difference
-- between "segments look different" and "46% of last year's regulars did not
-- return".
-- ---------------------------------------------------------------------------

-- name: cohort_retention_summary
WITH c25 AS (SELECT DISTINCT customer_id FROM v_sales_detail_attrib WHERE period_key = '2025Q3'),
     c26 AS (SELECT DISTINCT customer_id FROM v_sales_detail_attrib WHERE period_key = '2026Q3')
SELECT (SELECT COUNT(*) FROM c25)                                                   AS customers_2025q3,
       (SELECT COUNT(*) FROM c26)                                                   AS customers_2026q3,
       (SELECT COUNT(*) FROM c25 JOIN c26 USING (customer_id))                      AS returned,
       (SELECT COUNT(*) FROM c25 WHERE customer_id NOT IN (SELECT customer_id FROM c26)) AS lapsed,
       (SELECT COUNT(*) FROM c26 WHERE customer_id NOT IN (SELECT customer_id FROM c25)) AS new_in_2026,
       ROUND(100.0 * (SELECT COUNT(*) FROM c25 JOIN c26 USING (customer_id))
             / (SELECT COUNT(*) FROM c25), 2)                                       AS return_rate_pct;

-- name: cohort_retention_by_segment
WITH c25 AS (SELECT DISTINCT customer_id, customer_segment FROM v_sales_detail_attrib WHERE period_key = '2025Q3'),
     c26 AS (SELECT DISTINCT customer_id FROM v_sales_detail_attrib WHERE period_key = '2026Q3')
SELECT c25.customer_segment                                   AS segment_2025q3,
       COUNT(*)                                               AS customers,
       SUM(CASE WHEN c26.customer_id IS NOT NULL THEN 1 ELSE 0 END) AS returned,
       COUNT(*) - SUM(CASE WHEN c26.customer_id IS NOT NULL THEN 1 ELSE 0 END) AS lapsed,
       ROUND(100.0 * SUM(CASE WHEN c26.customer_id IS NOT NULL THEN 1 ELSE 0 END)
             / COUNT(*), 2)                                   AS return_rate_pct
FROM c25 LEFT JOIN c26 USING (customer_id)
GROUP BY c25.customer_segment
ORDER BY return_rate_pct ASC;

-- name: cohort_retention_by_branch_and_segment
WITH c25 AS (SELECT DISTINCT customer_id, customer_segment, branch_id FROM v_sales_detail_attrib WHERE period_key = '2025Q3'),
     c26 AS (SELECT DISTINCT customer_id FROM v_sales_detail_attrib WHERE period_key = '2026Q3')
SELECT b.branch_name,
       c25.customer_segment,
       COUNT(*)                                                     AS customers,
       ROUND(100.0 * SUM(CASE WHEN c26.customer_id IS NOT NULL THEN 1 ELSE 0 END)
             / COUNT(*), 2)                                         AS return_rate_pct
FROM c25
LEFT JOIN c26 USING (customer_id)
JOIN dim_branch b ON b.branch_id = c25.branch_id
GROUP BY b.branch_name, c25.customer_segment
HAVING COUNT(*) >= 40
ORDER BY return_rate_pct ASC
LIMIT 20;

-- name: segment_transition_matrix
-- Where did each 2025 segment actually go? "Lapsed" = bought nothing in 2026.
WITH c25 AS (SELECT DISTINCT customer_id, customer_segment AS seg_2025 FROM v_sales_detail_attrib WHERE period_key = '2025Q3'),
     c26 AS (SELECT DISTINCT customer_id, customer_segment AS seg_2026 FROM v_sales_detail_attrib WHERE period_key = '2026Q3')
SELECT c25.seg_2025,
       COALESCE(c26.seg_2026, 'Lapsed') AS seg_2026,
       COUNT(*)                         AS customers
FROM c25 LEFT JOIN c26 USING (customer_id)
GROUP BY c25.seg_2025, COALESCE(c26.seg_2026, 'Lapsed')
ORDER BY c25.seg_2025, customers DESC;

-- name: segment_frequency_and_basket
-- For each segment, in each period: how many, how often, how big a basket.
SELECT customer_segment,
       period_key,
       COUNT(DISTINCT customer_id)                                 AS customers,
       COUNT(DISTINCT invoice_id)                                  AS orders,
       ROUND(1.0 * COUNT(DISTINCT invoice_id) / COUNT(DISTINCT customer_id), 3) AS orders_per_customer,
       ROUND(SUM(net_revenue) / COUNT(DISTINCT invoice_id), 2)     AS avg_order_value,
       ROUND(SUM(net_revenue) / COUNT(DISTINCT customer_id), 2)    AS revenue_per_customer
FROM v_sales_detail_attrib
GROUP BY customer_segment, period_key
ORDER BY customer_segment, period_key;
