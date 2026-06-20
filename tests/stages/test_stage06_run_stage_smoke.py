"""Stage 06 progress-record run_stage smoke tests.

Exercises the REAL committed config (honesty, closure, Ian mapping, forbidden
wording) against synthetic frozen upstream run folders with real sha256
inventories: the reproducibility inventory (per-artifact sha256 + git_commit),
the pending_drive_fetch path for an absent run, the Ian mapping, the progress
record, manifest provenance, and fail-closed wording/contract gates. No fits,
no scoring, no holdout contact.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models import synthesis  # noqa: E402
from lst_models.artifacts import write_artifact_inventory, write_json  # noqa: E402
from lst_models.stages import ian_final_progress_record as stage06  # noqa: E402
from lst_models.stages.ian_final_progress_record import run_stage  # noqa: E402

CONFIG_PATH = ROOT / "configs" / "stages" / "06_ian_final_progress_record.yaml"


def _make_upstream(tmp: Path, stage: str, run_id: str, artifacts: dict, git_commit: str = "abc1234") -> Path:
    run_dir = tmp / stage / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / "run_manifest.json", {"stage_name": stage, "run_id": run_id, "git_commit": git_commit})
    for name, payload in artifacts.items():
        write_json(run_dir / name, payload)
    names = ["run_manifest.json"] + list(artifacts)
    write_artifact_inventory(run_dir, {n: run_dir / n for n in names})
    return run_dir


def _config(tmp: Path) -> dict:
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    present1 = _make_upstream(
        tmp, "03_frozen_validation_readout", "20260610_133305_716174",
        {"03_decision_record.json": {"decision": "met"}},
    )
    present2 = _make_upstream(
        tmp, "v2_1_guarded_walkforward_readout", "20260618_063559_889276",
        {"v2_1_decision_record.json": {"decision": "met"}}, git_commit="def5678",
    )
    missing = tmp / "05_thesis_synthesis" / "20260619_090454_562658"  # not created -> pending
    cfg["inputs"]["upstream_runs"] = [
        {"stage_name": "03_frozen_validation_readout", "run_id": "20260610_133305_716174",
         "drive_folder_id": "DRV03", "runtime_run_dir": str(present1)},
        {"stage_name": "v2_1_guarded_walkforward_readout", "run_id": "20260618_063559_889276",
         "drive_folder_id": "DRVv2", "runtime_run_dir": str(present2)},
        {"stage_name": "05_thesis_synthesis", "run_id": "20260619_090454_562658",
         "drive_folder_id": "DRV05", "runtime_run_dir": str(missing)},
    ]
    cfg["inputs"]["notebook_path"] = str(tmp / "06_nb.ipynb")
    cfg["outputs"]["output_dir"] = str(tmp / "out")
    return cfg


def _run_dir(cfg: dict) -> Path:
    out = Path(cfg["outputs"]["output_dir"])
    dirs = [d for d in out.iterdir() if d.is_dir()]
    assert len(dirs) == 1, f"expected one run folder, got {len(dirs)}"
    return dirs[0]


def test_happy_path_writes_artifacts_and_inventory(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    result = run_stage(cfg)
    run_dir = _run_dir(cfg)
    assert result.run_dir == run_dir
    for name in stage06.REQUIRED_STAGE06_ARTIFACTS:
        assert (run_dir / name).exists(), name
    inv = pd.read_csv(run_dir / "06_reproducibility_inventory.csv")
    assert list(inv.columns) == stage06.REPRO_INVENTORY_COLUMNS
    # present runs -> per-artifact rows with real sha256 + git_commit read from manifest
    present = inv[inv["stage_name"] == "03_frozen_validation_readout"]
    assert len(present) >= 2  # run_manifest.json + 03_decision_record.json
    assert (present["sha256_status"] == "present").all()
    assert present["sha256"].astype(str).str.len().gt(0).all()
    assert "abc1234" in set(present["git_commit"].astype(str))
    assert "def5678" in set(inv["git_commit"].astype(str))
    # absent run -> single pending_drive_fetch row, never a fabricated hash
    pend = inv[inv["stage_name"] == "05_thesis_synthesis"]
    assert len(pend) == 1
    assert pend.iloc[0]["sha256_status"] == "pending_drive_fetch"
    assert str(pend.iloc[0]["sha256"]) in ("", "nan")


def test_progress_record_honesty_and_flags(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    run_stage(cfg)
    rec = json.loads((_run_dir(cfg) / "06_progress_record.json").read_text(encoding="utf-8"))
    assert rec["scope"] == "progress_record_measure_only"
    assert rec["new_scoring_events"] == 0
    assert rec["holdout_test_contact"] is False
    assert rec["no_final_model_selected"] is True
    assert rec["clean_test_claim"] is False
    assert rec["n_pending_drive_fetch"] == 1
    assert "v2_1_guarded_walkforward_readout" in rec["stages_inventoried"]
    assert rec["honesty_statement"].strip() and rec["route_closure_statement"].strip()


def test_ian_mapping_and_manifest(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    run_stage(cfg)
    run_dir = _run_dir(cfg)
    mp = pd.read_csv(run_dir / "06_ian_requirement_mapping.csv")
    assert list(mp.columns) == stage06.IAN_MAPPING_COLUMNS
    assert len(mp) == len(cfg["ian_requirement_mapping"]["rows"])
    man = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert man["stage_name"] == "06_ian_final_progress_record"
    assert man["scope"] == "progress_record_measure_only"
    assert man["holdout_test_contact"] is False
    assert man["no_final_model_selected"] is True
    for field in ("git_commit", "config_sha256", "stages_inventoried", "output_artifacts"):
        assert field in man


def test_no_forbidden_wording_in_any_output(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    forbidden = cfg["forbidden"]["wording"]
    run_stage(cfg)
    run_dir = _run_dir(cfg)
    for name in ("06_progress_record.json", "06_ian_requirement_mapping.csv",
                 "06_reproducibility_inventory.csv"):
        text = (run_dir / name).read_text(encoding="utf-8")
        assert not synthesis.find_forbidden_wording(text, forbidden), name


def test_fails_closed_on_forbidden_wording_in_honesty(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    cfg["honesty_statement"] = "This is the final model and it is profitable."
    with pytest.raises(ValueError, match="forbidden wording"):
        run_stage(cfg)


def test_fails_closed_on_forbidden_wording_in_mapping(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    cfg["ian_requirement_mapping"]["rows"][0]["status"] = "this is the chosen threshold"
    with pytest.raises(ValueError, match="forbidden wording"):
        run_stage(cfg)


def test_fails_closed_on_empty_upstream_runs(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    cfg["inputs"]["upstream_runs"] = []
    with pytest.raises(ValueError, match="upstream_runs"):
        run_stage(cfg)


def test_fails_closed_on_wrong_scope(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    cfg["scope"] = "synthesis_measure_only"
    with pytest.raises(ValueError, match="scope"):
        run_stage(cfg)


def test_fails_closed_on_holdout_contact_true(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    cfg["holdout_test_contact"] = True
    with pytest.raises(ValueError, match="holdout_test_contact"):
        run_stage(cfg)
