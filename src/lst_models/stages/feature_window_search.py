from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from lst_models import metrics
from lst_models.artifacts import require_artifacts, write_artifact_inventory, write_json
from lst_models.config import hash_file, hash_mapping
from lst_models.data import read_raw_txt_file, resample_1min_to_5min
from lst_models.device import (
    device_manifest_fields as build_device_manifest_fields,
    resolve_torch_device as resolve_project_torch_device,
)
from lst_models.splits import add_split_column, parse_split_boundaries


SUMMARY_COLUMNS = [
    "candidate_id",
    "feature_set",
    "window_size",
    "n_samples_total",
    "n_samples_by_ticker_json",
    "n_train_inner_folds",
    "n_seeds",
    "n_probe_rows",
    "mean_macro_f1",
    "mean_balanced_accuracy",
    "mean_roc_auc",
    "mean_mcc",
    "mean_delta_macro_f1_vs_stratified_dummy",
    "lcb_delta_macro_f1_vs_stratified_dummy",
    "positive_ticker_count",
    "best_screening_family",
    "family_lcb_selection_policy",
    "median_family_lcb_delta_macro_f1_vs_stratified_dummy",
    "min_family_lcb_delta_macro_f1_vs_stratified_dummy",
    "best_family_lcb_delta_macro_f1_vs_stratified_dummy",
    "positive_stage02_family_count",
    "family_mean_delta_macro_f1_json",
    "family_lcb_delta_macro_f1_json",
    "family_positive_ticker_count_json",
    "seed_std_macro_f1",
    "fold_std_macro_f1",
    "selected_for_stage02",
    "selection_reason",
]

LEDGER_COLUMNS = [
    "probe_id",
    "model_family",
    "candidate_id",
    "feature_set",
    "window_size",
    "fold_id",
    "seed",
    "fit_status",
    "n_train_samples",
    "n_eval_samples",
    "macro_f1",
    "balanced_accuracy",
    "accuracy",
    "roc_auc",
    "mcc",
    "baseline_id",
    "baseline_macro_f1",
    "baseline_balanced_accuracy",
    "delta_macro_f1_vs_baseline",
    "delta_balanced_accuracy_vs_baseline",
    "sample_id_hash",
    "error_message",
    "positive_ticker_count",
    "ticker_delta_macro_f1_json",
    "block_delta_macro_f1_json",
    "requested_device",
    "resolved_device",
    "device_fallback_reason",
]

FOLD_COLUMNS = [
    "fold_id",
    "train_start",
    "train_end_exclusive",
    "eval_start",
    "eval_end_exclusive",
    "purge_or_embargo_policy",
    "n_train_samples",
    "n_eval_samples",
    "event_overlap_count",
]

MANDATORY_BASELINES = {"stratified_dummy_train_prior", "majority_train_prior"}
IMPLEMENTED_PROBES = {
    "logreg_flat_control",
    "lightgbm_small",
    "standard_dlinear_tiny",
    "tcn_tiny",
    "ms_dlinear_tcn_tiny",
}
PROBE_MODEL_FAMILY = {
    "stratified_dummy_train_prior": "mandatory_baseline",
    "majority_train_prior": "mandatory_baseline",
    "logreg_flat_control": "linear_control",
    "lightgbm_small": "lightgbm",
    "standard_dlinear_tiny": "standard_dlinear",
    "tcn_tiny": "tcn",
    "ms_dlinear_tcn_tiny": "ms_dlinear_tcn",
}
STAGE02_SCREENING_FAMILIES = {"lightgbm", "standard_dlinear", "tcn", "ms_dlinear_tcn"}
BAND_DIAGNOSTIC_BPS = (3.0, 10.0, 20.0, 30.0, 50.0)
_TORCH_IMPORT_ERROR: str | None = None


@dataclass(frozen=True)
class Stage01Result:
    output_dir: Path
    run_manifest: Path
    artifact_inventory: Path
    summary: Path
    candidate_inputs: Path
    probe_ledger: Path
    fold_manifest: Path
    band_diagnostic: Path


@dataclass(frozen=True)
class CandidateDataset:
    metadata: pd.DataFrame
    feature_blocks: Mapping[tuple[str, str], np.ndarray]
    feature_columns: tuple[str, ...]
    window_size: int


@dataclass(frozen=True)
class ProbeFitResult:
    predictions: np.ndarray
    scores: np.ndarray
    requested_device: str
    resolved_device: str
    cuda_available: bool | None
    gpu_name_or_null: str | None
    device_fallback_reason: str


def run_stage(config: Mapping[str, Any]) -> Stage01Result:
    _validate_config(config)

    inputs = _as_mapping(config["inputs"], "inputs")
    outputs = _as_mapping(config["outputs"], "outputs")
    stage00_run_dir = Path(str(inputs["stage00_runtime_run_dir"]))
    required = inputs.get("required_stage00_artifacts", [])
    stage00_paths = require_artifacts(stage00_run_dir, required)

    stage00_manifest = _load_json(stage00_paths["run_manifest.json"])
    if stage00_manifest.get("holdout_test_contact") is not False:
        raise ValueError("Stage 01 requires Stage 00 run_manifest holdout_test_contact=false")

    raw_manifest = _load_json(stage00_paths["raw_data_manifest.json"])
    split_freeze = _load_json(stage00_paths["split_freeze.json"])
    label_policy = _load_json(stage00_paths["label_policy.json"])
    sample_events = _load_sample_event_index(stage00_paths["sample_event_index.csv"])
    train_events = _train_valid_events(sample_events)
    train_bars = _load_train_bars(raw_manifest, split_freeze, inputs)
    feature_frame = _build_feature_frame(train_bars)
    folds = _build_train_inner_folds(train_events, int(config["train_inner"]["n_folds"]))
    band_diagnostic = _build_train_band_diagnostic(train_bars, label_policy)

    feature_sets = _as_mapping(config["feature_sets"], "feature_sets")
    window_sizes = tuple(int(value) for value in config["window_sizes"])
    seeds = tuple(int(value) for value in config["train_inner"]["seeds"])
    probe_ids = _enabled_probe_ids(config)
    _enforce_budget(tuple(feature_sets), window_sizes, probe_ids, folds, seeds, config)

    summary_rows: list[dict[str, Any]] = []
    ledger_parts: list[pd.DataFrame] = []
    for feature_set, requested_columns in feature_sets.items():
        feature_columns = tuple(str(column) for column in requested_columns)
        _require_feature_columns(feature_columns, feature_frame)
        for window_size in window_sizes:
            dataset = _build_window_dataset(
                feature_frame,
                train_events,
                feature_set=str(feature_set),
                feature_columns=feature_columns,
                window_size=window_size,
            )
            candidate_ledger = _run_candidate_probes(
                dataset,
                folds,
                seeds,
                probe_ids,
                str(feature_set),
                window_size,
                config,
            )
            ledger_parts.append(candidate_ledger)
            summary_rows.append(
                _summarize_candidate(
                    dataset,
                    candidate_ledger,
                    folds,
                    seeds,
                    probe_ids,
                    str(feature_set),
                    window_size,
                )
            )

    ledger = pd.concat(ledger_parts, ignore_index=True) if ledger_parts else pd.DataFrame(columns=LEDGER_COLUMNS)
    summary = _select_candidates(pd.DataFrame(summary_rows, columns=SUMMARY_COLUMNS), config)
    candidate_inputs = _build_candidate_inputs(config, stage00_manifest, summary, feature_sets)

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(str(outputs["output_dir"])) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / str(outputs["summary"])
    candidate_path = write_json(output_dir / str(outputs["candidate_inputs"]), candidate_inputs)
    ledger_path = output_dir / str(outputs["probe_ledger"])
    fold_path = output_dir / str(outputs["fold_manifest"])
    band_path = output_dir / str(outputs["label_band_diagnostic"])
    summary.to_csv(summary_path, index=False)
    ledger.to_csv(ledger_path, index=False)
    folds.to_csv(fold_path, index=False)
    band_diagnostic.to_csv(band_path, index=False)

    notebook_path = _resolve_repo_path(inputs["notebook_path"])
    manifest_payload = {
        "route": config["route"],
        "stage_name": config["stage_name"],
        "scope": config["scope"],
        "config_sha256": hash_mapping(config),
        "notebook_sha256": hash_file(notebook_path),
        "source_stage00_run_id": inputs["stage00_run_id"],
        "input_artifacts": [str(path) for path in stage00_paths.values()],
        "output_artifacts": [
            str(outputs["summary"]),
            str(outputs["candidate_inputs"]),
            str(outputs["probe_ledger"]),
            str(outputs["fold_manifest"]),
            str(outputs["label_band_diagnostic"]),
        ],
        "stage01_execution_mode": "feature_window_probe_screening_v1",
        "implemented_probe_ids": sorted(IMPLEMENTED_PROBES.intersection(probe_ids)),
        "skipped_probe_ids": sorted(set(probe_ids) - IMPLEMENTED_PROBES),
        "official_validation_for_selection": False,
        "no_final_model_selected": True,
        "holdout_test_contact": False,
    }
    manifest_payload.update(_device_manifest_fields(config, ledger))
    manifest_path = write_json(output_dir / str(outputs["manifest"]), manifest_payload)
    inventory_path = write_artifact_inventory(
        output_dir,
        {
            "run_manifest": manifest_path,
            "summary": summary_path,
            "candidate_inputs": candidate_path,
            "probe_ledger": ledger_path,
            "fold_manifest": fold_path,
            "label_band_diagnostic": band_path,
        },
    )

    return Stage01Result(
        output_dir=output_dir,
        run_manifest=manifest_path,
        artifact_inventory=inventory_path,
        summary=summary_path,
        candidate_inputs=candidate_path,
        probe_ledger=ledger_path,
        fold_manifest=fold_path,
        band_diagnostic=band_path,
    )


def _validate_config(config: Mapping[str, Any]) -> None:
    if config.get("scope") != "validation_only":
        raise ValueError(f"expected validation_only scope, got {config.get('scope')!r}")
    if config.get("holdout_test_contact") is not False:
        raise ValueError("Stage 01 requires holdout_test_contact=false")
    train_inner = _as_mapping(config["train_inner"], "train_inner")
    if train_inner.get("official_validation_for_selection") is not False:
        raise ValueError("Stage 01 selection must use train-inner folds only")
    if list(config.get("window_sizes", [])) != [10, 20, 30]:
        raise ValueError("Stage 01 window_sizes must be exactly [10, 20, 30]")
    baseline_ids = set(
        str(value)
        for value in _as_mapping(config["baseline_probes"], "baseline_probes").get(
            "mandatory_trivial", []
        )
    )
    if baseline_ids != MANDATORY_BASELINES:
        raise ValueError(
            "Stage 01 mandatory baselines must be exactly "
            "stratified_dummy_train_prior and majority_train_prior"
        )
    probe_ids = set(_as_mapping(config["lightweight_probes"], "lightweight_probes"))
    if not IMPLEMENTED_PROBES.issubset(probe_ids):
        missing = sorted(IMPLEMENTED_PROBES - probe_ids)
        raise ValueError(f"Stage 01 lightweight_probes missing required probes: {missing}")
    selection_rules = _as_mapping(config["selection_rules"], "selection_rules")
    if selection_rules.get("no_final_model_selected") is not True:
        raise ValueError("Stage 01 must declare no_final_model_selected=true")
    if str(selection_rules.get("baseline")) not in MANDATORY_BASELINES:
        raise ValueError("Stage 01 selection_rules.baseline must be one mandatory baseline")
    expected_handoff = ["lightgbm", "standard_dlinear", "tcn", "ms_dlinear_tcn"]
    handoff = _as_mapping(config["stage02_handoff"], "stage02_handoff")
    if list(handoff.get("recommended_model_families", [])) != expected_handoff:
        raise ValueError(
            "Stage 01 stage02_handoff.recommended_model_families must be "
            f"{expected_handoff}"
        )


def _as_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"expected mapping for {name}, got {type(value).__name__}")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"expected JSON object in {path}")
    return loaded


def _resolve_repo_path(path_value: Any) -> Path:
    path = Path(str(path_value))
    if path.is_absolute():
        return path
    return _repo_root() / path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_sample_event_index(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required_columns = {
        "sample_id",
        "ticker",
        "target_timestamp",
        "trading_day",
        "split",
        "label",
        "valid_label",
    }
    missing = sorted(required_columns - set(frame.columns))
    if missing:
        raise ValueError(f"sample_event_index.csv missing columns: {missing}")
    frame = frame.copy()
    frame["target_timestamp"] = pd.to_datetime(frame["target_timestamp"])
    frame["trading_day"] = frame["trading_day"].astype(str)
    return frame


def _train_valid_events(sample_events: pd.DataFrame) -> pd.DataFrame:
    valid_label = sample_events["valid_label"].map(_is_true)
    train = sample_events.loc[(sample_events["split"] == "train") & valid_label].copy()
    if train.empty:
        raise ValueError("Stage 01 found no train split rows with valid_label=true")
    train["label"] = train["label"].astype(int)
    return train.sort_values(["target_timestamp", "ticker", "sample_id"]).reset_index(drop=True)


def _is_true(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def _load_train_bars(
    raw_manifest: Mapping[str, Any],
    split_freeze: Mapping[str, Any],
    inputs: Mapping[str, Any],
) -> pd.DataFrame:
    raw_source = _as_mapping(raw_manifest["raw_source"], "raw_source")
    recipe = _as_mapping(raw_manifest["five_minute_recipe"], "five_minute_recipe")
    raw_data_dir = Path(str(inputs.get("raw_data_dir", raw_source["local_download_dir"])))
    boundaries = parse_split_boundaries(split_freeze)

    frames = []
    for ticker in raw_manifest["tickers"]:
        file_spec = _as_mapping(raw_source["files"][ticker], f"raw_source.files.{ticker}")
        raw_path = raw_data_dir / str(file_spec["name"])
        one_minute = read_raw_txt_file(raw_path, str(ticker), raw_source)
        five_minute = resample_1min_to_5min(one_minute, recipe)
        split_frame = add_split_column(five_minute, boundaries)
        frames.append(split_frame.loc[split_frame["split"] == "train"].copy())

    if not frames:
        raise ValueError("Stage 01 raw loading produced no train bar frames")
    bars = pd.concat(frames, ignore_index=True).sort_values(["ticker", "timestamp"])
    if bars.empty:
        raise ValueError("Stage 01 found no train bars after Stage 00 split filtering")
    bars["trading_day"] = bars["timestamp"].dt.strftime("%Y-%m-%d")
    return bars.reset_index(drop=True)


def _build_train_band_diagnostic(
    train_bars: pd.DataFrame, label_policy: Mapping[str, Any]
) -> pd.DataFrame:
    horizon_k = int(label_policy["horizon_k"])
    expected_horizon = pd.Timedelta(minutes=5 * horizon_k)
    parts = []
    for ticker, ticker_frame in train_bars.groupby("ticker", sort=True):
        part = ticker_frame.sort_values("timestamp").copy()
        close = part["close"].astype(float)
        future_timestamp = part["timestamp"].shift(-horizon_k)
        future_return = close.shift(-horizon_k) / close - 1.0
        same_day = pd.Series(True, index=part.index)
        current_day = part["timestamp"].dt.date
        for offset in range(1, horizon_k + 1):
            same_day &= current_day.shift(-offset).eq(current_day)
        actual_horizon = future_timestamp - part["timestamp"]
        valid_base = future_return.notna() & same_day & actual_horizon.eq(expected_horizon)
        parts.append(
            pd.DataFrame(
                {
                    "ticker": str(ticker),
                    "trading_day": part["trading_day"].astype(str),
                    "future_return": future_return,
                    "valid_before_band": valid_base,
                }
            )
        )
    if not parts:
        return pd.DataFrame(columns=_band_diagnostic_columns())

    frame = pd.concat(parts, ignore_index=True)
    eligible = frame.loc[frame["valid_before_band"]].copy()
    rows = [_band_diagnostic_row("overall", eligible, band) for band in BAND_DIAGNOSTIC_BPS]
    for ticker, group in eligible.groupby("ticker", sort=True):
        rows.extend(_band_diagnostic_row(str(ticker), group, band) for band in BAND_DIAGNOSTIC_BPS)
    return pd.DataFrame(rows, columns=_band_diagnostic_columns())


def _band_diagnostic_columns() -> list[str]:
    return [
        "scope",
        "band_bps",
        "n_train_base_rows",
        "valid_rows",
        "up_rows",
        "down_rows",
        "no_trade_rows",
        "valid_pct",
        "up_pct",
        "down_pct",
        "no_trade_pct",
        "abs_return_p50_bps",
        "abs_return_p75_bps",
        "abs_return_p90_bps",
        "abs_return_p95_bps",
        "abs_return_p99_bps",
    ]


def _band_diagnostic_row(scope: str, frame: pd.DataFrame, band_bps: float) -> dict[str, Any]:
    returns = frame["future_return"].astype(float)
    threshold = band_bps / 10000.0
    no_trade = returns.abs().le(threshold)
    up = returns.gt(threshold)
    down = returns.lt(-threshold)
    total = int(len(returns))
    abs_bps = returns.abs() * 10000.0
    quantiles = abs_bps.quantile([0.50, 0.75, 0.90, 0.95, 0.99]) if total else pd.Series(dtype=float)
    return {
        "scope": scope,
        "band_bps": float(band_bps),
        "n_train_base_rows": total,
        "valid_rows": int((~no_trade).sum()),
        "up_rows": int(up.sum()),
        "down_rows": int(down.sum()),
        "no_trade_rows": int(no_trade.sum()),
        "valid_pct": _safe_ratio((~no_trade).sum(), total),
        "up_pct": _safe_ratio(up.sum(), total),
        "down_pct": _safe_ratio(down.sum(), total),
        "no_trade_pct": _safe_ratio(no_trade.sum(), total),
        "abs_return_p50_bps": _quantile_value(quantiles, 0.50),
        "abs_return_p75_bps": _quantile_value(quantiles, 0.75),
        "abs_return_p90_bps": _quantile_value(quantiles, 0.90),
        "abs_return_p95_bps": _quantile_value(quantiles, 0.95),
        "abs_return_p99_bps": _quantile_value(quantiles, 0.99),
    }


def _safe_ratio(numerator: Any, denominator: int) -> float:
    return float(numerator) / float(denominator) if denominator else np.nan


def _quantile_value(quantiles: pd.Series, key: float) -> float:
    return float(quantiles.loc[key]) if key in quantiles.index else np.nan


def _build_feature_frame(train_bars: pd.DataFrame) -> pd.DataFrame:
    frame = train_bars.sort_values(["ticker", "timestamp"]).copy()
    day_group = frame.groupby(["ticker", "trading_day"], sort=False)

    previous_close = day_group["close"].shift(1)
    close = frame["close"].astype(float)
    open_ = frame["open"].astype(float)
    high = frame["high"].astype(float)
    low = frame["low"].astype(float)
    volume = frame["volume"].astype(float)

    frame["log_return"] = np.log(close / previous_close)
    frame["close_to_open_return"] = np.log(close / open_)
    frame["high_low_range"] = (high - low) / close.replace(0.0, np.nan)
    frame["rolling_volatility_20"] = day_group["log_return"].transform(
        lambda series: series.rolling(20, min_periods=5).std()
    )

    delta = day_group["close"].diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.groupby([frame["ticker"], frame["trading_day"]]).transform(
        lambda series: series.rolling(14, min_periods=5).mean()
    )
    avg_loss = loss.groupby([frame["ticker"], frame["trading_day"]]).transform(
        lambda series: series.rolling(14, min_periods=5).mean()
    )
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    frame["rsi_14"] = (100.0 - (100.0 / (1.0 + rs))) / 100.0
    frame.loc[avg_loss.eq(0.0) & avg_gain.gt(0.0), "rsi_14"] = 1.0

    rolling_mean = day_group["close"].transform(lambda series: series.rolling(20, min_periods=10).mean())
    rolling_std = day_group["close"].transform(lambda series: series.rolling(20, min_periods=10).std())
    lower = rolling_mean - 2.0 * rolling_std
    upper = rolling_mean + 2.0 * rolling_std
    frame["bollinger_pctb"] = (close - lower) / (upper - lower).replace(0.0, np.nan)

    # MACD/close_scale reset per trading day like every other feature in the set,
    # so this one indicator does not silently carry overnight-gap state across
    # sessions (which would make it behave differently from the day-local rest).
    ema12 = day_group["close"].transform(lambda series: series.ewm(span=12, adjust=False).mean())
    ema26 = day_group["close"].transform(lambda series: series.ewm(span=26, adjust=False).mean())
    macd = ema12 - ema26
    signal = macd.groupby([frame["ticker"], frame["trading_day"]]).transform(
        lambda series: series.ewm(span=9, adjust=False).mean()
    )
    macd_hist = macd - signal
    close_scale = day_group["close"].transform(lambda series: series.rolling(20, min_periods=10).std())
    frame["normalized_macd_hist"] = macd_hist / close_scale.replace(0.0, np.nan)

    rolling_volume = day_group["volume"].transform(lambda series: series.rolling(20, min_periods=5).mean())
    frame["normalized_volume_20"] = volume / rolling_volume.replace(0.0, np.nan) - 1.0

    minute_of_day = frame["timestamp"].dt.hour * 60 + frame["timestamp"].dt.minute
    market_open_minute = 9 * 60 + 30
    regular_session_minutes = 6.5 * 60
    phase = 2.0 * np.pi * (minute_of_day - market_open_minute) / regular_session_minutes
    frame["time_of_day_sin"] = np.sin(phase)
    frame["time_of_day_cos"] = np.cos(phase)

    return frame.reset_index(drop=True)


def _require_feature_columns(feature_columns: tuple[str, ...], feature_frame: pd.DataFrame) -> None:
    missing = sorted(set(feature_columns) - set(feature_frame.columns))
    if missing:
        raise ValueError(f"Stage 01 feature set references missing columns: {missing}")


def _build_train_inner_folds(train_events: pd.DataFrame, n_folds: int) -> pd.DataFrame:
    if n_folds < 1:
        raise ValueError("train_inner.n_folds must be at least 1")
    days = sorted(train_events["trading_day"].unique())
    if len(days) < n_folds + 1:
        raise ValueError(
            f"need at least {n_folds + 1} train trading days for {n_folds} train-inner folds, "
            f"got {len(days)}"
        )

    fold_span = max(1, len(days) // (n_folds + 1))
    rows = []
    for fold_index in range(n_folds):
        train_end_idx = min(len(days) - 1, fold_span * (fold_index + 1))
        eval_end_idx = len(days) if fold_index == n_folds - 1 else min(
            len(days), fold_span * (fold_index + 2)
        )
        train_days = days[:train_end_idx]
        eval_days = days[train_end_idx:eval_end_idx]
        fold_train = train_events.loc[train_events["trading_day"].isin(train_days)]
        fold_eval = train_events.loc[train_events["trading_day"].isin(eval_days)]
        if fold_train.empty or fold_eval.empty:
            raise ValueError(f"empty train-inner fold {fold_index}")

        eval_start = fold_eval["target_timestamp"].min()
        train_end_exclusive = eval_start
        event_overlap_count = int((fold_train["target_timestamp"] >= eval_start).sum())
        rows.append(
            {
                "fold_id": f"fold_{fold_index}",
                "train_start": fold_train["target_timestamp"].min().isoformat(),
                "train_end_exclusive": train_end_exclusive.isoformat(),
                "eval_start": eval_start.isoformat(),
                "eval_end_exclusive": (
                    fold_eval["target_timestamp"].max() + pd.Timedelta(microseconds=1)
                ).isoformat(),
                "purge_or_embargo_policy": "chronological_expanding_day_block_no_overlap",
                "n_train_samples": int(len(fold_train)),
                "n_eval_samples": int(len(fold_eval)),
                "event_overlap_count": event_overlap_count,
            }
        )

    fold_frame = pd.DataFrame(rows, columns=FOLD_COLUMNS)
    if not (fold_frame["event_overlap_count"] == 0).all():
        raise ValueError("Stage 01 train-inner folds have nonzero event overlap")
    return fold_frame


def _enabled_probe_ids(config: Mapping[str, Any]) -> tuple[str, ...]:
    lightweight = _as_mapping(config["lightweight_probes"], "lightweight_probes")
    probe_ids = [
        str(probe_id)
        for probe_id, probe_config in lightweight.items()
        if _as_mapping(probe_config, f"lightweight_probes.{probe_id}").get("enabled") is True
    ]
    controls = _as_mapping(config.get("optional_fixed_controls", {}), "optional_fixed_controls")
    probe_ids.extend(
        str(probe_id)
        for probe_id, probe_config in controls.items()
        if _as_mapping(probe_config, f"optional_fixed_controls.{probe_id}").get("enabled") is True
    )
    if not probe_ids:
        raise ValueError("Stage 01 requires at least one enabled lightweight probe")
    return tuple(probe_ids)


def _enforce_budget(
    feature_sets: tuple[str, ...],
    window_sizes: tuple[int, ...],
    probe_ids: tuple[str, ...],
    folds: pd.DataFrame,
    seeds: tuple[int, ...],
    config: Mapping[str, Any],
) -> None:
    planned_rows = len(feature_sets) * len(window_sizes) * len(probe_ids) * len(folds) * len(seeds)
    cap = int(_as_mapping(config["budget"], "budget")["max_counted_probe_rows"])
    if planned_rows > cap:
        raise ValueError(f"Stage 01 planned probe rows {planned_rows} exceed budget cap {cap}")


def _build_window_dataset(
    feature_frame: pd.DataFrame,
    train_events: pd.DataFrame,
    *,
    feature_set: str,
    feature_columns: tuple[str, ...],
    window_size: int,
) -> CandidateDataset:
    rows: list[dict[str, Any]] = []
    feature_blocks: dict[tuple[str, str], np.ndarray] = {}
    events_by_group = {
        key: group.sort_values("target_timestamp")
        for key, group in train_events.groupby(["ticker", "trading_day"], sort=False)
    }
    for key, bars in feature_frame.groupby(["ticker", "trading_day"], sort=False):
        if key not in events_by_group:
            continue
        typed_key = (str(key[0]), str(key[1]))
        bar_part = bars.sort_values("timestamp").reset_index(drop=True)
        values = bar_part.loc[:, feature_columns].to_numpy(dtype=np.float32)
        feature_blocks[typed_key] = values
        finite_row = np.isfinite(values).all(axis=1)
        position_by_timestamp = {
            pd.Timestamp(timestamp): position
            for position, timestamp in enumerate(bar_part["timestamp"].tolist())
        }
        for event in events_by_group[key].to_dict(orient="records"):
            position = position_by_timestamp.get(pd.Timestamp(event["target_timestamp"]))
            if position is None or position < window_size - 1:
                continue
            start = position - window_size + 1
            end = position + 1
            if not bool(finite_row[start:end].all()):
                continue
            rows.append(
                {
                    "sample_id": event["sample_id"],
                    "ticker": event["ticker"],
                    "target_timestamp": pd.Timestamp(event["target_timestamp"]),
                    "trading_day": event["trading_day"],
                    "label": int(event["label"]),
                    "window_start_position": int(start),
                    "window_end_position_exclusive": int(end),
                    "candidate_id": f"{feature_set}_w{window_size}",
                    "feature_set": feature_set,
                    "window_size": int(window_size),
                }
            )

    metadata = pd.DataFrame(rows)
    return CandidateDataset(
        metadata=metadata.reset_index(drop=True),
        feature_blocks=feature_blocks,
        feature_columns=feature_columns,
        window_size=window_size,
    )


def _run_candidate_probes(
    dataset: CandidateDataset,
    folds: pd.DataFrame,
    seeds: tuple[int, ...],
    probe_ids: tuple[str, ...],
    feature_set: str,
    window_size: int,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    candidate_id = f"{feature_set}_w{window_size}"
    baseline_id = str(_as_mapping(config["selection_rules"], "selection_rules")["baseline"])
    mandatory_baselines = tuple(
        str(value)
        for value in _as_mapping(config["baseline_probes"], "baseline_probes")["mandatory_trivial"]
    )
    sample_policy = _as_mapping(config.get("screening_sample_policy", {}), "screening_sample_policy")
    max_train = int(sample_policy.get("max_train_samples_per_fold", 50000))
    max_eval = int(sample_policy.get("max_eval_samples_per_fold", 20000))

    for fold in folds.to_dict(orient="records"):
        train_idx, eval_idx = _fold_indices(dataset.metadata, fold)
        train_idx = _cap_indices(dataset.metadata, train_idx, max_train)
        eval_idx = _cap_indices(dataset.metadata, eval_idx, max_eval)
        sample_hash = _sample_id_hash(dataset.metadata.iloc[eval_idx]["sample_id"].tolist())
        train_meta = dataset.metadata.iloc[train_idx]
        eval_meta = dataset.metadata.iloc[eval_idx]
        if len(train_idx) and len(eval_idx):
            x_train = _materialize_window_matrix(dataset, train_idx)
            x_eval = _materialize_window_matrix(dataset, eval_idx)
        else:
            width = dataset.window_size * len(dataset.feature_columns)
            x_train = np.empty((0, width), dtype=np.float32)
            x_eval = np.empty((0, width), dtype=np.float32)
        for seed in seeds:
            y_train = train_meta["label"].to_numpy(dtype=int)
            y_eval = eval_meta["label"].to_numpy(dtype=int)
            baseline_scores: dict[str, dict[str, Any]] = {}
            for current_baseline_id in mandatory_baselines:
                baseline_scores[current_baseline_id] = _score_train_prior_baseline(
                    current_baseline_id, y_train, y_eval, seed
                )
                rows.append(
                    _baseline_ledger_row(
                        baseline_id=current_baseline_id,
                        candidate_id=candidate_id,
                        feature_set=feature_set,
                        window_size=window_size,
                        fold_id=str(fold["fold_id"]),
                        seed=seed,
                        n_train=len(train_idx),
                        n_eval=len(eval_idx),
                        sample_hash=sample_hash,
                        scores=baseline_scores[current_baseline_id],
                    )
                )
            selected_baseline = baseline_scores[baseline_id]
            for probe_id in probe_ids:
                row = _empty_ledger_row(
                    probe_id=probe_id,
                    candidate_id=candidate_id,
                    feature_set=feature_set,
                    window_size=window_size,
                    fold_id=str(fold["fold_id"]),
                    seed=seed,
                    n_train=len(train_idx),
                    n_eval=len(eval_idx),
                    baseline_id=baseline_id,
                    sample_hash=sample_hash,
                )
                row.update(
                    {
                        "baseline_macro_f1": selected_baseline["macro_f1"],
                        "baseline_balanced_accuracy": selected_baseline["balanced_accuracy"],
                    }
                )
                if len(train_idx) == 0 or len(eval_idx) == 0:
                    row["fit_status"] = "skipped_no_fold_samples"
                    row["error_message"] = "candidate has no train/eval samples for this fold"
                else:
                    outcome = _fit_probe(
                        probe_id,
                        x_train,
                        train_meta,
                        x_eval,
                        eval_meta,
                        config,
                        seed,
                        dataset.window_size,
                        len(dataset.feature_columns),
                        selected_baseline["predictions"],
                    )
                    row.update(outcome)
                    if outcome["fit_status"] == "completed":
                        row["delta_macro_f1_vs_baseline"] = (
                            row["macro_f1"] - row["baseline_macro_f1"]
                        )
                        row["delta_balanced_accuracy_vs_baseline"] = (
                            row["balanced_accuracy"] - row["baseline_balanced_accuracy"]
                        )
                rows.append(row)
    return pd.DataFrame(rows, columns=LEDGER_COLUMNS)


def _materialize_window_matrix(dataset: CandidateDataset, indices: np.ndarray) -> np.ndarray:
    width = dataset.window_size * len(dataset.feature_columns)
    if len(indices) == 0:
        return np.empty((0, width), dtype=np.float32)
    rows = []
    for record in dataset.metadata.iloc[indices].to_dict(orient="records"):
        key = (str(record["ticker"]), str(record["trading_day"]))
        block = dataset.feature_blocks[key]
        start = int(record["window_start_position"])
        end = int(record["window_end_position_exclusive"])
        window = block[start:end]
        if len(window) != dataset.window_size:
            raise ValueError(
                f"materialized window has {len(window)} rows, expected {dataset.window_size}"
            )
        rows.append(window.reshape(-1))
    return np.vstack(rows).astype(np.float32, copy=False)


def _fold_indices(metadata: pd.DataFrame, fold: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    if metadata.empty:
        return np.array([], dtype=int), np.array([], dtype=int)
    timestamps = metadata["target_timestamp"]
    train_start = pd.Timestamp(fold["train_start"])
    train_end = pd.Timestamp(fold["train_end_exclusive"])
    eval_start = pd.Timestamp(fold["eval_start"])
    eval_end = pd.Timestamp(fold["eval_end_exclusive"])
    train_mask = (timestamps >= train_start) & (timestamps < train_end)
    eval_mask = (timestamps >= eval_start) & (timestamps < eval_end)
    return np.flatnonzero(train_mask.to_numpy()), np.flatnonzero(eval_mask.to_numpy())


def _cap_indices(metadata: pd.DataFrame, indices: np.ndarray, cap: int) -> np.ndarray:
    if cap <= 0 or len(indices) <= cap:
        return indices
    subset = metadata.iloc[indices].copy()
    subset["_source_position"] = indices
    groups = list(subset.groupby(["ticker", "label"], sort=True))
    per_group = max(1, cap // max(1, len(groups)))
    selected: list[int] = []
    for _, group in groups:
        ordered = group.sort_values(["target_timestamp", "sample_id"])
        positions = ordered["_source_position"].to_numpy(dtype=int)
        if len(positions) <= per_group:
            selected.extend(positions.tolist())
        else:
            take = np.linspace(0, len(positions) - 1, per_group, dtype=int)
            selected.extend(positions[take].tolist())
    if len(selected) > cap:
        selected = selected[:cap]
    return np.array(sorted(selected), dtype=int)


def _empty_ledger_row(
    *,
    probe_id: str,
    candidate_id: str,
    feature_set: str,
    window_size: int,
    fold_id: str,
    seed: int,
    n_train: int,
    n_eval: int,
    baseline_id: str,
    sample_hash: str,
) -> dict[str, Any]:
    return {
        "probe_id": probe_id,
        "model_family": PROBE_MODEL_FAMILY.get(probe_id, "unknown"),
        "candidate_id": candidate_id,
        "feature_set": feature_set,
        "window_size": int(window_size),
        "fold_id": fold_id,
        "seed": int(seed),
        "fit_status": "pending",
        "n_train_samples": int(n_train),
        "n_eval_samples": int(n_eval),
        "macro_f1": pd.NA,
        "balanced_accuracy": pd.NA,
        "accuracy": pd.NA,
        "roc_auc": pd.NA,
        "mcc": pd.NA,
        "baseline_id": baseline_id,
        "baseline_macro_f1": pd.NA,
        "baseline_balanced_accuracy": pd.NA,
        "delta_macro_f1_vs_baseline": pd.NA,
        "delta_balanced_accuracy_vs_baseline": pd.NA,
        "sample_id_hash": sample_hash,
        "error_message": "",
        "positive_ticker_count": 0,
        "ticker_delta_macro_f1_json": "{}",
        "block_delta_macro_f1_json": "{}",
        "requested_device": "cpu",
        "resolved_device": "cpu",
        "device_fallback_reason": "",
    }


def _baseline_ledger_row(
    *,
    baseline_id: str,
    candidate_id: str,
    feature_set: str,
    window_size: int,
    fold_id: str,
    seed: int,
    n_train: int,
    n_eval: int,
    sample_hash: str,
    scores: Mapping[str, Any],
) -> dict[str, Any]:
    row = _empty_ledger_row(
        probe_id=baseline_id,
        candidate_id=candidate_id,
        feature_set=feature_set,
        window_size=window_size,
        fold_id=fold_id,
        seed=seed,
        n_train=n_train,
        n_eval=n_eval,
        baseline_id=baseline_id,
        sample_hash=sample_hash,
    )
    row.update(
        {
            "fit_status": scores["fit_status"],
            "macro_f1": scores["macro_f1"],
            "balanced_accuracy": scores["balanced_accuracy"],
            "accuracy": scores["accuracy"],
            "roc_auc": scores.get("roc_auc", pd.NA),
            "mcc": scores.get("mcc", pd.NA),
            "baseline_macro_f1": scores["macro_f1"],
            "baseline_balanced_accuracy": scores["balanced_accuracy"],
            "delta_macro_f1_vs_baseline": 0.0,
            "delta_balanced_accuracy_vs_baseline": 0.0,
            "error_message": scores["error_message"],
        }
    )
    return row


def _score_train_prior_baseline(
    baseline_id: str, y_train: np.ndarray, y_eval: np.ndarray, seed: int
) -> dict[str, Any]:
    if len(y_train) == 0 or len(y_eval) == 0:
        predictions = np.zeros(len(y_eval), dtype=int)
        return {
            "fit_status": "skipped_no_fold_samples",
            "macro_f1": np.nan,
            "balanced_accuracy": np.nan,
            "accuracy": np.nan,
            "roc_auc": np.nan,
            "mcc": np.nan,
            "predictions": predictions,
            "scores": np.full(len(y_eval), 0.5),
            "error_message": "baseline has no train/eval samples for this fold",
        }
    if baseline_id == "stratified_dummy_train_prior":
        predictions, prediction_scores = metrics.predict_stratified_dummy(y_train, len(y_eval), seed)
    elif baseline_id == "majority_train_prior":
        predictions, prediction_scores = metrics.predict_majority(y_train, len(y_eval))
    else:
        raise ValueError(f"unknown Stage 01 mandatory baseline: {baseline_id}")
    scored = metrics.score_classifier(y_eval.astype(int), predictions, y_score=prediction_scores)
    return {
        "fit_status": "completed_baseline",
        "predictions": predictions,
        "scores": prediction_scores,
        "error_message": "",
        **scored,
    }


def _fit_probe(
    probe_id: str,
    x_train: np.ndarray,
    train_meta: pd.DataFrame,
    x_eval: np.ndarray,
    eval_meta: pd.DataFrame,
    config: Mapping[str, Any],
    seed: int,
    window_size: int,
    n_features: int,
    baseline_predictions: np.ndarray,
) -> dict[str, Any]:
    y_train = train_meta["label"].to_numpy(dtype=int)
    y_eval = eval_meta["label"].to_numpy(dtype=int)
    if len(np.unique(y_train)) < 2:
        return {
            "fit_status": "failed_single_class_train",
            "error_message": "train-inner fold train labels contain fewer than two classes",
        }
    try:
        if probe_id == "logreg_flat_control":
            predictions, prediction_scores = _fit_logreg_probe(x_train, y_train, x_eval, config, seed)
            device_info = _non_gpu_device_info()
        elif probe_id == "lightgbm_small":
            predictions, prediction_scores = _fit_lightgbm_probe(x_train, y_train, x_eval, config, seed)
            device_info = _non_gpu_device_info()
        elif probe_id in {"standard_dlinear_tiny", "tcn_tiny", "ms_dlinear_tcn_tiny"}:
            torch_result = _fit_torch_sequence_probe(
                probe_id,
                x_train,
                y_train,
                x_eval,
                config,
                seed,
                window_size,
                n_features,
            )
            predictions = torch_result.predictions
            prediction_scores = torch_result.scores
            device_info = {
                "requested_device": torch_result.requested_device,
                "resolved_device": torch_result.resolved_device,
                "device_fallback_reason": torch_result.device_fallback_reason,
            }
        else:
            return {"fit_status": "skipped_unknown_probe", "error_message": f"{probe_id} not implemented"}
    except ModuleNotFoundError as exc:
        return {"fit_status": "failed_dependency_missing", "error_message": str(exc)}
    except (ValueError, RuntimeError, FloatingPointError) as exc:
        if "GPU required" in str(exc) or "CUDA requested" in str(exc):
            raise
        return {"fit_status": "failed_exception", "error_message": f"{type(exc).__name__}: {exc}"}

    scored = metrics.score_classifier(y_eval, predictions, y_score=prediction_scores)
    ticker_deltas, positive_ticker_count = _ticker_delta_macro_f1(
        eval_meta, predictions, baseline_predictions
    )
    block_deltas = _block_delta_macro_f1(eval_meta, predictions, baseline_predictions)
    return {
        "fit_status": "completed",
        "macro_f1": scored["macro_f1"],
        "balanced_accuracy": scored["balanced_accuracy"],
        "accuracy": scored["accuracy"],
        "roc_auc": scored["roc_auc"],
        "mcc": scored["mcc"],
        "error_message": "",
        "positive_ticker_count": int(positive_ticker_count),
        "ticker_delta_macro_f1_json": json.dumps(ticker_deltas, sort_keys=True),
        "block_delta_macro_f1_json": json.dumps(block_deltas, sort_keys=True),
        **device_info,
    }


def _fit_logreg_probe(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_eval: np.ndarray,
    config: Mapping[str, Any],
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    defaults = _probe_defaults(config, "logreg_flat_control")
    scaler = StandardScaler()
    train_scaled = scaler.fit_transform(x_train)
    eval_scaled = scaler.transform(x_eval)
    model = LogisticRegression(
        solver=str(defaults.get("solver", "liblinear")),
        class_weight=defaults.get("class_weight", "balanced"),
        max_iter=int(defaults.get("max_iter", 2000)),
        random_state=seed,
    )
    model.fit(train_scaled, y_train)
    predictions = model.predict(eval_scaled).astype(int)
    scores = model.predict_proba(eval_scaled)[:, 1].astype(float)
    return predictions, scores


def _fit_lightgbm_probe(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_eval: np.ndarray,
    config: Mapping[str, Any],
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    from lightgbm import LGBMClassifier

    defaults = dict(_probe_defaults(config, "lightgbm_small"))
    defaults.setdefault("n_estimators", 200)
    defaults.setdefault("learning_rate", 0.03)
    defaults.setdefault("max_depth", 6)
    defaults.setdefault("num_leaves", 31)
    defaults.setdefault("subsample", 0.9)
    defaults.setdefault("subsample_freq", 1)
    defaults.setdefault("colsample_bytree", 0.9)
    defaults.setdefault("class_weight", "balanced")
    model = LGBMClassifier(**defaults, random_state=seed, verbosity=-1)
    model.fit(x_train, y_train)
    predictions = model.predict(x_eval).astype(int)
    scores = model.predict_proba(x_eval)[:, 1].astype(float)
    return predictions, scores


def _fit_torch_sequence_probe(
    probe_id: str,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_eval: np.ndarray,
    config: Mapping[str, Any],
    seed: int,
    window_size: int,
    n_features: int,
) -> ProbeFitResult:
    global _TORCH_IMPORT_ERROR
    if _TORCH_IMPORT_ERROR is not None:
        raise ModuleNotFoundError(_TORCH_IMPORT_ERROR)
    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset
    except (ImportError, OSError) as exc:
        _TORCH_IMPORT_ERROR = f"torch import failed: {exc}"
        raise ModuleNotFoundError(_TORCH_IMPORT_ERROR) from exc

    torch.manual_seed(seed)
    train_3d = x_train.reshape(len(x_train), window_size, n_features).astype(np.float32)
    eval_3d = x_eval.reshape(len(x_eval), window_size, n_features).astype(np.float32)
    mean = train_3d.mean(axis=(0, 1), keepdims=True)
    std = train_3d.std(axis=(0, 1), keepdims=True)
    std = np.where(std < 1e-6, 1.0, std)
    train_3d = (train_3d - mean) / std
    eval_3d = (eval_3d - mean) / std

    torch_defaults = _as_mapping(
        _as_mapping(config.get("probe_training_defaults", {}), "probe_training_defaults").get(
            "torch", {}
        ),
        "probe_training_defaults.torch",
    )
    probe_defaults = _probe_defaults(config, probe_id)
    requested_device = str(torch_defaults.get("device", "auto"))
    require_gpu = bool(torch_defaults.get("require_gpu", False))
    device, fallback_reason = resolve_project_torch_device(torch, requested_device, require_gpu)

    if probe_id == "standard_dlinear_tiny":
        model = _StandardDLinearTiny(window_size, n_features, probe_defaults)
    elif probe_id == "tcn_tiny":
        model = _TCNTiny(n_features, probe_defaults)
    elif probe_id == "ms_dlinear_tcn_tiny":
        model = _MSDLinearTCNTiny(window_size, n_features, probe_defaults)
    else:
        raise ValueError(f"unsupported torch probe: {probe_id}")

    model.to(device)
    class_counts = np.array([(y_train == 0).sum(), (y_train == 1).sum()], dtype=np.float32)
    class_counts = np.where(class_counts == 0.0, 1.0, class_counts)
    class_weights = class_counts.sum() / (2.0 * class_counts)
    loss_fn = nn.CrossEntropyLoss(
        weight=torch.as_tensor(class_weights, dtype=torch.float32, device=device)
    )
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(torch_defaults.get("learning_rate", 0.001)),
        weight_decay=float(torch_defaults.get("weight_decay", 0.0001)),
    )
    batch_size = int(torch_defaults.get("batch_size", 1024))
    epochs = int(torch_defaults.get("epochs", 8))
    train_dataset = TensorDataset(
        torch.as_tensor(train_3d, dtype=torch.float32),
        torch.as_tensor(y_train.astype(int), dtype=torch.long),
    )
    generator = torch.Generator()
    generator.manual_seed(seed)
    loader = DataLoader(
        train_dataset,
        batch_size=max(1, batch_size),
        shuffle=True,
        generator=generator,
    )
    model.train()
    for _ in range(max(1, epochs)):
        for batch_x, batch_y in loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = loss_fn(model(batch_x), batch_y)
            loss.backward()
            optimizer.step()

    model.eval()
    with torch.no_grad():
        logits = model(torch.as_tensor(eval_3d, dtype=torch.float32, device=device))
        probabilities = torch.softmax(logits, dim=1)[:, 1].cpu().numpy().astype(float)
        predictions = logits.argmax(dim=1).cpu().numpy().astype(int)
    device_fields = build_device_manifest_fields(torch, requested_device, device, fallback_reason)
    return ProbeFitResult(
        predictions=predictions,
        scores=probabilities,
        requested_device=str(device_fields["requested_device"]),
        resolved_device=str(device_fields["resolved_device"]),
        cuda_available=bool(device_fields["cuda_available"]),
        gpu_name_or_null=device_fields["gpu_name_or_null"],
        device_fallback_reason=str(device_fields["device_fallback_reason"] or ""),
    )


def _torch_gpu_name_or_null(torch_module: Any) -> str | None:
    if not bool(torch_module.cuda.is_available()):
        return None
    try:
        return str(torch_module.cuda.get_device_name(0))
    except Exception:
        return None


def _non_gpu_device_info() -> dict[str, str]:
    return {
        "requested_device": "cpu",
        "resolved_device": "cpu",
        "device_fallback_reason": "not_gpu_capable_probe",
    }


def _device_manifest_fields(config: Mapping[str, Any], ledger: pd.DataFrame) -> dict[str, Any]:
    torch_defaults = _as_mapping(
        _as_mapping(config.get("probe_training_defaults", {}), "probe_training_defaults").get(
            "torch", {}
        ),
        "probe_training_defaults.torch",
    )
    requested_device = str(torch_defaults.get("device", "auto"))
    cuda_available, gpu_name, import_error = _detect_torch_runtime()
    torch_rows = ledger.loc[ledger["model_family"].isin(STAGE02_SCREENING_FAMILIES)]
    torch_rows = torch_rows.loc[
        torch_rows["probe_id"].isin(
            ["standard_dlinear_tiny", "tcn_tiny", "ms_dlinear_tcn_tiny"]
        )
    ]
    completed = torch_rows.loc[torch_rows["fit_status"].eq("completed")]
    if completed.empty:
        resolved_device = "not_resolved"
        fallback_reason = import_error or "torch_probe_not_completed"
    else:
        resolved_values = sorted(
            str(value) for value in completed["resolved_device"].dropna().unique() if str(value)
        )
        resolved_device = ",".join(resolved_values) if resolved_values else "not_resolved"
        fallback_values = sorted(
            str(value)
            for value in completed["device_fallback_reason"].dropna().unique()
            if str(value)
        )
        fallback_reason = ",".join(fallback_values)
    return {
        "requested_device": requested_device,
        "resolved_device": resolved_device,
        "cuda_available": cuda_available,
        "gpu_name_or_null": gpu_name,
        "device_fallback_reason": fallback_reason,
    }


def _detect_torch_runtime() -> tuple[bool, str | None, str]:
    if _TORCH_IMPORT_ERROR:
        return False, None, _TORCH_IMPORT_ERROR
    try:
        import torch
    except ModuleNotFoundError as exc:
        return False, None, f"torch import failed: {exc}"
    cuda_available = bool(torch.cuda.is_available())
    return cuda_available, _torch_gpu_name_or_null(torch), "" if cuda_available else "cuda_unavailable"


class _StandardDLinearTiny:
    def __new__(cls, window_size: int, n_features: int, defaults: Mapping[str, Any]) -> Any:
        import torch.nn as nn

        class Model(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                kernel = _odd_kernel_within_window(int(defaults.get("moving_avg_kernel", 5)), window_size)
                self.kernel = kernel
                dropout = float(defaults.get("dropout", 0.10))
                width = window_size * n_features
                self.trend_head = nn.Linear(width, 2)
                self.residual_head = nn.Linear(width, 2)
                self.dropout = nn.Dropout(dropout)

            def forward(self, x: Any) -> Any:
                trend = _moving_average_same(x, self.kernel)
                residual = x - trend
                return self.trend_head(self.dropout(trend.flatten(1))) + self.residual_head(
                    self.dropout(residual.flatten(1))
                )

        return Model()


class _TCNTiny:
    def __new__(cls, n_features: int, defaults: Mapping[str, Any]) -> Any:
        import torch.nn as nn

        channels = [int(value) for value in defaults.get("channels", [32, 32])]
        kernel_size = int(defaults.get("kernel_size", 3))
        dropout = float(defaults.get("dropout", 0.10))

        class CausalBlock(nn.Module):
            def __init__(self, in_channels: int, out_channels: int, dilation: int) -> None:
                super().__init__()
                self.padding = (kernel_size - 1) * dilation
                self.conv = nn.Conv1d(
                    in_channels,
                    out_channels,
                    kernel_size=kernel_size,
                    padding=self.padding,
                    dilation=dilation,
                )
                self.norm = nn.ReLU()
                self.dropout = nn.Dropout(dropout)
                self.projection = (
                    nn.Identity()
                    if in_channels == out_channels
                    else nn.Conv1d(in_channels, out_channels, kernel_size=1)
                )

            def forward(self, x: Any) -> Any:
                y = self.conv(x)
                if self.padding:
                    y = y[:, :, :-self.padding]
                y = self.dropout(self.norm(y))
                return y + self.projection(x)

        class Model(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                layers = []
                in_channels = n_features
                for layer_index, out_channels in enumerate(channels):
                    layers.append(CausalBlock(in_channels, out_channels, dilation=2**layer_index))
                    in_channels = out_channels
                self.tcn = nn.Sequential(*layers)
                self.head = nn.Linear(in_channels, 2)

            def forward(self, x: Any) -> Any:
                encoded = self.tcn(x.transpose(1, 2))
                return self.head(encoded[:, :, -1])

        return Model()


class _MSDLinearTCNTiny:
    def __new__(cls, window_size: int, n_features: int, defaults: Mapping[str, Any]) -> Any:
        import torch
        import torch.nn as nn

        kernels = [
            _odd_kernel_within_window(int(value), window_size)
            for value in defaults.get("moving_avg_kernels", [3, 5, 9, 15])
            if int(value) <= window_size
        ]
        if not kernels:
            kernels = [3]
        dropout = float(defaults.get("dropout", 0.10))
        tcn_defaults = {
            "channels": defaults.get("tcn_channels", [32, 32]),
            "kernel_size": defaults.get("tcn_kernel_size", 3),
            "dropout": dropout,
        }

        class Model(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.kernels = kernels
                width = window_size * n_features
                self.trend_heads = nn.ModuleList([nn.Linear(width, 2) for _ in kernels])
                self.residual_heads = nn.ModuleList([nn.Linear(width, 2) for _ in kernels])
                self.tcn = _TCNTiny(n_features, tcn_defaults)
                self.dropout = nn.Dropout(dropout)
                self.mix = nn.Linear(4, 2)

            def forward(self, x: Any) -> Any:
                scale_logits = []
                for kernel, trend_head, residual_head in zip(
                    self.kernels, self.trend_heads, self.residual_heads
                ):
                    trend = _moving_average_same(x, kernel)
                    residual = x - trend
                    scale_logits.append(
                        trend_head(self.dropout(trend.flatten(1)))
                        + residual_head(self.dropout(residual.flatten(1)))
                    )
                dlinear_logits = torch.stack(scale_logits, dim=0).mean(dim=0)
                tcn_logits = self.tcn(x)
                return self.mix(torch.cat([dlinear_logits, tcn_logits], dim=1))

        return Model()


def _odd_kernel_within_window(kernel: int, window_size: int) -> int:
    current = max(1, min(kernel, window_size))
    if current % 2 == 0:
        current = max(1, current - 1)
    return current


def _moving_average_same(x: Any, kernel: int) -> Any:
    import torch.nn.functional as functional

    left = kernel // 2
    right = kernel - 1 - left
    channel_first = x.transpose(1, 2)
    padded = functional.pad(channel_first, (left, right), mode="replicate")
    return functional.avg_pool1d(padded, kernel_size=kernel, stride=1).transpose(1, 2)


def _probe_defaults(config: Mapping[str, Any], probe_id: str) -> Mapping[str, Any]:
    probe_config = _as_mapping(config["lightweight_probes"][probe_id], f"lightweight_probes.{probe_id}")
    return _as_mapping(probe_config.get("fixed_defaults", {}), f"lightweight_probes.{probe_id}.fixed_defaults")


def _classification_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import balanced_accuracy_score, f1_score

    accuracy = float((y_true == y_pred).mean()) if len(y_true) else np.nan
    return {
        "macro_f1": float(
            f1_score(y_true, y_pred, labels=[0, 1], average="macro", zero_division=0)
        )
        if len(y_true)
        else np.nan,
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred))
        if len(y_true)
        else np.nan,
        "accuracy": accuracy,
    }


def _ticker_delta_macro_f1(
    eval_meta: pd.DataFrame, predictions: np.ndarray, baseline_predictions: np.ndarray
) -> tuple[dict[str, float], int]:
    y_eval = eval_meta["label"].to_numpy(dtype=int)
    deltas: dict[str, float] = {}
    for ticker, group in eval_meta.assign(_position=np.arange(len(eval_meta))).groupby("ticker", sort=True):
        positions = group["_position"].to_numpy(dtype=int)
        model_score = _classification_metrics(y_eval[positions], predictions[positions])["macro_f1"]
        baseline_score = _classification_metrics(
            y_eval[positions], baseline_predictions[positions]
        )["macro_f1"]
        deltas[str(ticker)] = float(model_score - baseline_score)
    positive = sum(1 for value in deltas.values() if value > 0)
    return deltas, positive


def _block_delta_macro_f1(
    eval_meta: pd.DataFrame, predictions: np.ndarray, baseline_predictions: np.ndarray
) -> dict[str, float]:
    y_eval = eval_meta["label"].to_numpy(dtype=int)
    deltas: dict[str, float] = {}
    indexed = eval_meta.assign(_position=np.arange(len(eval_meta)))
    for (ticker, trading_day), group in indexed.groupby(["ticker", "trading_day"], sort=True):
        positions = group["_position"].to_numpy(dtype=int)
        model_score = _classification_metrics(y_eval[positions], predictions[positions])["macro_f1"]
        baseline_score = _classification_metrics(
            y_eval[positions], baseline_predictions[positions]
        )["macro_f1"]
        deltas[f"{ticker}|{trading_day}"] = float(model_score - baseline_score)
    return deltas


def _nan_safe_mean(values: pd.Series) -> Any:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return pd.NA
    return float(numeric.mean())


def _summarize_candidate(
    dataset: CandidateDataset,
    ledger: pd.DataFrame,
    folds: pd.DataFrame,
    seeds: tuple[int, ...],
    probe_ids: tuple[str, ...],
    feature_set: str,
    window_size: int,
) -> dict[str, Any]:
    candidate_id = f"{feature_set}_w{window_size}"
    if dataset.metadata.empty:
        by_ticker: dict[str, int] = {}
    else:
        by_ticker = {
            str(ticker): int(count)
            for ticker, count in dataset.metadata.groupby("ticker").size().to_dict().items()
        }
    completed = ledger.loc[ledger["fit_status"] == "completed"].copy()
    screening_completed = completed.loc[
        completed["model_family"].isin(STAGE02_SCREENING_FAMILIES)
    ].copy()
    row: dict[str, Any] = {
        "candidate_id": candidate_id,
        "feature_set": feature_set,
        "window_size": int(window_size),
        "n_samples_total": int(len(dataset.metadata)),
        "n_samples_by_ticker_json": json.dumps(by_ticker, sort_keys=True),
        "n_train_inner_folds": int(len(folds)),
        "n_seeds": int(len(seeds)),
        "n_probe_rows": int(len(folds) * len(seeds) * len(probe_ids)),
        "mean_macro_f1": pd.NA,
        "mean_balanced_accuracy": pd.NA,
        "mean_roc_auc": pd.NA,
        "mean_mcc": pd.NA,
        "mean_delta_macro_f1_vs_stratified_dummy": pd.NA,
        "lcb_delta_macro_f1_vs_stratified_dummy": pd.NA,
        "positive_ticker_count": 0,
        "best_screening_family": "",
        "family_lcb_selection_policy": "median_stage02_family_lcb",
        "median_family_lcb_delta_macro_f1_vs_stratified_dummy": pd.NA,
        "min_family_lcb_delta_macro_f1_vs_stratified_dummy": pd.NA,
        "best_family_lcb_delta_macro_f1_vs_stratified_dummy": pd.NA,
        "positive_stage02_family_count": 0,
        "family_mean_delta_macro_f1_json": "{}",
        "family_lcb_delta_macro_f1_json": "{}",
        "family_positive_ticker_count_json": "{}",
        "seed_std_macro_f1": pd.NA,
        "fold_std_macro_f1": pd.NA,
        "selected_for_stage02": False,
        "selection_reason": "no_completed_probe_rows",
    }
    if completed.empty:
        if len(dataset.metadata) == 0:
            row["selection_reason"] = "no_eligible_windows"
        return row

    if screening_completed.empty:
        row["selection_reason"] = "no_completed_stage02_family_probe_rows"
        return row

    row["mean_macro_f1"] = float(screening_completed["macro_f1"].astype(float).mean())
    row["mean_balanced_accuracy"] = float(
        screening_completed["balanced_accuracy"].astype(float).mean()
    )
    row["mean_roc_auc"] = _nan_safe_mean(screening_completed["roc_auc"])
    row["mean_mcc"] = _nan_safe_mean(screening_completed["mcc"])
    family_stats = _family_screening_stats(screening_completed)
    best_family, best_stats = _best_family_stats(family_stats)
    selection_stats = _family_selection_stats(family_stats)
    row["best_screening_family"] = best_family
    row["mean_delta_macro_f1_vs_stratified_dummy"] = selection_stats["median_mean_delta"]
    row["lcb_delta_macro_f1_vs_stratified_dummy"] = selection_stats["median_lcb_delta"]
    row["positive_ticker_count"] = int(best_stats["positive_ticker_count"])
    row["median_family_lcb_delta_macro_f1_vs_stratified_dummy"] = selection_stats[
        "median_lcb_delta"
    ]
    row["min_family_lcb_delta_macro_f1_vs_stratified_dummy"] = selection_stats[
        "min_lcb_delta"
    ]
    row["best_family_lcb_delta_macro_f1_vs_stratified_dummy"] = best_stats["lcb_delta"]
    row["positive_stage02_family_count"] = selection_stats["positive_family_count"]
    row["family_mean_delta_macro_f1_json"] = json.dumps(
        {family: stats["mean_delta"] for family, stats in family_stats.items()},
        sort_keys=True,
    )
    row["family_lcb_delta_macro_f1_json"] = json.dumps(
        {family: stats["lcb_delta"] for family, stats in family_stats.items()},
        sort_keys=True,
    )
    row["family_positive_ticker_count_json"] = json.dumps(
        {family: stats["positive_ticker_count"] for family, stats in family_stats.items()},
        sort_keys=True,
    )
    row["seed_std_macro_f1"] = _group_std(screening_completed, "seed", "macro_f1")
    row["fold_std_macro_f1"] = _group_std(screening_completed, "fold_id", "macro_f1")
    row["selection_reason"] = "screened_not_selected"
    return row


def _family_screening_stats(completed: pd.DataFrame) -> dict[str, dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = {}
    for family, group in completed.groupby("model_family", sort=True):
        deltas = group["delta_macro_f1_vs_baseline"].dropna().astype(float)
        ticker_deltas = _aggregate_ticker_deltas(group["ticker_delta_macro_f1_json"].tolist())
        stats[str(family)] = {
            "mean_delta": float(deltas.mean()) if not deltas.empty else np.nan,
            "lcb_delta": _block_bootstrap_lcb(group["block_delta_macro_f1_json"].tolist()),
            "positive_ticker_count": int(sum(1 for value in ticker_deltas.values() if value > 0)),
        }
    return stats


def _best_family_stats(family_stats: Mapping[str, Mapping[str, Any]]) -> tuple[str, Mapping[str, Any]]:
    if not family_stats:
        return "", {"mean_delta": np.nan, "lcb_delta": np.nan, "positive_ticker_count": 0}
    ordered = sorted(
        family_stats.items(),
        key=lambda item: (
            _nan_to_rank_value(item[1]["lcb_delta"]),
            _nan_to_rank_value(item[1]["mean_delta"]),
            str(item[0]),
        ),
        reverse=True,
    )
    return str(ordered[0][0]), ordered[0][1]


def _family_selection_stats(family_stats: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    mean_values = _finite_family_values(family_stats, "mean_delta")
    lcb_values = _finite_family_values(family_stats, "lcb_delta")
    positive_count = sum(1 for value in mean_values if value > 0.0)
    return {
        "median_mean_delta": _median_or_nan(mean_values),
        "median_lcb_delta": _median_or_nan(lcb_values),
        "min_lcb_delta": float(np.min(lcb_values)) if lcb_values else np.nan,
        "positive_family_count": int(positive_count),
    }


def _finite_family_values(
    family_stats: Mapping[str, Mapping[str, Any]], key: str
) -> list[float]:
    values = []
    for stats in family_stats.values():
        value = _to_float_or_nan(stats.get(key))
        if np.isfinite(value):
            values.append(float(value))
    return values


def _median_or_nan(values: list[float]) -> float:
    return float(np.median(values)) if values else np.nan


def _to_float_or_nan(value: Any) -> float:
    try:
        current = float(value)
    except (TypeError, ValueError):
        return np.nan
    return current if np.isfinite(current) else np.nan


def _nan_to_rank_value(value: Any) -> float:
    try:
        current = float(value)
    except (TypeError, ValueError):
        return float("-inf")
    return current if np.isfinite(current) else float("-inf")


def _block_bootstrap_lcb(encoded_rows: list[str], *, iterations: int = 1000) -> float:
    buckets: dict[str, list[float]] = {}
    for encoded in encoded_rows:
        if not encoded or encoded == "{}":
            continue
        decoded = json.loads(encoded)
        for block_id, value in decoded.items():
            buckets.setdefault(str(block_id), []).append(float(value))
    block_means = np.array([np.mean(values) for values in buckets.values()], dtype=float)
    block_means = block_means[np.isfinite(block_means)]
    if len(block_means) == 0:
        return np.nan
    if len(block_means) == 1:
        return float(block_means[0])
    rng = np.random.default_rng(20260608)
    draws = rng.choice(block_means, size=(iterations, len(block_means)), replace=True)
    return float(np.quantile(draws.mean(axis=1), 0.025))


def _aggregate_ticker_deltas(encoded_rows: list[str]) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for encoded in encoded_rows:
        if not encoded or encoded == "{}":
            continue
        decoded = json.loads(encoded)
        for ticker, value in decoded.items():
            buckets.setdefault(str(ticker), []).append(float(value))
    return {ticker: float(np.mean(values)) for ticker, values in buckets.items()}


def _group_std(frame: pd.DataFrame, group_column: str, value_column: str) -> float:
    grouped = frame.groupby(group_column)[value_column].mean()
    if len(grouped) < 2:
        return 0.0
    return float(grouped.astype(float).std(ddof=1))


def _select_candidates(summary: pd.DataFrame, config: Mapping[str, Any]) -> pd.DataFrame:
    current = summary.copy()
    rules = _as_mapping(config["selection_rules"], "selection_rules")
    max_candidates = int(rules.get("max_candidate_inputs_for_stage02", 2))
    min_positive_tickers = int(rules.get("minimum_positive_ticker_count", 3))
    min_positive_families = int(rules.get("minimum_positive_stage02_family_count", 1))
    policy = str(rules.get("family_lcb_selection_policy", "median_stage02_family_lcb"))
    if policy != "median_stage02_family_lcb":
        raise ValueError(
            "Stage 01 selection_rules.family_lcb_selection_policy must be "
            "'median_stage02_family_lcb'"
        )
    metric = "median_family_lcb_delta_macro_f1_vs_stratified_dummy"
    numeric_delta = pd.to_numeric(
        current["mean_delta_macro_f1_vs_stratified_dummy"], errors="coerce"
    )
    positive_tickers = pd.to_numeric(current["positive_ticker_count"], errors="coerce").fillna(0)
    positive_families = pd.to_numeric(
        current["positive_stage02_family_count"], errors="coerce"
    ).fillna(0)
    eligible = (
        (numeric_delta > 0.0)
        & (positive_tickers >= min_positive_tickers)
        & (positive_families >= min_positive_families)
    )
    if not eligible.any():
        current.loc[:, "selected_for_stage02"] = False
        current.loc[current["selection_reason"].eq("screened_not_selected"), "selection_reason"] = (
            "failed_stage02_eligibility_rule"
        )
        return current

    ranked = current.loc[eligible].copy()
    ranked["_rank_lcb"] = pd.to_numeric(ranked[metric], errors="coerce")
    ranked["_rank_min_family_lcb"] = pd.to_numeric(
        ranked["min_family_lcb_delta_macro_f1_vs_stratified_dummy"], errors="coerce"
    )
    ranked["_rank_best_family_lcb"] = pd.to_numeric(
        ranked["best_family_lcb_delta_macro_f1_vs_stratified_dummy"], errors="coerce"
    )
    ranked["_rank_mean_delta"] = numeric_delta.loc[eligible]
    ranked = ranked.sort_values(
        [
            "_rank_lcb",
            "_rank_min_family_lcb",
            "_rank_best_family_lcb",
            "_rank_mean_delta",
            "n_samples_total",
        ],
        ascending=[False, False, False, False, False],
    )
    selected_ids = set(ranked.head(max_candidates)["candidate_id"])
    current["selected_for_stage02"] = current["candidate_id"].isin(selected_ids)
    current.loc[current["selected_for_stage02"], "selection_reason"] = (
        "selected_train_inner_probe_signal"
    )
    return current


def _sample_id_hash(sample_ids: list[Any]) -> str:
    payload = "\n".join(str(sample_id) for sample_id in sample_ids).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _build_candidate_inputs(
    config: Mapping[str, Any],
    stage00_manifest: Mapping[str, Any],
    summary: pd.DataFrame,
    feature_sets: Mapping[str, Any],
) -> dict[str, Any]:
    handoff = _as_mapping(config["stage02_handoff"], "stage02_handoff")
    rules = _as_mapping(config["selection_rules"], "selection_rules")
    selected = summary.loc[summary["selected_for_stage02"].astype(bool)].copy()
    candidate_inputs = []
    for row in selected.to_dict(orient="records"):
        candidate_inputs.append(
            {
                "candidate_id": row["candidate_id"],
                "feature_set": row["feature_set"],
                "window_size": int(row["window_size"]),
                "feature_columns": list(feature_sets[row["feature_set"]]),
                "n_samples_total": int(row["n_samples_total"]),
                "selection_reason": row["selection_reason"],
                "best_screening_family": row.get("best_screening_family", ""),
                "family_lcb_selection_policy": row.get(
                    "family_lcb_selection_policy", "median_stage02_family_lcb"
                ),
                "mean_delta_macro_f1_vs_stratified_dummy": _json_number(
                    row["mean_delta_macro_f1_vs_stratified_dummy"]
                ),
                "lcb_delta_macro_f1_vs_stratified_dummy": _json_number(
                    row["lcb_delta_macro_f1_vs_stratified_dummy"]
                ),
                "median_family_lcb_delta_macro_f1_vs_stratified_dummy": _json_number(
                    row["median_family_lcb_delta_macro_f1_vs_stratified_dummy"]
                ),
                "min_family_lcb_delta_macro_f1_vs_stratified_dummy": _json_number(
                    row["min_family_lcb_delta_macro_f1_vs_stratified_dummy"]
                ),
                "best_family_lcb_delta_macro_f1_vs_stratified_dummy": _json_number(
                    row["best_family_lcb_delta_macro_f1_vs_stratified_dummy"]
                ),
                "positive_stage02_family_count": int(row["positive_stage02_family_count"]),
                "family_mean_delta_macro_f1": json.loads(
                    row.get("family_mean_delta_macro_f1_json", "{}") or "{}"
                ),
                "family_lcb_delta_macro_f1": json.loads(
                    row.get("family_lcb_delta_macro_f1_json", "{}") or "{}"
                ),
                "family_positive_ticker_count": json.loads(
                    row.get("family_positive_ticker_count_json", "{}") or "{}"
                ),
            }
        )
    decision = (
        "selected_candidate_inputs_for_stage02_train_inner_hpo"
        if candidate_inputs
        else "do_not_start_stage02_no_feature_window_cell_passed_train_inner_screen"
    )
    return {
        "route": config["route"],
        "stage_name": config["stage_name"],
        "source_stage00_run_id": config["inputs"]["stage00_run_id"],
        "source_stage00_config_sha256": stage00_manifest.get("config_sha256"),
        "candidate_inputs": candidate_inputs,
        "family_lcb_selection_policy": str(
            rules.get("family_lcb_selection_policy", "median_stage02_family_lcb")
        ),
        "approved_model_families_for_stage02": (
            list(handoff["recommended_model_families"]) if candidate_inputs else []
        ),
        "recommended_model_families_from_protocol": list(handoff["recommended_model_families"]),
        "control_models_for_stage02": list(handoff.get("control_models", [])),
        "stage02_modeling_scope_axis": list(handoff.get("modeling_scope_axis", [])),
        "decision": decision,
        "no_final_model_selected": True,
        "holdout_test_contact": False,
    }


def _json_number(value: Any) -> float | None:
    if pd.isna(value):
        return None
    return float(value)
