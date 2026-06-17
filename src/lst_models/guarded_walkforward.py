"""V2.1 guarded, historically-contacted walk-forward readout on the
post-2017-01-25 closed segment, under the pre-registered rules in
docs/protocols/v2_1_guarded_walkforward_readout_protocol.md.

This module holds the stage-specific implementation behind the public
lst_models.stages.guarded_walkforward_readout.run_stage wrapper.
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
    read_json_object,
    require_artifacts,
    write_artifact_inventory,
    write_json,
)
from lst_models.config import hash_file, hash_mapping, require_mapping, resolve_repo_path
from lst_models.data import (
    raw_manifest_integrity_summary,
    read_raw_txt_file,
    resample_1min_to_5min,
    verify_raw_file_integrity,
)
from lst_models.device import torch_runtime_device_fields
from lst_models.features import build_feature_frame, require_feature_columns
from lst_models.labels import make_direction_labels
from lst_models.windows import (
    build_window_dataset,
    materialize_window_matrix,
    sample_id_hash,
)


SCOPE = "guarded_walkforward_readout"
READOUT_TIER = "guarded_historically_contacted"

WALKFORWARD_READOUT_COLUMNS = [
    "table_row_id", "row_kind",
    "candidate_id", "feature_set", "window_size",
    "model_family", "hpo_profile_id",
    "period_id", "period_start", "period_end_exclusive", "seed",
    "n_refit_train_samples", "n_scored_rows",
    "train_sample_id_hash", "eval_sample_id_hash",
    "macro_f1", "balanced_accuracy", "accuracy", "mcc", "roc_auc",
    "precision_down", "recall_down", "f1_down", "support_down",
    "precision_up", "recall_up", "f1_up", "support_up",
    "baseline_macro_f1_stratified_dummy_train_prior",
    "baseline_macro_f1_majority_train_prior",
    "delta_macro_f1_vs_stratified_dummy_train_prior",
    "delta_macro_f1_vs_majority_train_prior",
    "best_iteration", "early_stopping_source", "early_stopping_used",
    "early_stopping_reason",
    "requested_device", "resolved_device", "device_fallback_reason",
    "fit_status", "error_message", "scope", "readout_tier",
]
PER_TICKER_READOUT_COLUMNS = [
    "table_row_id", "period_id", "seed", "ticker", "n_rows",
    "support_up", "support_down", "macro_f1", "balanced_accuracy",
    "accuracy", "f1_up", "f1_down",
    "delta_macro_f1_vs_stratified_dummy_train_prior",
    "scope", "readout_tier",
]
PREDICTION_COLUMNS = [
    "table_row_id", "candidate_id", "model_family", "hpo_profile_id",
    "period_id", "seed", "sample_id", "ticker", "target_timestamp",
    "trading_day", "y_true", "p_up", "y_pred", "scope", "readout_tier",
]
# Per-row baseline (stratified_dummy_train_prior) predictions for the judged
# row, captured so the protocol row-pooled pooled_delta (§8 lines 508-511 --
# candidate + per-period baseline predictions concatenated across periods per
# seed) is reproducible from artifacts. The dummy is scored once at seeds[0]
# and reused for every candidate seed (finding F10); one baseline frame is
# emitted per (period, seed) the judged row is scored on so the per-seed
# row-union lines up 1:1 with the candidate rows.
BASELINE_PREDICTION_COLUMNS = [
    "baseline_id", "period_id", "seed", "sample_id", "ticker",
    "target_timestamp", "trading_day", "y_true", "p_up", "y_pred",
    "scope", "readout_tier",
]

REFIT_EARLY_STOPPING_KEYS = (
    "early_stopping_source",
    "early_stopping_used",
    "early_stopping_reason",
    "early_stopping_train_sample_id_hash",
    "early_stopping_eval_sample_id_hash",
)

RUN_ID_PATTERN = re.compile(r"^\d{8}_\d{6}_\d{6}$")

RESUME_CHECKPOINT_FILES = (
    "checkpoint_manifest.json",
    "v2_1_ledger_state_partial.json",
    "v2_1_walkforward_readout_partial.csv",
    "v2_1_same_row_baselines_partial.csv",
    "v2_1_predictions_partial.csv",
)


@dataclass(frozen=True)
class V21Result:
    output_dir: Path
    run_manifest: Path
    artifact_inventory: Path
    decision_record: Path
    walkforward_readout: Path | None = None
    per_ticker_readout: Path | None = None
    period_summary: Path | None = None
    comparison_table: Path | None = None
    same_row_baselines: Path | None = None
    predictions: Path | None = None
    period_registry: Path | None = None


@dataclass
class _WalkforwardLedger:
    readout_rows: list[dict[str, Any]] = field(default_factory=list)
    per_ticker_rows: list[dict[str, Any]] = field(default_factory=list)
    baseline_rows: list[dict[str, Any]] = field(default_factory=list)
    prediction_frames: list[pd.DataFrame] = field(default_factory=list)
    baseline_prediction_frames: list[pd.DataFrame] = field(default_factory=list)
    scoring_events: list[dict[str, Any]] = field(default_factory=list)
    refit_records: list[dict[str, Any]] = field(default_factory=list)
    completed_units: list[str] = field(default_factory=list)
    readout_complete: bool = False
    incomplete_reason: str = ""


@dataclass(frozen=True)
class _ResumeState:
    run_id: str
    checkpoint_dir: Path
    ledger: _WalkforwardLedger


def run_guarded_walkforward(config: Mapping[str, Any]) -> V21Result:
    _validate_config(config)
    inputs_map = _verify_entry_gates(config)

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

    data_context = _load_data_context(config, inputs_map)
    return _execute_walkforward(
        config=config,
        inputs_map=inputs_map,
        data_context=data_context,
        output_dir=output_dir,
        run_id=run_id,
        resume_state=resume_state,
    )


def _validate_config(config: Mapping[str, Any]) -> None:
    if config.get("stage_name") != "v2_1_guarded_walkforward_readout":
        raise ValueError(
            f"expected V2.1 config, got {config.get('stage_name')!r}"
        )
    if config.get("scope") != SCOPE:
        raise ValueError(f"expected scope {SCOPE!r}, got {config.get('scope')!r}")
    if config.get("holdout_test_contact") is not True:
        raise ValueError("V2.1 requires holdout_test_contact=true")
    if config.get("holdout_contact_tier") != READOUT_TIER:
        raise ValueError(f"V2.1 requires holdout_contact_tier={READOUT_TIER!r}")
    if config.get("clean_test_claim") is not False:
        raise ValueError("V2.1 requires clean_test_claim=false")
    if config.get("no_final_model_selected") is not True:
        raise ValueError("V2.1 requires no_final_model_selected=true")

    wf = require_mapping(config["walkforward"], "walkforward")
    seeds = wf.get("seeds")
    if not isinstance(seeds, list) or not seeds:
        raise ValueError("walkforward.seeds must be a non-empty list of integers")
    if wf.get("score_each_period_model_seed_exactly_once") is not True:
        raise ValueError("V2.1 requires score_each_period_model_seed_exactly_once=true")

    periods = wf.get("periods")
    if not isinstance(periods, list) or not periods:
        raise ValueError("walkforward.periods must be a non-empty list")
    if int(wf.get("period_count", -1)) != len(periods):
        raise ValueError("walkforward.period_count must match len(periods)")

    inputs = require_mapping(config["inputs"], "inputs")
    for key in (
        "stage00_run_id",
        "stage01_run_id",
        "stage02_run_id",
        "stage03_run_id",
    ):
        value = str(inputs.get(key, ""))
        if not value or "<" in value:
            raise ValueError(f"fill inputs.{key} before running V2.1")
    ordering = str(inputs.get("stage04_ordering", ""))
    if ordering == "stage04_first":
        if not str(inputs.get("stage04_run_id", "")) or "<" in str(inputs.get("stage04_run_id", "")):
            raise ValueError("fill inputs.stage04_run_id before running V2.1")
    elif ordering == "override_with_reason":
        reason = str(inputs.get("stage04_ordering_override_reason", ""))
        if not reason or "<" in reason:
            raise ValueError(
                "fill inputs.stage04_ordering_override_reason before running V2.1"
            )
    else:
        raise ValueError("inputs.stage04_ordering must be stage04_first or override_with_reason")

    signoff = require_mapping(config.get("sign_off"), "sign_off")
    if signoff.get("status") != "complete":
        raise ValueError("sign_off.status must be complete before running V2.1")
    for key in ("user_sign_off_date", "advisor_confirmation_reference"):
        value = str(signoff.get(key, ""))
        if not value or "<" in value:
            raise ValueError(f"fill sign_off.{key} before running V2.1")
    resolved = require_mapping(
        signoff.get("resolved_open_decisions"), "sign_off.resolved_open_decisions"
    )
    for key in (
        "OD-A_period_count_k",
        "OD-B_period_length_months",
        "OD-C_candidate_input_policy",
        "OD-D_ablation_rows_included",
        "OD-E_stage04_ordering",
        "OD-F_criteria_accepted",
    ):
        if key not in resolved:
            raise ValueError(f"fill sign_off.resolved_open_decisions.{key}")

    coverage = require_mapping(config.get("coverage_probe"), "coverage_probe")
    if coverage.get("authorization") != "approved_after_sign_off":
        raise ValueError(
            "coverage_probe.authorization must be approved_after_sign_off"
        )
    if str(coverage.get("artifact", "")) != "v2_1_coverage_probe.json":
        raise ValueError("coverage_probe.artifact must be v2_1_coverage_probe.json")
    sha = str(coverage.get("artifact_sha256") or "")
    if len(sha) != 64 or "<" in sha:
        raise ValueError("fill coverage_probe.artifact_sha256 before running V2.1")
    timestamp = str(coverage.get("probe_timestamp_utc") or "")
    if not timestamp or "<" in timestamp:
        raise ValueError("fill coverage_probe.probe_timestamp_utc before running V2.1")

    roster = require_mapping(config["model_roster"], "model_roster")
    model_rows = roster.get("model_rows")
    if not isinstance(model_rows, list) or not model_rows:
        raise ValueError("model_roster.model_rows must be non-empty")

    criteria = require_mapping(
        config["predeclared_criteria"], "predeclared_criteria"
    )
    if int(criteria.get("positive_period_count_minimum", -1)) < 1:
        raise ValueError(
            "predeclared_criteria.positive_period_count_minimum must be >= 1"
        )


def _expected_scoring_unit_keys(config: Mapping[str, Any]) -> list[str]:
    wf = require_mapping(config["walkforward"], "walkforward")
    roster = require_mapping(config["model_roster"], "model_roster")
    return [
        f"{period['period_id']}:{model['table_row_id']}:{int(seed)}"
        for period in wf["periods"]
        for model in roster["model_rows"]
        for seed in wf["seeds"]
    ]


def _checkpoint_manifest_payload(
    config: Mapping[str, Any], run_id: str, ledger: _WalkforwardLedger,
) -> dict[str, Any]:
    expected_units = _expected_scoring_unit_keys(config)
    completed = list(dict.fromkeys(ledger.completed_units))
    completed_set = set(completed)
    pending = [unit for unit in expected_units if unit not in completed_set]
    return {
        "stage_name": "v2_1_guarded_walkforward_readout",
        "run_id": run_id,
        "status": "incomplete",
        "completed_units": completed,
        "completed_units_count": len(completed),
        "pending_units": pending,
        "pending_units_count": len(pending),
        "resume_instructions": {
            "resume_mode": "exact_run_checkpoint_only",
            "required_run_id": run_id,
        },
        "holdout_test_contact": True,
        "holdout_contact_tier": READOUT_TIER,
        "checkpoint_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


def _protocol_provenance_fields(config: Mapping[str, Any]) -> dict[str, Any]:
    inputs = require_mapping(config["inputs"], "inputs")
    protocol_path = str(
        inputs.get(
            "protocol_path",
            "docs/protocols/v2_1_guarded_walkforward_readout_protocol.md",
        )
    )
    protocol_sha256 = hash_file(resolve_repo_path(protocol_path))
    signoff = dict(require_mapping(config["sign_off"], "sign_off"))
    coverage_probe = dict(require_mapping(config["coverage_probe"], "coverage_probe"))
    return {
        "stage04_run_id_or_ordering_override": {
            "stage04_run_id": inputs.get("stage04_run_id"),
            "stage04_ordering": inputs.get("stage04_ordering"),
            "stage04_ordering_override_reason": inputs.get(
                "stage04_ordering_override_reason"
            ),
        },
        "protocol_reference": {
            "path": protocol_path,
            "sha256": protocol_sha256,
        },
        "protocol_sha256": protocol_sha256,
        "sign_off": signoff,
        "coverage_probe": coverage_probe,
        "walkforward_training_contact_disclosure": (
            "Official-validation rows from Stage 03 are used as V2.1 training "
            "rows only after guarded pre-registration sign-off; every scored "
            "row is in the later walk-forward period."
        ),
        "holdout_contact_authorization": {
            "protocol": protocol_path,
            "sign_off_date": signoff.get("user_sign_off_date"),
        },
        "official_validation_used_as_training_rows": True,
    }


def _verify_entry_gates(config: Mapping[str, Any]) -> dict[str, Any]:
    inputs = require_mapping(config["inputs"], "inputs")
    s00_dir = Path(str(inputs["stage00_runtime_run_dir"]))
    s01_dir = Path(str(inputs["stage01_runtime_run_dir"]))
    s02_dir = Path(str(inputs["stage02_runtime_run_dir"]))
    s03_dir = Path(str(inputs["stage03_runtime_run_dir"]))

    require_artifacts(s00_dir, inputs["required_stage00_artifacts"])
    require_artifacts(s01_dir, inputs["required_stage01_artifacts"])
    require_artifacts(s02_dir, inputs["required_stage02_artifacts"])
    require_artifacts(s03_dir, inputs["required_stage03_artifacts"])

    s03_decision = read_json_object(s03_dir / "03_decision_record.json")
    if s03_decision.get("holdout_test_contact") is not False:
        raise ValueError("Stage 03 decision record reports holdout contact")

    return {
        "stage00_dir": s00_dir,
        "stage01_dir": s01_dir,
        "stage02_dir": s02_dir,
        "stage03_dir": s03_dir,
        "stage03_decision": s03_decision,
    }


@dataclass(frozen=True)
class _DataContext:
    dataset: Any  # CandidateDataset
    metadata: pd.DataFrame
    feature_columns: tuple[str, ...]
    window_size: int
    n_features: int
    raw_file_integrity: dict[str, Any]


def _load_data_context(
    config: Mapping[str, Any], inputs_map: dict[str, Any]
) -> _DataContext:
    inputs_cfg = require_mapping(config["inputs"], "inputs")
    raw_data_dir = Path(str(inputs_cfg["raw_data_dir"]))
    label_policy = require_mapping(config["label_policy"], "label_policy")
    roster = require_mapping(config["model_roster"], "model_roster")
    candidate = require_mapping(roster["candidate_input"], "candidate_input")
    candidate_id = str(candidate["candidate_id"])
    feature_set = str(candidate["feature_set"])
    window_size = int(candidate["window_size"])

    s00_dir = inputs_map["stage00_dir"]
    s01_dir = inputs_map["stage01_dir"]
    raw_manifest = read_json_object(s00_dir / "raw_data_manifest.json")
    candidate_inputs = read_json_object(s01_dir / "01_candidate_inputs.json")
    ci_list = [
        c for c in candidate_inputs["candidate_inputs"]
        if c["candidate_id"] == candidate_id
    ]
    if len(ci_list) != 1:
        raise ValueError(f"candidate {candidate_id} not found")
    feature_columns = tuple(ci_list[0]["feature_columns"])

    wf = require_mapping(config["walkforward"], "walkforward")
    periods = wf["periods"]
    last_end = pd.Timestamp(max(p["end_exclusive"] for p in periods))

    raw_source = require_mapping(raw_manifest["raw_source"], "raw_source")
    recipe = require_mapping(raw_manifest["five_minute_recipe"], "five_minute_recipe")
    frames = []
    for ticker in raw_manifest["tickers"]:
        file_spec = require_mapping(
            raw_source["files"][ticker], f"raw_source.files.{ticker}"
        )
        raw_path = raw_data_dir / str(file_spec["name"])
        verify_raw_file_integrity(raw_path, file_spec, str(ticker))
        one_minute = read_raw_txt_file(raw_path, str(ticker), raw_source)
        five_minute = resample_1min_to_5min(one_minute, recipe)
        frames.append(five_minute)

    bars = pd.concat(frames, ignore_index=True).sort_values(
        ["ticker", "timestamp"]
    ).reset_index(drop=True)
    bars = bars[bars["timestamp"] < last_end].copy()

    def assign_split(ts: pd.Timestamp) -> str:
        for p in periods:
            if pd.Timestamp(p["start"]) <= ts < pd.Timestamp(p["end_exclusive"]):
                return p["period_id"]
        return "train_pool"

    bars["split"] = bars["timestamp"].map(assign_split)

    labeled = make_direction_labels(bars, label_policy)
    feature_frame = build_feature_frame(labeled)
    require_feature_columns(feature_columns, feature_frame)

    valid_events = labeled[labeled["valid_label"]].copy()
    valid_events["label"] = valid_events["label"].astype(int)
    valid_events["target_timestamp"] = valid_events["timestamp"]
    valid_events["trading_day"] = valid_events["timestamp"].dt.strftime("%Y-%m-%d")

    dataset = build_window_dataset(
        feature_frame, valid_events,
        feature_set=feature_set, feature_columns=feature_columns,
        window_size=window_size,
    )
    meta = dataset.metadata.copy()
    meta["trading_day_ts"] = pd.to_datetime(meta["trading_day"])

    return _DataContext(
        dataset=dataset,
        metadata=meta,
        feature_columns=feature_columns,
        window_size=window_size,
        n_features=len(feature_columns),
        raw_file_integrity=raw_manifest_integrity_summary(raw_manifest),
    )


def _execute_walkforward(
    *,
    config: Mapping[str, Any],
    inputs_map: dict[str, Any],
    data_context: _DataContext,
    output_dir: Path,
    run_id: str,
    resume_state: _ResumeState | None = None,
) -> V21Result:
    wf = require_mapping(config["walkforward"], "walkforward")
    periods = wf["periods"]
    seeds = [int(s) for s in wf["seeds"]]
    roster = require_mapping(config["model_roster"], "model_roster")
    model_rows = roster["model_rows"]
    candidate = require_mapping(roster["candidate_input"], "candidate_input")
    candidate_id = str(candidate["candidate_id"])
    feature_set = str(candidate["feature_set"])
    window_size = int(candidate["window_size"])
    judged_row = str(
        require_mapping(config["predeclared_criteria"], "predeclared_criteria")[
            "judged_row"
        ]
    )

    meta = data_context.metadata
    ledger = resume_state.ledger if resume_state is not None else _WalkforwardLedger()
    completed_baseline_periods = {r["period_id"] for r in ledger.baseline_rows}

    for period in periods:
        pid = period["period_id"]
        p_start = pd.Timestamp(period["start"])
        p_end = pd.Timestamp(period["end_exclusive"])

        train_mask = meta["trading_day_ts"] < p_start
        test_mask = (meta["trading_day_ts"] >= p_start) & (meta["trading_day_ts"] < p_end)
        train_indices = np.flatnonzero(train_mask.to_numpy())
        test_indices = np.flatnonzero(test_mask.to_numpy())
        train_meta = meta.iloc[train_indices].reset_index(drop=True)
        test_meta = meta.iloc[test_indices].reset_index(drop=True)
        n_train, n_test = len(train_meta), len(test_meta)

        if n_test == 0:
            continue

        assert train_meta["trading_day_ts"].max() < p_start, f"{pid}: train leak"
        assert test_meta["trading_day_ts"].min() >= p_start, f"{pid}: test leak"
        assert test_meta["trading_day_ts"].max() < p_end, f"{pid}: test leak (after)"

        x_train = materialize_window_matrix(data_context.dataset, train_indices)
        x_eval = materialize_window_matrix(data_context.dataset, test_indices)
        x_train_flat = x_train.reshape(n_train, -1)
        x_eval_flat = x_eval.reshape(n_test, -1)

        train_hash = sample_id_hash(train_meta["sample_id"].tolist())
        eval_hash = sample_id_hash(test_meta["sample_id"].tolist())

        y_train = train_meta["label"].to_numpy(dtype=int)
        y_test = test_meta["label"].to_numpy(dtype=int)

        period_baselines: dict[str, dict[str, Any]] = {}
        baseline_ids = [
            str(b) for b in
            require_mapping(config["baseline_controls"], "baseline_controls")["mandatory"]
        ]
        for bl_id in baseline_ids:
            bl = metrics.score_registry_baseline(bl_id, y_train, y_test, seed=seeds[0])
            period_baselines[bl_id] = bl
            if pid not in completed_baseline_periods:
                ledger.baseline_rows.append({
                    "period_id": pid, "baseline_id": bl_id,
                    "n_train": n_train, "n_eval": n_test,
                    "macro_f1": bl["macro_f1"],
                    "balanced_accuracy": bl["balanced_accuracy"],
                    "scope": SCOPE, "readout_tier": READOUT_TIER,
                })
        completed_baseline_periods.add(pid)

        dummy_preds = period_baselines["stratified_dummy_train_prior"]["predictions"]

        for model in model_rows:
            rid = model["table_row_id"]
            family = model["model_family"]
            profile = {
                **model["hpo_profile_params"],
                "profile_id": model["hpo_profile_id"],
            }

            for seed in seeds:
                unit_key = f"{pid}:{rid}:{seed}"
                if unit_key in ledger.completed_units:
                    continue

                result = _refit_and_predict(
                    family, profile, x_train_flat, train_meta,
                    x_eval_flat, test_meta, config, seed,
                    window_size, data_context.n_features,
                )
                fit_ok = result.get("fit_status") == "completed"

                ledger.scoring_events.append({
                    "table_row_id": rid, "period_id": pid, "seed": seed,
                    "n_rows": n_test,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "event_kind": "guarded_scoring",
                })

                bl_dummy = period_baselines["stratified_dummy_train_prior"]["macro_f1"]
                bl_majority = period_baselines["majority_train_prior"]["macro_f1"]
                macro_f1 = result.get("macro_f1") if fit_ok else None

                row: dict[str, Any] = {
                    "table_row_id": rid, "row_kind": "model",
                    "candidate_id": candidate_id,
                    "feature_set": feature_set,
                    "window_size": window_size,
                    "model_family": family,
                    "hpo_profile_id": model["hpo_profile_id"],
                    "period_id": pid,
                    "period_start": period["start"],
                    "period_end_exclusive": period["end_exclusive"],
                    "seed": seed,
                    "n_refit_train_samples": n_train,
                    "n_scored_rows": n_test,
                    "train_sample_id_hash": train_hash,
                    "eval_sample_id_hash": eval_hash,
                    "fit_status": result.get("fit_status", "unknown"),
                    "error_message": result.get("error_message", ""),
                    "scope": SCOPE, "readout_tier": READOUT_TIER,
                }
                if fit_ok:
                    scored = result
                    for k in (
                        "macro_f1", "balanced_accuracy", "accuracy",
                        "mcc", "roc_auc",
                        "precision_down", "recall_down", "f1_down", "support_down",
                        "precision_up", "recall_up", "f1_up", "support_up",
                    ):
                        row[k] = scored.get(k)
                    row["baseline_macro_f1_stratified_dummy_train_prior"] = bl_dummy
                    row["baseline_macro_f1_majority_train_prior"] = bl_majority
                    row["delta_macro_f1_vs_stratified_dummy_train_prior"] = (
                        float(scored["macro_f1"]) - bl_dummy
                    )
                    row["delta_macro_f1_vs_majority_train_prior"] = (
                        float(scored["macro_f1"]) - bl_majority
                    )
                else:
                    row["baseline_macro_f1_stratified_dummy_train_prior"] = bl_dummy
                    row["baseline_macro_f1_majority_train_prior"] = bl_majority
                    row["delta_macro_f1_vs_stratified_dummy_train_prior"] = None
                    row["delta_macro_f1_vs_majority_train_prior"] = None

                for k in (
                    "best_iteration", "early_stopping_source",
                    "early_stopping_used", "early_stopping_reason",
                    "requested_device", "resolved_device",
                    "device_fallback_reason",
                ):
                    row[k] = result.get(k)

                ledger.readout_rows.append(row)

                if fit_ok:
                    predictions = result["predictions"]
                    scores = result["scores"]
                    _record_per_ticker(
                        ledger, rid, pid, seed, test_meta,
                        predictions, dummy_preds,
                    )
                    _record_predictions(
                        ledger, rid, candidate_id, family,
                        model["hpo_profile_id"], pid, seed,
                        test_meta, predictions, scores,
                    )
                    if rid == judged_row:
                        _record_baseline_predictions(
                            ledger, "stratified_dummy_train_prior", pid, seed,
                            test_meta, dummy_preds,
                            period_baselines[
                                "stratified_dummy_train_prior"
                            ]["scores"],
                        )

                ledger.refit_records.append({
                    "table_row_id": rid, "period_id": pid, "seed": seed,
                    "fit_status": result.get("fit_status"),
                    "best_iteration": result.get("best_iteration"),
                    "early_stopping_source": result.get("early_stopping_source"),
                    "early_stopping_reason": result.get("early_stopping_reason"),
                    "early_stopping_used": result.get("early_stopping_used"),
                    "train_sample_id_hash": train_hash,
                    "eval_sample_id_hash": eval_hash,
                })

                ledger.completed_units.append(unit_key)

                status = result.get("fit_status", "?")
                mf1_str = f"{macro_f1:.4f}" if macro_f1 is not None else "N/A"
                print(f"  {rid:30s} {pid} seed={seed} {status:10s} macro_f1={mf1_str}")

            _write_checkpoint(config, run_id, ledger)

    all_completed = len(ledger.scoring_events) == (
        len(periods) * len(model_rows) * len(seeds)
    )
    ledger.readout_complete = all_completed
    if not all_completed:
        ledger.incomplete_reason = (
            f"completed {len(ledger.scoring_events)} of "
            f"{len(periods) * len(model_rows) * len(seeds)} expected events"
        )

    judgement = _aggregate_and_judge(
        ledger, config, is_resumed=resume_state is not None,
    )
    return _write_result(
        config=config,
        inputs_map=inputs_map,
        output_dir=output_dir,
        run_id=run_id,
        ledger=ledger,
        judgement=judgement,
        data_context=data_context,
        resume_state=resume_state,
    )


def _refit_and_predict(
    family: str,
    profile: Mapping[str, Any],
    x_train: np.ndarray,
    train_meta: pd.DataFrame,
    x_eval: np.ndarray,
    eval_meta: pd.DataFrame,
    config: Mapping[str, Any],
    seed: int,
    window_size: int,
    n_features: int,
) -> dict[str, Any]:
    y_train = train_meta["label"].to_numpy(dtype=int)
    y_eval = eval_meta["label"].to_numpy(dtype=int)
    if len(y_train) == 0 or len(x_eval) == 0:
        return {"fit_status": "skipped_no_samples", "error_message": "no train/eval"}
    if len(np.unique(y_train)) < 2:
        return {
            "fit_status": "failed_single_class_train",
            "error_message": "fewer than two classes in train",
        }
    if family == "lightgbm":
        outcome = _refit_lightgbm(profile, x_train, train_meta, x_eval, config, seed)
    else:
        outcome = _refit_torch(
            family, profile, x_train, train_meta, x_eval, config, seed,
            window_size, n_features,
        )
    if outcome.get("fit_status") != "completed":
        return outcome
    predictions = outcome["predictions"]
    scores = outcome["scores"]
    scored = metrics.score_classifier(y_eval, predictions, y_score=scores)
    return {**outcome, **scored}


def _refit_lightgbm(
    profile: Mapping[str, Any],
    x_train: np.ndarray,
    train_meta: pd.DataFrame,
    x_eval: np.ndarray,
    config: Mapping[str, Any],
    seed: int,
) -> dict[str, Any]:
    try:
        from lightgbm import LGBMClassifier
    except ModuleNotFoundError as exc:
        return {"fit_status": "failed_dependency_missing", "error_message": str(exc)}

    training_defaults = require_mapping(
        config["lightgbm_training_defaults"], "lightgbm_training_defaults"
    )
    split, fit_kwargs = fitting.lightgbm_tail_split_and_fit_kwargs(
        x_train=x_train,
        y_train=train_meta["label"].to_numpy(dtype=int),
        train_meta=train_meta,
        training_defaults=training_defaults,
    )
    model = LGBMClassifier(
        **fitting.lightgbm_hpo_params(profile), random_state=seed, verbosity=-1
    )
    try:
        model.fit(split["x_fit"], split["y_fit"], **fit_kwargs)
        predictions = model.predict(x_eval).astype(int)
        scores = model.predict_proba(x_eval)[:, 1].astype(float)
    except (ValueError, RuntimeError, FloatingPointError) as exc:
        return {
            "fit_status": "failed_exception",
            "error_message": f"{type(exc).__name__}: {exc}",
            **{k: split[k] for k in REFIT_EARLY_STOPPING_KEYS},
        }
    return {
        "fit_status": "completed", "error_message": "",
        "predictions": predictions, "scores": scores,
        "best_iteration": getattr(model, "best_iteration_", None),
        **{k: split[k] for k in REFIT_EARLY_STOPPING_KEYS},
        "requested_device": "cpu", "resolved_device": "cpu",
        "device_fallback_reason": "not_gpu_capable_trial",
    }


def _refit_torch(
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
    probe_id = fitting.PROBE_BY_FAMILY.get(family)
    if probe_id is None:
        return {"fit_status": "failed_unknown_family", "error_message": family}
    trial_config = fitting.probe_trial_config(config, probe_id, profile)
    try:
        result = fitting.fit_torch_sequence_probe(
            probe_id, x_train, train_meta["label"].to_numpy(dtype=int),
            x_eval, trial_config, seed, window_size, n_features,
            train_meta=train_meta,
        )
    except ModuleNotFoundError as exc:
        return {"fit_status": "failed_dependency_missing", "error_message": str(exc)}
    except (ValueError, RuntimeError, FloatingPointError) as exc:
        return {"fit_status": "failed_exception", "error_message": str(exc)}
    return {
        "fit_status": "completed", "error_message": "",
        "predictions": result.predictions, "scores": result.scores,
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


def _record_per_ticker(
    ledger: _WalkforwardLedger,
    rid: str, pid: str, seed: int,
    eval_meta: pd.DataFrame,
    predictions: np.ndarray,
    baseline_predictions: np.ndarray,
) -> None:
    y_eval = eval_meta["label"].to_numpy(dtype=int)
    for ticker, group in eval_meta.assign(
        _pos=np.arange(len(eval_meta))
    ).groupby("ticker", sort=True):
        pos = group["_pos"].to_numpy(dtype=int)
        m = metrics.classification_metrics(y_eval[pos], predictions[pos])
        bl = metrics.classification_metrics(y_eval[pos], baseline_predictions[pos])
        ledger.per_ticker_rows.append({
            "table_row_id": rid, "period_id": pid, "seed": seed,
            "ticker": str(ticker), "n_rows": len(pos),
            "support_up": m.get("support_up"),
            "support_down": m.get("support_down"),
            "macro_f1": m["macro_f1"],
            "balanced_accuracy": m["balanced_accuracy"],
            "accuracy": m["accuracy"],
            "f1_up": m.get("f1_up"), "f1_down": m.get("f1_down"),
            "delta_macro_f1_vs_stratified_dummy_train_prior": (
                m["macro_f1"] - bl["macro_f1"]
            ),
            "scope": SCOPE, "readout_tier": READOUT_TIER,
        })


def _record_predictions(
    ledger: _WalkforwardLedger,
    rid: str, candidate_id: str, family: str, hpo_id: str,
    pid: str, seed: int,
    eval_meta: pd.DataFrame,
    predictions: np.ndarray, scores: np.ndarray,
) -> None:
    frame = pd.DataFrame({
        "table_row_id": rid,
        "candidate_id": candidate_id,
        "model_family": family,
        "hpo_profile_id": hpo_id,
        "period_id": pid,
        "seed": int(seed),
        "sample_id": eval_meta["sample_id"].to_numpy(),
        "ticker": eval_meta["ticker"].to_numpy(),
        "target_timestamp": eval_meta["target_timestamp"].to_numpy(),
        "trading_day": eval_meta["trading_day"].to_numpy(),
        "y_true": eval_meta["label"].to_numpy(dtype=int),
        "p_up": np.asarray(scores, dtype=float),
        "y_pred": np.asarray(predictions, dtype=int),
        "scope": SCOPE,
        "readout_tier": READOUT_TIER,
    })[PREDICTION_COLUMNS]
    ledger.prediction_frames.append(frame)


def _record_baseline_predictions(
    ledger: _WalkforwardLedger,
    baseline_id: str, pid: str, seed: int,
    eval_meta: pd.DataFrame,
    predictions: np.ndarray, scores: np.ndarray,
) -> None:
    """Persist per-period baseline per-row predictions for the row-pooled
    pooled_delta. y_true/sample_id come from the SAME eval_meta the candidate
    cell used, so concatenation across periods per seed aligns 1:1. The dummy
    is seed-independent (scored at seeds[0]; finding F10), so per-seed frames
    are identical apart from the recorded ``seed`` column.
    """
    frame = pd.DataFrame({
        "baseline_id": baseline_id,
        "period_id": pid,
        "seed": int(seed),
        "sample_id": eval_meta["sample_id"].to_numpy(),
        "ticker": eval_meta["ticker"].to_numpy(),
        "target_timestamp": eval_meta["target_timestamp"].to_numpy(),
        "trading_day": eval_meta["trading_day"].to_numpy(),
        "y_true": eval_meta["label"].to_numpy(dtype=int),
        "p_up": np.asarray(scores, dtype=float),
        "y_pred": np.asarray(predictions, dtype=int),
        "scope": SCOPE,
        "readout_tier": READOUT_TIER,
    })[BASELINE_PREDICTION_COLUMNS]
    ledger.baseline_prediction_frames.append(frame)


def _concat_baseline_predictions(frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame(columns=BASELINE_PREDICTION_COLUMNS)
    return pd.concat(frames, ignore_index=True)[BASELINE_PREDICTION_COLUMNS]


def _row_pooled_pooled_delta(
    candidate_frames: list[pd.DataFrame],
    baseline_frames: list[pd.DataFrame],
    judged_row: str,
) -> float | None:
    """Protocol §8 row-pooled pooled_delta (lines 508-511).

    For each seed s, concatenate the judged row's predictions across all scored
    periods and the per-period stratified-dummy predictions across all periods,
    compute macro-F1 on each row-union, take delta(s), and return the mean of
    delta(s) over seeds. Returns ``None`` when the baseline per-row predictions
    were not captured (runs produced before this field existed) or when no seed
    has both candidate and baseline rows, so callers fall back to the
    equal-weight companion without crashing.
    """
    if not candidate_frames or not baseline_frames:
        return None
    cand = pd.concat(candidate_frames, ignore_index=True)
    cand = cand[cand["table_row_id"] == judged_row]
    base = pd.concat(baseline_frames, ignore_index=True)
    if cand.empty or base.empty:
        return None
    common_seeds = sorted(
        set(cand["seed"].tolist()) & set(base["seed"].tolist())
    )
    seed_deltas: list[float] = []
    for seed in common_seeds:
        c = cand[cand["seed"] == seed]
        b = base[base["seed"] == seed]
        if c.empty or b.empty:
            continue
        cand_f1 = metrics.binary_macro_f1(
            c["y_true"].to_numpy(dtype=int), c["y_pred"].to_numpy(dtype=int)
        )
        base_f1 = metrics.binary_macro_f1(
            b["y_true"].to_numpy(dtype=int), b["y_pred"].to_numpy(dtype=int)
        )
        seed_deltas.append(float(cand_f1) - float(base_f1))
    if not seed_deltas:
        return None
    return float(np.mean(seed_deltas))


def _write_checkpoint(
    config: Mapping[str, Any], run_id: str, ledger: _WalkforwardLedger,
) -> None:
    checkpointing = config.get("checkpointing", {})
    if not isinstance(checkpointing, Mapping) or not checkpointing.get("enabled"):
        return
    checkpoint_root = Path(str(checkpointing.get(
        "checkpoint_dir",
        "/content/lst_models_checkpoints/v2_1_guarded_walkforward_readout",
    )))
    checkpoint_dir = checkpoint_root / run_id
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(ledger.readout_rows).to_csv(
        checkpoint_dir / "v2_1_walkforward_readout_partial.csv", index=False
    )
    pd.DataFrame(ledger.baseline_rows).to_csv(
        checkpoint_dir / "v2_1_same_row_baselines_partial.csv", index=False
    )
    _concat_predictions(ledger.prediction_frames).to_csv(
        checkpoint_dir / "v2_1_predictions_partial.csv", index=False
    )
    _concat_baseline_predictions(ledger.baseline_prediction_frames).to_csv(
        checkpoint_dir / "v2_1_baseline_predictions_partial.csv", index=False
    )
    write_json(
        checkpoint_dir / "v2_1_ledger_state_partial.json",
        {
            "run_id": run_id,
            "completed_units": ledger.completed_units,
            "readout_rows": ledger.readout_rows,
            "per_ticker_rows": ledger.per_ticker_rows,
            "baseline_rows": ledger.baseline_rows,
            "scoring_events": ledger.scoring_events,
            "refit_records": ledger.refit_records,
            "readout_complete": ledger.readout_complete,
            "incomplete_reason": ledger.incomplete_reason,
        },
    )
    payload = _checkpoint_manifest_payload(config, run_id, ledger)
    payload["resume_instructions"]["required_checkpoint_dir"] = str(checkpoint_dir)
    write_json(checkpoint_dir / "checkpoint_manifest.json", payload)


def _load_resume_state(config: Mapping[str, Any]) -> _ResumeState | None:
    resume = config.get("resume", {})
    if not isinstance(resume, Mapping) or not resume.get("enabled"):
        return None
    run_id = str(resume["run_id"])
    if not RUN_ID_PATTERN.match(run_id):
        raise ValueError(f"resume.run_id invalid: {run_id!r}")
    checkpoint_dir = Path(str(resume["checkpoint_dir"]))
    for name in RESUME_CHECKPOINT_FILES:
        if not (checkpoint_dir / name).exists():
            raise FileNotFoundError(
                f"missing resume checkpoint file: {checkpoint_dir / name}"
            )
    state = read_json_object(checkpoint_dir / "v2_1_ledger_state_partial.json")
    if state.get("run_id") != run_id:
        raise ValueError("checkpoint run_id mismatch")
    ledger = _WalkforwardLedger(
        readout_rows=state.get("readout_rows", []),
        per_ticker_rows=state.get("per_ticker_rows", []),
        baseline_rows=state.get("baseline_rows", []),
        scoring_events=state.get("scoring_events", []),
        refit_records=state.get("refit_records", []),
        completed_units=state.get("completed_units", []),
    )
    partial_pred = checkpoint_dir / "v2_1_predictions_partial.csv"
    if partial_pred.exists() and partial_pred.stat().st_size > 0:
        ledger.prediction_frames.append(
            pd.read_csv(partial_pred)[PREDICTION_COLUMNS]
        )
    # Optional-if-present: older checkpoints (including the completed 20260617
    # run) predate this file, so it is NOT a required resume file -- load it
    # only when a post-fix checkpoint provides it.
    partial_base = checkpoint_dir / "v2_1_baseline_predictions_partial.csv"
    if partial_base.exists() and partial_base.stat().st_size > 0:
        ledger.baseline_prediction_frames.append(
            pd.read_csv(partial_base)[BASELINE_PREDICTION_COLUMNS]
        )
    return _ResumeState(
        run_id=run_id, checkpoint_dir=checkpoint_dir, ledger=ledger,
    )


def _concat_predictions(frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame(columns=PREDICTION_COLUMNS)
    return pd.concat(frames, ignore_index=True)[PREDICTION_COLUMNS]


def _aggregate_and_judge(
    ledger: _WalkforwardLedger, config: Mapping[str, Any],
    *, is_resumed: bool = False,
) -> dict[str, Any]:
    criteria = require_mapping(
        config["predeclared_criteria"], "predeclared_criteria"
    )
    judged_row = str(criteria["judged_row"])
    min_pos_periods = int(criteria["positive_period_count_minimum"])

    completed = [
        r for r in ledger.readout_rows
        if r["table_row_id"] == judged_row and r["fit_status"] == "completed"
    ]
    if not completed:
        return {
            "decision": "did_not_meet_predeclared_guarded_stability_criteria",
            "positive_period_count": 0,
            "pooled_delta": 0.0,
            "pooled_delta_estimand": "equal_weight",
            "pooled_delta_equal_weight": 0.0,
            "pooled_delta_row_pooled": None,
            "pooled_delta_row_pooled_available": False,
            "criteria_met": {
                "positive_period_count": False, "pooled_delta": False,
            },
        }

    period_deltas: dict[str, list[float]] = {}
    for r in completed:
        pid = r["period_id"]
        delta = r["delta_macro_f1_vs_stratified_dummy_train_prior"]
        if delta is not None:
            period_deltas.setdefault(pid, []).append(float(delta))

    period_mean_deltas = {
        pid: float(np.mean(vals)) for pid, vals in period_deltas.items()
    }
    positive_period_count = sum(
        1 for d in period_mean_deltas.values() if d > 0
    )
    # Two pooled_delta estimands (see register FIX-1 / F9 and the protocol
    # 2026-06-17 erratum):
    #   * equal_weight -- mean over per-(period, seed) cell deltas. This is what
    #     the shipped code computed and what the signed-off run
    #     20260617_051047_321730 reported (+0.005439); it currently BINDS c2.
    #   * row_pooled   -- the protocol section 8 definition (lines 508-511):
    #     per-seed row-union macro-F1 delta, mean over seeds. Emitted as a
    #     disclosed companion; this is the value c2 SHOULD bind once it is
    #     reconciled offline against the Drive prediction dump.
    # The row-pooled value is only trustworthy on a fresh single-pass run: on a
    # resumed run the candidate frames cover all periods but the baseline frames
    # (a new artifact) may cover only post-resume periods, so the row-union would
    # be coverage-mismatched. It is therefore computed only when not resumed.
    pooled_delta_equal_weight = float(np.mean([
        r["delta_macro_f1_vs_stratified_dummy_train_prior"]
        for r in completed
        if r["delta_macro_f1_vs_stratified_dummy_train_prior"] is not None
    ]))
    pooled_delta_row_pooled = (
        None if is_resumed
        else _row_pooled_pooled_delta(
            ledger.prediction_frames, ledger.baseline_prediction_frames,
            judged_row,
        )
    )
    row_pooled_available = pooled_delta_row_pooled is not None

    # BINDING (this landing -- register FIX-1 option C): c2 stays on the
    # equal-weight value so the signed-off decision is not retroactively altered
    # by an unverifiable recompute. To flip the binding to the protocol estimand
    # after the offline Drive reconciliation confirms the sign, change the next
    # line to `pooled_delta = pooled_delta_row_pooled if row_pooled_available
    # else pooled_delta_equal_weight` and set "pooled_delta_estimand" below to
    # reflect which estimand was used.
    pooled_delta = pooled_delta_equal_weight

    c1 = positive_period_count >= min_pos_periods
    c2 = pooled_delta > 0
    decision = (
        "met_predeclared_guarded_stability_criteria"
        if c1 and c2
        else "did_not_meet_predeclared_guarded_stability_criteria"
    )
    return {
        "decision": decision,
        "positive_period_count": positive_period_count,
        "pooled_delta": pooled_delta,
        "pooled_delta_estimand": "equal_weight",
        "pooled_delta_equal_weight": pooled_delta_equal_weight,
        "pooled_delta_row_pooled": pooled_delta_row_pooled,
        "pooled_delta_row_pooled_available": row_pooled_available,
        "period_mean_deltas": period_mean_deltas,
        "criteria_met": {
            "positive_period_count": c1,
            "pooled_delta": c2,
        },
    }


def _build_comparison_table(
    ledger: _WalkforwardLedger,
    model_rows: list[Mapping[str, Any]],
    periods: list[Mapping[str, Any]],
) -> pd.DataFrame:
    display_names = {
        "tcn_frozen_primary": "TCN",
        "lightgbm_family_best": "LightGBM",
        "standard_dlinear_family_best": "Std DLinear",
        "ms_dlinear_tcn_family_best": "MS-DLinear+TCN",
    }
    dummy_bl = [
        r for r in ledger.baseline_rows
        if r.get("baseline_id") == "stratified_dummy_train_prior"
    ]
    dummy_mean = float(np.mean([r["macro_f1"] for r in dummy_bl])) if dummy_bl else 0.5

    rows_out = [{"Model": "Dummy", "Mean macro-F1": round(dummy_mean, 4),
                 "Std": None, "Mean delta vs Dummy": 0.0,
                 "Periods pos": None}]
    for model in model_rows:
        rid = model["table_row_id"]
        completed = [
            r for r in ledger.readout_rows
            if r["table_row_id"] == rid and r["fit_status"] == "completed"
        ]
        if not completed:
            rows_out.append({"Model": display_names.get(rid, rid),
                             "Mean macro-F1": None, "Std": None,
                             "Mean delta vs Dummy": None, "Periods pos": None})
            continue
        mf1s = [r["macro_f1"] for r in completed]
        deltas = [
            r["delta_macro_f1_vs_stratified_dummy_train_prior"]
            for r in completed
            if r["delta_macro_f1_vs_stratified_dummy_train_prior"] is not None
        ]
        period_deltas: dict[str, list[float]] = {}
        for r in completed:
            d = r.get("delta_macro_f1_vs_stratified_dummy_train_prior")
            if d is not None:
                period_deltas.setdefault(r["period_id"], []).append(d)
        periods_pos = sum(
            1 for vals in period_deltas.values() if np.mean(vals) > 0
        )
        rows_out.append({
            "Model": display_names.get(rid, rid),
            "Mean macro-F1": round(float(np.mean(mf1s)), 4),
            "Std": round(float(np.std(mf1s)), 4),
            "Mean delta vs Dummy": round(float(np.mean(deltas)), 4) if deltas else None,
            "Periods pos": f"{periods_pos}/{len(periods)}",
        })
    return pd.DataFrame(rows_out)


def _build_period_registry(
    config: Mapping[str, Any], meta: pd.DataFrame,
) -> dict[str, Any]:
    wf = config["walkforward"]
    periods = wf["periods"]
    entries = []
    for p in periods:
        p_start = pd.Timestamp(p["start"])
        p_end = pd.Timestamp(p["end_exclusive"])
        in_period = meta[
            (meta["trading_day_ts"] >= p_start) & (meta["trading_day_ts"] < p_end)
        ]
        entries.append({
            "period_id": p["period_id"],
            "start": p["start"],
            "end_exclusive": p["end_exclusive"],
            "eligible_rows": len(in_period),
            "covered_trading_days": int(in_period["trading_day"].nunique())
            if not in_period.empty else 0,
        })
    return {
        "stage_name": "v2_1_guarded_walkforward_readout",
        "period_count": len(periods),
        "periods": entries,
    }


def _readout_device_fields(refit_records: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [
        record for record in refit_records
        if record.get("fit_status") == "completed"
    ]
    if not completed:
        return {
            "requested_device": "not_resolved",
            "resolved_device": "not_resolved",
            "cuda_available": False,
            "gpu_name_or_null": None,
            "device_fallback_reason": "no_refits_completed",
        }
    requested = sorted(
        {
            str(record.get("requested_device"))
            for record in completed
            if record.get("requested_device")
        }
    )
    resolved = sorted(
        {
            str(record.get("resolved_device"))
            for record in completed
            if record.get("resolved_device")
        }
    )
    fallbacks = sorted(
        {
            str(record.get("device_fallback_reason"))
            for record in completed
            if record.get("device_fallback_reason")
        }
    )
    resolved_device = ",".join(resolved) if resolved else "not_resolved"
    cuda_resolved = any(
        value.strip().startswith("cuda") for value in resolved_device.split(",")
    )
    runtime = (
        torch_runtime_device_fields()
        if cuda_resolved
        else {"cuda_available": False, "gpu_name_or_null": None}
    )
    return {
        "requested_device": ",".join(requested) if requested else "not_resolved",
        "resolved_device": resolved_device,
        "cuda_available": bool(runtime["cuda_available"] or cuda_resolved),
        "gpu_name_or_null": runtime["gpu_name_or_null"],
        "device_fallback_reason": ",".join(fallbacks),
    }


def _write_result(
    *,
    config: Mapping[str, Any],
    inputs_map: dict[str, Any],
    output_dir: Path,
    run_id: str,
    ledger: _WalkforwardLedger,
    judgement: dict[str, Any],
    data_context: _DataContext,
    resume_state: _ResumeState | None = None,
) -> V21Result:
    outputs = require_mapping(config["outputs"], "outputs")
    wf = require_mapping(config["walkforward"], "walkforward")
    roster = require_mapping(config["model_roster"], "model_roster")

    paths: dict[str, Path] = {}

    readout_path = output_dir / str(outputs.get(
        "walkforward_readout", "v2_1_walkforward_readout.csv"
    ))
    pd.DataFrame(
        ledger.readout_rows, columns=WALKFORWARD_READOUT_COLUMNS,
    ).to_csv(readout_path, index=False)
    paths["walkforward_readout"] = readout_path

    per_ticker_path = output_dir / str(outputs.get(
        "per_ticker_readout", "v2_1_per_ticker_readout.csv"
    ))
    pd.DataFrame(
        ledger.per_ticker_rows, columns=PER_TICKER_READOUT_COLUMNS,
    ).to_csv(per_ticker_path, index=False)
    paths["per_ticker_readout"] = per_ticker_path

    period_agg = _period_summary(ledger)
    period_summary_path = output_dir / str(outputs.get(
        "period_summary", "v2_1_period_summary.csv"
    ))
    period_agg.to_csv(period_summary_path, index=False)
    paths["period_summary"] = period_summary_path

    comparison = _build_comparison_table(
        ledger, roster["model_rows"], wf["periods"],
    )
    comparison_path = output_dir / str(outputs.get(
        "comparison_table", "v2_1_comparison_table.csv"
    ))
    comparison.to_csv(comparison_path, index=False)
    paths["comparison_table"] = comparison_path

    baselines_path = output_dir / str(outputs.get(
        "same_row_baselines", "v2_1_same_row_baselines.csv"
    ))
    pd.DataFrame(ledger.baseline_rows).to_csv(baselines_path, index=False)
    paths["same_row_baselines"] = baselines_path

    predictions_path = output_dir / str(outputs.get(
        "predictions", "v2_1_predictions.csv"
    ))
    _concat_predictions(ledger.prediction_frames).to_csv(
        predictions_path, index=False
    )
    paths["predictions"] = predictions_path

    baseline_predictions_path = output_dir / str(outputs.get(
        "baseline_predictions", "v2_1_baseline_predictions.csv"
    ))
    _concat_baseline_predictions(ledger.baseline_prediction_frames).to_csv(
        baseline_predictions_path, index=False
    )
    paths["baseline_predictions"] = baseline_predictions_path

    registry = _build_period_registry(config, data_context.metadata)
    registry_path = output_dir / str(outputs.get(
        "period_registry", "v2_1_period_registry.json"
    ))
    write_json(registry_path, registry)
    paths["period_registry"] = registry_path

    inputs_cfg = require_mapping(config["inputs"], "inputs")
    protocol_fields = _protocol_provenance_fields(config)
    notebook_path = resolve_repo_path(
        inputs_cfg.get("notebook_path", "notebooks/v2_1_guarded_walkforward_readout_colab.ipynb")
    )
    device_fields = _readout_device_fields(ledger.refit_records)
    record = {
        "route": config["route"],
        "stage_name": config["stage_name"],
        "scope": SCOPE,
        "source_stage00_run_id": str(inputs_cfg["stage00_run_id"]),
        "source_stage01_run_id": str(inputs_cfg["stage01_run_id"]),
        "source_stage02_run_id": str(inputs_cfg["stage02_run_id"]),
        "source_stage03_run_id": str(inputs_cfg["stage03_run_id"]),
        "source_stage04_run_id": str(inputs_cfg.get("stage04_run_id")),
        "superseded_stage02_run_ids": [
            str(v) for v in inputs_cfg.get("superseded_stage02_run_ids", [])
        ],
        **protocol_fields,
        "period_registry": registry,
        "model_roster": dict(require_mapping(config["model_roster"], "model_roster")),
        "predeclared_criteria": dict(
            require_mapping(config["predeclared_criteria"], "predeclared_criteria")
        ),
        "positive_period_count": judgement["positive_period_count"],
        "pooled_delta": judgement["pooled_delta"],
        "pooled_delta_estimand": judgement.get("pooled_delta_estimand"),
        "pooled_delta_equal_weight": judgement.get("pooled_delta_equal_weight"),
        "pooled_delta_row_pooled": judgement.get("pooled_delta_row_pooled"),
        "pooled_delta_row_pooled_available": judgement.get(
            "pooled_delta_row_pooled_available"
        ),
        "criteria_met": judgement["criteria_met"],
        "decision": judgement["decision"],
        "readout_complete": ledger.readout_complete,
        "readout_incomplete_reason": ledger.incomplete_reason,
        "guarded_scoring_events": len(ledger.scoring_events),
        "scoring_event_ledger": ledger.scoring_events,
        "refit_records": ledger.refit_records,
        "resumed_from_checkpoint": resume_state is not None,
        "holdout_test_contact": True,
        "holdout_contact_tier": READOUT_TIER,
        "clean_test_claim": False,
        "official_validation_scoring_events": 0,
        "official_validation_for_selection": False,
        "no_final_model_selected": True,
        "v2_frozen_selection_unchanged": True,
    }
    record_path = write_json(
        output_dir / str(outputs.get(
            "decision_record", "v2_1_decision_record.json"
        )),
        record,
    )
    paths["decision_record"] = record_path

    manifest = {
        "stage_name": config["stage_name"],
        "route": config["route"],
        "scope": SCOPE,
        "run_id": run_id,
        "source_stage00_run_id": str(inputs_cfg["stage00_run_id"]),
        "source_stage01_run_id": str(inputs_cfg["stage01_run_id"]),
        "source_stage02_run_id": str(inputs_cfg["stage02_run_id"]),
        "source_stage03_run_id": str(inputs_cfg["stage03_run_id"]),
        "source_stage04_run_id": str(inputs_cfg.get("stage04_run_id")),
        **protocol_fields,
        "period_registry": registry,
        "config_sha256": hash_mapping(config),
        "notebook_sha256": hash_file(notebook_path),
        "feature_rebuild_code_sha256": feature_rebuild_code_sha256(),
        "raw_file_integrity": data_context.raw_file_integrity,
        "holdout_test_contact": True,
        "holdout_contact_tier": READOUT_TIER,
        "clean_test_claim": False,
        "official_validation_scoring_events": 0,
        "official_validation_for_selection": False,
        "no_final_model_selected": True,
        "guarded_scoring_events": len(ledger.scoring_events),
        "readout_complete": ledger.readout_complete,
        "decision": judgement["decision"],
        "resumed_from_checkpoint": resume_state is not None,
        **device_fields,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path = write_json(
        output_dir / str(outputs.get("manifest", "run_manifest.json")),
        manifest,
    )
    paths["run_manifest"] = manifest_path

    inventory_path = write_artifact_inventory(output_dir, paths)
    paths["artifact_inventory"] = inventory_path

    return V21Result(
        output_dir=output_dir,
        run_manifest=manifest_path,
        artifact_inventory=inventory_path,
        decision_record=record_path,
        walkforward_readout=readout_path,
        per_ticker_readout=per_ticker_path,
        period_summary=period_summary_path,
        comparison_table=comparison_path,
        same_row_baselines=baselines_path,
        predictions=predictions_path,
        period_registry=registry_path,
    )


def _period_summary(ledger: _WalkforwardLedger) -> pd.DataFrame:
    completed = [
        r for r in ledger.readout_rows if r["fit_status"] == "completed"
    ]
    if not completed:
        return pd.DataFrame()
    df = pd.DataFrame(completed)
    return df.groupby(["table_row_id", "period_id"]).agg(
        mean_macro_f1=("macro_f1", "mean"),
        mean_delta_vs_dummy=(
            "delta_macro_f1_vs_stratified_dummy_train_prior", "mean"
        ),
        mean_delta_vs_majority=(
            "delta_macro_f1_vs_majority_train_prior", "mean"
        ),
    ).reset_index()
