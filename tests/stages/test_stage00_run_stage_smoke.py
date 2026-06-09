from __future__ import annotations

import sys
import json
import re
from pathlib import Path

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models.config import hash_file  # noqa: E402
from lst_models.stages.data_split_label_freeze import run_stage  # noqa: E402


def write_raw_txt(path: Path) -> None:
    rows = ["Date,Time,Open,High,Low,Close,Volume"]
    timestamps = pd.date_range("2020-01-02 09:30", periods=30, freq="1min")
    for idx, ts in enumerate(timestamps):
        close = 100.0 + idx * 0.05
        rows.append(
            f"{ts:%m/%d/%Y},{ts:%H:%M},{close:.2f},{close:.2f},{close:.2f},{close:.2f},100"
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_stage00_run_stage_writes_contract_artifacts(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    raw_file = raw_dir / "ABC.txt"
    write_raw_txt(raw_file)

    raw_manifest = {
        "tickers": ["ABC"],
        "raw_source": {
            "files": {"ABC": {"name": "ABC.txt", "file_id": "abc"}},
            "txt_columns": ["Date", "Time", "Open", "High", "Low", "Close", "Volume"],
            "date_format": "%m/%d/%Y",
            "time_format": "%H:%M",
        },
        "five_minute_recipe": {
            "resample_rule": "5min",
            "market_open": "09:30",
            "market_close": "16:00",
            "agg": {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"},
            "drop_na_subset": ["open", "high", "low", "close", "volume"],
            "output_columns": ["ticker", "timestamp", "open", "high", "low", "close", "volume"],
        },
    }
    raw_manifest_path = tmp_path / "manifest.yaml"
    raw_manifest_path.write_text(yaml.safe_dump(raw_manifest), encoding="utf-8")
    notebook_path = tmp_path / "stage00.ipynb"
    notebook_path.write_text("{}", encoding="utf-8")

    config = {
        "stage_name": "00_data_split_label_freeze",
        "route": "lst_models",
        "scope": "validation_only",
        "holdout_test_contact": False,
        "inputs": {
            "raw_data_manifest": str(raw_manifest_path),
            "notebook_path": str(notebook_path),
            "raw_data_dir": str(raw_dir),
        },
        "outputs": {"output_dir": str(tmp_path / "out")},
        "split": {
            "train_start": "2020-01-02",
            "train_end": "2020-01-03",
            "validation_start": "2020-01-03",
            "validation_end": "2020-01-04",
            "closed_holdout_test_start": "2020-01-04",
        },
        "label_policy": {
            "label_config_id": "h01_bps1p0",
            "operator": "endpoint_cumulative_return",
            "horizon_k": 1,
            "no_trade_band_bps": 1.0,
        },
        "baseline_registry": {
            "mandatory_trivial": [
                "stratified_dummy_train_prior",
                "majority_train_prior",
                "constant_up",
                "constant_down",
            ]
        },
        "provenance": {
            "repo_url": "https://github.com/zkc768/lstm-zhang.git",
            "git_commit": "testcommit",
            "bootstrap_mode": "unit_test",
        },
    }

    result = run_stage(config)

    assert re.fullmatch(r"\d{8}_\d{6}_\d{6}", result.output_dir.name)
    assert result.run_manifest.exists()
    assert result.artifact_inventory.exists()
    assert result.sample_event_index.exists()
    assert (result.output_dir / "baseline_registry.json").exists()
    manifest = json.loads(result.run_manifest.read_text(encoding="utf-8"))
    assert isinstance(manifest["notebook_sha256"], str)
    assert len(manifest["notebook_sha256"]) == 64
    assert len(manifest["config_sha256"]) == 64
    assert len(manifest["runtime_config_sha256"]) == 64
    assert manifest["repo_url"] == "https://github.com/zkc768/lstm-zhang.git"
    assert manifest["git_commit"] == "testcommit"
    assert manifest["bootstrap_mode"] == "unit_test"
    assert manifest["runtime_provenance"]["dependency_versions"]["pandas"]
    assert manifest["holdout_test_contact"] is False
    frozen_raw_manifest = json.loads(
        (result.output_dir / "raw_data_manifest.json").read_text(encoding="utf-8")
    )
    frozen_file_spec = frozen_raw_manifest["raw_source"]["files"]["ABC"]
    assert frozen_file_spec["bytes"] == raw_file.stat().st_size
    assert frozen_file_spec["sha256"] == hash_file(raw_file)
    inventory = pd.read_csv(result.artifact_inventory)
    assert "path" not in inventory.columns
    assert {
        "artifact_name",
        "file_name",
        "relative_path",
        "original_runtime_path",
        "exists",
        "bytes",
        "sha256",
    }.issubset(inventory.columns)
    assert set(inventory["relative_path"]) == {
        "run_manifest.json",
        "raw_data_manifest.json",
        "split_freeze.json",
        "label_policy.json",
        "baseline_registry.json",
        "label_validity_summary.csv",
        "sample_event_index.csv",
    }
    assert inventory["exists"].all()
    assert inventory["bytes"].gt(0).all()
    assert inventory["sha256"].str.fullmatch(r"[0-9a-f]{64}").all()
    sample_events = pd.read_csv(result.sample_event_index)
    assert set(sample_events["split"]) <= {"train", "validation"}
    assert "closed_holdout_test" not in set(sample_events["split"])
