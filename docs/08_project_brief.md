# Project Brief

## The business question

> **"Revenue fell 10%. Where did it come from?"**
>
> Which **branch × product × customer segment** drove the decline — and how much
> did each contributor cost us?

Verbally this is one scary sentence. Analytically it is four questions stacked:
*how* did the change happen, *where* is it concentrated, *why*, and *what does
it cost*.

## The decision it feeds

**Whose plan gets rewritten next quarter — retention, pricing, or
merchandising?**

This is the point of the whole exercise. A revenue decline does not need
"attention"; it needs to be converted into a small number of named owners with
quantified problems. If the analysis does not change who does what on Monday, it
has failed (Ch. 2, 30).

## Method (as specified, as executed)

| Step | Specification | Where it lives |
|---|---|---|
| 1 | Decompose by **mechanism** first: customers × frequency × basket size | `src/decompose.py` §1, `sql/04_mechanism.sql` |
| 2 | Then by **structure**: branch, category, segment, channel | `src/decompose.py` §2, `sql/05_structure.sql` |
| 3 | **Intersect**: branch × product × segment — the killer cross-cut | `src/decompose.py` §3, `sql/07_crosscut.sql` |
| 4 | An **evidential 5-Whys**: every "why" answered with a number, stopping at the actionable | `src/five_whys.py`, `docs/05_five_whys.md` |

Two rules were enforced mechanically rather than promised:

* the 5-Whys chain is **generated from tables**, so no "why" can become a
  narrative;
* the driver partition is **disjoint and audited** — `decompose.py` halts if the
  owned problems do not cover the decline exactly.

## The analyst's value, stated up front

> The waterfall turns one scary headline into four ranked department problems.

That is the bridge from descriptive to diagnostic (Ch. 24). Concretely, this
project converts

**"Revenue fell 10%."**

into

**"Supply Chain: −KSh 2.16M (41%). Retail Ops: −KSh 1.49M (29%). CRM: −KSh 0.97M
(19%). Pricing: −KSh 0.55M (11%). Every one with evidence, an owner, an expected
recovery and a review date."**

## Scope

| In scope | Out of scope |
|---|---|
| Six stores, eight categories, five lifecycle segments, two periods | Competitor data, macro data |
| Revenue, gross profit, margin, AOV, frequency, discount depth | Balance sheet, cash, working capital |
| Line-item grain; cohort-level retention | Individual customer lifetime value modelling |
| Availability evidence for the supply event | Supplier performance, lead times (recommended for capture) |

## Deliverables

| Artefact | Audience | File |
|---|---|---|
| Findings report (D → Diag → P → Presc) | Commercial director, store owners | `docs/04_findings_report.md` |
| Evidential 5-Whys | Whoever is being asked "why" | `docs/05_five_whys.md` |
| Recommendations register | Action owners | `docs/06_recommendations.md` |
| Data-quality report | Data/BI team | `docs/03_data_quality_report.md` |
| Dashboard specification | BI developer | `docs/07_dashboard_spec.md` |
| Executive brief (2 pp) | CEO / commercial director | `outputs/reports/Executive_Brief.pdf` |
| Boardroom deck (17 slides) | whoever is presenting | `outputs/reports/Revenue_Decline_Diagnostic.pptx` |
| Word report (21 pp) | the working team | `outputs/reports/Revenue_Decline_Diagnostic.docx` |
| PDF report (21 pp) | circulation | `outputs/reports/Revenue_Decline_Diagnostic.pdf` |
| Reproducible pipeline | Anyone who doubts a number | `src/run_pipeline.py` |
| Validation against ground truth | Skeptics (including future me) | `outputs/validation_report.md` |

## Success criteria

1. **The decision test** — the report names which plans get rewritten.
2. **The so-what test** — every observation has explanation → impact →
   recommendation.
3. **The baseline test** — no naked numbers; everything is against a like
   quarter or a target.
4. **The decomposition test** — the 10% headline is traced to drivers that sum
   to it.
5. **The honesty test** — facts and hypotheses are labelled; the unanswerable
   fifth why is declared, not filled in.
6. **The action test** — every recommendation has an owner, an expected impact
   and a review date (Ch. 30).

## How this differs from a dashboard project

A dashboard would have shown *that* revenue fell and *which* branches declined.
This project answers *why*, *how much it cost*, and *who should act* — and it
hands the monitoring job to a dashboard afterwards, with the targets the
analysis set (see `docs/07_dashboard_spec.md` §5).
