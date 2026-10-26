"""Run from the canva-clone folder:  python -m pytest web/tests -q"""
import io
import sys
import urllib.parse
import zipfile
from pathlib import Path

import pytest
import requests
from PIL import Image

WEB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WEB))

import app as webapp  # noqa: E402
from studio.canva_client import CanvaClient  # noqa: E402
from studio.mock_canva import MockCanva  # noqa: E402
from studio.paths import load_config  # noqa: E402

H = {"X-Studio": "1"}


@pytest.fixture()
def env(tmp_path):
    mock = MockCanva(8798).start()
    cfg = load_config("web")
    cfg.update(authorize_url=f"{mock.base}/api/oauth/authorize", token_url=f"{mock.base}/rest/v1/oauth/token",
               api_base=f"{mock.base}/rest/v1", redirect_uri="http://localhost/oauth/callback")
    client = CanvaClient(cfg, home=tmp_path, sleep=lambda s: None)
    app = webapp.create_app(cfg, home=tmp_path, client=client)
    app.config["TESTING"] = True
    yield app.test_client(), mock
    mock.stop()


def make(c, example="yoga-presentation"):
    r = c.post("/api/projects", json={"mode": "example", "example_id": example}, headers=H)
    assert r.status_code == 201
    return r.get_json()


def sign_in(c):
    r = c.get("/auth/login")
    assert r.status_code == 302
    url = r.headers["Location"]
    q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
    form = {k: q[k] for k in ("client_id", "redirect_uri", "state", "code_challenge", "scope")}
    form.update(email="vedansh@example.com", action="allow")
    back = requests.post(url.split("?")[0], data=form, allow_redirects=False).headers["Location"]
    cb = urllib.parse.urlparse(back)
    return c.get("/oauth/callback?" + cb.query)


def test_pages_and_bootstrap(env):
    c, _ = env
    assert b"Canvas Studio" in c.get("/").data
    assert c.get("/fonts/Poppins-Bold.ttf").status_code == 200
    assert c.get("/fonts/../studio/paths.py").status_code == 404
    boot = c.get("/api/bootstrap").get_json()
    assert len(boot["examples"]) == 5 and "Watercolour" in boot["options"]["styles"]
    assert boot["canva"]["signed_in"] is False


def test_csrf_header_required(env):
    c, _ = env
    assert c.post("/api/projects", json={"mode": "blank", "type": "logo"}).status_code == 403


def test_project_crud_and_validation(env):
    c, _ = env
    p = make(c)
    assert c.get(f"/api/projects/{p['id']}").get_json()["title"] == "Benefits of Yoga"
    p["title"] = "Renamed"
    p["slides"][0]["image"] = "/etc/passwd"
    saved = c.put(f"/api/projects/{p['id']}", json=p, headers=H).get_json()
    assert saved["title"] == "Renamed" and saved["slides"][0]["image"] == ""
    assert c.get("/api/projects/p_0000000000").status_code == 404
    assert c.get("/api/projects/..%2Fx").status_code == 404
    assert c.post("/api/projects", json={"mode": "idea", "type": "logo", "prompt": ""}, headers=H).status_code == 400
    assert c.post("/api/projects", json={"mode": "idea", "type": "nope", "prompt": "x"}, headers=H).status_code == 400
    assert c.post("/api/projects", json={"mode": "example", "example_id": "zzz"}, headers=H).status_code == 404
    idea = c.post("/api/projects", headers=H, json={"mode": "idea", "type": "presentation", "prompt": "A deck about tea",
                                                    "options": {"color": "Green", "length": "Short and sharp (1 to 5 pages)"}})
    assert idea.status_code == 201 and idea.get_json()["options"]["color"] == "Green"
    assert len(c.get("/api/projects").get_json()["projects"]) == 2
    assert c.delete(f"/api/projects/{p['id']}", headers=H).status_code == 200
    assert c.delete(f"/api/projects/{p['id']}", headers=H).status_code == 404


def test_previews_and_exports(env):
    c, _ = env
    deck = make(c)
    assert c.get(f"/api/projects/{deck['id']}/info").get_json()["count"] == 6
    r = c.get(f"/api/projects/{deck['id']}/page/2.png?scale=0.3")
    assert r.status_code == 200 and Image.open(io.BytesIO(r.data)).size == (576, 324)
    assert c.get(f"/api/projects/{deck['id']}/page/9.png").status_code == 404
    pdf = c.get(f"/api/projects/{deck['id']}/export.pdf")
    assert pdf.data.startswith(b"%PDF") and "attachment" in pdf.headers["Content-Disposition"]
    z = zipfile.ZipFile(io.BytesIO(c.get(f"/api/projects/{deck['id']}/export.zip").data))
    assert len(z.namelist()) == 6
    logo = make(c, "cafe-logo")
    assert c.get(f"/api/projects/{logo['id']}/logo/3.png").status_code == 200
    assert c.get(f"/api/projects/{logo['id']}/logo/9.png").status_code == 404
    assert Image.open(io.BytesIO(c.get(f"/api/projects/{logo['id']}/export.png").data)).size == (1000, 1000)
    doc = make(c, "workout-blog-first")
    assert c.get(f"/api/projects/{doc['id']}/info").get_json()["count"] == 2


def test_refine_endpoint(env):
    c, _ = env
    p = make(c)
    r = c.post(f"/api/projects/{p['id']}/refine", json={"text": "make it brighter"}, headers=H).get_json()
    assert r["project"]["tune"]["boldness"] == 1 and r["changes"]
    assert c.post(f"/api/projects/{p['id']}/refine", json={"text": ""}, headers=H).status_code == 400


def test_image_upload(env):
    c, _ = env
    p = make(c)
    buf = io.BytesIO()
    Image.new("RGB", (300, 200), "#00aa66").save(buf, "PNG")
    r = c.post(f"/api/projects/{p['id']}/image", headers=H, content_type="multipart/form-data",
               data={"file": (io.BytesIO(buf.getvalue()), "x.png"), "slide": "1"})
    assert r.status_code == 200 and r.get_json()["slides"][1]["image"].endswith(".jpg")
    assert Path(r.get_json()["slides"][1]["image"]).exists()
    bad = c.post(f"/api/projects/{p['id']}/image", headers=H, content_type="multipart/form-data",
                 data={"file": (io.BytesIO(b"not an image"), "x.png"), "slide": "1"})
    assert bad.status_code == 400 and "not a readable image" in bad.get_json()["error"]
    none = c.post(f"/api/projects/{p['id']}/image", headers=H, content_type="multipart/form-data", data={"slide": "1"})
    assert none.status_code == 400
    # the page that now has a photo still renders
    assert c.get(f"/api/projects/{p['id']}/page/1.png").status_code == 200


def test_oauth_and_push_flow(env):
    c, mock = env
    p = make(c)
    r = c.post(f"/api/projects/{p['id']}/push", json={}, headers=H)
    assert r.status_code == 401 and r.get_json()["needs_login"] is True
    assert c.get("/api/canva/designs").status_code == 401
    # state mismatch is refused
    c.get("/auth/login")
    assert "auth_error" in c.get("/oauth/callback?code=x&state=wrong").headers["Location"]
    cb = sign_in(c)
    assert cb.status_code == 302 and cb.headers["Location"].endswith("signed_in=1")
    st = c.get("/api/canva/status").get_json()
    assert st["signed_in"] is True and st["name"] == "vedansh"
    out = c.post(f"/api/projects/{p['id']}/push", json={}, headers=H).get_json()
    assert out["result"]["kind"] == "6-page design" and out["project"]["pushes"][0]["id"] == out["result"]["id"]
    assert out["result"]["edit_url"] in [d["urls"]["edit_url"] for d in mock.designs.values()]
    assert len(c.get("/api/canva/designs").get_json()["designs"]) == 1
    assert c.get("/api/projects").get_json()["projects"][0]["pushed"] is True
    assert c.post("/auth/logout", json={}, headers=H).status_code == 200
    assert c.get("/api/canva/status").get_json()["signed_in"] is False


def test_oauth_cancel(env):
    c, _ = env
    c.get("/auth/login")
    with c.session_transaction() as s:
        pass
    assert "auth_error" in c.get("/oauth/callback?error=access_denied&state=x").headers["Location"]
