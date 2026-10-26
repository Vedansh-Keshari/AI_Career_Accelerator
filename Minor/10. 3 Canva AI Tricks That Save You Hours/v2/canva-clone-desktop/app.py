"""Canvas Studio - desktop launcher. Run:  python app.py

Shows the same interface as the website in its own window. The app and the website share one
engine in the shared folder (shared/studio), so they always look and behave the same.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _find_shared(start: Path) -> Path:
    """Locate the shared folder: $CANVA_SHARED, ./shared, ../shared or ../../shared."""
    candidates = [Path(os.environ["CANVA_SHARED"])] if os.environ.get("CANVA_SHARED") else []
    candidates += [start / "shared", start.parent / "shared", start.parent.parent / "shared"]
    for c in candidates:
        if (c / "studio" / "__init__.py").exists():
            return c.resolve()
    raise SystemExit(
        "Could not find the 'shared' folder.\n"
        "Unzip the desktop app next to the shared folder (canva-clone/shared and canva-clone/desktop), "
        "or set CANVA_SHARED to its path."
    )


if not getattr(sys, "frozen", False):  # a packaged .exe already contains the engine
    sys.path.insert(0, str(_find_shared(HERE)))

from studio.desktop import run_desktop  # noqa: E402

if __name__ == "__main__":
    run_desktop()
