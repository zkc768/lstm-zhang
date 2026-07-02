"""V2 synthetic positive control: run_stage orchestration (train-domain only).

Reuses the REAL pipeline mechanism end to end (Stage 00 frozen artifacts ->
train bars -> features -> events -> folds -> windows -> capped fold rows ->
registry baselines -> the shared tcn_tiny fit wrapper) and swaps in exactly
one thing: the labels of eligible train rows, relabeled by
``lst_models.synthetic_control.inject_planted_labels`` at preregistered
strengths. Everything written here is synthetic-label protocol-validation
evidence, never market evidence (``spc_`` prefix, ``synthetic_labels=true``).
Preregistration: docs/protocols/v2_positive_control_preregistration_20260701.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from lst_models.artifacts import (
    feature_rebuild_gate_fields,
    git_commit_fields,
    read_json_object,
    require_artifacts,
    require_run_id_chain,
    require_safety_flags,
    write_artifact_inventory,
    write_incremental_checkpoint,
    write_json,
)
from lst_models.config import hash_file, hash_mapping, load_yaml, require_mapping, resolve_repo_path
from lst_models.data import (
    load_sample_event_index,
    load_train_bars,
    raw_manifest_integrity_summary,
)
from lst_models.device import aggregate_trial_device_fields
from lst_models.features import build_feature_frame, require_feature_columns
from lst_models.fitting import fit_stage_control
from lst_models.splits import build_train_inner_folds, train_valid_events
from lst_models.synthetic_control import (
    ARM_SUMMARY_COLUMNS, BASELINE_CONTROL_COLUMNS, CLOSED_HOLDOUT_TEST_START,
    PLANTED_RULE_FEATURE, PLANTED_RULE_ID, SENTINEL_LEDGER_COLUMNS,
    TRAIN_END_EXCLUSIVE, TRIAL_LEDGER_COLUMNS,
    arm_delta_aggregates, arm_tag, assert_train_domain_only,
    evaluate_predeclared_criteria, flags_signal_fields, inject_planted_labels,
    planted_rule_values, real_control_null_band, require_frozen_train_boundaries,
    score_arm_trials,
)
from lst_models.windows import build_window_dataset, sample_id_hash


STAGE_NAME = "v2_synthetic_positive_control"
RUN_ID_PATTERN = re.compile(r"^\d{8}_\d{6}_\d{6}$")
REQUIRED_SPC_ARTIFACTS = [
    "run_manifest.json", "artifact_inventory.csv",
    "spc_trial_ledger.csv", "spc_arm_summary.csv",
    "spc_baseline_control_summary.csv", "spc_sentinel_ledger.csv",
    "spc_injection_manifest.json", "spc_criteria_readout.json",
]


@dataclass(frozen=True)
class SyntheticPositiveControlResult:
    output_dir: Path
    run_manifest: Path
    artifact_inventory: Path
    trial_ledger: Path
    arm_summary: Path
    baseline_control_summary: Path
    sentinel_ledger: Path
    injection_manifest: Path
    criteria_readout: Path


@dataclass(frozen=True)
class SpcDataContext:
    stage00_paths: Mapping[str, Path]
    stage01_paths: Mapping[str, Path]
    stage02_paths: Mapping[str, Path]
    stage01_manifest: Mapping[str, Any]
    raw_manifest: Mapping[str, Any]
    split_freeze: Mapping[str, Any]
    candidate: Mapping[str, Any]
    train_events: pd.DataFrame
    feature_frame: pd.DataFrame
    folds: pd.DataFrame


def run_stage(config: Mapping[str, Any]) -> SyntheticPositiveControlResult:
    _validate_config(config)
    outputs = require_mapping(config["outputs"], "outputs")
    context = _load_data_context(config)
    profile = _resolve_profile(config)
    null_band = _null_band_from_real_stage02(config, context)
    arms = _arm_specs(config)
    _enforce_budget(config, arms, context.folds)

    run_id = _resolve_run_id(outputs.get("run_id"))
    output_dir = Path(str(outputs["output_dir"])) / run_id
    output_dir.mkdir(parents=True, exist_ok=False)

    trial_ledger, baseline_summary, sentinel_ledger, injection_records = _run_all_arms(
        config, context, profile, arms, run_id=run_id
    )
    ticker_floor = int(
        require_mapping(config["criteria"], "criteria")["minimum_positive_ticker_count"]
    )
    arm_summary = _build_arm_summary(
        trial_ledger, sentinel_ledger, injection_records,
        minimum_positive_ticker_count=ticker_floor,
    )
    criteria = _evaluate_criteria(config, trial_ledger, injection_records, null_band)

    paths = _write_result_tables(
        output_dir, outputs, trial_ledger, arm_summary, baseline_summary, sentinel_ledger
    )
    injection_manifest_path = write_json(
        output_dir / _output_name(outputs, "injection_manifest", "spc_injection_manifest.json"),
        _injection_manifest_payload(config, injection_records),
    )
    criteria_path = write_json(
        output_dir / _output_name(outputs, "criteria_readout", "spc_criteria_readout.json"),
        {**criteria, "null_band_source": null_band},
    )
    manifest_path = _write_run_manifest(
        config, context, profile, trial_ledger, null_band, output_dir, run_id,
        output_paths={**paths, "injection_manifest": injection_manifest_path,
                      "criteria_readout": criteria_path},
    )
    inventory_path = write_artifact_inventory(
        output_dir,
        {"run_manifest": manifest_path, "injection_manifest": injection_manifest_path,
         "criteria_readout": criteria_path, **paths},
    )
    return SyntheticPositiveControlResult(
        output_dir=output_dir,
        run_manifest=manifest_path,
        artifact_inventory=inventory_path,
        trial_ledger=paths["trial_ledger"],
        arm_summary=paths["arm_summary"],
        baseline_control_summary=paths["baseline_control_summary"],
        sentinel_ledger=paths["sentinel_ledger"],
        injection_manifest=injection_manifest_path,
        criteria_readout=criteria_path,
    )


def _validate_config(config: Mapping[str, Any]) -> None:
    if config.get("stage_name") != STAGE_NAME:
        raise ValueError(f"expected {STAGE_NAME} config, got {config.get('stage_name')!r}")
    if config.get("scope") != "validation_only":
        raise ValueError(f"expected validation_only scope, got {config.get('scope')!r}")
    if config.get("holdout_test_contact") is not False:
        raise ValueError(f"{STAGE_NAME} requires holdout_test_contact=false")
    if config.get("synthetic_labels") is not True:
        raise ValueError(f"{STAGE_NAME} requires synthetic_labels=true")
    if config.get("train_domain_only") is not True:
        raise ValueError(f"{STAGE_NAME} requires train_domain_only=true")

    inputs = require_mapping(config["inputs"], "inputs")
    for key in ("stage00_run_id", "stage01_run_id", "stage02_real_run_id"):
        if not inputs.get(key):
            raise ValueError(f"{STAGE_NAME} config requires inputs.{key}")

    injection = require_mapping(config["injection"], "injection")
    if str(injection.get("rule_id")) != PLANTED_RULE_ID:
        raise ValueError(
            f"injection.rule_id must be {PLANTED_RULE_ID!r}, got {injection.get('rule_id')!r}"
        )
    if str(injection.get("rule_feature")) != PLANTED_RULE_FEATURE:
        raise ValueError(
            f"injection.rule_feature must be {PLANTED_RULE_FEATURE!r}, "
            f"got {injection.get('rule_feature')!r}"
        )
    arms = injection.get("arms")
    if not isinstance(arms, list) or len(arms) < 2:
        raise ValueError("injection.arms must list at least the null arm and one planted arm")
    strengths = [float(require_mapping(arm, "injection.arm")["strength"]) for arm in arms]
    if sorted(strengths) != strengths or len(set(strengths)) != len(strengths):
        raise ValueError(f"injection arm strengths must be strictly increasing, got {strengths}")
    if strengths[0] != 0.0:
        raise ValueError("injection.arms must include the mandatory null arm strength 0.0 first")
    for arm in arms:
        expected_tag = arm_tag(float(arm["strength"]))
        if str(arm.get("arm_id")) != expected_tag:
            raise ValueError(
                f"arm_id {arm.get('arm_id')!r} must equal canonical tag {expected_tag!r}"
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
            f"{STAGE_NAME} is scoped to the tcn_tiny primary profile only, got "
            f"family={model.get('family')!r} probe_id={model.get('probe_id')!r}"
        )
    criteria = require_mapping(config["criteria"], "criteria")
    declared = set(strengths)
    for key in ("null_strength", "threshold_strength"):
        if float(criteria[key]) not in declared:
            raise ValueError(f"criteria.{key} must reference a declared arm strength")
    for key in ("detection_strengths", "monotone_strengths"):
        for value in criteria[key]:
            if float(value) not in declared:
                raise ValueError(f"criteria.{key} entry {value} is not a declared arm strength")
    if float(criteria["null_strength"]) != 0.0:
        raise ValueError("criteria.null_strength must be 0.0")


def _output_name(outputs: Mapping[str, Any], key: str, default: str) -> str:
    return str(outputs.get(key, default))


def _resolve_run_id(configured_run_id: Any | None = None) -> str:
    if configured_run_id in (None, ""):
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    run_id = str(configured_run_id)
    if RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise ValueError(
            f"{STAGE_NAME} outputs.run_id must match YYYYMMDD_HHMMSS_microseconds, got {run_id!r}"
        )
    return run_id


def _load_data_context(config: Mapping[str, Any]) -> SpcDataContext:
    inputs = require_mapping(config["inputs"], "inputs")
    stage00_paths = require_artifacts(
        Path(str(inputs["stage00_runtime_run_dir"])), inputs["required_stage00_artifacts"]
    )
    stage01_paths = require_artifacts(
        Path(str(inputs["stage01_runtime_run_dir"])), inputs["required_stage01_artifacts"]
    )
    stage02_paths = require_artifacts(
        Path(str(inputs["stage02_real_runtime_run_dir"])), inputs["required_stage02_artifacts"]
    )
    stage00_manifest = read_json_object(stage00_paths["run_manifest.json"])
    stage01_manifest = read_json_object(stage01_paths["run_manifest.json"])
    stage01_handoff = read_json_object(stage01_paths["01_candidate_inputs.json"])
    stage02_manifest = read_json_object(stage02_paths["run_manifest.json"])
    require_safety_flags(
        [
            ("Stage 00 run_manifest", stage00_manifest),
            ("Stage 01 run_manifest", stage01_manifest),
            ("Stage 01 candidate handoff", stage01_handoff),
            ("real Stage 02 run_manifest", stage02_manifest),
        ],
        stage_label=STAGE_NAME,
        field="holdout_test_contact",
        expected=False,
    )
    require_run_id_chain(
        [
            ("real Stage 02 run id", str(inputs["stage02_real_run_id"]),
             stage02_manifest.get("stage02_run_id", stage02_manifest.get("run_id"))),
            ("Stage 01 run id of real Stage 02", str(inputs["stage01_run_id"]),
             stage02_manifest.get("source_stage01_run_id")),
        ],
        stage_label=STAGE_NAME,
    )

    raw_manifest = read_json_object(stage00_paths["raw_data_manifest.json"])
    split_freeze = read_json_object(stage00_paths["split_freeze.json"])
    require_frozen_train_boundaries(split_freeze)

    candidate = _resolve_candidate(config, stage01_handoff)
    sample_events = load_sample_event_index(stage00_paths["sample_event_index.csv"])
    train_events = train_valid_events(sample_events)
    assert_train_domain_only(
        train_events, ["target_timestamp", "horizon_end_timestamp"],
        stage_label=f"{STAGE_NAME} eligible train events",
    )
    train_bars = load_train_bars(raw_manifest, split_freeze, inputs)
    assert_train_domain_only(train_bars, ["timestamp"], stage_label=f"{STAGE_NAME} train bars")
    feature_frame = build_feature_frame(train_bars)
    assert_train_domain_only(
        feature_frame, ["timestamp"], stage_label=f"{STAGE_NAME} feature frame"
    )
    require_feature_columns(
        tuple(str(column) for column in candidate["feature_columns"]), feature_frame
    )
    folds = build_train_inner_folds(train_events, int(config["train_inner"]["n_folds"]))
    expected_overlap = int(config["train_inner"].get("event_overlap_count_required", 0))
    if not folds["event_overlap_count"].eq(expected_overlap).all():
        raise ValueError(f"{STAGE_NAME} train-inner fold overlap check failed")
    max_eval_end = pd.to_datetime(folds["eval_end_exclusive"]).max()
    if max_eval_end >= TRAIN_END_EXCLUSIVE + pd.Timedelta(days=1):
        raise ValueError(
            f"{STAGE_NAME} blocked: fold eval_end_exclusive {max_eval_end.isoformat()} "
            f"reaches past train_end_exclusive {TRAIN_END_EXCLUSIVE.date().isoformat()}"
        )
    return SpcDataContext(
        stage00_paths=stage00_paths,
        stage01_paths=stage01_paths,
        stage02_paths=stage02_paths,
        stage01_manifest=stage01_manifest,
        raw_manifest=raw_manifest,
        split_freeze=split_freeze,
        candidate=candidate,
        train_events=train_events,
        feature_frame=feature_frame,
        folds=folds,
    )


def _resolve_candidate(
    config: Mapping[str, Any], stage01_handoff: Mapping[str, Any]
) -> Mapping[str, Any]:
    configured_id = str(require_mapping(config["candidate"], "candidate")["candidate_id"])
    candidates = stage01_handoff.get("candidate_inputs", [])
    matches = [
        candidate
        for candidate in candidates
        if str(require_mapping(candidate, "candidate_input").get("candidate_id")) == configured_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"{STAGE_NAME} requires exactly one Stage 01 candidate input named "
            f"{configured_id!r}; found {len(matches)}"
        )
    candidate = matches[0]
    feature_columns = [str(column) for column in candidate.get("feature_columns", [])]
    if PLANTED_RULE_FEATURE not in feature_columns:
        raise ValueError(
            f"planted rule feature {PLANTED_RULE_FEATURE!r} is not among the candidate "
            f"feature columns {feature_columns}; the plant would not be learnable in-window"
        )
    return candidate


def _resolve_profile(config: Mapping[str, Any]) -> Mapping[str, Any]:
    model = require_mapping(config["model"], "model")
    search_space = load_yaml(resolve_repo_path(model["search_space"]))
    if search_space.get("model_family") != str(model["family"]):
        raise ValueError(
            f"search space model_family mismatch: {search_space.get('model_family')!r} "
            f"!= {model['family']!r}"
        )
    profile_id = str(model["hpo_profile_id"])
    matches = [
        profile
        for profile in search_space.get("profiles", [])
        if str(require_mapping(profile, "profile").get("profile_id")) == profile_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"{STAGE_NAME} requires exactly one profile {profile_id!r} in "
            f"{model['search_space']}; found {len(matches)}"
        )
    return matches[0]


def _null_band_from_real_stage02(
    config: Mapping[str, Any], context: SpcDataContext
) -> dict[str, Any]:
    source = require_mapping(
        require_mapping(config["criteria"], "criteria")["null_band_source"],
        "criteria.null_band_source",
    )
    ledger_path = context.stage02_paths[str(source["artifact"])]
    trial_ledger = pd.read_csv(ledger_path)
    band = real_control_null_band(
        trial_ledger,
        candidate_id=str(source["candidate_id"]),
        model_family=str(source["model_family"]),
        hpo_profile_id=str(source["hpo_profile_id"]),
        expected_rows=int(source["expected_rows"]),
    )
    return {**band, "source_artifact": str(ledger_path)}


def _arm_specs(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    injection = require_mapping(config["injection"], "injection")
    return [{"arm_id": str(arm["arm_id"]), "strength": float(arm["strength"]),
             "role": str(arm.get("role", ""))} for arm in injection["arms"]]


def _enforce_budget(
    config: Mapping[str, Any], arms: list[dict[str, Any]], folds: pd.DataFrame
) -> None:
    seeds = [int(seed) for seed in config["train_inner"]["seeds"]]
    planned = len(arms) * len(folds) * len(seeds)
    cap = int(require_mapping(config["budget"], "budget")["max_planned_fit_rows"])
    if planned > cap:
        raise ValueError(f"{STAGE_NAME} planned fit rows {planned} exceed budget cap {cap}")


def _run_all_arms(
    config: Mapping[str, Any],
    context: SpcDataContext,
    profile: Mapping[str, Any],
    arms: list[dict[str, Any]],
    *,
    run_id: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    injection = require_mapping(config["injection"], "injection")
    injection_seed = int(injection["injection_seed"])
    candidate = context.candidate
    rule_values, rule_nan_count = planted_rule_values(context.feature_frame, context.train_events)

    trial_rows: list[dict[str, Any]] = []
    baseline_rows: list[dict[str, Any]] = []
    sentinel_rows: list[dict[str, Any]] = []
    injection_records: list[dict[str, Any]] = []
    reference_dataset_hash: str | None = None

    for arm_index, arm in enumerate(arms):
        relabeled_events, stats = inject_planted_labels(
            context.train_events, rule_values, rule_nan_count,
            strength=arm["strength"], injection_seed=injection_seed, arm_id=arm["arm_id"],
        )
        dataset = build_window_dataset(
            context.feature_frame, relabeled_events,
            feature_set=str(candidate["feature_set"]),
            feature_columns=tuple(str(column) for column in candidate["feature_columns"]),
            window_size=int(candidate["window_size"]),
        )
        if dataset.metadata.empty:
            raise ValueError(f"{STAGE_NAME} produced no windowed rows for {arm['arm_id']}")
        dataset_hash = sample_id_hash(dataset.metadata["sample_id"].tolist())
        if reference_dataset_hash is None:
            reference_dataset_hash = dataset_hash
        elif dataset_hash != reference_dataset_hash:
            raise ValueError(
                f"{STAGE_NAME} eligibility invariance broken: {arm['arm_id']} window rows "
                f"differ from the reference arm (injection must change labels only)"
            )
        assert_train_domain_only(
            dataset.metadata, ["target_timestamp"],
            stage_label=f"{STAGE_NAME} {arm['arm_id']} window metadata",
        )
        injection_records.append(
            {**stats, "role": arm["role"], "window_dataset_sample_id_hash": dataset_hash,
             "n_window_rows": int(len(dataset.metadata))}
        )
        arm_trials, arm_baselines, arm_sentinels = score_arm_trials(
            arm=arm,
            dataset=dataset,
            folds=context.folds,
            seeds=[int(seed) for seed in config["train_inner"]["seeds"]],
            candidate=candidate,
            model=require_mapping(config["model"], "model"),
            profile=profile,
            config=config,
            sample_policy=require_mapping(config["sample_policy"], "sample_policy"),
            sentinel_config=require_mapping(config["sentinels"], "sentinels"),
            fit_function=fit_stage_control,
        )
        trial_rows.extend(arm_trials)
        baseline_rows.extend(arm_baselines)
        sentinel_rows.extend(arm_sentinels)
        _maybe_checkpoint(config, run_id=run_id, arms=arms, completed_through=arm_index,
                          trial_rows=trial_rows)

    return (
        pd.DataFrame(trial_rows, columns=TRIAL_LEDGER_COLUMNS),
        pd.DataFrame(baseline_rows, columns=BASELINE_CONTROL_COLUMNS),
        pd.DataFrame(sentinel_rows, columns=SENTINEL_LEDGER_COLUMNS),
        injection_records,
    )


def _maybe_checkpoint(
    config: Mapping[str, Any], *, run_id: str, arms: list[dict[str, Any]],
    completed_through: int, trial_rows: list[dict[str, Any]],
) -> None:
    checkpointing = require_mapping(config.get("checkpointing", {}), "checkpointing")
    if checkpointing.get("enabled") is not True:
        return
    checkpoint_dir = Path(str(checkpointing["checkpoint_dir"])) / run_id
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    partial_path = checkpoint_dir / "spc_trial_ledger_partial.csv"
    pd.DataFrame(trial_rows, columns=TRIAL_LEDGER_COLUMNS).to_csv(partial_path, index=False)
    write_incremental_checkpoint(
        checkpoint_dir,
        stage_name=STAGE_NAME,
        run_id=run_id,
        completed_units=[arm["arm_id"] for arm in arms[: completed_through + 1]],
        pending_units=[arm["arm_id"] for arm in arms[completed_through + 1:]],
        required_files=[partial_path.name],
    )


def _sentinel_mean(arm_sentinels: pd.DataFrame, column: str) -> float:
    if arm_sentinels.empty:
        return float("nan")
    return float(arm_sentinels[column].astype(float).mean())


def _build_arm_summary(
    trial_ledger: pd.DataFrame,
    sentinel_ledger: pd.DataFrame,
    injection_records: list[dict[str, Any]],
    *,
    minimum_positive_ticker_count: int,
) -> pd.DataFrame:
    rows = []
    for record in injection_records:
        arm_id = str(record["arm_id"])
        aggregate = arm_delta_aggregates(trial_ledger, arm_id=arm_id)
        flags = flags_signal_fields(
            aggregate, minimum_positive_ticker_count=minimum_positive_ticker_count
        )
        arm_sentinels = sentinel_ledger.loc[sentinel_ledger["arm_id"].astype(str).eq(arm_id)]
        rows.append(
            {
                "arm_id": arm_id,
                "planted_strength": float(record["planted_strength"]),
                "expected_rows": aggregate["expected_rows"],
                "completed_rows": aggregate["completed_rows"],
                "failed_rows": aggregate["failed_rows"],
                "mean_delta_macro_f1_vs_stratified_dummy_train_prior": aggregate["mean_delta"],
                "lcb_delta_macro_f1_vs_stratified_dummy_train_prior": aggregate["lcb_delta"],
                "mean_dummy_macro_f1": aggregate["mean_dummy_macro_f1"],
                "min_positive_ticker_count": aggregate["min_positive_ticker_count"],
                "mean_positive_ticker_count": aggregate["mean_positive_ticker_count"],
                **flags,
                "mean_label_shuffle_p_value": _sentinel_mean(
                    arm_sentinels, "label_shuffle_p_value"
                ),
                "mean_time_reverse_delta": _sentinel_mean(
                    arm_sentinels, "time_reverse_delta"
                ),
                "realized_agreement_rate": float(record["realized_agreement_rate"]),
                "synthetic_up_prior": float(record["synthetic_up_prior"]),
                "synthetic_label_sha256": str(record["synthetic_label_sha256"]),
            }
        )
    return pd.DataFrame(rows, columns=ARM_SUMMARY_COLUMNS)


def _evaluate_criteria(
    config: Mapping[str, Any],
    trial_ledger: pd.DataFrame,
    injection_records: list[dict[str, Any]],
    null_band: Mapping[str, Any],
) -> dict[str, Any]:
    criteria = require_mapping(config["criteria"], "criteria")
    arm_aggregates = {
        float(record["planted_strength"]): arm_delta_aggregates(
            trial_ledger, arm_id=str(record["arm_id"])
        )
        for record in injection_records
    }
    return evaluate_predeclared_criteria(
        arm_aggregates,
        null_band_abs=float(null_band["max_abs_delta"]),
        minimum_positive_ticker_count=int(criteria["minimum_positive_ticker_count"]),
        null_strength=float(criteria["null_strength"]),
        detection_strengths=[float(value) for value in criteria["detection_strengths"]],
        monotone_strengths=[float(value) for value in criteria["monotone_strengths"]],
        threshold_strength=float(criteria["threshold_strength"]),
    )


def _write_result_tables(
    output_dir: Path,
    outputs: Mapping[str, Any],
    trial_ledger: pd.DataFrame,
    arm_summary: pd.DataFrame,
    baseline_summary: pd.DataFrame,
    sentinel_ledger: pd.DataFrame,
) -> dict[str, Path]:
    paths = {
        "trial_ledger": output_dir / _output_name(outputs, "trial_ledger", "spc_trial_ledger.csv"),
        "arm_summary": output_dir / _output_name(outputs, "arm_summary", "spc_arm_summary.csv"),
        "baseline_control_summary": output_dir
        / _output_name(outputs, "baseline_control_summary", "spc_baseline_control_summary.csv"),
        "sentinel_ledger": output_dir
        / _output_name(outputs, "sentinel_ledger", "spc_sentinel_ledger.csv"),
    }
    trial_ledger.to_csv(paths["trial_ledger"], index=False)
    arm_summary.to_csv(paths["arm_summary"], index=False)
    baseline_summary.to_csv(paths["baseline_control_summary"], index=False)
    sentinel_ledger.to_csv(paths["sentinel_ledger"], index=False)
    prefix = _output_name(outputs, "per_arm_trials_prefix", "spc_trials_")
    for arm_id in trial_ledger["arm_id"].astype(str).unique():
        arm_path = output_dir / f"{prefix}{arm_id}.csv"
        trial_ledger.loc[trial_ledger["arm_id"].astype(str).eq(arm_id)].to_csv(
            arm_path, index=False
        )
        paths[f"per_arm_trials_{arm_id}"] = arm_path
    return paths


def _injection_manifest_payload(
    config: Mapping[str, Any], injection_records: list[dict[str, Any]]
) -> dict[str, Any]:
    injection = require_mapping(config["injection"], "injection")
    hashes = sorted({str(record["window_dataset_sample_id_hash"]) for record in injection_records})
    return {
        "stage_name": STAGE_NAME,
        "rule_id": PLANTED_RULE_ID,
        "rule_feature": PLANTED_RULE_FEATURE,
        "injection_seed": int(injection["injection_seed"]),
        "labels_are_synthetic": True,
        "eligibility_invariance": {
            "window_dataset_sample_id_hashes": hashes,
            "all_arms_identical_rows": len(hashes) == 1,
        },
        "arms": injection_records,
        "train_domain_only": True,
        "train_end_exclusive": TRAIN_END_EXCLUSIVE.date().isoformat(),
        "closed_holdout_test_start": CLOSED_HOLDOUT_TEST_START.date().isoformat(),
    }


def _write_run_manifest(
    config: Mapping[str, Any],
    context: SpcDataContext,
    profile: Mapping[str, Any],
    trial_ledger: pd.DataFrame,
    null_band: Mapping[str, Any],
    output_dir: Path,
    run_id: str,
    *,
    output_paths: Mapping[str, Path],
) -> Path:
    inputs = require_mapping(config["inputs"], "inputs")
    outputs = require_mapping(config["outputs"], "outputs")
    notebook_path = resolve_repo_path(inputs["notebook_path"])
    events = context.train_events
    max_horizon_end = (
        pd.to_datetime(events["horizon_end_timestamp"]).max().isoformat()
        if "horizon_end_timestamp" in events.columns
        else None
    )
    payload = {
        "route": config["route"],
        "stage_name": STAGE_NAME,
        "scope": config["scope"],
        "run_id": run_id,
        "config_sha256": hash_mapping(config),
        "notebook_sha256": hash_file(notebook_path),
        "source_stage00_run_id": inputs["stage00_run_id"],
        "source_stage01_run_id": inputs["stage01_run_id"],
        "source_real_stage02_run_id": inputs["stage02_real_run_id"],
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
        "planted_rule_id": PLANTED_RULE_ID,
        "planted_rule_feature": PLANTED_RULE_FEATURE,
        "injection_seed": int(config["injection"]["injection_seed"]),
        "arms": [
            {"arm_id": str(arm["arm_id"]), "strength": float(arm["strength"])}
            for arm in config["injection"]["arms"]
        ],
        "random_seeds": [int(seed) for seed in config["train_inner"]["seeds"]],
        "planned_fit_rows": int(len(trial_ledger)),
        "completed_fit_rows": int(trial_ledger["fit_status"].astype(str).eq("completed").sum()),
        "fold_design_sha256": hash_mapping({"folds": context.folds.to_dict(orient="records")}),
        "raw_file_integrity": raw_manifest_integrity_summary(context.raw_manifest),
        **feature_rebuild_gate_fields(
            context.stage01_manifest,
            source_field="feature_rebuild_code_sha256",
            stage_label=STAGE_NAME,
            current_field="spc_feature_rebuild_code_sha256",
            legacy_reason="stage01_manifest_field_missing_legacy_run",
        ),
        **aggregate_trial_device_fields(trial_ledger),
        **git_commit_fields(),
        "null_band": dict(null_band),
        "train_domain_bounds": {
            "train_start": str(context.split_freeze.get("train_start")),
            "train_end_exclusive": TRAIN_END_EXCLUSIVE.date().isoformat(),
            "closed_holdout_test_start": CLOSED_HOLDOUT_TEST_START.date().isoformat(),
            "max_target_timestamp": pd.to_datetime(events["target_timestamp"]).max().isoformat(),
            "max_horizon_end_timestamp": max_horizon_end,
        },
        "synthetic_labels": True,
        "train_domain_only": True,
        "evidence_status": "synthetic_positive_control_protocol_validation_only",
        "official_validation_contact": False,
        "official_validation_for_selection": False,
        "no_final_model_selected": True,
        "holdout_test_contact": False,
    }
    return write_json(
        output_dir / _output_name(outputs, "manifest", "run_manifest.json"), payload
    )
