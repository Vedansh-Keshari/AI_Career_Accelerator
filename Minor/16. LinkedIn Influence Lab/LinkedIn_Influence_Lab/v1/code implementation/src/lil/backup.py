"""Per-phase backups: every finished phase is zipped into backups/ so nothing is ever lost."""
from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path

from . import paths, store

ALLOWED_PREFIXES = ("phases/", "data/inputs/profile.json", "data/state/")


def _unique(base: Path) -> Path:
    p, n = base, 1
    while p.exists():
        p = base.with_name(f"{base.stem}_{n}{base.suffix}")
        n += 1
    return p


def _add_tree(z: zipfile.ZipFile, root: Path, rel_to: Path) -> int:
    n = 0
    for f in root.rglob("*"):
        if f.is_file():
            z.write(f, f.relative_to(rel_to).as_posix())
            n += 1
    return n


def backup_phase(key: str, tag: str = "") -> Path:
    info = paths.phase_info(key)
    home = paths.home()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{info['folder']}__{stamp}" + (f"__{tag}" if tag else "") + ".zip"
    target = _unique(paths.backups_dir() / name)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        count = _add_tree(z, paths.phase_dir(key), home)
        prof = paths.inputs_dir() / "profile.json"  # never plugins.json: it can hold API keys
        if prof.exists():
            z.write(prof, "data/inputs/profile.json")
        z.writestr("MANIFEST.json", json.dumps({"phase": key, "folder": info["folder"], "created": stamp, "tag": tag, "files": count}))
    store.log(f"backup created: {target.name}")
    _prune(info["folder"])
    return target


def _prune(folder: str, keep: int = 12) -> None:
    files = sorted(paths.backups_dir().glob(f"{folder}__*.zip"))
    for old in files[:-keep]:
        old.unlink(missing_ok=True)


def backup_snapshot() -> Path:
    home = paths.home()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = _unique(paths.backups_dir() / f"FULL_SNAPSHOT__{stamp}.zip")
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for sub in ("phases", "deliverables", "data/state"):
            if (home / sub).exists():
                _add_tree(z, home / sub, home)
        prof = paths.inputs_dir() / "profile.json"
        if prof.exists():
            z.write(prof, "data/inputs/profile.json")
    return target


def list_backups() -> list[dict]:
    out = []
    for f in sorted(paths.backups_dir().glob("*.zip"), reverse=True):
        out.append({"file": f.name, "kb": round(f.stat().st_size / 1024, 1),
                    "created": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")})
    return out


def restore(name: str) -> list[str]:
    """Restore a backup zip over the working folders (current state is backed up first)."""
    src = paths.backups_dir() / Path(name).name
    if not src.exists():
        raise FileNotFoundError(name)
    home = paths.home().resolve()
    with zipfile.ZipFile(src) as z:
        manifest = json.loads(z.read("MANIFEST.json")) if "MANIFEST.json" in z.namelist() else {}
        if manifest.get("phase"):
            backup_phase(manifest["phase"], tag="before_restore")
        restored = []
        for member in z.namelist():
            if member == "MANIFEST.json" or not member.startswith(ALLOWED_PREFIXES):
                continue
            dest = (home / member).resolve()
            if home not in dest.parents:  # zip-slip guard
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(member))
            restored.append(member)
    store.log(f"restored backup {src.name} ({len(restored)} files)")
    return restored
