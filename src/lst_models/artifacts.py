from __future__ import annotations

import hashlib
import importlib.metadata
import inspect
import json
import subprocess
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
import platform
import sys
from typing import Any

import pandas as pd

# Canonical file-hash implementation lives in config.py (low in the import
# graph); re-exported here so `from lst_models.artifacts import hash_file`
# keeps working.
from lst_models.config import hash_file, repo_root
from lst_models.data import (
    load_train_bars,
    load_train_validation_bars,
    read_raw_txt_file,
    resample_1min_to_5min,
)
from lst_models.features import build_feature_frame, require_feature_columns
from lst_models.splits import valid_events_for_split
from lst_models.windows import build_window_dataset


def write_json(path: str | Path, payload: Mapping[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")
    return output_path


def read_json_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"expected JSON object in {path}")
    return loaded


def require_run_id_chain(
    checks: Iterable[tuple[str, str, Any]], *, stage_label: str
) -> None:
    """Fail closed when recorded upstream run ids drift from the config pins.

    ``checks`` rows are ``(field_label, expected, observed)``. Shared by the
    Stage 03 readout and Stage 04 diagnostics entry gates.
    """
    for field_label, expected, observed in checks:
        if observed is None or str(observed) != str(expected):
            raise ValueError(
                f"{stage_label} run id chain mismatch: {field_label} expected "
                f"{expected!r}, observed {observed!r}"
            )


def require_safety_flags(
    payloads: Iterable[tuple[str, Mapping[str, Any]]],
    *,
    stage_label: str,
    field: str,
    expected: bool,
) -> None:
    """Fail closed unless every payload records ``field`` exactly ``expected``."""
    expected_text = "true" if expected else "false"
    for label, payload in payloads:
        if payload.get(field) is not expected:
            raise ValueError(f"{stage_label} requires {label} {field}={expected_text}")


def require_distinct_file_hashes(
    path_a: Path, path_b: Path, *, blocked_label: str, reason: str
) -> None:
    """Fail closed when two artifacts are byte-identical (packaging defect)."""
    if hash_file(path_a) == hash_file(path_b):
        raise ValueError(f"{blocked_label} ({path_a} == {path_b}); {reason}")


def feature_rebuild_gate_fields(
    upstream_manifest: Mapping[str, Any],
    *,
    source_field: str,
    stage_label: str,
    current_field: str,
    legacy_reason: str,
) -> dict[str, Any]:
    """Rebuild-hash gate shared by Stage 03/04: block when the current
    feature-rebuild mechanism hash differs from the recorded upstream hash;
    record legacy tolerance when the upstream field predates provenance."""
    current_hash = feature_rebuild_code_sha256()
    source_hash = upstream_manifest.get(source_field)
    if source_hash and str(source_hash) != current_hash:
        raise ValueError(
            f"{source_field} does not match current {stage_label} rebuild code: "
            f"{source_hash!r} != {current_hash!r}"
        )
    return {
        current_field: current_hash,
        f"source_{source_field}": source_hash,
        "feature_rebuild_code_match": True if source_hash else None,
        "feature_rebuild_code_match_reason": "matched" if source_hash else legacy_reason,
    }


def load_incremental_checkpoint(checkpoint_dir: Path, *, expected_run_id: str) -> dict[str, Any]:
    """Exact-run checkpoint manifest loader (AGENTS.md section 5 resume rules).

    Fails closed when the manifest is missing or records a different run id —
    resume never scans for a latest folder and never crosses run ids.
    """
    manifest_path = checkpoint_dir / "checkpoint_manifest.json"
    if not expected_run_id or not manifest_path.exists():
        raise ValueError(
            "resume requires an exact run_id and an existing checkpoint_manifest.json "
            f"(looked at {manifest_path})"
        )
    manifest = read_json_object(manifest_path)
    if str(manifest.get("run_id")) != expected_run_id:
        raise ValueError(
            f"resume run_id mismatch: checkpoint manifest records "
            f"{manifest.get('run_id')!r}, resume.run_id is {expected_run_id!r}"
        )
    return manifest


def write_incremental_checkpoint(
    checkpoint_dir: Path,
    *,
    stage_name: str,
    run_id: str,
    completed_units: list[str],
    pending_units: list[str],
    required_files: list[str],
) -> Path:
    """AGENTS.md section 5 incremental checkpoint manifest with exact-run
    resume instructions (``status=incomplete``, no latest-parent scanning)."""
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    return write_json(
        checkpoint_dir / "checkpoint_manifest.json",
        {
            "stage_name": stage_name,
            "run_id": run_id,
            "status": "incomplete",
            "completed_units": list(completed_units),
            "pending_units": list(pending_units),
            "checkpoint_timestamp_utc": datetime.now(UTC).isoformat(),
            "holdout_test_contact": False,
            "official_validation_for_selection": False,
            "resume_instructions": {
                "resume_mode": "exact_run_checkpoint_only",
                "latest_parent_scan_allowed": False,
                "required_run_id": run_id,
                "required_checkpoint_dir": str(checkpoint_dir),
                "required_files": list(required_files),
            },
        },
    )


def make_run_id(now: datetime | None = None) -> str:
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    current = current.astimezone(UTC)
    return current.strftime("%Y%m%d_%H%M%S_%f")


def package_versions(package_names: Iterable[str]) -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for name in package_names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def runtime_provenance(config: Mapping[str, Any]) -> dict[str, Any]:
    configured = config.get("provenance", {})
    if not isinstance(configured, Mapping):
        configured = {}
    return {
        "repo_url": configured.get("repo_url"),
        "git_commit": configured.get("git_commit"),
        "bootstrap_mode": configured.get("bootstrap_mode"),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "dependency_versions": package_versions(["pandas", "numpy", "PyYAML"]),
    }


def write_artifact_inventory(output_dir: str | Path, artifact_paths: Mapping[str, Path]) -> Path:
    root = Path(output_dir)
    rows = []
    for name, path in artifact_paths.items():
        artifact_path = Path(path)
        exists = artifact_path.exists()
        try:
            relative_path = artifact_path.relative_to(root)
        except ValueError:
            relative_path = Path(artifact_path.name)
        rows.append(
            {
                "artifact_name": name,
                "file_name": artifact_path.name,
                "relative_path": relative_path.as_posix(),
                "original_runtime_path": str(artifact_path),
                "exists": exists,
                "bytes": artifact_path.stat().st_size if exists else 0,
                "sha256": hash_file(artifact_path) if exists else "",
            }
        )
    inventory = pd.DataFrame(rows)
    output_path = root / "artifact_inventory.csv"
    inventory.to_csv(output_path, index=False)
    return output_path


def require_artifacts(run_dir: str | Path, required_names: Iterable[str]) -> dict[str, Path]:
    root = Path(run_dir)
    paths = {name: root / name for name in required_names}
    missing = [path for path in paths.values() if not path.exists()]
    if missing:
        missing_text = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(f"missing required stage artifacts:\n{missing_text}")
    _verify_artifact_inventory_hashes(root, paths)
    return paths


def _verify_artifact_inventory_hashes(root: Path, paths: Mapping[str, Path]) -> None:
    inventory_path = root / "artifact_inventory.csv"
    if not inventory_path.exists():
        return
    try:
        inventory = pd.read_csv(inventory_path)
    except pd.errors.EmptyDataError:
        return
    if inventory.empty or "sha256" not in inventory.columns:
        return
    for required_name, path in paths.items():
        if required_name == "artifact_inventory.csv":
            continue
        row = _artifact_inventory_row(inventory, required_name)
        if row is None:
            continue
        exists_value = row.get("exists")
        if exists_value is not None and str(exists_value).strip().lower() in {"false", "0", "no"}:
            raise ValueError(f"artifact inventory marks required artifact as missing: {path}")
        expected_bytes = row.get("bytes")
        if pd.notna(expected_bytes) and str(expected_bytes).strip() not in {"", "0"}:
            observed_bytes = path.stat().st_size
            if observed_bytes != int(expected_bytes):
                raise ValueError(
                    f"artifact byte-size mismatch for {path}: "
                    f"expected {int(expected_bytes)}, observed {observed_bytes}"
                )
        expected_sha256 = row.get("sha256")
        if pd.notna(expected_sha256) and str(expected_sha256).strip():
            observed_sha256 = hash_file(path)
            if observed_sha256 != str(expected_sha256).strip().lower():
                raise ValueError(
                    f"artifact sha256 mismatch for {path}: "
                    f"expected {expected_sha256}, observed {observed_sha256}"
                )


def _artifact_inventory_row(inventory: pd.DataFrame, required_name: str) -> pd.Series | None:
    normalized_name = Path(required_name).as_posix()
    for column in ("relative_path", "file_name", "artifact_name"):
        if column not in inventory.columns:
            continue
        matches = inventory.loc[inventory[column].astype(str).eq(normalized_name)]
        if not matches.empty:
            return matches.iloc[0]
    return None


def git_commit_fields() -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root(),
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return {
            "git_commit": None,
            "git_commit_reason": "git_unavailable_or_not_a_repository",
        }
    commit = completed.stdout.strip()
    if completed.returncode == 0 and commit:
        return {"git_commit": commit, "git_commit_reason": "resolved_from_local_git_checkout"}
    return {
        "git_commit": None,
        "git_commit_reason": "workspace_not_git_repository",
    }


def feature_rebuild_code_sha256() -> str:
    """sha256 over the source text of the feature/window rebuild mechanism.

    The payload functions live in domain modules (data.py, features.py,
    windows.py) so stage-orchestration refactors cannot move this hash. Any
    change to this value between chained stages is a provenance break and must
    block downstream gates.
    """
    code_payload = {
        "read_raw_txt_file": inspect.getsource(read_raw_txt_file),
        "resample_1min_to_5min": inspect.getsource(resample_1min_to_5min),
        "load_train_bars": inspect.getsource(load_train_bars),
        "build_feature_frame": inspect.getsource(build_feature_frame),
        "require_feature_columns": inspect.getsource(require_feature_columns),
        "build_window_dataset": inspect.getsource(build_window_dataset),
    }
    payload = json.dumps(code_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def stage03_readout_code_sha256() -> str:
    """sha256 over the Stage 03 readout data-context source composed with the
    frozen feature rebuild chain: the train/validation bar loader, the split
    event filter, and the value of ``feature_rebuild_code_sha256`` (which
    already covers raw reading, resampling, feature building, and window
    building)."""
    code_payload = {
        "load_train_validation_bars": inspect.getsource(load_train_validation_bars),
        "valid_events_for_split": inspect.getsource(valid_events_for_split),
        "feature_rebuild_code_sha256": feature_rebuild_code_sha256(),
    }
    payload = json.dumps(code_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def stage05_synthesis_code_sha256() -> str:
    """sha256 over the Stage 05 synthesis mechanism: the measure-only packaging
    helpers in ``lst_models.synthesis`` (budget-ledger / claim-register /
    expectation-calibration builders, the fail-closed field resolver, and the
    forbidden-wording gate). Domain functions only — Stage 05 does no fit,
    feature rebuild, or scoring, so this hash is independent of the rebuild
    chain and of stage orchestration."""
    from lst_models import synthesis as synthesis_module

    code_payload = {
        "resolve_record_field": inspect.getsource(synthesis_module.resolve_record_field),
        "find_forbidden_wording": inspect.getsource(synthesis_module.find_forbidden_wording),
        "assert_no_forbidden_wording": inspect.getsource(
            synthesis_module.assert_no_forbidden_wording
        ),
        "build_validation_budget_ledger": inspect.getsource(
            synthesis_module.build_validation_budget_ledger
        ),
        "build_claim_boundary_register": inspect.getsource(
            synthesis_module.build_claim_boundary_register
        ),
        "build_expectation_calibration": inspect.getsource(
            synthesis_module.build_expectation_calibration
        ),
        "collect_pooled_delta_estimands": inspect.getsource(
            synthesis_module.collect_pooled_delta_estimands
        ),
    }
    payload = json.dumps(code_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def stage04_diagnostics_code_sha256() -> str:
    """sha256 over the Stage 04 measurement mechanism: the calibration and
    selective-prediction metric helpers, the baseline-reconstruction helper,
    the control fit mechanics, and the frozen rebuild chain hash. Domain
    functions only — stage-orchestration refactors cannot move this hash."""
    from lst_models import fitting as fitting_module
    from lst_models import metrics as metrics_module

    code_payload = {
        "reliability_bins": inspect.getsource(metrics_module.reliability_bins),
        "expected_calibration_error": inspect.getsource(
            metrics_module.expected_calibration_error
        ),
        "maximum_calibration_error": inspect.getsource(
            metrics_module.maximum_calibration_error
        ),
        "brier_score_decomposition": inspect.getsource(
            metrics_module.brier_score_decomposition
        ),
        "top_label_confidence": inspect.getsource(metrics_module.top_label_confidence),
        "risk_coverage_curve": inspect.getsource(metrics_module.risk_coverage_curve),
        "aurc_metrics": inspect.getsource(metrics_module.aurc_metrics),
        "predict_stratified_dummy": inspect.getsource(
            metrics_module.predict_stratified_dummy
        ),
        "last_bar_slice": inspect.getsource(fitting_module.last_bar_slice),
        "lightgbm_tail_split_and_fit_kwargs": inspect.getsource(
            fitting_module.lightgbm_tail_split_and_fit_kwargs
        ),
        "feature_rebuild_code_sha256": feature_rebuild_code_sha256(),
    }
    payload = json.dumps(code_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
