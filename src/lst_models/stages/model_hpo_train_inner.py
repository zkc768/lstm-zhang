from __future__ import annotations

import importlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
import yaml

from lst_models import metrics
from lst_models.artifacts import (
    feature_rebuild_code_sha256,
    git_commit_fields,
    read_json_object,
    require_artifacts,
    write_artifact_inventory,
    write_json,
)
from lst_models.config import hash_file, hash_mapping, load_yaml, require_mapping, resolve_repo_path
from lst_models.data import (
    load_sample_event_index,
    load_stage01_summary,
    load_train_bars,
    raw_manifest_integrity_summary,
)
from lst_models.features import build_feature_frame, require_feature_columns
from lst_models.fitting import (
    PROBE_BY_FAMILY,
    fit_probe,
    lightgbm_hpo_params,
    lightgbm_tail_split_and_fit_kwargs,
    probe_trial_config,
    profile_params,
    torch_training_defaults,
)
from lst_models.metrics import block_delta_macro_f1, ticker_delta_macro_f1
from lst_models.splits import build_train_inner_folds, train_valid_events
from lst_models.windows import (
    CandidateDataset,
    build_window_dataset,
    cap_indices,
    fold_indices,
    materialize_window_matrix,
    sample_id_hash,
    validate_rebuilt_candidate_counts,
)


SUMMARY_COLUMNS = [
    "status",
    "candidate_count",
    "model_family_count",
    "planned_hpo_rows",
    "completed_hpo_rows",
    "failed_hpo_rows",
    "selected_family_count",
    "ready_for_stage03",
    "primary_candidate_id",
    "primary_model_family",
    "primary_hpo_profile_id",
    "fallback_candidate_id",
    "fallback_model_family",
    "fallback_hpo_profile_id",
    "decision",
    "block_reason",
]

HPO_TRIAL_LEDGER_COLUMNS = [
    "trial_id",
    "candidate_id",
    "feature_set",
    "feature_columns_json",
    "window_size",
    "model_family",
    "probe_id",
    "hpo_profile_id",
    "hpo_profile_params_json",
    "fold_id",
    "seed",
    "fit_status",
    "n_train_samples",
    "n_eval_samples",
    "train_sample_id_hash",
    "eval_sample_id_hash",
    "sample_id_hash",
    "baseline_id",
    "baseline_fit_status",
    "baseline_macro_f1",
    "baseline_balanced_accuracy",
    "baseline_accuracy",
    "baseline_roc_auc",
    "baseline_mcc",
    "macro_f1",
    "balanced_accuracy",
    "accuracy",
    "roc_auc",
    "mcc",
    "delta_macro_f1_vs_baseline",
    "delta_balanced_accuracy_vs_baseline",
    "positive_ticker_count",
    "ticker_delta_macro_f1_json",
    "block_delta_macro_f1_json",
    "requested_device",
    "resolved_device",
    "device_fallback_reason",
    "best_iteration",
    "early_stopping_source",
    "early_stopping_used",
    "early_stopping_reason",
    "early_stopping_train_sample_id_hash",
    "early_stopping_eval_sample_id_hash",
    "selected_for_stage03",
    "error_message",
]

HPO_PLAN_LEDGER_COLUMNS = [
    "trial_id",
    "candidate_id",
    "feature_set",
    "feature_columns_json",
    "window_size",
    "model_family",
    "probe_id",
    "hpo_profile_id",
    "hpo_profile_params_json",
    "fold_id",
    "seed",
    "plan_status",
    "n_train_samples",
    "n_eval_samples",
    "train_sample_id_hash",
    "eval_sample_id_hash",
    "sample_id_hash",
    "baseline_id",
]

HPO_SUMMARY_COLUMNS = [
    "candidate_id",
    "feature_set",
    "window_size",
    "model_family",
    "probe_id",
    "hpo_profile_id",
    "hpo_profile_params_json",
    "expected_rows",
    "completed_rows",
    "failed_rows",
    "mean_macro_f1",
    "mean_balanced_accuracy",
    "mean_roc_auc",
    "mean_mcc",
    "mean_delta_macro_f1_vs_stratified_dummy_train_prior",
    "lcb_delta_macro_f1_vs_stratified_dummy_train_prior",
    "mean_delta_macro_f1_vs_majority_train_prior",
    "lcb_delta_macro_f1_vs_majority_train_prior",
    "min_positive_ticker_count",
    "mean_positive_ticker_count",
    "selected_role",
    "selection_reason",
]

BASELINE_CONTROL_COLUMNS = [
    "candidate_id",
    "feature_set",
    "window_size",
    "fold_id",
    "seed",
    "baseline_id",
    "fit_status",
    "n_train_samples",
    "n_eval_samples",
    "train_sample_id_hash",
    "eval_sample_id_hash",
    "sample_id_hash",
    "macro_f1",
    "balanced_accuracy",
    "accuracy",
    "roc_auc",
    "mcc",
    "error_message",
]

TORCH_FAMILIES = {"standard_dlinear", "tcn", "ms_dlinear_tcn"}
DEFAULT_BASELINES = (
    "stratified_dummy_train_prior",
    "majority_train_prior",
    "constant_up",
    "constant_down",
)
RUN_ID_PATTERN = re.compile(r"^\d{8}_\d{6}_\d{6}$")


@dataclass(frozen=True)
class Stage02Result:
    output_dir: Path
    run_manifest: Path
    artifact_inventory: Path
    summary: Path
    hpo_plan_ledger: Path
    best_params_by_family: Path
    stage03_handoff: Path
    hpo_trial_ledger: Path
    hpo_summary: Path
    baseline_control_summary: Path
    frozen_candidate: Path
    frozen_candidate_markdown: Path


@dataclass(frozen=True)
class Stage02DataContext:
    stage00_paths: Mapping[str, Path]
    stage00_manifest: Mapping[str, Any]
    raw_manifest: Mapping[str, Any]
    split_freeze: Mapping[str, Any]
    train_events: pd.DataFrame
    feature_frame: pd.DataFrame
    folds: pd.DataFrame


def run_stage(config: Mapping[str, Any]) -> Stage02Result:
    _validate_config(config)

    inputs = require_mapping(config["inputs"], "inputs")
    outputs = require_mapping(config["outputs"], "outputs")
    stage01_run_dir = Path(str(inputs["stage01_runtime_run_dir"]))
    stage01_paths = require_artifacts(stage01_run_dir, inputs["required_stage01_artifacts"])

    stage01_manifest = read_json_object(stage01_paths["run_manifest.json"])
    stage01_handoff = read_json_object(stage01_paths["01_candidate_inputs.json"])
    stage01_summary = load_stage01_summary(stage01_paths["01_feature_window_search_summary.csv"])
    _validate_stage01_contract(config, stage01_manifest, stage01_handoff)

    candidates = _candidate_inputs(stage01_handoff)
    approved_families = _approved_families(stage01_handoff, config)
    blocked_reason = _stage01_block_reason(stage01_handoff, candidates, approved_families)

    run_id = _resolve_run_id(outputs.get("run_id"))
    output_dir = Path(str(outputs["output_dir"])) / run_id
    output_dir.mkdir(parents=True, exist_ok=False)

    if blocked_reason:
        trial_ledger = pd.DataFrame(columns=HPO_TRIAL_LEDGER_COLUMNS)
        baseline_summary = pd.DataFrame(columns=BASELINE_CONTROL_COLUMNS)
        hpo_summary = pd.DataFrame(columns=HPO_SUMMARY_COLUMNS)
        summary = _summary_row(
            status="blocked",
            candidate_count=len(candidates),
            model_family_count=len(approved_families),
            planned_hpo_rows=0,
            completed_hpo_rows=0,
            failed_hpo_rows=0,
            selected_family_count=0,
            ready_for_stage03=False,
            primary=None,
            fallback=None,
            decision="do_not_start_stage03_stage02_blocked_by_stage01",
            block_reason=blocked_reason,
        )
        decision_bundle = _selection_bundle(
            ready_for_stage03=False,
            decision="do_not_start_stage03_stage02_blocked_by_stage01",
            block_reason=blocked_reason,
            primary=None,
            fallback=None,
        )
        stage00_context: Stage02DataContext | None = None
        profiles_by_family: dict[str, list[Mapping[str, Any]]] = {}
        execution_mode = "blocked_by_stage01_no_candidate_inputs"
    else:
        stage00_context = _load_stage02_data_context(config, stage01_handoff)
        profiles_by_family = _load_search_profiles(approved_families, config)
        planned_rows = _planned_hpo_rows(candidates, profiles_by_family, stage00_context.folds, config)
        _enforce_budget(planned_rows, config)
        trial_ledger, baseline_summary = _run_hpo_trials(
            candidates,
            profiles_by_family,
            stage00_context,
            stage01_summary,
            config,
            run_id=run_id,
            planned_hpo_rows=planned_rows,
        )
        hpo_summary = _build_hpo_summary(trial_ledger, baseline_summary)
        decision_bundle = _select_frozen_candidates(hpo_summary, trial_ledger, config)
        trial_ledger = _mark_selected_trials(trial_ledger, decision_bundle)
        hpo_summary = _mark_selected_summary(hpo_summary, decision_bundle)
        completed_rows = int(trial_ledger["fit_status"].eq("completed").sum())
        failed_rows = int(len(trial_ledger) - completed_rows)
        summary = _summary_row(
            status=_status_from_selection(decision_bundle, failed_rows),
            candidate_count=len(candidates),
            model_family_count=len(approved_families),
            planned_hpo_rows=len(trial_ledger),
            completed_hpo_rows=completed_rows,
            failed_hpo_rows=failed_rows,
            selected_family_count=_selected_family_count(decision_bundle),
            ready_for_stage03=bool(decision_bundle["ready_for_stage03"]),
            primary=decision_bundle.get("primary_candidate"),
            fallback=decision_bundle.get("fallback_candidate"),
            decision=str(decision_bundle["decision"]),
            block_reason=str(decision_bundle["block_reason"]),
        )
        execution_mode = "formal_train_inner_hpo_completed"

    plan_ledger = _build_hpo_plan_ledger(trial_ledger)
    device_provenance = _device_manifest_fields(config, trial_ledger)
    frozen_candidate = _frozen_candidate_payload(
        config=config,
        stage01_handoff=stage01_handoff,
        decision_bundle=decision_bundle,
        hpo_summary=hpo_summary,
        device_provenance=device_provenance,
    )
    best_params = _best_params_payload(
        config=config,
        stage01_handoff=stage01_handoff,
        profiles_by_family=profiles_by_family,
        hpo_summary=hpo_summary,
        decision_bundle=decision_bundle,
    )
    stage03_handoff = _stage03_handoff_payload(config, stage01_handoff, decision_bundle)

    summary_path = output_dir / _output_name(outputs, "summary", "02_model_hpo_train_inner_summary.csv")
    plan_ledger_path = output_dir / _output_name(outputs, "hpo_plan_ledger", "02_hpo_plan_ledger.csv")
    trial_ledger_path = output_dir / _output_name(outputs, "hpo_trial_ledger", "02_hpo_trial_ledger.csv")
    hpo_summary_path = output_dir / _output_name(outputs, "hpo_summary", "02_hpo_summary.csv")
    baseline_summary_path = output_dir / _output_name(
        outputs, "baseline_control_summary", "02_baseline_control_summary.csv"
    )
    frozen_candidate_path = output_dir / _output_name(outputs, "frozen_candidate", "02_frozen_candidate.json")
    frozen_md_path = output_dir / _output_name(outputs, "frozen_candidate_markdown", "02_frozen_candidate.md")
    best_params_path = output_dir / _output_name(outputs, "best_params_by_family", "02_best_params_by_family.json")
    handoff_path = output_dir / _output_name(outputs, "stage03_handoff", "02_stage03_handoff.json")

    summary.to_csv(summary_path, index=False)
    trial_ledger.to_csv(trial_ledger_path, index=False)
    plan_ledger.to_csv(plan_ledger_path, index=False)
    hpo_summary.to_csv(hpo_summary_path, index=False)
    baseline_summary.to_csv(baseline_summary_path, index=False)
    frozen_candidate_path = write_json(frozen_candidate_path, frozen_candidate)
    frozen_md_path.write_text(_frozen_candidate_markdown(frozen_candidate), encoding="utf-8")
    best_params_path = write_json(best_params_path, best_params)
    handoff_path = write_json(handoff_path, stage03_handoff)
    frozen_param_paths = _write_frozen_param_yamls(output_dir, outputs, frozen_candidate)

    notebook_path = resolve_repo_path(inputs["notebook_path"])
    input_artifacts = [str(path) for path in stage01_paths.values()]
    if stage00_context is not None:
        input_artifacts.extend(str(path) for path in stage00_context.stage00_paths.values())
    manifest_payload = {
        "route": config["route"],
        "stage_name": config["stage_name"],
        "scope": config["scope"],
        "run_id": run_id,
        "stage02_run_id": run_id,
        "superseded_stage02_run_ids": _superseded_stage02_run_ids(config),
        "config_sha256": hash_mapping(config),
        "notebook_sha256": hash_file(notebook_path),
        "source_stage00_run_id": inputs.get("stage00_run_id", stage01_handoff.get("source_stage00_run_id")),
        "source_stage01_run_id": inputs["stage01_run_id"],
        "input_artifacts": input_artifacts,
        "output_artifacts": [
            summary_path.name,
            plan_ledger_path.name,
            trial_ledger_path.name,
            hpo_summary_path.name,
            baseline_summary_path.name,
            frozen_candidate_path.name,
            frozen_md_path.name,
            best_params_path.name,
            handoff_path.name,
            *[str(path.relative_to(output_dir)) for path in frozen_param_paths],
        ],
        "stage02_execution_mode": execution_mode,
        "hpo_method": "bounded_predeclared_profile_grid",
        "hpo_budget_rows": int(len(trial_ledger)),
        "hpo_completed_rows": int(trial_ledger["fit_status"].eq("completed").sum())
        if not trial_ledger.empty
        else 0,
        "search_space_sha256": _search_space_hashes(config, approved_families),
        "fold_design_sha256": _fold_design_hash(stage00_context),
        "raw_file_integrity": _raw_file_integrity_manifest_field(stage00_context),
        **_feature_rebuild_manifest_fields(stage01_manifest),
        "random_seeds": [int(seed) for seed in config["train_inner"]["seeds"]],
        **git_commit_fields(),
        "approved_model_families_for_stage02": list(approved_families),
        "stage02_modeling_scope_axis": _stage02_modeling_scope_axis(stage01_handoff),
        "baseline_registry_names": _baseline_ids(config),
        "official_validation_for_selection": False,
        "no_final_model_selected": True,
        "holdout_test_contact": False,
    }
    manifest_payload.update(device_provenance)
    manifest_path = write_json(output_dir / _output_name(outputs, "manifest", "run_manifest.json"), manifest_payload)
    inventory_path = write_artifact_inventory(
        output_dir,
        {
            "run_manifest": manifest_path,
            "summary": summary_path,
            "hpo_plan_ledger": plan_ledger_path,
            "hpo_trial_ledger": trial_ledger_path,
            "hpo_summary": hpo_summary_path,
            "baseline_control_summary": baseline_summary_path,
            "frozen_candidate": frozen_candidate_path,
            "frozen_candidate_markdown": frozen_md_path,
            "best_params_by_family": best_params_path,
            "stage03_handoff": handoff_path,
            **{
                f"frozen_params_{index}": path
                for index, path in enumerate(frozen_param_paths, start=1)
            },
        },
    )

    return Stage02Result(
        output_dir=output_dir,
        run_manifest=manifest_path,
        artifact_inventory=inventory_path,
        summary=summary_path,
        hpo_plan_ledger=plan_ledger_path,
        best_params_by_family=best_params_path,
        stage03_handoff=handoff_path,
        hpo_trial_ledger=trial_ledger_path,
        hpo_summary=hpo_summary_path,
        baseline_control_summary=baseline_summary_path,
        frozen_candidate=frozen_candidate_path,
        frozen_candidate_markdown=frozen_md_path,
    )


def _validate_config(config: Mapping[str, Any]) -> None:
    if config.get("stage_name") != "02_model_hpo_train_inner":
        raise ValueError(f"expected Stage 02 config, got {config.get('stage_name')!r}")
    if config.get("scope") != "validation_only":
        raise ValueError(f"expected validation_only scope, got {config.get('scope')!r}")
    if config.get("holdout_test_contact") is not False:
        raise ValueError("Stage 02 requires holdout_test_contact=false")

    inputs = require_mapping(config["inputs"], "inputs")
    if "stage01_run_id" not in inputs:
        raise ValueError("Stage 02 config requires inputs.stage01_run_id")

    train_inner = require_mapping(config["train_inner"], "train_inner")
    if train_inner.get("official_validation_for_selection") is not False:
        raise ValueError("Stage 02 HPO must use train-inner folds only")
    if int(train_inner["n_folds"]) < 1:
        raise ValueError("train_inner.n_folds must be at least 1")

    selection_rules = require_mapping(config["selection_rules"], "selection_rules")
    if selection_rules.get("no_official_validation_selection") is not True:
        raise ValueError("Stage 02 must declare no_official_validation_selection=true")
    if selection_rules.get("no_final_model_selected") is not True:
        raise ValueError("Stage 02 must declare no_final_model_selected=true")
    if int(selection_rules.get("minimum_positive_ticker_count", 0)) < 0:
        raise ValueError("selection_rules.minimum_positive_ticker_count must be non-negative")

    lightgbm_defaults = require_mapping(
        config.get("lightgbm_training_defaults", {}), "lightgbm_training_defaults"
    )
    if int(lightgbm_defaults.get("early_stopping_rounds", 0)) > 0:
        if lightgbm_defaults.get("early_stopping_validation_source") != "inner_train_chronological_tail":
            raise ValueError(
                "LightGBM early stopping must use inner_train_chronological_tail, not scored inner-eval rows"
            )
    torch_defaults = torch_training_defaults(config)
    torch_early_stopping = str(torch_defaults.get("early_stopping", "none"))
    if torch_early_stopping not in {"none", "inner_train_chronological_tail"}:
        raise ValueError("Torch early_stopping must be none or inner_train_chronological_tail")
    if torch_early_stopping == "inner_train_chronological_tail":
        fraction = float(torch_defaults.get("early_stopping_validation_fraction", 0.2))
        if not 0.0 < fraction < 1.0:
            raise ValueError("Torch early_stopping_validation_fraction must be between 0 and 1")
        if int(torch_defaults.get("minimum_early_stopping_train_samples", 0)) < 1:
            raise ValueError("Torch minimum_early_stopping_train_samples must be positive")
        if int(torch_defaults.get("minimum_early_stopping_validation_samples", 0)) < 1:
            raise ValueError("Torch minimum_early_stopping_validation_samples must be positive")
        if int(torch_defaults.get("early_stopping_patience", 0)) < 1:
            raise ValueError("Torch early_stopping_patience must be positive")


def _output_name(outputs: Mapping[str, Any], key: str, default: str) -> str:
    return str(outputs.get(key, default))


def _resolve_run_id(configured_run_id: Any | None = None) -> str:
    if configured_run_id in (None, ""):
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    run_id = str(configured_run_id)
    if RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise ValueError(
            "Stage 02 outputs.run_id must match YYYYMMDD_HHMMSS_microseconds, "
            f"got {run_id!r}"
        )
    return run_id


def _superseded_stage02_run_ids(config: Mapping[str, Any]) -> list[str]:
    value = config.get("superseded_stage02_run_ids", [])
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise TypeError("Stage 02 superseded_stage02_run_ids must be a list")
    return [str(item) for item in value]


def _validate_stage01_contract(
    config: Mapping[str, Any],
    stage01_manifest: Mapping[str, Any],
    stage01_handoff: Mapping[str, Any],
) -> None:
    if stage01_manifest.get("holdout_test_contact") is not False:
        raise ValueError("Stage 02 requires Stage 01 run_manifest holdout_test_contact=false")
    if stage01_handoff.get("holdout_test_contact") is not False:
        raise ValueError("Stage 02 requires Stage 01 candidate handoff holdout_test_contact=false")
    if stage01_handoff.get("no_final_model_selected") is not True:
        raise ValueError("Stage 02 requires Stage 01 handoff no_final_model_selected=true")
    configured_stage00 = config["inputs"].get("stage00_run_id")
    source_stage00 = stage01_handoff.get("source_stage00_run_id")
    if configured_stage00 and source_stage00 and str(configured_stage00) != str(source_stage00):
        raise ValueError(
            "Stage 02 configured Stage 00 run id does not match Stage 01 handoff: "
            f"{configured_stage00!r} != {source_stage00!r}"
        )
    source_feature_hash = stage01_manifest.get("feature_rebuild_code_sha256")
    current_feature_hash = feature_rebuild_code_sha256()
    if source_feature_hash and str(source_feature_hash) != current_feature_hash:
        raise ValueError(
            "Stage 01 feature rebuild code hash does not match current Stage 02 rebuild code: "
            f"{source_feature_hash!r} != {current_feature_hash!r}"
        )


def _candidate_inputs(stage01_handoff: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates = stage01_handoff.get("candidate_inputs", [])
    if not isinstance(candidates, list):
        raise TypeError("01_candidate_inputs.json field candidate_inputs must be a list")
    for candidate in candidates:
        require_mapping(candidate, "candidate_input")
    return candidates


def _approved_families(
    stage01_handoff: Mapping[str, Any], config: Mapping[str, Any]
) -> tuple[str, ...]:
    approved = stage01_handoff.get("approved_model_families_for_stage02", [])
    if not isinstance(approved, list):
        raise TypeError(
            "01_candidate_inputs.json field approved_model_families_for_stage02 must be a list"
        )
    approved_families = tuple(str(value) for value in approved)
    active_families = set(_active_hpo_families(config))
    unknown = sorted(set(approved_families) - active_families)
    if unknown:
        raise ValueError(f"Stage 01 approved families not enabled in Stage 02 config: {unknown}")
    return approved_families


def _active_hpo_families(config: Mapping[str, Any]) -> tuple[str, ...]:
    families = require_mapping(config["hpo_families"], "hpo_families")
    active = []
    for family, family_config in families.items():
        if require_mapping(family_config, f"hpo_families.{family}").get("enabled") is True:
            if str(family) not in PROBE_BY_FAMILY:
                raise ValueError(f"Stage 02 enabled unknown HPO family: {family}")
            active.append(str(family))
    if not active:
        raise ValueError("Stage 02 requires at least one enabled HPO family")
    return tuple(active)


def _stage01_block_reason(
    stage01_handoff: Mapping[str, Any],
    candidates: list[Mapping[str, Any]],
    approved_families: tuple[str, ...],
) -> str:
    decision = str(stage01_handoff.get("decision", ""))
    if decision.startswith("do_not_start"):
        return decision
    if not candidates:
        return "stage01_candidate_inputs_empty"
    if not approved_families:
        return "stage01_approved_model_families_empty"
    return ""


def _load_stage02_data_context(
    config: Mapping[str, Any], stage01_handoff: Mapping[str, Any]
) -> Stage02DataContext:
    inputs = require_mapping(config["inputs"], "inputs")
    stage00_run_dir = Path(str(inputs["stage00_runtime_run_dir"]))
    stage00_paths = require_artifacts(stage00_run_dir, inputs["required_stage00_artifacts"])

    stage00_manifest = read_json_object(stage00_paths["run_manifest.json"])
    if stage00_manifest.get("holdout_test_contact") is not False:
        raise ValueError("Stage 02 requires Stage 00 run_manifest holdout_test_contact=false")
    if stage01_handoff.get("source_stage00_run_id") and inputs.get("stage00_run_id"):
        if str(stage01_handoff["source_stage00_run_id"]) != str(inputs["stage00_run_id"]):
            raise ValueError("Stage 02 Stage 00 run id does not match Stage 01 handoff")

    raw_manifest = read_json_object(stage00_paths["raw_data_manifest.json"])
    split_freeze = read_json_object(stage00_paths["split_freeze.json"])
    sample_events = load_sample_event_index(stage00_paths["sample_event_index.csv"])
    train_events = train_valid_events(sample_events)
    train_bars = load_train_bars(raw_manifest, split_freeze, inputs)
    feature_frame = build_feature_frame(train_bars)
    folds = build_train_inner_folds(train_events, int(config["train_inner"]["n_folds"]))
    expected_overlap = int(config["train_inner"].get("event_overlap_count_required", 0))
    if not folds["event_overlap_count"].eq(expected_overlap).all():
        raise ValueError("Stage 02 train-inner fold overlap check failed")
    return Stage02DataContext(
        stage00_paths=stage00_paths,
        stage00_manifest=stage00_manifest,
        raw_manifest=raw_manifest,
        split_freeze=split_freeze,
        train_events=train_events,
        feature_frame=feature_frame,
        folds=folds,
    )


def _load_search_profiles(
    approved_families: tuple[str, ...],
    config: Mapping[str, Any],
) -> dict[str, list[Mapping[str, Any]]]:
    family_configs = require_mapping(config["hpo_families"], "hpo_families")
    max_profiles = int(require_mapping(config["budget"], "budget")["max_profiles_per_family"])
    profiles_by_family: dict[str, list[Mapping[str, Any]]] = {}
    for family in approved_families:
        family_config = require_mapping(family_configs[family], f"hpo_families.{family}")
        search_space_path = resolve_repo_path(family_config["search_space"])
        search_space = load_yaml(search_space_path)
        if search_space.get("model_family") != family:
            raise ValueError(
                f"search space model_family mismatch for {family}: {search_space_path}"
            )
        profiles = search_space.get("profiles", [])
        if not isinstance(profiles, list) or not profiles:
            raise ValueError(f"search space requires non-empty profiles: {search_space_path}")
        if len(profiles) > max_profiles:
            raise ValueError(
                f"search space {search_space_path} has {len(profiles)} profiles, "
                f"exceeding max_profiles_per_family={max_profiles}"
            )
        profiles_by_family[family] = [require_mapping(profile, "profile") for profile in profiles]
    return profiles_by_family


def _search_space_hashes(config: Mapping[str, Any], approved_families: tuple[str, ...]) -> dict[str, str]:
    family_configs = require_mapping(config["hpo_families"], "hpo_families")
    hashes: dict[str, str] = {}
    for family in approved_families:
        family_config = require_mapping(family_configs[family], f"hpo_families.{family}")
        hashes[str(family)] = hash_file(resolve_repo_path(family_config["search_space"]))
    return hashes


def _fold_design_hash(data_context: Stage02DataContext | None) -> str | None:
    if data_context is None:
        return None
    return hash_mapping({"folds": data_context.folds.to_dict(orient="records")})


def _raw_file_integrity_manifest_field(
    data_context: Stage02DataContext | None,
) -> dict[str, Any] | None:
    if data_context is None:
        return None
    return raw_manifest_integrity_summary(data_context.raw_manifest)


def _feature_rebuild_manifest_fields(stage01_manifest: Mapping[str, Any]) -> dict[str, Any]:
    current_feature_hash = feature_rebuild_code_sha256()
    source_feature_hash = stage01_manifest.get("feature_rebuild_code_sha256")
    if source_feature_hash:
        match = str(source_feature_hash) == current_feature_hash
        reason = "matched" if match else "mismatch"
    else:
        match = None
        reason = "stage01_manifest_field_missing_legacy_run"
    return {
        "stage02_feature_rebuild_code_sha256": current_feature_hash,
        "source_stage01_feature_rebuild_code_sha256": source_feature_hash,
        "feature_rebuild_code_match": match,
        "feature_rebuild_code_match_reason": reason,
    }


def _planned_hpo_rows(
    candidates: list[Mapping[str, Any]],
    profiles_by_family: Mapping[str, list[Mapping[str, Any]]],
    folds: pd.DataFrame,
    config: Mapping[str, Any],
) -> int:
    seeds = tuple(int(seed) for seed in config["train_inner"]["seeds"])
    return int(len(candidates) * sum(len(profiles) for profiles in profiles_by_family.values()) * len(folds) * len(seeds))


def _enforce_budget(planned_rows: int, config: Mapping[str, Any]) -> None:
    cap = int(require_mapping(config["budget"], "budget")["max_hpo_plan_rows"])
    if planned_rows > cap:
        raise ValueError(f"Stage 02 planned HPO rows {planned_rows} exceed budget cap {cap}")


def _run_hpo_trials(
    candidates: list[Mapping[str, Any]],
    profiles_by_family: Mapping[str, list[Mapping[str, Any]]],
    data_context: Stage02DataContext,
    stage01_summary: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    run_id: str,
    planned_hpo_rows: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    seeds = tuple(int(seed) for seed in config["train_inner"]["seeds"])
    primary_baseline = str(config["selection_rules"]["baseline"])
    baseline_ids = _baseline_ids(config)
    trial_rows: list[dict[str, Any]] = []
    baseline_rows: list[dict[str, Any]] = []

    for candidate in candidates:
        dataset = _prepare_candidate_dataset(candidate, data_context)
        validate_rebuilt_candidate_counts(candidate, dataset, stage01_summary)
        feature_columns = tuple(str(column) for column in candidate.get("feature_columns", []))
        for fold in data_context.folds.to_dict(orient="records"):
            train_idx, eval_idx = _fold_capped_indices(dataset, fold, config)
            x_train, train_meta, x_eval, eval_meta = _materialize_fold_data(dataset, train_idx, eval_idx)
            train_hash = sample_id_hash(train_meta["sample_id"].tolist())
            eval_hash = sample_id_hash(eval_meta["sample_id"].tolist())
            y_train = train_meta["label"].to_numpy(dtype=int)
            y_eval = eval_meta["label"].to_numpy(dtype=int)
            for seed in seeds:
                baseline_scores = {
                    baseline_id: metrics.score_registry_baseline(baseline_id, y_train, y_eval, seed)
                    for baseline_id in baseline_ids
                }
                for baseline_id, baseline_score in baseline_scores.items():
                    baseline_rows.append(
                        _baseline_summary_row(
                            candidate,
                            fold,
                            seed,
                            baseline_id,
                            baseline_score,
                            len(train_meta),
                            len(eval_meta),
                            train_hash,
                            eval_hash,
                        )
                    )
                selected_baseline = baseline_scores[primary_baseline]
                for family, profiles in profiles_by_family.items():
                    probe_id = PROBE_BY_FAMILY[family]
                    for profile in profiles:
                        row = _empty_trial_row(
                            candidate=candidate,
                            feature_columns=feature_columns,
                            family=family,
                            probe_id=probe_id,
                            profile=profile,
                            fold=fold,
                            seed=seed,
                            n_train=len(train_meta),
                            n_eval=len(eval_meta),
                            train_hash=train_hash,
                            eval_hash=eval_hash,
                            baseline_id=primary_baseline,
                            baseline_score=selected_baseline,
                        )
                        if selected_baseline["fit_status"] != "completed_baseline":
                            row["fit_status"] = "skipped_baseline_failed"
                            row["error_message"] = str(selected_baseline["error_message"])
                        else:
                            outcome = _fit_stage02_model(
                                family=family,
                                profile=profile,
                                x_train=x_train,
                                train_meta=train_meta,
                                x_eval=x_eval,
                                eval_meta=eval_meta,
                                config=config,
                                seed=seed,
                                window_size=int(candidate["window_size"]),
                                n_features=len(feature_columns),
                                baseline_predictions=selected_baseline["predictions"],
                            )
                            row.update(_trial_outcome_fields(outcome, selected_baseline))
                        trial_rows.append(row)
                        _maybe_write_incremental_checkpoint(
                            config=config,
                            run_id=run_id,
                            trial_rows=trial_rows,
                            baseline_rows=baseline_rows,
                            planned_hpo_rows=planned_hpo_rows,
                        )

    return (
        pd.DataFrame(trial_rows, columns=HPO_TRIAL_LEDGER_COLUMNS),
        pd.DataFrame(baseline_rows, columns=BASELINE_CONTROL_COLUMNS),
    )


def _build_hpo_plan_ledger(trial_ledger: pd.DataFrame) -> pd.DataFrame:
    if trial_ledger.empty:
        return pd.DataFrame(columns=HPO_PLAN_LEDGER_COLUMNS)
    missing = [
        column
        for column in HPO_PLAN_LEDGER_COLUMNS
        if column != "plan_status" and column not in trial_ledger.columns
    ]
    if missing:
        raise ValueError(f"cannot build Stage 02 HPO plan ledger; missing columns: {missing}")
    plan = trial_ledger[[column for column in HPO_PLAN_LEDGER_COLUMNS if column != "plan_status"]].copy()
    insert_at = HPO_PLAN_LEDGER_COLUMNS.index("plan_status")
    plan.insert(insert_at, "plan_status", "planned")
    return plan[HPO_PLAN_LEDGER_COLUMNS]


def _prepare_candidate_dataset(
    candidate: Mapping[str, Any], data_context: Stage02DataContext
) -> CandidateDataset:
    feature_set = str(candidate["feature_set"])
    feature_columns = tuple(str(column) for column in candidate["feature_columns"])
    require_feature_columns(feature_columns, data_context.feature_frame)
    return build_window_dataset(
        data_context.feature_frame,
        data_context.train_events,
        feature_set=feature_set,
        feature_columns=feature_columns,
        window_size=int(candidate["window_size"]),
    )


def _fold_capped_indices(
    dataset: CandidateDataset, fold: Mapping[str, Any], config: Mapping[str, Any]
) -> tuple[np.ndarray, np.ndarray]:
    train_idx, eval_idx = fold_indices(dataset.metadata, fold)
    sample_policy = require_mapping(config.get("hpo_sample_policy", {}), "hpo_sample_policy")
    train_cap = int(sample_policy.get("max_train_samples_per_fold", 0))
    eval_cap = int(sample_policy.get("max_eval_samples_per_fold", 0))
    return (
        cap_indices(dataset.metadata, train_idx, train_cap),
        cap_indices(dataset.metadata, eval_idx, eval_cap),
    )


def _materialize_fold_data(
    dataset: CandidateDataset, train_idx: np.ndarray, eval_idx: np.ndarray
) -> tuple[np.ndarray, pd.DataFrame, np.ndarray, pd.DataFrame]:
    train_meta = dataset.metadata.iloc[train_idx].copy().reset_index(drop=True)
    eval_meta = dataset.metadata.iloc[eval_idx].copy().reset_index(drop=True)
    x_train = materialize_window_matrix(dataset, train_idx)
    x_eval = materialize_window_matrix(dataset, eval_idx)
    return x_train, train_meta, x_eval, eval_meta


def _baseline_ids(config: Mapping[str, Any]) -> list[str]:
    baseline_controls = config.get("baseline_controls", {})
    if isinstance(baseline_controls, Mapping):
        declared = baseline_controls.get("mandatory", DEFAULT_BASELINES)
    else:
        declared = DEFAULT_BASELINES
    baseline_ids = [str(value) for value in declared]
    missing_primary = str(config["selection_rules"]["baseline"]) not in baseline_ids
    if missing_primary:
        baseline_ids.insert(0, str(config["selection_rules"]["baseline"]))
    return baseline_ids


def _baseline_summary_row(
    candidate: Mapping[str, Any],
    fold: Mapping[str, Any],
    seed: int,
    baseline_id: str,
    baseline_score: Mapping[str, Any],
    n_train: int,
    n_eval: int,
    train_hash: str,
    eval_hash: str,
) -> dict[str, Any]:
    return {
        "candidate_id": str(candidate["candidate_id"]),
        "feature_set": str(candidate["feature_set"]),
        "window_size": int(candidate["window_size"]),
        "fold_id": str(fold["fold_id"]),
        "seed": int(seed),
        "baseline_id": baseline_id,
        "fit_status": baseline_score["fit_status"],
        "n_train_samples": int(n_train),
        "n_eval_samples": int(n_eval),
        "train_sample_id_hash": train_hash,
        "eval_sample_id_hash": eval_hash,
        "sample_id_hash": eval_hash,
        "macro_f1": baseline_score["macro_f1"],
        "balanced_accuracy": baseline_score["balanced_accuracy"],
        "accuracy": baseline_score["accuracy"],
        "roc_auc": baseline_score["roc_auc"],
        "mcc": baseline_score["mcc"],
        "error_message": baseline_score["error_message"],
    }


def _empty_trial_row(
    *,
    candidate: Mapping[str, Any],
    feature_columns: tuple[str, ...],
    family: str,
    probe_id: str,
    profile: Mapping[str, Any],
    fold: Mapping[str, Any],
    seed: int,
    n_train: int,
    n_eval: int,
    train_hash: str,
    eval_hash: str,
    baseline_id: str,
    baseline_score: Mapping[str, Any],
) -> dict[str, Any]:
    profile_id = str(profile["profile_id"])
    candidate_id = str(candidate["candidate_id"])
    return {
        "trial_id": f"{candidate_id}__{family}__{profile_id}__{fold['fold_id']}__seed{seed}",
        "candidate_id": candidate_id,
        "feature_set": str(candidate["feature_set"]),
        "feature_columns_json": json.dumps(list(feature_columns)),
        "window_size": int(candidate["window_size"]),
        "model_family": family,
        "probe_id": probe_id,
        "hpo_profile_id": profile_id,
        "hpo_profile_params_json": json.dumps(profile_params(profile), sort_keys=True),
        "fold_id": str(fold["fold_id"]),
        "seed": int(seed),
        "fit_status": "not_started",
        "n_train_samples": int(n_train),
        "n_eval_samples": int(n_eval),
        "train_sample_id_hash": train_hash,
        "eval_sample_id_hash": eval_hash,
        "sample_id_hash": eval_hash,
        "baseline_id": baseline_id,
        "baseline_fit_status": baseline_score["fit_status"],
        "baseline_macro_f1": baseline_score["macro_f1"],
        "baseline_balanced_accuracy": baseline_score["balanced_accuracy"],
        "baseline_accuracy": baseline_score["accuracy"],
        "baseline_roc_auc": baseline_score["roc_auc"],
        "baseline_mcc": baseline_score["mcc"],
        "macro_f1": pd.NA,
        "balanced_accuracy": pd.NA,
        "accuracy": pd.NA,
        "roc_auc": pd.NA,
        "mcc": pd.NA,
        "delta_macro_f1_vs_baseline": pd.NA,
        "delta_balanced_accuracy_vs_baseline": pd.NA,
        "positive_ticker_count": pd.NA,
        "ticker_delta_macro_f1_json": "{}",
        "block_delta_macro_f1_json": "{}",
        "requested_device": pd.NA,
        "resolved_device": pd.NA,
        "device_fallback_reason": pd.NA,
        "best_iteration": pd.NA,
        "early_stopping_source": pd.NA,
        "early_stopping_used": pd.NA,
        "early_stopping_reason": pd.NA,
        "early_stopping_train_sample_id_hash": pd.NA,
        "early_stopping_eval_sample_id_hash": pd.NA,
        "selected_for_stage03": False,
        "error_message": "",
    }


def _fit_stage02_model(
    *,
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
    baseline_predictions: np.ndarray,
) -> dict[str, Any]:
    y_train = train_meta["label"].to_numpy(dtype=int)
    y_eval = eval_meta["label"].to_numpy(dtype=int)
    if len(y_train) == 0 or len(y_eval) == 0:
        return {
            "fit_status": "skipped_no_fold_samples",
            "error_message": "trial has no train/eval samples for this fold",
        }
    if len(np.unique(y_train)) < 2:
        return {
            "fit_status": "failed_single_class_train",
            "error_message": "train-inner fold train labels contain fewer than two classes",
        }
    if family == "lightgbm":
        return _fit_lightgbm_hpo_trial(
            profile=profile,
            x_train=x_train,
            y_train=y_train,
            train_meta=train_meta,
            x_eval=x_eval,
            y_eval=y_eval,
            eval_meta=eval_meta,
            seed=seed,
            baseline_predictions=baseline_predictions,
            config=config,
        )
    probe_id = PROBE_BY_FAMILY[family]
    trial_config = probe_trial_config(config, probe_id, profile)
    return fit_probe(
        probe_id,
        x_train,
        train_meta,
        x_eval,
        eval_meta,
        trial_config,
        seed,
        window_size,
        n_features,
        baseline_predictions,
    )


def _fit_lightgbm_hpo_trial(
    *,
    profile: Mapping[str, Any],
    x_train: np.ndarray,
    y_train: np.ndarray,
    train_meta: pd.DataFrame,
    x_eval: np.ndarray,
    y_eval: np.ndarray,
    eval_meta: pd.DataFrame,
    seed: int,
    baseline_predictions: np.ndarray,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        from lightgbm import LGBMClassifier
    except ModuleNotFoundError as exc:
        return {"fit_status": "failed_dependency_missing", "error_message": str(exc)}

    params = lightgbm_hpo_params(profile)
    model = LGBMClassifier(**params, random_state=seed, verbosity=-1)
    training_defaults = require_mapping(
        config.get("lightgbm_training_defaults", {}), "lightgbm_training_defaults"
    )
    split, fit_kwargs = lightgbm_tail_split_and_fit_kwargs(
        x_train=x_train,
        y_train=y_train,
        train_meta=train_meta,
        training_defaults=training_defaults,
    )
    try:
        model.fit(
            split["x_fit"],
            split["y_fit"],
            **fit_kwargs,
        )
        predictions = model.predict(x_eval).astype(int)
        scores = model.predict_proba(x_eval)[:, 1].astype(float)
        outcome = _score_model_predictions(eval_meta, predictions, scores, baseline_predictions)
        outcome["best_iteration"] = getattr(model, "best_iteration_", None)
        outcome.update(_early_stopping_outcome_fields(split))
        return outcome
    except (ValueError, RuntimeError, FloatingPointError) as exc:
        return {
            "fit_status": "failed_exception",
            "error_message": f"{type(exc).__name__}: {exc}",
            **_early_stopping_outcome_fields(split),
        }


def _early_stopping_outcome_fields(split: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "early_stopping_source": split.get("early_stopping_source", pd.NA),
        "early_stopping_used": bool(split.get("early_stopping_used", False)),
        "early_stopping_reason": split.get("early_stopping_reason", ""),
        "early_stopping_train_sample_id_hash": split.get(
            "early_stopping_train_sample_id_hash", ""
        ),
        "early_stopping_eval_sample_id_hash": split.get(
            "early_stopping_eval_sample_id_hash", ""
        ),
    }


def _stage02_modeling_scope_axis(stage01_handoff: Mapping[str, Any]) -> list[str]:
    axis = stage01_handoff.get(
        "stage02_modeling_scope_axis", stage01_handoff.get("modeling_scope_axis", [])
    )
    if axis is None:
        return []
    if isinstance(axis, str):
        return [axis]
    if isinstance(axis, list):
        return [str(item) for item in axis]
    raise TypeError("stage02_modeling_scope_axis must be a list of strings")


def _device_manifest_fields(config: Mapping[str, Any], trial_ledger: pd.DataFrame) -> dict[str, Any]:
    requested_device = str(torch_training_defaults(config).get("device", "auto"))
    if trial_ledger.empty:
        return {
            "requested_device": requested_device,
            "resolved_device": "not_resolved",
            "cuda_available": False,
            "gpu_name_or_null": None,
            "device_fallback_reason": "no_hpo_trials_completed",
        }

    torch_rows = trial_ledger.loc[trial_ledger["model_family"].isin(TORCH_FAMILIES)]
    completed = torch_rows.loc[torch_rows["fit_status"].eq("completed")]
    if completed.empty:
        resolved_device = "not_resolved"
        fallback_reason = "torch_hpo_trials_not_completed"
    else:
        resolved_values = sorted(
            str(value)
            for value in completed["resolved_device"].dropna().unique()
            if str(value) and str(value) != "<NA>"
        )
        fallback_values = sorted(
            str(value)
            for value in completed["device_fallback_reason"].dropna().unique()
            if str(value) and str(value) != "<NA>"
        )
        resolved_device = ",".join(resolved_values) if resolved_values else "not_resolved"
        fallback_reason = ",".join(fallback_values)
    cuda_resolved = any(value.strip().startswith("cuda") for value in resolved_device.split(","))
    runtime_fields = (
        _torch_runtime_device_fields()
        if cuda_resolved
        else {"cuda_available": False, "gpu_name_or_null": None}
    )
    cuda_available = bool(runtime_fields["cuda_available"] or cuda_resolved)
    return {
        "requested_device": requested_device,
        "resolved_device": resolved_device,
        "cuda_available": cuda_available,
        "gpu_name_or_null": runtime_fields["gpu_name_or_null"] if cuda_available else None,
        "device_fallback_reason": fallback_reason,
    }


def _torch_runtime_device_fields() -> dict[str, Any]:
    try:
        torch_module = importlib.import_module("torch")
    except (ImportError, ModuleNotFoundError, OSError):
        return {"cuda_available": False, "gpu_name_or_null": None}

    cuda_available = bool(torch_module.cuda.is_available())
    gpu_name: str | None = None
    if cuda_available:
        try:
            gpu_name = str(torch_module.cuda.get_device_name(0))
        except (AttributeError, RuntimeError, ValueError):
            gpu_name = None
    return {"cuda_available": cuda_available, "gpu_name_or_null": gpu_name}


def _score_model_predictions(
    eval_meta: pd.DataFrame,
    predictions: np.ndarray,
    scores: np.ndarray,
    baseline_predictions: np.ndarray,
) -> dict[str, Any]:
    y_eval = eval_meta["label"].to_numpy(dtype=int)
    scored = metrics.score_classifier(y_eval, predictions, y_score=scores)
    ticker_deltas, positive_ticker_count = ticker_delta_macro_f1(
        eval_meta, predictions, baseline_predictions
    )
    block_deltas = block_delta_macro_f1(eval_meta, predictions, baseline_predictions)
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
        "requested_device": "cpu",
        "resolved_device": "cpu",
        "device_fallback_reason": "not_gpu_capable_trial",
    }


def _trial_outcome_fields(
    outcome: Mapping[str, Any], baseline_score: Mapping[str, Any]
) -> dict[str, Any]:
    if outcome.get("fit_status") != "completed":
        return {
            "fit_status": outcome.get("fit_status", "failed_unknown"),
            "early_stopping_source": outcome.get("early_stopping_source", pd.NA),
            "early_stopping_used": outcome.get("early_stopping_used", pd.NA),
            "early_stopping_reason": outcome.get("early_stopping_reason", pd.NA),
            "early_stopping_train_sample_id_hash": outcome.get(
                "early_stopping_train_sample_id_hash", pd.NA
            ),
            "early_stopping_eval_sample_id_hash": outcome.get(
                "early_stopping_eval_sample_id_hash", pd.NA
            ),
            "error_message": outcome.get("error_message", ""),
        }
    macro_f1 = float(outcome["macro_f1"])
    balanced_accuracy = float(outcome["balanced_accuracy"])
    baseline_macro = float(baseline_score["macro_f1"])
    baseline_balanced = float(baseline_score["balanced_accuracy"])
    return {
        "fit_status": "completed",
        "macro_f1": macro_f1,
        "balanced_accuracy": balanced_accuracy,
        "accuracy": outcome.get("accuracy", pd.NA),
        "roc_auc": outcome.get("roc_auc", pd.NA),
        "mcc": outcome.get("mcc", pd.NA),
        "delta_macro_f1_vs_baseline": macro_f1 - baseline_macro,
        "delta_balanced_accuracy_vs_baseline": balanced_accuracy - baseline_balanced,
        "positive_ticker_count": outcome.get("positive_ticker_count", pd.NA),
        "ticker_delta_macro_f1_json": outcome.get("ticker_delta_macro_f1_json", "{}"),
        "block_delta_macro_f1_json": outcome.get("block_delta_macro_f1_json", "{}"),
        "requested_device": outcome.get("requested_device", pd.NA),
        "resolved_device": outcome.get("resolved_device", pd.NA),
        "device_fallback_reason": outcome.get("device_fallback_reason", pd.NA),
        "best_iteration": outcome.get("best_iteration", pd.NA),
        "early_stopping_source": outcome.get("early_stopping_source", "not_applicable"),
        "early_stopping_used": outcome.get("early_stopping_used", False),
        "early_stopping_reason": outcome.get("early_stopping_reason", "not_lightgbm_trial"),
        "early_stopping_train_sample_id_hash": outcome.get(
            "early_stopping_train_sample_id_hash", ""
        ),
        "early_stopping_eval_sample_id_hash": outcome.get("early_stopping_eval_sample_id_hash", ""),
        "error_message": "",
    }


def _maybe_write_incremental_checkpoint(
    *,
    config: Mapping[str, Any],
    run_id: str,
    trial_rows: list[Mapping[str, Any]],
    baseline_rows: list[Mapping[str, Any]],
    planned_hpo_rows: int,
) -> None:
    checkpointing = config.get("checkpointing", {})
    if not isinstance(checkpointing, Mapping) or checkpointing.get("enabled") is not True:
        return
    every = max(1, int(checkpointing.get("checkpoint_every_trials", 8)))
    if len(trial_rows) % every != 0:
        return
    checkpoint_root = Path(
        str(checkpointing.get("checkpoint_dir", "/content/lst_models_checkpoints/02_model_hpo_train_inner"))
    )
    checkpoint_dir = checkpoint_root / run_id
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(trial_rows, columns=HPO_TRIAL_LEDGER_COLUMNS).to_csv(
        checkpoint_dir / "02_hpo_trial_ledger_partial.csv", index=False
    )
    pd.DataFrame(baseline_rows, columns=BASELINE_CONTROL_COLUMNS).to_csv(
        checkpoint_dir / "02_baseline_control_summary_partial.csv", index=False
    )
    manifest = {
        "stage_name": "02_model_hpo_train_inner",
        "run_id": run_id,
        "status": "incomplete",
        "completed_or_attempted_trial_rows": len(trial_rows),
        "planned_hpo_rows": int(planned_hpo_rows),
        "completed_units": {
            "trial_rows": len(trial_rows),
            "baseline_rows": len(baseline_rows),
            "last_trial_id": str(trial_rows[-1].get("trial_id", "")) if trial_rows else "",
        },
        "pending_units": {
            "trial_rows": max(0, int(planned_hpo_rows) - len(trial_rows)),
            "next_trial_index": len(trial_rows) + 1,
        },
        "baseline_rows": len(baseline_rows),
        "holdout_test_contact": False,
        "official_validation_for_selection": False,
        "resume_instructions": {
            "resume_mode": "exact_run_checkpoint_only",
            "required_run_id": run_id,
            "required_checkpoint_dir": str(checkpoint_dir),
            "required_files": [
                "checkpoint_manifest.json",
                "02_hpo_trial_ledger_partial.csv",
                "02_baseline_control_summary_partial.csv",
            ],
            "latest_parent_scan_allowed": False,
        },
        "checkpoint_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(checkpoint_dir / "checkpoint_manifest.json", manifest)


def _build_hpo_summary(
    trial_ledger: pd.DataFrame, baseline_summary: pd.DataFrame
) -> pd.DataFrame:
    if trial_ledger.empty:
        return pd.DataFrame(columns=HPO_SUMMARY_COLUMNS)
    baseline_lookup = _baseline_lookup(baseline_summary)
    rows = []
    group_columns = [
        "candidate_id",
        "feature_set",
        "window_size",
        "model_family",
        "probe_id",
        "hpo_profile_id",
        "hpo_profile_params_json",
    ]
    for key, group in trial_ledger.groupby(group_columns, sort=True, dropna=False):
        completed = group.loc[group["fit_status"].eq("completed")].copy()
        deltas = _baseline_delta_series(completed, baseline_lookup)
        rows.append(
            {
                "candidate_id": key[0],
                "feature_set": key[1],
                "window_size": int(key[2]),
                "model_family": key[3],
                "probe_id": key[4],
                "hpo_profile_id": key[5],
                "hpo_profile_params_json": key[6],
                "expected_rows": int(len(group)),
                "completed_rows": int(len(completed)),
                "failed_rows": int(len(group) - len(completed)),
                "mean_macro_f1": _mean_or_nan(completed["macro_f1"]),
                "mean_balanced_accuracy": _mean_or_nan(completed["balanced_accuracy"]),
                "mean_roc_auc": _mean_or_nan(completed["roc_auc"]),
                "mean_mcc": _mean_or_nan(completed["mcc"]),
                "mean_delta_macro_f1_vs_stratified_dummy_train_prior": _mean_or_nan(
                    deltas["stratified_dummy_train_prior"]
                ),
                "lcb_delta_macro_f1_vs_stratified_dummy_train_prior": metrics.compute_metric_lcb(
                    deltas["stratified_dummy_train_prior"].to_numpy(dtype=float)
                ),
                "mean_delta_macro_f1_vs_majority_train_prior": _mean_or_nan(
                    deltas["majority_train_prior"]
                ),
                "lcb_delta_macro_f1_vs_majority_train_prior": metrics.compute_metric_lcb(
                    deltas["majority_train_prior"].to_numpy(dtype=float)
                ),
                "min_positive_ticker_count": _min_or_nan(completed["positive_ticker_count"]),
                "mean_positive_ticker_count": _mean_or_nan(completed["positive_ticker_count"]),
                "selected_role": "",
                "selection_reason": "",
            }
        )
    return pd.DataFrame(rows, columns=HPO_SUMMARY_COLUMNS)


def _baseline_lookup(baseline_summary: pd.DataFrame) -> dict[tuple[str, str, int, str], float]:
    lookup: dict[tuple[str, str, int, str], float] = {}
    if baseline_summary.empty:
        return lookup
    for row in baseline_summary.to_dict(orient="records"):
        lookup[
            (
                str(row["candidate_id"]),
                str(row["fold_id"]),
                int(row["seed"]),
                str(row["baseline_id"]),
            )
        ] = float(row["macro_f1"]) if pd.notna(row["macro_f1"]) else np.nan
    return lookup


def _baseline_delta_series(
    completed: pd.DataFrame, baseline_lookup: Mapping[tuple[str, str, int, str], float]
) -> dict[str, pd.Series]:
    result = {}
    for baseline_id in ("stratified_dummy_train_prior", "majority_train_prior"):
        values = []
        for row in completed.to_dict(orient="records"):
            baseline_value = baseline_lookup.get(
                (str(row["candidate_id"]), str(row["fold_id"]), int(row["seed"]), baseline_id),
                np.nan,
            )
            values.append(float(row["macro_f1"]) - baseline_value)
        result[baseline_id] = pd.Series(values, dtype=float)
    return result


def _select_frozen_candidates(
    hpo_summary: pd.DataFrame, trial_ledger: pd.DataFrame, config: Mapping[str, Any]
) -> dict[str, Any]:
    selection_rules = require_mapping(config["selection_rules"], "selection_rules")
    if hpo_summary.empty:
        return _selection_bundle(
            ready_for_stage03=False,
            decision="do_not_start_stage03_no_hpo_summary_rows",
            block_reason="no_hpo_summary_rows",
            primary=None,
            fallback=None,
        )
    if bool(selection_rules.get("require_completed_rows_before_stage03", True)):
        if not trial_ledger["fit_status"].eq("completed").all():
            return _selection_bundle(
                ready_for_stage03=False,
                decision="do_not_start_stage03_hpo_trials_incomplete",
                block_reason="one_or_more_hpo_trials_failed_or_skipped",
                primary=None,
                fallback=None,
            )
    minimum_ticker_count = int(selection_rules.get("minimum_positive_ticker_count", 0))
    positive_ticker_count = pd.to_numeric(
        hpo_summary["min_positive_ticker_count"], errors="coerce"
    )
    eligible = hpo_summary.loc[
        (hpo_summary["completed_rows"] == hpo_summary["expected_rows"])
        & (hpo_summary["mean_delta_macro_f1_vs_stratified_dummy_train_prior"] > 0.0)
        & (hpo_summary["mean_delta_macro_f1_vs_majority_train_prior"] > 0.0)
        & (positive_ticker_count >= minimum_ticker_count)
    ].copy()
    if eligible.empty:
        return _selection_bundle(
            ready_for_stage03=False,
            decision="do_not_start_stage03_no_hpo_candidate_cleared_selection_gates",
            block_reason="no_hpo_candidate_cleared_baseline_or_ticker_robustness_gates",
            primary=None,
            fallback=None,
        )
    ranked_within_candidates = _rank_selection_frame(eligible)
    candidate_winners = ranked_within_candidates.groupby("candidate_id", sort=False).head(1)
    ranked_candidate_winners = _rank_selection_frame(candidate_winners)
    selections = _pick_primary_and_fallback(
        ranked_candidate_winners,
        ranked_within_candidates,
        max_per_family=int(selection_rules.get("max_selected_configs_per_family", 0)),
    )
    primary = selections[0] if selections else None
    fallback = selections[1] if len(selections) > 1 else None
    if primary is None or fallback is None:
        return _selection_bundle(
            ready_for_stage03=False,
            decision="do_not_start_stage03_missing_primary_or_fallback_candidate",
            block_reason="stage02_requires_primary_and_fallback_candidates",
            primary=primary,
            fallback=fallback,
        )
    return _selection_bundle(
        ready_for_stage03=True,
        decision="ready_for_stage03_frozen_train_inner_hpo_candidates",
        block_reason="",
        primary=primary,
        fallback=fallback,
    )


def _rank_selection_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values(
        [
            "lcb_delta_macro_f1_vs_stratified_dummy_train_prior",
            "mean_delta_macro_f1_vs_stratified_dummy_train_prior",
            "mean_macro_f1",
            "min_positive_ticker_count",
        ],
        ascending=[False, False, False, False],
    )


def _pick_primary_and_fallback(
    ranked_candidate_winners: pd.DataFrame,
    ranked_within_candidates: pd.DataFrame,
    *,
    max_per_family: int,
) -> list[dict[str, Any]]:
    selected_rows: list[Mapping[str, Any]] = []
    selected_keys: set[tuple[str, str, str]] = set()
    family_counts: dict[str, int] = {}

    def try_add(row: Mapping[str, Any]) -> None:
        key = (
            str(row["candidate_id"]),
            str(row["model_family"]),
            str(row["hpo_profile_id"]),
        )
        if key in selected_keys:
            return
        family = str(row["model_family"])
        if max_per_family > 0 and family_counts.get(family, 0) >= max_per_family:
            return
        selected_rows.append(row)
        selected_keys.add(key)
        family_counts[family] = family_counts.get(family, 0) + 1

    for row in ranked_candidate_winners.to_dict(orient="records"):
        try_add(row)
        if len(selected_rows) >= 2:
            return [_selection_record(row) for row in selected_rows]

    for row in ranked_within_candidates.to_dict(orient="records"):
        try_add(row)
        if len(selected_rows) >= 2:
            return [_selection_record(row) for row in selected_rows]

    return [_selection_record(row) for row in selected_rows]


def _selection_record(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(row["candidate_id"]),
        "feature_set": str(row["feature_set"]),
        "window_size": int(row["window_size"]),
        "model_family": str(row["model_family"]),
        "probe_id": str(row["probe_id"]),
        "hpo_profile_id": str(row["hpo_profile_id"]),
        "hpo_profile_params": json.loads(str(row["hpo_profile_params_json"])),
        "mean_macro_f1": _json_number(row["mean_macro_f1"]),
        "mean_delta_macro_f1_vs_stratified_dummy_train_prior": _json_number(
            row["mean_delta_macro_f1_vs_stratified_dummy_train_prior"]
        ),
        "lcb_delta_macro_f1_vs_stratified_dummy_train_prior": _json_number(
            row["lcb_delta_macro_f1_vs_stratified_dummy_train_prior"]
        ),
        "mean_delta_macro_f1_vs_majority_train_prior": _json_number(
            row["mean_delta_macro_f1_vs_majority_train_prior"]
        ),
        "min_positive_ticker_count": _json_number(row["min_positive_ticker_count"]),
        "selection_ranking_scope": "within_candidate_input_then_candidate_winners",
    }


def _selection_bundle(
    *,
    ready_for_stage03: bool,
    decision: str,
    block_reason: str,
    primary: Mapping[str, Any] | None,
    fallback: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "ready_for_stage03": bool(ready_for_stage03),
        "decision": decision,
        "block_reason": block_reason,
        "primary_candidate": dict(primary) if primary is not None else None,
        "fallback_candidate": dict(fallback) if fallback is not None else None,
    }


def _mark_selected_trials(trial_ledger: pd.DataFrame, decision_bundle: Mapping[str, Any]) -> pd.DataFrame:
    current = trial_ledger.copy()
    current["selected_for_stage03"] = False
    for selection in [decision_bundle.get("primary_candidate"), decision_bundle.get("fallback_candidate")]:
        if selection:
            mask = _selection_mask(current, selection)
            current.loc[mask, "selected_for_stage03"] = True
    return current


def _mark_selected_summary(hpo_summary: pd.DataFrame, decision_bundle: Mapping[str, Any]) -> pd.DataFrame:
    current = hpo_summary.copy()
    current["selected_role"] = ""
    current["selection_reason"] = ""
    for role, selection in [
        ("primary", decision_bundle.get("primary_candidate")),
        ("fallback", decision_bundle.get("fallback_candidate")),
    ]:
        if selection:
            mask = _selection_mask(current, selection)
            current.loc[mask, "selected_role"] = role
            current.loc[mask, "selection_reason"] = "selected_train_inner_hpo"
    return current


def _selection_mask(frame: pd.DataFrame, selection: Mapping[str, Any]) -> pd.Series:
    return (
        frame["candidate_id"].eq(selection["candidate_id"])
        & frame["model_family"].eq(selection["model_family"])
        & frame["hpo_profile_id"].eq(selection["hpo_profile_id"])
    )


def _summary_row(
    *,
    status: str,
    candidate_count: int,
    model_family_count: int,
    planned_hpo_rows: int,
    completed_hpo_rows: int,
    failed_hpo_rows: int,
    selected_family_count: int,
    ready_for_stage03: bool,
    primary: Mapping[str, Any] | None,
    fallback: Mapping[str, Any] | None,
    decision: str,
    block_reason: str,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "status": status,
                "candidate_count": candidate_count,
                "model_family_count": model_family_count,
                "planned_hpo_rows": planned_hpo_rows,
                "completed_hpo_rows": completed_hpo_rows,
                "failed_hpo_rows": failed_hpo_rows,
                "selected_family_count": selected_family_count,
                "ready_for_stage03": ready_for_stage03,
                "primary_candidate_id": primary.get("candidate_id") if primary else "",
                "primary_model_family": primary.get("model_family") if primary else "",
                "primary_hpo_profile_id": primary.get("hpo_profile_id") if primary else "",
                "fallback_candidate_id": fallback.get("candidate_id") if fallback else "",
                "fallback_model_family": fallback.get("model_family") if fallback else "",
                "fallback_hpo_profile_id": fallback.get("hpo_profile_id") if fallback else "",
                "decision": decision,
                "block_reason": block_reason,
            }
        ],
        columns=SUMMARY_COLUMNS,
    )


def _status_from_selection(decision_bundle: Mapping[str, Any], failed_rows: int) -> str:
    if failed_rows:
        return "formal_hpo_incomplete_failed_trials"
    if decision_bundle.get("ready_for_stage03") is True:
        return "formal_hpo_complete_ready_for_stage03"
    return "formal_hpo_complete_not_ready_for_stage03"


def _selected_family_count(decision_bundle: Mapping[str, Any]) -> int:
    families = {
        str(selection["model_family"])
        for selection in [
            decision_bundle.get("primary_candidate"),
            decision_bundle.get("fallback_candidate"),
        ]
        if selection
    }
    return len(families)


def _frozen_candidate_payload(
    *,
    config: Mapping[str, Any],
    stage01_handoff: Mapping[str, Any],
    decision_bundle: Mapping[str, Any],
    hpo_summary: pd.DataFrame,
    device_provenance: Mapping[str, Any],
) -> dict[str, Any]:
    outputs = require_mapping(config["outputs"], "outputs")
    train_inner = require_mapping(config["train_inner"], "train_inner")
    selection_rules = require_mapping(config["selection_rules"], "selection_rules")
    return {
        "route": config["route"],
        "stage_name": config["stage_name"],
        "source_stage00_run_id": config["inputs"].get(
            "stage00_run_id", stage01_handoff.get("source_stage00_run_id")
        ),
        "source_stage01_run_id": config["inputs"]["stage01_run_id"],
        "superseded_stage02_run_ids": _superseded_stage02_run_ids(config),
        "source_stage01_decision": stage01_handoff.get("decision"),
        "stage02_modeling_scope_axis": _stage02_modeling_scope_axis(stage01_handoff),
        "ready_for_stage03": bool(decision_bundle["ready_for_stage03"]),
        "decision": decision_bundle["decision"],
        "block_reason": decision_bundle["block_reason"],
        "selection_metric": config["selection_rules"]["primary_metric"],
        "selection_baseline": config["selection_rules"]["baseline"],
        "selection_rules": {
            "minimum_positive_ticker_count": int(
                selection_rules.get("minimum_positive_ticker_count", 0)
            ),
            "max_selected_configs_per_family": int(
                selection_rules.get("max_selected_configs_per_family", 0)
            ),
            "candidate_ranking_scope": "within_candidate_input_then_candidate_winners",
            "same_row_baseline_required": True,
        },
        "primary_candidate": decision_bundle.get("primary_candidate"),
        "fallback_candidate": decision_bundle.get("fallback_candidate"),
        "hpo_summary_rows": int(len(hpo_summary)),
        "fold_design": {
            "n_folds": int(train_inner["n_folds"]),
            "event_overlap_count_required": int(
                train_inner.get("event_overlap_count_required", 0)
            ),
            "official_validation_for_selection": False,
            "fold_source": "rebuilt_from_stage00_train_partition",
            "fold_type": "chronological_train_inner",
        },
        "row_contract": {
            "same_row_baselines": True,
            "candidate_vs_candidate_comparison": "within_candidate_input_then_candidate_winners",
            "sample_id_hash_fields": [
                "train_sample_id_hash",
                "eval_sample_id_hash",
                "sample_id_hash",
            ],
        },
        "preprocessing_contract": {
            "feature_source": "stage01_shortlisted_features_rebuilt_from_stage00_train_partition",
            "fit_scope": "inner_train_rows_only",
            "scored_rows": "inner_eval_rows_only",
            "lightgbm_early_stopping_source": "inner_train_chronological_tail_when_available",
            "torch_early_stopping_source": "inner_train_chronological_tail_when_available",
        },
        "seed_policy": {
            "train_inner_seeds": [int(seed) for seed in train_inner["seeds"]],
        },
        "device_provenance": dict(device_provenance),
        "artifact_references": {
            "hpo_trial_ledger": outputs.get("hpo_trial_ledger", "02_hpo_trial_ledger.csv"),
            "hpo_summary": outputs.get("hpo_summary", "02_hpo_summary.csv"),
            "baseline_control_summary": outputs.get(
                "baseline_control_summary", "02_baseline_control_summary.csv"
            ),
            "stage03_handoff": outputs.get("stage03_handoff", "02_stage03_handoff.json"),
        },
        "holdout_test_contact": False,
        "official_validation_for_selection": False,
        "no_final_model_selected": True,
    }


def _best_params_payload(
    *,
    config: Mapping[str, Any],
    stage01_handoff: Mapping[str, Any],
    profiles_by_family: Mapping[str, list[Mapping[str, Any]]],
    hpo_summary: pd.DataFrame,
    decision_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    best_by_family = {}
    if not hpo_summary.empty:
        completed = hpo_summary.loc[hpo_summary["completed_rows"] == hpo_summary["expected_rows"]]
        for family, group in completed.groupby("model_family", sort=True):
            ranked = group.sort_values(
                [
                    "lcb_delta_macro_f1_vs_stratified_dummy_train_prior",
                    "mean_delta_macro_f1_vs_stratified_dummy_train_prior",
                    "mean_macro_f1",
                ],
                ascending=[False, False, False],
            )
            if not ranked.empty:
                best_by_family[str(family)] = _selection_record(ranked.iloc[0].to_dict())
    return {
        "route": config["route"],
        "stage_name": config["stage_name"],
        "source_stage01_run_id": config["inputs"]["stage01_run_id"],
        "superseded_stage02_run_ids": _superseded_stage02_run_ids(config),
        "source_stage01_decision": stage01_handoff.get("decision"),
        "stage02_modeling_scope_axis": _stage02_modeling_scope_axis(stage01_handoff),
        "approved_model_families_for_stage02": list(profiles_by_family),
        "decision": decision_bundle["decision"],
        "best_params_by_family": best_by_family,
        "primary_candidate": decision_bundle.get("primary_candidate"),
        "fallback_candidate": decision_bundle.get("fallback_candidate"),
        "holdout_test_contact": False,
    }


def _stage03_handoff_payload(
    config: Mapping[str, Any],
    stage01_handoff: Mapping[str, Any],
    decision_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "route": config["route"],
        "stage_name": config["stage_name"],
        "source_stage00_run_id": config["inputs"].get(
            "stage00_run_id", stage01_handoff.get("source_stage00_run_id")
        ),
        "source_stage01_run_id": config["inputs"]["stage01_run_id"],
        "superseded_stage02_run_ids": _superseded_stage02_run_ids(config),
        "source_stage01_decision": stage01_handoff.get("decision"),
        "stage02_modeling_scope_axis": _stage02_modeling_scope_axis(stage01_handoff),
        "ready_for_stage03": bool(decision_bundle["ready_for_stage03"]),
        "decision": decision_bundle["decision"],
        "block_reason": decision_bundle["block_reason"],
        "primary_candidate": decision_bundle.get("primary_candidate"),
        "fallback_candidate": decision_bundle.get("fallback_candidate"),
        "frozen_candidate_artifact": "02_frozen_candidate.json",
        "hpo_trial_ledger": "02_hpo_trial_ledger.csv",
        "hpo_summary": "02_hpo_summary.csv",
        "baseline_control_summary": "02_baseline_control_summary.csv",
        "official_validation_for_selection": False,
        "no_final_model_selected": True,
        "holdout_test_contact": False,
    }


def _write_frozen_param_yamls(
    output_dir: Path, outputs: Mapping[str, Any], frozen_candidate: Mapping[str, Any]
) -> list[Path]:
    if frozen_candidate.get("ready_for_stage03") is not True:
        return []
    frozen_dir = output_dir / _output_name(outputs, "frozen_params_dir", "frozen_params")
    frozen_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for role in ("primary_candidate", "fallback_candidate"):
        selection = frozen_candidate.get(role)
        if not selection:
            continue
        name = _safe_filename(
            f"{role}_{selection['candidate_id']}_{selection['model_family']}_{selection['hpo_profile_id']}.yaml"
        )
        path = frozen_dir / name
        payload = {
            "role": role.replace("_candidate", ""),
            "source_stage01_run_id": frozen_candidate["source_stage01_run_id"],
            "candidate": selection,
            "holdout_test_contact": False,
            "official_validation_for_selection": False,
            "no_final_model_selected": True,
        }
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        paths.append(path)
    return paths


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def _frozen_candidate_markdown(payload: Mapping[str, Any]) -> str:
    lines = [
        "# Stage 02 Frozen Candidate",
        "",
        f"- decision: `{payload['decision']}`",
        f"- ready_for_stage03: `{payload['ready_for_stage03']}`",
        f"- source_stage01_run_id: `{payload['source_stage01_run_id']}`",
        f"- holdout_test_contact: `{payload['holdout_test_contact']}`",
        f"- no_final_model_selected: `{payload['no_final_model_selected']}`",
        "",
    ]
    for label, key in [("Primary", "primary_candidate"), ("Fallback", "fallback_candidate")]:
        selection = payload.get(key)
        lines.append(f"## {label}")
        if not selection:
            lines.append("")
            lines.append("No candidate frozen.")
            lines.append("")
            continue
        lines.extend(
            [
                "",
                f"- candidate_id: `{selection['candidate_id']}`",
                f"- model_family: `{selection['model_family']}`",
                f"- hpo_profile_id: `{selection['hpo_profile_id']}`",
                f"- feature_set: `{selection['feature_set']}`",
                f"- window_size: `{selection['window_size']}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _mean_or_nan(values: pd.Series) -> float:
    current = pd.to_numeric(values, errors="coerce").dropna()
    return float(current.mean()) if len(current) else np.nan


def _min_or_nan(values: pd.Series) -> float:
    current = pd.to_numeric(values, errors="coerce").dropna()
    return float(current.min()) if len(current) else np.nan


def _json_number(value: Any) -> float | None:
    if pd.isna(value):
        return None
    return float(value)
