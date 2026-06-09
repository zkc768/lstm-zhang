from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"missing config file: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"expected mapping in config file: {config_path}")
    return loaded


def stable_json_dumps(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def hash_mapping(value: Mapping[str, Any]) -> str:
    payload = stable_json_dumps(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


RUNTIME_PATH_KEYS = {
    "notebook_path",
    "output_dir",
    "raw_data_dir",
    "raw_data_manifest",
    "stage00_runtime_run_dir",
    "stage00_run_manifest",
    "stage01_runtime_run_dir",
    "stage01_candidate_inputs",
}


def normalize_for_research_hash(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): (
                "<runtime_path>"
                if str(key) in RUNTIME_PATH_KEYS
                else normalize_for_research_hash(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [normalize_for_research_hash(item) for item in value]
    if isinstance(value, tuple):
        return [normalize_for_research_hash(item) for item in value]
    return value


def hash_research_config(value: Mapping[str, Any]) -> str:
    payload = stable_json_dumps(normalize_for_research_hash(value)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def hash_file(path: str | Path) -> str:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"missing file for sha256: {file_path}")
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
