from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from lst_models.artifacts import make_run_id, runtime_provenance, write_artifact_inventory, write_json
from lst_models.config import hash_file, hash_mapping, hash_research_config, load_yaml
from lst_models.data import read_raw_txt_file, resample_1min_to_5min
from lst_models.labels import make_direction_labels, summarize_label_validity
from lst_models.splits import add_split_column, keep_validation_only_rows, parse_split_boundaries


@dataclass(frozen=True)
class Stage00Result:
    output_dir: Path
    run_manifest: Path
    artifact_inventory: Path
    sample_event_index: Path
    label_validity_summary: Path


def run_stage(config: Mapping[str, Any]) -> Stage00Result:
    if config.get("scope") != "validation_only":
        raise ValueError(f"expected validation_only scope, got {config.get('scope')!r}")
    if config.get("holdout_test_contact") is not False:
        raise ValueError("Stage 00 requires holdout_test_contact=false")

    raw_manifest_path = Path(str(config["inputs"]["raw_data_manifest"]))
    notebook_path = Path(str(config["inputs"]["notebook_path"]))
    raw_manifest = load_yaml(raw_manifest_path)
    boundaries = parse_split_boundaries(config["split"])
    label_policy = dict(config["label_policy"])

    run_id = make_run_id()
    output_dir = Path(str(config["outputs"]["output_dir"])) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_data_dir = Path(str(config["inputs"]["raw_data_dir"]))
    frames = []
    for ticker in raw_manifest["tickers"]:
        file_spec = raw_manifest["raw_source"]["files"][ticker]
        file_name = file_spec["name"]
        raw_path = raw_data_dir / file_name
        file_spec["bytes"] = int(raw_path.stat().st_size)
        file_spec["sha256"] = hash_file(raw_path)
        one_minute = read_raw_txt_file(raw_path, ticker, raw_manifest["raw_source"])
        five_minute = resample_1min_to_5min(one_minute, raw_manifest["five_minute_recipe"])
        split_frame = add_split_column(five_minute, boundaries)
        frames.append(keep_validation_only_rows(split_frame))

    if not frames:
        raise ValueError("No train/validation frames were created.")

    bars = pd.concat(frames, ignore_index=True).sort_values(["ticker", "timestamp"])
    sample_events = make_direction_labels(bars, label_policy)
    sample_columns = [
        "sample_id",
        "ticker",
        "target_timestamp",
        "trading_day",
        "split",
        "horizon_k",
        "horizon_end_timestamp",
        "label",
        "future_cumulative_return",
        "valid_label",
        "invalid_missing_future",
        "invalid_cross_trading_day",
        "invalid_irregular_horizon",
        "invalid_cross_split",
        "invalid_no_trade_band",
    ]
    sample_events = sample_events.rename(columns={"timestamp": "target_timestamp"})
    sample_events = sample_events.loc[:, sample_columns]

    label_summary = summarize_label_validity(sample_events)

    raw_manifest_out = write_json(output_dir / "raw_data_manifest.json", raw_manifest)
    split_out = write_json(output_dir / "split_freeze.json", dict(config["split"]))
    label_out = write_json(output_dir / "label_policy.json", label_policy)
    baseline_out = write_json(output_dir / "baseline_registry.json", dict(config["baseline_registry"]))
    sample_out = output_dir / "sample_event_index.csv"
    summary_out = output_dir / "label_validity_summary.csv"
    sample_events.to_csv(sample_out, index=False)
    label_summary.to_csv(summary_out, index=False)

    provenance = runtime_provenance(config)
    manifest_payload = {
        "route": config["route"],
        "stage_name": config["stage_name"],
        "scope": config["scope"],
        "repo_url": provenance["repo_url"],
        "git_commit": provenance["git_commit"],
        "bootstrap_mode": provenance["bootstrap_mode"],
        "config_sha256": hash_research_config(config),
        "runtime_config_sha256": hash_mapping(config),
        "notebook_sha256": hash_file(notebook_path),
        "runtime_provenance": provenance,
        "input_artifacts": [str(raw_manifest_path)],
        "output_artifacts": [
            "raw_data_manifest.json",
            "split_freeze.json",
            "label_policy.json",
            "baseline_registry.json",
            "label_validity_summary.csv",
            "sample_event_index.csv",
        ],
        "holdout_test_contact": False,
    }
    manifest_out = write_json(output_dir / "run_manifest.json", manifest_payload)
    inventory_out = write_artifact_inventory(
        output_dir,
        {
            "run_manifest": manifest_out,
            "raw_data_manifest": raw_manifest_out,
            "split_freeze": split_out,
            "label_policy": label_out,
            "baseline_registry": baseline_out,
            "label_validity_summary": summary_out,
            "sample_event_index": sample_out,
        },
    )

    return Stage00Result(
        output_dir=output_dir,
        run_manifest=manifest_out,
        artifact_inventory=inventory_out,
        sample_event_index=sample_out,
        label_validity_summary=summary_out,
    )
