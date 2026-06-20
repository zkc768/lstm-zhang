"""Stage 06 Ian final progress record orchestration (progress record, measure-only).

Stage 06 CLOSES the route as a progress record + reproducibility inventory. It
reads each frozen upstream run's ``artifact_inventory.csv`` (per-artifact sha256)
and ``run_manifest.json`` (git_commit), assembles a reproducibility inventory + the
Ian-requirement mapping + an honesty / route-closure record, and writes them.

It performs ZERO new scoring, ZERO fits, makes NO holdout/test contact, and
selects / ranks / crowns NO model (protocol 06 sections 2-6). An upstream run whose
artifacts are not present at runtime is recorded as ``pending_drive_fetch`` rather
than fabricated. This is orchestration only -- no provenance-hashed mechanism code.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from lst_models import synthesis
from lst_models.artifacts import (
    git_commit_fields,
    make_run_id,
    read_json_object,
    write_artifact_inventory,
    write_json,
)
from lst_models.config import hash_file, hash_mapping, require_mapping, resolve_repo_path

STAGE06_SCOPE = "progress_record_measure_only"
HOLDOUT_BOUNDARY = "2017-01-25"

REPRO_INVENTORY_COLUMNS = [
    "stage_name", "run_id", "drive_folder_id", "git_commit",
    "artifact", "sha256", "sha256_status",
]
IAN_MAPPING_COLUMNS = ["requirement", "stage", "artifact", "status"]
REQUIRED_STAGE06_ARTIFACTS = [
    "run_manifest.json",
    "artifact_inventory.csv",
    "06_reproducibility_inventory.csv",
    "06_ian_requirement_mapping.csv",
    "06_progress_record.json",
]


@dataclass(frozen=True)
class Stage06Result:
    run_dir: Path
    progress_record_path: Path
    manifest_path: Path


def run_stage(config: Mapping[str, Any]) -> Stage06Result:
    _validate_config(config)
    forbidden = [str(p) for p in require_mapping(config["forbidden"], "forbidden")["wording"]]
    inventory = _build_reproducibility_inventory(config)
    mapping = _build_ian_mapping(config, forbidden)
    outputs = require_mapping(config["outputs"], "outputs")
    run_id = str(outputs.get("run_id") or make_run_id())
    run_dir = Path(str(outputs["output_dir"])) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    record = _progress_record(config, inventory, mapping, run_id, forbidden)
    return _write_outputs(config, run_dir, run_id, inventory, mapping, record)


def _validate_config(config: Mapping[str, Any]) -> None:
    if str(config.get("stage_name")) != "06_ian_final_progress_record":
        raise ValueError("config stage_name must be 06_ian_final_progress_record")
    if str(config.get("scope")) != STAGE06_SCOPE:
        raise ValueError(f"Stage 06 requires scope={STAGE06_SCOPE}")
    if config.get("holdout_test_contact") is not False:
        raise ValueError("Stage 06 requires holdout_test_contact=false")
    if int(config.get("new_scoring_events", -1)) != 0:
        raise ValueError("Stage 06 requires new_scoring_events=0")
    if config.get("no_final_model_selected") is not True:
        raise ValueError("Stage 06 requires no_final_model_selected=true")
    if config.get("official_validation_for_selection") is not False:
        raise ValueError("Stage 06 requires official_validation_for_selection=false")
    inputs = require_mapping(config["inputs"], "inputs")
    if not list(inputs.get("upstream_runs", [])):
        raise ValueError("Stage 06 requires a non-empty inputs.upstream_runs")
    require_mapping(config["outputs"], "outputs")
    require_mapping(config["ian_requirement_mapping"], "ian_requirement_mapping")
    require_mapping(config["forbidden"], "forbidden")
    for field in ("honesty_statement", "route_closure_statement"):
        if not str(config.get(field, "")).strip():
            raise ValueError(f"Stage 06 requires a non-empty {field}")


def _build_reproducibility_inventory(config: Mapping[str, Any]) -> pd.DataFrame:
    """One row per (upstream run, artifact) with the artifact's frozen sha256, read
    from that run's ``artifact_inventory.csv``. A run folder absent at runtime is a
    single ``pending_drive_fetch`` row (never a fabricated hash)."""
    runs = require_mapping(config["inputs"], "inputs")["upstream_runs"]
    rows: list[dict[str, Any]] = []
    for run in runs:
        stage = str(run["stage_name"])
        run_id = str(run["run_id"])
        drive = str(run.get("drive_folder_id", "") or "")
        run_dir = Path(str(run["runtime_run_dir"]))
        inv_path = run_dir / str(run.get("inventory_artifact", "artifact_inventory.csv"))
        man_path = run_dir / str(run.get("manifest_artifact", "run_manifest.json"))
        git_commit = None
        if man_path.exists():
            git_commit = read_json_object(man_path).get("git_commit")
        common = {"stage_name": stage, "run_id": run_id, "drive_folder_id": drive,
                  "git_commit": git_commit}
        if inv_path.exists():
            inv = pd.read_csv(inv_path)
            name_col = "file_name" if "file_name" in inv.columns else "artifact_name"
            for _, art in inv.iterrows():
                sha = str(art.get("sha256", "") or "")
                rows.append({**common, "artifact": str(art[name_col]), "sha256": sha,
                             "sha256_status": "present" if sha else "missing_in_inventory"})
        else:
            rows.append({**common, "artifact": "<all>", "sha256": "",
                         "sha256_status": "pending_drive_fetch"})
    return pd.DataFrame(rows)[REPRO_INVENTORY_COLUMNS]


def _build_ian_mapping(config: Mapping[str, Any], forbidden: list[str]) -> pd.DataFrame:
    rows = require_mapping(config["ian_requirement_mapping"], "ian_requirement_mapping")["rows"]
    if not rows:
        raise ValueError("Stage 06 requires a non-empty ian_requirement_mapping.rows")
    out = [
        {"requirement": str(r["requirement"]), "stage": str(r.get("stage", "")),
         "artifact": str(r.get("artifact", "")), "status": str(r.get("status", ""))}
        for r in rows
    ]
    frame = pd.DataFrame(out)[IAN_MAPPING_COLUMNS]
    synthesis.assert_no_forbidden_wording(
        " ".join(frame.to_numpy().astype(str).ravel()), forbidden, context="ian requirement mapping"
    )
    return frame


def _progress_record(
    config: Mapping[str, Any], inventory: pd.DataFrame, mapping: pd.DataFrame,
    run_id: str, forbidden: list[str],
) -> dict[str, Any]:
    record = {
        "route": "lst_models",
        "stage_name": "06_ian_final_progress_record",
        "run_id": run_id,
        "scope": STAGE06_SCOPE,
        "honesty_statement": str(config["honesty_statement"]),
        "route_closure_statement": str(config["route_closure_statement"]),
        "stages_inventoried": sorted(set(inventory["stage_name"].astype(str))),
        "n_inventory_rows": int(len(inventory)),
        "n_pending_drive_fetch": int((inventory["sha256_status"] == "pending_drive_fetch").sum()),
        "ian_requirement_count": int(len(mapping)),
        "new_scoring_events": 0,
        "holdout_test_contact": False,
        "official_validation_for_selection": False,
        "no_final_model_selected": True,
        "clean_test_claim": False,
        "holdout_boundary": HOLDOUT_BOUNDARY,
    }
    synthesis.assert_no_forbidden_wording(
        json.dumps(record, default=str, sort_keys=True), forbidden, context="progress record"
    )
    return record


def _manifest_payload(
    config: Mapping[str, Any], run_id: str, inventory: pd.DataFrame
) -> dict[str, Any]:
    inputs = require_mapping(config["inputs"], "inputs")
    notebook = resolve_repo_path(
        Path(str(inputs.get("notebook_path", "notebooks/06_ian_final_progress_record_colab.ipynb")))
    )
    return {
        "route": "lst_models",
        "stage_name": "06_ian_final_progress_record",
        "run_id": run_id,
        "scope": STAGE06_SCOPE,
        "holdout_test_contact": False,
        "new_scoring_events": 0,
        "official_validation_for_selection": False,
        "no_final_model_selected": True,
        "stages_inventoried": sorted(set(inventory["stage_name"].astype(str))),
        **git_commit_fields(),
        "config_sha256": hash_mapping(config),
        "notebook_sha256": hash_file(notebook) if notebook.exists() else None,
        "input_artifacts": [str(run["runtime_run_dir"]) for run in inputs["upstream_runs"]],
        "output_artifacts": REQUIRED_STAGE06_ARTIFACTS,
    }


def _write_outputs(
    config: Mapping[str, Any], run_dir: Path, run_id: str,
    inventory: pd.DataFrame, mapping: pd.DataFrame, record: Mapping[str, Any],
) -> Stage06Result:
    outputs = require_mapping(config["outputs"], "outputs")
    artifact_paths: dict[str, Path] = {}
    inv_name = str(outputs["reproducibility_inventory"])
    inventory.to_csv(run_dir / inv_name, index=False)
    artifact_paths[inv_name] = run_dir / inv_name
    map_name = str(outputs["ian_requirement_mapping"])
    mapping.to_csv(run_dir / map_name, index=False)
    artifact_paths[map_name] = run_dir / map_name
    record_name = str(outputs["progress_record"])
    write_json(run_dir / record_name, record)
    artifact_paths[record_name] = run_dir / record_name
    manifest = _manifest_payload(config, run_id, inventory)
    manifest_name = str(outputs.get("manifest", "run_manifest.json"))
    write_json(run_dir / manifest_name, manifest)
    artifact_paths[manifest_name] = run_dir / manifest_name
    write_artifact_inventory(run_dir, artifact_paths)
    missing = [name for name in REQUIRED_STAGE06_ARTIFACTS if not (run_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Stage 06 required artifacts missing after write: {missing} under {run_dir}"
        )
    return Stage06Result(
        run_dir=run_dir,
        progress_record_path=run_dir / record_name,
        manifest_path=run_dir / manifest_name,
    )
