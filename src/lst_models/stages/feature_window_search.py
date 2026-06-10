from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from lst_models import fitting
from lst_models.artifacts import (
    feature_rebuild_code_sha256,
    read_json_object,
    require_artifacts,
    write_artifact_inventory,
    write_json,
)
from lst_models.config import hash_file, hash_mapping, require_mapping, resolve_repo_path
from lst_models.data import (
    load_sample_event_index,
    load_train_bars,
    raw_manifest_integrity_summary,
)
from lst_models.device import detect_torch_runtime
from lst_models.features import build_feature_frame, require_feature_columns
from lst_models.fitting import fit_probe
from lst_models.metrics import block_bootstrap_lcb, score_train_prior_baseline
from lst_models.splits import build_train_inner_folds, train_valid_events
from lst_models.windows import (
    CandidateDataset,
    build_window_dataset,
    cap_indices,
    fold_indices,
    materialize_window_matrix,
    sample_id_hash,
)


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


def run_stage(config: Mapping[str, Any]) -> Stage01Result:
    _validate_config(config)

    inputs = require_mapping(config["inputs"], "inputs")
    outputs = require_mapping(config["outputs"], "outputs")
    stage00_run_dir = Path(str(inputs["stage00_runtime_run_dir"]))
    required = inputs.get("required_stage00_artifacts", [])
    stage00_paths = require_artifacts(stage00_run_dir, required)

    stage00_manifest = read_json_object(stage00_paths["run_manifest.json"])
    if stage00_manifest.get("holdout_test_contact") is not False:
        raise ValueError("Stage 01 requires Stage 00 run_manifest holdout_test_contact=false")

    raw_manifest = read_json_object(stage00_paths["raw_data_manifest.json"])
    split_freeze = read_json_object(stage00_paths["split_freeze.json"])
    label_policy = read_json_object(stage00_paths["label_policy.json"])
    sample_events = load_sample_event_index(stage00_paths["sample_event_index.csv"])
    train_events = train_valid_events(sample_events)
    train_bars = load_train_bars(raw_manifest, split_freeze, inputs)
    feature_frame = build_feature_frame(train_bars)
    folds = build_train_inner_folds(train_events, int(config["train_inner"]["n_folds"]))
    band_diagnostic = _build_train_band_diagnostic(train_bars, label_policy)

    feature_sets = require_mapping(config["feature_sets"], "feature_sets")
    window_sizes = tuple(int(value) for value in config["window_sizes"])
    seeds = tuple(int(value) for value in config["train_inner"]["seeds"])
    probe_ids = _enabled_probe_ids(config)
    _enforce_budget(tuple(feature_sets), window_sizes, probe_ids, folds, seeds, config)

    summary_rows: list[dict[str, Any]] = []
    ledger_parts: list[pd.DataFrame] = []
    for feature_set, requested_columns in feature_sets.items():
        feature_columns = tuple(str(column) for column in requested_columns)
        require_feature_columns(feature_columns, feature_frame)
        for window_size in window_sizes:
            dataset = build_window_dataset(
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

    notebook_path = resolve_repo_path(inputs["notebook_path"])
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
        "feature_rebuild_code_sha256": feature_rebuild_code_sha256(),
        "raw_file_integrity": raw_manifest_integrity_summary(raw_manifest),
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
    train_inner = require_mapping(config["train_inner"], "train_inner")
    if train_inner.get("official_validation_for_selection") is not False:
        raise ValueError("Stage 01 selection must use train-inner folds only")
    if list(config.get("window_sizes", [])) != [10, 20, 30]:
        raise ValueError("Stage 01 window_sizes must be exactly [10, 20, 30]")
    baseline_ids = set(
        str(value)
        for value in require_mapping(config["baseline_probes"], "baseline_probes").get(
            "mandatory_trivial", []
        )
    )
    if baseline_ids != MANDATORY_BASELINES:
        raise ValueError(
            "Stage 01 mandatory baselines must be exactly "
            "stratified_dummy_train_prior and majority_train_prior"
        )
    probe_ids = set(require_mapping(config["lightweight_probes"], "lightweight_probes"))
    if not IMPLEMENTED_PROBES.issubset(probe_ids):
        missing = sorted(IMPLEMENTED_PROBES - probe_ids)
        raise ValueError(f"Stage 01 lightweight_probes missing required probes: {missing}")
    selection_rules = require_mapping(config["selection_rules"], "selection_rules")
    if selection_rules.get("no_final_model_selected") is not True:
        raise ValueError("Stage 01 must declare no_final_model_selected=true")
    if str(selection_rules.get("baseline")) not in MANDATORY_BASELINES:
        raise ValueError("Stage 01 selection_rules.baseline must be one mandatory baseline")
    expected_handoff = ["lightgbm", "standard_dlinear", "tcn", "ms_dlinear_tcn"]
    handoff = require_mapping(config["stage02_handoff"], "stage02_handoff")
    if list(handoff.get("recommended_model_families", [])) != expected_handoff:
        raise ValueError(
            "Stage 01 stage02_handoff.recommended_model_families must be "
            f"{expected_handoff}"
        )


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


def _enabled_probe_ids(config: Mapping[str, Any]) -> tuple[str, ...]:
    lightweight = require_mapping(config["lightweight_probes"], "lightweight_probes")
    probe_ids = [
        str(probe_id)
        for probe_id, probe_config in lightweight.items()
        if require_mapping(probe_config, f"lightweight_probes.{probe_id}").get("enabled") is True
    ]
    controls = require_mapping(config.get("optional_fixed_controls", {}), "optional_fixed_controls")
    probe_ids.extend(
        str(probe_id)
        for probe_id, probe_config in controls.items()
        if require_mapping(probe_config, f"optional_fixed_controls.{probe_id}").get("enabled") is True
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
    cap = int(require_mapping(config["budget"], "budget")["max_counted_probe_rows"])
    if planned_rows > cap:
        raise ValueError(f"Stage 01 planned probe rows {planned_rows} exceed budget cap {cap}")


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
    baseline_id = str(require_mapping(config["selection_rules"], "selection_rules")["baseline"])
    mandatory_baselines = tuple(
        str(value)
        for value in require_mapping(config["baseline_probes"], "baseline_probes")["mandatory_trivial"]
    )
    sample_policy = require_mapping(config.get("screening_sample_policy", {}), "screening_sample_policy")
    max_train = int(sample_policy.get("max_train_samples_per_fold", 50000))
    max_eval = int(sample_policy.get("max_eval_samples_per_fold", 20000))

    for fold in folds.to_dict(orient="records"):
        train_idx, eval_idx = fold_indices(dataset.metadata, fold)
        train_idx = cap_indices(dataset.metadata, train_idx, max_train)
        eval_idx = cap_indices(dataset.metadata, eval_idx, max_eval)
        sample_hash = sample_id_hash(dataset.metadata.iloc[eval_idx]["sample_id"].tolist())
        train_meta = dataset.metadata.iloc[train_idx]
        eval_meta = dataset.metadata.iloc[eval_idx]
        if len(train_idx) and len(eval_idx):
            x_train = materialize_window_matrix(dataset, train_idx)
            x_eval = materialize_window_matrix(dataset, eval_idx)
        else:
            width = dataset.window_size * len(dataset.feature_columns)
            x_train = np.empty((0, width), dtype=np.float32)
            x_eval = np.empty((0, width), dtype=np.float32)
        for seed in seeds:
            y_train = train_meta["label"].to_numpy(dtype=int)
            y_eval = eval_meta["label"].to_numpy(dtype=int)
            baseline_scores: dict[str, dict[str, Any]] = {}
            for current_baseline_id in mandatory_baselines:
                baseline_scores[current_baseline_id] = score_train_prior_baseline(
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
                    outcome = fit_probe(
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


def _device_manifest_fields(config: Mapping[str, Any], ledger: pd.DataFrame) -> dict[str, Any]:
    torch_defaults = require_mapping(
        require_mapping(config.get("probe_training_defaults", {}), "probe_training_defaults").get(
            "torch", {}
        ),
        "probe_training_defaults.torch",
    )
    requested_device = str(torch_defaults.get("device", "auto"))
    cuda_available, gpu_name, import_error = detect_torch_runtime(fitting.TORCH_IMPORT_ERROR)
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
    row["positive_ticker_count"] = selection_stats["median_positive_ticker_count"]
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
            "lcb_delta": block_bootstrap_lcb(group["block_delta_macro_f1_json"].tolist()),
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
    positive_ticker_values = _finite_family_values(family_stats, "positive_ticker_count")
    positive_count = sum(1 for value in mean_values if value > 0.0)
    return {
        "median_mean_delta": _median_or_nan(mean_values),
        "median_lcb_delta": _median_or_nan(lcb_values),
        "min_lcb_delta": float(np.min(lcb_values)) if lcb_values else np.nan,
        "median_positive_ticker_count": _median_count_floor(positive_ticker_values),
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


def _median_count_floor(values: list[float]) -> int:
    return int(np.floor(np.median(values))) if values else 0


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
    rules = require_mapping(config["selection_rules"], "selection_rules")
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


def _build_candidate_inputs(
    config: Mapping[str, Any],
    stage00_manifest: Mapping[str, Any],
    summary: pd.DataFrame,
    feature_sets: Mapping[str, Any],
) -> dict[str, Any]:
    handoff = require_mapping(config["stage02_handoff"], "stage02_handoff")
    rules = require_mapping(config["selection_rules"], "selection_rules")
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
