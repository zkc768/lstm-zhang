from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from sklearn.metrics import f1_score


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models import metrics  # noqa: E402


def test_binary_macro_f1_matches_sklearn() -> None:
    rng = np.random.default_rng(0)
    for _ in range(200):
        n = int(rng.integers(2, 60))
        y_true = rng.integers(0, 2, n)
        y_pred = rng.integers(0, 2, n)
        expected = f1_score(y_true, y_pred, labels=[0, 1], average="macro", zero_division=0)
        assert abs(metrics.binary_macro_f1(y_true, y_pred) - expected) < 1e-9


def test_score_classifier_keys_and_roc_auc_guard() -> None:
    y_true = np.array([0, 0, 1, 1])
    y_pred = np.array([0, 1, 0, 1])
    scores = np.array([0.2, 0.4, 0.6, 0.8])
    scored = metrics.score_classifier(y_true, y_pred, y_score=scores)
    assert set(scored) == {"macro_f1", "balanced_accuracy", "accuracy", "mcc", "roc_auc"}
    assert scored["roc_auc"] == scored["roc_auc"]  # not NaN when both classes + scores

    single_class = metrics.score_classifier(np.array([1, 1, 1]), np.array([1, 0, 1]))
    assert single_class["roc_auc"] != single_class["roc_auc"]  # NaN without scores/2 classes


def test_per_class_metrics_matches_sklearn_and_handles_missing_class() -> None:
    y_true = np.array([0, 0, 1, 1, 1])
    y_pred = np.array([0, 1, 1, 1, 0])
    result = metrics.per_class_metrics(y_true, y_pred)
    assert result["precision_down"] == pytest.approx(0.5)
    assert result["recall_down"] == pytest.approx(0.5)
    assert result["f1_down"] == pytest.approx(0.5)
    assert result["precision_up"] == pytest.approx(2.0 / 3.0)
    assert result["recall_up"] == pytest.approx(2.0 / 3.0)
    assert result["support_down"] == 2 and result["support_up"] == 3
    empty = metrics.per_class_metrics(np.array([1, 1]), np.array([1, 1]))
    assert empty["support_down"] == 0 and empty["f1_down"] == 0.0


def test_dummy_predictions_are_reproducible_and_constant() -> None:
    y_train = np.array([0, 0, 0, 1, 1])
    pred_a, score_a = metrics.predict_stratified_dummy(y_train, 50, seed=7)
    pred_b, _ = metrics.predict_stratified_dummy(y_train, 50, seed=7)
    assert np.array_equal(pred_a, pred_b)
    assert np.allclose(score_a, 2 / 5)  # train prior for positive class

    majority_pred, _ = metrics.predict_majority(y_train, 10)
    assert np.array_equal(majority_pred, np.zeros(10, dtype=int))


def test_block_bootstrap_separates_real_signal_from_noise() -> None:
    rng = np.random.default_rng(1)
    days = np.repeat(np.arange(20), 15)
    y_true = rng.integers(0, 2, days.size)
    baseline = rng.integers(0, 2, days.size)

    perfect = metrics.block_bootstrap_macro_f1_delta(y_true, y_true, baseline, days, n_boot=300, seed=2)
    assert perfect["lcb"] > 0.0  # a real signal clears the baseline lower bound

    noise = metrics.block_bootstrap_macro_f1_delta(y_true, baseline, baseline, days, n_boot=300, seed=2)
    assert noise["lcb"] <= 0.0 <= noise["ucb"]  # identical-to-baseline straddles zero


def test_compute_metric_lcb_small_sample() -> None:
    assert metrics.compute_metric_lcb([0.2]) == 0.2
    lcb = metrics.compute_metric_lcb([0.10, 0.12, 0.11])
    assert lcb < float(np.mean([0.10, 0.12, 0.11]))


def test_aggregate_family_delta_cis_is_conservative() -> None:
    family_cis = {
        "lightgbm_small": {"mean": 0.03, "lcb": 0.01, "ucb": 0.05},
        "tcn_tiny": {"mean": 0.02, "lcb": -0.02, "ucb": 0.06},
    }
    aggregate = metrics.aggregate_family_delta_cis(family_cis)
    assert aggregate["min_family_lcb"] == -0.02  # worst family drives selection
    assert aggregate["max_family_mean"] == 0.03
