from __future__ import annotations

import hashlib
import json
from pathlib import Path
from collections.abc import Iterable
from typing import Any, Mapping

import pandas as pd


def write_json(path: str | Path, payload: Mapping[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")
    return output_path


def hash_file(path: str | Path) -> str:
    file_path = Path(path)
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    return paths
