from __future__ import annotations

import ast
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "notebooks" / "04_diagnostics_ablation_colab.ipynb"

# The two-step exact-commit pin (AGENTS.md section 5) updates this constant
# together with the notebook constant in the same commit.
EXPECTED_PROJECT_REPO_COMMIT = "b901adfa38f6cdf55cf4a480119de37feee87cab"
CURRENT_STAGE00_RUN_ID = "20260610_051705_347450"
CURRENT_STAGE01_RUN_ID = "20260610_075002"
CURRENT_STAGE02_RUN_ID = "20260610_082130_797479"
CURRENT_STAGE03_RUN_ID = "20260610_133305_716174"
SUPERSEDED_STAGE02_RUN_IDS = '["20260609_100637_704705", "20260610_010019_507648"]'


def _notebook() -> nbformat.NotebookNode:
    return nbformat.read(NOTEBOOK, as_version=4)


def _full_text(notebook: nbformat.NotebookNode) -> str:
    return "\n".join(cell.source for cell in notebook.cells)


def _code_text(notebook: nbformat.NotebookNode) -> str:
    return "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")


def test_stage04_notebook_parses_and_has_empty_outputs() -> None:
    notebook = _notebook()
    assert notebook.cells
    for cell in notebook.cells:
        if cell.cell_type == "code":
            ast.parse(cell.source)
            assert cell.execution_count is None
            assert cell.outputs == []


def test_stage04_notebook_control_constants_and_pins() -> None:
    text = _full_text(_notebook())
    assert "Stage 04 - Diagnostics And Train-Inner Ablation" in text
    assert "RUN_PROJECT_BOOTSTRAP = True" in text
    assert 'PROJECT_BOOTSTRAP_MODE = "github_commit"' in text
    assert 'PROJECT_REPO_URL = "https://github.com/zkc768/lstm-zhang.git"' in text
    assert f'PROJECT_REPO_COMMIT = "{EXPECTED_PROJECT_REPO_COMMIT}"' in text
    assert "RUN_STAGE04 = False" in text
    assert "RUN_STAGE00_DRIVE_SYNC = True" in text
    assert "RUN_STAGE01_DRIVE_SYNC = True" in text
    assert "RUN_STAGE02_DRIVE_SYNC = True" in text
    assert "RUN_STAGE03_DRIVE_SYNC = True" in text
    assert "RUN_RAW_DATA_SYNC = True" in text
    assert "RUN_STAGE04_CHECKPOINT_MIRROR = True" in text
    assert "RUN_STAGE04_DRIVE_BACKUP = True" in text
    assert "RUN_ARTIFACT_DISPLAY = False" in text
    assert f'STAGE00_RUN_ID = "{CURRENT_STAGE00_RUN_ID}"' in text
    assert f'STAGE01_RUN_ID = "{CURRENT_STAGE01_RUN_ID}"' in text
    assert f'STAGE02_RUN_ID = "{CURRENT_STAGE02_RUN_ID}"' in text
    assert f'STAGE03_RUN_ID = "{CURRENT_STAGE03_RUN_ID}"' in text
    assert f"SUPERSEDED_STAGE02_RUN_IDS = {SUPERSEDED_STAGE02_RUN_IDS}" in text
    assert "FROZEN_SEEDS = [101, 202]" in text
    assert 'OFFICIAL_VALIDATION_CONTACT = "read_frozen_artifacts_only"' in text
    assert "NEW_VALIDATION_FIT_PREDICT_EVENTS = 0" in text
    assert "fill PROJECT_REPO_COMMIT with the Stage 04 full-bundle commit" in text
    assert "assert actual_commit == PROJECT_REPO_COMMIT" in text
    # The Stage 04 run id comes from the runner's output folder, never typed.
    assert "STAGE04_RUN_ID = Path(result.run_dir).name" in text
    assert not any(
        line.strip().startswith('STAGE04_RUN_ID = "') for line in text.splitlines()
    ), "the Stage 04 run id must never be a manually typed constant"
    # Exact-run resume surface (protocol section 13): empty by default.
    assert 'RESUME_STAGE04_RUN_ID = ""' in text
    assert 'RESUME_STAGE04_CHECKPOINT_DIR = ""' in text
    assert 'stage04_config["resume"] = {' in text
    assert "def fetch_resume_checkpoint_from_drive" in text
    assert "04_ablation_trial_ledger_partial.csv" in text


def test_stage04_notebook_runtime_injection_before_asserts() -> None:
    notebook = _notebook()
    code_cells = [cell.source for cell in notebook.cells if cell.cell_type == "code"]
    config_cell = next(
        source for source in code_cells if "stage04_config = yaml.safe_load(handle)" in source
    )
    injections = [
        'stage_inputs["stage00_run_id"] = STAGE00_RUN_ID',
        'stage_inputs["stage00_runtime_run_dir"] = str(STAGE00_OUTPUT_DIR)',
        'stage_inputs["stage01_run_id"] = STAGE01_RUN_ID',
        'stage_inputs["stage01_runtime_run_dir"] = str(STAGE01_OUTPUT_DIR)',
        'stage_inputs["stage02_run_id"] = STAGE02_RUN_ID',
        'stage_inputs["stage02_runtime_run_dir"] = str(STAGE02_OUTPUT_DIR)',
        'stage_inputs["stage03_run_id"] = STAGE03_RUN_ID',
        'stage_inputs["stage03_runtime_run_dir"] = str(STAGE03_OUTPUT_DIR)',
        'stage_inputs["superseded_stage02_run_ids"] = SUPERSEDED_STAGE02_RUN_IDS',
        'stage_inputs["raw_data_dir"] = str(RAW_DATA_DIR)',
        'stage_outputs["output_dir"] = str(OUTPUT_DIR)',
        'stage_checkpointing["checkpoint_dir"] = str(CHECKPOINT_ROOT)',
    ]
    first_assert = config_cell.index("\nassert ")
    for line in injections:
        assert line in config_cell, f"missing runtime injection: {line}"
        assert config_cell.index(line) < first_assert, f"injection after asserts: {line}"
    assert (
        'assert stage04_config["official_validation_contact"] == OFFICIAL_VALIDATION_CONTACT'
        in config_cell
    )
    assert (
        'assert int(stage04_config["new_validation_fit_predict_events"]) == '
        "NEW_VALIDATION_FIT_PREDICT_EVENTS" in config_cell
    )
    assert 'assert diagnostics_block["calibration"]["no_calibrator_fitting"] is True' in config_cell
    assert 'assert diagnostics_block["selective"]["no_operating_point"] is True' in config_cell
    assert "planned_rows = len(ablation_block" in config_cell
    assert 'assert int(ablation_block["reference_rows"]["expected_row_count"]) == 6' in config_cell


def test_stage04_notebook_upstream_sync_and_preflight() -> None:
    text = _code_text(_notebook())
    assert "require_artifacts(STAGE00_OUTPUT_DIR, required_stage00_artifacts)" in text
    assert "require_artifacts(STAGE01_OUTPUT_DIR, required_stage01_artifacts)" in text
    assert "require_artifacts(STAGE02_OUTPUT_DIR, required_stage02_artifacts)" in text
    assert "require_artifacts(STAGE03_OUTPUT_DIR, required_stage03_artifacts)" in text
    assert "def find_unique_drive_child" in text
    assert "expected exactly one Drive item named" in text
    assert "sync_raw_data_from_drive" in text
    # Pre-flight feasibility before any control fit (protocol section 13).
    assert "MAX_ABLATION_MATERIALIZED_BYTES" in text
    assert "window_size * n_features * 4" in text
    assert "BEFORE any fit" in text
    assert "zero control fits have occurred" in text


def test_stage04_notebook_durable_save_with_manifest_refusals() -> None:
    notebook = _notebook()
    code_cells = [cell.source for cell in notebook.cells if cell.cell_type == "code"]
    run_cell_index = next(
        index for index, source in enumerate(code_cells)
        if "result = run_stage(stage04_config)" in source
    )
    save_cell_index = next(
        index for index, source in enumerate(code_cells)
        if "def backup_stage04_results_to_drive" in source
    )
    assert save_cell_index == run_cell_index + 1, (
        "durable Drive result-save cell must immediately follow the run cell"
    )
    save_cell = code_cells[save_cell_index]
    assert (
        "from lst_models.stages.diagnostics_ablation import REQUIRED_STAGE04_ARTIFACTS"
        in save_cell
    ), "the required-output list must be imported, never retyped"
    assert 'int(run_manifest.get("new_validation_fit_predict_events", -1)) != 0' in save_cell
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


def test_stage04_notebook_checkpoint_mirror_contract() -> None:
    text = _code_text(_notebook())
    assert (
        'CHECKPOINT_ROOT = Path("/content/lst_models_checkpoints/04_diagnostics_ablation")'
        in text
    )
    assert (
        'CHECKPOINT_DRIVE_BASE_PARTS = ["lst_models", "checkpoints", "04_diagnostics_ablation"]'
        in text
    )
    assert "def start_stage04_checkpoint_mirror" in text
    assert "def stop_stage04_checkpoint_mirror" in text
    assert "mirror_stage04_checkpoints_once" in text
    assert "STAGE04_MIRROR_STABLE_SECONDS" in text
    assert "finally:" in text
    assert "stop_stage04_checkpoint_mirror(mirror_thread)" in text


def test_stage04_notebook_forbidden_active_patterns_absent() -> None:
    notebook = _notebook()
    code_text = _code_text(notebook)
    forbidden_code_patterns = [
        "drive.mount(",
        "train_test_split",
        "from intraday_research",
        "RUN_STAGE04 = True",
        "closed_holdout_test",
        "2017-01-25",
        'split"] == "holdout',
        "datetime.utcnow",
        # measure-only: calibrator-fitting tokens are forbidden (protocol 14)
        "CalibratedClassifierCV",
        "IsotonicRegression",
        "temperature_scal",
        "Platt",
        "sklearn.calibration",
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
    ]
    for phrase in forbidden_selection_phrases:
        assert phrase not in code_text, f"forbidden wording in code cells: {phrase}"
    markdown_text = "\n".join(
        cell.source for cell in notebook.cells if cell.cell_type == "markdown"
    )
    assert "Do not claim a final model" in markdown_text
    assert "no_final_model_selected=true" in markdown_text
    assert "Zadrozny 2004" in markdown_text
    assert "diagnosis, not selection" in markdown_text
    assert "zero new validation fit-predict events" in markdown_text
