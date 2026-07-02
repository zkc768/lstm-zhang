"""Unit tests for the half-spread settlement-control measurement module
(``lst_models.microstructure``): the pinned Roll (1984) estimator formula and
windowing, the undefined/insufficient cell handling, the frozen partition
edges, the fail-closed dump joins and baseline alignment, the readout schema
and delta arithmetic against inline references, and the mechanical verdict
rules of the pre-registration (section 8). Synthetic frames only — no dump,
no raw data, no fit, no scoring.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models import metrics, microstructure  # noqa: E402

BAND = 3.0 / 10000.0


def _bounce_bars(
    *, n_days: int, bars_per_day: int, halfspread: float, seed: int, ticker: str = "AAA"
) -> pd.DataFrame:
    """Roll-model bars: close = mid * exp(c * q) with q iid +/-1; flat mid."""
    rng = np.random.default_rng(seed)
    rows = []
    days = pd.bdate_range("2015-01-05", periods=n_days)
    for day in days:
        q = rng.choice([-1.0, 1.0], size=bars_per_day)
        for i in range(bars_per_day):
            ts = day + pd.Timedelta(minutes=9 * 60 + 30 + 5 * i)
            close = 100.0 * float(np.exp(halfspread * q[i]))
            rows.append({
                "ticker": ticker, "timestamp": ts,
                "trading_day": day.strftime("%Y-%m-%d"),
                "open": close, "high": close * 1.0002, "low": close * 0.9998,
                "close": close, "volume": 1000.0,
            })
    return pd.DataFrame(rows)


def _naive_roll_for_day(
    bars: pd.DataFrame, ticker: str, day: str, window_days: int
) -> tuple[int, float]:
    """Inline reference for the pinned formula: pooled within-day lag-1 pairs
    of the trailing window ending the day before ``day``."""
    sub = bars.loc[bars["ticker"] == ticker].sort_values("timestamp")
    days = sorted(sub["trading_day"].unique())
    position = days.index(day)
    window = days[max(0, position - window_days):position]
    a_all, b_all = [], []
    for d in window:
        closes = sub.loc[sub["trading_day"] == d, "close"].to_numpy(dtype=float)
        r = np.diff(np.log(closes))
        a_all.extend(r[1:].tolist())
        b_all.extend(r[:-1].tolist())
    n = len(a_all)
    if n < 2:
        return n, float("nan")
    a = np.asarray(a_all)
    b = np.asarray(b_all)
    cov = (float(np.sum(a * b)) - float(np.sum(a)) * float(np.sum(b)) / n) / (n - 1.0)
    return n, cov


def test_roll_matches_inline_reference_and_excludes_own_day() -> None:
    bars = _bounce_bars(n_days=8, bars_per_day=30, halfspread=4e-4, seed=3)
    out = microstructure.roll_halfspread_by_day(bars, window_days=5, min_pairs=50)
    day = sorted(out["trading_day"].unique())[6]
    row = out.loc[out["trading_day"] == day].iloc[0]
    n_ref, cov_ref = _naive_roll_for_day(bars, "AAA", day, 5)
    assert int(row["n_pairs"]) == n_ref
    assert row["autocov_lag1"] == pytest.approx(cov_ref, rel=1e-12)

    # perturb ONE bar inside the day (changes that day's within-day returns):
    # the day's own estimate must not move (trailing window excludes day d)
    perturbed = bars.copy()
    bar_index = perturbed.index[perturbed["trading_day"] == day][10]
    perturbed.loc[bar_index, "close"] = perturbed.loc[bar_index, "close"] * 1.01
    out2 = microstructure.roll_halfspread_by_day(perturbed, window_days=5, min_pairs=50)
    row2 = out2.loc[out2["trading_day"] == day].iloc[0]
    assert row2["autocov_lag1"] == pytest.approx(row["autocov_lag1"], rel=1e-12)
    # ...but the NEXT day's estimate must change
    next_day = sorted(out["trading_day"].unique())[7]
    before = out.loc[out["trading_day"] == next_day, "autocov_lag1"].iloc[0]
    after = out2.loc[out2["trading_day"] == next_day, "autocov_lag1"].iloc[0]
    assert before != pytest.approx(after, rel=1e-9)


def test_roll_recovers_planted_halfspread() -> None:
    planted = 6e-4
    bars = _bounce_bars(n_days=40, bars_per_day=78, halfspread=planted, seed=11)
    out = microstructure.roll_halfspread_by_day(bars, window_days=21, min_pairs=400)
    tail = out.tail(10)
    assert (tail["status"] == "ok").all()
    assert tail["halfspread"].mean() == pytest.approx(planted, rel=0.15)


def test_roll_undefined_and_insufficient_cells() -> None:
    # strongly trending closes -> positive lag-1 autocovariance -> undefined
    rows = []
    days = pd.bdate_range("2015-01-05", periods=6)
    price = 100.0
    for day in days:
        for i in range(30):
            price *= 1.001 if (i // 10) % 2 == 0 else 0.999  # persistent runs
            ts = day + pd.Timedelta(minutes=9 * 60 + 30 + 5 * i)
            rows.append({
                "ticker": "AAA", "timestamp": ts, "trading_day": day.strftime("%Y-%m-%d"),
                "open": price, "high": price, "low": price, "close": price, "volume": 1.0,
            })
    bars = pd.DataFrame(rows)
    out = microstructure.roll_halfspread_by_day(bars, window_days=5, min_pairs=50)
    first_day = sorted(out["trading_day"].unique())[0]
    assert out.loc[out["trading_day"] == first_day, "status"].iloc[0] == (
        microstructure.CELL_INSUFFICIENT
    )
    last_day = sorted(out["trading_day"].unique())[-1]
    assert out.loc[out["trading_day"] == last_day, "status"].iloc[0] == (
        microstructure.CELL_UNDEFINED
    )


def test_partition_edges_are_pinned() -> None:
    day_spread = pd.DataFrame({
        "ticker": "AAA", "trading_day": [f"2015-01-0{i}" for i in range(1, 8)],
        "n_pairs": 1000,
        "autocov_lag1": -1e-9,
        "halfspread": [BAND * r for r in (0.49, 0.5, 0.51, 1.0, 1.01, 2.0, 2.01)],
        "status": "ok",
    })
    out = microstructure.assign_spread_partition(day_spread, band_threshold=BAND)
    assert list(out["cell"]) == [
        microstructure.CELL_RATIO_LE_0P5, microstructure.CELL_RATIO_LE_0P5,
        microstructure.CELL_RATIO_0P5_TO_1, microstructure.CELL_RATIO_0P5_TO_1,
        microstructure.CELL_RATIO_1_TO_2, microstructure.CELL_RATIO_1_TO_2,
        microstructure.CELL_RATIO_GT_2,
    ]
    undefined = day_spread.assign(status=microstructure.CELL_UNDEFINED)
    out2 = microstructure.assign_spread_partition(undefined, band_threshold=BAND)
    assert set(out2["cell"]) == {microstructure.CELL_UNDEFINED}


def test_attach_day_column_fails_on_missing_day_and_preserves_order() -> None:
    dump = pd.DataFrame({
        "ticker": ["AAA", "AAA", "AAA"],
        "trading_day": ["2015-01-05", "2015-01-06", "2015-01-05"],
        "marker": [0, 1, 2],
    })
    days = pd.DataFrame({
        "ticker": ["AAA", "AAA"], "trading_day": ["2015-01-05", "2015-01-06"],
        "cell": ["ratio_le_0p5", "ratio_gt_2"],
    })
    out = microstructure.attach_day_column_to_dump(dump, days, column="cell", context="t")
    assert list(out["marker"]) == [0, 1, 2]
    assert list(out["cell"]) == ["ratio_le_0p5", "ratio_gt_2", "ratio_le_0p5"]
    with pytest.raises(ValueError, match="no .*match"):
        microstructure.attach_day_column_to_dump(
            dump.assign(trading_day=["2015-01-05", "2015-01-07", "2015-01-05"]),
            days, column="cell", context="t",
        )


def _dump_fixture(seed: int = 7) -> pd.DataFrame:
    """Two seeds x two cells x days; candidate accurate in the high cell only."""
    rng = np.random.default_rng(seed)
    rows = []
    plan = [
        ("2015-01-05", microstructure.CELL_RATIO_LE_0P5, "low", 0.50),
        ("2015-01-06", microstructure.CELL_RATIO_LE_0P5, "low", 0.50),
        ("2015-01-07", microstructure.CELL_RATIO_GT_2, "low", 0.90),
        ("2015-01-08", microstructure.CELL_RATIO_GT_2, "low", 0.90),
    ]
    for day, cell, tercile, accuracy in plan:
        for seed_value in (101, 202):
            for k in range(60):
                y = int(rng.integers(0, 2))
                y_pred = y if rng.random() < accuracy else 1 - y
                rows.append({
                    "ticker": "AAA", "trading_day": day, "seed": seed_value,
                    "sample_id": f"AAA|{day}|{seed_value}|{k}",
                    "y_true": y, "y_pred": y_pred,
                    "baseline_y_pred": int(rng.integers(0, 2)),
                    "cell": cell, "activity_tercile": tercile,
                })
    return pd.DataFrame(rows)


def test_readout_schema_and_delta_arithmetic() -> None:
    frame = _dump_fixture()
    out = microstructure.halfspread_partition_readout(
        frame, evidence_domain="official_validation", model_row="tcn_frozen_primary",
        row_scope="all_eligible", bootstrap=None,
    )
    assert list(out.columns) == microstructure.HALFSPREAD_READOUT_COLUMNS
    cells = set(out["cell"])
    for expected in ("all", microstructure.COARSE_CELL_LE_1, microstructure.COARSE_CELL_GT_1,
                     *microstructure.FINE_CELLS_ORDERED, *microstructure.UNDEFINED_CELLS):
        assert expected in cells
    sub = frame.loc[(frame["cell"] == microstructure.CELL_RATIO_GT_2) & (frame["seed"] == 101)]
    expected_delta = metrics.binary_macro_f1(
        sub["y_true"].to_numpy(int), sub["y_pred"].to_numpy(int)
    ) - metrics.binary_macro_f1(
        sub["y_true"].to_numpy(int), sub["baseline_y_pred"].to_numpy(int)
    )
    row = out.loc[(out["cell"] == microstructure.CELL_RATIO_GT_2) & (out["seed"] == "101")]
    assert row["delta_vs_dummy"].iloc[0] == pytest.approx(expected_delta, abs=1e-12)
    seed_rows = out.loc[
        (out["cell"] == microstructure.CELL_RATIO_GT_2) & (out["seed"] != "seed_mean")
    ]
    mean_row = out.loc[
        (out["cell"] == microstructure.CELL_RATIO_GT_2) & (out["seed"] == "seed_mean")
    ]
    assert mean_row["delta_vs_dummy"].iloc[0] == pytest.approx(
        seed_rows["delta_vs_dummy"].astype(float).mean(), abs=1e-12
    )
    # empty cells are still reported, flagged
    empty = out.loc[(out["cell"] == microstructure.CELL_INSUFFICIENT) & (out["seed"] == "101")]
    assert int(empty["n_rows"].iloc[0]) == 0 and bool(empty["thin_cell"].iloc[0])


def test_readout_bootstrap_smoke_and_domain_pooling_guard() -> None:
    frame = _dump_fixture()
    out = microstructure.halfspread_partition_readout(
        frame, evidence_domain="official_validation", model_row="tcn_frozen_primary",
        row_scope="all_eligible", bootstrap={"iterations": 10, "seed": 12345},
    )
    row = out.loc[(out["cell"] == "all") & (out["seed"] == "101")].iloc[0]
    assert np.isfinite(row["boot_delta_lcb"]) and np.isfinite(row["boot_delta_ucb"])
    mixed = frame.assign(evidence_domain=["official_validation", "guarded_walkforward"] * (len(frame) // 2))
    with pytest.raises(ValueError, match="never pooled"):
        microstructure.halfspread_partition_readout(
            mixed, evidence_domain="x", model_row="m", row_scope="all_eligible",
        )


def test_align_baseline_predictions_fail_closed() -> None:
    cand = pd.DataFrame({
        "period_id": ["p1", "p1"], "seed": [101, 101], "sample_id": ["a", "b"],
        "y_true": [1, 0], "y_pred": [1, 1],
    })
    base = cand.assign(y_pred=[0, 1])
    out = microstructure.align_baseline_predictions(
        cand, base, on=("period_id", "seed", "sample_id"), context="t"
    )
    assert list(out["baseline_y_pred"]) == [0, 1]
    with pytest.raises(ValueError, match="no baseline row"):
        microstructure.align_baseline_predictions(
            cand, base.iloc[:1], on=("period_id", "seed", "sample_id"), context="t"
        )
    with pytest.raises(ValueError, match="y_true differs"):
        microstructure.align_baseline_predictions(
            cand, base.assign(y_true=[0, 1]), on=("period_id", "seed", "sample_id"), context="t"
        )


def _verdict_frame(
    low_delta: float, low_lcb: float, low_ucb: float,
    high_delta: float, high_lcb: float,
    *, n_rows: int = 6000, all_delta: float = 0.05,
) -> pd.DataFrame:
    rows = []
    for seed in ("101", "202"):
        rows.append({"cell": microstructure.CELL_RATIO_LE_0P5, "seed": seed, "n_rows": n_rows,
                     "delta_vs_dummy": low_delta, "boot_delta_lcb": low_lcb,
                     "boot_delta_ucb": low_ucb})
        rows.append({"cell": microstructure.COARSE_CELL_GT_1, "seed": seed, "n_rows": n_rows,
                     "delta_vs_dummy": high_delta, "boot_delta_lcb": high_lcb,
                     "boot_delta_ucb": high_delta + 0.02})
    deltas = {
        microstructure.CELL_RATIO_LE_0P5: low_delta,
        microstructure.CELL_RATIO_0P5_TO_1: (low_delta + high_delta) / 2,
        microstructure.CELL_RATIO_1_TO_2: high_delta,
        microstructure.CELL_RATIO_GT_2: high_delta + 0.01,
    }
    for cell, delta in deltas.items():
        rows.append({"cell": cell, "seed": "seed_mean", "n_rows": 2 * n_rows,
                     "delta_vs_dummy": delta, "boot_delta_lcb": float("nan"),
                     "boot_delta_ucb": float("nan")})
    rows.append({"cell": "all", "seed": "seed_mean", "n_rows": 8 * n_rows,
                 "delta_vs_dummy": all_delta, "boot_delta_lcb": float("nan"),
                 "boot_delta_ucb": float("nan")})
    return pd.DataFrame(rows)


def test_verdict_outcome_a_bounce_domination() -> None:
    frame = _verdict_frame(0.001, -0.01, 0.012, 0.05, 0.02)
    verdict = microstructure.verdict_from_readout(frame, verdict_min_rows=5000)
    assert verdict["verdict"] == "consistent_with_bounce_domination"


def test_verdict_outcome_b_not_bounce_alone() -> None:
    frame = _verdict_frame(0.04, 0.01, 0.07, 0.05, 0.02, all_delta=0.05)
    verdict = microstructure.verdict_from_readout(frame, verdict_min_rows=5000)
    assert verdict["verdict"] == "not_explainable_by_bounce_alone"


def test_verdict_inconclusive_on_occupancy_and_sign_disagreement() -> None:
    thin = _verdict_frame(0.001, -0.01, 0.012, 0.05, 0.02, n_rows=100)
    verdict = microstructure.verdict_from_readout(thin, verdict_min_rows=5000)
    assert verdict["verdict"] == "inconclusive"
    assert verdict["reason"] == "anchor_occupancy_below_verdict_min_rows"

    frame = _verdict_frame(0.02, 0.001, 0.05, 0.05, 0.02)
    frame.loc[
        (frame["cell"] == microstructure.CELL_RATIO_LE_0P5) & (frame["seed"] == "202"),
        "delta_vs_dummy",
    ] = -0.02
    verdict = microstructure.verdict_from_readout(frame, verdict_min_rows=5000)
    assert verdict["verdict"] == "inconclusive"
    assert verdict["reason"] == "per_seed_sign_disagreement_on_low_anchor"


def test_corwin_schultz_nonnegative_and_status() -> None:
    bars = _bounce_bars(n_days=30, bars_per_day=78, halfspread=5e-4, seed=5)
    out = microstructure.corwin_schultz_halfspread_by_day(bars, window_days=21, min_spans=200)
    tail = out.tail(5)
    assert (tail["cs_status"] == "ok").all()
    assert (tail["cs_halfspread"] >= 0.0).all()
    assert out.iloc[0]["cs_status"] == microstructure.CELL_INSUFFICIENT


def test_within_day_returns_exclude_overnight() -> None:
    bars = _bounce_bars(n_days=2, bars_per_day=3, halfspread=1e-4, seed=1)
    returns = microstructure.within_day_log_returns(bars)
    # 3 bars per day -> 2 within-day returns per day; no cross-day return
    assert len(returns) == 4
    assert set(returns.groupby("trading_day").size()) == {2}
