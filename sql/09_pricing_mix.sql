-- ---------------------------------------------------------------------------
-- 09_pricing_mix.sql — the PRICE / MIX half of the AOV story
-- ---------------------------------------------------------------------------
-- AOV fell 4.1% while list prices rose 4.5%. That gap needs a cause: deeper
-- discounting, or a mix shift toward cheaper baskets, or both. These queries
-- separate the two.
-- ---------------------------------------------------------------------------

-- name: pricing_discount_depth_by_category
SELECT p.category,
       ROUND(SUM(CASE WHEN f.period_key = '2025Q3' THEN f.discount_amount END)
           / SUM(CASE WHEN f.period_key = '2025Q3' THEN f.gross_revenue END) * 100, 3) AS discount_pct_2025,
       ROUND(SUM(CASE WHEN f.period_key = '2026Q3' THEN f.discount_amount END)
           / SUM(CASE WHEN f.period_key = '2026Q3' THEN f.gross_revenue END) * 100, 3) AS discount_pct_2026,
       ROUND(SUM(CASE WHEN f.period_key = '2026Q3' THEN f.discount_amount END)
           / SUM(CASE WHEN f.period_key = '2026Q3' THEN f.gross_revenue END) * 100
           - SUM(CASE WHEN f.period_key = '2025Q3' THEN f.discount_amount END)
           / SUM(CASE WHEN f.period_key = '2025Q3' THEN f.gross_revenue END) * 100, 3)  AS discount_pp_change
FROM fact_sales_lines f
JOIN dim_product p ON p.product_id = f.product_id
GROUP BY p.category
ORDER BY discount_pp_change DESC;

-- name: pricing_price_per_unit_by_category
-- List-price inflation by category: proves prices did NOT fall.
SELECT p.category,
       ROUND(SUM(CASE WHEN f.period_key = '2025Q3' THEN f.gross_revenue END)
           / SUM(CASE WHEN f.period_key = '2025Q3' THEN f.quantity END), 2) AS gross_price_2025,
       ROUND(SUM(CASE WHEN f.period_key = '2026Q3' THEN f.gross_revenue END)
           / SUM(CASE WHEN f.period_key = '2026Q3' THEN f.quantity END), 2) AS gross_price_2026,
       ROUND((SUM(CASE WHEN f.period_key = '2026Q3' THEN f.gross_revenue END)
            / SUM(CASE WHEN f.period_key = '2026Q3' THEN f.quantity END))
           / (SUM(CASE WHEN f.period_key = '2025Q3' THEN f.gross_revenue END)
            / SUM(CASE WHEN f.period_key = '2025Q3' THEN f.quantity END)) * 100 - 100, 2) AS gross_price_yoy_pct,
       ROUND(SUM(CASE WHEN f.period_key = '2025Q3' THEN f.quantity END) / 1000.0, 1) AS units_2025_k,
       ROUND(SUM(CASE WHEN f.period_key = '2026Q3' THEN f.quantity END) / 1000.0, 1) AS units_2026_k
FROM fact_sales_lines f
JOIN dim_product p ON p.product_id = f.product_id
GROUP BY p.category
ORDER BY gross_price_yoy_pct DESC;

-- name: pricing_mix_shift
-- Mix: which categories gained or lost share of the basket.
WITH t AS (
    SELECT period_key, category, SUM(net_revenue) AS rev
    FROM v_sales_detail
    GROUP BY period_key, category
), tot AS (
    SELECT period_key, SUM(rev) AS total FROM t GROUP BY period_key
)
SELECT t.category,
       ROUND(100.0 * MAX(CASE WHEN t.period_key = '2025Q3' THEN t.rev END)
             / MAX(CASE WHEN t.period_key = '2025Q3' THEN tot.total END), 2) AS share_2025_pct,
       ROUND(100.0 * MAX(CASE WHEN t.period_key = '2026Q3' THEN t.rev END)
             / MAX(CASE WHEN t.period_key = '2026Q3' THEN tot.total END), 2) AS share_2026_pct,
       ROUND(100.0 * MAX(CASE WHEN t.period_key = '2026Q3' THEN t.rev END)
             / MAX(CASE WHEN t.period_key = '2026Q3' THEN tot.total END)
           - 100.0 * MAX(CASE WHEN t.period_key = '2025Q3' THEN t.rev END)
             / MAX(CASE WHEN t.period_key = '2025Q3' THEN tot.total END), 2) AS share_pp_change
FROM t JOIN tot ON tot.period_key = t.period_key
GROUP BY t.category
ORDER BY share_pp_change DESC;

-- name: pricing_discount_cost
-- Gross revenue and the discount given away, by period. The gap between the
-- two periods' discount rates is the price of the deepened promotion.
SELECT period_key,
       ROUND(SUM(gross_revenue), 2)                                  AS gross_revenue,
       ROUND(SUM(discount_amount), 2)                                AS discount_given,
       ROUND(SUM(discount_amount) / SUM(gross_revenue) * 100, 3)      AS discount_pct_of_gross
FROM fact_sales_lines
GROUP BY period_key
ORDER BY period_key;

-- name: pricing_aov_bridge_inputs
-- The three multiplicative inputs per period, plus margin, on one row each.
SELECT period_key,
       COUNT(DISTINCT customer_id)                              AS customers,
       COUNT(DISTINCT invoice_id)                               AS orders,
       ROUND(SUM(net_revenue), 0)                               AS net_revenue,
       ROUND(1.0 * COUNT(DISTINCT invoice_id)
             / COUNT(DISTINCT customer_id), 4)                  AS frequency,
       ROUND(SUM(net_revenue) / COUNT(DISTINCT invoice_id), 2)   AS aov,
       ROUND(SUM(gross_profit) / SUM(net_revenue) * 100, 2)      AS gross_margin_pct
FROM v_sales_detail_attrib
GROUP BY period_key
ORDER BY period_key;
