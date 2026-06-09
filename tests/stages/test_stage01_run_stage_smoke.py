from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import lst_models.stages.feature_window_search as feature_window_search  # noqa: E402
from lst_models.stages.feature_window_search import run_stage  # noqa: E402


TICKERS = ["AAA", "BBB", "CCC"]
TRAIN_DAYS = [
    "2020-01-02",
    "2020-01-03",
    "2020-01-06",
    "2020-01-07",
    "2020-01-08",
    "2020-01-09",
]


@pytest.fixture(autouse=True)
def disable_torch_import_for_fast_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        feature_window_search,
        "_TORCH_IMPORT_ERROR",
        "torch disabled in fast Stage 01 smoke test",
    )


def write_stage00_artifacts(
    run_dir: Path, raw_dir: Path, *, holdout_contact: bool = False
) -> None:
    run_dir.mkdir(parents=True)
    raw_dir.mkdir(parents=True)
    raw_manifest = {
        "tickers": TICKERS,
        "raw_source": {
            "local_download_dir": str(raw_dir),
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
    split_freeze = {
        "train_start": "2020-01-02 00:00:00",
        "train_end": "2020-01-10 00:00:00",
        "validation_start": "2020-01-10 00:00:00",
        "validation_end": "2020-01-11 00:00:00",
        "closed_holdout_test_start": "2020-01-11 00:00:00",
    }
    (run_dir / "raw_data_manifest.json").write_text(
        json.dumps(raw_manifest), encoding="utf-8"
    )
    (run_dir / "split_freeze.json").write_text(json.dumps(split_freeze), encoding="utf-8")
    (run_dir / "label_policy.json").write_text("{}", encoding="utf-8")
    (run_dir / "baseline_registry.json").write_text("{}", encoding="utf-8")
    (run_dir / "run_manifest.json").write_text(
        json.dumps({"holdout_test_contact": holdout_contact, "config_sha256": "stage00hash"}),
        encoding="utf-8",
    )
    sample_events = _write_raw_txt_files(raw_dir)
    pd.DataFrame(sample_events).to_csv(run_dir / "sample_event_index.csv", index=False)


def _write_raw_txt_files(raw_dir: Path) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for ticker_index, ticker in enumerate(TICKERS):
        rows = []
        price = 100.0 + ticker_index
        for day_index, day in enumerate(TRAIN_DAYS):
            bar_starts = pd.date_range(f"{day} 09:30", periods=72, freq="5min")
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
                        "split": "train",
                        "horizon_k": 1,
                        "horizon_end_timestamp": (
                            bar_start + pd.Timedelta(minutes=5)
                        ).isoformat(),
                        "label": 1 if signal > 0 else 0,
                        "valid_label": True,
                    }
                )
        pd.DataFrame(rows).to_csv(raw_dir / f"{ticker}.txt", index=False)
    return events


def stage01_config(tmp_path: Path, stage00_run_dir: Path, raw_dir: Path) -> dict:
    notebook_path = tmp_path / "01_feature_window_search_colab.ipynb"
    notebook_path.write_text("{}", encoding="utf-8")
    return {
        "stage_name": "01_feature_window_search",
        "route": "lst_models",
        "scope": "validation_only",
        "holdout_test_contact": False,
        "inputs": {
            "stage00_run_id": "stage00_test",
            "stage00_runtime_run_dir": str(stage00_run_dir),
            "stage00_drive_path_parts": ["lst_models", "results", "00", "stage00_test"],
            "stage00_run_manifest": str(stage00_run_dir / "run_manifest.json"),
            "raw_data_manifest": "configs/lst_models_data.yaml",
            "raw_data_dir": str(raw_dir),
            "notebook_path": str(notebook_path),
            "required_stage00_artifacts": [
                "raw_data_manifest.json",
                "split_freeze.json",
                "label_policy.json",
                "baseline_registry.json",
                "sample_event_index.csv",
                "run_manifest.json",
            ],
        },
        "outputs": {
            "output_dir": str(tmp_path / "out"),
            "manifest": "run_manifest.json",
            "artifact_inventory": "artifact_inventory.csv",
            "summary": "01_feature_window_search_summary.csv",
            "candidate_inputs": "01_candidate_inputs.json",
            "probe_ledger": "01_train_inner_probe_ledger.csv",
            "fold_manifest": "01_train_inner_fold_manifest.csv",
        },
        "feature_sets": {"price_action_core": ["log_return"]},
        "window_sizes": [10, 20, 30],
        "train_inner": {
            "n_folds": 2,
            "seeds": [101],
            "event_overlap_count_required": 0,
            "official_validation_for_selection": False,
        },
        "baseline_probes": {
            "mandatory_trivial": [
                "stratified_dummy_train_prior",
                "majority_train_prior",
            ]
        },
        "lightweight_probes": {
            "logreg_flat_control": {
                "enabled": True,
                "fixed_defaults": {
                    "solver": "liblinear",
                    "class_weight": "balanced",
                    "max_iter": 200,
                },
            },
            "lightgbm_small": {
                "enabled": True,
                "fixed_defaults": {
                    "n_estimators": 20,
                    "learning_rate": 0.05,
                    "max_depth": 3,
                    "num_leaves": 7,
                    "subsample": 0.9,
                    "colsample_bytree": 0.9,
                    "class_weight": "balanced",
                },
            },
            "standard_dlinear_tiny": {
                "enabled": True,
                "fixed_defaults": {"moving_avg_kernel": 3, "dropout": 0.0},
            },
            "tcn_tiny": {
                "enabled": True,
                "fixed_defaults": {"channels": [4], "kernel_size": 3, "dropout": 0.0},
            },
            "ms_dlinear_tcn_tiny": {
                "enabled": True,
                "fixed_defaults": {
                    "moving_avg_kernels": [3, 5],
                    "tcn_channels": [4],
                    "tcn_kernel_size": 3,
                    "dropout": 0.0,
                },
            },
        },
        "optional_fixed_controls": {
            "simple_gru": {"enabled": False, "stage02_hpo_family": False},
            "shallow_lstm": {"enabled": False, "stage02_hpo_family": False},
        },
        "probe_training_defaults": {
            "torch": {
                "epochs": 1,
                "batch_size": 128,
                "learning_rate": 0.001,
                "weight_decay": 0.0001,
                "device": "cpu",
                "require_gpu": False,
            }
        },
        "screening_sample_policy": {
            "max_train_samples_per_fold": 400,
            "max_eval_samples_per_fold": 300,
            "sample_method": "deterministic_even_stride_by_ticker_label",
        },
        "budget": {"max_counted_probe_rows": 40},
        "selection_rules": {
            "primary_metric": "macro_f1",
            "baseline": "stratified_dummy_train_prior",
            "require_mean_delta_macro_f1_vs_baseline_positive": True,
            "minimum_positive_ticker_count": 1,
            "max_candidate_inputs_for_stage02": 2,
            "no_final_model_selected": True,
        },
        "stage02_handoff": {
            "recommended_model_families": [
                "lightgbm",
                "standard_dlinear",
                "tcn",
                "ms_dlinear_tcn",
            ],
            "control_models": ["last_step_lightgbm_control"],
        },
    }


def test_stage01_run_stage_writes_real_screening_artifacts(tmp_path: Path) -> None:
    stage00_run_dir = tmp_path / "stage00"
    raw_dir = tmp_path / "raw"
    write_stage00_artifacts(stage00_run_dir, raw_dir)

    result = run_stage(stage01_config(tmp_path, stage00_run_dir, raw_dir))

    assert result.run_manifest.exists()
    assert result.artifact_inventory.exists()
    assert result.summary.exists()
    assert result.candidate_inputs.exists()
    assert result.probe_ledger.exists()
    assert result.fold_manifest.exists()

    manifest = json.loads(result.run_manifest.read_text(encoding="utf-8"))
    assert manifest["holdout_test_contact"] is False
    assert manifest["no_final_model_selected"] is True
    assert manifest["stage01_execution_mode"] == "feature_window_probe_screening_v1"
    assert set(manifest["implemented_probe_ids"]) == {
        "logreg_flat_control",
        "lightgbm_small",
        "standard_dlinear_tiny",
        "tcn_tiny",
        "ms_dlinear_tcn_tiny",
    }

    ledger = pd.read_csv(result.probe_ledger)
    assert {
        "stratified_dummy_train_prior",
        "majority_train_prior",
        "logreg_flat_control",
        "lightgbm_small",
        "standard_dlinear_tiny",
        "tcn_tiny",
        "ms_dlinear_tcn_tiny",
    }.issubset(set(ledger["probe_id"]))
    assert (ledger["probe_id"] == "stratified_dummy_train_prior").any()
    assert (ledger["probe_id"] == "majority_train_prior").any()
    probe_rows = ledger.loc[
        ledger["probe_id"].isin(
            [
                "logreg_flat_control",
                "lightgbm_small",
                "standard_dlinear_tiny",
                "tcn_tiny",
                "ms_dlinear_tcn_tiny",
            ]
        )
    ]
    assert "skipped_not_implemented" not in set(probe_rows["fit_status"])
    assert set(
        probe_rows.loc[
            probe_rows["probe_id"].isin(["logreg_flat_control", "lightgbm_small"]),
            "fit_status",
        ]
    ) == {"completed"}
    torch_statuses = set(
        probe_rows.loc[
            probe_rows["probe_id"].isin(
                ["standard_dlinear_tiny", "tcn_tiny", "ms_dlinear_tcn_tiny"]
            ),
            "fit_status",
        ]
    )
    assert torch_statuses <= {"completed", "failed_dependency_missing"}
    assert probe_rows["baseline_id"].eq("stratified_dummy_train_prior").all()
    assert probe_rows["sample_id_hash"].str.fullmatch(r"[0-9a-f]{64}").all()

    summary = pd.read_csv(result.summary)
    assert set(summary["window_size"]) == {10, 20, 30}
    assert summary["n_samples_total"].gt(0).all()

    candidates = json.loads(result.candidate_inputs.read_text(encoding="utf-8"))
    assert candidates["recommended_model_families_from_protocol"] == [
        "lightgbm",
        "standard_dlinear",
        "tcn",
        "ms_dlinear_tcn",
    ]
    assert candidates["no_final_model_selected"] is True
    assert candidates["holdout_test_contact"] is False

    folds = pd.read_csv(result.fold_manifest)
    assert folds["event_overlap_count"].eq(0).all()
    assert len(folds) == 2


def test_stage01_rejects_official_validation_selection(tmp_path: Path) -> None:
    stage00_run_dir = tmp_path / "stage00"
    raw_dir = tmp_path / "raw"
    write_stage00_artifacts(stage00_run_dir, raw_dir)
    config = stage01_config(tmp_path, stage00_run_dir, raw_dir)
    config["train_inner"]["official_validation_for_selection"] = True

    with pytest.raises(ValueError, match="train-inner"):
        run_stage(config)


def test_stage01_resolves_repo_relative_notebook_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stage00_run_dir = tmp_path / "stage00"
    raw_dir = tmp_path / "raw"
    write_stage00_artifacts(stage00_run_dir, raw_dir)
    config = stage01_config(tmp_path, stage00_run_dir, raw_dir)
    config["inputs"]["notebook_path"] = "notebooks/01_feature_window_search_colab.ipynb"
    monkeypatch.chdir(tmp_path)

    result = run_stage(config)

    manifest = json.loads(result.run_manifest.read_text(encoding="utf-8"))
    assert len(manifest["notebook_sha256"]) == 64


def test_stage01_reports_exact_missing_stage00_artifact(tmp_path: Path) -> None:
    stage00_run_dir = tmp_path / "stage00"
    raw_dir = tmp_path / "raw"
    write_stage00_artifacts(stage00_run_dir, raw_dir)
    (stage00_run_dir / "split_freeze.json").unlink()

    with pytest.raises(FileNotFoundError) as excinfo:
        run_stage(stage01_config(tmp_path, stage00_run_dir, raw_dir))

    assert str(stage00_run_dir / "split_freeze.json") in str(excinfo.value)
