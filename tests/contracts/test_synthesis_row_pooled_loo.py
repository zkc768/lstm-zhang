"""Unit tests for the row-pooled LOO domain function (synthesis.build_row_pooled_loo).

This is the TRUE row-pooled leave-one-out of the binding guarded estimand
(protocol §8 row union). macro-F1 is non-linear across rows, so it recomputes
pooled macro-F1 from the raw predictions; these tests validate the drop/seed
plumbing + schema against an inline reference (the trusted metrics primitive),
and that the no-drop baseline equals the row-union delta.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models import metrics, synthesis  # noqa: E402


def _reference_row_pooled_delta(cand: pd.DataFrame, base: pd.DataFrame) -> float:
    seeds = sorted(set(cand["seed"]) & set(base["seed"]))
    deltas = []
    for seed in seeds:
        c = cand[cand["seed"] == seed]
        b = base[base["seed"] == seed]
        deltas.append(
            metrics.binary_macro_f1(c["y_true"].to_numpy(int), c["y_pred"].to_numpy(int))
            - metrics.binary_macro_f1(b["y_true"].to_numpy(int), b["y_pred"].to_numpy(int))
        )
    return float(np.mean(deltas))


def _fixture() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(3)
    periods = ["wf_p1", "wf_p2", "wf_p3"]
    tickers = ["AAA", "BBB"]
    prim, base = [], []
    for seed in (101, 202):
        for p in periods:
            for t in tickers:
                for _ in range(40):
                    y = int(rng.integers(0, 2))
                    # primary: ~80% correct; dummy: ~50% (so delta > 0)
                    yp = y if rng.random() < 0.8 else 1 - y
                    bp = int(rng.integers(0, 2))
                    common = {"period_id": p, "seed": seed, "ticker": t, "y_true": y}
                    prim.append({"table_row_id": "tcn_frozen_primary", **common, "y_pred": yp})
                    base.append({"baseline_id": "stratified_dummy_train_prior", **common, "y_pred": bp})
                    # a decoy family with garbage predictions -> must be ignored
                    prim.append({"table_row_id": "decoy_family", **common, "y_pred": 1 - yp})
    return pd.DataFrame(prim), pd.DataFrame(base)


def test_row_pooled_loo_schema_counts_and_reference() -> None:
    primary, baseline = _fixture()
    out = synthesis.build_row_pooled_loo(
        primary, baseline, primary_model="tcn_frozen_primary",
        expected_period_count=3, expected_ticker_count=2,
    )
    assert list(out.columns) == synthesis.LOO_ROBUSTNESS_COLUMNS
    assert set(out["estimand"]) == {"row_pooled_over_periods", "row_pooled_over_tickers"}
    assert (out["weight_unit"] == "row").all()
    # 3 period drops + 1 summary + 2 ticker drops + 1 summary
    assert len(out) == 3 + 1 + 2 + 1

    cand = primary[primary["table_row_id"] == "tcn_frozen_primary"]
    # no-drop baseline == the row-union delta (decoy family ignored)
    expected_baseline = _reference_row_pooled_delta(cand, baseline)
    assert out["baseline_delta"].iloc[0] == pytest.approx(expected_baseline)
    assert out["baseline_delta"].nunique() == 1  # one binding estimand for all rows

    # every drop row matches the independent reference + arithmetic + sign flag
    for _, r in out[out["left_out"] != "<all:summary>"].iterrows():
        axis = "period_id" if r["estimand"].endswith("periods") else "ticker"
        ref = _reference_row_pooled_delta(
            cand[cand[axis].astype(str) != r["left_out"]],
            baseline[baseline[axis].astype(str) != r["left_out"]],
        )
        assert r["delta_after_drop"] == pytest.approx(ref)
        assert r["delta_shift"] == pytest.approx(r["delta_after_drop"] - r["baseline_delta"])
        assert bool(r["sign_after_drop"]) == bool(r["delta_after_drop"] > 0)
        assert int(r["n_units_remaining"]) < len(cand)  # rows, not units


def test_row_pooled_loo_summary_flags_sign_survival() -> None:
    primary, baseline = _fixture()
    out = synthesis.build_row_pooled_loo(
        primary, baseline, primary_model="tcn_frozen_primary",
    )
    for estimand in ("row_pooled_over_periods", "row_pooled_over_tickers"):
        drops = out[(out["estimand"] == estimand) & (out["left_out"] != "<all:summary>")]
        summary = out[(out["estimand"] == estimand) & (out["left_out"] == "<all:summary>")].iloc[0]
        # fixture is primary-better-everywhere -> no drop crosses zero
        assert drops["sign_after_drop"].all()
        assert bool(summary["sign_after_drop"]) is True
        assert "loo_sign_flip=False" in str(summary["note"])
        assert "pooled_delta_row_pooled" in str(summary["note"])


def test_row_pooled_loo_fails_closed_on_missing_columns_and_wrong_count() -> None:
    primary, baseline = _fixture()
    with pytest.raises(ValueError, match="missing columns"):
        synthesis.build_row_pooled_loo(
            primary.drop(columns=["y_pred"]), baseline, primary_model="tcn_frozen_primary",
        )
    with pytest.raises(ValueError, match="expected 9 period_id"):
        synthesis.build_row_pooled_loo(
            primary, baseline, primary_model="tcn_frozen_primary", expected_period_count=9,
        )
    with pytest.raises(ValueError, match="no rows for primary model"):
        synthesis.build_row_pooled_loo(
            primary, baseline, primary_model="does_not_exist",
        )
