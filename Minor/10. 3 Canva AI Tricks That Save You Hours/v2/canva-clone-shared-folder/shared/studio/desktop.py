"""Desktop shell: the same Canvas Studio UI in its own window (pywebview), served from this machine only."""
from __future__ import annotations

import socket
import threading
import time
import urllib.parse

from .mock_canva import ensure_demo_server
from .paths import load_config
from .secrets_store import SecretStore, Settings
from .webapp import create_app


def _wait_until_listening(host: str, port: int, timeout: float = 10.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        with socket.socket() as s:
            s.settimeout(0.2)
            if s.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.1)
    return False


class StoppableServer:
    """Wraps a waitress (or werkzeug) server so run()/close() can be used from two threads cleanly."""

    def __init__(self, inner, serve_forever, stop):
        self._inner, self._serve, self._stop = inner, serve_forever, stop
        self._closing = False

    def run(self) -> None:
        try:
            self._serve()
        except (OSError, ValueError):
            if not self._closing:  # a closed socket during shutdown is expected; anything else is real
                raise

    def close(self) -> None:
        self._closing = True
        self._stop()


def make_server(app, host: str, port: int) -> StoppableServer:
    """A stoppable local server (waitress when installed)."""
    try:
        from waitress.server import create_server
    except ImportError:
        from werkzeug.serving import make_server as wz_make
        wz = wz_make(host, port, app, threaded=True)
        return StoppableServer(wz, wz.serve_forever, wz.shutdown)
    wt = create_server(app, host=host, port=port, threads=8, ident="CanvasStudio")
    return StoppableServer(wt, wt.run, wt.close)


def run_desktop(window_factory=None) -> None:
    """Start the local server and show it in a native window. Falls back to the default browser if no window toolkit works."""
    secret_store, settings = SecretStore(), Settings()
    cfg = load_config("desktop", secret_store, settings)
    if cfg["demo"]:
        ensure_demo_server()
    parsed = urllib.parse.urlparse(cfg["redirect_uri"])
    host, port = parsed.hostname or "127.0.0.1", parsed.port or 5001
    app = create_app(cfg, app_name="desktop", desktop=True)
    try:
        server = make_server(app, host, port)
    except OSError as exc:
        raise SystemExit(f"Canvas Studio could not start: port {port} is already in use ({exc}). "
                         "Close the other copy of the app, or change desktop_redirect_uri in shared/config.json.") from exc
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    url = f"http://{host}:{port}/"
    if not _wait_until_listening(host, port):
        raise SystemExit("Canvas Studio's local server did not start.")
    try:
        if window_factory is not None:
            window_factory(url)
        else:
            import webview  # pywebview: WebView2 on Windows, WebKit on macOS, GTK/Qt on Linux
            try:
                webview.settings["ALLOW_DOWNLOADS"] = True
            except Exception:  # noqa: BLE001 - older pywebview
                pass
            webview.create_window("Canvas Studio", url, width=1360, height=860, min_size=(1000, 640))
            webview.start()
    except Exception as exc:  # noqa: BLE001 - no usable window toolkit: use the browser instead
        import webbrowser
        print(f"Could not open a window ({exc}). Opening your browser instead - close this console to quit.")
        try:
            webbrowser.open(url)
            while thread.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
    finally:
        server.close()
        thread.join(timeout=5)
