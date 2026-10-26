"""Drawing engine: slides, documents and logos (Pillow). Public API re-exported here."""
from .base import (
    DOC_SIZE,
    LOGO_SIZE,
    POST_SIZE,
    Canvas,
    Look,
    contrast,
    fit_block,
    get_font,
    mix,
    wrap,
)
from .documents import render_document
from .free import fit_element_text, render_background
from .logos import pick_icon, render_logo, render_logo_variants
from .output import pages_to_pdf, render_pages, to_jpeg_bytes, to_png_bytes
from .slides import render_slide, resolve_layout

__all__ = [
    "DOC_SIZE", "LOGO_SIZE", "POST_SIZE", "Canvas", "Look", "contrast", "fit_block", "get_font", "mix", "wrap",
    "render_document", "fit_element_text", "render_background", "pick_icon", "render_logo", "render_logo_variants", "pages_to_pdf", "render_pages",
    "to_jpeg_bytes", "to_png_bytes", "render_slide", "resolve_layout",
]
