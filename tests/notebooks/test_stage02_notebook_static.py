from __future__ import annotations

import ast
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "notebooks" / "02_model_hpo_train_inner_colab.ipynb"
CURRENT_STAGE01_RUN_ID = "20260610_075002"
CURRENT_STAGE00_RUN_ID = "20260610_051705_347450"


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
    assert "Stage 02 is formal train-inner HPO only" in text
    assert "RUN_PROJECT_BOOTSTRAP = True" in text
    assert 'PROJECT_BOOTSTRAP_MODE = "github_commit"' in text
    assert 'PROJECT_REPO_URL = "https://github.com/zkc768/lstm-zhang.git"' in text
    assert 'PROJECT_REPO_COMMIT = "4672f4d27e3e8a009ce95bc5344cadc0aac398e1"' in text
    assert "RUN_STAGE00_DRIVE_SYNC = True" in text
    assert "RUN_STAGE01_DRIVE_SYNC = True" in text
    assert "RUN_RAW_DATA_SYNC = True" in text
    assert "RUN_STAGE02_CHECKPOINT = False" in text
    assert "RUN_STAGE02_DRIVE_BACKUP = True" in text
    assert "RUN_STAGE02 = False" in text
    assert "RUN_ARTIFACT_DISPLAY = False" in text
    assert 'SUPERSEDED_STAGE02_RUN_IDS = ["20260609_100637_704705"]' in text
    assert 'STAGE02_RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")' in text
    assert 'STAGE02_OUTPUT_DIR = Path("/content/lst_models_results/02_model_hpo_train_inner") / STAGE02_RUN_ID' in text
    assert 'STAGE02_DRIVE_RESULT_PATH_PARTS = ["lst_models", "results", "02_model_hpo_train_inner"]' in text
    assert 'CHECKPOINT_DRIVE_PATH_PARTS = ["lst_models", "checkpoints", "02_model_hpo_train_inner", STAGE02_RUN_ID]' in text
    assert 'CHECKPOINT_DRIVE_PATH_PARTS = ["lst_models", "checkpoints", "02_model_hpo_train_inner", STAGE01_RUN_ID]' not in text
    assert "stage02_checkpoint_manifest.json" in text
    assert "Stage 02 Drive Result Backup" in text
    assert "backup_stage02_results_to_drive" in text
    assert "drive_backup_manifest.json" in text
    assert "backup_manifest_path.write_text" in text
    assert 'print("stage_run_id:", backup_manifest["stage_run_id"])' in text
    assert 'print("drive_path:", backup_manifest["drive_path"])' in text
    assert 'print("drive_folder_id:", backup_manifest["drive_folder_id"])' in text
    assert "ensure_stage02_result_drive_subpath" in text
    assert "relative_path = local_path.relative_to(run_dir)" in text
    assert "uploaded_relative_paths" in text
    assert "relative_path.as_posix()" in text
    assert "upload_or_update_stage02_result_file(service, drive_folder_id, run_dir, path)" in text
    assert "upload_or_update_stage02_result_file(service, drive_folder_id, path)" not in text
    assert '"stage_run_id": run_dir.name' in text
    assert "stage02_drive_backup_manifest = backup_stage02_results_to_drive(result.output_dir)" in text
    assert "MediaFileUpload" in text
    assert "def quote_drive_query_value" in text
    assert "if RUN_STAGE02 or RUN_STAGE02_CHECKPOINT:" in text
    assert "sync_raw_data_from_drive" in text
    assert "STAGE00_DRIVE_PATH_PARTS" in text
    assert 'stage_inputs["stage00_run_id"] = STAGE00_RUN_ID' in text
    assert 'stage_inputs["stage00_runtime_run_dir"] = str(STAGE00_OUTPUT_DIR)' in text
    assert 'stage_inputs["stage00_drive_path_parts"] = STAGE00_DRIVE_PATH_PARTS' in text
    assert 'stage_inputs["stage00_run_manifest"] = str(STAGE00_OUTPUT_DIR / "run_manifest.json")' in text
    assert 'stage_inputs["stage01_run_id"] = STAGE01_RUN_ID' in text
    assert 'stage_inputs["stage01_runtime_run_dir"] = str(STAGE01_OUTPUT_DIR)' in text
    assert 'stage_inputs["stage01_drive_path_parts"] = STAGE01_DRIVE_PATH_PARTS' in text
    assert 'stage_inputs["stage01_candidate_inputs"] = str(STAGE01_OUTPUT_DIR / "01_candidate_inputs.json")' in text
    assert 'stage_inputs["raw_data_dir"] = str(RAW_DATA_DIR)' in text
    assert 'stage_outputs["output_dir"] = str(OUTPUT_DIR)' in text
    assert 'stage_outputs["run_id"] = STAGE02_RUN_ID' in text
    assert 'stage02_config["superseded_stage02_run_ids"] = SUPERSEDED_STAGE02_RUN_IDS' in text
    assert 'stage_checkpointing["checkpoint_dir"] = str(CHECKPOINT_ROOT)' in text
    assert 'if Path(result.output_dir).name != STAGE02_RUN_ID:' in text
    assert 'if Path(result.output_dir) != STAGE02_OUTPUT_DIR:' in text
    assert "required_stage00_artifacts = stage02_config" in text
    assert "datetime.now(timezone.utc)" in text
    assert '"sync_timestamp_utc": datetime.now(timezone.utc).isoformat()' in text
    assert "datetime.utcnow" not in text
    assert 'checkpoint_stage01_artifacts = stage02_config["inputs"]["required_stage01_artifacts"]' in text
    assert 'checkpoint_stage00_artifacts = stage02_config["inputs"]["required_stage00_artifacts"]' in text
    assert 'run_manifest_path = output_run_dir / "run_manifest.json"' in text
    assert "run_manifest_holdout_contact" in text
    assert "assert_stage02_checkpoint_file_scope" in text
    assert "write_stage02_drive_checkpoint(\"pre_stage02\")" in text
    assert "write_stage02_drive_checkpoint(\"post_stage02\", output_run_dir=Path(result.output_dir))" in text
    assert f'STAGE00_RUN_ID = "{CURRENT_STAGE00_RUN_ID}"' in text
    assert f'STAGE01_RUN_ID = "{CURRENT_STAGE01_RUN_ID}"' in text
    assert 'STAGE00_DRIVE_PATH_PARTS = ["lst_models", "results", "00_data_split_label_freeze", STAGE00_RUN_ID]' in text
    assert 'STAGE01_DRIVE_PATH_PARTS = ["lst_models", "results", "01_feature_window_search", STAGE01_RUN_ID]' in text
    assert "CORE_HPO_FAMILIES" in text
    assert "BASELINE_REGISTRY_NAMES" in text
    assert "early_stopping_validation_source" in text
    assert 'torch_defaults["early_stopping"] == "inner_train_chronological_tail"' in text
    assert '"torch_early_stopping": torch_defaults["early_stopping"]' in text
    assert "minimum_positive_ticker_count" in text
    assert "max_selected_configs_per_family" in text
    assert "model_hpo_train_inner.py" in text
    assert "from lst_models.stages.model_hpo_train_inner import run_stage" in text
    assert "run_dir = Path(result.output_dir)" in text
    assert 'summary_path = run_dir / "02_model_hpo_train_inner_summary.csv"' in text
    assert 'trial_ledger_path = run_dir / "02_hpo_trial_ledger.csv"' in text
    assert 'hpo_summary_path = run_dir / "02_hpo_summary.csv"' in text
    assert 'baseline_summary_path = run_dir / "02_baseline_control_summary.csv"' in text


def test_stage02_checkpoint_helpers_are_available_before_checkpoint_cell() -> None:
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    code_cells = [cell.source for cell in notebook.cells if cell.cell_type == "code"]

    quote_cell_index = next(
        index for index, source in enumerate(code_cells) if "def quote_drive_query_value" in source
    )
    checkpoint_cell_index = next(
        index
        for index, source in enumerate(code_cells)
        if "def build_stage02_checkpoint_archive" in source
    )
    checkpoint_cell = code_cells[checkpoint_cell_index]

    assert quote_cell_index < checkpoint_cell_index
    assert "for artifact_name in checkpoint_stage01_artifacts:" in checkpoint_cell
    assert "name for name in checkpoint_stage01_artifacts" in checkpoint_cell
    assert "required_stage01_artifacts = stage02_config" not in checkpoint_cell


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
