"""Run from the canva-clone folder:  python -m pytest desktop/tests -q
These tests start the real local server and stand in for the window toolkit, so they need no display."""
import socket
import sys
import types
import urllib.request
from pathlib import Path

import pytest

DESK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DESK))

import app as desk_launcher  # noqa: E402,F401  (adds the shared folder to sys.path)

from studio import desktop  # noqa: E402


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def desk_env(tmp_path, monkeypatch):
    port = free_port()
    monkeypatch.setenv("CANVA_STUDIO_HOME", str(tmp_path))
    monkeypatch.setenv("CANVA_REDIRECT_URI", f"http://127.0.0.1:{port}/oauth/callback")
    monkeypatch.delenv("CANVA_CLIENT_ID", raising=False)
    monkeypatch.setattr("studio.desktop.ensure_demo_server", lambda: None)
    return port


def listening(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def test_window_shows_the_app_and_server_stops_afterwards(desk_env):
    port, seen = desk_env, {}

    def window(url):
        seen["url"] = url
        seen["html"] = urllib.request.urlopen(url).read().decode()
        seen["boot"] = urllib.request.urlopen(url + "api/bootstrap").read().decode()

    desktop.run_desktop(window_factory=window)
    assert seen["url"] == f"http://127.0.0.1:{port}/" and "Canvas Studio" in seen["html"]
    assert '"desktop":true' in seen["boot"].replace(" ", "")      # the UI knows to use the system browser for sign-in
    assert not listening(port)                                   # closing the window shuts the server down


def test_pywebview_is_called_with_the_right_window(desk_env, monkeypatch):
    calls = {}
    fake = types.ModuleType("webview")
    fake.settings = {}
    fake.create_window = lambda title, url, **kw: calls.update(title=title, url=url, kw=kw)
    fake.start = lambda: calls.update(started=True)
    monkeypatch.setitem(sys.modules, "webview", fake)
    desktop.run_desktop()
    assert calls["title"] == "Canvas Studio" and calls["started"] and calls["url"].startswith("http://127.0.0.1:")
    assert calls["kw"]["width"] >= 1000 and fake.settings.get("ALLOW_DOWNLOADS") is True


def test_falls_back_to_the_browser_when_no_window_toolkit_works(desk_env, monkeypatch, capsys):
    fake = types.ModuleType("webview")
    fake.settings = {}

    def broken(*a, **k):
        raise RuntimeError("WebView2 runtime is not installed")
    fake.create_window = broken
    fake.start = broken
    monkeypatch.setitem(sys.modules, "webview", fake)
    opened = []

    def fake_open(url):
        opened.append(url)
        raise KeyboardInterrupt        # the user closes the console
    monkeypatch.setattr("webbrowser.open", fake_open)
    desktop.run_desktop()
    assert opened and "WebView2" in capsys.readouterr().out
    assert not listening(desk_env)


def test_missing_pywebview_also_falls_back(desk_env, monkeypatch):
    monkeypatch.setitem(sys.modules, "webview", None)            # import webview -> ImportError
    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: (opened.append(url), (_ for _ in ()).throw(KeyboardInterrupt))[0])
    desktop.run_desktop()
    assert opened


def test_port_already_in_use_gives_a_plain_message(desk_env):
    with socket.socket() as blocker:
        blocker.bind(("127.0.0.1", desk_env))
        blocker.listen(1)
        with pytest.raises(SystemExit) as exc:
            desktop.run_desktop(window_factory=lambda url: None)
    assert "already in use" in str(exc.value)


def test_launcher_reports_a_missing_shared_folder(tmp_path, monkeypatch):
    monkeypatch.delenv("CANVA_SHARED", raising=False)
    with pytest.raises(SystemExit) as exc:
        desk_launcher._find_shared(tmp_path / "nowhere" / "desktop")
    assert "shared" in str(exc.value)
    assert desk_launcher._find_shared(Path(desk_launcher.__file__).resolve().parent)   # the copy inside this package is found with no setup
    monkeypatch.setenv("CANVA_SHARED", str(Path(desk_launcher.__file__).resolve().parent / "shared"))
    assert (desk_launcher._find_shared(tmp_path) / "studio").exists()
