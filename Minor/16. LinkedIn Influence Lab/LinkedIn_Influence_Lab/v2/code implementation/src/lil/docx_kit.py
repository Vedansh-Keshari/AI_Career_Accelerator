"""python-docx helpers: one consistent, restrained house style for every report
(cover with banner, document control, running header/footer with page numbers, clean tables)."""
from __future__ import annotations

from docx import Document
from docx.enum.section import WD_SECTION  # noqa: F401  (re-exported for callers)
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

INK, MUTED, LINE, BAND = "#1F2A44", "#64708A", "#D9DCE6", "#F5F4FB"
INDIGO, VIOLET, PINK, ORANGE, SKY, EMERALD = "#312E81", "#6D28D9", "#BE185D", "#C2410C", "#0369A1", "#047857"
TINT = {VIOLET: "#EFEAFB", PINK: "#FBE9F2", ORANGE: "#FDEEE3", SKY: "#E3F1F8", EMERALD: "#E2F3EC", INDIGO: "#E9E8F5"}
FONT = "Calibri"


def rgb(h: str) -> RGBColor:
    h = h.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def tint(color: str) -> str:
    return TINT.get(color, BAND)


# ------------------------------------------------------------------ low-level XML ---------
# OOXML wants child elements in a fixed order; Word can reject files that break it, so every insert honours it.
_AFTER = {
    "shd_tc": ("noWrap", "tcMar", "textDirection", "tcFitText", "vAlign", "hideMark"),
    "tcBorders": ("shd", "noWrap", "tcMar", "textDirection", "tcFitText", "vAlign", "hideMark"),
    "tblCellMar": ("tblLook", "tblCaption", "tblDescription"),
    "pBdr": ("shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap", "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi",
             "adjustRightInd", "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc", "textDirection",
             "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange"),
}


def _put(parent, el, key: str) -> None:
    for tag in _AFTER[key]:
        nxt = parent.find(qn(f"w:{tag}"))
        if nxt is not None:
            nxt.addprevious(el)
            return
    parent.append(el)


def shade(cell, hex_color: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    for old in tc_pr.findall(qn("w:shd")):
        tc_pr.remove(old)
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear"); el.set(qn("w:color"), "auto"); el.set(qn("w:fill"), hex_color.lstrip("#"))
    _put(tc_pr, el, "shd_tc")


def borders(cell, **edges) -> None:
    """edges: top/bottom/left/right = (size_eighths_pt, hex) or None for no border."""
    tc_pr = cell._tc.get_or_add_tcPr()
    el = tc_pr.find(qn("w:tcBorders"))
    if el is None:
        el = OxmlElement("w:tcBorders")
        _put(tc_pr, el, "tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        spec = edges.get(edge, "keep")
        if spec == "keep":
            continue
        for old in el.findall(qn(f"w:{edge}")):
            el.remove(old)
        b = OxmlElement(f"w:{edge}")
        if spec is None:
            b.set(qn("w:val"), "nil")
        else:
            b.set(qn("w:val"), "single"); b.set(qn("w:sz"), str(spec[0])); b.set(qn("w:space"), "0"); b.set(qn("w:color"), spec[1].lstrip("#"))
        el.append(b)  # children of tcBorders stay in top, left, bottom, right order only if added in that order:
    order = {t: i for i, t in enumerate(("top", "left", "bottom", "right"))}
    kids = sorted(list(el), key=lambda c: order[c.tag.split("}")[1]])
    for k in kids:
        el.remove(k)
    for k in kids:
        el.append(k)


def margins(table, top=60, bottom=60, left=100, right=100) -> None:
    pr = table._tbl.tblPr
    for old in pr.findall(qn("w:tblCellMar")):
        pr.remove(old)
    mar = OxmlElement("w:tblCellMar")
    for k, v in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        e = OxmlElement(f"w:{k}")
        e.set(qn("w:w"), str(v)); e.set(qn("w:type"), "dxa")
        mar.append(e)
    _put(pr, mar, "tblCellMar")


def _no_borders(table) -> None:
    for row in table.rows:
        for c in row.cells:
            borders(c, top=None, bottom=None, left=None, right=None)


def _field(run, code: str) -> None:
    for kind, text in (("begin", None), (None, code), ("separate", None), (None, "1"), ("end", None)):
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        elif text == code:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = f" {code} "
        else:
            el = OxmlElement("w:t")
            el.text = text
        run._r.append(el)


def _bottom_rule(paragraph, color=VIOLET, size=8) -> None:
    ppr = paragraph._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    b = OxmlElement("w:bottom")
    b.set(qn("w:val"), "single"); b.set(qn("w:sz"), str(size)); b.set(qn("w:space"), "4"); b.set(qn("w:color"), color.lstrip("#"))
    bdr.append(b)
    for old in ppr.findall(qn("w:pBdr")):
        ppr.remove(old)
    _put(ppr, bdr, "pBdr")


def _own_tabs(paragraph, width) -> None:
    """Header/Footer styles ship centre+right tab stops; clear them so our single right-aligned stop is the only one."""
    ts = paragraph.paragraph_format.tab_stops
    ts.add_tab_stop(Inches(3.25), WD_TAB_ALIGNMENT.CLEAR)
    ts.add_tab_stop(Inches(6.5), WD_TAB_ALIGNMENT.CLEAR)
    ts.add_tab_stop(width, WD_TAB_ALIGNMENT.RIGHT)


# ------------------------------------------------------------------ document ---------------
def new_doc(running_title: str, code: str = "LIL-2025-P1", note: str = "") -> Document:
    """A4 portrait, first page free of header/footer (the cover), running header/footer afterwards."""
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.1)
    sec.top_margin, sec.bottom_margin = Cm(2.3), Cm(2.0)
    sec.different_first_page_header_footer = True
    st = doc.styles["Normal"]
    st.font.name, st.font.size, st.font.color.rgb = FONT, Pt(10.5), rgb(INK)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    st.paragraph_format.space_after, st.paragraph_format.line_spacing = Pt(6), 1.12
    for name, size, color, before, after in (("Heading 1", 18, INDIGO, 20, 8), ("Heading 2", 13, VIOLET, 14, 4), ("Heading 3", 11, MUTED, 10, 3)):
        h = doc.styles[name]
        h.font.name, h.font.size, h.font.bold, h.font.color.rgb = FONT, Pt(size), True, rgb(color)
        h.element.rPr.rFonts.set(qn("w:ascii"), FONT); h.element.rPr.rFonts.set(qn("w:hAnsi"), FONT)
        h.paragraph_format.space_before, h.paragraph_format.space_after, h.paragraph_format.keep_with_next = Pt(before), Pt(after), True
    width = sec.page_width - sec.left_margin - sec.right_margin
    hp = sec.header.paragraphs[0]
    hp.text = ""
    r = hp.add_run(running_title)
    r.font.size, r.font.color.rgb, r.bold = Pt(8.5), rgb(MUTED), True
    _own_tabs(hp, width)
    r2 = hp.add_run(f"\t{code}")
    r2.font.size, r2.font.color.rgb = Pt(8.5), rgb(MUTED)
    _bottom_rule(hp, LINE, 6)
    fp = sec.footer.paragraphs[0]
    fp.text = ""
    _own_tabs(fp, width)
    left = fp.add_run((note + "  ·  " if note else "") + "Confidential: prepared for the named client")
    left.font.size, left.font.color.rgb = Pt(8), rgb(MUTED)
    fp.add_run("\t")
    for text, field in (("Page ", None), (None, "PAGE"), (" of ", None), (None, "NUMPAGES")):
        run = fp.add_run(text or "")
        run.font.size, run.font.color.rgb = Pt(8), rgb(MUTED)
        if field:
            _field(run, field)
    return doc


def cover(doc, banner_path, title: str, subtitle: str, rows: list[tuple[str, str]], stamp: str | None = None) -> None:
    doc.add_picture(str(banner_path), width=Cm(16.8))
    doc.paragraphs[-1].paragraph_format.space_after = Pt(26)
    p = doc.add_paragraph()
    r = p.add_run(title)
    r.font.size, r.bold, r.font.color.rgb = Pt(30), True, rgb(INDIGO)
    p.paragraph_format.space_after = Pt(4)
    p2 = doc.add_paragraph()
    r2 = p2.add_run(subtitle)
    r2.font.size, r2.font.color.rgb = Pt(13.5), rgb(MUTED)
    _bottom_rule(p2, ORANGE, 12)
    p2.paragraph_format.space_after = Pt(18)
    if stamp:
        t = doc.add_table(rows=1, cols=1)
        c = t.rows[0].cells[0]
        shade(c, "#FDECEC")
        borders(c, left=(36, "#B91C1C"), top=None, bottom=None, right=None)
        rr = c.paragraphs[0].add_run(stamp)
        rr.bold, rr.font.size, rr.font.color.rgb = True, Pt(9.5), rgb("#991B1B")
        margins(t, 80, 80, 140, 120)
        doc.add_paragraph()
    para(doc, "Document control", bold=True, color=INDIGO, size=11)
    t = doc.add_table(rows=0, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    for k, v in rows:
        cells = t.add_row().cells
        cells[0].width, cells[1].width = Cm(4.2), Cm(12.6)
        a = cells[0].paragraphs[0].add_run(k); a.bold, a.font.size, a.font.color.rgb = True, Pt(9.5), rgb(MUTED)
        b = cells[1].paragraphs[0].add_run(v); b.font.size = Pt(9.5)
        for c in cells:
            borders(c, top=None, left=None, right=None, bottom=(4, LINE))
    t.autofit = False
    t.columns[0].width, t.columns[1].width = Cm(4.2), Cm(12.6)
    margins(t, 70, 70, 60, 60)
    doc.add_page_break()


def h1(doc, text: str, new_page: bool = False) -> None:
    if new_page:
        doc.add_page_break()
    p = doc.add_heading(text, level=1)
    _bottom_rule(p, LINE, 6)


def h2(doc, text: str) -> None:
    doc.add_heading(text, level=2)


def h3(doc, text: str) -> None:
    doc.add_heading(text, level=3)


def para(doc, text: str, bold=False, italic=False, color: str | None = None, size: float | None = None, after: float | None = None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold, r.italic = bold, italic
    if color:
        r.font.color.rgb = rgb(color)
    if size:
        r.font.size = Pt(size)
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    return p


def bullets(doc, items) -> None:
    for it in items:
        p = doc.add_paragraph(str(it), style="List Bullet")
        p.paragraph_format.space_after = Pt(2)


def numbered(doc, items) -> None:
    for it in items:
        p = doc.add_paragraph(str(it), style="List Number")
        p.paragraph_format.space_after = Pt(2)


def table(doc, header: list[str], rows: list[list], color: str = INDIGO, widths: list[float] | None = None, bold_first: bool = False, size: float = 9):
    """Clean table: coloured header, hairline row rules, subtle banding. widths in cm."""
    t = doc.add_table(rows=1, cols=len(header))
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    t.autofit = False
    for i, name in enumerate(header):
        c = t.rows[0].cells[i]
        shade(c, color)
        run = c.paragraphs[0].add_run(str(name))
        run.bold, run.font.color.rgb, run.font.size = True, rgb("#FFFFFF"), Pt(size)
        borders(c, top=None, left=None, right=None, bottom=None)
    for n, row in enumerate(rows):
        cells = t.add_row().cells
        for i, val in enumerate(row):
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            run = p.add_run("" if val is None else str(val))
            run.font.size = Pt(size)
            if bold_first and i == 0:
                run.bold = True
            borders(cells[i], top=None, left=None, right=None, bottom=(4, LINE))
            if n % 2:
                shade(cells[i], BAND)
    if widths:
        for i, w in enumerate(widths):
            t.columns[i].width = Cm(w)
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    margins(t, 55, 55, 90, 90)
    sp = doc.add_paragraph()
    sp.paragraph_format.space_after = Pt(4)
    return t


def tiles(doc, items: list[tuple[str, str, str]]) -> None:
    """KPI tiles: (label, value, accent colour)."""
    t = doc.add_table(rows=1, cols=len(items))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for c, (label, value, color) in zip(t.rows[0].cells, items):
        shade(c, tint(color))
        borders(c, top=(18, color), left=(8, "#FFFFFF"), right=(8, "#FFFFFF"), bottom=None)
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(str(value))
        r.bold, r.font.size, r.font.color.rgb = True, Pt(17), rgb(color)
        p2 = c.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.space_after = Pt(0)
        r2 = p2.add_run(label)
        r2.font.size, r2.font.color.rgb = Pt(8), rgb(MUTED)
    margins(t, 90, 90, 60, 60)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def callout(doc, text: str, kind: str = "info", title: str | None = None) -> None:
    style = {"info": (SKY, "#E7F2F9", INK), "warn": ("#B45309", "#FEF3E2", "#7C2D12"), "alert": ("#B91C1C", "#FDECEC", "#7F1D1D"),
             "ok": (EMERALD, "#E4F4EC", "#064E3B")}[kind]
    t = doc.add_table(rows=1, cols=1)
    c = t.rows[0].cells[0]
    shade(c, style[1])
    borders(c, left=(30, style[0]), top=None, bottom=None, right=None)
    p = c.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    if title:
        r0 = p.add_run(title + "  ")
        r0.bold, r0.font.size, r0.font.color.rgb = True, Pt(9.5), rgb(style[0])
    r = p.add_run(text)
    r.font.size, r.font.color.rgb = Pt(9.5), rgb(style[2])
    margins(t, 90, 90, 150, 120)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def figure(doc, path, caption: str, width_cm: float = 15.5) -> None:
    doc.add_picture(str(path), width=Cm(width_cm))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.paragraphs[-1].paragraph_format.keep_with_next = True
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cap.add_run(caption)
    r.italic, r.font.size, r.font.color.rgb = True, Pt(8.5), rgb(MUTED)
    cap.paragraph_format.space_after = Pt(10)


def contents(doc, items: list[tuple[str, str, str]]) -> None:
    h = doc.add_paragraph()
    r = h.add_run("Contents")
    r.bold, r.font.size, r.font.color.rgb = True, Pt(20), rgb(INDIGO)
    _bottom_rule(h, LINE, 6)
    t = doc.add_table(rows=0, cols=3)
    t.autofit = False
    for num, title, desc in items:
        cells = t.add_row().cells
        for c, w in zip(cells, (1.3, 5.6, 9.9)):
            c.width = Cm(w)
            borders(c, top=None, left=None, right=None, bottom=(4, LINE))
        a = cells[0].paragraphs[0].add_run(num); a.bold, a.font.color.rgb, a.font.size = True, rgb(VIOLET), Pt(10.5)
        b = cells[1].paragraphs[0].add_run(title); b.bold, b.font.size = True, Pt(10.5)
        c3 = cells[2].paragraphs[0].add_run(desc); c3.font.size, c3.font.color.rgb = Pt(9.5), rgb(MUTED)
    for i, w in enumerate((1.3, 5.6, 9.9)):
        t.columns[i].width = Cm(w)
    margins(t, 80, 80, 80, 80)
    doc.add_page_break()


def signoff(doc, rows: list[str]) -> None:
    t = doc.add_table(rows=1, cols=4)
    t.autofit = False
    for i, name in enumerate(("Role", "Name", "Signature", "Date")):
        c = t.rows[0].cells[i]
        shade(c, INDIGO)
        r = c.paragraphs[0].add_run(name)
        r.bold, r.font.color.rgb, r.font.size = True, rgb("#FFFFFF"), Pt(9)
    for role in rows:
        cells = t.add_row().cells
        cells[0].paragraphs[0].add_run(role).font.size = Pt(9.5)
        for c in cells:
            borders(c, top=None, left=None, right=None, bottom=(4, LINE))
            c.paragraphs[0].paragraph_format.space_after = Pt(14)
    for row in t.rows:
        for c, w in zip(row.cells, (4.2, 5.0, 4.6, 3.0)):
            c.width = Cm(w)
    margins(t, 90, 90, 90, 90)
    doc.add_paragraph()


def page_break(doc) -> None:
    doc.add_page_break()


def draft_card(doc, header: str, meta: str, body_lines: list[str], color: str, extras: list[tuple[str, str]] | None = None, issues: str = "") -> None:
    """One post draft as a card: tinted header strip, text, optional poll/slide notes."""
    t = doc.add_table(rows=1, cols=1)
    t.autofit = False
    c = t.rows[0].cells[0]
    c.width = Cm(16.8)
    shade(c, tint(color))
    borders(c, left=(30, color), top=(4, LINE), right=(4, LINE), bottom=None)
    p = c.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(header)
    r.bold, r.font.size, r.font.color.rgb = True, Pt(10.5), rgb(color)
    p2 = c.add_paragraph()
    p2.paragraph_format.space_after = Pt(0)
    r2 = p2.add_run(meta)
    r2.font.size, r2.font.color.rgb = Pt(8.5), rgb(MUTED)
    row = t.add_row().cells[0]
    row.width = Cm(16.8)
    borders(row, left=(30, color), top=None, right=(4, LINE), bottom=(4, LINE))
    first = True
    block = []
    for line in body_lines + [""]:
        if line.strip():
            block.append(line)
            continue
        if block:
            para_ = row.paragraphs[0] if first else row.add_paragraph()
            first = False
            para_.paragraph_format.space_after = Pt(5)
            for n, text in enumerate(block):
                run = para_.add_run(text)
                run.font.size = Pt(10)
                if n < len(block) - 1:
                    run.add_break(WD_BREAK.LINE)
            block = []
    for label, text in extras or []:
        pe = row.add_paragraph()
        pe.paragraph_format.space_after = Pt(2)
        a = pe.add_run(label + "  ")
        a.bold, a.font.size, a.font.color.rgb = True, Pt(8.5), rgb(color)
        b = pe.add_run(text)
        b.font.size, b.font.color.rgb = Pt(8.5), rgb(MUTED)
    if issues:
        pi = row.add_paragraph()
        ri = pi.add_run("To fix:  " + issues)
        ri.font.size, ri.font.color.rgb = Pt(8.5), rgb("#B91C1C")
    margins(t, 80, 80, 150, 130)
    sp = doc.add_paragraph()
    sp.paragraph_format.space_after = Pt(6)
