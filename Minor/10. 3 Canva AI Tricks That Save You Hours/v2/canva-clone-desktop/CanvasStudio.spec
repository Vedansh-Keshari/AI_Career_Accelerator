# PyInstaller recipe for the Windows app. Build with build_windows.bat (or: pyinstaller --noconfirm CanvasStudio.spec)
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
SHARED = os.environ.get("CANVA_SHARED") or os.path.join(ROOT, "shared")

datas = [
    (os.path.join(SHARED, "assets"), "assets"),
    (os.path.join(SHARED, "data"), "data"),
    (os.path.join(SHARED, "studio", "static"), os.path.join("studio", "static")),
    (os.path.join(SHARED, "config.example.json"), "."),
]
# python-pptx and python-docx ship template files that PyInstaller does not find on its own
datas += collect_data_files("pptx") + collect_data_files("docx") + collect_data_files("webview")
hidden = collect_submodules("studio") + collect_submodules("waitress") + [
    "keyring.backends", "keyring.backends.Windows", "keyring.backends.macOS", "keyring.backends.SecretService",
    "webview.platforms.edgechromium", "webview.platforms.winforms", "webview.platforms.cef", "webview.platforms.gtk", "webview.platforms.qt",
    "cryptography.hazmat.backends.openssl", "pptx", "docx",
]
a = Analysis([os.path.join(SPECPATH, "app.py")], pathex=[SHARED], datas=datas, hiddenimports=hidden, noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="CanvasStudio", console=False, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, name="CanvasStudio")
