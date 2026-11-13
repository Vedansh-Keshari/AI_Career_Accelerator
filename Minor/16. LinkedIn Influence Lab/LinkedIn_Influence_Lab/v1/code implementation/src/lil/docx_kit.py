"""python-docx helpers that give every report the same colourful, human-looking style."""
from __future__ import annotations

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


def rgb(hex_color: str) -> RGBColor:
    h = hex_color.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def shade(cell, hex_color: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear"); el.set(qn("w:color"), "auto"); el.set(qn("w:fill"), hex_color.lstrip("#"))
    tc_pr.append(el)


def new_doc() -> Document:
    doc = Document()
    for s in doc.sections:
        s.left_margin = s.right_margin = Inches(0.9)
        s.top_margin = s.bottom_margin = Inches(0.8)
    st = doc.styles["Normal"]
    st.font.name, st.font.size = "Calibri", Pt(11)
    return doc


def cover(doc, title: str, subtitle: str, meta: list[str], color: str = "#4C1D95", accent: str = "#EC4899") -> None:
    t = doc.add_table(rows=1, cols=1)
    cell = t.rows[0].cells[0]
    shade(cell, color)
    p = cell.paragraphs[0]
    r = p.add_run(title); r.font.size, r.bold, r.font.color.rgb = Pt(28), True, rgb("#FFFFFF")
    p2 = cell.add_paragraph()
    r2 = p2.add_run(subtitle); r2.font.size, r2.font.color.rgb = Pt(13), rgb("#FDE68A")
    for line in meta:
        pm = cell.add_paragraph(); rm = pm.add_run(line); rm.font.size, rm.font.color.rgb = Pt(10), rgb("#E9D5FF")
    bar = doc.add_table(rows=1, cols=1)
    shade(bar.rows[0].cells[0], accent)
    bar.rows[0].cells[0].paragraphs[0].add_run(" ").font.size = Pt(4)
    doc.add_paragraph()


def h(doc, text: str, level: int = 1, color: str = "#4C1D95") -> None:
    para = doc.add_heading(level=level)
    run = para.add_run(text)
    run.font.color.rgb = rgb(color)
    run.font.name = "Calibri"


def para(doc, text: str, bold: bool = False, italic: bool = False, color: str | None = None, size: int | None = None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold, r.italic = bold, italic
    if color:
        r.font.color.rgb = rgb(color)
    if size:
        r.font.size = Pt(size)
    return p


def bullets(doc, items) -> None:
    for it in items:
        doc.add_paragraph(str(it), style="List Bullet")


def table(doc, header: list[str], rows: list[list], color: str = "#7C3AED", zebra: str = "#F5F3FF", widths: list[float] | None = None):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    if widths:
        t.autofit = False
    for i, name in enumerate(header):
        c = t.rows[0].cells[i]
        shade(c, color)
        run = c.paragraphs[0].add_run(str(name))
        run.bold, run.font.color.rgb, run.font.size = True, rgb("#FFFFFF"), Pt(10)
    for n, row in enumerate(rows):
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].paragraphs[0].add_run("" if val is None else str(val)).font.size = Pt(9.5)
            if n % 2:
                shade(cells[i], zebra)
    if widths:
        for i, w in enumerate(widths):
            t.columns[i].width = Inches(w)
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Inches(w)
    doc.add_paragraph()
    return t


def callout(doc, text: str, color: str = "#FEF3C7", text_color: str = "#92400E") -> None:
    t = doc.add_table(rows=1, cols=1)
    c = t.rows[0].cells[0]
    shade(c, color)
    r = c.paragraphs[0].add_run(text)
    r.font.color.rgb, r.font.size = rgb(text_color), Pt(10)
    doc.add_paragraph()


def image(doc, path, width: float = 6.2) -> None:
    doc.add_picture(str(path), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
