from __future__ import annotations

from pathlib import Path

import nbformat as nbf


CELL_SPECS = [
    (
        "markdown",
        "# Stage 02 - Model HPO Train-Inner\n\n"
        "Route: `lst_models` V2\n"
        "Scope: `validation_only`\n"
        "User-facing notebook: `notebooks/02_model_hpo_train_inner_colab.ipynb`\n\n"
        "This notebook runs the Stage 02 package entry point against the exact "
        "Stage 01 handoff. Stage 02 is train-inner HPO only. It does not read "
        "official validation or closed holdout/test rows and does not determine "
        "the final model.\n",
    ),
    (
        "markdown",
        "## Protocol Summary\n\n"
        "Stage 02 consumes `01_candidate_inputs.json` from one frozen Stage 01 "
        "run folder. If Stage 01 produced no candidate inputs, Stage 02 must "
        "block before fitting. If Stage 01 later produces candidates, Stage 02 "
        "plans bounded train-inner HPO for the approved model families only.\n\n"
        "Core Stage 02 families:\n\n"
        "- `lightgbm`\n"
        "- `standard_dlinear`\n"
        "- `tcn`\n"
        "- `ms_dlinear_tcn`\n\n"
        "`simple_gru` and `shallow_lstm` remain optional fixed controls, not "
        "core HPO families.\n",
    ),
    (
        "markdown",
        "## Expected Artifacts\n\n"
        "Stage 02 writes a compact run folder when `RUN_STAGE02=True`:\n\n"
        "```text\n"
        "results/02_model_hpo_train_inner/<run_id>/\n"
        "  run_manifest.json\n"
        "  artifact_inventory.csv\n"
        "  02_model_hpo_train_inner_summary.csv\n"
        "  02_hpo_plan_ledger.csv\n"
        "  02_best_params_by_family.json\n"
        "  02_stage03_handoff.json\n"
        "```\n\n"
        "The current package implementation is deliberately honest: it blocks "
        "when Stage 01 has no candidates and does not fabricate HPO metrics.\n",
    ),
    (
        "code",
        "from pathlib import Path\n"
        "import importlib\n"
        "import json\n"
        "import subprocess\n"
        "import sys\n"
        "import zipfile\n\n"
        "RUN_PROJECT_BOOTSTRAP = True\n"
        "PROJECT_BOOTSTRAP_MODE = \"github_commit\"  # github_commit | drive_bundle | manual_upload | already_present\n\n"
        "PROJECT_REPO_URL = \"https://github.com/zkc768/lstm-zhang.git\"\n"
        "PROJECT_REPO_COMMIT = \"b6a67edde32c619b649ca1dbcae9bf869bee6833\"\n"
        "PROJECT_ROOT = Path(\"/content/lst_models\")\n"
        "PROJECT_DRIVE_BUNDLE_FILE_ID = \"\"\n"
        "PROJECT_DRIVE_BUNDLE_NAME = \"lst_models_stage02_colab_project.zip\"\n\n"
        "RUN_STAGE01_DRIVE_SYNC = True\n"
        "RUN_STAGE02 = False\n"
        "RUN_ARTIFACT_DISPLAY = False\n\n"
        "STAGE_NAME = \"02_model_hpo_train_inner\"\n"
        "ROUTE = \"lst_models\"\n"
        "SCOPE = \"validation_only\"\n"
        "HOLDOUT_TEST_CONTACT = False\n"
        "STAGE01_RUN_ID = \"20260608_180233\"\n"
        "STAGE01_OUTPUT_DIR = Path(\"/content/lst_models_results/01_feature_window_search\") / STAGE01_RUN_ID\n"
        "STAGE01_DRIVE_PATH_PARTS = [\"lst_models\", \"results\", \"01_feature_window_search\", STAGE01_RUN_ID]\n"
        "OUTPUT_DIR = Path(\"/content/lst_models_results/02_model_hpo_train_inner\")\n"
        "CORE_HPO_FAMILIES = [\"lightgbm\", \"standard_dlinear\", \"tcn\", \"ms_dlinear_tcn\"]\n\n"
        "def run_cmd(args, cwd=None):\n"
        "    print(\"+\", \" \".join(str(arg) for arg in args))\n"
        "    subprocess.run(args, cwd=cwd, check=True)\n\n"
        "def looks_like_project_root(path):\n"
        "    return (\n"
        "        (path / \"configs\" / \"stages\" / \"02_model_hpo_train_inner.yaml\").exists()\n"
        "        and (path / \"docs\" / \"protocols\" / \"02_model_hpo_train_inner_protocol.md\").exists()\n"
        "        and (path / \"notebooks\" / \"02_model_hpo_train_inner_colab.ipynb\").exists()\n"
        "        and (path / \"src\" / \"lst_models\" / \"stages\" / \"model_hpo_train_inner.py\").exists()\n"
        "    )\n\n"
        "def safe_extract_project_zip(zip_path):\n"
        "    destination = Path(\"/content\").resolve()\n"
        "    with zipfile.ZipFile(zip_path) as archive:\n"
        "        for member in archive.infolist():\n"
        "            member_path = Path(member.filename)\n"
        "            if member_path.is_absolute() or \"..\" in member_path.parts:\n"
        "                raise ValueError(f\"Unsafe path in uploaded zip: {member.filename}\")\n"
        "            target = (destination / member_path).resolve()\n"
        "            if target != destination and destination not in target.parents:\n"
        "                raise ValueError(f\"Unsafe path in uploaded zip: {member.filename}\")\n"
        "        archive.extractall(destination)\n"
        "    candidates = [Path(\"/content/lst_models\"), Path(\"/content\") / zip_path.stem]\n"
        "    for candidate in candidates:\n"
        "        if looks_like_project_root(candidate):\n"
        "            return candidate\n"
        "    raise FileNotFoundError(\n"
        "        \"The project bundle was extracted, but no lst_models project root was found. \"\n"
        "        \"The bundle must contain configs/, docs/, notebooks/, and src/.\"\n"
        "    )\n\n"
        "def download_and_extract_project_zip_from_drive():\n"
        "    try:\n"
        "        from google.colab import auth\n"
        "        from googleapiclient.discovery import build\n"
        "        from googleapiclient.http import MediaIoBaseDownload\n"
        "    except ImportError as exc:\n"
        "        raise RuntimeError(\n"
        "            \"PROJECT_BOOTSTRAP_MODE='drive_bundle' only works inside Colab \"\n"
        "            \"with Google Drive API dependencies available.\"\n"
        "        ) from exc\n"
        "    file_id = PROJECT_DRIVE_BUNDLE_FILE_ID.strip()\n"
        "    if not file_id:\n"
        "        raise ValueError(\"PROJECT_DRIVE_BUNDLE_FILE_ID is required for drive_bundle mode.\")\n"
        "    auth.authenticate_user()\n"
        "    service = build(\"drive\", \"v3\")\n"
        "    zip_path = Path(\"/content\") / PROJECT_DRIVE_BUNDLE_NAME\n"
        "    request = service.files().get_media(fileId=file_id)\n"
        "    with zip_path.open(\"wb\") as file_handle:\n"
        "        downloader = MediaIoBaseDownload(file_handle, request)\n"
        "        done = False\n"
        "        while not done:\n"
        "            _, done = downloader.next_chunk()\n"
        "    return safe_extract_project_zip(zip_path)\n\n"
        "def upload_and_extract_project_zip():\n"
        "    try:\n"
        "        from google.colab import files\n"
        "    except ImportError as exc:\n"
        "        raise RuntimeError(\"PROJECT_BOOTSTRAP_MODE='manual_upload' only works inside Colab.\") from exc\n"
        "    uploaded = files.upload()\n"
        "    if not uploaded:\n"
        "        raise FileNotFoundError(\"No project zip was uploaded.\")\n"
        "    zip_names = [name for name in uploaded if name.endswith(\".zip\")]\n"
        "    if not zip_names:\n"
        "        raise ValueError(\"Upload a .zip file containing the lst_models project folder.\")\n"
        "    return safe_extract_project_zip(Path(\"/content\") / zip_names[0])\n\n"
        "if RUN_PROJECT_BOOTSTRAP:\n"
        "    if PROJECT_BOOTSTRAP_MODE == \"github_commit\":\n"
        "        if (PROJECT_ROOT / \".git\").exists():\n"
        "            run_cmd([\"git\", \"fetch\", \"origin\"], cwd=PROJECT_ROOT)\n"
        "            run_cmd([\"git\", \"checkout\", PROJECT_REPO_COMMIT], cwd=PROJECT_ROOT)\n"
        "        else:\n"
        "            run_cmd([\"git\", \"clone\", PROJECT_REPO_URL, str(PROJECT_ROOT)])\n"
        "            run_cmd([\"git\", \"checkout\", PROJECT_REPO_COMMIT], cwd=PROJECT_ROOT)\n"
        "        actual_commit = subprocess.check_output([\"git\", \"rev-parse\", \"HEAD\"], cwd=PROJECT_ROOT, text=True).strip()\n"
        "        assert actual_commit == PROJECT_REPO_COMMIT, (actual_commit, PROJECT_REPO_COMMIT)\n"
        "    elif PROJECT_BOOTSTRAP_MODE == \"drive_bundle\":\n"
        "        PROJECT_ROOT = download_and_extract_project_zip_from_drive()\n"
        "    elif PROJECT_BOOTSTRAP_MODE == \"manual_upload\":\n"
        "        PROJECT_ROOT = upload_and_extract_project_zip()\n"
        "    elif PROJECT_BOOTSTRAP_MODE == \"already_present\":\n"
        "        pass\n"
        "    else:\n"
        "        raise ValueError(\"PROJECT_BOOTSTRAP_MODE must be github_commit, drive_bundle, manual_upload, or already_present\")\n\n"
        "STAGE_CONFIG_PATH = PROJECT_ROOT / \"configs\" / \"stages\" / \"02_model_hpo_train_inner.yaml\"\n"
        "PROTOCOL_PATH = PROJECT_ROOT / \"docs\" / \"protocols\" / \"02_model_hpo_train_inner_protocol.md\"\n"
        "NOTEBOOK_PATH = PROJECT_ROOT / \"notebooks\" / \"02_model_hpo_train_inner_colab.ipynb\"\n"
        "STAGE_ENTRYPOINT_PATH = PROJECT_ROOT / \"src\" / \"lst_models\" / \"stages\" / \"model_hpo_train_inner.py\"\n"
        "SEARCH_SPACE_PATHS = [\n"
        "    PROJECT_ROOT / \"configs\" / \"models\" / family / \"search_space.yaml\"\n"
        "    for family in CORE_HPO_FAMILIES\n"
        "]\n"
        "REQUIRED_PROJECT_FILES = [STAGE_CONFIG_PATH, PROTOCOL_PATH, NOTEBOOK_PATH, STAGE_ENTRYPOINT_PATH, *SEARCH_SPACE_PATHS]\n"
        "missing_project_files = [path for path in REQUIRED_PROJECT_FILES if not path.exists()]\n"
        "if missing_project_files:\n"
        "    missing_text = \"\\n\".join(f\"- {path}\" for path in missing_project_files)\n"
        "    raise FileNotFoundError(\n"
        "        \"Stage 02 bootstrap target is missing required package sidecars. \"\n"
        "        \"For normal Colab use, push the full stage bundle to GitHub and update \"\n"
        "        \"PROJECT_REPO_COMMIT to that exact commit. Missing files:\\n\" + missing_text\n"
        "    )\n\n"
        "SRC_PATH = PROJECT_ROOT / \"src\"\n"
        "if str(SRC_PATH) not in sys.path:\n"
        "    sys.path.insert(0, str(SRC_PATH))\n\n"
        "def clear_project_import_cache():\n"
        "    cached = [name for name in sys.modules if name == \"lst_models\" or name.startswith(\"lst_models.\")]\n"
        "    for name in cached:\n"
        "        del sys.modules[name]\n"
        "    importlib.invalidate_caches()\n\n"
        "clear_project_import_cache()\n\n"
        "print(\"PROJECT_ROOT:\", PROJECT_ROOT)\n"
        "print(\"PROJECT_BOOTSTRAP_MODE:\", PROJECT_BOOTSTRAP_MODE)\n"
        "print(\"PROJECT_REPO_URL:\", PROJECT_REPO_URL)\n"
        "print(\"PROJECT_COMMIT:\", PROJECT_REPO_COMMIT)\n"
        "print(\"SRC_PATH:\", SRC_PATH)\n"
        "print(\"STAGE_CONFIG_PATH:\", STAGE_CONFIG_PATH)\n"
        "print(\"PROTOCOL_PATH:\", PROTOCOL_PATH)\n"
        "print(\"NOTEBOOK_PATH:\", NOTEBOOK_PATH)\n"
        "print(\"STAGE_ENTRYPOINT_PATH:\", STAGE_ENTRYPOINT_PATH)\n"
        "print(\"STAGE01_RUN_ID:\", STAGE01_RUN_ID)\n"
        "print(\"STAGE01_OUTPUT_DIR:\", STAGE01_OUTPUT_DIR)\n"
        "print(\"STAGE01_DRIVE_PATH_PARTS:\", STAGE01_DRIVE_PATH_PARTS)\n"
        "print(\"OUTPUT_DIR:\", OUTPUT_DIR)\n"
        "print(\"RUN_STAGE01_DRIVE_SYNC:\", RUN_STAGE01_DRIVE_SYNC)\n"
        "print(\"RUN_STAGE02:\", RUN_STAGE02)\n"
        "print(\"RUN_ARTIFACT_DISPLAY:\", RUN_ARTIFACT_DISPLAY)\n",
    ),
    (
        "markdown",
        "## Config Load And Contract Check\n\n"
        "This cell reads the Stage 02 config sidecar and checks the notebook-facing "
        "contract. It does not fit models or read official validation metrics.\n",
    ),
    (
        "code",
        "try:\n"
        "    import yaml\n"
        "except ModuleNotFoundError as exc:\n"
        "    raise ModuleNotFoundError(\n"
        "        \"PyYAML is required to read the Stage 02 config. Install project dependencies before running.\"\n"
        "    ) from exc\n\n"
        "def require_path(path):\n"
        "    if not path.exists():\n"
        "        raise FileNotFoundError(f\"missing required Stage 02 file: {path}\")\n\n"
        "require_path(STAGE_CONFIG_PATH)\n"
        "require_path(PROTOCOL_PATH)\n\n"
        "with STAGE_CONFIG_PATH.open(\"r\", encoding=\"utf-8\") as handle:\n"
        "    stage02_config = yaml.safe_load(handle)\n\n"
        "stage01_inputs = stage02_config[\"inputs\"]\n"
        "assert stage02_config[\"stage_name\"] == STAGE_NAME\n"
        "assert stage02_config[\"route\"] == ROUTE\n"
        "assert stage02_config[\"scope\"] == SCOPE\n"
        "assert stage02_config[\"holdout_test_contact\"] is HOLDOUT_TEST_CONTACT\n"
        "assert stage01_inputs[\"stage01_run_id\"] == STAGE01_RUN_ID\n"
        "assert Path(stage01_inputs[\"stage01_runtime_run_dir\"]) == STAGE01_OUTPUT_DIR\n"
        "assert stage01_inputs[\"stage01_drive_path_parts\"] == STAGE01_DRIVE_PATH_PARTS\n"
        "assert [family for family, spec in stage02_config[\"hpo_families\"].items() if spec[\"enabled\"]] == CORE_HPO_FAMILIES\n"
        "assert stage02_config[\"selection_rules\"][\"no_official_validation_selection\"] is True\n"
        "assert stage02_config[\"selection_rules\"][\"no_final_model_selected\"] is True\n\n"
        "print(json.dumps({\n"
        "    \"stage_name\": stage02_config[\"stage_name\"],\n"
        "    \"scope\": stage02_config[\"scope\"],\n"
        "    \"source_stage01_run_id\": stage01_inputs[\"stage01_run_id\"],\n"
        "    \"stage01_runtime_run_dir\": stage01_inputs[\"stage01_runtime_run_dir\"],\n"
        "    \"stage01_drive_path_parts\": stage01_inputs[\"stage01_drive_path_parts\"],\n"
        "    \"core_hpo_families\": CORE_HPO_FAMILIES,\n"
        "    \"holdout_test_contact\": stage02_config[\"holdout_test_contact\"],\n"
        "}, indent=2))\n",
    ),
    (
        "markdown",
        "## Stage 01 Input Check\n\n"
        "Stage 02 requires frozen Stage 01 artifacts from one exact run folder. "
        "When `RUN_STAGE02=True`, this cell first checks the runtime path. If files "
        "are missing and `RUN_STAGE01_DRIVE_SYNC=True`, it downloads the exact "
        "Stage 01 run folder files from Drive path parts in the config.\n",
    ),
    (
        "code",
        "from lst_models.artifacts import require_artifacts\n\n"
        "def quote_drive_query_value(value):\n"
        "    return str(value).replace(\"\\\\\", \"\\\\\\\\\").replace(\"'\", \"\\\\'\")\n\n"
        "def find_unique_drive_child(service, parent_id, name, mime_type=None):\n"
        "    escaped_name = quote_drive_query_value(name)\n"
        "    query_parts = [f\"name = '{escaped_name}'\", f\"'{parent_id}' in parents\", \"trashed = false\"]\n"
        "    if mime_type:\n"
        "        query_parts.append(f\"mimeType = '{mime_type}'\")\n"
        "    response = service.files().list(\n"
        "        q=\" and \".join(query_parts),\n"
        "        spaces=\"drive\",\n"
        "        fields=\"files(id, name, mimeType, size)\",\n"
        "        pageSize=10,\n"
        "    ).execute()\n"
        "    matches = response.get(\"files\", [])\n"
        "    if len(matches) != 1:\n"
        "        raise FileNotFoundError(\n"
        "            f\"expected exactly one Drive item named {name!r} under parent {parent_id}; found {len(matches)}\"\n"
        "        )\n"
        "    return matches[0]\n\n"
        "def resolve_drive_folder(service, path_parts):\n"
        "    folder_id = \"root\"\n"
        "    folder_mime = \"application/vnd.google-apps.folder\"\n"
        "    for folder_name in path_parts:\n"
        "        folder = find_unique_drive_child(service, folder_id, folder_name, folder_mime)\n"
        "        folder_id = folder[\"id\"]\n"
        "    return folder_id\n\n"
        "def download_drive_file(service, file_id, output_path):\n"
        "    from googleapiclient.http import MediaIoBaseDownload\n"
        "    output_path.parent.mkdir(parents=True, exist_ok=True)\n"
        "    request = service.files().get_media(fileId=file_id)\n"
        "    with output_path.open(\"wb\") as handle:\n"
        "        downloader = MediaIoBaseDownload(handle, request)\n"
        "        done = False\n"
        "        while not done:\n"
        "            _, done = downloader.next_chunk()\n\n"
        "def sync_stage01_artifacts_from_drive(required_names):\n"
        "    try:\n"
        "        from google.colab import auth\n"
        "        from googleapiclient.discovery import build\n"
        "    except ImportError as exc:\n"
        "        raise RuntimeError(\n"
        "            \"Stage 01 Drive sync only works inside Colab with Google API dependencies. \"\n"
        "            f\"Alternatively, place the frozen Stage 01 run folder at {STAGE01_OUTPUT_DIR}.\"\n"
        "        ) from exc\n"
        "    auth.authenticate_user()\n"
        "    service = build(\"drive\", \"v3\")\n"
        "    run_folder_id = resolve_drive_folder(service, STAGE01_DRIVE_PATH_PARTS)\n"
        "    for artifact_name in required_names:\n"
        "        output_path = STAGE01_OUTPUT_DIR / artifact_name\n"
        "        if output_path.exists():\n"
        "            continue\n"
        "        metadata = find_unique_drive_child(service, run_folder_id, artifact_name)\n"
        "        download_drive_file(service, metadata[\"id\"], output_path)\n"
        "        print(f\"Downloaded Stage 01 artifact: {output_path}\")\n\n"
        "required_stage01_artifacts = stage02_config[\"inputs\"][\"required_stage01_artifacts\"]\n"
        "if RUN_STAGE02:\n"
        "    missing_before = [name for name in required_stage01_artifacts if not (STAGE01_OUTPUT_DIR / name).exists()]\n"
        "    if missing_before and RUN_STAGE01_DRIVE_SYNC:\n"
        "        print(\"Missing Stage 01 artifacts in runtime; syncing exact frozen run from Drive.\")\n"
        "        print(\"Drive path parts:\", STAGE01_DRIVE_PATH_PARTS)\n"
        "        sync_stage01_artifacts_from_drive(missing_before)\n"
        "    stage01_paths = require_artifacts(STAGE01_OUTPUT_DIR, required_stage01_artifacts)\n"
        "    print(\"Stage 01 artifact presence check passed.\")\n"
        "    print(json.dumps({name: str(path) for name, path in stage01_paths.items()}, indent=2))\n"
        "else:\n"
        "    print(\"RUN_STAGE02=False; Stage 01 artifact check not executed.\")\n",
    ),
    (
        "markdown",
        "## Run Stage 02\n\n"
        "The package-backed stage entry point is expected at "
        "`lst_models.stages.model_hpo_train_inner.run_stage`. The committed "
        "notebook remains inert by default.\n",
    ),
    (
        "code",
        "if RUN_STAGE02:\n"
        "    try:\n"
        "        from lst_models.stages.model_hpo_train_inner import run_stage\n"
        "    except ModuleNotFoundError as exc:\n"
        "        raise ModuleNotFoundError(\n"
        "            \"Missing Stage 02 package entry point: src/lst_models/stages/model_hpo_train_inner.py.\"\n"
        "        ) from exc\n"
        "    result = run_stage(stage02_config)\n"
        "    display(result)\n"
        "else:\n"
        "    print(\"RUN_STAGE02=False; Stage 02 train-inner HPO not executed.\")\n",
    ),
    (
        "markdown",
        "## Artifact Display\n\n"
        "After an approved run, display only Stage 02 artifacts from "
        "`result.output_dir`. Do not scan for a latest run.\n",
    ),
    (
        "code",
        "if RUN_ARTIFACT_DISPLAY:\n"
        "    import pandas as pd\n\n"
        "    if \"result\" not in globals():\n"
        "        raise RuntimeError(\"RUN_ARTIFACT_DISPLAY=True requires running Stage 02 first.\")\n"
        "    run_dir = Path(result.output_dir)\n"
        "    inventory_path = run_dir / \"artifact_inventory.csv\"\n"
        "    summary_path = run_dir / \"02_model_hpo_train_inner_summary.csv\"\n"
        "    ledger_path = run_dir / \"02_hpo_plan_ledger.csv\"\n"
        "    best_params_path = run_dir / \"02_best_params_by_family.json\"\n"
        "    handoff_path = run_dir / \"02_stage03_handoff.json\"\n"
        "    for path in [inventory_path, summary_path, ledger_path, best_params_path, handoff_path]:\n"
        "        require_path(path)\n"
        "    display(pd.read_csv(inventory_path))\n"
        "    display(pd.read_csv(summary_path))\n"
        "    display(pd.read_csv(ledger_path).head(20))\n"
        "    with best_params_path.open(\"r\", encoding=\"utf-8\") as handle:\n"
        "        best_params = json.load(handle)\n"
        "    with handoff_path.open(\"r\", encoding=\"utf-8\") as handle:\n"
        "        stage03_handoff = json.load(handle)\n"
        "    assert best_params[\"holdout_test_contact\"] is False\n"
        "    assert stage03_handoff[\"holdout_test_contact\"] is False\n"
        "    print(json.dumps(best_params, indent=2))\n"
        "    print(json.dumps(stage03_handoff, indent=2))\n"
        "else:\n"
        "    print(\"RUN_ARTIFACT_DISPLAY=False; no Stage 02 artifacts displayed.\")\n",
    ),
    (
        "markdown",
        "## Interpretation Guard\n\n"
        "Allowed wording after Stage 02:\n\n"
        "- frozen train-inner HPO parameters for Stage 03 validation readout\n"
        "- Stage 02 train-inner HPO completed for approved families\n"
        "- Stage 02 blocked because Stage 01 produced no candidate inputs\n\n"
        "Do not claim a final model, official validation winner, holdout winner, "
        "or test winner from this notebook.\n",
    ),
]


def build_notebook() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        "colab": {"provenance": []},
    }
    nb.cells = []
    for cell_type, cell_source in CELL_SPECS:
        if cell_type == "markdown":
            cell = nbf.v4.new_markdown_cell(cell_source)
        elif cell_type == "code":
            cell = nbf.v4.new_code_cell(cell_source)
            cell.outputs = []
            cell.execution_count = None
        else:
            raise ValueError(f"unsupported cell type: {cell_type}")
        cell.metadata = {}
        nb.cells.append(cell)
    return nb


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    output_path = root / "notebooks" / "02_model_hpo_train_inner_colab.ipynb"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(build_notebook(), output_path)
    print(output_path)


if __name__ == "__main__":
    main()
