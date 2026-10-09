-- ---------------------------------------------------------------------------
-- 01_schema.sql — star schema for the revenue-decline diagnostic
-- ---------------------------------------------------------------------------
-- A deliberately Kimball-shaped model: conformed dimensions, one fact table at
-- line-item grain, plus a second fact for shelf availability. It is the same
-- model you would build in Power BI, which is why the dashboard spec in
-- docs/07_dashboard_spec.md maps 1:1 onto these tables.
--
-- Loaded by src/run_sql.py from data/processed/*.csv.
-- ---------------------------------------------------------------------------

DROP TABLE IF EXISTS fact_sales_lines;
DROP TABLE IF EXISTS fact_stockouts;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_branch;
DROP TABLE IF EXISTS dim_date;

-- ---------------------------------------------------------------- dimensions
CREATE TABLE dim_date (
    date_key          INTEGER PRIMARY KEY,   -- YYYYMMDD
    date              TEXT    NOT NULL,
    period_key        TEXT    NOT NULL,      -- '2025Q3' | '2026Q3'
    year              INTEGER NOT NULL,
    quarter           INTEGER NOT NULL,
    month             INTEGER NOT NULL,
    month_name        TEXT    NOT NULL,
    iso_week          INTEGER NOT NULL,
    day_of_week       INTEGER NOT NULL,      -- 1 = Monday
    day_name          TEXT    NOT NULL,
    is_weekend        INTEGER NOT NULL,
    is_school_holiday INTEGER NOT NULL
);

CREATE TABLE dim_branch (
    branch_id   TEXT PRIMARY KEY,
    branch_name TEXT NOT NULL,
    region      TEXT NOT NULL,
    size_index  REAL NOT NULL,
    opened_date TEXT NOT NULL
);

CREATE TABLE dim_product (
    product_id   TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category     TEXT NOT NULL,
    subcategory  TEXT NOT NULL,
    list_price   REAL NOT NULL,
    gross_margin REAL NOT NULL,
    is_hero_sku  INTEGER NOT NULL
);

CREATE TABLE dim_customer (
    customer_id        TEXT PRIMARY KEY,
    home_branch_id     TEXT NOT NULL,
    home_region        TEXT NOT NULL,
    acquisition_date   TEXT NOT NULL,
    acquisition_period TEXT NOT NULL
);

-- --------------------------------------------------------------------- facts
-- GRAIN: one row = one line item on one customer receipt.
CREATE TABLE fact_sales_lines (
    period_key       TEXT    NOT NULL,
    date_key         INTEGER NOT NULL,
    invoice_id       TEXT    NOT NULL,
    line_id          INTEGER NOT NULL,
    branch_id        TEXT    NOT NULL,
    customer_id      TEXT    NOT NULL,
    customer_segment TEXT    NOT NULL,   -- lifecycle label as at this period
    channel          TEXT    NOT NULL,
    product_id       TEXT    NOT NULL,
    quantity         REAL    NOT NULL,
    unit_price       REAL    NOT NULL,
    discount_pct     REAL    NOT NULL,
    gross_revenue    REAL    NOT NULL,
    discount_amount  REAL    NOT NULL,
    net_revenue      REAL    NOT NULL,
    cogs             REAL    NOT NULL,
    gross_profit     REAL    NOT NULL,
    PRIMARY KEY (invoice_id, line_id)
);

-- GRAIN: one row = one branch x one SKU x one day.
CREATE TABLE fact_stockouts (
    date_key             INTEGER NOT NULL,
    date                 TEXT    NOT NULL,
    period_key           TEXT    NOT NULL,
    branch_id            TEXT    NOT NULL,
    product_id           TEXT    NOT NULL,
    product_name         TEXT    NOT NULL,
    category             TEXT    NOT NULL,
    in_stock             INTEGER NOT NULL,   -- 1 = on shelf that day
    consecutive_days_out INTEGER NOT NULL,
    incident_flag        INTEGER NOT NULL,   -- 1 = inside the known supply incident
    PRIMARY KEY (date_key, branch_id, product_id)
);

CREATE INDEX ix_fact_sales_period  ON fact_sales_lines (period_key);
CREATE INDEX ix_fact_sales_branch  ON fact_sales_lines (branch_id, period_key);
CREATE INDEX ix_fact_sales_product ON fact_sales_lines (product_id);
CREATE INDEX ix_fact_sales_cust    ON fact_sales_lines (customer_id);
CREATE INDEX ix_stock_branch_sku   ON fact_stockouts (branch_id, product_id, date_key);
