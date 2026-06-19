"""Unit tests for the two Stage 05 guarded measure-only addenda
(synthesis.build_guarded_activity_tercile and
synthesis.build_row_pooled_multiplicity_discount).

Both recompute from the raw frozen guarded prediction dumps (Drive-only at run
time); these tests validate the schema, the cross-era activity-tercile binning +
delta arithmetic, and the row-pooled (binding-estimand) multiplicity matrix
against an inline reference, plus fail-closed behavior. No dump, no fit, no scoring.
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


FAMILIES = [
    "tcn_frozen_primary", "lightgbm_family_best",
    "standard_dlinear_family_best", "ms_dlinear_tcn_family_best",
]
# (ticker, trading_day, period_id) -> base sample count; per-ticker day sizes
# increase so the activity proxy populates low/mid/high terciles.
_DAY_PLAN = {
    ("AAA", "2017-01-25", "wf_p1"): 8,
    ("AAA", "2018-02-01", "wf_p2"): 16,
    ("AAA", "2019-03-01", "wf_p3"): 24,
    ("BBB", "2017-01-26", "wf_p1"): 10,
    ("BBB", "2018-02-02", "wf_p2"): 20,
    ("BBB", "2019-03-02", "wf_p3"): 30,
}


def _fixture() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(11)
    prim, base = [], []
    for (tk, td, pid), n in _DAY_PLAN.items():
        for seed in (101, 202):
            for k in range(n):
                y = int(rng.integers(0, 2))
                common = {
                    "period_id": pid, "seed": seed, "ticker": tk,
                    "trading_day": td, "sample_id": f"{tk}-{td}-{seed}-{k}", "y_true": y,
                }
                base.append({
                    "baseline_id": "stratified_dummy_train_prior", **common,
                    "y_pred": int(rng.integers(0, 2)), "p_up": float(rng.random()),
                })
                for fi, fam in enumerate(FAMILIES):
                    acc = 0.80 - 0.07 * fi  # primary best, others progressively worse
                    yp = y if rng.random() < acc else 1 - y
                    prim.append({
                        "table_row_id": fam, **common,
                        "y_pred": yp, "p_up": float(rng.random()),
                    })
    return pd.DataFrame(prim), pd.DataFrame(base)


def _ref_row_pooled(cand: pd.DataFrame, base: pd.DataFrame) -> float:
    seeds = sorted(set(cand["seed"]) & set(base["seed"]))
    deltas = []
    for s in seeds:
        c = cand[cand["seed"] == s]
        b = base[base["seed"] == s]
        deltas.append(
            metrics.binary_macro_f1(c["y_true"].to_numpy(int), c["y_pred"].to_numpy(int))
            - metrics.binary_macro_f1(b["y_true"].to_numpy(int), b["y_pred"].to_numpy(int))
        )
    return float(np.mean(deltas))


# --- build_guarded_activity_tercile ---------------------------------------

def test_guarded_activity_tercile_schema_and_arithmetic() -> None:
    primary, baseline = _fixture()
    out = synthesis.build_guarded_activity_tercile(
        primary, baseline, primary_model="tcn_frozen_primary", expected_ticker_count=2,
    )
    assert list(out.columns) == synthesis.GUARDED_ACTIVITY_TERCILE_COLUMNS
    assert (out["evidence_domain"] == "guarded_walkforward").all()
    assert set(out["activity_tercile"]) == {"all", "low", "mid", "high"}
    assert set(out["seed"]) == {"101", "202", "seed_mean"}
    # internal consistency on every finite row (per-seed AND seed-mean: mean is linear)
    finite = out[out["macro_f1"].notna()]
    for _, r in finite.iterrows():
        assert r["delta_vs_dummy"] == pytest.approx(r["macro_f1"] - r["dummy_macro_f1"])
        assert bool(r["below_random_prior"]) == bool(r["macro_f1"] < 0.5)
    # 'all' seed-101 macro_f1 reproduces the full candidate macro_f1
    cand = primary[primary["table_row_id"] == "tcn_frozen_primary"]
    c101 = cand[cand["seed"] == 101]
    ref = metrics.binary_macro_f1(c101["y_true"].to_numpy(int), c101["y_pred"].to_numpy(int))
    got = out[(out["activity_tercile"] == "all") & (out["seed"] == "101")]["macro_f1"].iloc[0]
    assert got == pytest.approx(ref)


def test_guarded_activity_tercile_fails_closed() -> None:
    primary, baseline = _fixture()
    with pytest.raises(ValueError, match="missing columns"):
        synthesis.build_guarded_activity_tercile(
            primary.drop(columns=["trading_day"]), baseline, primary_model="tcn_frozen_primary",
        )
    with pytest.raises(ValueError, match="no rows for primary model"):
        synthesis.build_guarded_activity_tercile(primary, baseline, primary_model="nope")
    with pytest.raises(ValueError, match="expected 5 tickers"):
        synthesis.build_guarded_activity_tercile(
            primary, baseline, primary_model="tcn_frozen_primary", expected_ticker_count=5,
        )


# --- build_row_pooled_multiplicity_discount -------------------------------

def test_row_pooled_multiplicity_schema_and_binding_central() -> None:
    primary, baseline = _fixture()
    out = synthesis.build_row_pooled_multiplicity_discount(
        primary, baseline, expected_family_count=4, expected_period_count=3,
    )
    assert list(out.columns) == synthesis.MULTIPLICITY_DISCOUNT_COLUMNS
    fam_rows = out[out["row_kind"] == "family"]
    assert len(fam_rows) == 4
    summary = out[out["row_kind"] == "summary"].iloc[0]
    # each family's central mean_delta is the row-pooled-over-all-rows BINDING estimand
    for _, r in fam_rows.iterrows():
        cand = primary[primary["table_row_id"] == r["family"]]
        assert r["mean_delta"] == pytest.approx(_ref_row_pooled(cand, baseline))
    # PBO is a share; aggregates line up with the per-family rows
    assert 0.0 <= float(summary["pbo"]) <= 1.0
    assert float(summary["min_family_lcb"]) == pytest.approx(float(fam_rows["period_delta_lcb"].min()))
    assert float(summary["max_family_mean"]) == pytest.approx(float(fam_rows["mean_delta"].max()))
    assert summary["seed_aggregation"] == "row_pooled_within_period_then_block"


def test_row_pooled_multiplicity_fails_closed() -> None:
    primary, baseline = _fixture()
    with pytest.raises(ValueError, match="expected 9 families"):
        synthesis.build_row_pooled_multiplicity_discount(
            primary, baseline, expected_family_count=9,
        )
    # drop one (family, period) cell -> incomplete roster raises (fail-closed)
    dropped = primary[~(
        (primary["table_row_id"] == "tcn_frozen_primary") & (primary["period_id"] == "wf_p3")
    )]
    with pytest.raises(ValueError, match="no candidate/baseline rows"):
        synthesis.build_row_pooled_multiplicity_discount(
            dropped, baseline, expected_family_count=4, expected_period_count=3,
        )
