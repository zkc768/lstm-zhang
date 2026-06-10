"""Stage 04 run_stage smoke tests: fail-closed gates, measure-only
diagnostics, reconstruction equality semantics, train-inner ablation
contracts, checkpoints, and exact-run resume — all on a tiny chronology-safe
fixture whose dates stay strictly before the 2017-01-25 closed boundary."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models import diagnostics, fitting, metrics  # noqa: E402
from lst_models.artifacts import write_artifact_inventory, write_json  # noqa: E402
from lst_models.artifacts import feature_rebuild_code_sha256  # noqa: E402
from lst_models.data import load_sample_event_index  # noqa: E402
from lst_models.features import build_feature_frame  # noqa: E402
from lst_models.data import load_train_bars  # noqa: E402
from lst_models.splits import build_train_inner_folds, valid_events_for_split  # noqa: E402
from lst_models.windows import (  # noqa: E402
    build_window_dataset,
    cap_indices,
    fold_indices,
    sample_id_hash,
)
from lst_models.stages import diagnostics_ablation as stage04  # noqa: E402
from lst_models.stages.diagnostics_ablation import run_stage  # noqa: E402


TICKERS = ["AAA", "BBB"]
TRAIN_DAYS = ["2013-01-02", "2013-01-03", "2013-01-04", "2013-01-07"]
VALIDATION_DAYS = ["2013-01-08", "2013-01-09"]
BARS_PER_DAY = 36
WINDOW_SIZE = 10
FEATURE_SET = "price_action_core"
FEATURE_COLUMNS = ["log_return"]
CANDIDATE_ID = f"{FEATURE_SET}_w{WINDOW_SIZE}"
N_FOLDS = 2
SEEDS = [101, 202]
STAGE00_RUN_ID = "stage00_test_run"
STAGE01_RUN_ID = "stage01_test_run"
STAGE02_RUN_ID = "20990101_000000_000002"
STAGE03_RUN_ID = "20990101_000000_000003"
SUPERSEDED_STAGE02_RUN_ID = "20260609_100637_704705"


@pytest.fixture(autouse=True)
def disable_torch_import_for_fast_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        fitting, "TORCH_IMPORT_ERROR", "torch disabled in fast Stage 04 smoke test"
    )


class Stage04Dirs:
    """Fake frozen stage00-03 chain with real sha256 inventories, a synthetic
    Stage 03 prediction dump generated so the OD2 reconstruction equality
    gates pass end-to-end, and a Stage 02 plan ledger whose fold hashes match
    the deterministic rebuild."""

    def __init__(self, tmp_path: Path) -> None:
        self.tmp_path = tmp_path
        self.raw_dir = tmp_path / "raw"
        self.stage00_dir = tmp_path / "stage00" / STAGE00_RUN_ID
        self.stage01_dir = tmp_path / "stage01" / STAGE01_RUN_ID
        self.stage02_dir = tmp_path / "stage02" / STAGE02_RUN_ID
        self.stage03_dir = tmp_path / "stage03" / STAGE03_RUN_ID
        self.output_dir = tmp_path / "out"
        self.checkpoint_root = tmp_path / "ckpt"
        self.notebook_path = tmp_path / "04_diagnostics_ablation_colab.ipynb"
        self.notebook_path.write_text("{}", encoding="utf-8")
        self._write_stage00_run_folder()
        self.train_metadata = self._rebuild_train_metadata()
        self.train_labels = self.train_metadata["label"].to_numpy(dtype=int)
        self._write_stage01_run_folder()
        self.fold_hashes = self._compute_fold_hashes()
        self._write_stage02_run_folder()
        self.dump = self._build_dump()
        self._write_stage03_run_folder()

    # ------------------------------------------------------------- config --
    def config(self) -> dict:
        return {
            "stage_name": "04_diagnostics_ablation",
            "route": "lst_models",
            "scope": "validation_only",
            "holdout_test_contact": False,
            "official_validation_contact": "read_frozen_artifacts_only",
            "official_validation_for_selection": False,
            "new_validation_fit_predict_events": 0,
            "inputs": {
                "stage00_run_id": STAGE00_RUN_ID,
                "stage00_runtime_run_dir": str(self.stage00_dir),
                "required_stage00_artifacts": [
                    "raw_data_manifest.json", "split_freeze.json", "label_policy.json",
                    "baseline_registry.json", "sample_event_index.csv",
                    "run_manifest.json", "artifact_inventory.csv",
                ],
                "stage01_run_id": STAGE01_RUN_ID,
                "stage01_runtime_run_dir": str(self.stage01_dir),
                "required_stage01_artifacts": [
                    "run_manifest.json", "artifact_inventory.csv",
                    "01_candidate_inputs.json", "01_feature_window_search_summary.csv",
                ],
                "stage02_run_id": STAGE02_RUN_ID,
                "stage02_runtime_run_dir": str(self.stage02_dir),
                "superseded_stage02_run_ids": [SUPERSEDED_STAGE02_RUN_ID],
                "required_stage02_artifacts": [
                    "run_manifest.json", "artifact_inventory.csv",
                    "02_hpo_plan_ledger.csv", "02_hpo_trial_ledger.csv",
                    "02_baseline_control_summary.csv", "02_frozen_candidate.json",
                    "02_best_params_by_family.json", "02_stage03_handoff.json",
                ],
                "stage03_run_id": STAGE03_RUN_ID,
                "stage03_runtime_run_dir": str(self.stage03_dir),
                "required_stage03_artifacts": [
                    "run_manifest.json", "artifact_inventory.csv",
                    "03_validation_readout.csv", "03_per_ticker_readout.csv",
                    "03_seed_summary.csv", "03_same_row_baselines.csv",
                    "03_validation_predictions.csv", "03_decision_record.json",
                ],
                "raw_data_manifest": "configs/lst_models_data.yaml",
                "raw_data_dir": str(self.raw_dir),
                "notebook_path": str(self.notebook_path),
            },
            "outputs": {
                "output_dir": str(self.output_dir),
                "manifest": "run_manifest.json",
                "artifact_inventory": "artifact_inventory.csv",
                "calibration_summary": "04_calibration_summary.csv",
                "reliability_bins": "04_reliability_bins.csv",
                "risk_coverage_curve": "04_risk_coverage_curve.csv",
                "selective_summary": "04_selective_summary.csv",
                "robustness_slices": "04_robustness_slices.csv",
                "failure_slices": "04_failure_slices.csv",
                "ablation_plan_ledger": "04_ablation_plan_ledger.csv",
                "ablation_trial_ledger": "04_ablation_trial_ledger.csv",
                "ablation_summary": "04_ablation_summary.csv",
                "diagnostics_report": "04_diagnostics_report.json",
            },
            "diagnostics": {
                "source": "stage03_validation_predictions_only",
                "expected_dump_rows": int(len(self.dump)),
                "expected_seeds": SEEDS,
                "calibration": {
                    "probability_views": ["p_up", "top_label_confidence"],
                    "primary_view": "p_up",
                    "binning_schemes": ["equal_width", "equal_mass"],
                    "primary_scheme": "equal_width",
                    "bin_counts": [2, 3],
                    "primary_bin_count": 2,
                    "no_calibrator_fitting": True,
                },
                "selective": {
                    "confidence_score": "top_label_confidence",
                    "risk_definition": "one_minus_accuracy_on_covered_rows",
                    "curve_resolution": "per_row_full_resolution",
                    "csv_coverage_grid_step": 0.25,
                    "csv_coverage_grid_minimum": 0.25,
                    "report_macro_f1_on_covered_rows": True,
                    "no_operating_point": True,
                },
                "baseline_reconstruction": {
                    "enabled": True,
                    "baseline_id": "stratified_dummy_train_prior",
                    "equality_tolerance": 1.0e-9,
                    "pooled_gate_artifact": "03_same_row_baselines.csv",
                    "per_ticker_gate_artifact": "03_per_ticker_readout.csv",
                    "on_mismatch": "mark_not_computed_keep_frozen_ticker_rows",
                },
                "robustness_slices": {
                    "slice_axes": [
                        "ticker", "seed", "calendar_year", "calendar_quarter",
                        "time_of_day_hour", "activity_tercile",
                    ],
                    "loo_sign_flip_axes": ["ticker", "seed", "calendar_year"],
                    "activity_proxy": "eligible_rows_per_ticker_trading_day_terciles",
                },
                "failure_slices": {
                    "slice_axes": [
                        "ticker_hour", "ticker_trading_day", "activity_tercile",
                        "calendar_month",
                    ],
                    "minimum_slice_rows": 5,
                    "top_k_per_axis": 5,
                },
                "bootstrap": {
                    "device": "trading_day_block_bootstrap",
                    "block_id": "ticker_trading_day",
                    "iterations": 25,
                    "seed": 12345,
                },
            },
            "ablation": {
                "candidate_input": CANDIDATE_ID,
                "fold_source": "stage02_train_inner_contract",
                "n_folds": N_FOLDS,
                "seeds": SEEDS,
                "hpo_sample_policy": {
                    "max_train_samples_per_fold": 200,
                    "max_eval_samples_per_fold": 100,
                    "sample_method": "deterministic_even_stride_by_ticker_label",
                },
                "controls": {
                    "tcn_only": {
                        "probe_id": "tcn_tiny",
                        "params_source": "stage03_decision_record_primary_hpo_profile_params",
                    },
                    "dlinear_only": {
                        "probe_id": "ms_dlinear_only_tiny",
                        "params_source": (
                            "stage02_best_params_by_family_ms_dlinear_tcn_dlinear_branch"
                        ),
                        "dropped_keys": ["tcn_channels", "tcn_kernel_size"],
                    },
                    "last_step_mlp": {
                        "probe_id": "last_step_mlp_tiny",
                        "params_source": "fixed_in_config",
                        "fixed_params": {
                            "hidden_size": 8, "dropout": 0.1,
                            "learning_rate": 0.001, "weight_decay": 0.0001,
                        },
                    },
                    "last_step_lightgbm_control": {
                        "probe_id": "last_step_lightgbm_control",
                        "params_source": "stage02_best_params_by_family_lightgbm",
                    },
                },
                "budget": {"max_ablation_plan_rows": 16},
                "reference_rows": {
                    "source": "02_hpo_trial_ledger.csv",
                    "candidate_id": CANDIDATE_ID,
                    "model_family": "tcn",
                    "hpo_profile_id": "tcn_p01",
                    "expected_row_count": N_FOLDS * len(SEEDS),
                },
                "same_row_baselines": {
                    "mandatory": [
                        "stratified_dummy_train_prior", "majority_train_prior",
                        "constant_up", "constant_down",
                    ],
                    "sample_hash_parity_artifact": "02_hpo_plan_ledger.csv",
                },
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
                    "epochs": 1, "batch_size": 64, "learning_rate": 0.001,
                    "weight_decay": 0.0001, "device": "cpu", "require_gpu": False,
                }
            },
            "checkpointing": {
                "enabled": True,
                "checkpoint_after_each_control": True,
                "checkpoint_dir": str(self.checkpoint_root),
                "checkpoint_drive_path_parts": [
                    "lst_models", "checkpoints", "04_diagnostics_ablation",
                ],
            },
            "resume": {"enabled": False, "run_id": None, "checkpoint_dir": None},
            "forbidden": {
                "wording": ["final model", "selected by official validation", "chosen threshold"]
            },
        }

    # ------------------------------------------------------- stage folders --
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
                    "open": "first", "high": "max", "low": "min",
                    "close": "last", "volume": "sum",
                },
                "drop_na_subset": ["open", "high", "low", "close", "volume"],
                "output_columns": [
                    "ticker", "timestamp", "open", "high", "low", "close", "volume",
                ],
            },
        }

    def _write_stage00_run_folder(self) -> None:
        self.stage00_dir.mkdir(parents=True)
        write_json(self.stage00_dir / "raw_data_manifest.json", self._raw_manifest_payload())
        write_json(
            self.stage00_dir / "split_freeze.json",
            {
                "train_start": "2013-01-02 00:00:00",
                "train_end": "2013-01-08 00:00:00",
                "validation_start": "2013-01-08 00:00:00",
                "validation_end": "2013-01-10 00:00:00",
                "closed_holdout_test_start": "2017-01-25 00:00:00",
            },
        )
        write_json(
            self.stage00_dir / "label_policy.json",
            {"label_config_id": "h01_bps3p0", "operator": "endpoint_cumulative_return",
             "horizon_k": 1, "no_trade_band_bps": 3.0},
        )
        write_json(self.stage00_dir / "baseline_registry.json", {})
        write_json(
            self.stage00_dir / "run_manifest.json",
            {"holdout_test_contact": False, "config_sha256": "stage00hash"},
        )
        self._write_raw_txt_and_sample_events()
        names = [
            "raw_data_manifest.json", "split_freeze.json", "label_policy.json",
            "baseline_registry.json", "sample_event_index.csv", "run_manifest.json",
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
                    for minute_offset, close_value in enumerate(
                        np.linspace(bar_open, bar_close, num=5)
                    ):
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

    def _rebuild_train_metadata(self) -> pd.DataFrame:
        raw_manifest = self._raw_manifest_payload()
        split_freeze = json.loads(
            (self.stage00_dir / "split_freeze.json").read_text(encoding="utf-8")
        )
        sample_events = load_sample_event_index(self.stage00_dir / "sample_event_index.csv")
        events = valid_events_for_split(sample_events, "train")
        bars = load_train_bars(raw_manifest, split_freeze, {"raw_data_dir": str(self.raw_dir)})
        dataset = build_window_dataset(
            build_feature_frame(bars),
            events,
            feature_set=FEATURE_SET,
            feature_columns=tuple(FEATURE_COLUMNS),
            window_size=WINDOW_SIZE,
        )
        return dataset.metadata

    def _write_stage01_run_folder(self) -> None:
        self.stage01_dir.mkdir(parents=True)
        by_ticker = {
            str(ticker): int(count)
            for ticker, count in self.train_metadata.groupby("ticker").size().items()
        }
        write_json(
            self.stage01_dir / "run_manifest.json",
            {"holdout_test_contact": False, "config_sha256": "stage01hash",
             "feature_rebuild_code_sha256": feature_rebuild_code_sha256()},
        )
        write_json(
            self.stage01_dir / "01_candidate_inputs.json",
            {
                "source_stage00_run_id": STAGE00_RUN_ID,
                "candidate_inputs": [
                    {
                        "candidate_id": CANDIDATE_ID,
                        "feature_set": FEATURE_SET,
                        "window_size": WINDOW_SIZE,
                        "feature_columns": list(FEATURE_COLUMNS),
                        "n_samples_total": int(len(self.train_metadata)),
                    }
                ],
                "no_final_model_selected": True,
                "holdout_test_contact": False,
            },
        )
        pd.DataFrame(
            [
                {
                    "candidate_id": CANDIDATE_ID,
                    "selected_for_stage02": True,
                    "n_samples_total": int(len(self.train_metadata)),
                    "n_samples_by_ticker_json": json.dumps(by_ticker, sort_keys=True),
                }
            ]
        ).to_csv(self.stage01_dir / "01_feature_window_search_summary.csv", index=False)
        names = [
            "run_manifest.json", "01_candidate_inputs.json",
            "01_feature_window_search_summary.csv",
        ]
        write_artifact_inventory(
            self.stage01_dir, {name: self.stage01_dir / name for name in names}
        )

    def _compute_fold_hashes(self) -> dict[str, tuple[str, str]]:
        sample_events = load_sample_event_index(self.stage00_dir / "sample_event_index.csv")
        train_events = valid_events_for_split(sample_events, "train")
        folds = build_train_inner_folds(train_events, N_FOLDS)
        hashes: dict[str, tuple[str, str]] = {}
        for fold in folds.to_dict(orient="records"):
            train_idx, eval_idx = fold_indices(self.train_metadata, fold)
            train_idx = cap_indices(self.train_metadata, train_idx, 200)
            eval_idx = cap_indices(self.train_metadata, eval_idx, 100)
            hashes[str(fold["fold_id"])] = (
                sample_id_hash(self.train_metadata.iloc[train_idx]["sample_id"].tolist()),
                sample_id_hash(self.train_metadata.iloc[eval_idx]["sample_id"].tolist()),
            )
        return hashes

    def _write_stage02_run_folder(self) -> None:
        self.stage02_dir.mkdir(parents=True)
        write_json(
            self.stage02_dir / "run_manifest.json",
            {
                "holdout_test_contact": False,
                "official_validation_for_selection": False,
                "source_stage00_run_id": STAGE00_RUN_ID,
                "source_stage01_run_id": STAGE01_RUN_ID,
                "stage02_feature_rebuild_code_sha256": feature_rebuild_code_sha256(),
            },
        )
        plan_rows = []
        trial_rows = []
        for fold_id, (train_hash, eval_hash) in self.fold_hashes.items():
            for seed in SEEDS:
                plan_rows.append(
                    {
                        "trial_id": f"trial_{fold_id}_{seed}",
                        "candidate_id": CANDIDATE_ID,
                        "fold_id": fold_id,
                        "seed": seed,
                        "plan_status": "planned",
                        "train_sample_id_hash": train_hash,
                        "eval_sample_id_hash": eval_hash,
                    }
                )
                trial_rows.append(
                    {
                        # mirrors the REAL stage02 HPO_TRIAL_LEDGER_COLUMNS subset
                        # stage04 consumes (delta vs baseline_id, not a long name)
                        "trial_id": f"trial_{fold_id}_{seed}",
                        "candidate_id": CANDIDATE_ID,
                        "model_family": "tcn",
                        "hpo_profile_id": "tcn_p01",
                        "fold_id": fold_id,
                        "seed": seed,
                        "fit_status": "completed",
                        "baseline_id": "stratified_dummy_train_prior",
                        "macro_f1": 0.52,
                        "delta_macro_f1_vs_baseline": 0.02,
                    }
                )
        pd.DataFrame(plan_rows).to_csv(self.stage02_dir / "02_hpo_plan_ledger.csv", index=False)
        pd.DataFrame(trial_rows).to_csv(self.stage02_dir / "02_hpo_trial_ledger.csv", index=False)
        pd.DataFrame(
            [{"candidate_id": CANDIDATE_ID, "baseline_id": "stratified_dummy_train_prior"}]
        ).to_csv(self.stage02_dir / "02_baseline_control_summary.csv", index=False)
        write_json(
            self.stage02_dir / "02_frozen_candidate.json",
            {"source_stage00_run_id": STAGE00_RUN_ID, "source_stage01_run_id": STAGE01_RUN_ID,
             "holdout_test_contact": False, "official_validation_for_selection": False},
        )
        write_json(
            self.stage02_dir / "02_best_params_by_family.json",
            {
                "best_params_by_family": {
                    "ms_dlinear_tcn": {
                        "hpo_profile_id": "msdt_p01",
                        "hpo_profile_params": {
                            "moving_avg_kernels": [3, 5], "tcn_channels": [8, 8],
                            "tcn_kernel_size": 3, "dropout": 0.1,
                            "learning_rate": 0.001, "weight_decay": 0.0001,
                        },
                    },
                    "lightgbm": {
                        "hpo_profile_id": "lgbm_p02",
                        "hpo_profile_params": {
                            "n_estimators": 20, "learning_rate": 0.1, "max_depth": 3,
                            "num_leaves": 7, "min_child_samples": 5, "subsample": 0.9,
                            "colsample_bytree": 0.9, "reg_lambda": 1.0,
                            "class_weight": "balanced",
                        },
                    },
                },
                "holdout_test_contact": False,
            },
        )
        write_json(
            self.stage02_dir / "02_stage03_handoff.json",
            {"ready_for_stage03": True, "holdout_test_contact": False,
             "official_validation_for_selection": False, "no_final_model_selected": True},
        )
        self._write_stage02_inventory()

    def _write_stage02_inventory(self) -> None:
        names = [
            "run_manifest.json", "02_hpo_plan_ledger.csv", "02_hpo_trial_ledger.csv",
            "02_baseline_control_summary.csv", "02_frozen_candidate.json",
            "02_best_params_by_family.json", "02_stage03_handoff.json",
        ]
        write_artifact_inventory(
            self.stage02_dir, {name: self.stage02_dir / name for name in names}
        )

    def _build_dump(self) -> pd.DataFrame:
        sample_events = load_sample_event_index(self.stage00_dir / "sample_event_index.csv")
        events = valid_events_for_split(sample_events, "validation")
        rows = []
        rng = np.random.default_rng(7)
        for seed in SEEDS:
            for position, event in enumerate(events.to_dict(orient="records")):
                y_true = int(event["label"])
                correct = (position + seed) % 3 != 0  # deterministic mix of errors
                y_pred = y_true if correct else 1 - y_true
                p_up = float(
                    np.clip(0.5 + (0.3 if y_pred == 1 else -0.3) + rng.normal(0, 0.05), 0.01, 0.99)
                )
                rows.append(
                    {
                        "candidate_role": "primary",
                        "candidate_id": CANDIDATE_ID,
                        "model_family": "tcn",
                        "hpo_profile_id": "tcn_p01",
                        "seed": seed,
                        "sample_id": str(event["sample_id"]),
                        "ticker": str(event["ticker"]),
                        "target_timestamp": pd.Timestamp(event["target_timestamp"]).isoformat(),
                        "trading_day": str(event["trading_day"]),
                        "y_true": y_true,
                        "p_up": p_up,
                        "y_pred": int(p_up >= 0.5),
                        "scope": "validation_only",
                    }
                )
        return pd.DataFrame(rows)

    def _write_stage03_run_folder(self) -> None:
        self.stage03_dir.mkdir(parents=True)
        write_json(
            self.stage03_dir / "run_manifest.json",
            {"holdout_test_contact": False, "official_validation_for_selection": False,
             "official_validation_contact": True},
        )
        baseline_rows = []
        ticker_rows = []
        per_seed = []
        for seed in SEEDS:
            seed_dump = self.dump.loc[self.dump["seed"].eq(seed)]
            dummy, _ = metrics.predict_stratified_dummy(
                self.train_labels, len(seed_dump), seed
            )
            y_true = seed_dump["y_true"].to_numpy(dtype=int)
            scored = metrics.score_classifier(y_true, dummy)
            baseline_rows.append(
                {
                    "candidate_role": "primary", "candidate_id": CANDIDATE_ID,
                    "seed": seed, "baseline_id": "stratified_dummy_train_prior",
                    "fit_status": "completed_baseline", **scored,
                }
            )
            deltas, _ = metrics.ticker_delta_macro_f1(
                pd.DataFrame({"ticker": seed_dump["ticker"].to_numpy(), "label": y_true}),
                seed_dump["y_pred"].to_numpy(dtype=int),
                dummy,
            )
            for ticker, delta in deltas.items():
                ticker_rows.append(
                    {
                        "candidate_role": "primary", "candidate_id": CANDIDATE_ID,
                        "seed": seed, "ticker": ticker,
                        "delta_macro_f1_vs_stratified_dummy_train_prior": delta,
                    }
                )
            per_seed.append({"seed": seed, "n_rows": int(len(seed_dump))})
        pd.DataFrame(baseline_rows).to_csv(
            self.stage03_dir / "03_same_row_baselines.csv", index=False
        )
        pd.DataFrame(ticker_rows).to_csv(
            self.stage03_dir / "03_per_ticker_readout.csv", index=False
        )
        pd.DataFrame([{"placeholder": True}]).to_csv(
            self.stage03_dir / "03_validation_readout.csv", index=False
        )
        pd.DataFrame([{"placeholder": True}]).to_csv(
            self.stage03_dir / "03_seed_summary.csv", index=False
        )
        self.dump.to_csv(self.stage03_dir / "03_validation_predictions.csv", index=False)
        write_json(
            self.stage03_dir / "03_decision_record.json",
            {
                "decision": "met_predeclared_validation_readout_criteria",
                "readout_complete": True,
                "holdout_test_contact": False,
                "official_validation_for_selection": False,
                "official_validation_scoring_events": len(per_seed),
                "scoring_event_ledger": per_seed,
                "source_stage00_run_id": STAGE00_RUN_ID,
                "source_stage01_run_id": STAGE01_RUN_ID,
                "source_stage02_run_id": STAGE02_RUN_ID,
                "primary_candidate": {
                    "candidate_id": CANDIDATE_ID,
                    "model_family": "tcn",
                    "hpo_profile_id": "tcn_p01",
                    "hpo_profile_params": {
                        "channels": [8, 8], "kernel_size": 2, "dropout": 0.0,
                        "learning_rate": 0.001, "weight_decay": 0.0001,
                    },
                },
            },
        )
        self._write_stage03_inventory()

    def _write_stage03_inventory(self) -> None:
        names = [
            "run_manifest.json", "03_validation_readout.csv", "03_per_ticker_readout.csv",
            "03_seed_summary.csv", "03_same_row_baselines.csv",
            "03_validation_predictions.csv", "03_decision_record.json",
        ]
        write_artifact_inventory(
            self.stage03_dir, {name: self.stage03_dir / name for name in names}
        )

    # ------------------------------------------------------------ mutators --
    def write_decision_record_override(self, **overrides: object) -> None:
        path = self.stage03_dir / "03_decision_record.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record.update(overrides)
        write_json(path, record)
        self._write_stage03_inventory()

    def corrupt_dump_drop_column(self, column: str) -> None:
        path = self.stage03_dir / "03_validation_predictions.csv"
        pd.read_csv(path).drop(columns=[column]).to_csv(path, index=False)
        self._write_stage03_inventory()

    def poison_dump_with_boundary_row(self) -> None:
        path = self.stage03_dir / "03_validation_predictions.csv"
        dump = pd.read_csv(path)
        poisoned = dump.iloc[[0]].copy()
        poisoned["target_timestamp"] = "2017-01-25T10:00:00"
        poisoned["sample_id"] = "poisoned_row"
        dump = pd.concat([dump, poisoned], ignore_index=True)
        dump.to_csv(path, index=False)
        record = json.loads(
            (self.stage03_dir / "03_decision_record.json").read_text(encoding="utf-8")
        )
        record["scoring_event_ledger"][-1]["n_rows"] += 1
        write_json(self.stage03_dir / "03_decision_record.json", record)
        self._write_stage03_inventory()

    def perturb_frozen_baseline(self) -> None:
        path = self.stage03_dir / "03_same_row_baselines.csv"
        frame = pd.read_csv(path)
        frame.loc[0, "macro_f1"] = float(frame.loc[0, "macro_f1"]) + 1e-3
        frame.to_csv(path, index=False)
        self._write_stage03_inventory()

    def copy_trial_ledger_over_plan_ledger(self) -> None:
        (self.stage02_dir / "02_hpo_plan_ledger.csv").write_bytes(
            (self.stage02_dir / "02_hpo_trial_ledger.csv").read_bytes()
        )
        self._write_stage02_inventory()

    def corrupt_plan_ledger_hashes(self) -> None:
        path = self.stage02_dir / "02_hpo_plan_ledger.csv"
        frame = pd.read_csv(path)
        frame["train_sample_id_hash"] = "deadbeef"
        frame.to_csv(path, index=False)
        self._write_stage02_inventory()

    def drop_reference_trial_rows(self, keep: int) -> None:
        path = self.stage02_dir / "02_hpo_trial_ledger.csv"
        pd.read_csv(path).head(keep).to_csv(path, index=False)
        self._write_stage02_inventory()

    def rename_trial_ledger_column(self, old: str, new: str) -> None:
        path = self.stage02_dir / "02_hpo_trial_ledger.csv"
        pd.read_csv(path).rename(columns={old: new}).to_csv(path, index=False)
        self._write_stage02_inventory()

    def set_trial_ledger_baseline_id(self, baseline_id: str) -> None:
        path = self.stage02_dir / "02_hpo_trial_ledger.csv"
        frame = pd.read_csv(path)
        frame["baseline_id"] = baseline_id
        frame.to_csv(path, index=False)
        self._write_stage02_inventory()

    def single_run_dir(self) -> Path:
        run_dirs = [path for path in self.output_dir.iterdir() if path.is_dir()]
        assert len(run_dirs) == 1, f"expected one run folder, got {len(run_dirs)}"
        return run_dirs[0]

    def read_output(self, name: str) -> str:
        return (self.single_run_dir() / name).read_text(encoding="utf-8")


@pytest.fixture()
def stage_dirs(tmp_path: Path) -> Stage04Dirs:
    return Stage04Dirs(tmp_path)


def test_blocks_when_readout_incomplete(stage_dirs: Stage04Dirs) -> None:
    stage_dirs.write_decision_record_override(readout_complete=False)
    with pytest.raises(ValueError, match="readout_complete"):
        run_stage(stage_dirs.config())


def test_blocks_on_run_id_chain_mismatch(stage_dirs: Stage04Dirs) -> None:
    stage_dirs.write_decision_record_override(source_stage02_run_id="wrong_id")
    with pytest.raises(ValueError, match="run id chain"):
        run_stage(stage_dirs.config())


def test_blocks_on_superseded_stage02_run_id(stage_dirs: Stage04Dirs) -> None:
    config = stage_dirs.config()
    config["inputs"]["stage02_run_id"] = SUPERSEDED_STAGE02_RUN_ID
    with pytest.raises(ValueError, match="superseded"):
        run_stage(config)


def test_blocks_on_dump_schema_mismatch(stage_dirs: Stage04Dirs) -> None:
    stage_dirs.corrupt_dump_drop_column("p_up")
    with pytest.raises(ValueError, match="03_validation_predictions"):
        run_stage(stage_dirs.config())


def test_blocks_on_holdout_boundary_row(stage_dirs: Stage04Dirs) -> None:
    stage_dirs.poison_dump_with_boundary_row()
    config = stage_dirs.config()
    config["diagnostics"]["expected_dump_rows"] += 1
    with pytest.raises(ValueError, match="2017-01-25"):
        run_stage(config)


def test_blocks_when_plan_ledger_copies_trial_ledger(stage_dirs: Stage04Dirs) -> None:
    stage_dirs.copy_trial_ledger_over_plan_ledger()
    with pytest.raises(ValueError, match="plan ledger"):
        run_stage(stage_dirs.config())


def test_blocks_on_fold_hash_parity_mismatch(stage_dirs: Stage04Dirs) -> None:
    stage_dirs.corrupt_plan_ledger_hashes()
    with pytest.raises(ValueError, match="same-row comparability"):
        run_stage(stage_dirs.config())


def test_reference_join_requires_exact_row_count(stage_dirs: Stage04Dirs) -> None:
    stage_dirs.drop_reference_trial_rows(keep=2)
    with pytest.raises(ValueError, match="reference rows"):
        run_stage(stage_dirs.config())


def test_reference_schema_gate_fires_before_any_fit(
    stage_dirs: Stage04Dirs, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 2026-06-10 Colab regression: the real stage02 ledger names its delta
    # column delta_macro_f1_vs_baseline; a schema mismatch must fail BEFORE
    # the fit loop burns compute, and never after it.
    stage_dirs.rename_trial_ledger_column("delta_macro_f1_vs_baseline", "delta_renamed")
    def must_not_fit(*args, **kwargs):
        raise AssertionError("control fit ran despite a reference schema mismatch")
    monkeypatch.setattr(stage04, "_fit_control", must_not_fit)
    with pytest.raises(ValueError, match="missing columns"):
        run_stage(stage_dirs.config())


def test_reference_rows_require_stratified_dummy_baseline_id(stage_dirs: Stage04Dirs) -> None:
    stage_dirs.set_trial_ledger_baseline_id("majority_train_prior")
    with pytest.raises(ValueError, match="must be measured against"):
        run_stage(stage_dirs.config())


def test_budget_cap_blocks_oversized_plan(stage_dirs: Stage04Dirs) -> None:
    config = stage_dirs.config()
    config["ablation"]["budget"]["max_ablation_plan_rows"] = 8
    with pytest.raises(ValueError, match="budget"):
        run_stage(config)


def test_happy_path_outputs_manifest_and_report(stage_dirs: Stage04Dirs) -> None:
    pytest.importorskip("lightgbm")
    result = run_stage(stage_dirs.config())
    run_dir = stage_dirs.single_run_dir()
    assert result.run_dir == run_dir
    for name in stage04.REQUIRED_STAGE04_ARTIFACTS:
        assert (run_dir / name).exists(), f"missing required artifact {name}"

    report = json.loads(stage_dirs.read_output("04_diagnostics_report.json"))
    assert report["baseline_reconstruction_status"] == "verified_identical"
    assert report["new_validation_fit_predict_events"] == 0
    assert report["official_validation_scoring_events"] == 0
    assert report["official_validation_rows_read"] == len(stage_dirs.dump)
    assert report["frozen_prediction_dump_read"] is True
    assert report["no_reselection"] is True
    assert report["stage03_decision"] == "met_predeclared_validation_readout_criteria"

    manifest = json.loads(stage_dirs.read_output("run_manifest.json"))
    assert manifest["official_validation_contact"] == "read_frozen_artifacts_only"
    assert manifest["holdout_test_contact"] is False
    assert manifest["new_validation_fit_predict_events"] == 0
    assert manifest["official_validation_rows_read"] == len(stage_dirs.dump)
    for field in ("requested_device", "resolved_device", "cuda_available",
                  "gpu_name_or_null", "device_fallback_reason",
                  "stage04_diagnostics_code_sha256", "config_sha256"):
        assert field in manifest

    plan = pd.read_csv(run_dir / "04_ablation_plan_ledger.csv")
    assert list(plan.columns) == stage04.ABLATION_PLAN_COLUMNS
    assert len(plan) == 4 * N_FOLDS * len(SEEDS)
    trial = pd.read_csv(run_dir / "04_ablation_trial_ledger.csv")
    assert list(trial.columns) == stage04.ABLATION_TRIAL_COLUMNS
    lightgbm_rows = trial.loc[trial["control_id"].eq("last_step_lightgbm_control")]
    assert (lightgbm_rows["fit_status"] == "completed").all()
    assert lightgbm_rows["delta_macro_f1_vs_stratified_dummy_train_prior"].notna().all()
    torch_rows = trial.loc[trial["control_id"].eq("tcn_only")]
    assert (torch_rows["fit_status"] == "failed_dependency_missing").all()

    slices = pd.read_csv(run_dir / "04_robustness_slices.csv")
    ticker_rows = slices.loc[slices["slice_axis"].eq("ticker")]
    assert (ticker_rows["delta_source"] == "frozen_stage03_artifact").all()
    seed_rows = slices.loc[slices["slice_axis"].eq("seed")]
    assert (seed_rows["delta_source"] == "reconstructed_realized").all()
    assert seed_rows["bootstrap_delta_lcb"].notna().all()

    calibration = pd.read_csv(run_dir / "04_calibration_summary.csv")
    assert set(calibration["view"]) == {"p_up", "top_label_confidence"}
    assert "seed_mean" in set(calibration["seed"].astype(str))
    assert set(TICKERS) <= set(calibration["ticker"].astype(str))

    curve = pd.read_csv(run_dir / "04_risk_coverage_curve.csv")
    assert list(curve.columns) == diagnostics.RISK_COVERAGE_CURVE_COLUMNS
    selective = pd.read_csv(run_dir / "04_selective_summary.csv")
    assert (selective["e_aurc"] >= -1e-12).all()

    for name in ("04_diagnostics_report.json", "04_ablation_summary.csv"):
        text = (run_dir / name).read_text(encoding="utf-8")
        for phrase in ("final model", "selected by official validation", "chosen threshold"):
            assert phrase not in text

    checkpoint_dirs = list(stage_dirs.checkpoint_root.iterdir())
    assert len(checkpoint_dirs) == 1
    checkpoint = json.loads(
        (checkpoint_dirs[0] / "checkpoint_manifest.json").read_text(encoding="utf-8")
    )
    assert checkpoint["resume_instructions"]["resume_mode"] == "exact_run_checkpoint_only"
    assert checkpoint["resume_instructions"]["latest_parent_scan_allowed"] is False
    assert set(checkpoint["completed_units"]) == set(stage04.CONTROL_PROBE_BY_ID)


def test_reconstruction_mismatch_never_mixes_delta_semantics(stage_dirs: Stage04Dirs) -> None:
    pytest.importorskip("lightgbm")
    stage_dirs.perturb_frozen_baseline()
    run_stage(stage_dirs.config())
    run_dir = stage_dirs.single_run_dir()
    report = json.loads(stage_dirs.read_output("04_diagnostics_report.json"))
    assert report["baseline_reconstruction_status"] == "mismatch_deltas_not_computed"
    slices = pd.read_csv(run_dir / "04_robustness_slices.csv")
    non_ticker = slices.loc[~slices["slice_axis"].eq("ticker")]
    assert non_ticker["delta_macro_f1_vs_stratified_dummy_train_prior"].isna().all()
    assert (non_ticker["delta_source"] == diagnostics.NOT_COMPUTED).all()
    assert non_ticker["loo_sign_flip"].isna().all()
    ticker_rows = slices.loc[slices["slice_axis"].eq("ticker")]
    assert (ticker_rows["delta_source"] == "frozen_stage03_artifact").all()
    assert ticker_rows["delta_macro_f1_vs_stratified_dummy_train_prior"].notna().all()


def test_ablation_never_touches_validation_rows(
    stage_dirs: Stage04Dirs, monkeypatch: pytest.MonkeyPatch
) -> None:
    validation_ids = set(stage_dirs.dump["sample_id"].astype(str))
    real_fit = fitting.fit_and_score_control_trial
    seen: list[str] = []

    def guard(probe_id, profile, x_train, train_meta, x_eval, eval_meta, *args, **kwargs):
        assert not (set(train_meta["sample_id"].astype(str)) & validation_ids)
        assert not (set(eval_meta["sample_id"].astype(str)) & validation_ids)
        seen.append(probe_id)
        return real_fit(probe_id, profile, x_train, train_meta, x_eval, eval_meta, *args, **kwargs)

    monkeypatch.setattr(fitting, "fit_and_score_control_trial", guard)
    run_stage(stage_dirs.config())
    assert len(seen) == 4 * N_FOLDS * len(SEEDS)


def test_resume_skips_completed_controls_and_requires_exact_run_id(
    stage_dirs: Stage04Dirs, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("lightgbm")
    run_stage(stage_dirs.config())
    checkpoint_dir = next(stage_dirs.checkpoint_root.iterdir())
    run_id = checkpoint_dir.name
    manifest_path = checkpoint_dir / "checkpoint_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    completed = ["tcn_only", "dlinear_only"]
    manifest["completed_units"] = completed
    manifest["pending_units"] = ["last_step_mlp", "last_step_lightgbm_control"]
    write_json(manifest_path, manifest)
    partial_path = checkpoint_dir / "04_ablation_trial_ledger_partial.csv"
    partial = pd.read_csv(partial_path)
    partial.loc[partial["control_id"].isin(completed)].to_csv(partial_path, index=False)

    fitted: list[str] = []
    real_fit_control = stage04._fit_control

    def recorder(control_id, *args, **kwargs):
        fitted.append(control_id)
        return real_fit_control(control_id, *args, **kwargs)

    monkeypatch.setattr(stage04, "_fit_control", recorder)
    config = stage_dirs.config()
    config["resume"] = {
        "enabled": True, "run_id": run_id, "checkpoint_dir": str(checkpoint_dir),
    }
    run_stage(config)
    assert set(fitted) == {"last_step_mlp", "last_step_lightgbm_control"}

    config_wrong = stage_dirs.config()
    config_wrong["resume"] = {
        "enabled": True, "run_id": "wrong_id", "checkpoint_dir": str(checkpoint_dir),
    }
    with pytest.raises(ValueError, match="run_id"):
        run_stage(config_wrong)


def test_loo_sign_flip_fires_when_one_ticker_carries_the_delta() -> None:
    # direct domain-module check: AAA carries all signal, BBB is below-dummy
    rows = []
    train_labels = np.array([0, 1] * 50)
    for seed in (101,):
        for index in range(400):
            ticker = "AAA" if index < 200 else "BBB"
            y_true = int(index % 2)
            day = f"2013-01-{(index % 4) + 2:02d}"
            if ticker == "AAA":
                y_pred = y_true  # perfect on AAA
            else:
                y_pred = 1 - y_true  # inverted on BBB: strictly below dummy
            rows.append(
                {
                    "candidate_role": "primary", "candidate_id": "probe", "seed": seed,
                    "sample_id": f"s{index:04d}", "ticker": ticker,
                    "target_timestamp": pd.Timestamp(f"{day} 10:00:00"),
                    "trading_day": day, "y_true": y_true, "y_pred": y_pred,
                    "p_up": 0.5, "correct": y_pred == y_true,
                    "calendar_year": "2013", "calendar_quarter": "2013Q1",
                    "time_of_day_hour": "10", "calendar_month": "2013-01",
                    "activity_tercile": "mid", "scope": "validation_only",
                }
            )
    dump = pd.DataFrame(rows)
    recon = {
        101: metrics.predict_stratified_dummy(train_labels, len(dump), 101)[0]
    }
    frozen_ticker = pd.DataFrame(
        [
            {"candidate_role": "primary", "seed": 101, "ticker": ticker,
             "delta_macro_f1_vs_stratified_dummy_train_prior": 0.0}
            for ticker in ("AAA", "BBB")
        ]
    )
    frame = diagnostics.robustness_frames(
        dump,
        train_labels,
        frozen_ticker,
        recon,
        "verified_identical",
        {"slice_axes": ["ticker"], "loo_sign_flip_axes": ["ticker"]},
        {"iterations": 10, "seed": 1},
    )
    aaa = frame.loc[frame["slice_value"].eq("AAA")].iloc[0]
    assert bool(aaa["loo_sign_flip"]) is True  # removing AAA kills the pooled delta
