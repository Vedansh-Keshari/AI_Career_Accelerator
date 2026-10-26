"""Windows-sensitive behaviour that can be checked on any OS (spaces, accents, reserved names, line endings,
busy ports, locked files). The Windows-only checks at the bottom run only on Windows.
Run:  python -m pytest shared/tests/test_windows_compat.py -q"""
import json
import socket
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from studio import generator as G  # noqa: E402
from studio import models as M  # noqa: E402
from studio import render as R  # noqa: E402
from studio.paths import SHARED_DIR  # noqa: E402
from studio.secrets_store import SecretStore, Settings  # noqa: E402
from studio.webapp import create_app, run_web  # noqa: E402

H = {"X-Studio": "1"}
ODD_HOMES = ["My Documents & Stuff", "José Núñez (work)", "日本語のフォルダ", "name with   spaces", "a" * 80]


@pytest.mark.parametrize("folder", ODD_HOMES)
def test_app_works_from_a_home_folder_with_spaces_and_accents(tmp_path, folder):
    home = tmp_path / folder / ".canvas_studio"
    home.mkdir(parents=True)
    app = create_app(home=home)
    c = app.test_client()
    p = c.post("/api/projects", json={"mode": "example", "example_id": "yoga-presentation"}, headers=H).get_json()
    assert c.get(f"/api/projects/{p['id']}/page/0.png").status_code == 200
    assert c.put("/api/settings", json={"ai": {"api_key": "sk-abc"}}, headers=H).status_code == 200
    SecretStore(home, use_keyring=False).set("k", "v")
    assert Settings(home).update({"a": 1})["a"] == 1
    for fmt in ("pdf", "pptx", "zip"):
        assert c.get(f"/api/projects/{p['id']}/export.{fmt}").status_code == 200


def test_unusual_titles_become_safe_file_names(tmp_path):
    c = create_app(home=tmp_path).test_client()
    for title, expect in (("Café – 日本語 😀", "caf"), ("CON", "design-con"), ("nul", "design-nul"), ('a<b>:"c"|d?*', "a-b-c-d"), ("   ", "design"), ("x" * 300, "x" * 60)):
        p = c.post("/api/projects", json={"mode": "example", "example_id": "cafe-logo"}, headers=H).get_json()
        p["title"] = title
        c.put(f"/api/projects/{p['id']}", json=p, headers=H)
        r = c.get(f"/api/projects/{p['id']}/export.png")
        name = r.headers["Content-Disposition"].split("filename=")[-1].strip('"')
        assert name == f"{expect}.png" or name.startswith(expect), (title, name)
        assert not set('<>:"/\\|?*') & set(name)


def test_unicode_text_renders_everywhere():
    p = G.project_from_example("workout-blog-refined")
    p["title"] = "Résumé 😀 日本語 — “quotes” ñ"
    p["doc"]["sections"][0]["body"] = "Línea con acentos, 中文 and emoji 😀 — fine."
    assert R.render_pages(M.clean_project(p), 0.3)
    deck = G.project_from_example("yoga-presentation")
    deck["slides"][0]["title"] = "Ünïcödé 日本語 😀"
    assert R.render_pages(M.clean_project(deck), 0.2)


def test_json_files_with_windows_line_endings_load(tmp_path):
    src = (SHARED_DIR / "data" / "test_data.json").read_text(encoding="utf-8")
    crlf = tmp_path / "test_data.json"
    crlf.write_bytes(src.replace("\n", "\r\n").encode("utf-8"))
    assert len(json.loads(crlf.read_text(encoding="utf-8"))["examples"]) == 5
    bom = tmp_path / "bom.json"
    bom.write_bytes(b"\xef\xbb\xbf" + src.encode("utf-8"))
    assert json.loads(bom.read_text(encoding="utf-8-sig"))["examples"]
    (tmp_path / "projects").mkdir()
    p = G.project_from_example("cafe-logo")
    pretty = json.dumps(p, indent=2, ensure_ascii=False).replace("\n", "\r\n")
    (tmp_path / "projects" / f"{p['id']}.json").write_bytes(b"\xef\xbb\xbf" + pretty.encode("utf-8"))   # what Notepad can produce
    assert M.Store(tmp_path).get(p["id"])["logo"]["brand"] == "Page & Pour"


def test_config_json_saved_by_notepad_with_a_bom_is_accepted(tmp_path, monkeypatch):
    from studio import paths
    cfg = tmp_path / "config.json"
    cfg.write_bytes(b"\xef\xbb\xbf" + json.dumps({"canva": {"client_id": "OC-bom", "client_secret": "s"}}).encode("utf-8"))
    monkeypatch.setattr(paths, "SHARED_DIR", tmp_path)
    monkeypatch.delenv("CANVA_CLIENT_ID", raising=False)
    monkeypatch.delenv("CANVA_CLIENT_SECRET", raising=False)
    assert paths.load_config("web")["client_id"] == "OC-bom"


def test_launcher_scripts_have_the_right_line_endings():
    root = SHARED_DIR.parent
    for bat in list(root.glob("run.bat")) + list(root.glob("*/run.bat")) + list((SHARED_DIR / "windows-tests").glob("*.bat")):
        raw = bat.read_bytes()
        assert b"\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b""), f"{bat} must use Windows (CRLF) line endings"
    for sh in list(root.glob("run.sh")) + list(root.glob("*/run.sh")):
        assert b"\r" not in sh.read_bytes(), f"{sh} must use Unix (LF) line endings"


def test_port_in_use_gives_a_plain_message(monkeypatch, tmp_path):
    monkeypatch.setenv("CANVA_STUDIO_HOME", str(tmp_path))
    monkeypatch.setenv("NO_BROWSER", "1")
    monkeypatch.setattr("studio.webapp.ensure_demo_server", lambda: None)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        monkeypatch.setenv("PORT", str(s.getsockname()[1]))
        with pytest.raises(SystemExit) as exc:
            run_web(open_browser=False)
    assert "free number" in str(exc.value)


def test_saving_survives_a_file_another_program_is_holding(tmp_path, monkeypatch):
    """Antivirus and indexers briefly lock files on Windows; the save must retry, not crash or lose data."""
    import os
    store = M.Store(tmp_path)
    p = store.save(G.project_from_example("cafe-logo"))
    real = os.replace
    state = {"fail": 3}

    def locked(a, b):
        if state["fail"] > 0:
            state["fail"] -= 1
            raise PermissionError(32, "The process cannot access the file because it is being used by another process")
        return real(a, b)
    monkeypatch.setattr(os, "replace", locked)
    p["title"] = "survived"
    assert store.save(p)["title"] == "survived" and store.get(p["id"])["title"] == "survived"
    monkeypatch.setattr(os, "replace", lambda a, b: (_ for _ in ()).throw(PermissionError(32, "still locked")))
    with pytest.raises(PermissionError):                         # gives up after a few tries rather than hanging
        store.save(p)


def test_many_saves_from_threads_do_not_corrupt_a_project(tmp_path):
    store = M.Store(tmp_path)
    p = store.save(G.project_from_example("cafe-logo"))
    errors = []

    def worker(n):
        try:
            for i in range(15):
                q = store.get(p["id"])
                q["logo"]["tagline"] = f"worker {n} save {i}"
                store.save(q)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
    threads = [threading.Thread(target=worker, args=(n,)) for n in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors and store.get(p["id"])["logo"]["tagline"].startswith("worker")


def test_server_starts_and_answers_on_a_real_port(tmp_path):
    import urllib.request

    from studio.desktop import make_server
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    server = make_server(create_app(home=tmp_path), "127.0.0.1", port)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    try:
        for _ in range(50):
            try:
                body = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/bootstrap", timeout=2).read()
                break
            except OSError:
                time.sleep(0.1)
        assert b"examples" in body
    finally:
        server.close()


# ---------------------------------------------------------------- run only on Windows
windows_only = pytest.mark.skipif(sys.platform != "win32", reason="Windows only")


@windows_only
def test_credential_manager_is_used_for_the_encryption_key(tmp_path):
    s = SecretStore(tmp_path, use_keyring=True)
    assert s.protected_by == "keyring", "Windows Credential Manager should hold the key"
    s.set("big", "x" * 50000)                                    # far above Credential Manager's size limit: the file holds the data
    assert len(SecretStore(tmp_path, use_keyring=True).get("big")) == 50000


@windows_only
def test_replace_while_another_handle_is_open(tmp_path):
    store = M.Store(tmp_path)
    p = store.save(G.project_from_example("cafe-logo"))
    path = tmp_path / "projects" / f"{p['id']}.json"
    with open(path, "rb") as f:                                  # a reader that is still holding the file
        threading.Timer(0.15, f.close).start()
        p["title"] = "after the reader closed"
        assert store.save(p)["title"] == "after the reader closed"
