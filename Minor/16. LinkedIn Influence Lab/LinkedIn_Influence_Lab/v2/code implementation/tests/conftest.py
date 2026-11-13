import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture(autouse=True)
def _reset_resolver():
    from lil import paths
    paths.set_resolver(None)
    yield
    paths.set_resolver(None)


@pytest.fixture()
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("LIL_HOME", str(tmp_path))
    monkeypatch.setenv("LIL_ADMIN_PASSCODE", "")  # tests manage the admin file explicitly
    return tmp_path


@pytest.fixture()
def profile(home):
    from lil import samples, settings
    p = samples.sample_profile("job_seeker")
    settings.save_profile(p)
    return p


@pytest.fixture()
def sample_ws(home):
    from lil import paths
    paths.set_resolver(lambda: "sample")
    return home
