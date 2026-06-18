from __future__ import annotations

import copy
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models.stages.guarded_walkforward_readout import (  # noqa: E402
    PER_TICKER_READOUT_COLUMNS,
    PREDICTION_COLUMNS,
    BASELINE_PREDICTION_COLUMNS,
    REQUIRED_V2_1_ARTIFACTS,
    RESUME_CHECKPOINT_FILES,
    SCOPE,
    V21Result,
    WALKFORWARD_READOUT_COLUMNS,
    READOUT_TIER,
    _validate_config,
    _aggregate_and_judge,
    _WalkforwardLedger,
    _build_comparison_table,
    _build_period_registry,
    _checkpoint_manifest_payload,
    _protocol_provenance_fields,
    _score_seed_dummies,
)


MINIMAL_CONFIG = {
    "stage_name": "v2_1_guarded_walkforward_readout",
    "route": "lst_models",
    "scope": "guarded_walkforward_readout",
    "holdout_test_contact": True,
    "holdout_contact_tier": "guarded_historically_contacted",
    "clean_test_claim": False,
    "no_final_model_selected": True,
    "walkforward": {
        "seeds": [101, 202],
        "score_each_period_model_seed_exactly_once": True,
        "period_count": 2,
        "periods": [
            {"period_id": "wf_p1", "start": "2020-01-01", "end_exclusive": "2021-01-01"},
            {"period_id": "wf_p2", "start": "2021-01-01", "end_exclusive": "2022-01-01"},
        ],
    },
    "inputs": {
        "stage00_run_id": "20260610_000000_000001",
        "stage01_run_id": "20260610_000000_000002",
        "stage02_run_id": "20260610_000000_000003",
        "stage03_run_id": "20260610_000000_000004",
        "stage04_run_id": "20260610_000000_000005",
        "stage04_ordering": "stage04_first",
        "stage04_ordering_override_reason": None,
    },
    "sign_off": {
        "status": "complete",
        "user_sign_off_date": "2026-06-16",
        "advisor_confirmation_reference": "advisor-msg-test",
        "resolved_open_decisions": {
            "OD-A_period_count_k": 2,
            "OD-B_period_length_months": 12,
            "OD-C_candidate_input_policy": "A_family_best_verbatim",
            "OD-D_ablation_rows_included": False,
            "OD-E_stage04_ordering": "stage04_first",
            "OD-F_criteria_accepted": "yes",
        },
    },
    "coverage_probe": {
        "authorization": "approved_after_sign_off",
        "artifact": "v2_1_coverage_probe.json",
        "artifact_sha256": "0" * 64,
        "probe_timestamp_utc": "2026-06-16T00:00:00+00:00",
    },
    "model_roster": {
        "candidate_input": {"candidate_id": "test_w10", "feature_set": "test", "window_size": 10},
        "model_rows": [
            {"table_row_id": "tcn_frozen_primary", "model_family": "tcn",
             "probe_id": "tcn_tiny", "hpo_profile_id": "tcn_p01",
             "hpo_profile_params": {"channels": [16], "kernel_size": 2}},
        ],
    },
    "predeclared_criteria": {
        "judged_row": "tcn_frozen_primary",
        "aggregate": "mean_over_seeds",
        "positive_period_count_minimum": 2,
        "pooled_delta_positive": True,
    },
    "baseline_controls": {"mandatory": ["stratified_dummy_train_prior"]},
}


def test_validate_config_accepts_minimal() -> None:
    _validate_config(MINIMAL_CONFIG)


def test_validate_config_rejects_wrong_stage_name() -> None:
    bad = {**MINIMAL_CONFIG, "stage_name": "wrong"}
    with pytest.raises(ValueError, match="expected V2.1 config"):
        _validate_config(bad)


def test_validate_config_rejects_clean_test_claim() -> None:
    bad = {**MINIMAL_CONFIG, "clean_test_claim": True}
    with pytest.raises(ValueError, match="clean_test_claim"):
        _validate_config(bad)


def test_validate_config_rejects_no_holdout_contact() -> None:
    bad = {**MINIMAL_CONFIG, "holdout_test_contact": False}
    with pytest.raises(ValueError, match="holdout_test_contact"):
        _validate_config(bad)


def test_validate_config_rejects_unfilled_run_ids() -> None:
    bad = copy.deepcopy(MINIMAL_CONFIG)
    bad["inputs"]["stage03_run_id"] = "<FILL>"
    with pytest.raises(ValueError, match="fill inputs.stage03_run_id"):
        _validate_config(bad)


def test_validate_config_rejects_unfilled_stage04_run_id() -> None:
    bad = copy.deepcopy(MINIMAL_CONFIG)
    bad["inputs"]["stage04_run_id"] = "<FILL>"
    with pytest.raises(ValueError, match="fill inputs.stage04_run_id"):
        _validate_config(bad)


def test_validate_config_rejects_unfilled_signoff() -> None:
    bad = copy.deepcopy(MINIMAL_CONFIG)
    bad["sign_off"]["status"] = "pending"
    with pytest.raises(ValueError, match="sign_off.status"):
        _validate_config(bad)


def test_validate_config_rejects_unfilled_coverage_probe() -> None:
    bad = copy.deepcopy(MINIMAL_CONFIG)
    bad["coverage_probe"]["artifact_sha256"] = None
    with pytest.raises(ValueError, match="coverage_probe.artifact_sha256"):
        _validate_config(bad)


def test_v21_result_dataclass_fields() -> None:
    r = V21Result(
        output_dir=Path("/tmp/out"),
        run_manifest=Path("/tmp/out/run_manifest.json"),
        artifact_inventory=Path("/tmp/out/artifact_inventory.csv"),
        decision_record=Path("/tmp/out/decision.json"),
    )
    assert r.output_dir == Path("/tmp/out")
    assert r.walkforward_readout is None
    assert r.predictions is None


def test_column_contracts_non_empty() -> None:
    assert len(WALKFORWARD_READOUT_COLUMNS) > 10
    assert len(PER_TICKER_READOUT_COLUMNS) > 5
    assert len(PREDICTION_COLUMNS) > 5
    assert "table_row_id" in WALKFORWARD_READOUT_COLUMNS
    assert "scope" in WALKFORWARD_READOUT_COLUMNS
    assert "readout_tier" in WALKFORWARD_READOUT_COLUMNS
    assert "macro_f1" in WALKFORWARD_READOUT_COLUMNS


def test_scope_and_tier_constants() -> None:
    assert SCOPE == "guarded_walkforward_readout"
    assert READOUT_TIER == "guarded_historically_contacted"


def test_drive_and_resume_artifact_contract_constants() -> None:
    assert "run_manifest.json" in REQUIRED_V2_1_ARTIFACTS
    assert "artifact_inventory.csv" in REQUIRED_V2_1_ARTIFACTS
    assert "v2_1_predictions.csv" in REQUIRED_V2_1_ARTIFACTS
    assert "drive_backup_manifest.json" not in REQUIRED_V2_1_ARTIFACTS
    assert "checkpoint_manifest.json" in RESUME_CHECKPOINT_FILES
    assert "v2_1_ledger_state_partial.json" in RESUME_CHECKPOINT_FILES
    assert "v2_1_predictions_partial.csv" in RESUME_CHECKPOINT_FILES


def _make_ledger_with_results(
    deltas: list[float], period_ids: list[str], seeds: list[int],
) -> _WalkforwardLedger:
    ledger = _WalkforwardLedger()
    idx = 0
    for pid in period_ids:
        for seed in seeds:
            d = deltas[idx % len(deltas)]
            ledger.readout_rows.append({
                "table_row_id": "tcn_frozen_primary",
                "row_kind": "model",
                "period_id": pid,
                "seed": seed,
                "fit_status": "completed",
                "macro_f1": 0.52 + d,
                "delta_macro_f1_vs_stratified_dummy_train_prior": d,
                "delta_macro_f1_vs_majority_train_prior": d - 0.01,
            })
            ledger.scoring_events.append({
                "table_row_id": "tcn_frozen_primary",
                "period_id": pid,
                "seed": seed,
                "n_rows": 100,
            })
            idx += 1
    return ledger


def test_aggregate_and_judge_met_criteria() -> None:
    ledger = _make_ledger_with_results(
        deltas=[0.03, 0.02, 0.01, 0.04],
        period_ids=["wf_p1", "wf_p2"],
        seeds=[101, 202],
    )
    result = _aggregate_and_judge(ledger, MINIMAL_CONFIG)
    assert result["decision"] == "met_predeclared_guarded_stability_criteria"
    assert result["positive_period_count"] == 2
    assert result["pooled_delta"] > 0
    assert result["criteria_met"]["positive_period_count"] is True
    assert result["criteria_met"]["pooled_delta"] is True


def test_aggregate_and_judge_not_met_criteria() -> None:
    ledger = _make_ledger_with_results(
        deltas=[-0.03, -0.02, 0.01, -0.04],
        period_ids=["wf_p1", "wf_p2"],
        seeds=[101, 202],
    )
    result = _aggregate_and_judge(ledger, MINIMAL_CONFIG)
    assert result["decision"] == "did_not_meet_predeclared_guarded_stability_criteria"
    assert result["pooled_delta"] < 0


def test_aggregate_and_judge_empty_ledger() -> None:
    ledger = _WalkforwardLedger()
    result = _aggregate_and_judge(ledger, MINIMAL_CONFIG)
    assert result["decision"] == "did_not_meet_predeclared_guarded_stability_criteria"
    assert result["positive_period_count"] == 0


def test_aggregate_and_judge_none_deltas_ignored() -> None:
    ledger = _WalkforwardLedger()
    ledger.readout_rows.append({
        "table_row_id": "tcn_frozen_primary",
        "period_id": "wf_p1",
        "seed": 101,
        "fit_status": "failed_exception",
        "macro_f1": None,
        "delta_macro_f1_vs_stratified_dummy_train_prior": None,
    })
    result = _aggregate_and_judge(ledger, MINIMAL_CONFIG)
    assert result["positive_period_count"] == 0


def _add_judged_prediction_frames(
    ledger: _WalkforwardLedger,
    period_rows: dict[str, int],
    seeds: list[int],
) -> None:
    """Attach candidate + baseline per-row prediction frames for the judged row
    so _aggregate_and_judge can compute the protocol row-pooled pooled_delta.
    The candidate is perfect on each union and the dummy is half-wrong, so the
    row-pooled delta is clearly positive and differs from the equal-weight value
    derived from the readout-row deltas.
    """
    for pid, n in period_rows.items():
        y_true = np.array([1, 0] * (n // 2), dtype=int)
        cand_pred = y_true.copy()
        dummy_pred = np.array([1, 1, 0, 0] * (n // 4), dtype=int)
        for seed in seeds:
            sample_ids = [f"{pid}_{seed}_{i}" for i in range(n)]
            ledger.prediction_frames.append(pd.DataFrame({
                "table_row_id": "tcn_frozen_primary",
                "candidate_id": "cand",
                "model_family": "tcn",
                "hpo_profile_id": "p",
                "period_id": pid,
                "seed": seed,
                "sample_id": sample_ids,
                "ticker": "AAA",
                "target_timestamp": "2020-01-01",
                "trading_day": "2020-01-01",
                "y_true": y_true,
                "p_up": 0.6,
                "y_pred": cand_pred,
                "scope": SCOPE,
                "readout_tier": READOUT_TIER,
            })[list(PREDICTION_COLUMNS)])
            ledger.baseline_prediction_frames.append(pd.DataFrame({
                "baseline_id": "stratified_dummy_train_prior",
                "period_id": pid,
                "seed": seed,
                "sample_id": sample_ids,
                "ticker": "AAA",
                "target_timestamp": "2020-01-01",
                "trading_day": "2020-01-01",
                "y_true": y_true,
                "p_up": 0.5,
                "y_pred": dummy_pred,
                "scope": SCOPE,
                "readout_tier": READOUT_TIER,
            })[list(BASELINE_PREDICTION_COLUMNS)])


def test_score_seed_dummies_uses_per_seed_draw() -> None:
    # F10 fix: the stratified dummy is scored PER SEED, so each candidate seed's
    # delta uses its own dummy draw rather than the seeds[0] draw reused for all.
    rng = np.random.default_rng(0)
    y_train = rng.integers(0, 2, size=400)
    y_test = rng.integers(0, 2, size=400)
    seed_dummies = _score_seed_dummies(y_train, y_test, [101, 202])
    assert set(seed_dummies) == {101, 202}
    p101 = np.asarray(seed_dummies[101]["predictions"])
    p202 = np.asarray(seed_dummies[202]["predictions"])
    assert not np.array_equal(p101, p202), "distinct seeds must draw distinct dummies"
    # Reproducible: re-scoring with the same seed yields the same draw.
    again = _score_seed_dummies(y_train, y_test, [101])
    assert np.array_equal(np.asarray(again[101]["predictions"]), p101)


def test_aggregate_and_judge_binds_row_pooled_on_fresh_run() -> None:
    ledger = _make_ledger_with_results(
        deltas=[0.01, 0.01, 0.01, 0.01],
        period_ids=["wf_p1", "wf_p2"],
        seeds=[101, 202],
    )
    _add_judged_prediction_frames(
        ledger, period_rows={"wf_p1": 4, "wf_p2": 8}, seeds=[101, 202],
    )
    # Fresh single-pass run -> the protocol section-8 row-pooled estimand is
    # computed and BINDS criterion 2 (register FIX-1, applied).
    result = _aggregate_and_judge(ledger, MINIMAL_CONFIG, is_resumed=False)
    assert result["pooled_delta_row_pooled_available"] is True
    assert result["pooled_delta_estimand"] == "row_pooled"
    assert result["pooled_delta"] == result["pooled_delta_row_pooled"]
    # The two estimands genuinely differ (the divergence FIX-1 is about).
    assert abs(
        result["pooled_delta_row_pooled"] - result["pooled_delta_equal_weight"]
    ) > 1e-9
    assert result["pooled_delta"] > 0
    assert result["decision"] == "met_predeclared_guarded_stability_criteria"


def test_aggregate_and_judge_row_pooled_suppressed_on_resume() -> None:
    ledger = _make_ledger_with_results(
        deltas=[0.01, 0.01, 0.01, 0.01],
        period_ids=["wf_p1", "wf_p2"],
        seeds=[101, 202],
    )
    _add_judged_prediction_frames(
        ledger, period_rows={"wf_p1": 4, "wf_p2": 8}, seeds=[101, 202],
    )
    # On a resumed run the baseline frames may cover only post-resume periods,
    # so the row-union would be coverage-mismatched: row-pooled is suppressed.
    result = _aggregate_and_judge(ledger, MINIMAL_CONFIG, is_resumed=True)
    assert result["pooled_delta_row_pooled_available"] is False
    assert result["pooled_delta_row_pooled"] is None
    # Binding falls back to the equal-weight companion, clearly labelled.
    assert result["pooled_delta_estimand"] == "equal_weight"
    assert result["pooled_delta"] == result["pooled_delta_equal_weight"]


def test_build_comparison_table_structure() -> None:
    ledger = _make_ledger_with_results(
        deltas=[0.03, 0.02, 0.01, 0.04],
        period_ids=["wf_p1", "wf_p2"],
        seeds=[101, 202],
    )
    ledger.baseline_rows = [
        {"baseline_id": "stratified_dummy_train_prior", "macro_f1": 0.50,
         "period_id": "wf_p1"},
        {"baseline_id": "stratified_dummy_train_prior", "macro_f1": 0.50,
         "period_id": "wf_p2"},
    ]
    model_rows = MINIMAL_CONFIG["model_roster"]["model_rows"]
    periods = MINIMAL_CONFIG["walkforward"]["periods"]
    table = _build_comparison_table(ledger, model_rows, periods)
    assert isinstance(table, pd.DataFrame)
    assert "Model" in table.columns
    assert "Mean macro-F1" in table.columns
    assert len(table) == 2  # Dummy + 1 model


def test_build_period_registry_structure() -> None:
    meta = pd.DataFrame({
        "trading_day": ["2020-03-01", "2020-06-01", "2021-03-01"],
        "trading_day_ts": pd.to_datetime(["2020-03-01", "2020-06-01", "2021-03-01"]),
    })
    registry = _build_period_registry(MINIMAL_CONFIG, meta)
    assert registry["period_count"] == 2
    assert len(registry["periods"]) == 2
    assert registry["periods"][0]["period_id"] == "wf_p1"


def test_checkpoint_manifest_payload_records_pending_units() -> None:
    ledger = _WalkforwardLedger(completed_units=["wf_p1:tcn_frozen_primary:101"])
    payload = _checkpoint_manifest_payload(
        MINIMAL_CONFIG, "20260610_000000_123456", ledger
    )
    assert payload["status"] == "incomplete"
    assert payload["completed_units"] == ["wf_p1:tcn_frozen_primary:101"]
    assert payload["pending_units_count"] == 3
    assert payload["pending_units"] == [
        "wf_p1:tcn_frozen_primary:202",
        "wf_p2:tcn_frozen_primary:101",
        "wf_p2:tcn_frozen_primary:202",
    ]


def test_protocol_provenance_fields_echo_guarded_gate_values() -> None:
    fields = _protocol_provenance_fields(MINIMAL_CONFIG)
    assert fields["stage04_run_id_or_ordering_override"] == {
        "stage04_run_id": "20260610_000000_000005",
        "stage04_ordering": "stage04_first",
        "stage04_ordering_override_reason": None,
    }
    assert fields["protocol_reference"]["path"] == (
        "docs/protocols/v2_1_guarded_walkforward_readout_protocol.md"
    )
    assert fields["sign_off"]["status"] == "complete"
    assert fields["coverage_probe"]["artifact_sha256"] == "0" * 64
    assert fields["holdout_contact_authorization"] == {
        "protocol": "docs/protocols/v2_1_guarded_walkforward_readout_protocol.md",
        "sign_off_date": "2026-06-16",
    }
    assert fields["official_validation_used_as_training_rows"] is True
