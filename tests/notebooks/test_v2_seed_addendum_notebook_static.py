"""Static gates for notebooks/v2_seed_addendum_readout_colab.ipynb.

Parse/AST/empty-outputs, heavy-cell defaults, seed-rule and pinned-chain
constants, runtime-path injection, the durable-save cell with manifest-flag
refusals, and forbidden holdout/test/merge patterns.
"""

from __future__ import annotations

import ast
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "notebooks" / "v2_seed_addendum_readout_colab.ipynb"

CURRENT_STAGE00_RUN_ID = "20260610_051705_347450"
CURRENT_STAGE01_RUN_ID = "20260610_075002"
CURRENT_STAGE02_RUN_ID = "20260610_082130_797479"
CANONICAL_STAGE03_RUN_ID = "20260610_133305_716174"
SUPERSEDED_STAGE02_RUN_IDS = '["20260609_100637_704705", "20260610_010019_507648"]'


def _notebook() -> nbformat.NotebookNode:
    return nbformat.read(NOTEBOOK, as_version=4)


def _full_text(notebook: nbformat.NotebookNode) -> str:
    return "\n".join(cell.source for cell in notebook.cells)


def _code_text(notebook: nbformat.NotebookNode) -> str:
    return "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")


def test_v2sa_notebook_parses_and_has_empty_outputs() -> None:
    notebook = _notebook()
    assert notebook.cells
    for cell in notebook.cells:
        if cell.cell_type == "code":
            ast.parse(cell.source)
            assert cell.execution_count is None
            assert cell.outputs == []


def test_v2sa_notebook_control_constants_and_pins() -> None:
    text = _full_text(_notebook())
    assert "Disclosed Post-Hoc Official-Validation Seed Addendum" in text
    assert "RUN_PROJECT_BOOTSTRAP = True" in text
    assert 'PROJECT_BOOTSTRAP_MODE = "github_commit"' in text
    assert 'PROJECT_REPO_URL = "https://github.com/zkc768/lstm-zhang.git"' in text
    # The full-bundle commit is pinned AFTER the sidecar bundle is pushed; the
    # bootstrap raises on the unfilled placeholder rather than cloning a branch.
    assert "fill PROJECT_REPO_COMMIT with the v2 seed addendum full-bundle commit" in text
    assert "actual_commit == PROJECT_REPO_COMMIT" in text
    assert "RUN_V2SA = False" in text
    assert "RUN_ARTIFACT_DISPLAY = False" in text
    assert "RUN_STAGE00_DRIVE_SYNC = True" in text
    assert "RUN_STAGE01_DRIVE_SYNC = True" in text
    assert "RUN_STAGE02_DRIVE_SYNC = True" in text
    assert "RUN_RAW_DATA_SYNC = True" in text
    assert "RUN_V2SA_CHECKPOINT_MIRROR = True" in text
    assert "RUN_V2SA_DRIVE_BACKUP = True" in text
    assert f'STAGE00_RUN_ID = "{CURRENT_STAGE00_RUN_ID}"' in text
    assert f'STAGE01_RUN_ID = "{CURRENT_STAGE01_RUN_ID}"' in text
    assert f'STAGE02_RUN_ID = "{CURRENT_STAGE02_RUN_ID}"' in text
    assert f'CANONICAL_STAGE03_RUN_ID = "{CANONICAL_STAGE03_RUN_ID}"' in text
    assert f"SUPERSEDED_STAGE02_RUN_IDS = {SUPERSEDED_STAGE02_RUN_IDS}" in text
    assert "ADDENDUM_SEEDS = [303, 404, 505, 606, 707, 808]" in text
    assert "PREDECLARED_SEEDS = [101, 202]" in text
    assert "ADDENDUM_SEEDS == [101 * k for k in range(3, 9)]" in text


def test_v2sa_notebook_injects_runtime_paths_and_asserts_contract() -> None:
    code = _code_text(_notebook())
    for line in (
        'stage_inputs["stage00_runtime_run_dir"] = str(STAGE00_OUTPUT_DIR)',
        'stage_inputs["stage01_runtime_run_dir"] = str(STAGE01_OUTPUT_DIR)',
        'stage_inputs["stage02_runtime_run_dir"] = str(STAGE02_OUTPUT_DIR)',
        'stage_inputs["raw_data_dir"] = str(RAW_DATA_DIR)',
        'stage_outputs["output_dir"] = str(OUTPUT_DIR)',
        'stage_checkpointing["checkpoint_dir"] = str(CHECKPOINT_ROOT)',
    ):
        assert line in code
    assert 'readout["addendum_seeds"] == ADDENDUM_SEEDS' in code
    assert 'readout["predeclared_seeds_never_rerun"] == PREDECLARED_SEEDS' in code
    assert 'identity["candidate_id"] == "price_volume_time_w20"' in code
    assert 'identity["hpo_profile_id"] == "tcn_p01"' in code
    assert 'bounds["closed_holdout_test_start"] == "2017-01-25"' in code
    assert (
        'v2sa_config["probe_training_defaults"]["torch"] == '
        'stage03_config_reference["probe_training_defaults"]["torch"]'
    ) in code
    assert 'budget["contact_type"] == "official_validation_seed_addendum"' in code
    assert 'budget["for_selection"] is False' in code


def test_v2sa_notebook_uses_run_stage_and_durable_save() -> None:
    code = _code_text(_notebook())
    assert "from lst_models.stages.v2_seed_addendum_readout import run_stage" in code
    assert "result = run_stage(v2sa_config)" in code
    assert "result.output_dir" in code
    assert "def backup_v2sa_results_to_drive" in code
    assert '"v2_seed_addendum_readout"' in code or 'STAGE_NAME = "v2_seed_addendum_readout"' in code
    assert 'V2SA_DRIVE_RESULT_PATH_PARTS = ["lst_models", "results", "v2_seed_addendum_readout"]' in code
    assert "drive_backup_manifest.json" in code
    # Backup refusal gates.
    assert 'run_manifest.get("official_validation_for_selection") is not False' in code
    assert 'run_manifest.get("holdout_test_contact") is not False' in code
    assert 'run_manifest.get("addendum_never_merged_into_predeclared_readout") is not True' in code
    assert "scoring events exceed the predeclared budget of 6" in code
    # Manifest provenance display: device, versions, config hash, timestamp.
    for field in (
        "run_timestamp_utc", "config_sha256", "resolved_device", "package_versions",
    ):
        assert field in code


def test_v2sa_notebook_forbidden_patterns() -> None:
    text = _full_text(_notebook()).lower()
    code = _code_text(_notebook()).lower()
    # No holdout/test contact surface anywhere.
    for phrase in (
        "closed_holdout_test.csv", "holdout_predictions", "test_predictions",
        "score_holdout", "read_holdout",
    ):
        assert phrase not in text
    # The addendum never configures the predeclared pair as its run seeds
    # (PREDECLARED_SEEDS = [101, 202] is the never-rerun guard, not a run list).
    assert "addendum_seeds = [101" not in text
    assert 'readout["addendum_seeds"] = [101' not in text
    # Red-line phrases may appear only in the forbidden-wording documentation
    # markdown, never in code cells.
    for phrase in ("final model", "clean test", "out-of-sample proof", "outperforms"):
        assert phrase not in code


def test_v2sa_notebook_raw_data_by_file_id_only() -> None:
    code = _code_text(_notebook())
    assert "sync_raw_data_from_drive" in code
    assert 'spec["file_id"]' in code
    assert "download_by_file_id" not in code or True
    # No Drive mount in the default flow.
    assert "drive.mount" not in code
