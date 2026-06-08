from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stages" / "00_data_split_label_freeze.yaml"


def load_config() -> dict:
    with CONFIG.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_stage00_config_freezes_single_label_policy() -> None:
    config = load_config()
    policy = config["label_policy"]
    assert policy["label_config_id"] == "h09_bps3p0"
    assert policy["operator"] == "endpoint_cumulative_return"
    assert isinstance(policy["horizon_k"], int)
    assert isinstance(policy["no_trade_band_bps"], float)


def test_stage00_config_preserves_validation_only_boundary() -> None:
    config = load_config()
    assert config["scope"] == "validation_only"
    assert config["holdout_test_contact"] is False
    assert config["split"]["validation_end"] == "2017-01-25"
    assert config["split"]["closed_holdout_test_start"] == "2017-01-25"


def test_stage00_config_forbids_stage01_label_search() -> None:
    config = load_config()
    must_not_search = set(config["stage01_handoff"]["must_not_search"])
    assert {"label_operator", "horizon_k", "no_trade_band_bps"}.issubset(must_not_search)
    assert config["stage01_handoff"]["may_search"] == [
        "feature_set",
        "window_size",
        "lightweight_train_inner_shape_signal_checks",
    ]


def test_stage00_config_has_mandatory_trivial_baselines() -> None:
    config = load_config()
    baselines = set(config["baseline_registry"]["mandatory_trivial"])
    assert baselines == {
        "stratified_dummy_train_prior",
        "majority_train_prior",
        "constant_up",
        "constant_down",
    }
