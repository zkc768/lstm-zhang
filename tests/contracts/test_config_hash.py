from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models.config import hash_mapping, hash_research_config  # noqa: E402


def test_research_config_hash_ignores_runtime_paths() -> None:
    base = {
        "stage_name": "00_data_split_label_freeze",
        "route": "lst_models",
        "scope": "validation_only",
        "inputs": {
            "raw_data_manifest": "/content/lst_models/configs/lst_models_data.yaml",
            "notebook_path": "/content/lst_models/notebooks/00_data_split_label_freeze_colab.ipynb",
            "raw_data_dir": "/content/lst_models_raw_stock_data",
        },
        "outputs": {"output_dir": "/content/lst_models_results/00_data_split_label_freeze"},
        "label_policy": {"operator": "endpoint_cumulative_return", "horizon_k": 9},
    }
    moved = {
        **base,
        "inputs": {
            "raw_data_manifest": "G:/Drive/lst_models/configs/lst_models_data.yaml",
            "notebook_path": "G:/Drive/lst_models/notebooks/00_data_split_label_freeze_colab.ipynb",
            "raw_data_dir": "G:/Drive/lst_models_raw_stock_data",
        },
        "outputs": {"output_dir": "G:/Drive/lst_models/results/00_data_split_label_freeze"},
    }

    assert hash_research_config(base) == hash_research_config(moved)
    assert hash_mapping(base) != hash_mapping(moved)


def test_research_config_hash_keeps_label_policy_changes() -> None:
    base = {
        "stage_name": "00_data_split_label_freeze",
        "label_policy": {"operator": "endpoint_cumulative_return", "horizon_k": 9},
        "inputs": {"raw_data_dir": "/content/a"},
    }
    changed = {
        "stage_name": "00_data_split_label_freeze",
        "label_policy": {"operator": "endpoint_cumulative_return", "horizon_k": 12},
        "inputs": {"raw_data_dir": "/content/b"},
    }

    assert hash_research_config(base) != hash_research_config(changed)
