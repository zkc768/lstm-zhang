from __future__ import annotations

from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


CONFIG = load_yaml(REPO_ROOT / "configs" / "stages" / "03_frozen_validation_readout.yaml")
STAGE02_CONFIG = load_yaml(REPO_ROOT / "configs" / "stages" / "02_model_hpo_train_inner.yaml")


def test_scope_and_contact_flags() -> None:
    assert CONFIG["scope"] == "validation_only"
    assert CONFIG["holdout_test_contact"] is False
    assert CONFIG["official_validation_contact"] is True
    assert CONFIG["official_validation_for_selection"] is False


@pytest.mark.xfail(strict=False, reason="pending roadmap Phase 0.3 stage02 re-run id")
def test_upstream_run_ids_chain() -> None:
    inputs = CONFIG["inputs"]
    assert inputs["stage00_run_id"] == "20260610_051705_347450"
    assert inputs["stage01_run_id"] == "20260609_070204"
    assert inputs["stage02_run_id"] not in inputs["superseded_stage02_run_ids"]
    assert inputs["stage02_run_id"] != "<NEW_STAGE02_RUN_ID>", (
        "fill inputs.stage02_run_id with the superseding Stage 02 run id "
        "(roadmap Phase 0.3) before executing Stage 03"
    )
    assert inputs["stage02_run_id"] in inputs["stage02_runtime_run_dir"]


def test_frozen_training_defaults_match_stage02() -> None:
    assert CONFIG["lightgbm_training_defaults"] == STAGE02_CONFIG["lightgbm_training_defaults"]
    assert CONFIG["probe_training_defaults"]["torch"] == (
        STAGE02_CONFIG["probe_training_defaults"]["torch"]
    )


def test_predeclared_criteria_frozen() -> None:
    criteria = CONFIG["predeclared_criteria"]
    assert criteria["aggregate"] == "mean_over_seeds"
    assert criteria["minimum_positive_ticker_count"] == 3
    assert CONFIG["readout"]["seeds"] == [101, 202]
    assert CONFIG["readout"]["score_each_seed_candidate_exactly_once"] is True


def test_fallback_policy_mechanical_only() -> None:
    policy = CONFIG["fallback_policy"]
    assert "weak_validation_metrics" in policy["forbidden_triggers"]
    assert policy["after_first_scoring_event"] == "never_activate"
    assert set(policy["allowed_triggers"]) == {
        "missing_frozen_artifact",
        "schema_or_hash_mismatch",
        "refit_crash_before_any_scoring",
        "candidate_not_reconstructable",
    }


def test_required_artifact_names_and_wording() -> None:
    outputs = CONFIG["outputs"]
    assert outputs["validation_predictions"] == "03_validation_predictions.csv"
    assert outputs["decision_record"] == "03_decision_record.json"
    for phrase in ["final model", "selected by official validation", "chosen threshold"]:
        assert phrase in CONFIG["forbidden"]["wording"]
    assert CONFIG["baseline_controls"]["mandatory"] == [
        "stratified_dummy_train_prior",
        "majority_train_prior",
        "constant_up",
        "constant_down",
    ]
