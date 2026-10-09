-- ---------------------------------------------------------------------------
-- 05_structure.sql — decompose by STRUCTURE (Ch. 22 step 2)
-- ---------------------------------------------------------------------------
-- Same total change, sliced four ways. Each slice answers WHERE the money went
-- and, by subtraction, how much each owner's plan has to change.
-- ---------------------------------------------------------------------------

-- name: structure_by_branch
SELECT b.branch_id,
       b.branch_name,
       b.region,
       ROUND(SUM(CASE WHEN f.period_key = '2025Q3' THEN f.net_revenue END), 2) AS rev_2025,
       ROUND(SUM(CASE WHEN f.period_key = '2026Q3' THEN f.net_revenue END), 2) AS rev_2026,
       ROUND(SUM(CASE WHEN f.period_key = '2026Q3' THEN f.net_revenue END)
           - SUM(CASE WHEN f.period_key = '2025Q3' THEN f.net_revenue END), 2) AS delta,
       ROUND((SUM(CASE WHEN f.period_key = '2026Q3' THEN f.net_revenue END)
            / SUM(CASE WHEN f.period_key = '2025Q3' THEN f.net_revenue END) - 1) * 100, 2) AS yoy_pct
FROM fact_sales_lines f
JOIN dim_branch b ON b.branch_id = f.branch_id
GROUP BY b.branch_id, b.branch_name, b.region
ORDER BY delta ASC;

-- name: structure_by_category
SELECT p.category,
       ROUND(SUM(CASE WHEN f.period_key = '2025Q3' THEN f.net_revenue END), 2) AS rev_2025,
       ROUND(SUM(CASE WHEN f.period_key = '2026Q3' THEN f.net_revenue END), 2) AS rev_2026,
       ROUND(SUM(CASE WHEN f.period_key = '2026Q3' THEN f.net_revenue END)
           - SUM(CASE WHEN f.period_key = '2025Q3' THEN f.net_revenue END), 2) AS delta,
       ROUND((SUM(CASE WHEN f.period_key = '2026Q3' THEN f.net_revenue END)
            / SUM(CASE WHEN f.period_key = '2025Q3' THEN f.net_revenue END) - 1) * 100, 2) AS yoy_pct,
       ROUND(SUM(CASE WHEN f.period_key = '2026Q3' THEN f.gross_profit END), 2) AS gp_2026,
       ROUND(SUM(CASE WHEN f.period_key = '2026Q3' THEN f.gross_profit END)
           - SUM(CASE WHEN f.period_key = '2025Q3' THEN f.gross_profit END), 2) AS gp_delta
FROM fact_sales_lines f
JOIN dim_product p ON p.product_id = f.product_id
GROUP BY p.category
ORDER BY delta ASC;

-- name: structure_by_channel
SELECT channel,
       ROUND(SUM(CASE WHEN period_key = '2025Q3' THEN net_revenue END), 2) AS rev_2025,
       ROUND(SUM(CASE WHEN period_key = '2026Q3' THEN net_revenue END), 2) AS rev_2026,
       ROUND(SUM(CASE WHEN period_key = '2026Q3' THEN net_revenue END)
           - SUM(CASE WHEN period_key = '2025Q3' THEN net_revenue END), 2) AS delta,
       ROUND((SUM(CASE WHEN period_key = '2026Q3' THEN net_revenue END)
            / SUM(CASE WHEN period_key = '2025Q3' THEN net_revenue END) - 1) * 100, 2) AS yoy_pct
FROM fact_sales_lines
GROUP BY channel
ORDER BY delta ASC;

-- name: structure_by_segment
SELECT customer_segment,
       ROUND(SUM(CASE WHEN period_key = '2025Q3' THEN net_revenue END), 2) AS rev_2025,
       ROUND(SUM(CASE WHEN period_key = '2026Q3' THEN net_revenue END), 2) AS rev_2026,
       ROUND(SUM(CASE WHEN period_key = '2026Q3' THEN net_revenue END)
           - SUM(CASE WHEN period_key = '2025Q3' THEN net_revenue END), 2) AS delta,
       ROUND((SUM(CASE WHEN period_key = '2026Q3' THEN net_revenue END)
            / SUM(CASE WHEN period_key = '2025Q3' THEN net_revenue END) - 1) * 100, 2) AS yoy_pct,
       COUNT(DISTINCT CASE WHEN period_key = '2025Q3' THEN customer_id END) AS cust_2025,
       COUNT(DISTINCT CASE WHEN period_key = '2026Q3' THEN customer_id END) AS cust_2026
FROM v_sales_detail_attrib
GROUP BY customer_segment
ORDER BY delta ASC;

-- name: structure_branch_mechanism
-- The mechanism identity applied per branch: separates a branch that lost
-- CUSTOMERS from one that kept them but lost FREQUENCY or BASKET SIZE.
SELECT b.branch_name,
       f.period_key,
       COUNT(DISTINCT f.customer_id)                                            AS customers,
       COUNT(DISTINCT f.invoice_id)                                             AS orders,
       ROUND(1.0 * COUNT(DISTINCT f.invoice_id) / COUNT(DISTINCT f.customer_id), 4) AS frequency,
       ROUND(SUM(f.net_revenue) / COUNT(DISTINCT f.invoice_id), 2)              AS avg_order_value
FROM fact_sales_lines f
JOIN dim_branch b ON b.branch_id = f.branch_id
WHERE f.customer_id <> 'UNKNOWN'
GROUP BY b.branch_name, f.period_key
ORDER BY b.branch_name, f.period_key;

-- name: structure_category_mechanism
SELECT p.category,
       f.period_key,
       ROUND(SUM(f.net_revenue), 2)                                             AS net_revenue,
       ROUND(1.0 * COUNT(*) / COUNT(DISTINCT f.invoice_id), 3)                  AS lines_per_order,
       ROUND(SUM(f.quantity) / COUNT(DISTINCT f.invoice_id), 3)                 AS units_per_order,
       ROUND(SUM(f.net_revenue) / SUM(f.quantity), 2)                           AS net_price_per_unit,
       ROUND(SUM(f.discount_amount) / SUM(f.gross_revenue) * 100, 3)            AS discount_pct
FROM fact_sales_lines f
JOIN dim_product p ON p.product_id = f.product_id
GROUP BY p.category, f.period_key
ORDER BY p.category, f.period_key;

-- name: structure_by_sku_top_declines
-- SKU-level, to get from "Personal Care fell" to "these two bottles fell".
SELECT p.product_id,
       p.product_name,
       p.category,
       p.is_hero_sku,
       ROUND(SUM(CASE WHEN f.period_key = '2025Q3' THEN f.net_revenue END), 2) AS rev_2025,
       ROUND(SUM(CASE WHEN f.period_key = '2026Q3' THEN f.net_revenue END), 2) AS rev_2026,
       ROUND(SUM(CASE WHEN f.period_key = '2026Q3' THEN f.net_revenue END)
           - SUM(CASE WHEN f.period_key = '2025Q3' THEN f.net_revenue END), 2) AS delta
FROM fact_sales_lines f
JOIN dim_product p ON p.product_id = f.product_id
GROUP BY p.product_id, p.product_name, p.category, p.is_hero_sku
ORDER BY delta ASC
LIMIT 15;
