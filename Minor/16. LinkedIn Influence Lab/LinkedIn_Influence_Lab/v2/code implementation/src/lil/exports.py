"""In-memory zip downloads for the Deliverables page: one set at a time, or every set at once."""
from __future__ import annotations

import io
import zipfile
from datetime import datetime

from . import paths

SKIP_NAMES = {"README.txt", ".gitkeep"}


def set_files(key: str) -> list:
    folder = paths.deliverable_dir(key)
    return sorted(f for f in folder.rglob("*") if f.is_file() and f.name not in SKIP_NAMES)


def _note(label: str, files, root) -> str:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"LinkedIn Influence Lab - {label}", f"Exported {stamp}" + ("  (SAMPLE DATA workspace)" if paths.is_sample() else ""), "", "Files:"]
    return "\n".join(lines + [f"  {f.relative_to(root).as_posix()}" for f in files]) + "\n"


def zip_set(key: str) -> bytes:
    folder = paths.deliverable_dir(key)
    files = set_files(key)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, f"{folder.name}/{f.relative_to(folder).as_posix()}")
        z.writestr(f"{folder.name}/_CONTENTS.txt", _note(folder.name, files, folder))
    return buf.getvalue()


def zip_all() -> bytes:
    buf = io.BytesIO()
    total = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for key in paths.DELIVERABLES:
            folder = paths.deliverable_dir(key)
            for f in set_files(key):
                z.write(f, f"deliverables/{folder.name}/{f.relative_to(folder).as_posix()}")
                total += 1
        z.writestr("deliverables/_CONTENTS.txt", f"LinkedIn Influence Lab - all deliverable sets\n{total} files\n"
                   + ("SAMPLE DATA workspace\n" if paths.is_sample() else ""))
    return buf.getvalue()


def counts() -> dict:
    return {k: len(set_files(k)) for k in paths.DELIVERABLES}
