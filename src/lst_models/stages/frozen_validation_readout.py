"""Stage 03 frozen official-validation readout: fail-closed verification of the
frozen Stage 00 -> 01 -> 02 artifact chain, rebuild of the train/validation
feature and window tensors with the same frozen Stage 01 builders Stage 02
used, and a one-shot official-validation scoring pass under the pre-registered
rules in docs/protocols/03_frozen_validation_readout_protocol.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from lst_models import metrics
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
from lst_models.features import build_feature_frame, require_feature_columns
from lst_models.splits import valid_events_for_split
from lst_models.windows import (
    CandidateDataset,
    build_window_dataset,
    validate_rebuilt_candidate_counts,
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


def run_stage(config: Mapping[str, Any]) -> Stage03Result:
    _validate_config(config)
    inputs = _verify_entry_gates(config)

    outputs = require_mapping(config["outputs"], "outputs")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    output_dir = Path(str(outputs["output_dir"])) / run_id
    output_dir.mkdir(parents=True, exist_ok=False)

    if inputs.stage02_handoff.get("ready_for_stage03") is not True:
        return _write_blocked_result(config, inputs, output_dir)

    data_context = _load_readout_data_context(config, inputs)
    primary = require_mapping(
        inputs.stage02_handoff["primary_candidate"], "stage02_handoff.primary_candidate"
    )
    train_dataset = _prepare_candidate_dataset(primary, data_context, data_context.train_events)
    validate_rebuilt_candidate_counts(
        {
            "candidate_id": primary["candidate_id"],
            "feature_columns": list(train_dataset.feature_columns),
        },
        train_dataset,
        inputs.stage01_summary,
    )
    return _execute_readout(
        config=config,
        inputs=inputs,
        data_context=data_context,
        train_dataset=train_dataset,
        output_dir=output_dir,
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


def _write_blocked_result(
    config: Mapping[str, Any], inputs: Stage03Inputs, output_dir: Path
) -> Stage03Result:
    outputs = require_mapping(config["outputs"], "outputs")
    record_path = write_json(
        output_dir / _output_name(outputs, "decision_record", "03_decision_record.json"),
        _blocked_decision_record(config, inputs),
    )
    manifest_path = write_json(
        output_dir / _output_name(outputs, "manifest", "run_manifest.json"),
        _blocked_manifest_payload(config, inputs, record_path),
    )
    inventory_path = write_artifact_inventory(
        output_dir,
        {"run_manifest": manifest_path, "decision_record": record_path},
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


def _blocked_manifest_payload(
    config: Mapping[str, Any], inputs: Stage03Inputs, record_path: Path
) -> dict[str, Any]:
    config_inputs = require_mapping(config["inputs"], "inputs")
    notebook_path = resolve_repo_path(config_inputs["notebook_path"])
    input_artifacts = [
        str(path)
        for paths in (inputs.stage00_paths, inputs.stage01_paths, inputs.stage02_paths)
        for path in paths.values()
    ]
    return {
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
        "stage03_execution_mode": "blocked_stage02_handoff_not_ready_for_stage03",
        "input_artifacts": input_artifacts,
        "output_artifacts": [record_path.name],
        "official_validation_contact": True,
        "official_validation_scoring_events": 0,
        "official_validation_for_selection": False,
        "no_final_model_selected": True,
        "holdout_test_contact": False,
        "stage03_readout_code_sha256": stage03_readout_code_sha256(),
        **dict(inputs.feature_rebuild_fields),
        **git_commit_fields(),
    }


def _execute_readout(
    *,
    config: Mapping[str, Any],
    inputs: Stage03Inputs,
    data_context: Stage03DataContext,
    train_dataset: CandidateDataset,
    output_dir: Path,
) -> Stage03Result:
    """Refit/scoring seam: plan Task 7 adds the mechanism-frozen refit wrappers
    and plan Task 8 replaces this raise with the one-shot per-seed scoring loop,
    aggregation, and predeclared-criteria judgement."""
    raise NotImplementedError("Stage 03 scoring is implemented in plan Task 8")
