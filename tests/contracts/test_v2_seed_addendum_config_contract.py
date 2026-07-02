"""Config + schema contract for the v2 seed addendum readout.

Guards the frozen preregistration values (seed rule, never-rerun list, budget
cap, frozen-identity block, byte-equal training defaults) and pins the
addendum's output-schema constants to the Stage 03 originals so the verbatim
copies cannot drift apart silently.

Preregistration: docs/protocols/v2_seed_addendum_preregistration_20260701.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from lst_models.stages import frozen_validation_readout as stage03  # noqa: E402
from lst_models.stages import v2_seed_addendum_readout as v2sa  # noqa: E402


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


CONFIG = load_yaml(REPO_ROOT / "configs" / "stages" / "v2_seed_addendum_readout.yaml")
STAGE03_CONFIG = load_yaml(REPO_ROOT / "configs" / "stages" / "03_frozen_validation_readout.yaml")


def test_scope_and_contact_flags() -> None:
    assert CONFIG["stage_name"] == "v2_seed_addendum_readout"
    assert CONFIG["scope"] == "validation_only"
    assert CONFIG["holdout_test_contact"] is False
    assert CONFIG["official_validation_contact"] is True
    assert CONFIG["official_validation_for_selection"] is False
    assert CONFIG["addendum_never_merged_into_predeclared_readout"] is True
    assert CONFIG["evidence_status"] == "official_validation_seed_addendum_disclosed_post_hoc"


def test_seed_rule_is_deterministic_and_disjoint_from_predeclared() -> None:
    readout = CONFIG["readout"]
    assert readout["seed_rule"] == "seed_k_equals_101_times_k_next_six_multipliers_k3_to_k8"
    assert readout["addendum_seeds"] == [101 * k for k in range(3, 9)]
    assert readout["addendum_seeds"] == [303, 404, 505, 606, 707, 808]
    assert readout["predeclared_seeds_never_rerun"] == [101, 202]
    assert not set(readout["addendum_seeds"]) & set(readout["predeclared_seeds_never_rerun"])
    assert readout["score_each_seed_candidate_exactly_once"] is True
    assert v2sa.EXPECTED_ADDENDUM_SEEDS == readout["addendum_seeds"]
    assert v2sa.PREDECLARED_SEEDS == readout["predeclared_seeds_never_rerun"]


def test_upstream_chain_pins_match_stage03_config() -> None:
    inputs, stage03_inputs = CONFIG["inputs"], STAGE03_CONFIG["inputs"]
    for key in ("stage00_run_id", "stage01_run_id", "stage02_run_id"):
        assert inputs[key] == stage03_inputs[key]
    assert inputs["stage02_run_id"] not in inputs["superseded_stage02_run_ids"]
    assert set(inputs["superseded_stage02_run_ids"]) == set(
        stage03_inputs["superseded_stage02_run_ids"]
    )
    for key in (
        "required_stage00_artifacts", "required_stage01_artifacts", "required_stage02_artifacts"
    ):
        assert inputs[key] == stage03_inputs[key]
    assert inputs["canonical_stage03_run_id"] == "20260610_133305_716174"
    assert inputs["raw_data_manifest"] == "configs/lst_models_data.yaml"


def test_frozen_primary_identity_block() -> None:
    identity = CONFIG["frozen_primary_identity"]
    assert identity["candidate_id"] == "price_volume_time_w20"
    assert identity["feature_set"] == "price_volume_time"
    assert identity["window_size"] == 20
    assert identity["model_family"] == "tcn"
    assert identity["probe_id"] == "tcn_tiny"
    assert identity["hpo_profile_id"] == "tcn_p01"


def test_torch_training_defaults_byte_equal_to_stage03() -> None:
    assert CONFIG["probe_training_defaults"]["torch"] == (
        STAGE03_CONFIG["probe_training_defaults"]["torch"]
    )


def test_date_bounds_frozen() -> None:
    bounds = CONFIG["date_bounds"]
    assert bounds["train_start"] == "1998-01-02"
    assert bounds["train_end_exclusive"] == "2013-09-16"
    assert bounds["validation_start"] == "2013-09-16"
    assert bounds["validation_end_exclusive"] == "2017-01-25"
    assert bounds["closed_holdout_test_start"] == "2017-01-25"


def test_budget_and_reporting_rules_frozen() -> None:
    budget = CONFIG["budget"]
    assert budget["max_new_official_validation_scoring_events"] == 6
    assert budget["contact_type"] == "official_validation_seed_addendum"
    assert budget["data_segment"] == "validation_2013_2017"
    assert budget["for_selection"] is False
    reporting = CONFIG["predeclared_reporting"]
    assert reporting["report_all_addendum_seeds_regardless_of_outcome"] is True
    assert reporting["summary_statistics"] == ["min", "median", "max"]
    assert reporting["primary_summary_metric"] == (
        "delta_macro_f1_vs_stratified_dummy_train_prior"
    )
    assert reporting["count_seeds_with_positive_delta"] is True
    assert reporting["interpretation"] == "descriptive_dispersion_evidence_only"
    assert reporting["wide_or_negative_touching_spread_is_reported_honestly"] is True
    assert reporting["canonical_readout"] == "predeclared_n2_seeds_101_202_remains_canonical"


def test_baseline_controls_match_stage03() -> None:
    assert CONFIG["baseline_controls"]["mandatory"] == (
        STAGE03_CONFIG["baseline_controls"]["mandatory"]
    )


def test_resume_block_disabled_for_fresh_runs() -> None:
    resume = CONFIG["resume"]
    assert resume["enabled"] is False
    assert resume["run_id"] is None
    assert resume["checkpoint_dir"] is None


def test_output_names_and_forbidden_lists() -> None:
    outputs = CONFIG["outputs"]
    assert outputs["validation_readout"] == "v2sa_validation_readout.csv"
    assert outputs["per_ticker_readout"] == "v2sa_per_ticker_readout.csv"
    assert outputs["seed_dispersion_summary"] == "v2sa_seed_dispersion_summary.csv"
    assert outputs["same_row_baselines"] == "v2sa_same_row_baselines.csv"
    assert outputs["validation_predictions"] == "v2sa_validation_predictions.csv"
    assert outputs["decision_record"] == "v2sa_decision_record.json"
    assert outputs["budget_ledger_row"] == "v2sa_budget_ledger_row.csv"
    actions = CONFIG["forbidden"]["actions"]
    for action in (
        "merge_with_predeclared_n2_readout", "rerun_predeclared_seeds_101_202",
        "model_selection", "seed_screening_or_dropping",
    ):
        assert action in actions
    wording = CONFIG["forbidden"]["wording"]
    for phrase in (
        "final model", "significant", "outperforms", "profitable",
        "replaces the predeclared readout",
    ):
        assert phrase in wording


def test_output_schema_constants_pinned_to_stage03() -> None:
    """The addendum writes stage-03-schema outputs; the verbatim constant
    copies in the addendum module must equal the Stage 03 originals."""
    assert v2sa.VALIDATION_READOUT_COLUMNS == stage03.VALIDATION_READOUT_COLUMNS
    assert v2sa.PER_TICKER_READOUT_COLUMNS == stage03.PER_TICKER_READOUT_COLUMNS
    assert v2sa.SAME_ROW_BASELINE_COLUMNS == stage03.SAME_ROW_BASELINE_COLUMNS
    assert v2sa.VALIDATION_PREDICTION_COLUMNS == stage03.VALIDATION_PREDICTION_COLUMNS


def test_budget_ledger_row_schema_matches_stage05_ledger() -> None:
    """The appendable row must carry the exact 05_validation_budget_ledger.csv
    header (see artifacts/05_thesis_synthesis/20260619_090454_562658/)."""
    assert v2sa.BUDGET_LEDGER_ROW_COLUMNS == [
        "stage_name", "run_id", "evidence_domain", "data_segment", "contact_type",
        "scoring_events", "for_selection", "notes",
    ]


def test_entry_gate_flag_check_matches_frozen_artifact_layout() -> None:
    """Regression for the 2026-07-01 Colab entry-gate failure.

    The frozen 01_candidate_inputs.json (Stage 01 train-inner handoff) carries
    holdout_test_contact but has NEVER carried official_validation_for_selection;
    only the three Stage 02 payloads do. The for_selection safety check must
    therefore cover exactly the Stage 02 payloads and must not require the flag
    on the Stage 01 handoff (prereg section 13 dated repair).
    """
    import pytest

    from lst_models.artifacts import require_safety_flags

    stage01_handoff = {"holdout_test_contact": False}  # flag absent, as frozen
    stage02_trio = [
        ("stage02 run_manifest.json", {"holdout_test_contact": False, "official_validation_for_selection": False}),
        ("02_stage03_handoff.json", {"holdout_test_contact": False, "official_validation_for_selection": False}),
        ("02_frozen_candidate.json", {"holdout_test_contact": False, "official_validation_for_selection": False}),
    ]
    labelled = [
        ("stage00 run_manifest.json", {"holdout_test_contact": False}),
        ("stage01 run_manifest.json", {"holdout_test_contact": False}),
        stage02_trio[0],
        ("01_candidate_inputs.json", stage01_handoff),
        stage02_trio[1],
        stage02_trio[2],
    ]
    # holdout flag: all six payloads carry it and must pass.
    require_safety_flags(
        labelled, stage_label="v2_seed_addendum_readout", field="holdout_test_contact", expected=False
    )
    # for_selection flag: the Stage 02 trio passes...
    require_safety_flags(
        [labelled[2], labelled[4], labelled[5]],
        stage_label="v2_seed_addendum_readout",
        field="official_validation_for_selection",
        expected=False,
    )
    # ...and re-including the Stage 01 handoff (the old labelled[2:] slice) must fail,
    # which is exactly the crash this repair removed.
    with pytest.raises(ValueError, match="01_candidate_inputs.json official_validation_for_selection"):
        require_safety_flags(
            labelled[2:],
            stage_label="v2_seed_addendum_readout",
            field="official_validation_for_selection",
            expected=False,
        )
