"""Project 1 — Revenue Decline Diagnostic: single source of truth.

Everything the pipeline needs lives here: filesystem paths, the dimensions of
the simulated retail chain, its product catalogue, and the *story factors* that
the data generator bakes into Q3 FY2026 to manufacture the YoY revenue decline.

Reading this file top-to-bottom is the fastest way to understand the project.
The `STORY` block near the bottom is effectively the answer key — but it is
also written out for humans in docs/00_ground_truth.md.
"""

from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths                                                                        #
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parents[1]
PYLIBS = REPO_ROOT / "pylibs"          # vendored numpy/matplotlib used by tools/

DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROC = PROJECT_ROOT / "data" / "processed"
OUT_TABLES = PROJECT_ROOT / "outputs" / "tables"
OUT_FIGURES = PROJECT_ROOT / "outputs" / "figures"
DOCS = PROJECT_ROOT / "docs"
SQL_DIR = PROJECT_ROOT / "sql"
DB_PATH = PROJECT_ROOT / "data" / "revenue_decline.sqlite"

# --------------------------------------------------------------------------- #
# Reproducibility                                                              #
# --------------------------------------------------------------------------- #
SEED = 20260914
CURRENCY = "KSh"

# --------------------------------------------------------------------------- #
# Business definition                                                          #
# --------------------------------------------------------------------------- #
COMPANY = "Mavuno Home & Care"
COMPANY_DESC = (
    "A six-store household, personal-care and grocery retailer in Kenya. "
    "Stores in Nairobi (3), Nakuru, Mombasa and Kisumu."
)

# The two comparison periods. We compare like-for-like quarters to neutralise
# seasonality (Ch. 12): Q3 FY2026 (Jul-Sep 2026) vs Q3 FY2025 (Jul-Sep 2025).
PERIODS = [
    {
        "key": "2025Q3",
        "label": "Q3 2025",
        "year": 2025,
        "start": "2025-07-01",
        "end": "2025-09-30",
        "phase": "base",
    },
    {
        "key": "2026Q3",
        "label": "Q3 2026",
        "year": 2026,
        "start": "2026-07-01",
        "end": "2026-09-30",
        "phase": "current",
    },
]

BASE_PERIOD_KEY = "2025Q3"
CURRENT_PERIOD_KEY = "2026Q3"

# --------------------------------------------------------------------------- #
# Dimensions                                                                   #
# --------------------------------------------------------------------------- #
# `size` is the store's share-of-chain scale (footfall/floor space proxy).
BRANCHES = [
    {"id": "BR01", "name": "Town Centre",     "region": "Nairobi",     "size": 1.35, "opened": "2016-03-01"},
    {"id": "BR02", "name": "Westlands",       "region": "Nairobi",     "size": 1.10, "opened": "2017-09-01"},
    {"id": "BR03", "name": "Thika Road",      "region": "Nairobi",     "size": 1.00, "opened": "2018-11-01"},
    {"id": "BR04", "name": "Nakuru CBD",      "region": "Rift Valley", "size": 0.75, "opened": "2019-06-01"},
    {"id": "BR05", "name": "Mombasa Nyali",   "region": "Coast",       "size": 0.95, "opened": "2020-10-01"},
    {"id": "BR06", "name": "Kisumu Lakefront", "region": "Nyanza",     "size": 0.70, "opened": "2021-08-01"},
]

# Customer lifecycle segments (Ch. 28). Every customer is classified by the CRM
# into exactly one segment per period; the label is carried on each sales line
# so the whole fact table can be sliced by lifecycle stage.
#
#   visits_per_month : how often a customer in this segment shops
#   lines_per_order  : basket breadth (number of line items per trip)
#   share            : proportion of the active customer base
SEGMENTS = [
    {"name": "Loyal",       "share": 0.20, "visits_per_month": 3.0, "lines_per_order": 4.6, "discount_uplift": 0.010},
    {"name": "Regular",     "share": 0.35, "visits_per_month": 2.0, "lines_per_order": 3.5, "discount_uplift": 0.000},
    {"name": "At-Risk",     "share": 0.20, "visits_per_month": 1.3, "lines_per_order": 3.0, "discount_uplift": 0.015},
    {"name": "New",         "share": 0.15, "visits_per_month": 1.2, "lines_per_order": 2.5, "discount_uplift": 0.020},
    {"name": "Hibernating", "share": 0.10, "visits_per_month": 1.0, "lines_per_order": 2.0, "discount_uplift": 0.025},
]
SEGMENT_NAMES = [s["name"] for s in SEGMENTS]

CHANNELS = [{"name": "In-store", "share": 0.86}, {"name": "Online", "share": 0.14}]

# Active customers per store of size 1.0, per quarter. Scaling knob for the
# whole dataset: raising it raises the CSV size and the runtime.
BASE_CUSTOMERS_PER_BRANCH = 900

# --------------------------------------------------------------------------- #
# Product catalogue                                                            #
# --------------------------------------------------------------------------- #
# `weight`  = share of all line items that fall in this category
# `margin`  = gross margin (1 - unit_cost / unit_price)
# `discount`= baseline promotional discount depth
# `skus`    = (code, name, list price in KSh, relative popularity weight)
CATEGORIES = [
    {
        "name": "Groceries", "weight": 0.24, "margin": 0.12, "discount": 0.030,
        "skus": [
            ("GR01", "Maize Flour 2kg", 135, 3.0),
            ("GR02", "Rice Pishori 5kg", 680, 1.6),
            ("GR03", "Cooking Oil 3L", 910, 1.4),
            ("GR04", "Sugar 2kg", 320, 2.2),
            ("GR05", "Wheat Flour 2kg", 165, 1.8),
            ("GR06", "Salt 1kg", 35, 2.0),
        ],
    },
    {
        "name": "Fresh Produce", "weight": 0.14, "margin": 0.26, "discount": 0.020,
        "skus": [
            ("FP01", "Tomatoes 1kg", 120, 2.0),
            ("FP02", "Potatoes 5kg", 360, 1.6),
            ("FP03", "Onions 1kg", 155, 1.7),
            ("FP04", "Sukuma Wiki Bunch", 35, 3.0),
            ("FP05", "Bananas 1kg", 160, 1.4),
        ],
    },
    {
        "name": "Dairy & Eggs", "weight": 0.12, "margin": 0.18, "discount": 0.020,
        "skus": [
            ("DE01", "Fresh Milk 500ml", 65, 4.0),
            ("DE02", "Eggs Tray (30)", 470, 1.5),
            ("DE03", "Yoghurt 1L", 260, 1.3),
            ("DE04", "Butter 250g", 420, 1.0),
            ("DE05", "Cheese 200g", 380, 0.8),
        ],
    },
    {
        "name": "Beverages", "weight": 0.14, "margin": 0.21, "discount": 0.050,
        "skus": [
            ("BV01", "Soda 2L", 190, 2.4),
            ("BV02", "Bottled Water 5L", 160, 3.0),
            ("BV03", "Juice 1L", 265, 1.6),
            ("BV04", "Tea Leaves 500g", 430, 1.4),
            ("BV05", "Coffee 100g", 370, 0.9),
        ],
    },
    {
        "name": "Bakery", "weight": 0.08, "margin": 0.45, "discount": 0.020,
        "skus": [
            ("BK01", "Bread 600g", 75, 4.0),
            ("BK02", "Cake Slice", 160, 1.2),
            ("BK03", "Mandazi 6pk", 130, 1.6),
            ("BK04", "Buns 6pk", 110, 1.5),
        ],
    },
    {
        "name": "Personal Care", "weight": 0.13, "margin": 0.36, "discount": 0.060,
        "skus": [
            ("PC01", "Bath Soap 800g", 360, 3.0),          # hero SKU
            ("PC02", "Shampoo 400ml", 570, 2.2),           # hero SKU
            ("PC03", "Body Lotion 400ml", 620, 1.6),
            ("PC04", "Toothpaste 150ml", 295, 2.0),
            ("PC05", "Deodorant 250ml", 470, 1.1),
            ("PC06", "Sanitary Pads 10pk", 210, 1.5),
        ],
    },
    {
        "name": "Household & Cleaning", "weight": 0.10, "margin": 0.30, "discount": 0.050,
        "skus": [
            ("HC01", "Detergent 2kg", 780, 2.6),
            ("HC02", "Dish Soap 1L", 310, 2.0),
            ("HC03", "Bleach 1L", 215, 1.4),
            ("HC04", "Tissue 10pk", 620, 1.8),
            ("HC05", "Scouring Powder 500g", 160, 1.5),
        ],
    },
    {
        "name": "Baby & Kids", "weight": 0.05, "margin": 0.24, "discount": 0.040,
        "skus": [
            ("BK11", "Diapers 30pk", 1450, 1.8),
            ("BK12", "Baby Wipes 80pk", 420, 2.0),
            ("BK13", "Baby Cereal 500g", 680, 1.2),
        ],
    },
]
CATEGORY_NAMES = [c["name"] for c in CATEGORIES]

HERO_SKUS = ["PC01", "PC02"]   # the two SKUs at the centre of the stock-out

# --------------------------------------------------------------------------- #
# THE STORY — what the generator bakes into Q3 FY2026                          #
# --------------------------------------------------------------------------- #
# Targets for the mechanism identity  Revenue = Customers x Frequency x AOV.
#   customers  : active customers, YoY
#   frequency  : orders per customer, YoY
#   aov        : average order value, YoY
# The product of the three (~0.90) is the ~10% headline decline.
STORY = {
    "headline_target": -0.10,
    # Revenue = Customers x Frequency x AOV. These are the *intended* YoY moves;
    # the realized values are measured from the data and reported in
    # outputs/validation_report.md (they land within ~0.5pp of these targets).
    "mechanism_target": {"customers": 0.055, "frequency": -0.114, "aov": -0.041},

    # A snapshot of the migrating customer base. Loyal customers decay
    # downwards; a large inflow of brand-new (cheap-to-serve, low-frequency)
    # customers masks the loss in the headline customer count.
    "new_customer_inflow_multiple": 1.45,   # x the number of Q3'25 "New" customers

    # Retention is the problem: even customers who stay lose shopping frequency.
    "frequency_factor": {
        "Loyal": 0.92, "Regular": 0.94, "At-Risk": 0.88,
        "New": 1.00, "Hibernating": 0.97,
    },

    # List-price inflation in FY2026 (cost pressures). Nominal AOV still falls
    # because discounting deepens and the mix shifts to cheaper baskets.
    "price_inflation": 0.045,
    "cost_inflation": 0.030,

    # Deepened promotional discounting, concentrated in Beverages (a local price
    # war). Added on top of each category's baseline discount.
    "discount_uplift": {"Beverages": 0.130, "Groceries": 0.045, "Household & Cleaning": 0.030},

    # BR03 Thika Road: road-works cut store access for the whole quarter.
    # Applied to Q3 FY2026 only.
    "branch_footfall_factor": {"BR03": 0.80},

    # BR05 Mombasa Nyali: a supply failure takes the two hero Personal Care SKUs
    # off the shelf for six weeks. This is the single largest cell in the
    # branch x product x segment cross-cut. Demand-side spillover shrinks the
    # basket of affected trips (customers buy less when their reason to visit
    # is unavailable).
    "stockout": {
        "branch_id": "BR05",
        "category": "Personal Care",
        "sku_codes": HERO_SKUS,
        "start": "2026-08-10",
        "end": "2026-09-20",
        "hero_availability": 0.10,       # hero SKUs on shelf ~10% of the window
        "category_availability": 0.62,   # rest of the category partially depleted
        "spillover_line_factor": 0.68,   # basket erosion on affected trips
    },

    # Everything not touched by the story grows gently.
    "steady_growth": 1.02,
}

# --------------------------------------------------------------------------- #
# Customer migration matrix (Q3 2025 segment -> Q3 2026 outcome)               #
# --------------------------------------------------------------------------- #
# This is what makes the retention story *provable*: the same customer IDs are
# carried across both periods, so the analysis can measure real cohort decay
# rather than comparing two unrelated snapshots. "Lapsed" means the customer
# made zero purchases in Q3 FY2026.
#
#   from_segment -> {to_segment: probability}   (each row sums to 1.0)
MIGRATION = {
    "Loyal":       {"Loyal": 0.70, "Regular": 0.17, "At-Risk": 0.06, "Hibernating": 0.03, "Lapsed": 0.04},
    "Regular":     {"Loyal": 0.16, "Regular": 0.68, "At-Risk": 0.09, "Hibernating": 0.03, "Lapsed": 0.04},
    "At-Risk":     {"Regular": 0.07, "At-Risk": 0.55, "Hibernating": 0.12, "Lapsed": 0.26},
    "New":         {"Regular": 0.30, "At-Risk": 0.33, "Hibernating": 0.13, "Lapsed": 0.24},
    "Hibernating": {"At-Risk": 0.06, "Hibernating": 0.44, "Lapsed": 0.50},
}

# New customers acquired in Q3 FY2026 (not present in the Q3 2025 roster).
# They all enter as "New" and are assigned a home branch proportionally.
NEW_CUSTOMER_SOURCE = "Q3 2026 acquisition"

# --------------------------------------------------------------------------- #
# Planted data-quality issues (Ch. 13-17)                                      #
# --------------------------------------------------------------------------- #
# The raw POS export is deliberately imperfect so the cleaning step has real
# work to do and the quality report has real findings. Counts are absolute.
# The unattributed rows are deliberately ~1% of volume: enough that the segment
# decomposition does NOT sum to the group total, so the analysis has to declare
# a coverage limit and reconcile the gap (Ch. 26).
DQ_ISSUES = {
    "duplicate_lines": 26,          # exact duplicate (invoice_id, line_id)
    "invalid_quantity": 17,         # quantity <= 0 or absurd (data-entry errors)
    "out_of_period_dates": 23,      # dates outside the two comparison quarters
    "null_discount": 84,            # discount_pct missing -> treated as 0
    "messy_category_labels": 130,   # "personal care", "Personal-Care", "personal  care"
    "null_customer": 1500,          # anonymous walk-ins (legitimate, but a coverage limit)
    "unknown_sku": 12,              # SKU code not present in dim_product
    "duplicate_invoice_header": 15,  # same invoice_id reused across two dates
}

# Category label variants used to plant the messy-label data-quality issue.
MESSY_CATEGORY_LABELS = [
    ("Personal Care", ["personal care", "Personal-Care", "Personal  Care"]),
    ("Household & Cleaning", ["household & cleaning", "Household and Cleaning"]),
    ("Baby & Kids", ["baby & kids", "Baby&Kids"]),
    ("Fresh Produce", ["fresh produce"]),
]


def branch_by_id(branch_id: str) -> dict:
    return next(b for b in BRANCHES if b["id"] == branch_id)


def segment_by_name(name: str) -> dict:
    return next(s for s in SEGMENTS if s["name"] == name)


def category_by_name(name: str) -> dict:
    return next(c for c in CATEGORIES if c["name"] == name)


def all_skus() -> list:
    """Flat catalogue: one dict per SKU with its category attached."""
    out = []
    for cat in CATEGORIES:
        for code, name, price, pop in cat["skus"]:
            out.append({
                "product_id": code,
                "product_name": name,
                "category": cat["name"],
                "list_price": float(price),
                "popularity": float(pop),
                "gross_margin": cat["margin"],
                "base_discount": cat["discount"],
                "is_hero": code in HERO_SKUS,
            })
    return out


def ensure_dirs() -> None:
    for p in (DATA_RAW, DATA_PROC, OUT_TABLES, OUT_FIGURES, DOCS):
        p.mkdir(parents=True, exist_ok=True)
