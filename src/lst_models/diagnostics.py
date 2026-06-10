"""Validation-diagnostics measurement builders over the frozen Stage 03 dump.

Pure measurement logic: every function takes already-loaded frames/mappings
and returns frames or plain values. No file paths, no model fitting, no stage
gates, no artifact writing — those belong to the stage orchestration module.
Measure-only by construction (protocol 04 sections 4-6, 10): nothing here
fits a calibrator, marks an operating point, or re-scores a model.
"""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd

from lst_models import metrics
from lst_models.config import require_mapping

DUMP_COLUMNS = [
    "candidate_role", "candidate_id", "model_family", "hpo_profile_id", "seed",
    "sample_id", "ticker", "target_timestamp", "trading_day", "y_true", "p_up",
    "y_pred", "scope",
]
NOT_COMPUTED = "not_computed_due_to_baseline_reconstruction_mismatch"
ROW_SCOPE = "validation_only"

CALIBRATION_SUMMARY_COLUMNS = [
    "candidate_role", "candidate_id", "seed", "ticker", "view", "binning_scheme",
    "n_bins", "n_rows", "ece", "mce", "brier_score", "brier_reliability",
    "brier_resolution", "brier_uncertainty", "mean_predicted", "base_rate_up",
    "scope",
]
RELIABILITY_BINS_COLUMNS = [
    "candidate_role", "candidate_id", "seed", "view", "binning_scheme", "n_bins",
    "bin_index", "bin_lower", "bin_upper", "n_rows", "mean_predicted",
    "empirical_frequency", "abs_gap", "scope",
]
RISK_COVERAGE_CURVE_COLUMNS = [
    "candidate_role", "candidate_id", "seed", "coverage", "n_covered",
    "confidence_at_coverage", "selective_risk", "selective_accuracy",
    "selective_macro_f1", "scope",
]
SELECTIVE_SUMMARY_COLUMNS = [
    "candidate_role", "candidate_id", "seed", "n_rows", "aurc", "oracle_aurc",
    "e_aurc", "full_coverage_risk", "full_coverage_macro_f1", "scope",
]
ROBUSTNESS_SLICES_COLUMNS = [
    "candidate_role", "candidate_id", "seed", "slice_axis", "slice_value",
    "n_rows", "macro_f1", "delta_macro_f1_vs_stratified_dummy_train_prior",
    "delta_macro_f1_vs_majority_train_prior", "delta_source",
    "share_of_pooled_positive_delta", "loo_pooled_delta", "loo_sign_flip",
    "bootstrap_delta_lcb", "bootstrap_delta_ucb", "scope",
]
FAILURE_SLICES_COLUMNS = [
    "candidate_role", "candidate_id", "seed", "slice_axis", "slice_value",
    "n_rows", "error_count", "error_rate", "error_rate_lift_vs_seed_pooled",
    "support_up", "support_down", "scope",
]


def gate_and_derive_dump(
    dump: pd.DataFrame,
    *,
    expected_seeds: list[int],
    expected_rows: int | None,
    ledger_rows: int,
    holdout_boundary: pd.Timestamp,
) -> pd.DataFrame:
    """Fail-closed schema/row gates plus the derived dump-native columns."""
    if list(dump.columns) != DUMP_COLUMNS:
        raise ValueError(
            "03_validation_predictions.csv columns mismatch: "
            f"expected {DUMP_COLUMNS}, observed {list(dump.columns)}"
        )
    if len(dump) != ledger_rows:
        raise ValueError(
            f"03_validation_predictions.csv row count {len(dump)} does not equal the "
            f"scoring-event ledger total {ledger_rows}"
        )
    if expected_rows is not None and int(expected_rows) != len(dump):
        raise ValueError(
            f"03_validation_predictions.csv row count {len(dump)} does not equal "
            f"diagnostics.expected_dump_rows {int(expected_rows)}"
        )
    if set(dump["candidate_role"].astype(str)) != {"primary"}:
        raise ValueError("Stage 04 expects only candidate_role=primary rows in the dump")
    if set(dump["scope"].astype(str)) != {ROW_SCOPE}:
        raise ValueError("Stage 04 dump rows must all carry scope=validation_only")
    if sorted(set(dump["seed"].astype(int))) != sorted(expected_seeds):
        raise ValueError(
            f"dump seeds {sorted(set(dump['seed'].astype(int)))} != expected {expected_seeds}"
        )
    dump = dump.copy()
    dump["target_timestamp"] = pd.to_datetime(dump["target_timestamp"])
    if dump["target_timestamp"].max() >= holdout_boundary:
        raise ValueError(
            "Stage 04 blocked: dump contains rows at or after the closed holdout boundary "
            "2017-01-25"
        )
    dump["correct"] = dump["y_pred"].astype(int) == dump["y_true"].astype(int)
    dump["confidence"] = metrics.top_label_confidence(dump["p_up"].to_numpy(dtype=float))
    dump["calendar_year"] = dump["target_timestamp"].dt.year.astype(str)
    dump["calendar_quarter"] = (
        dump["calendar_year"] + "Q" + dump["target_timestamp"].dt.quarter.astype(str)
    )
    dump["time_of_day_hour"] = dump["target_timestamp"].dt.hour.map("{:02d}".format)
    dump["calendar_month"] = dump["target_timestamp"].dt.strftime("%Y-%m")
    dump["activity_tercile"] = activity_terciles(dump)
    return dump


def activity_terciles(dump: pd.DataFrame) -> pd.Series:
    """Dump-native band-pass activity proxy: per-ticker terciles of eligible
    rows per (ticker, trading_day). Named an activity proxy, never realized
    volatility (protocol section 10)."""
    labels = np.array(["low", "mid", "high"])
    tercile = pd.Series(index=dump.index, dtype=object)
    day_counts = dump.groupby(["ticker", "trading_day"]).size().rename("n")
    for ticker, ticker_days in day_counts.groupby(level="ticker"):
        ranks = ticker_days.rank(method="first")
        bins = np.ceil(ranks / len(ticker_days) * 3).clip(1, 3).astype(int) - 1
        for (_, day), bin_index in bins.items():
            mask = (dump["ticker"] == ticker) & (dump["trading_day"] == day)
            tercile.loc[mask] = labels[bin_index]
    return tercile


def identity_fields(dump: pd.DataFrame) -> dict[str, str]:
    return {
        "candidate_role": str(dump["candidate_role"].iloc[0]),
        "candidate_id": str(dump["candidate_id"].iloc[0]),
    }


def _calibration_view_arrays(dump: pd.DataFrame, view: str) -> tuple[np.ndarray, np.ndarray]:
    if view == "p_up":
        return dump["p_up"].to_numpy(dtype=float), dump["y_true"].to_numpy(dtype=int)
    if view == "top_label_confidence":
        return dump["confidence"].to_numpy(dtype=float), dump["correct"].to_numpy(dtype=int)
    raise ValueError(f"unknown calibration view {view!r}")


def _calibration_summary_row(
    base: Mapping[str, Any], ticker: str, rows: pd.DataFrame, view: str, scheme: str, n_bins: int
) -> dict[str, Any]:
    values, outcomes = _calibration_view_arrays(rows, view)
    bins = metrics.reliability_bins(outcomes, values, n_bins=n_bins, scheme=scheme)
    row: dict[str, Any] = {
        **base, "ticker": ticker, "n_rows": int(len(rows)),
        "ece": metrics.expected_calibration_error(bins),
        "mce": metrics.maximum_calibration_error(bins),
        "mean_predicted": float(values.mean()),
        "base_rate_up": float(rows["y_true"].astype(int).mean()),
        "scope": ROW_SCOPE,
        "brier_score": np.nan, "brier_reliability": np.nan,
        "brier_resolution": np.nan, "brier_uncertainty": np.nan,
    }
    if view == "p_up":
        row.update(
            metrics.brier_score_decomposition(
                rows["y_true"].to_numpy(dtype=int),
                rows["p_up"].to_numpy(dtype=float),
                n_bins=n_bins,
                scheme=scheme,
            )
        )
    return row


def calibration_frames(
    dump: pd.DataFrame, calibration: Mapping[str, Any]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    identity = identity_fields(dump)
    views = [str(view) for view in calibration["probability_views"]]
    schemes = [str(scheme) for scheme in calibration["binning_schemes"]]
    bin_counts = [int(count) for count in calibration["bin_counts"]]
    primary = (
        str(calibration["primary_view"]),
        str(calibration["primary_scheme"]),
        int(calibration["primary_bin_count"]),
    )
    summary_rows: list[dict[str, Any]] = []
    bin_rows: list[dict[str, Any]] = []
    for seed, seed_dump in dump.groupby(dump["seed"].astype(int)):
        for view in views:
            values, outcomes = _calibration_view_arrays(seed_dump, view)
            for scheme in schemes:
                for n_bins in bin_counts:
                    bins = metrics.reliability_bins(outcomes, values, n_bins=n_bins, scheme=scheme)
                    base = {
                        **identity, "seed": str(seed), "view": view,
                        "binning_scheme": scheme, "n_bins": n_bins,
                    }
                    for record in bins.to_dict(orient="records"):
                        bin_rows.append({**base, **record, "scope": ROW_SCOPE})
                    summary_rows.append(
                        _calibration_summary_row(base, "pooled", seed_dump, view, scheme, n_bins)
                    )
        view, scheme, n_bins = primary
        for ticker, ticker_dump in seed_dump.groupby("ticker"):
            base = {
                **identity, "seed": str(seed), "view": view,
                "binning_scheme": scheme, "n_bins": n_bins,
            }
            summary_rows.append(
                _calibration_summary_row(base, str(ticker), ticker_dump, view, scheme, n_bins)
            )
    pooled = pd.DataFrame(summary_rows)
    pooled = pooled.loc[pooled["ticker"].eq("pooled")]
    group_keys = ["view", "binning_scheme", "n_bins"]
    for keys, group in pooled.groupby(group_keys):
        mean_row = {**identity, "seed": "seed_mean", "ticker": "pooled"}
        mean_row.update(dict(zip(group_keys, keys)))
        mean_row["n_rows"] = int(group["n_rows"].sum())
        for column in ("ece", "mce", "brier_score", "brier_reliability", "brier_resolution",
                       "brier_uncertainty", "mean_predicted", "base_rate_up"):
            mean_row[column] = float(group[column].mean())
        mean_row["scope"] = ROW_SCOPE
        summary_rows.append(mean_row)
    return (
        pd.DataFrame(summary_rows)[CALIBRATION_SUMMARY_COLUMNS],
        pd.DataFrame(bin_rows)[RELIABILITY_BINS_COLUMNS],
    )


def selective_frames(
    dump: pd.DataFrame, selective: Mapping[str, Any]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    identity = identity_fields(dump)
    grid_step = float(selective["csv_coverage_grid_step"])
    grid_min = float(selective["csv_coverage_grid_minimum"])
    curve_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for seed, seed_dump in dump.groupby(dump["seed"].astype(int)):
        confidence = seed_dump["confidence"].to_numpy(dtype=float)
        correct = seed_dump["correct"].to_numpy(dtype=bool)
        tie = seed_dump["sample_id"].to_numpy()
        curve = metrics.risk_coverage_curve(confidence, correct, tie_break=tie)
        order = metrics._selective_order(confidence, tie)
        y_true_sorted = seed_dump["y_true"].to_numpy(dtype=int)[order]
        y_pred_sorted = seed_dump["y_pred"].to_numpy(dtype=int)[order]
        n_total = len(curve)
        for coverage in np.arange(grid_min, 1.0 + grid_step / 2, grid_step):
            n_covered = max(1, min(n_total, int(np.ceil(round(coverage * n_total, 9)))))
            curve_row = curve.iloc[n_covered - 1]
            curve_rows.append(
                {
                    **identity, "seed": str(seed),
                    "coverage": float(curve_row["coverage"]),
                    "n_covered": int(curve_row["n_covered"]),
                    "confidence_at_coverage": float(curve_row["confidence_at_coverage"]),
                    "selective_risk": float(curve_row["selective_risk"]),
                    "selective_accuracy": float(curve_row["selective_accuracy"]),
                    "selective_macro_f1": metrics.binary_macro_f1(
                        y_true_sorted[:n_covered], y_pred_sorted[:n_covered]
                    ),
                    "scope": ROW_SCOPE,
                }
            )
        aurc = metrics.aurc_metrics(confidence, correct, tie_break=tie)
        summary_rows.append(
            {
                **identity, "seed": str(seed), "n_rows": int(n_total),
                **{key: float(value) for key, value in aurc.items()},
                "full_coverage_macro_f1": metrics.binary_macro_f1(y_true_sorted, y_pred_sorted),
                "scope": ROW_SCOPE,
            }
        )
    return (
        pd.DataFrame(curve_rows)[RISK_COVERAGE_CURVE_COLUMNS],
        pd.DataFrame(summary_rows)[SELECTIVE_SUMMARY_COLUMNS],
    )


def reconstruct_dummy_baseline(
    dump: pd.DataFrame,
    train_labels: np.ndarray,
    frozen_baselines: pd.DataFrame,
    frozen_ticker: pd.DataFrame,
    reconstruction: Mapping[str, Any],
) -> tuple[dict[int, np.ndarray] | None, str]:
    """Deterministic replay of the frozen stratified-dummy draw with dual
    equality gates (protocol section 10). Reconstruction-or-nothing: any
    mismatch rejects the whole replay so realized and expectation deltas can
    never mix."""
    if not bool(reconstruction.get("enabled", True)):
        return None, "disabled"
    tolerance = float(reconstruction["equality_tolerance"])
    baseline_id = str(reconstruction["baseline_id"])
    recon: dict[int, np.ndarray] = {}
    for seed, seed_dump in dump.groupby(dump["seed"].astype(int)):
        predictions, _ = metrics.predict_stratified_dummy(train_labels, len(seed_dump), int(seed))
        y_true = seed_dump["y_true"].to_numpy(dtype=int)
        scored = metrics.score_classifier(y_true, predictions)
        frozen_row = frozen_baselines.loc[
            frozen_baselines["baseline_id"].astype(str).eq(baseline_id)
            & frozen_baselines["seed"].astype(int).eq(int(seed))
            & frozen_baselines["candidate_role"].astype(str).eq("primary")
        ]
        if len(frozen_row) != 1:
            return None, "mismatch_deltas_not_computed"
        for metric_name in ("macro_f1", "accuracy", "mcc"):
            if abs(float(scored[metric_name]) - float(frozen_row.iloc[0][metric_name])) > tolerance:
                return None, "mismatch_deltas_not_computed"
        eval_meta = pd.DataFrame({"ticker": seed_dump["ticker"].to_numpy(), "label": y_true})
        deltas, _ = metrics.ticker_delta_macro_f1(
            eval_meta, seed_dump["y_pred"].to_numpy(dtype=int), predictions
        )
        frozen_seed_rows = frozen_ticker.loc[
            frozen_ticker["seed"].astype(int).eq(int(seed))
            & frozen_ticker["candidate_role"].astype(str).eq("primary")
        ]
        for record in frozen_seed_rows.to_dict(orient="records"):
            frozen_delta = float(record["delta_macro_f1_vs_stratified_dummy_train_prior"])
            observed = deltas.get(str(record["ticker"]), np.nan)
            if np.isnan(observed) or abs(observed - frozen_delta) > tolerance:
                return None, "mismatch_deltas_not_computed"
        recon[int(seed)] = predictions
    return recon, "verified_identical"


def _macro_f1_delta_vs_constant(y_true: np.ndarray, y_pred: np.ndarray, constant: int) -> float:
    constant_pred = np.full(len(y_true), constant, dtype=int)
    return metrics.binary_macro_f1(y_true, y_pred) - metrics.binary_macro_f1(y_true, constant_pred)


def _robustness_row(
    identity: Mapping[str, str],
    seed: str,
    axis: str,
    value: str,
    slice_rows: pd.DataFrame,
    seed_dump: pd.DataFrame,
    dummy_by_index: pd.Series | None,
    verified: bool,
    pooled_delta: float,
    majority_class: int,
    frozen_ticker: pd.DataFrame,
    loo_axes: set[str],
    bootstrap: Mapping[str, Any],
) -> dict[str, Any]:
    y_true = slice_rows["y_true"].to_numpy(dtype=int)
    y_pred = slice_rows["y_pred"].to_numpy(dtype=int)
    slice_macro = metrics.binary_macro_f1(y_true, y_pred)
    row: dict[str, Any] = {
        **identity, "seed": seed, "slice_axis": axis, "slice_value": value,
        "n_rows": int(len(slice_rows)), "macro_f1": slice_macro,
        "delta_macro_f1_vs_majority_train_prior": _macro_f1_delta_vs_constant(
            y_true, y_pred, majority_class
        ),
        "share_of_pooled_positive_delta": np.nan,
        "loo_pooled_delta": np.nan, "loo_sign_flip": np.nan,
        "bootstrap_delta_lcb": np.nan, "bootstrap_delta_ucb": np.nan,
        "scope": ROW_SCOPE,
    }
    if axis == "ticker":
        frozen = frozen_ticker.loc[
            frozen_ticker["seed"].astype(str).eq(seed)
            & frozen_ticker["ticker"].astype(str).eq(value)
            & frozen_ticker["candidate_role"].astype(str).eq("primary")
        ]
        row["delta_macro_f1_vs_stratified_dummy_train_prior"] = (
            float(frozen.iloc[0]["delta_macro_f1_vs_stratified_dummy_train_prior"])
            if len(frozen) == 1
            else np.nan
        )
        row["delta_source"] = "frozen_stage03_artifact"
    elif verified:
        slice_dummy = dummy_by_index.loc[slice_rows.index].to_numpy()
        row["delta_macro_f1_vs_stratified_dummy_train_prior"] = slice_macro - (
            metrics.binary_macro_f1(y_true, slice_dummy)
        )
        row["delta_source"] = "reconstructed_realized"
    else:
        row["delta_macro_f1_vs_stratified_dummy_train_prior"] = np.nan
        row["delta_source"] = NOT_COMPUTED
    if not verified:
        return row
    slice_delta = row["delta_macro_f1_vs_stratified_dummy_train_prior"]
    if pooled_delta > 0 and not np.isnan(slice_delta):
        row["share_of_pooled_positive_delta"] = float(
            (len(slice_rows) / len(seed_dump)) * slice_delta / pooled_delta
        )
    if axis in loo_axes:
        rest = seed_dump.drop(index=slice_rows.index)
        if len(rest):
            rest_dummy = dummy_by_index.loc[rest.index].to_numpy()
            loo = metrics.binary_macro_f1(
                rest["y_true"].to_numpy(dtype=int), rest["y_pred"].to_numpy(dtype=int)
            ) - metrics.binary_macro_f1(rest["y_true"].to_numpy(dtype=int), rest_dummy)
            row["loo_pooled_delta"] = float(loo)
            row["loo_sign_flip"] = bool(loo <= 0)
    if axis == "ticker":
        slice_dummy = dummy_by_index.loc[slice_rows.index].to_numpy()
        blocks = (
            slice_rows["ticker"].astype(str) + "|" + slice_rows["trading_day"].astype(str)
        ).to_numpy()
        ci = metrics.block_bootstrap_macro_f1_delta(
            y_true, y_pred, slice_dummy, blocks,
            n_boot=int(bootstrap["iterations"]), seed=int(bootstrap["seed"]),
        )
        row["bootstrap_delta_lcb"] = ci["lcb"]
        row["bootstrap_delta_ucb"] = ci["ucb"]
    return row


def _seed_axis_row(
    identity: Mapping[str, str],
    seed: str,
    seed_dump: pd.DataFrame,
    dump: pd.DataFrame,
    dummy_by_index: pd.Series | None,
    verified: bool,
    majority_class: int,
    loo_axes: set[str],
    bootstrap: Mapping[str, Any],
) -> dict[str, Any]:
    y_true = seed_dump["y_true"].to_numpy(dtype=int)
    y_pred = seed_dump["y_pred"].to_numpy(dtype=int)
    row: dict[str, Any] = {
        **identity, "seed": seed, "slice_axis": "seed", "slice_value": seed,
        "n_rows": int(len(seed_dump)),
        "macro_f1": metrics.binary_macro_f1(y_true, y_pred),
        "delta_macro_f1_vs_majority_train_prior": _macro_f1_delta_vs_constant(
            y_true, y_pred, majority_class
        ),
        "share_of_pooled_positive_delta": np.nan,
        "loo_pooled_delta": np.nan, "loo_sign_flip": np.nan,
        "bootstrap_delta_lcb": np.nan, "bootstrap_delta_ucb": np.nan,
        "scope": ROW_SCOPE,
    }
    if not verified:
        row["delta_macro_f1_vs_stratified_dummy_train_prior"] = np.nan
        row["delta_source"] = NOT_COMPUTED
        return row
    seed_dummy = dummy_by_index.loc[seed_dump.index].to_numpy()
    row["delta_macro_f1_vs_stratified_dummy_train_prior"] = metrics.binary_macro_f1(
        y_true, y_pred
    ) - metrics.binary_macro_f1(y_true, seed_dummy)
    row["delta_source"] = "reconstructed_realized"
    if "seed" in loo_axes:
        rest = dump.drop(index=seed_dump.index)
        if len(rest):
            rest_dummy = dummy_by_index.loc[rest.index].to_numpy()
            loo = metrics.binary_macro_f1(
                rest["y_true"].to_numpy(dtype=int), rest["y_pred"].to_numpy(dtype=int)
            ) - metrics.binary_macro_f1(rest["y_true"].to_numpy(dtype=int), rest_dummy)
            row["loo_pooled_delta"] = float(loo)
            row["loo_sign_flip"] = bool(loo <= 0)
    blocks = (
        seed_dump["ticker"].astype(str) + "|" + seed_dump["trading_day"].astype(str)
    ).to_numpy()
    ci = metrics.block_bootstrap_macro_f1_delta(
        y_true, y_pred, seed_dummy, blocks,
        n_boot=int(bootstrap["iterations"]), seed=int(bootstrap["seed"]),
    )
    row["bootstrap_delta_lcb"] = ci["lcb"]
    row["bootstrap_delta_ucb"] = ci["ucb"]
    return row


def robustness_frames(
    dump: pd.DataFrame,
    train_labels: np.ndarray,
    frozen_ticker: pd.DataFrame,
    recon: dict[int, np.ndarray] | None,
    recon_status: str,
    robustness: Mapping[str, Any],
    bootstrap: Mapping[str, Any],
) -> pd.DataFrame:
    identity = identity_fields(dump)
    axes = [str(axis) for axis in robustness["slice_axes"]]
    loo_axes = {str(axis) for axis in robustness["loo_sign_flip_axes"]}
    majority_class = int(np.argmax(np.bincount(train_labels, minlength=2)))
    verified = recon is not None and recon_status == "verified_identical"
    dummy_by_index: pd.Series | None = None
    if verified:
        dummy_values = np.empty(len(dump), dtype=int)
        for seed, seed_dump in dump.groupby(dump["seed"].astype(int)):
            dummy_values[dump.index.get_indexer(seed_dump.index)] = recon[int(seed)]
        dummy_by_index = pd.Series(dummy_values, index=dump.index)
    rows: list[dict[str, Any]] = []
    for seed, seed_dump in dump.groupby(dump["seed"].astype(int)):
        seed_y = seed_dump["y_true"].to_numpy(dtype=int)
        seed_pred = seed_dump["y_pred"].to_numpy(dtype=int)
        pooled_delta = (
            metrics.binary_macro_f1(seed_y, seed_pred)
            - metrics.binary_macro_f1(
                seed_y, dummy_by_index.loc[seed_dump.index].to_numpy()
            )
            if verified
            else np.nan
        )
        for axis in axes:
            if axis == "seed":
                continue
            for value, slice_rows in seed_dump.groupby(seed_dump[axis].astype(str)):
                rows.append(
                    _robustness_row(
                        identity, str(seed), axis, str(value), slice_rows, seed_dump,
                        dummy_by_index, verified, pooled_delta, majority_class,
                        frozen_ticker, loo_axes, bootstrap,
                    )
                )
        rows.append(
            _seed_axis_row(
                identity, str(seed), seed_dump, dump, dummy_by_index, verified,
                majority_class, loo_axes, bootstrap,
            )
        )
    return pd.DataFrame(rows)[ROBUSTNESS_SLICES_COLUMNS]


def failure_frames(dump: pd.DataFrame, failure: Mapping[str, Any]) -> pd.DataFrame:
    identity = identity_fields(dump)
    minimum_rows = int(failure["minimum_slice_rows"])
    top_k = int(failure["top_k_per_axis"])
    axis_values = {
        "ticker_hour": dump["ticker"].astype(str) + "|" + dump["time_of_day_hour"].astype(str),
        "ticker_trading_day": dump["ticker"].astype(str) + "|" + dump["trading_day"].astype(str),
        "activity_tercile": dump["activity_tercile"].astype(str),
        "calendar_month": dump["calendar_month"].astype(str),
    }
    rows: list[dict[str, Any]] = []
    for seed, seed_dump in dump.groupby(dump["seed"].astype(int)):
        pooled_error = float(1.0 - seed_dump["correct"].mean())
        for axis in [str(axis) for axis in failure["slice_axes"]]:
            values = axis_values[axis].loc[seed_dump.index]
            axis_rows: list[dict[str, Any]] = []
            for value, slice_rows in seed_dump.groupby(values):
                if len(slice_rows) < minimum_rows:
                    continue
                error_rate = float(1.0 - slice_rows["correct"].mean())
                y_true = slice_rows["y_true"].astype(int)
                axis_rows.append(
                    {
                        **identity, "seed": str(seed), "slice_axis": axis,
                        "slice_value": str(value), "n_rows": int(len(slice_rows)),
                        "error_count": int((~slice_rows["correct"]).sum()),
                        "error_rate": error_rate,
                        "error_rate_lift_vs_seed_pooled": error_rate - pooled_error,
                        "support_up": int((y_true == 1).sum()),
                        "support_down": int((y_true == 0).sum()),
                        "scope": ROW_SCOPE,
                    }
                )
            axis_rows.sort(key=lambda record: record["error_rate"], reverse=True)
            rows.extend(axis_rows[:top_k])
    return pd.DataFrame(rows)[FAILURE_SLICES_COLUMNS]


def concentration_summary(robustness: pd.DataFrame) -> dict[str, list[str]]:
    flagged = robustness.loc[robustness["loo_sign_flip"].eq(True)]
    return {
        str(axis): sorted(set(group["slice_value"].astype(str)))
        for axis, group in flagged.groupby("slice_axis")
    }


def run_diagnostics(
    dump: pd.DataFrame,
    train_labels: np.ndarray,
    frozen_baselines: pd.DataFrame,
    frozen_ticker: pd.DataFrame,
    diagnostics_config: Mapping[str, Any],
) -> dict[str, Any]:
    """All measure-only diagnostics frames for the Stage 04 runner."""
    recon, recon_status = reconstruct_dummy_baseline(
        dump,
        train_labels,
        frozen_baselines,
        frozen_ticker,
        require_mapping(diagnostics_config["baseline_reconstruction"], "baseline_reconstruction"),
    )
    calibration_summary, reliability = calibration_frames(
        dump, require_mapping(diagnostics_config["calibration"], "calibration")
    )
    risk_curve, selective_summary = selective_frames(
        dump, require_mapping(diagnostics_config["selective"], "selective")
    )
    robustness = robustness_frames(
        dump,
        train_labels,
        frozen_ticker,
        recon,
        recon_status,
        require_mapping(diagnostics_config["robustness_slices"], "robustness_slices"),
        require_mapping(diagnostics_config["bootstrap"], "bootstrap"),
    )
    failures = failure_frames(
        dump, require_mapping(diagnostics_config["failure_slices"], "failure_slices")
    )
    return {
        "calibration_summary": calibration_summary,
        "reliability_bins": reliability,
        "risk_coverage_curve": risk_curve,
        "selective_summary": selective_summary,
        "robustness_slices": robustness,
        "failure_slices": failures,
        "baseline_reconstruction_status": recon_status,
        "reconstructed_dummy": recon,
    }
