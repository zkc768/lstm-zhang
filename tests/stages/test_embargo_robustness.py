from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models import robustness as rb  # noqa: E402
from lst_models.artifacts import feature_rebuild_code_sha256  # noqa: E402
from lst_models.features import build_feature_frame  # noqa: E402
from lst_models.splits import build_train_inner_folds  # noqa: E402
from lst_models.stages import embargo_robustness as emb  # noqa: E402
from lst_models.windows import (  # noqa: E402
    build_window_dataset,
    cap_indices,
    fold_indices,
    sample_id_hash,
)


# ---------------------------------------------------------------------------
# domain module: embargo mask, first eval day, shrinkage reading rules
# ---------------------------------------------------------------------------


def test_first_eval_trading_day_reads_eval_start() -> None:
    fold = {"eval_start": "2010-03-01T09:40:00"}
    assert rb.first_eval_trading_day(fold) == "2010-03-01"


def test_embargo_keep_mask_drops_exactly_the_first_day() -> None:
    eval_meta = pd.DataFrame(
        {
            "sample_id": ["a", "b", "c", "d"],
            "trading_day": ["2010-03-01", "2010-03-01", "2010-03-02", "2010-03-03"],
        }
    )
    mask = rb.embargo_keep_mask(eval_meta, "2010-03-01")
    assert mask.tolist() == [False, False, True, True]


def _variant_ledger(margins: dict[tuple[str, int], list[float]]) -> pd.DataFrame:
    rows = []
    for (variant_id, seed), deltas in margins.items():
        for index, delta in enumerate(deltas):
            rows.append(
                {
                    "variant_id": variant_id,
                    "seed": seed,
                    "fold_id": f"fold_{index}",
                    "fit_status": "completed",
                    "delta_macro_f1_vs_baseline": delta,
                    "baseline_macro_f1": 0.5,
                    "n_eval_samples": 100,
                    "positive_ticker_count": 3.0,
                }
            )
    return pd.DataFrame(rows)


def test_embargo_reading_roughly_unchanged_outcome() -> None:
    ledger = _variant_ledger(
        {
            ("no_embargo", 101): [0.010, 0.012, 0.011],
            ("embargo_1day", 101): [0.009, 0.011, 0.010],
            ("no_embargo", 202): [0.008, 0.010, 0.009],
            ("embargo_1day", 202): [0.007, 0.009, 0.008],
        }
    )
    reading = rb.embargo_reading(ledger, seeds=[101, 202], shrinkage_fraction=0.5)
    assert reading["overall_outcome"] == "roughly_unchanged_limitation_bounded_not_removed"
    assert reading["limitation_removed"] is False
    assert reading["per_seed"]["101"]["materially_smaller"] is False
    assert reading["per_seed"]["101"]["retained_margin_fraction"] == pytest.approx(
        0.010 / 0.011, rel=1e-6
    )


def test_embargo_reading_materially_smaller_outcome() -> None:
    ledger = _variant_ledger(
        {
            ("no_embargo", 101): [0.010, 0.012, 0.011],
            ("embargo_1day", 101): [0.001, 0.002, 0.001],
            ("no_embargo", 202): [0.008, 0.010, 0.009],
            ("embargo_1day", 202): [0.000, 0.002, 0.001],
        }
    )
    reading = rb.embargo_reading(ledger, seeds=[101, 202], shrinkage_fraction=0.5)
    assert reading["overall_outcome"] == (
        "materially_smaller_cross_day_dependence_inflation_reported"
    )


def test_embargo_reading_inapplicable_and_mixed_outcomes() -> None:
    inapplicable = _variant_ledger(
        {
            ("no_embargo", 101): [-0.002, -0.001, 0.000],
            ("embargo_1day", 101): [-0.002, -0.001, 0.000],
            ("no_embargo", 202): [0.008, 0.010, 0.009],
            ("embargo_1day", 202): [0.007, 0.009, 0.008],
        }
    )
    reading = rb.embargo_reading(inapplicable, seeds=[101, 202], shrinkage_fraction=0.5)
    assert reading["overall_outcome"] == "baseline_margin_not_positive_rule_inapplicable"

    mixed = _variant_ledger(
        {
            ("no_embargo", 101): [0.010, 0.012, 0.011],
            ("embargo_1day", 101): [0.001, 0.002, 0.001],
            ("no_embargo", 202): [0.008, 0.010, 0.009],
            ("embargo_1day", 202): [0.007, 0.009, 0.008],
        }
    )
    reading = rb.embargo_reading(mixed, seeds=[101, 202], shrinkage_fraction=0.5)
    assert reading["overall_outcome"] == "mixed_across_seeds_inconclusive"


def test_embargo_reading_incomplete_voids_the_reading() -> None:
    ledger = _variant_ledger(
        {
            ("no_embargo", 101): [0.010, 0.012, 0.011],
            ("embargo_1day", 101): [0.009, 0.011, 0.010],
            ("no_embargo", 202): [0.008, 0.010, 0.009],
            ("embargo_1day", 202): [0.007, 0.009, 0.008],
        }
    )
    ledger.loc[0, "fit_status"] = "failed_exception"
    reading = rb.embargo_reading(ledger, seeds=[101, 202], shrinkage_fraction=0.5)
    assert reading["overall_outcome"] == "incomplete_run_fix_and_rerun"


def test_embargo_reading_rejects_bad_shrinkage_fraction() -> None:
    ledger = _variant_ledger({("no_embargo", 101): [0.01], ("embargo_1day", 101): [0.01]})
    with pytest.raises(ValueError, match="shrinkage_fraction"):
        rb.embargo_reading(ledger, seeds=[101], shrinkage_fraction=1.5)


# ---------------------------------------------------------------------------
# run_stage smoke: tiny real fixture + oracle fit (no torch required)
# ---------------------------------------------------------------------------


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _tiny_train_bars(n_days: int = 12, bars_per_day: int = 30) -> pd.DataFrame:
    days = pd.bdate_range("2010-01-04", periods=n_days)
    rng = np.random.default_rng(7)
    rows = []
    for ticker in ("AAA", "BBB"):
        price = 100.0
        for day in days:
            for bar in range(bars_per_day):
                timestamp = day + pd.Timedelta(hours=9, minutes=30) + pd.Timedelta(minutes=5 * bar)
                price *= float(np.exp(rng.normal(0.0, 0.001)))
                rows.append(
                    {
                        "ticker": ticker,
                        "timestamp": timestamp,
                        "open": price,
                        "high": price * 1.001,
                        "low": price * 0.999,
                        "close": price,
                        "volume": 1000.0,
                        "split": "train",
                    }
                )
    bars = pd.DataFrame(rows)
    bars["trading_day"] = bars["timestamp"].dt.strftime("%Y-%m-%d")
    return bars.sort_values(["ticker", "timestamp"]).reset_index(drop=True)


def _write_smoke_inputs(tmp_path: Path, bars: pd.DataFrame) -> None:
    frozen_events, _ = rb.rebuild_cell_events(bars, horizon_k=9, band_bps=3.0)

    stage00 = tmp_path / "stage00"
    stage00.mkdir(exist_ok=True)
    _write_json(stage00 / "run_manifest.json", {"holdout_test_contact": False})
    _write_json(stage00 / "raw_data_manifest.json", {})
    _write_json(
        stage00 / "split_freeze.json",
        {
            "train_start": "1998-01-02",
            "train_end": "2013-09-16",
            "validation_start": "2013-09-16",
            "validation_end": "2017-01-25",
            "closed_holdout_test_start": "2017-01-25",
        },
    )
    _write_json(
        stage00 / "label_policy.json",
        {"operator": "endpoint_cumulative_return", "horizon_k": 9, "no_trade_band_bps": 3.0},
    )
    _write_json(stage00 / "baseline_registry.json", {})
    frozen_events.assign(valid_label=True).to_csv(
        stage00 / "sample_event_index.csv", index=False
    )

    feature_frame = build_feature_frame(bars)
    dataset = build_window_dataset(
        feature_frame, frozen_events, feature_set="toy",
        feature_columns=("log_return",), window_size=2,
    )
    stage01 = tmp_path / "stage01"
    stage01.mkdir()
    _write_json(
        stage01 / "run_manifest.json",
        {
            "holdout_test_contact": False,
            "feature_rebuild_code_sha256": feature_rebuild_code_sha256(),
        },
    )
    _write_json(
        stage01 / "01_candidate_inputs.json",
        {
            "holdout_test_contact": False,
            "no_final_model_selected": True,
            "candidate_inputs": [
                {
                    "candidate_id": "toy_w2",
                    "feature_set": "toy",
                    "feature_columns": ["log_return"],
                    "window_size": 2,
                }
            ],
        },
    )
    pd.DataFrame(
        [
            {
                "candidate_id": "toy_w2",
                "n_samples_total": int(len(dataset.metadata)),
                "n_samples_by_ticker_json": json.dumps(
                    {
                        str(ticker): int(count)
                        for ticker, count in dataset.metadata.groupby("ticker").size().items()
                    }
                ),
            }
        ]
    ).to_csv(stage01 / "01_feature_window_search_summary.csv", index=False)

    folds = build_train_inner_folds(frozen_events, 2)
    plan_rows = []
    for fold in folds.to_dict(orient="records"):
        train_idx, eval_idx = fold_indices(dataset.metadata, fold)
        train_idx = cap_indices(dataset.metadata, train_idx, 0)
        eval_idx = cap_indices(dataset.metadata, eval_idx, 0)
        plan_rows.append(
            {
                "candidate_id": "toy_w2",
                "fold_id": str(fold["fold_id"]),
                "train_sample_id_hash": sample_id_hash(
                    dataset.metadata.iloc[train_idx]["sample_id"].tolist()
                ),
                "eval_sample_id_hash": sample_id_hash(
                    dataset.metadata.iloc[eval_idx]["sample_id"].tolist()
                ),
            }
        )
    stage02 = tmp_path / "stage02"
    stage02.mkdir()
    _write_json(
        stage02 / "run_manifest.json",
        {
            "holdout_test_contact": False,
            "stage02_run_id": "stage02_test",
            "source_stage01_run_id": "stage01_test",
        },
    )
    pd.DataFrame(plan_rows).to_csv(stage02 / "02_hpo_plan_ledger.csv", index=False)


def _smoke_config(tmp_path: Path) -> dict:
    search_space_path = tmp_path / "search_spaces" / "tcn" / "search_space.yaml"
    search_space_path.parent.mkdir(parents=True)
    search_space_path.write_text(
        yaml.safe_dump(
            {
                "model_family": "tcn",
                "search_mode": "bounded_profiles",
                "profiles": [
                    {
                        "profile_id": "tcn_p01",
                        "channels": [4],
                        "kernel_size": 2,
                        "dropout": 0.0,
                        "learning_rate": 0.001,
                        "weight_decay": 0.0,
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    notebook_path = tmp_path / "v2_embargo_robustness_colab.ipynb"
    notebook_path.write_text("{}", encoding="utf-8")
    return {
        "stage_name": "v2_embargo_robustness",
        "route": "lst_models",
        "scope": "validation_only",
        "holdout_test_contact": False,
        "train_domain_only": True,
        "inputs": {
            "stage00_run_id": "stage00_test",
            "stage00_runtime_run_dir": str(tmp_path / "stage00"),
            "required_stage00_artifacts": [
                "raw_data_manifest.json",
                "split_freeze.json",
                "label_policy.json",
                "baseline_registry.json",
                "sample_event_index.csv",
                "run_manifest.json",
            ],
            "raw_data_manifest": str(tmp_path / "raw.yaml"),
            "raw_data_dir": str(tmp_path / "raw"),
            "stage01_run_id": "stage01_test",
            "stage01_runtime_run_dir": str(tmp_path / "stage01"),
            "required_stage01_artifacts": [
                "run_manifest.json",
                "01_candidate_inputs.json",
                "01_feature_window_search_summary.csv",
            ],
            "stage02_run_id": "stage02_test",
            "stage02_runtime_run_dir": str(tmp_path / "stage02"),
            "required_stage02_artifacts": ["run_manifest.json", "02_hpo_plan_ledger.csv"],
            "notebook_path": str(notebook_path),
        },
        "candidate": {"candidate_id": "toy_w2"},
        "model": {
            "family": "tcn",
            "probe_id": "tcn_tiny",
            "hpo_profile_id": "tcn_p01",
            "search_space": str(search_space_path),
        },
        "embargo": {
            "rule_id": "drop_first_eval_trading_day_per_fold",
            "embargo_trading_days": 1,
            "fits_shared_across_variants": True,
            "variants": [
                {"variant_id": "no_embargo", "role": "stage02_baseline_fold_rows"},
                {"variant_id": "embargo_1day", "role": "eval_side_one_trading_day_embargo"},
            ],
        },
        "train_inner": {
            "n_folds": 2,
            "seeds": [101, 202],
            "official_validation_for_selection": False,
            "event_overlap_count_required": 0,
        },
        "sample_policy": {
            "max_train_samples_per_fold": 0,
            "max_eval_samples_per_fold": 0,
            "sample_method": "deterministic_even_stride_by_ticker_label",
        },
        "probe_training_defaults": {
            "torch": {
                "epochs": 1,
                "batch_size": 64,
                "learning_rate": 0.001,
                "weight_decay": 0.0,
                "device": "cpu",
                "require_gpu": False,
                "early_stopping": "none",
            }
        },
        "budget": {"max_planned_fit_rows": 8, "max_readout_rows": 16},
        "reading_rules": {
            "primary_baseline": "stratified_dummy_train_prior",
            "rule_id": "embargoed_margin_shrinkage_vs_no_embargo",
            "shrinkage_fraction": 0.5,
            "applicability": "no_embargo_margin_positive_per_seed",
            "evaluated_per_seed_and_must_agree": True,
        },
        "checkpointing": {"enabled": True, "checkpoint_dir": str(tmp_path / "checkpoints")},
        "outputs": {
            "output_dir": str(tmp_path / "out"),
            "manifest": "run_manifest.json",
            "trial_ledger": "emb_trial_ledger.csv",
            "variant_summary": "emb_variant_summary.csv",
            "fold_manifest": "emb_fold_manifest.csv",
            "dropped_rows": "emb_dropped_rows.csv",
            "baseline_control_summary": "emb_baseline_control_summary.csv",
            "reading_readout": "emb_reading_readout.json",
        },
    }


def _oracle_fit(probe_id, profile, x_train, train_meta, x_eval, config, seed,
                window_size, n_features):
    last_bar = np.asarray(x_eval)[:, -int(n_features):]
    predictions = (last_bar[:, 0] > 0.0).astype(int)
    return {
        "fit_status": "completed",
        "error_message": "",
        "predictions": predictions,
        "scores": np.where(predictions == 1, 0.9, 0.1),
        "best_iteration": 1,
        "early_stopping_source": "disabled",
        "early_stopping_used": False,
        "early_stopping_reason": "test_oracle",
        "early_stopping_train_sample_id_hash": "",
        "early_stopping_eval_sample_id_hash": "",
        "requested_device": "cpu",
        "resolved_device": "cpu",
        "device_fallback_reason": "not_gpu_capable_trial",
    }


def test_run_stage_smoke_with_oracle_fit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bars = _tiny_train_bars()
    _write_smoke_inputs(tmp_path, bars)
    config = _smoke_config(tmp_path)
    monkeypatch.setattr(rb, "load_train_bars", lambda *args, **kwargs: bars)
    monkeypatch.setattr(emb, "fit_stage_control", _oracle_fit)

    result = emb.run_stage(config)

    for path in (
        result.run_manifest, result.artifact_inventory, result.trial_ledger,
        result.variant_summary, result.fold_manifest, result.dropped_rows,
        result.baseline_control_summary, result.reading_readout,
    ):
        assert path.exists(), path

    trial_ledger = pd.read_csv(result.trial_ledger)
    assert len(trial_ledger) == 2 * 2 * 2  # variants x folds x seeds
    assert set(trial_ledger["fit_status"]) == {"completed"}
    assert set(trial_ledger["variant_id"]) == {"no_embargo", "embargo_1day"}

    # Shared-fit contract: both variants of a (fold, seed) share fit_group_id
    # and the identical train rows; embargo rows are a strict subset.
    for fit_group_id, group in trial_ledger.groupby("fit_group_id"):
        assert set(group["variant_id"]) == {"no_embargo", "embargo_1day"}
        assert group["train_sample_id_hash"].nunique() == 1
        base = group.loc[group["variant_id"] == "no_embargo"].iloc[0]
        embargoed = group.loc[group["variant_id"] == "embargo_1day"].iloc[0]
        assert int(embargoed["n_eval_samples"]) == int(base["n_eval_samples"]) - int(
            embargoed["n_embargo_dropped_rows"]
        )
        assert int(embargoed["n_embargo_dropped_rows"]) > 0

    fold_manifest = pd.read_csv(result.fold_manifest)
    dropped = pd.read_csv(result.dropped_rows)
    assert int(fold_manifest["n_embargo_dropped_rows"].sum()) == len(dropped)
    # Every dropped row sits on its fold's first eval trading day.
    merged = dropped.merge(
        fold_manifest[["fold_id", "first_eval_trading_day"]], on="fold_id",
        suffixes=("", "_fold"),
    )
    assert (merged["trading_day"] == merged["first_eval_trading_day"]).all()

    variant_summary = pd.read_csv(result.variant_summary)
    assert len(variant_summary) == 2 * 3  # variants x (2 seeds + seed_mean)
    assert set(variant_summary["seed"].astype(str)) == {"101", "202", "seed_mean"}

    reading = json.loads(result.reading_readout.read_text(encoding="utf-8"))
    assert reading["embargo_rule_id"] == "drop_first_eval_trading_day_per_fold"
    assert reading["limitation_removed"] is False
    assert reading["shrinkage_fraction"] == 0.5
    assert set(reading["per_seed"]) == {"101", "202"}
    assert reading["overall_outcome"] in {
        "materially_smaller_cross_day_dependence_inflation_reported",
        "roughly_unchanged_limitation_bounded_not_removed",
        "baseline_margin_not_positive_rule_inapplicable",
        "mixed_across_seeds_inconclusive",
    }

    manifest = json.loads(result.run_manifest.read_text(encoding="utf-8"))
    assert manifest["train_domain_only"] is True
    assert manifest["holdout_test_contact"] is False
    assert manifest["official_validation_contact"] is False
    assert manifest["fits_shared_across_variants"] is True
    assert manifest["embargo_trading_days"] == 1
    assert manifest["planned_fit_rows"] == 4  # folds x seeds
    assert manifest["planned_readout_rows"] == 8
    assert manifest["evidence_status"] == "train_inner_embargo_robustness_control"
    assert manifest["train_domain_bounds"]["max_target_timestamp"] < "2013-09-16"

    baseline_summary = pd.read_csv(result.baseline_control_summary)
    assert set(baseline_summary["baseline_id"]) == {
        "stratified_dummy_train_prior", "majority_train_prior", "constant_up", "constant_down",
    }
    assert set(baseline_summary["variant_id"]) == {"no_embargo", "embargo_1day"}
    checkpoint_manifest = (
        tmp_path / "checkpoints" / result.output_dir.name / "checkpoint_manifest.json"
    )
    assert checkpoint_manifest.exists()


def test_run_stage_blocks_on_plan_ledger_hash_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bars = _tiny_train_bars()
    _write_smoke_inputs(tmp_path, bars)
    plan_path = tmp_path / "stage02" / "02_hpo_plan_ledger.csv"
    plan = pd.read_csv(plan_path)
    plan.loc[0, "eval_sample_id_hash"] = "0" * 64
    plan.to_csv(plan_path, index=False)
    config = _smoke_config(tmp_path)
    monkeypatch.setattr(rb, "load_train_bars", lambda *args, **kwargs: bars)
    monkeypatch.setattr(emb, "fit_stage_control", _oracle_fit)
    with pytest.raises(ValueError, match="same-row comparability is void"):
        emb.run_stage(config)


def test_validate_config_rejects_unsafe_or_undeclared_settings(tmp_path: Path) -> None:
    config = _smoke_config(tmp_path)
    emb._validate_config(config)

    broken = dict(config)
    broken["embargo"] = {**config["embargo"], "rule_id": "drop_last_train_day"}
    with pytest.raises(ValueError, match="rule_id"):
        emb._validate_config(broken)

    broken = dict(config)
    broken["embargo"] = {**config["embargo"], "embargo_trading_days": 2}
    with pytest.raises(ValueError, match="one-trading-day"):
        emb._validate_config(broken)

    broken = dict(config)
    broken["embargo"] = {**config["embargo"], "fits_shared_across_variants": False}
    with pytest.raises(ValueError, match="fits_shared_across_variants=true"):
        emb._validate_config(broken)

    broken = dict(config)
    broken["reading_rules"] = {**config["reading_rules"], "shrinkage_fraction": 1.5}
    with pytest.raises(ValueError, match="shrinkage_fraction"):
        emb._validate_config(broken)
