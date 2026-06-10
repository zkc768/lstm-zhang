from __future__ import annotations

import ast
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "notebooks" / "03_frozen_validation_readout_colab.ipynb"

# Pre-pin placeholders: the publish task (two-step exact-commit pin) replaces
# both placeholders and these expected constants in the same commit.
EXPECTED_PROJECT_REPO_COMMIT = "<STAGE03_FULL_BUNDLE_COMMIT>"
EXPECTED_STAGE02_RUN_ID = "<NEW_STAGE02_RUN_ID>"
CURRENT_STAGE00_RUN_ID = "20260610_051705_347450"
CURRENT_STAGE01_RUN_ID = "20260610_075002"
SUPERSEDED_STAGE02_RUN_IDS = '["20260609_100637_704705", "20260610_010019_507648"]'


def _notebook() -> nbformat.NotebookNode:
    return nbformat.read(NOTEBOOK, as_version=4)


def _full_text(notebook: nbformat.NotebookNode) -> str:
    return "\n".join(cell.source for cell in notebook.cells)


def _code_text(notebook: nbformat.NotebookNode) -> str:
    return "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")


def test_stage03_notebook_parses_and_has_empty_outputs() -> None:
    notebook = _notebook()
    assert notebook.cells
    for cell in notebook.cells:
        if cell.cell_type == "code":
            ast.parse(cell.source)
            assert cell.execution_count is None
            assert cell.outputs == []


def test_stage03_notebook_control_constants_and_pins() -> None:
    text = _full_text(_notebook())
    assert "Stage 03 - Frozen Official-Validation Readout" in text
    assert "RUN_PROJECT_BOOTSTRAP = True" in text
    assert 'PROJECT_BOOTSTRAP_MODE = "github_commit"' in text
    assert 'PROJECT_REPO_URL = "https://github.com/zkc768/lstm-zhang.git"' in text
    assert f'PROJECT_REPO_COMMIT = "{EXPECTED_PROJECT_REPO_COMMIT}"' in text
    assert "RUN_STAGE03 = False" in text
    assert "RUN_STAGE00_DRIVE_SYNC = True" in text
    assert "RUN_STAGE01_DRIVE_SYNC = True" in text
    assert "RUN_STAGE02_DRIVE_SYNC = True" in text
    assert "RUN_RAW_DATA_SYNC = True" in text
    assert "RUN_STAGE03_CHECKPOINT_MIRROR = True" in text
    assert "RUN_STAGE03_DRIVE_BACKUP = True" in text
    assert "RUN_ARTIFACT_DISPLAY = False" in text
    assert f'STAGE00_RUN_ID = "{CURRENT_STAGE00_RUN_ID}"' in text
    assert f'STAGE01_RUN_ID = "{CURRENT_STAGE01_RUN_ID}"' in text
    assert f'STAGE02_RUN_ID = "{EXPECTED_STAGE02_RUN_ID}"' in text
    assert f"SUPERSEDED_STAGE02_RUN_IDS = {SUPERSEDED_STAGE02_RUN_IDS}" in text
    assert "FROZEN_SEEDS = [101, 202]" in text
    assert 'fill STAGE02_RUN_ID with the superseding Stage 02 run id' in text
    assert 'fill PROJECT_REPO_COMMIT with the Stage 03 full-bundle commit' in text
    assert "assert actual_commit == PROJECT_REPO_COMMIT" in text
    # The run id comes from the runner's output folder, never typed manually.
    assert "STAGE03_RUN_ID = Path(result.output_dir).name" in text
    assert not any(
        line.strip().startswith('STAGE03_RUN_ID = "') for line in text.splitlines()
    ), "the Stage 03 run id must never be a manually typed constant"
    # Exact-run resume surface (protocol section 11): empty by default.
    assert 'RESUME_STAGE03_RUN_ID = ""' in text
    assert 'RESUME_STAGE03_CHECKPOINT_DIR = ""' in text
    assert 'stage03_config["resume"] = {' in text
    assert "def fetch_resume_checkpoint_from_drive" in text
    assert "RESUME_REQUIRED_CHECKPOINT_FILES" in text
    assert "03_ledger_state_partial.json" in text


def test_stage03_notebook_runtime_injection_before_asserts() -> None:
    notebook = _notebook()
    code_cells = [cell.source for cell in notebook.cells if cell.cell_type == "code"]
    config_cell = next(
        source for source in code_cells if "stage03_config = yaml.safe_load(handle)" in source
    )
    injections = [
        'stage_inputs["stage00_run_id"] = STAGE00_RUN_ID',
        'stage_inputs["stage00_runtime_run_dir"] = str(STAGE00_OUTPUT_DIR)',
        'stage_inputs["stage00_drive_path_parts"] = STAGE00_DRIVE_PATH_PARTS',
        'stage_inputs["stage01_run_id"] = STAGE01_RUN_ID',
        'stage_inputs["stage01_runtime_run_dir"] = str(STAGE01_OUTPUT_DIR)',
        'stage_inputs["stage01_drive_path_parts"] = STAGE01_DRIVE_PATH_PARTS',
        'stage_inputs["stage02_run_id"] = STAGE02_RUN_ID',
        'stage_inputs["stage02_runtime_run_dir"] = str(STAGE02_OUTPUT_DIR)',
        'stage_inputs["stage02_drive_path_parts"] = STAGE02_DRIVE_PATH_PARTS',
        'stage_inputs["superseded_stage02_run_ids"] = SUPERSEDED_STAGE02_RUN_IDS',
        'stage_inputs["raw_data_dir"] = str(RAW_DATA_DIR)',
        'stage_outputs["output_dir"] = str(OUTPUT_DIR)',
        'stage_checkpointing["checkpoint_dir"] = str(CHECKPOINT_ROOT)',
    ]
    first_assert = config_cell.index("\nassert ")
    for line in injections:
        assert line in config_cell, f"missing runtime injection: {line}"
        assert config_cell.index(line) < first_assert, f"injection after asserts: {line}"
    assert 'assert stage03_config["readout"]["seeds"] == FROZEN_SEEDS' in config_cell
    assert (
        'assert stage03_config["readout"]["score_each_seed_candidate_exactly_once"] is True'
        in config_cell
    )
    assert 'assert criteria["minimum_positive_ticker_count"] == 3' in config_cell
    assert (
        'assert fallback_policy["after_first_scoring_event"] == "never_activate"' in config_cell
    )


def test_stage03_notebook_upstream_sync_and_preflight() -> None:
    text = _code_text(_notebook())
    assert "require_artifacts(STAGE00_OUTPUT_DIR, required_stage00_artifacts)" in text
    assert "require_artifacts(STAGE01_OUTPUT_DIR, required_stage01_artifacts)" in text
    assert "require_artifacts(STAGE02_OUTPUT_DIR, required_stage02_artifacts)" in text
    assert "def find_unique_drive_child" in text
    assert "expected exactly one Drive item named" in text
    assert "sync_raw_data_from_drive" in text
    # Pre-flight feasibility before any scoring event (protocol section 5).
    assert "max_materialized_train_bytes" in text
    assert "estimate_candidate_bytes" in text
    assert "window_size * n_features * 4" in text
    assert "combined_bytes" in text
    assert "BEFORE any scoring event" in text
    assert "zero scoring events have occurred" in text


def test_stage03_notebook_durable_save_with_manifest_refusals() -> None:
    notebook = _notebook()
    code_cells = [cell.source for cell in notebook.cells if cell.cell_type == "code"]
    run_cell_index = next(
        index for index, source in enumerate(code_cells) if "result = run_stage(stage03_config)" in source
    )
    save_cell_index = next(
        index
        for index, source in enumerate(code_cells)
        if "def backup_stage03_results_to_drive" in source
    )
    assert save_cell_index == run_cell_index + 1, (
        "durable Drive result-save cell must immediately follow the run cell"
    )
    save_cell = code_cells[save_cell_index]
    assert 'run_manifest.get("official_validation_for_selection") is not False' in save_cell
    assert 'run_manifest.get("holdout_test_contact") is not False' in save_cell
    assert 'run_manifest.get("no_final_model_selected") is not True' in save_cell
    assert "drive_backup_manifest.json" in save_cell
    assert '"bytes": None, "self_reference": True' in save_cell
    assert 'print("stage_run_id:", backup_manifest["stage_run_id"])' in save_cell
    assert 'print("drive_path:", backup_manifest["drive_path"])' in save_cell
    assert 'print("drive_folder_id:", backup_manifest["drive_folder_id"])' in save_cell
    assert "REQUIRED_STAGE03_OUTPUTS" in save_cell
    text = _full_text(notebook)
    assert "03_validation_predictions.csv" in text
    assert "03_decision_record.json" in text


def test_stage03_notebook_checkpoint_mirror_contract() -> None:
    text = _code_text(_notebook())
    assert 'CHECKPOINT_ROOT = Path("/content/lst_models_checkpoints/03_frozen_validation_readout")' in text
    assert 'CHECKPOINT_DRIVE_BASE_PARTS = ["lst_models", "checkpoints", "03_frozen_validation_readout"]' in text
    assert "def start_stage03_checkpoint_mirror" in text
    assert "def stop_stage03_checkpoint_mirror" in text
    assert "mirror_stage03_checkpoints_once" in text
    assert "STAGE03_MIRROR_STABLE_SECONDS" in text
    # The mirror must stop (and final-sweep) even when run_stage raises.
    assert "finally:" in text
    assert "stop_stage03_checkpoint_mirror(mirror_thread)" in text


def test_stage03_notebook_forbidden_active_patterns_absent() -> None:
    notebook = _notebook()
    code_text = _code_text(notebook)
    forbidden_code_patterns = [
        "drive.mount(",
        "train_test_split",
        "from intraday_research",
        "RUN_STAGE03 = True",
        "RUN_DOWNLOAD = True",
        "closed_holdout_test",
        "2017-01-25",
        'split"] == "holdout',
        "datetime.utcnow",
    ]
    for pattern in forbidden_code_patterns:
        assert pattern not in code_text, f"forbidden pattern in code cells: {pattern}"
    # Selection-on-validation language must not appear in code cells.
    forbidden_selection_phrases = [
        "final model",
        "official validation winner",
        "holdout winner",
        "test winner",
        "selected by official validation",
        "chosen threshold",
    ]
    for phrase in forbidden_selection_phrases:
        assert phrase not in code_text, f"forbidden wording in code cells: {phrase}"
    # The interpretation guard must exist in markdown.
    markdown_text = "\n".join(
        cell.source for cell in notebook.cells if cell.cell_type == "markdown"
    )
    assert "Do not claim a final model" in markdown_text
    assert "no_final_model_selected=true" in markdown_text
    assert "Zadrozny 2004" in markdown_text
