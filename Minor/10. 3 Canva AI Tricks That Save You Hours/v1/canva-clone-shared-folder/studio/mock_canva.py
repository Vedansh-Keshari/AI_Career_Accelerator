"""A tiny stand-in for Canva, used when no real Canva keys are configured.

It speaks the same endpoints the app uses (OAuth with PKCE, asset uploads, design
creation, design imports) so the whole flow can be tried and tested without a Canva
developer account. It is NOT Canva: nothing here reaches canva.com.
"""
from __future__ import annotations

import base64
import hashlib
import html
import http.server
import json
import secrets
import socket
import threading
import time
import urllib.parse

from .paths import DEMO_PORT


def _b64url_sha256(text: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(text.encode("ascii")).digest()).rstrip(b"=").decode("ascii")


class MockCanva:
    def __init__(self, port: int = DEMO_PORT, host: str = "127.0.0.1"):
        self.host, self.port = host, port
        self.codes: dict[str, dict] = {}
        self.access: dict[str, dict] = {}
        self.refresh: dict[str, dict] = {}
        self.jobs: dict[str, dict] = {}
        self.files: dict[str, tuple[bytes, str]] = {}
        self.assets: dict[str, dict] = {}
        self.designs: dict[str, dict] = {}
        self.lock = threading.Lock()
        self.server: http.server.ThreadingHTTPServer | None = None
        self.token_lifetime = 14400
        self.slow_jobs = 1  # polls that answer "in_progress" before success

    @property
    def base(self) -> str:
        return f"http://{self.host}:{self.port}"

    # -------------------------------------------------- lifecycle
    def start(self) -> "MockCanva":
        mock = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def _send(self, code, body=b"", ctype="application/json", extra=None):
                if isinstance(body, (dict, list)):
                    body = json.dumps(body).encode()
                elif isinstance(body, str):
                    body = body.encode()
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                for k, v in (extra or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(body)

            def _body(self) -> bytes:
                n = int(self.headers.get("Content-Length") or 0)
                return self.rfile.read(n) if n else b""

            def do_GET(self):  # noqa: N802
                mock.handle(self, "GET")

            def do_POST(self):  # noqa: N802
                mock.handle(self, "POST")

        self.server = http.server.ThreadingHTTPServer((self.host, self.port), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None

    # -------------------------------------------------- routing
    def handle(self, h, method: str):
        url = urllib.parse.urlparse(h.path)
        path, query = url.path, dict(urllib.parse.parse_qsl(url.query))
        try:
            if path == "/" and method == "GET":
                return h._send(200, "<h3>Demo Canva server</h3><p>This is a local stand-in for Canva.</p>", "text/html")
            if path == "/api/oauth/authorize":
                return self.authorize(h, method, query)
            if path == "/rest/v1/oauth/token" and method == "POST":
                return self.token(h)
            if path.startswith("/d/") and method == "GET":
                return self.viewer(h, path[3:])
            if path.startswith("/files/") and method == "GET":
                return self.file(h, path[7:])
            if path.startswith("/rest/v1/"):
                return self.api(h, method, path[len("/rest/v1"):], query)
            h._send(404, {"message": "not found"})
        except Exception as exc:  # pragma: no cover - defensive
            h._send(500, {"message": f"mock error: {exc}"})

    # -------------------------------------------------- OAuth
    def authorize(self, h, method: str, query: dict):
        if method == "POST":
            form = dict(urllib.parse.parse_qsl(h._body().decode()))
            q = {k: form.get(k, "") for k in ("client_id", "redirect_uri", "state", "code_challenge", "scope")}
            if form.get("action") == "cancel":
                loc = q["redirect_uri"] + "?" + urllib.parse.urlencode({"error": "access_denied", "state": q["state"]})
                return h._send(302, b"", "text/plain", {"Location": loc})
            email = form.get("email", "").strip()
            if "@" not in email or "." not in email.split("@")[-1]:
                return h._send(200, self._login_page(q, "Enter a valid email address."), "text/html; charset=utf-8")
            code = secrets.token_urlsafe(24)
            with self.lock:
                self.codes[code] = {"challenge": q["code_challenge"], "email": email,
                                    "redirect_uri": q["redirect_uri"], "client_id": q["client_id"], "scope": q["scope"]}
            loc = q["redirect_uri"] + "?" + urllib.parse.urlencode({"code": code, "state": q["state"]})
            return h._send(302, b"", "text/plain", {"Location": loc})
        needed = ("client_id", "redirect_uri", "state", "code_challenge", "response_type")
        missing = [k for k in needed if not query.get(k)]
        if missing:
            return h._send(400, f"Missing: {', '.join(missing)}", "text/plain")
        if query.get("code_challenge_method", "").lower() != "s256":
            return h._send(400, "code_challenge_method must be s256", "text/plain")
        h._send(200, self._login_page(query, ""), "text/html; charset=utf-8")

    def _login_page(self, q: dict, error: str) -> str:
        hidden = "".join(f'<input type="hidden" name="{k}" value="{html.escape(q.get(k, ""), quote=True)}">'
                         for k in ("client_id", "redirect_uri", "state", "code_challenge", "scope"))
        err = f'<p style="color:#b42318">{html.escape(error)}</p>' if error else ""
        return f"""<!doctype html><meta charset="utf-8"><title>Sign in to demo Canva</title>
<body style="font-family:system-ui,sans-serif;max-width:420px;margin:12vh auto;padding:0 20px">
<p style="background:#fff4d6;padding:10px 12px;border-radius:8px">Demo mode: this is a local stand-in for Canva's sign-in page. Nothing is sent to canva.com.</p>
<h2>Sign in with your email</h2>{err}
<form method="post">{hidden}
<input name="email" type="email" placeholder="you@example.com" autofocus required style="width:100%;padding:12px;font-size:16px;margin:8px 0">
<button name="action" value="allow" style="padding:12px 18px;font-size:16px">Continue and allow access</button>
<button name="action" value="cancel" style="padding:12px 18px;font-size:16px;margin-left:8px" formnovalidate>Cancel</button>
</form></body>"""

    def token(self, h):
        auth = h.headers.get("Authorization", "")
        if not auth.startswith("Basic "):
            return h._send(401, {"error": "invalid_client", "error_description": "Basic auth required"})
        form = dict(urllib.parse.parse_qsl(h._body().decode()))
        grant = form.get("grant_type")
        with self.lock:
            if grant == "authorization_code":
                info = self.codes.pop(form.get("code", ""), None)
                if not info:
                    return h._send(400, {"error": "invalid_grant", "error_description": "code is invalid or already used"})
                if not form.get("code_verifier") or _b64url_sha256(form["code_verifier"]) != info["challenge"]:
                    return h._send(400, {"error": "invalid_grant", "error_description": "PKCE verification failed"})
                if form.get("redirect_uri") != info["redirect_uri"]:
                    return h._send(400, {"error": "invalid_grant", "error_description": "redirect_uri mismatch"})
                user = {"email": info["email"], "scope": info["scope"]}
            elif grant == "refresh_token":
                user = self.refresh.pop(form.get("refresh_token", ""), None)
                if not user:
                    return h._send(400, {"error": "invalid_grant", "error_description": "refresh token is invalid"})
            else:
                return h._send(400, {"error": "unsupported_grant_type"})
            access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            self.access[access] = {**user, "expires": time.time() + self.token_lifetime}
            self.refresh[refresh] = user
        h._send(200, {"access_token": access, "refresh_token": refresh, "token_type": "Bearer",
                      "expires_in": self.token_lifetime, "scope": user["scope"]})

    # -------------------------------------------------- API
    def api(self, h, method: str, path: str, query: dict):
        auth = h.headers.get("Authorization", "")
        user = self.access.get(auth[7:]) if auth.startswith("Bearer ") else None
        if not user or user["expires"] < time.time():
            return h._send(401, {"code": "invalid_access_token", "message": "The access token is invalid or expired."})
        if path == "/users/me/profile" and method == "GET":
            return h._send(200, {"profile": {"display_name": user["email"].split("@")[0]}})
        if path == "/designs" and method == "GET":
            items = sorted(self.designs.values(), key=lambda d: -d["updated_at"])[: int(query.get("limit", 25))]
            return h._send(200, {"items": items})
        if path == "/designs" and method == "POST":
            return self.create_design(h)
        if path in ("/asset-uploads", "/imports") and method == "POST":
            return self.start_job(h, path)
        for prefix in ("/asset-uploads/", "/imports/"):
            if path.startswith(prefix) and method == "GET":
                return self.job_status(h, path[len(prefix):], prefix)
        h._send(404, {"message": f"Unknown endpoint {path}"})

    def start_job(self, h, path: str):
        data = h._body()
        if h.headers.get("Content-Type") != "application/octet-stream":
            return h._send(400, {"code": "unsupported_content_type", "message": "Use application/octet-stream"})
        if not data:
            return h._send(400, {"message": "Empty body"})
        job_id = secrets.token_hex(8)
        try:
            if path == "/asset-uploads":
                meta = json.loads(h.headers.get("Asset-Upload-Metadata", "{}"))
                name = base64.b64decode(meta["name_base64"]).decode("utf-8")
                mime = "image/png" if data[:4] == b"\x89PNG" else "image/jpeg"
                kind = "asset"
            else:
                meta = json.loads(h.headers.get("Import-Metadata", "{}"))
                name = base64.b64decode(meta["title_base64"]).decode("utf-8")
                mime = meta["mime_type"]
                if mime != "application/pdf" and not mime.startswith("application/vnd"):
                    return h._send(400, {"message": f"Unsupported mime_type {mime}"})
                kind = "import"
        except (KeyError, ValueError):
            return h._send(400, {"message": "Missing or invalid metadata header"})
        file_id = secrets.token_hex(8)
        with self.lock:
            self.files[file_id] = (data, mime)
            self.jobs[job_id] = {"kind": kind, "name": name, "file": file_id, "polls": 0}
        h._send(200, {"job": {"id": job_id, "status": "in_progress"}})

    def job_status(self, h, job_id: str, prefix: str):
        job = self.jobs.get(job_id)
        if not job:
            return h._send(404, {"message": "job not found"})
        job["polls"] += 1
        if job["polls"] <= self.slow_jobs:
            return h._send(200, {"job": {"id": job_id, "status": "in_progress"}})
        with self.lock:
            if job["kind"] == "asset":
                asset_id = "M" + job["file"]
                self.assets[asset_id] = {"id": asset_id, "name": job["name"], "file": job["file"]}
                return h._send(200, {"job": {"id": job_id, "status": "success", "asset": {"id": asset_id, "name": job["name"], "tags": []}}})
            if "design" not in job:
                job["design"] = self._new_design(job["name"], job["file"], pages_from=job["file"])
            return h._send(200, {"job": {"id": job_id, "status": "success", "result": {"type": "import", "designs": [job["design"]]}}})

    def _new_design(self, title: str, file_id: str, pages_from: str = "") -> dict:
        did = "D" + secrets.token_hex(6)
        design = {"id": did, "title": title, "file": file_id,
                  "urls": {"edit_url": f"{self.base}/d/{did}", "view_url": f"{self.base}/d/{did}"},
                  "created_at": int(time.time()), "updated_at": int(time.time())}
        self.designs[did] = design
        return design

    def create_design(self, h):
        try:
            body = json.loads(h._body() or b"{}")
        except ValueError:
            return h._send(400, {"message": "Invalid JSON"})
        asset_id = body.get("asset_id")
        if not body.get("design_type") and not asset_id:
            return h._send(400, {"message": "design_type or asset_id is required"})
        dt = body.get("design_type") or {}
        if dt.get("type") == "custom" and not (40 <= dt.get("width", 0) <= 8000 and 40 <= dt.get("height", 0) <= 8000):
            return h._send(400, {"message": "custom width and height must be between 40 and 8000"})
        file_id = ""
        if asset_id:
            asset = self.assets.get(asset_id)
            if not asset:
                return h._send(404, {"message": "asset not found"})
            file_id = asset["file"]
        with self.lock:
            design = self._new_design(body.get("title") or "Untitled", file_id)
        h._send(200, {"design": design})

    # -------------------------------------------------- viewer pages
    def viewer(self, h, design_id: str):
        design = self.designs.get(design_id)
        if not design:
            return h._send(404, "Design not found", "text/html")
        data, mime = self.files.get(design["file"], (b"", ""))
        if mime == "application/pdf":
            inner = f'<embed src="/files/{design["file"]}" type="application/pdf" style="width:100%;height:80vh">'
        elif mime.startswith("image/"):
            inner = f'<img src="/files/{design["file"]}" style="max-width:100%;max-height:80vh">'
        else:
            inner = "<p>Blank design</p>"
        page = (f"<!doctype html><meta charset='utf-8'><title>{html.escape(design['title'])}</title>"
                f"<body style='font-family:system-ui;padding:24px'><p style='background:#fff4d6;padding:8px 12px;border-radius:8px'>"
                f"Demo Canva - this is a local preview of the design that was pushed.</p><h2>{html.escape(design['title'])}</h2>{inner}</body>")
        h._send(200, page, "text/html; charset=utf-8")

    def file(self, h, file_id: str):
        data, mime = self.files.get(file_id, (b"", ""))
        if not data:
            return h._send(404, b"", "text/plain")
        h._send(200, data, mime)


_demo: MockCanva | None = None


def port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0


def ensure_demo_server(port: int = DEMO_PORT) -> MockCanva | None:
    """Start the demo Canva in a background thread (no-op if one is already running)."""
    global _demo
    if _demo is not None:
        return _demo
    if port_in_use(port):
        return None  # the other Canvas Studio app already runs it
    _demo = MockCanva(port).start()
    return _demo
