"""Option lists from the Canva AI notes plus palettes and style definitions."""
from __future__ import annotations

import colorsys
from typing import Any

AUDIENCES = ["Casual", "Professional", "Educational"]

STYLES = [
    "Minimalist", "Playful", "Organic", "Geometric", "Modular", "Elegant", "Bold",
    "Modern", "NeoDigital", "Professional", "Retro", "Scrapbook", "Watercolour",
]

LENGTHS: dict[str, tuple[int, int]] = {
    "Short and sharp (1 to 5 pages)": (3, 5),
    "Balanced (5 to 15 pages)": (6, 10),
    "Comprehensive (15+ pages)": (16, 18),
    "Decide for me": (6, 8),
}

THEMES = [
    "Architecture", "Art and design", "Beauty", "Business", "Career", "Community",
    "Education", "Engagement", "Environment", "Event", "Family and friends", "Fashion",
    "Finance", "Fitness", "Food", "Gaming", "Health", "Holiday", "Marketing", "Music",
    "Nature", "Party", "Photography", "Productivity", "Real estate", "Science",
    "Seasons", "Sport", "Technology", "Travel",
]

COLORS = ["Black", "White", "Pink", "Yellow", "Red", "Green", "Orange", "Blue",
          "Purple", "Gold", "Silver"]

FEATURES = ["None", "Animation", "Audio", "Video"]

# format name -> (width, height) in px for a full-size export
FORMATS: dict[str, tuple[int, int]] = {
    "Presentation (16:9)": (1920, 1080),
    "Presentation (4:3)": (1440, 1080),
    "Presentation (Mobile-First)": (1080, 1920),
}

DOC_TYPES = [
    "Blog post", "Pitch", "Summary", "Caption", "Outline", "Tweet", "Social post",
    "Email", "Description", "Letter", "Article", "Itinerary", "Strategy", "Story",
    "Script",
]
SHORT_DOC_TYPES = {"Caption", "Tweet", "Social post"}  # rendered as a square post

# font picker: label -> internal kind (see render/base.py FONT_FILES); "Style default" keeps the style's own font
FONTS = {"Style default": "auto", "Poppins": "sans", "DejaVu Serif": "serif", "DejaVu Sans": "dsans", "DejaVu Sans Mono": "mono"}

LOGO_ICONS = ["auto", "book", "cup", "leaf", "star", "bolt", "heart", "mountain"]
LOGO_VARIANTS = ["Badge", "Wordmark", "Icon stack", "Monogram"]

PROJECT_TYPES = ["presentation", "document", "logo"]

# bg = page background, surface = soft panels, primary = main brand colour,
# accent = highlight, ink = text on light, on_primary = text on primary
PALETTES: dict[str, dict[str, str]] = {
    "Black":  dict(bg="#F2F2F2", surface="#DADADA", primary="#141414", accent="#FFC857", ink="#141414", on_primary="#FFFFFF"),
    "White":  dict(bg="#FFFFFF", surface="#EEF1F5", primary="#2B3A55", accent="#7C9CBF", ink="#1E2A3D", on_primary="#FFFFFF"),
    "Pink":   dict(bg="#FFF1F5", surface="#FFD6E3", primary="#D6336C", accent="#FF8FB1", ink="#4A1730", on_primary="#FFFFFF"),
    "Yellow": dict(bg="#FFF9DB", surface="#FFEC99", primary="#F2B705", accent="#E8590C", ink="#3D3200", on_primary="#3D3200"),
    "Red":    dict(bg="#FFF0F0", surface="#FFC9C9", primary="#C92A2A", accent="#FF6B6B", ink="#3B0A0A", on_primary="#FFFFFF"),
    "Green":  dict(bg="#EFF9F0", surface="#C3E8C9", primary="#2F8F4E", accent="#8BD17C", ink="#10331C", on_primary="#FFFFFF"),
    "Orange": dict(bg="#FFF4E6", surface="#FFD8A8", primary="#E8590C", accent="#FFA94D", ink="#3F1D05", on_primary="#FFFFFF"),
    "Blue":   dict(bg="#EDF4FF", surface="#C5DBFF", primary="#1C6DD0", accent="#4DABF7", ink="#0B2545", on_primary="#FFFFFF"),
    "Purple": dict(bg="#F6F0FF", surface="#DCC8FF", primary="#6D3FC9", accent="#B197FC", ink="#25104A", on_primary="#FFFFFF"),
    "Gold":   dict(bg="#FBF6E6", surface="#EAD9A0", primary="#B8860B", accent="#E6C65C", ink="#3A2C05", on_primary="#FFFFFF"),
    "Silver": dict(bg="#F4F5F7", surface="#D5D9DF", primary="#6B7482", accent="#AEB6C2", ink="#232830", on_primary="#FFFFFF"),
}

# font: sans | serif ; mode: light | dark | primary (page background) ;
# decor: name of the decoration painter ; box: content area as fractions of the page
STYLE_DEFS: dict[str, dict[str, Any]] = {
    "Minimalist":   dict(font="sans",  mode="light",   decor="thin_line",    box=(0.10, 0.14, 0.90, 0.86), bold=False),
    "Playful":      dict(font="sans",  mode="light",   decor="confetti",     box=(0.09, 0.13, 0.91, 0.87), bold=True),
    "Organic":      dict(font="serif", mode="light",   decor="blobs",        box=(0.12, 0.15, 0.88, 0.85), bold=False),
    "Geometric":    dict(font="sans",  mode="light",   decor="geometric",    box=(0.10, 0.14, 0.78, 0.86), bold=True),
    "Modular":      dict(font="sans",  mode="light",   decor="modular",      box=(0.08, 0.13, 0.70, 0.87), bold=True),
    "Elegant":      dict(font="serif", mode="light",   decor="double_border", box=(0.14, 0.17, 0.86, 0.83), bold=False),
    "Bold":         dict(font="sans",  mode="primary", decor="heavy_block",  box=(0.08, 0.12, 0.92, 0.80), bold=True),
    "Modern":       dict(font="sans",  mode="light",   decor="split",        box=(0.36, 0.13, 0.93, 0.87), bold=False),
    "NeoDigital":   dict(font="sans",  mode="dark",    decor="neon_grid",    box=(0.09, 0.14, 0.91, 0.86), bold=True),
    "Professional": dict(font="sans",  mode="light",   decor="header_bar",   box=(0.08, 0.24, 0.92, 0.90), bold=False),
    "Retro":        dict(font="serif", mode="light",   decor="stripes",      box=(0.09, 0.12, 0.91, 0.66), bold=True),
    "Scrapbook":    dict(font="sans",  mode="light",   decor="tape",         box=(0.13, 0.18, 0.87, 0.82), bold=False),
    "Watercolour":  dict(font="serif", mode="light",   decor="watercolor",   box=(0.12, 0.15, 0.88, 0.85), bold=False),
}


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_to_hex(rgb) -> str:
    return "#%02X%02X%02X" % tuple(int(max(0, min(255, c))) for c in rgb)


def boost(hex_color: str, level: int) -> str:
    """Make a colour more vivid (level 0 = unchanged, 3 = very vivid)."""
    if level <= 0:
        return hex_color
    r, g, b = (c / 255 for c in hex_to_rgb(hex_color))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    s = min(1.0, s + 0.12 * level + (0.1 if s > 0.15 else 0))
    v = min(1.0, v + 0.03 * level) if v > 0.35 else v
    return rgb_to_hex([c * 255 for c in colorsys.hsv_to_rgb(h, s, v)])


def _tint(hex_color: str, t: float) -> str:
    """Blend a colour toward white (t=0 unchanged, t=1 white)."""
    return rgb_to_hex([c + (255 - c) * t for c in hex_to_rgb(hex_color)])


def _shade(hex_color: str, t: float) -> str:
    """Blend a colour toward black."""
    return rgb_to_hex([c * (1 - t) for c in hex_to_rgb(hex_color)])


def _luminance(hex_color: str) -> float:
    r, g, b = (c / 255 for c in hex_to_rgb(hex_color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def brand_palette(primary: str, accent: str) -> dict:
    """Build a full palette from two brand colours (used for the 'Brand' colour)."""
    return dict(
        bg=_tint(primary, 0.93), surface=_tint(primary, 0.78), primary=primary, accent=accent,
        ink=_shade(primary, 0.78), on_primary="#FFFFFF" if _luminance(primary) < 0.6 else _shade(primary, 0.8),
    )


def valid_hex(value: object) -> bool:
    return isinstance(value, str) and len(value) == 7 and value[0] == "#" and all(c in "0123456789abcdefABCDEF" for c in value[1:])


def palette_for(color: str, boldness: int = 0, brand: dict | None = None) -> dict:
    if color == "Brand" and brand and valid_hex(brand.get("primary")) and valid_hex(brand.get("accent")):
        base = brand_palette(brand["primary"], brand["accent"])
    else:
        base = dict(PALETTES.get(color, PALETTES["Blue"]))
    if boldness:
        for key in ("primary", "accent"):
            base[key] = boost(base[key], boldness)
        if boldness >= 2:
            base["surface"] = boost(base["surface"], boldness - 1)
    return base


def option_lists() -> dict:
    return {
        "audiences": AUDIENCES, "styles": STYLES, "lengths": list(LENGTHS),
        "themes": THEMES, "colors": COLORS, "features": FEATURES,
        "formats": list(FORMATS), "doc_types": DOC_TYPES, "logo_icons": LOGO_ICONS,
        "logo_variants": LOGO_VARIANTS, "palettes": PALETTES, "fonts": list(FONTS), "font_map": FONTS,
    }
