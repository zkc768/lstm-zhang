from __future__ import annotations

import ast
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "notebooks" / "05_thesis_synthesis_colab.ipynb"

# Two-step exact-commit pin (AGENTS.md section 5): the Stage 05 bundle is not yet
# committed/pinned (commit is user-gated), so the notebook ships the placeholder.
# When the user authorizes the bundle commit, update this constant and the
# notebook PROJECT_REPO_COMMIT together in the pin commit.
EXPECTED_PROJECT_REPO_COMMIT = "<STAGE05_FULL_BUNDLE_COMMIT>"
CURRENT_STAGE03_RUN_ID = "20260610_133305_716174"
CURRENT_STAGE04_RUN_ID = "20260618_234011_838683"
CURRENT_V2_1_RUN_ID = "20260618_063559_889276"


def _notebook() -> nbformat.NotebookNode:
    return nbformat.read(NOTEBOOK, as_version=4)


def _full_text(notebook: nbformat.NotebookNode) -> str:
    return "\n".join(cell.source for cell in notebook.cells)


def _code_text(notebook: nbformat.NotebookNode) -> str:
    return "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")


def test_stage05_notebook_parses_and_has_empty_outputs() -> None:
    notebook = _notebook()
    assert notebook.cells
    for cell in notebook.cells:
        if cell.cell_type == "code":
            ast.parse(cell.source)
            assert cell.execution_count is None
            assert cell.outputs == []


def test_stage05_notebook_control_constants_and_pins() -> None:
    text = _full_text(_notebook())
    assert "Stage 05 - Thesis Synthesis" in text
    assert "RUN_PROJECT_BOOTSTRAP = True" in text
    assert 'PROJECT_BOOTSTRAP_MODE = "github_commit"' in text
    assert 'PROJECT_REPO_URL = "https://github.com/zkc768/lstm-zhang.git"' in text
    assert f'PROJECT_REPO_COMMIT = "{EXPECTED_PROJECT_REPO_COMMIT}"' in text
    assert "RUN_STAGE05 = False" in text
    assert "RUN_STAGE03_DRIVE_SYNC = True" in text
    assert "RUN_STAGE04_DRIVE_SYNC = True" in text
    assert "RUN_V2_1_DRIVE_SYNC = True" in text
    assert "RUN_STAGE05_DRIVE_BACKUP = True" in text
    assert "RUN_ARTIFACT_DISPLAY = False" in text
    assert f'STAGE03_RUN_ID = "{CURRENT_STAGE03_RUN_ID}"' in text
    assert f'STAGE04_RUN_ID = "{CURRENT_STAGE04_RUN_ID}"' in text
    assert f'V2_1_RUN_ID = "{CURRENT_V2_1_RUN_ID}"' in text
    assert 'OFFICIAL_VALIDATION_CONTACT = "read_frozen_artifacts_only"' in text
    assert "NEW_SCORING_EVENTS = 0" in text
    assert "NO_FINAL_MODEL_SELECTED = True" in text
    assert "fill PROJECT_REPO_COMMIT with the Stage 05 full-bundle commit" in text
    assert "assert actual_commit == PROJECT_REPO_COMMIT" in text
    # The Stage 05 run id comes from the runner's output folder, never typed.
    assert "STAGE05_RUN_ID = Path(result.run_dir).name" in text
    assert not any(
        line.strip().startswith('STAGE05_RUN_ID = "') for line in text.splitlines()
    ), "the Stage 05 run id must never be a manually typed constant"


def test_stage05_notebook_runtime_injection_before_asserts() -> None:
    notebook = _notebook()
    code_cells = [cell.source for cell in notebook.cells if cell.cell_type == "code"]
    config_cell = next(
        source for source in code_cells if "stage05_config = yaml.safe_load(handle)" in source
    )
    injections = [
        'stage_inputs["stage03_run_id"] = STAGE03_RUN_ID',
        'stage_inputs["stage03_runtime_run_dir"] = str(STAGE03_OUTPUT_DIR)',
        'stage_inputs["stage04_run_id"] = STAGE04_RUN_ID',
        'stage_inputs["stage04_runtime_run_dir"] = str(STAGE04_OUTPUT_DIR)',
        'stage_inputs["v2_1_run_id"] = V2_1_RUN_ID',
        'stage_inputs["v2_1_runtime_run_dir"] = str(V2_1_OUTPUT_DIR)',
        'stage_outputs["output_dir"] = str(OUTPUT_DIR)',
    ]
    first_assert = config_cell.index("\nassert ")
    for line in injections:
        assert line in config_cell, f"missing runtime injection: {line}"
        assert config_cell.index(line) < first_assert, f"injection after asserts: {line}"
    assert (
        'assert stage05_config["official_validation_contact"] == OFFICIAL_VALIDATION_CONTACT'
        in config_cell
    )
    assert 'assert int(stage05_config["new_scoring_events"]) == NEW_SCORING_EVENTS' in config_cell
    assert 'assert stage05_config["no_final_model_selected"] is NO_FINAL_MODEL_SELECTED' in config_cell


def test_stage05_notebook_upstream_sync_and_preflight() -> None:
    text = _code_text(_notebook())
    assert "require_artifacts(STAGE03_OUTPUT_DIR, required_stage03_artifacts)" in text
    assert "require_artifacts(STAGE04_OUTPUT_DIR, required_stage04_artifacts)" in text
    assert "require_artifacts(V2_1_OUTPUT_DIR, required_v2_1_artifacts)" in text
    assert "def find_unique_drive_child" in text
    assert "expected exactly one Drive item named" in text
    assert "sync_stage_artifacts_from_drive" in text


def test_stage05_notebook_durable_save_with_manifest_refusals() -> None:
    notebook = _notebook()
    code_cells = [cell.source for cell in notebook.cells if cell.cell_type == "code"]
    run_cell_index = next(
        index for index, source in enumerate(code_cells)
        if "result = run_stage(stage05_config)" in source
    )
    save_cell_index = next(
        index for index, source in enumerate(code_cells)
        if "def backup_stage05_results_to_drive" in source
    )
    assert save_cell_index == run_cell_index + 1, (
        "durable Drive result-save cell must immediately follow the run cell"
    )
    save_cell = code_cells[save_cell_index]
    assert (
        "from lst_models.stages.thesis_synthesis import REQUIRED_STAGE05_ARTIFACTS" in save_cell
    ), "the required-output list must be imported, never retyped"
    assert 'int(run_manifest.get("new_scoring_events", -1)) != 0' in save_cell
    assert (
        'run_manifest.get("official_validation_contact") != "read_frozen_artifacts_only"'
        in save_cell
    )
    assert 'run_manifest.get("holdout_test_contact") is not False' in save_cell
    assert 'run_manifest.get("no_final_model_selected") is not True' in save_cell
    assert "drive_backup_manifest.json" in save_cell
    assert '"bytes": None, "self_reference": True' in save_cell
    assert 'print("stage_run_id:", backup_manifest["stage_run_id"])' in save_cell
    assert 'print("drive_path:", backup_manifest["drive_path"])' in save_cell
    assert 'print("drive_folder_id:", backup_manifest["drive_folder_id"])' in save_cell


def test_stage05_notebook_forbidden_active_patterns_absent() -> None:
    notebook = _notebook()
    code_text = _code_text(notebook)
    forbidden_code_patterns = [
        "drive.mount(",
        "train_test_split",
        "from intraday_research",
        "RUN_STAGE05 = True",
        "closed_holdout_test",
        "2017-01-25",
        'split"] == "holdout',
        "datetime.utcnow",
    ]
    for pattern in forbidden_code_patterns:
        assert pattern not in code_text, f"forbidden pattern in code cells: {pattern}"
    forbidden_selection_phrases = [
        "final model",
        "official validation winner",
        "holdout winner",
        "test winner",
        "selected by official validation",
        "chosen threshold",
        "clean test",
        "clean holdout",
    ]
    for phrase in forbidden_selection_phrases:
        assert phrase not in code_text, f"forbidden wording in code cells: {phrase}"
    markdown_text = "\n".join(
        cell.source for cell in notebook.cells if cell.cell_type == "markdown"
    )
    assert "Do not claim a final model" in markdown_text
    assert "no_final_model_selected=true" in markdown_text
    assert "synthesis, not selection" in markdown_text
    assert "Dwork 2015" in markdown_text
    assert "guarded historically-contacted" in markdown_text
    assert "conditional-signal limitation" in markdown_text
    assert "deferred_synthesis_items" in markdown_text
