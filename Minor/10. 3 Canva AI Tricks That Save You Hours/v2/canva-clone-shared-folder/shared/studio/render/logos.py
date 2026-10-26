"""Logo layouts and icons."""
from __future__ import annotations

import math

from PIL import Image, ImageDraw

from .. import options as O
from .base import (
    LOGO_SIZE,
    Canvas,
    Look,
    contrast,
    draw_lines,
    fit_block,
    fit_name,
    get_font,
    rgba,
)

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


