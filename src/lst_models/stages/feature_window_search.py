from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from lst_models.artifacts import require_artifacts, write_artifact_inventory, write_json
from lst_models.config import hash_file, hash_mapping


SUMMARY_COLUMNS = [
    "candidate_id",
    "feature_set",
    "window_size",
    "n_samples_total",
    "n_samples_by_ticker_json",
    "n_train_inner_folds",
    "n_seeds",
    "n_probe_rows",
    "mean_macro_f1",
    "mean_balanced_accuracy",
    "mean_delta_macro_f1_vs_stratified_dummy",
    "lcb_delta_macro_f1_vs_stratified_dummy",
    "positive_ticker_count",
    "seed_std_macro_f1",
    "fold_std_macro_f1",
    "selected_for_stage02",
    "selection_reason",
]

LEDGER_COLUMNS = [
    "probe_id",
    "candidate_id",
    "feature_set",
    "window_size",
    "fold_id",
    "seed",
    "fit_status",
    "n_train_samples",
    "n_eval_samples",
    "macro_f1",
    "balanced_accuracy",
    "accuracy",
    "baseline_id",
    "baseline_macro_f1",
    "baseline_balanced_accuracy",
    "delta_macro_f1_vs_baseline",
    "delta_balanced_accuracy_vs_baseline",
    "sample_id_hash",
    "error_message",
]

FOLD_COLUMNS = [
    "fold_id",
    "train_start",
    "train_end_exclusive",
    "eval_start",
    "eval_end_exclusive",
    "purge_or_embargo_policy",
    "n_train_samples",
    "n_eval_samples",
    "event_overlap_count",
]


@dataclass(frozen=True)
class Stage01Result:
    output_dir: Path
    run_manifest: Path
    artifact_inventory: Path
    summary: Path
    candidate_inputs: Path
    probe_ledger: Path
    fold_manifest: Path


def run_stage(config: Mapping[str, Any]) -> Stage01Result:
    _validate_config(config)

    inputs = _as_mapping(config["inputs"], "inputs")
    outputs = _as_mapping(config["outputs"], "outputs")
    stage00_run_dir = Path(str(inputs["stage00_runtime_run_dir"]))
    required = inputs.get("required_stage00_artifacts", [])
    stage00_paths = require_artifacts(stage00_run_dir, required)

    stage00_manifest = _load_json(stage00_paths["run_manifest.json"])
    if stage00_manifest.get("holdout_test_contact") is not False:
        raise ValueError("Stage 01 requires Stage 00 run_manifest holdout_test_contact=false")

    sample_events = _load_sample_event_index(stage00_paths["sample_event_index.csv"])
    train_events = _train_valid_events(sample_events)
    folds = _build_train_inner_folds(train_events, int(config["train_inner"]["n_folds"]))

    feature_sets = tuple(str(name) for name in _as_mapping(config["feature_sets"], "feature_sets"))
    window_sizes = tuple(int(value) for value in config["window_sizes"])
    seeds = tuple(int(value) for value in config["train_inner"]["seeds"])
    probe_ids = _enabled_probe_ids(config)
    _enforce_budget(feature_sets, window_sizes, probe_ids, folds, seeds, config)

    summary = _build_summary(train_events, feature_sets, window_sizes, folds, seeds, probe_ids)
    ledger = _build_probe_ledger(summary, folds, seeds, probe_ids, config)
    candidate_inputs = _build_candidate_inputs(config, stage00_manifest)

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(str(outputs["output_dir"])) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / str(outputs["summary"])
    candidate_path = write_json(output_dir / str(outputs["candidate_inputs"]), candidate_inputs)
    ledger_path = output_dir / str(outputs["probe_ledger"])
    fold_path = output_dir / str(outputs["fold_manifest"])
    summary.to_csv(summary_path, index=False)
    ledger.to_csv(ledger_path, index=False)
    folds.to_csv(fold_path, index=False)

    notebook_path = Path(str(inputs["notebook_path"]))
    manifest_payload = {
        "route": config["route"],
        "stage_name": config["stage_name"],
        "scope": config["scope"],
        "config_sha256": hash_mapping(config),
        "notebook_sha256": hash_file(notebook_path),
        "source_stage00_run_id": inputs["stage00_run_id"],
        "input_artifacts": [str(path) for path in stage00_paths.values()],
        "output_artifacts": [
            str(outputs["summary"]),
            str(outputs["candidate_inputs"]),
            str(outputs["probe_ledger"]),
            str(outputs["fold_manifest"]),
        ],
        "stage01_execution_mode": "contract_scaffold_no_probe_training",
        "official_validation_for_selection": False,
        "no_final_model_selected": True,
        "holdout_test_contact": False,
    }
    manifest_path = write_json(output_dir / str(outputs["manifest"]), manifest_payload)
    inventory_path = write_artifact_inventory(
        output_dir,
        {
            "run_manifest": manifest_path,
            "summary": summary_path,
            "candidate_inputs": candidate_path,
            "probe_ledger": ledger_path,
            "fold_manifest": fold_path,
        },
    )

    return Stage01Result(
        output_dir=output_dir,
        run_manifest=manifest_path,
        artifact_inventory=inventory_path,
        summary=summary_path,
        candidate_inputs=candidate_path,
        probe_ledger=ledger_path,
        fold_manifest=fold_path,
    )


def _validate_config(config: Mapping[str, Any]) -> None:
    if config.get("scope") != "validation_only":
        raise ValueError(f"expected validation_only scope, got {config.get('scope')!r}")
    if config.get("holdout_test_contact") is not False:
        raise ValueError("Stage 01 requires holdout_test_contact=false")
    train_inner = _as_mapping(config["train_inner"], "train_inner")
    if train_inner.get("official_validation_for_selection") is not False:
        raise ValueError("Stage 01 selection must use train-inner folds only")
    if list(config.get("window_sizes", [])) != [10, 20, 30]:
        raise ValueError("Stage 01 window_sizes must be exactly [10, 20, 30]")
    selection_rules = _as_mapping(config["selection_rules"], "selection_rules")
    if selection_rules.get("no_final_model_selected") is not True:
        raise ValueError("Stage 01 must declare no_final_model_selected=true")


def _as_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"expected mapping for {name}, got {type(value).__name__}")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"expected JSON object in {path}")
    return loaded


def _load_sample_event_index(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required_columns = {
        "sample_id",
        "ticker",
        "target_timestamp",
        "trading_day",
        "split",
        "valid_label",
    }
    missing = sorted(required_columns - set(frame.columns))
    if missing:
        raise ValueError(f"sample_event_index.csv missing columns: {missing}")
    frame = frame.copy()
    frame["target_timestamp"] = pd.to_datetime(frame["target_timestamp"])
    frame["trading_day"] = frame["trading_day"].astype(str)
    return frame


def _train_valid_events(sample_events: pd.DataFrame) -> pd.DataFrame:
    valid_label = sample_events["valid_label"].map(_is_true)
    train = sample_events.loc[(sample_events["split"] == "train") & valid_label].copy()
    if train.empty:
        raise ValueError("Stage 01 found no train split rows with valid_label=true")
    return train.sort_values(["target_timestamp", "ticker", "sample_id"]).reset_index(drop=True)


def _is_true(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def _build_train_inner_folds(train_events: pd.DataFrame, n_folds: int) -> pd.DataFrame:
    if n_folds < 1:
        raise ValueError("train_inner.n_folds must be at least 1")
    days = sorted(train_events["trading_day"].unique())
    if len(days) < n_folds + 1:
        raise ValueError(
            f"need at least {n_folds + 1} train trading days for {n_folds} train-inner folds, "
            f"got {len(days)}"
        )

    rows = []
    for fold_index in range(n_folds):
        eval_day = days[fold_index + 1]
        train_days = days[: fold_index + 1]
        fold_train = train_events.loc[train_events["trading_day"].isin(train_days)]
        fold_eval = train_events.loc[train_events["trading_day"] == eval_day]
        if fold_train.empty or fold_eval.empty:
            raise ValueError(f"empty train-inner fold {fold_index}")

        eval_start = fold_eval["target_timestamp"].min()
        train_end_exclusive = eval_start
        event_overlap_count = int((fold_train["target_timestamp"] >= eval_start).sum())
        rows.append(
            {
                "fold_id": f"fold_{fold_index}",
                "train_start": fold_train["target_timestamp"].min().isoformat(),
                "train_end_exclusive": train_end_exclusive.isoformat(),
                "eval_start": eval_start.isoformat(),
                "eval_end_exclusive": (
                    fold_eval["target_timestamp"].max() + pd.Timedelta(microseconds=1)
                ).isoformat(),
                "purge_or_embargo_policy": "chronological_day_block_no_overlap",
                "n_train_samples": int(len(fold_train)),
                "n_eval_samples": int(len(fold_eval)),
                "event_overlap_count": event_overlap_count,
            }
        )

    fold_frame = pd.DataFrame(rows, columns=FOLD_COLUMNS)
    if not (fold_frame["event_overlap_count"] == 0).all():
        raise ValueError("Stage 01 train-inner folds have nonzero event overlap")
    return fold_frame


def _enabled_probe_ids(config: Mapping[str, Any]) -> tuple[str, ...]:
    lightweight = _as_mapping(config["lightweight_probes"], "lightweight_probes")
    probe_ids = [
        str(probe_id)
        for probe_id, probe_config in lightweight.items()
        if _as_mapping(probe_config, f"lightweight_probes.{probe_id}").get("enabled") is True
    ]
    controls = _as_mapping(config.get("optional_fixed_controls", {}), "optional_fixed_controls")
    probe_ids.extend(
        str(probe_id)
        for probe_id, probe_config in controls.items()
        if _as_mapping(probe_config, f"optional_fixed_controls.{probe_id}").get("enabled") is True
    )
    if not probe_ids:
        raise ValueError("Stage 01 requires at least one enabled lightweight probe")
    return tuple(probe_ids)


def _enforce_budget(
    feature_sets: tuple[str, ...],
    window_sizes: tuple[int, ...],
    probe_ids: tuple[str, ...],
    folds: pd.DataFrame,
    seeds: tuple[int, ...],
    config: Mapping[str, Any],
) -> None:
    planned_rows = len(feature_sets) * len(window_sizes) * len(probe_ids) * len(folds) * len(seeds)
    budget = _as_mapping(config["budget"], "budget")
    cap = int(budget["max_counted_probe_rows"])
    if planned_rows > cap:
        raise ValueError(f"Stage 01 planned probe rows {planned_rows} exceed budget cap {cap}")


def _build_summary(
    train_events: pd.DataFrame,
    feature_sets: tuple[str, ...],
    window_sizes: tuple[int, ...],
    folds: pd.DataFrame,
    seeds: tuple[int, ...],
    probe_ids: tuple[str, ...],
) -> pd.DataFrame:
    rows = []
    for feature_set in feature_sets:
        for window_size in window_sizes:
            candidate_id = f"{feature_set}_w{window_size}"
            by_ticker = _label_only_window_counts(train_events, window_size)
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "feature_set": feature_set,
                    "window_size": window_size,
                    "n_samples_total": int(sum(by_ticker.values())),
                    "n_samples_by_ticker_json": json.dumps(by_ticker, sort_keys=True),
                    "n_train_inner_folds": int(len(folds)),
                    "n_seeds": int(len(seeds)),
                    "n_probe_rows": int(len(folds) * len(seeds) * len(probe_ids)),
                    "mean_macro_f1": pd.NA,
                    "mean_balanced_accuracy": pd.NA,
                    "mean_delta_macro_f1_vs_stratified_dummy": pd.NA,
                    "lcb_delta_macro_f1_vs_stratified_dummy": pd.NA,
                    "positive_ticker_count": 0,
                    "seed_std_macro_f1": pd.NA,
                    "fold_std_macro_f1": pd.NA,
                    "selected_for_stage02": False,
                    "selection_reason": "no_probe_fits_stage01_scaffold_only",
                }
            )
    return pd.DataFrame(rows, columns=SUMMARY_COLUMNS)


def _label_only_window_counts(train_events: pd.DataFrame, window_size: int) -> dict[str, int]:
    counts: dict[str, int] = {}
    grouped = train_events.groupby(["ticker", "trading_day"], sort=True)
    for (ticker, _day), day_frame in grouped:
        counts.setdefault(str(ticker), 0)
        counts[str(ticker)] += max(0, int(len(day_frame)) - window_size + 1)
    return counts


def _build_probe_ledger(
    summary: pd.DataFrame,
    folds: pd.DataFrame,
    seeds: tuple[int, ...],
    probe_ids: tuple[str, ...],
    config: Mapping[str, Any],
) -> pd.DataFrame:
    baseline_id = str(_as_mapping(config["selection_rules"], "selection_rules")["baseline"])
    rows = []
    for summary_row in summary.to_dict(orient="records"):
        for fold in folds.to_dict(orient="records"):
            sample_hash = _sample_id_hash(
                str(summary_row["candidate_id"]),
                str(fold["fold_id"]),
                int(fold["n_train_samples"]),
                int(fold["n_eval_samples"]),
            )
            for seed in seeds:
                for probe_id in probe_ids:
                    rows.append(
                        {
                            "probe_id": probe_id,
                            "candidate_id": summary_row["candidate_id"],
                            "feature_set": summary_row["feature_set"],
                            "window_size": summary_row["window_size"],
                            "fold_id": fold["fold_id"],
                            "seed": seed,
                            "fit_status": "skipped_not_implemented",
                            "n_train_samples": fold["n_train_samples"],
                            "n_eval_samples": fold["n_eval_samples"],
                            "macro_f1": pd.NA,
                            "balanced_accuracy": pd.NA,
                            "accuracy": pd.NA,
                            "baseline_id": baseline_id,
                            "baseline_macro_f1": pd.NA,
                            "baseline_balanced_accuracy": pd.NA,
                            "delta_macro_f1_vs_baseline": pd.NA,
                            "delta_balanced_accuracy_vs_baseline": pd.NA,
                            "sample_id_hash": sample_hash,
                            "error_message": (
                                "feature construction and lightweight probe fitting are not "
                                "implemented in this scaffold"
                            ),
                        }
                    )
    return pd.DataFrame(rows, columns=LEDGER_COLUMNS)


def _sample_id_hash(candidate_id: str, fold_id: str, n_train: int, n_eval: int) -> str:
    payload = f"{candidate_id}|{fold_id}|{n_train}|{n_eval}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _build_candidate_inputs(
    config: Mapping[str, Any], stage00_manifest: Mapping[str, Any]
) -> dict[str, Any]:
    handoff = _as_mapping(config["stage02_handoff"], "stage02_handoff")
    return {
        "route": config["route"],
        "stage_name": config["stage_name"],
        "source_stage00_run_id": config["inputs"]["stage00_run_id"],
        "source_stage00_config_sha256": stage00_manifest.get("config_sha256"),
        "candidate_inputs": [],
        "approved_model_families_for_stage02": [],
        "recommended_model_families_from_protocol": list(handoff["recommended_model_families"]),
        "control_models_for_stage02": list(handoff.get("control_models", [])),
        "decision": "do_not_start_stage02_probe_fits_not_implemented",
        "no_final_model_selected": True,
        "holdout_test_contact": False,
    }
