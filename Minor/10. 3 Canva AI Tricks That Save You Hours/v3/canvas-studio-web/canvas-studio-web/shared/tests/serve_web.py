"""Starts the website server (used by the browser test; the same server both packages run)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from studio.webapp import run_web  # noqa: E402

if __name__ == "__main__":
    run_web()
