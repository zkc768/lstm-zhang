"""V2 embargo robustness control: run_stage orchestration (train-domain only).

Reuses the REAL Stage 02 train-inner machinery unchanged (frozen Stage 00
labels at 3.0 bps / 9 bars, the frozen fold boundaries, the exact Stage 02
capped fold rows parity-gated against ``02_hpo_plan_ledger.csv``, registry
baselines, the shared tcn_tiny fit wrapper) and reads the same fitted models
under two predeclared eval-row variants: ``no_embargo`` (the Stage 02 fold
rows exactly as executed) and ``embargo_1day`` (EXACT rule: drop every capped
eval row whose trading day equals the fold's first eval trading day, leaving a
one-trading-day gap after ``train_end_exclusive``; train rows untouched).

Because the embargo removes eval rows only, both variants share the identical
fitted model per (fold, seed): the runner fits ONCE and scores both row sets
from the same predictions, so the variant contrast is free of fit-level
nondeterminism by construction. The same-row stratified dummy is RE-DRAWN per
variant (its draw length differs), per fold, per seed. Everything this stage
writes is train-inner-domain evidence only; it never touches the official
validation split or post-2017 rows, selects no model, and no outcome removes
the paper's limitation (a one-day embargo probes lag-one adjacency only).

Preregistration sidecar:
docs/protocols/v2_embargo_robustness_preregistration_20260701.md
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
from lst_models.fitting import fit_stage_control
from lst_models.metrics import (
    block_delta_macro_f1,
    compute_metric_lcb,
    score_classifier,
    score_registry_baseline,
    ticker_delta_macro_f1,
)
from lst_models.robustness import (
    EMBARGO_RULE_ID,
    EMBARGO_VARIANTS,
    RobustnessInputs,
    embargo_keep_mask,
    embargo_reading,
    first_eval_trading_day,
    load_robustness_inputs,
    resolve_frozen_tcn_profile,
    resolve_run_id_or_new,
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


STAGE_NAME = "v2_embargo_robustness"
REGISTRY_BASELINES = (
    "stratified_dummy_train_prior",
    "majority_train_prior",
    "constant_up",
    "constant_down",
)
REQUIRED_EMB_ARTIFACTS = [
    "run_manifest.json", "artifact_inventory.csv", "emb_trial_ledger.csv",
    "emb_variant_summary.csv", "emb_fold_manifest.csv", "emb_dropped_rows.csv",
    "emb_baseline_control_summary.csv", "emb_reading_readout.json",
]

TRIAL_LEDGER_COLUMNS = [
    "trial_id", "variant_id", "fit_group_id", "embargo_rule_id",
    "first_eval_trading_day", "n_embargo_dropped_rows", "candidate_id",
    "feature_set", "feature_columns_json", "window_size", "model_family",
    "probe_id", "hpo_profile_id", "hpo_profile_params_json", "fold_id", "seed",
    "fit_status", "n_train_samples", "n_eval_samples", "train_sample_id_hash",
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
    "variant_id", "candidate_id", "fold_id", "seed", "baseline_id", "fit_status",
    "n_train_samples", "n_eval_samples", "train_sample_id_hash", "eval_sample_id_hash",
    "sample_id_hash", "macro_f1", "balanced_accuracy", "accuracy", "roc_auc", "mcc",
    "error_message",
]
VARIANT_SUMMARY_COLUMNS = [
    "variant_id", "seed", "expected_rows", "completed_rows", "failed_rows",
    "fold_mean_delta_macro_f1_vs_stratified_dummy_train_prior",
    "lcb_delta_macro_f1_vs_stratified_dummy_train_prior",
    "mean_dummy_macro_f1", "mean_n_eval_samples",
]
FOLD_MANIFEST_COLUMNS = [
    *FOLD_COLUMNS, "first_eval_trading_day", "n_capped_train_rows", "n_capped_eval_rows",
    "n_embargo_retained_rows", "n_embargo_dropped_rows", "train_sample_id_hash",
    "eval_sample_id_hash", "embargo_eval_sample_id_hash",
]
DROPPED_ROW_COLUMNS = [
    "fold_id", "first_eval_trading_day", "sample_id", "ticker", "trading_day",
    "target_timestamp",
]


@dataclass(frozen=True)
class EmbargoRobustnessResult:
    output_dir: Path
    run_manifest: Path
    artifact_inventory: Path
    trial_ledger: Path
    variant_summary: Path
    fold_manifest: Path
    dropped_rows: Path
    baseline_control_summary: Path
    reading_readout: Path


def run_stage(config: Mapping[str, Any]) -> EmbargoRobustnessResult:
    _validate_config(config)
    outputs = require_mapping(config["outputs"], "outputs")
    context = load_robustness_inputs(config, stage_label=STAGE_NAME)
    folds = _build_folds(config, context)
    profile = resolve_frozen_tcn_profile(config, stage_label=STAGE_NAME)
    _enforce_budget(config, folds)

    run_id = resolve_run_id_or_new(outputs.get("run_id"), stage_label=STAGE_NAME)
    output_dir = Path(str(outputs["output_dir"])) / run_id
    output_dir.mkdir(parents=True, exist_ok=False)

    trial_rows, baseline_rows, fold_rows, dropped_rows = _run_all_folds(
        config, context, profile, folds, run_id=run_id
    )
    trial_ledger = pd.DataFrame(trial_rows, columns=TRIAL_LEDGER_COLUMNS)
    seeds = [int(seed) for seed in config["train_inner"]["seeds"]]
    shrinkage = float(require_mapping(config["reading_rules"], "reading_rules")["shrinkage_fraction"])
    reading = embargo_reading(trial_ledger, seeds=seeds, shrinkage_fraction=shrinkage)
    variant_summary = _build_variant_summary(trial_ledger, seeds)

    tables = {
        "trial_ledger": ("emb_trial_ledger.csv", trial_ledger),
        "variant_summary": ("emb_variant_summary.csv", variant_summary),
        "fold_manifest": (
            "emb_fold_manifest.csv", pd.DataFrame(fold_rows, columns=FOLD_MANIFEST_COLUMNS)
        ),
        "dropped_rows": (
            "emb_dropped_rows.csv", pd.DataFrame(dropped_rows, columns=DROPPED_ROW_COLUMNS)
        ),
        "baseline_control_summary": (
            "emb_baseline_control_summary.csv",
            pd.DataFrame(baseline_rows, columns=BASELINE_CONTROL_COLUMNS),
        ),
    }
    paths: dict[str, Path] = {}
    for key, (default_name, frame) in tables.items():
        paths[key] = output_dir / _output_name(outputs, key, default_name)
        frame.to_csv(paths[key], index=False)
    reading_path = write_json(
        output_dir / _output_name(outputs, "reading_readout", "emb_reading_readout.json"),
        reading,
    )
    manifest_path = _write_run_manifest(
        config, context, profile, folds, trial_ledger, reading, output_dir, run_id,
        output_paths={**paths, "reading_readout": reading_path},
    )
    inventory_path = write_artifact_inventory(
        output_dir, {"run_manifest": manifest_path, "reading_readout": reading_path, **paths}
    )
    return EmbargoRobustnessResult(
        output_dir=output_dir,
        run_manifest=manifest_path,
        artifact_inventory=inventory_path,
        trial_ledger=paths["trial_ledger"],
        variant_summary=paths["variant_summary"],
        fold_manifest=paths["fold_manifest"],
        dropped_rows=paths["dropped_rows"],
        baseline_control_summary=paths["baseline_control_summary"],
        reading_readout=reading_path,
    )


def _validate_config(config: Mapping[str, Any]) -> None:
    if config.get("stage_name") != STAGE_NAME:
        raise ValueError(f"expected {STAGE_NAME} config, got {config.get('stage_name')!r}")
    if config.get("scope") != "validation_only":
        raise ValueError(f"expected validation_only scope, got {config.get('scope')!r}")
    if config.get("holdout_test_contact") is not False:
        raise ValueError(f"{STAGE_NAME} requires holdout_test_contact=false")
    if config.get("train_domain_only") is not True:
        raise ValueError(f"{STAGE_NAME} requires train_domain_only=true")

    inputs = require_mapping(config["inputs"], "inputs")
    for key in ("stage00_run_id", "stage01_run_id", "stage02_run_id"):
        if not inputs.get(key):
            raise ValueError(f"{STAGE_NAME} config requires inputs.{key}")

    embargo = require_mapping(config["embargo"], "embargo")
    if str(embargo.get("rule_id")) != EMBARGO_RULE_ID:
        raise ValueError(
            f"embargo.rule_id must be {EMBARGO_RULE_ID!r}, got {embargo.get('rule_id')!r}"
        )
    if int(embargo.get("embargo_trading_days", 0)) != 1:
        raise ValueError(f"{STAGE_NAME} preregisters exactly a one-trading-day embargo")
    if embargo.get("fits_shared_across_variants") is not True:
        raise ValueError(
            f"{STAGE_NAME} requires embargo.fits_shared_across_variants=true (the "
            "embargo changes eval rows only, so both variants share the fitted model)"
        )
    variant_ids = [str(require_mapping(v, "embargo.variant")["variant_id"]) for v in embargo["variants"]]
    if variant_ids != list(EMBARGO_VARIANTS):
        raise ValueError(
            f"embargo.variants must be exactly {list(EMBARGO_VARIANTS)}, got {variant_ids}"
        )

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
    if str(reading_rules.get("primary_baseline")) != "stratified_dummy_train_prior":
        raise ValueError(
            f"{STAGE_NAME} requires reading_rules.primary_baseline=stratified_dummy_train_prior"
        )
    shrinkage = float(reading_rules["shrinkage_fraction"])
    if not 0.0 < shrinkage < 1.0:
        raise ValueError("reading_rules.shrinkage_fraction must be strictly between 0 and 1")


def _output_name(outputs: Mapping[str, Any], key: str, default: str) -> str:
    return str(outputs.get(key, default))


def _build_folds(config: Mapping[str, Any], context: RobustnessInputs) -> pd.DataFrame:
    folds = build_train_inner_folds(
        context.frozen_train_events, int(config["train_inner"]["n_folds"])
    )
    expected_overlap = int(config["train_inner"].get("event_overlap_count_required", 0))
    if not folds["event_overlap_count"].eq(expected_overlap).all():
        raise ValueError(f"{STAGE_NAME} train-inner fold overlap check failed")
    max_eval_end = pd.to_datetime(folds["eval_end_exclusive"]).max()
    if max_eval_end >= TRAIN_END_EXCLUSIVE + pd.Timedelta(days=1):
        raise ValueError(
            f"{STAGE_NAME} blocked: fold eval_end_exclusive {max_eval_end.isoformat()} "
            f"reaches past train_end_exclusive {TRAIN_END_EXCLUSIVE.date().isoformat()}"
        )
    return folds


def _enforce_budget(config: Mapping[str, Any], folds: pd.DataFrame) -> None:
    seeds = require_mapping(config["train_inner"], "train_inner")["seeds"]
    budget = require_mapping(config["budget"], "budget")
    planned_fits = len(folds) * len(seeds)
    planned_readouts = planned_fits * len(EMBARGO_VARIANTS)
    if planned_fits > int(budget["max_planned_fit_rows"]):
        raise ValueError(
            f"{STAGE_NAME} planned fit rows {planned_fits} exceed budget cap "
            f"{int(budget['max_planned_fit_rows'])}"
        )
    if planned_readouts > int(budget["max_readout_rows"]):
        raise ValueError(
            f"{STAGE_NAME} planned readout rows {planned_readouts} exceed budget cap "
            f"{int(budget['max_readout_rows'])}"
        )


def _run_all_folds(
    config: Mapping[str, Any],
    context: RobustnessInputs,
    profile: Mapping[str, Any],
    folds: pd.DataFrame,
    *,
    run_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    model = require_mapping(config["model"], "model")
    sample_policy = require_mapping(config["sample_policy"], "sample_policy")
    seeds = [int(seed) for seed in config["train_inner"]["seeds"]]
    candidate = context.candidate
    feature_columns = tuple(str(column) for column in candidate["feature_columns"])
    window_size = int(candidate["window_size"])

    dataset = build_window_dataset(
        context.feature_frame, context.frozen_train_events,
        feature_set=str(candidate["feature_set"]),
        feature_columns=feature_columns,
        window_size=window_size,
    )
    if dataset.metadata.empty:
        raise ValueError(f"{STAGE_NAME} produced no windowed rows")
    assert_train_domain_only(
        dataset.metadata, ["target_timestamp"], stage_label=f"{STAGE_NAME} window metadata"
    )
    validate_rebuilt_candidate_counts(candidate, dataset, context.stage01_summary)

    trial_rows: list[dict[str, Any]] = []
    baseline_rows: list[dict[str, Any]] = []
    fold_manifest_rows: list[dict[str, Any]] = []
    dropped_row_records: list[dict[str, Any]] = []
    fold_records = folds.to_dict(orient="records")

    for fold_index, fold in enumerate(fold_records):
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
        require_recorded_fold_hash_parity(
            context.stage02_plan_ledger, str(candidate["candidate_id"]),
            str(fold["fold_id"]), train_hash, eval_hash, stage_label=STAGE_NAME,
        )
        first_day = first_eval_trading_day(fold)
        keep_mask = embargo_keep_mask(eval_meta, first_day)
        embargo_meta = eval_meta.loc[keep_mask].copy().reset_index(drop=True)
        if embargo_meta.empty:
            raise ValueError(
                f"{STAGE_NAME} blocked: fold {fold['fold_id']} embargo removed every "
                "capped eval row; the eval fold spans a single trading day"
            )
        embargo_hash = sample_id_hash(embargo_meta["sample_id"].tolist())
        dropped_meta = eval_meta.loc[~keep_mask]
        for record in dropped_meta.to_dict(orient="records"):
            dropped_row_records.append(
                {
                    "fold_id": str(fold["fold_id"]),
                    "first_eval_trading_day": first_day,
                    "sample_id": str(record["sample_id"]),
                    "ticker": str(record["ticker"]),
                    "trading_day": str(record["trading_day"]),
                    "target_timestamp": pd.Timestamp(record["target_timestamp"]).isoformat(),
                }
            )
        fold_manifest_rows.append(
            {
                **fold,
                "first_eval_trading_day": first_day,
                "n_capped_train_rows": int(len(train_meta)),
                "n_capped_eval_rows": int(len(eval_meta)),
                "n_embargo_retained_rows": int(len(embargo_meta)),
                "n_embargo_dropped_rows": int(len(dropped_meta)),
                "train_sample_id_hash": train_hash,
                "eval_sample_id_hash": eval_hash,
                "embargo_eval_sample_id_hash": embargo_hash,
            }
        )
        x_train = materialize_window_matrix(dataset, train_idx)
        x_eval = materialize_window_matrix(dataset, eval_idx)
        y_train = train_meta["label"].to_numpy(dtype=int)
        y_eval = eval_meta["label"].to_numpy(dtype=int)
        variant_frames = {
            "no_embargo": (eval_meta, np.ones(len(eval_meta), dtype=bool), eval_hash, 0),
            "embargo_1day": (embargo_meta, keep_mask, embargo_hash, int(len(dropped_meta))),
        }
        for seed in seeds:
            fit_group_id = f"{fold['fold_id']}__seed{seed}"
            outcome = fit_stage_control(
                str(model["probe_id"]), profile, x_train, train_meta, x_eval, config,
                seed, window_size, len(feature_columns),
            )
            for variant_id in EMBARGO_VARIANTS:
                variant_meta, variant_mask, variant_hash, n_dropped = variant_frames[variant_id]
                y_variant = y_eval[variant_mask]
                baselines = {
                    baseline_id: score_registry_baseline(baseline_id, y_train, y_variant, seed)
                    for baseline_id in REGISTRY_BASELINES
                }
                for baseline_id, score in baselines.items():
                    baseline_rows.append(
                        {
                            "variant_id": variant_id,
                            "candidate_id": str(candidate["candidate_id"]),
                            "fold_id": str(fold["fold_id"]), "seed": int(seed),
                            "baseline_id": baseline_id, "fit_status": score["fit_status"],
                            "n_train_samples": int(len(train_meta)),
                            "n_eval_samples": int(len(variant_meta)),
                            "train_sample_id_hash": train_hash,
                            "eval_sample_id_hash": variant_hash,
                            "sample_id_hash": variant_hash,
                            "macro_f1": score["macro_f1"],
                            "balanced_accuracy": score["balanced_accuracy"],
                            "accuracy": score["accuracy"], "roc_auc": score["roc_auc"],
                            "mcc": score["mcc"], "error_message": score["error_message"],
                        }
                    )
                primary = baselines["stratified_dummy_train_prior"]
                row = _base_trial_row(
                    variant_id=variant_id, fit_group_id=fit_group_id, first_day=first_day,
                    n_dropped=n_dropped, candidate=candidate, model=model, profile=profile,
                    fold=fold, seed=seed, feature_columns=feature_columns,
                    n_train=len(train_meta), n_eval=len(variant_meta),
                    train_hash=train_hash, eval_hash=variant_hash, primary=primary,
                )
                row.update(
                    {key: outcome.get(key) for key in (
                        "fit_status", "error_message", "best_iteration",
                        "early_stopping_source", "early_stopping_used", "early_stopping_reason",
                        "early_stopping_train_sample_id_hash",
                        "early_stopping_eval_sample_id_hash",
                        "requested_device", "resolved_device", "device_fallback_reason",
                    )}
                )
                if primary["fit_status"] != "completed_baseline":
                    row["fit_status"] = "skipped_baseline_failed"
                    row["error_message"] = str(primary["error_message"])
                    trial_rows.append(row)
                    continue
                if outcome.get("fit_status") == "completed":
                    predictions = np.asarray(outcome["predictions"], dtype=int)[variant_mask]
                    scores_arr = outcome.get("scores")
                    variant_scores = (
                        np.asarray(scores_arr, dtype=float)[variant_mask]
                        if scores_arr is not None
                        else None
                    )
                    scored = score_classifier(y_variant, predictions, y_score=variant_scores)
                    baseline_predictions = np.asarray(primary["predictions"], dtype=int)
                    ticker_deltas, positive_count = ticker_delta_macro_f1(
                        variant_meta, predictions, baseline_predictions
                    )
                    block_deltas = block_delta_macro_f1(
                        variant_meta, predictions, baseline_predictions
                    )
                    row.update(scored)
                    row["delta_macro_f1_vs_baseline"] = float(
                        scored["macro_f1"] - primary["macro_f1"]
                    )
                    row["delta_balanced_accuracy_vs_baseline"] = float(
                        scored["balanced_accuracy"] - primary["balanced_accuracy"]
                    )
                    row["positive_ticker_count"] = int(positive_count)
                    row["ticker_delta_macro_f1_json"] = json.dumps(ticker_deltas, sort_keys=True)
                    row["block_delta_macro_f1_json"] = json.dumps(block_deltas, sort_keys=True)
                trial_rows.append(row)
        _maybe_checkpoint(
            config, run_id=run_id, fold_records=fold_records,
            completed_through=fold_index, trial_rows=trial_rows,
        )
    return trial_rows, baseline_rows, fold_manifest_rows, dropped_row_records


def _base_trial_row(
    *, variant_id: str, fit_group_id: str, first_day: str, n_dropped: int,
    candidate: Mapping[str, Any], model: Mapping[str, Any], profile: Mapping[str, Any],
    fold: Mapping[str, Any], seed: int, feature_columns: tuple[str, ...], n_train: int,
    n_eval: int, train_hash: str, eval_hash: str, primary: Mapping[str, Any],
) -> dict[str, Any]:
    profile_id = str(profile["profile_id"])
    profile_only = {str(key): value for key, value in profile.items() if str(key) != "profile_id"}
    row = {column: pd.NA for column in TRIAL_LEDGER_COLUMNS}
    row.update(
        {
            "trial_id": (
                f"{variant_id}__{candidate['candidate_id']}__{model['family']}"
                f"__{profile_id}__{fold['fold_id']}__seed{seed}"
            ),
            "variant_id": str(variant_id),
            "fit_group_id": str(fit_group_id),
            "embargo_rule_id": EMBARGO_RULE_ID,
            "first_eval_trading_day": str(first_day),
            "n_embargo_dropped_rows": int(n_dropped),
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
    config: Mapping[str, Any], *, run_id: str, fold_records: list[dict[str, Any]],
    completed_through: int, trial_rows: list[dict[str, Any]],
) -> None:
    checkpointing = require_mapping(config.get("checkpointing", {}), "checkpointing")
    if checkpointing.get("enabled") is not True:
        return
    checkpoint_dir = Path(str(checkpointing["checkpoint_dir"])) / run_id
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    partial_path = checkpoint_dir / "emb_trial_ledger_partial.csv"
    pd.DataFrame(trial_rows, columns=TRIAL_LEDGER_COLUMNS).to_csv(partial_path, index=False)
    write_incremental_checkpoint(
        checkpoint_dir,
        stage_name=STAGE_NAME,
        run_id=run_id,
        completed_units=[str(fold["fold_id"]) for fold in fold_records[: completed_through + 1]],
        pending_units=[str(fold["fold_id"]) for fold in fold_records[completed_through + 1:]],
        required_files=[partial_path.name],
    )


def _build_variant_summary(trial_ledger: pd.DataFrame, seeds: list[int]) -> pd.DataFrame:
    rows = []
    for variant_id in EMBARGO_VARIANTS:
        variant_rows = trial_ledger.loc[trial_ledger["variant_id"].astype(str).eq(variant_id)]
        seed_means = []
        for seed in seeds:
            seed_rows = variant_rows.loc[variant_rows["seed"].astype(int).eq(int(seed))]
            completed = seed_rows.loc[seed_rows["fit_status"].astype(str).eq("completed")]
            deltas = completed["delta_macro_f1_vs_baseline"].astype(float).to_numpy()
            fold_mean = float(np.mean(deltas)) if len(deltas) else float("nan")
            seed_means.append(fold_mean)
            rows.append(
                {
                    "variant_id": variant_id,
                    "seed": str(int(seed)),
                    "expected_rows": int(len(seed_rows)),
                    "completed_rows": int(len(completed)),
                    "failed_rows": int(len(seed_rows) - len(completed)),
                    "fold_mean_delta_macro_f1_vs_stratified_dummy_train_prior": fold_mean,
                    "lcb_delta_macro_f1_vs_stratified_dummy_train_prior": (
                        compute_metric_lcb(deltas) if len(deltas) else float("nan")
                    ),
                    "mean_dummy_macro_f1": (
                        float(completed["baseline_macro_f1"].astype(float).mean())
                        if len(completed) else float("nan")
                    ),
                    "mean_n_eval_samples": (
                        float(completed["n_eval_samples"].astype(float).mean())
                        if len(completed) else float("nan")
                    ),
                }
            )
        completed_all = variant_rows.loc[variant_rows["fit_status"].astype(str).eq("completed")]
        deltas_all = completed_all["delta_macro_f1_vs_baseline"].astype(float).to_numpy()
        finite_seed_means = [value for value in seed_means if value == value]
        rows.append(
            {
                "variant_id": variant_id,
                "seed": "seed_mean",
                "expected_rows": int(len(variant_rows)),
                "completed_rows": int(len(completed_all)),
                "failed_rows": int(len(variant_rows) - len(completed_all)),
                "fold_mean_delta_macro_f1_vs_stratified_dummy_train_prior": (
                    float(np.mean(finite_seed_means)) if finite_seed_means else float("nan")
                ),
                "lcb_delta_macro_f1_vs_stratified_dummy_train_prior": (
                    compute_metric_lcb(deltas_all) if len(deltas_all) else float("nan")
                ),
                "mean_dummy_macro_f1": (
                    float(completed_all["baseline_macro_f1"].astype(float).mean())
                    if len(completed_all) else float("nan")
                ),
                "mean_n_eval_samples": (
                    float(completed_all["n_eval_samples"].astype(float).mean())
                    if len(completed_all) else float("nan")
                ),
            }
        )
    return pd.DataFrame(rows, columns=VARIANT_SUMMARY_COLUMNS)


def _write_run_manifest(
    config: Mapping[str, Any],
    context: RobustnessInputs,
    profile: Mapping[str, Any],
    folds: pd.DataFrame,
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
    fit_rows = trial_ledger.loc[trial_ledger["variant_id"].astype(str).eq("no_embargo")]
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
        "embargo_rule_id": EMBARGO_RULE_ID,
        "embargo_trading_days": 1,
        "embargo_rule_text": (
            "drop every capped eval row whose trading day equals the fold's first "
            "eval trading day; train rows untouched; one fit per (fold, seed) is "
            "shared by both variants"
        ),
        "fits_shared_across_variants": True,
        "variants": list(EMBARGO_VARIANTS),
        "random_seeds": [int(seed) for seed in config["train_inner"]["seeds"]],
        "planned_fit_rows": int(len(fit_rows)),
        "planned_readout_rows": int(len(trial_ledger)),
        "completed_readout_rows": int(
            trial_ledger["fit_status"].astype(str).eq("completed").sum()
        ),
        "reading_outcome": str(reading["overall_outcome"]),
        "fold_design_sha256": hash_mapping({"folds": folds.to_dict(orient="records")}),
        "raw_file_integrity": raw_manifest_integrity_summary(context.raw_manifest),
        **feature_rebuild_gate_fields(
            context.stage01_manifest,
            source_field="feature_rebuild_code_sha256",
            stage_label=STAGE_NAME,
            current_field="emb_feature_rebuild_code_sha256",
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
        "limitation_removed": False,
        "evidence_status": "train_inner_embargo_robustness_control",
        "official_validation_contact": False,
        "official_validation_for_selection": False,
        "no_final_model_selected": True,
        "holdout_test_contact": False,
    }
    return write_json(
        output_dir / _output_name(outputs, "manifest", "run_manifest.json"), payload
    )
