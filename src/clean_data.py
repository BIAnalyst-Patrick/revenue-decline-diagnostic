"""Clean the raw POS export and produce the data-quality report.

The raw extract is deliberately imperfect (see config.DQ_ISSUES). This module
applies explicit, auditable rules to fix it and then writes a report describing
exactly what was wrong, what was done, and what is STILL uncertain afterwards
(the declared coverage limits required by Ch. 26).

Inputs : data/raw/*
Outputs: data/processed/fact_sales_lines_clean.csv
         data/processed/dim_*.csv            (copied, dimensions are already clean)
         data/processed/dq_issues_log.csv
         docs/03_data_quality_report.md

Run:  python3 src/clean_data.py
"""

import csv
import shutil
import sys
from pathlib import Path

import _bootstrap  # noqa: F401
import numpy as np

sys.path.append(str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

MAX_SANE_QUANTITY = 100.0
MAX_SANE_UNIT_PRICE = 50_000.0
MAX_SANE_LINE_VALUE = 500_000.0


# --------------------------------------------------------------------------- #
# IO helpers                                                                   #
# --------------------------------------------------------------------------- #
def read_csv(path):
    with open(path, newline="") as f:
        r = csv.reader(f)
        header = next(r)
        return header, [row for row in r]


def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def to_float(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------- #
# Cleaning                                                                     #
# --------------------------------------------------------------------------- #
def canonical_category(raw: str, lookup) -> str:
    return lookup.get(raw.strip().lower().replace("  ", " "), raw)


def clean():
    header, rows = read_csv(C.DATA_RAW / "fact_sales_lines.csv")
    idx = {name: i for i, name in enumerate(header)}
    _, dim_date_rows = read_csv(C.DATA_RAW / "dim_date.csv")
    valid_dates = {row[0]: row[1] for row in dim_date_rows}
    period_of_date = {row[0]: row[2] for row in dim_date_rows}

    _, dim_product_rows = read_csv(C.DATA_RAW / "dim_product.csv")
    known_skus = {row[0] for row in dim_product_rows}

    # canonical category lookup for the messy-label variants
    label_lookup = {}
    for canonical, variants in C.MESSY_CATEGORY_LABELS:
        label_lookup[canonical.strip().lower()] = canonical
        for v in variants:
            label_lookup[v.strip().lower()] = canonical

    # Planted data-quality issue counts (from the generator manifest:
    # columns are key, issue, planted_rows, treatment)
    _, manifest = read_csv(C.DATA_RAW / "dq_issue_manifest.csv")
    planned = {r[0]: int(r[2]) for r in manifest}

    stats = {k: {"rows": 0, "revenue": 0.0} for k in [
        "duplicate_lines", "invalid_quantity", "invalid_price", "out_of_period_dates",
        "null_discount", "messy_category_labels", "null_customer", "unknown_sku",
        "duplicate_invoice_header",
    ]}
    clean_rows = []
    seen_keys = set()
    invoice_dates = {}
    conflicting_invoices = set()
    input_rows = len(rows)

    # ---- pass 1: duplicates, invalid values, out-of-period ----------------- #
    for row in rows:
        key = (row[idx["invoice_id"]], row[idx["line_id"]])
        if key in seen_keys:
            stats["duplicate_lines"]["rows"] += 1
            stats["duplicate_lines"]["revenue"] += to_float(row[idx["net_revenue"]], 0.0)
            continue
        seen_keys.add(key)

        qty = to_float(row[idx["quantity"]], 0.0)
        price = to_float(row[idx["unit_price"]], 0.0)
        rev = to_float(row[idx["net_revenue"]], 0.0)
        if qty <= 0 or qty > MAX_SANE_QUANTITY:
            stats["invalid_quantity"]["rows"] += 1
            stats["invalid_quantity"]["revenue"] += rev
            continue
        if price <= 0 or price > MAX_SANE_UNIT_PRICE or rev > MAX_SANE_LINE_VALUE:
            stats["invalid_price"]["rows"] += 1
            stats["invalid_price"]["revenue"] += rev
            continue

        date_key = row[idx["date_key"]]
        if date_key not in valid_dates:
            stats["out_of_period_dates"]["rows"] += 1
            stats["out_of_period_dates"]["revenue"] += rev
            continue

        # timeliness: does the row's period_key agree with its calendar date?
        true_period = period_of_date[date_key]
        row[idx["period_key"]] = true_period      # authoritative from dim_date

        # an invoice may only belong to one date
        inv = row[idx["invoice_id"]]
        if inv in invoice_dates and invoice_dates[inv] != date_key:
            conflicting_invoices.add(inv)
            row[idx["date_key"]] = invoice_dates[inv]
            row[idx["date"]] = valid_dates[invoice_dates[inv]]
            row[idx["period_key"]] = period_of_date[invoice_dates[inv]]
        else:
            invoice_dates[inv] = date_key

        # ---- pass 2: attribute-level fixes --------------------------------- #
        flags = []

        if row[idx["discount_pct"]].strip() == "":
            stats["null_discount"]["rows"] += 1
            stats["null_discount"]["revenue"] += rev
            row[idx["discount_pct"]] = "0.0000"
            flags.append("discount_missing")

        canon = canonical_category(row[idx["category"]], label_lookup)
        if canon != row[idx["category"]]:
            stats["messy_category_labels"]["rows"] += 1
            row[idx["category"]] = canon
            flags.append("category_normalised")

        if row[idx["customer_id"]].strip() == "":
            stats["null_customer"]["rows"] += 1
            stats["null_customer"]["revenue"] += rev
            row[idx["customer_id"]] = "UNKNOWN"
            row[idx["customer_segment"]] = "Unattributed"
            flags.append("customer_unattributed")

        if row[idx["product_id"]] not in known_skus:
            stats["unknown_sku"]["rows"] += 1
            stats["unknown_sku"]["revenue"] += rev
            flags.append("product_unmapped")

        clean_rows.append(row + ["|".join(flags)])

    stats["duplicate_invoice_header"]["rows"] = len(conflicting_invoices)
    clean_rows.sort(key=lambda r: (r[idx["date"]], r[idx["invoice_id"]], r[idx["line_id"]]))
    return header, idx, clean_rows, stats, planned, input_rows, valid_dates


# --------------------------------------------------------------------------- #
# Reporting                                                                    #
# --------------------------------------------------------------------------- #
def fmt(n):
    return f"{n:,.0f}"


def revenue_by_period(rows, idx):
    out = {}
    for pk in (C.BASE_PERIOD_KEY, C.CURRENT_PERIOD_KEY):
        out[pk] = sum(to_float(r[idx["net_revenue"]], 0.0)
                      for r in rows if r[idx["period_key"]] == pk)
    return out


def write_report(header, idx, rows, stats, planned, input_rows, rev):
    base, current = rev[C.BASE_PERIOD_KEY], rev[C.CURRENT_PERIOD_KEY]
    yoy = (current / base - 1) * 100

    total_revenue = base + current
    unattributed = sum(to_float(r[idx["net_revenue"]], 0.0)
                      for r in rows if r[idx["customer_segment"]] == "Unattributed")
    unattrib_pct = unattributed / total_revenue * 100

    line = lambda k: (
        f"| {RULES_LABEL[k]} | {planned.get(k, 0):,} | {stats[k]['rows']:,} | "
        f"{C.CURRENCY} {fmt(stats[k]['revenue'])} | {RULES_FIX[k]} |"
    )

    L = []
    L.append("# Data Quality Report — Project 1\n")
    L.append("> Generated by `src/clean_data.py`. Every number below is produced by the "
             "cleaning run, not typed by hand.\n")
    L.append(f"**Source:** `data/raw/fact_sales_lines.csv`  \n"
             f"**Rows in:** {input_rows:,}  \n"
             f"**Rows out (clean):** {len(rows):,}  \n"
             f"**Rows quarantined:** {input_rows - len(rows):,} "
             f"({(input_rows - len(rows)) / input_rows * 100:.3f}%)\n")

    L.append("## 1. The six quality dimensions (Ch. 14)\n")
    L.append("| Dimension | Finding | Status |")
    L.append("|---|---|---|")
    L.append(f"| Completeness | {stats['null_discount']['rows']:,} lines missing `discount_pct`; "
             f"{stats['null_customer']['rows']:,} lines with no customer identifier | "
             "ATTENTION — both handled, discount impact immaterial |")
    L.append(f"| Accuracy | {stats['invalid_quantity']['rows']:,} impossible quantities "
             f"(0, negative, 999); {stats['invalid_price']['rows']:,} impossible prices | "
             "ATTENTION — quarantined |")
    L.append(f"| Consistency | {stats['messy_category_labels']['rows']:,} non-canonical category "
             "labels, {n} spellings | FIXED — mapped to canonical values |"
             .replace("{n}", str(len(C.MESSY_CATEGORY_LABELS))))
    L.append(f"| Validity | {stats['unknown_sku']['rows']:,} SKU codes absent from `dim_product` | "
             "ATTENTION — retained in totals, flagged `product_unmapped` |")
    L.append(f"| Uniqueness | {stats['duplicate_lines']['rows']:,} duplicate lines on "
             "`(invoice_id, line_id)`; {c} invoices reused across two dates | FIXED — deduplicated, "
             "first date retained |".replace("{c}", f"{stats['duplicate_invoice_header']['rows']:,}"))
    L.append(f"| Timeliness | {stats['out_of_period_dates']['rows']:,} transactions dated outside "
             "both comparison quarters | QUARANTINED — excluded from all period analysis |")
    L.append("")

    L.append("## 2. Issues found, quantified, and how each was treated\n")
    L.append("| Planted issue | Planted by generator | Detected by cleaner | Revenue affected | Treatment |")
    L.append("|---|---:|---:|---:|---|")
    for k in RULES_ORDER:
        L.append(line(k))
    L.append("")

    L.append("## 3. Grain and integrity after cleaning\n")
    L.append(f"- **Grain:** one row = one line item on one customer receipt. "
             f"{len(rows):,} line items across "
             f"{len({r[idx['invoice_id']] for r in rows}):,} distinct invoices.")
    L.append(f"- **Duplicate `(invoice_id, line_id)` keys remaining:** "
             f"{len(rows) - len({(r[idx['invoice_id']], r[idx['line_id']]) for r in rows}):,}")
    L.append(f"- **Invoices spanning more than one date remaining:** 0 (repaired in pass 1).")
    L.append(f"- **Every line joins to `dim_date`:** yes — rows failing this test were quarantined.")
    L.append("")

    L.append("## 4. Declared coverage limits (read this before trusting a slice)\n")
    L.append(f"1. **Unattributed revenue.** {stats['null_customer']['rows']:,} line items have no "
             f"customer identifier. They are legitimately anonymous walk-ins, but it means "
             f"**{C.CURRENCY} {fmt(unattributed)} ({unattrib_pct:.2f}% of revenue) cannot be "
             f"assigned to a customer segment.** Consequence: the segment decomposition does "
             f"**not** sum to the group total — it reconciles to {100 - unattrib_pct:.2f}%. "
             f"The analysis states this explicitly rather than hiding it in an 'Other' bucket.")
    L.append(f"2. **Unmapped SKUs.** {stats['unknown_sku']['rows']:,} lines carry a SKU code that is "
             f"not in `dim_product`. They are counted in every revenue total but excluded from "
             f"product-level rankings.")
    L.append(f"3. **Single-country, single-channel-of-record.** This dataset covers one retailer's "
             f"POS system. Online orders routed through a marketplace are out of scope.")
    L.append(f"4. **Simulated data.** The whole dataset is synthetic and its generating mechanism "
             f"is documented in `docs/00_ground_truth.md`. That is a feature: it lets "
             f"`src/validate_against_truth.py` check whether the diagnostic recovered the truth.")
    L.append("")

    L.append("## 5. Post-cleaning headline (before any diagnosis)\n")
    L.append(f"| Period | Net revenue |")
    L.append(f"|---|---:|")
    L.append(f"| {C.PERIODS[0]['label']} | {C.CURRENCY} {fmt(base)} |")
    L.append(f"| {C.PERIODS[1]['label']} | {C.CURRENCY} {fmt(current)} |")
    L.append(f"| **Change** | **{C.CURRENCY} {fmt(current - base)} ({yoy:+.2f}%)** |")
    L.append("")
    L.append("That single number is the *question*, not the answer. "
             "`src/decompose.py` takes it apart.\n")

    (C.DOCS / "03_data_quality_report.md").write_text("\n".join(L))
    return dict(base=base, current=current, yoy=yoy,
                unattributed_pct=unattrib_pct, unattributed_revenue=unattributed)


RULES_LABEL = {
    "duplicate_lines": "Duplicate line items (same invoice_id + line_id)",
    "invalid_quantity": "Impossible quantity (0, negative or 999)",
    "invalid_price": "Impossible price / line value",
    "out_of_period_dates": "Date outside both comparison quarters",
    "null_discount": "NULL discount_pct",
    "messy_category_labels": "Non-canonical category labels",
    "null_customer": "Missing customer_id (anonymous walk-in)",
    "unknown_sku": "SKU code absent from dim_product",
    "duplicate_invoice_header": "invoice_id reused on a second date",
}
RULES_FIX = {
    "duplicate_lines": "Deduplicate on (invoice_id, line_id); keep first",
    "invalid_quantity": "Quarantine; log for POS source review",
    "invalid_price": "Quarantine; log for POS source review",
    "out_of_period_dates": "Quarantine; excluded from period analysis",
    "null_discount": "Set to 0; flag `discount_missing`",
    "messy_category_labels": "Map to canonical label; flag `category_normalised`",
    "null_customer": "Label segment `Unattributed`; declare coverage limit",
    "unknown_sku": "Retain in totals; flag `product_unmapped`",
    "duplicate_invoice_header": "Retain first date for the invoice",
}
RULES_ORDER = ["duplicate_lines", "invalid_quantity", "invalid_price",
               "out_of_period_dates", "null_discount", "messy_category_labels",
               "null_customer", "unknown_sku", "duplicate_invoice_header"]


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main():
    C.ensure_dirs()
    header, idx, rows, stats, planned, input_rows, _ = clean()

    for name in ("dim_date", "dim_branch", "dim_product", "dim_customer"):
        shutil.copyfile(C.DATA_RAW / f"{name}.csv", C.DATA_PROC / f"{name}.csv")
    shutil.copyfile(C.DATA_RAW / "fact_stockouts.csv", C.DATA_PROC / "fact_stockouts.csv")

    out_header = header + ["dq_flags"]
    write_csv(C.DATA_PROC / "fact_sales_lines_clean.csv", out_header, rows)
    print(f"  wrote fact_sales_lines_clean.csv  {len(rows):,} rows")

    log_rows = [[RULES_LABEL[k], planned.get(k, 0), stats[k]["rows"],
                 f"{stats[k]['revenue']:.2f}", RULES_FIX[k]] for k in RULES_ORDER]
    write_csv(C.DATA_PROC / "dq_issues_log.csv",
              ["issue", "planned_rows", "detected_rows", "revenue_affected",
               "treatment"], log_rows)
    print(f"  wrote dq_issues_log.csv           {len(log_rows):,} rules")

    rev = revenue_by_period(rows, idx)
    summary = write_report(header + ["dq_flags"], idx, rows, stats, planned, input_rows, rev)
    print(f"  wrote docs/03_data_quality_report.md")

    print(f"\n  Clean revenue: {summary['base']:,.0f} -> {summary['current']:,.0f} "
          f"({summary['yoy']:+.2f}%)")
    print(f"  Unattributed: {summary['unattributed_pct']:.2f}% of revenue")
    print("\nDone. Next: python3 src/run_sql.py  (or python3 src/run_pipeline.py)")


if __name__ == "__main__":
    main()
