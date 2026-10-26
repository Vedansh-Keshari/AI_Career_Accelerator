"""Locating the shared folder, the user's data folder and the Canva config."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SHARED_DIR = Path(__file__).resolve().parent.parent
FONT_DIR = SHARED_DIR / "assets" / "fonts"
DATA_DIR = SHARED_DIR / "data"


def find_shared(start: Path) -> Path:
    """Find the shared folder from an app folder (used by web/ and desktop/).

    Looks at $CANVA_SHARED, then ./shared, ../shared and ../../shared.
    """
    candidates = []
    env = os.environ.get("CANVA_SHARED")
    if env:
        candidates.append(Path(env))
    start = Path(start).resolve()
    for base in (start, start.parent, start.parent.parent):
        candidates.append(base / "shared")
    for c in candidates:
        if (c / "studio" / "__init__.py").exists():
            return c.resolve()
    raise SystemExit(
        "Could not find the 'shared' folder.\n"
        "Put it next to this app's folder (canva-clone/shared, canva-clone/web) "
        "or set the CANVA_SHARED environment variable to its path."
    )


def studio_home() -> Path:
    """Where projects, uploads and sign-in tokens are stored."""
    home = Path(os.environ.get("CANVA_STUDIO_HOME", Path.home() / ".canvas_studio"))
    (home / "projects").mkdir(parents=True, exist_ok=True)
    (home / "uploads").mkdir(parents=True, exist_ok=True)
    return home


CANVA_AUTHORIZE_URL = "https://www.canva.com/api/oauth/authorize"
CANVA_API_BASE = "https://api.canva.com/rest/v1"
CANVA_TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"
DEFAULT_SCOPES = (
    "design:meta:read design:content:read design:content:write "
    "asset:read asset:write profile:read"
)
DEMO_PORT = 8765


def load_config(app: str, secrets=None, settings=None) -> dict:
    """Load Canva settings. `app` is 'web' or 'desktop'.

    Order: environment variables, then shared/config.json. With no client id the
    app runs against the built-in demo Canva (see mock_canva.py).
    """
    raw: dict = {}
    cfg_file = SHARED_DIR / "config.json"
    if getattr(sys, "frozen", False) and not cfg_file.exists():  # packaged .exe: look for config.json beside it
        cfg_file = Path(sys.executable).resolve().parent / "config.json"
    if cfg_file.exists():
        try:
            raw = json.loads(cfg_file.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"shared/config.json is not valid JSON: {exc}")
    canva = dict(raw.get("canva", {}))
    saved = (settings.all() if settings else {}).get("canva", {})
    canva.update({k: v for k, v in saved.items() if v})
    client_id = os.environ.get("CANVA_CLIENT_ID") or canva.get("client_id", "")
    stored_secret = secrets.get("canva_client_secret") if secrets else None
    client_secret = os.environ.get("CANVA_CLIENT_SECRET") or stored_secret or canva.get("client_secret", "")
    defaults = {
        "web": "http://127.0.0.1:5000/oauth/callback",
        "desktop": "http://127.0.0.1:5001/oauth/callback",
    }
    redirect = (
        os.environ.get("CANVA_REDIRECT_URI")
        or canva.get(f"{app}_redirect_uri")
        or defaults[app]
    )
    placeholder = client_id.strip() in ("", "YOUR_CANVA_CLIENT_ID")
    cfg = {
        "app": app,
        "demo": placeholder,
        "client_id": "" if placeholder else client_id.strip(),
        "client_secret": "" if placeholder else client_secret.strip(),
        "redirect_uri": redirect,
        "scopes": canva.get("scopes", DEFAULT_SCOPES),
        "authorize_url": CANVA_AUTHORIZE_URL,
        "token_url": CANVA_TOKEN_URL,
        "api_base": CANVA_API_BASE,
    }
    if not placeholder and (not client_secret.strip() or client_secret.strip() == "YOUR_CANVA_CLIENT_SECRET"):
        raise SystemExit("shared/config.json has a client_id but no client_secret. Paste both from canva.com/developers, "
                         "or remove the client_id to use demo mode.")
    if placeholder:
        base = f"http://127.0.0.1:{DEMO_PORT}"
        cfg.update(
            client_id="demo-client",
            client_secret="demo-secret",
            authorize_url=f"{base}/api/oauth/authorize",
            token_url=f"{base}/rest/v1/oauth/token",
            api_base=f"{base}/rest/v1",
        )
    return cfg
