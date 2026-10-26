"""Slide layouts."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageOps

from .. import options as O
from .base import Canvas, Look, draw_lines, fit_block, get_font, rgba, wrap
from .decor import paint_decor


# ---------------------------------------------------------------- slides
def resolve_layout(slides: list[dict], i: int) -> str:
    layout = slides[i].get("layout", "auto")
    if layout != "auto":
        return layout
    if i == 0:
        return "title"
    if i == len(slides) - 1 and len(slides) > 2:
        return "cta"
    lines = [ln for ln in slides[i]["body"].split("\n") if ln.strip()]
    if len(lines) <= 1 and len(slides[i]["body"]) <= 150:
        return "statement"
    return "bullets"


def _load_photo(path: str):
    if not path:
        return None
    try:
        return Image.open(path).convert("RGB")
    except (OSError, ValueError):
        return None


def _paste_photo(cv: Canvas, photo, box):
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = max(2, x1 - x0), max(2, y1 - y0)
    fitted = ImageOps.fit(photo, (w, h), Image.Resampling.LANCZOS)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=int(26 * cv.u), fill=255)
    cv.img.paste(fitted, (x0, y0), mask)


def _bullets(text: str) -> list[str]:
    items = []
    for ln in text.split("\n"):
        ln = ln.strip()
        if not ln:
            continue
        for mark in ("- ", "• ", "* "):
            if ln.startswith(mark):
                ln = ln[len(mark):].strip()
                break
        items.append(ln)
    return items


def render_slide(project: dict, index: int, size: tuple[int, int] | None = None,
                 look: Look | None = None, slides: list[dict] | None = None,
                 force_layout: str | None = None) -> Image.Image:
    look = look or Look(project)
    slides = slides if slides is not None else project["slides"]
    slide = slides[index]
    size = size or O.FORMATS[project["options"]["format"]]
    if slide.get("free") and slides is project["slides"] and not force_layout:
        from .free import render_free_slide
        return render_free_slide(project, index, size, look)
    cv = Canvas(size, look.bg)
    paint_decor(cv, look, project["id"] + str(index))
    layout = force_layout or resolve_layout(slides, index)
    u, ts = cv.u, look.text_scale
    bx = look.sdef["box"]
    x0, y0, x1, y1 = bx[0] * cv.w, bx[1] * cv.h, bx[2] * cv.w, bx[3] * cv.h
    portrait = cv.h > cv.w
    photo = _load_photo(slide.get("image", ""))
    # reserve room for a photo
    if photo is not None:
        if portrait:
            _paste_photo(cv, photo, (x0, y1 - (y1 - y0) * 0.38, x1, y1))
            y1 = y1 - (y1 - y0) * 0.38 - 30 * u
        else:
            px0 = x0 + (x1 - x0) * 0.60
            _paste_photo(cv, photo, (px0, y0, x1, y1))
            x1 = px0 - 40 * u
    max_w, max_h = x1 - x0, y1 - y0
    heavy, kind = look.heavy, look.kind
    title, body = slide["title"].strip(), slide["body"].strip()

    if layout in ("title", "cta"):
        center = layout == "cta"
        t_font, t_lines, t_size, t_h = fit_block(title, kind, True, max_w, max_h * 0.55, 132 * u * ts, 50 * u, 1.15)
        b_h = 0
        b_font = b_lines = None
        if body:
            b_font, b_lines, b_size, b_h = fit_block(body, kind, False, max_w, max_h * 0.28, 52 * u * ts, 28 * u, 1.35)
        total = t_h + (30 * u + b_h if body else 0) + (70 * u if center else 0)
        y = y0 + max(0, (max_h - total) / 2)
        y = draw_lines(cv, t_lines, t_font, x0, y, look.heading, t_size * 1.15, "center" if center else "left", max_w)
        if body:
            y += 30 * u
            y = draw_lines(cv, b_lines, b_font, x0, y, look.text, b_size * 1.35, "center" if center else "left", max_w)
        if center:
            pw = min(max_w * 0.4, 420 * u)
            cv.d.rounded_rectangle([x0 + (max_w - pw) / 2, y + 36 * u, x0 + (max_w + pw) / 2, y + 36 * u + 26 * u], radius=13 * u, fill=rgba(look.marker))
        elif not photo:
            cv.d.rectangle([x0, y + 34 * u, x0 + 110 * u, y + 34 * u + 8 * u], fill=rgba(look.marker))
    elif layout == "statement":
        y = y0
        if title:
            t_font, t_lines, t_size, t_h = fit_block(title, kind, True, max_w, max_h * 0.22, 54 * u * ts, 30 * u, 1.2)
            y = draw_lines(cv, t_lines, t_font, x0, y, look.heading, t_size * 1.2)
            y += 26 * u
        room = max(40 * u, y1 - y)
        b_font, b_lines, b_size, b_h = fit_block(body or title, kind, heavy, max_w, room, 92 * u * ts, 34 * u, 1.28)
        y = y + max(0, (room - b_h) / 2)
        draw_lines(cv, b_lines, b_font, x0, y, look.text, b_size * 1.28)
    else:  # bullets
        t_font, t_lines, t_size, t_h = fit_block(title, kind, True, max_w, max_h * 0.26, 86 * u * ts, 40 * u, 1.15)
        items = _bullets(body)
        indent = 52 * u
        gap_t = 44 * u
        room = max(60 * u, max_h - t_h - gap_t)
        fsize = 62 * u * ts
        while True:
            f = get_font(kind, False, int(fsize))
            wrapped = [wrap(it, f, max_w - indent) for it in items]
            gap = fsize * 0.62
            total = sum(len(w) * fsize * 1.3 for w in wrapped) + gap * max(0, len(wrapped) - 1)
            if total <= room or fsize <= 26 * u:
                break
            fsize *= 0.94
        block = t_h + gap_t + total
        y = y0 + max(0, (max_h - block) / 2)
        y = draw_lines(cv, t_lines, t_font, x0, y, look.heading, t_size * 1.15)
        y += gap_t
        for w in wrapped:
            r = fsize * 0.16
            cy = y + fsize * 0.65
            cv.d.ellipse([x0 + 4 * u, cy - r, x0 + 4 * u + 2 * r, cy + r], fill=rgba(look.marker))
            y = draw_lines(cv, w, f, x0 + indent, y, look.text, fsize * 1.3)
            y += gap
            if y > y1 + fsize:
                break
    return cv.finish()


