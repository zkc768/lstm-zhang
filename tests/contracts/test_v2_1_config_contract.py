from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


CONFIG = load_yaml(REPO_ROOT / "configs" / "stages" / "v2_1_guarded_walkforward_readout.yaml")
STAGE02_CONFIG = load_yaml(REPO_ROOT / "configs" / "stages" / "02_model_hpo_train_inner.yaml")


def test_scope_and_contact_flags() -> None:
    assert CONFIG["scope"] == "guarded_walkforward_readout"
    assert CONFIG["holdout_test_contact"] is True
    assert CONFIG["holdout_contact_tier"] == "guarded_historically_contacted"
    assert CONFIG["clean_test_claim"] is False
    assert CONFIG["official_validation_scoring_events"] == 0
    assert CONFIG["no_final_model_selected"] is True
    assert CONFIG["v2_frozen_selection_unchanged"] is True


def test_upstream_run_ids_pinned() -> None:
    inputs = CONFIG["inputs"]
    assert inputs["stage00_run_id"] == "20260610_051705_347450"
    assert inputs["stage01_run_id"] == "20260610_075002"
    assert inputs["stage02_run_id"] == "20260610_082130_797479"
    assert inputs["stage03_run_id"] == "20260610_133305_716174"
    assert inputs["stage04_run_id"] == "20260618_234011_838683"
    assert inputs["stage04_ordering"] == "stage04_first"
    assert inputs["stage04_ordering_override_reason"] is None
    assert inputs["stage00_run_id"] in inputs["stage00_runtime_run_dir"]
    assert inputs["stage01_run_id"] in inputs["stage01_runtime_run_dir"]
    assert inputs["stage02_run_id"] in inputs["stage02_runtime_run_dir"]
    assert inputs["stage03_run_id"] in inputs["stage03_runtime_run_dir"]
    assert "20260609_100637_704705" in inputs["superseded_stage02_run_ids"]
    assert "20260610_010019_507648" in inputs["superseded_stage02_run_ids"]


def test_signoff_and_coverage_probe_placeholders_are_explicit() -> None:
    signoff = CONFIG["sign_off"]
    assert signoff["status"] == "pending"
    assert signoff["user_sign_off_date"] is None
    assert signoff["advisor_confirmation_reference"] is None
    assert signoff["resolved_open_decisions"]["OD-E_stage04_ordering"] == "stage04_first"

    coverage = CONFIG["coverage_probe"]
    assert coverage["authorization"] == "pending"
    assert coverage["artifact"] == "v2_1_coverage_probe.json"
    assert coverage["artifact_sha256"] is None
    assert coverage["probe_timestamp_utc"] is None


def test_frozen_training_defaults_match_stage02() -> None:
    assert CONFIG["lightgbm_training_defaults"] == STAGE02_CONFIG["lightgbm_training_defaults"]
    assert CONFIG["probe_training_defaults"]["torch"] == (
        STAGE02_CONFIG["probe_training_defaults"]["torch"]
    )


def test_walkforward_period_design() -> None:
    wf = CONFIG["walkforward"]
    assert wf["seeds"] == [101, 202]
    assert wf["period_count"] == 7
    assert len(wf["periods"]) == 7
    assert wf["score_each_period_model_seed_exactly_once"] is True
    assert wf["closed_boundary"] == "2017-01-25"
    assert wf["periods"][0]["period_id"] == "wf_p1"
    assert wf["periods"][0]["start"] == "2017-01-25"
    assert wf["periods"][-1]["period_id"] == "wf_p7"
    assert wf["periods"][-1]["end_exclusive"] == "2024-04-19"


def test_predeclared_criteria_frozen() -> None:
    criteria = CONFIG["predeclared_criteria"]
    assert criteria["judged_row"] == "tcn_frozen_primary"
    assert criteria["aggregate"] == "mean_over_seeds"
    assert criteria["positive_period_count_minimum"] == 2
    assert criteria["pooled_delta_positive"] is True


def test_model_roster_complete() -> None:
    roster = CONFIG["model_roster"]
    row_ids = [r["table_row_id"] for r in roster["model_rows"]]
    assert "tcn_frozen_primary" in row_ids
    assert "lightgbm_family_best" in row_ids
    assert "standard_dlinear_family_best" in row_ids
    assert "ms_dlinear_tcn_family_best" in row_ids
    assert roster["candidate_input"]["candidate_id"] == "price_volume_time_w20"
    assert roster["candidate_input"]["window_size"] == 20


def test_resume_block_disabled_for_fresh_runs() -> None:
    resume = CONFIG["resume"]
    assert resume["enabled"] is False
    assert resume["run_id"] is None
    assert resume["checkpoint_dir"] is None


def test_required_stage03_artifacts() -> None:
    required = CONFIG["inputs"]["required_stage03_artifacts"]
    assert "run_manifest.json" in required
    assert "artifact_inventory.csv" in required
    assert "03_decision_record.json" in required


def test_forbidden_wording() -> None:
    forbidden = CONFIG["forbidden"]["wording"]
    for phrase in [
        "clean test", "clean holdout", "untouched test", "untouched holdout",
        "final evidence", "out-of-sample proof", "final model",
    ]:
        assert phrase in forbidden
    assert CONFIG["baseline_controls"]["mandatory"] == [
        "stratified_dummy_train_prior",
        "majority_train_prior",
        "constant_up",
        "constant_down",
    ]
