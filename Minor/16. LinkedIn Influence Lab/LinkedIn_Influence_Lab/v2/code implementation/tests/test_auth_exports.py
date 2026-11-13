import io
import zipfile

import pytest

from lil import auth, exports, paths, samples


def test_admin_passcode_lifecycle(home, monkeypatch):
    monkeypatch.delenv("LIL_ADMIN_PASSCODE", raising=False)
    # redirect the admin file into the temp home so tests never touch the real installation
    monkeypatch.setattr(auth, "_file", lambda: home / "admin.json")
    assert not auth.is_configured() and not auth.verify("anything")
    with pytest.raises(ValueError):
        auth.set_passcode("short")
    auth.set_passcode("correct horse 42")
    assert auth.is_configured() and auth.verify("correct horse 42") and not auth.verify("wrong")
    raw = (home / "admin.json").read_text()
    assert "correct horse" not in raw and "salt" in raw


def test_admin_passcode_from_environment(home, monkeypatch):
    monkeypatch.setenv("LIL_ADMIN_PASSCODE", "from-env-passcode")
    assert auth.env_managed() and auth.verify("from-env-passcode") and not auth.verify("x")
    with pytest.raises(PermissionError):
        auth.set_passcode("another passcode")


def test_zip_downloads_per_set_and_all(sample_ws):
    samples.seed("professional")
    counts = exports.counts()
    assert all(n >= 1 for n in counts.values()), counts
    for key in paths.DELIVERABLES:
        with zipfile.ZipFile(io.BytesIO(exports.zip_set(key))) as z:
            names = z.namelist()
            assert any(n.endswith("_CONTENTS.txt") for n in names) and len(names) == counts[key] + 1
            assert z.testzip() is None
    with zipfile.ZipFile(io.BytesIO(exports.zip_all())) as z:
        names = z.namelist()
        assert len(names) == sum(counts.values()) + 1
        assert {n.split("/")[1] for n in names if n.count("/") >= 2} == {paths.DELIVERABLES[k] for k in paths.DELIVERABLES}
