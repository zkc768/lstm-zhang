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

from lst_models import robustness as rb  # noqa: E402
from lst_models.artifacts import feature_rebuild_code_sha256  # noqa: E402
from lst_models.features import build_feature_frame  # noqa: E402
from lst_models.splits import build_train_inner_folds  # noqa: E402
from lst_models.stages import band_horizon_sensitivity as bhs  # noqa: E402
from lst_models.windows import (  # noqa: E402
    build_window_dataset,
    cap_indices,
    fold_indices,
    sample_id_hash,
)


# ---------------------------------------------------------------------------
# domain module: cell tags, cross validation, rebuild, parity, reading rules
# ---------------------------------------------------------------------------


def test_cell_tag_matches_stage00_label_config_style() -> None:
    assert rb.cell_tag(9, 3.0) == "h09_bps3p0"
    assert rb.cell_tag(9, 2.0) == "h09_bps2p0"
    assert rb.cell_tag(9, 4.0) == "h09_bps4p0"
    assert rb.cell_tag(6, 3.0) == "h06_bps3p0"
    assert rb.cell_tag(12, 3.0) == "h12_bps3p0"


def _full_cross() -> list[dict]:
    return [
        {"cell_id": "h09_bps2p0", "horizon_k": 9, "no_trade_band_bps": 2.0, "cell_axis": "band"},
        {"cell_id": "h09_bps3p0", "horizon_k": 9, "no_trade_band_bps": 3.0, "cell_axis": "frozen"},
        {"cell_id": "h09_bps4p0", "horizon_k": 9, "no_trade_band_bps": 4.0, "cell_axis": "band"},
        {"cell_id": "h06_bps3p0", "horizon_k": 6, "no_trade_band_bps": 3.0, "cell_axis": "horizon"},
        {"cell_id": "h12_bps3p0", "horizon_k": 12, "no_trade_band_bps": 3.0, "cell_axis": "horizon"},
    ]


def test_validate_cell_specs_accepts_the_preregistered_cross() -> None:
    cells = rb.validate_cell_specs(_full_cross())
    assert [cell["cell_id"] for cell in cells] == [
        "h09_bps2p0", "h09_bps3p0", "h09_bps4p0", "h06_bps3p0", "h12_bps3p0",
    ]
    assert sum(cell["is_frozen_cell"] for cell in cells) == 1


def test_validate_cell_specs_rejects_grid_missing_frozen_and_bad_ids() -> None:
    with pytest.raises(ValueError, match="never a grid"):
        rb.validate_cell_specs(
            _full_cross()
            + [{"cell_id": "h06_bps2p0", "horizon_k": 6, "no_trade_band_bps": 2.0,
                "cell_axis": "band"}]
        )
    without_frozen = [cell for cell in _full_cross() if cell["cell_id"] != "h09_bps3p0"]
    with pytest.raises(ValueError, match="exactly one frozen cell"):
        rb.validate_cell_specs(without_frozen)
    renamed = _full_cross()
    renamed[0] = {**renamed[0], "cell_id": "band_low"}
    with pytest.raises(ValueError, match="canonical tag"):
        rb.validate_cell_specs(renamed)


def test_require_frozen_label_policy_blocks_drift() -> None:
    rb.require_frozen_label_policy(
        {"operator": "endpoint_cumulative_return", "horizon_k": 9, "no_trade_band_bps": 3.0}
    )
    with pytest.raises(ValueError, match="operator"):
        rb.require_frozen_label_policy(
            {"operator": "smoothed_average_return", "horizon_k": 9, "no_trade_band_bps": 3.0}
        )
    with pytest.raises(ValueError, match="horizon_k"):
        rb.require_frozen_label_policy(
            {"operator": "endpoint_cumulative_return", "horizon_k": 7, "no_trade_band_bps": 3.0}
        )
    with pytest.raises(ValueError, match="no_trade_band_bps"):
        rb.require_frozen_label_policy(
            {"operator": "endpoint_cumulative_return", "horizon_k": 9, "no_trade_band_bps": 5.0}
        )


def _tiny_train_bars(n_days: int = 12, bars_per_day: int = 30) -> pd.DataFrame:
    days = pd.bdate_range("2010-01-04", periods=n_days)
    rng = np.random.default_rng(7)
    rows = []
    for ticker in ("AAA", "BBB"):
        price = 100.0
        for day in days:
            for bar in range(bars_per_day):
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


def test_rebuild_cell_events_band_and_horizon_mechanics() -> None:
    bars = _tiny_train_bars()
    tight, tight_profile = rb.rebuild_cell_events(bars, horizon_k=9, band_bps=2.0)
    frozen, frozen_profile = rb.rebuild_cell_events(bars, horizon_k=9, band_bps=3.0)
    wide, wide_profile = rb.rebuild_cell_events(bars, horizon_k=9, band_bps=4.0)
    longer, longer_profile = rb.rebuild_cell_events(bars, horizon_k=12, band_bps=3.0)
    # A tighter band keeps at least as many rows; a wider band keeps at most.
    assert len(tight) >= len(frozen) >= len(wide)
    assert tight_profile["n_invalid_no_trade_band"] <= wide_profile["n_invalid_no_trade_band"]
    # A longer horizon invalidates more end-of-day rows.
    assert longer_profile["n_invalid_cross_trading_day"] >= frozen_profile[
        "n_invalid_cross_trading_day"
    ]
    # Labels are day-local: horizon-end timestamps stay on the target day.
    assert (
        pd.to_datetime(frozen["horizon_end_timestamp"]).dt.strftime("%Y-%m-%d")
        == frozen["trading_day"]
    ).all()
    assert frozen_profile["n_eligible_label_rows"] == len(frozen)
    assert 0.0 < frozen_profile["up_prior"] < 1.0


def test_frozen_cell_event_parity_gate_detects_label_drift() -> None:
    bars = _tiny_train_bars()
    frozen, _ = rb.rebuild_cell_events(bars, horizon_k=9, band_bps=3.0)
    rb.require_frozen_cell_event_parity(frozen, frozen.copy(), stage_label="test")
    flipped = frozen.copy()
    flipped.loc[flipped.index[0], "label"] = 1 - int(flipped.iloc[0]["label"])
    with pytest.raises(ValueError, match="labels differ"):
        rb.require_frozen_cell_event_parity(flipped, frozen, stage_label="test")
    with pytest.raises(ValueError, match="eligible rows"):
        rb.require_frozen_cell_event_parity(frozen.iloc[:-1], frozen, stage_label="test")


def _reading_ledger(deltas_by_cell: dict[str, list[float]]) -> pd.DataFrame:
    rows = []
    for cell_id, deltas in deltas_by_cell.items():
        for index, delta in enumerate(deltas):
            rows.append(
                {
                    "cell_id": cell_id,
                    "fold_id": f"fold_{index % 3}",
                    "seed": 101 if index < 3 else 202,
                    "fit_status": "completed",
                    "delta_macro_f1_vs_baseline": delta,
                    "baseline_macro_f1": 0.5,
                    "positive_ticker_count": 3.0,
                }
            )
    return pd.DataFrame(rows)


def test_band_horizon_reading_sign_stable_and_flip_outcomes() -> None:
    cells = rb.validate_cell_specs(_full_cross())
    stable = _reading_ledger({cell["cell_id"]: [0.002] * 6 for cell in cells})
    reading = rb.band_horizon_reading(stable, cells)
    assert reading["overall_outcome"] == "not_knife_edge_sign_stable_both_axes"
    assert reading["band_axis_sign_stable"] is True
    assert reading["horizon_axis_sign_stable"] is True
    assert reading["no_cell_preferred"] is True
    assert reading["no_alternative_cell_recommended"] is True

    flipped = _reading_ledger(
        {
            cell["cell_id"]: ([-0.002] * 6 if cell["cell_id"] == "h09_bps4p0" else [0.002] * 6)
            for cell in cells
        }
    )
    reading = rb.band_horizon_reading(flipped, cells)
    assert reading["overall_outcome"] == "sign_flip_on_band_axis_limitation_strengthened"
    assert reading["band_axis_sign_stable"] is False
    assert reading["horizon_axis_sign_stable"] is True


def test_band_horizon_reading_incomplete_voids_the_reading() -> None:
    cells = rb.validate_cell_specs(_full_cross())
    ledger = _reading_ledger({cell["cell_id"]: [0.002] * 6 for cell in cells})
    ledger.loc[0, "fit_status"] = "failed_exception"
    reading = rb.band_horizon_reading(ledger, cells)
    assert reading["overall_outcome"] == "incomplete_run_fix_and_rerun"


def test_resolve_run_id_or_new_validates_format() -> None:
    assert rb.resolve_run_id_or_new(None, stage_label="test")
    assert rb.resolve_run_id_or_new("20260701_120000_123456", stage_label="test") == (
        "20260701_120000_123456"
    )
    with pytest.raises(ValueError, match="run_id"):
        rb.resolve_run_id_or_new("latest", stage_label="test")


# ---------------------------------------------------------------------------
# run_stage smoke: tiny real fixture + oracle fit (no torch required)
# ---------------------------------------------------------------------------


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


SMOKE_CELLS = [
    {"cell_id": "h09_bps2p0", "horizon_k": 9, "no_trade_band_bps": 2.0, "cell_axis": "band"},
    {"cell_id": "h09_bps3p0", "horizon_k": 9, "no_trade_band_bps": 3.0, "cell_axis": "frozen"},
    {"cell_id": "h12_bps3p0", "horizon_k": 12, "no_trade_band_bps": 3.0, "cell_axis": "horizon"},
]


def _write_smoke_inputs(tmp_path: Path, bars: pd.DataFrame, *, poison: bool = False) -> None:
    frozen_events, _ = rb.rebuild_cell_events(bars, horizon_k=9, band_bps=3.0)
    event_index = frozen_events.assign(valid_label=True)
    if poison:
        poisoned_ts = pd.Timestamp("2013-09-20 09:45:00")
        poison_row = event_index.iloc[[0]].copy()
        poison_row["sample_id"] = f"AAA|{poisoned_ts.isoformat()}"
        poison_row["target_timestamp"] = poisoned_ts
        poison_row["horizon_end_timestamp"] = poisoned_ts + pd.Timedelta(minutes=45)
        poison_row["trading_day"] = "2013-09-20"
        event_index = pd.concat([event_index, poison_row], ignore_index=True)

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
    _write_json(
        stage00 / "label_policy.json",
        {"operator": "endpoint_cumulative_return", "horizon_k": 9, "no_trade_band_bps": 3.0},
    )
    _write_json(stage00 / "baseline_registry.json", {})
    event_index.to_csv(stage00 / "sample_event_index.csv", index=False)

    feature_frame = build_feature_frame(bars)
    dataset = build_window_dataset(
        feature_frame, frozen_events, feature_set="toy",
        feature_columns=("log_return",), window_size=2,
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
    pd.DataFrame(
        [
            {
                "candidate_id": "toy_w2",
                "n_samples_total": int(len(dataset.metadata)),
                "n_samples_by_ticker_json": json.dumps(
                    {
                        str(ticker): int(count)
                        for ticker, count in dataset.metadata.groupby("ticker").size().items()
                    }
                ),
            }
        ]
    ).to_csv(stage01 / "01_feature_window_search_summary.csv", index=False)

    folds = build_train_inner_folds(frozen_events, 2)
    plan_rows = []
    for fold in folds.to_dict(orient="records"):
        train_idx, eval_idx = fold_indices(dataset.metadata, fold)
        train_idx = cap_indices(dataset.metadata, train_idx, 0)
        eval_idx = cap_indices(dataset.metadata, eval_idx, 0)
        plan_rows.append(
            {
                "candidate_id": "toy_w2",
                "fold_id": str(fold["fold_id"]),
                "train_sample_id_hash": sample_id_hash(
                    dataset.metadata.iloc[train_idx]["sample_id"].tolist()
                ),
                "eval_sample_id_hash": sample_id_hash(
                    dataset.metadata.iloc[eval_idx]["sample_id"].tolist()
                ),
            }
        )
    stage02 = tmp_path / "stage02"
    stage02.mkdir()
    _write_json(
        stage02 / "run_manifest.json",
        {
            "holdout_test_contact": False,
            "stage02_run_id": "stage02_test",
            "source_stage01_run_id": "stage01_test",
        },
    )
    pd.DataFrame(plan_rows).to_csv(stage02 / "02_hpo_plan_ledger.csv", index=False)


def _smoke_config(tmp_path: Path) -> dict:
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
    notebook_path = tmp_path / "v2_band_horizon_sensitivity_colab.ipynb"
    notebook_path.write_text("{}", encoding="utf-8")
    return {
        "stage_name": "v2_band_horizon_sensitivity",
        "route": "lst_models",
        "scope": "validation_only",
        "holdout_test_contact": False,
        "train_domain_only": True,
        "sensitivity_scan_no_cell_selected": True,
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
            "required_stage01_artifacts": [
                "run_manifest.json",
                "01_candidate_inputs.json",
                "01_feature_window_search_summary.csv",
            ],
            "stage02_run_id": "stage02_test",
            "stage02_runtime_run_dir": str(tmp_path / "stage02"),
            "required_stage02_artifacts": ["run_manifest.json", "02_hpo_plan_ledger.csv"],
            "notebook_path": str(notebook_path),
        },
        "candidate": {"candidate_id": "toy_w2"},
        "model": {
            "family": "tcn",
            "probe_id": "tcn_tiny",
            "hpo_profile_id": "tcn_p01",
            "search_space": str(search_space_path),
        },
        "label_scan": {
            "operator": "endpoint_cumulative_return",
            "frozen_cell": {"horizon_k": 9, "no_trade_band_bps": 3.0},
            "cells": SMOKE_CELLS,
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
        "budget": {"max_planned_fit_rows": 16},
        "reading_rules": {
            "primary_baseline": "stratified_dummy_train_prior",
            "rule_id": "sign_stability_across_adjacent_cells_per_axis",
            "cells_are_never_ranked": True,
            "no_alternative_cell_recommended": True,
        },
        "checkpointing": {"enabled": True, "checkpoint_dir": str(tmp_path / "checkpoints")},
        "outputs": {
            "output_dir": str(tmp_path / "out"),
            "manifest": "run_manifest.json",
            "trial_ledger": "bhs_trial_ledger.csv",
            "cell_summary": "bhs_cell_summary.csv",
            "cell_eligibility": "bhs_cell_eligibility.csv",
            "fold_manifest": "bhs_fold_manifest.csv",
            "baseline_control_summary": "bhs_baseline_control_summary.csv",
            "reading_readout": "bhs_reading_readout.json",
            "per_cell_trials_prefix": "bhs_trials_",
        },
    }


def _oracle_fit(probe_id, profile, x_train, train_meta, x_eval, config, seed,
                window_size, n_features):
    """Deterministic stand-in for the tcn_tiny fit: predicts the sign of the
    last bar's log_return from the eval windows."""
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
    monkeypatch.setattr(rb, "load_train_bars", lambda *args, **kwargs: bars)
    monkeypatch.setattr(bhs, "fit_stage_control", _oracle_fit)

    result = bhs.run_stage(config)

    for path in (
        result.run_manifest, result.artifact_inventory, result.trial_ledger,
        result.cell_summary, result.cell_eligibility, result.fold_manifest,
        result.baseline_control_summary, result.reading_readout,
    ):
        assert path.exists(), path

    trial_ledger = pd.read_csv(result.trial_ledger)
    assert len(trial_ledger) == 3 * 2 * 2  # cells x folds x seeds
    assert set(trial_ledger["fit_status"]) == {"completed"}
    assert set(trial_ledger["cell_id"]) == {cell["cell_id"] for cell in SMOKE_CELLS}
    assert set(trial_ledger["hpo_profile_id"]) == {"tcn_p01"}
    frozen_rows = trial_ledger.loc[trial_ledger["cell_id"] == "h09_bps3p0"]
    assert frozen_rows["is_frozen_cell"].all()

    eligibility = pd.read_csv(result.cell_eligibility)
    by_cell = eligibility.set_index("cell_id")
    # The band changes eligibility mechanically: tighter band keeps >= rows.
    assert (
        by_cell.loc["h09_bps2p0", "n_eligible_label_rows"]
        >= by_cell.loc["h09_bps3p0", "n_eligible_label_rows"]
    )
    # A longer horizon invalidates more end-of-day rows.
    assert (
        by_cell.loc["h12_bps3p0", "n_eligible_label_rows"]
        <= by_cell.loc["h09_bps3p0", "n_eligible_label_rows"]
    )
    assert by_cell.loc["h09_bps3p0", "frozen_cell_event_parity"] == (
        "passed_matches_stage00_event_index"
    )
    assert by_cell.loc["h09_bps2p0", "frozen_cell_event_parity"] == (
        "not_applicable_rebuilt_labels"
    )

    reading = json.loads(result.reading_readout.read_text(encoding="utf-8"))
    assert reading["no_cell_preferred"] is True
    assert reading["no_cell_ranked"] is True
    assert reading["no_alternative_cell_recommended"] is True
    assert reading["frozen_protocol_values_unchanged"] is True
    assert reading["frozen_cell_id"] == "h09_bps3p0"
    assert set(reading["per_cell"]) == {cell["cell_id"] for cell in SMOKE_CELLS}

    manifest = json.loads(result.run_manifest.read_text(encoding="utf-8"))
    assert manifest["train_domain_only"] is True
    assert manifest["holdout_test_contact"] is False
    assert manifest["official_validation_contact"] is False
    assert manifest["sensitivity_scan_no_cell_selected"] is True
    assert manifest["no_cell_preferred"] is True
    assert manifest["evidence_status"] == (
        "train_inner_protocol_sensitivity_scan_no_cell_selected"
    )
    assert manifest["train_domain_bounds"]["max_target_timestamp"] < "2013-09-16"

    baseline_summary = pd.read_csv(result.baseline_control_summary)
    assert set(baseline_summary["baseline_id"]) == {
        "stratified_dummy_train_prior", "majority_train_prior", "constant_up", "constant_down",
    }
    fold_manifest = pd.read_csv(result.fold_manifest)
    assert set(fold_manifest["cell_id"]) == {cell["cell_id"] for cell in SMOKE_CELLS}
    assert (fold_manifest["event_overlap_count"] == 0).all()

    per_cell = sorted(path.name for path in result.output_dir.glob("bhs_trials_*.csv"))
    assert per_cell == [
        "bhs_trials_h09_bps2p0.csv", "bhs_trials_h09_bps3p0.csv", "bhs_trials_h12_bps3p0.csv",
    ]
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
    monkeypatch.setattr(rb, "load_train_bars", lambda *args, **kwargs: bars)
    monkeypatch.setattr(bhs, "fit_stage_control", _oracle_fit)
    with pytest.raises(ValueError, match="train-domain only"):
        bhs.run_stage(config)


def test_validate_config_rejects_unsafe_or_undeclared_settings(tmp_path: Path) -> None:
    config = _smoke_config(tmp_path)
    bhs._validate_config(config)

    broken = dict(config)
    broken["sensitivity_scan_no_cell_selected"] = False
    with pytest.raises(ValueError, match="sensitivity_scan_no_cell_selected=true"):
        bhs._validate_config(broken)

    broken = dict(config)
    broken["model"] = {**config["model"], "probe_id": "ms_dlinear_tcn_tiny"}
    with pytest.raises(ValueError, match="tcn_tiny frozen primary profile only"):
        bhs._validate_config(broken)

    broken = dict(config)
    broken["label_scan"] = {
        **config["label_scan"],
        "frozen_cell": {"horizon_k": 9, "no_trade_band_bps": 2.0},
    }
    with pytest.raises(ValueError, match="frozen_cell"):
        bhs._validate_config(broken)

    broken = dict(config)
    broken["reading_rules"] = {**config["reading_rules"], "cells_are_never_ranked": False}
    with pytest.raises(ValueError, match="cells_are_never_ranked"):
        bhs._validate_config(broken)
