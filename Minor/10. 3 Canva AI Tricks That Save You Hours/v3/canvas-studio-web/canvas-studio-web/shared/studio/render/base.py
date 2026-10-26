"""Fonts, colours, canvas and text-fitting helpers."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .. import options as O
from ..paths import FONT_DIR

SS = 2  # supersampling factor
DOC_SIZE = (1240, 1754)  # A4 at 150 dpi
POST_SIZE = (1080, 1080)
LOGO_SIZE = (1000, 1000)

FONT_FILES = {
    ("sans", False): "Poppins-Regular.ttf",
    ("sans", True): "Poppins-Bold.ttf",
    ("serif", False): "DejaVuSerif.ttf",
    ("serif", True): "DejaVuSerif-Bold.ttf",
    ("dsans", False): "DejaVuSans.ttf",
    ("dsans", True): "DejaVuSans-Bold.ttf",
    ("mono", False): "DejaVuSansMono.ttf",
    ("mono", True): "DejaVuSansMono-Bold.ttf",
}


@lru_cache(maxsize=256)
def get_font(kind: str, bold: bool, size: int) -> Any:  # a FreeType font, or Pillow's built-in one if the file is missing
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
        self.pal = O.palette_for(opts["color"], tune["boldness"], project.get("brand"))
        self.text_scale = tune["text_scale"]
        picked = tune.get("font", "auto")
        self.kind = self.sdef["font"] if picked == "auto" else picked
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


def resolve_color(look: "Look", value: str) -> str:
    """Turn an element colour (a palette token such as 'accent', or a #hex) into a hex colour."""
    pal = look.pal
    table = {
        "text": look.text, "heading": look.heading, "accent": pal["accent"], "primary": pal["primary"],
        "on_primary": pal["on_primary"], "surface": pal["surface"], "bg": look.bg, "ink": pal["ink"],
    }
    return table.get(value, value if O.valid_hex(value) else look.text)


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
        return self.img.resize((self.W, self.H), Image.Resampling.LANCZOS)


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


