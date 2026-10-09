# Methodology

Why the analysis is built this way, and where its limits are. Read this before
challenging a number — the challenge may already be answered here.

## 1. Decision first, data second (Ch. 2, 31)

The brief was not "analyse revenue". It was:

> **Which branch × product × customer segment drove the decline, and how much
> did each contributor cost us?**
> Decision it feeds: **whose plan gets rewritten — retention, pricing, or
> merchandising.**

That framing dictates everything downstream. Because the decision is about
*who owns the fix*, the analysis must end in **disjoint, owned** quantities —
not overlapping slices that a reader has to reconcile.

## 2. Order of attack: mechanism → structure → intersect (Ch. 22)

```
Step 1  MECHANISM   Revenue = Customers × Frequency × Average order value
                    -> explains HOW the change happened

Step 2  STRUCTURE   branch | category | segment | channel
                    -> explains WHERE it happened

Step 3  INTERSECT   store × category × segment
                    -> finds the few cells that actually matter
```

Doing structure first (the usual instinct) produces "Beverages is down 20%"
without explaining whether the cause is fewer buyers, fewer trips, or smaller
baskets — three different departments. Mechanism first is what makes the
handover possible.

## 3. Comparing like with like

Both periods are **calendar Q3**. Seasonality (Ch. 12) is therefore neutralised
by design rather than by statistical adjustment. Every claim in the report is a
like-for-like comparison, and where a sub-window is used (the stock-out window)
the *same calendar days of the prior year* provide the baseline.

## 4. Attributing the mechanism change: log-mean Divisia

The identity is multiplicative, so a naive "% of total" split is wrong. For
`R = C · F · A`, the contribution of each factor is

```
contribution_i = L(R₀, R₁) · ln(x₁ᵢ / x₀ᵢ)        where  L(a,b) = (b − a) / (ln b − ln a)
```

Properties that matter:

* the three contributions **sum exactly** to the total revenue change;
* the attribution is **symmetric** — it does not depend on the order in which
  you multiply the factors, which the naive sequential method does;
* it is scale-consistent, so comparing a KSh 8M store with a KSh 12M store is
  legitimate.

**Sensitivity.** The report also computes the sequential decomposition in both
possible orders and reports the resulting *band*
(`decomp_mechanism_sensitivity.csv`). The frequency effect is the largest under
every ordering, so the headline ranking is robust to the method. That is the
relevant claim — not that one method is "correct".

## 5. The driver partition — disjoint by construction

The four owned problems (section 6.3 of the findings report) come from assigning
every `store × category × segment` cell to **exactly one** owner:

| Driver | Rule |
|---|---|
| D1 Supply Chain & Merchandising | all cells at Mombasa Nyali |
| D2 Retail Operations | all cells at Thika Road |
| D3 Pricing & Category Management | `Beverages` cells elsewhere |
| D4 CRM / Loyalty & Assortment | every remaining cell |

Consequences, stated openly:

* the four bars **add up to the decline** (plus a small reconciliation line for
  the ~0.8% of revenue with no customer identifier);
* this is an *ownership* attribution, not a causal one. Mombasa's residual
  frequency erosion is booked to D1 because that is who can act on the store
  this quarter. A different rule would move money between owners — which is why
  the rule is written down instead of implied;
* `src/decompose.py` **hard-fails** if the partition does not cover the
  attributed revenue exactly, so the table can never quietly stop adding up.

## 6. Facts, hypotheses, uncertainty (Ch. 26)

Three tiers are used explicitly in `docs/04_findings_report.md` §8:

1. **Fact** — measured in this data ("revenue fell 10.7%").
2. **Hypothesis** — labelled as such, with the observation it is consistent with
   and the data that would confirm it ("the stock-out caused the basket erosion:
   the two co-move exactly in time, but no causal test was run").
3. **Uncertainty** — declared limits ("0.76% of revenue has no customer
   identifier; this segment conclusion reconciles to 99.24%").

The most consequential application: **the fifth why is unanswerable here.** No
supplier, lead-time or replenishment data exists in the extract. The correct
output is a data-capture recommendation, not a plausible-sounding cause.

## 7. Tool choices, and why (Ch. 29)

| Layer | Tool | Reason |
|---|---|---|
| Warehouse | **SQLite + hand-written SQL** (`sql/*.sql`) | row-level logic, joins and window functions are the interview-relevant core skill; every aggregate is reproducible from a named query |
| Attribution maths | **Python** (`src/decompose.py`) | log-mean Divisia and disjoint partitioning are clearer as code than as SQL |
| Simulation | **Python + numpy** | reproducible, seeded, and the generating mechanism is auditable |
| Reporting | **Markdown generated from the numbers** | prose cannot drift from the data |
| Dashboard | **spec only** (`docs/07_dashboard_spec.md`) | Power BI is the delivery layer, built *after* the thinking (Ch. 25) |

The deliberate split: SQL answers *what the numbers are*, Python answers *how
the change decomposes*, and the documents never contain a hand-typed figure.

## 8. Known limitations

1. **Simulated data.** The mechanism is known and documented, which enables
   validation but means the absolute magnitudes are illustrative.
2. **Unattributed revenue.** ~0.76% of revenue carries no customer ID, so
   segment-level conclusions reconcile to ~99.24%.
3. **Attributed-only mechanism maths.** Customers and frequency are computed on
   lines with a customer identifier, because the maths is impossible otherwise.
   The waterfall therefore starts from the attributed subtotal.
4. **No causal identification.** Nothing here is a controlled experiment. The
   road-works and price-war claims are labelled hypotheses.
5. **Kisumu Lakefront's −11.5% is unexplained** and reported as such.
6. **Single-period comparison.** Two quarters, one comparison. A three-year
   pattern would be stronger evidence (Ch. 21).
