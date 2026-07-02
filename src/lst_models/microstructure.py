"""Microstructure spread proxies and the half-spread settlement-control readout.

Pure measurement logic for the pre-registered half-spread settlement control
(``docs/protocols/v2_halfspread_control_preregistration_20260701.md``): a
Roll (1984) effective half-spread proxy from canonical 5-minute bars, the
frozen spread-to-band partition, and the measure-only re-aggregation of
frozen per-row prediction dumps by that partition. Every function takes
already-loaded frames and returns frames or plain values — no file paths, no
model fitting, no stage gates, no artifact writing (those belong to
``lst_models.stages.halfspread_control``). Nothing here re-scores a model,
fits anything, or marks an operating point.

Estimator conventions are pinned by the pre-registration section 4 and by
``tests/contracts/test_microstructure_halfspread.py``; changing them after
the first measurement run requires a dated deviation-log entry, not an edit.
"""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd

from lst_models import metrics

ROLL_WINDOW_DAYS = 21
ROLL_MIN_PAIRS = 400
CS_MIN_SPANS = 200
REPORT_MIN_ROWS = 200
RATIO_EDGES = (0.5, 1.0, 2.0)

CELL_RATIO_LE_0P5 = "ratio_le_0p5"
CELL_RATIO_0P5_TO_1 = "ratio_0p5_to_1"
CELL_RATIO_1_TO_2 = "ratio_1_to_2"
CELL_RATIO_GT_2 = "ratio_gt_2"
CELL_UNDEFINED = "roll_undefined_nonneg_autocov"
CELL_INSUFFICIENT = "insufficient_history"
FINE_CELLS_ORDERED = (
    CELL_RATIO_LE_0P5, CELL_RATIO_0P5_TO_1, CELL_RATIO_1_TO_2, CELL_RATIO_GT_2,
)
UNDEFINED_CELLS = (CELL_UNDEFINED, CELL_INSUFFICIENT)
COARSE_CELL_LE_1 = "ratio_le_1"
COARSE_CELL_GT_1 = "ratio_gt_1"
COARSE_CELL_MEMBERS = {
    COARSE_CELL_LE_1: (CELL_RATIO_LE_0P5, CELL_RATIO_0P5_TO_1),
    COARSE_CELL_GT_1: (CELL_RATIO_1_TO_2, CELL_RATIO_GT_2),
}

DAY_SPREAD_COLUMNS = [
    "ticker", "trading_day", "n_pairs", "autocov_lag1", "halfspread",
    "spread_band_ratio", "cell", "status",
]
HALFSPREAD_READOUT_COLUMNS = [
    "evidence_domain", "model_row", "row_scope", "cell", "seed", "n_rows",
    "n_days", "up_rate", "macro_f1", "dummy_macro_f1", "delta_vs_dummy",
    "boot_delta_lcb", "boot_delta_ucb", "below_random_prior", "thin_cell",
    "note",
]
OCCUPANCY_COLUMNS = [
    "evidence_domain", "cell", "activity_tercile", "n_rows", "n_days",
]
AUTOCOV_COLUMNS = [
    "evidence_domain", "activity_tercile", "n_pairs", "autocov_lag1",
    "autocorr_lag1",
]

_READOUT_FRAME_REQUIRED = {
    "seed", "y_true", "y_pred", "baseline_y_pred", "ticker", "trading_day",
}


def within_day_log_returns(bars: pd.DataFrame) -> pd.DataFrame:
    """Per-(ticker, trading_day) consecutive 5-minute log close returns.

    The first bar of each day has no return (overnight gaps never enter),
    matching the day-grouped ``log_return`` convention of ``features.py``.
    """
    required = {"ticker", "trading_day", "timestamp", "close"}
    missing = sorted(required - set(bars.columns))
    if missing:
        raise ValueError(f"within_day_log_returns: bars missing columns {missing}")
    frame = bars.sort_values(["ticker", "timestamp"]).copy()
    frame["trading_day"] = frame["trading_day"].astype(str)
    close = frame["close"].astype(float)
    previous_close = frame.groupby(["ticker", "trading_day"], sort=False)["close"].shift(1)
    frame["log_return"] = np.log(close / previous_close.astype(float))
    out = frame.loc[
        frame["log_return"].notna(), ["ticker", "trading_day", "timestamp", "log_return"]
    ]
    return out.reset_index(drop=True)


def _day_pair_stats(returns: pd.DataFrame) -> pd.DataFrame:
    """Per-(ticker, trading_day) sufficient statistics of within-day lag-1
    pairs (a, b) = (r_i, r_{i-1}); pairs never span days."""
    frame = returns.sort_values(["ticker", "trading_day", "timestamp"]).copy()
    group = frame.groupby(["ticker", "trading_day"], sort=False)
    a = frame["log_return"].astype(float)
    b = group["log_return"].shift(1)
    pair = pd.DataFrame({
        "ticker": frame["ticker"], "trading_day": frame["trading_day"],
        "a": a, "b": b,
    }).dropna(subset=["b"])
    pair["ab"] = pair["a"] * pair["b"]
    pair["aa"] = pair["a"] * pair["a"]
    pair["bb"] = pair["b"] * pair["b"]
    pair["n"] = 1
    stats = (
        pair.groupby(["ticker", "trading_day"], sort=True)[["n", "a", "b", "ab", "aa", "bb"]]
        .sum()
        .rename(columns={"a": "sa", "b": "sb", "ab": "sab", "aa": "saa", "bb": "sbb"})
        .reset_index()
    )
    return stats


def _pooled_autocov(n: float, sa: float, sb: float, sab: float) -> float:
    """Pinned sample covariance over pooled pairs:
    (sum(ab) - sum(a)*sum(b)/n) / (n - 1)."""
    if n < 2:
        return float("nan")
    return float((sab - sa * sb / n) / (n - 1.0))


def roll_halfspread_by_day(
    bars: pd.DataFrame,
    *,
    window_days: int = ROLL_WINDOW_DAYS,
    min_pairs: int = ROLL_MIN_PAIRS,
) -> pd.DataFrame:
    """Roll (1984) relative half-spread proxy per (ticker, trading_day).

    For day d the estimation window pools the within-day lag-1 pairs of the
    trailing ``window_days`` OBSERVED trading days of that ticker ending at
    d-1 (day d itself is excluded, so the conditioning variable never
    contains the day's own returns). ``halfspread = sqrt(-autocov)`` when the
    pooled lag-1 autocovariance is negative; a non-negative autocovariance is
    the named undefined cell (never imputed to zero); fewer than ``min_pairs``
    pooled pairs is the named insufficient-history cell.
    """
    if int(window_days) < 1:
        raise ValueError("roll_halfspread_by_day: window_days must be >= 1")
    returns = within_day_log_returns(bars)
    stats = _day_pair_stats(returns)
    rows: list[dict[str, Any]] = []
    for ticker, ticker_stats in stats.groupby("ticker", sort=True):
        day_frame = ticker_stats.sort_values("trading_day").reset_index(drop=True)
        pooled = (
            day_frame[["n", "sa", "sb", "sab"]]
            .rolling(int(window_days), min_periods=1)
            .sum()
            .shift(1)
        )
        for i in range(len(day_frame)):
            n = float(pooled["n"].iloc[i]) if pd.notna(pooled["n"].iloc[i]) else 0.0
            autocov = float("nan")
            halfspread = float("nan")
            if n < float(min_pairs):
                status = CELL_INSUFFICIENT
            else:
                autocov = _pooled_autocov(
                    n, float(pooled["sa"].iloc[i]), float(pooled["sb"].iloc[i]),
                    float(pooled["sab"].iloc[i]),
                )
                if not np.isfinite(autocov) or autocov >= 0.0:
                    status = CELL_UNDEFINED
                else:
                    status = "ok"
                    halfspread = float(np.sqrt(-autocov))
            rows.append({
                "ticker": str(ticker),
                "trading_day": str(day_frame["trading_day"].iloc[i]),
                "n_pairs": int(n),
                "autocov_lag1": autocov,
                "halfspread": halfspread,
                "status": status,
            })
    if not rows:
        raise ValueError("roll_halfspread_by_day: no (ticker, trading_day) cells produced")
    return pd.DataFrame(rows)


def corwin_schultz_halfspread_by_day(
    bars: pd.DataFrame,
    *,
    window_days: int = ROLL_WINDOW_DAYS,
    min_spans: int = CS_MIN_SPANS,
) -> pd.DataFrame:
    """Corwin-Schultz (2012) high-low relative half-spread per day (robustness
    proxy only; no verdict power). Overlapping two-bar spans within each day,
    pooled over the same trailing window (day d excluded); negative spreads
    are clipped to 0 per the CS convention and the clipped share is implied by
    ``cs_alpha`` being reported per day."""
    required = {"ticker", "trading_day", "timestamp", "high", "low"}
    missing = sorted(required - set(bars.columns))
    if missing:
        raise ValueError(f"corwin_schultz_halfspread_by_day: bars missing columns {missing}")
    frame = bars.sort_values(["ticker", "timestamp"]).copy()
    frame["trading_day"] = frame["trading_day"].astype(str)
    high = frame["high"].astype(float)
    low = frame["low"].astype(float).replace(0.0, np.nan)
    frame["_hl2"] = np.square(np.log(high / low))
    group = frame.groupby(["ticker", "trading_day"], sort=False)
    prev_high = group["high"].shift(1).astype(float)
    prev_low = group["low"].shift(1).astype(float)
    span_high = np.maximum(high, prev_high)
    span_low = np.minimum(low, prev_low).replace(0.0, np.nan)
    span = pd.DataFrame({
        "ticker": frame["ticker"], "trading_day": frame["trading_day"],
        "beta_term": frame["_hl2"] + group["_hl2"].shift(1),
        "gamma_term": np.square(np.log(span_high / span_low)),
    }).dropna(subset=["beta_term", "gamma_term"])
    span["n"] = 1
    stats = (
        span.groupby(["ticker", "trading_day"], sort=True)[["n", "beta_term", "gamma_term"]]
        .sum()
        .reset_index()
    )
    k = 3.0 - 2.0 * np.sqrt(2.0)
    rows: list[dict[str, Any]] = []
    for ticker, ticker_stats in stats.groupby("ticker", sort=True):
        day_frame = ticker_stats.sort_values("trading_day").reset_index(drop=True)
        pooled = (
            day_frame[["n", "beta_term", "gamma_term"]]
            .rolling(int(window_days), min_periods=1)
            .sum()
            .shift(1)
        )
        for i in range(len(day_frame)):
            n = float(pooled["n"].iloc[i]) if pd.notna(pooled["n"].iloc[i]) else 0.0
            cs_halfspread = float("nan")
            alpha = float("nan")
            if n < float(min_spans):
                status = CELL_INSUFFICIENT
            else:
                beta = float(pooled["beta_term"].iloc[i]) / n
                gamma = float(pooled["gamma_term"].iloc[i]) / n
                alpha = (np.sqrt(2.0 * beta) - np.sqrt(beta)) / k - np.sqrt(gamma / k)
                spread = 2.0 * (np.exp(alpha) - 1.0) / (1.0 + np.exp(alpha))
                cs_halfspread = float(max(spread, 0.0) / 2.0)
                status = "ok"
            rows.append({
                "ticker": str(ticker),
                "trading_day": str(day_frame["trading_day"].iloc[i]),
                "cs_n_spans": int(n),
                "cs_alpha": float(alpha) if np.isfinite(alpha) else float("nan"),
                "cs_halfspread": cs_halfspread,
                "cs_status": status,
            })
    return pd.DataFrame(rows)


def assign_spread_partition(
    day_spread: pd.DataFrame,
    *,
    band_threshold: float,
    ratio_edges: tuple[float, float, float] = RATIO_EDGES,
    halfspread_column: str = "halfspread",
    status_column: str = "status",
) -> pd.DataFrame:
    """Attach ``spread_band_ratio`` and the frozen partition ``cell`` to the
    per-day proxy frame. Undefined and insufficient cells pass through as
    their own named cells (pre-registration section 5)."""
    if float(band_threshold) <= 0.0:
        raise ValueError("assign_spread_partition: band_threshold must be > 0")
    lo, mid, hi = (float(edge) for edge in ratio_edges)
    if not (0.0 < lo < mid < hi):
        raise ValueError(f"assign_spread_partition: bad ratio_edges {ratio_edges}")
    frame = day_spread.copy()
    ratio = frame[halfspread_column].astype(float) / float(band_threshold)
    frame["spread_band_ratio"] = ratio
    cells = pd.Series(CELL_INSUFFICIENT, index=frame.index, dtype=object)
    status = frame[status_column].astype(str)
    cells[status == CELL_UNDEFINED] = CELL_UNDEFINED
    defined = status == "ok"
    cells[defined & (ratio <= lo)] = CELL_RATIO_LE_0P5
    cells[defined & (ratio > lo) & (ratio <= mid)] = CELL_RATIO_0P5_TO_1
    cells[defined & (ratio > mid) & (ratio <= hi)] = CELL_RATIO_1_TO_2
    cells[defined & (ratio > hi)] = CELL_RATIO_GT_2
    frame["cell"] = cells
    return frame


def attach_day_column_to_dump(
    dump: pd.DataFrame,
    day_frame: pd.DataFrame,
    *,
    column: str,
    context: str,
) -> pd.DataFrame:
    """Left-join one per-(ticker, trading_day) column onto dump rows,
    preserving dump row order, failing loudly on any unmatched day."""
    for name, frame in (("dump", dump), ("day_frame", day_frame)):
        missing = sorted({"ticker", "trading_day"} - set(frame.columns))
        if missing:
            raise ValueError(f"{context}: {name} missing columns {missing}")
    if column not in day_frame.columns:
        raise ValueError(f"{context}: day_frame missing column {column!r}")
    key = ["ticker", "trading_day"]
    day_map = day_frame[key + [column]].copy()
    day_map["ticker"] = day_map["ticker"].astype(str)
    day_map["trading_day"] = day_map["trading_day"].astype(str)
    if day_map.duplicated(key).any():
        raise ValueError(f"{context}: duplicate (ticker, trading_day) rows in day_frame")
    out = dump.copy()
    out["ticker"] = out["ticker"].astype(str)
    out["trading_day"] = out["trading_day"].astype(str)
    merged = out.merge(day_map, on=key, how="left")
    if len(merged) != len(out):
        raise ValueError(f"{context}: join changed the dump row count")
    if merged[column].isna().any():
        missing_days = (
            merged.loc[merged[column].isna(), key].drop_duplicates().head(10)
        )
        raise ValueError(
            f"{context}: {int(merged[column].isna().sum())} dump rows have no "
            f"(ticker, trading_day) match for {column!r}; first missing days:\n"
            f"{missing_days.to_string(index=False)}"
        )
    return merged


def align_baseline_predictions(
    cand: pd.DataFrame,
    base: pd.DataFrame,
    *,
    on: tuple[str, ...],
    context: str,
) -> pd.DataFrame:
    """Merge the frozen baseline per-row prediction onto the candidate rows as
    ``baseline_y_pred`` (row-aligned), asserting a complete 1:1 key match and
    identical ``y_true`` on every matched row (fail-closed)."""
    keys = list(on)
    for name, frame, need in (
        ("candidate", cand, set(keys) | {"y_true", "y_pred"}),
        ("baseline", base, set(keys) | {"y_true", "y_pred"}),
    ):
        missing = sorted(need - set(frame.columns))
        if missing:
            raise ValueError(f"{context}: {name} frame missing columns {missing}")
    base_view = base[keys + ["y_true", "y_pred"]].rename(
        columns={"y_true": "_baseline_y_true", "y_pred": "baseline_y_pred"}
    )
    if base_view.duplicated(keys).any():
        raise ValueError(f"{context}: baseline rows are not unique on {keys}")
    merged = cand.merge(base_view, on=keys, how="left", validate="many_to_one")
    if merged["baseline_y_pred"].isna().any():
        n_missing = int(merged["baseline_y_pred"].isna().sum())
        raise ValueError(
            f"{context}: {n_missing} candidate rows have no baseline row on {keys}; "
            "candidate and baseline must score identical rows"
        )
    if not np.array_equal(
        merged["y_true"].to_numpy(dtype=int),
        merged["_baseline_y_true"].to_numpy(dtype=int),
    ):
        raise ValueError(f"{context}: y_true differs between candidate and baseline rows")
    return merged.drop(columns=["_baseline_y_true"])


def _require_single_domain(frame: pd.DataFrame, context: str) -> None:
    if "evidence_domain" in frame.columns:
        domains = sorted(set(frame["evidence_domain"].astype(str)))
        if len(domains) > 1:
            raise ValueError(
                f"{context}: frame mixes evidence domains {domains}; the two domains "
                "are never pooled (pre-registration section 7)"
            )


def _readout_cell_row(
    rows: pd.DataFrame,
    *,
    evidence_domain: str,
    model_row: str,
    row_scope: str,
    cell: str,
    seed: str,
    random_prior: float,
    report_min_rows: int,
    bootstrap: Mapping[str, Any] | None,
) -> dict[str, Any]:
    nan = float("nan")
    n_rows = int(len(rows))
    out: dict[str, Any] = {
        "evidence_domain": evidence_domain, "model_row": model_row,
        "row_scope": row_scope, "cell": cell, "seed": seed, "n_rows": n_rows,
        "n_days": int(rows[["ticker", "trading_day"]].drop_duplicates().shape[0]) if n_rows else 0,
        "up_rate": nan, "macro_f1": nan, "dummy_macro_f1": nan,
        "delta_vs_dummy": nan, "boot_delta_lcb": nan, "boot_delta_ucb": nan,
        "below_random_prior": False, "thin_cell": n_rows < int(report_min_rows),
        "note": "",
    }
    if n_rows == 0:
        out["note"] = "empty_cell"
        return out
    y_true = rows["y_true"].to_numpy(dtype=int)
    y_pred = rows["y_pred"].to_numpy(dtype=int)
    baseline_pred = rows["baseline_y_pred"].to_numpy(dtype=int)
    macro = metrics.binary_macro_f1(y_true, y_pred)
    dummy = metrics.binary_macro_f1(y_true, baseline_pred)
    out["up_rate"] = float(y_true.mean())
    out["macro_f1"] = float(macro)
    out["dummy_macro_f1"] = float(dummy)
    out["delta_vs_dummy"] = float(macro - dummy)
    out["below_random_prior"] = bool(macro < float(random_prior))
    if bootstrap is not None and seed != "seed_mean":
        block_ids = (
            rows["ticker"].astype(str) + "|" + rows["trading_day"].astype(str)
        ).to_numpy()
        ci = metrics.block_bootstrap_macro_f1_delta(
            y_true, y_pred, baseline_pred, block_ids,
            n_boot=int(bootstrap["iterations"]), seed=int(bootstrap["seed"]),
        )
        out["boot_delta_lcb"] = float(ci["lcb"])
        out["boot_delta_ucb"] = float(ci["ucb"])
    return out


def _seed_mean_row(seed_rows: list[dict[str, Any]], note: str) -> dict[str, Any]:
    head = {
        key: seed_rows[0][key]
        for key in ("evidence_domain", "model_row", "row_scope", "cell")
    }
    mean_of = ("up_rate", "macro_f1", "dummy_macro_f1", "delta_vs_dummy")
    agg: dict[str, Any] = {**head, "seed": "seed_mean"}
    for key in mean_of:
        finite = [float(r[key]) for r in seed_rows if np.isfinite(r[key])]
        agg[key] = float(np.mean(finite)) if finite else float("nan")
    agg["n_rows"] = int(sum(int(r["n_rows"]) for r in seed_rows))
    agg["n_days"] = int(max(int(r["n_days"]) for r in seed_rows))
    agg["boot_delta_lcb"] = float("nan")
    agg["boot_delta_ucb"] = float("nan")
    agg["below_random_prior"] = bool(
        np.isfinite(agg["macro_f1"]) and agg["macro_f1"] < 0.5
    )
    agg["thin_cell"] = bool(any(bool(r["thin_cell"]) for r in seed_rows))
    agg["note"] = note
    return agg


def halfspread_partition_readout(
    frame: pd.DataFrame,
    *,
    evidence_domain: str,
    model_row: str,
    row_scope: str,
    cell_column: str = "cell",
    seed_axis: str = "seed",
    random_prior: float = 0.5,
    report_min_rows: int = REPORT_MIN_ROWS,
    bootstrap: Mapping[str, Any] | None = None,
    descriptive_note: str = "",
) -> pd.DataFrame:
    """The frozen partition readout (pre-registration section 6, R1/R2).

    ``frame`` carries one domain's candidate rows with the row-aligned
    ``baseline_y_pred`` column (:func:`align_baseline_predictions`) and the
    per-day partition ``cell_column``. Emits one row per cell x seed plus a
    seed-mean row, for the ``all`` pool, every fine and undefined cell, and
    the two coarse anchor cells — ALL cells always reported, none dropped.
    Bootstrap intervals are computed per seed only (never for the seed-mean
    row) and are descriptive context, never a significance test.
    """
    missing = sorted((_READOUT_FRAME_REQUIRED | {cell_column}) - set(frame.columns))
    if missing:
        raise ValueError(f"halfspread_partition_readout: frame missing columns {missing}")
    _require_single_domain(frame, "halfspread_partition_readout")
    if len(frame) == 0:
        raise ValueError("halfspread_partition_readout: empty frame")
    seeds = sorted({int(s) for s in frame[seed_axis].tolist()})
    cell_values = frame[cell_column].astype(str)
    cell_specs: list[tuple[str, pd.Series]] = [("all", pd.Series(True, index=frame.index))]
    for cell in list(FINE_CELLS_ORDERED) + list(UNDEFINED_CELLS):
        cell_specs.append((cell, cell_values == cell))
    for coarse, members in COARSE_CELL_MEMBERS.items():
        cell_specs.append((coarse, cell_values.isin(members)))
    rows: list[dict[str, Any]] = []
    for cell, mask in cell_specs:
        seed_rows: list[dict[str, Any]] = []
        for seed in seeds:
            sub = frame.loc[mask & (frame[seed_axis].astype(int) == int(seed))]
            row = _readout_cell_row(
                sub, evidence_domain=evidence_domain, model_row=model_row,
                row_scope=row_scope, cell=cell, seed=str(int(seed)),
                random_prior=random_prior, report_min_rows=report_min_rows,
                bootstrap=bootstrap,
            )
            rows.append(row)
            seed_rows.append(row)
        rows.append(_seed_mean_row(seed_rows, descriptive_note if cell == "all" else ""))
    return pd.DataFrame(rows)[HALFSPREAD_READOUT_COLUMNS]


def spread_activity_occupancy(
    frame: pd.DataFrame,
    *,
    evidence_domain: str,
    cell_column: str = "cell",
    tercile_column: str = "activity_tercile",
) -> pd.DataFrame:
    """Two-way (partition cell x activity tercile) row/day occupancy table
    (pre-registration section 6, R3). Counts only; discloses thin cells
    before anyone reads a delta."""
    missing = sorted({cell_column, tercile_column, "ticker", "trading_day"} - set(frame.columns))
    if missing:
        raise ValueError(f"spread_activity_occupancy: frame missing columns {missing}")
    rows: list[dict[str, Any]] = []
    grouped = frame.groupby(
        [frame[cell_column].astype(str), frame[tercile_column].astype(str)], sort=True
    )
    for (cell, tercile), sub in grouped:
        rows.append({
            "evidence_domain": evidence_domain, "cell": cell,
            "activity_tercile": tercile, "n_rows": int(len(sub)),
            "n_days": int(sub[["ticker", "trading_day"]].drop_duplicates().shape[0]),
        })
    return pd.DataFrame(rows)[OCCUPANCY_COLUMNS]


def lag1_autocov_by_tercile(
    bars: pd.DataFrame,
    day_terciles: pd.DataFrame,
    *,
    evidence_domain: str,
    tercile_column: str = "activity_tercile",
) -> pd.DataFrame:
    """Pooled within-day lag-1 autocovariance/autocorrelation of 5-minute
    returns per activity tercile (pre-registration section 6, R4; the V2.1
    pre-registration section 5 H2 signature). ``day_terciles`` maps
    (ticker, trading_day) -> tercile for the domain's dump days; bar days
    without a dump day are excluded (they carry no scored rows)."""
    stats = _day_pair_stats(within_day_log_returns(bars))
    day_map = day_terciles[["ticker", "trading_day", tercile_column]].copy()
    day_map["ticker"] = day_map["ticker"].astype(str)
    day_map["trading_day"] = day_map["trading_day"].astype(str)
    if day_map.duplicated(["ticker", "trading_day"]).any():
        raise ValueError("lag1_autocov_by_tercile: duplicate day rows in day_terciles")
    merged = stats.merge(day_map, on=["ticker", "trading_day"], how="inner")
    rows: list[dict[str, Any]] = []
    for tercile in ("all", "low", "mid", "high"):
        sub = merged if tercile == "all" else merged.loc[
            merged[tercile_column].astype(str) == tercile
        ]
        n = float(sub["n"].sum())
        if n < 2:
            rows.append({
                "evidence_domain": evidence_domain, "activity_tercile": tercile,
                "n_pairs": int(n), "autocov_lag1": float("nan"),
                "autocorr_lag1": float("nan"),
            })
            continue
        sa, sb = float(sub["sa"].sum()), float(sub["sb"].sum())
        sab = float(sub["sab"].sum())
        saa, sbb = float(sub["saa"].sum()), float(sub["sbb"].sum())
        cov = sab - sa * sb / n
        var_a = saa - sa * sa / n
        var_b = sbb - sb * sb / n
        corr = cov / np.sqrt(var_a * var_b) if var_a > 0 and var_b > 0 else float("nan")
        rows.append({
            "evidence_domain": evidence_domain, "activity_tercile": tercile,
            "n_pairs": int(n), "autocov_lag1": float(cov / (n - 1.0)),
            "autocorr_lag1": float(corr),
        })
    return pd.DataFrame(rows)[AUTOCOV_COLUMNS]


def _anchor_rows(readout: pd.DataFrame, cell: str) -> pd.DataFrame:
    return readout.loc[
        (readout["cell"].astype(str) == cell) & (readout["seed"].astype(str) != "seed_mean")
    ]


def _anchor_ok(rows: pd.DataFrame, verdict_min_rows: int) -> bool:
    return bool(len(rows) > 0 and (rows["n_rows"].astype(int) >= int(verdict_min_rows)).all())


def _monotone_with_one_inversion(deltas: list[float]) -> bool:
    inversions = sum(1 for i in range(len(deltas) - 1) if deltas[i + 1] < deltas[i])
    return inversions <= 1


def verdict_from_readout(
    low_tercile_readout: pd.DataFrame,
    *,
    verdict_min_rows: int,
    report_min_rows: int = REPORT_MIN_ROWS,
    low_anchor: str = CELL_RATIO_LE_0P5,
    fallback_low_anchor: str = COARSE_CELL_LE_1,
    high_anchor: str = COARSE_CELL_GT_1,
) -> dict[str, Any]:
    """Mechanical application of the pre-registered interpretation rules
    (pre-registration section 8) to the LOW-activity-tercile readout (R2).

    Outcomes: ``consistent_with_bounce_domination`` (A),
    ``not_explainable_by_bounce_alone`` (B), ``inconclusive`` (C). Anchor
    conditions are evaluated PER SEED and must hold for both seeds; occupancy
    failures fall back once (low anchor -> coarse) then go inconclusive. A
    fine cell enters the monotone-tendency check only when its seed-mean row's
    summed ``n_rows`` clears ``2 * report_min_rows`` (both seeds pooled); with
    fewer than three evaluable fine cells Outcome A cannot fire. All
    intervals are descriptive block-bootstrap context, never significance.
    """
    conditions: dict[str, Any] = {
        "low_anchor_used": low_anchor,
        "high_anchor_used": high_anchor,
        "verdict_min_rows": int(verdict_min_rows),
    }
    low_rows = _anchor_rows(low_tercile_readout, low_anchor)
    if not _anchor_ok(low_rows, verdict_min_rows):
        conditions["low_anchor_used"] = fallback_low_anchor
        conditions["low_anchor_fallback"] = True
        low_rows = _anchor_rows(low_tercile_readout, fallback_low_anchor)
    high_rows = _anchor_rows(low_tercile_readout, high_anchor)
    occupancy_ok = _anchor_ok(low_rows, verdict_min_rows) and _anchor_ok(
        high_rows, verdict_min_rows
    )
    conditions["anchor_occupancy_ok"] = bool(occupancy_ok)
    if not occupancy_ok:
        return {
            "verdict": "inconclusive",
            "reason": "anchor_occupancy_below_verdict_min_rows",
            "conditions": conditions,
        }

    low_d = low_rows["delta_vs_dummy"].astype(float)
    low_lcb = low_rows["boot_delta_lcb"].astype(float)
    low_ucb = low_rows["boot_delta_ucb"].astype(float)
    high_d = high_rows["delta_vs_dummy"].astype(float)
    high_lcb = high_rows["boot_delta_lcb"].astype(float)

    low_null_every_seed = bool(((low_d <= 0.0) | ((low_lcb <= 0.0) & (low_ucb >= 0.0))).all())
    low_pos_every_seed = bool(((low_d > 0.0) & (low_lcb > 0.0)).all())
    high_pos_every_seed = bool(((high_d > 0.0) & (high_lcb > 0.0)).all())
    low_sign_agreement = bool((low_d > 0.0).all() or (low_d <= 0.0).all())
    conditions.update({
        "low_anchor_null_every_seed": low_null_every_seed,
        "low_anchor_positive_every_seed": low_pos_every_seed,
        "high_anchor_positive_every_seed": high_pos_every_seed,
        "low_anchor_seed_sign_agreement": low_sign_agreement,
    })
    if not low_sign_agreement:
        return {
            "verdict": "inconclusive",
            "reason": "per_seed_sign_disagreement_on_low_anchor",
            "conditions": conditions,
        }

    seed_mean = low_tercile_readout.loc[
        low_tercile_readout["seed"].astype(str) == "seed_mean"
    ]
    fine = seed_mean.loc[seed_mean["cell"].isin(FINE_CELLS_ORDERED)]
    evaluable = fine.loc[
        (fine["n_rows"].astype(int) >= int(report_min_rows) * 2)
        & np.isfinite(fine["delta_vs_dummy"].astype(float))
    ]
    ordered = [
        float(evaluable.loc[evaluable["cell"] == cell, "delta_vs_dummy"].iloc[0])
        for cell in FINE_CELLS_ORDERED
        if (evaluable["cell"] == cell).any()
    ]
    monotone_evaluable = len(ordered) >= 3
    monotone_ok = bool(monotone_evaluable and _monotone_with_one_inversion(ordered))
    conditions["monotone_evaluable"] = monotone_evaluable
    conditions["monotone_nondecreasing_ok"] = monotone_ok
    conditions["fine_cell_seed_mean_deltas_in_ratio_order"] = ordered

    all_row = seed_mean.loc[seed_mean["cell"] == "all"]
    all_delta = float(all_row["delta_vs_dummy"].iloc[0]) if len(all_row) else float("nan")
    low_mean_delta = float(low_d.mean())
    conditions["seed_mean_low_anchor_delta"] = low_mean_delta
    conditions["seed_mean_all_low_rows_delta"] = all_delta
    half_size_ok = bool(
        np.isfinite(all_delta) and all_delta > 0.0 and low_mean_delta >= 0.5 * all_delta
    )
    conditions["low_anchor_at_least_half_of_all_low_delta"] = half_size_ok

    if low_null_every_seed and high_pos_every_seed and monotone_ok:
        return {
            "verdict": "consistent_with_bounce_domination",
            "reason": "low_anchor_null_high_anchor_positive_monotone",
            "conditions": conditions,
        }
    if low_pos_every_seed and half_size_ok:
        return {
            "verdict": "not_explainable_by_bounce_alone",
            "reason": "low_anchor_positive_at_comparable_size",
            "conditions": conditions,
        }
    return {
        "verdict": "inconclusive",
        "reason": "pattern_matches_neither_predeclared_outcome",
        "conditions": conditions,
    }
