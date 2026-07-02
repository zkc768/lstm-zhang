"""V2 half-spread settlement-control orchestration (measure-only).

Runs the pre-registered half-spread settlement control
(``docs/protocols/v2_halfspread_control_preregistration_20260701.md``): a
Roll (1984) half-spread proxy from raw 5-minute bars re-slices the FROZEN
per-row prediction dumps against the frozen +/-3.0 bps no-trade band. Zero
new fit/predict events, no reselection, no operating point. Measurement
logic lives in ``lst_models.microstructure``; this module owns config gates,
domain loading, the dummy replay wiring, and artifact/manifest writing only.

One domain per invocation (``run_domain`` injected by the notebook):
``validation`` (primary; ``holdout_test_contact=false``) or ``guarded``
(secondary, non-independent; tier ``guarded_historically_contacted``). The
two domains write separate run folders and are never pooled.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from lst_models import diagnostics, metrics, microstructure, synthesis
from lst_models.artifacts import (
    git_commit_fields,
    make_run_id,
    package_versions,
    read_json_object,
    require_artifacts,
    write_artifact_inventory,
    write_json,
)
from lst_models.config import hash_file, hash_mapping, require_mapping, resolve_repo_path
from lst_models.data import (
    load_sample_event_index,
    load_stage01_summary,
    load_train_bars,
    load_train_validation_bars,
    read_raw_txt_file,
    resample_1min_to_5min,
    verify_raw_file_integrity,
)
from lst_models.features import build_feature_frame
from lst_models.splits import valid_events_for_split
from lst_models.windows import build_window_dataset, validate_rebuilt_candidate_counts

STAGE_NAME = "v2_halfspread_control"
SCOPE = "halfspread_control_measure_only"
DOMAINS = ("validation", "guarded")
HOLDOUT_BOUNDARY = pd.Timestamp("2017-01-25")
DUMMY_BASELINE_ID = "stratified_dummy_train_prior"

GUARDED_PREDICTION_USECOLS = [
    "table_row_id", "period_id", "seed", "sample_id", "ticker",
    "trading_day", "y_true", "y_pred",
]
GUARDED_BASELINE_USECOLS = [
    "baseline_id", "period_id", "seed", "sample_id", "ticker",
    "trading_day", "y_true", "y_pred",
]

REQUIRED_HALFSPREAD_ARTIFACTS = [
    "run_manifest.json",
    "artifact_inventory.csv",
    "halfspread_day_spread.csv",
    "halfspread_partition_readout.csv",
    "halfspread_low_tercile_readout.csv",
    "halfspread_occupancy.csv",
    "halfspread_autocov_by_tercile.csv",
    "halfspread_cs_robustness_readout.csv",
    "halfspread_verdict.json",
]


@dataclass(frozen=True)
class HalfspreadResult:
    run_dir: Path
    run_manifest: Path
    verdict_record: Path


def run_stage(config: Mapping[str, Any]) -> HalfspreadResult:
    _validate_config(config)
    domain = str(config["run_domain"])
    block = require_mapping(require_mapping(config["domains"], "domains")[domain], f"domains.{domain}")
    paths = _verify_entry_gates(config, domain, block)
    raw_manifest = _load_raw_manifest(config)

    bars = _load_domain_bars(config, domain, block, raw_manifest, paths)
    day_spread = _day_spread_frame(config, bars)

    if domain == "validation":
        frame, dump_hashes, replay_status = _load_validation_frame(config, block, paths, raw_manifest)
        model_rows = [str(require_mapping(config["readout"], "readout")["primary_model_row"])]
    else:
        frame, dump_hashes = _load_guarded_frames(block, paths)
        replay_status = "not_applicable_baseline_dump_exists"
        model_rows = [str(row) for row in block["model_rows"]]

    frame = microstructure.attach_day_column_to_dump(
        frame, day_spread, column="cell", context=f"{domain} roll partition"
    )
    frame = microstructure.attach_day_column_to_dump(
        frame, day_spread.rename(columns={"cs_cell": "_cs_cell"}),
        column="_cs_cell", context=f"{domain} cs partition",
    ).rename(columns={"_cs_cell": "cs_cell"})
    frame = _attach_activity_terciles(frame, domain, model_rows[0])

    tables = _build_readouts(config, block, frame, bars, model_rows, day_spread)
    verdict = _verdict_record(config, domain, tables["low_tercile_readout"])
    return _write_outputs(
        config, domain, block, tables, verdict, day_spread, dump_hashes, replay_status
    )


def _validate_config(config: Mapping[str, Any]) -> None:
    if str(config.get("stage_name")) != STAGE_NAME:
        raise ValueError(f"config stage_name must be {STAGE_NAME}")
    if str(config.get("scope")) != SCOPE:
        raise ValueError(f"{STAGE_NAME} requires scope={SCOPE}")
    if int(config.get("new_scoring_events", -1)) != 0:
        raise ValueError(f"{STAGE_NAME} requires new_scoring_events=0")
    if int(config.get("official_validation_scoring_events", -1)) != 0:
        raise ValueError(f"{STAGE_NAME} requires official_validation_scoring_events=0")
    if config.get("no_final_model_selected") is not True:
        raise ValueError(f"{STAGE_NAME} requires no_final_model_selected=true")
    if config.get("official_validation_for_selection") is not False:
        raise ValueError(f"{STAGE_NAME} requires official_validation_for_selection=false")
    domain = config.get("run_domain")
    if domain not in DOMAINS:
        raise ValueError(
            "run_domain must be injected by the notebook as 'validation' or 'guarded' "
            f"(repo config keeps it null / un-armed); got {domain!r}"
        )
    domains = require_mapping(config["domains"], "domains")
    block = require_mapping(domains[str(domain)], f"domains.{domain}")
    if domain == "validation":
        if block.get("holdout_test_contact") is not False:
            raise ValueError("validation domain requires holdout_test_contact=false")
    else:
        if block.get("holdout_test_contact") is not True:
            raise ValueError("guarded domain must declare holdout_test_contact=true")
        if str(block.get("holdout_contact_tier")) != "guarded_historically_contacted":
            raise ValueError(
                "guarded domain requires holdout_contact_tier=guarded_historically_contacted"
            )
        if block.get("clean_test_claim") is not False:
            raise ValueError("guarded domain requires clean_test_claim=false")
    estimator = require_mapping(config["estimator"], "estimator")
    label_policy = require_mapping(config["label_policy"], "label_policy")
    if float(estimator["band_bps"]) != float(label_policy["no_trade_band_bps"]):
        raise ValueError(
            "estimator.band_bps must equal the frozen label_policy.no_trade_band_bps"
        )
    require_mapping(config["readout"], "readout")
    require_mapping(config["inputs"], "inputs")
    require_mapping(config["outputs"], "outputs")
    forbidden = list(require_mapping(config["forbidden"], "forbidden")["wording"])
    if not forbidden:
        raise ValueError("forbidden wording list must be non-empty")


def _verify_entry_gates(
    config: Mapping[str, Any], domain: str, block: Mapping[str, Any]
) -> dict[str, dict[str, Path]]:
    keys = ("stage00", "stage01", "stage03") if domain == "validation" else ("v2_1",)
    paths: dict[str, dict[str, Path]] = {}
    for key in keys:
        run_dir = Path(str(block[f"{key}_runtime_run_dir"]))
        paths[key] = require_artifacts(run_dir, list(block[f"required_{key}_artifacts"]))
    return paths


def _load_raw_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    import yaml

    manifest_path = resolve_repo_path(require_mapping(config["inputs"], "inputs")["raw_data_manifest"])
    if not manifest_path.exists():
        raise FileNotFoundError(f"missing raw data manifest: {manifest_path}")
    with manifest_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _load_domain_bars(
    config: Mapping[str, Any],
    domain: str,
    block: Mapping[str, Any],
    raw_manifest: Mapping[str, Any],
    paths: Mapping[str, Mapping[str, Path]],
) -> pd.DataFrame:
    inputs = require_mapping(config["inputs"], "inputs")
    if domain == "validation":
        split_freeze = read_json_object(paths["stage00"]["split_freeze.json"])
        bars = load_train_validation_bars(raw_manifest, split_freeze, inputs)
        if pd.to_datetime(bars["timestamp"]).max() >= HOLDOUT_BOUNDARY:
            raise ValueError(
                "validation domain blocked: loaded bars reach the closed holdout boundary"
            )
        return bars
    raw_source = require_mapping(raw_manifest["raw_source"], "raw_source")
    recipe = require_mapping(raw_manifest["five_minute_recipe"], "five_minute_recipe")
    raw_data_dir = Path(str(inputs.get("raw_data_dir", raw_source["local_download_dir"])))
    end_exclusive = pd.Timestamp(str(block["window_end_exclusive"]))
    frames = []
    for ticker in raw_manifest["tickers"]:
        file_spec = require_mapping(raw_source["files"][ticker], f"raw_source.files.{ticker}")
        raw_path = raw_data_dir / str(file_spec["name"])
        verify_raw_file_integrity(raw_path, file_spec, str(ticker))
        one_minute = read_raw_txt_file(raw_path, str(ticker), raw_source)
        five_minute = resample_1min_to_5min(one_minute, recipe)
        frames.append(five_minute.loc[five_minute["timestamp"] < end_exclusive].copy())
    bars = pd.concat(frames, ignore_index=True).sort_values(["ticker", "timestamp"])
    if bars.empty:
        raise ValueError("guarded domain found no bars before window_end_exclusive")
    bars["trading_day"] = bars["timestamp"].dt.strftime("%Y-%m-%d")
    return bars.reset_index(drop=True)


def _day_spread_frame(config: Mapping[str, Any], bars: pd.DataFrame) -> pd.DataFrame:
    estimator = require_mapping(config["estimator"], "estimator")
    band_threshold = float(estimator["band_bps"]) / 10000.0
    roll = microstructure.roll_halfspread_by_day(
        bars,
        window_days=int(estimator["roll_window_days"]),
        min_pairs=int(estimator["roll_min_pairs"]),
    )
    roll = microstructure.assign_spread_partition(
        roll, band_threshold=band_threshold,
        ratio_edges=tuple(float(edge) for edge in estimator["ratio_edges"]),
    )
    cs = microstructure.corwin_schultz_halfspread_by_day(
        bars,
        window_days=int(estimator["roll_window_days"]),
        min_spans=int(estimator["cs_min_spans"]),
    )
    cs = microstructure.assign_spread_partition(
        cs, band_threshold=band_threshold,
        ratio_edges=tuple(float(edge) for edge in estimator["ratio_edges"]),
        halfspread_column="cs_halfspread", status_column="cs_status",
    ).rename(columns={"cell": "cs_cell", "spread_band_ratio": "cs_spread_band_ratio"})
    merged = roll.merge(
        cs[["ticker", "trading_day", "cs_n_spans", "cs_alpha", "cs_halfspread",
            "cs_spread_band_ratio", "cs_cell"]],
        on=["ticker", "trading_day"], how="left",
    )
    merged["cs_cell"] = merged["cs_cell"].fillna(microstructure.CELL_INSUFFICIENT)
    return merged


def _load_validation_frame(
    config: Mapping[str, Any],
    block: Mapping[str, Any],
    paths: Mapping[str, Mapping[str, Path]],
    raw_manifest: Mapping[str, Any],
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]], str]:
    record = read_json_object(paths["stage03"]["03_decision_record.json"])
    if record.get("readout_complete") is not True:
        raise ValueError("blocked: 03_decision_record.json readout_complete is not true")
    ledger = record.get("scoring_event_ledger", [])
    dump_path = paths["stage03"][str(block["dump"])]
    dump = diagnostics.gate_and_derive_dump(
        pd.read_csv(dump_path),
        expected_seeds=[int(seed) for seed in require_mapping(config["readout"], "readout")["seeds"]],
        expected_rows=block.get("expected_dump_rows"),
        ledger_rows=sum(int(event["n_rows"]) for event in ledger),
        holdout_boundary=HOLDOUT_BOUNDARY,
    )
    train_labels = _rebuild_train_labels(config, paths, raw_manifest)
    recon, status = diagnostics.reconstruct_dummy_baseline(
        dump,
        train_labels,
        pd.read_csv(paths["stage03"]["03_same_row_baselines.csv"]),
        pd.read_csv(paths["stage03"]["03_per_ticker_readout.csv"]),
        require_mapping(block["baseline_reconstruction"], "baseline_reconstruction"),
    )
    if status != "verified_identical" or recon is None:
        raise ValueError(
            "validation domain blocked (reconstruction-or-nothing, pre-registration "
            f"section 7): dummy replay status={status!r}; deltas are not computed"
        )
    dump = dump.copy()
    dump["baseline_y_pred"] = -1
    for seed, predictions in recon.items():
        seed_index = dump.index[dump["seed"].astype(int) == int(seed)]
        if len(seed_index) != len(predictions):
            raise ValueError(f"dummy replay length mismatch for seed {seed}")
        dump.loc[seed_index, "baseline_y_pred"] = predictions
    if (dump["baseline_y_pred"] < 0).any():
        raise ValueError("dummy replay left rows without a baseline prediction")
    dump["model_row"] = str(require_mapping(config["readout"], "readout")["primary_model_row"])
    hashes = {
        str(block["dump"]): {"sha256": hash_file(dump_path), "bytes": int(dump_path.stat().st_size)}
    }
    return dump, hashes, status


def _rebuild_train_labels(
    config: Mapping[str, Any],
    paths: Mapping[str, Mapping[str, Path]],
    raw_manifest: Mapping[str, Any],
) -> np.ndarray:
    """Frozen-mechanism rebuild of the windowed train labels (the exact array
    the dummy replay needs), gated against the frozen Stage 01 counts —
    the same public-domain chain Stage 04 uses."""
    inputs = require_mapping(config["inputs"], "inputs")
    sample_events = load_sample_event_index(paths["stage00"]["sample_event_index.csv"])
    train_events = valid_events_for_split(sample_events, "train")
    split_freeze = read_json_object(paths["stage00"]["split_freeze.json"])
    bars = load_train_bars(raw_manifest, split_freeze, inputs)
    feature_frame = build_feature_frame(bars)
    handoff = read_json_object(paths["stage01"]["01_candidate_inputs.json"])
    candidate_id = str(require_mapping(config["readout"], "readout")["candidate_id"])
    entries = [
        dict(entry) for entry in handoff.get("candidate_inputs", [])
        if str(entry.get("candidate_id")) == candidate_id
    ]
    if not entries:
        raise ValueError(f"candidate {candidate_id!r} not found in 01_candidate_inputs.json")
    entry = entries[0]
    dataset = build_window_dataset(
        feature_frame,
        train_events,
        feature_set=str(entry["feature_set"]),
        feature_columns=tuple(entry["feature_columns"]),
        window_size=int(entry["window_size"]),
    )
    validate_rebuilt_candidate_counts(
        entry, dataset, load_stage01_summary(paths["stage01"]["01_feature_window_search_summary.csv"])
    )
    return dataset.metadata["label"].to_numpy(dtype=int)


def _load_guarded_frames(
    block: Mapping[str, Any], paths: Mapping[str, Mapping[str, Path]]
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    pred_path = paths["v2_1"][str(block["predictions"])]
    base_path = paths["v2_1"][str(block["baseline_predictions"])]
    cand = pd.read_csv(pred_path, usecols=GUARDED_PREDICTION_USECOLS)
    base = pd.read_csv(base_path, usecols=GUARDED_BASELINE_USECOLS)
    base = base.loc[base["baseline_id"].astype(str) == DUMMY_BASELINE_ID].copy()
    if base.empty:
        raise ValueError(f"no {DUMMY_BASELINE_ID} rows in {base_path.name}")
    expected_rows = [str(row) for row in block["model_rows"]]
    observed_rows = sorted(set(cand["table_row_id"].astype(str)))
    if sorted(expected_rows) != observed_rows:
        raise ValueError(
            f"guarded dump model rows {observed_rows} != config model_rows {sorted(expected_rows)}"
        )
    observed_seeds = sorted({int(s) for s in cand["seed"].tolist()})
    if observed_seeds != [101, 202]:
        raise ValueError(f"guarded dump seeds {observed_seeds} != frozen [101, 202]")
    frame = microstructure.align_baseline_predictions(
        cand, base, on=("period_id", "seed", "sample_id"), context="guarded baseline alignment"
    )
    frame = frame.rename(columns={"table_row_id": "model_row"})
    hashes = {
        pred_path.name: {"sha256": hash_file(pred_path), "bytes": int(pred_path.stat().st_size)},
        base_path.name: {"sha256": hash_file(base_path), "bytes": int(base_path.stat().st_size)},
    }
    return frame, hashes


def _attach_activity_terciles(
    frame: pd.DataFrame, domain: str, primary_model_row: str
) -> pd.DataFrame:
    """Assign the frozen eligible-row-count activity proxy exactly as the
    existing addenda do: computed on the primary candidate rows, carried to
    every row of the frame by the (ticker, trading_day) day map."""
    if domain == "validation":
        return frame  # gate_and_derive_dump already added activity_tercile
    primary = frame.loc[frame["model_row"].astype(str) == primary_model_row]
    if primary.empty:
        raise ValueError(f"no rows for primary model {primary_model_row!r}")
    primary = primary.copy()
    primary["activity_tercile"] = diagnostics.activity_terciles(primary).astype(str)
    day_map = (
        primary.groupby(["ticker", "trading_day"])["activity_tercile"].first().reset_index()
    )
    return microstructure.attach_day_column_to_dump(
        frame, day_map, column="activity_tercile", context="guarded activity terciles"
    )


def _build_readouts(
    config: Mapping[str, Any],
    block: Mapping[str, Any],
    frame: pd.DataFrame,
    bars: pd.DataFrame,
    model_rows: list[str],
    day_spread: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    readout = require_mapping(config["readout"], "readout")
    bootstrap = require_mapping(readout["bootstrap"], "readout.bootstrap")
    evidence_domain = str(block["evidence_domain"])
    primary = str(readout["primary_model_row"])
    note = str(readout.get("descriptive_note", ""))
    common = {
        "evidence_domain": evidence_domain,
        "random_prior": float(readout.get("random_prior", 0.5)),
        "report_min_rows": int(readout["report_min_rows"]),
    }
    partition_parts = []
    for model_row in model_rows:
        rows = frame.loc[frame["model_row"].astype(str) == model_row]
        partition_parts.append(microstructure.halfspread_partition_readout(
            rows, model_row=model_row, row_scope="all_eligible", cell_column="cell",
            bootstrap=bootstrap if model_row == primary else None,
            descriptive_note=note, **common,
        ))
    primary_rows = frame.loc[frame["model_row"].astype(str) == primary]
    low_rows = primary_rows.loc[primary_rows["activity_tercile"].astype(str) == "low"]
    low_readout = microstructure.halfspread_partition_readout(
        low_rows, model_row=primary, row_scope="low_activity_tercile",
        cell_column="cell", bootstrap=bootstrap, descriptive_note=note, **common,
    )
    cs_parts = [
        microstructure.halfspread_partition_readout(
            primary_rows, model_row=primary, row_scope="all_eligible",
            cell_column="cs_cell", bootstrap=None,
            descriptive_note="corwin_schultz robustness proxy; no verdict power", **common,
        ),
        microstructure.halfspread_partition_readout(
            low_rows, model_row=primary, row_scope="low_activity_tercile",
            cell_column="cs_cell", bootstrap=None,
            descriptive_note="corwin_schultz robustness proxy; no verdict power", **common,
        ),
    ]
    day_terciles = (
        primary_rows.groupby(["ticker", "trading_day"])["activity_tercile"].first().reset_index()
    )
    return {
        "partition_readout": pd.concat(partition_parts, ignore_index=True),
        "low_tercile_readout": low_readout,
        "occupancy": microstructure.spread_activity_occupancy(
            primary_rows, evidence_domain=evidence_domain
        ),
        "autocov_by_tercile": microstructure.lag1_autocov_by_tercile(
            bars, day_terciles, evidence_domain=evidence_domain
        ),
        "cs_robustness_readout": pd.concat(cs_parts, ignore_index=True),
    }


def _verdict_record(
    config: Mapping[str, Any], domain: str, low_readout: pd.DataFrame
) -> dict[str, Any]:
    readout = require_mapping(config["readout"], "readout")
    verdict = microstructure.verdict_from_readout(
        low_readout,
        verdict_min_rows=int(readout["verdict_min_rows"]),
        report_min_rows=int(readout["report_min_rows"]),
    )
    verdict["role"] = (
        "primary_registered_verdict" if domain == "validation"
        else "guarded_replication_context_non_independent_never_pooled"
    )
    verdict["designation"] = (
        "half-spread settlement control (measure-only re-aggregation; no new scoring)"
    )
    forbidden = list(require_mapping(config["forbidden"], "forbidden")["wording"])
    synthesis.assert_no_forbidden_wording(
        json.dumps(verdict), forbidden, context="halfspread_verdict.json"
    )
    return verdict


def _write_outputs(
    config: Mapping[str, Any],
    domain: str,
    block: Mapping[str, Any],
    tables: Mapping[str, pd.DataFrame],
    verdict: Mapping[str, Any],
    day_spread: pd.DataFrame,
    dump_hashes: Mapping[str, Mapping[str, Any]],
    replay_status: str,
) -> HalfspreadResult:
    outputs = require_mapping(config["outputs"], "outputs")
    run_id = str(outputs.get("run_id") or make_run_id())
    run_dir = Path(str(outputs["output_dir"])) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    artifact_paths: dict[str, Path] = {}
    day_path = run_dir / str(outputs["day_spread"])
    day_spread[
        microstructure.DAY_SPREAD_COLUMNS
        + ["cs_n_spans", "cs_alpha", "cs_halfspread", "cs_spread_band_ratio", "cs_cell"]
    ].to_csv(day_path, index=False)
    artifact_paths["day_spread"] = day_path
    for key in (
        "partition_readout", "low_tercile_readout", "occupancy",
        "autocov_by_tercile", "cs_robustness_readout",
    ):
        path = run_dir / str(outputs[key])
        tables[key].to_csv(path, index=False)
        artifact_paths[key] = path

    verdict_path = run_dir / str(outputs["verdict"])
    write_json(verdict_path, dict(verdict))
    artifact_paths["verdict"] = verdict_path

    manifest = {
        "route": str(config["route"]),
        "stage_name": STAGE_NAME,
        "scope": SCOPE,
        "run_id": run_id,
        "run_domain": domain,
        "evidence_domain": str(block["evidence_domain"]),
        "data_segment": str(block["data_segment"]),
        "designation": str(verdict["designation"]),
        "preregistration": str(config.get("preregistration")),
        "holdout_test_contact": bool(block["holdout_test_contact"]),
        "holdout_contact_tier": str(block.get("holdout_contact_tier") or "none"),
        "clean_test_claim": False,
        "new_scoring_events": 0,
        "official_validation_scoring_events": 0,
        "no_final_model_selected": True,
        "v2_frozen_selection_unchanged": True,
        "upstream_run_ids": {
            key: str(block[f"{key}_run_id"])
            for key in ("stage00", "stage01", "stage03", "v2_1")
            if f"{key}_run_id" in block
        },
        "input_dumps": {name: dict(spec) for name, spec in dump_hashes.items()},
        "dummy_replay_status": replay_status,
        "estimator": dict(require_mapping(config["estimator"], "estimator")),
        "seeds": [int(s) for s in require_mapping(config["readout"], "readout")["seeds"]],
        "verdict": str(verdict["verdict"]),
        "verdict_role": str(verdict["role"]),
        "config_sha256": hash_mapping(_json_safe(config)),
        "microstructure_code_sha256": hash_file(Path(microstructure.__file__)),
        "metrics_code_sha256": hash_file(Path(metrics.__file__)),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "package_versions": package_versions(["pandas", "numpy", "scipy", "sklearn"]),
        **git_commit_fields(),
    }
    notebook_path = resolve_repo_path(require_mapping(config["inputs"], "inputs")["notebook_path"])
    manifest["notebook_sha256"] = hash_file(notebook_path) if notebook_path.exists() else None
    manifest_path = run_dir / str(outputs["manifest"])
    write_json(manifest_path, manifest)
    artifact_paths["manifest"] = manifest_path
    write_artifact_inventory(run_dir, artifact_paths)
    return HalfspreadResult(
        run_dir=run_dir, run_manifest=manifest_path, verdict_record=verdict_path
    )


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value
