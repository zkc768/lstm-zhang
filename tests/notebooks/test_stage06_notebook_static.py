from __future__ import annotations

import ast
from pathlib import Path

import nbformat
import yaml


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "notebooks" / "06_ian_final_progress_record_colab.ipynb"
CONFIG_PATH = ROOT / "configs" / "stages" / "06_ian_final_progress_record.yaml"
PIPELINE_PATH = ROOT / "configs" / "lst_models_pipeline.yaml"
EXPECTED_PROJECT_REPO_COMMIT = "279a964fddca73dbe541c10145df74a2b325a78c"


def _notebook() -> nbformat.NotebookNode:
    return nbformat.read(NOTEBOOK, as_version=4)


def _code_cells() -> list[nbformat.NotebookNode]:
    return [cell for cell in _notebook().cells if cell.cell_type == "code"]


def _source() -> str:
    return "\n\n".join(cell.source for cell in _code_cells())


def _config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def _pipeline() -> dict:
    return yaml.safe_load(PIPELINE_PATH.read_text(encoding="utf-8"))


def test_stage06_notebook_path_exists_from_config_and_pipeline() -> None:
    assert NOTEBOOK.exists()
    config_notebook = ROOT / _config()["inputs"]["notebook_path"]
    pipeline_stage = {
        str(stage["name"]): stage for stage in _pipeline()["stages"]
    }["06_ian_final_progress_record"]
    pipeline_notebook = ROOT / pipeline_stage["notebook"]
    assert config_notebook == NOTEBOOK
    assert pipeline_notebook == NOTEBOOK
    assert pipeline_stage["active_run_id"] is None


def test_stage06_notebook_code_cells_parse_and_outputs_are_empty() -> None:
    for index, cell in enumerate(_code_cells()):
        ast.parse(cell.source, filename=f"stage06_notebook_cell_{index}")
        assert cell.outputs == []
        assert cell.execution_count is None


def test_stage06_notebook_exact_bootstrap_and_required_sidecar_checks() -> None:
    source = _source()
    assert 'RUN_PROJECT_BOOTSTRAP = True' in source
    assert 'PROJECT_BOOTSTRAP_MODE = "github_commit"' in source
    assert 'PROJECT_REPO_URL = "https://github.com/zkc768/lstm-zhang.git"' in source
    assert f'PROJECT_REPO_COMMIT = "{EXPECTED_PROJECT_REPO_COMMIT}"' in source
    assert 'PROJECT_REPO_COMMIT.startswith("<")' in source
    assert 'run_command(["git", "checkout", PROJECT_REPO_COMMIT]' in source
    assert 'run_command(["git", "rev-parse", "HEAD"]' in source
    for required in (
        'Path("src/lst_models")',
        'Path("configs")',
        'Path("docs/protocols")',
        'NOTEBOOK_RELATIVE',
        'STAGE_CONFIG_RELATIVE',
        'STAGE_PROTOCOL_RELATIVE',
        'STAGE_ENTRYPOINT_RELATIVE',
    ):
        assert required in source


def test_stage06_notebook_defaults_are_measure_only_and_inactive() -> None:
    source = _source()
    assert 'STAGE_NAME = "06_ian_final_progress_record"' in source
    assert 'SCOPE = "progress_record_measure_only"' in source
    assert "HOLDOUT_TEST_CONTACT = False" in source
    assert "NEW_SCORING_EVENTS = 0" in source
    assert "NO_FINAL_MODEL_SELECTED = True" in source
    assert "OFFICIAL_VALIDATION_FOR_SELECTION = False" in source
    assert "RUN_STAGE06 = False" in source
    assert "RUN_STAGE06_DRIVE_SYNC = True" in source
    assert "RUN_STAGE06_DRIVE_BACKUP = True" in source
    assert "RUN_STAGE06 = True" not in source


def test_stage06_runtime_path_injection_precedes_run_stage_call() -> None:
    source = _source()
    run_stage_pos = source.index("run_stage(stage06_config)")
    for snippet in (
        'stage_inputs["notebook_path"] = str(NOTEBOOK_RELATIVE.as_posix())',
        'stage_outputs["output_dir"] = str(OUTPUT_DIR)',
        'run["runtime_run_dir"] = str(run_dir)',
        'run["drive_path_parts"] = UPSTREAM_DRIVE_PATH_PARTS[stage_name]',
    ):
        assert snippet in source
        assert source.index(snippet) < run_stage_pos
    assert 'if set(upstream_by_name) != set(UPSTREAM_RUNTIME_RUN_DIRS)' in source


def test_stage06_upstream_run_ids_match_config_and_pipeline() -> None:
    source = _source()
    config_runs = {
        str(run["stage_name"]): str(run["run_id"])
        for run in _config()["inputs"]["upstream_runs"]
    }
    pipeline = _pipeline()
    pipeline_runs = {str(stage["name"]): str(stage["active_run_id"]) for stage in pipeline["stages"]}
    branch = {str(branch["name"]): branch for branch in pipeline["branches"]}[
        "v2_1_guarded_walkforward_readout"
    ]
    pipeline_runs["v2_1_guarded_walkforward_readout"] = str(branch["active_run_id"])
    for stage_name, run_id in config_runs.items():
        assert run_id == pipeline_runs[stage_name]
        assert stage_name in source
        assert run_id in source


def test_stage06_upstream_preflight_uses_exact_artifacts_and_refuses_missing_on_run() -> None:
    source = _source()
    assert 'REQUIRED_UPSTREAM_RECORD_FILES = ["artifact_inventory.csv", "run_manifest.json"]' in source
    assert "def missing_upstream_record_files()" in source
    assert "format_missing_upstream_records" in source
    assert "if RUN_STAGE06:" in source
    assert "raise FileNotFoundError" in source
    assert "Stage 06 upstream record files are missing" in source
    assert "Stage 06 upstream record files are still missing after Drive sync" in source
    assert "latest" not in source.lower()


def test_stage06_durable_save_cell_immediately_follows_run_stage_cell() -> None:
    cells = _code_cells()
    run_indices = [
        index for index, cell in enumerate(cells)
        if "result = run_stage(stage06_config)" in cell.source
    ]
    assert len(run_indices) == 1
    save_cell = cells[run_indices[0] + 1].source
    assert "Durable Drive save cell" in save_cell
    assert "from lst_models.stages.ian_final_progress_record import REQUIRED_STAGE06_ARTIFACTS" in save_cell
    assert "def validate_stage06_run_folder" in save_cell
    assert "def backup_stage06_results_to_drive" in save_cell
    assert "drive_backup_manifest.json" in save_cell
    assert '"uploaded_byte_size": None' in save_cell
    for printed in ("stage_run_id", "drive_path", "drive_folder_id"):
        assert f'print("{printed}"' in save_cell


def test_stage06_backup_refuses_pending_fetch_and_missing_notebook_hash() -> None:
    source = _source()
    assert 'progress_record.get("n_pending_drive_fetch") != 0' in source
    assert "Stage 06 backup refused because upstream artifacts are still pending Drive fetch" in source
    assert 'manifest.get("notebook_sha256") is None' in source
    assert "Stage 06 manifest notebook_sha256 is missing" in source
    for key in (
        "stage_name",
        "scope",
        "holdout_test_contact",
        "new_scoring_events",
        "official_validation_for_selection",
        "no_final_model_selected",
    ):
        assert f'"{key}"' in source


def test_stage06_notebook_forbidden_active_patterns_absent() -> None:
    source = _source()
    lowered = source.lower()
    for forbidden in (
        "drive.mount(",
        "train_test_split",
        "shuffle=true",
        "random_split",
        "read_parquet",
        "read_csv(\"/content/lst_models_raw_stock_data",
    ):
        assert forbidden not in lowered
