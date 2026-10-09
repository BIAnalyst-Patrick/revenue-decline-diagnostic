"""The house style for Project 1 — matched to the Power BI dashboard.

Import this before building any figure so the whole pack shares one palette:

    import theme
    theme.apply()

Design rules, the same ones the dashboard follows:

* **green means growth, orange means decline.** Never the reverse, never a
  third hue competing for attention. `#259741` / `#FB6107`.
* Gradients encode *intensity only* (how deep a decline runs) and are always
  anchored so that the sign is still readable at a glance.
* **Every bar and every point carries its own value label.** No chart in this
  pack should make the reader trace back to an axis.
* One page colour (`#FFFDF0`), one panel colour (`#FFEFD5`), one warm ink
  (`#27241B`). The chrome stays quiet so the data is the loudest thing.

Nothing here computes anything — it is presentation only.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter

# --------------------------------------------------------------------------- #
# Palette                                                                      #
# --------------------------------------------------------------------------- #
GREEN = "#259741"        # growth / positive / "better than baseline"
ORANGE = "#FB6107"       # decline / negative / alert
BOOKEND = "#1B6B34"      # the two total bars in a bridge (darker than a gain)
GREEN_LT = "#7CC47F"     # light end of the growth gradient
ORANGE_LT = "#FBBF92"    # light end of the decline gradient

CREAM = "#FFFDF0"        # page background
PANEL = "#FFEFD5"        # tile / table / band fill
INK = "#27241B"          # primary text
MUTED = "#89877B"        # axis text, footnotes
GRID = "#EFE6D3"         # gridlines and hairlines
BAND = "#FDE3CF"         # highlight band (incident window, "look here")

WHITE = "#FFFFFF"

# One font family for the figures and the reports, so a chart and the page it
# sits on are typographically identical. Matplotlib falls back to DejaVu Sans if
# this is not installed.
FONT = "Liberation Sans"


def apply() -> None:
    """Install the rcParams that give every figure the dashboard surface."""
    plt.rcParams.update({
        "font.family": FONT,
        "font.size": 10.5,
        "figure.facecolor": CREAM,
        "savefig.facecolor": CREAM,
        "axes.facecolor": CREAM,
        "axes.edgecolor": GRID,
        "axes.labelcolor": INK,
        "axes.titlecolor": INK,
        "axes.titlesize": 12.5,
        "axes.titleweight": "bold",
        "text.color": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK,
        "ytick.labelcolor": INK,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "legend.frameon": False,
        "legend.fontsize": 9.0,
        "figure.dpi": 150,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.30,
    })


# --------------------------------------------------------------------------- #
# Colour logic                                                                 #
# --------------------------------------------------------------------------- #
def color_for(value: float, good_is_high: bool = True) -> str:
    """Green when the move is good news, orange when it is bad news."""
    if value == 0:
        return MUTED
    positive = value > 0
    if not good_is_high:
        positive = not positive
    return GREEN if positive else ORANGE


def diverging_cmap() -> LinearSegmentedColormap:
    """Decline -> neutral -> growth. The 0-point sits on the panel colour."""
    return LinearSegmentedColormap.from_list(
        "p1_diverging", [ORANGE, ORANGE_LT, PANEL, GREEN_LT, GREEN])


def orange_cmap() -> LinearSegmentedColormap:
    return LinearSegmentedColormap.from_list("p1_orange", [ORANGE_LT, ORANGE])


def green_cmap() -> LinearSegmentedColormap:
    return LinearSegmentedColormap.from_list("p1_green", [GREEN_LT, GREEN])


def severity_colors(values, cmap: str = "orange") -> list:
    """Map magnitude onto a single-hue gradient (used for ranked bars)."""
    vals = np.asarray(list(values), dtype=float)
    cm = orange_cmap() if cmap == "orange" else green_cmap()
    lo, hi = float(vals.min()), float(vals.max())
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return [ORANGE if cmap == "orange" else GREEN] * len(vals)
    return [cm((v - lo) / (hi - lo)) for v in vals]


def text_on(facecolor, dark: str = INK, light: str = CREAM) -> str:
    """Pick readable label text for a coloured cell (WCAG-ish relative luminance)."""
    r, g, b = (int(facecolor[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
           for c in (r, g, b)]
    lum = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    return dark if lum > 0.42 else light


# --------------------------------------------------------------------------- #
# Number formatting                                                            #
# --------------------------------------------------------------------------- #
def kes_m(x, _pos=None) -> str:
    return f"{x / 1e6:,.1f}M"


def kes_m_signed(x, _pos=None) -> str:
    return f"{x / 1e6:+,.2f}M"


def kes_k(x, _pos=None) -> str:
    return f"{x / 1e3:,.0f}K"


KES_FMT = FuncFormatter(kes_m)
KES_SIGNED_FMT = FuncFormatter(kes_m_signed)
KES_K_FMT = FuncFormatter(kes_k)


def pct(x, decimals: int = 1) -> str:
    return f"{x:+.{decimals}f}%"


def pp(x, decimals: int = 2) -> str:
    return f"{x:+.{decimals}f}pp"


# --------------------------------------------------------------------------- #
# Figure / axes chrome                                                         #
# --------------------------------------------------------------------------- #
def new_fig(w: float, h: float, nrows: int = 1, ncols: int = 1, **kw):
    """A cream figure with cream axes — the dashboard surface."""
    fig, axes = plt.subplots(nrows, ncols, figsize=(w, h), **kw)
    fig.patch.set_facecolor(CREAM)
    for ax in np.atleast_1d(axes).ravel():
        ax.set_facecolor(CREAM)
    return fig, axes


def panel(ax, grid: str | None = None) -> None:
    """Strip the box, warm the hairlines, and add an optional subtle grid."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
        ax.spines[side].set_linewidth(0.9)
    if grid:
        ax.grid(axis=grid, color=GRID, lw=0.9, zorder=0)
        ax.set_axisbelow(True)


def title(ax, headline: str, kicker: str | None = None) -> None:
    """Dashboard-style header: orange eyebrow, bold headline, orange accent rule."""
    if kicker:
        ax.text(0, 1.0 + 0.125, kicker, transform=ax.transAxes, fontsize=9.0,
                color=ORANGE, fontweight="bold", ha="left", va="bottom")
    ax.text(0, 1.0 + 0.042, headline, transform=ax.transAxes, fontsize=12.4,
            color=INK, fontweight="bold", ha="left", va="bottom")
    ax.plot([0, 0.085], [1.0 + 0.012, 1.0 + 0.012], transform=ax.transAxes,
            color=ORANGE, lw=2.8, clip_on=False, solid_capstyle="round")


def fig_title(fig, headline: str, kicker: str | None = None, y: float = 1.04) -> None:
    if kicker:
        fig.text(0.01, y + 0.055, kicker, fontsize=9.0, color=ORANGE,
                 fontweight="bold", ha="left", va="bottom")
    fig.text(0.01, y, headline, fontsize=13.0, color=INK, fontweight="bold",
             ha="left", va="bottom")


def guardrail(fig, text: str, y: float = -0.03) -> None:
    """The footnote band that names the unit, the denominator and the caveat."""
    fig.text(0.005, y, text, fontsize=8.3, color=MUTED, ha="left", va="top")


# --------------------------------------------------------------------------- #
# Data labels                                                                  #
# --------------------------------------------------------------------------- #
def label_bars(ax, bars, texts, orient: str = "v", fontsize: float = 9.0,
               color: str = INK, weight: str = "bold", pad: float = 0.018,
               inside: bool = False) -> None:
    """Write a value on every bar of a BarContainer.

    `orient="v"` labels above a positive bar / below a negative one;
    `orient="h"` labels to the right of a positive bar / to the left of a
    negative one. `inside=True` tucks the label just within the bar end, in
    cream, for bars too long to label outside.
    """
    if orient == "v":
        lo, hi = ax.get_ylim()
    else:
        lo, hi = ax.get_xlim()
    span = (hi - lo) or 1.0
    off = span * pad

    for bar, text in zip(bars, texts):
        if text in (None, ""):
            continue
        if orient == "v":
            x = bar.get_x() + bar.get_width() / 2.0
            h = bar.get_height()
            if inside:
                y, va, col = (h - off, "top", CREAM) if h >= 0 else (h + off, "bottom", CREAM)
            else:
                y, va, col = (h + off, "bottom", color) if h >= 0 else (h - off, "top", color)
            ax.text(x, y, text, ha="center", va=va, fontsize=fontsize,
                    fontweight=weight, color=col, zorder=6)
        else:
            y = bar.get_y() + bar.get_height() / 2.0
            w = bar.get_width()
            if inside:
                x, ha, col = (w - off, "right", CREAM) if w >= 0 else (w + off, "left", CREAM)
            else:
                x, ha, col = (w + off, "left", color) if w >= 0 else (w - off, "right", color)
            ax.text(x, y, text, ha=ha, va="center", fontsize=fontsize,
                    fontweight=weight, color=col, zorder=6)


def label_point(ax, x, y, text, dx: float = 0.0, dy: float = 0.0, **kw):
    """A callout for a line/dumbbell end-point."""
    kw.setdefault("fontsize", 9.0)
    kw.setdefault("fontweight", "bold")
    kw.setdefault("color", INK)
    kw.setdefault("ha", "left")
    kw.setdefault("va", "center")
    kw.setdefault("zorder", 6)
    return ax.annotate(text, (x, y), xytext=(x + dx, y + dy), textcoords="data", **kw)


# --------------------------------------------------------------------------- #
# Composite widgets                                                            #
# --------------------------------------------------------------------------- #
def waterfall(ax, start, deltas, start_label, end_label, mid_labels=None,
              start_color=None, end_color=None, total_color=None):
    """A bridging waterfall: start bar, signed deltas, end bar — all labelled.

    Green is used for a gain, orange for a loss; the two bookend bars are drawn
    in ink/panel tones so the *movement* is what stands out.
    """
    start_color = start_color or BOOKEND
    end_color = end_color or BOOKEND
    total_color = total_color or BOOKEND
    n = len(deltas)
    mid_labels = mid_labels or [""] * n
    running = start
    xs = np.arange(n + 2)

    ax.bar(0, start, color=start_color, width=0.6, zorder=3)
    ax.text(0, start, f"{start / 1e6:,.1f}M", ha="center", va="bottom",
            fontsize=9.5, fontweight="bold", color=INK, zorder=6)

    for i, d in enumerate(deltas, start=1):
        bottom = min(running, running + d)
        ax.bar(i, abs(d), bottom=bottom, width=0.6, zorder=3,
               color=GREEN if d >= 0 else ORANGE)
        ax.plot([i - 0.3, i + 0.3], [running + d, running + d],
                color=MUTED, lw=0.9, zorder=4)
        top = running + d
        if d >= 0:
            ax.text(i, top, f"{d / 1e6:+,.2f}M", ha="center", va="bottom",
                    fontsize=9.4, fontweight="bold", color=GREEN, zorder=6)
        else:
            ax.text(i, bottom, f"{d / 1e6:+,.2f}M", ha="center", va="top",
                    fontsize=9.4, fontweight="bold", color=ORANGE, zorder=6)
        running += d

    ax.bar(n + 1, running, color=end_color, width=0.6, zorder=3)
    ax.text(n + 1, running, f"{running / 1e6:,.1f}M", ha="center", va="bottom",
            fontsize=9.5, fontweight="bold", color=INK, zorder=6)

    ax.set_xticks(xs)
    ax.set_xticklabels([start_label] + list(mid_labels) + [end_label])
    ax.yaxis.set_major_formatter(KES_FMT)
    panel(ax, grid="y")
    return running
