"""Encrypted storage for tokens and API keys.

Values live in one encrypted file (Fernet). The encryption key is kept in the operating
system's credential store (Windows Credential Manager, macOS Keychain, Secret Service) when
available; otherwise it falls back to a key file readable only by you. The key is small, so it
fits Windows' credential size limit, which whole token sets would not.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from .models import _replace_with_retry
from .paths import studio_home

SERVICE = "CanvasStudio"
KEY_NAME = "master-key"


class SecretStore:
    def __init__(self, home: Path | None = None, use_keyring: bool | None = None):
        self.home = Path(home) if home else studio_home()
        self.home.mkdir(parents=True, exist_ok=True)
        self.path = self.home / "secrets.enc"
        self.keyfile = self.home / "secrets.key"
        if use_keyring is None:
            use_keyring = not os.environ.get("CANVAS_NO_KEYRING")
        self.use_keyring = use_keyring
        self.protected_by = "file"
        self._lock = threading.Lock()
        self._fernet = self._load_fernet()

    # -- key handling
    def _load_fernet(self):
        try:
            from cryptography.fernet import Fernet
        except ImportError:  # pragma: no cover - cryptography is in requirements
            self.protected_by = "none"
            return None
        key = None
        if self.use_keyring:
            try:
                import keyring
                key = keyring.get_password(SERVICE, KEY_NAME)
                if not key:
                    key = Fernet.generate_key().decode()
                    keyring.set_password(SERVICE, KEY_NAME, key)
                self.protected_by = "keyring"
            except Exception:  # noqa: BLE001 - no usable OS credential store
                key = None
        if not key:
            self.protected_by = "file"
            if self.keyfile.exists():
                key = self.keyfile.read_text().strip()
            else:
                key = Fernet.generate_key().decode()
                self.keyfile.write_text(key)
                try:
                    os.chmod(self.keyfile, 0o600)
                except OSError:
                    pass
        return Fernet(key.encode())

    # -- data
    def _read_all(self) -> dict:
        if not self.path.exists():
            return {}
        raw = self.path.read_bytes()
        try:
            if self._fernet:
                raw = self._fernet.decrypt(raw)
            return json.loads(raw.decode("utf-8"))
        except Exception:  # noqa: BLE001 - wrong key or damaged file: treat as empty, never crash the app
            return {}

    def _write_all(self, data: dict) -> None:
        raw = json.dumps(data).encode("utf-8")
        if self._fernet:
            raw = self._fernet.encrypt(raw)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_bytes(raw)
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        _replace_with_retry(tmp, self.path)

    def get(self, name: str) -> str | None:
        with self._lock:
            return self._read_all().get(name)

    def set(self, name: str, value: str) -> None:
        with self._lock:
            data = self._read_all()
            data[name] = value
            self._write_all(data)

    def delete(self, name: str) -> None:
        with self._lock:
            data = self._read_all()
            if name in data:
                del data[name]
                self._write_all(data)


class Settings:
    """Non-secret settings (brand kit, Canva client id, AI model) in settings.json."""

    def __init__(self, home: Path | None = None):
        self.home = Path(home) if home else studio_home()
        self.path = self.home / "settings.json"
        self._lock = threading.Lock()

    def all(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return {}

    def update(self, changes: dict) -> dict:
        with self._lock:
            data = self.all()
            data.update(changes)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            _replace_with_retry(tmp, self.path)
            return data
