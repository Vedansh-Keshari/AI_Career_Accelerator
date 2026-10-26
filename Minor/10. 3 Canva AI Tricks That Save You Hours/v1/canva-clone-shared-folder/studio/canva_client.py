"""Canva Connect API client (OAuth 2.0 Authorization Code + PKCE).

Sign-in happens on Canva's own page, in the browser, so this code never sees the
user's Canva email or password - it only receives an authorization code and then
tokens. The client secret stays on the machine running the app.
"""
from __future__ import annotations

import base64
import hashlib
import http.server
import json
import os
import secrets
import threading
import time
import urllib.parse
from pathlib import Path

import requests

from .paths import studio_home


class CanvaError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class NotSignedIn(CanvaError):
    pass


def make_pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(72)[:96]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


class TokenStore:
    """Keeps tokens in ~/.canvas_studio/tokens_<app>.json (one file per app)."""

    def __init__(self, app: str, home: Path | None = None):
        self.path = (Path(home) if home else studio_home()) / f"tokens_{app}.json"

    def load(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def save(self, data: dict) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, self.path)

    def clear(self) -> None:
        try:
            self.path.unlink()
        except OSError:
            pass


class CanvaClient:
    def __init__(self, cfg: dict, home: Path | None = None, sleep=time.sleep, timeout: int = 60):
        self.cfg = cfg
        self.tokens = TokenStore(cfg["app"], home)
        self.sleep = sleep
        self.timeout = timeout
        self.http = requests.Session()

    # ------------------------------------------------------------ sign-in
    @property
    def demo(self) -> bool:
        return bool(self.cfg.get("demo"))

    def authorize_url(self, state: str, challenge: str) -> str:
        params = {
            "code_challenge": challenge,
            "code_challenge_method": "s256",
            "scope": self.cfg["scopes"],
            "response_type": "code",
            "client_id": self.cfg["client_id"],
            "state": state,
            "redirect_uri": self.cfg["redirect_uri"],
        }
        return self.cfg["authorize_url"] + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)

    def _token_request(self, form: dict) -> dict:
        try:
            resp = self.http.post(
                self.cfg["token_url"], data=form,
                auth=(self.cfg["client_id"], self.cfg["client_secret"]), timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise CanvaError(f"Could not reach Canva: {exc}") from exc
        if resp.status_code != 200:
            raise CanvaError(_error_text(resp, "Canva refused the sign-in"), resp.status_code)
        data = resp.json()
        data["expires_at"] = time.time() + int(data.get("expires_in", 14400))
        data["api_base"] = self.cfg["api_base"]
        data["client_id"] = self.cfg["client_id"]
        return data

    def exchange_code(self, code: str, verifier: str) -> dict:
        data = self._token_request({
            "grant_type": "authorization_code", "code": code,
            "code_verifier": verifier, "redirect_uri": self.cfg["redirect_uri"],
        })
        self.tokens.save(data)
        return data

    def _refresh(self, saved: dict) -> dict:
        if not saved.get("refresh_token"):
            self.tokens.clear()
            raise NotSignedIn("Your Canva session ended. Sign in again.")
        try:
            data = self._token_request({"grant_type": "refresh_token", "refresh_token": saved["refresh_token"]})
        except CanvaError as exc:
            self.tokens.clear()
            raise NotSignedIn("Your Canva session ended. Sign in again.") from exc
        self.tokens.save(data)
        return data

    def _saved(self) -> dict:
        saved = self.tokens.load()
        if not saved or saved.get("api_base") != self.cfg["api_base"] or saved.get("client_id") != self.cfg["client_id"]:
            return {}
        return saved

    def is_signed_in(self) -> bool:
        return bool(self._saved().get("access_token"))

    def access_token(self) -> str:
        saved = self._saved()
        if not saved.get("access_token"):
            raise NotSignedIn("Sign in to Canva first.")
        if saved.get("expires_at", 0) - 60 < time.time():
            saved = self._refresh(saved)
        return saved["access_token"]

    def sign_out(self) -> None:
        self.tokens.clear()

    # ------------------------------------------------------------ requests
    def _request(self, method: str, path: str, _retried: bool = False, **kwargs) -> dict:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token()}"
        try:
            resp = self.http.request(method, self.cfg["api_base"] + path, headers=headers, timeout=self.timeout, **kwargs)
        except requests.RequestException as exc:
            raise CanvaError(f"Could not reach Canva: {exc}") from exc
        if resp.status_code == 401 and not _retried:
            self._refresh(self._saved())
            return self._request(method, path, _retried=True, headers=headers, **kwargs)
        if resp.status_code == 401:
            self.tokens.clear()
            raise NotSignedIn("Canva rejected the saved sign-in. Sign in again.")
        if resp.status_code == 429:
            raise CanvaError("Canva says you are going too fast. Wait a minute and try again.", 429)
        if resp.status_code >= 400:
            raise CanvaError(_error_text(resp, "Canva returned an error"), resp.status_code)
        return resp.json() if resp.content else {}

    def _poll(self, path: str, tries: int = 90, delay: float = 1.0) -> dict:
        for _ in range(tries):
            job = self._request("GET", path).get("job", {})
            status = job.get("status")
            if status == "success":
                return job
            if status == "failed":
                err = job.get("error") or {}
                raise CanvaError(f"Canva could not finish the job: {err.get('message') or err.get('code') or 'unknown error'}")
            self.sleep(delay)
        raise CanvaError("Canva took too long to finish. Check your Canva home page in a minute.")

    # ------------------------------------------------------------ API calls
    def profile(self) -> dict:
        try:
            data = self._request("GET", "/users/me/profile").get("profile", {})
        except NotSignedIn:
            raise
        except CanvaError:
            return {"display_name": ""}
        return {"display_name": data.get("display_name", "")}

    def list_designs(self, limit: int = 12) -> list[dict]:
        data = self._request("GET", "/designs", params={"limit": limit, "sort_by": "modified_descending"})
        return [_design_summary(d) for d in data.get("items", [])]

    def upload_asset(self, data: bytes, name: str) -> str:
        meta = json.dumps({"name_base64": base64.b64encode(name.encode("utf-8")).decode("ascii")})
        job = self._request("POST", "/asset-uploads", data=data,
                            headers={"Content-Type": "application/octet-stream", "Asset-Upload-Metadata": meta}).get("job", {})
        if job.get("status") != "success":
            job = self._poll(f"/asset-uploads/{job['id']}")
        return job["asset"]["id"]

    def create_design(self, title: str, asset_id: str, width: int, height: int) -> dict:
        body = {"type": "type_and_asset", "title": title[:255] or "Untitled", "asset_id": asset_id,
                "design_type": {"type": "custom", "width": width, "height": height}}
        return _design_summary(self._request("POST", "/designs", json=body).get("design", {}))

    def import_file(self, data: bytes, title: str, mime_type: str = "application/pdf") -> dict:
        meta = json.dumps({"title_base64": base64.b64encode(title[:50].encode("utf-8")).decode("ascii"), "mime_type": mime_type})
        job = self._request("POST", "/imports", data=data,
                            headers={"Content-Type": "application/octet-stream", "Import-Metadata": meta}).get("job", {})
        if job.get("status") != "success":
            job = self._poll(f"/imports/{job['id']}")
        designs = (job.get("result") or {}).get("designs") or []
        if not designs:
            raise CanvaError("Canva finished the import but returned no design.")
        return _design_summary(designs[0])


def _design_summary(d: dict) -> dict:
    urls = d.get("urls") or {}
    return {
        "id": d.get("id", ""), "title": d.get("title") or "Untitled",
        "edit_url": urls.get("edit_url", ""), "view_url": urls.get("view_url", ""),
        "thumbnail": (d.get("thumbnail") or {}).get("url", ""),
        "updated_at": d.get("updated_at", 0),
    }


def _error_text(resp: requests.Response, fallback: str) -> str:
    try:
        body = resp.json()
        msg = body.get("message") or body.get("error_description") or body.get("error")
        if msg:
            return f"{fallback}: {msg}"
    except ValueError:
        pass
    return f"{fallback} (HTTP {resp.status_code})"


# ---------------------------------------------------------------- pushing a project
def push_project(client: CanvaClient, project: dict) -> dict:
    """Send a project to the signed-in Canva account as a new design."""
    from . import options as O
    from .render import pages_to_pdf, render_pages, to_png_bytes

    title = project["title"] or "Untitled"
    images = render_pages(project, 1.0)
    if not images:
        raise CanvaError("Nothing to push yet - add a slide or section first.")
    single = project["type"] == "logo" or (
        project["type"] == "document" and project["doc"]["doc_type"] in O.SHORT_DOC_TYPES)
    if single:
        img = images[0]
        asset_id = client.upload_asset(to_png_bytes(img), f"{title}.png")
        design = client.create_design(title, asset_id, img.width, img.height)
        how = "image design"
    else:
        design = client.import_file(pages_to_pdf(images), title, "application/pdf")
        how = f"{len(images)}-page design"
    return {**design, "kind": how, "pages": len(images), "pushed_at": time.time()}


# ---------------------------------------------------------------- desktop sign-in helper
def wait_for_callback(redirect_uri: str, expected_state: str, timeout: int = 240, cancel: "threading.Event | None" = None) -> str:
    """Listen on the redirect URI's port for Canva's redirect and return the code.

    Used by the desktop app. Raises CanvaError on denial, mismatch or timeout.
    """
    parsed = urllib.parse.urlparse(redirect_uri)
    result: dict = {}
    done = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            url = urllib.parse.urlparse(self.path)
            if url.path != parsed.path:
                self.send_response(404)
                self.end_headers()
                return
            q = dict(urllib.parse.parse_qsl(url.query))
            result.update(q)
            body = ("<html><body style='font-family:sans-serif;padding:3rem'>"
                    "<h2>Signed in</h2><p>You can close this tab and go back to Canvas Studio.</p>"
                    "</body></html>").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            done.set()

        def log_message(self, *args):
            pass

    http.server.HTTPServer.allow_reuse_address = True
    server = http.server.HTTPServer((parsed.hostname or "127.0.0.1", parsed.port or 80), Handler)
    server.timeout = 1
    deadline = time.time() + timeout
    try:
        while not done.is_set() and time.time() < deadline and not (cancel and cancel.is_set()):
            server.handle_request()
    finally:
        server.server_close()
    if cancel and cancel.is_set() and not done.is_set():
        raise CanvaError("Sign-in cancelled.")
    if not done.is_set():
        raise CanvaError("Sign-in timed out. Try again.")
    if result.get("error"):
        raise CanvaError("Canva sign-in was cancelled or denied.")
    if result.get("state") != expected_state:
        raise CanvaError("Sign-in could not be verified (state mismatch). Try again.")
    if not result.get("code"):
        raise CanvaError("Canva did not send back a sign-in code.")
    return result["code"]
