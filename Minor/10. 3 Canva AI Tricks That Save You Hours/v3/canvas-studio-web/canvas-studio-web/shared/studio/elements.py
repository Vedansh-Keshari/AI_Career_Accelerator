"""Turning a slide's automatic layout into free-layout elements (so it can be dragged and resized)."""
from __future__ import annotations

import uuid

from . import options as O
from .models import clean_element
from .render import resolve_layout


def _id() -> str:
    return "e_" + uuid.uuid4().hex[:8]


def default_elements(project: dict, index: int) -> list[dict]:
    """Elements that look like the slide's current automatic layout."""
    slide = project["slides"][index]
    style = O.STYLE_DEFS[project["options"]["style"]]
    bx0, by0, bx1, by1 = style["box"]
    layout = resolve_layout(project["slides"], index)
    portrait = O.FORMATS[project["options"]["format"]][1] > O.FORMATS[project["options"]["format"]][0]
    title, body = slide["title"].strip(), slide["body"].strip()
    has_img = bool(slide.get("image"))
    out: list[dict] = []
    x0, w = bx0, bx1 - bx0
    y0, h = by0, by1 - by0
    if has_img:
        if portrait:
            out.append({"type": "image", "x": x0, "y": y0 + h * 0.62, "w": w, "h": h * 0.38, "image": slide["image"]})
            h = h * 0.58
        else:
            out.append({"type": "image", "x": x0 + w * 0.6, "y": y0, "w": w * 0.4, "h": h, "image": slide["image"]})
            w = w * 0.55
    if layout in ("title", "cta"):
        center = layout == "cta"
        align = "center" if center else "left"
        out.append({"type": "text", "x": x0, "y": y0 + h * 0.12, "w": w, "h": h * 0.40, "text": title, "size": 132 if layout == "title" else 120,
                    "bold": True, "align": align, "valign": "bottom", "color": "heading"})
        if body:
            out.append({"type": "text", "x": x0, "y": y0 + h * 0.58, "w": w, "h": h * 0.24, "text": body, "size": 52, "align": align, "valign": "top", "color": "text"})
        out.append({"type": "rect", "x": x0 + (w - 0.12) / 2 if center else x0, "y": y0 + h * 0.86, "w": 0.12, "h": 0.012, "fill": "accent", "radius": 0.5})
    elif layout == "statement":
        if title:
            out.append({"type": "text", "x": x0, "y": y0, "w": w, "h": h * 0.14, "text": title, "size": 54, "bold": True, "color": "heading"})
        out.append({"type": "text", "x": x0, "y": y0 + h * 0.2, "w": w, "h": h * 0.78, "text": body or title, "size": 92, "bold": style["bold"], "valign": "middle", "color": "text"})
    else:
        out.append({"type": "text", "x": x0, "y": y0, "w": w, "h": h * 0.2, "text": title, "size": 86, "bold": True, "valign": "middle", "color": "heading"})
        out.append({"type": "text", "x": x0, "y": y0 + h * 0.26, "w": w, "h": h * 0.74, "text": body, "size": 62, "color": "text"})
    return [e for e in (clean_element({**el, "id": _id()}) for el in out) if e]


def blank_element(kind: str) -> dict:
    presets = {
        "text": {"type": "text", "x": 0.30, "y": 0.40, "w": 0.40, "h": 0.14, "text": "New text", "size": 60, "color": "text"},
        "rect": {"type": "rect", "x": 0.35, "y": 0.35, "w": 0.30, "h": 0.25, "fill": "accent", "radius": 0.08},
        "ellipse": {"type": "ellipse", "x": 0.38, "y": 0.30, "w": 0.24, "h": 0.36, "fill": "primary"},
        "image": {"type": "image", "x": 0.30, "y": 0.25, "w": 0.40, "h": 0.50, "image": ""},
    }
    el = clean_element({**presets[kind], "id": _id()})
    if el is None:
        raise ValueError(f"Unknown element type: {kind}")
    return el
