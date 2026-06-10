from __future__ import annotations

import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


CONFIG = load_yaml(REPO_ROOT / "configs" / "stages" / "04_diagnostics_ablation.yaml")
STAGE02_CONFIG = load_yaml(REPO_ROOT / "configs" / "stages" / "02_model_hpo_train_inner.yaml")
STAGE03_CONFIG = load_yaml(REPO_ROOT / "configs" / "stages" / "03_frozen_validation_readout.yaml")


def test_scope_and_zero_event_flags() -> None:
    assert CONFIG["stage_name"] == "04_diagnostics_ablation"
    assert CONFIG["scope"] == "validation_only"
    assert CONFIG["holdout_test_contact"] is False
    assert CONFIG["official_validation_contact"] == "read_frozen_artifacts_only"
    assert CONFIG["official_validation_for_selection"] is False
    assert CONFIG["new_validation_fit_predict_events"] == 0


def test_upstream_run_id_chain_matches_stage03_config() -> None:
    inputs = CONFIG["inputs"]
    assert inputs["stage03_run_id"] == "20260610_133305_716174"
    for key in ("stage00_run_id", "stage01_run_id", "stage02_run_id"):
        assert inputs[key] == STAGE03_CONFIG["inputs"][key]
    assert inputs["superseded_stage02_run_ids"] == (
        STAGE03_CONFIG["inputs"]["superseded_stage02_run_ids"]
    )
    assert inputs["stage02_run_id"] not in inputs["superseded_stage02_run_ids"]
    for stage in ("stage00", "stage01", "stage02", "stage03"):
        assert inputs[f"{stage}_run_id"] in inputs[f"{stage}_runtime_run_dir"]
        assert inputs[f"{stage}_run_id"] in str(inputs[f"{stage}_drive_path_parts"])


def test_required_stage03_artifacts_cover_dump_and_decision_record() -> None:
    required = CONFIG["inputs"]["required_stage03_artifacts"]
    for name in (
        "run_manifest.json",
        "artifact_inventory.csv",
        "03_validation_predictions.csv",
        "03_decision_record.json",
        "03_same_row_baselines.csv",
        "03_per_ticker_readout.csv",
    ):
        assert name in required


def test_frozen_training_defaults_match_stage02() -> None:
    assert CONFIG["lightgbm_training_defaults"] == STAGE02_CONFIG["lightgbm_training_defaults"]
    assert CONFIG["probe_training_defaults"]["torch"] == (
        STAGE02_CONFIG["probe_training_defaults"]["torch"]
    )


def test_ablation_budget_arithmetic_closes() -> None:
    ablation = CONFIG["ablation"]
    planned = len(ablation["controls"]) * 1 * ablation["n_folds"] * len(ablation["seeds"])
    assert planned == 24
    assert planned <= ablation["budget"]["max_ablation_plan_rows"]
    assert set(ablation["controls"]) == {
        "dlinear_only",
        "tcn_only",
        "last_step_mlp",
        "last_step_lightgbm_control",
    }
    assert ablation["candidate_input"] == "price_volume_time_w20"
    assert ablation["seeds"] == [101, 202]
    assert ablation["hpo_sample_policy"] == STAGE02_CONFIG["hpo_sample_policy"]


def test_control_probe_ids_match_runner_mapping() -> None:
    from lst_models.stages.diagnostics_ablation import CONTROL_PROBE_BY_ID

    configured = {
        control_id: block["probe_id"] for control_id, block in CONFIG["ablation"]["controls"].items()
    }
    assert configured == CONTROL_PROBE_BY_ID


def test_diagnostics_measure_only_flags() -> None:
    diag = CONFIG["diagnostics"]
    assert diag["source"] == "stage03_validation_predictions_only"
    assert diag["calibration"]["no_calibrator_fitting"] is True
    assert diag["selective"]["no_operating_point"] is True
    assert diag["expected_dump_rows"] == 302128
    assert diag["expected_seeds"] == [101, 202]
    assert diag["baseline_reconstruction"]["on_mismatch"] == (
        "mark_not_computed_keep_frozen_ticker_rows"
    )
    assert diag["bootstrap"]["seed"] == 12345


def test_required_artifact_list_closes_with_runner_constant() -> None:
    from lst_models.stages.diagnostics_ablation import REQUIRED_STAGE04_ARTIFACTS

    outputs = CONFIG["outputs"]
    stage_artifacts = sorted(
        value for key, value in outputs.items() if key != "output_dir"
    )
    assert sorted(REQUIRED_STAGE04_ARTIFACTS) == stage_artifacts
    assert len(REQUIRED_STAGE04_ARTIFACTS) == 12
    assert "drive_backup_manifest.json" not in REQUIRED_STAGE04_ARTIFACTS


def test_checkpoint_drive_contract_declared() -> None:
    checkpointing = CONFIG["checkpointing"]
    assert checkpointing["enabled"] is True
    assert checkpointing["checkpoint_after_each_control"] is True
    assert checkpointing["checkpoint_drive_path_parts"] == [
        "lst_models",
        "checkpoints",
        "04_diagnostics_ablation",
    ]
    resume = CONFIG["resume"]
    assert resume["enabled"] is False
    assert resume["run_id"] is None


def test_required_artifacts_and_wording() -> None:
    outputs = CONFIG["outputs"]
    for key in (
        "calibration_summary",
        "reliability_bins",
        "risk_coverage_curve",
        "selective_summary",
        "robustness_slices",
        "failure_slices",
        "ablation_plan_ledger",
        "ablation_trial_ledger",
        "ablation_summary",
        "diagnostics_report",
    ):
        assert outputs[key].startswith("04_")
    for phrase in ("chosen threshold", "selected by official validation", "final model"):
        assert phrase in CONFIG["forbidden"]["wording"]
    assert len(CONFIG["forbidden"]["wording"]) == 10
    assert CONFIG["ablation"]["reference_rows"]["expected_row_count"] == 6
    assert CONFIG["ablation"]["same_row_baselines"]["mandatory"] == [
        "stratified_dummy_train_prior",
        "majority_train_prior",
        "constant_up",
        "constant_down",
    ]


def test_stage_module_contains_no_calibrator_fitting_tokens() -> None:
    source = (REPO_ROOT / "src" / "lst_models" / "stages" / "diagnostics_ablation.py").read_text(
        encoding="utf-8"
    )
    for token in ("CalibratedClassifierCV", "IsotonicRegression", "temperature_scal", "Platt"):
        assert token not in source
