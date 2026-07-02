from __future__ import annotations

import ast
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "notebooks" / "v2_band_horizon_sensitivity_colab.ipynb"

CURRENT_STAGE00_RUN_ID = "20260610_051705_347450"
CURRENT_STAGE01_RUN_ID = "20260610_075002"
CURRENT_STAGE02_RUN_ID = "20260610_082130_797479"


def _notebook() -> nbformat.NotebookNode:
    return nbformat.read(NOTEBOOK, as_version=4)


def _full_text(notebook: nbformat.NotebookNode) -> str:
    return "\n".join(cell.source for cell in notebook.cells)


def _code_text(notebook: nbformat.NotebookNode) -> str:
    return "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")


def _code_cells(notebook: nbformat.NotebookNode) -> list[str]:
    return [cell.source for cell in notebook.cells if cell.cell_type == "code"]


def test_bhs_notebook_parses_and_has_empty_outputs() -> None:
    notebook = _notebook()
    assert notebook.cells
    for cell in notebook.cells:
        if cell.cell_type == "code":
            ast.parse(cell.source)
            assert cell.execution_count is None
            assert cell.outputs == []


def test_bhs_notebook_control_constants_and_pins() -> None:
    text = _full_text(_notebook())
    assert "V2 Band/Horizon Sensitivity Scan" in text
    assert "RUN_PROJECT_BOOTSTRAP = True" in text
    assert 'PROJECT_BOOTSTRAP_MODE = "github_commit"' in text
    assert 'PROJECT_REPO_URL = "https://github.com/zkc768/lstm-zhang.git"' in text
    # Two-step exact-commit pin: the placeholder must be replaced with the
    # full-bundle commit before the notebook is executed; the bootstrap cell
    # fails loudly while the placeholder is present.
    assert "PROJECT_REPO_COMMIT = " in text
    assert "full-bundle commit" in text
    assert 'if "REPLACE_WITH" in PROJECT_REPO_COMMIT:' in text
    assert "actual_commit == PROJECT_REPO_COMMIT" in text
    assert "RUN_BHS = False" in text
    assert "RUN_STAGE00_DRIVE_SYNC = True" in text
    assert "RUN_STAGE01_DRIVE_SYNC = True" in text
    assert "RUN_STAGE02_DRIVE_SYNC = True" in text
    assert "RUN_RAW_DATA_SYNC = True" in text
    assert "RUN_BHS_DRIVE_BACKUP = True" in text
    assert "RUN_ARTIFACT_DISPLAY = False" in text
    assert f'STAGE00_RUN_ID = "{CURRENT_STAGE00_RUN_ID}"' in text
    assert f'STAGE01_RUN_ID = "{CURRENT_STAGE01_RUN_ID}"' in text
    assert f'STAGE02_RUN_ID = "{CURRENT_STAGE02_RUN_ID}"' in text
    assert "FROZEN_SEEDS = [101, 202]" in text
    assert (
        'SCAN_CELL_IDS = ["h09_bps2p0", "h09_bps3p0", "h09_bps4p0", '
        '"h06_bps3p0", "h12_bps3p0"]' in text
    )
    assert 'FROZEN_CELL_ID = "h09_bps3p0"' in text
    assert "FROZEN_HORIZON_K = 9" in text
    assert "FROZEN_BAND_BPS = 3.0" in text
    assert 'TRAIN_END_EXCLUSIVE = "2013-09-16"' in text


def test_bhs_notebook_uses_run_stage_and_validates_config_first() -> None:
    code = _code_text(_notebook())
    assert "from lst_models.stages.band_horizon_sensitivity import run_stage" in code
    assert "result = run_stage(bhs_config)" in code
    assert "from lst_models.stages.band_horizon_sensitivity import _validate_config" in code
    assert "_validate_config(bhs_config)" in code
    assert code.index("_validate_config(bhs_config)") < code.index(
        "service = get_drive_service_for_input_sync()"
    )


def test_bhs_notebook_runtime_path_injection() -> None:
    code = _code_text(_notebook())
    assert 'stage_inputs["stage00_runtime_run_dir"] = str(STAGE00_OUTPUT_DIR)' in code
    assert 'stage_inputs["stage01_runtime_run_dir"] = str(STAGE01_OUTPUT_DIR)' in code
    assert 'stage_inputs["stage02_runtime_run_dir"] = str(STAGE02_OUTPUT_DIR)' in code
    assert 'stage_inputs["raw_data_dir"] = str(RAW_DATA_DIR)' in code
    assert 'stage_outputs["output_dir"] = str(OUTPUT_DIR)' in code
    assert 'stage_outputs["run_id"] = BHS_RUN_ID' in code
    assert 'stage_checkpointing["checkpoint_dir"] = str(CHECKPOINT_ROOT)' in code
    assert 'Path(stage_inputs["raw_data_dir"]) == RAW_DATA_DIR' in code
    assert 'Path(stage_outputs["output_dir"]) == OUTPUT_DIR' in code


def test_bhs_notebook_input_sync_uses_exact_run_folders() -> None:
    code = _code_text(_notebook())
    assert "require_artifacts(STAGE00_OUTPUT_DIR, required_stage00_artifacts)" in code
    assert "require_artifacts(STAGE01_OUTPUT_DIR, required_stage01_artifacts)" in code
    assert "require_artifacts(STAGE02_OUTPUT_DIR, required_stage02_artifacts)" in code
    assert "STAGE00_DRIVE_PATH_PARTS" in code
    assert "STAGE01_DRIVE_PATH_PARTS" in code
    assert "STAGE02_DRIVE_PATH_PARTS" in code
    assert "sync_raw_data_from_drive" in code


def test_bhs_notebook_drive_backup_immediately_after_run_cell() -> None:
    notebook = _notebook()
    code_cells = _code_cells(notebook)
    run_cell_index = next(
        index for index, source in enumerate(code_cells)
        if "result = run_stage(bhs_config)" in source
    )
    backup_cell_index = next(
        index for index, source in enumerate(code_cells)
        if "REQUIRED_BHS_ARTIFACTS" in source and "RUN_BHS_DRIVE_BACKUP and RUN_BHS" in source
    )
    assert backup_cell_index == run_cell_index + 1
    backup_cell = code_cells[backup_cell_index]
    assert (
        "from lst_models.stages.band_horizon_sensitivity import REQUIRED_BHS_ARTIFACTS"
        in backup_cell
    )
    assert "missing_required_artifacts" in backup_cell
    assert "FileNotFoundError" in backup_cell
    assert "drive_backup_manifest.json" in backup_cell
    assert '"bytes": None' in backup_cell
    assert '"self_reference": True' in backup_cell
    assert 'print("stage_run_id:", BHS_RUN_ID)' in backup_cell
    assert 'print("drive_path:"' in backup_cell
    assert 'print("drive_folder_id:", drive_folder_id)' in backup_cell
    assert 'local_run_dir.glob("bhs_trials_*.csv")' in backup_cell


def test_bhs_notebook_forbidden_active_patterns_absent() -> None:
    notebook = _notebook()
    code_text = _code_text(notebook)
    forbidden_code_patterns = [
        "drive.mount(",
        "train_test_split",
        "from intraday_research",
        "RUN_BHS = True",
        "closed_holdout_test",
        "datetime.utcnow",
        "validation_start",
    ]
    for pattern in forbidden_code_patterns:
        assert pattern not in code_text, f"forbidden pattern in code cells: {pattern}"
    markdown_text = "\n".join(
        cell.source for cell in notebook.cells if cell.cell_type == "markdown"
    )
    normalized_markdown = " ".join(markdown_text.split())
    assert "FORBIDDEN wording" in normalized_markdown
    assert "ZERO contact" in normalized_markdown
    assert "TRAIN segment only" in normalized_markdown
    assert "train-inner domain evidence only; no cell selected" in normalized_markdown
    assert "No cell is preferred" in normalized_markdown
    assert "never ranked" in normalized_markdown
    assert "no alternative (band, horizon) is recommended" in normalized_markdown


def test_bhs_notebook_declares_scan_scope_asserts() -> None:
    code = _code_text(_notebook())
    assert 'bhs_config["train_domain_only"] is TRAIN_DOMAIN_ONLY' in code
    assert 'bhs_config["holdout_test_contact"] is HOLDOUT_TEST_CONTACT' in code
    assert 'bhs_config["sensitivity_scan_no_cell_selected"] is True' in code
    assert (
        '[cell["cell_id"] for cell in bhs_config["label_scan"]["cells"]] == SCAN_CELL_IDS'
        in code
    )
    assert 'bhs_config["train_inner"]["seeds"] == FROZEN_SEEDS' in code
    assert 'bhs_config["reading_rules"]["cells_are_never_ranked"] is True' in code
    assert 'bhs_config["reading_rules"]["no_alternative_cell_recommended"] is True' in code
