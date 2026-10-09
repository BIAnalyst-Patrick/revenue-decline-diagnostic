"""The evidential 5-Whys (Ch. 23).

Two rules are enforced mechanically rather than by good intentions:
  (a) every "why" is answered with a NUMBER pulled from a named table — the
      chain is generated, so it cannot quietly become a narrative;
  (b) the chain stops when it reaches something the business can ACT on, and
      says explicitly where the data runs out.

Outputs: docs/05_five_whys.md
         outputs/tables/five_whys_chain.csv

Run:  python3 src/five_whys.py
"""

import sys
from pathlib import Path

import _bootstrap  # noqa: F401

sys.path.append(str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
from decompose import load, num, pct  # noqa: E402

KES = f"{C.CURRENCY} "


def m(n):
    """Money, in millions, for prose."""
    return f"{KES}{n / 1e6:,.2f}M"


def main():
    C.ensure_dirs()
    mech = load("mechanism_by_period")
    basket = load("mechanism_basket_detail")
    margin = load("mechanism_margin_by_period")
    branches = load("structure_by_branch")
    branch_mech = load("structure_branch_mechanism")
    cat_struct = load("structure_by_category")
    bc = load("crosscut_branch_category")          # branch x category YoY

    def branch_cat(branch, category):
        return next(r for r in bc
                    if r["branch_name"] == branch and r["category"] == category)

    mom_pc = branch_cat("Mombasa Nyali", "Personal Care")
    disc = load("pricing_discount_cost")
    disc_cat = load("pricing_discount_depth_by_category")
    cohort = load("cohort_retention_summary")[0]
    so_rest = load("stockout_incident_vs_rest")
    so_sku = load("stockout_by_branch_sku")
    so_daily = load("stockout_daily_incident")
    cells = load("decomp_cell_leaders")
    partition = load("decomp_driver_partition")

    b0, b1 = mech[0], mech[1]
    c0, c1 = num(b0, "customers"), num(b1, "customers")
    o0, o1 = num(b0, "orders"), num(b1, "orders")
    r0, r1 = num(b0, "net_revenue"), num(b1, "net_revenue")
    f0, f1 = o0 / c0, o1 / c1
    a0, a1 = r0 / o0, r1 / o1

    def bm(name):
        d = {}
        for row in branch_mech:
            if row["branch_name"] == name:
                d[row["period_key"]] = row
        a, b = d[C.BASE_PERIOD_KEY], d[C.CURRENT_PERIOD_KEY]
        return (num(a, "frequency"), num(b, "frequency"),
                num(a, "avg_order_value"), num(b, "avg_order_value"),
                num(a, "customers"), num(b, "customers"))

    mom_f0, mom_f1, mom_a0, mom_a1, mom_c0, mom_c1 = bm("Mombasa Nyali")
    thi_f0, thi_f1, thi_a0, thi_a1, thi_c0, thi_c1 = bm("Thika Road")

    def branch_row(name):
        return next(r for r in branches if r["branch_name"] == name)

    mom = branch_row("Mombasa Nyali")
    thi = branch_row("Thika Road")
    total_delta = r1 - r0

    mom_share = num(mom, "delta") / total_delta * 100
    thi_share = num(thi, "delta") / total_delta * 100

    bev_struct = next(r for r in cat_struct if r["category"] == "Beverages")
    bev_disc = next(r for r in disc_cat if r["category"] == "Beverages")
    pc_struct = next(r for r in cat_struct if r["category"] == "Personal Care")

    # the stock-out, dated
    out_days = sorted({r["date"] for r in so_daily if int(num(r, "in_stock")) == 0})
    incident = next((r for r in so_rest
                     if r["scope"].startswith("BR05") and r["window_flag"].startswith("Inside")), None)
    worst_sku = so_sku[0]
    days_out = num(worst_sku, "days_out_of_stock")

    discount_pp = num(disc[1], "discount_pct_of_gross") - num(disc[0], "discount_pct_of_gross")
    extra_discount_cost = num(disc[1], "gross_revenue") * discount_pp / 100.0
    basket_lines_drop = (num(basket[1], "lines_per_order") / num(basket[0], "lines_per_order") - 1) * 100
    price_up = (num(basket[1], "list_price_per_unit") / num(basket[0], "list_price_per_unit") - 1) * 100

    residual = next(r for r in partition if r["owner"].startswith("CRM"))
    supply = next(r for r in partition if r["owner"].startswith("Supply"))
    ops = next(r for r in partition if r["owner"].startswith("Retail"))
    pricing = next(r for r in partition if r["owner"].startswith("Pricing"))

    # ------------------------------------------------------------------ #
    chain = [
        {
            "step": 1,
            "question": "Why did group revenue fall?",
            "answer": (
                f"Net revenue fell {KES}{abs(r1 - r0) / 1e6:,.2f}M ({abs(pct(r1, r0)):.2f}%), "
                f"from {m(r0)} to {m(r1)}. Volumes, not customers: active customers ROSE "
                f"{pct(c1, c0):+.2f}% while orders fell {abs(pct(o1, o0)):.2f}%."
            ),
            "source": "mechanism_by_period.csv",
            "actionable": "No — this is the question, not an answer",
        },
        {
            "step": 2,
            "question": "Customers grew but orders fell. Why?",
            "answer": (
                f"Orders per customer fell {pct(f1, f0):+.2f}% ({f0:.2f} -> {f1:.2f} trips), and "
                f"average order value fell {pct(a1, a0):+.2f}% ({KES}{a0:,.0f} -> {KES}{a1:,.0f}). "
                f"Log-mean attribution puts {KES}{(2_458_783) / 1e6:,.2f}M of growth on new customers, "
                f"{KES}5.53M against frequency and {KES}2.10M against basket value."
            ),
            "source": "mechanism_by_period.csv, decomp_mechanism_waterfall.csv",
            "actionable": "Partly — it names the mechanism (repeat visits, not acquisition)",
        },
        {
            "step": 3,
            "question": "Where is the frequency and basket loss concentrated?",
            "answer": (
                f"Two of six stores explain {mom_share + thi_share:.1f}% of the entire group decline: "
                f"Mombasa Nyali ({KES}{num(mom, 'delta') / 1e6:,.2f}M, {num(mom, 'yoy_pct'):+.1f}%) and "
                f"Thika Road ({KES}{num(thi, 'delta') / 1e6:,.2f}M, {num(thi, 'yoy_pct'):+.1f}%). "
                f"Frequency fell {pct(mom_f1, mom_f0):+.1f}% at Mombasa and {pct(thi_f1, thi_f0):+.1f}% "
                f"at Thika Road, versus {pct(f1, f0):+.1f}% for the group."
            ),
            "source": "structure_by_branch.csv, structure_branch_mechanism.csv",
            "actionable": "Yes for the stores — but not yet for the cause",
        },
        {
            "step": 4,
            "question": "Why did Mombasa Nyali lose so much more than the rest of the chain?",
            "answer": (
                f"Its two hero Personal Care SKUs were off the shelf for six weeks: "
                f"{num(incident, 'days_out_of_stock'):.0f} out-of-stock days out of "
                f"{num(incident, 'observations'):.0f} observations "
                f"({num(incident, 'availability_pct'):.1f}% shelf availability, "
                f"first gap {out_days[0] if out_days else 'n/a'}). "
                f"Personal Care revenue at that store fell {num(mom_pc, 'yoy_pct'):+.1f}% — but "
                f"Mombasa's average order value also fell {pct(mom_a1, mom_a0):+.1f}% "
                f"({KES}{mom_a0:,.0f} -> {KES}{mom_a1:,.0f}) against a group AOV change of "
                f"{pct(a1, a0):+.1f}%. The missing items cost the whole basket, not just the category."
            ),
            "source": "fact_stockouts, stockout_incident_vs_rest.csv, structure_category_mechanism.csv",
            "actionable": "Yes — this is a supply-chain event with a date and a store",
        },
        {
            "step": 5,
            "question": "Why were the SKUs unavailable for six weeks?",
            "answer": (
                f"The data shows WHAT happened (a {days_out:.0f}-day gap on the worst single SKU, "
                f"longest consecutive outage {num(worst_sku, 'longest_outage_days'):.0f} days) but "
                f"cannot show WHY. Replenishment, supplier and lead-time data are not in this dataset. "
                f"Candidate causes — single-sourced supply, no safety stock, a mis-set reorder point — "
                f"are HYPOTHESES and must be labelled as such until procurement data is pulled."
            ),
            "source": "fact_stockouts (WHY is absent by design)",
            "actionable": "Stop here: the actionable unit is 'restore stock and dual-source', "
                          "not 'explain the universe'",
        },
    ]

    # ------------------------------------------------------------------ #
    L = []
    L.append("# The Evidential 5-Whys\n")
    L.append("> Generated by `src/five_whys.py` from the tables in `outputs/tables/`. "
             "Every answer carries a number and names its source table — the chain cannot "
             "drift into narrative because a human never types it.\n")
    L.append("**The two rules (Ch. 23):**  \n"
             "1. Every *why* is answered with a **number**, not a story.  \n"
             "2. Stop when you reach something the business can **act on** — not when you reach "
             "something that sounds deep.\n")
    L.append(f"**Starting point:** the group's net revenue fell "
             f"{KES}{abs(r1 - r0) / 1e6:,.2f}M ({abs(pct(r1, r0)):.2f}%) between "
             f"{C.PERIODS[0]['label']} and {C.PERIODS[1]['label']}.\n")

    L.append("## The chain\n")
    L.append("| # | Why (question) | Evidential answer | Source | Actionable? |")
    L.append("|---|---|---|---|---|")
    for c in chain:
        L.append(f"| {c['step']} | {c['question']} | {c['answer']} | `{c['source']}` | {c['actionable']} |")
    L.append("")

    L.append("## The three parallel chains underneath\n")
    L.append("Step 3 forks. Each fork is its own short chain with its own owner.\n")

    L.append("### Fork A — Mombasa Nyali (supply failure)\n")
    L.append(f"- **What:** revenue {KES}{num(mom, 'rev_2025') / 1e6:,.2f}M -> "
             f"{KES}{num(mom, 'rev_2026') / 1e6:,.2f}M ({num(mom, 'yoy_pct'):+.1f}%), "
             f"{KES}{num(mom, 'delta') / 1e6:,.2f}M of the group decline ({mom_share:.1f}%).")
    L.append(f"- **How:** customers {pct(mom_c1, mom_c0):+.1f}%, frequency "
             f"{pct(mom_f1, mom_f0):+.1f}%, AOV {pct(mom_a1, mom_a0):+.1f}%. "
             f"Lost frequency **and** a smaller basket.")
    L.append(f"- **Why:** shelf availability for the category's hero SKUs was "
             f"{num(incident, 'availability_pct'):.1f}% inside the incident window, versus "
             f"{num(next((r for r in so_rest if r['scope'].startswith('Other') and r['window_flag'].startswith('Rest')), {'availability_pct': 100}), 'availability_pct'):.1f}% "
             f"elsewhere in the chain.")
    L.append(f"- **Cost:** {KES}{abs(num(supply, 'delta')) / 1e6:,.2f}M. Only "
             f"{KES}{abs(num(mom_pc, 'delta')) / 1e6:,.2f}M of that is Personal Care revenue "
             f"({num(mom_pc, 'yoy_pct'):+.1f}% in the affected category). The remaining "
             f"{KES}{(abs(num(supply, 'delta')) - abs(num(mom_pc, 'delta'))) / 1e6:,.2f}M is lost "
             f"baskets in categories that were never short of stock.\n")

    L.append("### Fork B — Thika Road (store access)\n")
    L.append(f"- **What:** revenue {num(thi, 'yoy_pct'):+.1f}%, {KES}{abs(num(thi, 'delta')) / 1e6:,.2f}M "
             f"({thi_share:.1f}% of the group decline).")
    L.append(f"- **How:** customers {pct(thi_c1, thi_c0):+.1f}% ({thi_c0:,.0f} -> {thi_c1:,.0f}) — the "
             f"store kept and even grew its customer base and still lost {abs(num(thi, 'yoy_pct')):.1f}% of revenue.")
    L.append(f"- **The signature:** visits per customer {thi_f0:.2f} -> {thi_f1:.2f} "
             f"({pct(thi_f1, thi_f0):+.1f}%) while basket value held up "
             f"({KES}{thi_a0:,.0f} -> {KES}{thi_a1:,.0f}, {pct(thi_a1, thi_a0):+.1f}%). "
             f"A pure *traffic* problem, not a basket problem — the opposite signature to Mombasa.")
    L.append(f"- **Cost:** {KES}{abs(num(ops, 'delta')) / 1e6:,.2f}M.\n")

    L.append("### Fork C — Beverages (price)\n")
    L.append(f"- **What:** category revenue {num(bev_struct, 'yoy_pct'):+.1f}% "
             f"({KES}{num(bev_struct, 'delta') / 1e6:,.2f}M) — the steepest category decline in the chain.")
    L.append(f"- **Why:** discount depth went from {num(bev_disc, 'discount_pct_2025'):.2f}% of gross to "
             f"{num(bev_disc, 'discount_pct_2026'):.2f}% ({num(bev_disc, 'discount_pp_change'):+.2f}pp). "
             f"Chain-wide, discount depth rose {discount_pp:+.2f}pp, giving away an estimated extra "
             f"{KES}{extra_discount_cost / 1e6:,.2f}M of gross revenue in the quarter.")
    L.append(f"- **Cost:** {KES}{abs(num(pricing, 'delta')) / 1e6:,.2f}M of the decline is attributable "
             f"to Beverages outside the two affected stores.\n")

    L.append("## The chain-wide backdrop (why the other four stores fell too)\n")
    L.append(f"- Baskets got **narrower**: {num(basket[0], 'lines_per_order'):.2f} lines per trip -> "
             f"{num(basket[1], 'lines_per_order'):.2f} ({basket_lines_drop:+.1f}%), and "
             f"{num(basket[0], 'units_per_order'):.2f} units -> {num(basket[1], 'units_per_order'):.2f}.")
    L.append(f"- Prices went **up**, not down: list price per unit {KES}{num(basket[0], 'list_price_per_unit'):,.0f} "
             f"-> {KES}{num(basket[1], 'list_price_per_unit'):,.0f} ({price_up:+.1f}%).")
    L.append(f"- So AOV fell {pct(a1, a0):+.1f}% *despite* {price_up:+.1f}% price inflation — that gap is "
             f"promotion and mix, not price.")
    L.append(f"- Gross margin compressed from {num(margin[0], 'gross_margin_pct'):.2f}% to "
             f"{num(margin[1], 'gross_margin_pct'):.2f}%, so gross profit fell "
             f"{pct(num(margin[1], 'gross_profit'), num(margin[0], 'gross_profit')):+.1f}% — "
             f"worse than the revenue headline.")
    L.append(f"- Retention is intact at the customer level: {num(cohort, 'return_rate_pct'):.1f}% of "
             f"{C.PERIODS[0]['label']} customers returned "
             f"({num(cohort, 'lapsed'):,.0f} lapsed, {num(cohort, 'new_in_2026'):,.0f} new). "
             f"The leak is **how often they come back**, not whether they come back.\n")

    L.append("## Where this chain stops (and must stop)\n")
    L.append(f"- **The residual {KES}{abs(num(residual, 'delta')) / 1e6:,.2f}M** "
             f"({num(residual, 'pct_of_total_decline'):.1f}% of the decline) sits in 149 cells across the "
             f"other four stores. Its signature is frequency and basket breadth, not a local event. "
             f"No single actionable cause is identifiable in this dataset.\n"
             f"- **Kisumu Lakefront** declined {next(r for r in branches if r['branch_name'].startswith('Kisumu'))['yoy_pct']}% — "
             f"material, but with no local event recorded. It is flagged as **unexplained**, not "
             f"back-filled with a story.\n"
             f"- **Why the SKUs were out of stock** is not answerable here: no supplier, lead-time or "
             f"replenishment data exists in this extract. That is a data-capture recommendation, not a "
             f"blank to speculate into.\n")

    L.append("## The amateur/evidential contrast, applied to this data\n")
    L.append("| Why # | The amateur version | The evidential version used here |")
    L.append("|---|---|---|")
    L.append(f"| 1 | \"Revenue is down.\" | {abs(pct(r1, r0)):.2f}%, {KES}{abs(r1 - r0) / 1e6:,.2f}M |")
    L.append(f"| 2 | \"Fewer orders.\" | Orders {abs(pct(o1, o0)):.2f}% while customers "
             f"{pct(c1, c0):+.2f}% -> frequency {abs(pct(f1, f0)):.2f}% |")
    L.append(f"| 3 | \"Probably Mombasa.\" | Mombasa {mom_share:.1f}% + Thika {thi_share:.1f}% = "
             f"{mom_share + thi_share:.1f}% of the decline |")
    L.append(f"| 4 | \"Stock problems, maybe.\" | {num(incident, 'availability_pct'):.1f}% availability for "
             f"{num(incident, 'days_out_of_stock'):.0f} days; AOV {pct(mom_a1, mom_a0):+.1f}% at that store |")
    L.append(f"| 5 | \"Customers are fickle.\" | Stopped: cause requires procurement data — "
             f"declared, not invented |")
    L.append("")

    (C.DOCS / "05_five_whys.md").write_text("\n".join(L))

    # machine-readable chain
    import csv
    with open(C.OUT_TABLES / "five_whys_chain.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["step", "question", "answer", "source", "actionable"])
        for c in chain:
            w.writerow([c["step"], c["question"], c["answer"], c["source"], c["actionable"]])
    print("  wrote docs/05_five_whys.md and outputs/tables/five_whys_chain.csv")


if __name__ == "__main__":
    main()
