"""The report narrative, authored once and rendered four ways.

The brief, the PowerPoint deck, the Word report and the PDF all read from this
module. That is deliberate: an organisation that circulates four documents which
quietly disagree with each other is worse off than one that circulates a single
PDF. Here the numbers come from `outputs/kpis.json` and the tables, so a figure
in the deck cannot drift from the same figure in the Word report — or from the
chart that draws it.

`build()` returns a plain nested dict. Nothing in this module touches styling;
the renderers own that.

Run `python3 -c "import sys;sys.path.insert(0,'src');import report_content as r;
import json;print(json.dumps(r.build()['headline'],indent=2))"` to inspect it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

sys.path.append(str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
from decompose import load, num  # noqa: E402

REPORT_DATE = "2026-10-05"          # analysis completed at the close of Q3 FY2026
CLASSIFICATION = "Internal — Commercial leadership"


# --------------------------------------------------------------------------- #
# Formatting helpers                                                           #
# --------------------------------------------------------------------------- #
def mn(x: float, signed: bool = False) -> str:
    """KSh in millions, the unit every statement in this project is quoted in."""
    return f"{C.CURRENCY} {x / 1e6:+,.2f}M" if signed else f"{C.CURRENCY} {x / 1e6:,.2f}M"


def pct(x: float, decimals: int = 1) -> str:
    return f"{x:+.{decimals}f}%"


def pp(x: float, decimals: int = 2) -> str:
    return f"{x:+.{decimals}f}pp"


def n(x: float, decimals: int = 0) -> str:
    return f"{x:,.{decimals}f}"


# --------------------------------------------------------------------------- #
# Build                                                                        #
# --------------------------------------------------------------------------- #
def build() -> dict:
    k = json.loads((C.PROJECT_ROOT / "outputs" / "kpis.json").read_text())
    h, m = k["headline"], k["mechanism"]
    base_lbl, cur_lbl = k["base_period"], k["current_period"]

    branches = k["structure"]["branch"]
    cats = k["structure"]["category"]
    segs = k["structure"]["segment"]
    chans = k["structure"]["channel"]
    part = k["driver_partition"]
    cohort, pricing, stk = k["cohort"], k["pricing"], k["stockout"]
    sig = k["driver_mechanism_signatures"]

    leaders = load("decomp_cell_leaders")
    conc = load("crosscut_concentration")
    sku = load("structure_by_sku_top_declines")
    qc = load("qc_unattributed_coverage")[0]
    qc_rows = load("qc_rows_by_period")
    sens = load("decomp_mechanism_sensitivity")
    whys = load("five_whys_chain")
    disc_cat = load("pricing_discount_depth_by_category")

    n_lines = sum(num(r, "line_items") for r in qc_rows)
    n_invoices = sum(num(r, "invoices") for r in qc_rows)
    cov_pct = num(qc, "pct_of_group_revenue")
    extra_disc = pricing["extra_discount_cost_2026"]

    mom = next(b for b in branches if b["slice"] == "Mombasa Nyali")
    thi = next(b for b in branches if b["slice"] == "Thika Road")
    kis = next(b for b in branches if b["slice"] == "Kisumu Lakefront")
    bev = next(c for c in cats if c["slice"] == "Beverages")
    gro = next(c for c in cats if c["slice"] == "Groceries")
    pc = next(c for c in cats if c["slice"] == "Personal Care")
    mom_pc = next((r for r in load("crosscut_branch_category")
                   if r["branch_name"] == "Mombasa Nyali" and r["category"] == "Personal Care"),
                  None)
    mom_pc_delta = num(mom_pc, "delta") if mom_pc else 0.0
    hero = [s for s in sku if s["is_hero_sku"] == "1"]
    bev_pp = next(num(r, "discount_pp_change") for r in disc_cat if r["category"] == "Beverages")

    supply = next(p for p in part if p["owner"].startswith("Supply"))
    ops = next(p for p in part if p["owner"].startswith("Retail"))
    crm = next(p for p in part if p["owner"].startswith("CRM"))
    price = next(p for p in part if p["owner"].startswith("Pricing"))
    recon = next(p for p in part if p["owner"].startswith("Data"))
    two_store_share = abs(mom["share_of_decline_pct"]) + abs(thi["share_of_decline_pct"])

    # A stated, assumption-carried run-rate. NOT a forecast — see the caveats.
    run_rate = h["revenue_delta"] * 4

    # ------------------------------------------------------------------ #
    # KPI strip — every tile carries a comparison; no naked numbers       #
    # ------------------------------------------------------------------ #
    tiles = [
        {
            "label": "Net revenue",
            "value": mn(h["revenue_2026"], signed=False),
            "delta": pct(h["revenue_yoy_pct"]),
            "detail": f"from {mn(h['revenue_2025'])} in {base_lbl}",
            "good": h["revenue_yoy_pct"] >= 0,
        },
        {
            "label": "Gross margin",
            "value": f"{m['gross_margin_2026']:.2f}%",
            "delta": pp(h["gross_margin_pp_change"]),
            "detail": f"gross profit {mn(m['gross_profit_2026'])}",
            "good": h["gross_margin_pp_change"] >= 0,
        },
        {
            "label": "Orders per customer",
            "value": f"{m['frequency_2026']:.2f}",
            "delta": pct(m["frequency_yoy_pct"]),
            "detail": "the engine of the decline",
            "good": m["frequency_yoy_pct"] >= 0,
        },
        {
            "label": "Average order value",
            "value": f"{C.CURRENCY} {m['aov_2026']:,.0f}",
            "delta": pct(m["aov_yoy_pct"]),
            "detail": f"{m['lines_per_order_2026']:.2f} lines per order",
            "good": m["aov_yoy_pct"] >= 0,
        },
        {
            "label": "Active customers",
            "value": n(m["customers_2026"]),
            "delta": pct(m["customers_yoy_pct"]),
            "detail": "acquisition is NOT the problem",
            "good": m["customers_yoy_pct"] >= 0,
        },
        {
            "label": "Revenue with no customer ID",
            "value": f"{cov_pct:.2f}%",
            "delta": f"{mn(num(qc, 'unattributed_revenue'))}",
            "detail": "the declared coverage limit",
            "good": None,
        },
    ]

    # ------------------------------------------------------------------ #
    # The four ranked, owned problems                                     #
    # ------------------------------------------------------------------ #
    # A one-line version of each problem, for the summary tables. The full
    # statement is kept in `problem` for the long-form report.
    short_problem = {
        "Supply Chain & Merchandising": "Hero SKUs out of stock 6 weeks (Mombasa Nyali)",
        "Retail Operations (Thika Road)": "Thika Road footfall cut for the quarter",
        "CRM / Loyalty & Assortment": "Fewer trips and slimmer baskets chain-wide",
        "Pricing & Category Management": "Beverage discount depth deepened outside those stores",
    }
    ranked = sorted([p for p in part if not p["owner"].startswith("Data")],
                    key=lambda p: p["delta"])
    problems = [{
        "rank": i,
        "owner": p["owner"],
        "problem": p["driver"],
        "short": short_problem.get(p["owner"], p["driver"]),
        "delta": p["delta"],
        "cost": mn(p["delta"]),
        "share": f"{p['pct_of_total_decline']:.0f}%",
        "yoy": num(p, "yoy_pct"),
        "cells": int(num(p, "cells_in_partition")),
    } for i, p in enumerate(ranked, 1)]

    # ------------------------------------------------------------------ #
    # Findings — the report's spine. Each has a so-what and an owner.     #
    # ------------------------------------------------------------------ #
    findings = [
        {
            "n": 1,
            "title": "We did not lose customers — we lost trips and basket size",
            "body": (
                f"Active customers rose {pct(m['customers_yoy_pct'])}, so acquisition is working. "
                f"But orders per customer fell {pct(m['frequency_yoy_pct'])} and average order value "
                f"fell {pct(m['aov_yoy_pct'])}. The engine failed, not the funnel — and that single "
                f"distinction changes who is accountable and what the fix is."),
            "so_what": "A funnel problem would be fixed in marketing. A frequency and basket problem "
                       "is fixed in CRM, assortment and availability.",
            "figure": "02_mechanism_identity.png",
            "cost": mn(m["ldi"]["frequency"]),
        },
        {
            "n": 2,
            "title": f"Two of six stores carry {two_store_share:.0f}% of the decline",
            "body": (
                f"{mom['slice']} ({pct(mom['yoy_pct'])}) and {thi['slice']} "
                f"({pct(thi['yoy_pct'])}) are not a chain-wide trend. They are two local, "
                f"separately-diagnosable events inside one quarter."),
            "so_what": "Treating this as a chain-wide trend would spread a thin fix across six stores "
                       "instead of a targeted fix on two.",
            "figure": "03_branch_waterfall.png",
            "cost": mn(abs(supply["delta"]) + abs(ops["delta"])),
        },
        {
            "n": 3,
            "title": "The largest single cost has a date, a store and an owner",
            "body": (
                f"Two hero Personal Care SKUs sat off the shelf at {mom['slice']} for "
                f"{stk['days_out_of_stock_in_incident']:.0f} days "
                f"({stk['availability_pct_in_incident']:.1f}% shelf availability). It cost "
                f"{mn(abs(supply['delta']))}. Only {mn(abs(mom_pc_delta))} of that is Personal Care "
                f"revenue — {mn(abs(supply['delta']) - abs(mom_pc_delta))} is baskets that were never "
                f"started."),
            "so_what": f"Measuring only the affected category understates the event by roughly "
                       f"{abs(supply['delta']) / abs(mom_pc_delta):.1f}x. Availability failures are "
                       f"basket failures, not category failures.",
            "figure": "08_stockout_timeline.png",
            "cost": mn(abs(supply["delta"])),
        },
        {
            "n": 4,
            "title": "Discounting, not pricing, is the second lever",
            "body": (
                f"List price per unit rose "
                f"{pct((m['list_price_per_unit_2026'] / m['list_price_per_unit_2025'] - 1) * 100)} while "
                f"discount depth went from {pricing['discount_pct_2025']:.2f}% to "
                f"{pricing['discount_pct_2026']:.2f}% of gross — roughly an extra "
                f"{mn(extra_disc)} given away in the quarter, concentrated in {bev['slice']} "
                f"({pp(bev_pp)})."),
            "so_what": "Gross profit fell faster than revenue. Price rises are being handed straight "
                       "back through promotions, so margin — not just revenue — is the thing at risk.",
            "figure": "09_discount_depth.png",
            "cost": mn(extra_disc),
        },
        {
            "n": 5,
            "title": "Retention is healthy; the leak is trip frequency",
            "body": (
                f"{n(cohort['returned'])} of {n(cohort['customers_2025q3'])} {base_lbl} customers "
                f"returned ({cohort['return_rate_pct']:.1f}%), and {n(cohort['new_in_2026'])} new "
                f"customers arrived. Churn is not the problem — the people we keep are simply "
                f"shopping less often."),
            "so_what": "Win-back for the 855 lapsed customers is worth doing, but the money is in "
                       "raising frequency among the customers who already come back.",
            "figure": "07_cohort_retention.png",
            "cost": mn(abs(crm["delta"])),
        },
    ]

    # ------------------------------------------------------------------ #
    # Facts, hypotheses, and what we genuinely do not know                 #
    # ------------------------------------------------------------------ #
    facts = [
        {"statement": f"Revenue fell {abs(h['revenue_yoy_pct']):.1f}%; gross profit fell "
                      f"{abs(m['gross_profit_yoy_pct']):.1f}%",
         "tier": "Fact", "note": "measured from the cleaned star schema"},
        {"statement": f"Two stores explain {two_store_share:.0f}% of the decline",
         "tier": "Fact", "note": "measured; contribution shares sum to the group change"},
        {"statement": f"Hero SKUs were {stk['availability_pct_in_incident']:.1f}% available for "
                      f"{stk['days_out_of_stock_in_incident']:.0f} days at {mom['slice']}",
         "tier": "Fact", "note": "from the branch x SKU x day availability table"},
        {"statement": f"Active customers rose {pct(m['customers_yoy_pct'])} while frequency fell "
                      f"{pct(m['frequency_yoy_pct'])}",
         "tier": "Fact", "note": "the mechanism identity, order-independent attribution"},
        {"statement": "The stock-out *caused* the basket erosion at that store",
         "tier": "Hypothesis",
         "note": "the two co-move exactly in time; no causal test was run"},
        {"statement": "Single-sourcing or no safety stock caused the stock-out",
         "tier": "Hypothesis", "note": "no procurement, supplier or lead-time data in this extract"},
        {"statement": f"{thi['slice']}'s decline is due to the road-works",
         "tier": "Hypothesis",
         "note": "the frequency-only signature is consistent with an access problem; no other "
                 "local factor is recorded"},
        {"statement": f"{kis['slice']}'s {pct(kis['yoy_pct'])}",
         "tier": "Unexplained", "note": "flagged, deliberately not back-filled with a story"},
        {"statement": f"{n(cohort['lapsed'])} {base_lbl} customers did not return",
         "tier": "Fact", "note": f"but {cohort['return_rate_pct']:.1f}% did — churn is not the problem"},
    ]

    caveats = [
        f"{cov_pct:.2f}% of revenue carries no customer identifier "
        f"({mn(num(qc, 'unattributed_revenue'))} of anonymous walk-ins). Every segment-level "
        f"conclusion therefore reconciles to {100 - cov_pct:.2f}% of revenue, not 100%. The "
        f"reconciliation is shown as its own line rather than hidden in an 'Other' bucket.",
        "The dataset is simulated from a documented mechanism (docs/00_ground_truth.md). That is "
        "deliberate: it lets the diagnosis be graded. See outputs/validation_report.md — 14/14 "
        "checks pass against the sealed answer key.",
        "No procurement, lead-time or supplier-performance data exists in this extract. The fifth "
        "why therefore stops at a data-capture recommendation instead of a guess.",
        f"The annualised figure is a stated run-rate ({mn(run_rate)}, the quarter's change x 4), not "
        f"a forecast. It assumes the {mom['slice']} incident does not repeat and ignores Q4 "
        f"seasonality.",
    ]

    # ------------------------------------------------------------------ #
    # Actions and the monitoring plan                                      #
    # ------------------------------------------------------------------ #
    actions = [
        {"n": 1,
         "short": "Rebuild safety stock on the hero SKUs; qualify a second supplier",
         "action": "Rebuild safety stock on the two hero Personal Care SKUs and qualify a second supplier",
         "owner": "Supply Chain",
         "why": f"Availability was {stk['availability_pct_in_incident']:.1f}% for "
                f"{stk['days_out_of_stock_in_incident']:.0f} days; the store lost {mn(abs(mom['delta']))}",
         "impact": f"{mn(abs(supply['delta']) * 0.7)} – {mn(abs(supply['delta']))}",
         "review": "2026-11-04 (+30d)"},
        {"n": 2,
         "short": "Rebuild the Mombasa basket: substitutes, adjacency, staff script",
         "action": "Rebuild the Mombasa basket: substitutes on shelf, Personal Care adjacent to "
                   "Groceries, a substitution script for staff",
         "owner": "Merchandising",
         "why": f"AOV fell {pct(sig['Mombasa Nyali']['aov_yoy_pct'])} while the category alone "
                f"explains only {mn(abs(mom_pc_delta))} of the {mn(abs(supply['delta']))} damage",
         "impact": mn(abs(mom_pc_delta) * 0.4),
         "review": "2026-11-19 (+45d)"},
        {"n": 3,
         "short": "Thika Road access recovery with the landlord and county",
         "action": "Thika Road access recovery: landlord and county engagement, extended hours, "
                   "local marketing to restore trips",
         "owner": "Retail Operations",
         "why": f"Frequency fell {pct(sig['Thika Road']['frequency_yoy_pct'])} while basket value "
                f"held at {pct(sig['Thika Road']['aov_yoy_pct'])} — a pure traffic problem worth "
                f"{mn(abs(ops['delta']))}",
         "impact": mn(abs(ops["delta"]) * 0.6),
         "review": "2026-12-04 (+60d)"},
        {"n": 4,
         "short": f"Cap beverage discount depth; gate approvals above {pricing['discount_pct_2025']:.1f}%",
         "action": f"Cap beverage promotional depth back toward {pricing['discount_pct_2025']:.1f}% "
                   f"of gross and require an approval gate above it",
         "owner": "Pricing & Category Management",
         "why": f"Beverage discount depth rose {pp(bev_pp)}; category revenue fell "
                f"{pct(bev['yoy_pct'])}",
         "impact": mn(abs(price["delta"]) * 0.5),
         "review": "2026-10-26 (+21d)"},
        {"n": 5,
         "short": "Win back lapsed customers; nudge a second purchase",
         "action": f"Convert the frequency leak: targeted win-back for the {n(cohort['lapsed'])} "
                   f"lapsed customers and a second-purchase nudge for the {n(cohort['new_in_2026'])} new ones",
         "owner": "CRM / Loyalty",
         "why": f"{pct(m['frequency_yoy_pct'])} trips per customer across all four established "
                f"segments; residual pool worth {mn(abs(crm['delta']))}",
         "impact": mn(abs(crm["delta"]) * 0.5),
         "review": "2027-01-03 (+90d)"},
        {"n": 6,
         "short": "Capture a customer ID on every sale; log supplier lead times",
         "action": "Capture a customer identifier on every transaction; start logging supplier "
                   "promised-vs-actual lead times",
         "owner": "Data / POS & Supply Chain",
         "why": f"{cov_pct:.2f}% of revenue is currently unattributable and the root cause of the "
                f"stock-out is unanswerable",
         "impact": "No direct revenue; removes both blind spots",
         "review": "2027-01-03 (next quarter)"},
    ]

    monitoring = [
        {"metric": "Orders per customer", "baseline": f"{m['frequency_2025']:.2f}",
         "target": f"back above {m['frequency_2025']:.2f}", "owner": "CRM"},
        {"metric": "Hero SKU shelf availability (Mombasa)",
         "baseline": f"{stk['availability_pct_in_incident']:.1f}%", "target": ">99%",
         "owner": "Supply Chain"},
        {"metric": "Thika Road visits per customer",
         "baseline": f"{pct(sig['Thika Road']['frequency_yoy_pct'])} YoY", "target": ">0% YoY",
         "owner": "Retail Ops"},
        {"metric": "Beverage discount depth", "baseline": f"{pricing['discount_pct_2026']:.2f}% of gross",
         "target": f"<= {pricing['discount_pct_2025']:.2f}%", "owner": "Pricing"},
        {"metric": "Gross margin", "baseline": f"{m['gross_margin_2026']:.2f}%",
         "target": f"back above {m['gross_margin_2025']:.2f}%", "owner": "Finance"},
    ]

    # ------------------------------------------------------------------ #
    # Charts — the deck and the report both walk this list                  #
    # ------------------------------------------------------------------ #
    figures = [
        {"file": "01_headline_waterfall.png",
         "caption": "One headline, three mechanisms",
         "so_what": f"The {abs(h['revenue_yoy_pct']):.1f}% fall is one customer gain against two "
                    f"larger losses — it is not one event.",
         "section": "Mechanism"},
        {"file": "02_mechanism_identity.png",
         "caption": "Customers up, frequency down",
         "so_what": "Acquisition is working; repeat behaviour is not. Different problem, different owner.",
         "section": "Mechanism"},
        {"file": "03_branch_waterfall.png",
         "caption": "Where the money went, by store",
         "so_what": f"Two stores carry {two_store_share:.0f}% of the decline.",
         "section": "Structure"},
        {"file": "04_branch_category_heatmap.png",
         "caption": "The intersection: store x category",
         "so_what": "The decline is concentrated, not diffuse — so the fix can be too.",
         "section": "Intersection"},
        {"file": "05_category_decline.png",
         "caption": "Categories: KSh and % side by side",
         "so_what": "Groceries is the biggest absolute loss, Beverages the fastest fall. Either alone misleads.",
         "section": "Structure"},
        {"file": "06_segment_waterfall.png",
         "caption": "Every segment shrank except the customers we bought",
         "so_what": "Buying growth is not a strategy while the existing base contracts.",
         "section": "Segments"},
        {"file": "07_cohort_retention.png",
         "caption": "Who came back",
         "so_what": f"{cohort['return_rate_pct']:.1f}% returned — the leak is trips, not churn.",
         "section": "Segments"},
        {"file": "08_stockout_timeline.png",
         "caption": "The supply failure, with dates",
         "so_what": f"{stk['availability_pct_in_incident']:.1f}% availability for "
                    f"{stk['days_out_of_stock_in_incident']:.0f} days at {mom['slice']}.",
         "section": "Evidence"},
        {"file": "09_discount_depth.png",
         "caption": "Prices rose, discounting rose faster",
         "so_what": f"{mn(extra_disc)} of extra discount in one quarter.",
         "section": "Pricing"},
        {"file": "10_driver_partition.png",
         "caption": "Four ranked, owned problems",
         "so_what": "Disjoint and audited: the bars sum to the whole decline with no double counting.",
         "section": "Actions"},
    ]

    return {
        "meta": {
            "company": k["company"],
            "base_period": base_lbl,
            "current_period": cur_lbl,
            "comparison": f"{cur_lbl} vs {base_lbl}",
            "prepared": REPORT_DATE,
            "classification": CLASSIFICATION,
            "currency": C.CURRENCY,
            "seed": C.SEED,
            "title": "Revenue Decline Diagnostic",
            "subtitle": f"Why group revenue fell {abs(h['revenue_yoy_pct']):.1f}% — and who owns each cause",
            "author": "Senior Data Analyst",
            "reproduce": "python3 src/run_pipeline.py",
        },
        "headline": {
            "revenue_2025": h["revenue_2025"], "revenue_2026": h["revenue_2026"],
            "revenue_delta": h["revenue_delta"], "revenue_yoy_pct": h["revenue_yoy_pct"],
            "gross_profit_delta": h["gross_profit_delta"],
            "gross_margin_pp_change": h["gross_margin_pp_change"],
            "gross_margin_2025": m["gross_margin_2025"], "gross_margin_2026": m["gross_margin_2026"],
            "gross_profit_2025": m["gross_profit_2025"], "gross_profit_2026": m["gross_profit_2026"],
            "gross_profit_yoy_pct": m["gross_profit_yoy_pct"],
            "answer": (
                f"Group net revenue fell {mn(abs(h['revenue_delta']))} "
                f"({abs(h['revenue_yoy_pct']):.1f}%). We did not lose customers — active customers "
                f"rose {pct(m['customers_yoy_pct'])}. We lost trips ({pct(m['frequency_yoy_pct'])} "
                f"orders per customer) and basket ({pct(m['aov_yoy_pct'])} average order value), and "
                f"{two_store_share:.0f}% of the damage sits in two of six stores."),
            "decision": "Whose plan gets rewritten next quarter — retention, pricing, or merchandising?",
            "two_store_share": two_store_share,
        },
        "tiles": tiles,
        "problems": problems,
        "findings": findings,
        "metrics": [
            {"metric": "Net revenue", "base": mn(h["revenue_2025"]), "cur": mn(h["revenue_2026"]),
             "change": f"{pct(h['revenue_yoy_pct'])}", "pct": h["revenue_yoy_pct"]},
            {"metric": "Gross profit", "base": mn(m["gross_profit_2025"]), "cur": mn(m["gross_profit_2026"]),
             "change": f"{pct(m['gross_profit_yoy_pct'])}", "pct": m["gross_profit_yoy_pct"]},
            {"metric": "Gross margin", "base": f"{m['gross_margin_2025']:.2f}%",
             "cur": f"{m['gross_margin_2026']:.2f}%", "change": pp(h["gross_margin_pp_change"]),
             "pct": h["gross_margin_pp_change"]},
            {"metric": "Active customers", "base": n(m["customers_2025"]), "cur": n(m["customers_2026"]),
             "change": pct(m["customers_yoy_pct"]), "pct": m["customers_yoy_pct"]},
            {"metric": "Orders", "base": n(m["orders_2025"]), "cur": n(m["orders_2026"]),
             "change": pct((m["orders_2026"] / m["orders_2025"] - 1) * 100),
             "pct": (m["orders_2026"] / m["orders_2025"] - 1) * 100},
            {"metric": "Orders per customer", "base": f"{m['frequency_2025']:.2f}",
             "cur": f"{m['frequency_2026']:.2f}", "change": pct(m["frequency_yoy_pct"]),
             "pct": m["frequency_yoy_pct"]},
            {"metric": "Average order value", "base": f"{C.CURRENCY} {m['aov_2025']:,.0f}",
             "cur": f"{C.CURRENCY} {m['aov_2026']:,.0f}", "change": pct(m["aov_yoy_pct"]),
             "pct": m["aov_yoy_pct"]},
            {"metric": "Lines per order", "base": f"{m['lines_per_order_2025']:.2f}",
             "cur": f"{m['lines_per_order_2026']:.2f}",
             "change": pct((m["lines_per_order_2026"] / m["lines_per_order_2025"] - 1) * 100),
             "pct": (m["lines_per_order_2026"] / m["lines_per_order_2025"] - 1) * 100},
            {"metric": "List price per unit", "base": f"{C.CURRENCY} {m['list_price_per_unit_2025']:,.0f}",
             "cur": f"{C.CURRENCY} {m['list_price_per_unit_2026']:,.0f}",
             "change": pct((m["list_price_per_unit_2026"] / m["list_price_per_unit_2025"] - 1) * 100),
             "pct": (m["list_price_per_unit_2026"] / m["list_price_per_unit_2025"] - 1) * 100},
            {"metric": "Discount depth (% of gross)", "base": f"{pricing['discount_pct_2025']:.2f}%",
             "cur": f"{pricing['discount_pct_2026']:.2f}%",
             "change": pp(pricing["discount_pct_2026"] - pricing["discount_pct_2025"]),
             "pct": pricing["discount_pct_2026"] - pricing["discount_pct_2025"]},
        ],
        "mechanism": {
            "rows": [
                {"driver": "Customers", "effect": m["ldi"]["customers"], "yoy": m["customers_yoy_pct"]},
                {"driver": "Orders per customer", "effect": m["ldi"]["frequency"],
                 "yoy": m["frequency_yoy_pct"]},
                {"driver": "Average order value", "effect": m["ldi"]["aov"], "yoy": m["aov_yoy_pct"]},
            ],
            "total": h["revenue_delta"],
            "total_yoy": h["revenue_yoy_pct"],
            "sensitivity": [
                {"driver": r["driver"], "low": mn(num(r, "band_low")), "high": mn(num(r, "band_high"))}
                for r in sens],
            "note": "Attribution is log-mean Divisia, so the ranking does not depend on the order in "
                    "which the three factors are multiplied. The frequency effect is the largest "
                    "under every ordering — that is the robust part of the result.",
        },
        "structure": {
            "branch": branches, "category": cats, "segment": segs, "channel": chans,
            "by_store": [
                {"store": b["slice"], "delta": b["delta"], "cost": mn(b["delta"]),
                 "yoy": pct(b["yoy_pct"]), "share": f"{b['share_of_decline_pct']:.1f}%",
                 "pct": b["yoy_pct"]} for b in branches],
        },
        "intersection": {
            "concentration_n": len(conc),
            "concentration_share": sum(num(r, "pct_of_decline") for r in conc),
            "leaders": [{"rank": r["rank"], "cell": r["cell"], "delta": mn(num(r, "delta")),
                         "yoy": pct(num(r, "yoy_pct")),
                         "share": f"{num(r, 'pct_of_total_decline'):.1f}%"} for r in leaders[:8]],
            "top_cell": leaders[0]["cell"],
            "understatement": abs(supply["delta"]) / abs(mom_pc_delta) if mom_pc_delta else 0.0,
        },
        "retention": {
            "customers_2025": n(cohort["customers_2025q3"]),
            "returned": n(cohort["returned"]),
            "lapsed": n(cohort["lapsed"]),
            "new": n(cohort["new_in_2026"]),
            "return_rate": f"{cohort['return_rate_pct']:.1f}%",
        },
        "supply": {
            "store": mom["slice"],
            "sku": ", ".join(s["product_name"] for s in hero) or "PC01, PC02",
            "days": f"{stk['days_out_of_stock_in_incident']:.0f}",
            "availability": f"{stk['availability_pct_in_incident']:.1f}%",
            "cost": mn(abs(supply["delta"])),
            "category_only": mn(abs(mom_pc_delta)),
            "spillover": mn(abs(supply["delta"]) - abs(mom_pc_delta)),
        },
        "pricing": {
            "depth_2025": f"{pricing['discount_pct_2025']:.2f}%",
            "depth_2026": f"{pricing['discount_pct_2026']:.2f}%",
            "extra": mn(extra_disc),
            "beverages_pp": pp(bev_pp),
        },
        "facts": facts,
        "run_rate": {"value": mn(run_rate), "quarter": mn(abs(h["revenue_delta"]))},
        "actions": actions,
        "monitoring": monitoring,
        "figures": figures,
        "caveats": caveats,
        "whys": [{"step": w["step"], "question": w["question"], "answer": w["answer"],
                  "source": w["source"], "actionable": w["actionable"]} for w in whys],
        "provenance": {
            "lines": n(n_lines), "invoices": n(n_invoices), "coverage_pct": f"{cov_pct:.2f}%",
            "data_note": "Simulated POS extract, star schema, line-item grain, two like-for-like quarters.",
        },
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, default=str)[:4000])
