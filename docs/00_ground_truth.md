# Ground Truth — what was actually built into the data

> **Read this AFTER attempting the analysis.** It is the answer key for
> `docs/04_findings_report.md`. It exists because the dataset is simulated from
> a known mechanism (`src/config.py` → `STORY`, `MIGRATION`), which means the
> diagnostic can be *graded* rather than merely presented — see
> `src/validate_against_truth.py` and `outputs/validation_report.md`.

Simulation seed: **20260914** · Regenerate with `python3 src/run_pipeline.py`  
Every figure quoted in this document reflects that seed. The generated
`docs/04_findings_report.md` and `docs/06_recommendations.md` recompute
themselves, so they can never drift.

---

## 1. The business

**Mavuno Home & Care** — a six-store household, personal-care and grocery
retailer in Kenya (three Nairobi stores, plus Nakuru, Mombasa and Kisumu).

| | Value |
|---|---|
| Base period | Q3 2025 (2025-07-01 → 2025-09-30) |
| Comparison period | Q3 2026 (2026-07-01 → 2026-09-30) |
| Grain of the fact table | one line item on one customer receipt |
| Scale | ~195k line items, ~55k invoices, ~6.4k customers, 39 SKUs, 8 categories |

Comparing **like quarters** is deliberate: it neutralises seasonality (Ch. 12)
by construction rather than by adjustment.

## 2. The designed headline

The mechanism identity was targeted at:

```
Revenue = Customers x Frequency x AOV
0.896   =   1.055   x   0.886    x  0.959        ->  -10.4%
```

| Mechanism | Design target | Realised in the data | Recovered by the analysis? |
|---|---:|---:|---|
| Active customers | +5.5% | **+5.5%** | yes |
| Orders per customer | −11.4% | **−11.4%** | yes |
| Average order value | −4.1% | **−4.5%** | yes |
| **Net revenue** | **−10.0%** | **−10.7%** | yes |

Gross margin was designed to compress (deeper discounts + mix shift away from
high-margin Personal Care); the realised move is 19.95% → 18.57%, so gross
profit falls faster than revenue. A revenue-only analysis would miss this.

## 3. The four things that were put in the data

### D1 — Supply failure at Mombasa Nyali (the dominant driver)

* **What:** the two hero Personal Care SKUs (`PC01` Bath Soap 800g, `PC02`
  Shampoo 400ml) were taken off the shelf for **six weeks**, 2026-08-10 →
  2026-09-20, at store `BR05`.
* **How strong:** designed shelf availability inside the window was
  `hero_availability = 0.10` and `category_availability = 0.62` for the rest of
  the category.
* **Second-order effect (deliberate):** affected trips lost non-Personal-Care
  lines too (`spillover_line_factor = 0.68`) — the stock-out removed the reason
  for the trip, so the whole basket shrank.
* **Consequence:** Personal Care at that store falls ~34%, but the store as a
  whole falls ~27%, and the largest single *cells* of the group decline are in
  Groceries and Baby & Kids — categories that were never out of stock.

This is the design's main teaching point: **the cost of a stock-out is not the
missing product's revenue.** Measuring only the affected category understates
the event by roughly 4.8x.

### D2 — Store access at Thika Road

* `BR03` lost footfall for the whole quarter: `branch_footfall_factor = 0.80`
  applied to visits in Q3 2026 only.
* It produces a distinctive signature: **frequency collapses, basket does not.**
  Customers +6.9%, frequency −23.7%, AOV −0.3%.

### D3 — A beverage price war

* Discount depth was deepened on `Beverages` (+13.0pp), and more mildly on
  `Groceries` (+4.5pp) and `Household & Cleaning` (+3.0pp).
* List prices were simultaneously inflated `price_inflation = 4.5%` (cost
  inflation 3.0%), which is why AOV can fall *while* prices rise.
* Beverages end up the steepest percentage decline in the chain (−20.3%).

### D4 — Chain-wide frequency erosion (the residual)

* Every established segment shopped less often:
  `frequency_factor` = Loyal 0.92, Regular 0.94, At-Risk 0.88, Hibernating 0.97.
* No single local cause was injected for this — it is meant to be the honest
  residual that the analysis must not over-explain.

## 4. Customer migration (the retention story)

The same customer IDs appear in both periods, so cohort behaviour is
measurable. Each Q3 2025 segment migrates as follows:

| From (Q3 2025) | Loyal | Regular | At-Risk | Hibernating | Lapsed |
|---|---:|---:|---:|---:|---:|
| Loyal | 0.70 | 0.17 | 0.06 | 0.03 | 0.04 |
| Regular | 0.16 | 0.68 | 0.09 | 0.03 | 0.04 |
| At-Risk | — | 0.07 | 0.55 | 0.12 | 0.26 |
| New | — | 0.30 | 0.33 | 0.13 | 0.24 |
| Hibernating | — | — | 0.06 | 0.44 | 0.50 |

Plus a new-customer inflow sized at `1.45 x` the Q3 2025 "New" cohort — which
is *why* the headline customer count rises while the business shrinks.

**Deliberate nuance:** customer-level retention stays high (83.8% return rate;
Loyal 96.3%). The loss is in **trips per customer**, not in customers. An
analysis that reports "a retention crisis" has mis-read the mechanism.

## 5. Data-quality issues deliberately planted

The raw extract is imperfect on purpose so that cleaning has real work
(Ch. 13–17). All are enumerated with counts in
`data/raw/dq_issue_manifest.csv` and detected in
`docs/03_data_quality_report.md`: duplicate lines, impossible quantities,
out-of-period dates, NULL discounts, non-canonical category labels, anonymous
walk-ins (~0.8% of revenue), unmapped SKUs, and one invoice reused on two dates.

**Sampling is disjoint across issue types**, so the "planted" and "detected"
counts in the quality report must match exactly. A divergence there is a real
bug, not a rounding artefact.

## 6. What is deliberately NOT in the data

* **No procurement, supplier, or lead-time data.** So the *fifth* why (why the
  stock ran out) is unanswerable by design. The correct analyst behaviour is to
  stop and request the data — not to invent a cause. `validate_against_truth.py`
  deliberately does **not** check for an explanation of the stock-out, because a
  tool that "passes" an unanswerable question is worse than no tool.
* **No competitor, pricing-elasticity, or footfall-count data.** So the causal
  claims about the price war and the road-works are labelled *hypotheses
  consistent with the data*, never facts (Ch. 26).
* **Kisumu Lakefront (−11.5%) has no injected driver.** It is the control that
  tests whether the analysis will honestly report an unexplained movement
  instead of manufacturing a cause for it.

## 7. Grading

`src/validate_against_truth.py` asserts 14 falsifiable claims — the realised
headline and mechanism moves, the identity of the worst and second-worst
stores, the worst category by percentage, the low shelf availability, the
retention level, the margin compression, the primacy of the supply driver, and
that the driver partition sums to 100%. It exits non-zero if any fail, so the
pipeline cannot silently ship a broken diagnosis.
