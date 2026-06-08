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
    assert 'PROJECT_REPO_COMMIT = "12063a19a8c32e1d97fa552830f7c56388eb02da"' in text
    assert "PROJECT_DRIVE_BUNDLE_FILE_ID = \"\"" in text
    assert "RUN_STAGE00 = False" in text
    assert "RUN_DOWNLOAD = False" in text
    assert "git\", \"clone\"" in text
    assert "git\", \"checkout\"" in text
    assert "download_and_extract_project_zip_from_drive" in text


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
