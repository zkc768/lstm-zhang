from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stages" / "02_model_hpo_train_inner.yaml"
CURRENT_STAGE01_RUN_ID = "20260609_070204"


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


def test_stage02_config_budget_and_train_inner_rules() -> None:
    config = load_config()
    assert config["train_inner"]["n_folds"] == 3
    assert config["train_inner"]["seeds"] == [101, 202]
    assert config["train_inner"]["official_validation_for_selection"] is False
    assert config["budget"]["max_hpo_plan_rows"] == 240
    assert config["selection_rules"]["no_official_validation_selection"] is True
    assert config["selection_rules"]["no_final_model_selected"] is True


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
