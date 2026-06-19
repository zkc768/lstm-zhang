"""Stage 05 thesis-synthesis orchestration (measure-only).

Synthesis/packaging logic lives in ``lst_models.synthesis``; this module owns
entry gates, the synthesis report/manifest, and artifact writing only. Stage 05
reads frozen Stage 03 / Stage 04 / V2.1 artifacts and emits the validation
budget ledger, claim boundary register, and expectation-calibration table —
zero new fits, zero new scoring events, no reselection (protocol 05 §2, §7).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from lst_models import diagnostics, synthesis
from lst_models.artifacts import (
    git_commit_fields,
    make_run_id,
    read_json_object,
    require_artifacts,
    require_run_id_chain,
    require_safety_flags,
    stage05_synthesis_code_sha256,
    write_artifact_inventory,
    write_json,
)
from lst_models.config import hash_file, hash_mapping, require_mapping, resolve_repo_path

STAGE05_SCOPE = "synthesis_measure_only"
HOLDOUT_BOUNDARY = "2017-01-25"
GUARDED_CONTACT_TIER = "guarded_historically_contacted"
UPSTREAM_KEYS = ("stage03", "stage04", "v2_1")
UPSTREAM_DECISION_ARTIFACT = {
    "stage03": "03_decision_record.json",
    "stage04": "04_diagnostics_report.json",
    "v2_1": "v2_1_decision_record.json",
}

REQUIRED_STAGE05_ARTIFACTS = [
    "run_manifest.json",
    "artifact_inventory.csv",
    "05_validation_budget_ledger.csv",
    "05_claim_boundary_register.csv",
    "05_expectation_calibration.csv",
    "05_multiplicity_discount.csv",
    "05_selective_autopsy.csv",
    "05_thesis_synthesis_report.json",
]

# output config key -> frozen columns contract
_FRAME_OUTPUTS = {
    "validation_budget_ledger": synthesis.VALIDATION_BUDGET_LEDGER_COLUMNS,
    "claim_boundary_register": synthesis.CLAIM_BOUNDARY_REGISTER_COLUMNS,
    "expectation_calibration": synthesis.EXPECTATION_CALIBRATION_COLUMNS,
    "multiplicity_discount": synthesis.MULTIPLICITY_DISCOUNT_COLUMNS,
    "selective_autopsy": synthesis.SELECTIVE_AUTOPSY_COLUMNS,
}


@dataclass(frozen=True)
class Stage05Inputs:
    stage_paths: dict[str, dict[str, Path]]
    records_by_key: dict[str, dict[str, Any]]
    stage04_manifest: dict[str, Any]
    run_ids_by_key: dict[str, str]
    notebook_path: Path


@dataclass(frozen=True)
class Stage05Result:
    run_dir: Path
    synthesis_report_path: Path
    manifest_path: Path


def run_stage(config: Mapping[str, Any]) -> Stage05Result:
    _validate_config(config)
    inputs = _verify_entry_gates(config)
    forbidden = _forbidden_wording(config)
    frames = _build_frames(config, inputs, forbidden)
    run_id = str(require_mapping(config["outputs"], "outputs").get("run_id") or make_run_id())
    run_dir = Path(str(require_mapping(config["outputs"], "outputs")["output_dir"])) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    report = _synthesis_report(config, inputs, frames, forbidden, run_id)
    return _write_outputs(config, inputs, run_dir, run_id, frames, report)


def _validate_config(config: Mapping[str, Any]) -> None:
    if str(config.get("stage_name")) != "05_thesis_synthesis":
        raise ValueError("config stage_name must be 05_thesis_synthesis")
    if str(config.get("scope")) != STAGE05_SCOPE:
        raise ValueError(f"Stage 05 requires scope={STAGE05_SCOPE}")
    if config.get("holdout_test_contact") is not False:
        raise ValueError("Stage 05 requires holdout_test_contact=false")
    if str(config.get("official_validation_contact")) != "read_frozen_artifacts_only":
        raise ValueError("Stage 05 requires official_validation_contact=read_frozen_artifacts_only")
    if int(config.get("new_scoring_events", -1)) != 0:
        raise ValueError("Stage 05 requires new_scoring_events=0")
    if config.get("official_validation_for_selection") is not False:
        raise ValueError("Stage 05 requires official_validation_for_selection=false")
    if config.get("no_final_model_selected") is not True:
        raise ValueError("Stage 05 requires no_final_model_selected=true")
    require_mapping(config["inputs"], "inputs")
    require_mapping(config["outputs"], "outputs")
    require_mapping(config["budget_ledger"], "budget_ledger")
    require_mapping(config["claim_boundary_register"], "claim_boundary_register")
    require_mapping(config["expectation_calibration"], "expectation_calibration")
    require_mapping(config["multiplicity_discount"], "multiplicity_discount")
    require_mapping(config["selective_autopsy"], "selective_autopsy")
    if not list(config.get("evidence_domains", [])):
        raise ValueError("Stage 05 requires a non-empty evidence_domains list")
    require_mapping(config["required_upstream_decisions"], "required_upstream_decisions")
    require_mapping(config["forbidden"], "forbidden")


def _verify_entry_gates(config: Mapping[str, Any]) -> Stage05Inputs:
    inputs = require_mapping(config["inputs"], "inputs")
    paths = {
        key: require_artifacts(
            Path(str(inputs[f"{key}_runtime_run_dir"])),
            inputs[f"required_{key}_artifacts"],
            strict=True,  # Stage 03/04/V2.1 are fully provenanced -> fail closed
        )
        for key in UPSTREAM_KEYS
    }
    records = {
        key: read_json_object(paths[key][UPSTREAM_DECISION_ARTIFACT[key]]) for key in UPSTREAM_KEYS
    }
    stage04_manifest = read_json_object(paths["stage04"]["run_manifest.json"])
    _gate_readout_completeness(records)
    _gate_scoring_event_integrity(records)
    _gate_upstream_decisions(config, records)
    _gate_stage04_measure_only(records["stage04"])
    _gate_run_id_chain(inputs, records)
    _gate_safety_flags(records, stage04_manifest)
    _gate_guarded_tier(records["v2_1"])
    return Stage05Inputs(
        stage_paths=paths,
        records_by_key=records,
        stage04_manifest=stage04_manifest,
        run_ids_by_key={key: str(inputs[f"{key}_run_id"]) for key in UPSTREAM_KEYS},
        notebook_path=Path(str(inputs["notebook_path"])),
    )


def _gate_readout_completeness(records: Mapping[str, Mapping[str, Any]]) -> None:
    if records["stage03"].get("readout_complete") is not True:
        raise ValueError("Stage 05 blocked: 03_decision_record.json readout_complete is not true")
    if records["v2_1"].get("readout_complete") is not True:
        raise ValueError("Stage 05 blocked: v2_1_decision_record.json readout_complete is not true")
    if int(records["v2_1"].get("guarded_scoring_events", -1)) < 0:
        raise ValueError("Stage 05 blocked: v2_1_decision_record.json guarded_scoring_events missing")


def _gate_scoring_event_integrity(records: Mapping[str, Mapping[str, Any]]) -> None:
    """The recorded scoring-event count must equal its ledger length (V2.1
    protocol §17; mirrors the Stage 04 entry gate). A count that disagrees with
    the ledger is a tampered/partial record, not a budget we can synthesize."""
    stage03 = records["stage03"]
    ledger03 = stage03.get("scoring_event_ledger")
    if not isinstance(ledger03, list):
        raise ValueError(
            "Stage 05 blocked: 03_decision_record.json scoring_event_ledger missing or not a list"
        )
    if int(stage03.get("official_validation_scoring_events", -1)) != len(ledger03):
        raise ValueError(
            "Stage 05 blocked: Stage 03 official_validation_scoring_events does not equal the "
            "scoring_event_ledger length"
        )
    v2_1 = records["v2_1"]
    ledger_v = v2_1.get("scoring_event_ledger")
    if not isinstance(ledger_v, list):
        raise ValueError(
            "Stage 05 blocked: v2_1_decision_record.json scoring_event_ledger missing or not a list"
        )
    if int(v2_1.get("guarded_scoring_events", -1)) != len(ledger_v):
        raise ValueError(
            "Stage 05 blocked: V2.1 guarded_scoring_events does not equal the "
            "scoring_event_ledger length"
        )


def _gate_upstream_decisions(
    config: Mapping[str, Any], records: Mapping[str, Mapping[str, Any]]
) -> None:
    """The positive 'met criteria' claims (C3/C4) require the pinned upstream
    record to actually carry the met decision; a complete-but-failed pin fails
    closed instead of silently emitting a met claim."""
    required = require_mapping(config["required_upstream_decisions"], "required_upstream_decisions")
    for key, expected in required.items():
        if key not in records:
            raise KeyError(f"required_upstream_decisions key {key!r} is not a wired record")
        actual = records[str(key)].get("decision")
        if str(actual) != str(expected):
            raise ValueError(
                f"Stage 05 blocked: {key} decision must be {expected!r} for the positive "
                f"met-criteria claims, observed {actual!r}"
            )


def _gate_stage04_measure_only(stage04_report: Mapping[str, Any]) -> None:
    if int(stage04_report.get("new_validation_fit_predict_events", -1)) != 0:
        raise ValueError(
            "Stage 05 blocked: 04_diagnostics_report.json new_validation_fit_predict_events != 0"
        )
    if int(stage04_report.get("official_validation_scoring_events", -1)) != 0:
        raise ValueError(
            "Stage 05 blocked: 04_diagnostics_report.json official_validation_scoring_events != 0"
        )


def _gate_run_id_chain(
    inputs: Mapping[str, Any], records: Mapping[str, Mapping[str, Any]]
) -> None:
    # Binding invariant: a SHARED frozen Stage 03. The Stage 04 diagnostics run
    # and the V2.1 guarded readout are siblings off the same Stage 03 dump. V2.1's
    # own source_stage04_run_id is an ordering reference (stage04_first) and MAY
    # differ from the canonical sentinel Stage 04 diagnostics run Stage 05 reads
    # (e.g. V2.1 sequenced after an earlier Stage 04, before the sentinel re-run);
    # it is recorded in the report for provenance, not gated for equality.
    stage03_id = str(inputs["stage03_run_id"])
    require_run_id_chain(
        [
            (
                "04_diagnostics_report.json source_stage03_run_id",
                stage03_id,
                records["stage04"].get("source_stage03_run_id"),
            ),
            (
                "v2_1_decision_record.json source_stage03_run_id",
                stage03_id,
                records["v2_1"].get("source_stage03_run_id"),
            ),
        ],
        stage_label="Stage 05",
    )


def _gate_safety_flags(
    records: Mapping[str, Mapping[str, Any]], stage04_manifest: Mapping[str, Any]
) -> None:
    require_safety_flags(
        [
            ("03_decision_record.json", records["stage03"]),
            ("04_diagnostics_report.json", records["stage04"]),
            ("stage04 run_manifest.json", stage04_manifest),
        ],
        stage_label="Stage 05", field="holdout_test_contact", expected=False,
    )
    require_safety_flags(
        [
            ("03_decision_record.json", records["stage03"]),
            ("04_diagnostics_report.json", records["stage04"]),
            ("v2_1_decision_record.json", records["v2_1"]),
        ],
        stage_label="Stage 05", field="official_validation_for_selection", expected=False,
    )
    require_safety_flags(
        [
            ("04_diagnostics_report.json", records["stage04"]),
            ("v2_1_decision_record.json", records["v2_1"]),
        ],
        stage_label="Stage 05", field="no_final_model_selected", expected=True,
    )
    require_safety_flags(
        [("v2_1_decision_record.json", records["v2_1"])],
        stage_label="Stage 05", field="clean_test_claim", expected=False,
    )


def _gate_guarded_tier(v2_1_record: Mapping[str, Any]) -> None:
    tier = str(v2_1_record.get("holdout_contact_tier"))
    if tier != GUARDED_CONTACT_TIER:
        raise ValueError(
            f"Stage 05 blocked: v2_1 holdout_contact_tier must be {GUARDED_CONTACT_TIER!r}, "
            f"got {tier!r}"
        )


def _forbidden_wording(config: Mapping[str, Any]) -> list[str]:
    return [str(phrase) for phrase in require_mapping(config["forbidden"], "forbidden")["wording"]]


def _build_frames(
    config: Mapping[str, Any], inputs: Stage05Inputs, forbidden: list[str]
) -> dict[str, pd.DataFrame]:
    evidence_domains = [str(domain) for domain in config["evidence_domains"]]
    budget = synthesis.build_validation_budget_ledger(
        require_mapping(config["budget_ledger"], "budget_ledger")["stages"],
        inputs.records_by_key,
        inputs.run_ids_by_key,
        evidence_domains=evidence_domains,
    )
    inputs_cfg = require_mapping(config["inputs"], "inputs")
    supporting_artifacts_by_key = {
        key: [str(name) for name in inputs_cfg[f"required_{key}_artifacts"]]
        for key in UPSTREAM_KEYS
    }
    register = synthesis.build_claim_boundary_register(
        require_mapping(config["claim_boundary_register"], "claim_boundary_register")["claims"],
        inputs.run_ids_by_key,
        forbidden,
        evidence_domains=evidence_domains,
        supporting_artifacts_by_key=supporting_artifacts_by_key,
    )
    expectation = synthesis.build_expectation_calibration(
        require_mapping(config["expectation_calibration"], "expectation_calibration")["rows"],
        inputs.records_by_key,
        forbidden,
    )
    multiplicity_cfg = require_mapping(config["multiplicity_discount"], "multiplicity_discount")
    source_key = str(multiplicity_cfg["source_key"])
    readout = pd.read_csv(inputs.stage_paths[source_key][str(multiplicity_cfg["source_artifact"])])
    multiplicity = synthesis.build_multiplicity_discount(
        readout,
        family_axis=str(multiplicity_cfg["family_axis"]),
        period_axis=str(multiplicity_cfg["period_axis"]),
        delta_field=str(multiplicity_cfg["delta_field"]),
        completed_status_field=str(multiplicity_cfg.get("completed_status_field", "fit_status")),
        completed_status_value=str(multiplicity_cfg.get("completed_status_value", "completed")),
        model_row_kind=multiplicity_cfg.get("model_row_kind"),
        is_block_count=multiplicity_cfg.get("is_block_count"),
        expected_family_count=multiplicity_cfg.get("expected_family_count"),
        expected_period_count=multiplicity_cfg.get("expected_period_count"),
        expected_seeds_per_cell=multiplicity_cfg.get("expected_seeds_per_cell"),
        seed_aggregation=str(multiplicity_cfg.get("seed_aggregation", "mean_over_seeds")),
        descriptive_note=str(multiplicity_cfg.get("descriptive_note", "")),
    )
    autopsy = _build_selective_autopsy(config, inputs)
    return {
        "validation_budget_ledger": budget,
        "claim_boundary_register": register,
        "expectation_calibration": expectation,
        "multiplicity_discount": multiplicity,
        "selective_autopsy": autopsy,
    }


def _build_selective_autopsy(config: Mapping[str, Any], inputs: Stage05Inputs) -> pd.DataFrame:
    cfg = require_mapping(config["selective_autopsy"], "selective_autopsy")
    seeds = [int(seed) for seed in cfg["expected_seeds"]]
    dump_raw = pd.read_csv(
        inputs.stage_paths[str(cfg["dump_source_key"])][str(cfg["dump_artifact"])]
    )
    ledger = inputs.records_by_key["stage03"].get("scoring_event_ledger", [])
    gated_dump = diagnostics.gate_and_derive_dump(
        dump_raw,
        expected_seeds=seeds,
        expected_rows=cfg.get("expected_dump_rows"),
        ledger_rows=sum(int(event["n_rows"]) for event in ledger),
        holdout_boundary=pd.Timestamp(HOLDOUT_BOUNDARY),
    )
    robustness = pd.read_csv(
        inputs.stage_paths[str(cfg["mde_source_key"])][str(cfg["mde_artifact"])]
    )
    return synthesis.build_selective_autopsy(
        gated_dump,
        robustness,
        seeds=seeds,
        activity_axis=str(cfg.get("activity_axis", "activity_tercile")),
        mde_seed_slice_axis=str(cfg.get("mde_seed_slice_axis", "seed")),
        mde_tercile_slice_axis=str(cfg.get("mde_tercile_slice_axis", "activity_tercile")),
    )


def _source_run_id_fields(config: Mapping[str, Any]) -> dict[str, Any]:
    inputs = config["inputs"]
    return {
        "source_stage03_run_id": str(inputs["stage03_run_id"]),
        "source_stage04_run_id": str(inputs["stage04_run_id"]),
        "source_v2_1_run_id": str(inputs["v2_1_run_id"]),
    }


def _multiplicity_summary(frame: pd.DataFrame) -> dict[str, Any]:
    summary = frame.loc[frame["row_kind"].eq("summary")]
    if summary.empty:
        return {}
    row = summary.iloc[0]

    def _num(value: Any) -> float | None:
        return None if pd.isna(value) else float(value)

    def _int(value: Any) -> int | None:
        return None if pd.isna(value) else int(value)

    return {
        "min_family_lcb": _num(row["min_family_lcb"]),
        "median_family_lcb": _num(row["median_family_lcb"]),
        "max_family_mean": _num(row["max_family_mean"]),
        "pbo": _num(row["pbo"]),
        "pbo_n_trials": _int(row["pbo_n_trials"]),
        "pbo_n_blocks": _int(row["pbo_n_blocks"]),
        "pbo_n_combinations": _int(row["pbo_n_combinations"]),
        "pbo_method": None if pd.isna(row["pbo_method"]) else str(row["pbo_method"]),
        "seed_aggregation": None if pd.isna(row["seed_aggregation"]) else str(row["seed_aggregation"]),
        "descriptive_only": True,
    }


def _selective_autopsy_summary(frame: pd.DataFrame, note: str) -> dict[str, Any]:
    def _pick(tercile: str, seed: str) -> pd.Series | None:
        sub = frame[(frame["activity_tercile"].eq(tercile)) & (frame["seed"].eq(seed))]
        return None if sub.empty else sub.iloc[0]

    def _num(value: Any) -> float | None:
        return None if value is None or pd.isna(value) else float(value)

    def _clears(value: Any) -> bool | None:
        return None if value is None or pd.isna(value) else bool(value)

    pooled = _pick("all", "seed_mean")
    summary: dict[str, Any] = {
        "descriptive_only": True,
        "selective_metric_basis": "accuracy_no_cost_or_return",
        "note": str(note),
    }
    if pooled is not None:
        summary["pooled_augrc"] = _num(pooled["augrc"])
        summary["pooled_e_aurc"] = _num(pooled["e_aurc"])
        summary["pooled_full_coverage_risk"] = _num(pooled["full_coverage_risk"])
    summary["delta_clears_mde_by_tercile"] = {
        tercile: (None if (row := _pick(tercile, "seed_mean")) is None
                  else _clears(row["delta_clears_mde"]))
        for tercile in ("low", "mid", "high")
    }
    return summary


def _synthesis_report(
    config: Mapping[str, Any],
    inputs: Stage05Inputs,
    frames: Mapping[str, pd.DataFrame],
    forbidden: list[str],
    run_id: str,
) -> dict[str, Any]:
    budget = frames["validation_budget_ledger"]
    register = frames["claim_boundary_register"]
    v2_1_record = inputs.records_by_key["v2_1"]
    report = {
        "route": "lst_models",
        "stage_name": "05_thesis_synthesis",
        "run_id": run_id,
        "scope": STAGE05_SCOPE,
        **_source_run_id_fields(config),
        "stage03_decision": str(inputs.records_by_key["stage03"].get("decision")),
        "v2_1_decision": str(v2_1_record.get("decision")),
        # provenance: the Stage 04 diagnostics run Stage 05 reads (source_stage04_run_id
        # above) may differ from the Stage 04 V2.1 sequenced after -- both chain to the
        # same Stage 03; the divergence is recorded, not hidden.
        "v2_1_source_stage04_run_id": str(v2_1_record.get("source_stage04_run_id")),
        "v2_1_pooled_delta_estimands": synthesis.collect_pooled_delta_estimands(v2_1_record),
        "multiplicity_discount": _multiplicity_summary(frames["multiplicity_discount"]),
        "selective_autopsy": _selective_autopsy_summary(
            frames["selective_autopsy"],
            str(require_mapping(config["selective_autopsy"], "selective_autopsy").get(
                "descriptive_note", ""
            )),
        ),
        "scoring_event_budget": {
            str(row["stage_name"]): int(row["scoring_events"])
            for _, row in budget.iterrows()
        },
        "claim_count": int(len(register)),
        "limitation_count": int(register["is_limitation"].astype(bool).sum()),
        "evidence_domains": [str(domain) for domain in config["evidence_domains"]],
        "kb_wording_guardrails": [str(item) for item in config["kb_wording_guardrails"]],
        "deferred_synthesis_items": [str(item) for item in config["deferred_synthesis_items"]],
        "new_scoring_events": 0,
        "no_final_model_selected": True,
        "clean_test_claim": False,
        "holdout_test_contact": False,
        "official_validation_contact": "read_frozen_artifacts_only",
        "reads_guarded_walkforward_artifacts": True,
        "holdout_boundary": HOLDOUT_BOUNDARY,
    }
    synthesis.assert_no_forbidden_wording(
        json.dumps(report, default=str, sort_keys=True), forbidden, context="synthesis report"
    )
    return report


def _manifest_payload(
    config: Mapping[str, Any], inputs: Stage05Inputs, run_id: str
) -> dict[str, Any]:
    # Resolve the notebook against the repo root so notebook_sha256 is reliable
    # regardless of the runtime cwd (a bare relative path hashes to null off-root).
    notebook_resolved = resolve_repo_path(inputs.notebook_path)
    notebook_present = notebook_resolved.exists()
    return {
        "route": "lst_models",
        "stage_name": "05_thesis_synthesis",
        "run_id": run_id,
        "scope": STAGE05_SCOPE,
        "holdout_test_contact": False,
        "official_validation_contact": "read_frozen_artifacts_only",
        "official_validation_for_selection": False,
        "new_scoring_events": 0,
        "reads_guarded_walkforward_artifacts": True,
        "no_final_model_selected": True,
        **_source_run_id_fields(config),
        "v2_1_decision": str(inputs.records_by_key["v2_1"].get("decision")),
        "stage03_decision": str(inputs.records_by_key["stage03"].get("decision")),
        "stage05_synthesis_code_sha256": stage05_synthesis_code_sha256(),
        **git_commit_fields(),
        "config_sha256": hash_mapping(config),
        "notebook_sha256": hash_file(notebook_resolved) if notebook_present else None,
        "notebook_sha256_reason": (
            "resolved_from_repo_root" if notebook_present else "notebook_not_present_at_runtime"
        ),
        "input_artifacts": [
            str(path) for key in UPSTREAM_KEYS for path in inputs.stage_paths[key].values()
        ],
        "output_artifacts": REQUIRED_STAGE05_ARTIFACTS,
    }


def _write_outputs(
    config: Mapping[str, Any],
    inputs: Stage05Inputs,
    run_dir: Path,
    run_id: str,
    frames: Mapping[str, pd.DataFrame],
    report: Mapping[str, Any],
) -> Stage05Result:
    outputs = require_mapping(config["outputs"], "outputs")
    artifact_paths: dict[str, Path] = {}
    for key, columns in _FRAME_OUTPUTS.items():
        frame = frames[key]
        if list(frame.columns) != columns:
            raise ValueError(f"Stage 05 output {key} columns drifted from the frozen contract")
        name = str(outputs[key])
        frame.to_csv(run_dir / name, index=False)
        artifact_paths[name] = run_dir / name
    report_name = str(outputs["synthesis_report"])
    write_json(run_dir / report_name, report)
    artifact_paths[report_name] = run_dir / report_name
    manifest = _manifest_payload(config, inputs, run_id)
    manifest_name = str(outputs.get("manifest", "run_manifest.json"))
    write_json(run_dir / manifest_name, manifest)
    artifact_paths[manifest_name] = run_dir / manifest_name
    write_artifact_inventory(run_dir, artifact_paths)
    missing = [name for name in REQUIRED_STAGE05_ARTIFACTS if not (run_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Stage 05 required artifacts missing after write: {missing} under {run_dir}"
        )
    return Stage05Result(
        run_dir=run_dir,
        synthesis_report_path=run_dir / report_name,
        manifest_path=run_dir / manifest_name,
    )
