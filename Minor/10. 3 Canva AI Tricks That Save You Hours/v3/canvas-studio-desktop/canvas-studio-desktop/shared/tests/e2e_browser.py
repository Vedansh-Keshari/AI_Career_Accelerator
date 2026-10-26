"""Real-browser end-to-end test of the website (Playwright + Chromium).

Usage (from the canva-clone folder):
    pip install playwright && python -m playwright install chromium
    python shared/tests/e2e_browser.py            # starts the website server on port 5000 and tests it
Options via environment: E2E_PYTHON (python to launch the app with), E2E_APP (path to the launcher),
E2E_SHOTS (folder for screenshots), E2E_PORT (default 5000 - the demo sign-in expects the app on 5000).
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
PORT = os.environ.get("E2E_PORT", "5000")
APP = os.environ.get("E2E_APP", str(Path(__file__).resolve().parent / "serve_web.py"))
PY = os.environ.get("E2E_PYTHON", sys.executable)
SHOTS = Path(os.environ.get("E2E_SHOTS", tempfile.mkdtemp(prefix="studio-shots-")))
SHOTS.mkdir(parents=True, exist_ok=True)
BASE = f"http://127.0.0.1:{PORT}"
home = tempfile.mkdtemp(prefix="studio-e2e-home-")
env = dict(os.environ, CANVA_STUDIO_HOME=home, PORT=PORT, NO_BROWSER="1", CANVAS_NO_KEYRING="1")
for k in ("CANVA_CLIENT_ID", "CANVA_CLIENT_SECRET"):
    env.pop(k, None)

srv = subprocess.Popen([PY, APP], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
for _ in range(80):
    try:
        urllib.request.urlopen(BASE + "/api/canva/status")
        break
    except Exception:
        if srv.poll() is not None:
            sys.exit("server exited early:\n" + srv.stdout.read())
        time.sleep(0.5)
else:
    srv.terminate()
    sys.exit("server did not start")

from PIL import Image  # noqa: E402

photo = Path(home) / "photo.png"
Image.new("RGB", (600, 400), "#e91e63").save(photo)
errors, steps = [], []


def step(name):
    steps.append(name)
    print("  ok -", name)


try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        page = ctx.new_page()
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("response", lambda r: errors.append("HTTP %s %s" % (r.status, r.url)) if r.status >= 400 and r.status != 409 else (print("   [409 during step %d]" % len(steps), r.request.method, r.url) if r.status == 409 else None))
        page.goto(BASE + "/")
        expect(page.locator("#newDlg")).to_be_visible()
        page.click("button.ex:has-text('Benefits of yoga')")
        expect(page.locator("#strip .thumb")).to_have_count(6)
        page.wait_for_function("document.querySelector('#preview').naturalWidth > 100")
        step("open the yoga example")

        # ---- free layout editor
        page.click("#tabs button[data-tab=content]")
        page.click("#strip .thumb:nth-child(3)")
        page.click("button:has-text('Edit freely')")
        expect(page.locator("#overlay .el")).to_have_count(2)
        step("switch a slide to free layout")
        page.click("button[data-action=add-el][data-kind=text]")
        expect(page.locator("#overlay .el")).to_have_count(3)
        page.fill("#elText", "Hello from the editor")
        page.wait_for_function("S.saveState === 'saved' && !S.saveTimer")
        page.wait_for_timeout(300)
        sel = page.locator("#overlay .el.sel")
        expect(sel).to_be_visible()
        box = sel.bounding_box()
        before = page.evaluate("(() => { const e = S.p.slides[2].elements.find(x => x.id === S.sel); return [e.x, e.y, e.w, e.h]; })()")
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()
        page.mouse.move(box["x"] + box["width"] / 2 + 120, box["y"] + box["height"] / 2 + 60, steps=8)
        page.mouse.up()
        after = page.evaluate("(() => { const e = S.p.slides[2].elements.find(x => x.id === S.sel); return [e.x, e.y, e.w, e.h]; })()")
        assert after[0] > before[0] + 0.03 and after[1] > before[1] + 0.03 and abs(after[2] - before[2]) < 1e-6, (before, after)
        step("drag a box to move it")
        handle = page.locator("#overlay .el.sel .hd[data-h=se]").bounding_box()
        page.mouse.move(handle["x"] + 6, handle["y"] + 6)
        page.mouse.down()
        page.mouse.move(handle["x"] + 106, handle["y"] + 66, steps=8)
        page.mouse.up()
        resized = page.evaluate("(() => { const e = S.p.slides[2].elements.find(x => x.id === S.sel); return [e.x, e.y, e.w, e.h]; })()")
        assert resized[2] > after[2] + 0.04 and resized[3] > after[3] + 0.04 and abs(resized[0] - after[0]) < 1e-6, (after, resized)
        step("drag a handle to resize")
        page.wait_for_timeout(1000)
        page.screenshot(path=str(SHOTS / "editor.png"))
        # saved on the server with the new geometry
        pid = page.evaluate("S.p.id")
        saved = json.load(urllib.request.urlopen(f"{BASE}/api/projects/{pid}"))
        el = [e for e in saved["slides"][2]["elements"] if e["text"] == "Hello from the editor"][0]
        assert abs(el["x"] - resized[0]) < 1e-3 and abs(el["w"] - resized[2]) < 1e-3
        step("geometry is saved on the server")

        # ---- undo / redo / keyboard
        n = page.evaluate("S.p.slides[2].elements.length")
        page.keyboard.press("Delete")
        page.wait_for_timeout(700)
        assert page.evaluate("S.p.slides[2].elements.length") == n - 1
        page.click("#undoBtn")
        page.wait_for_function(f"S.p.slides[2].elements.length === {n}")
        page.click("#redoBtn")
        page.wait_for_function(f"S.p.slides[2].elements.length === {n - 1}")
        page.click("#undoBtn")
        page.wait_for_function(f"S.p.slides[2].elements.length === {n}")
        page.keyboard.press("Control+z")
        page.wait_for_timeout(900)
        step("undo, redo and keyboard shortcuts")
        page.click("button:has-text('Back to automatic layout')")
        page.wait_for_function("!S.p.slides[2].free")
        step("back to automatic layout")

        # ---- reorder slides by dragging
        first_title = page.evaluate("S.p.slides[0].title")
        page.locator("#strip .thumb").nth(0).drag_to(page.locator("#strip .thumb").nth(3))
        page.wait_for_function(f"S.p.slides[3].title === {json.dumps(first_title)}")
        step("reorder slides by dragging")
        page.click("#undoBtn")
        page.wait_for_function(f"S.p.slides[0].title === {json.dumps(first_title)}")

        # ---- look: font + brand kit via settings
        page.click("#settingsBtn")
        expect(page.locator("#setDlg")).to_be_visible()
        page.fill("#setBname", "Acme")
        page.evaluate("(() => { for (const [id, v] of [['setB1', '#7a1f5c'], ['setB2', '#f4a261']]) { const i = document.getElementById(id); i.value = v; } })()")
        page.select_option("#setBfont", "DejaVu Serif")
        page.click("button[data-action=save-brand]")
        expect(page.locator("#toast")).to_contain_text("Brand kit saved")
        page.click("#setDlg button[data-action=close-settings]")
        page.click("#tabs button[data-tab=look]")
        page.click("button:has-text('Apply my brand kit')")
        page.wait_for_function("S.p.options.color === 'Brand' && S.p.tune.font === 'serif'")
        step("save and apply a brand kit")
        page.select_option("#fontPick", "DejaVu Sans Mono")
        page.wait_for_function("S.p.tune.font === 'mono'")
        step("font picker")
        page.wait_for_timeout(1000)
        page.screenshot(path=str(SHOTS / "brand.png"))

        # ---- conflict from a second tab
        other = ctx.new_page()
        other.goto(BASE + "/")
        other.wait_for_function("typeof S !== 'undefined' && S.p")
        other.fill("#title", "Edited in tab two")
        other.wait_for_timeout(1200)
        page.fill("#title", "Edited in tab one")
        expect(page.locator("#conflict")).to_be_visible(timeout=8000)
        step("second tab edit shows the conflict warning")
        page.click("#conflict button")
        page.wait_for_function("S.p && S.p.title === 'Edited in tab two'")
        other.close()

        # ---- sign in (demo) and push with progress
        page.click("#tabs button[data-tab=canva]")
        page.click("button:has-text('Sign in (demo)')")
        page.wait_for_url("**/api/oauth/authorize**")
        page.fill("input[name=email]", "vedansh@example.com")
        page.click("button[value=allow]")
        page.wait_for_url(BASE + "/")
        expect(page.locator("#canvaChip")).to_contain_text("vedansh")
        step("sign in through the demo Canva page")
        page.click("#tabs button[data-tab=canva]")
        page.click("button:has-text('Push this project to Canva')")
        expect(page.locator("#toast")).to_contain_text("editable design", timeout=30000)
        expect(page.locator("#panel .dlist a").first).to_be_visible()
        link = page.locator("#panel .dlist a").first.get_attribute("href")
        v = ctx.new_page()
        v.goto(link)
        expect(v.locator("body")).to_contain_text("editable slides")
        v.close()
        step("push an editable deck")

        # ---- downloads
        page.click("#downloadMenu summary")
        with page.expect_download() as d:
            page.click("#downloadLinks a:has-text('PowerPoint')")
        path = d.value.path()
        assert Path(path).read_bytes()[:2] == b"PK" and d.value.suggested_filename.endswith(".pptx")
        step("download an editable .pptx")

        # ---- other project types
        page.click("#newBtn")
        page.click("button[data-newtab=idea]")
        page.click("button[data-type=logo]")
        page.fill("#nPrompt", "A mountain bike shop called Ridge Runner, rugged and bright")
        page.click("button:has-text('Create project')")
        page.wait_for_function("S.p && S.p.type === 'logo' && S.p.logo.brand === 'Ridge Runner'")
        expect(page.locator("#strip .thumb")).to_have_count(4)
        step("create a logo from my own idea")
        page.click("#newBtn")
        page.click("button[data-newtab=example]")
        page.click("button.ex:has-text('refined')")
        page.wait_for_function("S.p && S.p.type === 'document'")
        page.click("button:has-text('Add section')")
        page.wait_for_timeout(1200)
        with page.expect_download() as d2:
            page.click("#downloadMenu summary")
            page.click("#downloadLinks a:has-text('Word')")
        assert d2.value.suggested_filename.endswith(".docx")
        step("document: add a section and download .docx")
        page.screenshot(path=str(SHOTS / "document.png"))

        m = b.new_context(viewport={"width": 390, "height": 800}).new_page()
        m.goto(BASE + "/")
        m.wait_for_function("typeof S !== 'undefined' && S.p")
        m.wait_for_function("document.querySelector('#preview').naturalWidth > 100")
        m.screenshot(path=str(SHOTS / "mobile.png"))
        step("phone-sized layout loads")
        b.close()
    bad = [e for e in errors if "favicon" not in e and "409 (CONFLICT)" not in e]  # 409 is the expected answer in the conflict step
    print(f"\nE2E {'OK' if not bad else 'FAILED'}: {len(steps)} steps; console/network errors: {bad}")
    print("Screenshots in", SHOTS)
    sys.exit(1 if bad else 0)
finally:
    srv.terminate()
