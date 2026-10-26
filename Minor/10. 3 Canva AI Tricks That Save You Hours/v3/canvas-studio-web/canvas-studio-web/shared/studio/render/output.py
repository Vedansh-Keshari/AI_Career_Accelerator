"""Entry points and file output helpers."""
from __future__ import annotations

import io

from PIL import Image

from .. import options as O
from .base import Look
from .documents import render_document
from .logos import render_logo
from .slides import render_slide


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

