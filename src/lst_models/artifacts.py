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
