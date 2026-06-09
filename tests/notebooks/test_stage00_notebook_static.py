from __future__ import annotations

import ast
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "notebooks" / "00_data_split_label_freeze_colab.ipynb"


def test_stage00_notebook_parses_and_has_empty_outputs() -> None:
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    assert notebook.cells
    for cell in notebook.cells:
        if cell.cell_type == "code":
            ast.parse(cell.source)
            assert cell.execution_count is None
            assert cell.outputs == []


def test_stage00_notebook_is_single_stage00_entrypoint() -> None:
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    text = "\n".join(cell.source for cell in notebook.cells)
    assert "Stage 00 - Data Split Label Freeze" in text
    assert "endpoint_cumulative_return" in text
    assert "RUN_PROJECT_BOOTSTRAP = True" in text
    assert 'PROJECT_BOOTSTRAP_MODE = "github_commit"' in text
    assert 'PROJECT_REPO_URL = "https://github.com/zkc768/lstm-zhang.git"' in text
    assert 'PROJECT_REPO_COMMIT = "4d2aeeb6afd4aa4653d3f6db8228ab0b04e55c02"' in text
    assert "PROJECT_DRIVE_BUNDLE_FILE_ID = \"\"" in text
    assert "RUN_STAGE00 = False" in text
    assert "RUN_DOWNLOAD = False" in text
    assert "RUN_STAGE00_DRIVE_BACKUP = True" in text
    assert 'STAGE00_DRIVE_RESULT_PATH_PARTS = ["lst_models", "results", "00_data_split_label_freeze"]' in text
    assert "git\", \"clone\"" in text
    assert "git\", \"checkout\"" in text
    assert "clear_project_import_cache" in text
    assert "importlib.invalidate_caches()" in text
    assert "download_and_extract_project_zip_from_drive" in text
    assert 'stage_config["provenance"]' in text
    assert '"repo_url": PROJECT_REPO_URL' in text
    assert '"git_commit": PROJECT_REPO_COMMIT' in text
    assert "Stage 00 Drive Result Backup" in text
    assert "backup_stage00_results_to_drive" in text
    assert "drive_backup_manifest.json" in text
    assert 'print("stage_run_id:", backup_manifest["stage_run_id"])' in text
    assert 'print("drive_path:", backup_manifest["drive_path"])' in text
    assert 'print("drive_folder_id:", backup_manifest["drive_folder_id"])' in text


def test_stage00_drive_backup_cell_follows_run_stage_cell() -> None:
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    code_cells = [cell.source for cell in notebook.cells if cell.cell_type == "code"]
    run_cell_index = next(
        index for index, source in enumerate(code_cells) if "result = run_stage(stage_config)" in source
    )
    backup_cell_index = next(
        index for index, source in enumerate(code_cells) if "backup_stage00_results_to_drive" in source
    )
    assert backup_cell_index == run_cell_index + 1


def test_stage00_notebook_forbidden_active_patterns_absent() -> None:
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    code_text = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")
    forbidden = [
        "drive.mount(",
        "train_test_split",
        "from intraday_research",
        "baseline_helpers",
    ]
    for pattern in forbidden:
        assert pattern not in code_text
