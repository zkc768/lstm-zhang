"""Post-hoc correction of a V2.1 run manifest's device provenance fields.

Background: before the fix in ``guarded_walkforward._refit_record``, the per-fit
``refit_records`` omitted the device keys, so the manifest aggregation
(``_readout_device_fields``) found nothing and recorded
``resolved_device='not_resolved'`` / ``cuda_available=False`` even when the run
actually fit on cuda. The per-fit truth was still written to
``v2_1_walkforward_readout.csv`` (``requested_device`` / ``resolved_device`` /
``device_fallback_reason`` per row).

This tool recomputes the manifest device fields from that readout CSV and patches
``run_manifest.json`` in place, recording a transparent ``device_fields_correction``
block and updating the ``run_manifest.json`` row of ``artifact_inventory.csv`` so
the run stays internally consistent. It is idempotent (skips if already corrected).

Note: the run's GPU *name* is NOT recoverable from the run's own artifacts (the
bug dropped it and the readout CSV does not carry it), so ``gpu_name_or_null`` is
left null with a note. ``resolved_device`` and ``cuda_available`` ARE recoverable.

    python -m scripts.backfill_run_device_fields --run-dir "<path to run folder>"
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEVICE_FIELDS = (
    "requested_device", "resolved_device", "cuda_available",
    "gpu_name_or_null", "device_fallback_reason",
)


def _aggregate_from_readout(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Mirror ``guarded_walkforward._readout_device_fields`` but source the
    per-fit device fields from the readout rows (which carry them) and leave the
    GPU name null (the run's actual GPU name is not recorded in the readout)."""
    completed = [r for r in rows if r.get("fit_status") == "completed"]
    requested = sorted({r["requested_device"] for r in completed if r.get("requested_device")})
    resolved = sorted({r["resolved_device"] for r in completed if r.get("resolved_device")})
    fallbacks = sorted({r["device_fallback_reason"] for r in completed if r.get("device_fallback_reason")})
    resolved_device = ",".join(resolved) if resolved else "not_resolved"
    cuda_resolved = any(v.strip().startswith("cuda") for v in resolved_device.split(","))
    return {
        "requested_device": ",".join(requested) if requested else "not_resolved",
        "resolved_device": resolved_device,
        "cuda_available": bool(cuda_resolved),
        "gpu_name_or_null": None,
        "device_fallback_reason": ",".join(fallbacks),
        "_completed_fits": len(completed),
    }


def backfill_run_device_fields(run_dir: str | Path) -> dict[str, Any]:
    run = Path(run_dir)
    readout = run / "v2_1_walkforward_readout.csv"
    manifest_path = run / "run_manifest.json"
    if not readout.exists() or not manifest_path.exists():
        raise FileNotFoundError(f"run folder missing readout/manifest: {run}")

    with readout.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    agg = _aggregate_from_readout(rows)
    completed_fits = agg.pop("_completed_fits")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if "device_fields_correction" in manifest:
        return {"status": "already_corrected", "run_dir": str(run)}

    prior = {k: manifest.get(k) for k in DEVICE_FIELDS}
    for k in DEVICE_FIELDS:
        manifest[k] = agg[k]
    manifest["device_fields_correction"] = {
        "corrected_on_utc": datetime.now(timezone.utc).isoformat(),
        "reason": (
            "run_manifest device fields recorded 'not_resolved'/cuda_available=False "
            "because the v2.1 refit_records omitted the per-fit device keys "
            "(guarded_walkforward._refit_record), so _readout_device_fields found no "
            "device info. Recomputed from per-fit v2_1_walkforward_readout.csv."
        ),
        "source": "v2_1_walkforward_readout.csv",
        "completed_fits_used": completed_fits,
        "prior_values": prior,
        "corrected_values": agg,
        "gpu_name_note": (
            "the run's GPU name is not recoverable (dropped by the bug; not in the "
            "readout CSV), left null; same-session Stage 01/02/03 recorded 'Tesla T4'."
        ),
    }

    text = json.dumps(manifest, indent=2)
    manifest_path.write_bytes(text.encode("utf-8"))
    new_bytes = len(text.encode("utf-8"))
    new_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()

    inv_path = run / "artifact_inventory.csv"
    if inv_path.exists():
        with inv_path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            fieldnames = reader.fieldnames
            inv = list(reader)
        for r in inv:
            if r.get("file_name") == "run_manifest.json":
                if "bytes" in r:
                    r["bytes"] = str(new_bytes)
                if "sha256" in r:
                    r["sha256"] = new_sha
        with inv_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(inv)

    return {
        "status": "corrected",
        "run_dir": str(run),
        "prior": prior,
        "corrected": agg,
        "manifest_bytes": new_bytes,
        "manifest_sha256": new_sha,
    }


if __name__ == "__main__":  # pragma: no cover - CLI convenience
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", required=True, help="path to the V2.1 run folder")
    args = ap.parse_args()
    out = backfill_run_device_fields(args.run_dir)
    print(json.dumps(out, indent=2, default=str))
