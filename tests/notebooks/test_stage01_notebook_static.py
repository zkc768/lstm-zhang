from __future__ import annotations

import ast
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "notebooks" / "01_feature_window_search_colab.ipynb"


def test_stage01_notebook_parses_and_has_empty_outputs() -> None:
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    assert notebook.cells
    for cell in notebook.cells:
        if cell.cell_type == "code":
            ast.parse(cell.source)
            assert cell.execution_count is None
            assert cell.outputs == []


def test_stage01_notebook_is_single_stage01_entrypoint() -> None:
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    text = "\n".join(cell.source for cell in notebook.cells)
    assert "Stage 01 - Feature Window Search" in text
    assert "Stage 01 does not determine the final" in text
    assert "model" in text
    assert "RUN_PROJECT_BOOTSTRAP = True" in text
    assert 'PROJECT_BOOTSTRAP_MODE = "github_commit"' in text
    assert 'PROJECT_REPO_URL = "https://github.com/zkc768/lstm-zhang.git"' in text
    assert 'PROJECT_REPO_COMMIT = "12063a19a8c32e1d97fa552830f7c56388eb02da"' in text
    assert "PROJECT_DRIVE_BUNDLE_FILE_ID = \"\"" in text
    assert "RUN_STAGE00_DRIVE_SYNC = True" in text
    assert "RUN_STAGE01 = False" in text
    assert "RUN_ARTIFACT_DISPLAY = False" in text
    assert 'STAGE00_RUN_ID = "20260608_164408"' in text
    assert 'STAGE00_DRIVE_PATH_PARTS = ["lst_models", "results", "00_data_split_label_freeze", STAGE00_RUN_ID]' in text
    assert "EXPECTED_WINDOWS = [10, 20, 30]" in text
    assert "STAGE02_RECOMMENDED_FAMILIES" in text
    assert "simple_gru" in text
    assert "shallow_lstm" in text
    assert "git\", \"clone\"" in text
    assert "git\", \"checkout\"" in text
    assert "src\" / \"lst_models\" / \"stages\" / \"feature_window_search.py" in text
    assert "sync_stage00_artifacts_from_drive" in text
    assert "resolve_drive_folder" in text
    assert "from lst_models.artifacts import require_artifacts" in text


def test_stage01_notebook_forbidden_active_patterns_absent() -> None:
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    code_text = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")
    forbidden = [
        "drive.mount(",
        "train_test_split",
        "from intraday_research",
        "baseline_helpers",
        "RUN_DOWNLOAD = True",
    ]
    for pattern in forbidden:
        assert pattern not in code_text


def test_stage01_notebook_guarded_stage_import() -> None:
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    code_text = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")
    assert "from lst_models.stages.feature_window_search import run_stage" in code_text
    assert "if RUN_STAGE01:" in code_text
    assert "RUN_STAGE00_DRIVE_SYNC" in code_text
    assert "stage00_runtime_run_dir" in code_text
    assert "stage00_drive_path_parts" in code_text
    assert "no_final_model_selected" in code_text
    assert "holdout_test_contact" in code_text
