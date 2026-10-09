-- ---------------------------------------------------------------------------
-- 04_mechanism.sql — decompose by MECHANISM first (Ch. 22 step 1)
-- ---------------------------------------------------------------------------
-- Revenue = Customers x Frequency x Average Order Value. This explains HOW the
-- change happened before we ask WHERE. Run on attributed lines only, because
-- customer and frequency maths is impossible without a customer identifier.
-- ---------------------------------------------------------------------------

-- name: mechanism_by_period
SELECT period_key,
       COUNT(DISTINCT customer_id)                                  AS customers,
       COUNT(DISTINCT invoice_id)                                   AS orders,
       ROUND(SUM(net_revenue), 2)                                   AS net_revenue,
       ROUND(1.0 * COUNT(DISTINCT invoice_id) /
             COUNT(DISTINCT customer_id), 4)                        AS orders_per_customer,
       ROUND(SUM(net_revenue) / COUNT(DISTINCT invoice_id), 2)      AS avg_order_value
FROM v_sales_detail_attrib
GROUP BY period_key
ORDER BY period_key;

-- name: mechanism_basket_detail
-- The AOV driver, opened up: basket breadth and depth = what changed per trip.
SELECT period_key,
       COUNT(DISTINCT invoice_id)                                        AS orders,
       ROUND(1.0 * COUNT(*) / COUNT(DISTINCT invoice_id), 3)             AS lines_per_order,
       ROUND(SUM(quantity) / COUNT(DISTINCT invoice_id), 3)              AS units_per_order,
       ROUND(SUM(gross_revenue) / SUM(quantity), 2)                      AS list_price_per_unit,
       ROUND(SUM(discount_amount) / SUM(gross_revenue) * 100, 3)         AS avg_discount_pct,
       ROUND(SUM(net_revenue) / SUM(quantity), 2)                        AS net_price_per_unit
FROM v_sales_detail_attrib
GROUP BY period_key
ORDER BY period_key;

-- name: mechanism_margin_by_period
-- Revenue is not profit (Ch. 20): the same story told with margin attached.
SELECT period_key,
       ROUND(SUM(net_revenue), 2)                                        AS net_revenue,
       ROUND(SUM(cogs), 2)                                               AS cogs,
       ROUND(SUM(gross_profit), 2)                                       AS gross_profit,
       ROUND(SUM(gross_profit) / SUM(net_revenue) * 100, 2)              AS gross_margin_pct
FROM v_sales_detail_attrib
GROUP BY period_key
ORDER BY period_key;
