"""Backups: plain zip files with a checksummed manifest. No database is used.

Two kinds, both stored in <workspace>/backups/:
  * phase backup    <phase folder>__<timestamp>[__tag].zip   (that phase's working files + your profile)
  * full snapshot   FULL_SNAPSHOT__<timestamp>[__tag].zip    (phases, deliverables, hub data, status ledger, profile)
API keys (plugins.json), the admin passcode and the backups folder itself are never included.
"""
from __future__ import annotations

import hashlib
import io
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

from . import paths, store

ALLOWED_PREFIXES = ("phases/", "deliverables/", "data/hub/", "data/state/", "data/inputs/profile.json")
SNAPSHOT_TREES = ("phases", "deliverables", "data/hub", "data/state")
PHASE_BACKUPS_KEPT = 12


def _unique(base: Path) -> Path:
    p, n = base, 1
    while p.exists():
        p = base.with_name(f"{base.stem}_{n}{base.suffix}")
        n += 1
    return p


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _collect(home: Path, trees) -> list[tuple[Path, str]]:
    out = []
    for t in trees:
        root = home / t
        if root.is_file():
            out.append((root, t))
        elif root.exists():
            out += [(f, f.relative_to(home).as_posix()) for f in sorted(root.rglob("*")) if f.is_file()]
    return out


def _write(target: Path, kind: str, files: list[tuple[Path, str]], extra: dict) -> Path:
    entries = []
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for src, arc in files:
            data = src.read_bytes()
            z.writestr(arc, data)
            entries.append({"path": arc, "bytes": len(data), "sha256": _sha(data)})
        manifest = {"type": kind, "created": datetime.now().isoformat(timespec="seconds"), "workspace": paths.workspace(),
                    "count": len(entries), "files": entries, **extra}
        z.writestr("MANIFEST.json", json.dumps(manifest, indent=2))
    return target


def backup_phase(key: str, tag: str = "") -> Path:
    info = paths.phase_info(key)
    home = paths.home()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = _unique(paths.backups_dir() / (f"{info['folder']}__{stamp}" + (f"__{tag}" if tag else "") + ".zip"))
    files = _collect(home, [f"phases/{info['folder']}", "data/inputs/profile.json"])  # never plugins.json (API keys)
    _write(target, "phase", files, {"phase": key, "folder": info["folder"], "tag": tag})
    store.log(f"backup created: {target.name}")
    old = sorted(paths.backups_dir().glob(f"{info['folder']}__*.zip"))
    for f in old[:-PHASE_BACKUPS_KEPT]:
        f.unlink(missing_ok=True)
    return target


def backup_snapshot(tag: str = "") -> Path:
    home = paths.home()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = _unique(paths.backups_dir() / (f"FULL_SNAPSHOT__{stamp}" + (f"__{tag}" if tag else "") + ".zip"))
    files = _collect(home, list(SNAPSHOT_TREES) + ["data/inputs/profile.json"])
    _write(target, "snapshot", files, {"tag": tag})
    store.log(f"snapshot created: {target.name}")
    return target


def _manifest(path: Path) -> dict:
    try:
        with zipfile.ZipFile(path) as z:
            return json.loads(z.read("MANIFEST.json"))
    except (KeyError, zipfile.BadZipFile, json.JSONDecodeError):
        return {}


def list_backups() -> list[dict]:
    out = []
    for f in sorted(paths.backups_dir().glob("*.zip"), reverse=True):
        m = _manifest(f)
        out.append({"file": f.name, "type": {"phase": "Phase backup", "snapshot": "Full snapshot"}.get(m.get("type"), "Unknown"),
                    "scope": m.get("folder") or ("all phases + deliverables" if m.get("type") == "snapshot" else ""),
                    "tag": m.get("tag", ""), "files": m.get("count", 0), "kb": round(f.stat().st_size / 1024, 1),
                    "created": m.get("created", datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="seconds"))})
    return out


def describe(name: str) -> dict:
    path = paths.backups_dir() / Path(name).name
    m = _manifest(path)
    if not m:
        raise FileNotFoundError(f"{name} is missing or is not a valid backup")
    top: dict[str, int] = {}
    for e in m["files"]:
        key = "/".join(PurePosixPath(e["path"]).parts[:2]) if e["path"].startswith(("phases/", "deliverables/")) else e["path"]
        top[key] = top.get(key, 0) + 1
    return {**{k: v for k, v in m.items() if k != "files"}, "groups": top, "files": m["files"]}


def verify(name: str) -> tuple[bool, list[str]]:
    """Re-read every file and compare its SHA-256 with the manifest."""
    path = paths.backups_dir() / Path(name).name
    problems = []
    try:
        with zipfile.ZipFile(path) as z:
            m = json.loads(z.read("MANIFEST.json"))
            names = set(z.namelist())
            for e in m["files"]:
                if e["path"] not in names:
                    problems.append(f"missing: {e['path']}")
                elif _sha(z.read(e["path"])) != e["sha256"]:
                    problems.append(f"changed: {e['path']}")
    except (KeyError, FileNotFoundError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        return False, [f"unreadable backup ({exc.__class__.__name__})"]
    return not problems, problems


def _safe_dest(home: Path, member: str) -> Path | None:
    p = PurePosixPath(member)
    if p.is_absolute() or ".." in p.parts or not member.startswith(ALLOWED_PREFIXES):
        return None
    dest = (home / member).resolve()
    return dest if home.resolve() in dest.parents else None


def restore(name: str) -> dict:
    """Put a backup back. Order: verify -> safety snapshot of the current state -> clear the covered folders -> extract."""
    path = paths.backups_dir() / Path(name).name
    if not path.exists():
        raise FileNotFoundError(name)
    ok, problems = verify(path.name)
    if not ok:
        raise ValueError("Backup failed its integrity check: " + "; ".join(problems[:3]))
    m = _manifest(path)
    safety = backup_snapshot(tag="before_restore")
    home = paths.home()
    covered = SNAPSHOT_TREES if m.get("type") == "snapshot" else (f"phases/{m.get('folder')}",)
    removed = 0
    for t in covered:
        d = home / t
        if d.exists():
            removed += sum(1 for f in d.rglob("*") if f.is_file())
            shutil.rmtree(d)
    restored = []
    with zipfile.ZipFile(path) as z:
        for member in z.namelist():
            if member == "MANIFEST.json":
                continue
            dest = _safe_dest(home, member)
            if dest is None:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(member))
            restored.append(member)
    store.log(f"restored {path.name}: {len(restored)} files restored, {removed} replaced; safety copy {safety.name}")
    return {"restored": restored, "replaced": removed, "safety_backup": safety.name, "type": m.get("type")}


def import_backup(data: bytes, filename: str) -> str:
    """Accept a backup zip made elsewhere. It must carry a manifest, pass the checksum test and contain only allowed paths."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            m = json.loads(z.read("MANIFEST.json"))
            for e in m["files"]:
                if _safe_dest(paths.home(), e["path"]) is None:
                    raise ValueError(f"not allowed: {e['path']}")
                if _sha(z.read(e["path"])) != e["sha256"]:
                    raise ValueError(f"checksum mismatch: {e['path']}")
    except (KeyError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        raise ValueError("That file is not a LinkedIn Influence Lab backup.") from exc
    stem = Path(filename).stem[:60].replace(" ", "_")
    target = _unique(paths.backups_dir() / f"IMPORTED__{stem}.zip")
    target.write_bytes(data)
    return target.name
