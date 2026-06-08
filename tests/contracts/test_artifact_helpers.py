from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models.artifacts import require_artifacts  # noqa: E402


def test_require_artifacts_returns_exact_paths(tmp_path: Path) -> None:
    (tmp_path / "run_manifest.json").write_text("{}", encoding="utf-8")
    (tmp_path / "sample_event_index.csv").write_text("sample_id\n", encoding="utf-8")

    paths = require_artifacts(tmp_path, ["run_manifest.json", "sample_event_index.csv"])

    assert paths["run_manifest.json"] == tmp_path / "run_manifest.json"
    assert paths["sample_event_index.csv"] == tmp_path / "sample_event_index.csv"


def test_require_artifacts_reports_exact_missing_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError) as excinfo:
        require_artifacts(tmp_path, ["split_freeze.json"])

    assert str(tmp_path / "split_freeze.json") in str(excinfo.value)
