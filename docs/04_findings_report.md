# Findings Report — Why group revenue fell

**Company:** Mavuno Home & Care  
**Period compared:** Q3 2026 vs Q3 2025 (like-for-like quarter, so seasonality is controlled by construction)  
**Prepared:** 2026-10-05  
**Reproduce with:** `python3 src/run_pipeline.py`

---

## 1. The decision this supports

> **Whose plan gets rewritten next quarter — retention, pricing, or merchandising?**

The analysis is only worth reading to the extent it answers that. It does, in section 6, with a number and an owner attached to each answer.

## 2. Executive summary

**Group net revenue fell KSh 5.21M (10.7%) to KSh 43.65M, and gross profit fell KSh 1.63M — worse than the revenue headline, because gross margin compressed 1.38pp to 18.57%.**

Four findings, ranked by how much of the decline they own:

1. **We did not lose customers — we lost trips and basket size.** Active customers rose +5.5%, but orders per customer fell -11.4% and average order value fell -4.5%. The engine failed, not the funnel.
2. **Two of six stores carry 71% of the decline.** Mombasa Nyali (-27.0%) and Thika Road (-18.7%) are not a chain-wide problem; they are two local events.
3. **The biggest single cause is a supply failure with a date.** Two hero Personal Care SKUs sat off the shelf for six weeks at Mombasa Nyali (9.5% availability). It cost KSh 2.16M, and **KSh 1.71M of that was not Personal Care revenue at all** — it was baskets that never got started.
4. **Discounting, not pricing, is the second lever.** List prices rose +4.3% yet AOV still fell: discount depth went from 4.80% to 7.82% of gross, giving away roughly an extra KSh 1.43M in the quarter.

## 3. What the data is, and what it is not

Line-item grain: **one row = one line item on one customer receipt** — 195,224 lines across 55,431 invoices in the two quarters, plus a separate branch x SKU x day shelf-availability table that makes the supply event provable.

Declared limits (these are limits on the *conclusions*, not footnotes):

- **0.76% of revenue has no customer identifier** (KSh 0.70M of anonymous walk-ins). Segment-level conclusions therefore reconcile to 99.24%, not 100%. The reconciliation appears as its own line in section 6 rather than being hidden in an 'Other' bucket.
- **The dataset is simulated** and its generating mechanism is documented in `docs/00_ground_truth.md`. That is deliberate: it lets the analysis be graded (see `outputs/validation_report.md` — 14/14 checks passed).
- **No procurement, lead-time or supplier data exists in this extract.** Section 8 therefore stops rather than speculating.

## 4. Descriptive — what happened

| Metric | Q3 2025 | Q3 2026 | Change |
|---|---:|---:|---:|
| Net revenue | KSh 48.86M | KSh 43.65M | **-10.7%** |
| Gross profit | KSh 9.68M | KSh 8.04M | -16.9% |
| Gross margin | 19.95% | 18.57% | -1.38pp |
| Active customers | 5,265 | 5,555 | +5.5% |
| Orders | 28,618 | 26,764 | -6.5% |
| Orders per customer | 5.44 | 4.82 | -11.4% |
| Average order value | KSh 1,694 | KSh 1,619 | -4.5% |
| Lines per order | 3.59 | 3.40 | -5.2% |
| List price per unit | KSh 312 | KSh 326 | +4.3% |

![Headline waterfall](../outputs/figures/01_headline_waterfall.png)

Revenue is not profit: gross profit fell 16.9% against a 10.7% revenue fall. Every recommendation below is therefore priced in gross profit, not just revenue.

## 5. Diagnostic, part 1 — the mechanism

`Revenue = Customers x Frequency x Average order value`

| Driver | Effect on revenue | YoY move |
|---|---:|---:|
| Customers | KSh 2.46M | +5.5% |
| Orders per customer | KSh -5.53M | -11.4% |
| Average order value | KSh -2.10M | -4.5% |
| **Total** | **KSh -5.21M** | **-10.7%** |

Attribution is log-mean Divisia, so the ranking does not depend on the order you multiply in. The sequential-order sensitivity band is: customers KSh 2.26M to KSh 2.67M; frequency KSh -5.81M to KSh -5.26M; aov KSh -2.17M to KSh -2.03M. The frequency effect is the largest under every ordering — that is the robust part of the result.

![Mechanism identity](../outputs/figures/02_mechanism_identity.png)

The critical read: **customers grew +5.5%, so any report that stops at 'fewer customers' is wrong.** Acquisition is working. What failed is repeat behaviour.

## 6. Diagnostic, part 2 — the structure, and who owns what

### 6.1 The same change, sliced four ways

**By store**

| Rank | Slice | Revenue change | YoY | Share of group decline |
|---:|---|---:|---:|---:|
| 1 | Mombasa Nyali | KSh -2.18M | -27.0% | 41.9% |
| 2 | Thika Road | KSh -1.50M | -18.7% | 28.9% |
| 3 | Kisumu Lakefront | KSh -0.69M | -11.5% | 13.2% |
| 4 | Town Centre | KSh -0.39M | -3.4% | 7.4% |
| 5 | Westlands | KSh -0.26M | -2.8% | 5.0% |
| 6 | Nakuru CBD | KSh -0.19M | -3.0% | 3.6% |

**By category**

| Rank | Slice | Revenue change | YoY | Share of group decline |
|---:|---|---:|---:|---:|
| 1 | Groceries | KSh -1.60M | -13.1% | 30.7% |
| 2 | Beverages | KSh -1.08M | -20.3% | 20.7% |
| 3 | Household & Cleaning | KSh -0.82M | -11.3% | 15.7% |
| 4 | Personal Care | KSh -0.65M | -7.9% | 12.4% |
| 5 | Baby & Kids | KSh -0.46M | -6.7% | 8.8% |
| 6 | Dairy & Eggs | KSh -0.37M | -8.0% | 7.0% |
| 7 | Fresh Produce | KSh -0.15M | -4.7% | 2.9% |
| 8 | Bakery | KSh -0.09M | -6.9% | 1.7% |
| 9 | Unclassified | KSh -0.00M | -27.9% | 0.0% |

**By customer segment**

| Rank | Slice | Revenue change | YoY | Share of group decline |
|---:|---|---:|---:|---:|
| 1 | Loyal | KSh -3.03M | -15.2% | 58.2% |
| 2 | Regular | KSh -2.52M | -14.0% | 48.4% |
| 3 | At-Risk | KSh -0.85M | -14.2% | 16.3% |
| 4 | Hibernating | KSh -0.04M | -2.9% | 0.8% |
| 5 | New | KSh 1.28M | +40.7% | -24.5% |

**By channel**

| Rank | Slice | Revenue change | YoY | Share of group decline |
|---:|---|---:|---:|---:|
| 1 | In-store | KSh -4.54M | -10.8% | 87.1% |
| 2 | Online | KSh -0.67M | -9.9% | 12.9% |

![Store waterfall](../outputs/figures/03_branch_waterfall.png)

![Category decline](../outputs/figures/05_category_decline.png)

Note how the two panels of the category chart disagree: Groceries is the largest **absolute** loss, Beverages the largest **percentage** loss. Both are true; either alone is a misleading brief.

### 6.2 The intersection — which store x product x segment

![Store x category heat map](../outputs/figures/04_branch_category_heatmap.png)

The decline is concentrated, not diffuse: the worst 8 cells (store x category x segment) account for 23.5% of the total.

| # | Cell | Revenue change | YoY | % of group decline |
|---:|---|---:|---:|---:|
| 1 | Mombasa Nyali | Groceries | Regular | KSh -0.28M | -33.6% | 5.4% |
| 2 | Mombasa Nyali | Groceries | Loyal | KSh -0.23M | -29.6% | 4.4% |
| 3 | Mombasa Nyali | Personal Care | Regular | KSh -0.22M | -41.1% | 4.2% |
| 4 | Mombasa Nyali | Baby & Kids | Loyal | KSh -0.21M | -42.0% | 4.0% |
| 5 | Mombasa Nyali | Personal Care | Loyal | KSh -0.19M | -35.9% | 3.6% |
| 6 | Mombasa Nyali | Baby & Kids | Regular | KSh -0.17M | -34.8% | 3.3% |
| 7 | Thika Road | Personal Care | Loyal | KSh -0.17M | -30.9% | 3.3% |
| 8 | Mombasa Nyali | Household & Cleaning | Regular | KSh -0.17M | -37.0% | 3.2% |

**The counter-intuitive result:** the single largest cell is not Personal Care — it is Mombasa Nyali | Groceries | Regular. At Mombasa Nyali, every category fell 25-40% because the stock failure removed the reason for the trip and the whole basket shrank with it. If you had only measured the affected category, you would have understated this event by roughly 4.8x.

### 6.3 The four ranked department problems

![Driver partition](../outputs/figures/10_driver_partition.png)

Each store x category x segment cell is assigned to **exactly one** owner, so these bars add up to the whole decline with no double counting.

| Rank | Owner | Problem | Cost | Share |
|---:|---|---|---:|---:|
| 1 | Supply Chain & Merchandising | Two hero Personal Care SKUs out of stock for six weeks at Mombasa Nyali; the damage spread to whole baskets | KSh -2.16M | 41.4% |
| 2 | Retail Operations (Thika Road) | Thika Road footfall cut for the full quarter — visits per customer well below every other store | KSh -1.49M | 28.6% |
| 3 | CRM / Loyalty & Assortment | Residual: fewer trips per customer and slimmer baskets right across the chain | KSh -0.97M | 18.7% |
| 4 | Pricing & Category Management | Beverage promotional depth deepened sharply outside the two affected stores | KSh -0.55M | 10.5% |
| — | Data / POS capture | Reconciliation: revenue with no customer identifier (anonymous walk-ins) | KSh -0.04M | 0.7% |

### 6.4 The signatures are different, so the fixes must be too

| | Customers | Frequency | Basket value | Diagnosis |
|---|---:|---:|---:|---|
| Mombasa Nyali | +7.0% | -11.7% | -22.6% | lost trips **and** basket |
| Thika Road | +6.9% | -23.7% | -0.3% | lost trips only |
| Group | +5.5% | -11.4% | -4.5% | frequency-led |

That table is the single most useful thing in this report. A **basket** problem needs merchandising; a **traffic** problem needs access, hours and local marketing. Applying one fix to both stores would waste a quarter.

## 7. Diagnostic, part 3 — the evidential 5-Whys

Full chain: [`docs/05_five_whys.md`](05_five_whys.md). Condensed:

**Why 1 — Why did group revenue fall?**  
Net revenue fell KSh 5.17M (10.66%), from KSh 48.49M to KSh 43.32M. Volumes, not customers: active customers ROSE +5.51% while orders fell 6.48%.  
*Source: `mechanism_by_period.csv` · No — this is the question, not an answer*

**Why 2 — Customers grew but orders fell. Why?**  
Orders per customer fell -11.36% (5.44 -> 4.82 trips), and average order value fell -4.48% (KSh 1,694 -> KSh 1,619). Log-mean attribution puts KSh 2.46M of growth on new customers, KSh 5.53M against frequency and KSh 2.10M against basket value.  
*Source: `mechanism_by_period.csv, decomp_mechanism_waterfall.csv` · Partly — it names the mechanism (repeat visits, not acquisition)*

**Why 3 — Where is the frequency and basket loss concentrated?**  
Two of six stores explain 71.3% of the entire group decline: Mombasa Nyali (KSh -2.18M, -27.0%) and Thika Road (KSh -1.50M, -18.7%). Frequency fell -11.7% at Mombasa and -23.7% at Thika Road, versus -11.4% for the group.  
*Source: `structure_by_branch.csv, structure_branch_mechanism.csv` · Yes for the stores — but not yet for the cause*

**Why 4 — Why did Mombasa Nyali lose so much more than the rest of the chain?**  
Its two hero Personal Care SKUs were off the shelf for six weeks: 76 out-of-stock days out of 84 observations (9.5% shelf availability, first gap 2026-08-10). Personal Care revenue at that store fell -34.2% — but Mombasa's average order value also fell -22.6% (KSh 1,724 -> KSh 1,334) against a group AOV change of -4.5%. The missing items cost the whole basket, not just the category.  
*Source: `fact_stockouts, stockout_incident_vs_rest.csv, structure_category_mechanism.csv` · Yes — this is a supply-chain event with a date and a store*

**Why 5 — Why were the SKUs unavailable for six weeks?**  
The data shows WHAT happened (a 40-day gap on the worst single SKU, longest consecutive outage 33 days) but cannot show WHY. Replenishment, supplier and lead-time data are not in this dataset. Candidate causes — single-sourced supply, no safety stock, a mis-set reorder point — are HYPOTHESES and must be labelled as such until procurement data is pulled.  
*Source: `fact_stockouts (WHY is absent by design)` · Stop here: the actionable unit is 'restore stock and dual-source', not 'explain the universe'*

![Stock-out timeline](../outputs/figures/08_stockout_timeline.png)

The availability panel is the whole reason this report can say 'supply failure' instead of 'probably supply'. Without the shelf-availability table, 9.5% availability for 76 days would be a guess.

## 8. Facts, hypotheses, and the edge of what we know

| Statement | Tier |
|---|---|
| Revenue fell 10.7%; gross profit fell 16.9% | **Fact** (measured) |
| Two stores explain 71% of the decline | **Fact** (measured) |
| Hero SKUs were 9.5% available for 76 days at Mombasa Nyali | **Fact** (measured) |
| The stock-out *caused* the basket erosion at that store | **Hypothesis — consistent with**, not proven: the two co-move exactly in time, but no causal test was run |
| Single-sourcing / no safety stock caused the stock-out | **Hypothesis** — no procurement or lead-time data in this extract |
| Thika Road's decline is due to the road-works | **Hypothesis** — the frequency-only signature is consistent with an access problem, and no other local factor is recorded |
| Kisumu Lakefront's -11.5% | **Unexplained.** Flagged, not back-filled with a story |
| 855 customers who shopped in Q3 2025 did not return | **Fact**, but 83.8% did return — churn is not the problem |

## 9. Predictive — the run-rate if nothing changes

If Q3's frequency and basket levels persist, the annualised revenue impact is roughly **KSh -20.83M** (KSh -5.21M x 4). That is a **run-rate, not a forecast**: it assumes the Mombasa incident does not repeat (it should be fixed) and ignores Q4 seasonality, which is typically stronger. Treat it as the size of the hole, not the shape of the year.

![Segment waterfall](../outputs/figures/06_segment_waterfall.png)

Every established segment shrank; the only growth came from 1,145 new customers worth KSh 1.28M. Buying growth is not a strategy while the existing base is contracting.

## 10. Prescriptive — what to do

Full register with owners, expected impact and review dates: [`docs/06_recommendations.md`](06_recommendations.md).

| # | Action | Owner | Expected gross-profit recovery | Review |
|---:|---|---|---:|---|
| 1 | Restore stock and dual-source the two hero SKUs | Supply Chain | KSh 0.28M – KSh 0.40M | +30 days |
| 2 | Rebuild the Mombasa basket (substitutes, adjacency, staff script) | Merchandising | KSh 0.03M | +45 days |
| 3 | Thika Road access recovery plan with the landlord and county | Retail Operations | KSh 0.17M | +60 days |
| 4 | Cap beverage discount depth back toward 4.8% | Pricing | KSh 0.27M | +21 days |
| 5 | Convert the frequency leak: win-back + second-purchase nudge | CRM / Loyalty | KSh 0.09M | +90 days |
| 6 | Capture a customer ID on every transaction; start logging supplier lead times | Data / POS | enables the next diagnosis | next quarter |
| | **Total expected gross-profit recovery** | | **KSh 0.85M – KSh 0.97M** | vs a KSh 1.63M gross-profit decline |

Each action has an owner, an expected impact and a review date — the test from Ch. 30. **Impacts are gross-profit recovery, not revenue recovered:** volume, traffic and basket actions are converted at the blended Q3 FY2026 gross margin (18.57%), while the pricing action is a discount stop and converts at near-full value. Together they recover KSh 0.85M–KSh 0.97M, about 52–59% of the KSh 1.63M of gross profit the quarter lost — deliberately short of the whole hole, because no plan recovers all of it in one quarter. The follow-up question that closes the loop: **did any of it change a decision?**

---

## Appendix — the numbers behind every claim

| Source | Contains |
|---|---|
| `outputs/kpis.json` | every headline figure in this report, machine-readable |
| `outputs/tables/mechanism_by_period.csv` | the mechanism identity inputs |
| `outputs/tables/decomp_mechanism_waterfall.csv` | the waterfall, with attribution method |
| `outputs/tables/decomp_mechanism_sensitivity.csv` | order-dependence band |
| `outputs/tables/decomp_driver_partition.csv` | the four owned problems |
| `outputs/tables/crosscut_branch_category_segment_full.csv` | the whole intersection grid |
| `outputs/tables/cohort_retention_by_segment.csv` | who came back |
| `outputs/tables/stockout_*.csv` | the supply evidence |
| `outputs/validation_report.md` | the analysis graded against the ground truth |
| `docs/03_data_quality_report.md` | what was wrong with the raw extract |
