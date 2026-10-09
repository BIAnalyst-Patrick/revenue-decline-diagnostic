"""Grade the diagnostic against the generator's answer key.

This is the part most portfolio projects cannot do. Because the data is
simulated from `config.STORY`, we know what the true drivers were — so we can
ask the uncomfortable question: did the analysis actually find them?

Each check is a falsifiable claim with a tolerance. A failing check means the
analysis (not the data) is wrong, and the script exits non-zero.

Outputs: outputs/validation_report.md
Run:     python3 src/validate_against_truth.py
"""

import json
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

sys.path.append(str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
from decompose import load, num  # noqa: E402


def check(name, expected, actual, tol, unit="", note=""):
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        ok = abs(actual - expected) <= tol
    else:
        ok = expected == actual
    return {"check": name, "expected": expected, "actual": actual,
            "tolerance": tol, "unit": unit, "pass": bool(ok), "note": note}


def main():
    C.ensure_dirs()
    kpis = json.loads((C.PROJECT_ROOT / "outputs" / "kpis.json").read_text())
    branch = load("decomp_structure_branch")
    category = load("decomp_structure_category")
    cohort = load("cohort_retention_summary")[0]
    cohort_seg = load("cohort_retention_by_segment")
    part = [p for p in kpis["driver_partition"]
            if not p["driver"].lower().startswith("reconciliation")]
    story = C.STORY["mechanism_target"]

    m = kpis["mechanism"]
    worst_branch = min(branch, key=lambda r: num(r, "delta"))
    second_branch = sorted(branch, key=lambda r: num(r, "delta"))[1]
    worst_cat = min([c for c in category if c["slice"] != "Unclassified"],
                    key=lambda r: num(r, "yoy_pct"))
    top_driver = min(part, key=lambda p: p["delta"])
    stock_branch_name = C.branch_by_id(C.STORY["stockout"]["branch_id"])["name"]
    access_branch_name = C.branch_by_id(next(iter(C.STORY["branch_footfall_factor"])))["name"]
    incident_availability = kpis["stockout"]["availability_pct_in_incident"]
    loyalty_return = next(num(r, "return_rate_pct") for r in cohort_seg if r["segment_2025q3"] == "Loyal")

    checks = [
        check("Headline revenue change vs the -10% story", -0.10,
              kpis["headline"]["revenue_yoy_pct"] / 100, 0.02, "ratio",
              "The scenario is only meaningful if the headline lands where intended"),
        check("Mechanism: customer count change", story["customers"],
              m["customers_yoy_pct"] / 100, 0.03, "ratio",
              "Did the analysis recover the customer growth it was built with?"),
        check("Mechanism: frequency change", story["frequency"],
              m["frequency_yoy_pct"] / 100, 0.035, "ratio",
              "The dominant mechanism — must be recovered"),
        check("Mechanism: AOV change", story["aov"],
              m["aov_yoy_pct"] / 100, 0.03, "ratio",
              "Price/mix mechanism recovered"),
        check("Mechanism signs correct (customers up, frequency and AOV down)",
              "up,down,down",
              ",".join(["up" if m["customers_yoy_pct"] > 0 else "down",
                        "down" if m["frequency_yoy_pct"] < 0 else "up",
                        "down" if m["aov_yoy_pct"] < 0 else "up"]), 0, "",
              "Direction matters more than the decimal"),
        check("Worst branch by revenue decline is the stock-out store",
              stock_branch_name, worst_branch["slice"], 0, "",
              f"actual worst = {worst_branch['slice']} ({num(worst_branch, 'yoy_pct'):+.1f}%)"),
        check("Second-worst branch is the access-affected store",
              access_branch_name, second_branch["slice"], 0, "",
              f"actual second = {second_branch['slice']} ({num(second_branch, 'yoy_pct'):+.1f}%)"),
        check("Worst category by YoY % is Beverages", "Beverages",
              worst_cat["slice"], 0, "",
              f"actual = {worst_cat['slice']} ({num(worst_cat, 'yoy_pct'):+.1f}%)"),
        check("Hero SKU availability at the affected store is very low inside the incident window",
              True, incident_availability < 30.0, 0, "%",
              f"availability = {incident_availability:.1f}% inside the window"),
        check("Customer-level retention stays high (leak is frequency, not churn)",
              True, num(cohort, "return_rate_pct") > 80, 0, "%",
              f"return rate = {num(cohort, 'return_rate_pct'):.1f}%, Loyal {loyalty_return:.1f}%"),
        check("Discount depth deepened", True,
              kpis["pricing"]["discount_pct_2026"] > kpis["pricing"]["discount_pct_2025"], 0, "pp",
              f"{kpis['pricing']['discount_pct_2025']:.2f}% -> "
              f"{kpis['pricing']['discount_pct_2026']:.2f}%"),
        check("Gross margin compressed", True,
              kpis["headline"]["gross_margin_pp_change"] < 0, 0, "pp",
              f"{kpis['headline']['gross_margin_pp_change']:+.2f}pp"),
        check("Largest single driver is the supplier failure (Mombasa)", "Supply",
              top_driver["owner"].split()[0], 0, "",
              f"actual = {top_driver['owner']} ({num(top_driver, 'pct_of_total_decline') if False else top_driver['pct_of_total_decline']:.1f}%)"),
        check("Driver partition covers the whole decline (no orphan money)", True,
              abs(sum(p["pct_of_total_decline"] for p in kpis["driver_partition"]) - 100) < 0.5,
              0, "%",
              f"sum = {sum(p['pct_of_total_decline'] for p in kpis['driver_partition']):.2f}%"),
    ]

    n_pass = sum(1 for c in checks if c["pass"])
    L = ["# Validation Against Ground Truth\n",
         "> Generated by `src/validate_against_truth.py`. The dataset is simulated, so the",
         "> true drivers are known in advance (`config.STORY` and `docs/00_ground_truth.md`).",
         "> These checks ask whether the diagnostic recovered them — a failing row means the",
         "> *analysis* is wrong, not the data.\n",
         f"**Result: {n_pass}/{len(checks)} checks passed.**\n",
         "| # | Check | Expected | Actual | Tolerance | Result |",
         "|---|---|---|---|---|---|"]
    for i, c in enumerate(checks, 1):
        exp = f"{c['expected']:.4f}" if isinstance(c["expected"], float) else c["expected"]
        act = f"{c['actual']:.4f}" if isinstance(c["actual"], float) else c["actual"]
        L.append(f"| {i} | {c['check']} | {exp} | {act} | ±{c['tolerance']}{c['unit']} | "
                 f"{'PASS' if c['pass'] else 'FAIL'} |")
    L.append("")
    L.append("## Notes on the checks that are deliberately loose\n")
    L.append("- **Mechanism tolerances are ±3pp, not exact.** The generator applies factors to a")
    L.append("  stochastic process, so realised values differ slightly from the design. Demanding")
    L.append("  an exact match would be a test of arithmetic, not of diagnosis.")
    L.append("- **Two checks are structural, not numeric:** the worst branch and the second-worst")
    L.append("  branch. Those are the claims the findings report actually stakes its recommendations")
    L.append("  on, so they are asserted exactly.")
    L.append("- **One claim is deliberately NOT checked:** why the stock ran out. No data in this")
    L.append("  repository can settle it, and a validation suite that 'passes' an unanswerable")
    L.append("  question would be worse than useless.\n")
    L.append("## Failing checks\n")
    fails = [c for c in checks if not c["pass"]]
    if fails:
        for c in fails:
            L.append(f"- **{c['check']}** — expected {c['expected']}, got {c['actual']} ({c['note']})")
    else:
        L.append("None. The diagnostic recovered every driver that was built into the data.\n")

    (C.PROJECT_ROOT / "outputs" / "validation_report.md").write_text("\n".join(L))
    print(f"  wrote outputs/validation_report.md  ({n_pass}/{len(checks)} passed)")
    for c in checks:
        if not c["pass"]:
            print(f"    FAIL: {c['check']} (expected {c['expected']}, got {c['actual']})")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
