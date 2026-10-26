"""Project model (plain dicts so they save as JSON) and storage."""
from __future__ import annotations

import copy
import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from . import options as O
from .paths import studio_home

SCHEMA_VERSION = 2
WINDOWS_RESERVED = {"con", "prn", "aux", "nul", *{f"com{i}" for i in range(1, 10)}, *{f"lpt{i}" for i in range(1, 10)}}

DEFAULT_OPTIONS: dict[str, str] = {
    "audience": "Casual",
    "style": "Modern",
    "length": "Balanced (5 to 15 pages)",
    "theme": "Productivity",
    "color": "Blue",
    "feature": "None",
    "format": "Presentation (16:9)",
}


def new_id() -> str:
    return "p_" + uuid.uuid4().hex[:10]


def now() -> float:
    return time.time()


def blank_project(ptype: str, title: str = "Untitled") -> dict[str, Any]:
    if ptype not in O.PROJECT_TYPES:
        raise ValueError(f"Unknown project type: {ptype}")
    project: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "rev": 0,
        "id": new_id(),
        "type": ptype,
        "title": title,
        "prompt": "",
        "options": dict(DEFAULT_OPTIONS),
        "tune": {"boldness": 0, "text_scale": 1.0, "font": "auto"},
        "slides": [],
        "doc": {"doc_type": "Blog post", "sections": []},
        "logo": {"brand": "", "tagline": "", "description": "", "icon": "auto", "variant": 0},
        "history": [],
        "pushes": [],
        "created": now(),
        "updated": now(),
    }
    if ptype == "presentation":
        project["slides"] = [
            {"title": title, "body": "Add your subtitle", "layout": "auto", "image": "", "free": False, "elements": []},
            {"title": "Your first point", "body": "- Add a detail\n- Add another", "layout": "auto", "image": "", "free": False, "elements": []},
        ]
    elif ptype == "document":
        project["doc"]["sections"] = [{"heading": "Introduction", "body": "Start writing here."}]
    else:
        project["logo"]["brand"] = title
    return project


ELEMENT_TYPES = ("text", "rect", "ellipse", "image")
COLOR_TOKENS = ("text", "heading", "accent", "primary", "on_primary", "surface", "bg", "ink")


def _num(value: object, lo: float, hi: float, default: float) -> float:
    try:
        v = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


def _color(value: object, default: str) -> str:
    if isinstance(value, str) and (value in COLOR_TOKENS or O.valid_hex(value)):
        return value
    return default


def clean_element(el: dict) -> dict | None:
    """Validate one free-layout element. Positions are fractions of the slide."""
    if not isinstance(el, dict) or el.get("type") not in ELEMENT_TYPES:
        return None
    out = {
        "id": str(el.get("id") or "e_" + uuid.uuid4().hex[:8])[:24],
        "type": el["type"],
        "x": _num(el.get("x"), -0.2, 1.0, 0.1), "y": _num(el.get("y"), -0.2, 1.0, 0.1),
        "w": _num(el.get("w"), 0.02, 1.4, 0.3), "h": _num(el.get("h"), 0.02, 1.4, 0.2),
    }
    if el["type"] == "text":
        out.update(
            text=str(el.get("text", ""))[:3000], size=_num(el.get("size"), 8, 400, 48), bold=bool(el.get("bold", False)),
            align=el.get("align") if el.get("align") in ("left", "center", "right") else "left",
            valign=el.get("valign") if el.get("valign") in ("top", "middle", "bottom") else "top",
            color=_color(el.get("color"), "text"), fill=_color(el.get("fill"), "") if el.get("fill") else "",
        )
    elif el["type"] in ("rect", "ellipse"):
        out.update(fill=_color(el.get("fill"), "accent"), opacity=_num(el.get("opacity"), 0.05, 1, 1), radius=_num(el.get("radius"), 0, 0.5, 0.0))
    else:
        out["image"] = str(el.get("image", ""))
    return out


def migrate(project: dict) -> dict:
    """Bring an older saved project up to SCHEMA_VERSION (never loses user content)."""
    version = int(project.get("schema_version", 1) or 1)
    if version < 2:  # v1 had no free-layout elements, rev counter or font choice
        for s in project.get("slides", []):
            s.setdefault("free", False)
            s.setdefault("elements", [])
        project.setdefault("rev", 0)
        project.setdefault("tune", {}).setdefault("font", "auto")
    project["schema_version"] = SCHEMA_VERSION
    return project


def clean_project(project: dict) -> dict:
    """Fill gaps and clamp values so a project from any source is safe to render."""
    project = migrate(dict(project))
    base = blank_project(project.get("type", "presentation"), project.get("title", "Untitled"))
    out = copy.deepcopy(base)
    for key in ("id", "title", "prompt", "created", "updated", "history", "pushes", "generated_by"):
        if key in project:
            out[key] = project[key]
    out["rev"] = int(project.get("rev", 0) or 0)
    brand = project.get("brand")
    if isinstance(brand, dict) and O.valid_hex(brand.get("primary")) and O.valid_hex(brand.get("accent")):
        out["brand"] = {"primary": brand["primary"], "accent": brand["accent"], "name": str(brand.get("name", ""))[:60]}
    out["options"].update({k: v for k, v in project.get("options", {}).items() if k in DEFAULT_OPTIONS})
    opts = out["options"]
    if opts["style"] not in O.STYLE_DEFS:
        opts["style"] = DEFAULT_OPTIONS["style"]
    if opts["color"] not in O.PALETTES and not (opts["color"] == "Brand" and "brand" in out):
        opts["color"] = DEFAULT_OPTIONS["color"]
    if opts["format"] not in O.FORMATS:
        opts["format"] = DEFAULT_OPTIONS["format"]
    if opts["length"] not in O.LENGTHS:
        opts["length"] = DEFAULT_OPTIONS["length"]
    tune = project.get("tune", {})
    out["tune"]["boldness"] = int(max(0, min(3, tune.get("boldness", 0))))
    out["tune"]["text_scale"] = float(max(0.7, min(1.6, tune.get("text_scale", 1.0))))
    out["tune"]["font"] = tune.get("font") if tune.get("font") in ("auto", *O.FONTS.values()) else "auto"
    if "slides" in project:
        slides = []
        for s in project["slides"][:60]:
            layout = s.get("layout", "auto")
            elements = [e for e in (clean_element(x) for x in (s.get("elements") or [])[:40]) if e]
            slides.append({
                "title": str(s.get("title", "")), "body": str(s.get("body", "")),
                "layout": layout if layout in ("auto", "title", "bullets", "statement", "cta") else "auto",
                "image": str(s.get("image", "")), "free": bool(s.get("free", False)) and True, "elements": elements,
            })
        out["slides"] = slides
    doc = project.get("doc", {})
    out["doc"]["doc_type"] = doc.get("doc_type", out["doc"]["doc_type"])
    if out["doc"]["doc_type"] not in O.DOC_TYPES:
        out["doc"]["doc_type"] = "Blog post"
    if "sections" in doc:
        out["doc"]["sections"] = [
            {"heading": str(s.get("heading", "")), "body": str(s.get("body", ""))}
            for s in doc["sections"]
        ][:60]
    logo = project.get("logo", {})
    for key in ("brand", "tagline", "description"):
        if key in logo:
            out["logo"][key] = str(logo[key])
    if logo.get("icon") in O.LOGO_ICONS:
        out["logo"]["icon"] = logo["icon"]
    out["logo"]["variant"] = int(max(0, min(len(O.LOGO_VARIANTS) - 1, logo.get("variant", 0))))
    out["updated"] = now()
    return out


def page_count(project: dict) -> int:
    if project["type"] == "presentation":
        return max(1, len(project["slides"]))
    if project["type"] == "logo":
        return 1
    from .render import render_pages  # local import: Pillow is only needed here
    return len(render_pages(project, scale=0.2))


def slug(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()[:60].strip("-")
    if not s or s in WINDOWS_RESERVED:  # "con", "nul"... cannot be file names on Windows
        return "design-" + s if s else "design"
    return s


class Conflict(Exception):
    """The project was changed elsewhere (for example in another tab) since it was loaded."""


def _replace_with_retry(tmp: Path, dest: Path, tries: int = 6) -> None:
    """os.replace can fail on Windows while antivirus or an indexer briefly holds the file."""
    for attempt in range(tries):
        try:
            os.replace(tmp, dest)
            return
        except PermissionError:
            if attempt == tries - 1:
                raise
            time.sleep(0.05 * (attempt + 1))


class Store:
    """Saves each project as one JSON file in ~/.canvas_studio/projects."""

    def __init__(self, home: Path | None = None):
        self.home = Path(home) if home else studio_home()
        self.dir = self.home / "projects"
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.home / "uploads").mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, pid: str) -> Path:
        if not re.fullmatch(r"p_[0-9a-f]{10}", pid):
            raise KeyError(pid)
        return self.dir / f"{pid}.json"

    def _read(self, pid: str) -> dict:
        path = self._path(pid)
        if not path.exists():
            raise KeyError(pid)
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def save(self, project: dict, expected_rev: int | None = None, bump: bool = True) -> dict:
        """Save a project. With expected_rev, refuse (Conflict) if the stored copy moved on.

        bump=False is for server-owned changes (push history) that must not invalidate an open editor.
        """
        project = clean_project(project)
        with self._lock:
            path = self._path(project["id"])
            if path.exists():
                try:
                    stored = int(json.loads(path.read_text(encoding="utf-8-sig")).get("rev", 0) or 0)
                except (ValueError, json.JSONDecodeError):
                    stored = 0
                if expected_rev is not None and stored != expected_rev:
                    raise Conflict(f"stored rev {stored}, expected {expected_rev}")
                project["rev"] = stored + 1 if bump else stored
            else:
                project["rev"] = max(1, project["rev"])
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(project, indent=2, ensure_ascii=False), encoding="utf-8")
            _replace_with_retry(tmp, path)
        return project

    def get(self, pid: str) -> dict:
        return clean_project(self._read(pid))

    def delete(self, pid: str) -> None:
        path = self._path(pid)
        if path.exists():
            path.unlink()

    def list(self) -> list[dict]:
        items = []
        for p in self.dir.glob("p_*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8-sig"))
            except (json.JSONDecodeError, OSError):
                continue
            items.append({
                "id": data.get("id"), "type": data.get("type"), "title": data.get("title"),
                "updated": data.get("updated", 0), "pushed": bool(data.get("pushes")),
            })
        return sorted(items, key=lambda x: x["updated"], reverse=True)

    def upload_path(self, name: str) -> Path:
        return self.home / "uploads" / name

    def is_upload(self, path: str) -> bool:
        """True only for files inside this store's uploads folder (case-insensitive on Windows)."""
        if not path:
            return False
        try:
            Path(os.path.realpath(path)).relative_to(os.path.realpath(self.home / "uploads"))
            return True
        except ValueError:
            return False

    def save_upload(self, data: bytes, ext: str) -> str:
        ext = ext.lower().lstrip(".")
        if ext not in ("png", "jpg", "jpeg", "webp", "gif"):
            raise ValueError("Only png, jpg, webp or gif images can be added.")
        name = uuid.uuid4().hex[:12] + "." + ext
        self.upload_path(name).write_bytes(data)
        return str(self.upload_path(name))

    def cleanup_uploads(self, max_age_days: float = 30) -> int:
        """Delete uploaded images no project uses and that are older than max_age_days."""
        used: set[str] = set()
        for p in self.dir.glob("p_*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8-sig"))
            except (json.JSONDecodeError, OSError):
                continue
            for s in data.get("slides", []):
                used.add(os.path.normcase(os.path.realpath(s.get("image", "") or "-")))
                for e in s.get("elements", []) or []:
                    used.add(os.path.normcase(os.path.realpath(e.get("image", "") or "-")))
        removed = 0
        cutoff = time.time() - max_age_days * 86400
        for f in (self.home / "uploads").glob("*"):
            try:
                if os.path.normcase(os.path.realpath(f)) not in used and f.stat().st_mtime < cutoff:
                    f.unlink()
                    removed += 1
            except OSError:
                continue
        return removed
