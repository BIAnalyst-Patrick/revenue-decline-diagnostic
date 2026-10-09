"""Generate the simulated retail dataset for Project 1.

Builds a Kimball-style star schema and writes it to `data/raw/` as CSV:

    dim_date.csv          one row = one calendar day
    dim_branch.csv        one row = one store
    dim_product.csv       one row = one SKU
    dim_customer.csv      one row = one customer (static attributes only)
    fact_sales_lines.csv  one row = one line item on one receipt  <-- the grain
    fact_stockouts.csv    one row = one branch x SKU x day shelf-status observation

The data is SIMULATED, but it is not random noise: a specific, quantified
decline story is baked into Q3 FY2026 (see config.STORY and
docs/00_ground_truth.md). The whole point is that the diagnostic pipeline has a
real mechanism to discover and a known answer to be graded against.

The raw export is also deliberately imperfect (config.DQ_ISSUES) so that the
cleaning step and data-quality report have real work to do.

Run:  python3 src/generate_data.py
"""

import csv
import sys
from datetime import date, timedelta
from pathlib import Path

import _bootstrap  # noqa: F401  (makes pylibs/ importable -- must precede numpy)
import numpy as np

sys.path.append(str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

WEEKDAY_WEIGHTS = np.array([0.95, 0.98, 1.02, 1.08, 1.30, 1.45, 1.20])  # Mon..Sun
MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def period_dates(period):
    d = date.fromisoformat(period["start"])
    end = date.fromisoformat(period["end"])
    out = []
    while d <= end:
        out.append(d)
        d += timedelta(days=1)
    return out


def in_stockout_window(period_key, d: date) -> bool:
    so = C.STORY["stockout"]
    return (period_key == C.CURRENT_PERIOD_KEY
            and date.fromisoformat(so["start"]) <= d <= date.fromisoformat(so["end"]))


# --------------------------------------------------------------------------- #
# Dimensions                                                                   #
# --------------------------------------------------------------------------- #
def build_dim_date():
    rows = []
    for p in C.PERIODS:
        for d in period_dates(p):
            rows.append({
                "date_key": int(d.strftime("%Y%m%d")),
                "date": d.isoformat(),
                "period_key": p["key"],
                "year": d.year,
                "quarter": (d.month - 1) // 3 + 1,
                "month": d.month,
                "month_name": MONTH_NAMES[d.month],
                "iso_week": int(d.isocalendar()[1]),
                "day_of_week": d.weekday() + 1,
                "day_name": DAY_NAMES[d.weekday()],
                "is_weekend": int(d.weekday() >= 5),
                "is_school_holiday": int(d.month == 8),
            })
    return rows


def build_dim_branch():
    return [{
        "branch_id": b["id"],
        "branch_name": b["name"],
        "region": b["region"],
        "size_index": b["size"],
        "opened_date": b["opened"],
    } for b in C.BRANCHES]


def build_dim_product():
    return [{
        "product_id": s["product_id"],
        "product_name": s["product_name"],
        "category": s["category"],
        "subcategory": s["category"].split()[0],
        "list_price": round(s["list_price"], 2),
        "gross_margin": round(s["gross_margin"], 4),
        "is_hero_sku": int(s["is_hero"]),
    } for s in C.all_skus()]


# --------------------------------------------------------------------------- #
# Customer roster + migration                                                  #
# --------------------------------------------------------------------------- #
def build_roster(rng):
    """Return the customer universe with a Q3'25 segment and a Q3'26 outcome.

    Segment labels are NOT static: a customer classified Loyal in Q3 2025 may
    be Regular, At-Risk or Lapsed in Q3 2026. That migration is the evidence
    behind the retention finding.
    """
    seg_names = C.SEGMENT_NAMES
    seg_share = np.array([s["share"] for s in C.SEGMENTS])
    customers = []
    cid = 0

    for b in C.BRANCHES:
        n = int(round(C.BASE_CUSTOMERS_PER_BRANCH * b["size"]))
        seg25 = rng.choice(seg_names, size=n, p=seg_share)
        for s in seg25:
            cid += 1
            # acquisition 6-36 months before the base period
            acq = date(2025, 7, 1) - timedelta(days=int(rng.integers(180, 1080)))
            customers.append({
                "customer_id": f"C{cid:07d}",
                "home_branch_id": b["id"],
                "home_region": b["region"],
                "segment_2025": s,
                "acquisition_date": acq.isoformat(),
                "acquisition_period": "pre-2025Q3",
            })

    # --- migration into Q3 2026 ------------------------------------------- #
    for c in customers:
        outcomes = list(C.MIGRATION[c["segment_2025"]].keys())
        probs = np.array(list(C.MIGRATION[c["segment_2025"]].values()))
        c["segment_2026"] = str(rng.choice(outcomes, p=probs))

    # --- new-customer inflow (all enter as "New") ------------------------- #
    base_new = sum(1 for c in customers if c["segment_2025"] == "New")
    inflow = int(round(base_new * C.STORY["new_customer_inflow_multiple"]))
    branch_p = np.array([b["size"] for b in C.BRANCHES])
    branch_p = branch_p / branch_p.sum()
    branch_ids = [b["id"] for b in C.BRANCHES]
    region_of = {b["id"]: b["region"] for b in C.BRANCHES}
    for _ in range(inflow):
        cid += 1
        bid = str(rng.choice(branch_ids, p=branch_p))
        acq = date(2026, 7, 1) + timedelta(days=int(rng.integers(0, 92)))
        customers.append({
            "customer_id": f"C{cid:07d}",
            "home_branch_id": bid,
            "home_region": region_of[bid],
            "segment_2025": None,          # did not exist in the base period
            "segment_2026": "New",
            "acquisition_date": acq.isoformat(),
            "acquisition_period": "2026Q3",
        })
    return customers


def build_dim_customer(roster):
    """Static attributes only -- period-specific segments live on the fact table."""
    return [{
        "customer_id": c["customer_id"],
        "home_branch_id": c["home_branch_id"],
        "home_region": c["home_region"],
        "acquisition_date": c["acquisition_date"],
        "acquisition_period": c["acquisition_period"],
    } for c in roster]


# --------------------------------------------------------------------------- #
# Fact: sales lines                                                            #
# --------------------------------------------------------------------------- #
def generate_period_fact(rng, roster, period, first_invoice_no):
    """Simulate every line item sold in one quarter. Returns dict-of-arrays."""
    # Customers only exist in the periods they were around for: the 2026-only
    # acquisitions must not appear in the Q3 2025 base quarter.
    if period["phase"] == "base":
        roster_idx = np.array([i for i, c in enumerate(roster) if c["segment_2025"]], dtype=int)
        seg_all = np.array([c["segment_2025"] or "" for c in roster], dtype=object)
    else:
        roster_idx = np.arange(len(roster))
        seg_all = np.array([c["segment_2026"] or "" for c in roster], dtype=object)

    seg_of = seg_all[roster_idx]
    branch_of = np.array([c["home_branch_id"] for c in roster], dtype=object)[roster_idx]
    roster_n = len(roster_idx)

    # --- who is active, and how often do they visit? ----------------------- #
    vpm = {s["name"]: s["visits_per_month"] for s in C.SEGMENTS}
    ff = dict(C.STORY["frequency_factor"])
    vpm["Lapsed"] = 0.0        # lapsed customers are in the roster but shop zero times
    ff["Lapsed"] = 0.0
    footfall = C.STORY["branch_footfall_factor"]

    lam = np.array([vpm[s] for s in seg_of], dtype=float) * 3.0
    if period["phase"] == "current":
        # Story factors apply to the CURRENT quarter only -- applying one to the
        # base year as well would silently distort the very comparison we need.
        lam = lam * np.array([ff[s] for s in seg_of], dtype=float)
        lam = lam * np.array([footfall.get(b, 1.0) for b in branch_of], dtype=float)

    visits = rng.poisson(lam)
    if period["phase"] == "base":
        active = np.ones(roster_n, dtype=bool)
    else:
        active = np.array([s != "Lapsed" for s in seg_of])
    visits[~active] = 0
    visits[active] = np.maximum(visits[active], 1)

    n_invoices = int(visits.sum())
    inv_cust = np.repeat(np.arange(roster_n), visits)

    # --- date of each invoice --------------------------------------------- #
    days = period_dates(period)
    dow = np.array([d.weekday() for d in days])
    day_w = WEEKDAY_WEIGHTS[dow]
    day_w = day_w / day_w.sum()
    inv_day = rng.choice(len(days), size=n_invoices, p=day_w)
    inv_date = np.array([days[i] for i in inv_day])

    # --- basket breadth ---------------------------------------------------- #
    lpo = {s["name"]: s["lines_per_order"] for s in C.SEGMENTS}
    lpo["Lapsed"] = 0.0
    mean_lines = np.array([lpo[s] for s in seg_of], dtype=float)[inv_cust]
    so = C.STORY["stockout"]
    if period["phase"] == "current":
        window = np.array([in_stockout_window(period["key"], d) for d in inv_date])
        br05 = np.array([b == so["branch_id"] for b in branch_of[inv_cust]])
        spill = window & br05
        mean_lines = np.where(spill, mean_lines * so["spillover_line_factor"], mean_lines)
    lines = 1 + rng.poisson(np.maximum(mean_lines - 1.0, 0.02))
    lines = np.clip(lines, 1, 25).astype(int)

    n_lines = int(lines.sum())
    inv_idx = np.repeat(np.arange(n_invoices), lines)
    cust_idx = inv_cust[inv_idx]
    dts = inv_date[inv_idx]
    segs = seg_of[cust_idx]
    brs = branch_of[cust_idx]

    # --- product selection ------------------------------------------------- #
    all_skus = C.all_skus()
    sku_price = np.array([s["list_price"] for s in all_skus])
    sku_margin = np.array([s["gross_margin"] for s in all_skus])
    sku_base_disc = np.array([s["base_discount"] for s in all_skus])
    sku_cat = np.array([s["category"] for s in all_skus])
    # NOTE: text columns are built as object arrays. A plain np.array([...]) of
    # strings becomes a fixed-width <U array and would silently truncate any
    # later value longer than the widest original string.
    sku_code = np.array([s["product_id"] for s in all_skus], dtype=object)
    sku_name = np.array([s["product_name"] for s in all_skus], dtype=object)

    cat_names = np.array(C.CATEGORY_NAMES, dtype=object)
    cat_w = np.array([c["weight"] for c in C.CATEGORIES])
    cat_w = cat_w / cat_w.sum()
    line_cat = cat_names[rng.choice(len(cat_names), size=n_lines, p=cat_w)]

    sku_idx = np.zeros(n_lines, dtype=int)
    for cat in C.CATEGORIES:
        m = line_cat == cat["name"]
        k = int(m.sum())
        if k == 0:
            continue
        local = np.where(sku_cat == cat["name"])[0]
        pops = np.array([s[3] for s in cat["skus"]], dtype=float)
        sku_idx[m] = rng.choice(local, size=k, p=pops / pops.sum())

    # --- quantities and prices -------------------------------------------- #
    qty = rng.choice([1, 2, 3, 4], size=n_lines, p=[0.62, 0.22, 0.11, 0.05]).astype(float)
    price_infl = C.STORY["price_inflation"] if period["phase"] == "current" else 0.0
    cost_infl = C.STORY["cost_inflation"] if period["phase"] == "current" else 0.0
    unit_price = sku_price[sku_idx] * (1 + price_infl) * rng.lognormal(0, 0.02, n_lines)
    unit_cost = (sku_price[sku_idx] * (1 - sku_margin[sku_idx]) * (1 + cost_infl)
                 * rng.lognormal(0, 0.015, n_lines))

    seg_dupl = {s["name"]: s["discount_uplift"] for s in C.SEGMENTS}
    seg_dupl["Lapsed"] = 0.0
    disc = sku_base_disc[sku_idx] + np.array([seg_dupl[s] for s in segs])
    if period["phase"] == "current":
        up = C.STORY["discount_uplift"]
        disc = disc + np.array([up.get(c, 0.0) for c in line_cat])
    disc = np.clip(disc + rng.normal(0, 0.008, n_lines), 0.0, 0.60)

    # --- the stock-out: hero SKUs simply are not there ---------------------- #
    if period["phase"] == "current":
        window = np.array([in_stockout_window(period["key"], d) for d in dts])
        br05 = np.array([b == so["branch_id"] for b in brs])
        pcare = np.array([c == so["category"] for c in line_cat])
        hero = np.isin(sku_code[sku_idx], so["sku_codes"])
        affected = window & br05 & pcare
        keep_p = np.ones(n_lines)
        keep_p[affected & hero] = so["hero_availability"]
        keep_p[affected & ~hero] = so["category_availability"]
        keep = rng.random(n_lines) < keep_p
    else:
        keep = np.ones(n_lines, dtype=bool)

    qty, unit_price, unit_cost, disc = qty[keep], unit_price[keep], unit_cost[keep], disc[keep]
    inv_idx, cust_idx = inv_idx[keep], cust_idx[keep]
    dts, segs, brs = dts[keep], segs[keep], brs[keep]
    sku_idx, line_cat = sku_idx[keep], line_cat[keep]

    # --- line ids: 1..n within each surviving invoice ---------------------- #
    # inv_idx is non-decreasing, so positions minus each group's start offset
    # gives the 1-based line number inside its invoice.
    counts = np.bincount(inv_idx, minlength=n_invoices)
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    line_id = (np.arange(len(inv_idx)) - np.repeat(starts, counts)) + 1

    # --- measures ---------------------------------------------------------- #
    gross = qty * unit_price
    disc_amt = gross * disc
    net = gross - disc_amt
    cogs = qty * unit_cost
    gp = net - cogs

    # -- channel is a property of the trip, not the line -------------------- #
    ch_names = [c["name"] for c in C.CHANNELS]
    ch_p = np.array([c["share"] for c in C.CHANNELS])
    trip_channel = rng.choice(ch_names, size=n_invoices, p=ch_p / ch_p.sum())
    channel = trip_channel[inv_idx]

    roster_ids = np.array([c["customer_id"] for c in roster], dtype=object)[roster_idx]
    cust_ids = roster_ids[cust_idx]
    invoice_ids = np.array([f"{period['year']}{period['key'][-2:]}-{first_invoice_no + i:07d}"
                            for i in range(n_invoices)], dtype=object)[inv_idx]

    return {
        "period_key": np.full(len(inv_idx), period["key"], dtype=object),
        "date": np.array([d.isoformat() for d in dts], dtype=object),
        "date_key": np.array([int(d.strftime("%Y%m%d")) for d in dts], dtype=int),
        "invoice_id": invoice_ids,
        "line_id": line_id,
        "branch_id": brs,
        "customer_id": cust_ids,
        "customer_segment": segs,
        "channel": channel,
        "product_id": sku_code[sku_idx],
        "product_name": sku_name[sku_idx],
        "category": line_cat,
        "quantity": qty,
        "unit_price": np.round(unit_price, 2),
        "discount_pct": np.round(disc, 4),
        "gross_revenue": np.round(gross, 2),
        "discount_amount": np.round(disc_amt, 2),
        "net_revenue": np.round(net, 2),
        "unit_cost": np.round(unit_cost, 2),
        "cogs": np.round(cogs, 2),
        "gross_profit": np.round(gp, 2),
    }


# --------------------------------------------------------------------------- #
# Fact: stock-out observations                                                 #
# --------------------------------------------------------------------------- #
def build_fact_stockouts(rng):
    """Shelf-status observations for Personal Care SKUs across both quarters.

    This is the evidence table that lets the analysis PROVE the availability
    failure rather than assert it. A handful of unrelated one-day stock-outs are
    sprinkled across the chain so the real incident has to be found, not assumed.
    """
    pc_skus = [s for s in C.all_skus() if s["category"] == "Personal Care"]
    so = C.STORY["stockout"]
    rows = []
    for p in C.PERIODS:
        for b in C.BRANCHES:
            for sku in pc_skus:
                out_streak = 0
                for d in period_dates(p):
                    is_incident = (p["key"] == C.CURRENT_PERIOD_KEY
                                   and b["id"] == so["branch_id"]
                                   and sku["product_id"] in so["sku_codes"]
                                   and date.fromisoformat(so["start"]) <= d <= date.fromisoformat(so["end"]))
                    if is_incident:
                        in_stock = int(rng.random() < so["hero_availability"])
                    else:
                        # background noise: rare, short, single-SKU outages
                        in_stock = int(rng.random() > 0.004)
                    out_streak = 0 if in_stock else out_streak + 1
                    rows.append({
                        "date_key": int(d.strftime("%Y%m%d")),
                        "date": d.isoformat(),
                        "period_key": p["key"],
                        "branch_id": b["id"],
                        "product_id": sku["product_id"],
                        "product_name": sku["product_name"],
                        "category": sku["category"],
                        "in_stock": in_stock,
                        "consecutive_days_out": out_streak,
                        "incident_flag": int(is_incident),
                    })
    return rows


# --------------------------------------------------------------------------- #
# Planted data-quality issues                                                  #
# --------------------------------------------------------------------------- #
def plant_data_quality_issues(rng, fact):
    """Corrupt the export in the specific ways real POS extracts are corrupt.

    Returns (corrupted_fact, issue_log). Every mutation is recorded so the
    cleaning step can be audited line by line.

    Sampling is DISJOINT across issue types: a row is corrupted by exactly one
    rule, so the cleaning report's "planted" and "detected" counts agree and any
    divergence signals a real bug rather than an artefact of overlapping
    injections.
    """
    dq = C.DQ_ISSUES
    n = len(fact["date"])
    log = []
    used = set()

    def pick(k, eligible=None):
        pool = eligible if eligible is not None else np.arange(n)
        pool = np.array([i for i in pool if i not in used], dtype=int)
        k = min(k, len(pool))
        chosen = rng.choice(pool, size=k, replace=False)
        used.update(int(x) for x in chosen)
        return chosen

    def record(key, issue, count, fix):
        log.append({"key": key, "issue": issue, "planted_rows": count, "treatment": fix})

    # 1. Exact duplicate line items ---------------------------------------- #
    dup = pick(dq["duplicate_lines"])
    for col in fact:
        fact[col] = np.concatenate([fact[col], fact[col][dup]])
    record("duplicate_lines", "Duplicate line items (same invoice_id + line_id)",
           dq["duplicate_lines"], "Deduplicate on (invoice_id, line_id); keep first")

    # 2. Invalid quantities -------------------------------------------------- #
    idx = pick(dq["invalid_quantity"])
    fact["quantity"][idx] = rng.choice([0.0, -2.0, 999.0], size=len(idx))
    record("invalid_quantity", "Invalid quantity (0, negative or 999 data-entry values)",
           dq["invalid_quantity"], "Quarantine; log for POS source review")

    # 3. Out-of-period dates ------------------------------------------------- #
    idx = pick(dq["out_of_period_dates"])
    for i in idx:
        y = int(rng.choice([2025, 2026]))
        fact["date"][i] = f"{y}-{rng.choice(['04','05','10','11','12'])}-{int(rng.integers(1,28)):02d}"
        fact["date_key"][i] = int(fact["date"][i].replace("-", ""))
    record("out_of_period_dates", "Transactions dated outside both comparison quarters",
           dq["out_of_period_dates"], "Quarantine; excluded from period analysis")

    # 4. Missing discount ---------------------------------------------------- #
    fact["discount_missing"] = np.zeros(len(fact["date"]), dtype=int)
    idx = pick(dq["null_discount"])
    fact["discount_missing"][idx] = 1
    record("null_discount", "NULL discount_pct", dq["null_discount"],
           "Set to 0; flag `discount_missing`")

    # 5. Messy category labels ---------------------------------------------- #
    canonical_set = {c for c, _ in C.MESSY_CATEGORY_LABELS}
    eligible = np.array([i for i in range(n) if fact["category"][i] in canonical_set], dtype=int)
    idx = pick(dq["messy_category_labels"], eligible)
    for i in idx:
        for canonical, variants in C.MESSY_CATEGORY_LABELS:
            if fact["category"][i] == canonical:
                fact["category"][i] = str(rng.choice(variants))
                break
    record("messy_category_labels", "Inconsistent category labels (case / spacing / hyphenation)",
           len(idx), "Map to canonical label; flag `category_normalised`")

    # 6. Anonymous customers (legitimate, but a coverage limit) -------------- #
    idx = pick(dq["null_customer"])
    fact["customer_id"][idx] = ""
    fact["customer_segment"][idx] = ""
    record("null_customer", "Missing customer_id / customer_segment (anonymous walk-ins)",
           len(idx), "Label segment 'Unattributed'; declare a coverage limit")

    # 7. Unknown SKU codes --------------------------------------------------- #
    idx = pick(dq["unknown_sku"])
    fact["product_id"][idx] = "ZZ99"
    fact["product_name"][idx] = "UNKNOWN ITEM"
    record("unknown_sku", "SKU codes absent from dim_product", len(idx),
           "Retain in totals; flag `product_unmapped`")

    # 8. Invoice reused across two dates ------------------------------------ #
    # line_id is also moved to a high, unique value so that this injection does
    # not accidentally create a (invoice_id, line_id) duplicate as a side effect,
    # and victims are drawn from DISTINCT invoices so the number of invoices left
    # with two dates equals the number of injected rows.
    idx = pick(dq["duplicate_invoice_header"])
    first_of_invoice = {}
    for i, v in enumerate(fact["invoice_id"]):
        first_of_invoice.setdefault(v, i)
    victims = pick(len(idx), np.array(sorted(first_of_invoice.values()), dtype=int))
    fact["invoice_id"][idx] = fact["invoice_id"][victims]
    fact["line_id"][idx] = np.arange(9001, 9001 + len(idx))
    record("duplicate_invoice_header", "invoice_id reused on a second date",
           len(idx), "Retain first date for the invoice")

    # shuffle so planted issues are not all at the tail
    order = rng.permutation(len(fact["date"]))
    for col in fact:
        fact[col] = fact[col][order]
    return fact, log


# --------------------------------------------------------------------------- #
# CSV writing                                                                  #
# --------------------------------------------------------------------------- #
def write_rows(path, rows, columns):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {path.name:26s} {len(rows):>9,} rows")


def write_fact(path, fact, columns):
    n = len(fact["date"])
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(columns)
        for i in range(n):
            row = []
            for col in columns:
                v = fact[col][i]
                if col == "discount_pct" and fact["discount_missing"][i]:
                    row.append("")                      # the planted NULL
                elif isinstance(v, (np.floating, float)):
                    row.append(f"{float(v):.4f}" if col in ("discount_pct", "gross_margin") else f"{float(v):.2f}")
                elif isinstance(v, (np.integer, int)):
                    row.append(int(v))
                else:
                    row.append(str(v))
            w.writerow(row)
    print(f"  wrote {path.name:26s} {n:>9,} rows")


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main():
    C.ensure_dirs()
    rng = np.random.default_rng(C.SEED)

    print(f"Generating {C.COMPANY} — Q3 2025 vs Q3 2026 (seed {C.SEED})")
    print(f"Output -> {C.DATA_RAW}")

    write_rows(C.DATA_RAW / "dim_date.csv", build_dim_date(),
               ["date_key", "date", "period_key", "year", "quarter", "month",
                "month_name", "iso_week", "day_of_week", "day_name", "is_weekend",
                "is_school_holiday"])
    write_rows(C.DATA_RAW / "dim_branch.csv", build_dim_branch(),
               ["branch_id", "branch_name", "region", "size_index", "opened_date"])
    write_rows(C.DATA_RAW / "dim_product.csv", build_dim_product(),
               ["product_id", "product_name", "category", "subcategory", "list_price",
                "gross_margin", "is_hero_sku"])

    roster = build_roster(rng)
    write_rows(C.DATA_RAW / "dim_customer.csv", build_dim_customer(roster),
               ["customer_id", "home_branch_id", "home_region", "acquisition_date",
                "acquisition_period"])

    # --- sales lines -------------------------------------------------------- #
    parts = []
    next_invoice = 1
    for p in C.PERIODS:
        part = generate_period_fact(rng, roster, p, next_invoice)
        next_invoice += len(np.unique(part["invoice_id"]))
        parts.append(part)
        print(f"  {p['label']}: {len(part['date']):,} lines, "
              f"{len(np.unique(part['invoice_id'])):,} invoices")

    fact = {col: np.concatenate([p[col] for p in parts]) for col in parts[0]}
    fact, dq_log = plant_data_quality_issues(rng, fact)

    fact_cols = ["period_key", "date", "date_key", "invoice_id", "line_id",
                 "branch_id", "customer_id", "customer_segment", "channel",
                 "product_id", "product_name", "category", "quantity", "unit_price",
                 "discount_pct", "gross_revenue", "discount_amount", "net_revenue",
                 "unit_cost", "cogs", "gross_profit"]
    write_fact(C.DATA_RAW / "fact_sales_lines.csv", fact, fact_cols)

    write_rows(C.DATA_RAW / "fact_stockouts.csv", build_fact_stockouts(rng),
               ["date_key", "date", "period_key", "branch_id", "product_id",
                "product_name", "category", "in_stock", "consecutive_days_out",
                "incident_flag"])

    write_rows(C.DATA_RAW / "dq_issue_manifest.csv", dq_log,
               ["key", "issue", "planted_rows", "treatment"])

    # --- quick sanity print (net revenue by period) ------------------------- #
    print("\nRaw net revenue by period (uncleaned):")
    for key in (C.BASE_PERIOD_KEY, C.CURRENT_PERIOD_KEY):
        m = fact["period_key"] == key
        print(f"  {key}: {fact['net_revenue'][m].sum():>14,.0f}  {C.CURRENCY}")
    print("\nDone. Next: python3 src/clean_data.py")


if __name__ == "__main__":
    main()
