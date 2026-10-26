"""Run from the canva-clone folder (needs a display; on Linux use xvfb-run):
    xvfb-run -a python -m pytest desktop/tests -q
"""
import sys
import threading
import time
import urllib.parse
from pathlib import Path

import pytest
import requests

DESK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DESK))

tk = pytest.importorskip("tkinter")
import app as desk  # noqa: E402
from studio.canva_client import CanvaClient  # noqa: E402
from studio.mock_canva import MockCanva  # noqa: E402
from studio.paths import load_config  # noqa: E402


@pytest.fixture()
def env(tmp_path, monkeypatch):
    mock = MockCanva(8797).start()
    cfg = load_config("desktop")
    cfg.update(authorize_url=f"{mock.base}/api/oauth/authorize", token_url=f"{mock.base}/rest/v1/oauth/token",
               api_base=f"{mock.base}/rest/v1", redirect_uri="http://127.0.0.1:5101/oauth/callback")
    client = CanvaClient(cfg, home=tmp_path, sleep=lambda s: None)
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display available")
    root.geometry("1360x860")
    app = desk.App(root, cfg, home=tmp_path, client=client)
    opened = []
    monkeypatch.setattr(desk.webbrowser, "open", lambda url, *a, **k: opened.append(url) or True)
    yield app, mock, opened
    try:
        app.cancel_sign_in()
        root.destroy()
    except tk.TclError:
        pass
    mock.stop()


def pump(app, cond, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        app.root.update()
        if cond():
            return True
        time.sleep(0.02)
    return False


def walk(w):
    for c in w.winfo_children():
        yield c
        yield from walk(c)


def fake_browser(url, email="vedansh@example.com", cancel=False):
    """Plays the user's browser: open Canva's page, type the email, follow the redirect to the app."""
    q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
    assert requests.get(url).status_code == 200
    form = {k: q[k] for k in ("client_id", "redirect_uri", "state", "code_challenge", "scope")}
    form.update(email=email, action="cancel" if cancel else "allow")
    loc = requests.post(url.split("?")[0], data=form, allow_redirects=False).headers["Location"]
    time.sleep(0.3)
    requests.get(loc, timeout=10)


def test_starts_empty_and_every_example_opens(env):
    app, mock, _ = env
    assert pump(app, lambda: app.newwin is not None and app.newwin.winfo_exists())  # first run opens New project
    for ex_id, kind in (("yoga-presentation", "presentation"), ("workout-blog-first", "document"), ("cafe-logo", "logo"), ("cafe-logo-bright", "logo")):
        app.start_example(ex_id)
        app.root.update()
        assert app.p["type"] == kind and app.tk_main is not None
        assert len(app.tk_thumbs) == {"presentation": 6, "document": 2, "logo": 4}[kind]
        for tab in ("content", "look", "refine", "canva"):
            app.set_tab(tab)
            app.root.update()
    assert len(app.store.list()) == 4


def test_typing_in_fields_is_saved(env):
    app, *_ = env
    app.start_example("yoga-presentation")
    entries = [w for w in walk(app.panel.inner) if isinstance(w, tk.Entry)]
    entries[0].delete(0, "end")
    entries[0].insert(0, "Yoga for Everyone")
    texts = [w for w in walk(app.panel.inner) if isinstance(w, tk.Text)]
    texts[0].delete("1.0", "end")
    texts[0].insert("1.0", "- one\n- two")
    app.root.update()
    app.title_entry.delete(0, "end")
    app.title_entry.insert(0, "My Deck")
    assert pump(app, lambda: app.store.get(app.p["id"])["title"] == "My Deck", 5)
    saved = app.store.get(app.p["id"])
    assert saved["slides"][0]["title"] == "Yoga for Everyone" and saved["slides"][0]["body"] == "- one\n- two"


def test_slide_and_section_operations(env, tmp_path):
    app, *_ = env
    app.start_example("yoga-presentation")
    n = len(app.p["slides"])
    app.add_slide(); app.dup_slide()
    assert len(app.p["slides"]) == n + 2
    app.move_slide(-1); app.del_slide()
    assert len(app.p["slides"]) == n + 1
    from PIL import Image
    img = tmp_path / "pic.png"
    Image.new("RGB", (500, 300), "#ff0066").save(img)
    app.pick_image(str(img))
    assert app.p["slides"][app.page]["image"].endswith(".jpg") and "image" not in app.status.cget("text").lower().replace("image added", "")
    app.pick_image(str(tmp_path / "missing.png"))
    assert "not a readable image" in app.status.cget("text")
    app.remove_image()
    assert app.p["slides"][app.page]["image"] == ""
    app.start_example("workout-blog-first")
    k = len(app.p["doc"]["sections"])
    app.add_sec(); app.move_sec(k, -1); app.del_sec(0)
    assert len(app.p["doc"]["sections"]) == k


def test_look_refine_and_new_idea(env):
    app, *_ = env
    app.start_example("yoga-presentation")
    app.set_tab("look")
    app.set_color("Purple")
    assert app.p["options"]["color"] == "Purple"
    app.set_tab("refine")
    changes = app.apply_refine("make it brighter and bolder")
    assert app.p["tune"]["boldness"] == 1 and changes
    app.apply_refine("")
    assert "Describe the change" in app.status.cget("text")
    app.create_idea({"type": "document", "prompt": "Write a blog post on sleep, highlighting four benefits", "title": "", "style": "Playful",
                     "color": "Green", "audience": "Casual", "theme": "Health", "doc_type": "Blog post"})
    assert app.p["type"] == "document" and app.p["options"]["color"] == "Green" and len(app.p["doc"]["sections"]) == 7
    app.create_idea({"type": "logo", "prompt": "A bakery called Rise & Shine", "title": ""})
    assert app.p["logo"]["brand"] == "Rise & Shine"


def test_downloads(env, tmp_path):
    app, *_ = env
    app.start_example("yoga-presentation")
    app.save_pdf(str(tmp_path / "deck.pdf"))
    assert (tmp_path / "deck.pdf").read_bytes().startswith(b"%PDF")
    folder = tmp_path / "pngs"; folder.mkdir()
    app.save_pngs(str(folder))
    assert len(list(folder.glob("*.png"))) == 6
    app.start_example("cafe-logo")
    app.save_png_single(str(tmp_path / "logo.png"))
    from PIL import Image
    assert Image.open(tmp_path / "logo.png").size == (1000, 1000)


def test_sign_in_push_and_sign_out(env):
    app, mock, opened = env
    app.start_example("yoga-presentation")
    app.on_push()  # signed out -> starts sign-in instead
    assert pump(app, lambda: opened, 5)
    threading.Thread(target=fake_browser, args=(opened[0],), daemon=True).start()
    assert pump(app, lambda: app.canva["signed_in"], 15), app.status.cget("text")
    assert app.canva["name"] == "vedansh" and "vedansh" in app.chip.cget("text")
    app.on_push()
    assert pump(app, lambda: app.p["pushes"], 20), app.status.cget("text")
    push = app.p["pushes"][0]
    assert push["kind"] == "6-page design" and "Pushed" in app.status.cget("text") and app.last_open_url == push["edit_url"]
    assert mock.files[mock.designs[push["id"]]["file"]][1] == "application/pdf"
    assert app.store.get(app.p["id"])["pushes"][0]["id"] == push["id"]
    app.set_tab("canva")
    assert pump(app, lambda: isinstance(app.recent, list) and len(app.recent) == 1, 10)
    app.start_example("cafe-logo")
    app.on_push()
    assert pump(app, lambda: app.p["pushes"], 20)
    assert app.p["pushes"][0]["kind"] == "image design"
    app.sign_out()
    assert not app.canva["signed_in"] and app.push_btn.cget("text") == "Sign in to push"


def test_sign_in_denied_and_cancelled(env):
    app, mock, opened = env
    app.start_example("cafe-logo")
    app.sign_in()
    assert pump(app, lambda: opened, 5)
    threading.Thread(target=fake_browser, args=(opened[0],), kwargs={"cancel": True}, daemon=True).start()
    assert pump(app, lambda: app.cancel_signin is None, 15)
    assert not app.canva["signed_in"] and "cancelled" in app.status.cget("text").lower()
    opened.clear()
    app.sign_in()
    assert pump(app, lambda: opened, 5)
    app.cancel_sign_in()
    assert pump(app, lambda: app.cancel_signin is None, 10)
    assert "cancelled" in app.status.cget("text").lower()
    app.sign_in()  # port is free again after cancelling
    assert app.cancel_signin is not None
    app.cancel_sign_in()
    assert pump(app, lambda: app.cancel_signin is None, 10)


def test_delete_project(env, monkeypatch):
    app, *_ = env
    app.start_example("cafe-logo")
    monkeypatch.setattr(desk.messagebox, "askyesno", lambda *a, **k: True)
    app.delete_current()
    assert app.p is None and app.store.list() == []
    app.refresh_preview()


def test_screenshot(env):
    app, *_ = env
    app.start_example("yoga-presentation")
    app.set_tab("canva")
    for _ in range(30):
        app.root.update(); time.sleep(0.02)
    try:
        from PIL import ImageGrab
        ImageGrab.grab(xdisplay=None).save("/tmp/e2e/desktop_shot.png")
    except Exception as exc:  # screenshots are best-effort
        print("no screenshot:", exc)
