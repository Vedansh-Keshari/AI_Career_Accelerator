"""Canvas Studio - website launcher. Run:  python app.py   then open http://127.0.0.1:5000

The server itself lives in the shared folder (shared/studio/webapp.py) so the desktop app uses the same one.
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
        "Unzip the web app next to the shared folder (canva-clone/shared and canva-clone/web), "
        "or set CANVA_SHARED to its path."
    )


sys.path.insert(0, str(_find_shared(HERE)))

from studio.webapp import create_app, run_web  # noqa: E402, F401  (create_app is re-exported for tests)

if __name__ == "__main__":
    run_web()
