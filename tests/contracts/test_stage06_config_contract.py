from __future__ import annotations

import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from lst_models import synthesis  # noqa: E402

CONFIG = yaml.safe_load(
    (REPO_ROOT / "configs" / "stages" / "06_ian_final_progress_record.yaml").read_text(encoding="utf-8")
)
PIPELINE = yaml.safe_load(
    (REPO_ROOT / "configs" / "lst_models_pipeline.yaml").read_text(encoding="utf-8")
)

EXPECTED_STAGES = {
    "00_data_split_label_freeze", "01_feature_window_search", "02_model_hpo_train_inner",
    "03_frozen_validation_readout", "04_diagnostics_ablation", "05_thesis_synthesis",
    "v2_1_guarded_walkforward_readout",
}


def test_scope_and_measure_only_flags() -> None:
    assert CONFIG["stage_name"] == "06_ian_final_progress_record"
    assert CONFIG["route"] == "lst_models"
    assert CONFIG["scope"] == "progress_record_measure_only"
    assert CONFIG["holdout_test_contact"] is False
    assert CONFIG["new_scoring_events"] == 0
    assert CONFIG["no_final_model_selected"] is True
    assert CONFIG["official_validation_for_selection"] is False


def test_upstream_runs_cover_every_stage_with_real_ids() -> None:
    runs = CONFIG["inputs"]["upstream_runs"]
    assert {str(r["stage_name"]) for r in runs} == EXPECTED_STAGES
    for run in runs:
        run_id = str(run["run_id"])
        assert run_id and run_id != "None"
        assert str(run["drive_folder_id"]).strip()
        assert run_id in str(run["runtime_run_dir"])
        assert run_id in str(run["drive_path_parts"])


def test_required_artifact_list_closes_with_runner_constant() -> None:
    from lst_models.stages.ian_final_progress_record import REQUIRED_STAGE06_ARTIFACTS

    outputs = CONFIG["outputs"]
    stage_artifacts = sorted(value for key, value in outputs.items() if key != "output_dir")
    assert sorted(REQUIRED_STAGE06_ARTIFACTS) == stage_artifacts
    for key in ("reproducibility_inventory", "ian_requirement_mapping", "progress_record"):
        assert outputs[key].startswith("06_")


def test_ian_requirement_mapping_well_formed() -> None:
    rows = CONFIG["ian_requirement_mapping"]["rows"]
    assert rows, "Ian-requirement mapping must declare at least one row"
    for row in rows:
        for field in ("requirement", "stage", "artifact", "status"):
            assert str(row.get(field, "")).strip(), f"row missing {field}: {row}"
    statuses = " ".join(str(r["status"]) for r in rows).lower()
    # honesty: the threshold-sweep limitation and the guarded (not clean) framing surface
    assert "limitation" in statuses
    assert any("guarded" in str(r["status"]).lower() for r in rows)


def test_honesty_and_closure_present_and_forbidden_clean() -> None:
    forbidden = CONFIG["forbidden"]["wording"]
    for field in ("honesty_statement", "route_closure_statement"):
        text = str(CONFIG[field])
        assert text.strip()
        hits = synthesis.find_forbidden_wording(text, forbidden)
        assert not hits, f"forbidden wording in {field}: {hits}"
    # the mapping rows must also be forbidden-clean (runner asserts this at run time)
    flat = " ".join(
        f"{r['requirement']} {r['stage']} {r['artifact']} {r['status']}"
        for r in CONFIG["ian_requirement_mapping"]["rows"]
    )
    assert not synthesis.find_forbidden_wording(flat, forbidden)


def test_forbidden_superset_present() -> None:
    forbidden = CONFIG["forbidden"]["wording"]
    for phrase in (
        "final model", "official validation winner", "holdout winner", "test winner",
        "proved best model", "generalization proven", "profitable", "holdout-ready",
        "selected by official validation", "chosen threshold", "clean test",
    ):
        assert phrase in forbidden


def test_pipeline_registry_lists_every_stage_and_06() -> None:
    by_name = {str(s["name"]): s for s in PIPELINE["stages"]}
    assert PIPELINE["route"] == "lst_models"
    for nn in ("00_data_split_label_freeze", "03_frozen_validation_readout",
               "05_thesis_synthesis", "06_ian_final_progress_record"):
        assert nn in by_name
        assert by_name[nn]["config"].startswith("configs/")
        assert by_name[nn]["protocol"].startswith("docs/protocols/")
    # the v2.1 measure-only branch is registered and chains correctly
    branch = {str(b["name"]): b for b in PIPELINE["branches"]}["v2_1_guarded_walkforward_readout"]
    assert branch["branches_after"] == "04_diagnostics_ablation"
    assert branch["feeds"] == "05_thesis_synthesis"
    # the Stage 06 config's upstream run ids agree with the pipeline registry
    reg_ids = {str(s["name"]): str(s["active_run_id"]) for s in PIPELINE["stages"]}
    reg_ids["v2_1_guarded_walkforward_readout"] = str(branch["active_run_id"])
    for run in CONFIG["inputs"]["upstream_runs"]:
        assert str(run["run_id"]) == reg_ids[str(run["stage_name"])]
