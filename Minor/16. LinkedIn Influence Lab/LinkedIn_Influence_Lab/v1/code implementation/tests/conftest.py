import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture()
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("LIL_HOME", str(tmp_path))
    (tmp_path / "sample_data").mkdir()
    (tmp_path / "sample_data" / "sample_profile.json").write_text((ROOT / "sample_data" / "sample_profile.json").read_text())
    return tmp_path


@pytest.fixture()
def profile(home):
    from lil import settings
    p = settings.default_profile()
    p.update(json.loads((ROOT / "sample_data" / "sample_profile.json").read_text()))
    settings.save_profile(p)
    return p
