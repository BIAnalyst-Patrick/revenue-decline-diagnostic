# Project 1 — Revenue Decline Diagnostic

> **"Revenue fell 10%. Where did it come from?"**
> Which **branch × product × customer segment** drove the decline, and how much
> did each contributor cost us?
>
> **Decision it feeds:** whose plan gets rewritten — retention, pricing, or
> merchandising?

A complete diagnostic analytics project on a simulated six-store Kenyan
retailer (**Mavuno Home & Care**): raw POS extract → cleaned star schema in SQL
→ mechanism/structure/intersection decomposition → evidential 5-Whys → ranked,
owned recommendations → validated against a known ground truth.

**Read this first:** [`docs/04_findings_report.md`](docs/04_findings_report.md)

---

## The headline result

| | Q3 2025 | Q3 2026 | Change |
|---|---:|---:|---:|
| Net revenue | KSh 48.86M | KSh 43.65M | **−10.7%** |
| Gross profit | KSh 9.68M | KSh 8.04M | **−16.9%** |
| Gross margin | 19.95% | 18.57% | −1.38pp |
| Active customers | 5,265 | 5,555 | **+5.5%** |
| Orders per customer | 5.44 | 4.82 | **−11.4%** |
| Average order value | KSh 1,694 | KSh 1,619 | **−4.5%** |

**The one-line answer:** we did not lose customers — we lost trips and basket
size, and **two of six stores carry 71% of the decline**.

## One headline → four ranked, owned problems

Each store × category × segment cell is assigned to exactly one owner, so the
bars add up to the whole −KSh 5.21M with no double counting.

| Rank | Owner | Problem | Cost | Share |
|---:|---|---|---:|---:|
| 1 | Supply Chain & Merchandising | Two hero Personal Care SKUs out of stock six weeks at Mombasa Nyali (9.5% shelf availability); the damage spread to whole baskets | −KSh 2.16M | 41% |
| 2 | Retail Operations | Thika Road footfall cut for the quarter — a pure traffic problem (frequency −23.7%, basket flat) | −KSh 1.49M | 29% |
| 3 | CRM / Loyalty & Assortment | Residual: fewer trips and slimmer baskets across the chain | −KSh 0.97M | 19% |
| 4 | Pricing & Category Management | Beverage discount depth deepened +13pp outside the two affected stores | −KSh 0.55M | 11% |
| — | Data / POS capture | Reconciliation: revenue with no customer identifier | −KSh 0.04M | 0.7% |

The counter-intuitive finding worth the whole project: at Mombasa Nyali, **only
KSh 0.45M of the KSh 2.16M damage is Personal Care revenue.** The other
KSh 1.71M is baskets that were never started — measuring only the affected
category would have understated the event by ~4.8x.

## What makes this more than a chart pack

| Property | How it is enforced |
|---|---|
| Every number is reproducible | `python3 src/run_pipeline.py` regenerates data → warehouse → analysis → documents → figures |
| The prose cannot drift from the data | the findings report and recommendations are **generated** from `outputs/kpis.json` |
| The attribution is not order-dependent | log-mean Divisia, with a sequential sensitivity band reported alongside |
| The ownership table cannot silently break | `decompose.py` hard-fails if the driver partition doesn't cover the decline exactly |
| The analysis is graded, not just presented | `src/validate_against_truth.py` asserts 14 falsifiable claims — **14/14 pass** |
| Data quality is proven, not assumed | 9 planted defect classes, all detected; grain and referential-integrity checks return 0 failures |
| The unanswerable is declared | the 5th why (why the stock ran out) stops at a data-capture recommendation instead of a guess |

## Layout

```
project-1-revenue-decline-diagnostic/
├── README.md                     ← you are here
├── PROJECT_BRIEF.md              short pointer to the full brief
├── docs/
│   ├── 00_ground_truth.md        the sealed answer key (read after)
│   ├── 01_data_dictionary.md     grain, columns, denominators, segment rules
│   ├── 02_methodology.md         why each method, and its limits
│   ├── 03_data_quality_report.md GENERATED
│   ├── 04_findings_report.md     GENERATED — the main deliverable
│   ├── 05_five_whys.md           GENERATED — the evidential why-chain
│   ├── 06_recommendations.md     GENERATED — action register
│   ├── 07_dashboard_spec.md      Power BI build spec (measures, pages, RLS)
│   ├── 08_project_brief.md       question, decision, scope, success criteria
│   └── 09_executive_brief.md     GENERATED — the one-pager, in plain text
├── Dashboard/                    the four Power BI page images this pack matches
├── data/                         GENERATED — not committed (see .gitignore)
│   ├── raw/                      simulated POS export WITH planted defects
│   ├── processed/                cleaned star schema (what analysis uses)
│   └── revenue_decline.sqlite    the warehouse
├── sql/                          01 schema · 02 views · 03 quality · 04 mechanism
│                                 · 05 structure · 06 cohort · 07 crosscut
│                                 · 08 stockout · 09 pricing
├── src/                          config · generate_data · clean_data · run_sql
│                                 · decompose · five_whys · write_report
│                                 · theme (the shared visual language)
│                                 · make_figures · report_content · docx_kit
│                                 · write_reports · validate_against_truth
│                                 · run_pipeline (entry point)
└── outputs/
    ├── figures/                  10 charts, each tied to a sentence in the report
    ├── reports/                  the executive brief, the deck, the Word report, the PDF
    ├── tables/                   every table cited anywhere in the docs
    ├── kpis.json                 machine-readable headline metrics
    └── validation_report.md      the analysis graded against the truth
```

## How to run

No installation. The repo vendors numpy / matplotlib / python-docx / python-pptx
under `pylibs/`, and the scripts add it to `sys.path` automatically.

**Interpreter pin.** The vendored numpy is built for **CPython 3.12**, so a newer
`python3` cannot import it. Run the pipeline with a 3.12 interpreter that can see
`pylibs/`, or let the Makefile find one:

```bash
cd projects/project-1-revenue-decline-diagnostic

make                                 # everything (~60s), auto-detects a 3.12 interpreter
make PY=/usr/bin/python3.12          # or name one explicitly
```

Directly:

```bash
python3.12 src/run_pipeline.py          # everything
python3.12 src/run_pipeline.py --fast   # skip regeneration, re-run analysis only
```

Individual steps:

```bash
python3.12 src/generate_data.py           # simulate the dataset (~9s)
python3.12 src/clean_data.py              # audit + fix, write the quality report
python3.12 src/run_sql.py                 # build SQLite, run every sql/*.sql
python3.12 src/decompose.py               # mechanism → structure → intersect
python3.12 src/five_whys.py               # the evidential why-chain
python3.12 src/write_report.py            # findings + recommendations
python3.12 src/make_figures.py            # 10 figures, in the dashboard's style
python3.12 src/write_reports.py           # brief + deck + Word + PDF
python3.12 src/validate_against_truth.py  # exit 0 = 14/14 checks pass
```

> The PDFs are produced from the Word files with headless LibreOffice, so the
> Word and PDF versions cannot disagree about a number or a page.

Inspect the warehouse directly (SQLite is stdlib, so no client is needed):

```bash
python3 -c "import sqlite3; print(sqlite3.connect('data/revenue_decline.sqlite')
            .execute('SELECT * FROM mechanism_by_period').fetchall())"
```

## The figures

All ten are rendered in the dashboard's visual language — one cream surface,
**green `#259741` for growth and orange `#FB6107` for decline**, gradients only
where they encode intensity, and a value label on every bar and every point.
The rules live in [`src/theme.py`](src/theme.py) so a colour is defined once.

| Figure | The sentence it proves |
|---|---|
| `01_headline_waterfall.png` | the 10% headline is three mechanisms, not one |
| `02_mechanism_identity.png` | customers up, frequency down — the engine failed, not the funnel |
| `03_branch_waterfall.png` | two stores carry 71% of the decline |
| `04_branch_category_heatmap.png` | the decline is concentrated in the intersection, not diffuse |
| `05_category_decline.png` | Groceries is the biggest KSh loss, Beverages the fastest fall |
| `06_segment_waterfall.png` | every established segment shrank; only bought growth grew |
| `07_cohort_retention.png` | retention is healthy — the leak is trip frequency |
| `08_stockout_timeline.png` | the supply failure has a date, a store and a revenue trace |
| `09_discount_depth.png` | prices rose while discounting deepened |
| `10_driver_partition.png` | four ranked, owned problems |

## The reports

Four formats, one source. They reach different readers in different rooms, but
every number in all four comes from `outputs/kpis.json` and the exported tables
via [`src/report_content.py`](src/report_content.py), so they cannot drift apart
from each other or from the charts.

| Artefact | Audience | Why this format |
|---|---|---|
| [Executive brief](outputs/reports/Executive_Brief.pdf) (2 pp) | the CEO | the only page that gets read before the meeting |
| [Deck](outputs/reports/Revenue_Decline_Diagnostic.pptx) (17 slides) | the boardroom | presented, not read; notes on every slide |
| [Word report](outputs/reports/Revenue_Decline_Diagnostic.docx) (21 pp) | the team | the working document — editable |
| [PDF report](outputs/reports/Revenue_Decline_Diagnostic.pdf) (21 pp) | circulation | the locked, distributable version of the Word report |

## About the data

The dataset is **simulated** from a documented mechanism (`src/config.py` →
`STORY`, `MIGRATION`; written out in `docs/00_ground_truth.md`). That is a
deliberate design choice, not a shortcut: it is what allows the diagnosis to be
**graded** rather than merely presented. The simulation also plants nine classes
of real-world data-quality defect so the cleaning step has genuine work to do.

~195k line items · 55,431 invoices · 6,412 customers · 39 SKUs · 8 categories ·
6 stores · 2 quarters. Seed **20260914**; the figures quoted in this README
reflect that seed, while everything in `docs/04`–`06` recomputes itself.

`data/` is **not committed** — it is ~110 MB and is regenerated in full by
`make`, so a fresh clone rebuilds it on the first run.

## Suggested reading order

1. `docs/08_project_brief.md` — what was asked and why
2. `docs/04_findings_report.md` — the answer
3. `docs/05_five_whys.md` — the evidence chain behind it
4. `docs/06_recommendations.md` — what to do on Monday
5. `docs/02_methodology.md` — how to challenge the numbers
6. `src/decompose.py` — the attribution maths itself
7. `docs/00_ground_truth.md` — what was really baked in
