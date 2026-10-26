"""Project model (plain dicts so they save as JSON) and storage."""
from __future__ import annotations

import copy
import json
import os
import re
import time
import uuid
from pathlib import Path

from . import options as O
from .paths import studio_home

DEFAULT_OPTIONS = {
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


def blank_project(ptype: str, title: str = "Untitled") -> dict:
    if ptype not in O.PROJECT_TYPES:
        raise ValueError(f"Unknown project type: {ptype}")
    project = {
        "id": new_id(),
        "type": ptype,
        "title": title,
        "prompt": "",
        "options": dict(DEFAULT_OPTIONS),
        "tune": {"boldness": 0, "text_scale": 1.0},
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
            {"title": title, "body": "Add your subtitle", "layout": "auto", "image": ""},
            {"title": "Your first point", "body": "- Add a detail\n- Add another", "layout": "auto", "image": ""},
        ]
    elif ptype == "document":
        project["doc"]["sections"] = [{"heading": "Introduction", "body": "Start writing here."}]
    else:
        project["logo"]["brand"] = title
    return project


def clean_project(project: dict) -> dict:
    """Fill gaps and clamp values so a project from any source is safe to render."""
    base = blank_project(project.get("type", "presentation"), project.get("title", "Untitled"))
    out = copy.deepcopy(base)
    for key in ("id", "title", "prompt", "created", "updated", "history", "pushes"):
        if key in project:
            out[key] = project[key]
    out["options"].update({k: v for k, v in project.get("options", {}).items() if k in DEFAULT_OPTIONS})
    opts = out["options"]
    if opts["style"] not in O.STYLE_DEFS:
        opts["style"] = DEFAULT_OPTIONS["style"]
    if opts["color"] not in O.PALETTES:
        opts["color"] = DEFAULT_OPTIONS["color"]
    if opts["format"] not in O.FORMATS:
        opts["format"] = DEFAULT_OPTIONS["format"]
    if opts["length"] not in O.LENGTHS:
        opts["length"] = DEFAULT_OPTIONS["length"]
    tune = project.get("tune", {})
    out["tune"]["boldness"] = int(max(0, min(3, tune.get("boldness", 0))))
    out["tune"]["text_scale"] = float(max(0.7, min(1.6, tune.get("text_scale", 1.0))))
    if "slides" in project:
        out["slides"] = [
            {
                "title": str(s.get("title", "")),
                "body": str(s.get("body", "")),
                "layout": s.get("layout", "auto") if s.get("layout", "auto") in ("auto", "title", "bullets", "statement", "cta") else "auto",
                "image": str(s.get("image", "")),
            }
            for s in project["slides"]
        ][:60]
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
    s = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return s or "design"


class Store:
    """Saves each project as one JSON file in ~/.canvas_studio/projects."""

    def __init__(self, home: Path | None = None):
        self.home = Path(home) if home else studio_home()
        self.dir = self.home / "projects"
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.home / "uploads").mkdir(parents=True, exist_ok=True)

    def _path(self, pid: str) -> Path:
        if not re.fullmatch(r"p_[0-9a-f]{10}", pid):
            raise KeyError(pid)
        return self.dir / f"{pid}.json"

    def save(self, project: dict) -> dict:
        project = clean_project(project)
        tmp = self._path(project["id"]).with_suffix(".tmp")
        tmp.write_text(json.dumps(project, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self._path(project["id"]))
        return project

    def get(self, pid: str) -> dict:
        path = self._path(pid)
        if not path.exists():
            raise KeyError(pid)
        return clean_project(json.loads(path.read_text(encoding="utf-8")))

    def delete(self, pid: str) -> None:
        path = self._path(pid)
        if path.exists():
            path.unlink()

    def list(self) -> list[dict]:
        items = []
        for p in self.dir.glob("p_*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            items.append({
                "id": data.get("id"), "type": data.get("type"), "title": data.get("title"),
                "updated": data.get("updated", 0), "pushed": bool(data.get("pushes")),
            })
        return sorted(items, key=lambda x: x["updated"], reverse=True)

    def upload_path(self, name: str) -> Path:
        return self.home / "uploads" / name

    def save_upload(self, data: bytes, ext: str) -> str:
        ext = ext.lower().lstrip(".")
        if ext not in ("png", "jpg", "jpeg", "webp", "gif"):
            raise ValueError("Only png, jpg, webp or gif images can be added.")
        name = uuid.uuid4().hex[:12] + "." + ext
        self.upload_path(name).write_bytes(data)
        return str(self.upload_path(name))
