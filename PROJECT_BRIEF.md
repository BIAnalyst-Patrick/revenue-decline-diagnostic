# Project Brief — one page

**Question.** Revenue fell 10%. Where did it come from — which **branch ×
product × customer segment** drove the decline, and how much did each
contributor cost us?

**Decision it feeds.** Whose plan gets rewritten — **retention, pricing, or
merchandising**?

**Method.** Decompose by **mechanism** first (customers × frequency × basket
size), then by **structure** (branch, product, segment), then **intersect**
(store × category × segment). Finish with an **evidential 5-Whys** where every
"why" is answered with a number and the chain stops at something actionable.

**Answer (short form).**

* The business did not lose customers — customers **+5.5%**, but trips per
  customer **−11.4%** and basket value **−4.5%**.
* **Two of six stores carry 71% of the decline**: Mombasa Nyali (−27.0%,
  a six-week stock-out of two hero SKUs) and Thika Road (−18.7%, a traffic-only
  problem).
* Gross profit fell **16.9%** against a 10.7% revenue fall — margin compressed
  1.38pp, so this is not merely a volume story.
* Four owned problems: Supply Chain 41% · Retail Operations 29% · CRM 19% ·
  Pricing 11%.

**Deliverables.** Findings report · evidential 5-Whys · recommendations register
· data-quality report · Power BI dashboard spec · reproducible pipeline ·
validation against ground truth.

**Full brief (scope, stakeholders, success criteria):**
[`docs/08_project_brief.md`](docs/08_project_brief.md)

**The findings themselves:**
[`docs/04_findings_report.md`](docs/04_findings_report.md)

**Run it:** `python3 src/run_pipeline.py`
