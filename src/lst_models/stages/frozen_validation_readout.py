"""Stage 03 frozen official-validation readout: fail-closed verification of the
frozen Stage 00 -> 01 -> 02 artifact chain, rebuild of the train/validation
feature and window tensors with the same frozen Stage 01 builders Stage 02
used, and a one-shot official-validation scoring pass under the pre-registered
rules in docs/protocols/03_frozen_validation_readout_protocol.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from lst_models import fitting, metrics
from lst_models.artifacts import (
    feature_rebuild_code_sha256,
    git_commit_fields,
    read_json_object,
    require_artifacts,
    stage03_readout_code_sha256,
    write_artifact_inventory,
    write_json,
)
from lst_models.config import hash_file, hash_mapping, load_yaml, require_mapping, resolve_repo_path
from lst_models.data import (
    load_sample_event_index,
    load_stage01_summary,
    load_train_validation_bars,
)
from lst_models.device import torch_runtime_device_fields
from lst_models.features import build_feature_frame, require_feature_columns
from lst_models.splits import valid_events_for_split
from lst_models.windows import (
    CandidateDataset,
    build_window_dataset,
    materialize_window_matrix,
    sample_id_hash,
    validate_rebuilt_candidate_counts,
)


READOUT_ROW_SCOPE = "validation_only"

# Frozen column contracts. Protocol section 10 carries verbatim copies of
# these constants; doc and code freeze together.
VALIDATION_READOUT_COLUMNS = [
    "candidate_role", "candidate_id", "feature_set", "window_size",
    "model_family", "hpo_profile_id", "seed", "n_refit_train_samples",
    "n_scored_validation_samples", "train_sample_id_hash",
    "eval_sample_id_hash", "macro_f1", "balanced_accuracy", "accuracy",
    "mcc", "roc_auc",
    "precision_down", "recall_down", "f1_down", "support_down",
    "precision_up", "recall_up", "f1_up", "support_up",
    "baseline_macro_f1_stratified_dummy_train_prior",
    "baseline_macro_f1_majority_train_prior",
    "delta_macro_f1_vs_stratified_dummy_train_prior",
    "delta_macro_f1_vs_majority_train_prior",
    "delta_balanced_accuracy_vs_stratified_dummy_train_prior",
    "positive_ticker_count", "best_iteration", "early_stopping_source",
    "early_stopping_used", "early_stopping_reason",
    "early_stopping_train_sample_id_hash", "early_stopping_eval_sample_id_hash",
    "requested_device", "resolved_device", "device_fallback_reason",
    "fit_status", "error_message", "scope",
]
PER_TICKER_READOUT_COLUMNS = [
    "candidate_role", "candidate_id", "seed", "ticker", "n_rows",
    "support_up", "support_down", "macro_f1", "balanced_accuracy",
    "accuracy", "f1_up", "f1_down",
    "delta_macro_f1_vs_stratified_dummy_train_prior",
    "delta_macro_f1_vs_majority_train_prior", "scope",
]
SEED_SUMMARY_COLUMNS = [
    "candidate_role", "candidate_id", "n_seeds",
    "mean_macro_f1", "std_macro_f1",
    "mean_delta_macro_f1_vs_stratified_dummy_train_prior",
    "min_delta_macro_f1_vs_stratified_dummy_train_prior",
    "mean_delta_macro_f1_vs_majority_train_prior",
    "min_delta_macro_f1_vs_majority_train_prior",
    "positive_ticker_count_mean_across_seeds",
    "criteria_delta_vs_stratified_dummy_met",
    "criteria_delta_vs_majority_met", "criteria_ticker_floor_met",
    "met_predeclared_criteria", "scope",
]
SAME_ROW_BASELINE_COLUMNS = [
    "candidate_role", "candidate_id", "seed", "baseline_id", "fit_status",
    "n_train_samples", "n_eval_samples", "train_sample_id_hash",
    "eval_sample_id_hash", "sample_id_hash", "macro_f1",
    "balanced_accuracy", "accuracy", "roc_auc", "mcc", "error_message",
    "scope",
]
VALIDATION_PREDICTION_COLUMNS = [
    "candidate_role", "candidate_id", "model_family", "hpo_profile_id",
    "seed", "sample_id", "ticker", "target_timestamp", "trading_day",
    "y_true", "p_up", "y_pred", "scope",
]

AGGREGATED_READOUT_METRIC_COLUMNS = (
    "macro_f1", "balanced_accuracy", "accuracy", "mcc", "roc_auc",
    "precision_down", "recall_down", "f1_down", "support_down",
    "precision_up", "recall_up", "f1_up", "support_up",
    "baseline_macro_f1_stratified_dummy_train_prior",
    "baseline_macro_f1_majority_train_prior",
    "delta_macro_f1_vs_stratified_dummy_train_prior",
    "delta_macro_f1_vs_majority_train_prior",
    "delta_balanced_accuracy_vs_stratified_dummy_train_prior",
)


@dataclass(frozen=True)
class Stage03Result:
    output_dir: Path
    run_manifest: Path
    artifact_inventory: Path
    decision_record: Path
    validation_readout: Path | None = None
    per_ticker_readout: Path | None = None
    seed_summary: Path | None = None
    same_row_baselines: Path | None = None
    validation_predictions: Path | None = None


@dataclass(frozen=True)
class Stage03Inputs:
    stage00_paths: Mapping[str, Path]
    stage01_paths: Mapping[str, Path]
    stage02_paths: Mapping[str, Path]
    stage00_manifest: Mapping[str, Any]
    stage01_manifest: Mapping[str, Any]
    stage01_handoff: Mapping[str, Any]
    stage01_summary: pd.DataFrame
    stage02_manifest: Mapping[str, Any]
    stage02_handoff: Mapping[str, Any]
    frozen_candidate: Mapping[str, Any]
    raw_manifest: Mapping[str, Any]
    split_freeze: Mapping[str, Any]
    feature_rebuild_fields: Mapping[str, Any]


@dataclass(frozen=True)
class Stage03DataContext:
    inputs: Stage03Inputs
    train_events: pd.DataFrame
    validation_events: pd.DataFrame
    feature_frame: pd.DataFrame


class _MechanicalReadoutFailure(Exception):
    """Protocol section 8 mechanical-trigger signal.

    Raised only for the frozen fallback taxonomy (missing_frozen_artifact,
    schema_or_hash_mismatch, refit_crash_before_any_scoring,
    candidate_not_reconstructable) and only before the first scoring event of
    the failing candidate. Weak metrics never raise this.
    """

    def __init__(self, trigger: str, detail: str) -> None:
        super().__init__(f"{trigger}: {detail}")
        self.trigger = trigger
        self.detail = detail


@dataclass
class _ReadoutLedger:
    """Mutable run state for the one-shot readout: every scoring event,
    refit record, and artifact row is appended here exactly once. The full
    state (minus prediction rows, which live in the partial CSV) is
    serialized into each per-seed checkpoint so an exact-run resume can
    rebuild it without repeating a scoring event."""

    readout_rows: list[dict[str, Any]] = field(default_factory=list)
    per_ticker_rows: list[dict[str, Any]] = field(default_factory=list)
    baseline_rows: list[dict[str, Any]] = field(default_factory=list)
    prediction_frames: list[pd.DataFrame] = field(default_factory=list)
    scoring_events: list[dict[str, Any]] = field(default_factory=list)
    refit_records: list[dict[str, Any]] = field(default_factory=list)
    ticker_deltas: list[dict[str, Any]] = field(default_factory=list)
    readout_complete: bool = True
    incomplete_reason: str = ""
    fallback_activated: bool = False
    fallback_reason: str = ""
    fallback_candidate_failure_reason: str = ""


RUN_ID_PATTERN = re.compile(r"^\d{8}_\d{6}_\d{6}$")

RESUME_REQUIRED_CHECKPOINT_FILES = (
    "checkpoint_manifest.json",
    "03_ledger_state_partial.json",
    "03_validation_readout_partial.csv",
    "03_same_row_baselines_partial.csv",
    "03_validation_predictions_partial.csv",
)


@dataclass(frozen=True)
class _ResumeState:
    """Ledger state recovered from an exact per-seed checkpoint folder."""

    run_id: str
    checkpoint_dir: Path
    candidate_role: str
    ledger: _ReadoutLedger


@dataclass(frozen=True)
class _RolePreparedData:
    """Per-candidate tensors materialized once and reused across seeds."""

    train_meta: pd.DataFrame
    eval_meta: pd.DataFrame
    x_train: np.ndarray
    x_eval: np.ndarray
    feature_columns: tuple[str, ...]
    train_sample_id_hash: str
    eval_sample_id_hash: str


def run_stage(config: Mapping[str, Any]) -> Stage03Result:
    _validate_config(config)
    inputs = _verify_entry_gates(config)

    outputs = require_mapping(config["outputs"], "outputs")
    resume_state = _load_resume_state(config)
    if resume_state is None:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        output_dir = Path(str(outputs["output_dir"])) / run_id
        output_dir.mkdir(parents=True, exist_ok=False)
    else:
        run_id = resume_state.run_id
        output_dir = Path(str(outputs["output_dir"])) / run_id
        output_dir.mkdir(parents=True, exist_ok=True)

    if inputs.stage02_handoff.get("ready_for_stage03") is not True:
        return _write_blocked_result(config, inputs, output_dir)

    data_context = _load_readout_data_context(config, inputs)
    return _execute_readout(
        config=config,
        inputs=inputs,
        data_context=data_context,
        output_dir=output_dir,
        run_id=run_id,
        resume_state=resume_state,
    )


def _validate_config(config: Mapping[str, Any]) -> None:
    if config.get("stage_name") != "03_frozen_validation_readout":
        raise ValueError(f"expected Stage 03 config, got {config.get('stage_name')!r}")
    if config.get("scope") != "validation_only":
        raise ValueError(f"expected validation_only scope, got {config.get('scope')!r}")
    if config.get("holdout_test_contact") is not False:
        raise ValueError("Stage 03 requires holdout_test_contact=false")
    if config.get("official_validation_contact") is not True:
        raise ValueError("Stage 03 requires official_validation_contact=true")
    if config.get("official_validation_for_selection") is not False:
        raise ValueError("Stage 03 requires official_validation_for_selection=false")

    readout = require_mapping(config["readout"], "readout")
    seeds = readout.get("seeds")
    if (
        not isinstance(seeds, list)
        or not seeds
        or not all(isinstance(seed, int) and not isinstance(seed, bool) for seed in seeds)
    ):
        raise ValueError("Stage 03 readout.seeds must be a non-empty list of integers")
    if readout.get("score_each_seed_candidate_exactly_once") is not True:
        raise ValueError("Stage 03 requires readout.score_each_seed_candidate_exactly_once=true")

    criteria = require_mapping(config["predeclared_criteria"], "predeclared_criteria")
    if int(criteria.get("minimum_positive_ticker_count", -1)) < 0:
        raise ValueError(
            "predeclared_criteria.minimum_positive_ticker_count must be non-negative"
        )
    if criteria.get("aggregate") != "mean_over_seeds":
        raise ValueError("predeclared_criteria.aggregate must be mean_over_seeds")

    fallback_policy = require_mapping(config["fallback_policy"], "fallback_policy")
    if fallback_policy.get("after_first_scoring_event") != "never_activate":
        raise ValueError("fallback_policy.after_first_scoring_event must be never_activate")

    inputs = require_mapping(config["inputs"], "inputs")
    stage02_run_id = str(inputs.get("stage02_run_id") or "")
    if not stage02_run_id or "<" in stage02_run_id:
        raise ValueError(
            "fill inputs.stage02_run_id with the superseding Stage 02 run id (roadmap Phase 0.3)"
        )
    superseded = {str(value) for value in inputs.get("superseded_stage02_run_ids", [])}
    if stage02_run_id in superseded:
        raise ValueError(
            f"superseded Stage 02 run id {stage02_run_id!r} must not be pinned as "
            "inputs.stage02_run_id; pin the superseding run id (roadmap Phase 0.3)"
        )


def _output_name(outputs: Mapping[str, Any], key: str, default: str) -> str:
    return str(outputs.get(key, default))


def _load_resume_state(config: Mapping[str, Any]) -> _ResumeState | None:
    """Exact-run resume loader (protocol section 11).

    Fail-closed: requires the exact run id and the exact checkpoint folder
    (whose name must equal the run id, so a parent-directory scan can never
    masquerade as a resume), plus every checkpoint file the ledger rebuild
    needs. Returns None when resume is absent or disabled.
    """
    resume = config.get("resume")
    if resume is None:
        return None
    resume = require_mapping(resume, "resume")
    if resume.get("enabled") is not True:
        return None
    run_id = str(resume.get("run_id") or "")
    if not RUN_ID_PATTERN.match(run_id):
        raise ValueError(
            f"resume.run_id must be an exact Stage 03 run id, got {run_id!r}"
        )
    checkpoint_dir = Path(str(resume.get("checkpoint_dir") or ""))
    if not str(resume.get("checkpoint_dir") or ""):
        raise ValueError("resume.checkpoint_dir must name the exact checkpoint folder")
    if checkpoint_dir.name != run_id:
        raise ValueError(
            "resume.checkpoint_dir must end in the exact resume.run_id "
            f"(no parent-folder scans): {checkpoint_dir} vs run id {run_id!r}"
        )
    missing = [
        checkpoint_dir / name
        for name in RESUME_REQUIRED_CHECKPOINT_FILES
        if not (checkpoint_dir / name).exists()
    ]
    if missing:
        missing_text = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(f"missing required Stage 03 resume checkpoint files:\n{missing_text}")

    manifest = read_json_object(checkpoint_dir / "checkpoint_manifest.json")
    state = read_json_object(checkpoint_dir / "03_ledger_state_partial.json")
    for label, payload in (("checkpoint_manifest.json", manifest), ("03_ledger_state_partial.json", state)):
        if str(payload.get("stage_name")) != str(config["stage_name"]):
            raise ValueError(f"resume {label} stage_name mismatch: {payload.get('stage_name')!r}")
        if str(payload.get("run_id")) != run_id:
            raise ValueError(f"resume {label} run_id mismatch: {payload.get('run_id')!r} != {run_id!r}")

    scoring_events = [dict(event) for event in state.get("scoring_events", [])]
    if not scoring_events:
        raise ValueError(
            "resume checkpoint records zero scoring events; a fresh run (new run id) "
            "is required instead of a resume"
        )
    config_seeds = {int(seed) for seed in require_mapping(config["readout"], "readout")["seeds"]}
    event_seeds = {int(event["seed"]) for event in scoring_events}
    if not event_seeds <= config_seeds:
        raise ValueError(
            f"resume checkpoint seeds {sorted(event_seeds)} are not a subset of "
            f"config readout.seeds {sorted(config_seeds)}"
        )

    prediction_frame = pd.read_csv(checkpoint_dir / "03_validation_predictions_partial.csv")
    ledger = _ReadoutLedger(
        readout_rows=[dict(row) for row in state.get("readout_rows", [])],
        per_ticker_rows=[dict(row) for row in state.get("per_ticker_rows", [])],
        baseline_rows=[dict(row) for row in state.get("baseline_rows", [])],
        prediction_frames=(
            [prediction_frame[VALIDATION_PREDICTION_COLUMNS]] if len(prediction_frame) else []
        ),
        scoring_events=scoring_events,
        refit_records=[dict(record) for record in state.get("refit_records", [])],
        ticker_deltas=[dict(entry) for entry in state.get("ticker_deltas", [])],
        readout_complete=bool(state.get("readout_complete", True)),
        incomplete_reason=str(state.get("incomplete_reason", "")),
        fallback_activated=bool(state.get("fallback_activated", False)),
        fallback_reason=str(state.get("fallback_reason", "")),
        fallback_candidate_failure_reason=str(
            state.get("fallback_candidate_failure_reason", "")
        ),
    )
    candidate_role = str(state.get("candidate_role") or manifest.get("candidate_role") or "")
    if candidate_role not in {"primary", "fallback"}:
        raise ValueError(f"resume checkpoint candidate_role must be primary or fallback, got {candidate_role!r}")
    return _ResumeState(
        run_id=run_id,
        checkpoint_dir=checkpoint_dir,
        candidate_role=candidate_role,
        ledger=ledger,
    )


def _require_resume_candidate_consistency(
    resume_state: _ResumeState, selection: Mapping[str, Any]
) -> None:
    expected = str(selection["candidate_id"])
    for event in resume_state.ledger.scoring_events:
        if str(event.get("candidate_id")) != expected:
            raise ValueError(
                "resume checkpoint scoring events belong to candidate "
                f"{event.get('candidate_id')!r}, but the frozen {resume_state.candidate_role} "
                f"candidate is {expected!r}; resume must target the identical frozen chain"
            )


def _jsonable(value: Any) -> Any:
    """Plain-Python conversion for the ledger-state checkpoint payload, so a
    resume round-trips numerics instead of receiving stringified numpy."""
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def _verify_entry_gates(config: Mapping[str, Any]) -> Stage03Inputs:
    inputs = require_mapping(config["inputs"], "inputs")
    stage00_run_dir = Path(str(inputs["stage00_runtime_run_dir"]))
    stage01_run_dir = Path(str(inputs["stage01_runtime_run_dir"]))
    stage02_run_dir = Path(str(inputs["stage02_runtime_run_dir"]))
    stage00_paths = require_artifacts(stage00_run_dir, inputs["required_stage00_artifacts"])
    stage01_paths = require_artifacts(stage01_run_dir, inputs["required_stage01_artifacts"])
    stage02_paths = require_artifacts(stage02_run_dir, inputs["required_stage02_artifacts"])

    stage00_manifest = read_json_object(stage00_paths["run_manifest.json"])
    raw_manifest = read_json_object(stage00_paths["raw_data_manifest.json"])
    split_freeze = read_json_object(stage00_paths["split_freeze.json"])
    stage01_manifest = read_json_object(stage01_paths["run_manifest.json"])
    stage01_handoff = read_json_object(stage01_paths["01_candidate_inputs.json"])
    stage01_summary = load_stage01_summary(
        stage01_paths["01_feature_window_search_summary.csv"]
    )
    stage02_manifest = read_json_object(stage02_paths["run_manifest.json"])
    stage02_handoff = read_json_object(stage02_paths["02_stage03_handoff.json"])
    frozen_candidate = read_json_object(stage02_paths["02_frozen_candidate.json"])

    _require_plan_ledger_differs_from_trial_ledger(stage02_paths)
    _require_run_id_chain(inputs, stage01_handoff, stage02_manifest, stage02_handoff, frozen_candidate)
    feature_rebuild_fields = _feature_rebuild_gate_fields(stage02_manifest)
    _require_upstream_safety_flags(
        stage00_manifest=stage00_manifest,
        stage01_manifest=stage01_manifest,
        stage02_manifest=stage02_manifest,
        stage01_handoff=stage01_handoff,
        stage02_handoff=stage02_handoff,
        frozen_candidate=frozen_candidate,
    )
    _require_frozen_seed_policy(frozen_candidate, config)
    if stage02_handoff.get("ready_for_stage03") is True:
        _require_ready_handoff_candidates(stage02_handoff)

    return Stage03Inputs(
        stage00_paths=stage00_paths,
        stage01_paths=stage01_paths,
        stage02_paths=stage02_paths,
        stage00_manifest=stage00_manifest,
        stage01_manifest=stage01_manifest,
        stage01_handoff=stage01_handoff,
        stage01_summary=stage01_summary,
        stage02_manifest=stage02_manifest,
        stage02_handoff=stage02_handoff,
        frozen_candidate=frozen_candidate,
        raw_manifest=raw_manifest,
        split_freeze=split_freeze,
        feature_rebuild_fields=feature_rebuild_fields,
    )


def _require_plan_ledger_differs_from_trial_ledger(stage02_paths: Mapping[str, Path]) -> None:
    plan_path = stage02_paths["02_hpo_plan_ledger.csv"]
    trial_path = stage02_paths["02_hpo_trial_ledger.csv"]
    if hash_file(plan_path) == hash_file(trial_path):
        raise ValueError(
            "Stage 03 blocked: Stage 02 plan ledger is byte-identical to the trial ledger "
            f"({plan_path} == {trial_path}); a copied plan ledger is the pre-6182508 "
            "packaging defect signature"
        )


def _require_run_id_chain(
    inputs: Mapping[str, Any],
    stage01_handoff: Mapping[str, Any],
    stage02_manifest: Mapping[str, Any],
    stage02_handoff: Mapping[str, Any],
    frozen_candidate: Mapping[str, Any],
) -> None:
    expected_stage00 = str(inputs["stage00_run_id"])
    expected_stage01 = str(inputs["stage01_run_id"])
    checks = [
        ("01_candidate_inputs.json source_stage00_run_id", expected_stage00, stage01_handoff.get("source_stage00_run_id")),
        ("02_stage03_handoff.json source_stage00_run_id", expected_stage00, stage02_handoff.get("source_stage00_run_id")),
        ("02_stage03_handoff.json source_stage01_run_id", expected_stage01, stage02_handoff.get("source_stage01_run_id")),
        ("stage02 run_manifest.json source_stage01_run_id", expected_stage01, stage02_manifest.get("source_stage01_run_id")),
        ("02_frozen_candidate.json source_stage00_run_id", expected_stage00, frozen_candidate.get("source_stage00_run_id")),
        ("02_frozen_candidate.json source_stage01_run_id", expected_stage01, frozen_candidate.get("source_stage01_run_id")),
    ]
    for field_label, expected, observed in checks:
        if observed is None or str(observed) != expected:
            raise ValueError(
                f"Stage 03 run id chain mismatch: {field_label} expected {expected!r}, "
                f"observed {observed!r}"
            )


def _feature_rebuild_gate_fields(stage02_manifest: Mapping[str, Any]) -> dict[str, Any]:
    current_hash = feature_rebuild_code_sha256()
    source_hash = stage02_manifest.get("stage02_feature_rebuild_code_sha256")
    if source_hash and str(source_hash) != current_hash:
        raise ValueError(
            "Stage 02 feature rebuild code hash does not match current Stage 03 rebuild code: "
            f"{source_hash!r} != {current_hash!r}"
        )
    if source_hash:
        match: bool | None = True
        reason = "matched"
    else:
        match = None
        reason = "stage02_manifest_field_missing_legacy_run"
    return {
        "stage03_feature_rebuild_code_sha256": current_hash,
        "source_stage02_feature_rebuild_code_sha256": source_hash,
        "feature_rebuild_code_match": match,
        "feature_rebuild_code_match_reason": reason,
    }


def _require_upstream_safety_flags(
    *,
    stage00_manifest: Mapping[str, Any],
    stage01_manifest: Mapping[str, Any],
    stage02_manifest: Mapping[str, Any],
    stage01_handoff: Mapping[str, Any],
    stage02_handoff: Mapping[str, Any],
    frozen_candidate: Mapping[str, Any],
) -> None:
    no_holdout_contact = [
        ("stage00 run_manifest.json", stage00_manifest),
        ("stage01 run_manifest.json", stage01_manifest),
        ("stage02 run_manifest.json", stage02_manifest),
        ("01_candidate_inputs.json", stage01_handoff),
        ("02_stage03_handoff.json", stage02_handoff),
        ("02_frozen_candidate.json", frozen_candidate),
    ]
    for label, payload in no_holdout_contact:
        if payload.get("holdout_test_contact") is not False:
            raise ValueError(f"Stage 03 requires {label} holdout_test_contact=false")
    no_validation_selection = [
        ("stage02 run_manifest.json", stage02_manifest),
        ("02_stage03_handoff.json", stage02_handoff),
        ("02_frozen_candidate.json", frozen_candidate),
    ]
    for label, payload in no_validation_selection:
        if payload.get("official_validation_for_selection") is not False:
            raise ValueError(f"Stage 03 requires {label} official_validation_for_selection=false")
    if stage02_handoff.get("no_final_model_selected") is not True:
        raise ValueError("Stage 03 requires 02_stage03_handoff.json no_final_model_selected=true")


def _require_frozen_seed_policy(
    frozen_candidate: Mapping[str, Any], config: Mapping[str, Any]
) -> None:
    seed_policy = require_mapping(
        frozen_candidate.get("seed_policy", {}), "frozen_candidate.seed_policy"
    )
    frozen_seeds = [int(seed) for seed in seed_policy.get("train_inner_seeds", [])]
    config_seeds = [int(seed) for seed in require_mapping(config["readout"], "readout")["seeds"]]
    if frozen_seeds != config_seeds:
        raise ValueError(
            "Stage 03 readout.seeds must equal 02_frozen_candidate.json "
            f"seed_policy.train_inner_seeds: {config_seeds} != {frozen_seeds}"
        )


def _require_ready_handoff_candidates(stage02_handoff: Mapping[str, Any]) -> None:
    if not str(stage02_handoff.get("decision") or ""):
        raise ValueError(
            "02_stage03_handoff.json records ready_for_stage03=true but no decision string"
        )
    for role in ("primary_candidate", "fallback_candidate"):
        candidate = stage02_handoff.get(role)
        if not isinstance(candidate, Mapping):
            raise ValueError(
                f"02_stage03_handoff.json records ready_for_stage03=true but {role} "
                "is not a frozen candidate mapping"
            )


def _load_readout_data_context(
    config: Mapping[str, Any], inputs: Stage03Inputs
) -> Stage03DataContext:
    config_inputs = require_mapping(config["inputs"], "inputs")
    sample_events = load_sample_event_index(
        inputs.stage00_paths["sample_event_index.csv"]
    )
    train_events = valid_events_for_split(sample_events, "train")
    validation_events = valid_events_for_split(sample_events, "validation")
    bars = load_train_validation_bars(inputs.raw_manifest, inputs.split_freeze, config_inputs)
    feature_frame = build_feature_frame(bars)
    return Stage03DataContext(
        inputs=inputs,
        train_events=train_events,
        validation_events=validation_events,
        feature_frame=feature_frame,
    )


def _resolve_candidate_feature_columns(
    candidate_selection: Mapping[str, Any], stage01_handoff: Mapping[str, Any]
) -> tuple[str, ...]:
    candidate_id = str(candidate_selection["candidate_id"])
    for entry in stage01_handoff.get("candidate_inputs", []):
        entry_mapping = require_mapping(entry, "candidate_input")
        if str(entry_mapping.get("candidate_id")) == candidate_id:
            return tuple(str(column) for column in entry_mapping["feature_columns"])
    raise ValueError(
        "Stage 03 cannot resolve feature_columns: 01_candidate_inputs.json has no "
        f"candidate_inputs entry for candidate_id {candidate_id!r}"
    )


def _prepare_candidate_dataset(
    candidate_selection: Mapping[str, Any],
    data_context: Stage03DataContext,
    events: pd.DataFrame,
) -> CandidateDataset:
    feature_columns = _resolve_candidate_feature_columns(
        candidate_selection, data_context.inputs.stage01_handoff
    )
    require_feature_columns(feature_columns, data_context.feature_frame)
    return build_window_dataset(
        data_context.feature_frame,
        events,
        feature_set=str(candidate_selection["feature_set"]),
        feature_columns=feature_columns,
        window_size=int(candidate_selection["window_size"]),
    )


REFIT_EARLY_STOPPING_KEYS = (
    "early_stopping_source",
    "early_stopping_used",
    "early_stopping_reason",
    "early_stopping_train_sample_id_hash",
    "early_stopping_eval_sample_id_hash",
)


def _refit_and_predict(
    family: str,
    profile: Mapping[str, Any],
    x_train: np.ndarray,
    train_meta: pd.DataFrame,
    x_eval: np.ndarray,
    config: Mapping[str, Any],
    seed: int,
    window_size: int,
    n_features: int,
) -> dict[str, Any]:
    """Mechanism-frozen refit dispatch (protocol section 5, decisions D1+D2)."""
    if family not in fitting.PROBE_BY_FAMILY:
        raise ValueError(f"unknown Stage 03 refit model family: {family!r}")
    y_train = train_meta["label"].to_numpy(dtype=int)
    if len(y_train) == 0 or len(x_eval) == 0:
        return {
            "fit_status": "skipped_no_fold_samples",
            "error_message": "refit has no train/eval samples",
        }
    if len(np.unique(y_train)) < 2:
        return {
            "fit_status": "failed_single_class_train",
            "error_message": "refit train labels contain fewer than two classes",
        }
    if family == "lightgbm":
        return _refit_lightgbm_and_predict(profile, x_train, train_meta, x_eval, config, seed)
    return _refit_torch_and_predict(
        family, profile, x_train, train_meta, x_eval, config, seed, window_size, n_features
    )


def _refit_lightgbm_and_predict(
    profile: Mapping[str, Any],
    x_train: np.ndarray,
    train_meta: pd.DataFrame,
    x_eval: np.ndarray,
    config: Mapping[str, Any],
    seed: int,
) -> dict[str, Any]:
    """LightGBM refit with the frozen Stage 02 chronological-tail early stopping.

    The scored official-validation rows (``x_eval``) are never passed as the
    early-stopping ``eval_set``; the tail is carved from the refit rows only.
    """
    try:
        from lightgbm import LGBMClassifier, early_stopping, log_evaluation
    except ModuleNotFoundError as exc:
        return {"fit_status": "failed_dependency_missing", "error_message": str(exc)}

    training_defaults = require_mapping(
        config["lightgbm_training_defaults"], "lightgbm_training_defaults"
    )
    early_rounds = int(training_defaults.get("early_stopping_rounds", 25))
    split = fitting.lightgbm_inner_train_early_stopping_split(
        x_train=x_train,
        y_train=train_meta["label"].to_numpy(dtype=int),
        train_meta=train_meta,
        training_defaults=training_defaults,
        early_rounds=early_rounds,
    )
    callbacks = [log_evaluation(period=0)]
    fit_kwargs: dict[str, Any] = {
        "eval_metric": str(training_defaults.get("eval_metric", "binary_logloss")),
        "callbacks": callbacks,
    }
    if split["early_stopping_used"]:
        callbacks.append(early_stopping(early_rounds, verbose=False))
        fit_kwargs["eval_set"] = [(split["x_stop"], split["y_stop"])]
    model = LGBMClassifier(**fitting.lightgbm_hpo_params(profile), random_state=seed, verbosity=-1)
    try:
        model.fit(split["x_fit"], split["y_fit"], **fit_kwargs)
        predictions = model.predict(x_eval).astype(int)
        scores = model.predict_proba(x_eval)[:, 1].astype(float)
    except (ValueError, RuntimeError, FloatingPointError) as exc:
        return {
            "fit_status": "failed_exception",
            "error_message": f"{type(exc).__name__}: {exc}",
            **{key: split[key] for key in REFIT_EARLY_STOPPING_KEYS},
        }
    return {
        "fit_status": "completed",
        "error_message": "",
        "predictions": predictions,
        "scores": scores,
        "best_iteration": getattr(model, "best_iteration_", None),
        **{key: split[key] for key in REFIT_EARLY_STOPPING_KEYS},
        "requested_device": "cpu",
        "resolved_device": "cpu",
        "device_fallback_reason": "not_gpu_capable_trial",
    }


def _refit_torch_and_predict(
    family: str,
    profile: Mapping[str, Any],
    x_train: np.ndarray,
    train_meta: pd.DataFrame,
    x_eval: np.ndarray,
    config: Mapping[str, Any],
    seed: int,
    window_size: int,
    n_features: int,
) -> dict[str, Any]:
    """Torch-family refit through the shared frozen sequence-probe mechanism."""
    probe_id = fitting.PROBE_BY_FAMILY[family]
    trial_config = fitting.probe_trial_config(config, probe_id, profile)
    try:
        result = fitting.fit_torch_sequence_probe(
            probe_id,
            x_train,
            train_meta["label"].to_numpy(dtype=int),
            x_eval,
            trial_config,
            seed,
            window_size,
            n_features,
            train_meta=train_meta,
        )
    except ModuleNotFoundError as exc:
        return {"fit_status": "failed_dependency_missing", "error_message": str(exc)}
    except (ValueError, RuntimeError, FloatingPointError) as exc:
        if "GPU required" in str(exc) or "CUDA requested" in str(exc):
            raise
        return {"fit_status": "failed_exception", "error_message": f"{type(exc).__name__}: {exc}"}
    return {
        "fit_status": "completed",
        "error_message": "",
        "predictions": result.predictions,
        "scores": result.scores,
        "best_iteration": result.best_iteration,
        "early_stopping_source": result.early_stopping_source,
        "early_stopping_used": result.early_stopping_used,
        "early_stopping_reason": result.early_stopping_reason,
        "early_stopping_train_sample_id_hash": result.early_stopping_train_sample_id_hash,
        "early_stopping_eval_sample_id_hash": result.early_stopping_eval_sample_id_hash,
        "requested_device": result.requested_device,
        "resolved_device": result.resolved_device,
        "device_fallback_reason": result.device_fallback_reason,
    }


def _write_blocked_result(
    config: Mapping[str, Any], inputs: Stage03Inputs, output_dir: Path
) -> Stage03Result:
    record_path, manifest_path, inventory_path = _write_record_manifest_inventory(
        config,
        inputs,
        output_dir,
        _blocked_decision_record(config, inputs),
        execution_mode="blocked_stage02_handoff_not_ready_for_stage03",
        scoring_events=0,
    )
    return Stage03Result(
        output_dir=output_dir,
        run_manifest=manifest_path,
        artifact_inventory=inventory_path,
        decision_record=record_path,
    )


def _blocked_decision_record(
    config: Mapping[str, Any], inputs: Stage03Inputs
) -> dict[str, Any]:
    config_inputs = require_mapping(config["inputs"], "inputs")
    handoff = inputs.stage02_handoff
    block_reason = str(
        handoff.get("block_reason")
        or handoff.get("decision")
        or "stage02_handoff_not_ready_for_stage03"
    )
    return {
        "route": config["route"],
        "stage_name": config["stage_name"],
        "scope": config["scope"],
        "source_stage00_run_id": str(config_inputs["stage00_run_id"]),
        "source_stage01_run_id": str(config_inputs["stage01_run_id"]),
        "source_stage02_run_id": str(config_inputs["stage02_run_id"]),
        "superseded_stage02_run_ids": [
            str(value) for value in config_inputs.get("superseded_stage02_run_ids", [])
        ],
        "decision": "do_not_start_stage03_stage02_not_ready",
        "block_reason": block_reason,
        "stage02_handoff_decision": handoff.get("decision"),
        "official_validation_scoring_events": 0,
        "scoring_event_ledger": [],
        "fallback_activated": False,
        "fallback_reason": "",
        "readout_complete": False,
        "holdout_test_contact": False,
        "official_validation_for_selection": False,
        "no_final_model_selected": True,
    }


def _manifest_payload(
    config: Mapping[str, Any],
    inputs: Stage03Inputs,
    *,
    execution_mode: str,
    scoring_events: int,
    output_artifacts: list[str],
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Shared Stage 03 manifest body for the blocked and scored paths."""
    config_inputs = require_mapping(config["inputs"], "inputs")
    notebook_path = resolve_repo_path(config_inputs["notebook_path"])
    input_artifacts = [
        str(path)
        for paths in (inputs.stage00_paths, inputs.stage01_paths, inputs.stage02_paths)
        for path in paths.values()
    ]
    payload = {
        "route": config["route"],
        "stage_name": config["stage_name"],
        "scope": config["scope"],
        "config_sha256": hash_mapping(config),
        "notebook_sha256": hash_file(notebook_path),
        "source_stage00_run_id": str(config_inputs["stage00_run_id"]),
        "source_stage01_run_id": str(config_inputs["stage01_run_id"]),
        "source_stage02_run_id": str(config_inputs["stage02_run_id"]),
        "superseded_stage02_run_ids": [
            str(value) for value in config_inputs.get("superseded_stage02_run_ids", [])
        ],
        "stage03_execution_mode": execution_mode,
        "input_artifacts": input_artifacts,
        "output_artifacts": output_artifacts,
        "official_validation_contact": True,
        "official_validation_scoring_events": int(scoring_events),
        "official_validation_for_selection": False,
        "no_final_model_selected": True,
        "holdout_test_contact": False,
        "stage03_readout_code_sha256": stage03_readout_code_sha256(),
        **dict(inputs.feature_rebuild_fields),
        **git_commit_fields(),
    }
    if extra:
        payload.update(extra)
    return payload


def _write_record_manifest_inventory(
    config: Mapping[str, Any],
    inputs: Stage03Inputs,
    output_dir: Path,
    record: Mapping[str, Any],
    *,
    execution_mode: str,
    scoring_events: int,
    manifest_extra: Mapping[str, Any] | None = None,
    artifact_paths: Mapping[str, Path] | None = None,
) -> tuple[Path, Path, Path]:
    """Shared decision-record/manifest/inventory writer for both run paths."""
    outputs = require_mapping(config["outputs"], "outputs")
    extra_paths = dict(artifact_paths or {})
    record_path = write_json(
        output_dir / _output_name(outputs, "decision_record", "03_decision_record.json"),
        record,
    )
    manifest_payload = _manifest_payload(
        config,
        inputs,
        execution_mode=execution_mode,
        scoring_events=scoring_events,
        output_artifacts=[record_path.name, *[path.name for path in extra_paths.values()]],
        extra=manifest_extra,
    )
    manifest_path = write_json(
        output_dir / _output_name(outputs, "manifest", "run_manifest.json"), manifest_payload
    )
    inventory_path = write_artifact_inventory(
        output_dir,
        {"run_manifest": manifest_path, "decision_record": record_path, **extra_paths},
    )
    return record_path, manifest_path, inventory_path


def _execute_readout(
    *,
    config: Mapping[str, Any],
    inputs: Stage03Inputs,
    data_context: Stage03DataContext,
    output_dir: Path,
    run_id: str,
    resume_state: _ResumeState | None = None,
) -> Stage03Result:
    """One-shot official-validation readout (protocol sections 5-8 and 11).

    The primary candidate is scored exactly once per frozen seed. The fallback
    activates only on a mechanical failure before the first scoring event;
    after the first scoring event nothing activates it, and weak metrics are
    never a trigger (they are readout outcomes, judged afterwards).
    """
    handoff = inputs.stage02_handoff
    primary = require_mapping(handoff["primary_candidate"], "stage02_handoff.primary_candidate")
    fallback = require_mapping(handoff["fallback_candidate"], "stage02_handoff.fallback_candidate")
    if resume_state is not None:
        # Exact-run resume: the ledger is rebuilt from the checkpoint, the
        # candidate role is fixed to the role that was being scored, and the
        # restored scoring events make every fallback trigger unreachable
        # (protocol section 8: nothing activates the fallback after the first
        # scoring event; protocol section 11: never repeat a scoring event).
        ledger = resume_state.ledger
        scored_role: str | None = resume_state.candidate_role
        scored_selection: Mapping[str, Any] | None = (
            primary if resume_state.candidate_role == "primary" else fallback
        )
        _require_resume_candidate_consistency(resume_state, scored_selection)
        _score_candidate_role(
            scored_role, scored_selection, config, inputs, data_context, ledger, run_id
        )
    else:
        ledger = _ReadoutLedger()
        scored_role = "primary"
        scored_selection = primary
        try:
            _score_candidate_role("primary", primary, config, inputs, data_context, ledger, run_id)
        except _MechanicalReadoutFailure as primary_failure:
            if ledger.scoring_events:
                raise  # protocol section 8: nothing activates the fallback after the first scoring event
            ledger.fallback_activated = True
            ledger.fallback_reason = f"{primary_failure.trigger}: {primary_failure.detail}"
            scored_role, scored_selection = "fallback", fallback
            try:
                _score_candidate_role(
                    "fallback", fallback, config, inputs, data_context, ledger, run_id
                )
            except _MechanicalReadoutFailure as fallback_failure:
                ledger.fallback_candidate_failure_reason = (
                    f"{fallback_failure.trigger}: {fallback_failure.detail}"
                )
                scored_role, scored_selection = None, None
                ledger.readout_complete = False
                ledger.incomplete_reason = (
                    "primary and fallback candidates both failed mechanically before any "
                    "scoring event; zero official-validation scoring events recorded"
                )
    if scored_role is not None:
        _refresh_readout_completeness(ledger, scored_role, config, resumed=resume_state is not None)
    judgement = _aggregate_and_judge(ledger, scored_role, config)
    return _write_scored_result(
        config=config,
        inputs=inputs,
        output_dir=output_dir,
        ledger=ledger,
        judgement=judgement,
        scored_role=scored_role,
        scored_selection=scored_selection,
        resume_state=resume_state,
    )


def _refresh_readout_completeness(
    ledger: _ReadoutLedger,
    scored_role: str,
    config: Mapping[str, Any],
    *,
    resumed: bool,
) -> None:
    """Completeness is defined by the scoring-event ledger: the readout is
    complete exactly when every frozen seed has a recorded scoring event for
    the scored role. A resume that retried a previously failed seed clears the
    incomplete state but keeps the historical reason, prefixed as resolved."""
    expected_seeds = {
        int(seed) for seed in require_mapping(config["readout"], "readout")["seeds"]
    }
    completed_seeds = {
        int(event["seed"])
        for event in ledger.scoring_events
        if event["candidate_role"] == scored_role
    }
    ledger.readout_complete = expected_seeds <= completed_seeds
    if ledger.readout_complete and ledger.incomplete_reason and resumed:
        ledger.incomplete_reason = "resolved_after_resume: " + ledger.incomplete_reason


def _score_candidate_role(
    role: str,
    selection: Mapping[str, Any],
    config: Mapping[str, Any],
    inputs: Stage03Inputs,
    data_context: Stage03DataContext,
    ledger: _ReadoutLedger,
    run_id: str,
) -> None:
    """Identical frozen procedure per candidate role: dataset rebuild + parity,
    then the per-seed score loop with per-seed checkpoints. Seeds whose
    scoring event is already in the ledger (exact-run resume) are skipped and
    never re-scored; a previously failed seed is retried after its failed
    rows are purged, so each seed ends with at most one row per outcome."""
    prep = _prepare_role_datasets(role, selection, inputs, data_context)
    seeds = [int(seed) for seed in require_mapping(config["readout"], "readout")["seeds"]]
    for seed in seeds:
        already_scored = {
            int(event["seed"])
            for event in ledger.scoring_events
            if event["candidate_role"] == role
        }
        if seed in already_scored:
            continue
        _purge_failed_seed_rows(ledger, role, seed)
        _score_one_seed(role, selection, prep, seed, config, ledger)
        _write_seed_checkpoint(config, run_id, role, seeds, ledger)


def _purge_failed_seed_rows(ledger: _ReadoutLedger, role: str, seed: int) -> None:
    """Drop a retried seed's failed rows before re-scoring it (resume path),
    so the final artifacts carry one outcome per seed; completed rows are
    protected by the scoring-event skip and are never purged."""

    def keep(row: Mapping[str, Any]) -> bool:
        return not (
            str(row.get("candidate_role")) == role
            and int(row.get("seed", -1)) == seed
            and str(row.get("fit_status")) != "completed"
        )

    ledger.readout_rows = [row for row in ledger.readout_rows if keep(row)]
    ledger.refit_records = [record for record in ledger.refit_records if keep(record)]
    ledger.baseline_rows = [
        row
        for row in ledger.baseline_rows
        if not (str(row.get("candidate_role")) == role and int(row.get("seed", -1)) == seed)
    ]


def _prepare_role_datasets(
    role: str,
    selection: Mapping[str, Any],
    inputs: Stage03Inputs,
    data_context: Stage03DataContext,
) -> _RolePreparedData:
    """Candidate reconstruction: window-dataset rebuild, Stage 01 parity check,
    and one-time train/eval materialization (reused across seeds).

    ``FileNotFoundError``/``ValueError`` raised here are the protocol section 8
    mechanical triggers; they are wrapped into the trigger taxonomy, never
    swallowed.
    """
    try:
        train_dataset = _prepare_candidate_dataset(
            selection, data_context, data_context.train_events
        )
        validate_rebuilt_candidate_counts(
            {
                "candidate_id": selection["candidate_id"],
                "feature_columns": list(train_dataset.feature_columns),
            },
            train_dataset,
            inputs.stage01_summary,
        )
        validation_dataset = _prepare_candidate_dataset(
            selection, data_context, data_context.validation_events
        )
        if validation_dataset.metadata.empty:
            raise ValueError(
                f"{role} candidate produced no eligible official-validation window rows"
            )
        x_train = materialize_window_matrix(
            train_dataset, np.arange(len(train_dataset.metadata))
        )
        x_eval = materialize_window_matrix(
            validation_dataset, np.arange(len(validation_dataset.metadata))
        )
    except FileNotFoundError as exc:
        raise _MechanicalReadoutFailure("missing_frozen_artifact", f"{role}: {exc}") from exc
    except ValueError as exc:
        raise _MechanicalReadoutFailure("candidate_not_reconstructable", f"{role}: {exc}") from exc
    train_meta = train_dataset.metadata.reset_index(drop=True)
    eval_meta = validation_dataset.metadata.reset_index(drop=True)
    return _RolePreparedData(
        train_meta=train_meta,
        eval_meta=eval_meta,
        x_train=x_train,
        x_eval=x_eval,
        feature_columns=tuple(train_dataset.feature_columns),
        train_sample_id_hash=sample_id_hash(train_meta["sample_id"].tolist()),
        eval_sample_id_hash=sample_id_hash(eval_meta["sample_id"].tolist()),
    )


def _baseline_control_ids(config: Mapping[str, Any]) -> list[str]:
    controls = require_mapping(config["baseline_controls"], "baseline_controls")
    baseline_ids = [str(value) for value in controls.get("mandatory", [])]
    if not baseline_ids:
        raise ValueError("Stage 03 baseline_controls.mandatory must list the registry baselines")
    return baseline_ids


def _score_one_seed(
    role: str,
    selection: Mapping[str, Any],
    prep: _RolePreparedData,
    seed: int,
    config: Mapping[str, Any],
    ledger: _ReadoutLedger,
) -> None:
    """One frozen seed: same-row registry baselines, mechanism-frozen refit,
    then exactly one scoring event when the refit completed."""
    y_train = prep.train_meta["label"].to_numpy(dtype=int)
    y_eval = prep.eval_meta["label"].to_numpy(dtype=int)
    baseline_scores = {
        baseline_id: metrics.score_registry_baseline(baseline_id, y_train, y_eval, seed)
        for baseline_id in _baseline_control_ids(config)
    }
    for baseline_id, score in baseline_scores.items():
        ledger.baseline_rows.append(
            _same_row_baseline_row(role, selection, seed, baseline_id, score, prep)
        )
    profile = {
        "profile_id": str(selection["hpo_profile_id"]),
        **require_mapping(selection["hpo_profile_params"], "hpo_profile_params"),
    }
    outcome = _refit_and_predict(
        str(selection["model_family"]),
        profile,
        prep.x_train,
        prep.train_meta,
        prep.x_eval,
        config,
        int(seed),
        int(selection["window_size"]),
        len(prep.feature_columns),
    )
    ledger.refit_records.append(_refit_record(role, selection, seed, outcome))
    if outcome.get("fit_status") != "completed":
        _record_failed_refit(role, selection, prep, seed, outcome, ledger)
        return
    _record_completed_scoring(role, selection, prep, seed, outcome, baseline_scores, ledger)


def _record_failed_refit(
    role: str,
    selection: Mapping[str, Any],
    prep: _RolePreparedData,
    seed: int,
    outcome: Mapping[str, Any],
    ledger: _ReadoutLedger,
) -> None:
    if not ledger.scoring_events:
        raise _MechanicalReadoutFailure(
            "refit_crash_before_any_scoring",
            f"{role} candidate refit failed on seed {seed} before any scoring event "
            f"({outcome.get('fit_status')}: {outcome.get('error_message', '')})",
        )
    ledger.readout_complete = False
    reason = (
        f"{role} candidate refit failed on seed {seed} after the first scoring event "
        f"({outcome.get('fit_status')}: {outcome.get('error_message', '')}); protocol "
        "section 8 records an incomplete readout and never activates the fallback"
    )
    ledger.incomplete_reason = "; ".join(filter(None, [ledger.incomplete_reason, reason]))
    ledger.readout_rows.append(_readout_row_from_outcome(role, selection, prep, seed, outcome))


def _record_completed_scoring(
    role: str,
    selection: Mapping[str, Any],
    prep: _RolePreparedData,
    seed: int,
    outcome: Mapping[str, Any],
    baseline_scores: Mapping[str, Mapping[str, Any]],
    ledger: _ReadoutLedger,
) -> None:
    predictions = np.asarray(outcome["predictions"], dtype=int)
    scores = np.asarray(outcome["scores"], dtype=float)
    # Predictions for official-validation rows now exist: this IS the scoring
    # event, counted before any metric arithmetic (protocol section 11).
    ledger.scoring_events.append(
        {
            "candidate_role": role,
            "candidate_id": str(selection["candidate_id"]),
            "seed": int(seed),
            "n_rows": int(len(prep.eval_meta)),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
    )
    y_eval = prep.eval_meta["label"].to_numpy(dtype=int)
    scored = metrics.score_classifier(y_eval, predictions, y_score=scores)
    per_class = metrics.per_class_metrics(y_eval, predictions)
    dummy = baseline_scores["stratified_dummy_train_prior"]
    majority = baseline_scores["majority_train_prior"]
    dummy_deltas, positive_ticker_count = metrics.ticker_delta_macro_f1(
        prep.eval_meta, predictions, np.asarray(dummy["predictions"], dtype=int)
    )
    majority_deltas, _ = metrics.ticker_delta_macro_f1(
        prep.eval_meta, predictions, np.asarray(majority["predictions"], dtype=int)
    )
    row = _readout_row_from_outcome(role, selection, prep, seed, outcome)
    row.update(scored)
    row.update(per_class)
    row.update(
        {
            "baseline_macro_f1_stratified_dummy_train_prior": float(dummy["macro_f1"]),
            "baseline_macro_f1_majority_train_prior": float(majority["macro_f1"]),
            "delta_macro_f1_vs_stratified_dummy_train_prior": float(
                scored["macro_f1"] - dummy["macro_f1"]
            ),
            "delta_macro_f1_vs_majority_train_prior": float(
                scored["macro_f1"] - majority["macro_f1"]
            ),
            "delta_balanced_accuracy_vs_stratified_dummy_train_prior": float(
                scored["balanced_accuracy"] - dummy["balanced_accuracy"]
            ),
            "positive_ticker_count": int(positive_ticker_count),
        }
    )
    ledger.readout_rows.append(row)
    ledger.ticker_deltas.append(
        {"candidate_role": role, "seed": int(seed), "deltas": dict(dummy_deltas)}
    )
    ledger.per_ticker_rows.extend(
        _per_ticker_rows(role, selection, seed, prep.eval_meta, predictions, dummy_deltas, majority_deltas)
    )
    ledger.prediction_frames.append(
        _prediction_frame(role, selection, seed, prep.eval_meta, predictions, scores)
    )


def _readout_row_from_outcome(
    role: str,
    selection: Mapping[str, Any],
    prep: _RolePreparedData,
    seed: int,
    outcome: Mapping[str, Any],
) -> dict[str, Any]:
    """Readout row with identity, refit, and device fields filled; metric
    columns stay None until a completed scoring fills them."""
    row: dict[str, Any] = {column: None for column in VALIDATION_READOUT_COLUMNS}
    row.update(
        {
            "candidate_role": role,
            "candidate_id": str(selection["candidate_id"]),
            "feature_set": str(selection["feature_set"]),
            "window_size": int(selection["window_size"]),
            "model_family": str(selection["model_family"]),
            "hpo_profile_id": str(selection["hpo_profile_id"]),
            "seed": int(seed),
            "n_refit_train_samples": int(len(prep.train_meta)),
            "n_scored_validation_samples": int(len(prep.eval_meta)),
            "train_sample_id_hash": prep.train_sample_id_hash,
            "eval_sample_id_hash": prep.eval_sample_id_hash,
            "best_iteration": outcome.get("best_iteration"),
            "early_stopping_source": outcome.get("early_stopping_source"),
            "early_stopping_used": outcome.get("early_stopping_used"),
            "early_stopping_reason": outcome.get("early_stopping_reason"),
            "early_stopping_train_sample_id_hash": outcome.get(
                "early_stopping_train_sample_id_hash", ""
            ),
            "early_stopping_eval_sample_id_hash": outcome.get(
                "early_stopping_eval_sample_id_hash", ""
            ),
            "requested_device": outcome.get("requested_device"),
            "resolved_device": outcome.get("resolved_device"),
            "device_fallback_reason": outcome.get("device_fallback_reason"),
            "fit_status": str(outcome.get("fit_status", "failed_unknown")),
            "error_message": str(outcome.get("error_message", "")),
            "scope": READOUT_ROW_SCOPE,
        }
    )
    return row


def _refit_record(
    role: str, selection: Mapping[str, Any], seed: int, outcome: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "candidate_role": role,
        "candidate_id": str(selection["candidate_id"]),
        "seed": int(seed),
        "fit_status": str(outcome.get("fit_status", "failed_unknown")),
        "best_iteration": outcome.get("best_iteration"),
        "early_stopping_source": outcome.get("early_stopping_source"),
        "early_stopping_used": outcome.get("early_stopping_used"),
        "early_stopping_reason": outcome.get("early_stopping_reason"),
        "early_stopping_train_sample_id_hash": outcome.get(
            "early_stopping_train_sample_id_hash", ""
        ),
        "early_stopping_eval_sample_id_hash": outcome.get(
            "early_stopping_eval_sample_id_hash", ""
        ),
        "requested_device": outcome.get("requested_device"),
        "resolved_device": outcome.get("resolved_device"),
        "device_fallback_reason": outcome.get("device_fallback_reason"),
        "error_message": str(outcome.get("error_message", "")),
    }


def _same_row_baseline_row(
    role: str,
    selection: Mapping[str, Any],
    seed: int,
    baseline_id: str,
    score: Mapping[str, Any],
    prep: _RolePreparedData,
) -> dict[str, Any]:
    return {
        "candidate_role": role,
        "candidate_id": str(selection["candidate_id"]),
        "seed": int(seed),
        "baseline_id": baseline_id,
        "fit_status": score["fit_status"],
        "n_train_samples": int(len(prep.train_meta)),
        "n_eval_samples": int(len(prep.eval_meta)),
        "train_sample_id_hash": prep.train_sample_id_hash,
        "eval_sample_id_hash": prep.eval_sample_id_hash,
        "sample_id_hash": prep.eval_sample_id_hash,
        "macro_f1": score["macro_f1"],
        "balanced_accuracy": score["balanced_accuracy"],
        "accuracy": score["accuracy"],
        "roc_auc": score["roc_auc"],
        "mcc": score["mcc"],
        "error_message": score["error_message"],
        "scope": READOUT_ROW_SCOPE,
    }


def _per_ticker_rows(
    role: str,
    selection: Mapping[str, Any],
    seed: int,
    eval_meta: pd.DataFrame,
    predictions: np.ndarray,
    dummy_deltas: Mapping[str, float],
    majority_deltas: Mapping[str, float],
) -> list[dict[str, Any]]:
    y_eval = eval_meta["label"].to_numpy(dtype=int)
    indexed = eval_meta.assign(_position=np.arange(len(eval_meta)))
    rows: list[dict[str, Any]] = []
    for ticker, group in indexed.groupby("ticker", sort=True):
        positions = group["_position"].to_numpy(dtype=int)
        slice_true = y_eval[positions]
        slice_pred = predictions[positions]
        scored = metrics.classification_metrics(slice_true, slice_pred)
        per_class = metrics.per_class_metrics(slice_true, slice_pred)
        rows.append(
            {
                "candidate_role": role,
                "candidate_id": str(selection["candidate_id"]),
                "seed": int(seed),
                "ticker": str(ticker),
                "n_rows": int(len(positions)),
                "support_up": per_class["support_up"],
                "support_down": per_class["support_down"],
                "macro_f1": scored["macro_f1"],
                "balanced_accuracy": scored["balanced_accuracy"],
                "accuracy": scored["accuracy"],
                "f1_up": per_class["f1_up"],
                "f1_down": per_class["f1_down"],
                "delta_macro_f1_vs_stratified_dummy_train_prior": dummy_deltas[str(ticker)],
                "delta_macro_f1_vs_majority_train_prior": majority_deltas[str(ticker)],
                "scope": READOUT_ROW_SCOPE,
            }
        )
    return rows


def _prediction_frame(
    role: str,
    selection: Mapping[str, Any],
    seed: int,
    eval_meta: pd.DataFrame,
    predictions: np.ndarray,
    scores: np.ndarray,
) -> pd.DataFrame:
    """REQUIRED per-row prediction dump rows for one scoring event."""
    return pd.DataFrame(
        {
            "candidate_role": role,
            "candidate_id": str(selection["candidate_id"]),
            "model_family": str(selection["model_family"]),
            "hpo_profile_id": str(selection["hpo_profile_id"]),
            "seed": int(seed),
            "sample_id": eval_meta["sample_id"].to_numpy(),
            "ticker": eval_meta["ticker"].to_numpy(),
            "target_timestamp": eval_meta["target_timestamp"].to_numpy(),
            "trading_day": eval_meta["trading_day"].to_numpy(),
            "y_true": eval_meta["label"].to_numpy(dtype=int),
            "p_up": np.asarray(scores, dtype=float),
            "y_pred": np.asarray(predictions, dtype=int),
            "scope": READOUT_ROW_SCOPE,
        }
    )[VALIDATION_PREDICTION_COLUMNS]


def _readout_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=VALIDATION_READOUT_COLUMNS)


def _baseline_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=SAME_ROW_BASELINE_COLUMNS)


def _prediction_frame_concat(frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame(columns=VALIDATION_PREDICTION_COLUMNS)
    return pd.concat(frames, ignore_index=True)[VALIDATION_PREDICTION_COLUMNS]


def _write_seed_checkpoint(
    config: Mapping[str, Any],
    run_id: str,
    role: str,
    seeds: list[int],
    ledger: _ReadoutLedger,
) -> None:
    """Per-seed recovery checkpoint (recovery state only, never evidence)."""
    checkpointing = config.get("checkpointing", {})
    if not isinstance(checkpointing, Mapping) or checkpointing.get("enabled") is not True:
        return
    checkpoint_root = Path(
        str(
            checkpointing.get(
                "checkpoint_dir", "/content/lst_models_checkpoints/03_frozen_validation_readout"
            )
        )
    )
    checkpoint_dir = checkpoint_root / run_id
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    _readout_frame(ledger.readout_rows).to_csv(
        checkpoint_dir / "03_validation_readout_partial.csv", index=False
    )
    _baseline_frame(ledger.baseline_rows).to_csv(
        checkpoint_dir / "03_same_row_baselines_partial.csv", index=False
    )
    _prediction_frame_concat(ledger.prediction_frames).to_csv(
        checkpoint_dir / "03_validation_predictions_partial.csv", index=False
    )
    write_json(
        checkpoint_dir / "03_ledger_state_partial.json",
        _jsonable(
            {
                "stage_name": str(config["stage_name"]),
                "run_id": run_id,
                "candidate_role": role,
                "readout_rows": ledger.readout_rows,
                "per_ticker_rows": ledger.per_ticker_rows,
                "baseline_rows": ledger.baseline_rows,
                "scoring_events": ledger.scoring_events,
                "refit_records": ledger.refit_records,
                "ticker_deltas": ledger.ticker_deltas,
                "readout_complete": ledger.readout_complete,
                "incomplete_reason": ledger.incomplete_reason,
                "fallback_activated": ledger.fallback_activated,
                "fallback_reason": ledger.fallback_reason,
                "fallback_candidate_failure_reason": ledger.fallback_candidate_failure_reason,
            }
        ),
    )
    completed_seeds = [
        int(event["seed"]) for event in ledger.scoring_events if event["candidate_role"] == role
    ]
    manifest = {
        "stage_name": str(config["stage_name"]),
        "run_id": run_id,
        "status": "incomplete",
        "candidate_role": role,
        "completed_seeds": completed_seeds,
        "pending_seeds": [int(seed) for seed in seeds if int(seed) not in completed_seeds],
        "resume_instructions": {
            "resume_mode": "exact_run_checkpoint_only",
            "required_run_id": run_id,
            "required_checkpoint_dir": str(checkpoint_dir),
            "required_files": list(RESUME_REQUIRED_CHECKPOINT_FILES),
            "latest_parent_scan_allowed": False,
        },
        "holdout_test_contact": False,
        "official_validation_for_selection": False,
        "checkpoint_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(checkpoint_dir / "checkpoint_manifest.json", manifest)


def _aggregate_and_judge(
    ledger: _ReadoutLedger, scored_role: str | None, config: Mapping[str, Any]
) -> dict[str, Any]:
    """Seed-aggregate (mean over completed seeds) and the predeclared-criteria
    judgement (protocol section 7); criteria are judged after scoring and never
    feed back into scoring or fallback decisions."""
    criteria = require_mapping(config["predeclared_criteria"], "predeclared_criteria")
    minimum_positive = int(criteria["minimum_positive_ticker_count"])
    completed = [
        row
        for row in ledger.readout_rows
        if row["candidate_role"] == scored_role and row["fit_status"] == "completed"
    ]
    if not completed:
        return {
            "decision": "do_not_start_stage03_primary_and_fallback_mechanical_failure",
            "criteria": {
                "delta_vs_stratified_dummy_met": False,
                "delta_vs_majority_met": False,
                "ticker_floor_met": False,
            },
            "aggregate": {
                "n_completed_seeds": 0,
                "mean_macro_f1": None,
                "mean_delta_macro_f1_vs_stratified_dummy_train_prior": None,
                "mean_delta_macro_f1_vs_majority_train_prior": None,
                "per_ticker_mean_delta_macro_f1_vs_stratified_dummy_train_prior": {},
                "positive_ticker_count": None,
            },
        }
    mean_dummy_delta = float(
        np.mean([row["delta_macro_f1_vs_stratified_dummy_train_prior"] for row in completed])
    )
    mean_majority_delta = float(
        np.mean([row["delta_macro_f1_vs_majority_train_prior"] for row in completed])
    )
    per_ticker = _per_ticker_mean_deltas(ledger.ticker_deltas, scored_role)
    positive_count = sum(1 for value in per_ticker.values() if value > 0)
    checks = {
        "delta_vs_stratified_dummy_met": bool(mean_dummy_delta > 0),
        "delta_vs_majority_met": bool(mean_majority_delta > 0),
        "ticker_floor_met": bool(positive_count >= minimum_positive),
    }
    decision = (
        "met_predeclared_validation_readout_criteria"
        if all(checks.values())
        else "did_not_meet_predeclared_validation_readout_criteria"
    )
    return {
        "decision": decision,
        "criteria": checks,
        "aggregate": {
            "n_completed_seeds": len(completed),
            "mean_macro_f1": float(np.mean([row["macro_f1"] for row in completed])),
            "mean_delta_macro_f1_vs_stratified_dummy_train_prior": mean_dummy_delta,
            "mean_delta_macro_f1_vs_majority_train_prior": mean_majority_delta,
            "per_ticker_mean_delta_macro_f1_vs_stratified_dummy_train_prior": per_ticker,
            "positive_ticker_count": int(positive_count),
        },
    }


def _per_ticker_mean_deltas(
    ticker_deltas: list[dict[str, Any]], scored_role: str | None
) -> dict[str, float]:
    """Per-ticker delta vs the stratified dummy, averaged across completed
    seeds per ticker (predeclared_criteria.per_ticker_aggregation)."""
    buckets: dict[str, list[float]] = {}
    for entry in ticker_deltas:
        if entry["candidate_role"] != scored_role:
            continue
        for ticker, value in entry["deltas"].items():
            buckets.setdefault(str(ticker), []).append(float(value))
    return {ticker: float(np.mean(values)) for ticker, values in sorted(buckets.items())}


def _aggregate_readout_rows(
    ledger: _ReadoutLedger,
    judgement: Mapping[str, Any],
    scored_role: str | None,
) -> list[dict[str, Any]]:
    """One aggregate_mean row per scored role (mean over completed seeds)."""
    completed = [
        row
        for row in ledger.readout_rows
        if row["candidate_role"] == scored_role and row["fit_status"] == "completed"
    ]
    if scored_role is None or not completed:
        return []
    row: dict[str, Any] = {column: None for column in VALIDATION_READOUT_COLUMNS}
    identity_columns = (
        "candidate_role", "candidate_id", "feature_set", "window_size",
        "model_family", "hpo_profile_id", "n_refit_train_samples",
        "n_scored_validation_samples", "train_sample_id_hash", "eval_sample_id_hash",
    )
    row.update({column: completed[0][column] for column in identity_columns})
    for column in AGGREGATED_READOUT_METRIC_COLUMNS:
        row[column] = float(np.mean([seed_row[column] for seed_row in completed]))
    row.update(
        {
            "seed": "aggregate_mean",
            "positive_ticker_count": judgement["aggregate"]["positive_ticker_count"],
            "fit_status": "aggregate_mean",
            "error_message": "",
            "scope": READOUT_ROW_SCOPE,
        }
    )
    return [row]


def _seed_summary_rows(
    ledger: _ReadoutLedger,
    judgement: Mapping[str, Any],
    scored_role: str | None,
    scored_selection: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    completed = [
        row
        for row in ledger.readout_rows
        if row["candidate_role"] == scored_role and row["fit_status"] == "completed"
    ]
    if scored_role is None or scored_selection is None or not completed:
        return []
    macro = pd.Series([row["macro_f1"] for row in completed], dtype=float)
    dummy_deltas = [row["delta_macro_f1_vs_stratified_dummy_train_prior"] for row in completed]
    majority_deltas = [row["delta_macro_f1_vs_majority_train_prior"] for row in completed]
    checks = judgement["criteria"]
    return [
        {
            "candidate_role": scored_role,
            "candidate_id": str(scored_selection["candidate_id"]),
            "n_seeds": len(completed),
            "mean_macro_f1": float(macro.mean()),
            "std_macro_f1": float(macro.std()),
            "mean_delta_macro_f1_vs_stratified_dummy_train_prior": float(np.mean(dummy_deltas)),
            "min_delta_macro_f1_vs_stratified_dummy_train_prior": float(np.min(dummy_deltas)),
            "mean_delta_macro_f1_vs_majority_train_prior": float(np.mean(majority_deltas)),
            "min_delta_macro_f1_vs_majority_train_prior": float(np.min(majority_deltas)),
            "positive_ticker_count_mean_across_seeds": float(
                np.mean([row["positive_ticker_count"] for row in completed])
            ),
            "criteria_delta_vs_stratified_dummy_met": bool(
                checks["delta_vs_stratified_dummy_met"]
            ),
            "criteria_delta_vs_majority_met": bool(checks["delta_vs_majority_met"]),
            "criteria_ticker_floor_met": bool(checks["ticker_floor_met"]),
            "met_predeclared_criteria": bool(all(checks.values())),
            "scope": READOUT_ROW_SCOPE,
        }
    ]


def _per_seed_outcome_rows(readout_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = (
        "candidate_role", "candidate_id", "seed", "fit_status", "macro_f1",
        "balanced_accuracy",
        "delta_macro_f1_vs_stratified_dummy_train_prior",
        "delta_macro_f1_vs_majority_train_prior",
        "positive_ticker_count", "error_message",
    )
    return [{key: row.get(key) for key in keys} for row in readout_rows]


def _readout_device_fields(refit_records: list[dict[str, Any]]) -> dict[str, Any]:
    """AGENTS.md device provenance aggregated from the completed refit outcomes
    (mirrors the Stage 02 trial-ledger aggregation pattern)."""
    completed = [record for record in refit_records if record["fit_status"] == "completed"]
    if not completed:
        return {
            "requested_device": "not_resolved",
            "resolved_device": "not_resolved",
            "cuda_available": False,
            "gpu_name_or_null": None,
            "device_fallback_reason": "no_refits_completed",
        }
    requested_values = sorted(
        {str(record["requested_device"]) for record in completed if record["requested_device"]}
    )
    resolved_values = sorted(
        {str(record["resolved_device"]) for record in completed if record["resolved_device"]}
    )
    fallback_values = sorted(
        {
            str(record["device_fallback_reason"])
            for record in completed
            if record["device_fallback_reason"]
        }
    )
    resolved_device = ",".join(resolved_values) if resolved_values else "not_resolved"
    cuda_resolved = any(value.strip().startswith("cuda") for value in resolved_device.split(","))
    runtime_fields = (
        torch_runtime_device_fields()
        if cuda_resolved
        else {"cuda_available": False, "gpu_name_or_null": None}
    )
    cuda_available = bool(runtime_fields["cuda_available"] or cuda_resolved)
    return {
        "requested_device": ",".join(requested_values) if requested_values else "not_resolved",
        "resolved_device": resolved_device,
        "cuda_available": cuda_available,
        "gpu_name_or_null": runtime_fields["gpu_name_or_null"] if cuda_available else None,
        "device_fallback_reason": ",".join(fallback_values),
    }


def _scored_decision_record(
    config: Mapping[str, Any],
    inputs: Stage03Inputs,
    ledger: _ReadoutLedger,
    judgement: Mapping[str, Any],
    scored_role: str | None,
    resume_state: _ResumeState | None,
) -> dict[str, Any]:
    config_inputs = require_mapping(config["inputs"], "inputs")
    frozen_candidate = inputs.frozen_candidate
    return {
        "route": config["route"],
        "stage_name": config["stage_name"],
        "scope": config["scope"],
        "source_stage00_run_id": str(config_inputs["stage00_run_id"]),
        "source_stage01_run_id": str(config_inputs["stage01_run_id"]),
        "source_stage02_run_id": str(config_inputs["stage02_run_id"]),
        "superseded_stage02_run_ids": [
            str(value) for value in config_inputs.get("superseded_stage02_run_ids", [])
        ],
        "primary_candidate": frozen_candidate.get("primary_candidate"),
        "fallback_candidate": frozen_candidate.get("fallback_candidate"),
        "scored_candidate_role": scored_role,
        "predeclared_criteria": dict(
            require_mapping(config["predeclared_criteria"], "predeclared_criteria")
        ),
        "per_seed_outcomes": _per_seed_outcome_rows(ledger.readout_rows),
        "aggregate": dict(judgement["aggregate"]),
        "criteria": dict(judgement["criteria"]),
        "decision": judgement["decision"],
        "fallback_activated": bool(ledger.fallback_activated),
        "fallback_reason": str(ledger.fallback_reason),
        "fallback_candidate_failure_reason": str(ledger.fallback_candidate_failure_reason),
        "readout_complete": bool(ledger.readout_complete),
        "readout_incomplete_reason": ledger.incomplete_reason,
        "official_validation_scoring_events": len(ledger.scoring_events),
        "scoring_event_ledger": list(ledger.scoring_events),
        "refit_records": list(ledger.refit_records),
        "resumed_from_checkpoint": resume_state is not None,
        "resume_checkpoint_dir": (
            str(resume_state.checkpoint_dir) if resume_state is not None else None
        ),
        "holdout_test_contact": False,
        "official_validation_for_selection": False,
        "no_final_model_selected": True,
    }


def _write_scored_result(
    *,
    config: Mapping[str, Any],
    inputs: Stage03Inputs,
    output_dir: Path,
    ledger: _ReadoutLedger,
    judgement: Mapping[str, Any],
    scored_role: str | None,
    scored_selection: Mapping[str, Any] | None,
    resume_state: _ResumeState | None = None,
) -> Stage03Result:
    outputs = require_mapping(config["outputs"], "outputs")
    paths = {
        "validation_readout": output_dir
        / _output_name(outputs, "validation_readout", "03_validation_readout.csv"),
        "per_ticker_readout": output_dir
        / _output_name(outputs, "per_ticker_readout", "03_per_ticker_readout.csv"),
        "seed_summary": output_dir / _output_name(outputs, "seed_summary", "03_seed_summary.csv"),
        "same_row_baselines": output_dir
        / _output_name(outputs, "same_row_baselines", "03_same_row_baselines.csv"),
        "validation_predictions": output_dir
        / _output_name(outputs, "validation_predictions", "03_validation_predictions.csv"),
    }
    readout_rows = [*ledger.readout_rows, *_aggregate_readout_rows(ledger, judgement, scored_role)]
    _readout_frame(readout_rows).to_csv(paths["validation_readout"], index=False)
    pd.DataFrame(ledger.per_ticker_rows, columns=PER_TICKER_READOUT_COLUMNS).to_csv(
        paths["per_ticker_readout"], index=False
    )
    pd.DataFrame(
        _seed_summary_rows(ledger, judgement, scored_role, scored_selection),
        columns=SEED_SUMMARY_COLUMNS,
    ).to_csv(paths["seed_summary"], index=False)
    _baseline_frame(ledger.baseline_rows).to_csv(paths["same_row_baselines"], index=False)
    _prediction_frame_concat(ledger.prediction_frames).to_csv(
        paths["validation_predictions"], index=False
    )
    record = _scored_decision_record(config, inputs, ledger, judgement, scored_role, resume_state)
    manifest_extra = {
        "decision": judgement["decision"],
        "readout_complete": bool(ledger.readout_complete),
        "fallback_activated": bool(ledger.fallback_activated),
        "resumed_from_checkpoint": resume_state is not None,
        **_readout_device_fields(ledger.refit_records),
    }
    record_path, manifest_path, inventory_path = _write_record_manifest_inventory(
        config,
        inputs,
        output_dir,
        record,
        execution_mode="one_shot_official_validation_readout",
        scoring_events=len(ledger.scoring_events),
        manifest_extra=manifest_extra,
        artifact_paths=paths,
    )
    return Stage03Result(
        output_dir=output_dir,
        run_manifest=manifest_path,
        artifact_inventory=inventory_path,
        decision_record=record_path,
        validation_readout=paths["validation_readout"],
        per_ticker_readout=paths["per_ticker_readout"],
        seed_summary=paths["seed_summary"],
        same_row_baselines=paths["same_row_baselines"],
        validation_predictions=paths["validation_predictions"],
    )
