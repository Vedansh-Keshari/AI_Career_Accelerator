"""Slide background decorations (one painter per style)."""
from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw, ImageFilter

from .base import Canvas, Look, rgba


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
    d, u = cv.d, cv.u
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
    d, u = cv.d, cv.u
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


