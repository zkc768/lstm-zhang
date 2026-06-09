from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stages" / "01_feature_window_search.yaml"


def load_config() -> dict:
    with CONFIG.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_stage01_config_preserves_validation_only_scope() -> None:
    config = load_config()
    assert config["stage_name"] == "01_feature_window_search"
    assert config["route"] == "lst_models"
    assert config["scope"] == "validation_only"
    assert config["holdout_test_contact"] is False


def test_stage01_config_points_to_exact_stage00_run_folder() -> None:
    config = load_config()
    inputs = config["inputs"]
    assert inputs["stage00_run_id"] == "20260609_015034_927813"
    assert inputs["stage00_runtime_run_dir"].endswith(
        "/00_data_split_label_freeze/20260609_015034_927813"
    )
    assert inputs["stage00_drive_run_dir"].endswith(
        "lst_models/results/00_data_split_label_freeze/20260609_015034_927813"
    )
    assert inputs["stage00_drive_path_parts"] == [
        "lst_models",
        "results",
        "00_data_split_label_freeze",
        "20260609_015034_927813",
    ]
    assert inputs["stage00_run_manifest"].endswith(
        "/00_data_split_label_freeze/20260609_015034_927813/run_manifest.json"
    )


def test_stage01_config_freezes_window_grid_and_budget() -> None:
    config = load_config()
    assert config["window_sizes"] == [10, 20, 30]
    assert config["train_inner"]["n_folds"] == 2
    assert config["train_inner"]["seeds"] == [101, 202]
    assert config["budget"]["max_counted_probe_rows"] == 240
    assert config["train_inner"]["official_validation_for_selection"] is False
    assert config["inputs"]["raw_data_dir"] == "/content/lst_models_raw_stock_data"
    assert config["outputs"]["label_band_diagnostic"] == "01_train_label_band_diagnostic.csv"
    assert config["screening_sample_policy"]["sample_method"] == (
        "deterministic_even_stride_by_ticker_label"
    )


def test_stage01_config_declares_feature_sets_and_probes() -> None:
    config = load_config()
    assert set(config["feature_sets"]) == {
        "price_action_core",
        "technical_price",
        "price_volume_time",
    }
    assert set(config["baseline_probes"]["mandatory_trivial"]) == {
        "stratified_dummy_train_prior",
        "majority_train_prior",
    }
    assert set(config["lightweight_probes"]) == {
        "logreg_flat_control",
        "lightgbm_small",
        "standard_dlinear_tiny",
        "tcn_tiny",
        "ms_dlinear_tcn_tiny",
    }
    lightgbm_defaults = config["lightweight_probes"]["lightgbm_small"]["fixed_defaults"]
    assert lightgbm_defaults["subsample"] == 0.9
    assert lightgbm_defaults["subsample_freq"] == 1


def test_stage01_config_does_not_promote_recurrent_controls_to_hpo() -> None:
    config = load_config()
    assert config["optional_fixed_controls"]["simple_gru"]["enabled"] is False
    assert config["optional_fixed_controls"]["simple_gru"]["stage02_hpo_family"] is False
    assert config["optional_fixed_controls"]["shallow_lstm"]["enabled"] is False
    assert config["optional_fixed_controls"]["shallow_lstm"]["stage02_hpo_family"] is False


def test_stage01_config_handoff_and_forbidden_axes() -> None:
    config = load_config()
    assert config["selection_rules"]["no_final_model_selected"] is True
    assert (
        config["selection_rules"]["family_lcb_selection_policy"]
        == "median_stage02_family_lcb"
    )
    assert config["selection_rules"]["minimum_positive_stage02_family_count"] == 1
    assert config["selection_rules"]["max_candidate_inputs_for_stage02"] == 2
    assert config["stage02_handoff"]["recommended_model_families"] == [
        "lightgbm",
        "standard_dlinear",
        "tcn",
        "ms_dlinear_tcn",
    ]
    assert config["stage02_handoff"]["control_models"] == ["last_step_lightgbm_control"]
    assert set(config["forbidden"]["search_axes"]) == {
        "label_operator",
        "horizon_k",
        "no_trade_band_bps",
        "calendar_split_boundaries",
        "holdout_test_wording",
    }
