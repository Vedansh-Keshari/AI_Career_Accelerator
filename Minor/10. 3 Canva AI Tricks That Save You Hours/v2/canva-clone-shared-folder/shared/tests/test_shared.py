"""Run with:  python -m pytest shared/tests -q   (from the canva-clone folder)"""
import io
import sys
import urllib.parse
from pathlib import Path

import pytest
import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from studio import generator as G  # noqa: E402
from studio import models as M  # noqa: E402
from studio import office  # noqa: E402
from studio import options as O  # noqa: E402
from studio import render as R  # noqa: E402
from studio.canva_client import CanvaClient, CanvaError, NotSignedIn, make_pkce, push_project  # noqa: E402
from studio.mock_canva import MockCanva  # noqa: E402
from studio.paths import load_config  # noqa: E402


# ------------------------------------------------------------------ rendering
def test_every_style_color_and_format_renders():
    p = G.project_from_example("yoga-presentation")
    for fmt in O.FORMATS:
        p["options"]["format"] = fmt
        for style in O.STYLES:
            p["options"]["style"] = style
            for color in O.COLORS:
                p["options"]["color"] = color
                pages = R.render_pages(p, scale=0.12)
                assert len(pages) == len(p["slides"])
                assert all(im.width >= 40 for im in pages)


def test_full_size_export_dimensions():
    p = G.project_from_example("yoga-presentation")
    assert R.render_pages(p)[0].size == (1920, 1080)
    p["options"]["format"] = "Presentation (Mobile-First)"
    assert R.render_pages(p)[0].size == (1080, 1920)
    p["options"]["format"] = "Presentation (4:3)"
    assert R.render_pages(p)[0].size == (1440, 1080)


def test_long_and_empty_text_do_not_crash():
    p = M.blank_project("presentation", "x")
    p["slides"] = [
        {"title": "T" * 400, "body": "word " * 500, "layout": "bullets", "image": ""},
        {"title": "", "body": "", "layout": "auto", "image": ""},
        {"title": "Unbroken", "body": "A" * 600, "layout": "statement", "image": ""},
        {"title": "Emoji 😀 and ünïcode", "body": "- one\n- two\n\n- three", "layout": "cta", "image": ""},
    ]
    assert len(R.render_pages(M.clean_project(p), 0.3)) == 4


def test_slide_photo_is_used(tmp_path):
    photo = tmp_path / "p.png"
    Image.new("RGB", (400, 300), "#ff00ff").save(photo)
    p = G.project_from_example("yoga-presentation")
    p["slides"][1]["image"] = str(photo)
    img = R.render_slide(p, 1, size=(960, 540))
    px = img.getpixel((int(960 * 0.80), 270))
    assert px[0] > 200 and px[2] > 200 and px[1] < 80  # magenta photo on the right
    portrait = dict(p, options={**p["options"], "format": "Presentation (Mobile-First)"})
    R.render_slide(portrait, 1, size=(540, 960))


def test_missing_photo_file_is_ignored():
    p = G.project_from_example("yoga-presentation")
    p["slides"][1]["image"] = "/does/not/exist.png"
    R.render_slide(p, 1, size=(480, 270))


def test_document_paginates_and_short_types_are_posts():
    p = G.project_from_example("workout-blog-first")
    p["doc"]["sections"] *= 6
    pages = R.render_pages(M.clean_project(p), 0.3)
    assert len(pages) >= 3
    p["doc"]["doc_type"] = "Tweet"
    post = R.render_pages(M.clean_project(p), 0.5)
    assert len(post) == 1 and post[0].size == (540, 540)


def test_logo_variants_and_icons():
    p = G.project_from_example("cafe-logo")
    assert R.pick_icon(p["logo"]) == "book_steam"
    for icon in O.LOGO_ICONS:
        p["logo"]["icon"] = icon
        for v in range(len(O.LOGO_VARIANTS)):
            assert R.render_logo(p, v, 0.2).size == (200, 200)
    assert len(R.render_logo_variants(p, 0.2)) == 4


def test_boldness_changes_colours():
    base = O.palette_for("Blue", 0)["primary"]
    assert O.palette_for("Blue", 3)["primary"] != base


def test_pdf_export_has_all_pages():
    p = G.project_from_example("yoga-presentation")
    pdf = R.pages_to_pdf(R.render_pages(p, 0.2))
    assert pdf.startswith(b"%PDF") and pdf.count(b"/Type /Page\n") + pdf.count(b"/Type /Page ") >= 1
    with pytest.raises(ValueError):
        R.pages_to_pdf([])


# ------------------------------------------------------------------ generator / models
def test_examples_all_load_and_render():
    for ex in G.load_examples():
        p = G.project_from_example(ex["id"])
        assert R.render_pages(p, 0.15)


def test_build_project_from_own_ideas():
    pres = G.build_project("presentation", "A deck about urban beekeeping for school kids",
                           {"length": "Short and sharp (1 to 5 pages)", "audience": "Educational", "color": "Gold"})
    assert pres["title"] == "Urban Beekeeping for School Kids"
    assert 3 <= len(pres["slides"]) <= 6 and pres["slides"][-1]["layout"] == "cta"
    long_deck = G.build_project("presentation", "about solar power", {"length": "Comprehensive (15+ pages)"})
    assert len(long_deck["slides"]) >= 15
    doc = G.build_project("document", "Write a blog post on sleep, highlighting four benefits", {}, doc_type="Blog post")
    assert len([s for s in doc["doc"]["sections"] if s["heading"].startswith("Reason")]) == 4
    for t in O.DOC_TYPES:
        assert G.build_project("document", "about teamwork", {}, doc_type=t)["doc"]["sections"]
    logo = G.build_project("logo", "A tech startup called Volt & Co that sells fast chargers", {})
    assert logo["logo"]["brand"] == "Volt & Co" and R.pick_icon(logo["logo"]) == "bolt"


def test_refine_rules():
    p = G.project_from_example("yoga-presentation")
    p2, ch = G.refine(p, "make it brighter and bolder")
    assert p2["tune"]["boldness"] == 1 and ch
    p3, _ = G.refine(p2, "Ensure the text is in a readable font size. Fill up slides that look too empty.")
    assert p3["tune"]["text_scale"] > 1.0
    p4, _ = G.refine(p3, "use a different colour palette")
    assert p4["options"]["color"] != p3["options"]["color"]
    p5, _ = G.refine(p4, "make it elegant")
    assert p5["options"]["style"] == "Elegant"
    p6, ch6 = G.refine(p5, "a more interesting non-generic title")
    assert p6["title"] != p5["title"] and p6["slides"][0]["title"] == p6["title"]
    _, ch7 = G.refine(p6, "qwerty")
    assert "No matching tweak" in ch7[0]
    assert len(p6["history"]) == 5


def test_store_roundtrip_and_bad_ids(tmp_path):
    store = M.Store(tmp_path)
    p = store.save(G.project_from_example("cafe-logo"))
    assert store.get(p["id"])["logo"]["brand"] == "Page & Pour"
    assert [x["id"] for x in store.list()] == [p["id"]]
    store.delete(p["id"])
    with pytest.raises(KeyError):
        store.get(p["id"])
    for bad in ("../x", "p_zz", "", "p_0123456789/../../etc"):
        with pytest.raises(KeyError):
            store.get(bad)
    with pytest.raises(ValueError):
        store.save_upload(b"x", "exe")


def test_clean_project_repairs_bad_input():
    p = M.clean_project({"type": "presentation", "options": {"style": "Nope", "color": "Nope", "format": "x"},
                         "tune": {"boldness": 99, "text_scale": 0}, "slides": [{"title": 1}]})
    assert p["options"]["style"] == "Modern" and p["tune"]["boldness"] == 3 and p["tune"]["text_scale"] == 0.7
    assert p["slides"][0]["layout"] == "auto"


# ------------------------------------------------------------------ Canva flow against the demo server
@pytest.fixture()
def canva(tmp_path):
    port = 8799
    mock = MockCanva(port).start()
    cfg = load_config("web")
    cfg.update(
        authorize_url=f"{mock.base}/api/oauth/authorize", token_url=f"{mock.base}/rest/v1/oauth/token",
        api_base=f"{mock.base}/rest/v1", redirect_uri="http://127.0.0.1:5000/oauth/callback",
    )
    client = CanvaClient(cfg, home=tmp_path, sleep=lambda s: None)
    yield client, mock
    mock.stop()


def browser_sign_in(client, email="vedansh@example.com", cancel=False):
    """Plays the part of the browser: open Canva's page, type an email, follow the redirect."""
    verifier, challenge = make_pkce()
    state = "st_" + verifier[:8]
    url = client.authorize_url(state, challenge)
    page = requests.get(url)
    assert page.status_code == 200 and "Sign in with your email" in page.text
    q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
    form = {k: q[k] for k in ("client_id", "redirect_uri", "state", "code_challenge", "scope")}
    form["action"] = "cancel" if cancel else "allow"
    form["email"] = email
    resp = requests.post(url.split("?")[0], data=form, allow_redirects=False)
    assert resp.status_code == 302
    back = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(resp.headers["Location"]).query))
    assert back["state"] == state
    return back, verifier


def test_authorize_url_has_pkce_and_scopes(canva):
    client, _ = canva
    url = client.authorize_url("abc", "chal")
    q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
    assert q["code_challenge_method"] == "s256" and q["response_type"] == "code" and q["state"] == "abc"
    assert "design:content:write" in q["scope"] and "asset:write" in q["scope"]


def test_full_sign_in_and_profile(canva):
    client, _ = canva
    assert not client.is_signed_in()
    back, verifier = browser_sign_in(client)
    client.exchange_code(back["code"], verifier)
    assert client.is_signed_in() and client.profile()["display_name"] == "vedansh"
    client.sign_out()
    assert not client.is_signed_in()
    with pytest.raises(NotSignedIn):
        client.profile()


def test_bad_email_cancel_wrong_verifier_and_reused_code(canva):
    client, mock = canva
    verifier, challenge = make_pkce()
    url = client.authorize_url("s", challenge)
    q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
    form = {k: q[k] for k in ("client_id", "redirect_uri", "state", "code_challenge", "scope")}
    bad = requests.post(url.split("?")[0], data={**form, "email": "not-an-email", "action": "allow"}, allow_redirects=False)
    assert bad.status_code == 200 and "valid email" in bad.text
    back, _ = browser_sign_in(client, cancel=True)
    assert back["error"] == "access_denied"
    back, verifier = browser_sign_in(client)
    with pytest.raises(CanvaError):
        client.exchange_code(back["code"], "wrong-verifier-" + "x" * 30)
    with pytest.raises(CanvaError):  # code is single use (and was burned by the failed try)
        client.exchange_code(back["code"], verifier)
    assert not client.is_signed_in()


def test_token_refresh_and_expiry(canva):
    client, mock = canva
    back, verifier = browser_sign_in(client)
    client.exchange_code(back["code"], verifier)
    first = client.access_token()
    saved = client.tokens.load()
    saved["expires_at"] = 0  # force local expiry
    client.tokens.save(saved)
    assert client.access_token() != first
    # server forgets the access token (e.g. revoked): one automatic refresh, then it works
    mock.access.clear()
    assert client.profile()["display_name"] == "vedansh"
    # refresh token also gone: signed out cleanly
    mock.access.clear()
    mock.refresh.clear()
    with pytest.raises(NotSignedIn):
        client.list_designs()
    assert not client.is_signed_in()


def test_tokens_from_another_server_are_ignored(canva):
    client, _ = canva
    client.tokens.save({"access_token": "x", "api_base": "https://api.canva.com/rest/v1", "client_id": "other", "expires_at": 9e12})
    assert not client.is_signed_in()


def signed_in(client):
    back, verifier = browser_sign_in(client)
    client.exchange_code(back["code"], verifier)


def test_push_logo_as_image_design(canva):
    client, mock = canva
    signed_in(client)
    p = G.project_from_example("cafe-logo")
    result = push_project(client, p)
    assert result["kind"] == "image design" and result["edit_url"].startswith(mock.base)
    page = requests.get(result["edit_url"])
    assert "Page &amp; Pour" in page.text and "<img" in page.text
    design = mock.designs[result["id"]]
    img = Image.open(io.BytesIO(mock.files[design["file"]][0]))
    assert img.size == (1000, 1000)


def test_push_presentation_and_document_as_editable_import(canva):
    client, mock = canva
    signed_in(client)
    for ex, kind, mime in (("yoga-presentation", "6-slide editable design", office.PPTX_MIME),
                           ("workout-blog-first", "2-page editable document", office.DOCX_MIME)):
        result = push_project(client, G.project_from_example(ex))
        assert result["kind"] == kind and result["editable"] is True
        data, got_mime = mock.files[mock.designs[result["id"]]["file"]]
        assert got_mime == mime and data[:2] == b"PK"  # a real zip-based Office file
    assert len(client.list_designs()) == 2


def test_push_short_document_as_single_image(canva):
    client, mock = canva
    signed_in(client)
    p = G.build_project("document", "about teamwork", {}, doc_type="Tweet")
    result = push_project(client, p)
    assert result["kind"] == "image design"
    assert Image.open(io.BytesIO(mock.files[mock.designs[result["id"]]["file"]][0])).size == (1080, 1080)


def test_push_requires_sign_in_and_content(canva):
    client, _ = canva
    with pytest.raises(NotSignedIn):
        push_project(client, G.project_from_example("cafe-logo"))
    signed_in(client)
    empty = M.blank_project("presentation", "x")
    empty["slides"] = []
    with pytest.raises(CanvaError, match="Nothing to push"):
        push_project(client, empty)


def test_api_errors_are_readable(canva):
    client, mock = canva
    signed_in(client)
    with pytest.raises(CanvaError, match="asset not found"):
        client.create_design("t", "Mmissing", 100, 100)
    with pytest.raises(CanvaError, match="between 40 and 8000"):
        client.create_design("t", "Mmissing", 10, 10) if False else client._request(
            "POST", "/designs", json={"design_type": {"type": "custom", "width": 5, "height": 5}})


def test_config_demo_vs_live(monkeypatch):
    monkeypatch.delenv("CANVA_CLIENT_ID", raising=False)
    assert load_config("web")["demo"] is True
    monkeypatch.setenv("CANVA_CLIENT_ID", "OC-abc")
    monkeypatch.setenv("CANVA_CLIENT_SECRET", "sec")
    cfg = load_config("desktop")
    assert cfg["demo"] is False and cfg["api_base"] == "https://api.canva.com/rest/v1"
    assert cfg["authorize_url"] == "https://www.canva.com/api/oauth/authorize"
    assert cfg["redirect_uri"].endswith(":5001/oauth/callback")
