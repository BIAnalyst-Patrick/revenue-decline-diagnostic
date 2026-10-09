"""Every visual in the project, built from outputs/tables/*.csv.

Each figure is a decision aid, not decoration: it exists to make one sentence of
the findings report impossible to argue with.

The *look* lives in `src/theme.py` now, so the whole pack shares one palette with
the dashboard: a cream surface, **green for growth, orange for decline**, and a
value label on every bar and every point, so no chart has to be read off an axis.

  01 headline waterfall      — one scary number -> three mechanisms
  02 mechanism identity      — customers / frequency / AOV indexed to 100
  03 branch waterfall        — where the money went, by store
  04 branch x category heat  — the intersection, at a glance
  05 category decline        — KSh and % side by side (denominator matters)
  06 segment waterfall       — new customers vs shrinking repeat segments
  07 cohort retention        — who came back
  08 stock-out timeline      — the evidence behind the biggest cell
  09 discount depth          — the price/mix half of the AOV story
  10 driver partition        — four ranked department problems

Run:  python3 src/make_figures.py
"""

import sys
from pathlib import Path

import _bootstrap  # noqa: F401

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D

sys.path.append(str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
import theme as T  # noqa: E402
from decompose import load, num  # noqa: E402

T.apply()


def save(fig, name):
    path = C.OUT_FIGURES / name
    fig.savefig(path)
    plt.close(fig)
    print(f"  wrote {name}")


# --------------------------------------------------------------------------- #
def fig_headline_waterfall():
    rows = load("decomp_mechanism_waterfall")
    start = num(rows[0], "effect")
    deltas = [num(r, "effect") for r in rows[1:-1]]

    fig, ax = T.new_fig(10.0, 5.1)
    labels = ["Customers", "Orders per\ncustomer", "Average order\nvalue"]
    T.waterfall(ax, start, deltas, C.PERIODS[0]["label"], C.PERIODS[1]["label"], labels)
    ax.margins(y=0.20)
    T.panel(ax, grid="y")
    T.title(ax, "One headline, three mechanisms: revenue = customers x frequency x basket",
            kicker="REVENUE BRIDGE  ·  Q3 2025 → Q3 2026")
    ax.set_ylabel(f"Net revenue ({C.CURRENCY})")
    T.guardrail(fig, "Attribution: log-mean Divisia (order-independent). Attributed lines only. "
                     "Green = a gain to revenue, orange = a loss. See decomp_mechanism_sensitivity.csv.")
    save(fig, "01_headline_waterfall.png")


def fig_mechanism_identity():
    mech = load("mechanism_by_period")
    o0, c0 = num(mech[0], "orders"), num(mech[0], "customers")
    o1, c1 = num(mech[1], "orders"), num(mech[1], "customers")
    r0, r1 = num(mech[0], "net_revenue"), num(mech[1], "net_revenue")
    series = {
        "Active customers": c1 / c0 * 100,
        "Orders per customer": (o1 / c1) / (o0 / c0) * 100,
        "Average order value": (r1 / o1) / (r0 / o0) * 100,
        "Net revenue": r1 / r0 * 100,
    }
    names = list(series.keys())
    vals = [series[n] for n in names]
    # the values are indices around 100, so the *sign of the move* is v - 100
    colors = [T.color_for(v - 100) for v in vals]

    fig, ax = T.new_fig(9.4, 4.7)
    y = np.arange(len(names))
    bars = ax.barh(y, vals, color=colors, height=0.58, zorder=3)
    ax.axvline(100, color=T.INK, lw=1.2, ls=(0, (4, 3)), zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xlim(84, 112)
    T.panel(ax, grid="x")
    T.label_bars(ax, bars, [f"{v:.1f}" for v in vals], orient="h")
    ax.text(99.6, len(names) - 0.30, "Q3 2025 = 100", fontsize=9, color=T.MUTED,
            ha="right", va="bottom")
    T.title(ax, "The engine failed, not the funnel: customers up, frequency down",
            kicker="INDEXED TO THE BASE QUARTER  ·  Q3 2025 = 100")
    T.guardrail(fig, "Green = ahead of the base quarter, orange = behind it. "
                     "A value above 100 is growth; below 100 is decline.")
    save(fig, "02_mechanism_identity.png")


def fig_branch_waterfall():
    rows = load("decomp_structure_branch")
    mc = load("decomp_mechanism_waterfall")
    start = num(mc[0], "effect")
    losses = sorted([r for r in rows if num(r, "delta") < 0], key=lambda r: num(r, "delta"))
    labels = [f"{r['slice'].replace(' ', chr(10), 1)}\n{T.pct(num(r, 'yoy_pct'))}" for r in losses]
    deltas = [num(r, "delta") for r in losses]
    other = sum(num(r, "delta") for r in rows if num(r, "delta") >= 0)
    if abs(other) > 1:
        labels.append("Other stores")
        deltas.append(other)

    fig, ax = T.new_fig(11.8, 5.3)
    T.waterfall(ax, start, deltas, C.PERIODS[0]["label"], C.PERIODS[1]["label"], labels)
    ax.margins(y=0.24)
    ax.tick_params(axis="x", labelsize=8.3)
    T.panel(ax, grid="y")
    T.title(ax, "Where the money went, by store: two stores carry 71% of the decline",
            kicker="STORE CONTRIBUTION  ·  KSh, like-for-like quarter")
    ax.set_ylabel(f"Net revenue ({C.CURRENCY})")
    T.guardrail(fig, "Bars are ordered by the size of the loss; the figures under each store are "
                     "that store's revenue change vs the same quarter last year.")
    save(fig, "03_branch_waterfall.png")


def fig_branch_category_heat():
    rows = load("crosscut_branch_category")
    branches, cats = [], []
    for r in rows:
        if r["branch_name"] not in branches:
            branches.append(r["branch_name"])
        if r["category"] not in cats:
            cats.append(r["category"])
    grid = np.full((len(branches), len(cats)), np.nan)
    for r in rows:
        grid[branches.index(r["branch_name"]), cats.index(r["category"])] = num(r, "yoy_pct")

    vmax = 30.0
    cmap = T.diverging_cmap()
    norm = Normalize(vmin=-vmax, vmax=vmax)

    fig, ax = T.new_fig(12.0, 4.9)
    im = ax.imshow(grid, cmap=cmap, norm=norm, aspect="auto")

    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels([c.replace(" & ", " &\n").replace(" ", "\n") for c in cats], fontsize=8.6)
    ax.set_yticks(range(len(branches)))
    ax.set_yticklabels(branches, fontsize=9.4)

    for i in range(len(branches)):
        for j in range(len(cats)):
            v = grid[i, j]
            if not np.isnan(v):
                rgba = cmap(norm(v))
                face = "#%02X%02X%02X" % tuple(int(round(c * 255)) for c in rgba[:3])
                weight = "bold" if abs(v) >= 10 else "normal"
                ax.text(j, i, f"{v:+.0f}%", ha="center", va="center", fontsize=8.0,
                        color=T.text_on(face), fontweight=weight, zorder=5)

    ax.set_xticks(np.arange(-0.5, len(cats), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(branches), 1), minor=True)
    ax.grid(which="minor", color=T.CREAM, lw=2.2)
    ax.tick_params(which="minor", length=0)
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="both", length=0)

    cb = fig.colorbar(im, ax=ax, shrink=0.86, pad=0.015)
    cb.set_label("Revenue YoY %", color=T.INK, fontsize=9.4)
    cb.outline.set_visible(False)
    cb.ax.tick_params(colors=T.MUTED, labelsize=8.6)

    T.title(ax, "The intersection: revenue YoY % by store x category",
            kicker="ORANGE = DECLINE  ·  GREEN = GROWTH  ·  0-CENTRED")
    T.guardrail(fig, "Each cell is one store x category pair. The ramp is centred on 0%, so "
                     "colour reads as sign and intensity reads as depth of decline.")
    save(fig, "04_branch_category_heatmap.png")


def fig_category_decline():
    rows = [r for r in load("decomp_structure_category") if r["slice"] != "Unclassified"]
    rows = sorted(rows, key=lambda r: num(r, "delta"))
    names = [r["slice"] for r in rows]
    deltas = [num(r, "delta") for r in rows]
    yoys = [num(r, "yoy_pct") for r in rows]
    y = np.arange(len(names))[::-1]

    fig, axes = T.new_fig(13.0, 4.9, 1, 2, gridspec_kw={"wspace": 0.30})

    # --- left: absolute KSh change, now labelled ------------------------- #
    lcol = [T.color_for(d) for d in deltas]
    left = axes[0]
    bars = left.barh(y, deltas, color=lcol, height=0.6, zorder=3)
    left.set_yticks(y)
    left.set_yticklabels(names, fontsize=9.4)
    left.xaxis.set_major_formatter(T.KES_FMT)
    left.axvline(0, color=T.MUTED, lw=1)
    left.margins(x=0.16)
    T.label_bars(left, bars, [f"{d / 1e6:+,.2f}M" for d in deltas], orient="h", inside=True)
    T.panel(left, grid="x")
    T.title(left, f"KSh change: {C.PERIODS[0]['label']} → {C.PERIODS[1]['label']}",
            kicker="ABSOLUTE  ·  THE BIGGEST NUMBER")

    # --- right: percentage change, the denominator lesson ---------------- #
    rcol = [T.color_for(v) for v in yoys]
    right = axes[1]
    bars2 = right.barh(y, yoys, color=rcol, height=0.6, zorder=3)
    right.set_yticks(y)
    right.set_yticklabels([])
    right.axvline(0, color=T.MUTED, lw=1)
    right.margins(x=0.22)
    T.label_bars(right, bars2, [f"{v:+.1f}%" for v in yoys], orient="h", fontsize=9.0)
    T.panel(right, grid="x")
    T.title(right, "YoY %: the denominator changes the ranking",
            kicker="RELATIVE  ·  THE FASTEST FALL")

    T.fig_title(fig, "Categories: Groceries is the biggest number, Beverages the fastest fall",
                kicker="ORANGE = DECLINE, GREEN = GROWTH  ·  SAME DATA, TWO DENOMINATORS")
    T.guardrail(fig, "Groceries loses the most money; Beverages falls fastest. Either number alone "
                     "gives a different, misleading brief — the two panels must be read together.",
                y=-0.05)
    save(fig, "05_category_decline.png")


def fig_segment_waterfall():
    rows = load("decomp_structure_segment")
    mc = load("decomp_mechanism_waterfall")
    start = num(mc[0], "effect")
    order = sorted(rows, key=lambda r: num(r, "delta"))
    seq = [r for r in order if num(r, "delta") <= 0] + [r for r in order if num(r, "delta") > 0]
    labels = [f"{r['slice']}\n{T.pct(num(r, 'yoy_pct'), 0)}" for r in seq]
    deltas = [num(r, "delta") for r in seq]

    fig, ax = T.new_fig(10.4, 5.2)
    T.waterfall(ax, start, deltas, C.PERIODS[0]["label"], C.PERIODS[1]["label"], labels)
    ax.margins(y=0.22)
    T.panel(ax, grid="y")
    T.title(ax, "Every segment shrank — except the new customers we bought",
            kicker="CUSTOMER SEGMENT CONTRIBUTION  ·  KSh")
    ax.set_ylabel(f"Net revenue ({C.CURRENCY})")
    T.guardrail(fig, "New customers returned +KSh 1.34M; the four established segments gave back "
                     "KSh 6.55M between them. Green = the one segment that grew.")
    save(fig, "06_segment_waterfall.png")


def fig_cohort_retention():
    rows = load("cohort_retention_by_segment")
    summ = load("cohort_retention_summary")[0]
    benchmark = num(summ, "return_rate_pct")
    rows = sorted(rows, key=lambda r: num(r, "return_rate_pct"))
    names = [r["segment_2025q3"] for r in rows]
    rates = [num(r, "return_rate_pct") for r in rows]
    counts = [num(r, "customers") for r in rows]

    fig, ax = T.new_fig(9.8, 4.6)
    y = np.arange(len(names))
    bars = ax.barh(y, rates, color=[T.GREEN if v >= benchmark else T.ORANGE for v in rates],
                   height=0.6, zorder=3)
    ax.axvline(benchmark, color=T.INK, ls=(0, (4, 3)), lw=1.2, zorder=4)
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xlim(0, 122)
    T.panel(ax, grid="x")
    T.label_bars(ax, bars, [f"{v:.1f}%   (n={n:,.0f})" for v, n in zip(rates, counts)],
                 orient="h", fontsize=9.2)
    ax.text(benchmark, -0.62, f"group return rate {benchmark:.1f}%", fontsize=9,
            color=T.INK, ha="center", va="bottom")
    T.title(ax, "Retention is healthy where it matters — the leak is trip frequency",
            kicker="Q3 2025 CUSTOMERS WHO CAME BACK IN Q3 2026")
    T.guardrail(fig, f"{num(summ, 'lapsed'):,.0f} of {num(summ, 'customers_2025q3'):,.0f} "
                     f"Q3 2025 customers did not return; {num(summ, 'new_in_2026'):,.0f} new "
                     f"customers arrived. Green = at or above the group return rate.")
    save(fig, "07_cohort_retention.png")


def fig_stockout_timeline():
    daily = load("stockout_daily_incident")
    rev = load("stockout_daily_revenue")
    so = C.STORY["stockout"]

    fig, axes = T.new_fig(11.8, 6.6, 2, 1, sharex=False,
                          gridspec_kw={"height_ratios": [1, 1.3], "hspace": 0.55})

    # --- panel 1: shelf availability ------------------------------------- #
    ax = axes[0]
    days = sorted({r["date"] for r in daily})
    x = np.arange(len(days))
    for sku, color, label in (("PC01", T.ORANGE, "PC01 Bath Soap 800g"),
                              ("PC02", "#F79A4B", "PC02 Shampoo 400ml")):
        vals = np.array([next((int(num(r, "in_stock")) for r in daily
                               if r["date"] == d and r["product_id"] == sku), 1) for d in days])
        ax.step(x, vals, where="post", color=color, lw=2.0, label=label, zorder=4)
    i0, i1 = days.index(so["start"]), days.index(so["end"])
    ax.axvspan(i0, i1, color=T.BAND, alpha=0.9, zorder=0)
    ax.text((i0 + i1) / 2, 1.42, "supply incident  ·  6 weeks off shelf", ha="center",
            fontsize=9.2, color=T.ORANGE, fontweight="bold")
    ax.set_yticks([0, 1], ["out of\nstock", "on\nshelf"], fontsize=9)
    ax.set_ylim(-0.35, 1.75)
    ax.set_xlim(-1, len(days))
    T.panel(ax, grid=None)
    ax.legend(loc="center left", fontsize=8.8)
    T.title(ax, f"Evidence: hero Personal Care SKUs at {C.STORY['stockout']['branch_id']} "
                f"(Mombasa Nyali), Q3 2026",
            kicker="SHELF AVAILABILITY  ·  THE ROOT CAUSE, WITH DATES")

    # --- panel 2: same-category revenue, both years ----------------------- #
    ax = axes[1]
    n_days = 0
    ends = []
    for pk, color, label in ((C.BASE_PERIOD_KEY, T.MUTED, C.PERIODS[0]["label"]),
                             (C.CURRENT_PERIOD_KEY, T.ORANGE, C.PERIODS[1]["label"])):
        rows = sorted([r for r in rev if r["period_key"] == pk], key=lambda r: r["date"])
        vals = np.array([num(r, "net_revenue") for r in rows])
        k = 7
        smooth = np.convolve(vals, np.ones(k) / k, mode="same") if len(vals) >= k else vals
        ax.plot(np.arange(len(vals)), smooth, color=color, lw=2.0, label=label, zorder=4)
        n_days = max(n_days, len(vals))
        ends.append((float(vals.mean()), color, label))
    ax.axvspan(i0, i1, color=T.BAND, alpha=0.9, zorder=0)
    ax.set_xlim(-1, n_days + 22)
    ax.margins(y=0.18)
    for ymean, color, label in ends:
        ax.annotate(f"{label} avg  {ymean / 1e3:,.0f}K/day", (n_days + 2, ymean),
                    xytext=(0, 0), textcoords="offset points", fontsize=8.8,
                    fontweight="bold", color=color, va="center", ha="left", zorder=6)
        ax.scatter([n_days + 2], [ymean], color=color, s=0, zorder=5)
    T.panel(ax, grid="y")
    ax.yaxis.set_major_formatter(T.KES_K_FMT)
    ax.set_ylabel(f"Net revenue ({C.CURRENCY})/day")
    T.title(ax, "Personal Care revenue at that store, 7-day rolling",
            kicker="THE SAME CATEGORY, BOTH YEARS  ·  KSh per day")
    ax.set_xlabel("Day of quarter")
    ax.set_ylabel(f"Net revenue ({C.CURRENCY})/day")

    T.guardrail(fig, f"Availability collapsed to {num(so, 'hero_availability'):.0%} of the window "
                     f"for the two hero SKUs. Without this shelf table the report could only say "
                     f"'probably supply'.", y=-0.02)
    save(fig, "08_stockout_timeline.png")


def fig_discount_depth():
    rows = [r for r in load("pricing_discount_depth_by_category")
            if r["category"] != "Unclassified"]
    rows = sorted(rows, key=lambda r: num(r, "discount_pp_change"), reverse=True)
    changes = [num(r, "discount_pp_change") for r in rows]
    grad = T.severity_colors(changes, "orange")

    fig, ax = T.new_fig(10.2, 5.0)
    y = np.arange(len(rows))[::-1]
    for yy, r, col in zip(y, rows, grad):
        a, b = num(r, "discount_pct_2025"), num(r, "discount_pct_2026")
        ax.plot([a, b], [yy, yy], color="#DED3BE", lw=2.6, zorder=2,
                solid_capstyle="round")
        ax.scatter([a], [yy], color=T.MUTED, s=46, zorder=3)
        ax.scatter([b], [yy], color=col, s=64, zorder=4)
        ax.text(max(a, b) + 0.45, yy, T.pp(num(r, "discount_pp_change")),
                va="center", ha="left", fontsize=9.2, fontweight="bold",
                color=T.ORANGE if num(r, "discount_pp_change") > 1 else T.INK, zorder=6)
        ax.text(min(a, b) - 0.75, yy, f"{min(a, b):.1f}%", va="center", ha="right",
                fontsize=8.6, color=T.MUTED, zorder=6)

    ax.set_yticks(y)
    ax.set_yticklabels([r["category"] for r in rows], fontsize=9.4)
    ax.set_xlim(-1.6, max(num(r, "discount_pct_2026") for r in rows) + 3.4)
    T.panel(ax, grid="x")
    ax.set_xlabel("% of gross revenue given away as discount")
    ax.legend(handles=[Line2D([], [], marker="o", ls="", color=T.MUTED,
                              label=C.PERIODS[0]["label"], markersize=8),
                       Line2D([], [], marker="o", ls="", color=T.ORANGE,
                              label=C.PERIODS[1]["label"], markersize=9)],
              loc="lower right")
    T.title(ax, "Prices rose, but so did discounting — and the depth is concentrated",
            kicker="DUMBBELL: PRIOR YEAR → CURRENT YEAR  ·  PERCENTAGE POINTS")
    T.guardrail(fig, "The dot colour runs light-to-dark with the size of the change, so the "
                     "deepest new discounting is the darkest mark.")
    save(fig, "09_discount_depth.png")


def fig_driver_partition():
    rows = [r for r in load("decomp_driver_partition")
            if not r["driver"].lower().startswith("reconciliation")]
    rows.sort(key=lambda r: num(r, "delta"))
    labels = [r["owner"] for r in rows]
    deltas = [num(r, "delta") for r in rows]
    shares = [num(r, "pct_of_total_decline") for r in rows]
    # gradient by magnitude, so the largest problem is the darkest orange
    colors = T.severity_colors([abs(d) for d in deltas], "orange")

    fig, ax = T.new_fig(11.0, 4.6)
    y = np.arange(len(rows))[::-1]
    bars = ax.barh(y, deltas, color=colors, height=0.62, zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10)
    ax.xaxis.set_major_formatter(T.KES_FMT)
    ax.axvline(0, color=T.MUTED, lw=1)
    ax.margins(x=0.05)
    T.panel(ax, grid="x")
    for yy, d, s in zip(y, deltas, shares):
        ax.text(d, yy - 0.34, f"{d / 1e6:,.2f}M  ·  {s:.0f}% of the decline",
                va="top", ha="left", fontsize=9.4, fontweight="bold", color=T.INK, zorder=6)
    ax.set_xlim(min(deltas) * 1.30, abs(min(deltas)) * 0.10)
    T.title(ax, "One headline → four ranked, owned problems",
            kicker="DISJOINT PARTITION  ·  SUMS TO THE WHOLE DECLINE, NO DOUBLE COUNTING")
    T.guardrail(fig, "Each store x category x segment cell is assigned to exactly one owner, so the "
                     "bars add up to the -KSh 5.21M. Darker orange = a bigger problem.")
    save(fig, "10_driver_partition.png")


def main():
    C.ensure_dirs()
    print("Generating figures ->", C.OUT_FIGURES)
    fig_headline_waterfall()
    fig_mechanism_identity()
    fig_branch_waterfall()
    fig_branch_category_heat()
    fig_category_decline()
    fig_segment_waterfall()
    fig_cohort_retention()
    fig_stockout_timeline()
    fig_discount_depth()
    fig_driver_partition()
    print("Done.")


if __name__ == "__main__":
    main()
