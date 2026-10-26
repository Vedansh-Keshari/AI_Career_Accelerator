"""Canvas Studio - website. Run:  python app.py   then open http://127.0.0.1:5000"""
from __future__ import annotations

import io
import os
import secrets
import sys
import zipfile
from collections import OrderedDict
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

from flask import Flask, Response, jsonify, redirect, request, send_file, send_from_directory, session  # noqa: E402
from PIL import Image  # noqa: E402

from studio import generator as G  # noqa: E402
from studio import models as M  # noqa: E402
from studio import options as O  # noqa: E402
from studio import render as R  # noqa: E402
from studio.canva_client import CanvaClient, CanvaError, NotSignedIn, make_pkce, push_project  # noqa: E402
from studio.mock_canva import ensure_demo_server  # noqa: E402
from studio.paths import FONT_DIR, load_config, studio_home  # noqa: E402

MAX_UPLOAD = 10 * 1024 * 1024


def create_app(config: dict | None = None, home: Path | None = None, client: CanvaClient | None = None) -> Flask:
    app = Flask(__name__, static_folder=str(HERE / "static"), static_url_path="/static")
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD + 1024 * 1024
    cfg = config or load_config("web")
    home = Path(home) if home else studio_home()
    store = M.Store(home)
    canva = client or CanvaClient(cfg, home=home)

    secret_file = home / "web_secret.key"
    if not secret_file.exists():
        secret_file.write_text(secrets.token_hex(32))
    app.secret_key = secret_file.read_text().strip()
    app.config.update(SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_HTTPONLY=True)

    cache: OrderedDict = OrderedDict()

    def cached_pages(project: dict, scale: float):
        key = (project["id"], project["updated"], round(scale, 2))
        if key not in cache:
            cache[key] = [R.to_png_bytes(im) for im in R.render_pages(project, scale)]
            while len(cache) > 12:
                cache.popitem(last=False)
        cache.move_to_end(key)
        return cache[key]

    def err(message: str, status: int = 400, **extra):
        return jsonify({"error": message, **extra}), status

    def load(pid: str):
        try:
            return store.get(pid)
        except KeyError:
            return None

    # ------------------------------------------------------------ guards
    @app.before_request
    def csrf_guard():
        if request.method in ("POST", "PUT", "DELETE") and request.headers.get("X-Studio") != "1":
            return err("Missing X-Studio header", 403)

    @app.after_request
    def headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "same-origin"
        if request.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.errorhandler(413)
    def too_big(_):
        return err("That file is too large (10 MB max).", 413)

    # ------------------------------------------------------------ pages and assets
    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/fonts/<name>")
    def fonts(name):
        if name not in ("Poppins-Regular.ttf", "Poppins-Medium.ttf", "Poppins-Bold.ttf"):
            return err("Not found", 404)
        return send_from_directory(str(FONT_DIR), name, max_age=86400)

    # ------------------------------------------------------------ Canva sign-in
    def canva_status() -> dict:
        info = {"demo": canva.demo, "signed_in": False, "name": ""}
        if canva.is_signed_in():
            try:
                info["name"] = canva.profile().get("display_name", "")
                info["signed_in"] = True
            except NotSignedIn:
                pass
            except CanvaError:
                info["signed_in"] = True
        return info

    @app.get("/auth/login")
    def login():
        verifier, challenge = make_pkce()
        state = secrets.token_urlsafe(24)
        session["oauth"] = {"state": state, "verifier": verifier}
        return redirect(canva.authorize_url(state, challenge))

    @app.get("/oauth/callback")
    def oauth_callback():
        pending = session.pop("oauth", None)
        if request.args.get("error"):
            return redirect("/?auth_error=" + "Canva sign-in was cancelled.")
        if not pending or request.args.get("state") != pending["state"]:
            return redirect("/?auth_error=" + "Sign-in could not be verified. Please try again.")
        try:
            canva.exchange_code(request.args.get("code", ""), pending["verifier"])
        except CanvaError as exc:
            return redirect("/?auth_error=" + str(exc).replace("&", "and"))
        return redirect("/?signed_in=1")

    @app.post("/auth/logout")
    def logout():
        canva.sign_out()
        return jsonify({"ok": True})

    @app.get("/api/canva/status")
    def status():
        return jsonify(canva_status())

    @app.get("/api/canva/designs")
    def designs():
        try:
            return jsonify({"designs": canva.list_designs(12)})
        except NotSignedIn as exc:
            return err(str(exc), 401, needs_login=True)
        except CanvaError as exc:
            return err(str(exc), 502)

    # ------------------------------------------------------------ bootstrap
    @app.get("/api/bootstrap")
    def bootstrap():
        examples = [{k: e[k] for k in ("id", "name", "kind", "description", "prompt")} for e in G.load_examples()]
        return jsonify({"options": O.option_lists(), "examples": examples, "projects": store.list(),
                        "canva": canva_status(), "formats": {k: list(v) for k, v in O.FORMATS.items()}})

    # ------------------------------------------------------------ projects
    @app.get("/api/projects")
    def list_projects():
        return jsonify({"projects": store.list()})

    @app.post("/api/projects")
    def create_project():
        body = request.get_json(silent=True) or {}
        mode = body.get("mode")
        try:
            if mode == "example":
                project = G.project_from_example(str(body.get("example_id", "")))
            elif mode == "idea":
                ptype = body.get("type")
                if ptype not in O.PROJECT_TYPES:
                    return err("Choose presentation, document or logo.")
                prompt = str(body.get("prompt", "")).strip()
                if not prompt:
                    return err("Describe your idea first - even one sentence works.")
                project = G.build_project(ptype, prompt[:2000], body.get("options") or {},
                                          doc_type=body.get("doc_type", "Blog post"), title=str(body.get("title", ""))[:120])
            elif mode == "blank":
                ptype = body.get("type")
                if ptype not in O.PROJECT_TYPES:
                    return err("Choose presentation, document or logo.")
                project = M.blank_project(ptype, str(body.get("title", "Untitled"))[:120] or "Untitled")
            else:
                return err("Unknown way to start a project.")
        except KeyError:
            return err("That example does not exist.", 404)
        return jsonify(store.save(project)), 201

    @app.get("/api/projects/<pid>")
    def get_project(pid):
        project = load(pid)
        return jsonify(project) if project else err("Project not found.", 404)

    @app.put("/api/projects/<pid>")
    def update_project(pid):
        current = load(pid)
        if not current:
            return err("Project not found.", 404)
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return err("Send the project as JSON.")
        body["id"], body["type"] = pid, current["type"]
        body["created"], body["pushes"], body["history"] = current["created"], current["pushes"], current["history"]
        uploads = str((home / "uploads").resolve())
        for s in body.get("slides", []):
            img = s.get("image") or ""
            if img and not str(Path(img).resolve()).startswith(uploads):
                s["image"] = ""
        return jsonify(store.save(body))

    @app.delete("/api/projects/<pid>")
    def delete_project(pid):
        if not load(pid):
            return err("Project not found.", 404)
        store.delete(pid)
        return jsonify({"ok": True})

    @app.post("/api/projects/<pid>/refine")
    def refine(pid):
        project = load(pid)
        if not project:
            return err("Project not found.", 404)
        text = str((request.get_json(silent=True) or {}).get("text", "")).strip()
        if not text:
            return err("Describe the change you want, for example: make it brighter.")
        project, changes = G.refine(project, text[:500])
        return jsonify({"project": store.save(project), "changes": changes})

    @app.post("/api/projects/<pid>/image")
    def add_image(pid):
        project = load(pid)
        if not project:
            return err("Project not found.", 404)
        file = request.files.get("file")
        try:
            slide = int(request.form.get("slide", "-1"))
        except ValueError:
            slide = -1
        if project["type"] != "presentation" or not file or not (0 <= slide < len(project["slides"])):
            return err("Pick a slide and an image file.")
        raw = file.read()
        if len(raw) > MAX_UPLOAD:
            return err("That file is too large (10 MB max).", 413)
        try:
            img = Image.open(io.BytesIO(raw))
            img.load()
            img = img.convert("RGB")
        except Exception:
            return err("That file is not a readable image. Use png, jpg, webp or gif.")
        img.thumbnail((2400, 2400))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=88)
        path = store.save_upload(buf.getvalue(), "jpg")
        project["slides"][slide]["image"] = path
        return jsonify(store.save(project))

    # ------------------------------------------------------------ previews and exports
    @app.get("/api/projects/<pid>/info")
    def info(pid):
        project = load(pid)
        if not project:
            return err("Project not found.", 404)
        pages = cached_pages(project, 0.3)
        return jsonify({"count": len(pages), "updated": project["updated"]})

    @app.get("/api/projects/<pid>/page/<int:n>.png")
    def page_png(pid, n):
        project = load(pid)
        if not project:
            return err("Project not found.", 404)
        try:
            scale = float(request.args.get("scale", "0.5"))
        except ValueError:
            scale = 0.5
        scale = max(0.1, min(1.0, scale))
        pages = cached_pages(project, scale)
        if not 0 <= n < len(pages):
            return err("No such page.", 404)
        return Response(pages[n], mimetype="image/png", headers={"Cache-Control": "private, max-age=60"})

    @app.get("/api/projects/<pid>/logo/<int:v>.png")
    def logo_png(pid, v):
        project = load(pid)
        if not project or project["type"] != "logo":
            return err("Logo not found.", 404)
        if not 0 <= v < len(O.LOGO_VARIANTS):
            return err("No such variant.", 404)
        scale = max(0.1, min(1.0, float(request.args.get("scale", "0.4") or 0.4)))
        return Response(R.to_png_bytes(R.render_logo(project, v, scale)), mimetype="image/png")

    @app.get("/api/projects/<pid>/export.<fmt>")
    def export(pid, fmt):
        project = load(pid)
        if not project:
            return err("Project not found.", 404)
        images = R.render_pages(project, 1.0)
        name = M.slug(project["title"])
        if not images:
            return err("Nothing to export yet - add a slide or section first.")
        if fmt == "pdf":
            return send_file(io.BytesIO(R.pages_to_pdf(images)), mimetype="application/pdf",
                             as_attachment=True, download_name=f"{name}.pdf")
        if fmt == "png" and len(images) == 1:
            return send_file(io.BytesIO(R.to_png_bytes(images[0])), mimetype="image/png",
                             as_attachment=True, download_name=f"{name}.png")
        if fmt in ("zip", "png"):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                for i, im in enumerate(images, 1):
                    z.writestr(f"{name}-{i:02d}.png", R.to_png_bytes(im))
            buf.seek(0)
            return send_file(buf, mimetype="application/zip", as_attachment=True, download_name=f"{name}-pages.zip")
        return err("Export as pdf, png or zip.", 404)

    # ------------------------------------------------------------ push to Canva
    @app.post("/api/projects/<pid>/push")
    def push(pid):
        project = load(pid)
        if not project:
            return err("Project not found.", 404)
        try:
            result = push_project(canva, project)
        except NotSignedIn as exc:
            return err(str(exc), 401, needs_login=True)
        except CanvaError as exc:
            return err(str(exc), 502)
        project["pushes"] = ([result] + project["pushes"])[:10]
        store.save(project)
        return jsonify({"result": result, "project": store.get(pid)})

    return app


def main():
    cfg = load_config("web")
    if cfg["demo"]:
        ensure_demo_server()
    app = create_app(cfg)
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    print(f"\n  Canvas Studio is running at http://{host}:{port}")
    print("  Canva: " + ("DEMO mode (no Canva keys found - see README to connect your real account)" if cfg["demo"] else "live, redirect " + cfg["redirect_uri"]))
    print("  Press Ctrl+C to stop.\n")
    if not os.environ.get("NO_BROWSER"):
        import threading
        import webbrowser
        threading.Timer(1.2, webbrowser.open, args=(f"http://{host}:{port}",)).start()
    app.run(host=host, port=port, threaded=True, debug=False)


if __name__ == "__main__":
    main()
