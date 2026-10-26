"""Canvas Studio - website launcher. Run:  python app.py   then open http://127.0.0.1:5000

The server itself lives in the shared folder (shared/studio/webapp.py) so the desktop app uses the same one.
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


sys.path.insert(0, str(_find_shared(HERE)))

from studio.webapp import create_app, run_web  # noqa: E402, F401  (create_app is re-exported for tests)

if __name__ == "__main__":
    run_web()
