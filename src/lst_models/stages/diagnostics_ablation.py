"""Stage 04 diagnostics + train-inner ablation orchestration.

Measure-only diagnostics live in ``lst_models.diagnostics``; control fit
mechanics live in ``lst_models.fitting``. This module owns gates, ledgers,
checkpoints, and artifact/manifest writing only — zero new
official-validation fit-predict events (protocol 04 sections 2-8, 9-14).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from lst_models import diagnostics, fitting
from lst_models.artifacts import (
    feature_rebuild_gate_fields,
    git_commit_fields,
    load_incremental_checkpoint,
    make_run_id,
    read_json_object,
    require_artifacts,
    require_distinct_file_hashes,
    require_run_id_chain,
    require_safety_flags,
    stage04_diagnostics_code_sha256,
    write_artifact_inventory,
    write_incremental_checkpoint,
    write_json,
)
from lst_models.config import hash_file, hash_mapping, require_mapping
from lst_models.data import load_sample_event_index, load_stage01_summary, load_train_bars
from lst_models.device import aggregate_trial_device_fields
from lst_models.features import build_feature_frame
from lst_models.splits import build_train_inner_folds, valid_events_for_split
from lst_models.windows import (
    build_capped_fold_rows,
    build_window_dataset,
    materialize_window_matrix,
    validate_rebuilt_candidate_counts,
)

STAGE04_ROW_SCOPE = "validation_only"
HOLDOUT_BOUNDARY = pd.Timestamp("2017-01-25")
DIAGNOSTIC_FRAME_KEYS = (
    "calibration_summary", "reliability_bins", "risk_coverage_curve",
    "selective_summary", "robustness_slices", "failure_slices",
)
CONTROL_PROBE_BY_ID = {
    "tcn_only": "tcn_tiny", "dlinear_only": "ms_dlinear_only_tiny",
    "last_step_mlp": "last_step_mlp_tiny",
    "last_step_lightgbm_control": "last_step_lightgbm_control",
}
CONTROL_FAMILY = {
    "tcn_only": "tcn", "dlinear_only": "ms_dlinear_only",
    "last_step_mlp": "last_step_mlp", "last_step_lightgbm_control": "lightgbm",
}

REQUIRED_STAGE04_ARTIFACTS = [
    "run_manifest.json", "artifact_inventory.csv",
    "04_calibration_summary.csv", "04_reliability_bins.csv",
    "04_risk_coverage_curve.csv", "04_selective_summary.csv",
    "04_robustness_slices.csv", "04_failure_slices.csv",
    "04_ablation_plan_ledger.csv", "04_ablation_trial_ledger.csv",
    "04_ablation_summary.csv", "04_diagnostics_report.json",
]

ABLATION_PLAN_COLUMNS = [
    "control_id", "probe_id", "candidate_id", "feature_set", "window_size",
    "model_family", "params_source", "params_source_detail", "fold_id", "seed",
    "n_train_rows", "n_eval_rows", "train_sample_id_hash", "eval_sample_id_hash",
    "baseline_ids", "scope",
]
ABLATION_TRIAL_COLUMNS = ABLATION_PLAN_COLUMNS[:-1] + [
    "fit_status", "error_message", "macro_f1", "balanced_accuracy", "accuracy",
    "mcc", "roc_auc", "baseline_macro_f1_stratified_dummy_train_prior",
    "baseline_macro_f1_majority_train_prior",
    "delta_macro_f1_vs_stratified_dummy_train_prior",
    "delta_macro_f1_vs_majority_train_prior", "positive_ticker_count",
    "best_iteration", "early_stopping_source", "early_stopping_used",
    "early_stopping_reason", "early_stopping_train_sample_id_hash",
    "early_stopping_eval_sample_id_hash", "requested_device", "resolved_device",
    "device_fallback_reason", "scope",
]
ABLATION_SUMMARY_COLUMNS = [
    "control_id", "probe_id", "candidate_id", "n_trials", "n_completed",
    "mean_macro_f1", "mean_delta_macro_f1_vs_stratified_dummy_train_prior",
    "min_delta_macro_f1_vs_stratified_dummy_train_prior",
    "mean_delta_macro_f1_vs_majority_train_prior", "positive_ticker_count_mean",
    "reference_primary_family_mean_macro_f1",
    "reference_primary_family_mean_delta_vs_stratified_dummy",
    "gap_to_reference_mean_delta", "scope",
]


@dataclass(frozen=True)
class Stage04Inputs:
    stage_paths: dict[str, dict[str, Path]]
    stage03_decision_record: dict[str, Any]
    stage02_best_params: dict[str, Any]
    stage01_summary: pd.DataFrame
    raw_manifest: dict[str, Any]
    split_freeze: dict[str, Any]
    candidate_entry: dict[str, Any]
    dump: pd.DataFrame
    feature_rebuild_fields: dict[str, Any]
    notebook_path: Path


@dataclass(frozen=True)
class Stage04DataContext:
    dataset: Any
    folds: pd.DataFrame
    fold_rows: dict[tuple[str, int], dict[str, Any]]
    train_labels: np.ndarray
    window_size: int
    n_features: int


@dataclass(frozen=True)
class Stage04Result:
    run_dir: Path
    diagnostics_report_path: Path
    manifest_path: Path


def run_stage(config: Mapping[str, Any]) -> Stage04Result:
    _validate_config(config)
    inputs = _verify_entry_gates(config)
    context = _load_ablation_data_context(config, inputs)
    run_id, resume_rows, completed_controls = _resolve_run_identity(config)
    run_dir = Path(str(require_mapping(config["outputs"], "outputs")["output_dir"])) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    diagnostics_result = diagnostics.run_diagnostics(
        inputs.dump,
        context.train_labels,
        pd.read_csv(inputs.stage_paths["stage03"]["03_same_row_baselines.csv"]),
        pd.read_csv(inputs.stage_paths["stage03"]["03_per_ticker_readout.csv"]),
        require_mapping(config["diagnostics"], "diagnostics"),
    )
    plan_frame = _build_ablation_plan(config, inputs, context)
    _require_plan_within_budget(config, plan_frame)
    trial_frame = _run_ablation_fits(
        config, inputs, context, plan_frame, run_id, resume_rows, completed_controls
    )
    summary_frame = _ablation_summary(config, inputs, trial_frame)

    frames = {
        key: (diagnostics_result[key], getattr(diagnostics, f"{key.upper()}_COLUMNS"))
        for key in DIAGNOSTIC_FRAME_KEYS
    }
    frames["ablation_plan_ledger"] = (plan_frame, ABLATION_PLAN_COLUMNS)
    frames["ablation_trial_ledger"] = (trial_frame, ABLATION_TRIAL_COLUMNS)
    frames["ablation_summary"] = (summary_frame, ABLATION_SUMMARY_COLUMNS)
    return _write_outputs(
        config, inputs, run_dir, run_id, frames, diagnostics_result, trial_frame
    )


def _validate_config(config: Mapping[str, Any]) -> None:
    if str(config.get("stage_name")) != "04_diagnostics_ablation":
        raise ValueError("config stage_name must be 04_diagnostics_ablation")
    if str(config.get("scope")) != STAGE04_ROW_SCOPE:
        raise ValueError("Stage 04 requires scope=validation_only")
    if config.get("holdout_test_contact") is not False:
        raise ValueError("Stage 04 requires holdout_test_contact=false")
    if str(config.get("official_validation_contact")) != "read_frozen_artifacts_only":
        raise ValueError(
            "Stage 04 requires official_validation_contact=read_frozen_artifacts_only"
        )
    if config.get("official_validation_for_selection") is not False:
        raise ValueError("Stage 04 requires official_validation_for_selection=false")
    if int(config.get("new_validation_fit_predict_events", -1)) != 0:
        raise ValueError("Stage 04 requires new_validation_fit_predict_events=0")
    ablation = require_mapping(config["ablation"], "ablation")
    controls = require_mapping(ablation["controls"], "ablation.controls")
    if set(controls) != set(CONTROL_PROBE_BY_ID):
        raise ValueError(
            f"ablation.controls must be exactly {sorted(CONTROL_PROBE_BY_ID)}, "
            f"got {sorted(controls)}"
        )
    for control_id, block in controls.items():
        if str(require_mapping(block, control_id)["probe_id"]) != CONTROL_PROBE_BY_ID[control_id]:
            raise ValueError(f"ablation.controls.{control_id}.probe_id mismatch")
    require_mapping(config["diagnostics"], "diagnostics")
    require_mapping(config["resume"], "resume")


def _verify_entry_gates(config: Mapping[str, Any]) -> Stage04Inputs:
    inputs = require_mapping(config["inputs"], "inputs")
    stage02_run_id = str(inputs["stage02_run_id"])
    if stage02_run_id in [str(v) for v in inputs.get("superseded_stage02_run_ids", [])]:
        raise ValueError(f"Stage 04 blocked: stage02_run_id {stage02_run_id} is superseded")
    paths = {
        stage: require_artifacts(
            Path(str(inputs[f"{stage}_runtime_run_dir"])),
            inputs[f"required_{stage}_artifacts"],
        )
        for stage in ("stage00", "stage01", "stage02", "stage03")
    }
    manifests = {
        stage: read_json_object(paths[stage]["run_manifest.json"]) for stage in paths
    }
    record = read_json_object(paths["stage03"]["03_decision_record.json"])
    if record.get("readout_complete") is not True:
        raise ValueError("Stage 04 blocked: 03_decision_record.json readout_complete is not true")
    ledger = record.get("scoring_event_ledger", [])
    if int(record.get("official_validation_scoring_events", -1)) != len(ledger):
        raise ValueError(
            "Stage 04 blocked: official_validation_scoring_events does not equal the "
            "scoring_event_ledger length"
        )
    require_run_id_chain(
        [
            (
                f"03_decision_record.json source_{stage}_run_id",
                str(inputs[f"{stage}_run_id"]),
                record.get(f"source_{stage}_run_id"),
            )
            for stage in ("stage00", "stage01", "stage02")
        ],
        stage_label="Stage 04",
    )
    require_safety_flags(
        [(f"{stage} run_manifest.json", manifests[stage]) for stage in manifests]
        + [("03_decision_record.json", record)],
        stage_label="Stage 04", field="holdout_test_contact", expected=False,
    )
    require_safety_flags(
        [("stage03 run_manifest.json", manifests["stage03"]), ("03_decision_record.json", record)],
        stage_label="Stage 04", field="official_validation_for_selection", expected=False,
    )
    require_distinct_file_hashes(
        paths["stage02"]["02_hpo_plan_ledger.csv"],
        paths["stage02"]["02_hpo_trial_ledger.csv"],
        blocked_label=(
            "Stage 04 blocked: Stage 02 plan ledger is byte-identical to the trial ledger"
        ),
        reason="a copied plan ledger is the pre-6182508 packaging defect signature",
    )
    diagnostics_config = require_mapping(config["diagnostics"], "diagnostics")
    dump = diagnostics.gate_and_derive_dump(
        pd.read_csv(paths["stage03"]["03_validation_predictions.csv"]),
        expected_seeds=[int(seed) for seed in diagnostics_config["expected_seeds"]],
        expected_rows=diagnostics_config.get("expected_dump_rows"),
        ledger_rows=sum(int(event["n_rows"]) for event in ledger),
        holdout_boundary=HOLDOUT_BOUNDARY,
    )
    return Stage04Inputs(
        stage_paths=paths,
        stage03_decision_record=record,
        stage02_best_params=read_json_object(paths["stage02"]["02_best_params_by_family.json"]),
        stage01_summary=load_stage01_summary(
            paths["stage01"]["01_feature_window_search_summary.csv"]
        ),
        raw_manifest=read_json_object(paths["stage00"]["raw_data_manifest.json"]),
        split_freeze=read_json_object(paths["stage00"]["split_freeze.json"]),
        candidate_entry=_resolve_candidate_entry(config, paths["stage01"]),
        dump=dump,
        feature_rebuild_fields=_feature_rebuild_gate_fields(manifests["stage02"]),
        notebook_path=Path(str(inputs["notebook_path"])),
    )


def _feature_rebuild_gate_fields(stage02_manifest: Mapping[str, Any]) -> dict[str, Any]:
    return feature_rebuild_gate_fields(
        stage02_manifest,
        source_field="stage02_feature_rebuild_code_sha256",
        stage_label="Stage 04",
        current_field="stage04_feature_rebuild_code_sha256",
        legacy_reason="stage02_manifest_field_missing_legacy_run",
    )


def _resolve_candidate_entry(
    config: Mapping[str, Any], stage01_paths: Mapping[str, Path]
) -> dict[str, Any]:
    candidate_id = str(require_mapping(config["ablation"], "ablation")["candidate_input"])
    handoff = read_json_object(stage01_paths["01_candidate_inputs.json"])
    matches = [
        dict(entry)
        for entry in handoff.get("candidate_inputs", [])
        if str(entry.get("candidate_id")) == candidate_id
    ]
    if not matches:
        raise ValueError(
            f"ablation.candidate_input {candidate_id!r} not found in 01_candidate_inputs.json"
        )
    return matches[0]


def _load_ablation_data_context(
    config: Mapping[str, Any], inputs: Stage04Inputs
) -> Stage04DataContext:
    ablation = require_mapping(config["ablation"], "ablation")
    sample_events = load_sample_event_index(
        inputs.stage_paths["stage00"]["sample_event_index.csv"]
    )
    train_events = valid_events_for_split(sample_events, "train")
    bars = load_train_bars(inputs.raw_manifest, inputs.split_freeze, config["inputs"])
    feature_frame = build_feature_frame(bars)
    entry = inputs.candidate_entry
    dataset = build_window_dataset(
        feature_frame,
        train_events,
        feature_set=str(entry["feature_set"]),
        feature_columns=tuple(entry["feature_columns"]),
        window_size=int(entry["window_size"]),
    )
    validate_rebuilt_candidate_counts(entry, dataset, inputs.stage01_summary)
    overlap = set(dataset.metadata["sample_id"].astype(str)) & set(
        inputs.dump["sample_id"].astype(str)
    )
    if overlap:
        raise ValueError(
            f"Stage 04 blocked: {len(overlap)} ablation train rows overlap validation "
            "dump sample_ids"
        )
    folds = build_train_inner_folds(train_events, int(ablation["n_folds"]))
    caps = require_mapping(ablation["hpo_sample_policy"], "ablation.hpo_sample_policy")
    fold_rows = build_capped_fold_rows(
        dataset,
        folds,
        [int(s) for s in ablation["seeds"]],
        max_train_samples=int(caps["max_train_samples_per_fold"]),
        max_eval_samples=int(caps["max_eval_samples_per_fold"]),
        plan_ledger=pd.read_csv(inputs.stage_paths["stage02"]["02_hpo_plan_ledger.csv"]),
        candidate_id=str(entry["candidate_id"]),
        stage_label="Stage 04",
    )
    return Stage04DataContext(
        dataset=dataset,
        folds=folds,
        fold_rows=fold_rows,
        train_labels=dataset.metadata["label"].to_numpy(dtype=int),
        window_size=int(entry["window_size"]),
        n_features=len(tuple(entry["feature_columns"])),
    )


def _resolve_run_identity(
    config: Mapping[str, Any],
) -> tuple[str, list[dict[str, Any]], list[str]]:
    resume = require_mapping(config["resume"], "resume")
    outputs = require_mapping(config["outputs"], "outputs")
    if not bool(resume.get("enabled")):
        return str(outputs.get("run_id") or make_run_id()), [], []
    run_id = str(resume.get("run_id") or "")
    checkpoint_dir = Path(str(resume.get("checkpoint_dir") or ""))
    manifest = load_incremental_checkpoint(checkpoint_dir, expected_run_id=run_id)
    partial = pd.read_csv(checkpoint_dir / "04_ablation_trial_ledger_partial.csv")
    return run_id, partial.to_dict(orient="records"), [
        str(control) for control in manifest.get("completed_units", [])
    ]


def _resolve_control_profile(
    control_id: str, block: Mapping[str, Any], inputs: Stage04Inputs
) -> tuple[dict[str, Any], str]:
    return fitting.resolve_control_profile(
        control_id,
        block,
        inputs.stage03_decision_record,
        require_mapping(
            inputs.stage02_best_params.get("best_params_by_family", {}), "best_params_by_family"
        ),
    )


def _build_ablation_plan(
    config: Mapping[str, Any], inputs: Stage04Inputs, context: Stage04DataContext
) -> pd.DataFrame:
    ablation = require_mapping(config["ablation"], "ablation")
    controls = require_mapping(ablation["controls"], "ablation.controls")
    baseline_ids = ",".join(
        str(name)
        for name in require_mapping(ablation["same_row_baselines"], "same_row_baselines")["mandatory"]
    )
    entry = inputs.candidate_entry
    rows: list[dict[str, Any]] = []
    for control_id in CONTROL_PROBE_BY_ID:
        block = require_mapping(controls[control_id], control_id)
        _, detail = _resolve_control_profile(control_id, block, inputs)
        for (fold_id, seed), fold_data in context.fold_rows.items():
            rows.append(
                {
                    "control_id": control_id, "probe_id": CONTROL_PROBE_BY_ID[control_id],
                    "candidate_id": str(entry["candidate_id"]),
                    "feature_set": str(entry["feature_set"]),
                    "window_size": int(entry["window_size"]),
                    "model_family": CONTROL_FAMILY[control_id],
                    "params_source": str(block["params_source"]),
                    "params_source_detail": detail, "fold_id": fold_id, "seed": seed,
                    "n_train_rows": int(len(fold_data["train_idx"])),
                    "n_eval_rows": int(len(fold_data["eval_idx"])),
                    "train_sample_id_hash": fold_data["train_sample_id_hash"],
                    "eval_sample_id_hash": fold_data["eval_sample_id_hash"],
                    "baseline_ids": baseline_ids, "scope": STAGE04_ROW_SCOPE,
                }
            )
    return pd.DataFrame(rows)[ABLATION_PLAN_COLUMNS]


def _require_plan_within_budget(config: Mapping[str, Any], plan_frame: pd.DataFrame) -> None:
    cap = int(require_mapping(config["ablation"], "ablation")["budget"]["max_ablation_plan_rows"])
    if len(plan_frame) > cap:
        raise ValueError(
            f"Stage 04 ablation plan has {len(plan_frame)} rows, above the predeclared "
            f"budget cap {cap}"
        )


def _run_ablation_fits(
    config: Mapping[str, Any],
    inputs: Stage04Inputs,
    context: Stage04DataContext,
    plan_frame: pd.DataFrame,
    run_id: str,
    resume_rows: list[dict[str, Any]],
    completed_controls: list[str],
) -> pd.DataFrame:
    ablation = require_mapping(config["ablation"], "ablation")
    controls = list(CONTROL_PROBE_BY_ID)
    trial_rows: list[dict[str, Any]] = list(resume_rows)
    done_controls = list(completed_controls)
    checkpointing = require_mapping(config.get("checkpointing", {}), "checkpointing")
    for control_id in controls:
        if control_id in done_controls:
            continue
        block = require_mapping(ablation["controls"][control_id], control_id)
        params, _ = _resolve_control_profile(control_id, block, inputs)
        for plan_row in plan_frame.loc[plan_frame["control_id"].eq(control_id)].to_dict(
            orient="records"
        ):
            fold_data = context.fold_rows[(str(plan_row["fold_id"]), int(plan_row["seed"]))]
            outcome = _fit_control(control_id, params, plan_row, fold_data, context, config)
            trial_rows.append({**plan_row, **outcome, "scope": STAGE04_ROW_SCOPE})
            print(
                f"stage04 ablation {control_id} {plan_row['fold_id']} seed {plan_row['seed']}: "
                f"{outcome.get('fit_status')}"
            )
        done_controls.append(control_id)
        if bool(checkpointing.get("enabled")) and bool(
            checkpointing.get("checkpoint_after_each_control")
        ):
            _write_control_checkpoint(checkpointing, run_id, done_controls, controls, trial_rows)
    frame = pd.DataFrame(trial_rows)
    for column in ABLATION_TRIAL_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA
    return frame[ABLATION_TRIAL_COLUMNS]


def _fit_control(
    control_id: str,
    params: Mapping[str, Any],
    plan_row: Mapping[str, Any],
    fold_data: Mapping[str, Any],
    context: Stage04DataContext,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    return fitting.fit_and_score_control_trial(
        CONTROL_PROBE_BY_ID[control_id],
        {"profile_id": str(plan_row["params_source_detail"]), **dict(params)},
        materialize_window_matrix(context.dataset, fold_data["train_idx"]),
        context.dataset.metadata.iloc[fold_data["train_idx"]].reset_index(drop=True),
        materialize_window_matrix(context.dataset, fold_data["eval_idx"]),
        context.dataset.metadata.iloc[fold_data["eval_idx"]].reset_index(drop=True),
        config,
        int(plan_row["seed"]),
        context.window_size,
        context.n_features,
    )


def _write_control_checkpoint(
    checkpointing: Mapping[str, Any],
    run_id: str,
    done_controls: list[str],
    all_controls: list[str],
    trial_rows: list[dict[str, Any]],
) -> None:
    checkpoint_dir = Path(str(checkpointing["checkpoint_dir"])) / run_id
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(trial_rows).to_csv(
        checkpoint_dir / "04_ablation_trial_ledger_partial.csv", index=False
    )
    write_incremental_checkpoint(
        checkpoint_dir,
        stage_name="04_diagnostics_ablation",
        run_id=run_id,
        completed_units=list(done_controls),
        pending_units=[c for c in all_controls if c not in done_controls],
        required_files=["checkpoint_manifest.json", "04_ablation_trial_ledger_partial.csv"],
    )


def _completed_stat(completed: pd.DataFrame, column: str, statistic: str = "mean") -> float:
    if not len(completed):
        return np.nan
    series = completed[column].astype(float)
    return float(series.min() if statistic == "min" else series.mean())


def _ablation_summary(
    config: Mapping[str, Any], inputs: Stage04Inputs, trial_frame: pd.DataFrame
) -> pd.DataFrame:
    reference = _reference_rows(config, inputs)
    reference_macro = float(reference["macro_f1"].astype(float).mean())
    reference_delta = float(
        reference["delta_macro_f1_vs_stratified_dummy_train_prior"].astype(float).mean()
    )
    delta_col = "delta_macro_f1_vs_stratified_dummy_train_prior"
    rows: list[dict[str, Any]] = []
    for control_id in CONTROL_PROBE_BY_ID:
        control_rows = trial_frame.loc[trial_frame["control_id"].eq(control_id)]
        completed = control_rows.loc[control_rows["fit_status"].eq("completed")]
        mean_delta = _completed_stat(completed, delta_col)
        rows.append(
            {
                "control_id": control_id,
                "probe_id": CONTROL_PROBE_BY_ID[control_id],
                "candidate_id": str(config["ablation"]["candidate_input"]),
                "n_trials": int(len(control_rows)),
                "n_completed": int(len(completed)),
                "mean_macro_f1": _completed_stat(completed, "macro_f1"),
                "mean_delta_macro_f1_vs_stratified_dummy_train_prior": mean_delta,
                "min_delta_macro_f1_vs_stratified_dummy_train_prior": _completed_stat(
                    completed, delta_col, "min"
                ),
                "mean_delta_macro_f1_vs_majority_train_prior": _completed_stat(
                    completed, "delta_macro_f1_vs_majority_train_prior"
                ),
                "positive_ticker_count_mean": _completed_stat(completed, "positive_ticker_count"),
                "reference_primary_family_mean_macro_f1": reference_macro,
                "reference_primary_family_mean_delta_vs_stratified_dummy": reference_delta,
                "gap_to_reference_mean_delta": (
                    mean_delta - reference_delta if not np.isnan(mean_delta) else np.nan
                ),
                "scope": STAGE04_ROW_SCOPE,
            }
        )
    return pd.DataFrame(rows)[ABLATION_SUMMARY_COLUMNS]


def _reference_rows(config: Mapping[str, Any], inputs: Stage04Inputs) -> pd.DataFrame:
    reference = require_mapping(config["ablation"], "ablation")["reference_rows"]
    trial_ledger = pd.read_csv(inputs.stage_paths["stage02"]["02_hpo_trial_ledger.csv"])
    rows = trial_ledger.loc[
        trial_ledger["candidate_id"].astype(str).eq(str(reference["candidate_id"]))
        & trial_ledger["model_family"].astype(str).eq(str(reference["model_family"]))
        & trial_ledger["hpo_profile_id"].astype(str).eq(str(reference["hpo_profile_id"]))
        & trial_ledger["fit_status"].astype(str).eq("completed")
    ]
    expected = int(reference["expected_row_count"])
    if len(rows) != expected:
        raise ValueError(
            f"Stage 04 reference rows: expected exactly {expected} completed Stage 02 trial "
            f"rows for ({reference['candidate_id']}, {reference['model_family']}, "
            f"{reference['hpo_profile_id']}), found {len(rows)}"
        )
    return rows


def _write_outputs(
    config: Mapping[str, Any],
    inputs: Stage04Inputs,
    run_dir: Path,
    run_id: str,
    frames: Mapping[str, tuple[pd.DataFrame, list[str]]],
    diagnostics_result: Mapping[str, Any],
    trial_frame: pd.DataFrame,
) -> Stage04Result:
    outputs = require_mapping(config["outputs"], "outputs")
    artifact_paths: dict[str, Path] = {}
    for key, (frame, columns) in frames.items():
        if list(frame.columns) != columns:
            raise ValueError(f"Stage 04 output {key} columns drifted from the frozen contract")
        name = str(outputs[key])
        frame.to_csv(run_dir / name, index=False)
        artifact_paths[name] = run_dir / name
    report = _diagnostics_report(config, inputs, diagnostics_result, trial_frame, run_id)
    report_name = str(outputs["diagnostics_report"])
    write_json(run_dir / report_name, report)
    artifact_paths[report_name] = run_dir / report_name
    manifest = _manifest_payload(config, inputs, diagnostics_result, trial_frame, run_id)
    manifest_name = str(outputs.get("manifest", "run_manifest.json"))
    write_json(run_dir / manifest_name, manifest)
    artifact_paths[manifest_name] = run_dir / manifest_name
    write_artifact_inventory(run_dir, artifact_paths)
    missing = [name for name in REQUIRED_STAGE04_ARTIFACTS if not (run_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Stage 04 required artifacts missing after write: {missing} under {run_dir}"
        )
    return Stage04Result(
        run_dir=run_dir,
        diagnostics_report_path=run_dir / report_name,
        manifest_path=run_dir / manifest_name,
    )


def _source_run_id_fields(config: Mapping[str, Any]) -> dict[str, Any]:
    inputs = config["inputs"]
    fields: dict[str, Any] = {
        f"source_{stage}_run_id": str(inputs[f"{stage}_run_id"])
        for stage in ("stage00", "stage01", "stage02", "stage03")
    }
    fields["superseded_stage02_run_ids"] = list(inputs["superseded_stage02_run_ids"])
    return fields


def _diagnostics_report(
    config: Mapping[str, Any],
    inputs: Stage04Inputs,
    diagnostics_result: Mapping[str, Any],
    trial_frame: pd.DataFrame,
    run_id: str,
) -> dict[str, Any]:
    record = inputs.stage03_decision_record
    dump = inputs.dump
    completed = trial_frame.loc[trial_frame["fit_status"].eq("completed")]
    return {
        "route": "lst_models",
        "stage_name": "04_diagnostics_ablation",
        "run_id": run_id,
        "scope": STAGE04_ROW_SCOPE,
        **_source_run_id_fields(config),
        "stage03_decision": str(record.get("decision")),
        "dump_rows_per_seed": {
            str(seed): int(count)
            for seed, count in dump.groupby(dump["seed"].astype(int)).size().items()
        },
        "official_validation_rows_read": int(len(dump)),
        "frozen_prediction_dump_read": True,
        "new_validation_fit_predict_events": 0,
        "official_validation_scoring_events": 0,
        "baseline_reconstruction_status": str(
            diagnostics_result["baseline_reconstruction_status"]
        ),
        "concentration_loo_sign_flips": diagnostics.concentration_summary(
            diagnostics_result["robustness_slices"]
        ),
        "ablation_plan_rows": int(len(trial_frame)),
        "ablation_completed_rows_by_control": {
            control_id: int((completed["control_id"].astype(str) == control_id).sum())
            for control_id in CONTROL_PROBE_BY_ID
        },
        "no_reselection": True,
        "no_final_model_selected": True,
        "holdout_test_contact": False,
        "official_validation_for_selection": False,
        "deferred_items": ["raw_bar_volatility_slice", "shap_permutation_importance"],
    }


def _manifest_payload(
    config: Mapping[str, Any],
    inputs: Stage04Inputs,
    diagnostics_result: Mapping[str, Any],
    trial_frame: pd.DataFrame,
    run_id: str,
) -> dict[str, Any]:
    return {
        "route": "lst_models",
        "stage_name": "04_diagnostics_ablation",
        "run_id": run_id,
        "scope": STAGE04_ROW_SCOPE,
        "holdout_test_contact": False,
        "official_validation_contact": "read_frozen_artifacts_only",
        "official_validation_for_selection": False,
        "new_validation_fit_predict_events": 0,
        "official_validation_scoring_events": 0,
        "official_validation_rows_read": int(len(inputs.dump)),
        "frozen_prediction_dump_read": True,
        "no_final_model_selected": True,
        **_source_run_id_fields(config),
        "stage03_decision": str(inputs.stage03_decision_record.get("decision")),
        "baseline_reconstruction_status": str(
            diagnostics_result["baseline_reconstruction_status"]
        ),
        "stage04_diagnostics_code_sha256": stage04_diagnostics_code_sha256(),
        **inputs.feature_rebuild_fields,
        **aggregate_trial_device_fields(trial_frame),
        **git_commit_fields(),
        "config_sha256": hash_mapping(config),
        "notebook_sha256": (
            hash_file(inputs.notebook_path) if inputs.notebook_path.exists() else None
        ),
        "input_artifacts": [
            str(path)
            for stage in ("stage00", "stage01", "stage02", "stage03")
            for path in inputs.stage_paths[stage].values()
        ],
        "output_artifacts": REQUIRED_STAGE04_ARTIFACTS,
    }
