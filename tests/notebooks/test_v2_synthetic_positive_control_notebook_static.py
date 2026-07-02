from __future__ import annotations

import ast
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "notebooks" / "v2_synthetic_positive_control_colab.ipynb"

CURRENT_STAGE00_RUN_ID = "20260610_051705_347450"
CURRENT_STAGE01_RUN_ID = "20260610_075002"
CURRENT_REAL_STAGE02_RUN_ID = "20260610_082130_797479"


def _notebook() -> nbformat.NotebookNode:
    return nbformat.read(NOTEBOOK, as_version=4)


def _full_text(notebook: nbformat.NotebookNode) -> str:
    return "\n".join(cell.source for cell in notebook.cells)


def _code_text(notebook: nbformat.NotebookNode) -> str:
    return "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")


def _code_cells(notebook: nbformat.NotebookNode) -> list[str]:
    return [cell.source for cell in notebook.cells if cell.cell_type == "code"]


def test_spc_notebook_parses_and_has_empty_outputs() -> None:
    notebook = _notebook()
    assert notebook.cells
    for cell in notebook.cells:
        if cell.cell_type == "code":
            ast.parse(cell.source)
            assert cell.execution_count is None
            assert cell.outputs == []


def test_spc_notebook_control_constants_and_pins() -> None:
    text = _full_text(_notebook())
    assert "V2 Synthetic Positive Control" in text
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
    assert "RUN_SPC = False" in text
    assert "RUN_STAGE00_DRIVE_SYNC = True" in text
    assert "RUN_STAGE01_DRIVE_SYNC = True" in text
    assert "RUN_STAGE02_REAL_DRIVE_SYNC = True" in text
    assert "RUN_RAW_DATA_SYNC = True" in text
    assert "RUN_SPC_DRIVE_BACKUP = True" in text
    assert "RUN_ARTIFACT_DISPLAY = False" in text
    assert f'STAGE00_RUN_ID = "{CURRENT_STAGE00_RUN_ID}"' in text
    assert f'STAGE01_RUN_ID = "{CURRENT_STAGE01_RUN_ID}"' in text
    assert f'STAGE02_REAL_RUN_ID = "{CURRENT_REAL_STAGE02_RUN_ID}"' in text
    assert "FROZEN_SEEDS = [101, 202]" in text
    assert "ARM_STRENGTHS = [0.0, 0.01, 0.02, 0.05]" in text
    assert "INJECTION_SEED = 20260701" in text
    assert 'TRAIN_END_EXCLUSIVE = "2013-09-16"' in text


def test_spc_notebook_uses_run_stage_and_validates_config_first() -> None:
    code = _code_text(_notebook())
    assert "from lst_models.stages.synthetic_positive_control import run_stage" in code
    assert "result = run_stage(spc_config)" in code
    assert "from lst_models.stages.synthetic_positive_control import _validate_config" in code
    assert "_validate_config(spc_config)" in code
    assert code.index("_validate_config(spc_config)") < code.index(
        "service = get_drive_service_for_input_sync()"
    )


def test_spc_notebook_runtime_path_injection() -> None:
    code = _code_text(_notebook())
    assert 'stage_inputs["stage00_runtime_run_dir"] = str(STAGE00_OUTPUT_DIR)' in code
    assert 'stage_inputs["stage01_runtime_run_dir"] = str(STAGE01_OUTPUT_DIR)' in code
    assert 'stage_inputs["stage02_real_runtime_run_dir"] = str(STAGE02_REAL_OUTPUT_DIR)' in code
    assert 'stage_inputs["raw_data_dir"] = str(RAW_DATA_DIR)' in code
    assert 'stage_outputs["output_dir"] = str(OUTPUT_DIR)' in code
    assert 'stage_outputs["run_id"] = SPC_RUN_ID' in code
    assert 'stage_checkpointing["checkpoint_dir"] = str(CHECKPOINT_ROOT)' in code
    assert 'Path(stage_inputs["raw_data_dir"]) == RAW_DATA_DIR' in code
    assert 'Path(stage_outputs["output_dir"]) == OUTPUT_DIR' in code


def test_spc_notebook_input_sync_uses_exact_run_folders() -> None:
    code = _code_text(_notebook())
    assert "require_artifacts(STAGE00_OUTPUT_DIR, required_stage00_artifacts)" in code
    assert "require_artifacts(STAGE01_OUTPUT_DIR, required_stage01_artifacts)" in code
    assert "require_artifacts(STAGE02_REAL_OUTPUT_DIR, required_stage02_artifacts)" in code
    assert "STAGE00_DRIVE_PATH_PARTS" in code
    assert "STAGE01_DRIVE_PATH_PARTS" in code
    assert "STAGE02_REAL_DRIVE_PATH_PARTS" in code
    assert "sync_raw_data_from_drive" in code


def test_spc_notebook_drive_backup_immediately_after_run_cell() -> None:
    notebook = _notebook()
    code_cells = _code_cells(notebook)
    run_cell_index = next(
        index for index, source in enumerate(code_cells)
        if "result = run_stage(spc_config)" in source
    )
    backup_cell_index = next(
        index for index, source in enumerate(code_cells)
        if "REQUIRED_SPC_ARTIFACTS" in source and "RUN_SPC_DRIVE_BACKUP and RUN_SPC" in source
    )
    assert backup_cell_index == run_cell_index + 1
    backup_cell = code_cells[backup_cell_index]
    assert (
        "from lst_models.stages.synthetic_positive_control import REQUIRED_SPC_ARTIFACTS"
        in backup_cell
    )
    assert "missing_required_artifacts" in backup_cell
    assert "FileNotFoundError" in backup_cell
    assert "drive_backup_manifest.json" in backup_cell
    assert '"bytes": None' in backup_cell
    assert '"self_reference": True' in backup_cell
    assert 'print("stage_run_id:", SPC_RUN_ID)' in backup_cell
    assert 'print("drive_path:"' in backup_cell
    assert 'print("drive_folder_id:", drive_folder_id)' in backup_cell


def test_spc_notebook_forbidden_active_patterns_absent() -> None:
    notebook = _notebook()
    code_text = _code_text(notebook)
    forbidden_code_patterns = [
        "drive.mount(",
        "train_test_split",
        "from intraday_research",
        "RUN_SPC = True",
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
    assert "synthetic-label protocol-validation evidence" in normalized_markdown
    assert "NEVER market evidence" in normalized_markdown


def test_spc_notebook_declares_synthetic_scope_asserts() -> None:
    code = _code_text(_notebook())
    assert 'spc_config["synthetic_labels"] is SYNTHETIC_LABELS' in code
    assert 'spc_config["train_domain_only"] is TRAIN_DOMAIN_ONLY' in code
    assert 'spc_config["holdout_test_contact"] is HOLDOUT_TEST_CONTACT' in code
    assert '[arm["strength"] for arm in spc_config["injection"]["arms"]] == ARM_STRENGTHS' in code
    assert 'spc_config["train_inner"]["seeds"] == FROZEN_SEEDS' in code
