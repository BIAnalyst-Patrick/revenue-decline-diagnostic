"""python-docx helpers that dress the reports in the dashboard's language.

Kept deliberately dumb: each function does one formatting thing, so the renderers
in `write_reports.py` read like the report outline rather than like XML plumbing.

Palette is imported from `theme.py` so a colour can only be defined once.
"""

from __future__ import annotations

import sys
from pathlib import Path

import _bootstrap  # noqa: F401

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Emu, Inches, Pt, RGBColor

sys.path.append(str(Path(__file__).resolve().parent))
import theme as T  # noqa: E402


def _rgb(hex_str: str) -> RGBColor:
    h = hex_str.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


GREEN = _rgb(T.GREEN)
BOOKEND = _rgb(T.BOOKEND)
ORANGE = _rgb(T.ORANGE)
INK = _rgb(T.INK)
MUTED = _rgb(T.MUTED)
WHITE = _rgb("#FFFFFF")

CREAM_HEX = T.CREAM.lstrip("#")
PANEL_HEX = T.PANEL.lstrip("#")
GREEN_HEX = T.GREEN.lstrip("#")
ORANGE_HEX = T.ORANGE.lstrip("#")
GRID_HEX = T.GRID.lstrip("#")
INK_HEX = T.INK.lstrip("#")
MUTED_HEX = T.MUTED.lstrip("#")

BODY_FONT = T.FONT
MAX_W = 6.4          # usable width in inches (A4, 0.9in side margins)
FIG_W = 5.05         # chart width — full-bleed charts make the report long


# --------------------------------------------------------------------------- #
# Low-level XML helpers                                                        #
# --------------------------------------------------------------------------- #
def set_cell_bg(cell, hex_fill: str) -> None:
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill.lstrip("#"))
    cell._tc.get_or_add_tcPr().append(shd)


def set_cell_margins(cell, top=60, bottom=60, left=110, right=110) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    mar = OxmlElement("w:tcMar")
    for tag, val in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{tag}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tcPr.append(mar)


def set_table_borders(table, color: str = GRID_HEX, size: int = 4,
                      inside: bool = True, outside: bool = True) -> None:
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    edges = []
    if outside:
        edges += ["top", "left", "bottom", "right"]
    if inside:
        edges += ["insideH", "insideV"]
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        if edge in edges:
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), str(size))
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), color)
        else:
            el.set(qn("w:val"), "none")
            el.set(qn("w:sz"), "0")
            el.set(qn("w:color"), "auto")
        borders.append(el)
    tblPr.append(borders)


def set_repeat_header(row) -> None:
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def add_paragraph_border(paragraph, color: str = ORANGE_HEX, size: int = 18,
                         position: str = "bottom") -> None:
    pPr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    el = OxmlElement(f"w:{position}")
    el.set(qn("w:val"), "single")
    el.set(qn("w:sz"), str(size))
    el.set(qn("w:space"), "6")
    el.set(qn("w:color"), color)
    borders.append(el)
    pPr.append(borders)


def add_field(paragraph, instr: str) -> None:
    run = paragraph.add_run()
    fld = OxmlElement("w:fldChar")
    fld.set(qn("w:fldCharType"), "begin")
    run._r.append(fld)
    run2 = paragraph.add_run()
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = instr
    run2._r.append(it)
    run3 = paragraph.add_run()
    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "end")
    run3._r.append(fld2)


# --------------------------------------------------------------------------- #
# Document setup                                                               #
# --------------------------------------------------------------------------- #
def new_document(landscape: bool = False, margin: float = 1.0) -> Document:
    doc = Document()
    for section in doc.sections:
        if landscape:
            from docx.enum.section import WD_ORIENT
            section.orientation = WD_ORIENT.LANDSCAPE
            section.page_width, section.page_height = section.page_height, section.page_width
        section.top_margin = Inches(margin)
        section.bottom_margin = Inches(margin * 0.85)
        section.left_margin = Inches(margin * 0.9)
        section.right_margin = Inches(margin * 0.9)
    style_document(doc)
    return doc


def style_document(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = INK
    normal.paragraph_format.space_after = Pt(7)
    normal.paragraph_format.line_spacing = 1.16

    for name, size, color, before, after in [
        ("Heading 1", 17, BOOKEND, 20, 8),
        ("Heading 2", 13, INK, 14, 5),
        ("Heading 3", 11.5, ORANGE, 11, 4),
    ]:
        st = doc.styles[name]
        st.font.name = BODY_FONT
        st.font.size = Pt(size)
        st.font.color.rgb = color
        st.font.bold = True
        st.font.italic = False
        st.paragraph_format.space_before = Pt(before)
        st.paragraph_format.space_after = Pt(after)
        st.paragraph_format.keep_with_next = True
    try:
        doc.styles["Heading 1"].font.all_caps = False
    except Exception:
        pass


def set_page_background(doc: Document, hex_fill: str = CREAM_HEX) -> None:
    """Paint the page cream (a real Word feature; LibreOffice honours it for PDF)."""
    for section in doc.sections:
        sectPr = section._sectPr
        bg = OxmlElement("w:background")
        bg.set(qn("w:color"), hex_fill)
        doc.element.insert(0, bg)
        break


# --------------------------------------------------------------------------- #
# Content helpers                                                              #
# --------------------------------------------------------------------------- #
def para(doc, text: str, size: float = 10.5, color: RGBColor = INK, bold: bool = False,
         italic: bool = False, align=None, space_after: float = 7, font: str = BODY_FONT):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = font
    return p


def rich_para(doc, chunks, size: float = 10.5, align=None, space_after: float = 7):
    """A paragraph built from (text, bold, color) triples — for inline emphasis."""
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    for chunk in chunks:
        text = chunk[0]
        bold = chunk[1] if len(chunk) > 1 else False
        color = chunk[2] if len(chunk) > 2 else INK
        italic = chunk[3] if len(chunk) > 3 else False
        run = p.add_run(text)
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.italic = italic
        run.font.color.rgb = color
        run.font.name = BODY_FONT
    return p


def bullet(doc, text: str, size: float = 10.5, color: RGBColor = INK, bold_lead: str | None = None):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(4)
    if bold_lead:
        run = p.add_run(bold_lead)
        run.font.bold = True
        run.font.size = Pt(size)
        run.font.color.rgb = INK
        run.font.name = BODY_FONT
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.name = BODY_FONT
    return p


def eyebrow(doc, text: str):
    p = para(doc, text.upper(), size=8.6, color=ORANGE, bold=True, space_after=2)
    return p


def h1(doc, text: str):
    return doc.add_heading(text, level=1)


def h2(doc, text: str):
    return doc.add_heading(text, level=2)


def h3(doc, text: str):
    return doc.add_heading(text, level=3)


def rule(doc, color: str = ORANGE_HEX, size: int = 16):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.space_before = Pt(0)
    add_paragraph_border(p, color=color, size=size, position="bottom")
    return p


def spacer(doc, points: float = 8):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    for run in p.runs:
        run.font.size = Pt(points)
    p.add_run("").font.size = Pt(points)
    return p


# --------------------------------------------------------------------------- #
# Tables                                                                       #
# --------------------------------------------------------------------------- #
def data_table(doc, headers, rows, widths=None, aligns=None, header_fill=PANEL_HEX,
               zebra: bool = True, font_size: float = 9.6, header_color: RGBColor = INK):
    """A hairline table with a cream header band and optional zebra striping."""
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table, color=GRID_HEX, size=4)

    hdr = table.rows[0]
    for i, text in enumerate(headers):
        cell = hdr.cells[i]
        set_cell_bg(cell, header_fill)
        set_cell_margins(cell)
        cell.text = ""
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.space_before = Pt(2)
        run = p.add_run(str(text))
        run.font.bold = True
        run.font.size = Pt(font_size)
        run.font.color.rgb = header_color
        run.font.name = BODY_FONT
        if aligns and i < len(aligns) and aligns[i] == "r":
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    set_repeat_header(hdr)

    for r_i, row in enumerate(rows):
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cell = cells[i]
            set_cell_margins(cell)
            if zebra and r_i % 2 == 1:
                set_cell_bg(cell, CREAM_HEX)
            cell.text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.space_before = Pt(2)
            run = p.add_run(str(value))
            run.font.size = Pt(font_size)
            run.font.name = BODY_FONT
            run.font.color.rgb = INK
            if aligns and i < len(aligns) and aligns[i] == "r":
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    if widths:
        for row in table.rows:
            for i, w in enumerate(widths):
                if i < len(row.cells):
                    row.cells[i].width = Inches(w)
    return table


def _tile_cell(cell, tile):
    set_cell_bg(cell, CREAM_HEX)
    set_cell_margins(cell, top=110, bottom=110, left=130, right=130)
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(1)
    run = p.add_run(tile["label"].upper())
    run.font.size = Pt(7.8)
    run.font.bold = True
    run.font.color.rgb = MUTED
    run.font.name = BODY_FONT

    p2 = cell.add_paragraph()
    p2.paragraph_format.space_after = Pt(1)
    run = p2.add_run(tile["value"])
    run.font.size = Pt(15)
    run.font.bold = True
    run.font.name = BODY_FONT
    run.font.color.rgb = INK if tile.get("good") is None else (GREEN if tile["good"] else ORANGE)

    p3 = cell.add_paragraph()
    p3.paragraph_format.space_after = Pt(0)
    run = p3.add_run(tile["delta"])
    run.font.size = Pt(9.6)
    run.font.bold = True
    run.font.name = BODY_FONT
    run.font.color.rgb = MUTED if tile.get("good") is None else (GREEN if tile["good"] else ORANGE)
    run2 = p3.add_run(f"   {tile['detail']}")
    run2.font.size = Pt(8.0)
    run2.font.name = BODY_FONT
    run2.font.color.rgb = MUTED


def kpi_strip(doc, tiles, cols: int = 3):
    """A grid of KPI tiles — the Word equivalent of the dashboard's card row."""
    rows = (len(tiles) + cols - 1) // cols
    table = doc.add_table(rows=rows, cols=cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table, color=PANEL_HEX, size=8)
    for idx, tile in enumerate(tiles):
        r, c = divmod(idx, cols)
        _tile_cell(table.rows[r].cells[c], tile)
    for r in range(rows):
        for c in range(cols):
            table.rows[r].cells[c].width = Inches(MAX_W / cols)
    return table


def callout(doc, title: str, body: str, accent: str = GREEN_HEX):
    table = doc.add_table(rows=1, cols=1)
    table.autofit = False
    set_table_borders(table, color=accent, size=10)
    cell = table.rows[0].cells[0]
    set_cell_bg(cell, PANEL_HEX)
    set_cell_margins(cell, top=120, bottom=120, left=160, right=160)
    cell.width = Inches(MAX_W)
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(title)
    run.font.bold = True
    run.font.size = Pt(10.4)
    run.font.name = BODY_FONT
    run.font.color.rgb = _rgb("#" + accent)
    p2 = cell.add_paragraph()
    p2.paragraph_format.space_after = Pt(0)
    run = p2.add_run(body)
    run.font.size = Pt(9.8)
    run.font.name = BODY_FONT
    run.font.color.rgb = INK
    return table


# --------------------------------------------------------------------------- #
# Images and page furniture                                                    #
# --------------------------------------------------------------------------- #
def figure(doc, image_path, caption: str, so_what: str | None = None,
           width: float = FIG_W):
    doc.add_picture(str(image_path), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.paragraphs[-1].paragraph_format.space_after = Pt(3)
    if so_what:
        p = para(doc, so_what, size=9.4, color=INK, italic=True,
                 align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    if caption:
        para(doc, caption, size=8.4, color=MUTED,
             align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)


def footer(doc, left_text: str, show_page: bool = True) -> None:
    for section in doc.sections:
        f = section.footer
        p = f.paragraphs[0] if f.paragraphs else f.add_paragraph()
        p.text = ""
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = p.add_run(left_text)
        run.font.size = Pt(8.0)
        run.font.color.rgb = MUTED
        run.font.name = BODY_FONT
        if show_page:
            p.add_run("\t\t")
            run = p.add_run("Page ")
            run.font.size = Pt(8.0)
            run.font.color.rgb = MUTED
            run.font.name = BODY_FONT
            add_field(p, "PAGE")
            run = p.add_run(" of ")
            run.font.size = Pt(8.0)
            run.font.color.rgb = MUTED
            run.font.name = BODY_FONT
            add_field(p, "NUMPAGES")


def page_break(doc):
    from docx.enum.text import WD_BREAK
    p = doc.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)
    return p


def plain_paragraph(text: str, size: float = 10.5, color: RGBColor = INK,
                    bold: bool = False, align=None):
    """Build a paragraph without a document (used by the PPTX renderer for notes)."""
    return text
