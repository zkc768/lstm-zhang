from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models.stages.feature_window_search import run_stage  # noqa: E402


def write_stage00_artifacts(run_dir: Path, *, holdout_contact: bool = False) -> None:
    run_dir.mkdir(parents=True)
    for name in [
        "raw_data_manifest.json",
        "split_freeze.json",
        "label_policy.json",
        "baseline_registry.json",
    ]:
        (run_dir / name).write_text("{}", encoding="utf-8")
    (run_dir / "run_manifest.json").write_text(
        json.dumps({"holdout_test_contact": holdout_contact, "config_sha256": "stage00hash"}),
        encoding="utf-8",
    )
    sample_events = []
    for day in ["2020-01-02", "2020-01-03", "2020-01-06"]:
        timestamps = pd.date_range(f"{day} 09:30", periods=15, freq="5min")
        for ticker in ["AAA", "BBB"]:
            for idx, ts in enumerate(timestamps):
                sample_events.append(
                    {
                        "sample_id": f"{ticker}_{ts:%Y%m%d_%H%M}",
                        "ticker": ticker,
                        "target_timestamp": ts.isoformat(),
                        "trading_day": day,
                        "split": "train",
                        "horizon_k": 1,
                        "horizon_end_timestamp": (ts + pd.Timedelta(minutes=5)).isoformat(),
                        "label": 1 if idx % 2 else 0,
                        "valid_label": True,
                    }
                )
    timestamps = pd.date_range("2020-01-07 09:30", periods=30, freq="5min")
    for idx, ts in enumerate(timestamps):
        sample_events.append(
            {
                "sample_id": f"VAL_{idx}",
                "ticker": "AAA",
                "target_timestamp": ts.isoformat(),
                "trading_day": "2020-01-07",
                "split": "validation",
                "horizon_k": 1,
                "horizon_end_timestamp": (ts + pd.Timedelta(minutes=5)).isoformat(),
                "label": 1,
                "valid_label": True,
            }
        )
    pd.DataFrame(sample_events).to_csv(run_dir / "sample_event_index.csv", index=False)


def stage01_config(tmp_path: Path, stage00_run_dir: Path) -> dict:
    notebook_path = tmp_path / "01_feature_window_search_colab.ipynb"
    notebook_path.write_text("{}", encoding="utf-8")
    return {
        "stage_name": "01_feature_window_search",
        "route": "lst_models",
        "scope": "validation_only",
        "holdout_test_contact": False,
        "inputs": {
            "stage00_run_id": "stage00_test",
            "stage00_runtime_run_dir": str(stage00_run_dir),
            "stage00_drive_path_parts": ["lst_models", "results", "00", "stage00_test"],
            "stage00_run_manifest": str(stage00_run_dir / "run_manifest.json"),
            "raw_data_manifest": "configs/lst_models_data.yaml",
            "notebook_path": str(notebook_path),
            "required_stage00_artifacts": [
                "raw_data_manifest.json",
                "split_freeze.json",
                "label_policy.json",
                "baseline_registry.json",
                "sample_event_index.csv",
                "run_manifest.json",
            ],
        },
        "outputs": {
            "output_dir": str(tmp_path / "out"),
            "manifest": "run_manifest.json",
            "artifact_inventory": "artifact_inventory.csv",
            "summary": "01_feature_window_search_summary.csv",
            "candidate_inputs": "01_candidate_inputs.json",
            "probe_ledger": "01_train_inner_probe_ledger.csv",
            "fold_manifest": "01_train_inner_fold_manifest.csv",
        },
        "feature_sets": {"price_action_core": ["log_return"]},
        "window_sizes": [10, 20, 30],
        "train_inner": {
            "n_folds": 2,
            "seeds": [101],
            "event_overlap_count_required": 0,
            "official_validation_for_selection": False,
        },
        "baseline_probes": {"mandatory_trivial": ["stratified_dummy_train_prior"]},
        "lightweight_probes": {"lightgbm_small": {"enabled": True}},
        "optional_fixed_controls": {"simple_gru": {"enabled": False}},
        "budget": {"max_counted_probe_rows": 20},
        "selection_rules": {
            "primary_metric": "macro_f1",
            "baseline": "stratified_dummy_train_prior",
            "no_final_model_selected": True,
        },
        "stage02_handoff": {
            "recommended_model_families": [
                "lightgbm",
                "dlinear_only",
                "tcn_only",
                "ms_dlinear_tcn",
            ],
            "control_models": ["last_step_lightgbm_control"],
        },
    }


def test_stage01_run_stage_writes_scaffold_contract_artifacts(tmp_path: Path) -> None:
    stage00_run_dir = tmp_path / "stage00"
    write_stage00_artifacts(stage00_run_dir)

    result = run_stage(stage01_config(tmp_path, stage00_run_dir))

    assert result.run_manifest.exists()
    assert result.artifact_inventory.exists()
    assert result.summary.exists()
    assert result.candidate_inputs.exists()
    assert result.probe_ledger.exists()
    assert result.fold_manifest.exists()

    manifest = json.loads(result.run_manifest.read_text(encoding="utf-8"))
    assert manifest["holdout_test_contact"] is False
    assert manifest["no_final_model_selected"] is True
    assert manifest["stage01_execution_mode"] == "contract_scaffold_no_probe_training"

    candidates = json.loads(result.candidate_inputs.read_text(encoding="utf-8"))
    assert candidates["candidate_inputs"] == []
    assert candidates["approved_model_families_for_stage02"] == []
    assert candidates["decision"] == "do_not_start_stage02_probe_fits_not_implemented"
    assert candidates["recommended_model_families_from_protocol"] == [
        "lightgbm",
        "dlinear_only",
        "tcn_only",
        "ms_dlinear_tcn",
    ]

    summary = pd.read_csv(result.summary)
    assert set(summary["window_size"]) == {10, 20, 30}
    assert summary["selected_for_stage02"].eq(False).all()
    assert summary["selection_reason"].eq("no_probe_fits_stage01_scaffold_only").all()
    assert int(summary.loc[summary["window_size"] == 10, "n_samples_total"].iloc[0]) == 36

    ledger = pd.read_csv(result.probe_ledger)
    assert set(ledger["fit_status"]) == {"skipped_not_implemented"}
    assert len(ledger) == 6
    assert ledger["baseline_id"].eq("stratified_dummy_train_prior").all()
    assert ledger["sample_id_hash"].str.fullmatch(r"[0-9a-f]{64}").all()

    folds = pd.read_csv(result.fold_manifest)
    assert folds["event_overlap_count"].eq(0).all()
    assert len(folds) == 2


def test_stage01_rejects_official_validation_selection(tmp_path: Path) -> None:
    stage00_run_dir = tmp_path / "stage00"
    write_stage00_artifacts(stage00_run_dir)
    config = stage01_config(tmp_path, stage00_run_dir)
    config["train_inner"]["official_validation_for_selection"] = True

    with pytest.raises(ValueError, match="train-inner"):
        run_stage(config)


def test_stage01_reports_exact_missing_stage00_artifact(tmp_path: Path) -> None:
    stage00_run_dir = tmp_path / "stage00"
    write_stage00_artifacts(stage00_run_dir)
    (stage00_run_dir / "split_freeze.json").unlink()

    with pytest.raises(FileNotFoundError) as excinfo:
        run_stage(stage01_config(tmp_path, stage00_run_dir))

    assert str(stage00_run_dir / "split_freeze.json") in str(excinfo.value)
