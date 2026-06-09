from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models.stages import feature_window_search as stage01  # noqa: E402
from lst_models.stages import model_hpo_train_inner as stage02  # noqa: E402


def write_stage01_artifacts(
    run_dir: Path,
    *,
    handoff: dict | None = None,
    holdout_contact: bool = False,
    feature_rebuild_code_sha256: str | None = None,
) -> None:
    run_dir.mkdir(parents=True)
    manifest = {"holdout_test_contact": holdout_contact, "config_sha256": "stage01hash"}
    if feature_rebuild_code_sha256 is not None:
        manifest["feature_rebuild_code_sha256"] = feature_rebuild_code_sha256
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    (run_dir / "artifact_inventory.csv").write_text("artifact_name,file_name\n", encoding="utf-8")
    if handoff is None:
        handoff = {
            "route": "lst_models",
            "stage_name": "01_feature_window_search",
            "source_stage00_run_id": "stage00_test",
            "candidate_inputs": [],
            "approved_model_families_for_stage02": [],
            "decision": "do_not_start_stage02_no_feature_window_cell_passed_train_inner_screen",
            "no_final_model_selected": True,
            "holdout_test_contact": False,
        }
    (run_dir / "01_candidate_inputs.json").write_text(json.dumps(handoff), encoding="utf-8")
    if handoff.get("candidate_inputs"):
        summary_rows = [
            {
                "candidate_id": candidate["candidate_id"],
                "selected_for_stage02": True,
                "n_samples_total": 6,
                "n_samples_by_ticker_json": json.dumps({"AAA": 3, "BBB": 3}, sort_keys=True),
            }
            for candidate in handoff["candidate_inputs"]
        ]
    else:
        summary_rows = [
            {
                "candidate_id": "price_action_core_w10",
                "selected_for_stage02": False,
                "n_samples_total": 0,
                "n_samples_by_ticker_json": "{}",
            }
        ]
    pd.DataFrame(summary_rows).to_csv(
        run_dir / "01_feature_window_search_summary.csv", index=False
    )
    pd.DataFrame([{"probe_id": "lightgbm_small", "fit_status": "skipped"}]).to_csv(
        run_dir / "01_train_inner_probe_ledger.csv", index=False
    )
    pd.DataFrame([{"fold_id": "fold_0", "event_overlap_count": 0}]).to_csv(
        run_dir / "01_train_inner_fold_manifest.csv", index=False
    )


def write_search_space(path: Path, family: str, profile_ids: list[str]) -> None:
    path.parent.mkdir(parents=True)
    payload = {
        "model_family": family,
        "search_mode": "bounded_profiles",
        "profiles": [{"profile_id": profile_id} for profile_id in profile_ids],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def stage02_config(tmp_path: Path, stage01_run_dir: Path) -> dict:
    notebook_path = tmp_path / "02_model_hpo_train_inner_colab.ipynb"
    notebook_path.write_text("{}", encoding="utf-8")
    search_root = tmp_path / "search_spaces"
    for family in ["lightgbm", "standard_dlinear", "tcn", "ms_dlinear_tcn"]:
        write_search_space(search_root / family / "search_space.yaml", family, ["p01", "p02"])
    return {
        "stage_name": "02_model_hpo_train_inner",
        "route": "lst_models",
        "scope": "validation_only",
        "holdout_test_contact": False,
        "inputs": {
            "stage00_run_id": "stage00_test",
            "stage00_runtime_run_dir": str(tmp_path / "stage00"),
            "raw_data_manifest": str(tmp_path / "raw.yaml"),
            "raw_data_dir": str(tmp_path / "raw"),
            "required_stage00_artifacts": [
                "raw_data_manifest.json",
                "split_freeze.json",
                "label_policy.json",
                "baseline_registry.json",
                "sample_event_index.csv",
                "run_manifest.json",
            ],
            "stage01_run_id": "stage01_test",
            "stage01_runtime_run_dir": str(stage01_run_dir),
            "stage01_drive_path_parts": ["lst_models", "results", "01", "stage01_test"],
            "stage01_candidate_inputs": str(stage01_run_dir / "01_candidate_inputs.json"),
            "notebook_path": str(notebook_path),
            "required_stage01_artifacts": [
                "run_manifest.json",
                "artifact_inventory.csv",
                "01_candidate_inputs.json",
                "01_feature_window_search_summary.csv",
                "01_train_inner_probe_ledger.csv",
                "01_train_inner_fold_manifest.csv",
            ],
        },
        "outputs": {
            "output_dir": str(tmp_path / "out"),
            "manifest": "run_manifest.json",
            "artifact_inventory": "artifact_inventory.csv",
            "summary": "02_model_hpo_train_inner_summary.csv",
            "hpo_plan_ledger": "02_hpo_plan_ledger.csv",
            "hpo_trial_ledger": "02_hpo_trial_ledger.csv",
            "hpo_summary": "02_hpo_summary.csv",
            "baseline_control_summary": "02_baseline_control_summary.csv",
            "frozen_candidate": "02_frozen_candidate.json",
            "frozen_candidate_markdown": "02_frozen_candidate.md",
            "frozen_params_dir": "frozen_params",
            "best_params_by_family": "02_best_params_by_family.json",
            "stage03_handoff": "02_stage03_handoff.json",
        },
        "train_inner": {
            "n_folds": 2,
            "seeds": [101],
            "official_validation_for_selection": False,
            "event_overlap_count_required": 0,
        },
        "hpo_families": {
            family: {
                "enabled": family in ["lightgbm", "standard_dlinear"],
                "search_space": str(search_root / family / "search_space.yaml"),
            }
            for family in ["lightgbm", "standard_dlinear", "tcn", "ms_dlinear_tcn"]
        },
        "baseline_controls": {
            "mandatory": [
                "stratified_dummy_train_prior",
                "majority_train_prior",
                "constant_up",
                "constant_down",
            ]
        },
        "optional_fixed_controls": {"simple_gru": {"enabled": False}},
        "budget": {"max_hpo_plan_rows": 20, "max_profiles_per_family": 2},
        "hpo_sample_policy": {"max_train_samples_per_fold": 0, "max_eval_samples_per_fold": 0},
        "lightgbm_training_defaults": {
            "eval_metric": "binary_logloss",
            "early_stopping_rounds": 25,
            "early_stopping_validation_source": "inner_train_chronological_tail",
            "early_stopping_validation_fraction": 0.2,
            "minimum_early_stopping_train_samples": 2,
            "minimum_early_stopping_validation_samples": 1,
        },
        "probe_training_defaults": {
            "torch": {
                "epochs": 1,
                "batch_size": 16,
                "learning_rate": 0.001,
                "weight_decay": 0.0001,
                "device": "cpu",
                "require_gpu": False,
            }
        },
        "checkpointing": {"enabled": False},
        "selection_rules": {
            "primary_metric": "macro_f1",
            "baseline": "stratified_dummy_train_prior",
            "require_completed_rows_before_stage03": True,
            "minimum_positive_ticker_count": 2,
            "max_selected_configs_per_family": 1,
            "no_official_validation_selection": True,
            "no_final_model_selected": True,
        },
        "stage03_handoff": {"allowed_when_hpo_complete": True},
    }


def candidate_handoff() -> dict:
    return {
        "route": "lst_models",
        "stage_name": "01_feature_window_search",
        "source_stage00_run_id": "stage00_test",
        "candidate_inputs": [
            {
                "candidate_id": "price_action_core_w2",
                "feature_set": "price_action_core",
                "feature_columns": ["f1", "f2"],
                "window_size": 2,
            }
        ],
        "approved_model_families_for_stage02": ["lightgbm", "standard_dlinear"],
        "decision": "selected_candidate_inputs_for_stage02_train_inner_hpo",
        "no_final_model_selected": True,
        "holdout_test_contact": False,
    }


def patch_fake_stage02_execution(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    stage00_manifest = tmp_path / "stage00_manifest.json"
    stage00_manifest.write_text(json.dumps({"holdout_test_contact": False}), encoding="utf-8")
    folds = pd.DataFrame(
        [
            {
                "fold_id": "fold_0",
                "train_start": "2026-01-01T09:35:00",
                "train_end_exclusive": "2026-01-02T09:35:00",
                "eval_start": "2026-01-02T09:35:00",
                "eval_end_exclusive": "2026-01-03T09:35:00",
                "purge_or_embargo_policy": "test_chronological",
                "n_train_samples": 2,
                "n_eval_samples": 2,
                "event_overlap_count": 0,
            },
            {
                "fold_id": "fold_1",
                "train_start": "2026-01-01T09:35:00",
                "train_end_exclusive": "2026-01-03T09:35:00",
                "eval_start": "2026-01-03T09:35:00",
                "eval_end_exclusive": "2026-01-04T09:35:00",
                "purge_or_embargo_policy": "test_chronological",
                "n_train_samples": 4,
                "n_eval_samples": 2,
                "event_overlap_count": 0,
            },
        ]
    )
    context = stage02.Stage02DataContext(
        stage00_paths={"run_manifest.json": stage00_manifest},
        stage00_manifest={"holdout_test_contact": False},
        raw_manifest={},
        split_freeze={},
        train_events=pd.DataFrame(),
        feature_frame=pd.DataFrame(),
        folds=folds,
    )
    monkeypatch.setattr(stage02, "_load_stage02_data_context", lambda config, handoff: context)

    metadata = pd.DataFrame(
        [
            _sample("s1", "AAA", "2026-01-01", 0),
            _sample("s2", "BBB", "2026-01-01", 1),
            _sample("s3", "AAA", "2026-01-02", 0),
            _sample("s4", "BBB", "2026-01-02", 1),
            _sample("s5", "AAA", "2026-01-03", 0),
            _sample("s6", "BBB", "2026-01-03", 1),
        ]
    )
    feature_blocks = {}
    for row_index, row in metadata.iterrows():
        key = (str(row["ticker"]), str(row["trading_day"]))
        feature_blocks[key] = np.asarray(
            [[row_index + 1.0, row_index + 2.0], [row_index + 3.0, row_index + 4.0]],
            dtype=np.float32,
        )
    dataset = stage01.CandidateDataset(
        metadata=metadata,
        feature_blocks=feature_blocks,
        feature_columns=("f1", "f2"),
        window_size=2,
    )
    monkeypatch.setattr(stage02, "_prepare_candidate_dataset", lambda candidate, context: dataset)

    def fake_fit(**kwargs):
        eval_meta = kwargs["eval_meta"]
        return {
            "fit_status": "completed",
            "macro_f1": 1.0,
            "balanced_accuracy": 1.0,
            "accuracy": 1.0,
            "roc_auc": 1.0,
            "mcc": 1.0,
            "error_message": "",
            "positive_ticker_count": int(eval_meta["ticker"].nunique()),
            "ticker_delta_macro_f1_json": "{}",
            "block_delta_macro_f1_json": "{}",
            "requested_device": "cpu",
            "resolved_device": "cpu",
            "device_fallback_reason": "test_fake_fit",
            "best_iteration": 1,
        }

    monkeypatch.setattr(stage02, "_fit_stage02_model", fake_fit)


def _sample(sample_id: str, ticker: str, day: str, label: int) -> dict:
    timestamp = pd.Timestamp(f"{day}T09:35:00")
    return {
        "sample_id": sample_id,
        "ticker": ticker,
        "target_timestamp": timestamp,
        "trading_day": day,
        "label": label,
        "window_start_position": 0,
        "window_end_position_exclusive": 2,
        "candidate_id": "price_action_core_w2",
        "feature_set": "price_action_core",
        "window_size": 2,
    }


def test_stage02_selection_blocks_below_positive_ticker_floor(tmp_path: Path) -> None:
    config = stage02_config(tmp_path, tmp_path / "stage01")
    hpo_summary = pd.DataFrame(
        [
            {
                "candidate_id": "c1",
                "feature_set": "price_action_core",
                "window_size": 2,
                "model_family": "lightgbm",
                "probe_id": "lightgbm_small",
                "hpo_profile_id": "p01",
                "hpo_profile_params_json": "{}",
                "expected_rows": 1,
                "completed_rows": 1,
                "failed_rows": 0,
                "mean_macro_f1": 1.0,
                "mean_balanced_accuracy": 1.0,
                "mean_roc_auc": 1.0,
                "mean_mcc": 1.0,
                "mean_delta_macro_f1_vs_stratified_dummy_train_prior": 0.1,
                "lcb_delta_macro_f1_vs_stratified_dummy_train_prior": 0.1,
                "mean_delta_macro_f1_vs_majority_train_prior": 0.1,
                "lcb_delta_macro_f1_vs_majority_train_prior": 0.1,
                "min_positive_ticker_count": 1,
                "mean_positive_ticker_count": 1,
                "selected_role": "",
                "selection_reason": "",
            }
        ]
    )
    trial_ledger = pd.DataFrame([{"fit_status": "completed"}])

    decision = stage02._select_frozen_candidates(hpo_summary, trial_ledger, config)

    assert decision["ready_for_stage03"] is False
    assert decision["block_reason"] == "no_hpo_candidate_cleared_baseline_or_ticker_robustness_gates"


def test_lightgbm_early_stopping_split_uses_inner_train_tail_only() -> None:
    train_meta = pd.DataFrame(
        [
            _sample("s1", "AAA", "2026-01-01", 0),
            _sample("s2", "BBB", "2026-01-01", 1),
            _sample("s3", "AAA", "2026-01-02", 0),
            _sample("s4", "BBB", "2026-01-02", 1),
        ]
    )
    x_train = np.arange(8, dtype=np.float32).reshape(4, 2)
    y_train = train_meta["label"].to_numpy(dtype=int)
    split = stage02._lightgbm_inner_train_early_stopping_split(
        x_train=x_train,
        y_train=y_train,
        train_meta=train_meta,
        training_defaults={
            "early_stopping_validation_fraction": 0.5,
            "minimum_early_stopping_train_samples": 2,
            "minimum_early_stopping_validation_samples": 2,
        },
        early_rounds=5,
    )

    assert split["early_stopping_used"] is True
    assert split["early_stopping_source"] == "inner_train_chronological_tail"
    assert split["early_stopping_train_sample_id_hash"] == stage01._sample_id_hash(["s1", "s2"])
    assert split["early_stopping_eval_sample_id_hash"] == stage01._sample_id_hash(["s3", "s4"])


def test_lightgbm_early_stopping_split_respects_minimum_validation_rows() -> None:
    train_meta = pd.DataFrame(
        [
            _sample("s1", "AAA", "2026-01-01", 0),
            _sample("s2", "BBB", "2026-01-01", 1),
            _sample("s3", "AAA", "2026-01-02", 0),
            _sample("s4", "BBB", "2026-01-02", 1),
            _sample("s5", "AAA", "2026-01-03", 0),
            _sample("s6", "BBB", "2026-01-03", 1),
        ]
    )
    x_train = np.arange(12, dtype=np.float32).reshape(6, 2)
    y_train = train_meta["label"].to_numpy(dtype=int)

    split = stage02._lightgbm_inner_train_early_stopping_split(
        x_train=x_train,
        y_train=y_train,
        train_meta=train_meta,
        training_defaults={
            "early_stopping_validation_fraction": 0.2,
            "minimum_early_stopping_train_samples": 5,
            "minimum_early_stopping_validation_samples": 2,
        },
        early_rounds=5,
    )

    assert split["early_stopping_used"] is False
    assert split["early_stopping_reason"] == "insufficient_inner_train_rows_for_minimum_validation_subsplit"
    assert split["early_stopping_eval_sample_id_hash"] == ""


def test_lightgbm_hpo_trial_true_fit_uses_inner_train_tail_eval_set() -> None:
    pytest.importorskip("lightgbm")
    train_meta = pd.DataFrame(
        [
            _sample("s1", "AAA", "2026-01-01", 0),
            _sample("s2", "BBB", "2026-01-01", 1),
            _sample("s3", "AAA", "2026-01-02", 0),
            _sample("s4", "BBB", "2026-01-02", 1),
            _sample("s5", "AAA", "2026-01-03", 0),
            _sample("s6", "BBB", "2026-01-03", 1),
            _sample("s7", "AAA", "2026-01-04", 0),
            _sample("s8", "BBB", "2026-01-04", 1),
        ]
    )
    x_train = np.asarray(
        [
            [0.0, 0.0],
            [1.0, 0.0],
            [0.1, 0.1],
            [1.1, 0.1],
            [0.2, 0.2],
            [1.2, 0.2],
            [0.3, 0.3],
            [1.3, 0.3],
        ],
        dtype=np.float32,
    )
    eval_meta = pd.DataFrame(
        [
            _sample("e1", "AAA", "2026-01-05", 0),
            _sample("e2", "BBB", "2026-01-05", 1),
            _sample("e3", "AAA", "2026-01-06", 1),
            _sample("e4", "BBB", "2026-01-06", 0),
        ]
    )
    x_eval = np.asarray([[0.05, 0.0], [1.05, 0.0], [0.15, 0.1], [1.15, 0.1]], dtype=np.float32)

    outcome = stage02._fit_lightgbm_hpo_trial(
        profile={
            "profile_id": "lgbm_test",
            "num_leaves": 3,
            "max_depth": 2,
            "min_data_in_leaf": 1,
            "learning_rate": 0.1,
            "n_estimators": 20,
            "feature_fraction": 1.0,
            "bagging_fraction": 1.0,
            "class_weight": None,
        },
        x_train=x_train,
        y_train=train_meta["label"].to_numpy(dtype=int),
        train_meta=train_meta,
        x_eval=x_eval,
        y_eval=eval_meta["label"].to_numpy(dtype=int),
        eval_meta=eval_meta,
        seed=101,
        baseline_predictions=np.zeros(len(eval_meta), dtype=int),
        config={
            "lightgbm_training_defaults": {
                "eval_metric": "binary_logloss",
                "early_stopping_rounds": 2,
                "early_stopping_validation_fraction": 0.25,
                "minimum_early_stopping_train_samples": 4,
                "minimum_early_stopping_validation_samples": 2,
            }
        },
    )

    assert outcome["fit_status"] == "completed"
    assert outcome["early_stopping_used"] is True
    assert outcome["early_stopping_source"] == "inner_train_chronological_tail"
    assert outcome["early_stopping_train_sample_id_hash"] == stage01._sample_id_hash(
        ["s1", "s2", "s3", "s4", "s5", "s6"]
    )
    assert outcome["early_stopping_eval_sample_id_hash"] == stage01._sample_id_hash(["s7", "s8"])
    assert "best_iteration" in outcome
    assert np.isfinite(float(outcome["macro_f1"]))
    assert np.isfinite(float(outcome["balanced_accuracy"]))


def test_torch_early_stopping_split_uses_inner_train_tail_only() -> None:
    train_meta = pd.DataFrame(
        [
            _sample("s1", "AAA", "2026-01-01", 0),
            _sample("s2", "BBB", "2026-01-01", 1),
            _sample("s3", "AAA", "2026-01-02", 0),
            _sample("s4", "BBB", "2026-01-02", 1),
        ]
    )
    train_3d = np.arange(8, dtype=np.float32).reshape(4, 2, 1)
    y_train = train_meta["label"].to_numpy(dtype=int)

    split = stage01._torch_inner_train_early_stopping_split(
        train_3d=train_3d,
        y_train=y_train,
        train_meta=train_meta,
        torch_defaults={
            "early_stopping": "inner_train_chronological_tail",
            "early_stopping_validation_fraction": 0.5,
            "minimum_early_stopping_train_samples": 2,
            "minimum_early_stopping_validation_samples": 2,
        },
    )

    assert split["early_stopping_used"] is True
    assert split["early_stopping_source"] == "inner_train_chronological_tail"
    assert split["early_stopping_train_sample_id_hash"] == stage01._sample_id_hash(["s1", "s2"])
    assert split["early_stopping_eval_sample_id_hash"] == stage01._sample_id_hash(["s3", "s4"])
    assert split["y_fit"].tolist() == [0, 1]
    assert split["y_stop"].tolist() == [0, 1]


def test_torch_early_stopping_split_respects_minimum_validation_rows() -> None:
    train_meta = pd.DataFrame(
        [
            _sample("s1", "AAA", "2026-01-01", 0),
            _sample("s2", "BBB", "2026-01-01", 1),
            _sample("s3", "AAA", "2026-01-02", 0),
            _sample("s4", "BBB", "2026-01-02", 1),
            _sample("s5", "AAA", "2026-01-03", 0),
            _sample("s6", "BBB", "2026-01-03", 1),
        ]
    )
    train_3d = np.arange(12, dtype=np.float32).reshape(6, 2, 1)
    y_train = train_meta["label"].to_numpy(dtype=int)

    split = stage01._torch_inner_train_early_stopping_split(
        train_3d=train_3d,
        y_train=y_train,
        train_meta=train_meta,
        torch_defaults={
            "early_stopping": "inner_train_chronological_tail",
            "early_stopping_validation_fraction": 0.2,
            "minimum_early_stopping_train_samples": 5,
            "minimum_early_stopping_validation_samples": 2,
        },
    )

    assert split["early_stopping_used"] is False
    assert split["early_stopping_reason"] == "insufficient_inner_train_rows_for_minimum_validation_subsplit"
    assert split["early_stopping_eval_sample_id_hash"] == ""


def test_stage02_blocks_when_stage01_has_no_candidates(tmp_path: Path) -> None:
    stage01_run_dir = tmp_path / "stage01"
    write_stage01_artifacts(stage01_run_dir)

    result = stage02.run_stage(stage02_config(tmp_path, stage01_run_dir))

    assert result.run_manifest.exists()
    assert result.artifact_inventory.exists()
    assert result.summary.exists()
    assert result.hpo_plan_ledger.exists()
    assert result.hpo_trial_ledger.exists()
    assert result.hpo_summary.exists()
    assert result.baseline_control_summary.exists()
    assert result.frozen_candidate.exists()
    assert result.frozen_candidate_markdown.exists()
    assert result.best_params_by_family.exists()
    assert result.stage03_handoff.exists()

    manifest = json.loads(result.run_manifest.read_text(encoding="utf-8"))
    assert manifest["holdout_test_contact"] is False
    assert manifest["no_final_model_selected"] is True
    assert manifest["stage02_execution_mode"] == "blocked_by_stage01_no_candidate_inputs"

    summary = pd.read_csv(result.summary)
    assert summary.loc[0, "status"] == "blocked"
    assert summary.loc[0, "decision"] == "do_not_start_stage03_stage02_blocked_by_stage01"

    ledger = pd.read_csv(result.hpo_plan_ledger)
    assert list(ledger.columns)
    assert ledger.empty

    handoff = json.loads(result.stage03_handoff.read_text(encoding="utf-8"))
    assert handoff["ready_for_stage03"] is False
    assert handoff["holdout_test_contact"] is False


def test_stage02_blocks_when_stage01_feature_rebuild_hash_differs(tmp_path: Path) -> None:
    stage01_run_dir = tmp_path / "stage01"
    write_stage01_artifacts(
        stage01_run_dir,
        feature_rebuild_code_sha256="0" * 64,
    )

    with pytest.raises(ValueError, match="Stage 01 feature rebuild code hash"):
        stage02.run_stage(stage02_config(tmp_path, stage01_run_dir))


def test_stage02_blocks_when_rebuilt_candidate_counts_differ_from_stage01_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stage01_run_dir = tmp_path / "stage01"
    write_stage01_artifacts(stage01_run_dir, handoff=candidate_handoff())
    summary_path = stage01_run_dir / "01_feature_window_search_summary.csv"
    summary = pd.read_csv(summary_path)
    summary.loc[0, "n_samples_total"] = 999
    summary.to_csv(summary_path, index=False)
    patch_fake_stage02_execution(monkeypatch, tmp_path)

    with pytest.raises(ValueError, match="rebuilt sample count mismatch"):
        stage02.run_stage(stage02_config(tmp_path, stage01_run_dir))


def test_stage02_runs_formal_hpo_rows_for_stage01_candidates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stage01_run_dir = tmp_path / "stage01"
    write_stage01_artifacts(stage01_run_dir, handoff=candidate_handoff())
    patch_fake_stage02_execution(monkeypatch, tmp_path)

    result = stage02.run_stage(stage02_config(tmp_path, stage01_run_dir))

    manifest = json.loads(result.run_manifest.read_text(encoding="utf-8"))
    assert manifest["stage02_execution_mode"] == "formal_train_inner_hpo_completed"
    assert manifest["official_validation_for_selection"] is False
    assert manifest["search_space_sha256"]
    assert manifest["fold_design_sha256"]
    assert manifest["random_seeds"] == [101]
    assert "git_commit" in manifest
    assert "git_commit_reason" in manifest
    assert manifest["raw_file_integrity"]["status"] == "not_available"
    assert len(manifest["stage02_feature_rebuild_code_sha256"]) == 64
    assert manifest["source_stage01_feature_rebuild_code_sha256"] is None
    assert manifest["feature_rebuild_code_match"] is None
    assert manifest["feature_rebuild_code_match_reason"] == "stage01_manifest_field_missing_legacy_run"

    ledger = pd.read_csv(result.hpo_trial_ledger)
    assert len(ledger) == 8
    assert set(ledger["model_family"]) == {"lightgbm", "standard_dlinear"}
    assert set(ledger["fit_status"]) == {"completed"}
    assert ledger["selected_for_stage03"].any()
    assert "early_stopping_source" in ledger.columns
    assert "early_stopping_used" in ledger.columns

    plan_ledger = pd.read_csv(result.hpo_plan_ledger)
    assert len(plan_ledger) == len(ledger)
    assert set(plan_ledger["plan_status"]) == {"planned"}
    assert "macro_f1" not in plan_ledger.columns
    assert "fit_status" not in plan_ledger.columns
    assert "selected_for_stage03" not in plan_ledger.columns
    assert hashlib.sha256(result.hpo_plan_ledger.read_bytes()).hexdigest() != hashlib.sha256(
        result.hpo_trial_ledger.read_bytes()
    ).hexdigest()

    baseline_summary = pd.read_csv(result.baseline_control_summary)
    assert set(baseline_summary["baseline_id"]) == {
        "stratified_dummy_train_prior",
        "majority_train_prior",
        "constant_up",
        "constant_down",
    }
    assert baseline_summary["sample_id_hash"].equals(baseline_summary["eval_sample_id_hash"])

    hpo_summary = pd.read_csv(result.hpo_summary)
    assert len(hpo_summary) == 4
    assert {"primary", "fallback"}.issubset(set(hpo_summary["selected_role"]))

    frozen_candidate = json.loads(result.frozen_candidate.read_text(encoding="utf-8"))
    assert frozen_candidate["ready_for_stage03"] is True
    assert frozen_candidate["primary_candidate"]
    assert frozen_candidate["fallback_candidate"]
    assert frozen_candidate["primary_candidate"]["model_family"] != frozen_candidate["fallback_candidate"]["model_family"]
    assert frozen_candidate["selection_rules"]["minimum_positive_ticker_count"] == 2
    assert frozen_candidate["selection_rules"]["candidate_ranking_scope"] == "within_candidate_input_then_candidate_winners"
    assert frozen_candidate["fold_design"]["official_validation_for_selection"] is False
    assert frozen_candidate["row_contract"]["same_row_baselines"] is True
    assert frozen_candidate["preprocessing_contract"]["fit_scope"] == "inner_train_rows_only"
    assert frozen_candidate["seed_policy"]["train_inner_seeds"] == [101]
    assert frozen_candidate["device_provenance"]["requested_device"] == "cpu"
    assert frozen_candidate["artifact_references"]["hpo_trial_ledger"] == "02_hpo_trial_ledger.csv"

    handoff = json.loads(result.stage03_handoff.read_text(encoding="utf-8"))
    assert handoff["ready_for_stage03"] is True
    assert handoff["holdout_test_contact"] is False


def test_stage02_run_ids_do_not_merge_fast_repeated_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stage01_run_dir = tmp_path / "stage01"
    write_stage01_artifacts(stage01_run_dir, handoff=candidate_handoff())
    patch_fake_stage02_execution(monkeypatch, tmp_path)
    config = stage02_config(tmp_path, stage01_run_dir)

    first = stage02.run_stage(config)
    second = stage02.run_stage(config)

    assert first.output_dir != second.output_dir
    assert first.output_dir.exists()
    assert second.output_dir.exists()
    assert len(first.output_dir.name.split("_")) == 3
    assert len(second.output_dir.name.split("_")) == 3
    assert len(first.output_dir.name.split("_")[-1]) == 6
    assert len(second.output_dir.name.split("_")[-1]) == 6
    assert first.output_dir.name.split("_")[-1].isdigit()
    assert second.output_dir.name.split("_")[-1].isdigit()


def test_stage02_rejects_stage01_holdout_contact(tmp_path: Path) -> None:
    stage01_run_dir = tmp_path / "stage01"
    write_stage01_artifacts(stage01_run_dir, holdout_contact=True)

    with pytest.raises(ValueError, match="holdout_test_contact=false"):
        stage02.run_stage(stage02_config(tmp_path, stage01_run_dir))


def test_stage02_rejects_unknown_stage01_family(tmp_path: Path) -> None:
    stage01_run_dir = tmp_path / "stage01"
    handoff = {
        "candidate_inputs": [
            {
                "candidate_id": "c1",
                "feature_set": "price_action_core",
                "feature_columns": ["f1", "f2"],
                "window_size": 10,
            }
        ],
        "approved_model_families_for_stage02": ["shallow_lstm"],
        "decision": "selected_candidate_inputs_for_stage02_train_inner_hpo",
        "no_final_model_selected": True,
        "holdout_test_contact": False,
    }
    write_stage01_artifacts(stage01_run_dir, handoff=handoff)

    with pytest.raises(ValueError, match="not enabled"):
        stage02.run_stage(stage02_config(tmp_path, stage01_run_dir))
