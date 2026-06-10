from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models.artifacts import write_artifact_inventory, write_json  # noqa: E402
from lst_models.stages import feature_window_search as stage01  # noqa: E402
from lst_models.stages import frozen_validation_readout as stage03  # noqa: E402
from lst_models.stages.frozen_validation_readout import run_stage  # noqa: E402


TICKERS = ["AAA", "BBB"]
TRAIN_DAYS = ["2020-01-02", "2020-01-03", "2020-01-06", "2020-01-07"]
VALIDATION_DAYS = ["2020-01-08", "2020-01-09"]
BARS_PER_DAY = 36
WINDOW_SIZE = 10
FEATURE_SET = "price_action_core"
FEATURE_COLUMNS = ["log_return"]
CANDIDATE_ID = f"{FEATURE_SET}_w{WINDOW_SIZE}"
STAGE00_RUN_ID = "stage00_test_run"
STAGE01_RUN_ID = "stage01_test_run"
STAGE02_RUN_ID = "20990101_000000_000001"
SUPERSEDED_STAGE02_RUN_ID = "20260609_100637_704705"

STAGE02_ARTIFACT_NAMES = [
    "run_manifest.json",
    "02_model_hpo_train_inner_summary.csv",
    "02_hpo_plan_ledger.csv",
    "02_hpo_trial_ledger.csv",
    "02_hpo_summary.csv",
    "02_baseline_control_summary.csv",
    "02_frozen_candidate.json",
    "02_frozen_candidate.md",
    "02_best_params_by_family.json",
    "02_stage03_handoff.json",
]


class Stage03Dirs:
    """Tiny chronology-safe fixture: real raw txt bars spanning train and
    validation intervals plus fake Stage 00/01/02 run folders whose inventories
    carry real sha256 values, so stage03 entry gates run for real."""

    def __init__(self, tmp_path: Path) -> None:
        self.tmp_path = tmp_path
        self.raw_dir = tmp_path / "raw"
        self.stage00_dir = tmp_path / "stage00" / STAGE00_RUN_ID
        self.stage01_dir = tmp_path / "stage01" / STAGE01_RUN_ID
        self.stage02_dir = tmp_path / "stage02" / STAGE02_RUN_ID
        self.output_dir = tmp_path / "out"
        self.notebook_path = tmp_path / "03_frozen_validation_readout_colab.ipynb"
        self.notebook_path.write_text("{}", encoding="utf-8")
        self._write_stage00_run_folder()
        train_total, train_by_ticker = self._compute_rebuilt_train_counts()
        self._write_stage01_run_folder(train_total, train_by_ticker)
        self._write_stage02_run_folder()

    def config(self) -> dict:
        return {
            "stage_name": "03_frozen_validation_readout",
            "route": "lst_models",
            "scope": "validation_only",
            "holdout_test_contact": False,
            "official_validation_contact": True,
            "official_validation_for_selection": False,
            "inputs": {
                "stage00_run_id": STAGE00_RUN_ID,
                "stage00_runtime_run_dir": str(self.stage00_dir),
                "required_stage00_artifacts": [
                    "raw_data_manifest.json",
                    "split_freeze.json",
                    "label_policy.json",
                    "baseline_registry.json",
                    "sample_event_index.csv",
                    "run_manifest.json",
                    "artifact_inventory.csv",
                ],
                "stage01_run_id": STAGE01_RUN_ID,
                "stage01_runtime_run_dir": str(self.stage01_dir),
                "required_stage01_artifacts": [
                    "run_manifest.json",
                    "artifact_inventory.csv",
                    "01_candidate_inputs.json",
                    "01_feature_window_search_summary.csv",
                ],
                "stage02_run_id": STAGE02_RUN_ID,
                "stage02_runtime_run_dir": str(self.stage02_dir),
                "superseded_stage02_run_ids": [SUPERSEDED_STAGE02_RUN_ID],
                "required_stage02_artifacts": [
                    "run_manifest.json",
                    "artifact_inventory.csv",
                    *[name for name in STAGE02_ARTIFACT_NAMES if name != "run_manifest.json"],
                ],
                "raw_data_manifest": "configs/lst_models_data.yaml",
                "raw_data_dir": str(self.raw_dir),
                "notebook_path": str(self.notebook_path),
            },
            "outputs": {
                "output_dir": str(self.output_dir),
                "manifest": "run_manifest.json",
                "artifact_inventory": "artifact_inventory.csv",
                "validation_readout": "03_validation_readout.csv",
                "per_ticker_readout": "03_per_ticker_readout.csv",
                "seed_summary": "03_seed_summary.csv",
                "same_row_baselines": "03_same_row_baselines.csv",
                "validation_predictions": "03_validation_predictions.csv",
                "decision_record": "03_decision_record.json",
            },
            "readout": {
                "seeds": [101, 202],
                "refit_rows": "all_eligible_official_train_rows",
                "scoring_rows": "all_eligible_official_validation_rows",
                "refit_recipe": "frozen_mechanism_chronological_tail_early_stopping",
                "score_each_seed_candidate_exactly_once": True,
                "max_materialized_train_bytes": 2000000000,
            },
            "predeclared_criteria": {
                "aggregate": "mean_over_seeds",
                "require_delta_macro_f1_vs_stratified_dummy_train_prior_positive": True,
                "require_delta_macro_f1_vs_majority_train_prior_positive": True,
                "minimum_positive_ticker_count": 2,
                "per_ticker_aggregation": "mean_delta_across_seeds_then_count_positive",
            },
            "fallback_policy": {
                "allowed_triggers": [
                    "missing_frozen_artifact",
                    "schema_or_hash_mismatch",
                    "refit_crash_before_any_scoring",
                    "candidate_not_reconstructable",
                ],
                "forbidden_triggers": [
                    "weak_validation_metrics",
                    "below_dummy",
                    "per_ticker_instability",
                ],
                "after_first_scoring_event": "never_activate",
            },
            "baseline_controls": {
                "mandatory": [
                    "stratified_dummy_train_prior",
                    "majority_train_prior",
                    "constant_up",
                    "constant_down",
                ]
            },
            "lightgbm_training_defaults": {
                "eval_metric": "binary_logloss",
                "early_stopping_rounds": 5,
                "early_stopping_validation_source": "inner_train_chronological_tail",
                "early_stopping_validation_fraction": 0.2,
                "minimum_early_stopping_train_samples": 8,
                "minimum_early_stopping_validation_samples": 4,
            },
            "probe_training_defaults": {
                "torch": {
                    "epochs": 1,
                    "batch_size": 64,
                    "learning_rate": 0.001,
                    "weight_decay": 0.0001,
                    "device": "cpu",
                    "require_gpu": False,
                }
            },
            "checkpointing": {"enabled": False},
            "forbidden": {
                "wording": [
                    "final model",
                    "selected by official validation",
                    "chosen threshold",
                ]
            },
        }

    def write_stage02_handoff(self, **overrides: object) -> None:
        handoff_path = self.stage02_dir / "02_stage03_handoff.json"
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
        handoff.update(overrides)
        write_json(handoff_path, handoff)
        self._write_stage02_inventory()

    def copy_trial_ledger_over_plan_ledger(self) -> None:
        plan_path = self.stage02_dir / "02_hpo_plan_ledger.csv"
        plan_path.write_bytes((self.stage02_dir / "02_hpo_trial_ledger.csv").read_bytes())
        self._write_stage02_inventory()

    def read_path(self, name: str) -> Path:
        return self._single_run_dir() / name

    def read_output(self, name: str) -> str:
        return self.read_path(name).read_text(encoding="utf-8")

    def _single_run_dir(self) -> Path:
        run_dirs = [path for path in self.output_dir.iterdir() if path.is_dir()]
        if len(run_dirs) != 1:
            raise AssertionError(
                f"expected exactly one run folder under {self.output_dir}, got {len(run_dirs)}"
            )
        return run_dirs[0]

    def _raw_manifest_payload(self) -> dict:
        return {
            "tickers": TICKERS,
            "raw_source": {
                "local_download_dir": str(self.raw_dir),
                "files": {ticker: {"name": f"{ticker}.txt"} for ticker in TICKERS},
                "txt_columns": ["Date", "Time", "Open", "High", "Low", "Close", "Volume"],
                "date_format": "%m/%d/%Y",
                "time_format": "%H:%M",
            },
            "five_minute_recipe": {
                "market_open": "09:30",
                "market_close": "16:00",
                "resample_rule": "5min",
                "agg": {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                },
                "drop_na_subset": ["open", "high", "low", "close", "volume"],
                "output_columns": [
                    "ticker",
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ],
            },
        }

    def _write_stage00_run_folder(self) -> None:
        self.stage00_dir.mkdir(parents=True)
        write_json(self.stage00_dir / "raw_data_manifest.json", self._raw_manifest_payload())
        write_json(
            self.stage00_dir / "split_freeze.json",
            {
                "train_start": "2020-01-02 00:00:00",
                "train_end": "2020-01-08 00:00:00",
                "validation_start": "2020-01-08 00:00:00",
                "validation_end": "2020-01-10 00:00:00",
                "closed_holdout_test_start": "2020-01-10 00:00:00",
            },
        )
        write_json(
            self.stage00_dir / "label_policy.json",
            {
                "label_config_id": "h01_bps3p0",
                "operator": "endpoint_cumulative_return",
                "horizon_k": 1,
                "no_trade_band_bps": 3.0,
            },
        )
        write_json(self.stage00_dir / "baseline_registry.json", {})
        write_json(
            self.stage00_dir / "run_manifest.json",
            {"holdout_test_contact": False, "config_sha256": "stage00hash"},
        )
        self._write_raw_txt_and_sample_events()
        names = [
            "raw_data_manifest.json",
            "split_freeze.json",
            "label_policy.json",
            "baseline_registry.json",
            "sample_event_index.csv",
            "run_manifest.json",
        ]
        write_artifact_inventory(
            self.stage00_dir, {name: self.stage00_dir / name for name in names}
        )

    def _write_raw_txt_and_sample_events(self) -> None:
        self.raw_dir.mkdir(parents=True)
        day_split_pairs = [(day, "train") for day in TRAIN_DAYS] + [
            (day, "validation") for day in VALIDATION_DAYS
        ]
        events: list[dict[str, object]] = []
        for ticker_index, ticker in enumerate(TICKERS):
            rows: list[dict[str, object]] = []
            price = 100.0 + ticker_index
            for day_index, (day, split) in enumerate(day_split_pairs):
                bar_starts = pd.date_range(f"{day} 09:30", periods=BARS_PER_DAY, freq="5min")
                for bar_index, bar_start in enumerate(bar_starts):
                    signal = 1 if (bar_index + day_index + ticker_index) % 2 == 0 else -1
                    bar_open = price
                    bar_close = bar_open * (1.0 + signal * 0.002)
                    minute_prices = np.linspace(bar_open, bar_close, num=5)
                    for minute_offset, close_value in enumerate(minute_prices):
                        ts = bar_start + pd.Timedelta(minutes=minute_offset)
                        rows.append(
                            {
                                "Date": ts.strftime("%m/%d/%Y"),
                                "Time": ts.strftime("%H:%M"),
                                "Open": close_value,
                                "High": close_value * 1.0005,
                                "Low": close_value * 0.9995,
                                "Close": close_value,
                                "Volume": 1000 + 10 * bar_index + ticker_index,
                            }
                        )
                    price = bar_close
                    events.append(
                        {
                            "sample_id": f"{ticker}_{bar_start:%Y%m%d_%H%M}",
                            "ticker": ticker,
                            "target_timestamp": bar_start.isoformat(),
                            "trading_day": day,
                            "split": split,
                            "label": 1 if signal > 0 else 0,
                            "valid_label": True,
                        }
                    )
            pd.DataFrame(rows).to_csv(self.raw_dir / f"{ticker}.txt", index=False)
        pd.DataFrame(events).to_csv(self.stage00_dir / "sample_event_index.csv", index=False)

    def _compute_rebuilt_train_counts(self) -> tuple[int, dict[str, int]]:
        raw_manifest = json.loads(
            (self.stage00_dir / "raw_data_manifest.json").read_text(encoding="utf-8")
        )
        split_freeze = json.loads(
            (self.stage00_dir / "split_freeze.json").read_text(encoding="utf-8")
        )
        sample_events = stage01._load_sample_event_index(
            self.stage00_dir / "sample_event_index.csv"
        )
        train_events = stage03._valid_events_for_split(sample_events, "train")
        bars = stage03._load_train_validation_bars(
            raw_manifest, split_freeze, {"raw_data_dir": str(self.raw_dir)}
        )
        feature_frame = stage01._build_feature_frame(bars)
        dataset = stage01._build_window_dataset(
            feature_frame,
            train_events,
            feature_set=FEATURE_SET,
            feature_columns=tuple(FEATURE_COLUMNS),
            window_size=WINDOW_SIZE,
        )
        by_ticker = {
            str(ticker): int(count)
            for ticker, count in dataset.metadata.groupby("ticker").size().to_dict().items()
        }
        if len(dataset.metadata) == 0:
            raise AssertionError("stage03 smoke fixture produced no rebuilt train samples")
        return int(len(dataset.metadata)), by_ticker

    def _write_stage01_run_folder(self, train_total: int, train_by_ticker: dict[str, int]) -> None:
        self.stage01_dir.mkdir(parents=True)
        write_json(
            self.stage01_dir / "run_manifest.json",
            {
                "holdout_test_contact": False,
                "config_sha256": "stage01hash",
                "feature_rebuild_code_sha256": stage01.feature_rebuild_code_sha256(),
            },
        )
        write_json(
            self.stage01_dir / "01_candidate_inputs.json",
            {
                "route": "lst_models",
                "stage_name": "01_feature_window_search",
                "source_stage00_run_id": STAGE00_RUN_ID,
                "candidate_inputs": [
                    {
                        "candidate_id": CANDIDATE_ID,
                        "feature_set": FEATURE_SET,
                        "window_size": WINDOW_SIZE,
                        "feature_columns": list(FEATURE_COLUMNS),
                        "n_samples_total": train_total,
                    }
                ],
                "approved_model_families_for_stage02": ["lightgbm"],
                "decision": "selected_candidate_inputs_for_stage02_train_inner_hpo",
                "no_final_model_selected": True,
                "holdout_test_contact": False,
            },
        )
        pd.DataFrame(
            [
                {
                    "candidate_id": CANDIDATE_ID,
                    "selected_for_stage02": True,
                    "n_samples_total": train_total,
                    "n_samples_by_ticker_json": json.dumps(train_by_ticker, sort_keys=True),
                }
            ]
        ).to_csv(self.stage01_dir / "01_feature_window_search_summary.csv", index=False)
        names = [
            "run_manifest.json",
            "01_candidate_inputs.json",
            "01_feature_window_search_summary.csv",
        ]
        write_artifact_inventory(
            self.stage01_dir, {name: self.stage01_dir / name for name in names}
        )

    def _selection_record(self, hpo_profile_id: str) -> dict:
        return {
            "candidate_id": CANDIDATE_ID,
            "feature_set": FEATURE_SET,
            "window_size": WINDOW_SIZE,
            "model_family": "lightgbm",
            "probe_id": "lightgbm_small",
            "hpo_profile_id": hpo_profile_id,
            "hpo_profile_params": {
                "num_leaves": 7,
                "max_depth": 3,
                "learning_rate": 0.1,
                "n_estimators": 20,
            },
            "mean_macro_f1": 0.55,
            "mean_delta_macro_f1_vs_stratified_dummy_train_prior": 0.05,
            "lcb_delta_macro_f1_vs_stratified_dummy_train_prior": 0.03,
            "mean_delta_macro_f1_vs_majority_train_prior": 0.04,
            "min_positive_ticker_count": 2,
            "selection_ranking_scope": "within_candidate_input_then_candidate_winners",
        }

    def _write_stage02_run_folder(self) -> None:
        self.stage02_dir.mkdir(parents=True)
        primary = self._selection_record("p01")
        fallback = self._selection_record("p02")
        write_json(
            self.stage02_dir / "run_manifest.json",
            {
                "route": "lst_models",
                "stage_name": "02_model_hpo_train_inner",
                "scope": "validation_only",
                "config_sha256": "stage02hash",
                "source_stage00_run_id": STAGE00_RUN_ID,
                "source_stage01_run_id": STAGE01_RUN_ID,
                "stage02_feature_rebuild_code_sha256": stage01.feature_rebuild_code_sha256(),
                "official_validation_for_selection": False,
                "no_final_model_selected": True,
                "holdout_test_contact": False,
            },
        )
        pd.DataFrame(
            [
                {
                    "status": "formal_hpo_complete_ready_for_stage03",
                    "ready_for_stage03": True,
                    "primary_candidate_id": CANDIDATE_ID,
                    "fallback_candidate_id": CANDIDATE_ID,
                    "decision": "ready_for_stage03_frozen_train_inner_hpo_candidates",
                }
            ]
        ).to_csv(self.stage02_dir / "02_model_hpo_train_inner_summary.csv", index=False)
        pd.DataFrame(
            [
                {
                    "trial_id": "trial_001",
                    "candidate_id": CANDIDATE_ID,
                    "hpo_profile_id": "p01",
                    "plan_status": "planned",
                }
            ]
        ).to_csv(self.stage02_dir / "02_hpo_plan_ledger.csv", index=False)
        pd.DataFrame(
            [
                {
                    "trial_id": "trial_001",
                    "candidate_id": CANDIDATE_ID,
                    "hpo_profile_id": "p01",
                    "fit_status": "completed",
                    "macro_f1": 0.55,
                }
            ]
        ).to_csv(self.stage02_dir / "02_hpo_trial_ledger.csv", index=False)
        pd.DataFrame(
            [
                {
                    "candidate_id": CANDIDATE_ID,
                    "model_family": "lightgbm",
                    "hpo_profile_id": "p01",
                    "selected_role": "primary",
                }
            ]
        ).to_csv(self.stage02_dir / "02_hpo_summary.csv", index=False)
        pd.DataFrame(
            [
                {
                    "candidate_id": CANDIDATE_ID,
                    "baseline_id": "stratified_dummy_train_prior",
                    "fit_status": "completed_baseline",
                }
            ]
        ).to_csv(self.stage02_dir / "02_baseline_control_summary.csv", index=False)
        write_json(
            self.stage02_dir / "02_frozen_candidate.json",
            {
                "route": "lst_models",
                "stage_name": "02_model_hpo_train_inner",
                "source_stage00_run_id": STAGE00_RUN_ID,
                "source_stage01_run_id": STAGE01_RUN_ID,
                "ready_for_stage03": True,
                "decision": "ready_for_stage03_frozen_train_inner_hpo_candidates",
                "block_reason": "",
                "primary_candidate": primary,
                "fallback_candidate": fallback,
                "seed_policy": {"train_inner_seeds": [101, 202]},
                "device_provenance": {"requested_device": "cpu", "resolved_device": "cpu"},
                "holdout_test_contact": False,
                "official_validation_for_selection": False,
                "no_final_model_selected": True,
            },
        )
        (self.stage02_dir / "02_frozen_candidate.md").write_text(
            "# Stage 02 Frozen Candidate\n\n- decision: ready_for_stage03\n",
            encoding="utf-8",
        )
        write_json(
            self.stage02_dir / "02_best_params_by_family.json",
            {
                "best_params_by_family": {"lightgbm": primary},
                "holdout_test_contact": False,
            },
        )
        write_json(
            self.stage02_dir / "02_stage03_handoff.json",
            {
                "route": "lst_models",
                "stage_name": "02_model_hpo_train_inner",
                "source_stage00_run_id": STAGE00_RUN_ID,
                "source_stage01_run_id": STAGE01_RUN_ID,
                "source_stage01_decision": (
                    "selected_candidate_inputs_for_stage02_train_inner_hpo"
                ),
                "stage02_modeling_scope_axis": [
                    "feature_set",
                    "window_size",
                    "model_family",
                    "hpo_profile",
                ],
                "ready_for_stage03": True,
                "decision": "ready_for_stage03_frozen_train_inner_hpo_candidates",
                "block_reason": "",
                "primary_candidate": primary,
                "fallback_candidate": fallback,
                "frozen_candidate_artifact": "02_frozen_candidate.json",
                "hpo_trial_ledger": "02_hpo_trial_ledger.csv",
                "hpo_summary": "02_hpo_summary.csv",
                "baseline_control_summary": "02_baseline_control_summary.csv",
                "official_validation_for_selection": False,
                "no_final_model_selected": True,
                "holdout_test_contact": False,
            },
        )
        self._write_stage02_inventory()

    def _write_stage02_inventory(self) -> None:
        write_artifact_inventory(
            self.stage02_dir,
            {name: self.stage02_dir / name for name in STAGE02_ARTIFACT_NAMES},
        )


@pytest.fixture()
def stage_dirs(tmp_path: Path) -> Stage03Dirs:
    return Stage03Dirs(tmp_path)


def test_blocks_when_handoff_not_ready(stage_dirs) -> None:
    stage_dirs.write_stage02_handoff(ready_for_stage03=False)
    result = run_stage(stage_dirs.config())
    record = json.loads(stage_dirs.read_output("03_decision_record.json"))
    assert record["decision"].startswith("do_not_start")
    assert record["official_validation_scoring_events"] == 0
    assert result.decision_record.exists()


def test_blocks_on_run_id_chain_mismatch(stage_dirs) -> None:
    stage_dirs.write_stage02_handoff(source_stage01_run_id="wrong_id")
    with pytest.raises(ValueError, match="run id"):
        run_stage(stage_dirs.config())


def test_blocks_when_plan_ledger_is_trial_ledger_copy(stage_dirs) -> None:
    stage_dirs.copy_trial_ledger_over_plan_ledger()
    with pytest.raises(ValueError, match="plan ledger"):
        run_stage(stage_dirs.config())


def test_blocks_on_superseded_stage02_run_id(stage_dirs) -> None:
    config = stage_dirs.config()
    config["inputs"]["stage02_run_id"] = config["inputs"]["superseded_stage02_run_ids"][0]
    with pytest.raises(ValueError, match="superseded"):
        run_stage(config)


def test_happy_path_reaches_scoring_seam(stage_dirs) -> None:
    # Gates, data context, primary dataset rebuild, and train-row parity all
    # pass on clean inputs; plan Task 8 replaces this seam test with real
    # happy-path scoring tests.
    with pytest.raises(NotImplementedError, match="Task 8"):
        run_stage(stage_dirs.config())
