"""V2 band/horizon sensitivity scan: run_stage orchestration (train-domain only).

Reuses the REAL pipeline mechanism end to end — Stage 00 frozen artifacts,
``load_train_bars`` -> ``build_feature_frame`` -> per-cell
``labels.make_direction_labels`` (via ``robustness.rebuild_cell_events``) ->
``build_train_inner_folds`` -> ``build_window_dataset`` -> capped fold rows ->
registry baselines -> the shared tcn_tiny fit wrapper — and varies exactly one
thing: the (no_trade_band_bps, horizon_k) label-policy cell, over the
preregistered cross {2.0, 3.0, 4.0} bps at horizon 9 plus horizons {6, 9, 12}
at 3.0 bps. The same-row stratified dummy is RE-DRAWN per cell, per fold, per
seed on that cell's own labels: each cell has its own label prior and its own
eligible rows, so no dummy draw is ever shared across cells.

This scan is NEVER a tuning pass: no cell is preferred, cells are never
ranked, and no alternative (band, horizon) is recommended. The frozen protocol
values (3.0 bps, 9 bars) remain frozen regardless of outcome. Everything this
stage writes is train-inner-domain evidence only and is never fused with the
official validation, train-inner control, or guarded walk-forward domains.

Preregistration sidecar:
docs/protocols/v2_band_horizon_sensitivity_preregistration_20260701.md
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from lst_models.artifacts import (
    feature_rebuild_gate_fields,
    git_commit_fields,
    write_artifact_inventory,
    write_incremental_checkpoint,
    write_json,
)
from lst_models.config import hash_file, hash_mapping, require_mapping, resolve_repo_path
from lst_models.data import raw_manifest_integrity_summary
from lst_models.device import aggregate_trial_device_fields
from lst_models.features import build_feature_frame  # noqa: F401 (rebuild chain re-export for tests)
from lst_models.fitting import fit_stage_control
from lst_models.metrics import (
    block_delta_macro_f1,
    score_classifier,
    score_registry_baseline,
    ticker_delta_macro_f1,
)
from lst_models.robustness import (
    FROZEN_BAND_BPS,
    FROZEN_HORIZON_K,
    RobustnessInputs,
    band_horizon_reading,
    events_identity_sha256,
    load_robustness_inputs,
    rebuild_cell_events,
    require_frozen_cell_event_parity,
    resolve_frozen_tcn_profile,
    resolve_run_id_or_new,
    validate_cell_specs,
)
from lst_models.splits import FOLD_COLUMNS, build_train_inner_folds
from lst_models.synthetic_control import (
    CLOSED_HOLDOUT_TEST_START,
    TRAIN_END_EXCLUSIVE,
    assert_train_domain_only,
)
from lst_models.windows import (
    build_window_dataset,
    cap_indices,
    fold_indices,
    materialize_window_matrix,
    require_recorded_fold_hash_parity,
    sample_id_hash,
    validate_rebuilt_candidate_counts,
)


STAGE_NAME = "v2_band_horizon_sensitivity"
REGISTRY_BASELINES = (
    "stratified_dummy_train_prior",
    "majority_train_prior",
    "constant_up",
    "constant_down",
)
REQUIRED_BHS_ARTIFACTS = [
    "run_manifest.json",
    "artifact_inventory.csv",
    "bhs_trial_ledger.csv",
    "bhs_cell_summary.csv",
    "bhs_cell_eligibility.csv",
    "bhs_fold_manifest.csv",
    "bhs_baseline_control_summary.csv",
    "bhs_reading_readout.json",
]

TRIAL_LEDGER_COLUMNS = [
    "trial_id", "cell_id", "horizon_k", "no_trade_band_bps", "cell_axis",
    "is_frozen_cell", "candidate_id", "feature_set", "feature_columns_json",
    "window_size", "model_family", "probe_id", "hpo_profile_id",
    "hpo_profile_params_json", "fold_id", "seed", "fit_status",
    "n_train_samples", "n_eval_samples", "train_sample_id_hash",
    "eval_sample_id_hash", "sample_id_hash", "baseline_id", "baseline_fit_status",
    "baseline_macro_f1", "baseline_balanced_accuracy", "baseline_accuracy",
    "baseline_roc_auc", "baseline_mcc", "macro_f1", "balanced_accuracy",
    "accuracy", "roc_auc", "mcc", "delta_macro_f1_vs_baseline",
    "delta_balanced_accuracy_vs_baseline", "positive_ticker_count",
    "ticker_delta_macro_f1_json", "block_delta_macro_f1_json",
    "requested_device", "resolved_device", "device_fallback_reason",
    "best_iteration", "early_stopping_source", "early_stopping_used",
    "early_stopping_reason", "early_stopping_train_sample_id_hash",
    "early_stopping_eval_sample_id_hash", "error_message",
]

BASELINE_CONTROL_COLUMNS = [
    "cell_id", "horizon_k", "no_trade_band_bps", "candidate_id", "fold_id",
    "seed", "baseline_id", "fit_status", "n_train_samples", "n_eval_samples",
    "train_sample_id_hash", "eval_sample_id_hash", "sample_id_hash", "macro_f1",
    "balanced_accuracy", "accuracy", "roc_auc", "mcc", "error_message",
]

CELL_SUMMARY_COLUMNS = [
    "cell_id", "horizon_k", "no_trade_band_bps", "cell_axis", "is_frozen_cell",
    "expected_rows", "completed_rows", "failed_rows",
    "mean_delta_macro_f1_vs_stratified_dummy_train_prior",
    "lcb_delta_macro_f1_vs_stratified_dummy_train_prior", "mean_sign",
    "positive_sign_rows", "negative_sign_rows", "zero_sign_rows",
    "mean_dummy_macro_f1", "min_positive_ticker_count",
    "mean_positive_ticker_count", "n_eligible_label_rows", "n_window_rows",
    "up_prior",
]

ELIGIBILITY_COLUMNS = [
    "cell_id", "horizon_k", "no_trade_band_bps", "cell_axis", "is_frozen_cell",
    "n_bar_rows", "n_eligible_label_rows", "n_window_rows",
    "n_invalid_no_trade_band", "n_invalid_missing_future",
    "n_invalid_cross_trading_day", "n_invalid_irregular_horizon",
    "n_invalid_cross_split", "up_rows", "down_rows", "up_prior",
    "n_trading_days", "n_eligible_by_ticker_json", "n_window_rows_by_ticker_json",
    "window_dataset_sample_id_hash", "events_identity_sha256",
    "frozen_cell_event_parity",
]

FOLD_MANIFEST_COLUMNS = ["cell_id", *FOLD_COLUMNS]


@dataclass(frozen=True)
class BandHorizonSensitivityResult:
    output_dir: Path
    run_manifest: Path
    artifact_inventory: Path
    trial_ledger: Path
    cell_summary: Path
    cell_eligibility: Path
    fold_manifest: Path
    baseline_control_summary: Path
    reading_readout: Path


def run_stage(config: Mapping[str, Any]) -> BandHorizonSensitivityResult:
    cells = _validate_config(config)
    outputs = require_mapping(config["outputs"], "outputs")
    context = load_robustness_inputs(config, stage_label=STAGE_NAME)
    profile = resolve_frozen_tcn_profile(config, stage_label=STAGE_NAME)
    _enforce_budget(config, cells)

    run_id = resolve_run_id_or_new(outputs.get("run_id"), stage_label=STAGE_NAME)
    output_dir = Path(str(outputs["output_dir"])) / run_id
    output_dir.mkdir(parents=True, exist_ok=False)

    trial_rows, baseline_rows, eligibility_rows, fold_rows = _run_all_cells(
        config, context, profile, cells, run_id=run_id
    )
    trial_ledger = pd.DataFrame(trial_rows, columns=TRIAL_LEDGER_COLUMNS)
    reading = band_horizon_reading(trial_ledger, cells)
    cell_summary = _build_cell_summary(reading, eligibility_rows)

    paths: dict[str, Path] = {}
    paths["trial_ledger"] = output_dir / _output_name(outputs, "trial_ledger", "bhs_trial_ledger.csv")
    trial_ledger.to_csv(paths["trial_ledger"], index=False)
    paths["cell_summary"] = output_dir / _output_name(outputs, "cell_summary", "bhs_cell_summary.csv")
    cell_summary.to_csv(paths["cell_summary"], index=False)
    paths["cell_eligibility"] = output_dir / _output_name(
        outputs, "cell_eligibility", "bhs_cell_eligibility.csv"
    )
    pd.DataFrame(eligibility_rows, columns=ELIGIBILITY_COLUMNS).to_csv(
        paths["cell_eligibility"], index=False
    )
    paths["fold_manifest"] = output_dir / _output_name(outputs, "fold_manifest", "bhs_fold_manifest.csv")
    pd.DataFrame(fold_rows, columns=FOLD_MANIFEST_COLUMNS).to_csv(paths["fold_manifest"], index=False)
    paths["baseline_control_summary"] = output_dir / _output_name(
        outputs, "baseline_control_summary", "bhs_baseline_control_summary.csv"
    )
    pd.DataFrame(baseline_rows, columns=BASELINE_CONTROL_COLUMNS).to_csv(
        paths["baseline_control_summary"], index=False
    )
    prefix = _output_name(outputs, "per_cell_trials_prefix", "bhs_trials_")
    for cell in cells:
        cell_path = output_dir / f"{prefix}{cell['cell_id']}.csv"
        trial_ledger.loc[trial_ledger["cell_id"].astype(str).eq(cell["cell_id"])].to_csv(
            cell_path, index=False
        )
        paths[f"per_cell_trials_{cell['cell_id']}"] = cell_path
    reading_path = write_json(
        output_dir / _output_name(outputs, "reading_readout", "bhs_reading_readout.json"),
        reading,
    )
    manifest_path = _write_run_manifest(
        config, context, profile, cells, trial_ledger, reading, output_dir, run_id,
        output_paths={**paths, "reading_readout": reading_path},
    )
    inventory_path = write_artifact_inventory(
        output_dir, {"run_manifest": manifest_path, "reading_readout": reading_path, **paths}
    )
    return BandHorizonSensitivityResult(
        output_dir=output_dir,
        run_manifest=manifest_path,
        artifact_inventory=inventory_path,
        trial_ledger=paths["trial_ledger"],
        cell_summary=paths["cell_summary"],
        cell_eligibility=paths["cell_eligibility"],
        fold_manifest=paths["fold_manifest"],
        baseline_control_summary=paths["baseline_control_summary"],
        reading_readout=reading_path,
    )


def _validate_config(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    if config.get("stage_name") != STAGE_NAME:
        raise ValueError(f"expected {STAGE_NAME} config, got {config.get('stage_name')!r}")
    if config.get("scope") != "validation_only":
        raise ValueError(f"expected validation_only scope, got {config.get('scope')!r}")
    if config.get("holdout_test_contact") is not False:
        raise ValueError(f"{STAGE_NAME} requires holdout_test_contact=false")
    if config.get("train_domain_only") is not True:
        raise ValueError(f"{STAGE_NAME} requires train_domain_only=true")
    if config.get("sensitivity_scan_no_cell_selected") is not True:
        raise ValueError(f"{STAGE_NAME} requires sensitivity_scan_no_cell_selected=true")

    inputs = require_mapping(config["inputs"], "inputs")
    for key in ("stage00_run_id", "stage01_run_id", "stage02_run_id"):
        if not inputs.get(key):
            raise ValueError(f"{STAGE_NAME} config requires inputs.{key}")

    label_scan = require_mapping(config["label_scan"], "label_scan")
    frozen_cell = require_mapping(label_scan["frozen_cell"], "label_scan.frozen_cell")
    if int(frozen_cell["horizon_k"]) != FROZEN_HORIZON_K or float(
        frozen_cell["no_trade_band_bps"]
    ) != FROZEN_BAND_BPS:
        raise ValueError(
            f"label_scan.frozen_cell must be ({FROZEN_HORIZON_K}, {FROZEN_BAND_BPS}), got "
            f"({frozen_cell.get('horizon_k')!r}, {frozen_cell.get('no_trade_band_bps')!r})"
        )
    cells = validate_cell_specs(label_scan["cells"])

    train_inner = require_mapping(config["train_inner"], "train_inner")
    if train_inner.get("official_validation_for_selection") is not False:
        raise ValueError(f"{STAGE_NAME} must declare official_validation_for_selection=false")
    if int(train_inner["n_folds"]) < 1:
        raise ValueError("train_inner.n_folds must be at least 1")
    seeds = train_inner.get("seeds")
    if not isinstance(seeds, list) or not seeds:
        raise ValueError("train_inner.seeds must be a non-empty list")

    model = require_mapping(config["model"], "model")
    if str(model.get("family")) != "tcn" or str(model.get("probe_id")) != "tcn_tiny":
        raise ValueError(
            f"{STAGE_NAME} is scoped to the tcn_tiny frozen primary profile only, got "
            f"family={model.get('family')!r} probe_id={model.get('probe_id')!r}"
        )
    reading_rules = require_mapping(config["reading_rules"], "reading_rules")
    if reading_rules.get("cells_are_never_ranked") is not True:
        raise ValueError(f"{STAGE_NAME} requires reading_rules.cells_are_never_ranked=true")
    if reading_rules.get("no_alternative_cell_recommended") is not True:
        raise ValueError(
            f"{STAGE_NAME} requires reading_rules.no_alternative_cell_recommended=true"
        )
    if str(reading_rules.get("primary_baseline")) != "stratified_dummy_train_prior":
        raise ValueError(
            f"{STAGE_NAME} requires reading_rules.primary_baseline=stratified_dummy_train_prior"
        )
    return cells


def _output_name(outputs: Mapping[str, Any], key: str, default: str) -> str:
    return str(outputs.get(key, default))


def _enforce_budget(config: Mapping[str, Any], cells: list[dict[str, Any]]) -> None:
    train_inner = require_mapping(config["train_inner"], "train_inner")
    planned = len(cells) * int(train_inner["n_folds"]) * len(train_inner["seeds"])
    cap = int(require_mapping(config["budget"], "budget")["max_planned_fit_rows"])
    if planned > cap:
        raise ValueError(f"{STAGE_NAME} planned fit rows {planned} exceed budget cap {cap}")


def _run_all_cells(
    config: Mapping[str, Any],
    context: RobustnessInputs,
    profile: Mapping[str, Any],
    cells: list[dict[str, Any]],
    *,
    run_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    candidate = context.candidate
    feature_columns = tuple(str(column) for column in candidate["feature_columns"])
    window_size = int(candidate["window_size"])
    n_folds = int(config["train_inner"]["n_folds"])
    expected_overlap = int(config["train_inner"].get("event_overlap_count_required", 0))

    trial_rows: list[dict[str, Any]] = []
    baseline_rows: list[dict[str, Any]] = []
    eligibility_rows: list[dict[str, Any]] = []
    fold_manifest_rows: list[dict[str, Any]] = []

    for cell_index, cell in enumerate(cells):
        events, cell_profile = rebuild_cell_events(
            context.train_bars,
            horizon_k=int(cell["horizon_k"]),
            band_bps=float(cell["no_trade_band_bps"]),
        )
        assert_train_domain_only(
            events, ["target_timestamp", "horizon_end_timestamp"],
            stage_label=f"{STAGE_NAME} {cell['cell_id']} eligible events",
        )
        parity = "not_applicable_rebuilt_labels"
        if bool(cell["is_frozen_cell"]):
            require_frozen_cell_event_parity(
                events, context.frozen_train_events,
                stage_label=f"{STAGE_NAME} frozen cell {cell['cell_id']}",
            )
            parity = "passed_matches_stage00_event_index"
        folds = build_train_inner_folds(events, n_folds)
        if not folds["event_overlap_count"].eq(expected_overlap).all():
            raise ValueError(f"{STAGE_NAME} {cell['cell_id']} train-inner fold overlap check failed")
        max_eval_end = pd.to_datetime(folds["eval_end_exclusive"]).max()
        if max_eval_end >= TRAIN_END_EXCLUSIVE + pd.Timedelta(days=1):
            raise ValueError(
                f"{STAGE_NAME} blocked: {cell['cell_id']} fold eval_end_exclusive "
                f"{max_eval_end.isoformat()} reaches past train_end_exclusive "
                f"{TRAIN_END_EXCLUSIVE.date().isoformat()}"
            )
        for fold_record in folds.to_dict(orient="records"):
            fold_manifest_rows.append({"cell_id": cell["cell_id"], **fold_record})

        dataset = build_window_dataset(
            context.feature_frame, events,
            feature_set=str(candidate["feature_set"]),
            feature_columns=feature_columns,
            window_size=window_size,
        )
        if dataset.metadata.empty:
            raise ValueError(f"{STAGE_NAME} produced no windowed rows for {cell['cell_id']}")
        assert_train_domain_only(
            dataset.metadata, ["target_timestamp"],
            stage_label=f"{STAGE_NAME} {cell['cell_id']} window metadata",
        )
        if bool(cell["is_frozen_cell"]):
            validate_rebuilt_candidate_counts(candidate, dataset, context.stage01_summary)
        eligibility_rows.append(
            {
                "cell_id": cell["cell_id"],
                "cell_axis": cell["cell_axis"],
                "is_frozen_cell": bool(cell["is_frozen_cell"]),
                **{
                    key: value
                    for key, value in cell_profile.items()
                    if key != "n_eligible_by_ticker"
                },
                "n_window_rows": int(len(dataset.metadata)),
                "n_eligible_by_ticker_json": json.dumps(
                    cell_profile["n_eligible_by_ticker"], sort_keys=True
                ),
                "n_window_rows_by_ticker_json": json.dumps(
                    {
                        str(ticker): int(count)
                        for ticker, count in dataset.metadata.groupby("ticker").size().to_dict().items()
                    },
                    sort_keys=True,
                ),
                "window_dataset_sample_id_hash": sample_id_hash(
                    dataset.metadata["sample_id"].tolist()
                ),
                "events_identity_sha256": events_identity_sha256(events),
                "frozen_cell_event_parity": parity,
            }
        )
        _run_cell_trials(
            config, context, profile, cell, dataset, folds,
            trial_rows=trial_rows, baseline_rows=baseline_rows,
        )
        _maybe_checkpoint(config, run_id=run_id, cells=cells, completed_through=cell_index,
                          trial_rows=trial_rows)

    return trial_rows, baseline_rows, eligibility_rows, fold_manifest_rows


def _run_cell_trials(
    config: Mapping[str, Any],
    context: RobustnessInputs,
    profile: Mapping[str, Any],
    cell: Mapping[str, Any],
    dataset: Any,
    folds: pd.DataFrame,
    *,
    trial_rows: list[dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
) -> None:
    model = require_mapping(config["model"], "model")
    sample_policy = require_mapping(config["sample_policy"], "sample_policy")
    seeds = [int(seed) for seed in config["train_inner"]["seeds"]]
    candidate = context.candidate
    feature_columns = tuple(str(column) for column in candidate["feature_columns"])
    window_size = int(candidate["window_size"])

    for fold in folds.to_dict(orient="records"):
        train_idx, eval_idx = fold_indices(dataset.metadata, fold)
        train_idx = cap_indices(
            dataset.metadata, train_idx, int(sample_policy["max_train_samples_per_fold"])
        )
        eval_idx = cap_indices(
            dataset.metadata, eval_idx, int(sample_policy["max_eval_samples_per_fold"])
        )
        train_meta = dataset.metadata.iloc[train_idx].copy().reset_index(drop=True)
        eval_meta = dataset.metadata.iloc[eval_idx].copy().reset_index(drop=True)
        train_hash = sample_id_hash(train_meta["sample_id"].tolist())
        eval_hash = sample_id_hash(eval_meta["sample_id"].tolist())
        if bool(cell["is_frozen_cell"]):
            require_recorded_fold_hash_parity(
                context.stage02_plan_ledger, str(candidate["candidate_id"]),
                str(fold["fold_id"]), train_hash, eval_hash,
                stage_label=f"{STAGE_NAME} frozen cell {cell['cell_id']}",
            )
        x_train = materialize_window_matrix(dataset, train_idx)
        x_eval = materialize_window_matrix(dataset, eval_idx)
        y_train = train_meta["label"].to_numpy(dtype=int)
        y_eval = eval_meta["label"].to_numpy(dtype=int)
        for seed in seeds:
            baselines = {
                baseline_id: score_registry_baseline(baseline_id, y_train, y_eval, seed)
                for baseline_id in REGISTRY_BASELINES
            }
            for baseline_id, score in baselines.items():
                baseline_rows.append(
                    {
                        "cell_id": cell["cell_id"], "horizon_k": int(cell["horizon_k"]),
                        "no_trade_band_bps": float(cell["no_trade_band_bps"]),
                        "candidate_id": str(candidate["candidate_id"]),
                        "fold_id": str(fold["fold_id"]), "seed": int(seed),
                        "baseline_id": baseline_id, "fit_status": score["fit_status"],
                        "n_train_samples": int(len(train_meta)),
                        "n_eval_samples": int(len(eval_meta)),
                        "train_sample_id_hash": train_hash,
                        "eval_sample_id_hash": eval_hash, "sample_id_hash": eval_hash,
                        "macro_f1": score["macro_f1"],
                        "balanced_accuracy": score["balanced_accuracy"],
                        "accuracy": score["accuracy"], "roc_auc": score["roc_auc"],
                        "mcc": score["mcc"], "error_message": score["error_message"],
                    }
                )
            primary = baselines["stratified_dummy_train_prior"]
            row = _base_trial_row(
                cell=cell, candidate=candidate, model=model, profile=profile, fold=fold,
                seed=seed, feature_columns=feature_columns, n_train=len(train_meta),
                n_eval=len(eval_meta), train_hash=train_hash, eval_hash=eval_hash,
                primary=primary,
            )
            if primary["fit_status"] != "completed_baseline":
                row["fit_status"] = "skipped_baseline_failed"
                row["error_message"] = str(primary["error_message"])
                trial_rows.append(row)
                continue
            outcome = fit_stage_control(
                str(model["probe_id"]), profile, x_train, train_meta, x_eval, config,
                seed, window_size, len(feature_columns),
            )
            row.update(
                {key: outcome.get(key) for key in (
                    "fit_status", "error_message", "best_iteration",
                    "early_stopping_source", "early_stopping_used", "early_stopping_reason",
                    "early_stopping_train_sample_id_hash", "early_stopping_eval_sample_id_hash",
                    "requested_device", "resolved_device", "device_fallback_reason",
                )}
            )
            if outcome.get("fit_status") == "completed":
                predictions = np.asarray(outcome["predictions"], dtype=int)
                scored = score_classifier(y_eval, predictions, y_score=outcome.get("scores"))
                baseline_predictions = np.asarray(primary["predictions"], dtype=int)
                ticker_deltas, positive_count = ticker_delta_macro_f1(
                    eval_meta, predictions, baseline_predictions
                )
                block_deltas = block_delta_macro_f1(eval_meta, predictions, baseline_predictions)
                row.update(scored)
                row["delta_macro_f1_vs_baseline"] = float(scored["macro_f1"] - primary["macro_f1"])
                row["delta_balanced_accuracy_vs_baseline"] = float(
                    scored["balanced_accuracy"] - primary["balanced_accuracy"]
                )
                row["positive_ticker_count"] = int(positive_count)
                row["ticker_delta_macro_f1_json"] = json.dumps(ticker_deltas, sort_keys=True)
                row["block_delta_macro_f1_json"] = json.dumps(block_deltas, sort_keys=True)
            trial_rows.append(row)


def _base_trial_row(
    *, cell: Mapping[str, Any], candidate: Mapping[str, Any], model: Mapping[str, Any],
    profile: Mapping[str, Any], fold: Mapping[str, Any], seed: int,
    feature_columns: tuple[str, ...], n_train: int, n_eval: int, train_hash: str,
    eval_hash: str, primary: Mapping[str, Any],
) -> dict[str, Any]:
    profile_id = str(profile["profile_id"])
    profile_only = {str(key): value for key, value in profile.items() if str(key) != "profile_id"}
    row = {column: pd.NA for column in TRIAL_LEDGER_COLUMNS}
    row.update(
        {
            "trial_id": (
                f"{cell['cell_id']}__{candidate['candidate_id']}__{model['family']}"
                f"__{profile_id}__{fold['fold_id']}__seed{seed}"
            ),
            "cell_id": str(cell["cell_id"]),
            "horizon_k": int(cell["horizon_k"]),
            "no_trade_band_bps": float(cell["no_trade_band_bps"]),
            "cell_axis": str(cell["cell_axis"]),
            "is_frozen_cell": bool(cell["is_frozen_cell"]),
            "candidate_id": str(candidate["candidate_id"]),
            "feature_set": str(candidate["feature_set"]),
            "feature_columns_json": json.dumps(list(feature_columns)),
            "window_size": int(candidate["window_size"]),
            "model_family": str(model["family"]),
            "probe_id": str(model["probe_id"]),
            "hpo_profile_id": profile_id,
            "hpo_profile_params_json": json.dumps(profile_only, sort_keys=True),
            "fold_id": str(fold["fold_id"]),
            "seed": int(seed),
            "fit_status": "not_started",
            "n_train_samples": int(n_train),
            "n_eval_samples": int(n_eval),
            "train_sample_id_hash": train_hash,
            "eval_sample_id_hash": eval_hash,
            "sample_id_hash": eval_hash,
            "baseline_id": "stratified_dummy_train_prior",
            "baseline_fit_status": primary["fit_status"],
            "baseline_macro_f1": primary["macro_f1"],
            "baseline_balanced_accuracy": primary["balanced_accuracy"],
            "baseline_accuracy": primary["accuracy"],
            "baseline_roc_auc": primary["roc_auc"],
            "baseline_mcc": primary["mcc"],
            "ticker_delta_macro_f1_json": "{}",
            "block_delta_macro_f1_json": "{}",
            "error_message": "",
        }
    )
    return row


def _maybe_checkpoint(
    config: Mapping[str, Any], *, run_id: str, cells: list[dict[str, Any]],
    completed_through: int, trial_rows: list[dict[str, Any]],
) -> None:
    checkpointing = require_mapping(config.get("checkpointing", {}), "checkpointing")
    if checkpointing.get("enabled") is not True:
        return
    checkpoint_dir = Path(str(checkpointing["checkpoint_dir"])) / run_id
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    partial_path = checkpoint_dir / "bhs_trial_ledger_partial.csv"
    pd.DataFrame(trial_rows, columns=TRIAL_LEDGER_COLUMNS).to_csv(partial_path, index=False)
    write_incremental_checkpoint(
        checkpoint_dir,
        stage_name=STAGE_NAME,
        run_id=run_id,
        completed_units=[cell["cell_id"] for cell in cells[: completed_through + 1]],
        pending_units=[cell["cell_id"] for cell in cells[completed_through + 1:]],
        required_files=[partial_path.name],
    )


def _build_cell_summary(
    reading: Mapping[str, Any], eligibility_rows: list[dict[str, Any]]
) -> pd.DataFrame:
    eligibility_by_cell = {str(row["cell_id"]): row for row in eligibility_rows}
    rows = []
    for cell_id, record in reading["per_cell"].items():
        eligibility = eligibility_by_cell.get(str(cell_id), {})
        rows.append(
            {
                "cell_id": str(cell_id),
                "horizon_k": int(record["horizon_k"]),
                "no_trade_band_bps": float(record["no_trade_band_bps"]),
                "cell_axis": str(record["cell_axis"]),
                "is_frozen_cell": bool(record["is_frozen_cell"]),
                "expected_rows": int(record["expected_rows"]),
                "completed_rows": int(record["completed_rows"]),
                "failed_rows": int(record["failed_rows"]),
                "mean_delta_macro_f1_vs_stratified_dummy_train_prior": record["mean_delta"],
                "lcb_delta_macro_f1_vs_stratified_dummy_train_prior": record["lcb_delta"],
                "mean_sign": str(record["mean_sign"]),
                "positive_sign_rows": int(record["positive_sign_rows"]),
                "negative_sign_rows": int(record["negative_sign_rows"]),
                "zero_sign_rows": int(record["zero_sign_rows"]),
                "mean_dummy_macro_f1": record["mean_dummy_macro_f1"],
                "min_positive_ticker_count": record["min_positive_ticker_count"],
                "mean_positive_ticker_count": record["mean_positive_ticker_count"],
                "n_eligible_label_rows": eligibility.get("n_eligible_label_rows"),
                "n_window_rows": eligibility.get("n_window_rows"),
                "up_prior": eligibility.get("up_prior"),
            }
        )
    return pd.DataFrame(rows, columns=CELL_SUMMARY_COLUMNS)


def _write_run_manifest(
    config: Mapping[str, Any],
    context: RobustnessInputs,
    profile: Mapping[str, Any],
    cells: list[dict[str, Any]],
    trial_ledger: pd.DataFrame,
    reading: Mapping[str, Any],
    output_dir: Path,
    run_id: str,
    *,
    output_paths: Mapping[str, Path],
) -> Path:
    inputs = require_mapping(config["inputs"], "inputs")
    outputs = require_mapping(config["outputs"], "outputs")
    notebook_path = resolve_repo_path(inputs["notebook_path"])
    events = context.frozen_train_events
    payload = {
        "route": config["route"],
        "stage_name": STAGE_NAME,
        "scope": config["scope"],
        "run_id": run_id,
        "config_sha256": hash_mapping(config),
        "notebook_sha256": hash_file(notebook_path),
        "source_stage00_run_id": inputs["stage00_run_id"],
        "source_stage01_run_id": inputs["stage01_run_id"],
        "source_stage02_run_id": inputs["stage02_run_id"],
        "input_artifacts": [
            str(path)
            for paths in (context.stage00_paths, context.stage01_paths, context.stage02_paths)
            for path in paths.values()
        ],
        "output_artifacts": sorted(path.name for path in output_paths.values()),
        "candidate_id": str(context.candidate["candidate_id"]),
        "model_family": str(config["model"]["family"]),
        "probe_id": str(config["model"]["probe_id"]),
        "hpo_profile_id": str(profile["profile_id"]),
        "label_scan_cells": [
            {
                "cell_id": cell["cell_id"],
                "horizon_k": cell["horizon_k"],
                "no_trade_band_bps": cell["no_trade_band_bps"],
                "cell_axis": cell["cell_axis"],
                "is_frozen_cell": cell["is_frozen_cell"],
            }
            for cell in cells
        ],
        "random_seeds": [int(seed) for seed in config["train_inner"]["seeds"]],
        "planned_fit_rows": int(len(trial_ledger)),
        "completed_fit_rows": int(trial_ledger["fit_status"].astype(str).eq("completed").sum()),
        "reading_outcome": str(reading["overall_outcome"]),
        "raw_file_integrity": raw_manifest_integrity_summary(context.raw_manifest),
        **feature_rebuild_gate_fields(
            context.stage01_manifest,
            source_field="feature_rebuild_code_sha256",
            stage_label=STAGE_NAME,
            current_field="bhs_feature_rebuild_code_sha256",
            legacy_reason="stage01_manifest_field_missing_legacy_run",
        ),
        **aggregate_trial_device_fields(trial_ledger),
        **git_commit_fields(),
        "train_domain_bounds": {
            "train_start": str(context.split_freeze.get("train_start")),
            "train_end_exclusive": TRAIN_END_EXCLUSIVE.date().isoformat(),
            "closed_holdout_test_start": CLOSED_HOLDOUT_TEST_START.date().isoformat(),
            "max_target_timestamp": pd.to_datetime(events["target_timestamp"]).max().isoformat(),
        },
        "train_domain_only": True,
        "sensitivity_scan_no_cell_selected": True,
        "no_cell_preferred": True,
        "no_cell_ranked": True,
        "no_alternative_cell_recommended": True,
        "frozen_protocol_values_unchanged": True,
        "evidence_status": "train_inner_protocol_sensitivity_scan_no_cell_selected",
        "official_validation_contact": False,
        "official_validation_for_selection": False,
        "no_final_model_selected": True,
        "holdout_test_contact": False,
    }
    return write_json(
        output_dir / _output_name(outputs, "manifest", "run_manifest.json"), payload
    )
