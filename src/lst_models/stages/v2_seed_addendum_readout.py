"""V2 seed addendum readout: disclosed post-hoc official-validation seed addendum.

Trains the FROZEN Stage 02 primary spec (price_volume_time_w20 / tcn / tcn_p01)
under six additional seeds (deterministic rule: seed_k = 101 * k, k in {3..8})
and scores each seed EXACTLY ONCE on the official validation split against the
same-row registry baselines, reusing the identical Stage 03 mechanism through
the shared domain modules: ``load_sample_event_index`` ->
``valid_events_for_split`` -> ``load_train_validation_bars`` ->
``build_feature_frame`` -> ``build_window_dataset`` (Stage 01 parity gate) ->
``fitting.fit_torch_sequence_probe`` (frozen chronological-tail early stopping)
-> ``metrics.score_registry_baseline`` / ``score_classifier``.

The addendum NEVER reruns seeds 101/202, NEVER touches rows at or after the
closed holdout boundary (2017-01-25; asserted in code), performs NO selection
and NO pass/fail judging, and is NEVER merged into the predeclared n=2 readout,
which remains the canonical official-validation number either way.

Preregistration sidecar: docs/protocols/v2_seed_addendum_preregistration_20260701.md
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
    feature_rebuild_gate_fields,
    git_commit_fields,
    read_json_object,
    require_artifacts,
    require_distinct_file_hashes,
    require_run_id_chain,
    require_safety_flags,
    stage03_readout_code_sha256,
    write_artifact_inventory,
    write_json,
)
from lst_models.config import hash_file, hash_mapping, require_mapping, resolve_repo_path
from lst_models.data import (
    load_sample_event_index,
    load_stage01_summary,
    load_train_validation_bars,
    raw_manifest_integrity_summary,
)
from lst_models.device import torch_runtime_device_fields
from lst_models.features import build_feature_frame, require_feature_columns
from lst_models.splits import valid_events_for_split
from lst_models.windows import (
    build_window_dataset,
    materialize_window_matrix,
    sample_id_hash,
    validate_rebuilt_candidate_counts,
)


STAGE_NAME = "v2_seed_addendum_readout"
ROW_SCOPE = "validation_only"
RUN_ID_PATTERN = re.compile(r"^\d{8}_\d{6}_\d{6}$")
SEED_RULE_ID = "seed_k_equals_101_times_k_next_six_multipliers_k3_to_k8"
EXPECTED_ADDENDUM_SEEDS = [101 * k for k in range(3, 9)]  # [303, 404, 505, 606, 707, 808]
PREDECLARED_SEEDS = [101, 202]

# Verbatim copies of the Stage 03 frozen column contracts (same-schema addendum
# outputs). Parity with lst_models.stages.frozen_validation_readout is pinned by
# tests/contracts/test_v2_seed_addendum_config_contract.py; do not edit one copy alone.
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

# Addendum-specific predeclared descriptive summary (min/median/max dispersion,
# positive-delta seed counts; NO pass/fail column by design).
SEED_DISPERSION_SUMMARY_COLUMNS = [
    "candidate_id", "model_family", "hpo_profile_id", "seed_rule",
    "n_addendum_seeds", "n_completed_seeds", "n_failed_seeds",
    "min_macro_f1", "median_macro_f1", "max_macro_f1",
    "mean_macro_f1", "std_macro_f1",
    "min_delta_macro_f1_vs_stratified_dummy_train_prior",
    "median_delta_macro_f1_vs_stratified_dummy_train_prior",
    "max_delta_macro_f1_vs_stratified_dummy_train_prior",
    "mean_delta_macro_f1_vs_stratified_dummy_train_prior",
    "n_seeds_delta_vs_stratified_dummy_positive",
    "min_delta_macro_f1_vs_majority_train_prior",
    "median_delta_macro_f1_vs_majority_train_prior",
    "max_delta_macro_f1_vs_majority_train_prior",
    "n_seeds_delta_vs_majority_positive",
    "min_positive_ticker_count", "median_positive_ticker_count",
    "max_positive_ticker_count",
    "interpretation", "canonical_readout", "scope",
]

# Exact schema of artifacts/05_thesis_synthesis/<run>/05_validation_budget_ledger.csv.
BUDGET_LEDGER_ROW_COLUMNS = [
    "stage_name", "run_id", "evidence_domain", "data_segment", "contact_type",
    "scoring_events", "for_selection", "notes",
]

# Refit-outcome fields carried into readout rows and refit records unchanged.
OUTCOME_PASSTHROUGH_KEYS = (
    "best_iteration", "early_stopping_source", "early_stopping_used",
    "early_stopping_reason", "requested_device", "resolved_device",
    "device_fallback_reason",
)
RESUME_REQUIRED_CHECKPOINT_FILES = (
    "checkpoint_manifest.json",
    "v2sa_ledger_state_partial.json",
    "v2sa_validation_readout_partial.csv",
    "v2sa_same_row_baselines_partial.csv",
    "v2sa_validation_predictions_partial.csv",
)


@dataclass(frozen=True)
class SeedAddendumResult:
    output_dir: Path
    run_manifest: Path
    artifact_inventory: Path
    decision_record: Path
    validation_readout: Path
    per_ticker_readout: Path
    seed_dispersion_summary: Path
    same_row_baselines: Path
    validation_predictions: Path
    budget_ledger_row: Path


@dataclass(frozen=True)
class _AddendumInputs:
    stage00_paths: Mapping[str, Path]
    stage01_paths: Mapping[str, Path]
    stage02_paths: Mapping[str, Path]
    stage01_handoff: Mapping[str, Any]
    stage01_summary: pd.DataFrame
    primary_selection: Mapping[str, Any]
    raw_manifest: Mapping[str, Any]
    split_freeze: Mapping[str, Any]
    feature_rebuild_fields: Mapping[str, Any]


@dataclass(frozen=True)
class _PreparedData:
    train_meta: pd.DataFrame
    eval_meta: pd.DataFrame
    x_train: np.ndarray
    x_eval: np.ndarray
    feature_columns: tuple[str, ...]
    train_sample_id_hash: str
    eval_sample_id_hash: str


@dataclass
class _AddendumLedger:
    """Mutable run state: every scoring event and output row appended exactly
    once; serialized per-seed so an exact-run resume never repeats a scoring
    event (same discipline as the Stage 03 readout ledger)."""

    readout_rows: list[dict[str, Any]] = field(default_factory=list)
    per_ticker_rows: list[dict[str, Any]] = field(default_factory=list)
    baseline_rows: list[dict[str, Any]] = field(default_factory=list)
    prediction_frames: list[pd.DataFrame] = field(default_factory=list)
    scoring_events: list[dict[str, Any]] = field(default_factory=list)
    refit_records: list[dict[str, Any]] = field(default_factory=list)
    ticker_deltas: list[dict[str, Any]] = field(default_factory=list)


def run_stage(config: Mapping[str, Any]) -> SeedAddendumResult:
    _validate_config(config)
    inputs = _verify_entry_gates(config)
    prep = _load_and_prepare_data(config, inputs)

    outputs = require_mapping(config["outputs"], "outputs")
    resume_state = _load_resume_state(config, inputs.primary_selection)
    if resume_state is None:
        run_id, ledger = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f"), _AddendumLedger()
    else:
        run_id, ledger = resume_state
    output_dir = Path(str(outputs["output_dir"])) / run_id
    output_dir.mkdir(parents=True, exist_ok=resume_state is not None)

    seeds = [int(seed) for seed in require_mapping(config["readout"], "readout")["addendum_seeds"]]
    max_events = int(require_mapping(config["budget"], "budget")[
        "max_new_official_validation_scoring_events"
    ])
    for seed in seeds:
        if seed in {int(event["seed"]) for event in ledger.scoring_events}:
            continue  # exact-run resume: never repeat a recorded scoring event
        if len(ledger.scoring_events) >= max_events:
            raise RuntimeError(
                f"{STAGE_NAME} budget breach: {len(ledger.scoring_events)} scoring events "
                f"already recorded, cap is {max_events}"
            )
        _purge_failed_seed_rows(ledger, seed)
        _score_one_seed(inputs.primary_selection, prep, seed, config, ledger)
        _write_seed_checkpoint(config, run_id, seeds, ledger)

    return _write_results(config, inputs, prep, ledger, output_dir, run_id, resume_state is not None)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(f"{STAGE_NAME}: {message}")


def _validate_config(config: Mapping[str, Any]) -> None:
    _require(config.get("stage_name") == STAGE_NAME, f"stage_name must be {STAGE_NAME}")
    _require(config.get("scope") == "validation_only", "scope must be validation_only")
    for flag, expected in (
        ("holdout_test_contact", False),
        ("official_validation_contact", True),
        ("official_validation_for_selection", False),
        ("addendum_never_merged_into_predeclared_readout", True),
    ):
        _require(config.get(flag) is expected, f"requires {flag}={expected}")

    readout = require_mapping(config["readout"], "readout")
    _require(str(readout.get("seed_rule")) == SEED_RULE_ID, f"readout.seed_rule must be {SEED_RULE_ID}")
    seeds = readout.get("addendum_seeds")
    _require(
        isinstance(seeds, list) and [int(s) for s in seeds] == EXPECTED_ADDENDUM_SEEDS,
        f"readout.addendum_seeds must equal the declared rule {EXPECTED_ADDENDUM_SEEDS} "
        f"(seed_k = 101*k, k in 3..8), got {seeds}",
    )
    never_rerun = [int(s) for s in readout.get("predeclared_seeds_never_rerun", [])]
    _require(
        never_rerun == PREDECLARED_SEEDS,
        f"readout.predeclared_seeds_never_rerun must equal {PREDECLARED_SEEDS}, got {never_rerun}",
    )
    _require(
        not set(EXPECTED_ADDENDUM_SEEDS) & set(PREDECLARED_SEEDS),
        "addendum seeds overlap the predeclared seeds; the addendum never reruns 101/202",
    )
    _require(
        readout.get("score_each_seed_candidate_exactly_once") is True,
        "requires readout.score_each_seed_candidate_exactly_once=true",
    )

    budget = require_mapping(config["budget"], "budget")
    _require(
        int(budget["max_new_official_validation_scoring_events"]) == len(EXPECTED_ADDENDUM_SEEDS),
        "budget.max_new_official_validation_scoring_events must equal the addendum seed count "
        f"{len(EXPECTED_ADDENDUM_SEEDS)}",
    )
    _require(budget.get("for_selection") is False, "requires budget.for_selection=false")
    _require(
        str(budget.get("contact_type")) == "official_validation_seed_addendum",
        "budget.contact_type must be official_validation_seed_addendum",
    )

    reporting = require_mapping(config["predeclared_reporting"], "predeclared_reporting")
    _require(
        reporting.get("report_all_addendum_seeds_regardless_of_outcome") is True,
        "requires predeclared_reporting.report_all_addendum_seeds_regardless_of_outcome=true",
    )
    _require(
        str(reporting.get("interpretation")) == "descriptive_dispersion_evidence_only",
        "predeclared_reporting.interpretation must be descriptive_dispersion_evidence_only",
    )

    identity = require_mapping(config["frozen_primary_identity"], "frozen_primary_identity")
    for key in ("candidate_id", "feature_set", "window_size", "model_family", "probe_id", "hpo_profile_id"):
        _require(bool(identity.get(key)), f"frozen_primary_identity.{key} is required")
    _require(
        str(identity["model_family"]) == "tcn" and str(identity["probe_id"]) == "tcn_tiny",
        "scoped to the frozen tcn_tiny primary only, got "
        f"family={identity.get('model_family')!r} probe_id={identity.get('probe_id')!r}",
    )

    config_inputs = require_mapping(config["inputs"], "inputs")
    stage02_run_id = str(config_inputs.get("stage02_run_id") or "")
    superseded = {str(v) for v in config_inputs.get("superseded_stage02_run_ids", [])}
    _require(
        bool(stage02_run_id) and "<" not in stage02_run_id and stage02_run_id not in superseded,
        f"inputs.stage02_run_id must pin the superseding Stage 02 run id, got {stage02_run_id!r}",
    )


def _verify_entry_gates(config: Mapping[str, Any]) -> _AddendumInputs:
    """Fail-closed verification of the identical frozen Stage 00->01->02 chain
    the predeclared Stage 03 readout consumed (same gates, same artifacts)."""
    inputs = require_mapping(config["inputs"], "inputs")
    stage00_paths = require_artifacts(
        Path(str(inputs["stage00_runtime_run_dir"])), inputs["required_stage00_artifacts"]
    )
    stage01_paths = require_artifacts(
        Path(str(inputs["stage01_runtime_run_dir"])), inputs["required_stage01_artifacts"]
    )
    stage02_paths = require_artifacts(
        Path(str(inputs["stage02_runtime_run_dir"])), inputs["required_stage02_artifacts"]
    )
    stage00_manifest = read_json_object(stage00_paths["run_manifest.json"])
    raw_manifest = read_json_object(stage00_paths["raw_data_manifest.json"])
    split_freeze = read_json_object(stage00_paths["split_freeze.json"])
    stage01_manifest = read_json_object(stage01_paths["run_manifest.json"])
    stage01_handoff = read_json_object(stage01_paths["01_candidate_inputs.json"])
    stage01_summary = load_stage01_summary(stage01_paths["01_feature_window_search_summary.csv"])
    stage02_manifest = read_json_object(stage02_paths["run_manifest.json"])
    stage02_handoff = read_json_object(stage02_paths["02_stage03_handoff.json"])
    frozen_candidate = read_json_object(stage02_paths["02_frozen_candidate.json"])

    require_distinct_file_hashes(
        stage02_paths["02_hpo_plan_ledger.csv"],
        stage02_paths["02_hpo_trial_ledger.csv"],
        blocked_label=f"{STAGE_NAME} blocked: Stage 02 plan ledger is byte-identical to the trial ledger",
        reason="a copied plan ledger is the pre-6182508 packaging defect signature",
    )
    expected00, expected01 = str(inputs["stage00_run_id"]), str(inputs["stage01_run_id"])
    require_run_id_chain(
        [
            ("01_candidate_inputs.json source_stage00_run_id", expected00, stage01_handoff.get("source_stage00_run_id")),
            ("02_stage03_handoff.json source_stage00_run_id", expected00, stage02_handoff.get("source_stage00_run_id")),
            ("02_stage03_handoff.json source_stage01_run_id", expected01, stage02_handoff.get("source_stage01_run_id")),
            ("stage02 run_manifest.json source_stage01_run_id", expected01, stage02_manifest.get("source_stage01_run_id")),
            ("02_frozen_candidate.json source_stage00_run_id", expected00, frozen_candidate.get("source_stage00_run_id")),
            ("02_frozen_candidate.json source_stage01_run_id", expected01, frozen_candidate.get("source_stage01_run_id")),
        ],
        stage_label=STAGE_NAME,
    )
    feature_rebuild_fields = feature_rebuild_gate_fields(
        stage02_manifest,
        source_field="stage02_feature_rebuild_code_sha256",
        stage_label=STAGE_NAME,
        current_field="v2sa_feature_rebuild_code_sha256",
        legacy_reason="stage02_manifest_field_missing_legacy_run",
    )
    labelled = [
        ("stage00 run_manifest.json", stage00_manifest),
        ("stage01 run_manifest.json", stage01_manifest),
        ("stage02 run_manifest.json", stage02_manifest),
        ("01_candidate_inputs.json", stage01_handoff),
        ("02_stage03_handoff.json", stage02_handoff),
        ("02_frozen_candidate.json", frozen_candidate),
    ]
    require_safety_flags(labelled, stage_label=STAGE_NAME, field="holdout_test_contact", expected=False)
    require_safety_flags(
        labelled[2:], stage_label=STAGE_NAME, field="official_validation_for_selection", expected=False
    )
    _require(
        stage02_handoff.get("ready_for_stage03") is True,
        "blocked: 02_stage03_handoff.json does not record ready_for_stage03=true; "
        "the addendum may only score the frozen readout chain",
    )
    seed_policy = require_mapping(frozen_candidate.get("seed_policy", {}), "frozen_candidate.seed_policy")
    frozen_seeds = [int(s) for s in seed_policy.get("train_inner_seeds", [])]
    _require(
        frozen_seeds == PREDECLARED_SEEDS,
        f"expects frozen seed_policy.train_inner_seeds == {PREDECLARED_SEEDS}, got {frozen_seeds}",
    )
    primary_selection = _require_frozen_identity(config, stage02_handoff)

    return _AddendumInputs(
        stage00_paths=stage00_paths, stage01_paths=stage01_paths, stage02_paths=stage02_paths,
        stage01_handoff=stage01_handoff, stage01_summary=stage01_summary,
        primary_selection=primary_selection, raw_manifest=raw_manifest,
        split_freeze=split_freeze, feature_rebuild_fields=feature_rebuild_fields,
    )


def _require_frozen_identity(
    config: Mapping[str, Any], stage02_handoff: Mapping[str, Any]
) -> Mapping[str, Any]:
    """Spec-identity bind: the scored selection is the frozen Stage 02 primary
    candidate, field-for-field equal to the config-declared identity."""
    primary = require_mapping(stage02_handoff["primary_candidate"], "stage02_handoff.primary_candidate")
    identity = require_mapping(config["frozen_primary_identity"], "frozen_primary_identity")
    for key, cast in (
        ("candidate_id", str), ("feature_set", str), ("window_size", int),
        ("model_family", str), ("hpo_profile_id", str),
    ):
        _require(
            cast(primary[key]) == cast(identity[key]),
            f"frozen-identity mismatch on {key}: config declares {cast(identity[key])!r}, "
            f"02_stage03_handoff.json primary_candidate records {cast(primary[key])!r}",
        )
    require_mapping(primary["hpo_profile_params"], "primary_candidate.hpo_profile_params")
    return primary


def _require_pre_holdout_rows(
    frame: pd.DataFrame, columns: list[str], holdout_start: pd.Timestamp, label: str
) -> None:
    """Date-bound gate: no row at or after the closed holdout boundary may
    enter the addendum in any timestamp column (post-2017 rows never touched)."""
    for column in columns:
        if column not in frame.columns:
            continue
        max_value = pd.to_datetime(frame[column]).max()
        _require(
            pd.isna(max_value) or max_value < holdout_start,
            f"blocked: {label} column {column!r} reaches {max_value} >= "
            f"closed_holdout_test_start {holdout_start.date().isoformat()}",
        )


def _require_frozen_date_bounds(
    config: Mapping[str, Any], split_freeze: Mapping[str, Any]
) -> Mapping[str, Any]:
    """split_freeze.json must carry exactly the config-declared boundaries."""
    bounds = require_mapping(config["date_bounds"], "date_bounds")
    for config_key, freeze_key in (
        ("train_start", "train_start"), ("train_end_exclusive", "train_end"),
        ("validation_start", "validation_start"), ("validation_end_exclusive", "validation_end"),
        ("closed_holdout_test_start", "closed_holdout_test_start"),
    ):
        expected = pd.Timestamp(str(bounds[config_key]))
        observed = pd.Timestamp(str(split_freeze.get(freeze_key)))
        _require(
            observed == expected,
            f"date-bound mismatch: split_freeze.json {freeze_key}={observed} != "
            f"config date_bounds.{config_key}={expected}",
        )
    return bounds


def _load_and_prepare_data(config: Mapping[str, Any], inputs: _AddendumInputs) -> _PreparedData:
    """Identical frozen data path as Stage 03: event index -> split filter ->
    bar rebuild -> feature frame -> window datasets -> Stage 01 parity ->
    materialized matrices, with the post-2017 date-bound gates added."""
    config_inputs = require_mapping(config["inputs"], "inputs")
    bounds = _require_frozen_date_bounds(config, inputs.split_freeze)
    holdout_start = pd.Timestamp(str(bounds["closed_holdout_test_start"]))

    sample_events = load_sample_event_index(inputs.stage00_paths["sample_event_index.csv"])
    train_events = valid_events_for_split(sample_events, "train")
    validation_events = valid_events_for_split(sample_events, "validation")
    event_columns = ["target_timestamp", "horizon_end_timestamp"]
    _require_pre_holdout_rows(train_events, event_columns, holdout_start, "eligible train events")
    _require_pre_holdout_rows(
        validation_events, event_columns, holdout_start, "eligible official-validation events"
    )
    bars = load_train_validation_bars(inputs.raw_manifest, inputs.split_freeze, config_inputs)
    _require_pre_holdout_rows(bars, ["timestamp"], holdout_start, "rebuilt train/validation bars")
    feature_frame = build_feature_frame(bars)
    _require_pre_holdout_rows(feature_frame, ["timestamp"], holdout_start, "feature frame")

    selection = inputs.primary_selection
    feature_columns = _resolve_candidate_feature_columns(selection, inputs.stage01_handoff)
    require_feature_columns(feature_columns, feature_frame)
    window_kwargs = {
        "feature_set": str(selection["feature_set"]),
        "feature_columns": feature_columns,
        "window_size": int(selection["window_size"]),
    }
    train_dataset = build_window_dataset(feature_frame, train_events, **window_kwargs)
    validate_rebuilt_candidate_counts(
        {"candidate_id": selection["candidate_id"],
         "feature_columns": list(train_dataset.feature_columns)},
        train_dataset,
        inputs.stage01_summary,
    )
    validation_dataset = build_window_dataset(feature_frame, validation_events, **window_kwargs)
    _require(
        not validation_dataset.metadata.empty,
        "produced no eligible official-validation window rows",
    )
    _require_pre_holdout_rows(
        validation_dataset.metadata, ["target_timestamp"], holdout_start,
        "official-validation window metadata",
    )
    train_meta = train_dataset.metadata.reset_index(drop=True)
    eval_meta = validation_dataset.metadata.reset_index(drop=True)
    return _PreparedData(
        train_meta=train_meta, eval_meta=eval_meta,
        x_train=materialize_window_matrix(train_dataset, np.arange(len(train_dataset.metadata))),
        x_eval=materialize_window_matrix(
            validation_dataset, np.arange(len(validation_dataset.metadata))
        ),
        feature_columns=tuple(train_dataset.feature_columns),
        train_sample_id_hash=sample_id_hash(train_meta["sample_id"].tolist()),
        eval_sample_id_hash=sample_id_hash(eval_meta["sample_id"].tolist()),
    )


def _resolve_candidate_feature_columns(
    selection: Mapping[str, Any], stage01_handoff: Mapping[str, Any]
) -> tuple[str, ...]:
    candidate_id = str(selection["candidate_id"])
    for entry in stage01_handoff.get("candidate_inputs", []):
        entry_mapping = require_mapping(entry, "candidate_input")
        if str(entry_mapping.get("candidate_id")) == candidate_id:
            return tuple(str(column) for column in entry_mapping["feature_columns"])
    raise ValueError(
        f"{STAGE_NAME} cannot resolve feature_columns: 01_candidate_inputs.json has no "
        f"candidate_inputs entry for candidate_id {candidate_id!r}"
    )


def _score_one_seed(
    selection: Mapping[str, Any],
    prep: _PreparedData,
    seed: int,
    config: Mapping[str, Any],
    ledger: _AddendumLedger,
) -> None:
    """One addendum seed: same-row registry baselines (per-seed draws, Stage 03
    dummy convention), the mechanism-frozen torch refit, then exactly one
    scoring event when the refit completed. A failed refit is recorded as a
    failed row (reported, never suppressed) and the loop continues."""
    baseline_ids = [
        str(v) for v in require_mapping(config["baseline_controls"], "baseline_controls")["mandatory"]
    ]
    _require(bool(baseline_ids), "baseline_controls.mandatory must list the registry baselines")
    y_train = prep.train_meta["label"].to_numpy(dtype=int)
    y_eval = prep.eval_meta["label"].to_numpy(dtype=int)
    baseline_scores = {
        baseline_id: metrics.score_registry_baseline(baseline_id, y_train, y_eval, seed)
        for baseline_id in baseline_ids
    }
    for baseline_id, score in baseline_scores.items():
        ledger.baseline_rows.append(_baseline_row(selection, seed, baseline_id, score, prep))

    family = str(selection["model_family"])
    _require(
        family in fitting.PROBE_BY_FAMILY and family != "lightgbm",
        f"refit family must be a torch probe family, got {family!r}",
    )
    profile = {
        "profile_id": str(selection["hpo_profile_id"]),
        **require_mapping(selection["hpo_profile_params"], "hpo_profile_params"),
    }
    # Mechanism-frozen refit through the shared tested wrapper (also used by the
    # Stage 04 controls and the synthetic positive control): profile params as
    # fixed defaults + the frozen chronological-tail early stopping.
    outcome = fitting.fit_stage_control(
        fitting.PROBE_BY_FAMILY[family], profile, prep.x_train, prep.train_meta, prep.x_eval,
        config, int(seed), int(selection["window_size"]), len(prep.feature_columns),
    )
    ledger.refit_records.append(
        {
            "candidate_role": "primary", "candidate_id": str(selection["candidate_id"]),
            "seed": int(seed), "fit_status": str(outcome.get("fit_status", "failed_unknown")),
            "error_message": str(outcome.get("error_message", "")),
            **{key: outcome.get(key) for key in OUTCOME_PASSTHROUGH_KEYS},
        }
    )
    if outcome.get("fit_status") != "completed":
        ledger.readout_rows.append(_readout_row(selection, prep, seed, outcome))
        return
    _record_completed_scoring(selection, prep, seed, outcome, baseline_scores, ledger)


def _record_completed_scoring(
    selection: Mapping[str, Any],
    prep: _PreparedData,
    seed: int,
    outcome: Mapping[str, Any],
    baseline_scores: Mapping[str, Mapping[str, Any]],
    ledger: _AddendumLedger,
) -> None:
    predictions = np.asarray(outcome["predictions"], dtype=int)
    scores = np.asarray(outcome["scores"], dtype=float)
    # Predictions for official-validation rows now exist: this IS the scoring
    # event, counted before any metric arithmetic.
    ledger.scoring_events.append(
        {
            "candidate_role": "primary", "candidate_id": str(selection["candidate_id"]),
            "seed": int(seed), "n_rows": int(len(prep.eval_meta)),
            "contact_type": "official_validation_seed_addendum", "for_selection": False,
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
    row = _readout_row(selection, prep, seed, outcome)
    row.update(scored)
    row.update(per_class)
    row.update(
        {
            "baseline_macro_f1_stratified_dummy_train_prior": float(dummy["macro_f1"]),
            "baseline_macro_f1_majority_train_prior": float(majority["macro_f1"]),
            "delta_macro_f1_vs_stratified_dummy_train_prior": float(scored["macro_f1"] - dummy["macro_f1"]),
            "delta_macro_f1_vs_majority_train_prior": float(scored["macro_f1"] - majority["macro_f1"]),
            "delta_balanced_accuracy_vs_stratified_dummy_train_prior": float(
                scored["balanced_accuracy"] - dummy["balanced_accuracy"]
            ),
            "positive_ticker_count": int(positive_ticker_count),
        }
    )
    ledger.readout_rows.append(row)
    ledger.ticker_deltas.append({"seed": int(seed), "deltas": dict(dummy_deltas)})
    ledger.per_ticker_rows.extend(
        _per_ticker_rows(selection, seed, prep.eval_meta, predictions, dummy_deltas, majority_deltas)
    )
    ledger.prediction_frames.append(
        _prediction_frame(selection, seed, prep.eval_meta, predictions, scores)
    )


def _readout_row(
    selection: Mapping[str, Any], prep: _PreparedData, seed: int, outcome: Mapping[str, Any]
) -> dict[str, Any]:
    row: dict[str, Any] = {column: None for column in VALIDATION_READOUT_COLUMNS}
    row.update(
        {
            "candidate_role": "primary", "candidate_id": str(selection["candidate_id"]),
            "feature_set": str(selection["feature_set"]),
            "window_size": int(selection["window_size"]),
            "model_family": str(selection["model_family"]),
            "hpo_profile_id": str(selection["hpo_profile_id"]), "seed": int(seed),
            "n_refit_train_samples": int(len(prep.train_meta)),
            "n_scored_validation_samples": int(len(prep.eval_meta)),
            "train_sample_id_hash": prep.train_sample_id_hash,
            "eval_sample_id_hash": prep.eval_sample_id_hash,
            "early_stopping_train_sample_id_hash": outcome.get("early_stopping_train_sample_id_hash", ""),
            "early_stopping_eval_sample_id_hash": outcome.get("early_stopping_eval_sample_id_hash", ""),
            "fit_status": str(outcome.get("fit_status", "failed_unknown")),
            "error_message": str(outcome.get("error_message", "")),
            "scope": ROW_SCOPE,
            **{key: outcome.get(key) for key in OUTCOME_PASSTHROUGH_KEYS},
        }
    )
    return row


def _baseline_row(
    selection: Mapping[str, Any], seed: int, baseline_id: str,
    score: Mapping[str, Any], prep: _PreparedData,
) -> dict[str, Any]:
    return {
        "candidate_role": "primary", "candidate_id": str(selection["candidate_id"]),
        "seed": int(seed), "baseline_id": baseline_id, "fit_status": score["fit_status"],
        "n_train_samples": int(len(prep.train_meta)), "n_eval_samples": int(len(prep.eval_meta)),
        "train_sample_id_hash": prep.train_sample_id_hash,
        "eval_sample_id_hash": prep.eval_sample_id_hash,
        "sample_id_hash": prep.eval_sample_id_hash,
        "macro_f1": score["macro_f1"], "balanced_accuracy": score["balanced_accuracy"],
        "accuracy": score["accuracy"], "roc_auc": score["roc_auc"], "mcc": score["mcc"],
        "error_message": score["error_message"], "scope": ROW_SCOPE,
    }


def _per_ticker_rows(
    selection: Mapping[str, Any], seed: int, eval_meta: pd.DataFrame,
    predictions: np.ndarray, dummy_deltas: Mapping[str, float],
    majority_deltas: Mapping[str, float],
) -> list[dict[str, Any]]:
    y_eval = eval_meta["label"].to_numpy(dtype=int)
    indexed = eval_meta.assign(_position=np.arange(len(eval_meta)))
    rows: list[dict[str, Any]] = []
    for ticker, group in indexed.groupby("ticker", sort=True):
        positions = group["_position"].to_numpy(dtype=int)
        scored = metrics.classification_metrics(y_eval[positions], predictions[positions])
        per_class = metrics.per_class_metrics(y_eval[positions], predictions[positions])
        rows.append(
            {
                "candidate_role": "primary", "candidate_id": str(selection["candidate_id"]),
                "seed": int(seed), "ticker": str(ticker), "n_rows": int(len(positions)),
                "support_up": per_class["support_up"], "support_down": per_class["support_down"],
                "macro_f1": scored["macro_f1"], "balanced_accuracy": scored["balanced_accuracy"],
                "accuracy": scored["accuracy"], "f1_up": per_class["f1_up"],
                "f1_down": per_class["f1_down"],
                "delta_macro_f1_vs_stratified_dummy_train_prior": dummy_deltas[str(ticker)],
                "delta_macro_f1_vs_majority_train_prior": majority_deltas[str(ticker)],
                "scope": ROW_SCOPE,
            }
        )
    return rows


def _prediction_frame(
    selection: Mapping[str, Any], seed: int, eval_meta: pd.DataFrame,
    predictions: np.ndarray, scores: np.ndarray,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "candidate_role": "primary", "candidate_id": str(selection["candidate_id"]),
            "model_family": str(selection["model_family"]),
            "hpo_profile_id": str(selection["hpo_profile_id"]), "seed": int(seed),
            "sample_id": eval_meta["sample_id"].to_numpy(),
            "ticker": eval_meta["ticker"].to_numpy(),
            "target_timestamp": eval_meta["target_timestamp"].to_numpy(),
            "trading_day": eval_meta["trading_day"].to_numpy(),
            "y_true": eval_meta["label"].to_numpy(dtype=int),
            "p_up": np.asarray(scores, dtype=float),
            "y_pred": np.asarray(predictions, dtype=int),
            "scope": ROW_SCOPE,
        }
    )[VALIDATION_PREDICTION_COLUMNS]


def _to_plain(value: Any) -> Any:
    """Plain-Python conversion so a resume round-trips numerics."""
    if isinstance(value, dict):
        return {str(key): _to_plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def _purge_failed_seed_rows(ledger: _AddendumLedger, seed: int) -> None:
    """Drop a retried seed's failed rows before re-scoring it (resume path);
    completed rows are protected by the scoring-event skip."""

    def keep(row: Mapping[str, Any]) -> bool:
        return not (int(row.get("seed", -1)) == seed and str(row.get("fit_status")) != "completed")

    ledger.readout_rows = [row for row in ledger.readout_rows if keep(row)]
    ledger.refit_records = [record for record in ledger.refit_records if keep(record)]
    ledger.baseline_rows = [row for row in ledger.baseline_rows if int(row.get("seed", -1)) != seed]


def _write_seed_checkpoint(
    config: Mapping[str, Any], run_id: str, seeds: list[int], ledger: _AddendumLedger
) -> None:
    """Per-seed recovery checkpoint (recovery state only, never evidence)."""
    checkpointing = config.get("checkpointing", {})
    if not isinstance(checkpointing, Mapping) or checkpointing.get("enabled") is not True:
        return
    checkpoint_dir = Path(str(checkpointing["checkpoint_dir"])) / run_id
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(ledger.readout_rows, columns=VALIDATION_READOUT_COLUMNS).to_csv(
        checkpoint_dir / "v2sa_validation_readout_partial.csv", index=False
    )
    pd.DataFrame(ledger.baseline_rows, columns=SAME_ROW_BASELINE_COLUMNS).to_csv(
        checkpoint_dir / "v2sa_same_row_baselines_partial.csv", index=False
    )
    _concat_predictions(ledger.prediction_frames).to_csv(
        checkpoint_dir / "v2sa_validation_predictions_partial.csv", index=False
    )
    write_json(
        checkpoint_dir / "v2sa_ledger_state_partial.json",
        _to_plain(
            {
                "stage_name": STAGE_NAME, "run_id": run_id,
                "readout_rows": ledger.readout_rows,
                "per_ticker_rows": ledger.per_ticker_rows,
                "baseline_rows": ledger.baseline_rows,
                "scoring_events": ledger.scoring_events,
                "refit_records": ledger.refit_records,
                "ticker_deltas": ledger.ticker_deltas,
            }
        ),
    )
    completed_seeds = [int(event["seed"]) for event in ledger.scoring_events]
    write_json(
        checkpoint_dir / "checkpoint_manifest.json",
        {
            "stage_name": STAGE_NAME, "run_id": run_id, "status": "incomplete",
            "completed_seeds": completed_seeds,
            "pending_seeds": [int(s) for s in seeds if int(s) not in completed_seeds],
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
        },
    )


def _load_resume_state(
    config: Mapping[str, Any], primary_selection: Mapping[str, Any]
) -> tuple[str, _AddendumLedger] | None:
    """Exact-run resume: exact run id, exact checkpoint folder (name == run id,
    no parent scans), all required files, candidate and seed consistency."""
    resume = config.get("resume")
    if resume is None:
        return None
    resume = require_mapping(resume, "resume")
    if resume.get("enabled") is not True:
        return None
    run_id = str(resume.get("run_id") or "")
    _require(
        bool(RUN_ID_PATTERN.match(run_id)),
        f"resume.run_id must be an exact {STAGE_NAME} run id, got {run_id!r}",
    )
    checkpoint_dir = Path(str(resume.get("checkpoint_dir") or ""))
    _require(
        bool(str(resume.get("checkpoint_dir") or "")) and checkpoint_dir.name == run_id,
        f"resume.checkpoint_dir must end in the exact resume.run_id {run_id!r} "
        f"(no parent-folder scans): {checkpoint_dir}",
    )
    missing = [
        checkpoint_dir / name
        for name in RESUME_REQUIRED_CHECKPOINT_FILES
        if not (checkpoint_dir / name).exists()
    ]
    if missing:
        missing_text = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            f"missing required {STAGE_NAME} resume checkpoint files:\n{missing_text}"
        )
    state = read_json_object(checkpoint_dir / "v2sa_ledger_state_partial.json")
    manifest = read_json_object(checkpoint_dir / "checkpoint_manifest.json")
    for label, payload in (
        ("checkpoint_manifest.json", manifest), ("v2sa_ledger_state_partial.json", state),
    ):
        _require(
            str(payload.get("stage_name")) == STAGE_NAME and str(payload.get("run_id")) == run_id,
            f"resume {label} stage_name/run_id mismatch: "
            f"{payload.get('stage_name')!r}/{payload.get('run_id')!r}",
        )
    scoring_events = [dict(event) for event in state.get("scoring_events", [])]
    _require(
        bool(scoring_events),
        "resume checkpoint records zero scoring events; start a fresh run instead of a resume",
    )
    event_seeds = {int(event["seed"]) for event in scoring_events}
    _require(
        event_seeds <= set(EXPECTED_ADDENDUM_SEEDS),
        f"resume checkpoint seeds {sorted(event_seeds)} are not a subset of the "
        f"addendum seeds {EXPECTED_ADDENDUM_SEEDS}",
    )
    expected_candidate = str(primary_selection["candidate_id"])
    for event in scoring_events:
        _require(
            str(event.get("candidate_id")) == expected_candidate,
            f"resume checkpoint scoring events belong to candidate "
            f"{event.get('candidate_id')!r}, expected {expected_candidate!r}",
        )
    prediction_frame = pd.read_csv(checkpoint_dir / "v2sa_validation_predictions_partial.csv")
    ledger = _AddendumLedger(
        readout_rows=[dict(row) for row in state.get("readout_rows", [])],
        per_ticker_rows=[dict(row) for row in state.get("per_ticker_rows", [])],
        baseline_rows=[dict(row) for row in state.get("baseline_rows", [])],
        prediction_frames=(
            [prediction_frame[VALIDATION_PREDICTION_COLUMNS]] if len(prediction_frame) else []
        ),
        scoring_events=scoring_events,
        refit_records=[dict(record) for record in state.get("refit_records", [])],
        ticker_deltas=[dict(entry) for entry in state.get("ticker_deltas", [])],
    )
    return run_id, ledger


def _concat_predictions(frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame(columns=VALIDATION_PREDICTION_COLUMNS)
    return pd.concat(frames, ignore_index=True)[VALIDATION_PREDICTION_COLUMNS]


def _dispersion_summary_rows(
    ledger: _AddendumLedger, selection: Mapping[str, Any], config: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Predeclared descriptive summary: min/median/max (plus mean/std context)
    of the per-seed deltas and the positive-delta seed counts. All seeds are
    reported regardless of outcome; there is no pass/fail judging."""
    completed = [row for row in ledger.readout_rows if row["fit_status"] == "completed"]
    reporting = require_mapping(config["predeclared_reporting"], "predeclared_reporting")
    seeds = [int(seed) for seed in require_mapping(config["readout"], "readout")["addendum_seeds"]]
    row: dict[str, Any] = {column: None for column in SEED_DISPERSION_SUMMARY_COLUMNS}
    row.update(
        {
            "candidate_id": str(selection["candidate_id"]),
            "model_family": str(selection["model_family"]),
            "hpo_profile_id": str(selection["hpo_profile_id"]),
            "seed_rule": SEED_RULE_ID,
            "n_addendum_seeds": len(seeds),
            "n_completed_seeds": len(completed),
            "n_failed_seeds": len(seeds) - len(completed),
            "interpretation": str(reporting["interpretation"]),
            "canonical_readout": str(reporting["canonical_readout"]),
            "scope": ROW_SCOPE,
        }
    )
    if completed:
        arrays = {
            "macro_f1": np.asarray([r["macro_f1"] for r in completed], dtype=float),
            "delta_macro_f1_vs_stratified_dummy_train_prior": np.asarray(
                [r["delta_macro_f1_vs_stratified_dummy_train_prior"] for r in completed], dtype=float
            ),
            "delta_macro_f1_vs_majority_train_prior": np.asarray(
                [r["delta_macro_f1_vs_majority_train_prior"] for r in completed], dtype=float
            ),
            "positive_ticker_count": np.asarray(
                [r["positive_ticker_count"] for r in completed], dtype=float
            ),
        }
        for name, values in arrays.items():
            for stat, fn in (("min", np.min), ("median", np.median), ("max", np.max)):
                key = f"{stat}_{name}"
                if key in row:
                    row[key] = float(fn(values))
        macro = arrays["macro_f1"]
        dummy = arrays["delta_macro_f1_vs_stratified_dummy_train_prior"]
        row.update(
            {
                "mean_macro_f1": float(macro.mean()),
                "std_macro_f1": float(macro.std(ddof=1)) if len(macro) > 1 else None,
                "mean_delta_macro_f1_vs_stratified_dummy_train_prior": float(dummy.mean()),
                "n_seeds_delta_vs_stratified_dummy_positive": int((dummy > 0).sum()),
                "n_seeds_delta_vs_majority_positive": int(
                    (arrays["delta_macro_f1_vs_majority_train_prior"] > 0).sum()
                ),
            }
        )
    return [row]


def _per_ticker_mean_deltas(ledger: _AddendumLedger) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for entry in ledger.ticker_deltas:
        for ticker, value in entry["deltas"].items():
            buckets.setdefault(str(ticker), []).append(float(value))
    return {ticker: float(np.mean(values)) for ticker, values in sorted(buckets.items())}


def _environment_snapshot() -> dict[str, Any]:
    import importlib.metadata as importlib_metadata
    import platform

    versions: dict[str, Any] = {}
    for package in ("numpy", "pandas", "scikit-learn", "torch", "PyYAML"):
        try:
            versions[package] = importlib_metadata.version(package)
        except importlib_metadata.PackageNotFoundError:
            versions[package] = None
    return {"python_version": platform.python_version(), "package_versions": versions}


def _device_fields(refit_records: list[dict[str, Any]]) -> dict[str, Any]:
    """AGENTS.md device provenance aggregated from completed refit outcomes."""
    completed = [record for record in refit_records if record["fit_status"] == "completed"]
    if not completed:
        return {
            "requested_device": "not_resolved", "resolved_device": "not_resolved",
            "cuda_available": False, "gpu_name_or_null": None,
            "device_fallback_reason": "no_refits_completed",
        }
    def uniques(key: str) -> list[str]:
        return sorted({str(r[key]) for r in completed if r[key]})

    resolved_device = ",".join(uniques("resolved_device")) or "not_resolved"
    cuda_resolved = any(value.strip().startswith("cuda") for value in resolved_device.split(","))
    runtime_fields = (
        torch_runtime_device_fields()
        if cuda_resolved
        else {"cuda_available": False, "gpu_name_or_null": None}
    )
    cuda_available = bool(runtime_fields["cuda_available"] or cuda_resolved)
    return {
        "requested_device": ",".join(uniques("requested_device")) or "not_resolved",
        "resolved_device": resolved_device,
        "cuda_available": cuda_available,
        "gpu_name_or_null": runtime_fields["gpu_name_or_null"] if cuda_available else None,
        "device_fallback_reason": ",".join(uniques("device_fallback_reason")),
    }


def _decision_record(
    config: Mapping[str, Any], ledger: _AddendumLedger, run_id: str, resumed: bool
) -> dict[str, Any]:
    config_inputs = require_mapping(config["inputs"], "inputs")
    seeds = [int(seed) for seed in require_mapping(config["readout"], "readout")["addendum_seeds"]]
    completed_seeds = sorted({int(event["seed"]) for event in ledger.scoring_events})
    per_seed_keys = (
        "candidate_id", "seed", "fit_status", "macro_f1", "balanced_accuracy",
        "delta_macro_f1_vs_stratified_dummy_train_prior",
        "delta_macro_f1_vs_majority_train_prior", "positive_ticker_count", "error_message",
    )
    return {
        "route": config["route"], "stage_name": STAGE_NAME, "scope": config["scope"],
        "run_id": run_id, "evidence_status": str(config["evidence_status"]),
        "source_stage00_run_id": str(config_inputs["stage00_run_id"]),
        "source_stage01_run_id": str(config_inputs["stage01_run_id"]),
        "source_stage02_run_id": str(config_inputs["stage02_run_id"]),
        "canonical_stage03_run_id": str(config_inputs["canonical_stage03_run_id"]),
        "seed_rule": SEED_RULE_ID,
        "addendum_seeds": seeds,
        "predeclared_seeds_never_rerun": PREDECLARED_SEEDS,
        "predeclared_reporting": dict(
            require_mapping(config["predeclared_reporting"], "predeclared_reporting")
        ),
        "per_seed_outcomes": [
            {key: row.get(key) for key in per_seed_keys} for row in ledger.readout_rows
        ],
        "per_ticker_mean_delta_macro_f1_vs_stratified_dummy_train_prior": (
            _per_ticker_mean_deltas(ledger)
        ),
        "readout_complete": set(seeds) <= set(completed_seeds),
        "official_validation_scoring_events": len(ledger.scoring_events),
        "scoring_event_ledger": list(ledger.scoring_events),
        "refit_records": list(ledger.refit_records),
        "resumed_from_checkpoint": resumed,
        "interpretation": "descriptive_dispersion_evidence_only",
        "merged_into_predeclared_readout": False,
        "canonical_readout_unchanged": True,
        "no_final_model_selected": True,
        "holdout_test_contact": False,
        "official_validation_for_selection": False,
    }


def _write_results(
    config: Mapping[str, Any],
    inputs: _AddendumInputs,
    prep: _PreparedData,
    ledger: _AddendumLedger,
    output_dir: Path,
    run_id: str,
    resumed: bool,
) -> SeedAddendumResult:
    outputs = require_mapping(config["outputs"], "outputs")
    config_inputs = require_mapping(config["inputs"], "inputs")
    budget = require_mapping(config["budget"], "budget")
    selection = inputs.primary_selection

    def out(key: str, default: str) -> Path:
        return output_dir / str(outputs.get(key, default))

    paths = {
        "validation_readout": out("validation_readout", "v2sa_validation_readout.csv"),
        "per_ticker_readout": out("per_ticker_readout", "v2sa_per_ticker_readout.csv"),
        "seed_dispersion_summary": out("seed_dispersion_summary", "v2sa_seed_dispersion_summary.csv"),
        "same_row_baselines": out("same_row_baselines", "v2sa_same_row_baselines.csv"),
        "validation_predictions": out("validation_predictions", "v2sa_validation_predictions.csv"),
        "budget_ledger_row": out("budget_ledger_row", "v2sa_budget_ledger_row.csv"),
    }
    pd.DataFrame(ledger.readout_rows, columns=VALIDATION_READOUT_COLUMNS).to_csv(
        paths["validation_readout"], index=False
    )
    pd.DataFrame(ledger.per_ticker_rows, columns=PER_TICKER_READOUT_COLUMNS).to_csv(
        paths["per_ticker_readout"], index=False
    )
    pd.DataFrame(
        _dispersion_summary_rows(ledger, selection, config),
        columns=SEED_DISPERSION_SUMMARY_COLUMNS,
    ).to_csv(paths["seed_dispersion_summary"], index=False)
    pd.DataFrame(ledger.baseline_rows, columns=SAME_ROW_BASELINE_COLUMNS).to_csv(
        paths["same_row_baselines"], index=False
    )
    _concat_predictions(ledger.prediction_frames).to_csv(paths["validation_predictions"], index=False)
    # The exact appendable Stage 05 budget-ledger row; the event count is
    # resolved from the recorded scoring events, never hand-typed.
    pd.DataFrame(
        [
            {
                "stage_name": STAGE_NAME, "run_id": run_id,
                "evidence_domain": "official_validation",
                "data_segment": str(budget["data_segment"]),
                "contact_type": str(budget["contact_type"]),
                "scoring_events": len(ledger.scoring_events), "for_selection": False,
                "notes": (
                    "disclosed post-hoc seed addendum on the frozen primary; scored once per "
                    "addendum seed; reported separately and never merged into the predeclared "
                    "n=2 readout (Dwork 2015 reusable-holdout budget)"
                ),
            }
        ],
        columns=BUDGET_LEDGER_ROW_COLUMNS,
    ).to_csv(paths["budget_ledger_row"], index=False)
    record_path = write_json(
        out("decision_record", "v2sa_decision_record.json"),
        _decision_record(config, ledger, run_id, resumed),
    )
    manifest_payload = {
        "route": config["route"], "stage_name": STAGE_NAME, "scope": config["scope"],
        "run_id": run_id,
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_status": str(config["evidence_status"]),
        "config_sha256": hash_mapping(config),
        "notebook_sha256": hash_file(resolve_repo_path(config_inputs["notebook_path"])),
        "source_stage00_run_id": str(config_inputs["stage00_run_id"]),
        "source_stage01_run_id": str(config_inputs["stage01_run_id"]),
        "source_stage02_run_id": str(config_inputs["stage02_run_id"]),
        "canonical_stage03_run_id": str(config_inputs["canonical_stage03_run_id"]),
        "superseded_stage02_run_ids": [
            str(value) for value in config_inputs.get("superseded_stage02_run_ids", [])
        ],
        "seed_rule": SEED_RULE_ID,
        "addendum_seeds": [int(seed) for seed in config["readout"]["addendum_seeds"]],
        "predeclared_seeds_never_rerun": PREDECLARED_SEEDS,
        "candidate_id": str(selection["candidate_id"]),
        "feature_set": str(selection["feature_set"]),
        "window_size": int(selection["window_size"]),
        "model_family": str(selection["model_family"]),
        "hpo_profile_id": str(selection["hpo_profile_id"]),
        "n_refit_train_samples": int(len(prep.train_meta)),
        "n_scored_validation_samples": int(len(prep.eval_meta)),
        "train_sample_id_hash": prep.train_sample_id_hash,
        "eval_sample_id_hash": prep.eval_sample_id_hash,
        "date_bounds": dict(require_mapping(config["date_bounds"], "date_bounds")),
        "max_scored_target_timestamp": pd.to_datetime(
            prep.eval_meta["target_timestamp"]
        ).max().isoformat(),
        "input_artifacts": [
            str(path)
            for paths_ in (inputs.stage00_paths, inputs.stage01_paths, inputs.stage02_paths)
            for path in paths_.values()
        ],
        "output_artifacts": [record_path.name, *[path.name for path in paths.values()]],
        "official_validation_contact": True,
        "official_validation_scoring_events": len(ledger.scoring_events),
        "official_validation_for_selection": False,
        "addendum_never_merged_into_predeclared_readout": True,
        "no_final_model_selected": True,
        "holdout_test_contact": False,
        "v2sa_readout_code_sha256": stage03_readout_code_sha256(),
        "raw_file_integrity": raw_manifest_integrity_summary(inputs.raw_manifest),
        **dict(inputs.feature_rebuild_fields),
        **_device_fields(ledger.refit_records),
        **_environment_snapshot(),
        **git_commit_fields(),
    }
    manifest_path = write_json(
        output_dir / str(outputs.get("manifest", "run_manifest.json")), manifest_payload
    )
    inventory_path = write_artifact_inventory(
        output_dir, {"run_manifest": manifest_path, "decision_record": record_path, **paths}
    )
    return SeedAddendumResult(
        output_dir=output_dir, run_manifest=manifest_path, artifact_inventory=inventory_path,
        decision_record=record_path,
        validation_readout=paths["validation_readout"],
        per_ticker_readout=paths["per_ticker_readout"],
        seed_dispersion_summary=paths["seed_dispersion_summary"],
        same_row_baselines=paths["same_row_baselines"],
        validation_predictions=paths["validation_predictions"],
        budget_ledger_row=paths["budget_ledger_row"],
    )
