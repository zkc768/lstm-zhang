from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stages" / "02_model_hpo_train_inner.yaml"
CURRENT_STAGE01_RUN_ID = "20260610_075002"
CURRENT_STAGE00_RUN_ID = "20260610_051705_347450"


def load_config() -> dict:
    with CONFIG.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_stage02_config_preserves_validation_only_scope() -> None:
    config = load_config()
    assert config["stage_name"] == "02_model_hpo_train_inner"
    assert config["route"] == "lst_models"
    assert config["scope"] == "validation_only"
    assert config["holdout_test_contact"] is False


def test_stage02_config_points_to_exact_stage01_run_folder() -> None:
    config = load_config()
    inputs = config["inputs"]
    assert inputs["stage00_run_id"] == CURRENT_STAGE00_RUN_ID
    assert inputs["stage00_runtime_run_dir"].endswith(
        f"/00_data_split_label_freeze/{CURRENT_STAGE00_RUN_ID}"
    )
    assert inputs["stage00_drive_run_dir"].endswith(
        f"lst_models/results/00_data_split_label_freeze/{CURRENT_STAGE00_RUN_ID}"
    )
    assert inputs["stage00_drive_path_parts"] == [
        "lst_models",
        "results",
        "00_data_split_label_freeze",
        CURRENT_STAGE00_RUN_ID,
    ]
    assert inputs["raw_data_manifest"] == "configs/lst_models_data.yaml"
    assert inputs["raw_data_dir"] == "/content/lst_models_raw_stock_data"
    assert set(inputs["required_stage00_artifacts"]) == {
        "raw_data_manifest.json",
        "split_freeze.json",
        "label_policy.json",
        "baseline_registry.json",
        "sample_event_index.csv",
        "run_manifest.json",
    }
    assert inputs["stage01_run_id"] == CURRENT_STAGE01_RUN_ID
    assert inputs["stage01_runtime_run_dir"].endswith(
        f"/01_feature_window_search/{CURRENT_STAGE01_RUN_ID}"
    )
    assert inputs["stage01_drive_run_dir"].endswith(
        f"lst_models/results/01_feature_window_search/{CURRENT_STAGE01_RUN_ID}"
    )
    assert inputs["stage01_drive_path_parts"] == [
        "lst_models",
        "results",
        "01_feature_window_search",
        CURRENT_STAGE01_RUN_ID,
    ]
    assert inputs["stage01_candidate_inputs"].endswith(
        f"/01_feature_window_search/{CURRENT_STAGE01_RUN_ID}/01_candidate_inputs.json"
    )
    assert "01_train_label_band_diagnostic.csv" in inputs["required_stage01_artifacts"]


def test_stage02_config_declares_core_hpo_families_and_search_spaces() -> None:
    config = load_config()
    expected = ["lightgbm", "standard_dlinear", "tcn", "ms_dlinear_tcn"]
    active = [
        family
        for family, family_config in config["hpo_families"].items()
        if family_config["enabled"] is True
    ]
    assert active == expected
    for family in expected:
        search_space_path = ROOT / config["hpo_families"][family]["search_space"]
        assert search_space_path.exists()
        with search_space_path.open("r", encoding="utf-8") as handle:
            search_space = yaml.safe_load(handle)
        assert search_space["model_family"] == family
        assert 1 <= len(search_space["profiles"]) <= config["budget"]["max_profiles_per_family"]


def test_stage02_search_space_records_only_effective_profile_keys() -> None:
    config = load_config()
    allowed_profile_keys = {
        "lightgbm": {
            "profile_id",
            "num_leaves",
            "max_depth",
            "min_data_in_leaf",
            "min_child_samples",
            "learning_rate",
            "n_estimators",
            "feature_fraction",
            "colsample_bytree",
            "bagging_fraction",
            "subsample",
            "bagging_freq",
            "subsample_freq",
            "lambda_l1",
            "reg_alpha",
            "lambda_l2",
            "reg_lambda",
            "class_weight",
        },
        "standard_dlinear": {
            "profile_id",
            "moving_avg_kernel",
            "dropout",
            "learning_rate",
            "weight_decay",
        },
        "tcn": {
            "profile_id",
            "channels",
            "kernel_size",
            "dropout",
            "learning_rate",
            "weight_decay",
        },
        "ms_dlinear_tcn": {
            "profile_id",
            "moving_avg_kernels",
            "tcn_channels",
            "tcn_kernel_size",
            "dropout",
            "learning_rate",
            "weight_decay",
        },
    }
    for family, allowed_keys in allowed_profile_keys.items():
        search_space_path = ROOT / config["hpo_families"][family]["search_space"]
        with search_space_path.open("r", encoding="utf-8") as handle:
            search_space = yaml.safe_load(handle)
        for profile in search_space["profiles"]:
            assert set(profile).issubset(allowed_keys), (family, profile)


def test_stage02_config_budget_and_train_inner_rules() -> None:
    config = load_config()
    assert config["train_inner"]["n_folds"] == 3
    assert config["train_inner"]["seeds"] == [101, 202]
    assert config["train_inner"]["official_validation_for_selection"] is False
    assert config["budget"]["max_hpo_plan_rows"] == 240
    assert config["hpo_sample_policy"]["max_train_samples_per_fold"] == 50000
    assert config["hpo_sample_policy"]["max_eval_samples_per_fold"] == 20000
    assert config["lightgbm_training_defaults"]["early_stopping_rounds"] == 25
    assert (
        config["lightgbm_training_defaults"]["early_stopping_validation_source"]
        == "inner_train_chronological_tail"
    )
    assert config["lightgbm_training_defaults"]["minimum_early_stopping_train_samples"] == 128
    assert config["lightgbm_training_defaults"]["minimum_early_stopping_validation_samples"] == 128
    torch_defaults = config["probe_training_defaults"]["torch"]
    assert torch_defaults["epochs"] == 64
    assert torch_defaults["early_stopping"] == "inner_train_chronological_tail"
    assert torch_defaults["early_stopping_validation_fraction"] == 0.2
    assert torch_defaults["minimum_early_stopping_train_samples"] == 128
    assert torch_defaults["minimum_early_stopping_validation_samples"] == 128
    assert torch_defaults["early_stopping_patience"] == 8
    assert torch_defaults["early_stopping_min_delta"] == 0.0
    assert torch_defaults["gradient_clip_norm"] == 1.0
    assert config["checkpointing"]["enabled"] is True
    assert config["checkpointing"]["checkpoint_every_trials"] == 8
    assert config["selection_rules"]["minimum_positive_ticker_count"] == 3
    assert config["selection_rules"]["max_selected_configs_per_family"] == 1
    assert config["selection_rules"]["no_official_validation_selection"] is True
    assert config["selection_rules"]["no_final_model_selected"] is True


def test_stage02_config_declares_formal_outputs_and_baselines() -> None:
    config = load_config()
    outputs = config["outputs"]
    assert outputs["hpo_trial_ledger"] == "02_hpo_trial_ledger.csv"
    assert outputs["hpo_summary"] == "02_hpo_summary.csv"
    assert outputs["baseline_control_summary"] == "02_baseline_control_summary.csv"
    assert outputs["frozen_candidate"] == "02_frozen_candidate.json"
    assert outputs["frozen_candidate_markdown"] == "02_frozen_candidate.md"
    assert outputs["frozen_params_dir"] == "frozen_params"
    assert config["baseline_controls"]["mandatory"] == [
        "stratified_dummy_train_prior",
        "majority_train_prior",
        "constant_up",
        "constant_down",
    ]


def test_stage02_config_does_not_promote_recurrent_controls_to_hpo() -> None:
    config = load_config()
    assert config["optional_fixed_controls"]["simple_gru"]["enabled"] is False
    assert config["optional_fixed_controls"]["simple_gru"]["stage02_hpo_family"] is False
    assert config["optional_fixed_controls"]["shallow_lstm"]["enabled"] is False
    assert config["optional_fixed_controls"]["shallow_lstm"]["stage02_hpo_family"] is False


def test_stage02_forbidden_axes_are_declared() -> None:
    config = load_config()
    assert set(config["forbidden"]["search_axes"]) == {
        "label_operator",
        "horizon_k",
        "no_trade_band_bps",
        "calendar_split_boundaries",
        "official_validation_tiebreaker",
        "holdout_test_wording",
    }
