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
    """Locate the engine: the ./shared folder inside this package (always preferred), then $CANVA_SHARED."""
    candidates = [start / "shared"]
    if os.environ.get("CANVA_SHARED"):
        candidates.append(Path(os.environ["CANVA_SHARED"]))
    for c in candidates:
        if (c / "studio" / "__init__.py").exists():
            return c.resolve()
    raise SystemExit(
        "The 'shared' folder is missing from this program folder.\n"
        "Extract the WHOLE zip again (the 'shared' folder must stay inside this folder, next to app.py)."
    )


if not getattr(sys, "frozen", False):  # a packaged .exe already contains the engine
    sys.path.insert(0, str(_find_shared(HERE)))

from studio.desktop import run_desktop  # noqa: E402

if __name__ == "__main__":
    run_desktop()
