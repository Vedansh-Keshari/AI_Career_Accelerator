"""Run from the canva-clone folder:  python -m pytest web/tests -q"""
import io
import json
import sys
import time
import urllib.parse
import zipfile
from pathlib import Path

import pytest
import requests
from PIL import Image

WEB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WEB))

import app as webapp  # noqa: E402  (the launcher; adds the shared folder to sys.path)

from studio.canva_client import CanvaClient  # noqa: E402
from studio.mock_canva import MockCanva  # noqa: E402
from studio.paths import load_config  # noqa: E402
from studio.secrets_store import SecretStore  # noqa: E402

H = {"X-Studio": "1"}


class FakeAI:
    """Stands in for api.anthropic.com."""
    def __init__(self, text="", status=200):
        self.text, self.status, self.calls = text, status, 0

    def post(self, url, **kw):
        self.calls += 1
        r = requests.Response()
        r.status_code = self.status
        r._content = json.dumps({"content": [{"type": "text", "text": self.text}]}).encode()
        return r


@pytest.fixture()
def env(tmp_path):
    mock = MockCanva(8798).start()
    cfg = load_config("web")
    cfg.update(authorize_url=f"{mock.base}/api/oauth/authorize", token_url=f"{mock.base}/rest/v1/oauth/token",
               api_base=f"{mock.base}/rest/v1", redirect_uri="http://localhost/oauth/callback")
    client = CanvaClient(cfg, home=tmp_path, sleep=lambda s: None, secret_store=SecretStore(tmp_path, use_keyring=False))
    ai = FakeAI()
    app = webapp.create_app(cfg, home=tmp_path, client=client, ai_session=ai)
    app.config["TESTING"] = True
    c = app.test_client()
    c.ai, c.home, c.app_obj = ai, tmp_path, app
    yield c, mock
    mock.stop()


def make(c, example="yoga-presentation"):
    r = c.post("/api/projects", json={"mode": "example", "example_id": example}, headers=H)
    assert r.status_code == 201
    return r.get_json()


def sign_in(c, external=False):
    r = c.post("/auth/start", json={"external": external}, headers=H)
    url = r.get_json()["url"]
    q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
    form = {k: q[k] for k in ("client_id", "redirect_uri", "state", "code_challenge", "scope")}
    form.update(email="vedansh@example.com", action="allow")
    back = requests.post(url.split("?")[0], data=form, allow_redirects=False).headers["Location"]
    return c.get("/oauth/callback?" + urllib.parse.urlparse(back).query)


def run_push(c, pid, timeout=20):
    r = c.post(f"/api/projects/{pid}/push", json={}, headers=H)
    assert r.status_code == 202
    job = r.get_json()["job_id"]
    end = time.time() + timeout
    while time.time() < end:
        j = c.get(f"/api/jobs/{job}").get_json()
        if j["state"] != "running":
            return j
        time.sleep(0.05)
    raise AssertionError("push job never finished")


def test_pages_headers_and_bootstrap(env):
    c, _ = env
    r = c.get("/")
    assert b"Canvas Studio" in r.data and r.headers["X-Frame-Options"] == "DENY" and r.headers["X-Content-Type-Options"] == "nosniff"
    assert c.get("/fonts/Poppins-Bold.ttf").status_code == 200
    assert c.get("/fonts/../studio/paths.py").status_code == 404
    assert c.get("/static/app.js").status_code == 200 and c.get("/static/style.css").status_code == 200
    boot = c.get("/api/bootstrap").get_json()
    assert len(boot["examples"]) == 5 and "Watercolour" in boot["options"]["styles"] and boot["canva"]["signed_in"] is False
    assert boot["desktop"] is False and "Poppins" in boot["options"]["fonts"]


def test_csrf_header_required(env):
    c, _ = env
    assert c.post("/api/projects", json={"mode": "blank", "type": "logo"}).status_code == 403
    assert c.put("/api/settings", json={}).status_code == 403


def test_project_crud_and_validation(env):
    c, _ = env
    p = make(c)
    assert c.get(f"/api/projects/{p['id']}").get_json()["title"] == "Benefits of Yoga"
    p["title"] = "Renamed"
    p["slides"][0]["image"] = "/etc/passwd"
    p["slides"][1]["elements"] = [{"type": "image", "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2, "image": "C:\\Windows\\win.ini"}]
    saved = c.put(f"/api/projects/{p['id']}", json=p, headers=H).get_json()
    assert saved["title"] == "Renamed" and saved["slides"][0]["image"] == "" and saved["slides"][1]["elements"][0]["image"] == ""
    assert c.get("/api/projects/p_0000000000").status_code == 404
    assert c.get("/api/projects/..%2Fx").status_code == 404
    assert c.post("/api/projects", json={"mode": "idea", "type": "logo", "prompt": ""}, headers=H).status_code == 400
    assert c.post("/api/projects", json={"mode": "idea", "type": "nope", "prompt": "x"}, headers=H).status_code == 400
    assert c.post("/api/projects", json={"mode": "example", "example_id": "zzz"}, headers=H).status_code == 404
    idea = c.post("/api/projects", headers=H, json={"mode": "idea", "type": "presentation", "prompt": "A deck about tea",
                                                    "options": {"color": "Green", "length": "Short and sharp (1 to 5 pages)"}})
    assert idea.status_code == 201 and idea.get_json()["options"]["color"] == "Green" and idea.get_json()["generated_by"] == "templates"
    assert len(c.get("/api/projects").get_json()["projects"]) == 2
    assert c.delete(f"/api/projects/{p['id']}", headers=H).status_code == 200
    assert c.delete(f"/api/projects/{p['id']}", headers=H).status_code == 404


def test_two_tabs_cannot_overwrite_each_other(env):
    c, _ = env
    p = make(c)
    tab_a = c.get(f"/api/projects/{p['id']}").get_json()
    tab_b = c.get(f"/api/projects/{p['id']}").get_json()
    tab_a["title"] = "From tab A"
    saved = c.put(f"/api/projects/{p['id']}", json=tab_a, headers=H).get_json()
    assert saved["rev"] == tab_a["rev"] + 1
    tab_b["title"] = "From tab B"
    r = c.put(f"/api/projects/{p['id']}", json=tab_b, headers=H)
    assert r.status_code == 409 and r.get_json()["conflict"] is True
    assert c.get(f"/api/projects/{p['id']}").get_json()["title"] == "From tab A"
    saved["title"] = "A again"
    assert c.put(f"/api/projects/{p['id']}", json=saved, headers=H).status_code == 200


def test_previews_and_exports(env):
    c, _ = env
    deck = make(c)
    assert c.get(f"/api/projects/{deck['id']}/info").get_json()["count"] == 6
    r = c.get(f"/api/projects/{deck['id']}/page/2.png?scale=0.3")
    assert r.status_code == 200 and Image.open(io.BytesIO(r.data)).size == (576, 324)
    assert c.get(f"/api/projects/{deck['id']}/page/9.png").status_code == 404
    assert c.get(f"/api/projects/{deck['id']}/page/1.png?scale=abc").status_code == 200
    pdf = c.get(f"/api/projects/{deck['id']}/export.pdf")
    assert pdf.data.startswith(b"%PDF") and "attachment" in pdf.headers["Content-Disposition"]
    z = zipfile.ZipFile(io.BytesIO(c.get(f"/api/projects/{deck['id']}/export.zip").data))
    assert len(z.namelist()) == 6
    pptx = c.get(f"/api/projects/{deck['id']}/export.pptx")
    assert pptx.status_code == 200 and pptx.data[:2] == b"PK" and ".pptx" in pptx.headers["Content-Disposition"]
    assert c.get(f"/api/projects/{deck['id']}/export.docx").status_code == 400
    logo = make(c, "cafe-logo")
    assert c.get(f"/api/projects/{logo['id']}/logo/3.png").status_code == 200
    assert c.get(f"/api/projects/{logo['id']}/logo/9.png").status_code == 404
    assert Image.open(io.BytesIO(c.get(f"/api/projects/{logo['id']}/export.png").data)).size == (1000, 1000)
    doc = make(c, "workout-blog-first")
    assert c.get(f"/api/projects/{doc['id']}/info").get_json()["count"] == 2
    docx = c.get(f"/api/projects/{doc['id']}/export.docx")
    assert docx.data[:2] == b"PK" and c.get(f"/api/projects/{doc['id']}/export.pptx").status_code == 400


def test_refine_and_brand(env):
    c, _ = env
    p = make(c)
    r = c.post(f"/api/projects/{p['id']}/refine", json={"text": "make it brighter"}, headers=H).get_json()
    assert r["project"]["tune"]["boldness"] == 1 and r["changes"]
    assert c.post(f"/api/projects/{p['id']}/refine", json={"text": ""}, headers=H).status_code == 400
    assert c.post(f"/api/projects/{p['id']}/apply-brand", json={}, headers=H).status_code == 400    # no brand kit yet
    assert c.put("/api/settings", json={"brand": {"primary": "red", "accent": "#fff"}}, headers=H).status_code == 400
    s = c.put("/api/settings", json={"brand": {"name": "Acme", "primary": "#7a1f5c", "accent": "#f4a261", "font": "DejaVu Serif"}}, headers=H).get_json()
    assert s["brand"]["font"] == "DejaVu Serif"
    branded = c.post(f"/api/projects/{p['id']}/apply-brand", json={}, headers=H).get_json()
    assert branded["options"]["color"] == "Brand" and branded["tune"]["font"] == "serif" and branded["brand"]["primary"] == "#7a1f5c"
    assert c.get(f"/api/projects/{p['id']}/page/0.png").status_code == 200


def test_free_layout_endpoints(env):
    c, _ = env
    p = make(c)
    r = c.post(f"/api/projects/{p['id']}/free", json={"slide": 1, "enable": True}, headers=H).get_json()
    assert r["slides"][1]["free"] is True and len(r["slides"][1]["elements"]) == 2
    added = c.post(f"/api/projects/{p['id']}/elements", json={"slide": 1, "kind": "ellipse"}, headers=H).get_json()
    assert added["project"]["slides"][1]["elements"][-1]["id"] == added["element_id"]
    assert c.post(f"/api/projects/{p['id']}/elements", json={"slide": 1, "kind": "video"}, headers=H).status_code == 400
    assert c.post(f"/api/projects/{p['id']}/elements", json={"slide": 99, "kind": "text"}, headers=H).status_code == 400
    buf = io.BytesIO()
    Image.new("RGB", (300, 200), "#00aa66").save(buf, "PNG")
    up = c.post(f"/api/projects/{p['id']}/image", headers=H, content_type="multipart/form-data",
                data={"file": (io.BytesIO(buf.getvalue()), "x.png"), "slide": "1", "element": "new"})
    els = up.get_json()["slides"][1]["elements"]
    assert up.status_code == 200 and els[-1]["type"] == "image" and Path(els[-1]["image"]).exists()
    assert c.post(f"/api/projects/{p['id']}/image", headers=H, content_type="multipart/form-data",
                  data={"file": (io.BytesIO(buf.getvalue()), "x.png"), "slide": "1", "element": "e_nope"}).status_code == 404
    off = c.post(f"/api/projects/{p['id']}/free", json={"slide": 1, "enable": False}, headers=H).get_json()
    assert off["slides"][1]["free"] is False and len(off["slides"][1]["elements"]) == 4   # kept for coming back
    assert c.get(f"/api/projects/{p['id']}/page/1.png").status_code == 200
    logo = make(c, "cafe-logo")
    assert c.post(f"/api/projects/{logo['id']}/free", json={"slide": 0}, headers=H).status_code == 400


def test_image_upload(env):
    c, _ = env
    p = make(c)
    buf = io.BytesIO()
    Image.new("RGB", (300, 200), "#00aa66").save(buf, "PNG")
    r = c.post(f"/api/projects/{p['id']}/image", headers=H, content_type="multipart/form-data",
               data={"file": (io.BytesIO(buf.getvalue()), "x.png"), "slide": "1"})
    assert r.status_code == 200 and r.get_json()["slides"][1]["image"].endswith(".jpg")
    bad = c.post(f"/api/projects/{p['id']}/image", headers=H, content_type="multipart/form-data",
                 data={"file": (io.BytesIO(b"not an image"), "x.png"), "slide": "1"})
    assert bad.status_code == 400 and "not a readable image" in bad.get_json()["error"]
    assert c.post(f"/api/projects/{p['id']}/image", headers=H, content_type="multipart/form-data", data={"slide": "1"}).status_code == 400
    assert c.get(f"/api/projects/{p['id']}/page/1.png").status_code == 200


def test_oauth_push_job_and_logout(env):
    c, mock = env
    p = make(c)
    r = c.post(f"/api/projects/{p['id']}/push", json={}, headers=H)
    assert r.status_code == 401 and r.get_json()["needs_login"] is True
    assert c.get("/api/canva/designs").status_code == 401
    c.post("/auth/start", json={}, headers=H)
    assert "auth_error" in c.get("/oauth/callback?code=x&state=wrong").headers["Location"]
    cb = sign_in(c)
    assert cb.status_code == 302 and cb.headers["Location"].endswith("signed_in=1")
    assert c.get("/api/canva/status").get_json() == {"demo": True, "name": "vedansh", "signed_in": True}
    job = run_push(c, p["id"])
    assert job["state"] == "done" and job["result"]["kind"] == "6-slide editable design" and job["result"]["editable"] is True
    assert job["project"]["pushes"][0]["id"] == job["result"]["id"]
    assert job["result"]["edit_url"] in [d["urls"]["edit_url"] for d in mock.designs.values()]
    assert len(c.get("/api/canva/designs").get_json()["designs"]) == 1
    assert c.get("/api/projects").get_json()["projects"][0]["pushed"] is True
    # the push saved history without invalidating an editor that is still open
    open_copy = c.get(f"/api/projects/{p['id']}").get_json()
    open_copy["title"] = "still editable"
    assert c.put(f"/api/projects/{p['id']}", json=open_copy, headers=H).status_code == 200
    assert c.get("/api/jobs/nope").status_code == 404
    assert c.post("/auth/logout", json={}, headers=H).status_code == 200
    assert c.get("/api/canva/status").get_json()["signed_in"] is False


def test_push_errors_are_reported_not_hidden(env):
    c, mock = env
    p = make(c)
    sign_in(c)
    mock.access.clear()
    mock.refresh.clear()                       # Canva forgot us: the job must report "sign in again"
    job = run_push(c, p["id"])
    assert job["state"] == "error" and job["needs_login"] is True
    sign_in(c)
    empty = make(c, "cafe-logo")
    empty["slides"] = []
    deck = c.post("/api/projects", json={"mode": "blank", "type": "presentation"}, headers=H).get_json()
    deck["slides"] = []
    c.put(f"/api/projects/{deck['id']}", json=deck, headers=H)
    job = run_push(c, deck["id"])
    assert job["state"] == "error" and "Nothing to push" in job["error"]


def test_desktop_sign_in_uses_the_system_browser(env):
    c, _ = env
    opened = []
    app = webapp.create_app(load_config("web"), home=c.home / "d", desktop=True, open_url=opened.append)
    d = app.test_client()
    r = d.post("/auth/start", json={"external": True}, headers=H).get_json()
    assert r["external"] is True and opened == [r["url"]]
    assert c.post("/auth/start", json={"external": True}, headers=H).get_json()["external"] is False   # website never does this
    # an unknown or expired state shows a plain page for the external browser, not a redirect into the app
    page = d.get("/oauth/callback?code=x&state=nope")
    assert page.status_code == 200 and b"did not finish" in page.data


def test_settings_roundtrip_and_secrets_stay_server_side(env):
    c, _ = env
    s = c.get("/api/settings").get_json()
    assert s["canva"]["demo"] is True and s["ai"]["has_key"] is False and s["storage"]["protected_by"] in ("file", "keyring")
    assert c.put("/api/settings", json={"canva": {"client_id": "bad id", "client_secret": "x"}}, headers=H).status_code == 400
    assert c.put("/api/settings", json={"canva": {"client_id": "OC-abc"}}, headers=H).status_code == 400     # secret missing
    out = c.put("/api/settings", json={"canva": {"client_id": "OC-abc", "client_secret": "TOP-SECRET-VALUE"},
                                       "ai": {"api_key": "sk-ant-KEYKEY", "model": "claude-test"}}, headers=H)
    body = out.get_data(as_text=True)
    assert out.status_code == 200 and "TOP-SECRET-VALUE" not in body and "KEYKEY" not in body
    s = out.get_json()
    assert s["canva"]["demo"] is False and s["canva"]["client_id"] == "OC-abc" and s["ai"] == {"has_key": True, "model": "claude-test"}
    assert "TOP-SECRET-VALUE" not in c.get("/api/bootstrap").get_data(as_text=True)
    for f in c.home.iterdir():
        if f.is_file():
            assert b"TOP-SECRET-VALUE" not in f.read_bytes() and b"KEYKEY" not in f.read_bytes()
    assert c.put("/api/settings", json={"canva": {"clear": True}, "ai": {"clear_key": True}}, headers=H).get_json()["canva"]["demo"] is True


def test_ai_is_used_when_a_key_is_saved_and_fallback_is_explained(env):
    c, _ = env
    c.put("/api/settings", json={"ai": {"api_key": "sk-test"}}, headers=H)
    c.ai.text = json.dumps({"title": "Bees", "slides": [{"title": "Bees", "body": "Intro"}, {"title": "Why", "body": "- a\n- b"}, {"title": "Join", "body": "Go"}]})
    good = c.post("/api/projects", json={"mode": "idea", "type": "presentation", "prompt": "bees"}, headers=H).get_json()
    assert good["generated_by"] == "ai" and good["title"] == "Bees" and good["notices"] == [] and c.ai.calls == 1
    c.ai.status = 401
    bad = c.post("/api/projects", json={"mode": "idea", "type": "presentation", "prompt": "bees"}, headers=H).get_json()
    assert bad["generated_by"] == "templates" and "rejected" in bad["notices"][0]


def test_startup_cleans_old_unused_uploads(tmp_path):
    import os

    from studio import models as M
    store = M.Store(tmp_path)
    junk = Path(store.save_upload(b"x", "png"))
    os.utime(junk, (0, 0))
    webapp.create_app(load_config("web"), home=tmp_path)
    assert not junk.exists()
