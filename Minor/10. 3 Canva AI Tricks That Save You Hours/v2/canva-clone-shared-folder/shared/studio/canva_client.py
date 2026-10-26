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
import secrets
import threading
import time
import urllib.parse
from pathlib import Path

import requests

from .secrets_store import SecretStore


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
    """Keeps sign-in tokens in the encrypted secret store (one entry per app)."""

    def __init__(self, app: str, home: Path | None = None, secrets: SecretStore | None = None):
        self.name = f"tokens_{app}"
        self.secrets = secrets or SecretStore(home)

    def load(self) -> dict:
        try:
            return json.loads(self.secrets.get(self.name) or "{}")
        except json.JSONDecodeError:
            return {}

    def save(self, data: dict) -> None:
        self.secrets.set(self.name, json.dumps(data))

    def clear(self) -> None:
        self.secrets.delete(self.name)


class CanvaClient:
    def __init__(self, cfg: dict, home: Path | None = None, sleep=time.sleep, timeout: int = 60, secret_store: SecretStore | None = None):
        self.cfg = cfg
        self.tokens = TokenStore(cfg["app"], home, secret_store)
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
    RETRY_STATUS = (429, 500, 502, 503, 504)

    def _send(self, method: str, path: str, headers: dict, kwargs: dict) -> requests.Response:
        """One HTTP call with retries for temporary failures.

        GETs retry on network errors and 429/5xx (backoff 0.5s, 1s, 2s). Other calls are not repeated
        automatically (so a design is never created twice), except after a 429 where Canva did nothing.
        """
        attempts = 4 if method == "GET" else 2
        for attempt in range(attempts):
            last = attempt == attempts - 1
            try:
                resp = self.http.request(method, self.cfg["api_base"] + path, headers=headers, timeout=self.timeout, **kwargs)
            except requests.RequestException as exc:
                if method != "GET" or last:
                    raise CanvaError(f"Could not reach Canva: {exc}") from exc
                self.sleep(0.5 * 2 ** attempt)
                continue
            retry = resp.status_code == 429 if method != "GET" else resp.status_code in self.RETRY_STATUS
            if retry and not last:
                try:
                    wait = min(10.0, float(resp.headers.get("Retry-After", 0)))
                except ValueError:
                    wait = 0.0
                self.sleep(wait or 0.5 * 2 ** attempt)
                continue
            return resp
        raise CanvaError("Could not reach Canva.")  # pragma: no cover

    def _request(self, method: str, path: str, _retried: bool = False, **kwargs) -> dict:
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = f"Bearer {self.access_token()}"
        resp = self._send(method, path, headers, kwargs)
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

    def _poll(self, path: str, tries: int = 90, delay: float = 1.0, progress=None) -> dict:
        for n in range(tries):
            job = self._request("GET", path).get("job", {})
            status = job.get("status")
            if status == "success":
                return job
            if status == "failed":
                err = job.get("error") or {}
                raise CanvaError(f"Canva could not finish the job: {err.get('message') or err.get('code') or 'unknown error'}")
            if progress:
                progress("Waiting for Canva to finish", n + 1)
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

    def upload_asset(self, data: bytes, name: str, progress=None) -> str:
        meta = json.dumps({"name_base64": base64.b64encode(name.encode("utf-8")).decode("ascii")})
        job = self._request("POST", "/asset-uploads", data=data,
                            headers={"Content-Type": "application/octet-stream", "Asset-Upload-Metadata": meta}).get("job", {})
        if job.get("status") != "success":
            job = self._poll(f"/asset-uploads/{job['id']}", progress=progress)
        return job["asset"]["id"]

    def create_design(self, title: str, asset_id: str, width: int, height: int) -> dict:
        body = {"type": "type_and_asset", "title": title[:255] or "Untitled", "asset_id": asset_id,
                "design_type": {"type": "custom", "width": width, "height": height}}
        return _design_summary(self._request("POST", "/designs", json=body).get("design", {}))

    def import_file(self, data: bytes, title: str, mime_type: str = "application/pdf", progress=None) -> dict:
        meta = json.dumps({"title_base64": base64.b64encode(title[:50].encode("utf-8")).decode("ascii"), "mime_type": mime_type})
        job = self._request("POST", "/imports", data=data,
                            headers={"Content-Type": "application/octet-stream", "Import-Metadata": meta}).get("job", {})
        if job.get("status") != "success":
            job = self._poll(f"/imports/{job['id']}", progress=progress)
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
def push_project(client: CanvaClient, project: dict, progress=None) -> dict:
    """Send a project to the signed-in Canva account as a new design.

    Decks go as an editable .pptx and documents as an editable .docx (text stays text in Canva).
    Logos and short posts go as an image design. If Canva rejects the editable file, or the Office
    libraries are missing, it falls back to a PDF of page images and says so in the result.
    progress(stage, step) is called as the push moves along (used for the progress bar).
    """
    from . import options as O
    from .render import pages_to_pdf, render_pages, to_png_bytes

    def tick(stage: str, step: int = 0) -> None:
        if progress:
            progress(stage, step)

    title = project["title"] or "Untitled"
    tick("Preparing your pages")
    single = project["type"] == "logo" or (project["type"] == "document" and project["doc"]["doc_type"] in O.SHORT_DOC_TYPES)
    if single:
        images = render_pages(project, 1.0)
        if not images:
            raise CanvaError("Nothing to push yet - add a slide or section first.")
        img = images[0]
        tick("Uploading the image to Canva")
        asset_id = client.upload_asset(to_png_bytes(img), f"{title}.png", progress)
        tick("Creating the design")
        design = client.create_design(title, asset_id, img.width, img.height)
        return {**design, "kind": "image design", "pages": 1, "editable": False, "pushed_at": time.time()}

    if project["type"] == "presentation" and not project["slides"]:
        raise CanvaError("Nothing to push yet - add a slide or section first.")
    if project["type"] == "document" and not project["doc"]["sections"]:
        raise CanvaError("Nothing to push yet - add a slide or section first.")
    count = len(project["slides"]) if project["type"] == "presentation" else len(render_pages(project, 0.1))
    note = ""
    try:
        from . import office
        tick("Building an editable file")
        if project["type"] == "presentation":
            data, mime, label = office.presentation_to_pptx(project), office.PPTX_MIME, f"{count}-slide editable design"
        else:
            data, mime, label = office.document_to_docx(project), office.DOCX_MIME, f"{count}-page editable document"
        tick("Uploading to Canva")
        design = client.import_file(data, title, mime, progress)
        return {**design, "kind": label, "pages": count, "editable": True, "pushed_at": time.time()}
    except ImportError:
        note = "Office libraries are not installed, so pages were sent as images."
    except CanvaError as exc:
        if exc.status not in (400, 415, 422):
            raise
        note = f"Canva did not accept the editable file ({exc}); pages were sent as images instead."
    tick("Sending page images instead")
    pdf = pages_to_pdf(render_pages(project, 1.0))
    design = client.import_file(pdf, title, "application/pdf", progress)
    return {**design, "kind": f"{count}-page design (images)", "pages": count, "editable": False, "note": note, "pushed_at": time.time()}


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
            body = (b"<html><body style='font-family:sans-serif;padding:3rem'>"
                    b"<h2>Signed in</h2><p>You can close this tab and go back to Canvas Studio.</p>"
                    b"</body></html>")
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
