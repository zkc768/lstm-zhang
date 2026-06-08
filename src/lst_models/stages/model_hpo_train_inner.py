from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from lst_models.artifacts import require_artifacts, write_artifact_inventory, write_json
from lst_models.config import hash_file, hash_mapping, load_yaml


SUMMARY_COLUMNS = [
    "status",
    "candidate_count",
    "model_family_count",
    "planned_hpo_rows",
    "completed_hpo_rows",
    "selected_family_count",
    "decision",
    "block_reason",
]

HPO_LEDGER_COLUMNS = [
    "candidate_id",
    "feature_set",
    "window_size",
    "model_family",
    "hpo_profile_id",
    "fold_id",
    "seed",
    "fit_status",
    "macro_f1",
    "balanced_accuracy",
    "baseline_macro_f1",
    "delta_macro_f1_vs_baseline",
    "selected_for_stage03",
    "error_message",
]


@dataclass(frozen=True)
class Stage02Result:
    output_dir: Path
    run_manifest: Path
    artifact_inventory: Path
    summary: Path
    hpo_plan_ledger: Path
    best_params_by_family: Path
    stage03_handoff: Path


def run_stage(config: Mapping[str, Any]) -> Stage02Result:
    _validate_config(config)

    inputs = _as_mapping(config["inputs"], "inputs")
    outputs = _as_mapping(config["outputs"], "outputs")
    stage01_run_dir = Path(str(inputs["stage01_runtime_run_dir"]))
    stage01_paths = require_artifacts(stage01_run_dir, inputs["required_stage01_artifacts"])

    stage01_manifest = _load_json(stage01_paths["run_manifest.json"])
    stage01_handoff = _load_json(stage01_paths["01_candidate_inputs.json"])
    _validate_stage01_contract(stage01_manifest, stage01_handoff)

    candidates = _candidate_inputs(stage01_handoff)
    approved_families = _approved_families(stage01_handoff, config)
    blocked_reason = _stage01_block_reason(stage01_handoff, candidates, approved_families)

    if blocked_reason:
        ledger = pd.DataFrame(columns=HPO_LEDGER_COLUMNS)
        summary = _summary_row(
            status="blocked",
            candidate_count=len(candidates),
            model_family_count=len(approved_families),
            planned_hpo_rows=0,
            completed_hpo_rows=0,
            selected_family_count=0,
            decision="do_not_start_stage03_stage02_blocked_by_stage01",
            block_reason=blocked_reason,
        )
        best_params = _blocked_best_params(config, stage01_handoff, blocked_reason)
        stage03_handoff = _blocked_stage03_handoff(config, stage01_handoff, blocked_reason)
        execution_mode = "blocked_by_stage01_no_candidate_inputs"
    else:
        profiles_by_family = _load_search_profiles(approved_families, config)
        ledger = _build_hpo_plan_ledger(candidates, profiles_by_family, config)
        _enforce_budget(len(ledger), config)
        summary = _summary_row(
            status="planned_not_executed",
            candidate_count=len(candidates),
            model_family_count=len(approved_families),
            planned_hpo_rows=len(ledger),
            completed_hpo_rows=0,
            selected_family_count=0,
            decision="do_not_start_stage03_hpo_fits_not_implemented",
            block_reason="hpo_fitters_not_implemented",
        )
        best_params = _planned_best_params(config, stage01_handoff, approved_families)
        stage03_handoff = _planned_stage03_handoff(config, stage01_handoff)
        execution_mode = "hpo_plan_scaffold_no_training"

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(str(outputs["output_dir"])) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / str(outputs["summary"])
    ledger_path = output_dir / str(outputs["hpo_plan_ledger"])
    best_params_path = write_json(output_dir / str(outputs["best_params_by_family"]), best_params)
    handoff_path = write_json(output_dir / str(outputs["stage03_handoff"]), stage03_handoff)
    summary.to_csv(summary_path, index=False)
    ledger.to_csv(ledger_path, index=False)

    notebook_path = _resolve_repo_path(inputs["notebook_path"])
    manifest_payload = {
        "route": config["route"],
        "stage_name": config["stage_name"],
        "scope": config["scope"],
        "config_sha256": hash_mapping(config),
        "notebook_sha256": hash_file(notebook_path),
        "source_stage01_run_id": inputs["stage01_run_id"],
        "input_artifacts": [str(path) for path in stage01_paths.values()],
        "output_artifacts": [
            str(outputs["summary"]),
            str(outputs["hpo_plan_ledger"]),
            str(outputs["best_params_by_family"]),
            str(outputs["stage03_handoff"]),
        ],
        "stage02_execution_mode": execution_mode,
        "official_validation_for_selection": False,
        "no_final_model_selected": True,
        "holdout_test_contact": False,
    }
    manifest_path = write_json(output_dir / str(outputs["manifest"]), manifest_payload)
    inventory_path = write_artifact_inventory(
        output_dir,
        {
            "run_manifest": manifest_path,
            "summary": summary_path,
            "hpo_plan_ledger": ledger_path,
            "best_params_by_family": best_params_path,
            "stage03_handoff": handoff_path,
        },
    )

    return Stage02Result(
        output_dir=output_dir,
        run_manifest=manifest_path,
        artifact_inventory=inventory_path,
        summary=summary_path,
        hpo_plan_ledger=ledger_path,
        best_params_by_family=best_params_path,
        stage03_handoff=handoff_path,
    )


def _validate_config(config: Mapping[str, Any]) -> None:
    if config.get("stage_name") != "02_model_hpo_train_inner":
        raise ValueError(f"expected Stage 02 config, got {config.get('stage_name')!r}")
    if config.get("scope") != "validation_only":
        raise ValueError(f"expected validation_only scope, got {config.get('scope')!r}")
    if config.get("holdout_test_contact") is not False:
        raise ValueError("Stage 02 requires holdout_test_contact=false")

    train_inner = _as_mapping(config["train_inner"], "train_inner")
    if train_inner.get("official_validation_for_selection") is not False:
        raise ValueError("Stage 02 HPO must use train-inner folds only")
    if int(train_inner["n_folds"]) < 1:
        raise ValueError("train_inner.n_folds must be at least 1")

    selection_rules = _as_mapping(config["selection_rules"], "selection_rules")
    if selection_rules.get("no_official_validation_selection") is not True:
        raise ValueError("Stage 02 must declare no_official_validation_selection=true")
    if selection_rules.get("no_final_model_selected") is not True:
        raise ValueError("Stage 02 must declare no_final_model_selected=true")


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


def _validate_stage01_contract(
    stage01_manifest: Mapping[str, Any], stage01_handoff: Mapping[str, Any]
) -> None:
    if stage01_manifest.get("holdout_test_contact") is not False:
        raise ValueError("Stage 02 requires Stage 01 run_manifest holdout_test_contact=false")
    if stage01_handoff.get("holdout_test_contact") is not False:
        raise ValueError("Stage 02 requires Stage 01 candidate handoff holdout_test_contact=false")
    if stage01_handoff.get("no_final_model_selected") is not True:
        raise ValueError("Stage 02 requires Stage 01 handoff no_final_model_selected=true")


def _candidate_inputs(stage01_handoff: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates = stage01_handoff.get("candidate_inputs", [])
    if not isinstance(candidates, list):
        raise TypeError("01_candidate_inputs.json field candidate_inputs must be a list")
    for candidate in candidates:
        _as_mapping(candidate, "candidate_input")
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
    families = _as_mapping(config["hpo_families"], "hpo_families")
    active = []
    for family, family_config in families.items():
        if _as_mapping(family_config, f"hpo_families.{family}").get("enabled") is True:
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


def _load_search_profiles(
    approved_families: tuple[str, ...],
    config: Mapping[str, Any],
) -> dict[str, list[Mapping[str, Any]]]:
    family_configs = _as_mapping(config["hpo_families"], "hpo_families")
    max_profiles = int(_as_mapping(config["budget"], "budget")["max_profiles_per_family"])
    profiles_by_family: dict[str, list[Mapping[str, Any]]] = {}
    for family in approved_families:
        family_config = _as_mapping(family_configs[family], f"hpo_families.{family}")
        search_space_path = _resolve_repo_path(family_config["search_space"])
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
        profiles_by_family[family] = [_as_mapping(profile, "profile") for profile in profiles]
    return profiles_by_family


def _build_hpo_plan_ledger(
    candidates: list[Mapping[str, Any]],
    profiles_by_family: Mapping[str, list[Mapping[str, Any]]],
    config: Mapping[str, Any],
) -> pd.DataFrame:
    train_inner = _as_mapping(config["train_inner"], "train_inner")
    n_folds = int(train_inner["n_folds"])
    seeds = tuple(int(seed) for seed in train_inner["seeds"])
    rows = []
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        feature_set = str(candidate["feature_set"])
        window_size = int(candidate["window_size"])
        for family, profiles in profiles_by_family.items():
            for profile in profiles:
                profile_id = str(profile["profile_id"])
                for fold_index in range(n_folds):
                    for seed in seeds:
                        rows.append(
                            {
                                "candidate_id": candidate_id,
                                "feature_set": feature_set,
                                "window_size": window_size,
                                "model_family": family,
                                "hpo_profile_id": profile_id,
                                "fold_id": f"fold_{fold_index}",
                                "seed": seed,
                                "fit_status": "skipped_not_implemented",
                                "macro_f1": pd.NA,
                                "balanced_accuracy": pd.NA,
                                "baseline_macro_f1": pd.NA,
                                "delta_macro_f1_vs_baseline": pd.NA,
                                "selected_for_stage03": False,
                                "error_message": (
                                    "Stage 02 HPO trainer is not implemented in this "
                                    "package-backed scaffold"
                                ),
                            }
                        )
    return pd.DataFrame(rows, columns=HPO_LEDGER_COLUMNS)


def _enforce_budget(planned_rows: int, config: Mapping[str, Any]) -> None:
    cap = int(_as_mapping(config["budget"], "budget")["max_hpo_plan_rows"])
    if planned_rows > cap:
        raise ValueError(f"Stage 02 planned HPO rows {planned_rows} exceed budget cap {cap}")


def _summary_row(
    *,
    status: str,
    candidate_count: int,
    model_family_count: int,
    planned_hpo_rows: int,
    completed_hpo_rows: int,
    selected_family_count: int,
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
                "selected_family_count": selected_family_count,
                "decision": decision,
                "block_reason": block_reason,
            }
        ],
        columns=SUMMARY_COLUMNS,
    )


def _blocked_best_params(
    config: Mapping[str, Any], stage01_handoff: Mapping[str, Any], reason: str
) -> dict[str, Any]:
    return {
        "route": config["route"],
        "stage_name": config["stage_name"],
        "source_stage01_run_id": config["inputs"]["stage01_run_id"],
        "source_stage01_decision": stage01_handoff.get("decision"),
        "decision": "no_frozen_params",
        "frozen_params": {},
        "block_reason": reason,
        "holdout_test_contact": False,
    }


def _planned_best_params(
    config: Mapping[str, Any],
    stage01_handoff: Mapping[str, Any],
    approved_families: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "route": config["route"],
        "stage_name": config["stage_name"],
        "source_stage01_run_id": config["inputs"]["stage01_run_id"],
        "source_stage01_decision": stage01_handoff.get("decision"),
        "approved_model_families_for_stage02": list(approved_families),
        "decision": "no_frozen_params_hpo_fits_not_implemented",
        "frozen_params": {},
        "holdout_test_contact": False,
    }


def _blocked_stage03_handoff(
    config: Mapping[str, Any], stage01_handoff: Mapping[str, Any], reason: str
) -> dict[str, Any]:
    return {
        "route": config["route"],
        "stage_name": config["stage_name"],
        "source_stage01_run_id": config["inputs"]["stage01_run_id"],
        "source_stage01_decision": stage01_handoff.get("decision"),
        "ready_for_stage03": False,
        "decision": "do_not_start_stage03_stage02_blocked_by_stage01",
        "block_reason": reason,
        "holdout_test_contact": False,
    }


def _planned_stage03_handoff(
    config: Mapping[str, Any], stage01_handoff: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "route": config["route"],
        "stage_name": config["stage_name"],
        "source_stage01_run_id": config["inputs"]["stage01_run_id"],
        "source_stage01_decision": stage01_handoff.get("decision"),
        "ready_for_stage03": False,
        "decision": "do_not_start_stage03_hpo_fits_not_implemented",
        "block_reason": "hpo_fitters_not_implemented",
        "holdout_test_contact": False,
    }
