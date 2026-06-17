from __future__ import annotations

import ast
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "notebooks" / "v2_1_guarded_walkforward_readout_colab.ipynb"

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


def test_v2_1_notebook_parses_and_has_empty_outputs() -> None:
    notebook = _notebook()
    assert notebook.cells
    for cell in notebook.cells:
        if cell.cell_type == "code":
            ast.parse(cell.source)
            assert cell.execution_count is None
            assert cell.outputs == []


def test_v2_1_notebook_control_constants_and_pins() -> None:
    text = _full_text(_notebook())
    assert "Guarded, Historically-Contacted Walk-Forward Readout" in text
    assert "RUN_PROJECT_BOOTSTRAP = True" in text
    assert 'PROJECT_BOOTSTRAP_MODE = "github_commit"' in text
    assert 'PROJECT_REPO_URL = "https://github.com/zkc768/lstm-zhang.git"' in text
    assert "RUN_V2_1 = False" in text
    assert "RUN_UPSTREAM_DRIVE_SYNC = True" in text
    assert "RUN_RAW_DATA_SYNC = True" in text
    assert "RUN_DRIVE_BACKUP = True" in text
    assert "RUN_ARTIFACT_DISPLAY = False" in text
    assert f'STAGE00_RUN_ID = "{CURRENT_STAGE00_RUN_ID}"' in text
    assert f'STAGE01_RUN_ID = "{CURRENT_STAGE01_RUN_ID}"' in text
    assert f'STAGE02_RUN_ID = "{CURRENT_STAGE02_RUN_ID}"' in text
    assert f'STAGE03_RUN_ID = "{CURRENT_STAGE03_RUN_ID}"' in text
    assert f"SUPERSEDED_STAGE02_RUN_IDS = {SUPERSEDED_STAGE02_RUN_IDS}" in text
    assert "FROZEN_SEEDS = [101, 202]" in text


def test_v2_1_notebook_uses_run_stage() -> None:
    code = _code_text(_notebook())
    assert "from lst_models.stages.guarded_walkforward_readout import run_stage" in code
    assert "result = run_stage(v2_1_config)" in code
    assert "result.output_dir" in code
    assert "result.decision_record" in code
    assert "result.comparison_table" in code


def test_v2_1_notebook_stage03_sync() -> None:
    code = _code_text(_notebook())
    assert "STAGE03_OUTPUT_DIR" in code
    assert "STAGE03_DRIVE_PATH_PARTS" in code
    assert "required_s03" in code
    assert "require_artifacts(STAGE03_OUTPUT_DIR, required_s03)" in code


def test_v2_1_notebook_config_contract_check() -> None:
    code = _code_text(_notebook())
    assert 'v2_1_config["holdout_test_contact"] is True' in code
    assert 'v2_1_config["holdout_contact_tier"] == "guarded_historically_contacted"' in code
    assert 'v2_1_config["clean_test_claim"] is False' in code
    assert 'v2_1_config["no_final_model_selected"] is True' in code
    assert '"clean test" in v2_1_config["forbidden"]["wording"]' in code


def test_v2_1_notebook_drive_backup_guards() -> None:
    code = _code_text(_notebook())
    assert 'holdout_contact_tier' in code
    assert 'clean_test_claim' in code
    assert "drive_backup_manifest.json" in code
    assert "V2_1_DRIVE_RESULT_PATH_PARTS" in code


def test_v2_1_notebook_validates_before_drive_or_raw_sync() -> None:
    code = _code_text(_notebook())
    assert "from lst_models.stages.guarded_walkforward_readout import _validate_config" in code
    assert "_validate_config(v2_1_config)" in code
    assert code.index("_validate_config(v2_1_config)") < code.index("service = get_drive_service()")


def test_v2_1_notebook_forbidden_active_patterns_absent() -> None:
    notebook = _notebook()
    code_text = _code_text(notebook)
    forbidden_code_patterns = [
        "drive.mount(",
        "train_test_split",
        "from intraday_research",
        "RUN_V2_1 = True",
        "closed_holdout_test",
        "datetime.utcnow",
    ]
    for pattern in forbidden_code_patterns:
        assert pattern not in code_text, f"forbidden pattern in code cells: {pattern}"
    forbidden_wording = [
        "clean test",
        "clean holdout",
        "untouched test",
        "untouched holdout",
        "final evidence",
        "out-of-sample proof",
    ]
    for phrase in forbidden_wording:
        for cell in notebook.cells:
            if cell.cell_type != "code":
                continue
            for line in cell.source.splitlines():
                if phrase in line and 'forbidden' not in line.lower():
                    raise AssertionError(
                        f"forbidden wording in code cell: {phrase!r} in: {line.strip()}"
                    )
    markdown_text = "\n".join(
        cell.source for cell in notebook.cells if cell.cell_type == "markdown"
    )
    assert "FORBIDDEN wording" in markdown_text
    assert "guarded" in markdown_text.lower()


def test_v2_1_notebook_walkforward_period_table() -> None:
    code = _code_text(_notebook())
    assert '"wf_p1"' in code
    assert '"wf_p7"' in code
    assert '"2017-01-25"' in code
    assert '"2024-04-19"' in code
