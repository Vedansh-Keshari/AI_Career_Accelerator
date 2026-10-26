"""Paged documents and square posts."""
from __future__ import annotations

import json

from PIL import Image

from .. import options as O
from .base import (
    DOC_SIZE,
    POST_SIZE,
    Canvas,
    Look,
    contrast,
    draw_lines,
    fit_block,
    get_font,
    rgba,
    wrap,
)
from .slides import render_slide


# ---------------------------------------------------------------- documents
def _doc_page_look(look: Look):
    if look.mode == "dark":
        return look.bg, look.text
    return "#FFFFFF", look.pal["ink"]


_DOC_CACHE: "dict[str, list[Image.Image]]" = {}


def _full_document(project: dict) -> list[Image.Image]:
    """Full-size pages, remembered for the last few versions so preview sizes share one render."""
    key = json.dumps({k: project[k] for k in ("id", "title", "options", "tune", "doc")}, sort_keys=True)
    if key not in _DOC_CACHE:
        if len(_DOC_CACHE) >= 4:
            _DOC_CACHE.pop(next(iter(_DOC_CACHE)))
        _DOC_CACHE[key] = render_document(project, 1.0)
    return _DOC_CACHE[key]


def render_document(project: dict, scale: float = 1.0) -> list[Image.Image]:
    look = Look(project)
    doc = project["doc"]
    if doc["doc_type"] in O.SHORT_DOC_TYPES:
        text = "\n\n".join(s["body"].strip() for s in doc["sections"] if s["body"].strip())
        pseudo = [{"title": project["title"], "body": text or " ", "layout": "statement", "image": ""}]
        size = (int(POST_SIZE[0] * scale), int(POST_SIZE[1] * scale))
        return [render_slide(project, 0, size=size, look=look, slides=pseudo)]

    if abs(scale - 1.0) > 1e-9:
        # Always paginate at full size so previews, thumbnails and exports agree on the page count.
        full = _full_document(project)
        size = (max(20, int(DOC_SIZE[0] * scale)), max(20, int(DOC_SIZE[1] * scale)))
        return [im.resize(size, Image.Resampling.LANCZOS) for im in full]
    W, H = DOC_SIZE
    page_bg, ink = _doc_page_look(look)
    kind = look.kind
    probe = Canvas((W, H), page_bg, unit_from="w")
    margin = 110 * probe.u
    text_w = probe.w - 2 * margin
    body_size = 27 * probe.u * look.text_scale
    h_size = 36 * probe.u * look.text_scale
    body_font = get_font(kind, False, int(body_size))
    head_font = get_font(kind, True, int(h_size))
    title_font, title_lines, title_size, title_h = fit_block(
        project["title"], kind, True, text_w, 260 * probe.u, 70 * probe.u, 40 * probe.u, 1.15)
    band_h = max(300 * probe.u, title_h + 190 * probe.u)
    first_top = band_h + 70 * probe.u
    other_top = 130 * probe.u
    bottom = probe.h - 130 * probe.u
    lh = body_size * 1.55

    # flow items into pages
    pages: list[list[tuple]] = [[]]
    y = first_top
    def need(h):
        nonlocal y
        if y + h > bottom:
            pages.append([])
            y = other_top
    for sec in doc["sections"]:
        heading = sec["heading"].strip()
        lines: list[tuple[str, str]] = []
        for para in sec["body"].split("\n"):
            s_ = para.strip()
            if not s_:
                lines.append(("", "gap"))
                continue
            bullet = s_[:2] in ("- ", "• ", "* ")
            if bullet:
                s_ = s_[2:].strip()
            f_w = text_w - (36 * probe.u if bullet else 0)
            for j, ln in enumerate(wrap(s_, body_font, f_w)):
                lines.append((ln, ("bullet" if j == 0 else "cont") if bullet else "plain"))
        if heading:
            need(h_size * 1.4 + lh * 2)
            pages[-1].append(("h", heading, y))
            y += h_size * 1.45
        for ln, mode in lines:
            if mode == "gap":
                y += lh * 0.45
                continue
            need(lh)
            pages[-1].append(("l", ln, y, mode))
            y += lh
        y += lh * 0.7

    out = []
    total = len(pages)
    for n, items in enumerate(pages):
        cv = Canvas((W, H), page_bg, unit_from="w")
        d, p = cv.d, look.pal
        if n == 0:
            if look.sdef["decor"] in ("watercolor", "blobs"):
                d.rectangle([0, 0, cv.w, band_h], fill=rgba(p["surface"]))
                d.ellipse([cv.w * 0.72, -band_h * 0.5, cv.w * 1.1, band_h * 0.8], fill=rgba(p["accent"], 160))
                head_col = ink if contrast(ink, p["surface"]) >= 4 else "#000000"
            else:
                d.rectangle([0, 0, cv.w, band_h], fill=rgba(p["primary"]))
                d.rectangle([0, band_h, cv.w, band_h + 10 * cv.u], fill=rgba(look.marker if look.mode != "dark" else p["accent"]))
                head_col = p["on_primary"] if look.mode != "dark" else look.heading
            ty = (band_h - title_h) / 2
            draw_lines(cv, title_lines, title_font, margin, ty, head_col, title_size * 1.15)
        else:
            d.rectangle([margin, 70 * cv.u, cv.w - margin, 70 * cv.u + 4 * cv.u], fill=rgba(p["primary"], 220))
        for item in items:
            if item[0] == "h":
                col = look.heading if look.mode != "dark" else look.heading
                d.text((margin, item[2]), item[1], font=head_font, fill=col)
            else:
                _, ln, yy, mode = item
                if mode == "bullet":
                    r = body_size * 0.15
                    cy = yy + body_size * 0.7
                    d.ellipse([margin + 6 * cv.u, cy - r, margin + 6 * cv.u + 2 * r, cy + r], fill=rgba(look.marker))
                x = margin + (36 * cv.u if mode in ("bullet", "cont") else 0)
                d.text((x, yy), ln, font=body_font, fill=ink)
        foot = get_font(kind, False, int(18 * cv.u))
        d.text((cv.w - margin, cv.h - 80 * cv.u), f"{n + 1} / {total}", font=foot, fill=rgba(ink, 130), anchor="ra")
        out.append(cv.finish())
    return out


