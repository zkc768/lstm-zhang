from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models import fitting  # noqa: E402
from lst_models.artifacts import write_artifact_inventory, write_json  # noqa: E402
from lst_models.artifacts import feature_rebuild_code_sha256  # noqa: E402
from lst_models.data import load_sample_event_index, load_train_validation_bars  # noqa: E402
from lst_models.features import build_feature_frame  # noqa: E402
from lst_models.splits import valid_events_for_split  # noqa: E402
from lst_models.windows import build_window_dataset, sample_id_hash  # noqa: E402
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

    def rebuild_window_metadata(self, split_name: str) -> pd.DataFrame:
        """Rebuild the candidate window metadata for one split with the same
        public domain builders run_stage uses (deterministic row order)."""
        raw_manifest = json.loads(
            (self.stage00_dir / "raw_data_manifest.json").read_text(encoding="utf-8")
        )
        split_freeze = json.loads(
            (self.stage00_dir / "split_freeze.json").read_text(encoding="utf-8")
        )
        sample_events = load_sample_event_index(
            self.stage00_dir / "sample_event_index.csv"
        )
        events = valid_events_for_split(sample_events, split_name)
        bars = load_train_validation_bars(
            raw_manifest, split_freeze, {"raw_data_dir": str(self.raw_dir)}
        )
        feature_frame = build_feature_frame(bars)
        dataset = build_window_dataset(
            feature_frame,
            events,
            feature_set=FEATURE_SET,
            feature_columns=tuple(FEATURE_COLUMNS),
            window_size=WINDOW_SIZE,
        )
        return dataset.metadata

    def _compute_rebuilt_train_counts(self) -> tuple[int, dict[str, int]]:
        metadata = self.rebuild_window_metadata("train")
        by_ticker = {
            str(ticker): int(count)
            for ticker, count in metadata.groupby("ticker").size().to_dict().items()
        }
        if len(metadata) == 0:
            raise AssertionError("stage03 smoke fixture produced no rebuilt train samples")
        return int(len(metadata)), by_ticker

    def _write_stage01_run_folder(self, train_total: int, train_by_ticker: dict[str, int]) -> None:
        self.stage01_dir.mkdir(parents=True)
        write_json(
            self.stage01_dir / "run_manifest.json",
            {
                "holdout_test_contact": False,
                "config_sha256": "stage01hash",
                "feature_rebuild_code_sha256": feature_rebuild_code_sha256(),
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
                "stage02_feature_rebuild_code_sha256": feature_rebuild_code_sha256(),
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


def _install_refit_stub(
    monkeypatch: pytest.MonkeyPatch,
    y_eval: np.ndarray,
    *,
    invert: bool = False,
    fail_seeds: set[int] | frozenset[int] = frozenset(),
) -> None:
    """Deterministic stand-in for the same-stage refit dispatch seam.

    Stubbing ``_refit_and_predict`` keeps these run_stage scoring-contract
    tests model-free and torch-free (the pytest process on this machine cannot
    import torch); the real wrappers are covered by the refit tests below.
    """
    expected = np.asarray(y_eval, dtype=int)

    def stub(family, profile, x_train, train_meta, x_eval, config, seed, window_size, n_features):
        if int(seed) in fail_seeds:
            return {"fit_status": "failed_exception", "error_message": "stubbed refit crash"}
        assert len(expected) == len(x_eval)
        predictions = (1 - expected) if invert else expected.copy()
        scores = np.where(predictions == 1, 0.9, 0.1).astype(float)
        return {
            "fit_status": "completed",
            "error_message": "",
            "predictions": predictions,
            "scores": scores,
            "best_iteration": 7,
            "early_stopping_source": "inner_train_chronological_tail",
            "early_stopping_used": True,
            "early_stopping_reason": "configured_inner_train_subsplit",
            "early_stopping_train_sample_id_hash": "stub_fit_subset_hash",
            "early_stopping_eval_sample_id_hash": "stub_stop_tail_hash",
            "requested_device": "cpu",
            "resolved_device": "cpu",
            "device_fallback_reason": "not_gpu_capable_trial",
        }

    monkeypatch.setattr(stage03, "_refit_and_predict", stub)


def test_scores_each_seed_exactly_once_and_aggregates(
    stage_dirs, monkeypatch: pytest.MonkeyPatch
) -> None:
    eval_meta = stage_dirs.rebuild_window_metadata("validation")
    n_validation = len(eval_meta)
    assert n_validation > 0
    _install_refit_stub(monkeypatch, eval_meta["label"].to_numpy(dtype=int))

    result = run_stage(stage_dirs.config())

    record = json.loads(stage_dirs.read_output("03_decision_record.json"))
    assert record["official_validation_scoring_events"] == 2  # one per frozen seed
    assert [event["seed"] for event in record["scoring_event_ledger"]] == [101, 202]
    assert all(
        event["candidate_role"] == "primary" for event in record["scoring_event_ledger"]
    )
    assert record["decision"] == "met_predeclared_validation_readout_criteria"
    assert record["readout_complete"] is True
    assert record["fallback_activated"] is False

    readout = pd.read_csv(stage_dirs.read_path("03_validation_readout.csv"))
    assert set(readout["seed"].astype(str)) == {"101", "202", "aggregate_mean"}
    assert (readout["n_scored_validation_samples"] == n_validation).all()

    predictions = pd.read_csv(stage_dirs.read_path("03_validation_predictions.csv"))
    assert len(predictions) == n_validation * 2  # n_scored_validation_samples x seeds
    assert result.validation_predictions is not None
    assert result.validation_predictions.exists()


def test_weak_primary_never_activates_fallback(
    stage_dirs, monkeypatch: pytest.MonkeyPatch
) -> None:
    eval_meta = stage_dirs.rebuild_window_metadata("validation")
    _install_refit_stub(monkeypatch, eval_meta["label"].to_numpy(dtype=int), invert=True)

    run_stage(stage_dirs.config())

    record = json.loads(stage_dirs.read_output("03_decision_record.json"))
    assert record["decision"] == "did_not_meet_predeclared_validation_readout_criteria"
    assert record["fallback_activated"] is False
    assert record["criteria"] == {
        "delta_vs_stratified_dummy_met": False,
        "delta_vs_majority_met": False,
        "ticker_floor_met": False,
    }
    # Weak metrics are readout outcomes, never failures: scoring still happened
    # exactly once per frozen seed.
    assert record["official_validation_scoring_events"] == 2
    assert record["readout_complete"] is True


def test_mechanical_failure_before_scoring_activates_fallback(
    stage_dirs, monkeypatch: pytest.MonkeyPatch
) -> None:
    eval_meta = stage_dirs.rebuild_window_metadata("validation")
    _install_refit_stub(monkeypatch, eval_meta["label"].to_numpy(dtype=int))
    real_prepare = stage03._prepare_candidate_dataset

    def failing_primary_prepare(selection, data_context, events):
        if str(selection.get("hpo_profile_id")) == "p01":  # the frozen primary profile
            raise FileNotFoundError(
                "missing frozen params artifact for primary candidate profile p01"
            )
        return real_prepare(selection, data_context, events)

    monkeypatch.setattr(stage03, "_prepare_candidate_dataset", failing_primary_prepare)

    run_stage(stage_dirs.config())

    record = json.loads(stage_dirs.read_output("03_decision_record.json"))
    assert record["fallback_activated"] is True
    allowed_triggers = set(stage_dirs.config()["fallback_policy"]["allowed_triggers"])
    assert record["fallback_reason"].split(":")[0] in allowed_triggers
    assert record["official_validation_scoring_events"] == 2
    assert [event["candidate_role"] for event in record["scoring_event_ledger"]] == [
        "fallback",
        "fallback",
    ]
    assert record["scored_candidate_role"] == "fallback"
    # Decision is computed from the fallback's own readout metrics.
    assert record["decision"] == "met_predeclared_validation_readout_criteria"
    assert record["readout_complete"] is True


def test_failure_after_first_scoring_event_never_falls_back(
    stage_dirs, monkeypatch: pytest.MonkeyPatch
) -> None:
    eval_meta = stage_dirs.rebuild_window_metadata("validation")
    n_validation = len(eval_meta)
    _install_refit_stub(monkeypatch, eval_meta["label"].to_numpy(dtype=int), fail_seeds={202})

    run_stage(stage_dirs.config())

    record = json.loads(stage_dirs.read_output("03_decision_record.json"))
    assert record["readout_complete"] is False
    assert record["fallback_activated"] is False
    assert record["official_validation_scoring_events"] == 1
    assert [event["seed"] for event in record["scoring_event_ledger"]] == [101]

    # Artifacts for the completed portion are still written, and the failed
    # seed is recorded honestly in the readout ledger.
    readout = pd.read_csv(stage_dirs.read_path("03_validation_readout.csv"))
    fit_status_by_seed = dict(zip(readout["seed"].astype(str), readout["fit_status"]))
    assert fit_status_by_seed["101"] == "completed"
    assert fit_status_by_seed["202"] == "failed_exception"
    assert "aggregate_mean" in fit_status_by_seed
    predictions = pd.read_csv(stage_dirs.read_path("03_validation_predictions.csv"))
    assert len(predictions) == n_validation  # one completed seed only


def test_artifact_schemas_and_scope(stage_dirs, monkeypatch: pytest.MonkeyPatch) -> None:
    eval_meta = stage_dirs.rebuild_window_metadata("validation")
    _install_refit_stub(monkeypatch, eval_meta["label"].to_numpy(dtype=int))

    run_stage(stage_dirs.config())

    expected_columns = {
        "03_validation_readout.csv": stage03.VALIDATION_READOUT_COLUMNS,
        "03_per_ticker_readout.csv": stage03.PER_TICKER_READOUT_COLUMNS,
        "03_seed_summary.csv": stage03.SEED_SUMMARY_COLUMNS,
        "03_same_row_baselines.csv": stage03.SAME_ROW_BASELINE_COLUMNS,
        "03_validation_predictions.csv": stage03.VALIDATION_PREDICTION_COLUMNS,
    }
    for name, columns in expected_columns.items():
        frame = pd.read_csv(stage_dirs.read_path(name))
        assert list(frame.columns) == list(columns), name
        assert set(frame["scope"]) == {"validation_only"}, name

    baselines = pd.read_csv(stage_dirs.read_path("03_same_row_baselines.csv"))
    assert len(baselines) == 8  # 4 registry baselines x 2 frozen seeds
    assert set(baselines["baseline_id"]) == set(
        stage_dirs.config()["baseline_controls"]["mandatory"]
    )
    assert set(baselines["seed"]) == {101, 202}
    assert (baselines["sample_id_hash"] == baselines["eval_sample_id_hash"]).all()

    manifest = json.loads(stage_dirs.read_output("run_manifest.json"))
    assert manifest["official_validation_contact"] is True
    assert manifest["official_validation_scoring_events"] == 2
    assert manifest["holdout_test_contact"] is False
    for field_name in (
        "requested_device",
        "resolved_device",
        "cuda_available",
        "gpu_name_or_null",
        "device_fallback_reason",
    ):
        assert field_name in manifest, field_name
    assert manifest["stage03_readout_code_sha256"]


def test_checkpoint_manifest_written_per_seed(
    stage_dirs, monkeypatch: pytest.MonkeyPatch
) -> None:
    eval_meta = stage_dirs.rebuild_window_metadata("validation")
    _install_refit_stub(monkeypatch, eval_meta["label"].to_numpy(dtype=int))
    checkpoint_root = stage_dirs.tmp_path / "checkpoints"
    config = stage_dirs.config()
    config["checkpointing"] = {
        "enabled": True,
        "checkpoint_after_each_seed": True,
        "checkpoint_dir": str(checkpoint_root),
    }

    run_stage(config)

    run_id = stage_dirs._single_run_dir().name
    checkpoint_dir = checkpoint_root / run_id
    manifest = json.loads(
        (checkpoint_dir / "checkpoint_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["stage_name"] == "03_frozen_validation_readout"
    assert manifest["run_id"] == run_id
    assert manifest["status"] == "incomplete"
    assert manifest["candidate_role"] == "primary"
    assert manifest["completed_seeds"] == [101, 202]
    assert manifest["pending_seeds"] == []
    assert manifest["holdout_test_contact"] is False
    assert manifest["official_validation_for_selection"] is False
    assert manifest["checkpoint_timestamp_utc"]
    assert run_id in json.dumps(manifest["resume_instructions"])
    for name in (
        "03_validation_readout_partial.csv",
        "03_same_row_baselines_partial.csv",
        "03_validation_predictions_partial.csv",
    ):
        assert (checkpoint_dir / name).exists(), name


def _refit_train_meta(n_rows: int) -> pd.DataFrame:
    """Deterministic chronology-safe refit metadata with both label classes."""
    bars_per_day = 36
    days = pd.bdate_range("2021-01-04", periods=(n_rows // bars_per_day) + 1)
    rows = []
    for index in range(n_rows):
        day = days[index // bars_per_day]
        rows.append(
            {
                "sample_id": f"r{index:04d}",
                "ticker": "AAA" if index % 2 == 0 else "BBB",
                "target_timestamp": day + pd.Timedelta(hours=9, minutes=30 + 5 * (index % bars_per_day)),
                "trading_day": day.strftime("%Y-%m-%d"),
                "label": index % 2,
            }
        )
    return pd.DataFrame(rows)


def _refit_features(train_meta: pd.DataFrame) -> np.ndarray:
    n_rows = len(train_meta)
    position = np.arange(n_rows, dtype=np.float32) / max(1, n_rows)
    labels = train_meta["label"].to_numpy(dtype=np.float32)
    return np.column_stack(
        [position + 0.25 * labels, np.sin(0.1 * np.arange(n_rows))]
    ).astype(np.float32)


def _refit_config() -> dict:
    return {
        "lightgbm_training_defaults": {
            "eval_metric": "binary_logloss",
            "early_stopping_rounds": 5,
            "early_stopping_validation_source": "inner_train_chronological_tail",
            "early_stopping_validation_fraction": 0.2,
            "minimum_early_stopping_train_samples": 128,
            "minimum_early_stopping_validation_samples": 128,
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
    }


# TEMPORARY same-stage private-helper tests (AGENTS.md Anti-Spaghetti gates).
# Removal target: fold into public run_stage(config) scoring-contract tests
# once plan Task 8 wires _execute_readout to these refit wrappers.
def test_lightgbm_refit_uses_train_tail_eval_set(monkeypatch: pytest.MonkeyPatch) -> None:
    lightgbm = pytest.importorskip("lightgbm")
    train_meta = _refit_train_meta(320)
    x_train = _refit_features(train_meta)
    x_eval = np.column_stack(
        [np.linspace(0.1, 0.9, num=12), np.linspace(-0.5, 0.5, num=12)]
    ).astype(np.float32)
    captured: dict[str, object] = {}
    real_fit = lightgbm.LGBMClassifier.fit

    def spy_fit(self, x_fit, y_fit, **kwargs):
        captured["x_fit"] = np.asarray(x_fit).copy()
        captured["eval_set"] = kwargs.get("eval_set")
        return real_fit(self, x_fit, y_fit, **kwargs)

    monkeypatch.setattr(lightgbm.LGBMClassifier, "fit", spy_fit)

    outcome = stage03._refit_lightgbm_and_predict(
        {
            "profile_id": "p_refit_lightgbm",
            "n_estimators": 40,
            "num_leaves": 7,
            "max_depth": 3,
            "learning_rate": 0.1,
            "min_data_in_leaf": 5,
        },
        x_train,
        train_meta,
        x_eval,
        _refit_config(),
        seed=101,
    )

    assert captured["eval_set"] is not None
    tail_x, tail_y = captured["eval_set"][0]
    assert len(tail_x) < len(x_train)
    assert len(tail_x) == 128
    assert np.array_equal(tail_x, x_train[-128:])
    assert np.array_equal(tail_y, train_meta["label"].to_numpy(dtype=int)[-128:])
    sample_ids = train_meta["sample_id"].tolist()
    assert outcome["early_stopping_train_sample_id_hash"] == sample_id_hash(sample_ids[:-128])
    assert outcome["early_stopping_eval_sample_id_hash"] == sample_id_hash(sample_ids[-128:])
    assert outcome["early_stopping_source"] == "inner_train_chronological_tail"
    assert outcome["early_stopping_used"] is True
    assert outcome["fit_status"] == "completed"
    assert len(outcome["predictions"]) == len(x_eval)
    assert outcome["best_iteration"] is not None


def test_lightgbm_refit_without_tail_when_rows_insufficient() -> None:
    pytest.importorskip("lightgbm")
    train_meta = _refit_train_meta(200)
    x_train = _refit_features(train_meta)
    x_eval = np.column_stack(
        [np.linspace(0.2, 0.8, num=6), np.linspace(-0.3, 0.3, num=6)]
    ).astype(np.float32)

    outcome = stage03._refit_lightgbm_and_predict(
        {
            "profile_id": "p_refit_no_tail",
            "n_estimators": 20,
            "num_leaves": 5,
            "max_depth": 2,
            "learning_rate": 0.1,
        },
        x_train,
        train_meta,
        x_eval,
        _refit_config(),
        seed=101,
    )

    assert outcome["fit_status"] == "completed"
    assert outcome["early_stopping_used"] is False
    assert outcome["early_stopping_reason"] == (
        "insufficient_inner_train_rows_for_minimum_validation_subsplit"
    )
    assert outcome["early_stopping_eval_sample_id_hash"] == ""
    assert len(outcome["predictions"]) == len(x_eval)


def test_torch_refit_maps_probe_result_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    probe_result = fitting.ProbeFitResult(
        predictions=np.asarray([1, 0, 1], dtype=int),
        scores=np.asarray([0.9, 0.2, 0.8], dtype=float),
        requested_device="cpu",
        resolved_device="cpu",
        cuda_available=False,
        gpu_name_or_null=None,
        device_fallback_reason="cuda_unavailable",
        best_iteration=4,
        early_stopping_source="inner_train_chronological_tail",
        early_stopping_used=True,
        early_stopping_reason="patience_exhausted",
        early_stopping_train_sample_id_hash="hash_fit_subset",
        early_stopping_eval_sample_id_hash="hash_stop_tail",
    )

    def fake_fit_torch_sequence_probe(
        probe_id,
        x_train,
        y_train,
        x_eval,
        trial_config,
        seed,
        window_size,
        n_features,
        *,
        train_meta=None,
    ):
        captured["probe_id"] = probe_id
        captured["trial_config"] = trial_config
        captured["seed"] = seed
        captured["window_size"] = window_size
        captured["n_features"] = n_features
        captured["train_meta_rows"] = 0 if train_meta is None else len(train_meta)
        captured["y_train"] = np.asarray(y_train).copy()
        return probe_result

    monkeypatch.setattr(fitting, "fit_torch_sequence_probe", fake_fit_torch_sequence_probe)
    train_meta = _refit_train_meta(4)
    x_train = np.arange(16, dtype=np.float32).reshape(4, 4)
    x_eval = np.arange(12, dtype=np.float32).reshape(3, 4)
    profile = {"profile_id": "p_torch", "learning_rate": 0.005, "epochs": 3, "channels": [8, 8]}

    outcome = stage03._refit_torch_and_predict(
        "tcn", profile, x_train, train_meta, x_eval, _refit_config(), 202, 2, 2
    )

    assert captured["probe_id"] == "tcn_tiny"
    assert captured["seed"] == 202
    assert captured["window_size"] == 2
    assert captured["n_features"] == 2
    assert captured["train_meta_rows"] == len(train_meta)
    assert np.array_equal(captured["y_train"], train_meta["label"].to_numpy(dtype=int))
    trial_config = captured["trial_config"]
    fixed_defaults = trial_config["lightweight_probes"]["tcn_tiny"]["fixed_defaults"]
    assert fixed_defaults == {"learning_rate": 0.005, "epochs": 3, "channels": [8, 8]}
    torch_defaults = trial_config["probe_training_defaults"]["torch"]
    assert torch_defaults["learning_rate"] == 0.005
    assert torch_defaults["epochs"] == 3
    assert torch_defaults["device"] == "cpu"

    assert outcome["fit_status"] == "completed"
    assert np.array_equal(outcome["predictions"], probe_result.predictions)
    assert np.array_equal(outcome["scores"], probe_result.scores)
    assert outcome["best_iteration"] == 4
    assert outcome["early_stopping_source"] == "inner_train_chronological_tail"
    assert outcome["early_stopping_used"] is True
    assert outcome["early_stopping_reason"] == "patience_exhausted"
    assert outcome["early_stopping_train_sample_id_hash"] == "hash_fit_subset"
    assert outcome["early_stopping_eval_sample_id_hash"] == "hash_stop_tail"
    assert outcome["requested_device"] == "cpu"
    assert outcome["resolved_device"] == "cpu"
    assert outcome["device_fallback_reason"] == "cuda_unavailable"


def test_refit_dispatch_rejects_unknown_family() -> None:
    train_meta = _refit_train_meta(4)
    x_train = np.arange(8, dtype=np.float32).reshape(4, 2)
    x_eval = np.arange(4, dtype=np.float32).reshape(2, 2)

    with pytest.raises(ValueError, match="unknown Stage 03 refit model family"):
        stage03._refit_and_predict(
            "shallow_lstm",
            {"profile_id": "p_bad"},
            x_train,
            train_meta,
            x_eval,
            _refit_config(),
            101,
            2,
            1,
        )


def _checkpointing_block(stage_dirs) -> dict:
    return {
        "enabled": True,
        "checkpoint_after_each_seed": True,
        "checkpoint_dir": str(stage_dirs.tmp_path / "checkpoints"),
    }


def test_resume_completes_pending_seed_without_repeating_scoring(
    stage_dirs, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Protocol section 11: a resumed run loads the exact checkpoint, retries
    only the seed without a scoring event, and never re-scores seed 101."""
    eval_meta = stage_dirs.rebuild_window_metadata("validation")
    y_eval = eval_meta["label"].to_numpy(dtype=int)

    config = stage_dirs.config()
    config["checkpointing"] = _checkpointing_block(stage_dirs)
    _install_refit_stub(monkeypatch, y_eval, fail_seeds={202})
    run_stage(config)

    first_record = json.loads(stage_dirs.read_output("03_decision_record.json"))
    assert first_record["readout_complete"] is False
    assert first_record["official_validation_scoring_events"] == 1
    first_events = first_record["scoring_event_ledger"]
    assert [event["seed"] for event in first_events] == [101]
    run_id = stage_dirs.read_path("run_manifest.json").parent.name
    checkpoint_dir = stage_dirs.tmp_path / "checkpoints" / run_id
    assert (checkpoint_dir / "03_ledger_state_partial.json").exists()

    _install_refit_stub(monkeypatch, y_eval)
    resume_config = stage_dirs.config()
    resume_config["checkpointing"] = _checkpointing_block(stage_dirs)
    resume_config["resume"] = {
        "enabled": True,
        "run_id": run_id,
        "checkpoint_dir": str(checkpoint_dir),
    }
    result = run_stage(resume_config)

    assert Path(result.output_dir).name == run_id
    record = json.loads(stage_dirs.read_output("03_decision_record.json"))
    assert record["resumed_from_checkpoint"] is True
    assert record["readout_complete"] is True
    assert record["official_validation_scoring_events"] == 2
    assert [event["seed"] for event in record["scoring_event_ledger"]] == [101, 202]
    # Seed 101's restored scoring event is byte-identical: it was never re-scored.
    assert record["scoring_event_ledger"][0] == first_events[0]
    assert record["readout_incomplete_reason"].startswith("resolved_after_resume: ")

    readout = pd.read_csv(stage_dirs.read_path("03_validation_readout.csv"))
    per_seed = readout[readout["seed"].astype(str).isin({"101", "202"})]
    assert sorted(per_seed["seed"].astype(int).tolist()) == [101, 202]
    assert (per_seed["fit_status"] == "completed").all()
    predictions = pd.read_csv(stage_dirs.read_path("03_validation_predictions.csv"))
    assert len(predictions) == len(eval_meta) * 2

    # Idempotence: a second resume with every seed completed re-scores nothing.
    rerun_config = stage_dirs.config()
    rerun_config["checkpointing"] = _checkpointing_block(stage_dirs)
    rerun_config["resume"] = {
        "enabled": True,
        "run_id": run_id,
        "checkpoint_dir": str(checkpoint_dir),
    }
    run_stage(rerun_config)
    rerun_record = json.loads(stage_dirs.read_output("03_decision_record.json"))
    assert rerun_record["official_validation_scoring_events"] == 2
    assert rerun_record["scoring_event_ledger"] == record["scoring_event_ledger"]


def test_resume_rejects_inexact_or_missing_checkpoint_inputs(
    stage_dirs, monkeypatch: pytest.MonkeyPatch
) -> None:
    eval_meta = stage_dirs.rebuild_window_metadata("validation")
    _install_refit_stub(monkeypatch, eval_meta["label"].to_numpy(dtype=int))

    bad_run_id = stage_dirs.config()
    bad_run_id["resume"] = {
        "enabled": True,
        "run_id": "latest",
        "checkpoint_dir": str(stage_dirs.tmp_path / "checkpoints" / "latest"),
    }
    with pytest.raises(ValueError, match="exact Stage 03 run id"):
        run_stage(bad_run_id)

    mismatched_folder = stage_dirs.config()
    mismatched_folder["resume"] = {
        "enabled": True,
        "run_id": "20260610_120000_000001",
        "checkpoint_dir": str(stage_dirs.tmp_path / "checkpoints"),
    }
    with pytest.raises(ValueError, match="must end in the exact resume.run_id"):
        run_stage(mismatched_folder)

    missing_files = stage_dirs.config()
    empty_dir = stage_dirs.tmp_path / "checkpoints" / "20260610_120000_000001"
    empty_dir.mkdir(parents=True)
    missing_files["resume"] = {
        "enabled": True,
        "run_id": "20260610_120000_000001",
        "checkpoint_dir": str(empty_dir),
    }
    with pytest.raises(FileNotFoundError, match="resume checkpoint files"):
        run_stage(missing_files)
