"""Free-layout slides: draggable text boxes, shapes and images placed by fractions of the slide."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageOps

from .base import Canvas, Look, get_font, resolve_color, rgba, wrap
from .decor import paint_decor


def parse_paragraphs(text: str) -> list[tuple[bool, str]]:
    """Split text into (is_bullet, line) pairs. Lines starting with '- ' are bullets; blank lines are spacers."""
    out: list[tuple[bool, str]] = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            out.append((False, ""))
        elif line[:2] in ("- ", "• ", "* "):
            out.append((True, line[2:].strip()))
        else:
            out.append((False, line))
    return out


def fit_element_text(el: dict, look: Look, box_w: float, box_h: float, u: float) -> dict:
    """Largest size (<= the element's size, scaled by u) at which the text fits the box.

    Returns {'size': px, 'lines': [(bullet, line, first_of_item)], 'height': px, 'font': FreeTypeFont}.
    Used by both the renderer and the .pptx exporter so they agree on the final font size.
    """
    paras = parse_paragraphs(el["text"])
    size = max(8 * u, el["size"] * u * look.text_scale)
    floor = 8 * u
    indent_px = 0.0
    while True:
        font = get_font(look.kind, el["bold"], int(size))
        indent_px = size * 0.85
        lines: list[tuple[bool, str, bool]] = []
        for bullet, text in paras:
            if not text:
                lines.append((False, "", False))
                continue
            for j, ln in enumerate(wrap(text, font, box_w - (indent_px if bullet else 0))):
                lines.append((bullet, ln, j == 0))
        lh = size * 1.3
        height = sum(lh * (0.5 if not ln and not b else 1.0) for b, ln, _ in lines)
        if height <= box_h or size <= floor:
            break
        size *= 0.94
    return {"size": size, "lines": lines, "height": height, "font": font, "lh": size * 1.3, "indent": indent_px}


def draw_text_element(cv: Canvas, look: Look, el: dict) -> None:
    x, y, w, h = el["x"] * cv.w, el["y"] * cv.h, el["w"] * cv.w, el["h"] * cv.h
    d = cv.d
    if el.get("fill"):
        d.rounded_rectangle([x, y, x + w, y + h], radius=14 * cv.u, fill=rgba(resolve_color(look, el["fill"])))
    pad = 10 * cv.u if el.get("fill") else 0
    fit = fit_element_text(el, look, w - 2 * pad, h - 2 * pad, cv.u)
    color = resolve_color(look, el["color"])
    top = y + pad
    if el["valign"] == "middle":
        top = y + (h - fit["height"]) / 2
    elif el["valign"] == "bottom":
        top = y + h - pad - fit["height"]
    cur = top
    size, lh, indent = fit["size"], fit["lh"], fit["indent"]
    for bullet, line, first in fit["lines"]:
        if not line:
            cur += lh * 0.5
            continue
        tx = x + pad + (indent if bullet else 0)
        if el["align"] == "center":
            d.text((x + w / 2 + (indent / 2 if bullet else 0), cur), line, font=fit["font"], fill=color, anchor="ma")
        elif el["align"] == "right":
            d.text((x + w - pad, cur), line, font=fit["font"], fill=color, anchor="ra")
        else:
            d.text((tx, cur), line, font=fit["font"], fill=color)
        if bullet and first and el["align"] == "left":
            r = size * 0.15
            cy = cur + size * 0.65
            d.ellipse([x + pad + 3 * cv.u, cy - r, x + pad + 3 * cv.u + 2 * r, cy + r], fill=rgba(look.marker))
        cur += lh


def draw_elements(cv: Canvas, look: Look, elements: list[dict]) -> None:
    for el in elements:
        x, y, w, h = el["x"] * cv.w, el["y"] * cv.h, el["w"] * cv.w, el["h"] * cv.h
        if el["type"] in ("rect", "ellipse"):
            fill = rgba(resolve_color(look, el["fill"]), int(255 * el["opacity"]))
            if el["type"] == "ellipse":
                cv.d.ellipse([x, y, x + w, y + h], fill=fill)
            else:
                cv.d.rounded_rectangle([x, y, x + w, y + h], radius=el["radius"] * min(w, h), fill=fill)
        elif el["type"] == "image":
            try:
                photo = Image.open(el["image"]).convert("RGB")
            except (OSError, ValueError):
                cv.d.rounded_rectangle([x, y, x + w, y + h], radius=16 * cv.u, outline=rgba(look.pal["surface"]), width=int(3 * cv.u))
                continue
            iw, ih = max(2, int(w)), max(2, int(h))
            fitted = ImageOps.fit(photo, (iw, ih), Image.Resampling.LANCZOS)
            mask = Image.new("L", (iw, ih), 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, iw - 1, ih - 1], radius=int(24 * cv.u), fill=255)
            cv.img.paste(fitted, (int(x), int(y)), mask)
        else:
            draw_text_element(cv, look, el)


def render_free_slide(project: dict, index: int, size: tuple[int, int], look: Look | None = None) -> Image.Image:
    look = look or Look(project)
    slide = project["slides"][index]
    cv = Canvas(size, look.bg)
    paint_decor(cv, look, project["id"] + str(index))
    draw_elements(cv, look, slide["elements"])
    return cv.finish()


def render_background(project: dict, index: int, size: tuple[int, int], look: Look | None = None) -> Image.Image:
    """Just the style's background and decoration (no text), used behind native .pptx text."""
    look = look or Look(project)
    cv = Canvas(size, look.bg)
    paint_decor(cv, look, project["id"] + str(index))
    return cv.finish()
