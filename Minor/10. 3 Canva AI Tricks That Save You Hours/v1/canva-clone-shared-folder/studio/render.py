"""Pillow renderer shared by the website and the desktop app.

Everything is drawn at 2x and scaled down, so edges and text are smooth.
render_pages(project, scale) -> list of PIL images (slides, document pages or the logo).
"""
from __future__ import annotations

import io
import math
import random
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from . import options as O
from .paths import FONT_DIR

SS = 2  # supersampling factor
DOC_SIZE = (1240, 1754)  # A4 at 150 dpi
POST_SIZE = (1080, 1080)
LOGO_SIZE = (1000, 1000)

FONT_FILES = {
    ("sans", False): "Poppins-Regular.ttf",
    ("sans", True): "Poppins-Bold.ttf",
    ("serif", False): "DejaVuSerif.ttf",
    ("serif", True): "DejaVuSerif-Bold.ttf",
}


@lru_cache(maxsize=256)
def get_font(kind: str, bold: bool, size: int) -> ImageFont.FreeTypeFont:
    size = max(6, int(size))
    path = Path(FONT_DIR) / FONT_FILES[(kind, bold)]
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default(size=size)  # Pillow 10.1+ built-in font


# ---------------------------------------------------------------- colour helpers
def _lum(rgb) -> float:
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: str, b: str) -> float:
    la, lb = _lum(O.hex_to_rgb(a)), _lum(O.hex_to_rgb(b))
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def mix(a: str, b: str, t: float) -> str:
    ra, rb = O.hex_to_rgb(a), O.hex_to_rgb(b)
    return O.rgb_to_hex([ra[i] * (1 - t) + rb[i] * t for i in range(3)])


class Look:
    """Colours, fonts and decoration chosen from a project's options."""

    def __init__(self, project: dict):
        opts, tune = project["options"], project["tune"]
        self.sdef = O.STYLE_DEFS[opts["style"]]
        self.pal = O.palette_for(opts["color"], tune["boldness"])
        self.text_scale = tune["text_scale"]
        self.kind = self.sdef["font"]
        self.heavy = self.sdef["bold"]
        p, mode = self.pal, self.sdef["mode"]
        self.mode = mode
        if mode == "dark":
            self.bg = mix(p["primary"], "#000000", 0.82)
            self.text = "#F2F5FA"
            self.heading = p["accent"] if contrast(p["accent"], self.bg) >= 3 else "#FFFFFF"
        elif mode == "primary":
            self.bg = p["primary"]
            self.text = p["on_primary"]
            self.heading = p["on_primary"]
        else:
            self.bg = p["bg"]
            self.text = p["ink"]
            self.heading = p["primary"] if contrast(p["primary"], self.bg) >= 3 else p["ink"]
        self.marker = p["accent"] if contrast(p["accent"], self.bg) >= 1.6 else p["primary"]
        if contrast(self.marker, self.bg) < 1.3:
            self.marker = self.text


class Canvas:
    def __init__(self, size: tuple[int, int], bg: str, unit_from: str = "min"):
        self.W, self.H = size
        self.w, self.h = self.W * SS, self.H * SS
        base = min(self.W, self.H) if unit_from == "min" else self.W
        self.u = base / 1080 * SS  # one design unit in drawing pixels
        self.img = Image.new("RGB", (self.w, self.h), bg)
        self.d = ImageDraw.Draw(self.img, "RGBA")

    def paste_layer(self, layer: Image.Image):
        self.img.paste(layer, (0, 0), layer)
        self.d = ImageDraw.Draw(self.img, "RGBA")

    def finish(self) -> Image.Image:
        return self.img.resize((self.W, self.H), Image.LANCZOS)


def rgba(hex_color: str, alpha: int = 255):
    return O.hex_to_rgb(hex_color) + (alpha,)


# ---------------------------------------------------------------- text helpers
def wrap(text: str, font, max_w: float) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            trial = f"{cur} {word}".strip() if cur else word
            if font.getlength(trial) <= max_w:
                cur = trial
                continue
            if cur:
                lines.append(cur)
            while len(word) > 1 and font.getlength(word) > max_w:
                k = len(word)
                while k > 1 and font.getlength(word[:k]) > max_w:
                    k -= 1
                lines.append(word[:k])
                word = word[k:]
            cur = word
        lines.append(cur)
    return lines


def fit_name(text, kind, bold, max_w, max_h, start, min_single, minimum, spacing=1.1):
    """Keep a short name on one line if it can stay at least `min_single` big; otherwise wrap."""
    size = float(start)
    while size >= min_single:
        font = get_font(kind, bold, int(size))
        if font.getlength(text) <= max_w:
            return font, [text], size, size * spacing
        size *= 0.95
    return fit_block(text, kind, bold, max_w, max_h, start, minimum, spacing)


def fit_block(text, kind, bold, max_w, max_h, start, minimum, spacing=1.3):
    """Largest font size (down to `minimum`) whose wrapped text fits max_h."""
    size = float(start)
    while True:
        font = get_font(kind, bold, int(size))
        lines = wrap(text, font, max_w)
        height = len(lines) * size * spacing
        if height <= max_h or size <= minimum:
            break
        size *= 0.94
    fits = int(max_h // (size * spacing)) or 1
    if len(lines) > fits:
        lines = lines[:fits]
        lines[-1] = lines[-1].rstrip(" .,;") + "…"
        height = len(lines) * size * spacing
    return font, lines, size, height


def draw_lines(cv: Canvas, lines, font, x, y, color, lh, align="left", max_w=0):
    for line in lines:
        if align == "center":
            cv.d.text((x + max_w / 2, y), line, font=font, fill=color, anchor="ma")
        else:
            cv.d.text((x, y), line, font=font, fill=color)
        y += lh
    return y


# ---------------------------------------------------------------- decorations
def _poly_rot(cx, cy, w, h, deg):
    a = math.radians(deg)
    pts = []
    for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        pts.append((cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a)))
    return pts


def _outside_box(x, y, r, box, w, h, pad=0.02):
    x0, y0, x1, y1 = box[0] * w, box[1] * h, box[2] * w, box[3] * h
    px, py = pad * w, pad * h
    return x + r < x0 - px or x - r > x1 + px or y + r < y0 - py or y - r > y1 + py


def decor_thin_line(cv, look, rng):
    d, u, p = cv.d, cv.u, look.pal
    d.rectangle([cv.w * 0.058, cv.h * 0.14, cv.w * 0.058 + 6 * u, cv.h * 0.30], fill=rgba(look.marker))
    d.rectangle([cv.w * 0.90, cv.h * 0.92, cv.w * 0.94, cv.h * 0.92 + 6 * u], fill=rgba(p["primary"]))


def decor_confetti(cv, look, rng):
    d, u, p = cv.d, cv.u, look.pal
    colors = [p["accent"], p["surface"], p["primary"]]
    placed = 0
    for _ in range(300):
        r = rng.uniform(16, 60) * u
        x, y = rng.uniform(0, cv.w), rng.uniform(0, cv.h)
        if _outside_box(x, y, r, look.sdef["box"], cv.w, cv.h, 0.01):
            d.ellipse([x - r, y - r, x + r, y + r], fill=rgba(rng.choice(colors), 235))
            placed += 1
            if placed >= 14:
                break
    d.rounded_rectangle([cv.w * 0.04, cv.h * 0.93, cv.w * 0.20, cv.h * 0.93 + 22 * u], radius=11 * u, fill=rgba(p["primary"]))


def decor_blobs(cv, look, rng):
    p = look.pal
    layer = Image.new("RGBA", (cv.w, cv.h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([cv.w * 0.70, -cv.h * 0.25, cv.w * 1.15, cv.h * 0.38], fill=rgba(p["surface"], 235))
    d.ellipse([cv.w * 0.82, cv.h * 0.02, cv.w * 1.05, cv.h * 0.30], fill=rgba(p["accent"], 150))
    d.ellipse([-cv.w * 0.12, cv.h * 0.66, cv.w * 0.26, cv.h * 1.2], fill=rgba(p["surface"], 235))
    d.ellipse([cv.w * 0.02, cv.h * 0.84, cv.w * 0.16, cv.h * 1.06], fill=rgba(p["primary"], 120))
    cv.paste_layer(layer)


def decor_geometric(cv, look, rng):
    d, p = cv.d, look.pal
    d.polygon([(cv.w, 0), (cv.w * 0.80, 0), (cv.w, cv.h * 0.46)], fill=rgba(p["primary"]))
    d.polygon([(cv.w, cv.h * 0.16), (cv.w * 0.93, cv.h * 0.16), (cv.w, cv.h * 0.30)], fill=rgba(p["accent"]))
    d.rectangle([cv.w * 0.84, cv.h * 0.74, cv.w, cv.h], fill=rgba(p["accent"]))
    d.ellipse([cv.w * 0.80, cv.h * 0.66, cv.w * 0.92, cv.h * 0.66 + cv.w * 0.12], outline=rgba(p["primary"]), width=int(8 * cv.u))
    d.rectangle([0, cv.h * 0.95, cv.w * 0.30, cv.h], fill=rgba(p["surface"]))


def decor_modular(cv, look, rng):
    d, p = cv.d, look.pal
    cols, rows = 3, 4
    gx0, gx1 = cv.w * 0.73, cv.w * 0.95
    gy0, gy1 = cv.h * 0.12, cv.h * 0.88
    gap = 14 * cv.u
    cw, ch = (gx1 - gx0 - gap * (cols - 1)) / cols, (gy1 - gy0 - gap * (rows - 1)) / rows
    pattern = [p["primary"], p["surface"], None, p["accent"], None, p["primary"],
               p["surface"], p["accent"], None, None, p["surface"], p["primary"]]
    for i, color in enumerate(pattern):
        if color is None:
            continue
        r, c = divmod(i, cols)
        x, y = gx0 + c * (cw + gap), gy0 + r * (ch + gap)
        d.rounded_rectangle([x, y, x + cw, y + ch], radius=14 * cv.u, fill=rgba(color))


def decor_double_border(cv, look, rng):
    d, u, p = cv.d, cv.u, look.pal
    m1, m2 = 0.04, 0.055
    d.rectangle([cv.w * m1, cv.h * m1, cv.w * (1 - m1), cv.h * (1 - m1)], outline=rgba(p["primary"]), width=int(4 * u))
    d.rectangle([cv.w * m2, cv.h * m2 * (cv.w / cv.h), cv.w * (1 - m2), cv.h - cv.h * m2 * (cv.w / cv.h)], outline=rgba(look.marker), width=max(1, int(2 * u)))


def decor_heavy_block(cv, look, rng):
    d, p = cv.d, look.pal
    d.rectangle([0, cv.h * 0.86, cv.w, cv.h], fill=rgba(p["accent"]))
    d.ellipse([cv.w * 0.84, -cv.h * 0.12, cv.w * 1.08, cv.h * 0.20], fill=rgba(p["surface"], 90))
    d.rectangle([0, cv.h * 0.86 - 10 * cv.u, cv.w * 0.35, cv.h * 0.86], fill=rgba(look.text, 255))


def decor_split(cv, look, rng):
    d, p = cv.d, look.pal
    x = cv.w * 0.30
    d.rectangle([0, 0, x, cv.h], fill=rgba(p["primary"]))
    d.rectangle([x, 0, x + 12 * cv.u, cv.h], fill=rgba(p["accent"]))
    d.ellipse([-cv.w * 0.10, cv.h * 0.62, cv.w * 0.20, cv.h * 0.62 + cv.w * 0.30], fill=rgba(p["surface"], 70))
    d.ellipse([cv.w * 0.05, cv.h * 0.06, cv.w * 0.14, cv.h * 0.06 + cv.w * 0.09], outline=rgba(p["on_primary"], 200), width=int(6 * cv.u))


def decor_neon_grid(cv, look, rng):
    d, u, p = cv.d, cv.u, look.pal
    step = 90 * u
    x = 0
    while x < cv.w:
        d.line([(x, 0), (x, cv.h)], fill=rgba(look.marker, 22), width=max(1, int(u)))
        x += step
    y = 0
    while y < cv.h:
        d.line([(0, y), (cv.w, y)], fill=rgba(look.marker, 22), width=max(1, int(u)))
        y += step
    m = cv.w * 0.035
    L = 70 * u
    for sx, sy, dx, dy in ((m, m, 1, 1), (cv.w - m, m, -1, 1), (m, cv.h - m, 1, -1), (cv.w - m, cv.h - m, -1, -1)):
        d.line([(sx, sy), (sx + dx * L, sy)], fill=rgba(look.marker), width=int(5 * u))
        d.line([(sx, sy), (sx, sy + dy * L)], fill=rgba(look.marker), width=int(5 * u))


def decor_header_bar(cv, look, rng):
    d, p = cv.d, look.pal
    d.rectangle([0, 0, cv.w, cv.h * 0.15], fill=rgba(p["primary"]))
    d.rectangle([0, cv.h * 0.15, cv.w, cv.h * 0.15 + 8 * cv.u], fill=rgba(look.marker))
    d.rectangle([cv.w * 0.08, cv.h * 0.94, cv.w * 0.92, cv.h * 0.94 + 3 * cv.u], fill=rgba(p["surface"]))


def decor_stripes(cv, look, rng):
    d, p = cv.d, look.pal
    top = cv.h * 0.72
    band = cv.h * 0.07
    for i, color in enumerate((p["primary"], p["accent"], p["surface"], p["primary"])):
        d.rectangle([0, top + i * band, cv.w, top + (i + 1) * band], fill=rgba(color))
    r = cv.h * 0.17
    d.pieslice([cv.w * 0.78 - r, top - r, cv.w * 0.78 + r, top + r], 180, 360, fill=rgba(p["accent"]))


def decor_tape(cv, look, rng):
    d, u, p = cv.d, cv.u, look.pal
    bx = look.sdef["box"]
    pad = 0.05
    cx, cy = cv.w * (bx[0] + bx[2]) / 2, cv.h * (bx[1] + bx[3]) / 2
    pw, ph = cv.w * (bx[2] - bx[0] + pad * 1.6), cv.h * (bx[3] - bx[1] + pad * 1.6)
    d.polygon(_poly_rot(cx + 8 * u, cy + 10 * u, pw, ph, -1.2), fill=(0, 0, 0, 38))
    d.polygon(_poly_rot(cx, cy, pw, ph, -1.2), fill=(255, 255, 255, 255))
    for dx, ang in ((-0.43, -28), (0.43, 24)):
        d.polygon(_poly_rot(cx + dx * pw, cy - ph / 2 + 6 * u, 150 * u, 46 * u, ang), fill=rgba(look.pal["accent"], 190))


def decor_watercolor(cv, look, rng):
    """Soft washes: paint translucent ellipses, then blur (nothing else is on the page yet)."""
    p = look.pal
    d = cv.d
    blobs = [
        (0.05, 0.0, 0.42, 0.40, p["accent"], 130), (0.58, -0.05, 1.02, 0.34, p["primary"], 105),
        (0.74, 0.62, 1.10, 1.08, p["accent"], 125), (-0.08, 0.66, 0.34, 1.10, p["primary"], 100),
        (0.30, 0.78, 0.62, 1.10, p["surface"], 170),
    ]
    for x0, y0, x1, y1, color, a in blobs:
        d.ellipse([cv.w * x0, cv.h * y0, cv.w * x1, cv.h * y1], fill=rgba(color, a))
    cv.img = cv.img.filter(ImageFilter.GaussianBlur(radius=34 * cv.u))
    cv.d = ImageDraw.Draw(cv.img, "RGBA")


DECORS = {
    "thin_line": decor_thin_line, "confetti": decor_confetti, "blobs": decor_blobs,
    "geometric": decor_geometric, "modular": decor_modular, "double_border": decor_double_border,
    "heavy_block": decor_heavy_block, "split": decor_split, "neon_grid": decor_neon_grid,
    "header_bar": decor_header_bar, "stripes": decor_stripes, "tape": decor_tape,
    "watercolor": decor_watercolor,
}


def paint_decor(cv: Canvas, look: Look, seed: str):
    DECORS[look.sdef["decor"]](cv, look, random.Random(seed))


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
    fitted = ImageOps.fit(photo, (w, h), Image.LANCZOS)
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
        size = 62 * u * ts
        while True:
            f = get_font(kind, False, int(size))
            wrapped = [wrap(it, f, max_w - indent) for it in items]
            gap = size * 0.62
            total = sum(len(w) * size * 1.3 for w in wrapped) + gap * max(0, len(wrapped) - 1)
            if total <= room or size <= 26 * u:
                break
            size *= 0.94
        block = t_h + gap_t + total
        y = y0 + max(0, (max_h - block) / 2)
        y = draw_lines(cv, t_lines, t_font, x0, y, look.heading, t_size * 1.15)
        y += gap_t
        for w in wrapped:
            r = size * 0.16
            cy = y + size * 0.65
            cv.d.ellipse([x0 + 4 * u, cy - r, x0 + 4 * u + 2 * r, cy + r], fill=rgba(look.marker))
            y = draw_lines(cv, w, f, x0 + indent, y, look.text, size * 1.3)
            y += gap
            if y > y1 + size:
                break
    return cv.finish()


# ---------------------------------------------------------------- documents
def _doc_page_look(look: Look):
    if look.mode == "dark":
        return look.bg, look.text
    return "#FFFFFF", look.pal["ink"]


_DOC_CACHE: "dict[str, list[Image.Image]]" = {}


def _full_document(project: dict) -> list[Image.Image]:
    """Full-size pages, remembered for the last few versions so preview sizes share one render."""
    import json
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
        return [im.resize(size, Image.LANCZOS) for im in full]
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


# ---------------------------------------------------------------- logos
ICON_WORDS = [
    ("book_steam", ("book", "read", "librar"), ("caf", "coffee", "tea", "bakery", "food")),
    ("book", ("book", "read", "librar", "novel", "publish"), ()),
    ("cup", ("caf", "coffee", "tea", "bakery", "restaurant", "food", "kitchen"), ()),
    ("leaf", ("plant", "eco", "green", "garden", "nature", "organic", "leaf", "farm"), ()),
    ("bolt", ("energy", "power", "tech", "fast", "electric", "speed", "gaming"), ()),
    ("heart", ("love", "care", "health", "wellness", "family", "charity"), ()),
    ("mountain", ("travel", "mountain", "outdoor", "hike", "adventure", "trek"), ()),
]


def pick_icon(logo: dict) -> str:
    if logo.get("icon") and logo["icon"] != "auto":
        return logo["icon"]
    text = (logo.get("description", "") + " " + logo.get("brand", "") + " " + logo.get("tagline", "")).lower()
    for name, must_any, also_any in ICON_WORDS:
        if any(w in text for w in must_any) and (not also_any or any(w in text for w in also_any)):
            return name
    return "star"


def draw_icon(d: ImageDraw.ImageDraw, name: str, cx: float, cy: float, s: float, c1, c2):
    """Draw a simple icon about 2*s wide, centred on cx, cy. c1 main colour, c2 accent."""
    steam = name == "book_steam"
    if name in ("book", "book_steam"):
        oy = s * 0.12 if steam else 0
        left = [(cx - s, cy - 0.45 * s + oy), (cx - 0.04 * s, cy - 0.25 * s + oy), (cx - 0.04 * s, cy + 0.6 * s + oy), (cx - s, cy + 0.4 * s + oy)]
        right = [(cx + s, cy - 0.45 * s + oy), (cx + 0.04 * s, cy - 0.25 * s + oy), (cx + 0.04 * s, cy + 0.6 * s + oy), (cx + s, cy + 0.4 * s + oy)]
        d.polygon(left, fill=c1)
        d.polygon(right, fill=c1)
        d.line([(cx - 0.8 * s, cy - 0.1 * s + oy), (cx - 0.25 * s, cy + 0.03 * s + oy)], fill=c2, width=max(2, int(s * 0.06)))
        d.line([(cx + 0.8 * s, cy - 0.1 * s + oy), (cx + 0.25 * s, cy + 0.03 * s + oy)], fill=c2, width=max(2, int(s * 0.06)))
        d.line([(cx - 1.05 * s, cy + 0.62 * s + oy), (cx + 1.05 * s, cy + 0.62 * s + oy)], fill=c2, width=max(3, int(s * 0.1)))
        if steam:
            for dx in (-0.35, 0, 0.35):
                pts = [(cx + dx * s + math.sin(t / 3 * math.pi * 2) * 0.09 * s, cy - 0.62 * s - t * 0.12 * s) for t in range(0, 7)]
                d.line(pts, fill=c2, width=max(3, int(s * 0.07)), joint="curve")
    elif name == "cup":
        d.rounded_rectangle([cx - 0.62 * s, cy - 0.15 * s, cx + 0.5 * s, cy + 0.65 * s], radius=int(0.22 * s), fill=c1)
        d.ellipse([cx + 0.28 * s, cy + 0.0 * s, cx + 0.95 * s, cy + 0.48 * s], outline=c1, width=max(3, int(s * 0.1)))
        d.rounded_rectangle([cx - 0.95 * s, cy + 0.68 * s, cx + 0.85 * s, cy + 0.8 * s], radius=int(0.06 * s), fill=c2)
        for dx in (-0.3, 0.0, 0.3):
            pts = [(cx + dx * s + math.sin(t / 3 * math.pi * 2) * 0.08 * s, cy - 0.3 * s - t * 0.12 * s) for t in range(0, 6)]
            d.line(pts, fill=c2, width=max(3, int(s * 0.07)), joint="curve")
    elif name == "leaf":
        a = math.radians(-38)
        pts = []
        for i in range(0, 41):
            x = -1 + i / 20 if i <= 20 else 1 - (i - 20) / 20
            sign = -1 if i <= 20 else 1
            y = sign * 0.52 * (1 - x * x)
            pts.append((cx + s * (x * math.cos(a) - y * math.sin(a)), cy + s * (x * math.sin(a) + y * math.cos(a))))
        d.polygon(pts, fill=c1)
        d.line([(cx - s * math.cos(a), cy - s * math.sin(a)), (cx + 0.95 * s * math.cos(a), cy + 0.95 * s * math.sin(a))], fill=c2, width=max(3, int(s * 0.07)))
    elif name == "star":
        pts = []
        for i in range(10):
            r = s if i % 2 == 0 else s * 0.42
            ang = -math.pi / 2 + i * math.pi / 5
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        d.polygon(pts, fill=c1)
        d.ellipse([cx - 0.14 * s, cy - 0.14 * s, cx + 0.14 * s, cy + 0.14 * s], fill=c2)
    elif name == "bolt":
        pts = [(0.15, -1), (-0.55, 0.12), (-0.05, 0.12), (-0.25, 1), (0.6, -0.2), (0.08, -0.2), (0.4, -1)]
        d.polygon([(cx + x * s, cy + y * s) for x, y in pts], fill=c1)
    elif name == "heart":
        r = 0.5 * s
        d.ellipse([cx - s, cy - 0.85 * s, cx, cy + 0.15 * s], fill=c1)
        d.ellipse([cx, cy - 0.85 * s, cx + s, cy + 0.15 * s], fill=c1)
        d.polygon([(cx - 0.97 * s, cy - 0.28 * s), (cx + 0.97 * s, cy - 0.28 * s), (cx, cy + 0.95 * s)], fill=c1)
        d.ellipse([cx - 0.7 * s, cy - 0.55 * s, cx - 0.4 * s, cy - 0.28 * s], fill=c2)
    elif name == "mountain":
        d.polygon([(cx - s, cy + 0.7 * s), (cx - 0.25 * s, cy - 0.6 * s), (cx + 0.5 * s, cy + 0.7 * s)], fill=c1)
        d.polygon([(cx - 0.1 * s, cy + 0.7 * s), (cx + 0.5 * s, cy - 0.2 * s), (cx + s, cy + 0.7 * s)], fill=c2)
        d.ellipse([cx + 0.45 * s, cy - 0.85 * s, cx + 0.85 * s, cy - 0.45 * s], fill=c2)


def _initials(brand: str) -> str:
    words = [w for w in brand.replace("&", " ").split() if w[:1].isalnum()]
    if not words:
        return "?"
    return (words[0][0] + (words[1][0] if len(words) > 1 else "")).upper()


def render_logo(project: dict, variant: int | None = None, scale: float = 1.0) -> Image.Image:
    look = Look(project)
    if look.mode == "primary":  # a primary-coloured page would hide primary-coloured marks
        look.bg, look.text = look.pal["bg"], look.pal["ink"]
        look.heading = look.pal["primary"] if contrast(look.pal["primary"], look.bg) >= 3 else look.pal["ink"]
        look.marker = look.pal["accent"]
    logo = project["logo"]
    variant = logo["variant"] if variant is None else variant
    W, H = int(LOGO_SIZE[0] * scale), int(LOGO_SIZE[1] * scale)
    cv = Canvas((W, H), look.bg)
    d, u, p = cv.d, cv.u, look.pal
    brand = logo["brand"].strip() or project["title"]
    tagline = logo["tagline"].strip()
    icon = pick_icon(logo)
    kind = look.kind
    cx = cv.w / 2
    brand_col = look.heading if look.mode != "dark" else look.text

    if variant == 0:  # Badge
        r = cv.w * 0.39
        cy = cv.h / 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=rgba(p["primary"]))
        d.ellipse([cx - r + 24 * u, cy - r + 24 * u, cx + r - 24 * u, cy + r - 24 * u], outline=rgba(p["surface"], 210), width=int(8 * u))
        draw_icon(d, icon, cx, cy - r * 0.42, r * 0.26, rgba(p["on_primary"]), rgba(p["surface"]))
        f, lines, size, h = fit_name(brand, kind, True, r * 1.3, r * 0.55, 76 * u, 44 * u, 28 * u, 1.12)
        y = cy - r * 0.08
        y = draw_lines(cv, lines, f, cx - r * 0.65, y, p["on_primary"], size * 1.12, "center", r * 1.3)
        if tagline:
            f2, l2, s2, h2 = fit_block(tagline, kind, False, r * 1.2, r * 0.3, 34 * u, 18 * u, 1.2)
            draw_lines(cv, l2, f2, cx - r * 0.6, y + 12 * u, rgba(p["on_primary"], 215), s2 * 1.2, "center", r * 1.2)
    elif variant == 1:  # Wordmark
        f, lines, size, h = fit_name(brand, kind, True, cv.w * 0.82, cv.h * 0.34, 150 * u, 80 * u, 48 * u, 1.1)
        icon_s = cv.w * 0.07
        total = icon_s * 2 + 40 * u + h + 60 * u + (80 * u if tagline else 0)
        y = (cv.h - total) / 2
        draw_icon(d, icon, cx, y + icon_s, icon_s, rgba(p["primary"]), rgba(p["accent"]))
        y += icon_s * 2 + 40 * u
        y = draw_lines(cv, lines, f, cv.w * 0.09, y, brand_col, size * 1.1, "center", cv.w * 0.82)
        d.rounded_rectangle([cx - cv.w * 0.14, y + 22 * u, cx + cv.w * 0.14, y + 22 * u + 14 * u], radius=7 * u, fill=rgba(p["accent"]))
        if tagline:
            f2, l2, s2, h2 = fit_block(tagline, kind, False, cv.w * 0.8, cv.h * 0.12, 42 * u, 22 * u, 1.2)
            draw_lines(cv, l2, f2, cv.w * 0.10, y + 56 * u, look.text, s2 * 1.2, "center", cv.w * 0.8)
    elif variant == 2:  # Icon stack
        tile = cv.w * 0.40
        top = cv.h * 0.12
        d.rounded_rectangle([cx - tile / 2, top, cx + tile / 2, top + tile], radius=int(tile * 0.24), fill=rgba(p["surface"]))
        draw_icon(d, icon, cx, top + tile / 2, tile * 0.30, rgba(p["primary"]), rgba(p["accent"]))
        f, lines, size, h = fit_name(brand, kind, True, cv.w * 0.84, cv.h * 0.26, 110 * u, 60 * u, 44 * u, 1.1)
        y = top + tile + 54 * u
        y = draw_lines(cv, lines, f, cv.w * 0.08, y, brand_col, size * 1.1, "center", cv.w * 0.84)
        if tagline:
            f2, l2, s2, h2 = fit_block(tagline, kind, False, cv.w * 0.8, cv.h * 0.1, 40 * u, 22 * u, 1.2)
            draw_lines(cv, l2, f2, cv.w * 0.10, y + 14 * u, look.text, s2 * 1.2, "center", cv.w * 0.8)
    else:  # Monogram
        tile = cv.w * 0.36
        top = cv.h * 0.14
        d.rounded_rectangle([cx - tile / 2, top, cx + tile / 2, top + tile], radius=int(tile * 0.18), fill=rgba(p["primary"]))
        mono = _initials(brand)
        f = get_font(kind, True, int(tile * 0.52))
        d.text((cx, top + tile / 2), mono, font=f, fill=rgba(p["on_primary"]), anchor="mm")
        d.ellipse([cx + tile / 2 - 34 * u, top + tile - 34 * u, cx + tile / 2 + 10 * u, top + tile + 10 * u], fill=rgba(p["accent"]))
        f, lines, size, h = fit_name(brand, kind, True, cv.w * 0.84, cv.h * 0.26, 104 * u, 60 * u, 42 * u, 1.1)
        y = top + tile + 70 * u
        y = draw_lines(cv, lines, f, cv.w * 0.08, y, brand_col, size * 1.1, "center", cv.w * 0.84)
        if tagline:
            f2, l2, s2, h2 = fit_block(tagline, kind, False, cv.w * 0.8, cv.h * 0.1, 40 * u, 22 * u, 1.2)
            draw_lines(cv, l2, f2, cv.w * 0.10, y + 14 * u, look.text, s2 * 1.2, "center", cv.w * 0.8)
    return cv.finish()


def render_logo_variants(project: dict, scale: float = 0.4) -> list[Image.Image]:
    return [render_logo(project, v, scale) for v in range(len(O.LOGO_VARIANTS))]


# ---------------------------------------------------------------- entry points
def render_pages(project: dict, scale: float = 1.0) -> list[Image.Image]:
    """Render a whole project. scale 1.0 = export size; use 0.3-0.5 for previews."""
    if project["type"] == "presentation":
        if not project["slides"]:
            return []
        base = O.FORMATS[project["options"]["format"]]
        size = (max(40, int(base[0] * scale)), max(40, int(base[1] * scale)))
        look = Look(project)
        return [render_slide(project, i, size=size, look=look) for i in range(len(project["slides"]))]
    if project["type"] == "document":
        return render_document(project, scale)
    return [render_logo(project, None, scale)]


def to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def to_jpeg_bytes(img: Image.Image, quality: int = 82) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=quality)
    return buf.getvalue()


def pages_to_pdf(images: list[Image.Image]) -> bytes:
    if not images:
        raise ValueError("Nothing to export yet - add a slide or section first.")
    rgb = [im.convert("RGB") for im in images]
    buf = io.BytesIO()
    rgb[0].save(buf, "PDF", save_all=True, append_images=rgb[1:], resolution=150.0)
    return buf.getvalue()
