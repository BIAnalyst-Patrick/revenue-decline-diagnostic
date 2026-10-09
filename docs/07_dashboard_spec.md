# Dashboard Specification

A build-ready spec for the Power BI layer. The analysis is already done — this
document exists so that the dashboard **monitors what the analysis concluded**
instead of re-deriving it, and so that the numbers on the tiles obey the same
grain rules as the report (Ch. 4, 18, 25).

> **Read §0 before building anything.** The most common failure with a project
> like this is a beautiful dashboard that answers no question.

## 0. What this dashboard is and is not (Ch. 25)

| | This dashboard | The analysis (already done) |
|---|---|---|
| Job | monitor the KPIs the analysis identified, against targets | explain a change and support a decision |
| Question | "are we OK?" | "why, and what should we do?" |
| Cadence | monthly, always-on | one-off, on demand |
| Output | tiles, trends, exceptions | findings + recommendations, with owners |

The dashboard ships **after** the thinking. Every visual below exists because
the findings report cited it — nothing is here because it would look good.

## 1. Semantic model

Connect to `data/revenue_decline.sqlite` (SQLite connector, Import mode) or load
`data/processed/*.csv` directly.

```
dim_date (date_key) ──1:*──┐
dim_branch (branch_id) ─1:*┤
dim_product (product_id) ─1:*├── fact_sales_lines
dim_customer (customer_id) ─0:1 ┘
dim_date ─1:*── fact_stockouts ─*:1── dim_branch
                                └──*:1── dim_product
```

| Setting | Value |
|---|---|
| Relationship direction | single (dimension → fact) |
| `dim_date` | mark as date table |
| `customer_id` | keep the `UNKNOWN` member (do **not** filter it out of the model) |
| `dim_product` | includes the inferred member `ZZ99` / `Unclassified` |
| Storage mode | Import; the dataset is ~189k rows |

**Grain discipline:** `fact_sales_lines` is one row per line item. Never count
rows as "orders" — use `DISTINCTCOUNT(invoice_id)`.

## 2. Measures (DAX)

Create these in a dedicated `_Measures` table so they are easy to find.

```dax
Net Revenue       = SUM ( fact_sales_lines[net_revenue] )
Gross Profit      = SUM ( fact_sales_lines[gross_profit] )
Gross Margin %    = DIVIDE ( [Gross Profit], [Net Revenue] )

Orders            = DISTINCTCOUNT ( fact_sales_lines[invoice_id] )
Active Customers  = CALCULATE (
                        DISTINCTCOUNT ( fact_sales_lines[customer_id] ),
                        fact_sales_lines[customer_id] <> "UNKNOWN" )
Frequency         = DIVIDE ( [Orders], [Active Customers] )
AOV               = DIVIDE ( [Net Revenue], [Orders] )

Lines per Order   = DIVIDE ( COUNTROWS ( fact_sales_lines ), [Orders] )
Units per Order   = DIVIDE ( SUM ( fact_sales_lines[quantity] ), [Orders] )
Discount Depth %  = DIVIDE ( SUM ( fact_sales_lines[discount_amount] ),
                             SUM ( fact_sales_lines[gross_revenue] ) )
List Price / Unit = DIVIDE ( SUM ( fact_sales_lines[gross_revenue] ),
                             SUM ( fact_sales_lines[quantity] ) )

-- YoY (like quarter vs same quarter last year)
Net Revenue LY    = CALCULATE ( [Net Revenue], SAMEPERIODLASTYEAR ( dim_date[date] ) )
Net Revenue YoY % = DIVIDE ( [Net Revenue] - [Net Revenue LY], [Net Revenue LY] )
Net Revenue YoY K = [Net Revenue] - [Net Revenue LY]

-- share of the group's total decline (denominator is the GROUP total, not the slice)
Group Revenue YoY K = CALCULATE ( [Net Revenue YoY K], ALL ( dim_branch, dim_product ) )
Share of Decline %  = DIVIDE ( [Net Revenue YoY K], [Group Revenue YoY K] )

-- availability (from fact_stockouts; add a dedicated measure table join)
Shelf Availability % = AVERAGE ( fact_stockouts[in_stock] )
OOS Days             = CALCULATE ( COUNTROWS ( fact_stockouts ),
                                    fact_stockouts[in_stock] = 0 )
```

**Grain traps to avoid**

* `Active Customers` must exclude `UNKNOWN`, or ~1,500 anonymous lines inflate
  the count by exactly one customer and distort the frequency measure.
* `Share of Decline %` must use `ALL()` on the group dimensions; a slice-relative
  denominator makes every slice look like 100%.
* `Discount Depth %` uses **gross** revenue in the denominator. Net revenue
  would understate the rate.
* Do not use `AVERAGE(discount_pct)` — it weights every line equally. The
  correct measure is discount-amount ÷ gross-revenue.

## 3. Page-by-page build

### Page 1 — Executive summary (the only page the CEO opens)

| Visual | Fields | Notes |
|---|---|---|
| 4 KPI cards | Net Revenue, Gross Margin %, Frequency, AOV | each with a YoY delta and a target reference line |
| Waterfall | `decomp_mechanism_waterfall` (`component`, `effect`) | the headline chart from the report |
| Bar chart | Store, `Net Revenue YoY K` | sorted ascending; the two problem stores fall out instantly |
| Card | Share of decline in the top two stores | 71% — the "this is two events, not a trend" tile |
| Table | `decomp_driver_partition` | owner, KSh, % of decline, expected recovery |

### Page 2 — Mechanism (how the change happened)

* Decomposition tree: `Net Revenue` → `Active Customers`, `Frequency`, `AOV`.
* Line: `Customers`, `Frequency`, `AOV` indexed to the base quarter = 100
  (reproduces `02_mechanism_identity.png`).
* Card group showing the log-mean attribution and the sensitivity band.
* Slicers: period, region, branch, category, segment, channel.

### Page 3 — Structure (where it happened)

* Matrix: rows = store, columns = category, values = `Net Revenue YoY %`, with
  conditional formatting (red-to-green, 0-centred). This is the heat map.
* Pair of bar charts: category `Net Revenue YoY K` **and** `Net Revenue YoY %`
  side by side — the denominator lesson, made visual (Ch. 27).
* Channel breakdown as a secondary small multiple.

### Page 4 — Segments & retention

* Cohort matrix: Q3 2025 segment (rows) × Q3 2026 segment (columns), values =
  distinct customers, plus a `Lapsed` column.
* Bar: return rate by Q3 2025 segment, against the group line (83.8%).
* Scatter: revenue per customer vs orders per customer, one point per segment.
* Card: new customers acquired, and the total decline attributed to the "New"
  segment's growth (it is a **gain**, so colour it that way).

### Page 5 — Operations & availability

* Heat map: date × SKU for `fact_stockouts` where `in_stock = 0` (this is the
  single most useful operational visual in the model).
* Line: 7-day rolling Personal Care revenue at Mombasa, current vs prior year
  (reproduces `08_stockout_timeline.png`).
* Cards: `Shelf Availability %`, `OOS Days`, and the KSh lost.
* Slicers: branch, SKU, category.

### Page 6 — Pricing & mix

* Dumbbell chart: prior-year vs current discount depth by category
  (reproduces `09_discount_depth.png`).
* Bar: list price per unit by category, prior vs current.
* Waterfall: category mix share, prior → current (mix shift).
* Card: estimated extra discount given away this quarter.

### Page 7 — Detail / drill-through

* Table at line-item grain for the selected store × category × segment cell.
* Drill-through targets: store, category, SKU, segment.
* Export enabled for analysts; hidden from the executive and operations roles.

## 4. Interaction, roles and operations

| Item | Setting |
|---|---|
| Default slicers | period (single select), region |
| Sync slicers | page 1 ↔ pages 3-6 for period; page 3 ↔ page 7 for store/category |
| Row-level security | by `dim_branch[region]`: Coast / Nairobi / Rift Valley / Nyanza → store managers |
| Bookmarks | "Headline view" (exec) and "Driver view" (analyst) |
| Refresh | monthly, after the POS close; the pipeline in `src/run_pipeline.py` regenerates the model inputs |
| Data-quality tile | a card showing unattributed revenue % — visible, so the coverage limit never disappears from view |

## 5. Targets to set on page 1

The recommendations register defines the targets; put them in the model so the
tiles can show red/amber/green rather than a bare number.

| KPI | Baseline (Q3 2025) | Target | Owner |
|---|---:|---:|---|
| Orders per customer | 5.44 | ≥ 5.44 | CRM / Loyalty |
| Hero SKU shelf availability (Mombasa) | 9.5% in incident | > 99% | Supply Chain |
| Thika Road frequency YoY | −23.7% | > 0% | Retail Operations |
| Beverage discount depth | 18.85% of gross | ≤ 5.79% | Pricing |
| Gross margin | 19.95% | ≥ 19.95% | Finance |

## 6. Acceptance test before publishing

Ask these five questions of the finished dashboard (Ch. 25, 30). If any answer
is "no", the dashboard is decoration:

1. Can a manager see, on page 1, **which two stores** caused the decline and
   **who owns each**?
2. Does every tile carry a comparison (YoY, target, or both)? No naked numbers.
3. Does the mechanism page distinguish "fewer customers" from "fewer trips"?
4. Is the unattributed-revenue limitation visible somewhere on the report?
5. For each red tile, is there a named owner and a review date in
   `docs/06_recommendations.md`?

> The uncomfortable test from Ch. 25: if the dashboard's consumers make the same
> decisions they made before it existed, it is decoration.
