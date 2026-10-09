-- ---------------------------------------------------------------------------
-- 02_views.sql — the two views every other query builds on
-- ---------------------------------------------------------------------------
-- v_sales_detail      : the star schema flattened for ad-hoc analysis
-- v_sales_detail_attrib: the same, restricted to lines that carry a customer
--                        identifier (the mechanism bridge runs on this, because
--                        customer/frequency maths is impossible without an ID)
-- ---------------------------------------------------------------------------

DROP VIEW IF EXISTS v_sales_detail;
CREATE VIEW v_sales_detail AS
SELECT
    f.period_key,
    d.date,
    d.date_key,
    d.year,
    d.month,
    d.month_name,
    d.iso_week,
    d.day_name,
    d.is_weekend,
    f.invoice_id,
    f.line_id,
    b.branch_id,
    b.branch_name,
    b.region,
    f.customer_id,
    f.customer_segment,
    c.home_branch_id,
    f.channel,
    p.product_id,
    p.product_name,
    p.category,
    p.is_hero_sku,
    f.quantity,
    f.unit_price,
    f.discount_pct,
    f.gross_revenue,
    f.discount_amount,
    f.net_revenue,
    f.cogs,
    f.gross_profit
FROM fact_sales_lines f
JOIN dim_date    d ON d.date_key   = f.date_key
JOIN dim_branch  b ON b.branch_id  = f.branch_id
JOIN dim_product p ON p.product_id = f.product_id
LEFT JOIN dim_customer c ON c.customer_id = f.customer_id;

DROP VIEW IF EXISTS v_sales_detail_attrib;
CREATE VIEW v_sales_detail_attrib AS
SELECT *
FROM v_sales_detail
WHERE customer_id <> 'UNKNOWN';
