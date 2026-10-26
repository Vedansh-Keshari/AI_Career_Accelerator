"""The Canvas Studio server (Flask). The website launches it in a browser; the desktop app in its own window."""
from __future__ import annotations

import io
import os
import secrets
import threading
import time
import zipfile
from collections import OrderedDict
from pathlib import Path

from flask import Flask, Response, jsonify, redirect, request, send_file, send_from_directory
from PIL import Image

from . import ai as ai_mod
from . import elements as E
from . import generator as G
from . import models as M
from . import office
from . import options as O
from . import render as R
from .canva_client import CanvaClient, CanvaError, NotSignedIn, make_pkce, push_project
from .mock_canva import ensure_demo_server
from .paths import FONT_DIR, load_config, studio_home
from .secrets_store import SecretStore, Settings

STATIC = Path(__file__).resolve().parent / "static"
MAX_UPLOAD = 10 * 1024 * 1024
PENDING_TTL = 600


def create_app(config: dict | None = None, home: Path | None = None, client: CanvaClient | None = None,
               app_name: str = "web", desktop: bool = False, ai_session=None, open_url=None) -> Flask:
    app = Flask(__name__, static_folder=str(STATIC), static_url_path="/static")
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD + 1024 * 1024
    home = Path(home) if home else studio_home()
    store = M.Store(home)
    secret_store = SecretStore(home)
    settings = Settings(home)
    cfg = config if config is not None else load_config(app_name, secret_store, settings)
    canva = client or CanvaClient(cfg, home=home, secret_store=secret_store)
    cfg = canva.cfg  # one shared dict, updated in place when settings change
    store.cleanup_uploads()

    key_file = home / "web_secret.key"
    if not key_file.exists():
        key_file.write_text(secrets.token_hex(32))
    app.secret_key = key_file.read_text().strip()
    app.config.update(SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_HTTPONLY=True)

    cache: OrderedDict = OrderedDict()
    pending: dict[str, dict] = {}
    jobs: dict[str, dict] = {}
    jobs_lock = threading.Lock()

    render_locks: dict[tuple, threading.Lock] = {}
    render_guard = threading.Lock()

    def cached(key: tuple, make):
        """Render once per (project version, size); parallel requests for the same picture wait for the first."""
        with render_guard:
            lock = render_locks.setdefault(key, threading.Lock())
        with lock:
            if key not in cache:
                cache[key] = make()
                while len(cache) > 200:
                    cache.popitem(last=False)
                    render_locks.pop(next(iter(render_locks)), None)
            cache.move_to_end(key)
            return cache[key]

    def cached_pages(project: dict, scale: float):
        """All pages as PNG bytes (documents paginate as a whole, so they are rendered together)."""
        key = (project["id"], project["updated"], round(scale, 2), "all")
        return cached(key, lambda: [R.to_png_bytes(im) for im in R.render_pages(project, scale)])

    def page_bytes(project: dict, n: int, scale: float) -> bytes | None:
        """One slide (or logo) rendered on its own; documents come from the whole-document render."""
        scale = round(max(0.1, min(1.0, scale)), 2)
        if project["type"] == "presentation":
            if not 0 <= n < len(project["slides"]):
                return None
            base = O.FORMATS[project["options"]["format"]]
            size = (max(40, int(base[0] * scale)), max(40, int(base[1] * scale)))
            return cached((project["id"], project["updated"], scale, n),
                          lambda: R.to_png_bytes(R.render_slide(project, n, size=size)))
        pages = cached_pages(project, scale)
        return pages[n] if 0 <= n < len(pages) else None

    def err(message: str, status: int = 400, **extra):
        return jsonify({"error": message, **extra}), status

    def load(pid: str):
        try:
            return store.get(pid)
        except KeyError:
            return None

    def ai_callable():
        key = secret_store.get("anthropic_key")
        if not key:
            return None
        model = settings.all().get("ai", {}).get("model") or ai_mod.DEFAULT_MODEL
        return lambda kind, prompt, options, doc_type: ai_mod.generate(kind, prompt, options, doc_type, key, model, ai_session)

    # ------------------------------------------------------------ guards
    @app.before_request
    def csrf_guard():
        if request.method in ("POST", "PUT", "DELETE") and request.headers.get("X-Studio") != "1":
            return err("Missing X-Studio header", 403)

    @app.after_request
    def headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "same-origin"
        resp.headers["X-Frame-Options"] = "DENY"
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

    def begin_login(external: bool) -> str:
        verifier, challenge = make_pkce()
        state = secrets.token_urlsafe(24)
        now = time.time()
        for k in [k for k, v in pending.items() if now - v["at"] > PENDING_TTL]:
            del pending[k]
        pending[state] = {"verifier": verifier, "external": external, "at": now}
        return canva.authorize_url(state, challenge)

    @app.get("/auth/login")
    def login():
        return redirect(begin_login(False))

    @app.post("/auth/start")
    def start_login():
        external = bool((request.get_json(silent=True) or {}).get("external")) and desktop
        url = begin_login(external)
        if external:
            (open_url or __import__("webbrowser").open)(url)
        return jsonify({"url": url, "external": external})

    def done_page(ok: bool, message: str):
        title = "Signed in" if ok else "Sign-in did not finish"
        body = (f"<html><head><meta charset='utf-8'><title>{title}</title></head><body style='font-family:system-ui,sans-serif;"
                f"max-width:480px;margin:18vh auto;padding:0 20px'><h2>{title}</h2><p>{message}</p></body></html>")
        return Response(body, mimetype="text/html")

    @app.get("/oauth/callback")
    def oauth_callback():
        entry = pending.pop(request.args.get("state", ""), None)
        external = desktop or bool(entry and entry["external"])  # the desktop app signs in via the system browser
        if request.args.get("error"):
            return done_page(False, "Canva sign-in was cancelled. You can close this tab.") if external else redirect("/?auth_error=Canva sign-in was cancelled.")
        if not entry or time.time() - entry["at"] > PENDING_TTL:
            msg = "Sign-in could not be verified or took too long. Please try again."
            return done_page(False, msg) if external else redirect("/?auth_error=" + msg)
        try:
            canva.exchange_code(request.args.get("code", ""), entry["verifier"])
        except CanvaError as exc:
            return done_page(False, str(exc)) if external else redirect("/?auth_error=" + str(exc).replace("&", "and"))
        if external:
            return done_page(True, "You can close this tab and go back to Canvas Studio.")
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

    # ------------------------------------------------------------ settings
    def settings_view() -> dict:
        saved = settings.all()
        brand = saved.get("brand", {})
        return {
            "canva": {"client_id": "" if canva.demo else cfg["client_id"], "has_secret": not canva.demo, "demo": canva.demo,
                      "redirect_uri": cfg["redirect_uri"], "from_env": bool(os.environ.get("CANVA_CLIENT_ID"))},
            "ai": {"has_key": bool(secret_store.get("anthropic_key")), "model": saved.get("ai", {}).get("model") or ai_mod.DEFAULT_MODEL},
            "brand": {"name": brand.get("name", ""), "primary": brand.get("primary", ""), "accent": brand.get("accent", ""), "font": brand.get("font", "Style default")},
            "storage": {"protected_by": secret_store.protected_by},
        }

    @app.get("/api/settings")
    def get_settings():
        return jsonify(settings_view())

    @app.put("/api/settings")
    def put_settings():
        body = request.get_json(silent=True) or {}
        canva_in, ai_in, brand_in = body.get("canva") or {}, body.get("ai") or {}, body.get("brand") or {}
        if canva_in.get("clear"):
            secret_store.delete("canva_client_secret")
            settings.update({"canva": {"client_id": ""}})
            reload_canva()
        elif canva_in.get("client_id") is not None and (canva_in.get("client_id") or canva_in.get("client_secret")):
            cid = str(canva_in.get("client_id", "")).strip()
            csec = str(canva_in.get("client_secret", "")).strip()
            if not cid or len(cid) > 120 or " " in cid:
                return err("The Canva client id looks wrong (no spaces, under 120 characters).")
            if not csec and not secret_store.get("canva_client_secret"):
                return err("Paste the client secret too.")
            if csec:
                if len(csec) > 300:
                    return err("The Canva client secret looks too long.")
                secret_store.set("canva_client_secret", csec)
            settings.update({"canva": {"client_id": cid}})
            reload_canva()
        if ai_in.get("clear_key"):
            secret_store.delete("anthropic_key")
        elif ai_in.get("api_key"):
            key = str(ai_in["api_key"]).strip()
            if len(key) > 300 or " " in key:
                return err("That AI key looks wrong.")
            secret_store.set("anthropic_key", key)
        if "model" in ai_in:
            model = str(ai_in["model"]).strip()[:60]
            settings.update({"ai": {"model": model}})
        if brand_in:
            primary, accent = str(brand_in.get("primary", "")), str(brand_in.get("accent", ""))
            if (primary and not O.valid_hex(primary)) or (accent and not O.valid_hex(accent)):
                return err("Brand colours must look like #1C6DD0.")
            font = brand_in.get("font", "Style default")
            settings.update({"brand": {"name": str(brand_in.get("name", ""))[:60], "primary": primary, "accent": accent,
                                       "font": font if font in O.FONTS else "Style default"}})
        return jsonify(settings_view())

    def reload_canva():
        new = load_config(app_name, secret_store, settings)
        cfg.clear()
        cfg.update(new)
        canva.sign_out()  # credentials changed, old tokens no longer apply
        if cfg["demo"]:
            ensure_demo_server()

    # ------------------------------------------------------------ bootstrap
    @app.get("/api/bootstrap")
    def bootstrap():
        examples = [{k: e[k] for k in ("id", "name", "kind", "description", "prompt")} for e in G.load_examples()]
        return jsonify({"options": O.option_lists(), "examples": examples, "projects": store.list(), "desktop": desktop,
                        "canva": canva_status(), "settings": settings_view(), "formats": {k: list(v) for k, v in O.FORMATS.items()}})

    # ------------------------------------------------------------ projects
    @app.get("/api/projects")
    def list_projects():
        return jsonify({"projects": store.list()})

    @app.post("/api/projects")
    def create_project():
        body = request.get_json(silent=True) or {}
        mode = body.get("mode")
        notices: list[str] = []
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
                project = G.build_project(ptype, prompt[:2000], body.get("options") or {}, doc_type=body.get("doc_type", "Blog post"),
                                          title=str(body.get("title", ""))[:120], ai=ai_callable(), notices=notices)
            elif mode == "blank":
                ptype = body.get("type")
                if ptype not in O.PROJECT_TYPES:
                    return err("Choose presentation, document or logo.")
                project = M.blank_project(ptype, str(body.get("title", "Untitled"))[:120] or "Untitled")
            else:
                return err("Unknown way to start a project.")
        except KeyError:
            return err("That example does not exist.", 404)
        saved = store.save(project)
        return jsonify({**saved, "notices": notices}), 201

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
        expected = body.get("rev")
        body["id"], body["type"] = pid, current["type"]
        body["created"], body["pushes"], body["history"] = current["created"], current["pushes"], current["history"]
        for s in body.get("slides", []):
            if s.get("image") and not store.is_upload(s["image"]):
                s["image"] = ""
            for el in s.get("elements") or []:
                if el.get("image") and not store.is_upload(el["image"]):
                    el["image"] = ""
        try:
            return jsonify(store.save(body, expected_rev=int(expected) if expected is not None else None))
        except M.Conflict:
            return err("This project was changed somewhere else (another tab or window). Reload it to see the latest.", 409, conflict=True)

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

    @app.post("/api/projects/<pid>/apply-brand")
    def apply_brand(pid):
        project = load(pid)
        if not project:
            return err("Project not found.", 404)
        brand = settings.all().get("brand", {})
        if not (O.valid_hex(brand.get("primary", "")) and O.valid_hex(brand.get("accent", ""))):
            return err("Set your brand colours in Settings first.")
        project["brand"] = {"primary": brand["primary"], "accent": brand["accent"], "name": brand.get("name", "")}
        project["options"]["color"] = "Brand"
        font = O.FONTS.get(brand.get("font", "Style default"), "auto")
        project["tune"]["font"] = font
        return jsonify(store.save(project))

    # ---- editor: free layout
    def slide_of(project: dict, n) -> int | None:
        try:
            n = int(n)
        except (TypeError, ValueError):
            return None
        return n if 0 <= n < len(project["slides"]) and project["type"] == "presentation" else None

    @app.post("/api/projects/<pid>/free")
    def toggle_free(pid):
        project = load(pid)
        body = request.get_json(silent=True) or {}
        i = slide_of(project, body.get("slide")) if project else None
        if project is None or i is None:
            return err("Pick a slide first.", 404 if project is None else 400)
        slide = project["slides"][i]
        if body.get("enable", True):
            if not slide["elements"]:
                slide["elements"] = E.default_elements(project, i)
            slide["free"] = True
        else:
            slide["free"] = False
        return jsonify(store.save(project))

    @app.post("/api/projects/<pid>/elements")
    def add_element(pid):
        project = load(pid)
        body = request.get_json(silent=True) or {}
        i = slide_of(project, body.get("slide")) if project else None
        if project is None or i is None:
            return err("Pick a slide first.", 404 if project is None else 400)
        if body.get("kind") not in ("text", "rect", "ellipse"):
            return err("Add a text box, rectangle or circle.")
        slide = project["slides"][i]
        if len(slide["elements"]) >= 40:
            return err("That slide already has 40 elements.")
        if not slide["free"]:
            slide["elements"] = slide["elements"] or E.default_elements(project, i)
            slide["free"] = True
        el = E.blank_element("ellipse" if body["kind"] == "ellipse" else body["kind"])
        slide["elements"].append(el)
        return jsonify({"project": store.save(project), "element_id": el["id"]})

    @app.post("/api/projects/<pid>/image")
    def add_image(pid):
        project = load(pid)
        if not project:
            return err("Project not found.", 404)
        file = request.files.get("file")
        i = slide_of(project, request.form.get("slide", "-1"))
        if i is None or not file:
            return err("Pick a slide and an image file.")
        raw = file.read()
        if len(raw) > MAX_UPLOAD:
            return err("That file is too large (10 MB max).", 413)
        try:
            img = Image.open(io.BytesIO(raw))
            img.load()
            img = img.convert("RGB")
        except Exception:  # noqa: BLE001
            return err("That file is not a readable image. Use png, jpg, webp or gif.")
        img.thumbnail((2400, 2400))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=88)
        path = store.save_upload(buf.getvalue(), "jpg")
        slide = project["slides"][i]
        target = request.form.get("element", "")
        if target == "new":
            if len(slide["elements"]) >= 40:
                return err("That slide already has 40 elements.")
            if not slide["free"]:
                slide["elements"] = slide["elements"] or E.default_elements(project, i)
                slide["free"] = True
            el = E.blank_element("image")
            el["image"] = path
            slide["elements"].append(el)
        elif target:
            hit = [e for e in slide["elements"] if e["id"] == target and e["type"] == "image"]
            if not hit:
                return err("That image box no longer exists.", 404)
            hit[0]["image"] = path
        else:
            slide["image"] = path
        return jsonify(store.save(project))

    # ------------------------------------------------------------ previews and exports
    @app.get("/api/projects/<pid>/info")
    def info(pid):
        project = load(pid)
        if not project:
            return err("Project not found.", 404)
        count = len(project["slides"]) if project["type"] == "presentation" else len(cached_pages(project, 0.3))
        return jsonify({"count": count, "updated": project["updated"]})

    @app.get("/api/projects/<pid>/page/<int:n>.png")
    def page_png(pid, n):
        project = load(pid)
        if not project:
            return err("Project not found.", 404)
        try:
            scale = float(request.args.get("scale", "0.5"))
        except ValueError:
            scale = 0.5
        data = page_bytes(project, n, scale)
        if data is None:
            return err("No such page.", 404)
        return Response(data, mimetype="image/png", headers={"Cache-Control": "private, max-age=60"})

    @app.get("/api/projects/<pid>/logo/<int:v>.png")
    def logo_png(pid, v):
        project = load(pid)
        if not project or project["type"] != "logo":
            return err("Logo not found.", 404)
        if not 0 <= v < len(O.LOGO_VARIANTS):
            return err("No such variant.", 404)
        try:
            scale = max(0.1, min(1.0, float(request.args.get("scale", "0.4"))))
        except ValueError:
            scale = 0.4
        return Response(R.to_png_bytes(R.render_logo(project, v, scale)), mimetype="image/png")

    @app.get("/api/projects/<pid>/export.<fmt>")
    def export(pid, fmt):
        project = load(pid)
        if not project:
            return err("Project not found.", 404)
        name = M.slug(project["title"])
        if fmt == "pptx":
            if project["type"] != "presentation" or not project["slides"]:
                return err("Only presentations can be saved as PowerPoint.")
            return send_file(io.BytesIO(office.presentation_to_pptx(project)), mimetype=office.PPTX_MIME, as_attachment=True, download_name=f"{name}.pptx")
        if fmt == "docx":
            if project["type"] != "document" or not project["doc"]["sections"]:
                return err("Only documents can be saved as Word.")
            return send_file(io.BytesIO(office.document_to_docx(project)), mimetype=office.DOCX_MIME, as_attachment=True, download_name=f"{name}.docx")
        images = R.render_pages(project, 1.0)
        if not images:
            return err("Nothing to export yet - add a slide or section first.")
        if fmt == "pdf":
            return send_file(io.BytesIO(R.pages_to_pdf(images)), mimetype="application/pdf", as_attachment=True, download_name=f"{name}.pdf")
        if fmt == "png" and len(images) == 1:
            return send_file(io.BytesIO(R.to_png_bytes(images[0])), mimetype="image/png", as_attachment=True, download_name=f"{name}.png")
        if fmt in ("zip", "png"):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                for n, im in enumerate(images, 1):
                    z.writestr(f"{name}-{n:02d}.png", R.to_png_bytes(im))
            buf.seek(0)
            return send_file(buf, mimetype="application/zip", as_attachment=True, download_name=f"{name}-pages.zip")
        return err("Export as pdf, pptx, docx, png or zip.", 404)

    # ------------------------------------------------------------ push to Canva (background job with progress)
    @app.post("/api/projects/<pid>/push")
    def push(pid):
        project = load(pid)
        if not project:
            return err("Project not found.", 404)
        if not canva.is_signed_in():
            return err("Sign in to Canva first.", 401, needs_login=True)
        job_id = secrets.token_urlsafe(8)
        job = {"id": job_id, "state": "running", "stage": "Starting", "step": 0, "result": None, "error": "", "needs_login": False, "pid": pid}
        with jobs_lock:
            jobs[job_id] = job
            for old in [k for k, v in jobs.items() if v["state"] != "running" and len(jobs) > 20]:
                del jobs[old]

        def progress(stage: str, step: int = 0) -> None:
            job["stage"], job["step"] = stage, step

        def run() -> None:
            try:
                result = push_project(canva, project, progress)
                latest = store.get(pid) if load(pid) else project
                latest["pushes"] = ([result] + latest["pushes"])[:10]
                store.save(latest, bump=False)
                job.update(state="done", stage="Done", result=result)
            except NotSignedIn as exc:
                job.update(state="error", error=str(exc), needs_login=True)
            except CanvaError as exc:
                job.update(state="error", error=str(exc))
            except Exception as exc:  # noqa: BLE001 - never leave a job stuck on "running"
                job.update(state="error", error=f"Something unexpected went wrong: {exc}")

        threading.Thread(target=run, daemon=True).start()
        return jsonify({"job_id": job_id}), 202

    @app.get("/api/jobs/<job_id>")
    def job_status(job_id):
        job = jobs.get(job_id)
        if not job:
            return err("Unknown job.", 404)
        out = {k: job[k] for k in ("id", "state", "stage", "step", "result", "error", "needs_login")}
        if job["state"] == "done":
            out["project"] = load(job["pid"])
        return jsonify(out)

    return app


def serve(app: Flask, host: str, port: int) -> None:
    """Run with waitress (a real server that also works on Windows); fall back to Flask's own."""
    try:
        from waitress import serve as waitress_serve
    except ImportError:
        app.run(host=host, port=port, threaded=True, debug=False)
        return
    waitress_serve(app, host=host, port=port, threads=8, ident="CanvasStudio")


def run_web(open_browser: bool = True) -> None:
    """Entry point used by web/app.py."""
    import webbrowser

    app_name = "web"
    secret_store, settings = SecretStore(), Settings()
    cfg = load_config(app_name, secret_store, settings)
    if cfg["demo"]:
        ensure_demo_server()
    app = create_app(cfg, app_name=app_name)
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    print(f"\n  Canvas Studio is running at http://{host}:{port}")
    print("  Canva: " + ("DEMO mode (add your Canva keys in Settings to connect your real account)" if cfg["demo"] else "live, redirect " + cfg["redirect_uri"]))
    print("  Press Ctrl+C to stop.\n")
    if open_browser and not os.environ.get("NO_BROWSER"):
        threading.Timer(1.2, webbrowser.open, args=(f"http://{host}:{port}",)).start()
    try:
        serve(app, host, port)
    except OSError as exc:
        raise SystemExit(f"Could not start on port {port} ({exc}). Another program may be using it - set PORT to a free number and try again.") from exc
