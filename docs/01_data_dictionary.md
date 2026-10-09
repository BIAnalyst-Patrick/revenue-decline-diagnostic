# Data Dictionary

Everything a reader (or a Power BI developer) needs to use this dataset without
guessing. The model is a Kimball star schema: conformed dimensions, two fact
tables, and one denormalised view for ad-hoc work.

## 1. The grain statement (write this before any query — Ch. 4)

| Table | One row = | Keys |
|---|---|---|
| `fact_sales_lines` | **one line item on one customer receipt** | `(invoice_id, line_id)` |
| `fact_stockouts` | one branch × one SKU × one day | `(date_key, branch_id, product_id)` |
| `dim_date` | one calendar day | `date_key` |
| `dim_branch` | one store | `branch_id` |
| `dim_product` | one SKU | `product_id` |
| `dim_customer` | one customer | `customer_id` |

If an analysis needs customer behaviour, the grain supports it. If it needs
individual unit serials, the grain does not — and no amount of SQL will recover
them (Ch. 19).

## 2. `fact_sales_lines`

| Column | Type | Notes |
|---|---|---|
| `period_key` | text | `2025Q3` or `2026Q3`; authoritative from `dim_date` |
| `date_key` | int | YYYYMMDD → `dim_date` |
| `invoice_id` | text | e.g. `2026Q3-0117919`; one receipt |
| `line_id` | int | 1..n within the invoice |
| `branch_id` | text | → `dim_branch` |
| `customer_id` | text | → `dim_customer`; `UNKNOWN` for anonymous walk-ins |
| `customer_segment` | text | **period-specific** lifecycle label (see §6) |
| `channel` | text | `In-store` or `Online` (a property of the trip) |
| `product_id` | text | → `dim_product`; `ZZ99` = inferred unmapped member |
| `quantity` | real | units |
| `unit_price` | real | gross price per unit, before discount |
| `discount_pct` | real | 0–1 |
| `gross_revenue` | real | `quantity × unit_price` |
| `discount_amount` | real | `gross_revenue × discount_pct` |
| `net_revenue` | real | `gross_revenue − discount_amount` ← **the revenue measure** |
| `cogs` | real | `quantity × unit_cost` |
| `gross_profit` | real | `net_revenue − cogs` |

`customer_segment` lives on the fact table deliberately: it is the label *as at
that period*, so no future information leaks into the base-year analysis. The
same customer can legitimately carry a different label in Q3 2026 — that
migration is the retention evidence, not a data error.

## 3. `fact_stockouts`

| Column | Notes |
|---|---|
| `date_key`, `date`, `period_key` | when the shelf was observed |
| `branch_id`, `product_id`, `product_name` | where and what |
| `category` | `Personal Care` for every row in this dataset |
| `in_stock` | 1 = on shelf that day, 0 = not |
| `consecutive_days_out` | running streak of consecutive zero days |
| `incident_flag` | 1 = inside the known supply incident window |

This table is what converts "probably a stock problem" into evidence (Ch. 23).
Without it, the supply finding would be a hypothesis; with it, it is measured.

## 4. Dimensions

**`dim_date`** — `date_key, date, period_key, year, quarter, month, month_name,
iso_week, day_of_week (1=Mon), day_name, is_weekend, is_school_holiday`.
The one dimension every business shares; built once, reused everywhere (Ch. 18).

**`dim_branch`** — `branch_id, branch_name, region, size_index, opened_date`.
`size_index` is a scale proxy (1.00 = a standard store) used only by the
simulator; do not report on it.

**`dim_product`** — `product_id, product_name, category, subcategory,
list_price, gross_margin, is_hero_sku`. `is_hero_sku = 1` marks the two SKUs at
the centre of the supply incident.

**`dim_customer`** — `customer_id, home_branch_id, home_region,
acquisition_date, acquisition_period`. Static attributes only; the
period-varying label is on the fact table.

## 5. Denominators — the pairs that must travel together (Ch. 27)

| Metric | Numerator | Denominator | Interrogate |
|---|---|---|---|
| Average order value | `SUM(net_revenue)` | `COUNT(DISTINCT invoice_id)` | identified customers only |
| Orders per customer | `COUNT(DISTINCT invoice_id)` | `COUNT(DISTINCT customer_id)` | excludes `UNKNOWN` |
| Discount depth | `SUM(discount_amount)` | `SUM(gross_revenue)` | gross, not net |
| Gross margin % | `SUM(gross_profit)` | `SUM(net_revenue)` | net revenue |
| Return / retention rate | customers in both periods | customers in base period | excludes new customers |

**Never ship one without its pair.** "Retention 83.8%" is incomplete;
"Retention 83.8% on a base of 5,265, with 1,145 new customers added" is a fact.

## 6. Segment definitions

Lifecycle segments are assigned by the (simulated) CRM at period start from
recency/frequency/value:

| Segment | Working definition | Action it implies |
|---|---|---|
| **Loyal** | recent, frequent, high value | reward, protect |
| **Regular** | recent, mid frequency | upsell, cross-sell |
| **At-Risk** | was frequent, now stale, high past value | win-back now |
| **New** | first purchase within the last 90 days | onboarding → 2nd purchase |
| **Hibernating** | stale, low frequency | cheap reactivation only |
| **Unattributed** | no customer identifier | fix capture at source |

`Unattributed` is not a segment; it is the *absence* of one, and it is reported
as a coverage limit rather than an "Other" bucket.

## 7. Derived analysis tables

Produced by the pipeline into `outputs/tables/`:

| Table | One row = |
|---|---|
| `mechanism_by_period` | one period's customers, orders, revenue, frequency, AOV |
| `decomp_mechanism_waterfall` | one bar of the mechanism bridge |
| `decomp_mechanism_sensitivity` | one driver's attribution under three methods |
| `decomp_structure_<slice>` | one branch/category/segment/channel contribution |
| `decomp_driver_partition` | one owned problem (sums to the total decline) |
| `decomp_cell_leaders` | one store × category × segment cell |
| `crosscut_branch_category_segment_full` | the complete intersection grid |
| `cohort_retention_*` | one cohort's return behaviour |
| `stockout_*` | the shelf-availability evidence |
| `pricing_*` | discount depth, price per unit, mix shift |

## 8. Planted data-quality issues (and their treatment)

Documented in full in `docs/03_data_quality_report.md`. Summary:

| Issue | Treatment |
|---|---|
| Duplicate `(invoice_id, line_id)` | deduplicate, keep first |
| Quantity 0 / negative / 999 | quarantine |
| Date outside both quarters | quarantine |
| NULL `discount_pct` | set to 0, flag `discount_missing` |
| Non-canonical category labels | map to canonical, flag `category_normalised` |
| Missing `customer_id` | label `Unattributed`, declare a coverage limit |
| SKU absent from `dim_product` | inferred member `ZZ99`, flag `product_unmapped` |
| Invoice on two dates | retain the first date for the invoice |
