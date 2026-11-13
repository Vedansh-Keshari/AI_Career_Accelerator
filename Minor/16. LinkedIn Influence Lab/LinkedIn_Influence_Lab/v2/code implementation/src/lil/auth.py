"""Admin passcode handling (salted PBKDF2). Pure Python, no Streamlit.

Honest scope: this gates the *interface* (e.g. the Folder map). It is not a substitute for operating-system
file permissions: anyone who can open the project folder on disk can still read the files.

Set LIL_ADMIN_PASSCODE in the environment to manage the passcode outside the app (hosted deployments).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets

from . import paths, store

MIN_LEN = 8
ITERATIONS = 200_000


def _file():
    d = paths.app_root() / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d / "admin.json"


def _hash(passcode: str, salt: bytes, iterations: int = ITERATIONS) -> str:
    return base64.b64encode(hashlib.pbkdf2_hmac("sha256", passcode.encode("utf-8"), salt, iterations)).decode()


def env_managed() -> bool:
    return bool(os.environ.get("LIL_ADMIN_PASSCODE"))


def is_configured() -> bool:
    return env_managed() or _file().exists()


def set_passcode(passcode: str) -> None:
    if env_managed():
        raise PermissionError("The passcode is managed by the LIL_ADMIN_PASSCODE environment variable.")
    if len(passcode) < MIN_LEN:
        raise ValueError(f"Use at least {MIN_LEN} characters.")
    salt = secrets.token_bytes(16)
    store.write_json(_file(), {"salt": base64.b64encode(salt).decode(), "iterations": ITERATIONS, "hash": _hash(passcode, salt)})


def verify(passcode: str) -> bool:
    if env_managed():
        return hmac.compare_digest(passcode.encode(), os.environ["LIL_ADMIN_PASSCODE"].encode())
    rec = store.read_json(_file())
    if not rec:
        return False
    salt = base64.b64decode(rec["salt"])
    return hmac.compare_digest(_hash(passcode, salt, int(rec.get("iterations", ITERATIONS))), rec["hash"])
