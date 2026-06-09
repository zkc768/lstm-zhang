from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models.stages.model_hpo_train_inner import run_stage  # noqa: E402


def write_stage01_artifacts(
    run_dir: Path,
    *,
    handoff: dict | None = None,
    holdout_contact: bool = False,
) -> None:
    run_dir.mkdir(parents=True)
    (run_dir / "run_manifest.json").write_text(
        json.dumps({"holdout_test_contact": holdout_contact, "config_sha256": "stage01hash"}),
        encoding="utf-8",
    )
    (run_dir / "artifact_inventory.csv").write_text("artifact_name,file_name\n", encoding="utf-8")
    if handoff is None:
        handoff = {
            "route": "lst_models",
            "stage_name": "01_feature_window_search",
            "source_stage00_run_id": "stage00_test",
            "candidate_inputs": [],
            "approved_model_families_for_stage02": [],
            "decision": "do_not_start_stage02_probe_fits_not_implemented",
            "no_final_model_selected": True,
            "holdout_test_contact": False,
        }
    (run_dir / "01_candidate_inputs.json").write_text(json.dumps(handoff), encoding="utf-8")
    pd.DataFrame(
        [{"candidate_id": "price_action_core_w10", "selected_for_stage02": False}]
    ).to_csv(run_dir / "01_feature_window_search_summary.csv", index=False)
    pd.DataFrame([{"probe_id": "lightgbm_small", "fit_status": "skipped"}]).to_csv(
        run_dir / "01_train_inner_probe_ledger.csv", index=False
    )
    pd.DataFrame([{"fold_id": "fold_0", "event_overlap_count": 0}]).to_csv(
        run_dir / "01_train_inner_fold_manifest.csv", index=False
    )


def write_search_space(path: Path, family: str, profile_ids: list[str]) -> None:
    path.parent.mkdir(parents=True)
    payload = {
        "model_family": family,
        "search_mode": "bounded_profiles",
        "profiles": [{"profile_id": profile_id} for profile_id in profile_ids],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def stage02_config(tmp_path: Path, stage01_run_dir: Path) -> dict:
    notebook_path = tmp_path / "02_model_hpo_train_inner_colab.ipynb"
    notebook_path.write_text("{}", encoding="utf-8")
    search_root = tmp_path / "search_spaces"
    for family in ["lightgbm", "standard_dlinear", "tcn", "ms_dlinear_tcn"]:
        write_search_space(search_root / family / "search_space.yaml", family, ["p01", "p02"])
    return {
        "stage_name": "02_model_hpo_train_inner",
        "route": "lst_models",
        "scope": "validation_only",
        "holdout_test_contact": False,
        "inputs": {
            "stage01_run_id": "stage01_test",
            "stage01_runtime_run_dir": str(stage01_run_dir),
            "stage01_drive_path_parts": ["lst_models", "results", "01", "stage01_test"],
            "stage01_candidate_inputs": str(stage01_run_dir / "01_candidate_inputs.json"),
            "notebook_path": str(notebook_path),
            "required_stage01_artifacts": [
                "run_manifest.json",
                "artifact_inventory.csv",
                "01_candidate_inputs.json",
                "01_feature_window_search_summary.csv",
                "01_train_inner_probe_ledger.csv",
                "01_train_inner_fold_manifest.csv",
            ],
        },
        "outputs": {
            "output_dir": str(tmp_path / "out"),
            "manifest": "run_manifest.json",
            "artifact_inventory": "artifact_inventory.csv",
            "summary": "02_model_hpo_train_inner_summary.csv",
            "hpo_plan_ledger": "02_hpo_plan_ledger.csv",
            "best_params_by_family": "02_best_params_by_family.json",
            "stage03_handoff": "02_stage03_handoff.json",
        },
        "train_inner": {
            "n_folds": 2,
            "seeds": [101],
            "official_validation_for_selection": False,
            "event_overlap_count_required": 0,
        },
        "hpo_families": {
            family: {
                "enabled": family in ["lightgbm", "standard_dlinear"],
                "search_space": str(search_root / family / "search_space.yaml"),
            }
            for family in ["lightgbm", "standard_dlinear", "tcn", "ms_dlinear_tcn"]
        },
        "optional_fixed_controls": {"simple_gru": {"enabled": False}},
        "budget": {"max_hpo_plan_rows": 20, "max_profiles_per_family": 2},
        "selection_rules": {
            "primary_metric": "macro_f1",
            "baseline": "stratified_dummy_train_prior",
            "require_completed_rows_before_stage03": True,
            "max_selected_configs_per_family": 1,
            "no_official_validation_selection": True,
            "no_final_model_selected": True,
        },
        "stage03_handoff": {"allowed_when_hpo_complete": True},
    }


def test_stage02_blocks_when_stage01_has_no_candidates(tmp_path: Path) -> None:
    stage01_run_dir = tmp_path / "stage01"
    write_stage01_artifacts(stage01_run_dir)

    result = run_stage(stage02_config(tmp_path, stage01_run_dir))

    assert result.run_manifest.exists()
    assert result.artifact_inventory.exists()
    assert result.summary.exists()
    assert result.hpo_plan_ledger.exists()
    assert result.best_params_by_family.exists()
    assert result.stage03_handoff.exists()

    manifest = json.loads(result.run_manifest.read_text(encoding="utf-8"))
    assert manifest["holdout_test_contact"] is False
    assert manifest["no_final_model_selected"] is True
    assert manifest["stage02_execution_mode"] == "blocked_by_stage01_no_candidate_inputs"

    summary = pd.read_csv(result.summary)
    assert summary.loc[0, "status"] == "blocked"
    assert summary.loc[0, "decision"] == "do_not_start_stage03_stage02_blocked_by_stage01"

    ledger = pd.read_csv(result.hpo_plan_ledger)
    assert list(ledger.columns)
    assert ledger.empty

    handoff = json.loads(result.stage03_handoff.read_text(encoding="utf-8"))
    assert handoff["ready_for_stage03"] is False
    assert handoff["holdout_test_contact"] is False


def test_stage02_plans_hpo_rows_for_stage01_candidates(tmp_path: Path) -> None:
    stage01_run_dir = tmp_path / "stage01"
    handoff = {
        "route": "lst_models",
        "stage_name": "01_feature_window_search",
        "source_stage00_run_id": "stage00_test",
        "candidate_inputs": [
            {
                "candidate_id": "price_action_core_w10",
                "feature_set": "price_action_core",
                "window_size": 10,
            }
        ],
        "approved_model_families_for_stage02": ["lightgbm", "standard_dlinear"],
        "decision": "selected_candidate_inputs_for_stage02_train_inner_hpo",
        "no_final_model_selected": True,
        "holdout_test_contact": False,
    }
    write_stage01_artifacts(stage01_run_dir, handoff=handoff)

    result = run_stage(stage02_config(tmp_path, stage01_run_dir))

    manifest = json.loads(result.run_manifest.read_text(encoding="utf-8"))
    assert manifest["stage02_execution_mode"] == "hpo_plan_scaffold_no_training"

    ledger = pd.read_csv(result.hpo_plan_ledger)
    assert len(ledger) == 8
    assert set(ledger["model_family"]) == {"lightgbm", "standard_dlinear"}
    assert set(ledger["fit_status"]) == {"skipped_not_implemented"}
    assert ledger["selected_for_stage03"].eq(False).all()

    best_params = json.loads(result.best_params_by_family.read_text(encoding="utf-8"))
    assert best_params["decision"] == "no_frozen_params_hpo_fits_not_implemented"


def test_stage02_rejects_stage01_holdout_contact(tmp_path: Path) -> None:
    stage01_run_dir = tmp_path / "stage01"
    write_stage01_artifacts(stage01_run_dir, holdout_contact=True)

    with pytest.raises(ValueError, match="holdout_test_contact=false"):
        run_stage(stage02_config(tmp_path, stage01_run_dir))


def test_stage02_rejects_unknown_stage01_family(tmp_path: Path) -> None:
    stage01_run_dir = tmp_path / "stage01"
    handoff = {
        "candidate_inputs": [
            {"candidate_id": "c1", "feature_set": "price_action_core", "window_size": 10}
        ],
        "approved_model_families_for_stage02": ["shallow_lstm"],
        "decision": "selected_candidate_inputs_for_stage02_train_inner_hpo",
        "no_final_model_selected": True,
        "holdout_test_contact": False,
    }
    write_stage01_artifacts(stage01_run_dir, handoff=handoff)

    with pytest.raises(ValueError, match="not enabled"):
        run_stage(stage02_config(tmp_path, stage01_run_dir))
