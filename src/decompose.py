"""Turn one scary headline into ranked, owned problems.

This is the analytical core of the project (Ch. 22). It reads the aggregate
tables that `src/run_sql.py` exported and produces:

  1. the MECHANISM bridge   — Revenue = Customers x Frequency x AOV, attributed
                              with log-mean Divisia plus a sequential
                              sensitivity band, so the ranking is not an
                              artefact of the order you multiply in;
  2. STRUCTURAL contributions — the same total change sliced by branch,
                              category, segment and channel;
  3. the DRIVER PARTITION   — four DISJOINT, non-overlapping cell groups that
                              sum exactly to the total decline, each with an
                              owner, a number, and the evidence behind it.

Reading the code: the three sections map onto the three steps of the method
(mechanism -> structure -> intersect). Nothing here re-aggregates raw rows; SQL
already did that, and this module only does the attribution maths.

Run:  python3 src/decompose.py
"""

import csv
import json
import math
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

sys.path.append(str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

# --------------------------------------------------------------------------- #
# Small IO / numeric helpers                                                   #
# --------------------------------------------------------------------------- #
def load(table):
    """Read an exported query result into a list of dicts."""
    path = C.OUT_TABLES / f"{table}.csv"
    if not path.exists():
        raise SystemExit(f"missing {path} — run src/run_sql.py first")
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def num(row, key, default=0.0):
    v = row.get(key)
    if v in (None, "", "None"):
        return default
    return float(v)


def _cell(v):
    if isinstance(v, float):
        return "" if not math.isfinite(v) else round(v, 2)     # blank, not 'nan'
    return v


def write_table(name, rows, columns):
    path = C.OUT_TABLES / f"{name}.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(columns)
        for r in rows:
            w.writerow([_cell(r[c]) for c in columns])
    print(f"  wrote {name}.csv ({len(rows)} rows)")


def pct(new, old):
    return (new / old - 1.0) * 100.0 if old else float("nan")


# --------------------------------------------------------------------------- #
# 1. Mechanism attribution                                                     #
# --------------------------------------------------------------------------- #
def ldi_decompose(c0, f0, a0, c1, f1, a1):
    """Log-mean Divisia attribution of R = C x F x A.

    Contributions are symmetric and order-independent, and sum exactly to the
    total revenue change. This is the primary method.
    """
    R0, R1 = c0 * f0 * a0, c1 * f1 * a1
    if R0 <= 0 or R1 <= 0 or abs(R1 - R0) < 1e-9:
        return {"customers": 0.0, "frequency": 0.0, "aov": 0.0}
    L = (R1 - R0) / (math.log(R1) - math.log(R0))
    return {
        "customers": L * math.log(c1 / c0),
        "frequency": L * math.log(f1 / f0),
        "aov": L * math.log(a1 / a0),
    }


def sequential_decompose(c0, f0, a0, c1, f1, a1, order):
    """Step-by-step attribution in a given order. Order-dependent, so it is used
    only as a sensitivity band around the log-mean result."""
    v = {"customers": c0, "frequency": f0, "aov": a0}
    target = {"customers": c1, "frequency": f1, "aov": a1}
    running = c0 * f0 * a0
    effects = {}
    for key in order:
        v[key] = target[key]
        nxt = v["customers"] * v["frequency"] * v["aov"]
        effects[key] = nxt - running
        running = nxt
    return effects


def build_mechanism(mech, basket, margin):
    base, cur = mech[0], mech[1]
    # Frequency and AOV are re-derived from the raw counts rather than read from
    # the pre-rounded SQL columns, so that Customers x Frequency x AOV ties back
    # to the reported revenue exactly instead of leaving a rounding residual.
    c0, o0, r0 = num(base, "customers"), num(base, "orders"), num(base, "net_revenue")
    c1, o1, r1 = num(cur, "customers"), num(cur, "orders"), num(cur, "net_revenue")
    f0, a0 = o0 / c0, r0 / o0
    f1, a1 = o1 / c1, r1 / o1

    ldi = ldi_decompose(c0, f0, a0, c1, f1, a1)
    forward = sequential_decompose(c0, f0, a0, c1, f1, a1, ("customers", "frequency", "aov"))
    reverse = sequential_decompose(c0, f0, a0, c1, f1, a1, ("aov", "frequency", "customers"))

    R0, R1 = c0 * f0 * a0, c1 * f1 * a1
    total = R1 - R0

    rows = [
        {"component": "Q3 2025 net revenue (attributed lines)", "effect": R0, "kind": "start"},
        {"component": "Customer count (+{:.1f}%)".format(pct(c1, c0)), "effect": ldi["customers"], "kind": "driver"},
        {"component": "Orders per customer ({:+.1f}%)".format(pct(f1, f0)), "effect": ldi["frequency"], "kind": "driver"},
        {"component": "Average order value ({:+.1f}%)".format(pct(a1, a0)), "effect": ldi["aov"], "kind": "driver"},
        {"component": "Q3 2026 net revenue (attributed lines)", "effect": R1, "kind": "end"},
    ]
    write_table("decomp_mechanism_waterfall", rows, ["component", "effect", "kind"])

    sens = []
    for k in ("customers", "frequency", "aov"):
        vals = [ldi[k], forward[k], reverse[k]]
        sens.append({
            "driver": k,
            "log_mean_divisia": ldi[k],
            "sequential_forward": forward[k],
            "sequential_reverse": reverse[k],
            "band_low": min(vals),
            "band_high": max(vals),
            "range_pct_of_effect": abs(max(vals) - min(vals)) / abs(ldi[k]) * 100 if ldi[k] else 0.0,
        })
    write_table("decomp_mechanism_sensitivity", sens,
                ["driver", "log_mean_divisia", "sequential_forward", "sequential_reverse",
                 "band_low", "band_high", "range_pct_of_effect"])

    b0, b1 = basket[0], basket[1]
    m0, m1 = margin[0], margin[1]
    return {
        "customers_2025": c0, "customers_2026": c1, "customers_yoy_pct": pct(c1, c0),
        "orders_2025": num(base, "orders"), "orders_2026": num(cur, "orders"),
        "frequency_2025": f0, "frequency_2026": f1, "frequency_yoy_pct": pct(f1, f0),
        "aov_2025": a0, "aov_2026": a1, "aov_yoy_pct": pct(a1, a0),
        "revenue_attributed_2025": R0, "revenue_attributed_2026": R1,
        "revenue_attributed_delta": total,
        "revenue_attributed_yoy_pct": pct(R1, R0),
        "ldi": ldi, "sequential_forward": forward, "sequential_reverse": reverse,
        "lines_per_order_2025": num(b0, "lines_per_order"),
        "lines_per_order_2026": num(b1, "lines_per_order"),
        "units_per_order_2025": num(b0, "units_per_order"),
        "units_per_order_2026": num(b1, "units_per_order"),
        "list_price_per_unit_2025": num(b0, "list_price_per_unit"),
        "list_price_per_unit_2026": num(b1, "list_price_per_unit"),
        "net_price_per_unit_2025": num(b0, "net_price_per_unit"),
        "net_price_per_unit_2026": num(b1, "net_price_per_unit"),
        "discount_pct_2025": num(b0, "avg_discount_pct"),
        "discount_pct_2026": num(b1, "avg_discount_pct"),
        "gross_profit_2025": num(m0, "gross_profit"), "gross_profit_2026": num(m1, "gross_profit"),
        "gross_profit_yoy_pct": pct(num(m1, "gross_profit"), num(m0, "gross_profit")),
        "gross_margin_2025": num(m0, "gross_margin_pct"),
        "gross_margin_2026": num(m1, "gross_margin_pct"),
    }


# --------------------------------------------------------------------------- #
# 2. Structure                                                                 #
# --------------------------------------------------------------------------- #
def structural_contribution(rows, label_key, total_delta):
    out = []
    for r in rows:
        delta = num(r, "delta")
        out.append({
            "slice": r[label_key],
            "rev_2025": num(r, "rev_2025"),
            "rev_2026": num(r, "rev_2026"),
            "delta": delta,
            "share_of_decline_pct": (delta / total_delta * 100.0) if total_delta else 0.0,
            "yoy_pct": num(r, "yoy_pct"),
        })
    out.sort(key=lambda x: x["delta"])
    for i, r in enumerate(out, 1):
        r["rank"] = i
    return out


# --------------------------------------------------------------------------- #
# 3. The driver partition — disjoint, sums to the total decline                #
# --------------------------------------------------------------------------- #
# Each cell (branch x category x segment) is assigned to exactly ONE driver, so
# the group totals add up to the whole change with no double counting. The
# attribution RULES are stated explicitly so a reader can challenge them — which
# is the point: a waterfall you cannot audit is a story, not an analysis.
MOMBASA = "Mombasa Nyali"
THIKA = "Thika Road"


def partition_driver(row):
    if row["branch_name"] == MOMBASA:
        return "D1_supply_failure_mombasa"
    if row["branch_name"] == THIKA:
        return "D2_store_access_thika_road"
    if row["category"] == "Beverages":
        return "D3_beverage_price_war"
    return "D4_chain_wide_frequency_erosion"


DRIVER_META = {
    "D1_supply_failure_mombasa": {
        "owner": "Supply Chain & Merchandising",
        "headline": "Two hero Personal Care SKUs out of stock for six weeks at Mombasa Nyali; the damage spread to whole baskets",
    },
    "D2_store_access_thika_road": {
        "owner": "Retail Operations (Thika Road)",
        "headline": "Thika Road footfall cut for the full quarter — visits per customer well below every other store",
    },
    "D3_beverage_price_war": {
        "owner": "Pricing & Category Management",
        "headline": "Beverage promotional depth deepened sharply outside the two affected stores",
    },
    "D4_chain_wide_frequency_erosion": {
        "owner": "CRM / Loyalty & Assortment",
        "headline": "Residual: fewer trips per customer and slimmer baskets right across the chain",
    },
}


def build_partition(cells, total_delta, clean_delta, attributed, branch_mech):
    """`attributed` is the (rev_2025, rev_2026) total of all lines that carry a
    customer identifier. The partition must cover exactly that universe, and the
    difference between it and the clean group total becomes the reconciliation
    line rather than being quietly absorbed."""
    groups = {}
    for row in cells:
        g = partition_driver(row)
        d = groups.setdefault(g, {"rev_2025": 0.0, "rev_2026": 0.0, "cells": 0})
        d["rev_2025"] += num(row, "rev_2025")
        d["rev_2026"] += num(row, "rev_2026")
        d["cells"] += 1

    rows = []
    attributed_delta = 0.0
    for key, d in groups.items():
        delta = d["rev_2026"] - d["rev_2025"]
        attributed_delta += delta
        meta = DRIVER_META[key]
        rows.append({
            "driver": meta["headline"],
            "owner": meta["owner"],
            "cells_in_partition": d["cells"],
            "rev_2025": d["rev_2025"],
            "rev_2026": d["rev_2026"],
            "delta": delta,
            "pct_of_total_decline": delta / total_delta * 100.0 if total_delta else 0.0,
            "yoy_pct": pct(d["rev_2026"], d["rev_2025"]),
        })
    rows.sort(key=lambda r: r["delta"])

    # --- integrity test: the partition must cover the attributed universe --- #
    covered_2025 = sum(d["rev_2025"] for d in groups.values())
    covered_2026 = sum(d["rev_2026"] for d in groups.values())
    gap_2025 = abs(covered_2025 - attributed[0])
    gap_2026 = abs(covered_2026 - attributed[1])
    print(f"  partition coverage gap: {gap_2025:,.2f} / {gap_2026:,.2f} {C.CURRENCY} (should be ~0)")
    if gap_2025 > 1 or gap_2026 > 1:
        raise SystemExit("driver partition does not cover the attributed revenue — fix the rules")

    # reconciliation: revenue with no customer identifier cannot be segmented
    unattributed_delta = clean_delta - attributed_delta
    rows.append({
        "driver": "Reconciliation: revenue with no customer identifier (anonymous walk-ins)",
        "owner": "Data / POS capture",
        "cells_in_partition": 0,
        "rev_2025": float("nan"),
        "rev_2026": float("nan"),
        "delta": unattributed_delta,
        "pct_of_total_decline": unattributed_delta / total_delta * 100.0 if total_delta else 0.0,
        "yoy_pct": float("nan"),
    })
    write_table("decomp_driver_partition", rows,
                ["driver", "owner", "cells_in_partition", "rev_2025", "rev_2026",
                 "delta", "pct_of_total_decline", "yoy_pct"])

    # mechanism signature per driver group (branch-groups only, where we have it)
    mech_by_branch = {}
    for r in branch_mech:
        mech_by_branch.setdefault(r["branch_name"], {})[r["period_key"]] = r
    signatures = {}
    for name in (MOMBASA, THIKA):
        pair = mech_by_branch.get(name, {})
        if C.BASE_PERIOD_KEY in pair and C.CURRENT_PERIOD_KEY in pair:
            a, b = pair[C.BASE_PERIOD_KEY], pair[C.CURRENT_PERIOD_KEY]
            signatures[name] = {
                "customers_yoy_pct": pct(num(b, "customers"), num(a, "customers")),
                "frequency_yoy_pct": pct(num(b, "frequency"), num(a, "frequency")),
                "aov_yoy_pct": pct(num(b, "avg_order_value"), num(a, "avg_order_value")),
            }
    return rows, signatures


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main():
    C.ensure_dirs()
    print("Decomposing the revenue change (mechanism -> structure -> intersect)")

    mech = load("mechanism_by_period")
    basket = load("mechanism_basket_detail")
    margin = load("mechanism_margin_by_period")
    qc = load("qc_rows_by_period")
    disc = load("pricing_discount_cost")
    cohort = load("cohort_retention_summary")[0]
    cells = load("crosscut_branch_category_segment_full")
    branch_mech = load("structure_branch_mechanism")

    total_2025 = num(qc[0], "net_revenue") if qc[0]["period_key"] == C.BASE_PERIOD_KEY else num(qc[1], "net_revenue")
    total_2026 = num(qc[1], "net_revenue") if qc[1]["period_key"] == C.CURRENT_PERIOD_KEY else num(qc[0], "net_revenue")
    clean_delta = total_2026 - total_2025

    # ---- 1. mechanism ----------------------------------------------------- #
    k = build_mechanism(mech, basket, margin)
    k["revenue_total_2025"] = total_2025
    k["revenue_total_2026"] = total_2026
    k["revenue_total_delta"] = clean_delta
    k["revenue_total_yoy_pct"] = pct(total_2026, total_2025)

    # ---- 2. structure ----------------------------------------------------- #
    structure = {
        "branch": structural_contribution(load("structure_by_branch"), "branch_name", clean_delta),
        "category": structural_contribution(load("structure_by_category"), "category", clean_delta),
        "segment": structural_contribution(load("structure_by_segment"), "customer_segment", clean_delta),
        "channel": structural_contribution(load("structure_by_channel"), "channel", clean_delta),
    }
    for name, rows in structure.items():
        write_table(f"decomp_structure_{name}", rows,
                    ["rank", "slice", "rev_2025", "rev_2026", "delta",
                     "share_of_decline_pct", "yoy_pct"])

    # ---- 3. intersect / partition ---------------------------------------- #
    partition, signatures = build_partition(
        cells, clean_delta, clean_delta,
        (k["revenue_attributed_2025"], k["revenue_attributed_2026"]), branch_mech)

    leaders = sorted(cells, key=lambda r: num(r, "rev_2026") - num(r, "rev_2025"))
    leader_rows = [{
        "rank": i,
        "cell": f"{r['branch_name']} | {r['category']} | {r['segment']}",
        "rev_2025": num(r, "rev_2025"),
        "rev_2026": num(r, "rev_2026"),
        "delta": num(r, "rev_2026") - num(r, "rev_2025"),
        "pct_of_total_decline": (num(r, "rev_2026") - num(r, "rev_2025")) / clean_delta * 100.0,
        "yoy_pct": pct(num(r, "rev_2026"), num(r, "rev_2025")),
    } for i, r in enumerate(leaders[:15], 1)]
    write_table("decomp_cell_leaders", leader_rows,
                ["rank", "cell", "rev_2025", "rev_2026", "delta",
                 "pct_of_total_decline", "yoy_pct"])

    # ---- KPIs for the dashboard / report --------------------------------- #
    stockout = load("stockout_incident_vs_rest")
    so_incident = next((r for r in stockout
                        if r["scope"].startswith("BR05") and r["window_flag"].startswith("Inside")), None)
    gp0, gp1 = k["gross_profit_2025"], k["gross_profit_2026"]

    kpis = {
        "company": C.COMPANY,
        "base_period": C.PERIODS[0]["label"],
        "current_period": C.PERIODS[1]["label"],
        "currency": C.CURRENCY,
        "headline": {
            "revenue_2025": total_2025, "revenue_2026": total_2026,
            "revenue_delta": clean_delta, "revenue_yoy_pct": k["revenue_total_yoy_pct"],
            "gross_profit_delta": gp1 - gp0,
            "gross_margin_pp_change": k["gross_margin_2026"] - k["gross_margin_2025"],
        },
        "mechanism": k,
        "structure": structure,
        "driver_partition": partition,
        "driver_mechanism_signatures": signatures,
        "cohort": {
            "customers_2025q3": num(cohort, "customers_2025q3"),
            "customers_2026q3": num(cohort, "customers_2026q3"),
            "returned": num(cohort, "returned"),
            "lapsed": num(cohort, "lapsed"),
            "new_in_2026": num(cohort, "new_in_2026"),
            "return_rate_pct": num(cohort, "return_rate_pct"),
        },
        "pricing": {
            "discount_pct_2025": num(disc[0], "discount_pct_of_gross"),
            "discount_pct_2026": num(disc[1], "discount_pct_of_gross"),
            "gross_revenue_2026": num(disc[1], "gross_revenue"),
            "discount_given_2025": num(disc[0], "discount_given"),
            "discount_given_2026": num(disc[1], "discount_given"),
            "extra_discount_cost_2026": num(disc[1], "gross_revenue")
            * (num(disc[1], "discount_pct_of_gross") - num(disc[0], "discount_pct_of_gross")) / 100.0,
        },
        "stockout": {
            "availability_pct_in_incident": num(so_incident, "availability_pct") if so_incident else None,
            "days_out_of_stock_in_incident": num(so_incident, "days_out_of_stock") if so_incident else None,
            "observations_in_incident": num(so_incident, "observations") if so_incident else None,
        },
        "cell_leaders": leader_rows[:5],
    }
    (C.PROJECT_ROOT / "outputs" / "kpis.json").write_text(json.dumps(kpis, indent=2))
    print("  wrote outputs/kpis.json")

    # ---- console summary -------------------------------------------------- #
    print(f"\n  HEADLINE  {total_2025:,.0f} -> {total_2026:,.0f} "
          f"({k['revenue_total_yoy_pct']:+.2f}%)")
    print("  MECHANISM (log-mean Divisia, KSh):")
    for kk in ("customers", "frequency", "aov"):
        print(f"    {kk:10s} {k['ldi'][kk]:>14,.0f}   (yoy {k['%s_yoy_pct' % kk]:+.2f}%)")
    print("  DRIVER PARTITION (disjoint, sums to the total):")
    for r in partition:
        print(f"    {r['owner']:38s} {r['delta']:>14,.0f}  {r['pct_of_total_decline']:>6.1f}%")
    print("\nDone. Next: python3 src/five_whys.py / src/make_figures.py")


if __name__ == "__main__":
    main()
