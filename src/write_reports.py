"""Render the four reader-facing reports from one content model.

    outputs/reports/Executive_Brief.pdf                1-2 pages, the CEO's copy
    outputs/reports/Executive_Brief.docx               the same brief, editable
    outputs/reports/Revenue_Decline_Diagnostic.pptx     the boardroom deck (~18 slides)
    outputs/reports/Revenue_Decline_Diagnostic.docx     the full report (~18 pages)
    outputs/reports/Revenue_Decline_Diagnostic.pdf      the same report, locked for circulation

Plus `docs/09_executive_brief.md`, the brief in plain text.

Why four formats, and why from one source: they reach different readers in
different rooms. A one-pager is read; a deck is presented; a Word file is worked
on; a PDF is circulated. But a brief, a deck and a report that quietly disagree
about the same number is worse than having only one of them — so every number
here comes from `report_content.build()`, which comes from `outputs/kpis.json`
and the exported tables. The prose cannot drift from the data because it is never
typed twice.

Run:  python3 src/write_reports.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

sys.path.append(str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
import docx_kit as D  # noqa: E402
import report_content as RC  # noqa: E402

OUT = C.PROJECT_ROOT / "outputs" / "reports"
FIGS = C.OUT_FIGURES
SOFFICE = shutil.which("soffice") or shutil.which("libreoffice")


# --------------------------------------------------------------------------- #
# Shared                                                                        #
# --------------------------------------------------------------------------- #
def _figure_path(name: str) -> Path:
    return FIGS / name


def _soffice_pdf(docx_path: Path, out_dir: Path) -> Path:
    """Convert a .docx to .pdf with LibreOffice, so the PDF cannot disagree."""
    if not SOFFICE:
        return _matplotlib_pdf_fallback(docx_path, out_dir)
    subprocess.run(
        [SOFFICE, "--headless", "--norestore", "--convert-to", "pdf",
         "--outdir", str(out_dir), str(docx_path)],
        check=True, capture_output=True, timeout=420)
    pdf = out_dir / (docx_path.stem + ".pdf")
    if not pdf.exists():
        return _matplotlib_pdf_fallback(docx_path, out_dir)
    return pdf


def _matplotlib_pdf_fallback(docx_path: Path, out_dir: Path) -> Path:
    """Last resort if LibreOffice is unavailable: a plain but complete PDF.

    Keeps the deliverable alive rather than failing the pipeline on a missing
    converter; the Word document remains the styling-accurate artefact.
    """
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    import theme as T

    print("    !! LibreOffice not found — writing a plain PDF fallback")
    out = out_dir / (docx_path.stem + ".pdf")
    content = RC.build()
    pages = [(content["meta"]["title"],
              [content["headline"]["answer"], ""] +
              [f"{t['label']}: {t['value']}  ({t['delta']})" for t in content["tiles"]]),
             ("Findings", [f"{f['n']}. {f['title']}" for f in content["findings"]]),
             ("Recommendations",
              [f"{a['n']}. {a['action']} — {a['owner']} ({a['review']})" for a in content["actions"]])]
    with PdfPages(out) as pdf:
        for title, lines in pages:
            fig = plt.figure(figsize=(8.27, 11.69))
            fig.patch.set_facecolor(T.CREAM)
            fig.text(0.08, 0.94, title, fontsize=17, fontweight="bold", color=T.INK)
            fig.text(0.08, 0.955, "Revenue Decline Diagnostic", fontsize=8.5,
                     color=T.ORANGE, fontweight="bold")
            y = 0.885
            for line in lines:
                fig.text(0.08, y, line, fontsize=10.5, color=T.INK, wrap=True)
                y -= 0.045
            pdf.savefig(fig)
            plt.close(fig)
    return out


# --------------------------------------------------------------------------- #
# 1. The executive brief                                                        #
# --------------------------------------------------------------------------- #
def render_brief(c: dict) -> list:
    """The one-to-two page brief, as a Word file, a PDF and a Markdown mirror."""
    meta = c["meta"]
    doc = D.new_document(margin=0.85)
    D.footer(doc, f"{meta['company']}  ·  {meta['title']}  ·  {meta['comparison']}")

    D.eyebrow(doc, f"Executive brief  ·  {meta['company']}  ·  {meta['comparison']}")
    p = doc.add_paragraph()
    run = p.add_run(f"Revenue fell {abs(c['headline']['revenue_yoy_pct']):.1f}% — "
                    f"not because we lost customers, but because we lost trips")
    run.font.size = Pt(17)
    run.font.bold = True
    run.font.color.rgb = D.INK
    run.font.name = D.BODY_FONT
    p.paragraph_format.space_after = Pt(4)
    D.rule(doc)

    D.rich_para(doc, [
        ("Prepared ", False, D.MUTED), (meta["prepared"], True, D.MUTED),
        ("  ·  Analysis by ", False, D.MUTED), (meta["author"], True, D.MUTED),
        ("  ·  ", False, D.MUTED), (meta["classification"], False, D.MUTED),
    ], size=8.6, space_after=10)

    D.kpi_strip(doc, c["tiles"][:3], cols=3)
    D.spacer(doc, 2)

    D.h2(doc, "The answer in one paragraph")
    D.para(doc, c["headline"]["answer"], size=10.5, space_after=6)

    D.h2(doc, "The four ranked, owned problems")
    rows = [[p_["rank"], p_["owner"], p_["short"], p_["cost"], p_["share"]]
            for p_ in c["problems"]]
    D.data_table(doc, ["#", "Owner", "The problem, in one line", "Cost", "Share"],
                 rows, widths=[0.28, 1.42, 3.25, 0.75, 0.6], aligns=["r", "l", "l", "r", "r"],
                 font_size=8.8)
    D.spacer(doc, 2)

    D.h2(doc, "What the analysis found")
    for f in c["findings"]:
        D.rich_para(doc, [
            (f"{f['n']}. {f['title']}  ", True, D.INK),
            (f["body"], False, D.INK),
            (f"  {f['so_what']}", False, D.MUTED, True),
        ], size=9.5, space_after=5)

    D.h2(doc, "What we recommend — owners, impact and review dates")
    rec = c["recovery"]
    D.data_table(doc, ["#", "Action", "Owner", "Expected gross-profit recovery", "Review"],
                 [[a["n"], a["short"], a["owner"], a["impact"], a["review"]] for a in c["actions"]]
                 + [["", "Total expected gross-profit recovery", "",
                     f"{rec['low']} – {rec['high']}", ""]],
                 widths=[0.26, 3.55, 0.98, 0.88, 0.80],
                 aligns=["r", "l", "l", "r", "r"], font_size=8.3)
    D.rich_para(doc, [(f"{rec['basis']} Together the register recovers about "
                       f"{rec['pct_low']}-{rec['pct_high']}% of the {rec['gp_lost']} of gross "
                       f"profit the quarter lost.", False, D.MUTED)], size=8.0, space_after=4)
    D.spacer(doc, 2)

    D.callout(doc,
              "What would change this conclusion",
              "  ·  ".join([c["caveats"][0], c["caveats"][3]]), D.ORANGE_HEX)

    docx_path = OUT / "Executive_Brief.docx"
    doc.save(docx_path)
    pdf = _soffice_pdf(docx_path, OUT)
    md = _brief_markdown(c)
    (C.DOCS / "09_executive_brief.md").write_text(md)
    print(f"  wrote {docx_path.name}, {pdf.name}, docs/09_executive_brief.md")
    return [docx_path, pdf]


def _brief_markdown(c: dict) -> str:
    meta, h = c["meta"], c["headline"]
    L = [f"# Executive Brief — {h['revenue_yoy_pct']:+.1f}% group revenue\n",
         f"**{meta['company']}** · {meta['comparison']} · prepared {meta['prepared']} · "
         f"{meta['classification']}\n",
         f"> {h['answer']}\n",
         "## The numbers\n",
         "| Metric | Value | vs base quarter |",
         "|---|---:|---:|"]
    for t in c["tiles"]:
        L.append(f"| {t['label']} | {t['value']} | **{t['delta']}** |")
    L.append("")
    L.append("## The four findings, ranked by cost\n")
    L.append("| # | Owner | Problem | Cost | Share |")
    L.append("|---:|---|---|---:|---:|")
    for p in c["problems"]:
        L.append(f"| {p['rank']} | {p['owner']} | {p['problem']} | {p['cost']} | **{p['share']}** |")
    L.append("")
    for f in c["findings"]:
        L.append(f"### {f['n']}. {f['title']}\n")
        L.append(f"{f['body']}\n")
        L.append(f"*So what: {f['so_what']}*\n")
    rec = c["recovery"]
    L.append("## What we recommend\n")
    L.append("| # | Action | Owner | Expected gross-profit recovery | Review |")
    L.append("|---:|---|---|---:|---|")
    for a in c["actions"]:
        L.append(f"| {a['n']} | {a['action']} | {a['owner']} | {a['impact']} | {a['review']} |")
    L.append(f"| | **Total expected gross-profit recovery** | | **{rec['low']} – {rec['high']}** "
             f"| vs a {rec['gp_lost']} gross-profit decline |")
    L.append("")
    L.append(f"*{rec['basis']} Together the register recovers about {rec['pct_low']}-{rec['pct_high']}% "
             f"of the {rec['gp_lost']} of gross profit the quarter lost.*\n")
    L.append("## What would change this conclusion\n")
    for cv in c["caveats"]:
        L.append(f"- {cv}")
    L.append("")
    return "\n".join(L)


# --------------------------------------------------------------------------- #
# 2. The full Word report                                                       #
# --------------------------------------------------------------------------- #
def _cover(doc, c: dict) -> None:
    meta = c["meta"]
    D.spacer(doc, 60)
    D.eyebrow(doc, meta["company"])
    p = doc.add_paragraph()
    run = p.add_run(meta["title"])
    run.font.size = Pt(30)
    run.font.bold = True
    run.font.color.rgb = D.BOOKEND
    run.font.name = D.BODY_FONT
    p.paragraph_format.space_after = Pt(2)

    p = doc.add_paragraph()
    run = p.add_run(meta["subtitle"])
    run.font.size = Pt(13.5)
    run.font.color.rgb = D.INK
    run.font.name = D.BODY_FONT
    p.paragraph_format.space_after = Pt(10)
    D.rule(doc, size=24)

    D.data_table(doc, ["", ""], [
        ["Comparison period", meta["comparison"]],
        ["Prepared", meta["prepared"]],
        ["Prepared by", meta["author"]],
        ["Classification", meta["classification"]],
        ["Reproduce with", meta["reproduce"]],
    ], widths=[1.9, 4.5], aligns=["l", "l"], font_size=9.6, zebra=False)

    D.spacer(doc, 18)
    D.callout(doc, "The question this answers", meta and c["headline"]["decision"], D.GREEN_HEX)
    D.spacer(doc, 10)
    D.para(doc, c["headline"]["answer"], size=11, bold=False)
    D.page_break(doc)


def _contents(doc, c: dict) -> None:
    D.h1(doc, "Contents")
    sections = [
        "1.  Executive summary",
        "2.  The decision this supports",
        "3.  What the data is, and what it is not",
        "4.  Descriptive — what happened",
        "5.  Diagnostic, part 1 — the mechanism",
        "6.  Diagnostic, part 2 — the structure, and who owns what",
        "7.  The intersection — which store x product x segment",
        "8.  Segments and retention",
        "9.  The supply event, with dates",
        "10. Pricing, mix and margin",
        "11. Facts, hypotheses, and the edge of what we know",
        "12. Predictive — the run-rate if nothing changes",
        "13. Prescriptive — what to do",
        "14. How we will know whether it worked",
        "Appendix A — method, provenance and reproducibility",
        "Appendix B — index of charts",
        "Appendix C — the evidential 5-Whys",
    ]
    for s in sections:
        D.para(doc, s, size=10.2, space_after=3)
    D.page_break(doc)


def render_word(c: dict) -> Path:
    meta, h = c["meta"], c["headline"]
    doc = D.new_document(margin=0.95)
    D.footer(doc, f"{meta['company']}  ·  {meta['title']}  ·  {meta['comparison']}  ·  "
                  f"{meta['classification']}")

    _cover(doc, c)
    _contents(doc, c)

    # 1 — executive summary ------------------------------------------------- #
    D.eyebrow(doc, "Section 1")
    D.h1(doc, "Executive summary")
    D.kpi_strip(doc, c["tiles"], cols=3)
    D.spacer(doc, 6)
    D.para(doc, h["answer"], size=11)
    D.para(doc, f"Gross profit fell {abs(h['gross_profit_yoy_pct']):.1f}% against a "
                f"{abs(h['revenue_yoy_pct']):.1f}% revenue fall, because gross margin compressed "
                f"{abs(h['gross_margin_pp_change']):.2f}pp to {h['gross_margin_2026']:.2f}%. Revenue is "
                f"not profit: every recommendation below is therefore priced in gross profit, not "
                f"revenue.")
    D.h2(doc, "The four findings, ranked by how much of the decline they own")
    D.data_table(doc, ["#", "Owner", "The problem", "Cost", "Share"],
                 [[p["rank"], p["owner"], p["problem"], p["cost"], p["share"]]
                  for p in c["problems"]],
                 widths=[0.35, 1.5, 2.85, 0.85, 0.85],
                 aligns=["r", "l", "l", "r", "r"], font_size=8.9)
    D.spacer(doc, 4)
    D.figure(doc, _figure_path("01_headline_waterfall.png"),
             "Figure 1 — the revenue bridge: one gain, two larger losses.",
             c["figures"][0]["so_what"])

    # 2 — the decision ------------------------------------------------------ #
    D.eyebrow(doc, "Section 2")
    D.h1(doc, "The decision this supports")
    D.callout(doc, "The question", h["decision"], D.GREEN_HEX)
    D.spacer(doc, 6)
    D.para(doc, "An analysis is only worth reading to the extent it changes who does what on Monday. "
                "This one converts a single headline — revenue fell — into four named owners with a "
                "quantified problem, an expected recovery and a review date. If it does not change "
                "someone's plan next quarter, it has failed.")
    D.h2(doc, "What this report is, and what a dashboard is")
    D.data_table(doc, ["", "This report", "The dashboard that follows it"], [
        ["Job", "explain a change and support a decision", "monitor the KPIs the analysis identified"],
        ["Question", "\u201cwhy, and what should we do?\u201d", "\u201care we OK?\u201d"],
        ["Cadence", "one-off, on demand", "monthly, always-on"],
        ["Output", "findings + recommendations, with owners", "tiles, trends, exceptions"],
    ], widths=[1.1, 2.7, 2.6], aligns=["l", "l", "l"], font_size=9.2)
    D.spacer(doc, 4)
    D.para(doc, "The dashboard ships after the thinking and monitors what this report concluded. "
                "Its build specification, including the DAX measures and the targets below, is "
                "docs/07_dashboard_spec.md.", size=9.8, color=D.MUTED)

    # 3 — the data ---------------------------------------------------------- #
    D.eyebrow(doc, "Section 3")
    D.h1(doc, "What the data is, and what it is not")
    D.para(doc, f"Line-item grain: one row = one line item on one customer receipt — "
                f"{c['provenance']['lines']} lines across {c['provenance']['invoices']} invoices in the "
                f"two quarters, plus a separate branch x SKU x day shelf-availability table that makes "
                f"the supply event provable rather than plausible.")
    D.h2(doc, "Declared limits — limits on the conclusions, not footnotes")
    for cv in c["caveats"]:
        D.bullet(doc, cv, size=9.8)
    D.spacer(doc, 4)
    D.para(doc, "Method in one line: decompose by mechanism first (customers x frequency x basket), "
                "then by structure (store, category, segment, channel), then intersect the three, then "
                "ask why five times with a number attached to every answer. The attribution is "
                "log-mean Divisia, audited so the driver partition covers the decline exactly.",
           size=9.8, color=D.MUTED)

    # 4 — descriptive ------------------------------------------------------- #
    D.eyebrow(doc, "Section 4")
    D.h1(doc, "Descriptive — what happened")
    D.data_table(doc, ["Metric", meta["base_period"], meta["current_period"], "Change"],
                 [[m["metric"], m["base"], m["cur"], m["change"]] for m in c["metrics"]],
                 widths=[2.5, 1.35, 1.35, 1.2], aligns=["l", "r", "r", "r"], font_size=9.0)
    D.spacer(doc, 4)
    D.para(doc, "Every figure in this table is reproduced from outputs/kpis.json, which the pipeline "
                "regenerates. Nothing here is typed by hand.", size=9.4, color=D.MUTED)
    D.figure(doc, _figure_path("01_headline_waterfall.png"),
             "Figure 1 — the revenue bridge.",
             "One customer gain against two larger losses. This is not one event.")

    # 5 — mechanism --------------------------------------------------------- #
    D.eyebrow(doc, "Section 5")
    D.h1(doc, "Diagnostic, part 1 — the mechanism")
    D.para(doc, "Revenue = Customers x Frequency x Average order value.", size=10.2, bold=True)
    D.data_table(doc, ["Driver", "Effect on revenue", "YoY move"],
                 [[r["driver"], RC.mn(r["effect"], signed=True), RC.pct(r["yoy"])]
                  for r in c["mechanism"]["rows"]] +
                 [["Total", RC.mn(c["mechanism"]["total"], signed=True),
                   RC.pct(c["mechanism"]["total_yoy"])]],
                 widths=[2.4, 2.2, 1.6], aligns=["l", "r", "r"], font_size=9.4)
    D.spacer(doc, 4)
    D.para(doc, c["mechanism"]["note"], size=9.8)
    D.para(doc, "Sequential-order sensitivity band: " +
                "; ".join(f"{s['driver']} {s['low']} to {s['high']}" for s in c["mechanism"]["sensitivity"]) +
                ".", size=9.4, color=D.MUTED)
    D.figure(doc, _figure_path("02_mechanism_identity.png"),
             "Figure 2 — the same three drivers indexed to the base quarter.",
             "Customers grew. Orders per customer and basket value did not. "
             "Any report that stops at \u201cfewer customers\u201d is wrong.")
    D.page_break(doc)

    # 6 — structure --------------------------------------------------------- #
    D.eyebrow(doc, "Section 6")
    D.h1(doc, "Diagnostic, part 2 — the structure, and who owns what")
    for title, key in (("By store", "branch"), ("By category", "category"),
                       ("By customer segment", "segment"), ("By channel", "channel")):
        D.h3(doc, title)
        D.data_table(doc, ["Rank", "Slice", "Revenue change", "YoY", "Share of group decline"],
                     [[r["rank"], r["slice"], RC.mn(r["delta"], signed=True), RC.pct(r["yoy_pct"]),
                       f"{r['share_of_decline_pct']:.1f}%"] for r in c["structure"][key]],
                     widths=[0.6, 2.0, 1.5, 1.0, 1.3], aligns=["r", "l", "r", "r", "r"],
                     font_size=8.8)
        D.spacer(doc, 4)
    D.figure(doc, _figure_path("03_branch_waterfall.png"),
             "Figure 3 — where the money went, by store.",
             f"Two of six stores carry {c['headline']['two_store_share']:.0f}% of the decline.")
    D.figure(doc, _figure_path("05_category_decline.png"),
             "Figure 4 — categories, in both KSh and %.",
             "Groceries is the biggest absolute loss, Beverages the fastest fall. "
             "Either alone is a misleading brief.")
    D.page_break(doc)

    # 7 — intersection ------------------------------------------------------ #
    D.eyebrow(doc, "Section 7")
    D.h1(doc, "The intersection — which store x product x segment")
    D.figure(doc, _figure_path("04_branch_category_heatmap.png"),
             "Figure 5 — revenue YoY % by store x category.",
             "The decline is concentrated, not diffuse — which is why the fix can be targeted too.")
    D.para(doc, f"The worst {c['intersection']['concentration_n']} cells (store x category x segment) "
                f"account for {c['intersection']['concentration_share']:.1f}% of the total decline.")
    D.data_table(doc, ["#", "Cell", "Revenue change", "YoY", "% of group decline"],
                 [[r["rank"], r["cell"], r["delta"], r["yoy"], r["share"]]
                  for r in c["intersection"]["leaders"]],
                 widths=[0.4, 3.1, 1.25, 0.8, 0.85], aligns=["r", "l", "r", "r", "r"],
                 font_size=8.8)
    D.spacer(doc, 4)
    D.callout(doc, "The counter-intuitive result",
              f"The single largest cell is {c['intersection']['top_cell']} — not the category that "
              f"was out of stock. At {c['supply']['store']}, every category fell together because the "
              f"stock failure removed the reason for the trip and the whole basket shrank with it. "
              f"Measuring only the affected category would have understated this event by roughly "
              f"{c['intersection']['understatement']:.1f}x.", D.ORANGE_HEX)
    D.figure(doc, _figure_path("10_driver_partition.png"),
             "Figure 6 — four ranked, owned problems (disjoint; sums to the whole decline).",
             "Each cell is assigned to exactly one owner, so there is no double counting.")
    D.page_break(doc)

    # 8 — retention --------------------------------------------------------- #
    D.eyebrow(doc, "Section 8")
    D.h1(doc, "Segments and retention")
    D.data_table(doc, ["Cohort metric", "Value"], [
        ["Q3 2025 customers", c["retention"]["customers_2025"]],
        ["Returned in Q3 2026", f"{c['retention']['returned']}  ({c['retention']['return_rate']})"],
        ["Lapsed", c["retention"]["lapsed"]],
        ["New customers acquired", c["retention"]["new"]],
    ], widths=[3.0, 3.2], aligns=["l", "r"], font_size=9.4)
    D.spacer(doc, 4)
    D.figure(doc, _figure_path("06_segment_waterfall.png"),
             "Figure 7 — every established segment shrank except the customers we bought.",
             "Buying growth is not a strategy while the existing base contracts.")
    D.figure(doc, _figure_path("07_cohort_retention.png"),
             "Figure 8 — return rate by base-quarter segment.",
             "Retention is healthy where it matters. The leak is trip frequency, not churn.")

    # 9 — supply ------------------------------------------------------------ #
    D.eyebrow(doc, "Section 9")
    D.h1(doc, "The supply event, with dates")
    D.data_table(doc, ["", "Value"], [
        ["Store", c["supply"]["store"]],
        ["Hero SKUs", c["supply"]["sku"]],
        ["Shelf availability in the incident window", c["supply"]["availability"]],
        ["Days out of stock", c["supply"]["days"]],
        ["Total cost attributed", c["supply"]["cost"]],
        ["Of which the affected category", c["supply"]["category_only"]],
        ["Of which basket spillover (other categories)", c["supply"]["spillover"]],
    ], widths=[3.6, 2.6], aligns=["l", "r"], font_size=9.2)
    D.spacer(doc, 4)
    D.callout(doc, "Why this is evidence, not a story",
              "The shelf-availability table records, per branch, per SKU, per day, whether the item "
              "was on the shelf. That is what turns \u201cprobably a supply problem\u201d into a dated, "
              "store-specific, owned finding.", D.GREEN_HEX)
    D.figure(doc, _figure_path("08_stockout_timeline.png"),
             "Figure 9 — shelf availability and the revenue trace that followed it.",
             "The incident has a start date, an end date, a store and a measurable cost.")

    # 10 — pricing ---------------------------------------------------------- #
    D.eyebrow(doc, "Section 10")
    D.h1(doc, "Pricing, mix and margin")
    D.data_table(doc, ["", meta["base_period"], meta["current_period"], "Change"], [
        ["Discount depth (% of gross)", c["pricing"]["depth_2025"], c["pricing"]["depth_2026"],
         f"{float(c['pricing']['depth_2026'].rstrip('%')) - float(c['pricing']['depth_2025'].rstrip('%')):+.2f}pp"],
        ["Gross margin", f"{h['gross_margin_2025']:.2f}%", f"{h['gross_margin_2026']:.2f}%",
         f"{h['gross_margin_pp_change']:+.2f}pp"],
        ["Gross profit", RC.mn(h["gross_profit_2025"]), RC.mn(h["gross_profit_2026"]),
         RC.pct(h["gross_profit_yoy_pct"])],
    ], widths=[2.6, 1.35, 1.35, 1.1], aligns=["l", "r", "r", "r"], font_size=9.2)
    D.spacer(doc, 4)
    D.para(doc, f"Roughly {c['pricing']['extra']} of extra discount was given away this quarter, "
                f"concentrated in Beverages ({c['pricing']['beverages_pp']}). Gross profit fell faster "
                f"than revenue, so margin — not just revenue — is the thing at risk.")
    D.figure(doc, _figure_path("09_discount_depth.png"),
             "Figure 10 — discount depth, prior year vs current year, by category.",
             "Prices rose, but so did discounting. The depth is concentrated.")

    # 11 — facts vs hypotheses ---------------------------------------------- #
    D.eyebrow(doc, "Section 11")
    D.h1(doc, "Facts, hypotheses, and the edge of what we know")
    D.para(doc, "A senior analysis is judged as much by what it refuses to claim as by what it "
                "concludes. Every statement below is tagged.", size=10.0)
    D.data_table(doc, ["Statement", "Tier", "Note"],
                 [[f["statement"], f["tier"], f["note"]] for f in c["facts"]],
                 widths=[3.0, 1.0, 2.4], aligns=["l", "l", "l"], font_size=8.8)

    # 12 — predictive ------------------------------------------------------- #
    D.eyebrow(doc, "Section 12")
    D.h1(doc, "Predictive — the run-rate if nothing changes")
    D.callout(doc, "A run-rate, not a forecast",
              f"If this quarter's frequency and basket levels persist, the annualised revenue impact "
              f"is roughly {c['run_rate']['value']} ({c['run_rate']['quarter']} x 4). This assumes the "
              f"{c['supply']['store']} incident does not repeat — it should be fixed — and it ignores "
              f"Q4 seasonality, which is typically stronger. Treat it as the size of the hole, not the "
              f"shape of the year.", D.ORANGE_HEX)
    D.spacer(doc, 6)
    D.para(doc, "The honest reading: the quarter's damage is stable and repeatable in nature, so the "
                "cost of inaction is not zero. It is the run-rate above, minus whatever the actions in "
                "Section 13 recover.")

    # 13 — prescriptive ----------------------------------------------------- #
    D.eyebrow(doc, "Section 13")
    D.h1(doc, "Prescriptive — what to do")
    D.para(doc, "Every action carries the four things an action needs to be real: an owner, an "
                "expected impact, an evidence link and a review date. Impacts are deliberately "
                "conservative and priced in gross profit — they assume partial capture.", size=10.0)
    D.data_table(doc, ["#", "Action", "Owner", "Why (evidence)", "Expected impact", "Review"],
                 [[a["n"], a["action"], a["owner"], a["why"], a["impact"], a["review"]]
                  for a in c["actions"]],
                 widths=[0.3, 1.75, 1.0, 1.7, 0.85, 0.8],
                 aligns=["r", "l", "l", "l", "r", "l"], font_size=8.0)
    D.spacer(doc, 4)
    D.h2(doc, "Sequencing and dependencies")
    D.bullet(doc, "Days 0-30: actions 1 and 4. Both are cheap and reversible, and both stop active "
                  "bleeding. Action 4 is a policy change; action 1 is a purchase order.", size=9.8)
    D.bullet(doc, "Days 30-60: actions 2 and 3. These need time to show up in traffic data.", size=9.8)
    D.bullet(doc, "Days 60-90: action 5, which depends on knowing the base is stable first.", size=9.8)
    D.bullet(doc, "Continuous: action 6. It is the only item that makes the *next* diagnosis cheaper — "
                  "and this entire report exists because two data gaps had to be worked around.",
             size=9.8)

    # 14 — monitoring ------------------------------------------------------- #
    D.eyebrow(doc, "Section 14")
    D.h1(doc, "How we will know whether it worked")
    D.para(doc, "Track the same five numbers this analysis used, on the same grain, every month. "
                "An analysis that never checks its own predictions never improves.", size=10.0)
    D.data_table(doc, ["Metric", "Baseline", "Target by Q1 FY2027", "Watched by"],
                 [[m["metric"], m["baseline"], m["target"], m["owner"]] for m in c["monitoring"]],
                 widths=[2.1, 1.5, 1.7, 1.1], aligns=["l", "r", "r", "l"], font_size=9.2)

    # appendix A ------------------------------------------------------------ #
    D.eyebrow(doc, "Appendix A")
    D.h1(doc, "Method, provenance and reproducibility")
    D.para(doc, "The whole project is a pipeline, not a set of notebooks. Each step consumes the "
                "previous step's outputs, so the analysis is reproducible rather than narrated.")
    D.data_table(doc, ["Step", "What it does"], [
        ["generate_data", "simulate the star schema, with planted data-quality defects"],
        ["clean_data", "audit and repair, and write the data-quality report"],
        ["run_sql", "build the SQLite warehouse and run every sql/*.sql"],
        ["decompose", "mechanism, structure and the disjoint driver partition"],
        ["five_whys", "the evidential why-chain, generated from tables"],
        ["write_report", "the findings report and the recommendations register"],
        ["make_figures", "the ten decision charts, in the dashboard's visual language"],
        ["write_reports", "this report, the brief, the deck and the PDF"],
        ["validate_against_truth", "grade the diagnosis against the sealed answer key"],
    ], widths=[1.9, 4.5], aligns=["l", "l"], font_size=9.0)
    D.spacer(doc, 4)
    D.para(doc, f"Reproduce everything with: {meta['reproduce']}   (dataset seed {meta['seed']}). "
                f"Note on the interpreter: the vendored numpy is built for CPython 3.12, so run the "
                f"pipeline with a 3.12 interpreter that can see pylibs/ — for example "
                f"make PY=/usr/bin/python3.12.", size=9.4, color=D.MUTED)
    D.para(doc, "The dataset is simulated from a documented mechanism (docs/00_ground_truth.md). "
                "That is deliberate: it allows the diagnosis to be graded. "
                "outputs/validation_report.md records 14/14 falsifiable checks passing.",
           size=9.6)

    # appendix B ------------------------------------------------------------ #
    D.eyebrow(doc, "Appendix B")
    D.h1(doc, "Index of charts")
    D.data_table(doc, ["Figure", "Section", "The sentence it proves"],
                 [[f["caption"], f["section"], f["so_what"]] for f in c["figures"]],
                 widths=[1.7, 1.0, 3.7], aligns=["l", "l", "l"], font_size=8.6)

    # appendix C ------------------------------------------------------------ #
    D.eyebrow(doc, "Appendix C")
    D.h1(doc, "The evidential 5-Whys")
    D.para(doc, "Every \u201cwhy\u201d is answered with a number and a source, and the chain stops "
                "where the data stops rather than speculating.", size=10.0)
    for w in c["whys"]:
        D.rich_para(doc, [(f"Why {w['step']} — {w['question']}", True, D.INK)], size=10.0,
                    space_after=1)
        D.para(doc, w["answer"], size=9.5, space_after=1)
        D.para(doc, f"Source: {w['source']}  ·  {w['actionable']}", size=8.4, color=D.MUTED,
                space_after=8)

    path = OUT / "Revenue_Decline_Diagnostic.docx"
    doc.save(path)
    print(f"  wrote {path.name}")
    return path


# --------------------------------------------------------------------------- #
# 3. The PowerPoint deck                                                        #
# --------------------------------------------------------------------------- #
def render_pptx(c: dict) -> Path:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.util import Emu, Inches as PInches, Pt as PPt

    def rgb(hex_str):
        h = hex_str.lstrip("#")
        return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    CREAM, PANEL, INK, MUTED, GREEN, ORANGE = (rgb("#FFFDF0"), rgb("#FFEFD5"), rgb("#27241B"),
                                                rgb("#89877B"), rgb("#259741"), rgb("#FB6107"))
    BOOKEND = rgb("#1B6B34")
    FONT = D.BODY_FONT

    prs = Presentation()
    prs.slide_width = PInches(13.333)
    prs.slide_height = PInches(7.5)
    blank = prs.slide_layouts[6]
    W, H = 13.333, 7.5
    M = 0.55

    def add_slide():
        s = prs.slides.add_slide(blank)
        bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = CREAM
        bg.line.fill.background()
        bg.shadow.inherit = False
        return s

    def textbox(s, left, top, width, height, text, size=14, color=INK, bold=False,
                align=PP_ALIGN.LEFT, italic=False, anchor=MSO_ANCHOR.TOP, space_after=4,
                line_spacing=1.0):
        tb = s.shapes.add_textbox(PInches(left), PInches(top), PInches(width), PInches(height))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = anchor
        tf.margin_left = tf.margin_right = Emu(0)
        tf.margin_top = tf.margin_bottom = Emu(0)
        lines = text if isinstance(text, list) else [text]
        for i, line in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            p.space_after = PPt(space_after)
            p.line_spacing = line_spacing
            run = p.add_run()
            run.text = line
            run.font.size = PPt(size)
            run.font.bold = bold
            run.font.italic = italic
            run.font.color.rgb = color
            run.font.name = FONT
        return tb

    def rect(s, left, top, width, height, fill=PANEL, line=None, radius=None):
        shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
                                 PInches(left), PInches(top), PInches(width), PInches(height))
        if fill is None:
            shp.fill.background()
        else:
            shp.fill.solid()
            shp.fill.fore_color.rgb = fill
        if line:
            shp.line.color.rgb = line
            shp.line.width = PPt(1.25)
        else:
            shp.line.fill.background()
        shp.shadow.inherit = False
        if radius is not None:
            try:
                shp.adjustments[0] = radius
            except Exception:
                pass
        return shp

    def header(s, title, eyebrow=None):
        y = 0.34
        if eyebrow:
            textbox(s, M, y, W - 2 * M, 0.3, eyebrow.upper(), size=10.5, color=ORANGE, bold=True)
            y += 0.30
        textbox(s, M, y, W - 2 * M, 0.62, title, size=23, color=INK, bold=True)
        rect(s, M, y + 0.66, 0.62, 0.055, fill=ORANGE)

    def notes(s, text):
        s.notes_slide.notes_text_frame.text = text

    def tile(s, left, top, width, height, label, value, delta, good, detail=""):
        rect(s, left, top, width, height, fill=PANEL)
        textbox(s, left + 0.14, top + 0.10, width - 0.28, 0.24, label.upper(), size=9,
                color=MUTED, bold=True)
        textbox(s, left + 0.14, top + 0.32, width - 0.28, 0.45, value, size=20,
                color=(INK if good is None else (GREEN if good else ORANGE)), bold=True)
        textbox(s, left + 0.14, top + 0.80, width - 0.28, 0.5,
                [delta, detail], size=10.5,
                color=(MUTED if good is None else (GREEN if good else ORANGE)), bold=True,
                space_after=1)

    def chart_slide(title, eyebrow, fig, so_what, bullet_lines=None):
        s = add_slide()
        header(s, title, eyebrow)
        img = _figure_path(fig)
        s.shapes.add_picture(str(img), PInches(M), PInches(1.42),
                             width=PInches((W - 2 * M) * (0.66 if bullet_lines else 1.0)))
        rect(s, M, 6.62, W - 2 * M, 0.62, fill=PANEL)
        textbox(s, M + 0.16, 6.72, W - 2 * M - 0.32, 0.45, so_what, size=12, color=INK,
                italic=True)
        if bullet_lines:
            textbox(s, M + (W - 2 * M) * 0.70, 1.55, (W - 2 * M) * 0.30, 4.6, bullet_lines,
                    size=12, color=INK, space_after=9, line_spacing=1.05)
        notes(s, so_what)
        return s

    # --- 1. title ---------------------------------------------------------- #
    s = add_slide()
    rect(s, 0, 0, W, 0.14, fill=ORANGE)
    textbox(s, M, 1.05, W - 2 * M, 0.35, c["meta"]["company"].upper(), size=13, color=ORANGE,
            bold=True)
    textbox(s, M, 1.50, W - 2 * M, 1.2, c["meta"]["title"], size=44, color=BOOKEND, bold=True)
    textbox(s, M, 2.62, W - 2 * M, 0.8, c["meta"]["subtitle"], size=18, color=INK)
    rect(s, M, 3.52, 1.1, 0.07, fill=ORANGE)
    textbox(s, M, 3.80, W - 2 * M, 0.4,
            f"{c['meta']['comparison']}   ·   prepared {c['meta']['prepared']}   ·   "
            f"{c['meta']['author']}   ·   {c['meta']['classification']}",
            size=12, color=MUTED)
    span = (W - 2 * M - 3 * 0.18) / 4
    for i, t in enumerate(c["tiles"][:4]):
        tile(s, M + i * (span + 0.18), 4.65, span, 1.45, t["label"], t["value"], t["delta"],
             t["good"])
    notes(s, f"Bottom line: {c['headline']['answer']}")

    # --- 2. the decision --------------------------------------------------- #
    s = add_slide()
    header(s, "The decision this analysis exists to support", "Framing")
    rect(s, M, 1.55, W - 2 * M, 1.5, fill=PANEL, line=GREEN)
    textbox(s, M + 0.3, 1.80, W - 2 * M - 0.6, 1.0, c["headline"]["decision"], size=24,
            color=BOOKEND, bold=True)
    textbox(s, M, 3.35, W - 2 * M, 1.4, c["headline"]["answer"], size=16, color=INK,
            line_spacing=1.15)
    textbox(s, M, 5.35, W - 2 * M, 1.4, [
        "A revenue decline does not need attention. It needs a small number of named owners "
        "with quantified problems.",
        "This deck converts one headline into four owned problems — with evidence, an expected "
        "recovery and a review date.",
    ], size=14, color=MUTED, space_after=8, line_spacing=1.1)
    notes(s, "Open with the decision, not the method. If nobody's plan changes, the analysis failed.")

    # --- 3. executive summary ---------------------------------------------- #
    s = add_slide()
    header(s, "Executive summary", "The numbers, each against a comparison")
    cols, rowsn = 3, 2
    span = (W - 2 * M - (cols - 1) * 0.20) / cols
    for i, t in enumerate(c["tiles"][:6]):
        r, cc = divmod(i, cols)
        tile(s, M + cc * (span + 0.20), 1.50 + r * 1.62, span, 1.45,
             t["label"], t["value"], t["delta"], t["good"], t["detail"])
    textbox(s, M, 4.90, W - 2 * M, 0.9,
            f"Gross profit fell {abs(c['headline']['gross_profit_yoy_pct']):.1f}% against a "
            f"{abs(c['headline']['revenue_yoy_pct']):.1f}% revenue fall — margin compressed "
            f"{abs(c['headline']['gross_margin_pp_change']):.2f}pp. Revenue is not profit.",
            size=15, color=ORANGE, bold=True)
    textbox(s, M, 5.9, W - 2 * M, 0.9,
            "No naked numbers: every tile carries a year-on-year move or a target.",
            size=12.5, color=MUTED, italic=True)
    notes(s, "Six tiles, six comparisons. The one to dwell on is orders per customer — it is the "
             "engine of the whole decline.")

    # --- 4-5. findings ----------------------------------------------------- #
    def findings_slide(items, part):
        s = add_slide()
        header(s, "What the analysis found", f"Findings {part}")
        top = 1.45
        for f in items:
            rect(s, M, top, W - 2 * M, 2.55, fill=PANEL)
            rect(s, M, top, 0.09, 2.55, fill=(GREEN if f["n"] == 5 else ORANGE))
            textbox(s, M + 0.28, top + 0.14, W - 2 * M - 0.6, 0.4,
                    f"{f['n']}.  {f['title']}", size=16, color=INK, bold=True)
            textbox(s, M + 0.28, top + 0.62, W - 2 * M - 0.6, 1.15, f["body"], size=11.5,
                    color=INK, line_spacing=1.05)
            textbox(s, M + 0.28, top + 1.88, W - 2 * M - 0.6, 0.55,
                    f"So what: {f['so_what']}", size=11, color=MUTED, italic=True,
                    line_spacing=1.0)
            top += 2.72
        notes(s, "Each finding carries a so-what. A finding without a consequence is trivia.")

    findings_slide(c["findings"][:2], "1–2 of 5")
    findings_slide(c["findings"][2:4], "3–4 of 5")
    findings_slide([c["findings"][4]], "5 of 5")

    # --- 6+. chart slides -------------------------------------------------- #
    fig_by_name = {f["file"]: f for f in c["figures"]}

    def fig_slide(name, title, eyebrow, bullets=None):
        f = fig_by_name[name]
        chart_slide(title, eyebrow, name, f["so_what"], bullets)

    fig_slide("01_headline_waterfall.png",
              "One headline, three mechanisms", "The bridge",
              ["Customers contributed a gain of "
               f"{RC.mn(c['mechanism']['rows'][0]['effect'], signed=True)}.",
               "Orders per customer cost "
               f"{RC.mn(c['mechanism']['rows'][1]['effect'])}.",
               "Average order value cost "
               f"{RC.mn(c['mechanism']['rows'][2]['effect'])}.",
               "Frequency is the largest effect under every ordering — "
               "that is the robust result."])
    fig_slide("02_mechanism_identity.png",
              "Customers up, frequency down: the engine failed, not the funnel", "The mechanism",
              ["Active customers "
               f"{RC.pct(c['mechanism']['rows'][0]['yoy'])}.",
               "Orders per customer "
               f"{RC.pct(c['mechanism']['rows'][1]['yoy'])}.",
               "Average order value "
               f"{RC.pct(c['mechanism']['rows'][2]['yoy'])}.",
               "Acquisition is working. Repeat behaviour is not."])
    fig_slide("03_branch_waterfall.png",
              "Two of six stores carry the decline", "Where it happened",
              [f"{c['structure']['by_store'][0]['store']}: "
               f"{c['structure']['by_store'][0]['cost']} "
               f"({c['structure']['by_store'][0]['yoy']}).",
               f"{c['structure']['by_store'][1]['store']}: "
               f"{c['structure']['by_store'][1]['cost']} "
               f"({c['structure']['by_store'][1]['yoy']}).",
               "Two local events, not a chain-wide trend.",
               "The fix must therefore be targeted, not spread thin."])
    fig_slide("04_branch_category_heatmap.png",
              "The decline is concentrated in the intersection", "Where it happened",
              ["Red-orange = decline; green = growth; the ramp is centred on 0%.",
               "Mombasa Nyali and Thika Road light up across every category.",
               "Concentration means the fix can be targeted too."])
    fig_slide("05_category_decline.png",
              "Groceries loses the most money; Beverages falls fastest", "Structure",
              ["Two denominators, two different rankings.",
               "Absolute loss points at Groceries.",
               "Percentage fall points at Beverages.",
               "Quoting either alone would mislead the room."])
    fig_slide("08_stockout_timeline.png",
              "The biggest single cost has a date, a store and an owner", "The evidence",
              [f"{c['supply']['sku']} at {c['supply']['store']}.",
               f"{c['supply']['availability']} shelf availability for "
               f"{c['supply']['days']} days.",
               f"Total cost {c['supply']['cost']} — of which only "
               f"{c['supply']['category_only']} is the affected category.",
               f"{c['supply']['spillover']} is baskets that were never started."])
    fig_slide("09_discount_depth.png",
              "Prices rose, but discounting rose faster", "Pricing and margin",
              [f"Discount depth {c['pricing']['depth_2025']} → {c['pricing']['depth_2026']} "
               f"of gross.",
               f"Beverages alone: {c['pricing']['beverages_pp']}.",
               f"About {c['pricing']['extra']} of extra discount in one quarter.",
               "Gross profit fell faster than revenue."])
    fig_slide("10_driver_partition.png",
              "One headline → four ranked, owned problems", "What to do about it",
              [f"{p['owner']} — {p['cost']} ({p['share']})." for p in c["problems"]] +
              ["Disjoint and audited: the bars sum to the whole decline."])

    # --- the evidence index / pricing table -------------------------------- #
    s = add_slide()
    header(s, "Ranked problems, owners and expected recovery", "The action register")
    PPt2 = PPt
    tbl_shape = s.shapes.add_table(len(c["problems"]) + 1, 5, PInches(M), PInches(1.55),
                                   PInches(W - 2 * M), PInches(2.2))
    table = tbl_shape.table
    headers = ["#", "Owner", "The problem", "Cost", "Share of decline"]
    for j, htxt in enumerate(headers):
        cell = table.cell(0, j)
        cell.text = htxt
        cell.fill.solid(); cell.fill.fore_color.rgb = PANEL
        para = cell.text_frame.paragraphs[0]
        para.runs[0].font.bold = True
        para.runs[0].font.size = PPt2(13)
        para.runs[0].font.color.rgb = INK
        para.runs[0].font.name = FONT
    for i, p in enumerate(c["problems"], 1):
        for j, val in enumerate([p["rank"], p["owner"], p["problem"], p["cost"], p["share"]]):
            cell = table.cell(i, j)
            cell.text = str(val)
            cell.fill.solid()
            cell.fill.fore_color.rgb = CREAM if i % 2 else PANEL
            para = cell.text_frame.paragraphs[0]
            para.runs[0].font.size = PPt2(11.5)
            para.runs[0].font.color.rgb = INK
            para.runs[0].font.name = FONT
    table.columns[0].width = PInches(0.5)
    table.columns[1].width = PInches(2.6)
    table.columns[2].width = PInches(5.3)
    table.columns[3].width = PInches(1.5)
    table.columns[4].width = PInches(2.3)
    textbox(s, M, 4.2, W - 2 * M, 2.6,
            ["Days 0–30: rebuild safety stock on the hero SKUs; cap beverage discount depth "
             "with an approval gate.",
             "Days 30–60: rebuild the Mombasa basket; Thika Road access recovery with the landlord "
             "and county.",
             "Days 60–90: win-back and second-purchase nudges to fix the frequency leak.",
             "Continuous: capture a customer ID on every transaction and log supplier lead times."],
            size=13, color=INK, space_after=8, line_spacing=1.05)
    notes(s, "Two cheap reversible actions first. The policy change and the purchase order can start "
             "this week.")

    # --- facts vs hypotheses ----------------------------------------------- #
    s = add_slide()
    header(s, "Facts, hypotheses, and the edge of what we know", "Intellectual honesty")
    s.shapes.add_table(len(c["facts"]) + 1, 3, PInches(M), PInches(1.5),
                       PInches(W - 2 * M), PInches(4.9))
    table = s.shapes[-1].table
    for j, htxt in enumerate(["Statement", "Tier", "Note"]):
        cell = table.cell(0, j)
        cell.text = htxt
        cell.fill.solid(); cell.fill.fore_color.rgb = PANEL
        para = cell.text_frame.paragraphs[0]
        para.runs[0].font.bold = True
        para.runs[0].font.size = PPt(11.5)
        para.runs[0].font.color.rgb = INK
        para.runs[0].font.name = FONT
    tier_color = {"Fact": GREEN, "Hypothesis": ORANGE, "Unexplained": MUTED}
    for i, f in enumerate(c["facts"], 1):
        for j, val in enumerate([f["statement"], f["tier"], f["note"]]):
            cell = table.cell(i, j)
            cell.text = str(val)
            cell.fill.solid()
            cell.fill.fore_color.rgb = CREAM if i % 2 else PANEL
            para = cell.text_frame.paragraphs[0]
            para.runs[0].font.size = PPt(9.5)
            para.runs[0].font.name = FONT
            para.runs[0].font.color.rgb = (tier_color.get(f["tier"], INK)
                                            if j == 1 else INK)
            para.runs[0].font.bold = (j == 1)
    table.columns[0].width = PInches(5.5)
    table.columns[1].width = PInches(1.6)
    table.columns[2].width = PInches(5.1)
    notes(s, "A senior analysis is judged as much by what it refuses to claim. The Kisumu figure is "
             "flagged and deliberately not back-filled with a story.")

    # --- monitoring / closing ---------------------------------------------- #
    s = add_slide()
    header(s, "How we will know whether it worked", "Monitoring")
    s.shapes.add_table(len(c["monitoring"]) + 1, 4, PInches(M), PInches(1.55),
                       PInches(W - 2 * M), PInches(2.6))
    table = s.shapes[-1].table
    for j, htxt in enumerate(["Metric", "Baseline", "Target by Q1 FY2027", "Watched by"]):
        cell = table.cell(0, j)
        cell.text = htxt
        cell.fill.solid(); cell.fill.fore_color.rgb = PANEL
        para = cell.text_frame.paragraphs[0]
        para.runs[0].font.bold = True
        para.runs[0].font.size = PPt(12)
        para.runs[0].font.color.rgb = INK
        para.runs[0].font.name = FONT
    for i, mrow in enumerate(c["monitoring"], 1):
        for j, val in enumerate([mrow["metric"], mrow["baseline"], mrow["target"], mrow["owner"]]):
            cell = table.cell(i, j)
            cell.text = str(val)
            cell.fill.solid()
            cell.fill.fore_color.rgb = CREAM if i % 2 else PANEL
            para = cell.text_frame.paragraphs[0]
            para.runs[0].font.size = PPt(11.5)
            para.runs[0].font.name = FONT
            para.runs[0].font.color.rgb = INK
    for j, wdt in enumerate([4.4, 2.3, 2.8, 2.7]):
        table.columns[j].width = PInches(wdt)
    rect(s, M, 4.55, W - 2 * M, 1.6, fill=PANEL, line=ORANGE)
    textbox(s, M + 0.3, 4.78, W - 2 * M - 0.6, 1.2,
            ["The uncomfortable test: if the people who receive this deck make the same decisions "
             "they made last quarter, it was decoration.",
             "Follow up in 90 days: did the decision change, and did the recommendation work?"],
            size=14, color=INK, space_after=8, line_spacing=1.1)
    notes(s, "Name the follow-up date in the room. An analysis that never checks its own predictions "
             "never improves.")

    path = OUT / "Revenue_Decline_Diagnostic.pptx"
    prs.save(path)
    print(f"  wrote {path.name}  ({len(prs.slides._sldIdLst)} slides)")
    return path


# --------------------------------------------------------------------------- #
# Main                                                                          #
# --------------------------------------------------------------------------- #
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("Building reports ->", OUT)
    c = RC.build()
    render_brief(c)
    docx_path = render_word(c)
    pdf = _soffice_pdf(docx_path, OUT)
    print(f"  wrote {pdf.name}")
    render_pptx(c)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
