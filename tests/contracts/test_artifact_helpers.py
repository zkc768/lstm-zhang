from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models.artifacts import hash_file, require_artifacts, write_artifact_inventory  # noqa: E402


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


def test_require_artifacts_verifies_inventory_sha256(tmp_path: Path) -> None:
    manifest = tmp_path / "run_manifest.json"
    sample_events = tmp_path / "sample_event_index.csv"
    manifest.write_text("{}", encoding="utf-8")
    sample_events.write_text("sample_id\ns1\n", encoding="utf-8")
    write_artifact_inventory(
        tmp_path,
        {"run_manifest": manifest, "sample_event_index": sample_events},
    )

    paths = require_artifacts(tmp_path, ["run_manifest.json", "sample_event_index.csv"])

    assert paths["run_manifest.json"] == manifest
    assert hash_file(sample_events)


def test_require_artifacts_blocks_inventory_sha256_mismatch(tmp_path: Path) -> None:
    manifest = tmp_path / "run_manifest.json"
    sample_events = tmp_path / "sample_event_index.csv"
    manifest.write_text("{}", encoding="utf-8")
    sample_events.write_text("sample_id\ns1\n", encoding="utf-8")
    write_artifact_inventory(
        tmp_path,
        {"run_manifest": manifest, "sample_event_index": sample_events},
    )
    sample_events.write_text("sample_id\ns1\ns2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="artifact .* mismatch"):
        require_artifacts(tmp_path, ["run_manifest.json", "sample_event_index.csv"])


def test_require_artifacts_allows_legacy_inventory_without_hash_columns(tmp_path: Path) -> None:
    (tmp_path / "run_manifest.json").write_text("{}", encoding="utf-8")
    pd.DataFrame([{"artifact_name": "run_manifest", "file_name": "run_manifest.json"}]).to_csv(
        tmp_path / "artifact_inventory.csv", index=False
    )

    paths = require_artifacts(tmp_path, ["run_manifest.json"])

    assert paths["run_manifest.json"] == tmp_path / "run_manifest.json"
