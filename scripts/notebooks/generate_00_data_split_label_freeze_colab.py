from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import nbformat as nbf


PROJECT_REPO_COMMIT = "4672f4d27e3e8a009ce95bc5344cadc0aac398e1"


def markdown(source: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(dedent(source).strip() + "\n")


def code(source: str) -> nbf.NotebookNode:
    cell = nbf.v4.new_code_cell(dedent(source).strip() + "\n")
    cell.outputs = []
    cell.execution_count = None
    return cell


def build_notebook() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        "colab": {"provenance": []},
    }
    nb.cells = [
        markdown(
            """
            # Stage 00 - Data Split Label Freeze

            Route: `lst_models` V2
            Scope: `validation_only`
            User-facing notebook: `notebooks/00_data_split_label_freeze_colab.ipynb`

            This notebook freezes raw-data provenance, 1-minute to 5-minute bar
            construction, chronological split boundaries, endpoint
            cumulative-return labels, label invalidation flags, and the mandatory
            trivial baseline registry. It does not perform feature/window search,
            model selection, HPO, official-validation readout, or holdout/test
            analysis.
            """
        ),
        markdown(
            """
            ## Protocol Summary

            Stage 00 consumes the Drive file-ID manifest from
            `configs/lst_models_data.yaml` and the frozen protocol from
            `docs/protocols/00_data_split_label_freeze_protocol.md`.

            Frozen rules:

            - ticker universe: `CSCO`, `JPM`, `KO`, `MSFT`, `WMT`
            - canonical bars: regular-session 1-minute `.txt` files resampled to 5-minute OHLCV
            - split: chronological train / official validation / closed holdout-test boundary
            - label operator: `endpoint_cumulative_return`
            - no-trade band: invalid supervised row, not a third class
            - Stage 01 handoff: feature/window search only; no relabeling or resplitting
            """
        ),
        code(
            f"""
            from pathlib import Path
            import importlib
            import subprocess
            import sys
            import zipfile

            RUN_PROJECT_BOOTSTRAP = True
            PROJECT_BOOTSTRAP_MODE = "github_commit"  # github_commit | drive_bundle | manual_upload | already_present

            PROJECT_REPO_URL = "https://github.com/zkc768/lstm-zhang.git"
            PROJECT_REPO_COMMIT = "{PROJECT_REPO_COMMIT}"
            PROJECT_ROOT = Path("/content/lst_models")
            PROJECT_DRIVE_BUNDLE_FILE_ID = ""
            PROJECT_DRIVE_BUNDLE_NAME = "lst_models_stage00_colab_project.zip"

            RUN_DOWNLOAD = False
            RUN_STAGE00 = False
            RUN_STAGE00_DRIVE_BACKUP = True

            STAGE_NAME = "00_data_split_label_freeze"
            SCOPE = "validation_only"
            HOLDOUT_TEST_CONTACT = False
            RAW_DATA_DIR = Path("/content/lst_models_raw_stock_data")
            STAGE00_DRIVE_RESULT_PATH_PARTS = ["lst_models", "results", "00_data_split_label_freeze"]


            def run_cmd(args, cwd=None):
                print("+", " ".join(str(arg) for arg in args))
                subprocess.run(args, cwd=cwd, check=True)


            def looks_like_project_root(path):
                return (
                    (path / "configs" / "stages" / "00_data_split_label_freeze.yaml").exists()
                    and (path / "configs" / "lst_models_data.yaml").exists()
                    and (path / "docs" / "protocols" / "00_data_split_label_freeze_protocol.md").exists()
                    and (path / "notebooks" / "00_data_split_label_freeze_colab.ipynb").exists()
                    and (path / "src" / "lst_models" / "stages" / "data_split_label_freeze.py").exists()
                )


            def safe_extract_project_zip(zip_path):
                destination = Path("/content").resolve()
                with zipfile.ZipFile(zip_path) as archive:
                    for member in archive.infolist():
                        member_path = Path(member.filename)
                        if member_path.is_absolute() or ".." in member_path.parts:
                            raise ValueError(f"Unsafe path in uploaded zip: {{member.filename}}")
                        target = (destination / member_path).resolve()
                        if target != destination and destination not in target.parents:
                            raise ValueError(f"Unsafe path in uploaded zip: {{member.filename}}")
                    archive.extractall(destination)
                candidates = [Path("/content/lst_models"), Path("/content") / zip_path.stem]
                for candidate in candidates:
                    if looks_like_project_root(candidate):
                        return candidate
                raise FileNotFoundError(
                    "The project bundle was extracted, but no lst_models project root was found. "
                    "The bundle must contain configs/, docs/, notebooks/, and src/."
                )


            def download_and_extract_project_zip_from_drive():
                try:
                    from google.colab import auth
                    from googleapiclient.discovery import build
                    from googleapiclient.http import MediaIoBaseDownload
                except ImportError as exc:
                    raise RuntimeError(
                        "PROJECT_BOOTSTRAP_MODE='drive_bundle' only works inside Colab "
                        "with Google Drive API dependencies available."
                    ) from exc

                file_id = PROJECT_DRIVE_BUNDLE_FILE_ID.strip()
                if not file_id:
                    raise ValueError(
                        "PROJECT_DRIVE_BUNDLE_FILE_ID is required when "
                        "PROJECT_BOOTSTRAP_MODE='drive_bundle'."
                    )
                auth.authenticate_user()
                service = build("drive", "v3")
                zip_path = Path("/content") / PROJECT_DRIVE_BUNDLE_NAME
                request = service.files().get_media(fileId=file_id)
                with zip_path.open("wb") as file_handle:
                    downloader = MediaIoBaseDownload(file_handle, request)
                    done = False
                    while not done:
                        _, done = downloader.next_chunk()
                return safe_extract_project_zip(zip_path)


            def upload_and_extract_project_zip():
                try:
                    from google.colab import files
                except ImportError as exc:
                    raise RuntimeError(
                        "PROJECT_BOOTSTRAP_MODE='manual_upload' only works inside Colab."
                    ) from exc

                uploaded = files.upload()
                if not uploaded:
                    raise FileNotFoundError("No project zip was uploaded.")
                zip_names = [name for name in uploaded if name.endswith(".zip")]
                if not zip_names:
                    raise ValueError("Upload a .zip file containing the lst_models project folder.")
                zip_path = Path("/content") / zip_names[0]
                return safe_extract_project_zip(zip_path)


            if RUN_PROJECT_BOOTSTRAP:
                if PROJECT_BOOTSTRAP_MODE == "github_commit":
                    if (PROJECT_ROOT / ".git").exists():
                        run_cmd(["git", "fetch", "origin"], cwd=PROJECT_ROOT)
                        run_cmd(["git", "checkout", PROJECT_REPO_COMMIT], cwd=PROJECT_ROOT)
                    else:
                        run_cmd(["git", "clone", PROJECT_REPO_URL, str(PROJECT_ROOT)])
                        run_cmd(["git", "checkout", PROJECT_REPO_COMMIT], cwd=PROJECT_ROOT)
                    actual_commit = subprocess.check_output(
                        ["git", "rev-parse", "HEAD"],
                        cwd=PROJECT_ROOT,
                        text=True,
                    ).strip()
                    assert actual_commit == PROJECT_REPO_COMMIT, (actual_commit, PROJECT_REPO_COMMIT)
                elif PROJECT_BOOTSTRAP_MODE == "drive_bundle":
                    PROJECT_ROOT = download_and_extract_project_zip_from_drive()
                elif PROJECT_BOOTSTRAP_MODE == "manual_upload":
                    PROJECT_ROOT = upload_and_extract_project_zip()
                elif PROJECT_BOOTSTRAP_MODE == "already_present":
                    pass
                else:
                    raise ValueError(
                        "PROJECT_BOOTSTRAP_MODE must be one of: "
                        "github_commit, drive_bundle, manual_upload, already_present"
                    )

            STAGE_CONFIG_PATH = PROJECT_ROOT / "configs" / "stages" / "00_data_split_label_freeze.yaml"
            RAW_DATA_MANIFEST_PATH = PROJECT_ROOT / "configs" / "lst_models_data.yaml"
            PROTOCOL_PATH = PROJECT_ROOT / "docs" / "protocols" / "00_data_split_label_freeze_protocol.md"
            NOTEBOOK_PATH = PROJECT_ROOT / "notebooks" / "00_data_split_label_freeze_colab.ipynb"

            REQUIRED_PROJECT_FILES = [
                STAGE_CONFIG_PATH,
                RAW_DATA_MANIFEST_PATH,
                PROTOCOL_PATH,
                NOTEBOOK_PATH,
                PROJECT_ROOT / "src" / "lst_models" / "stages" / "data_split_label_freeze.py",
            ]
            missing_project_files = [path for path in REQUIRED_PROJECT_FILES if not path.exists()]
            if missing_project_files:
                missing_text = "\\n".join(f"- {{path}}" for path in missing_project_files)
                raise FileNotFoundError(
                    "Stage 00 bootstrap target is missing required package sidecars. "
                    "For normal Colab use, push the full stage bundle to GitHub and update "
                    "PROJECT_REPO_COMMIT to that exact commit. Drive bundle/manual upload "
                    "are fallback modes only. "
                    f"Missing files:\\n{{missing_text}}"
                )

            SRC_PATH = PROJECT_ROOT / "src"
            if str(SRC_PATH) not in sys.path:
                sys.path.insert(0, str(SRC_PATH))

            def clear_project_import_cache():
                cached = [
                    name
                    for name in sys.modules
                    if name == "lst_models" or name.startswith("lst_models.")
                ]
                for name in cached:
                    del sys.modules[name]
                importlib.invalidate_caches()

            clear_project_import_cache()

            print("PROJECT_ROOT:", PROJECT_ROOT)
            print("PROJECT_BOOTSTRAP_MODE:", PROJECT_BOOTSTRAP_MODE)
            print("PROJECT_REPO_URL:", PROJECT_REPO_URL)
            print("PROJECT_COMMIT:", PROJECT_REPO_COMMIT)
            print("SRC_PATH:", SRC_PATH)
            print("STAGE_CONFIG_PATH:", STAGE_CONFIG_PATH)
            print("RAW_DATA_MANIFEST_PATH:", RAW_DATA_MANIFEST_PATH)
            print("PROTOCOL_PATH:", PROTOCOL_PATH)
            print("NOTEBOOK_PATH:", NOTEBOOK_PATH)
            print("RAW_DATA_DIR:", RAW_DATA_DIR)
            print("STAGE00_DRIVE_RESULT_PATH_PARTS:", STAGE00_DRIVE_RESULT_PATH_PARTS)
            print("RUN_PROJECT_BOOTSTRAP:", RUN_PROJECT_BOOTSTRAP)
            print("RUN_DOWNLOAD:", RUN_DOWNLOAD)
            print("RUN_STAGE00:", RUN_STAGE00)
            print("RUN_STAGE00_DRIVE_BACKUP:", RUN_STAGE00_DRIVE_BACKUP)
            """
        ),
        markdown(
            """
            ## Raw File Download

            The default setup does not mount Drive and does not scan Drive folders.
            If running in Colab, set `RUN_DOWNLOAD = True` in the bootstrap cell
            to authenticate with the Google Drive API and download the five raw
            `.txt` files by file ID into `/content/lst_models_raw_stock_data`.
            """
        ),
        code(
            """
            RAW_DRIVE_FILES = {
                "CSCO": {"name": "CSCO.txt", "file_id": "17A49kUiMELuQqdkOhw1KrpudjP5i5xIN"},
                "JPM": {"name": "JPM.txt", "file_id": "11UQUJKVXTrBb8XFWY5Z8JDQ8_4i_DE-q"},
                "KO": {"name": "KO.txt", "file_id": "1XmtwuZ2dTP20NsU27w5dMyRdSvdnNTSn"},
                "MSFT": {"name": "MSFT.txt", "file_id": "1Ud1SQpQbaiRKemFf9dgu1o_raUPnFvGs"},
                "WMT": {"name": "WMT.txt", "file_id": "1NNfsoUJrrsj2ae5EnC-PTPcZs_QGR_7c"},
            }


            def download_drive_file(file_id, output_path):
                from google.colab import auth
                from googleapiclient.discovery import build
                from googleapiclient.http import MediaIoBaseDownload

                auth.authenticate_user()
                service = build("drive", "v3")
                request = service.files().get_media(fileId=file_id)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with output_path.open("wb") as handle:
                    downloader = MediaIoBaseDownload(handle, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                        if status:
                            print(f"{output_path.name}: {int(status.progress() * 100)}%")
                return output_path


            if RUN_DOWNLOAD:
                RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
                downloaded = []
                for ticker, item in RAW_DRIVE_FILES.items():
                    path = RAW_DATA_DIR / item["name"]
                    downloaded.append(download_drive_file(item["file_id"], path))
                print("Downloaded files:")
                for path in downloaded:
                    print("-", path)
            else:
                print("RUN_DOWNLOAD=False; raw files were not downloaded in this committed notebook.")
            """
        ),
        markdown(
            """
            ## Stage 00 Invocation

            `RUN_STAGE00` is `False` in the committed notebook. When enabled after
            raw files are present, the stage writes a compact artifact bundle under
            `/content/lst_models_results/00_data_split_label_freeze/<run_id>/`.
            """
        ),
        code(
            """
            from lst_models.config import load_yaml
            from lst_models.stages.data_split_label_freeze import run_stage

            stage_config = load_yaml(STAGE_CONFIG_PATH)
            stage_config["inputs"]["raw_data_manifest"] = str(RAW_DATA_MANIFEST_PATH)
            stage_config["inputs"]["notebook_path"] = str(NOTEBOOK_PATH)
            stage_config["inputs"]["raw_data_dir"] = str(RAW_DATA_DIR)
            stage_config["provenance"] = {
                "repo_url": PROJECT_REPO_URL,
                "git_commit": PROJECT_REPO_COMMIT,
                "bootstrap_mode": PROJECT_BOOTSTRAP_MODE,
            }

            assert stage_config["stage_name"] == STAGE_NAME
            assert stage_config["scope"] == SCOPE
            assert stage_config["holdout_test_contact"] is HOLDOUT_TEST_CONTACT
            assert stage_config["label_policy"]["operator"] == "endpoint_cumulative_return"
            assert len(stage_config["stage01_handoff"]["must_not_search"]) >= 5

            if RUN_STAGE00:
                result = run_stage(stage_config)
                print("Stage 00 output directory:", result.output_dir)
                print("Run manifest:", result.run_manifest)
                print("Artifact inventory:", result.artifact_inventory)
                print("Sample event index:", result.sample_event_index)
                print("Label validity summary:", result.label_validity_summary)
            else:
                result = None
                print("RUN_STAGE00=False; Stage 00 was not executed in this committed notebook.")
            """
        ),
        code(
            """
            # Stage 00 Drive Result Backup
            def get_drive_service_for_stage00_result_backup():
                try:
                    from google.colab import auth
                    from googleapiclient.discovery import build
                except ImportError as exc:
                    raise RuntimeError(
                        "RUN_STAGE00_DRIVE_BACKUP=True only works inside Colab with Google API dependencies."
                    ) from exc
                auth.authenticate_user()
                return build("drive", "v3")


            def quote_drive_query_value(value):
                return str(value).replace("\\\\", "\\\\\\\\").replace("'", "\\\\'")


            def find_stage00_result_drive_child(service, parent_id, name, mime_type=None):
                escaped_name = quote_drive_query_value(name)
                query_parts = [f"name = '{escaped_name}'", f"'{parent_id}' in parents", "trashed = false"]
                if mime_type:
                    query_parts.append(f"mimeType = '{mime_type}'")
                response = service.files().list(
                    q=" and ".join(query_parts),
                    fields="files(id, name, mimeType, size, webViewLink)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    pageSize=10,
                ).execute()
                return response.get("files", [])


            def ensure_stage00_result_drive_folder(service, parent_id, name):
                folder_mime = "application/vnd.google-apps.folder"
                matches = find_stage00_result_drive_child(service, parent_id, name, folder_mime)
                if len(matches) == 1:
                    return matches[0]["id"]
                if len(matches) > 1:
                    raise RuntimeError(f"Duplicate Drive folders named {name!r} under parent {parent_id}")
                created = service.files().create(
                    body={"name": name, "mimeType": folder_mime, "parents": [parent_id]},
                    fields="id, name, webViewLink",
                    supportsAllDrives=True,
                ).execute()
                print("Created Drive folder:", name, created.get("webViewLink"))
                return created["id"]


            def ensure_stage00_result_drive_path(service, path_parts):
                folder_id = "root"
                for part in path_parts:
                    folder_id = ensure_stage00_result_drive_folder(service, folder_id, part)
                return folder_id


            def upload_or_update_stage00_result_file(service, drive_folder_id, run_dir, local_path):
                from googleapiclient.http import MediaFileUpload

                relative_path = local_path.relative_to(run_dir)
                matches = find_stage00_result_drive_child(service, drive_folder_id, relative_path.name)
                media = MediaFileUpload(str(local_path), resumable=True)
                if len(matches) == 0:
                    uploaded = service.files().create(
                        body={"name": relative_path.name, "parents": [drive_folder_id]},
                        media_body=media,
                        fields="id, name, size, webViewLink",
                        supportsAllDrives=True,
                    ).execute()
                    action = "uploaded"
                elif len(matches) == 1:
                    uploaded = service.files().update(
                        fileId=matches[0]["id"],
                        media_body=media,
                        fields="id, name, size, webViewLink",
                        supportsAllDrives=True,
                    ).execute()
                    action = "updated"
                else:
                    raise RuntimeError(f"Duplicate Drive files named {relative_path.name!r} under parent {drive_folder_id}")
                uploaded = dict(uploaded)
                uploaded["relative_path"] = relative_path.as_posix()
                uploaded["uploaded_byte_size"] = int(local_path.stat().st_size)
                print(f"{action}: {relative_path.as_posix()}")
                return uploaded


            def backup_stage00_results_to_drive(output_run_dir):
                from datetime import datetime, timezone
                import json

                run_dir = Path(output_run_dir)
                if not run_dir.exists():
                    raise FileNotFoundError(f"Stage 00 output folder not found: {run_dir}")
                required_stage00_files = [
                    stage_config["outputs"]["manifest"],
                    stage_config["outputs"]["artifact_inventory"],
                    stage_config["outputs"]["raw_data_manifest"],
                    stage_config["outputs"]["split_freeze"],
                    stage_config["outputs"]["label_policy"],
                    stage_config["outputs"]["baseline_registry"],
                    stage_config["outputs"]["label_validity_summary"],
                    stage_config["outputs"]["sample_event_index"],
                ]
                missing = [name for name in required_stage00_files if not (run_dir / name).exists()]
                if missing:
                    raise FileNotFoundError(f"Missing required Stage 00 artifacts before Drive backup: {missing}")
                run_manifest_path = run_dir / stage_config["outputs"]["manifest"]
                run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
                if run_manifest.get("holdout_test_contact") is not False:
                    raise ValueError(f"Stage 00 result backup requires holdout_test_contact=false: {run_manifest_path}")
                service = get_drive_service_for_stage00_result_backup()
                drive_path_parts = STAGE00_DRIVE_RESULT_PATH_PARTS + [run_dir.name]
                drive_folder_id = ensure_stage00_result_drive_path(service, drive_path_parts)
                backup_manifest_path = run_dir / "drive_backup_manifest.json"
                local_files = sorted(path for path in run_dir.rglob("*") if path.is_file() and path.name != backup_manifest_path.name)
                uploads = [upload_or_update_stage00_result_file(service, drive_folder_id, run_dir, path) for path in local_files]
                backup_manifest = {
                    "stage_name": STAGE_NAME,
                    "run_id": run_dir.name,
                    "stage_run_id": run_dir.name,
                    "local_output_dir": str(run_dir),
                    "drive_path": "My Drive/" + "/".join(drive_path_parts),
                    "drive_path_parts": drive_path_parts,
                    "drive_folder_id": drive_folder_id,
                    "uploaded_file_names": [upload["name"] for upload in uploads],
                    "uploaded_file_ids": [upload["id"] for upload in uploads],
                    "uploaded_byte_sizes": [upload["uploaded_byte_size"] for upload in uploads],
                    "uploaded_files": uploads,
                    "sync_timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "holdout_test_contact": run_manifest.get("holdout_test_contact"),
                }
                backup_manifest_path.write_text(json.dumps(backup_manifest, indent=2), encoding="utf-8")
                manifest_upload = upload_or_update_stage00_result_file(service, drive_folder_id, run_dir, backup_manifest_path)
                backup_manifest["uploaded_files"].append(manifest_upload)
                backup_manifest["uploaded_file_names"].append(manifest_upload["name"])
                backup_manifest["uploaded_file_ids"].append(manifest_upload["id"])
                backup_manifest["uploaded_byte_sizes"].append(manifest_upload["uploaded_byte_size"])
                backup_manifest_path.write_text(json.dumps(backup_manifest, indent=2), encoding="utf-8")
                upload_or_update_stage00_result_file(service, drive_folder_id, run_dir, backup_manifest_path)
                print("stage_run_id:", backup_manifest["stage_run_id"])
                print("drive_path:", backup_manifest["drive_path"])
                print("drive_folder_id:", backup_manifest["drive_folder_id"])
                return backup_manifest


            if RUN_STAGE00_DRIVE_BACKUP and RUN_STAGE00:
                if result is None:
                    raise RuntimeError("RUN_STAGE00_DRIVE_BACKUP=True requires a successful Stage 00 run.")
                stage00_drive_backup_manifest = backup_stage00_results_to_drive(result.output_dir)
            else:
                print("RUN_STAGE00_DRIVE_BACKUP is disabled or RUN_STAGE00=False; no Stage 00 result backup uploaded.")
            """
        ),
        markdown(
            """
            ## Artifact Review

            After a real Stage 00 run, inspect the artifact inventory and
            label-validity summary before handing artifacts to Stage 01. Stage 01
            may search only `feature_set`, `window_size`, and lightweight
            train-inner shape/signal checks.
            """
        ),
        code(
            """
            if result is not None:
                import pandas as pd

                inventory = pd.read_csv(result.artifact_inventory)
                label_summary = pd.read_csv(result.label_validity_summary)
                display(inventory)
                display(label_summary)
            else:
                print("No artifacts to display because RUN_STAGE00=False.")
            """
        ),
        markdown(
            """
            ## Handoff To Stage 01

            Stage 01 receives the frozen split and label artifacts from Stage 00.
            It must not change `endpoint_cumulative_return`, `horizon_k`,
            `no_trade_band_bps`, split boundaries, invalidation rules, or
            holdout/test wording. If Stage 00 produces empty train or validation
            supervised rows, stop and fix the Stage 00 protocol/config before
            running Stage 01.
            """
        ),
    ]
    for cell in nb.cells:
        cell.metadata = {}
    return nb


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    output_path = root / "notebooks" / "00_data_split_label_freeze_colab.ipynb"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(build_notebook(), output_path)
    print(output_path)


if __name__ == "__main__":
    main()
