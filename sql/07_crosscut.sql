-- ---------------------------------------------------------------------------
-- 07_crosscut.sql — INTERSECT (Ch. 22 step 3)
-- ---------------------------------------------------------------------------
-- The killer question is not "which branch" or "which product" or "which
-- segment" — it is "which branch x product x segment". These queries find the
-- cells that matter, ranked by how much of the group decline they explain.
-- ---------------------------------------------------------------------------

-- name: crosscut_branch_category_segment
WITH cell AS (
    SELECT branch_name,
           category,
           customer_segment AS segment,
           SUM(CASE WHEN period_key = '2025Q3' THEN net_revenue ELSE 0 END) AS rev_2025,
           SUM(CASE WHEN period_key = '2026Q3' THEN net_revenue ELSE 0 END) AS rev_2026
    FROM v_sales_detail_attrib
    GROUP BY branch_name, category, customer_segment
), tot AS (
    SELECT SUM(CASE WHEN period_key = '2025Q3' THEN net_revenue ELSE 0 END) AS t25,
           SUM(CASE WHEN period_key = '2026Q3' THEN net_revenue ELSE 0 END) AS t26
    FROM v_sales_detail_attrib
)
SELECT c.branch_name,
       c.category,
       c.segment,
       ROUND(c.rev_2025, 0)                                                AS rev_2025,
       ROUND(c.rev_2026, 0)                                                AS rev_2026,
       ROUND(c.rev_2026 - c.rev_2025, 0)                                   AS delta,
       ROUND(100.0 * (c.rev_2026 - c.rev_2025) / (t.t26 - t.t25), 2)       AS pct_of_decline,
       ROUND(100.0 * (c.rev_2026 / c.rev_2025 - 1), 1)                     AS yoy_pct
FROM cell c CROSS JOIN tot t
WHERE c.rev_2025 > 0
ORDER BY delta ASC
LIMIT 25;

-- name: crosscut_branch_category
-- Same intersection collapsed one level, for the heat-map visual.
SELECT branch_name,
       category,
       ROUND(SUM(CASE WHEN period_key = '2025Q3' THEN net_revenue END), 0) AS rev_2025,
       ROUND(SUM(CASE WHEN period_key = '2026Q3' THEN net_revenue END), 0) AS rev_2026,
       ROUND(SUM(CASE WHEN period_key = '2026Q3' THEN net_revenue END)
           - SUM(CASE WHEN period_key = '2025Q3' THEN net_revenue END), 0) AS delta,
       ROUND((SUM(CASE WHEN period_key = '2026Q3' THEN net_revenue END)
            / SUM(CASE WHEN period_key = '2025Q3' THEN net_revenue END) - 1) * 100, 1) AS yoy_pct
FROM v_sales_detail
GROUP BY branch_name, category
ORDER BY delta ASC;

-- name: crosscut_branch_category_segment_full
-- The complete grid (no LIMIT) so the driver partition in src/decompose.py can
-- be computed as a exact, non-overlapping partition of the total change.
SELECT b.branch_id,
       b.branch_name,
       p.category,
       f.customer_segment AS segment,
       SUM(CASE WHEN f.period_key = '2025Q3' THEN f.net_revenue ELSE 0 END) AS rev_2025,
       SUM(CASE WHEN f.period_key = '2026Q3' THEN f.net_revenue ELSE 0 END) AS rev_2026,
       SUM(CASE WHEN f.period_key = '2026Q3' THEN f.gross_profit ELSE 0 END)
     - SUM(CASE WHEN f.period_key = '2025Q3' THEN f.gross_profit ELSE 0 END) AS gp_delta
FROM v_sales_detail_attrib f
JOIN dim_branch  b ON b.branch_id  = f.branch_id
JOIN dim_product p ON p.product_id = f.product_id
GROUP BY b.branch_id, b.branch_name, p.category, f.customer_segment;

-- name: crosscut_concentration
-- How concentrated is the damage? Share of the total decline held by the worst
-- N cells — the "few cells explain most of it" test.
WITH cell AS (
    SELECT branch_name || ' | ' || category || ' | ' || customer_segment AS cell,
           SUM(CASE WHEN period_key = '2026Q3' THEN net_revenue ELSE 0 END)
         - SUM(CASE WHEN period_key = '2025Q3' THEN net_revenue ELSE 0 END) AS delta
    FROM v_sales_detail_attrib
    GROUP BY branch_name, category, customer_segment
), ranked AS (
    SELECT cell, delta,
           ROW_NUMBER() OVER (ORDER BY delta ASC) AS rn,
           SUM(CASE WHEN delta < 0 THEN delta ELSE 0 END) OVER () AS total_decline
    FROM cell
)
SELECT rn, cell, ROUND(delta, 0) AS delta,
       ROUND(100.0 * delta / total_decline, 2) AS pct_of_decline
FROM ranked
WHERE rn <= 8
ORDER BY rn;
