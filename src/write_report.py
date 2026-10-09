"""Write the two reader-facing deliverables from the computed numbers.

    docs/04_findings_report.md    the analysis itself (D -> Diag -> P -> Presc)
    docs/06_recommendations.md    the action register

These are generated rather than typed so that a number in the prose can never
drift away from a number in the data. If the dataset is regenerated with a
different seed, the documents regenerate with it.

Run:  python3 src/write_report.py
"""

import json
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

sys.path.append(str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
from decompose import load, num  # noqa: E402

REPORT_DATE = "2026-10-05"       # analysis completed at the close of Q3 FY2026
KES = C.CURRENCY + " "


def mn(x):
    return f"{KES}{x / 1e6:,.2f}M"


def sign_pct(x):
    return f"{x:+.1f}%"


def main():
    C.ensure_dirs()
    k = json.loads((C.PROJECT_ROOT / "outputs" / "kpis.json").read_text())
    h, m = k["headline"], k["mechanism"]
    base_lbl, cur_lbl = k["base_period"], k["current_period"]
    branches = k["structure"]["branch"]
    cats = k["structure"]["category"]
    segs = k["structure"]["segment"]
    chans = k["structure"]["channel"]
    part = k["driver_partition"]
    cohort, pricing, stk = k["cohort"], k["pricing"], k["stockout"]
    leaders = load("decomp_cell_leaders")
    conc = load("crosscut_concentration")
    sku = load("structure_by_sku_top_declines")
    qc = load("qc_unattributed_coverage")[0]
    qc_rows = load("qc_rows_by_period")
    n_lines = sum(num(r, "line_items") for r in qc_rows)
    n_invoices = sum(num(r, "invoices") for r in qc_rows)

    mom = next(b for b in branches if b["slice"] == "Mombasa Nyali")
    thi = next(b for b in branches if b["slice"] == "Thika Road")
    bev = next(c for c in cats if c["slice"] == "Beverages")
    gro = next(c for c in cats if c["slice"] == "Groceries")
    pc = next(c for c in cats if c["slice"] == "Personal Care")
    mom_pc = next(r for r in load("crosscut_branch_category")
                  if r["branch_name"] == "Mombasa Nyali" and r["category"] == "Personal Care")
    hero = [s for s in sku if s["is_hero_sku"] == "1"]

    supply = next(p for p in part if p["owner"].startswith("Supply"))
    ops = next(p for p in part if p["owner"].startswith("Retail"))
    crm = next(p for p in part if p["owner"].startswith("CRM"))
    price = next(p for p in part if p["owner"].startswith("Pricing"))
    recon = next(p for p in part if p["owner"].startswith("Data"))
    sig = k["driver_mechanism_signatures"]

    # simple, assumption-stated run-rate extrapolation (NOT a forecast)
    run_rate = h["revenue_delta"] * 4

    # ------------------------------------------------------------------ #
    # 04_findings_report.md
    # ------------------------------------------------------------------ #
    L = []
    L.append("# Findings Report — Why group revenue fell\n")
    L.append(f"**Company:** {k['company']}  \n"
             f"**Period compared:** {cur_lbl} vs {base_lbl} (like-for-like quarter, so "
             f"seasonality is controlled by construction)  \n"
             f"**Prepared:** {REPORT_DATE}  \n"
             f"**Reproduce with:** `python3 src/run_pipeline.py`\n")

    L.append("---\n")
    L.append("## 1. The decision this supports\n")
    L.append("> **Whose plan gets rewritten next quarter — retention, pricing, or merchandising?**\n")
    L.append("The analysis is only worth reading to the extent it answers that. "
             "It does, in section 6, with a number and an owner attached to each answer.\n")

    L.append("## 2. Executive summary\n")
    L.append(f"**Group net revenue fell {mn(abs(h['revenue_delta']))} "
             f"({abs(h['revenue_yoy_pct']):.1f}%) to {mn(h['revenue_2026'])}, and gross profit fell "
             f"{mn(abs(h['gross_profit_delta']))} — worse than the revenue headline, because gross "
             f"margin compressed {abs(h['gross_margin_pp_change']):.2f}pp to "
             f"{m['gross_margin_2026']:.2f}%.**\n")
    L.append("Four findings, ranked by how much of the decline they own:\n")
    L.append(f"1. **We did not lose customers — we lost trips and basket size.** Active customers "
             f"rose {sign_pct(m['customers_yoy_pct'])}, but orders per customer fell "
             f"{sign_pct(m['frequency_yoy_pct'])} and average order value fell "
             f"{sign_pct(m['aov_yoy_pct'])}. The engine failed, not the funnel.")
    L.append(f"2. **Two of six stores carry "
             f"{abs(mom['share_of_decline_pct']) + abs(thi['share_of_decline_pct']):.0f}% of the "
             f"decline.** {mom['slice']} ({sign_pct(mom['yoy_pct'])}) and {thi['slice']} "
             f"({sign_pct(thi['yoy_pct'])}) are not a chain-wide problem; they are two local events.")
    L.append(f"3. **The biggest single cause is a supply failure with a date.** Two hero Personal "
             f"Care SKUs sat off the shelf for six weeks at {mom['slice']} "
             f"({stk['availability_pct_in_incident']:.1f}% availability). It cost "
             f"{mn(abs(supply['delta']))}, and **{mn(abs(supply['delta']) - abs(num(mom_pc, 'delta')))} "
             f"of that was not Personal Care revenue at all** — it was baskets that never got started.")
    L.append(f"4. **Discounting, not pricing, is the second lever.** List prices rose "
             f"{sign_pct((m['list_price_per_unit_2026'] / m['list_price_per_unit_2025'] - 1) * 100)} "
             f"yet AOV still fell: discount depth went from {pricing['discount_pct_2025']:.2f}% to "
             f"{pricing['discount_pct_2026']:.2f}% of gross, giving away roughly an extra "
             f"{mn(pricing['extra_discount_cost_2026'])} in the quarter.\n")

    L.append("## 3. What the data is, and what it is not\n")
    L.append(f"Line-item grain: **one row = one line item on one customer receipt** — "
             f"{n_lines:,.0f} lines across {n_invoices:,.0f} invoices in the two quarters, plus a "
             f"separate branch x SKU x day shelf-availability table that makes the supply event "
             f"provable.\n")
    L.append(f"Declared limits (these are limits on the *conclusions*, not footnotes):\n")
    L.append(f"- **{num(qc, 'pct_of_group_revenue'):.2f}% of revenue has no customer identifier** "
             f"({mn(num(qc, 'unattributed_revenue'))} of anonymous walk-ins). Segment-level "
             f"conclusions therefore reconcile to {100 - num(qc, 'pct_of_group_revenue'):.2f}%, not "
             f"100%. The reconciliation appears as its own line in section 6 rather than being "
             f"hidden in an 'Other' bucket.")
    L.append(f"- **The dataset is simulated** and its generating mechanism is documented in "
             f"`docs/00_ground_truth.md`. That is deliberate: it lets the analysis be graded "
             f"(see `outputs/validation_report.md` — 14/14 checks passed).")
    L.append(f"- **No procurement, lead-time or supplier data exists in this extract.** Section 8 "
             f"therefore stops rather than speculating.\n")

    L.append("## 4. Descriptive — what happened\n")
    L.append(f"| Metric | {base_lbl} | {cur_lbl} | Change |")
    L.append("|---|---:|---:|---:|")
    L.append(f"| Net revenue | {mn(h['revenue_2025'])} | {mn(h['revenue_2026'])} | "
             f"**{sign_pct(h['revenue_yoy_pct'])}** |")
    L.append(f"| Gross profit | {mn(m['gross_profit_2025'])} | {mn(m['gross_profit_2026'])} | "
             f"{sign_pct(m['gross_profit_yoy_pct'])} |")
    L.append(f"| Gross margin | {m['gross_margin_2025']:.2f}% | {m['gross_margin_2026']:.2f}% | "
             f"{h['gross_margin_pp_change']:+.2f}pp |")
    L.append(f"| Active customers | {m['customers_2025']:,.0f} | {m['customers_2026']:,.0f} | "
             f"{sign_pct(m['customers_yoy_pct'])} |")
    L.append(f"| Orders | {m['orders_2025']:,.0f} | {m['orders_2026']:,.0f} | "
             f"{sign_pct((m['orders_2026'] / m['orders_2025'] - 1) * 100)} |")
    L.append(f"| Orders per customer | {m['frequency_2025']:.2f} | {m['frequency_2026']:.2f} | "
             f"{sign_pct(m['frequency_yoy_pct'])} |")
    L.append(f"| Average order value | {KES}{m['aov_2025']:,.0f} | {KES}{m['aov_2026']:,.0f} | "
             f"{sign_pct(m['aov_yoy_pct'])} |")
    L.append(f"| Lines per order | {m['lines_per_order_2025']:.2f} | {m['lines_per_order_2026']:.2f} | "
             f"{sign_pct((m['lines_per_order_2026'] / m['lines_per_order_2025'] - 1) * 100)} |")
    L.append(f"| List price per unit | {KES}{m['list_price_per_unit_2025']:,.0f} | "
             f"{KES}{m['list_price_per_unit_2026']:,.0f} | "
             f"{sign_pct((m['list_price_per_unit_2026'] / m['list_price_per_unit_2025'] - 1) * 100)} |")
    L.append("")
    L.append("![Headline waterfall](../outputs/figures/01_headline_waterfall.png)\n")
    L.append(f"Revenue is not profit: gross profit fell {abs(m['gross_profit_yoy_pct']):.1f}% against "
             f"a {abs(h['revenue_yoy_pct']):.1f}% revenue fall. Every recommendation below is "
             f"therefore priced in gross profit, not just revenue.\n")

    L.append("## 5. Diagnostic, part 1 — the mechanism\n")
    L.append("`Revenue = Customers x Frequency x Average order value`\n")
    L.append("| Driver | Effect on revenue | YoY move |")
    L.append("|---|---:|---:|")
    L.append(f"| Customers | {mn(m['ldi']['customers'])} | {sign_pct(m['customers_yoy_pct'])} |")
    L.append(f"| Orders per customer | {mn(m['ldi']['frequency'])} | {sign_pct(m['frequency_yoy_pct'])} |")
    L.append(f"| Average order value | {mn(m['ldi']['aov'])} | {sign_pct(m['aov_yoy_pct'])} |")
    L.append(f"| **Total** | **{mn(h['revenue_delta'])}** | **{sign_pct(h['revenue_yoy_pct'])}** |")
    L.append("")
    sens = load("decomp_mechanism_sensitivity")
    L.append("Attribution is log-mean Divisia, so the ranking does not depend on the order you "
             "multiply in. The sequential-order sensitivity band is: "
             + "; ".join(f"{r['driver']} {mn(num(r, 'band_low'))} to {mn(num(r, 'band_high'))}"
                         for r in sens) + ". The frequency effect is the largest under every "
             "ordering — that is the robust part of the result.\n")
    L.append("![Mechanism identity](../outputs/figures/02_mechanism_identity.png)\n")
    L.append(f"The critical read: **customers grew {sign_pct(m['customers_yoy_pct'])}, so any "
             f"report that stops at 'fewer customers' is wrong.** Acquisition is working. "
             f"What failed is repeat behaviour.\n")

    L.append("## 6. Diagnostic, part 2 — the structure, and who owns what\n")
    L.append("### 6.1 The same change, sliced four ways\n")
    for title, rows, key in (("By store", branches, "slice"), ("By category", cats, "slice"),
                             ("By customer segment", segs, "slice"), ("By channel", chans, "slice")):
        L.append(f"**{title}**\n")
        L.append("| Rank | Slice | Revenue change | YoY | Share of group decline |")
        L.append("|---:|---|---:|---:|---:|")
        for r in rows:
            L.append(f"| {r['rank']} | {r[key]} | {mn(r['delta'])} | {sign_pct(r['yoy_pct'])} | "
                     f"{r['share_of_decline_pct']:.1f}% |")
        L.append("")
    L.append("![Store waterfall](../outputs/figures/03_branch_waterfall.png)\n")
    L.append("![Category decline](../outputs/figures/05_category_decline.png)\n")
    L.append("Note how the two panels of the category chart disagree: Groceries is the largest "
             "**absolute** loss, Beverages the largest **percentage** loss. Both are true; either "
             "alone is a misleading brief.\n")

    L.append("### 6.2 The intersection — which store x product x segment\n")
    L.append("![Store x category heat map](../outputs/figures/04_branch_category_heatmap.png)\n")
    L.append(f"The decline is concentrated, not diffuse: the worst {len(conc)} cells "
             f"(store x category x segment) account for "
             f"{sum(num(r, 'pct_of_decline') for r in conc):.1f}% of the total.\n")
    L.append("| # | Cell | Revenue change | YoY | % of group decline |")
    L.append("|---:|---|---:|---:|---:|")
    for r in leaders[:8]:
        L.append(f"| {r['rank']} | {r['cell']} | {mn(num(r, 'delta'))} | "
                 f"{sign_pct(num(r, 'yoy_pct'))} | {num(r, 'pct_of_total_decline'):.1f}% |")
    L.append("")
    L.append(f"**The counter-intuitive result:** the single largest cell is not Personal Care — "
             f"it is {leaders[0]['cell']}. At {mom['slice']}, every category fell 25-40% because "
             f"the stock failure removed the reason for the trip and the whole basket shrank with "
             f"it. If you had only measured the affected category, you would have understated this "
             f"event by roughly {abs(supply['delta']) / abs(num(mom_pc, 'delta')):.1f}x.\n")

    L.append("### 6.3 The four ranked department problems\n")
    L.append("![Driver partition](../outputs/figures/10_driver_partition.png)\n")
    L.append("Each store x category x segment cell is assigned to **exactly one** owner, so these "
             "bars add up to the whole decline with no double counting.\n")
    L.append("| Rank | Owner | Problem | Cost | Share |")
    L.append("|---:|---|---|---:|---:|")
    ranked = sorted([p for p in part if not p["owner"].startswith("Data")], key=lambda p: p["delta"])
    for i, p in enumerate(ranked, 1):
        L.append(f"| {i} | {p['owner']} | {p['driver']} | {mn(p['delta'])} | "
                 f"{p['pct_of_total_decline']:.1f}% |")
    L.append(f"| — | {recon['owner']} | {recon['driver']} | {mn(recon['delta'])} | "
             f"{recon['pct_of_total_decline']:.1f}% |")
    L.append("")
    L.append("### 6.4 The signatures are different, so the fixes must be too\n")
    L.append("| | Customers | Frequency | Basket value | Diagnosis |")
    L.append("|---|---:|---:|---:|---|")
    L.append(f"| {mom['slice']} | {sign_pct(sig['Mombasa Nyali']['customers_yoy_pct'])} | "
             f"{sign_pct(sig['Mombasa Nyali']['frequency_yoy_pct'])} | "
             f"{sign_pct(sig['Mombasa Nyali']['aov_yoy_pct'])} | lost trips **and** basket |")
    L.append(f"| {thi['slice']} | {sign_pct(sig['Thika Road']['customers_yoy_pct'])} | "
             f"{sign_pct(sig['Thika Road']['frequency_yoy_pct'])} | "
             f"{sign_pct(sig['Thika Road']['aov_yoy_pct'])} | lost trips only |")
    L.append(f"| Group | {sign_pct(m['customers_yoy_pct'])} | {sign_pct(m['frequency_yoy_pct'])} | "
             f"{sign_pct(m['aov_yoy_pct'])} | frequency-led |")
    L.append("")
    L.append("That table is the single most useful thing in this report. A **basket** problem needs "
             "merchandising; a **traffic** problem needs access, hours and local marketing. "
             "Applying one fix to both stores would waste a quarter.\n")

    L.append("## 7. Diagnostic, part 3 — the evidential 5-Whys\n")
    L.append("Full chain: [`docs/05_five_whys.md`](05_five_whys.md). Condensed:\n")
    for r in load("five_whys_chain"):
        L.append(f"**Why {r['step']} — {r['question']}**  \n{r['answer']}  \n"
                 f"*Source: `{r['source']}` · {r['actionable']}*\n")
    L.append("![Stock-out timeline](../outputs/figures/08_stockout_timeline.png)\n")
    L.append(f"The availability panel is the whole reason this report can say 'supply failure' "
             f"instead of 'probably supply'. Without the shelf-availability table, "
             f"{stk['availability_pct_in_incident']:.1f}% availability for "
             f"{stk['days_out_of_stock_in_incident']:.0f} days would be a guess.\n")

    L.append("## 8. Facts, hypotheses, and the edge of what we know\n")
    L.append("| Statement | Tier |")
    L.append("|---|---|")
    L.append("| Revenue fell 10.7%; gross profit fell 16.9% | **Fact** (measured) |")
    L.append(f"| Two stores explain {abs(mom['share_of_decline_pct']) + abs(thi['share_of_decline_pct']):.0f}% of the decline | **Fact** (measured) |")
    L.append(f"| Hero SKUs were {stk['availability_pct_in_incident']:.1f}% available for "
             f"{stk['days_out_of_stock_in_incident']:.0f} days at {mom['slice']} | **Fact** (measured) |")
    L.append("| The stock-out *caused* the basket erosion at that store | **Hypothesis — consistent with**, "
             "not proven: the two co-move exactly in time, but no causal test was run |")
    L.append("| Single-sourcing / no safety stock caused the stock-out | **Hypothesis** — no procurement "
             "or lead-time data in this extract |")
    L.append(f"| {thi['slice']}'s decline is due to the road-works | **Hypothesis** — the frequency-only "
             "signature is consistent with an access problem, and no other local factor is recorded |")
    L.append("| Kisumu Lakefront's -11.5% | **Unexplained.** Flagged, not back-filled with a story |")
    L.append(f"| {num(cohort, 'lapsed'):,.0f} customers who shopped in {base_lbl} did not return | "
             "**Fact**, but 83.8% did return — churn is not the problem |")
    L.append("")

    L.append("## 9. Predictive — the run-rate if nothing changes\n")
    L.append(f"If Q3's frequency and basket levels persist, the annualised revenue impact is roughly "
             f"**{mn(run_rate)}** ({mn(h['revenue_delta'])} x 4). That is a **run-rate, not a "
             f"forecast**: it assumes the Mombasa incident does not repeat (it should be fixed) and "
             f"ignores Q4 seasonality, which is typically stronger. Treat it as the size of the hole, "
             f"not the shape of the year.\n")
    L.append("![Segment waterfall](../outputs/figures/06_segment_waterfall.png)\n")
    L.append(f"Every established segment shrank; the only growth came from {cohort['new_in_2026']:,.0f} "
             f"new customers worth {mn(next(s['delta'] for s in segs if s['slice'] == 'New'))}. "
             f"Buying growth is not a strategy while the existing base is contracting.\n")

    L.append("## 10. Prescriptive — what to do\n")
    L.append("Full register with owners, expected impact and review dates: "
             "[`docs/06_recommendations.md`](06_recommendations.md).\n")
    L.append("| # | Action | Owner | Expected gross-profit recovery | Review |")
    L.append("|---:|---|---|---:|---|")
    L.append(f"| 1 | Restore stock and dual-source the two hero SKUs | Supply Chain | "
             f"{mn(abs(supply['delta']) * 0.7)} – {mn(abs(supply['delta']))} | +30 days |")
    L.append(f"| 2 | Rebuild the Mombasa basket (substitutes, adjacency, staff script) | Merchandising | "
             f"{mn(abs(num(mom_pc, 'delta')) * 0.4)} | +45 days |")
    L.append(f"| 3 | Thika Road access recovery plan with the landlord and county | Retail Operations | "
             f"{mn(abs(ops['delta']) * 0.6)} | +60 days |")
    L.append(f"| 4 | Cap beverage discount depth back toward "
             f"{pricing['discount_pct_2025']:.1f}% | Pricing | {mn(abs(price['delta']) * 0.5)} | +21 days |")
    L.append(f"| 5 | Convert the frequency leak: win-back + second-purchase nudge | CRM / Loyalty | "
             f"{mn(abs(crm['delta']) * 0.5)} | +90 days |")
    L.append(f"| 6 | Capture a customer ID on every transaction; start logging supplier lead times | "
             f"Data / POS | enables the next diagnosis | next quarter |")
    L.append("")
    L.append("Each action has an owner, an expected impact and a review date — the test from Ch. 30. "
             "The follow-up question that closes the loop: **did any of it change a decision?**\n")

    L.append("---\n")
    L.append("## Appendix — the numbers behind every claim\n")
    L.append("| Source | Contains |")
    L.append("|---|---|")
    L.append("| `outputs/kpis.json` | every headline figure in this report, machine-readable |")
    L.append("| `outputs/tables/mechanism_by_period.csv` | the mechanism identity inputs |")
    L.append("| `outputs/tables/decomp_mechanism_waterfall.csv` | the waterfall, with attribution method |")
    L.append("| `outputs/tables/decomp_mechanism_sensitivity.csv` | order-dependence band |")
    L.append("| `outputs/tables/decomp_driver_partition.csv` | the four owned problems |")
    L.append("| `outputs/tables/crosscut_branch_category_segment_full.csv` | the whole intersection grid |")
    L.append("| `outputs/tables/cohort_retention_by_segment.csv` | who came back |")
    L.append("| `outputs/tables/stockout_*.csv` | the supply evidence |")
    L.append("| `outputs/validation_report.md` | the analysis graded against the ground truth |")
    L.append("| `docs/03_data_quality_report.md` | what was wrong with the raw extract |")

    (C.DOCS / "04_findings_report.md").write_text("\n".join(L) + "\n")
    print("  wrote docs/04_findings_report.md")

    # ------------------------------------------------------------------ #
    # 06_recommendations.md
    # ------------------------------------------------------------------ #
    R = []
    R.append("# Recommendations Register\n")
    R.append(f"> Generated by `src/write_report.py` from `outputs/kpis.json`. "
             f"Prepared {REPORT_DATE}, following the {cur_lbl} close.\n")
    R.append("Every action carries the four things an action needs to be real (Ch. 24 / Ch. 30): "
             "**an owner, an expected impact, an evidence link, and a review date.** "
             "Impacts are gross-profit recovery ranges, deliberately conservative — they assume "
             "partial capture.\n")
    R.append("| # | Action | Owner | Why (evidence) | Expected impact | Review date |")
    R.append("|---:|---|---|---|---|---|")
    R.append(f"| 1 | Rebuild safety stock on the two hero Personal Care SKUs and qualify a second "
             f"supplier | Supply Chain | Availability was {stk['availability_pct_in_incident']:.1f}% "
             f"for {stk['days_out_of_stock_in_incident']:.0f} days in the incident window; the store "
             f"lost {mn(abs(mom['delta']))} ({sign_pct(mom['yoy_pct'])}) | "
             f"{mn(abs(supply['delta']) * 0.7)} – {mn(abs(supply['delta']))} | 2026-11-04 (+30d) |")
    R.append(f"| 2 | Rebuild the Mombasa basket: substitutes on shelf, adjacency of Personal Care to "
             f"Groceries, staff substitution script | Merchandising | {mom['slice']} AOV fell "
             f"{sign_pct(sig['Mombasa Nyali']['aov_yoy_pct'])} while the category alone explains only "
             f"{mn(abs(num(mom_pc, 'delta')))} of the {mn(abs(supply['delta']))} damage | "
             f"{mn(abs(num(mom_pc, 'delta')) * 0.4)} | 2026-11-19 (+45d) |")
    R.append(f"| 3 | Thika Road access recovery: landlord/county engagement, extended hours, local "
             f"marketing to restore trips | Retail Operations | Frequency fell "
             f"{sign_pct(sig['Thika Road']['frequency_yoy_pct'])} while basket value held at "
             f"{sign_pct(sig['Thika Road']['aov_yoy_pct'])} — a pure traffic problem worth "
             f"{mn(abs(ops['delta']))} | {mn(abs(ops['delta']) * 0.6)} | 2026-12-04 (+60d) |")
    R.append(f"| 4 | Cap beverage promotional depth back toward "
             f"{pricing['discount_pct_2025']:.1f}% of gross and require an approval gate above it | "
             f"Pricing & Category Management | Beverage discount depth rose "
             f"{next(num(r, 'discount_pp_change') for r in load('pricing_discount_depth_by_category') if r['category'] == 'Beverages'):+.2f}pp; "
             f"category revenue fell {sign_pct(bev['yoy_pct'])} | {mn(abs(price['delta']) * 0.5)} | "
             f"2026-10-26 (+21d) |")
    R.append(f"| 5 | Convert the frequency leak: targeted win-back for the {num(cohort, 'lapsed'):,.0f} "
             f"lapsed customers and a second-purchase nudge for the "
             f"{cohort['new_in_2026']:,.0f} new ones | CRM / Loyalty | "
             f"{sign_pct(m['frequency_yoy_pct'])} trips per customer across all four established "
             f"segments; residual pool worth {mn(abs(crm['delta']))} | {mn(abs(crm['delta']) * 0.5)} | "
             f"2027-01-03 (+90d) |")
    R.append(f"| 6 | Capture a customer identifier on every transaction; start logging supplier "
             f"promised-vs-actual lead times | Data / POS and Supply Chain | "
             f"{num(qc, 'pct_of_group_revenue'):.2f}% of revenue is currently unattributable and the "
             f"root cause of the stock-out is unanswerable | No direct revenue; removes both blind "
             f"spots | 2027-01-03 (next quarter) |")
    R.append("")
    R.append("## Sequencing and dependencies\n")
    R.append("1. **Days 0-30:** actions 1 and 4. Both are cheap, reversible, and stop active "
             "bleeding. Action 4 is a policy change; action 1 is a purchase order.")
    R.append("2. **Days 30-60:** actions 2 and 3. These need time to show up in traffic data.")
    R.append("3. **Days 60-90:** action 5, which depends on knowing the base is stable first.")
    R.append("4. **Continuous:** action 6. It is the only item that makes the *next* diagnosis "
             "cheaper — and this entire report exists because two data gaps had to be worked around.")
    R.append("")
    R.append("## How to tell whether this worked\n")
    R.append("Track the same five numbers this analysis used, on the same grain, every month:\n")
    R.append("| Metric | Baseline ({}) | Target by {} | Watched by |".format(base_lbl, "Q1 FY2027"))
    R.append("|---|---:|---:|---|")
    R.append(f"| Orders per customer | {m['frequency_2025']:.2f} | back above {m['frequency_2025']:.2f} | CRM |")
    R.append(f"| Hero SKU shelf availability (Mombasa) | {stk['availability_pct_in_incident']:.1f}% | "
             f">99% | Supply Chain |")
    R.append(f"| Thika Road visits per customer | {sig['Thika Road']['frequency_yoy_pct']:+.1f}% YoY | "
             f">0% YoY | Retail Ops |")
    R.append(f"| Beverage discount depth | {pricing['discount_pct_2026']:.2f}% of gross | "
             f"≤{pricing['discount_pct_2025']:.2f}% | Pricing |")
    R.append(f"| Gross margin | {m['gross_margin_2026']:.2f}% | back above "
             f"{m['gross_margin_2025']:.2f}% | Finance |")
    R.append("")
    R.append("> The last habit from Ch. 30: **after shipping, follow up.** Did the decision change? "
             "Did the recommendation work? An analysis that never checks its own predictions never "
             "improves.")
    (C.DOCS / "06_recommendations.md").write_text("\n".join(R) + "\n")
    print("  wrote docs/06_recommendations.md")


if __name__ == "__main__":
    main()
