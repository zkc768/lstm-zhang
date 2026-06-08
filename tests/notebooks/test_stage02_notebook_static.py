from __future__ import annotations

import ast
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "notebooks" / "02_model_hpo_train_inner_colab.ipynb"


def test_stage02_notebook_parses_and_has_empty_outputs() -> None:
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    assert notebook.cells
    for cell in notebook.cells:
        if cell.cell_type == "code":
            ast.parse(cell.source)
            assert cell.execution_count is None
            assert cell.outputs == []


def test_stage02_notebook_is_single_stage02_entrypoint() -> None:
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    text = "\n".join(cell.source for cell in notebook.cells)
    assert "Stage 02 - Model HPO Train-Inner" in text
    assert "Stage 02 is train-inner HPO only" in text
    assert "RUN_PROJECT_BOOTSTRAP = True" in text
    assert 'PROJECT_BOOTSTRAP_MODE = "github_commit"' in text
    assert 'PROJECT_REPO_URL = "https://github.com/zkc768/lstm-zhang.git"' in text
    assert 'PROJECT_REPO_COMMIT = "0ed7f4446120271d154acab29524fa56068e9330"' in text
    assert "RUN_STAGE01_DRIVE_SYNC = True" in text
    assert "RUN_STAGE02 = False" in text
    assert "RUN_ARTIFACT_DISPLAY = False" in text
    assert 'STAGE01_RUN_ID = "20260608_180233"' in text
    assert 'STAGE01_DRIVE_PATH_PARTS = ["lst_models", "results", "01_feature_window_search", STAGE01_RUN_ID]' in text
    assert "CORE_HPO_FAMILIES" in text
    assert "model_hpo_train_inner.py" in text
    assert "from lst_models.stages.model_hpo_train_inner import run_stage" in text
    assert "run_dir = Path(result.output_dir)" in text
    assert 'summary_path = run_dir / "02_model_hpo_train_inner_summary.csv"' in text


def test_stage02_notebook_forbidden_active_patterns_absent() -> None:
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    code_text = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")
    forbidden = [
        "drive.mount(",
        "train_test_split",
        "from intraday_research",
        "RUN_STAGE02 = True",
        "RUN_DOWNLOAD = True",
    ]
    for pattern in forbidden:
        assert pattern not in code_text
