from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stages" / "v2_synthetic_positive_control.yaml"
STAGE02_CONFIG = ROOT / "configs" / "stages" / "02_model_hpo_train_inner.yaml"
PROTOCOL = ROOT / "docs" / "protocols" / "v2_positive_control_preregistration_20260701.md"
NOTEBOOK = ROOT / "notebooks" / "v2_synthetic_positive_control_colab.ipynb"
TCN_SEARCH_SPACE = ROOT / "configs" / "models" / "tcn" / "search_space.yaml"

CURRENT_STAGE00_RUN_ID = "20260610_051705_347450"
CURRENT_STAGE01_RUN_ID = "20260610_075002"
CURRENT_REAL_STAGE02_RUN_ID = "20260610_082130_797479"


def load_config() -> dict:
    with CONFIG.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_stage02_config() -> dict:
    with STAGE02_CONFIG.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_spc_sidecar_files_exist() -> None:
    assert CONFIG.exists()
    assert PROTOCOL.exists()
    assert NOTEBOOK.exists()
    assert (ROOT / "src" / "lst_models" / "synthetic_control.py").exists()
    assert (ROOT / "src" / "lst_models" / "stages" / "synthetic_positive_control.py").exists()


def test_spc_config_declares_synthetic_train_domain_scope() -> None:
    config = load_config()
    assert config["stage_name"] == "v2_synthetic_positive_control"
    assert config["route"] == "lst_models"
    assert config["scope"] == "validation_only"
    assert config["holdout_test_contact"] is False
    assert config["synthetic_labels"] is True
    assert config["train_domain_only"] is True
    assert config["evidence_status"] == (
        "synthetic_positive_control_protocol_validation_only"
    )


def test_spc_config_pins_exact_upstream_run_folders() -> None:
    inputs = load_config()["inputs"]
    assert inputs["stage00_run_id"] == CURRENT_STAGE00_RUN_ID
    assert inputs["stage00_runtime_run_dir"].endswith(
        f"/00_data_split_label_freeze/{CURRENT_STAGE00_RUN_ID}"
    )
    assert inputs["stage00_drive_path_parts"] == [
        "lst_models", "results", "00_data_split_label_freeze", CURRENT_STAGE00_RUN_ID,
    ]
    assert inputs["stage01_run_id"] == CURRENT_STAGE01_RUN_ID
    assert inputs["stage01_drive_path_parts"] == [
        "lst_models", "results", "01_feature_window_search", CURRENT_STAGE01_RUN_ID,
    ]
    assert inputs["stage02_real_run_id"] == CURRENT_REAL_STAGE02_RUN_ID
    assert inputs["stage02_real_drive_path_parts"] == [
        "lst_models", "results", "02_model_hpo_train_inner", CURRENT_REAL_STAGE02_RUN_ID,
    ]
    assert set(inputs["required_stage00_artifacts"]) == {
        "raw_data_manifest.json", "split_freeze.json", "label_policy.json",
        "baseline_registry.json", "sample_event_index.csv", "run_manifest.json",
    }
    assert set(inputs["required_stage01_artifacts"]) == {
        "run_manifest.json", "01_candidate_inputs.json",
    }
    assert set(inputs["required_stage02_artifacts"]) == {
        "run_manifest.json", "02_hpo_trial_ledger.csv",
    }
    assert inputs["raw_data_manifest"] == "configs/lst_models_data.yaml"
    assert inputs["raw_data_dir"] == "/content/lst_models_raw_stock_data"
    assert inputs["notebook_path"] == "notebooks/v2_synthetic_positive_control_colab.ipynb"


def test_spc_config_scopes_to_frozen_primary_configuration_only() -> None:
    config = load_config()
    assert config["candidate"]["candidate_id"] == "price_volume_time_w20"
    model = config["model"]
    assert model["family"] == "tcn"
    assert model["probe_id"] == "tcn_tiny"
    assert model["hpo_profile_id"] == "tcn_p01"
    assert model["search_space"] == "configs/models/tcn/search_space.yaml"
    with TCN_SEARCH_SPACE.open("r", encoding="utf-8") as handle:
        search_space = yaml.safe_load(handle)
    profile_ids = [profile["profile_id"] for profile in search_space["profiles"]]
    assert "tcn_p01" in profile_ids


def test_spc_config_predeclares_arms_and_criteria() -> None:
    config = load_config()
    injection = config["injection"]
    assert injection["rule_id"] == "sign_of_day_local_log_return_at_target_bar"
    assert injection["rule_feature"] == "log_return"
    assert injection["injection_seed"] == 20260701
    arms = injection["arms"]
    assert [arm["strength"] for arm in arms] == [0.0, 0.01, 0.02, 0.05]
    assert [arm["arm_id"] for arm in arms] == [
        "arm_s0p000", "arm_s0p010", "arm_s0p020", "arm_s0p050",
    ]
    assert arms[0]["role"] == "mandatory_null_arm"

    criteria = config["criteria"]
    assert criteria["primary_baseline"] == "stratified_dummy_train_prior"
    assert criteria["minimum_positive_ticker_count"] == 3
    assert criteria["null_strength"] == 0.0
    assert criteria["detection_strengths"] == [0.02, 0.05]
    assert criteria["monotone_strengths"] == [0.0, 0.02, 0.05]
    assert criteria["threshold_strength"] == 0.01
    band = criteria["null_band_source"]
    assert band["artifact"] == "02_hpo_trial_ledger.csv"
    assert band["candidate_id"] == "price_volume_time_w20"
    assert band["model_family"] == "tcn"
    assert band["hpo_profile_id"] == "tcn_p01"
    assert band["expected_rows"] == 6


def test_spc_config_machinery_matches_executed_stage02() -> None:
    config = load_config()
    stage02 = load_stage02_config()
    assert config["train_inner"]["n_folds"] == stage02["train_inner"]["n_folds"] == 3
    assert config["train_inner"]["seeds"] == stage02["train_inner"]["seeds"] == [101, 202]
    assert config["train_inner"]["official_validation_for_selection"] is False
    assert (
        config["sample_policy"]["max_train_samples_per_fold"]
        == stage02["hpo_sample_policy"]["max_train_samples_per_fold"]
    )
    assert (
        config["sample_policy"]["max_eval_samples_per_fold"]
        == stage02["hpo_sample_policy"]["max_eval_samples_per_fold"]
    )
    assert (
        config["sample_policy"]["sample_method"]
        == stage02["hpo_sample_policy"]["sample_method"]
    )
    assert (
        config["probe_training_defaults"]["torch"]
        == stage02["probe_training_defaults"]["torch"]
    )


def test_spc_config_budget_covers_arms_by_folds_by_seeds() -> None:
    config = load_config()
    planned = (
        len(config["injection"]["arms"])
        * int(config["train_inner"]["n_folds"])
        * len(config["train_inner"]["seeds"])
    )
    assert planned == 24
    assert planned <= int(config["budget"]["max_planned_fit_rows"])


def test_spc_config_outputs_and_forbidden_lists() -> None:
    config = load_config()
    outputs = config["outputs"]
    assert outputs["output_dir"] == "/content/lst_models_results/v2_synthetic_positive_control"
    for key, name in {
        "manifest": "run_manifest.json",
        "artifact_inventory": "artifact_inventory.csv",
        "trial_ledger": "spc_trial_ledger.csv",
        "arm_summary": "spc_arm_summary.csv",
        "baseline_control_summary": "spc_baseline_control_summary.csv",
        "sentinel_ledger": "spc_sentinel_ledger.csv",
        "injection_manifest": "spc_injection_manifest.json",
        "criteria_readout": "spc_criteria_readout.json",
    }.items():
        assert outputs[key] == name
    assert outputs["per_arm_trials_prefix"] == "spc_trials_"
    assert config["checkpointing"]["enabled"] is True
    assert config["checkpointing"]["checkpoint_dir"].startswith(
        "/content/lst_models_checkpoints/"
    )
    forbidden = config["forbidden"]
    for axis in [
        "label_operator", "horizon_k", "no_trade_band_bps", "calendar_split_boundaries",
        "injection_rule_after_first_fit", "additional_arms_after_first_fit",
    ]:
        assert axis in forbidden["search_axes"]
    for phrase in ["market evidence", "model evidence", "profitable", "clean test", "final model"]:
        assert phrase in forbidden["wording"]


def test_spc_sentinel_settings_are_predeclared() -> None:
    config = load_config()
    assert config["sentinels"]["n_perm"] == 200
    assert config["sentinels"]["seed"] == 20260617
