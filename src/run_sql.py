"""Build the SQLite warehouse and run every diagnostic query in sql/.

    sql/01_schema.sql      DDL            -> executed, not exported
    sql/02_views.sql       views          -> executed, not exported
    sql/03..09_*.sql       analyses       -> each `-- name: <slug>` becomes
                                             outputs/tables/<slug>.csv

Any statement preceded by a `-- name: slug` comment line is exported to CSV, so
every table cited in the report is reproducible from a single query file. This
is the "SQL is the non-negotiable core skill" half of the project: the same
questions a BI analyst would ask in the warehouse.

Run:  python3 src/run_sql.py
"""

import csv
import sqlite3
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

sys.path.append(str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

# table -> (source csv, columns to load in order)
LOADS = [
    ("dim_date", "dim_date.csv", ["date_key", "date", "period_key", "year", "quarter",
                                  "month", "month_name", "iso_week", "day_of_week",
                                  "day_name", "is_weekend", "is_school_holiday"]),
    ("dim_branch", "dim_branch.csv", ["branch_id", "branch_name", "region",
                                      "size_index", "opened_date"]),
    ("dim_product", "dim_product.csv", ["product_id", "product_name", "category",
                                        "subcategory", "list_price", "gross_margin",
                                        "is_hero_sku"]),
    ("dim_customer", "dim_customer.csv", ["customer_id", "home_branch_id", "home_region",
                                          "acquisition_date", "acquisition_period"]),
    ("fact_sales_lines", "fact_sales_lines_clean.csv",
     ["period_key", "date_key", "invoice_id", "line_id", "branch_id", "customer_id",
      "customer_segment", "channel", "product_id", "quantity", "unit_price",
      "discount_pct", "gross_revenue", "discount_amount", "net_revenue", "cogs",
      "gross_profit"]),
    ("fact_stockouts", "fact_stockouts.csv",
     ["date_key", "date", "period_key", "branch_id", "product_id", "product_name",
      "category", "in_stock", "consecutive_days_out", "incident_flag"]),
]


def parse_named_queries(text):
    """Split a .sql file into (name, sql) blocks marked by `-- name: slug`."""
    blocks, cur, buf = [], None, []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("-- name:"):
            if cur:
                blocks.append((cur, "\n".join(buf).strip()))
            cur = stripped.split(":", 1)[1].strip()
            buf = []
        else:
            buf.append(line)
    if cur:
        blocks.append((cur, "\n".join(buf).strip()))
    return blocks


def load_table(conn, table, filename, columns):
    path = C.DATA_PROC / filename
    with open(path, newline="") as f:
        r = csv.reader(f)
        header = next(r)
        pos = [header.index(c) for c in columns]
        rows = [tuple(row[i] for i in pos) for row in r]
    placeholders = ", ".join("?" * len(columns))
    conn.executemany(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})", rows)
    return len(rows)


def insert_inferred_product_members(conn):
    """Kimball rule: a fact row must never vanish because its dimension row is
    missing. Unmapped SKUs get an 'inferred' member so inner joins are safe."""
    missing = conn.execute("""
        SELECT DISTINCT f.product_id
        FROM fact_sales_lines f
        LEFT JOIN dim_product p ON p.product_id = f.product_id
        WHERE p.product_id IS NULL
    """).fetchall()
    for (pid,) in missing:
        conn.execute(
            "INSERT INTO dim_product (product_id, product_name, category, subcategory,"
            " list_price, gross_margin, is_hero_sku) VALUES (?,?,?,?,?,?,?)",
            (pid, "UNKNOWN ITEM (inferred member)", "Unclassified", "Unclassified", 0.0, 0.0, 0))
    return [pid for (pid,) in missing]


def export(conn, name, sql, out_dir):
    cur = conn.execute(sql)
    if cur.description is None:          # a statement that returns no rows
        return None
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    path = out_dir / f"{name}.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    return len(rows)


def main():
    C.ensure_dirs()
    if C.DB_PATH.exists():
        C.DB_PATH.unlink()
    conn = sqlite3.connect(C.DB_PATH)
    conn.execute("PRAGMA journal_mode = OFF")

    files = sorted(C.SQL_DIR.glob("*.sql"))
    schema = [f for f in files if f.name.startswith("01_")]
    views = [f for f in files if f.name.startswith("02_")]
    analyses = [f for f in files if f.name >= "03_"]

    print(f"Building warehouse: {C.DB_PATH.name}")
    for f in schema:
        conn.executescript(f.read_text())
        print(f"  {f.name:26s} schema applied")

    for table, filename, columns in LOADS:
        n = load_table(conn, table, filename, columns)
        print(f"  loaded {table:22s} {n:>9,} rows")
    inferred = insert_inferred_product_members(conn)
    if inferred:
        print(f"  inferred dim_product members for: {', '.join(inferred)}")
    conn.commit()

    for f in views:
        conn.executescript(f.read_text())
        print(f"  {f.name:26s} views applied")

    for sqlfile in analyses:
        for name, sql in parse_named_queries(sqlfile.read_text()):
            try:
                n = export(conn, name, sql, C.OUT_TABLES)
            except sqlite3.Error as e:
                print(f"  !! {name}: {e}")
                continue
            if n is not None:
                print(f"  {sqlfile.name:26s} -> {name}.csv ({n} rows)")
    conn.commit()
    conn.close()
    print("\nDone. Tables written to outputs/tables/")


if __name__ == "__main__":
    main()
