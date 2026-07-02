from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models import synthetic_control as sc  # noqa: E402
from lst_models.artifacts import feature_rebuild_code_sha256  # noqa: E402
from lst_models.stages import synthetic_positive_control as spc  # noqa: E402


# ---------------------------------------------------------------------------
# domain module: planted rule, injection, date-bound guards, criteria
# ---------------------------------------------------------------------------


def _tiny_events(timestamps: list[str], *, labels: list[int] | None = None) -> pd.DataFrame:
    parsed = [pd.Timestamp(value) for value in timestamps]
    return pd.DataFrame(
        {
            "sample_id": [f"AAA|{ts.isoformat()}" for ts in parsed],
            "ticker": "AAA",
            "target_timestamp": parsed,
            "trading_day": [ts.strftime("%Y-%m-%d") for ts in parsed],
            "label": labels if labels is not None else [1] * len(parsed),
        }
    )


def test_arm_tag_is_canonical() -> None:
    assert sc.arm_tag(0.0) == "arm_s0p000"
    assert sc.arm_tag(0.01) == "arm_s0p010"
    assert sc.arm_tag(0.02) == "arm_s0p020"
    assert sc.arm_tag(0.05) == "arm_s0p050"


def test_planted_rule_values_sign_and_nan_policy() -> None:
    events = _tiny_events(
        ["2010-01-04 09:35:00", "2010-01-04 09:40:00", "2010-01-04 09:45:00"]
    )
    feature_frame = pd.DataFrame(
        {
            "ticker": "AAA",
            "timestamp": events["target_timestamp"],
            "log_return": [0.002, -0.001, np.nan],
        }
    )
    rule, nan_count = sc.planted_rule_values(feature_frame, events)
    assert rule.tolist() == [1, 0, 0]
    assert nan_count == 1


def test_planted_rule_values_missing_bar_raises() -> None:
    events = _tiny_events(["2010-01-04 09:35:00", "2010-01-04 09:40:00"])
    feature_frame = pd.DataFrame(
        {
            "ticker": "AAA",
            "timestamp": [events["target_timestamp"].iloc[0]],
            "log_return": [0.002],
        }
    )
    with pytest.raises(ValueError, match="no matching feature bar"):
        sc.planted_rule_values(feature_frame, events)


def test_relabel_uniforms_deterministic_and_arm_keyed() -> None:
    sample_ids = [f"AAA|2010-01-04T09:{35 + i}:00" for i in range(5)]
    first = sc.relabel_uniforms(sample_ids, injection_seed=20260701, arm_id="arm_s0p020")
    second = sc.relabel_uniforms(sample_ids, injection_seed=20260701, arm_id="arm_s0p020")
    other_arm = sc.relabel_uniforms(sample_ids, injection_seed=20260701, arm_id="arm_s0p050")
    reversed_ids = sc.relabel_uniforms(
        list(reversed(sample_ids)), injection_seed=20260701, arm_id="arm_s0p020"
    )
    assert np.array_equal(first, second)
    assert not np.array_equal(first, other_arm)
    assert np.array_equal(first, reversed_ids[::-1])  # order-invariant per row
    assert ((first >= 0.0) & (first < 1.0)).all()


def _in_domain_events(n_rows: int) -> pd.DataFrame:
    timestamps = pd.date_range("2010-01-04 09:35:00", periods=n_rows, freq="5min")
    labels = [int(index % 2) for index in range(n_rows)]
    events = _tiny_events([str(ts) for ts in timestamps], labels=labels)
    return events


def test_inject_strength_half_matches_rule_exactly() -> None:
    events = _in_domain_events(64)
    rule = np.asarray([index % 3 == 0 for index in range(64)], dtype=int)
    relabeled, stats = sc.inject_planted_labels(
        events, rule, 0, strength=0.5, injection_seed=20260701, arm_id="arm_s0p500"
    )
    assert relabeled["label"].to_numpy().tolist() == rule.tolist()
    assert stats["realized_agreement_rate"] == 1.0
    assert stats["labels_are_synthetic"] is True


def test_inject_null_arm_is_balanced_and_only_changes_labels() -> None:
    events = _in_domain_events(2000)
    rule = np.asarray([1] * 2000, dtype=int)  # even a constant rule must give a fair coin
    relabeled, stats = sc.inject_planted_labels(
        events, rule, 0, strength=0.0, injection_seed=20260701, arm_id="arm_s0p000"
    )
    assert 0.45 < stats["realized_agreement_rate"] < 0.55
    assert 0.45 < stats["synthetic_up_prior"] < 0.55
    # eligibility and identity untouched: same rows, same order, same columns
    # except the replaced label and the added audit column.
    assert relabeled["sample_id"].tolist() == events["sample_id"].tolist()
    assert relabeled["target_timestamp"].tolist() == events["target_timestamp"].tolist()
    assert relabeled["ticker"].tolist() == events["ticker"].tolist()
    assert set(relabeled.columns) - set(events.columns) == {"planted_rule_value"}


def test_inject_is_reproducible_per_arm() -> None:
    events = _in_domain_events(128)
    rule = np.asarray([index % 2 for index in range(128)], dtype=int)
    first, first_stats = sc.inject_planted_labels(
        events, rule, 0, strength=0.02, injection_seed=20260701, arm_id="arm_s0p020"
    )
    second, second_stats = sc.inject_planted_labels(
        events, rule, 0, strength=0.02, injection_seed=20260701, arm_id="arm_s0p020"
    )
    assert first["label"].tolist() == second["label"].tolist()
    assert first_stats["synthetic_label_sha256"] == second_stats["synthetic_label_sha256"]


def test_inject_rejects_out_of_train_domain_rows() -> None:
    events = _tiny_events(["2013-09-16 09:35:00"])
    with pytest.raises(ValueError, match="train-domain only"):
        sc.inject_planted_labels(
            events, np.asarray([1]), 0, strength=0.0, injection_seed=1, arm_id="arm_s0p000"
        )


def test_assert_train_domain_only_is_boundary_exclusive() -> None:
    ok = _tiny_events(["2013-09-13 15:55:00"])
    sc.assert_train_domain_only(ok, ["target_timestamp"], stage_label="test")
    at_boundary = _tiny_events(["2013-09-16 00:00:00"])
    with pytest.raises(ValueError, match="2013-09-16"):
        sc.assert_train_domain_only(at_boundary, ["target_timestamp"], stage_label="test")
    post_2017 = _tiny_events(["2017-02-01 09:35:00"])
    with pytest.raises(ValueError, match="train-domain only"):
        sc.assert_train_domain_only(post_2017, ["target_timestamp"], stage_label="test")
    with pytest.raises(ValueError, match="none of the timestamp columns"):
        sc.assert_train_domain_only(ok, ["missing_column"], stage_label="test")


def test_require_frozen_train_boundaries_blocks_drift() -> None:
    frozen = {
        "train_start": "1998-01-02",
        "train_end": "2013-09-16",
        "validation_start": "2013-09-16",
        "closed_holdout_test_start": "2017-01-25",
    }
    sc.require_frozen_train_boundaries(frozen)
    with pytest.raises(ValueError, match="train_end"):
        sc.require_frozen_train_boundaries({**frozen, "train_end": "2014-01-01"})
    with pytest.raises(ValueError, match="closed_holdout_test_start"):
        sc.require_frozen_train_boundaries(
            {**frozen, "closed_holdout_test_start": "2016-01-01"}
        )


def _real_ledger(deltas: list[float], *, fit_status: str = "completed") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "candidate_id": "price_volume_time_w20",
            "model_family": "tcn",
            "hpo_profile_id": "tcn_p01",
            "fit_status": fit_status,
            "delta_macro_f1_vs_baseline": deltas,
        }
    )


def test_real_control_null_band_reads_max_abs_delta() -> None:
    band = sc.real_control_null_band(
        _real_ledger([0.004, -0.006, 0.001, 0.002, -0.001, 0.003]),
        candidate_id="price_volume_time_w20",
        model_family="tcn",
        hpo_profile_id="tcn_p01",
        expected_rows=6,
    )
    assert band["max_abs_delta"] == pytest.approx(0.006)
    assert band["n_rows"] == 6


def test_real_control_null_band_fails_closed() -> None:
    with pytest.raises(ValueError, match="expected 6"):
        sc.real_control_null_band(
            _real_ledger([0.004, 0.001]),
            candidate_id="price_volume_time_w20",
            model_family="tcn",
            hpo_profile_id="tcn_p01",
            expected_rows=6,
        )
    with pytest.raises(ValueError, match="non-completed"):
        sc.real_control_null_band(
            _real_ledger([0.1] * 6, fit_status="failed_exception"),
            candidate_id="price_volume_time_w20",
            model_family="tcn",
            hpo_profile_id="tcn_p01",
            expected_rows=6,
        )


def _aggregate(
    arm_id: str, mean_delta: float, lcb_delta: float, min_ticker: float,
    *, completed: int = 6, expected: int = 6,
) -> dict:
    return {
        "arm_id": arm_id,
        "expected_rows": expected,
        "completed_rows": completed,
        "failed_rows": expected - completed,
        "mean_delta": mean_delta,
        "lcb_delta": lcb_delta,
        "min_positive_ticker_count": min_ticker,
        "mean_positive_ticker_count": min_ticker,
        "mean_dummy_macro_f1": 0.5,
    }


def _criteria_kwargs() -> dict:
    return {
        "null_band_abs": 0.005,
        "minimum_positive_ticker_count": 3,
        "null_strength": 0.0,
        "detection_strengths": [0.02, 0.05],
        "monotone_strengths": [0.0, 0.02, 0.05],
        "threshold_strength": 0.01,
    }


def test_criteria_pass_scenario() -> None:
    outcome = sc.evaluate_predeclared_criteria(
        {
            0.0: _aggregate("arm_s0p000", 0.001, -0.002, 2.0),
            0.01: _aggregate("arm_s0p010", 0.006, 0.001, 3.0),
            0.02: _aggregate("arm_s0p020", 0.014, 0.008, 4.0),
            0.05: _aggregate("arm_s0p050", 0.041, 0.030, 5.0),
        },
        **_criteria_kwargs(),
    )
    assert outcome["p1_pass"] and outcome["p2_monotone_pass"] and outcome["p3_detection_pass"]
    assert outcome["overall_outcome"] == "pass"
    assert outcome["threshold_arm_flags_signal"] is True


def test_criteria_fail_insensitive_scenario() -> None:
    outcome = sc.evaluate_predeclared_criteria(
        {
            0.0: _aggregate("arm_s0p000", 0.000, -0.003, 2.0),
            0.01: _aggregate("arm_s0p010", 0.001, -0.002, 2.0),
            0.02: _aggregate("arm_s0p020", 0.002, -0.001, 2.0),
            0.05: _aggregate("arm_s0p050", 0.030, 0.020, 5.0),
        },
        **_criteria_kwargs(),
    )
    assert outcome["overall_outcome"] == "fail_insensitive"


def test_criteria_fail_manufacturing_scenario() -> None:
    outcome = sc.evaluate_predeclared_criteria(
        {
            0.0: _aggregate("arm_s0p000", 0.012, 0.006, 5.0),
            0.01: _aggregate("arm_s0p010", 0.015, 0.008, 5.0),
            0.02: _aggregate("arm_s0p020", 0.020, 0.012, 5.0),
            0.05: _aggregate("arm_s0p050", 0.050, 0.040, 5.0),
        },
        **_criteria_kwargs(),
    )
    assert outcome["overall_outcome"] == "fail_manufacturing"


def test_criteria_incomplete_rows_void_the_reading() -> None:
    outcome = sc.evaluate_predeclared_criteria(
        {
            0.0: _aggregate("arm_s0p000", 0.001, -0.002, 2.0),
            0.01: _aggregate("arm_s0p010", 0.006, 0.001, 3.0),
            0.02: _aggregate("arm_s0p020", 0.014, 0.008, 4.0, completed=5),
            0.05: _aggregate("arm_s0p050", 0.041, 0.030, 5.0),
        },
        **_criteria_kwargs(),
    )
    assert outcome["overall_outcome"] == "incomplete_run_fix_and_rerun"


# ---------------------------------------------------------------------------
# run_stage smoke: tiny real fixture + oracle fit (no torch required)
# ---------------------------------------------------------------------------


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _tiny_train_bars() -> pd.DataFrame:
    days = pd.bdate_range("2010-01-04", periods=24)
    rng = np.random.default_rng(7)
    rows = []
    for ticker in ("AAA", "BBB"):
        price = 100.0
        for day in days:
            for bar in range(10):
                timestamp = day + pd.Timedelta(hours=9, minutes=30) + pd.Timedelta(minutes=5 * bar)
                price *= float(np.exp(rng.normal(0.0, 0.001)))
                rows.append(
                    {
                        "ticker": ticker,
                        "timestamp": timestamp,
                        "open": price,
                        "high": price * 1.001,
                        "low": price * 0.999,
                        "close": price,
                        "volume": 1000.0,
                        "split": "train",
                    }
                )
    bars = pd.DataFrame(rows)
    bars["trading_day"] = bars["timestamp"].dt.strftime("%Y-%m-%d")
    return bars.sort_values(["ticker", "timestamp"]).reset_index(drop=True)


def _tiny_event_index(bars: pd.DataFrame, *, poison: bool = False) -> pd.DataFrame:
    rows = []
    for (ticker, _), group in bars.groupby(["ticker", "trading_day"], sort=False):
        ordered = group.sort_values("timestamp").reset_index(drop=True)
        for position in range(2, 9):
            timestamp = ordered.loc[position, "timestamp"]
            rows.append(
                {
                    "sample_id": f"{ticker}|{timestamp.isoformat()}",
                    "ticker": ticker,
                    "target_timestamp": timestamp,
                    "trading_day": timestamp.strftime("%Y-%m-%d"),
                    "split": "train",
                    "label": int(position % 2),
                    "valid_label": True,
                    "horizon_end_timestamp": timestamp + pd.Timedelta(minutes=5),
                }
            )
    if poison:
        poisoned_ts = pd.Timestamp("2013-09-20 09:45:00")
        rows.append(
            {
                "sample_id": f"AAA|{poisoned_ts.isoformat()}",
                "ticker": "AAA",
                "target_timestamp": poisoned_ts,
                "trading_day": "2013-09-20",
                "split": "train",
                "label": 1,
                "valid_label": True,
                "horizon_end_timestamp": poisoned_ts + pd.Timedelta(minutes=5),
            }
        )
    return pd.DataFrame(rows)


def _smoke_config(tmp_path: Path, *, arms: list[dict] | None = None) -> dict:
    search_space_path = tmp_path / "search_spaces" / "tcn" / "search_space.yaml"
    search_space_path.parent.mkdir(parents=True)
    search_space_path.write_text(
        yaml.safe_dump(
            {
                "model_family": "tcn",
                "search_mode": "bounded_profiles",
                "profiles": [
                    {
                        "profile_id": "tcn_p01",
                        "channels": [4],
                        "kernel_size": 2,
                        "dropout": 0.0,
                        "learning_rate": 0.001,
                        "weight_decay": 0.0,
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    notebook_path = tmp_path / "v2_synthetic_positive_control_colab.ipynb"
    notebook_path.write_text("{}", encoding="utf-8")
    if arms is None:
        arms = [
            {"arm_id": "arm_s0p000", "strength": 0.0, "role": "mandatory_null_arm"},
            {"arm_id": "arm_s0p500", "strength": 0.5, "role": "must_detect_arm"},
        ]
    return {
        "stage_name": "v2_synthetic_positive_control",
        "route": "lst_models",
        "scope": "validation_only",
        "holdout_test_contact": False,
        "synthetic_labels": True,
        "train_domain_only": True,
        "inputs": {
            "stage00_run_id": "stage00_test",
            "stage00_runtime_run_dir": str(tmp_path / "stage00"),
            "required_stage00_artifacts": [
                "raw_data_manifest.json",
                "split_freeze.json",
                "label_policy.json",
                "baseline_registry.json",
                "sample_event_index.csv",
                "run_manifest.json",
            ],
            "raw_data_manifest": str(tmp_path / "raw.yaml"),
            "raw_data_dir": str(tmp_path / "raw"),
            "stage01_run_id": "stage01_test",
            "stage01_runtime_run_dir": str(tmp_path / "stage01"),
            "required_stage01_artifacts": ["run_manifest.json", "01_candidate_inputs.json"],
            "stage02_real_run_id": "stage02_real_test",
            "stage02_real_runtime_run_dir": str(tmp_path / "stage02_real"),
            "required_stage02_artifacts": ["run_manifest.json", "02_hpo_trial_ledger.csv"],
            "notebook_path": str(notebook_path),
        },
        "candidate": {"candidate_id": "toy_w2"},
        "model": {
            "family": "tcn",
            "probe_id": "tcn_tiny",
            "hpo_profile_id": "tcn_p01",
            "search_space": str(search_space_path),
        },
        "injection": {
            "rule_id": "sign_of_day_local_log_return_at_target_bar",
            "rule_feature": "log_return",
            "injection_seed": 20260701,
            "arms": arms,
        },
        "train_inner": {
            "n_folds": 2,
            "seeds": [101, 202],
            "official_validation_for_selection": False,
            "event_overlap_count_required": 0,
        },
        "sample_policy": {
            "max_train_samples_per_fold": 0,
            "max_eval_samples_per_fold": 0,
            "sample_method": "deterministic_even_stride_by_ticker_label",
        },
        "probe_training_defaults": {
            "torch": {
                "epochs": 1,
                "batch_size": 64,
                "learning_rate": 0.001,
                "weight_decay": 0.0,
                "device": "cpu",
                "require_gpu": False,
                "early_stopping": "none",
            }
        },
        "budget": {"max_planned_fit_rows": 8},
        "sentinels": {"n_perm": 5, "seed": 20260617},
        "criteria": {
            "primary_baseline": "stratified_dummy_train_prior",
            "minimum_positive_ticker_count": 2,
            "null_strength": 0.0,
            "detection_strengths": [0.5],
            "monotone_strengths": [0.0, 0.5],
            "threshold_strength": 0.5,
            "null_band_source": {
                "artifact": "02_hpo_trial_ledger.csv",
                "candidate_id": "toy_w2",
                "model_family": "tcn",
                "hpo_profile_id": "tcn_p01",
                "expected_rows": 6,
            },
        },
        "checkpointing": {
            "enabled": True,
            "checkpoint_dir": str(tmp_path / "checkpoints"),
        },
        "outputs": {
            "output_dir": str(tmp_path / "out"),
            "manifest": "run_manifest.json",
            "artifact_inventory": "artifact_inventory.csv",
            "trial_ledger": "spc_trial_ledger.csv",
            "arm_summary": "spc_arm_summary.csv",
            "baseline_control_summary": "spc_baseline_control_summary.csv",
            "sentinel_ledger": "spc_sentinel_ledger.csv",
            "injection_manifest": "spc_injection_manifest.json",
            "criteria_readout": "spc_criteria_readout.json",
            "per_arm_trials_prefix": "spc_trials_",
        },
    }


def _write_smoke_inputs(tmp_path: Path, bars: pd.DataFrame, *, poison: bool = False) -> None:
    stage00 = tmp_path / "stage00"
    stage00.mkdir()
    _write_json(stage00 / "run_manifest.json", {"holdout_test_contact": False})
    _write_json(stage00 / "raw_data_manifest.json", {})
    _write_json(
        stage00 / "split_freeze.json",
        {
            "train_start": "1998-01-02",
            "train_end": "2013-09-16",
            "validation_start": "2013-09-16",
            "validation_end": "2017-01-25",
            "closed_holdout_test_start": "2017-01-25",
        },
    )
    _write_json(stage00 / "label_policy.json", {})
    _write_json(stage00 / "baseline_registry.json", {})
    _tiny_event_index(bars, poison=poison).to_csv(
        stage00 / "sample_event_index.csv", index=False
    )

    stage01 = tmp_path / "stage01"
    stage01.mkdir()
    _write_json(
        stage01 / "run_manifest.json",
        {
            "holdout_test_contact": False,
            "feature_rebuild_code_sha256": feature_rebuild_code_sha256(),
        },
    )
    _write_json(
        stage01 / "01_candidate_inputs.json",
        {
            "holdout_test_contact": False,
            "no_final_model_selected": True,
            "candidate_inputs": [
                {
                    "candidate_id": "toy_w2",
                    "feature_set": "toy",
                    "feature_columns": ["log_return"],
                    "window_size": 2,
                }
            ],
        },
    )

    stage02 = tmp_path / "stage02_real"
    stage02.mkdir()
    _write_json(
        stage02 / "run_manifest.json",
        {
            "holdout_test_contact": False,
            "stage02_run_id": "stage02_real_test",
            "source_stage01_run_id": "stage01_test",
        },
    )
    pd.DataFrame(
        {
            "candidate_id": "toy_w2",
            "model_family": "tcn",
            "hpo_profile_id": "tcn_p01",
            "fit_status": "completed",
            "delta_macro_f1_vs_baseline": [0.004, -0.003, 0.002, 0.001, -0.002, 0.003],
        }
    ).to_csv(stage02 / "02_hpo_trial_ledger.csv", index=False)


def _oracle_fit(probe_id, profile, x_train, train_meta, x_eval, config, seed,
                window_size, n_features):
    """Deterministic stand-in for the tcn_tiny fit: predicts the planted rule
    (sign of the target bar's log_return) directly from the eval windows."""
    last_bar = np.asarray(x_eval)[:, -int(n_features):]
    predictions = (last_bar[:, 0] > 0.0).astype(int)
    return {
        "fit_status": "completed",
        "error_message": "",
        "predictions": predictions,
        "scores": np.where(predictions == 1, 0.9, 0.1),
        "best_iteration": 1,
        "early_stopping_source": "disabled",
        "early_stopping_used": False,
        "early_stopping_reason": "test_oracle",
        "early_stopping_train_sample_id_hash": "",
        "early_stopping_eval_sample_id_hash": "",
        "requested_device": "cpu",
        "resolved_device": "cpu",
        "device_fallback_reason": "not_gpu_capable_trial",
    }


def test_run_stage_smoke_with_oracle_fit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bars = _tiny_train_bars()
    _write_smoke_inputs(tmp_path, bars)
    config = _smoke_config(tmp_path)
    monkeypatch.setattr(spc, "load_train_bars", lambda *args, **kwargs: bars)
    monkeypatch.setattr(spc, "fit_stage_control", _oracle_fit)

    result = spc.run_stage(config)

    for path in (
        result.run_manifest, result.artifact_inventory, result.trial_ledger,
        result.arm_summary, result.baseline_control_summary, result.sentinel_ledger,
        result.injection_manifest, result.criteria_readout,
    ):
        assert path.exists(), path

    trial_ledger = pd.read_csv(result.trial_ledger)
    assert len(trial_ledger) == 2 * 2 * 2  # arms x folds x seeds
    assert set(trial_ledger["fit_status"]) == {"completed"}
    assert set(trial_ledger["model_family"]) == {"tcn"}
    assert set(trial_ledger["hpo_profile_id"]) == {"tcn_p01"}

    # strength 0.5 relabels every row to the rule; the oracle predicts the rule
    # exactly, so its macro-F1 is exactly 1.0 on every fold/seed row.
    planted = trial_ledger.loc[trial_ledger["arm_id"] == "arm_s0p500"]
    assert (planted["macro_f1"].astype(float) == 1.0).all()
    assert (planted["delta_macro_f1_vs_baseline"].astype(float) > 0.0).all()

    injection = json.loads(result.injection_manifest.read_text(encoding="utf-8"))
    assert injection["labels_are_synthetic"] is True
    assert injection["eligibility_invariance"]["all_arms_identical_rows"] is True
    by_arm = {record["arm_id"]: record for record in injection["arms"]}
    assert by_arm["arm_s0p500"]["realized_agreement_rate"] == 1.0
    assert 0.45 < by_arm["arm_s0p000"]["realized_agreement_rate"] < 0.55
    assert (
        by_arm["arm_s0p000"]["synthetic_label_sha256"]
        != by_arm["arm_s0p500"]["synthetic_label_sha256"]
    )

    arm_summary = pd.read_csv(result.arm_summary)
    planted_row = arm_summary.loc[arm_summary["arm_id"] == "arm_s0p500"].iloc[0]
    null_row = arm_summary.loc[arm_summary["arm_id"] == "arm_s0p000"].iloc[0]
    assert bool(planted_row["flags_signal"]) is True
    assert (
        planted_row["mean_delta_macro_f1_vs_stratified_dummy_train_prior"]
        > null_row["mean_delta_macro_f1_vs_stratified_dummy_train_prior"]
    )

    criteria = json.loads(result.criteria_readout.read_text(encoding="utf-8"))
    assert criteria["p3_detection_pass"] is True
    assert criteria["null_band_source"]["max_abs_delta"] == pytest.approx(0.004)
    assert criteria["evidence_status"] == (
        "synthetic_positive_control_protocol_validation_only"
    )

    manifest = json.loads(result.run_manifest.read_text(encoding="utf-8"))
    assert manifest["synthetic_labels"] is True
    assert manifest["train_domain_only"] is True
    assert manifest["holdout_test_contact"] is False
    assert manifest["official_validation_contact"] is False
    assert manifest["planted_rule_id"] == "sign_of_day_local_log_return_at_target_bar"
    assert manifest["train_domain_bounds"]["max_target_timestamp"] < "2013-09-16"

    baseline_summary = pd.read_csv(result.baseline_control_summary)
    assert set(baseline_summary["baseline_id"]) == {
        "stratified_dummy_train_prior", "majority_train_prior", "constant_up", "constant_down",
    }
    sentinel_ledger = pd.read_csv(result.sentinel_ledger)
    assert len(sentinel_ledger) == len(trial_ledger)

    per_arm = sorted(path.name for path in result.output_dir.glob("spc_trials_arm_*.csv"))
    assert per_arm == ["spc_trials_arm_s0p000.csv", "spc_trials_arm_s0p500.csv"]

    checkpoint_manifest = (
        tmp_path / "checkpoints" / result.output_dir.name / "checkpoint_manifest.json"
    )
    assert checkpoint_manifest.exists()


def test_run_stage_blocks_on_out_of_domain_event_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bars = _tiny_train_bars()
    _write_smoke_inputs(tmp_path, bars, poison=True)
    config = _smoke_config(tmp_path)
    monkeypatch.setattr(spc, "load_train_bars", lambda *args, **kwargs: bars)
    monkeypatch.setattr(spc, "fit_stage_control", _oracle_fit)
    with pytest.raises(ValueError, match="train-domain only"):
        spc.run_stage(config)


def test_validate_config_rejects_unsafe_or_undeclared_settings(tmp_path: Path) -> None:
    config = _smoke_config(tmp_path)
    spc._validate_config(config)

    broken = dict(config)
    broken["synthetic_labels"] = False
    with pytest.raises(ValueError, match="synthetic_labels=true"):
        spc._validate_config(broken)

    broken = dict(config)
    broken["model"] = {**config["model"], "probe_id": "ms_dlinear_tcn_tiny"}
    with pytest.raises(ValueError, match="tcn_tiny primary profile only"):
        spc._validate_config(broken)

    broken = dict(config)
    broken["injection"] = {
        **config["injection"],
        "arms": [
            {"arm_id": "arm_s0p010", "strength": 0.01, "role": "x"},
            {"arm_id": "arm_s0p020", "strength": 0.02, "role": "y"},
        ],
    }
    with pytest.raises(ValueError, match="mandatory null arm"):
        spc._validate_config(broken)

    broken = dict(config)
    broken["criteria"] = {**config["criteria"], "detection_strengths": [0.09]}
    with pytest.raises(ValueError, match="not a declared arm strength"):
        spc._validate_config(broken)
