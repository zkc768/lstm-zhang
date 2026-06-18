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


def test_minimum_detectable_effect_is_bootstrap_half_width() -> None:
    rng = np.random.default_rng(3)
    days = np.repeat(np.arange(20), 15)
    y_true = rng.integers(0, 2, days.size)
    baseline = rng.integers(0, 2, days.size)
    out = metrics.minimum_detectable_effect(y_true, y_true, baseline, days, n_boot=300, seed=2)
    ci = metrics.block_bootstrap_macro_f1_delta(y_true, y_true, baseline, days, n_boot=300, seed=2)
    # MDE = lower half-width (mean - lcb); reference symmetric = (ucb - lcb)/2.
    assert out["mde"] == pytest.approx(ci["mean"] - ci["lcb"])
    assert out["mde_symmetric"] == pytest.approx((ci["ucb"] - ci["lcb"]) / 2.0)
    assert out["mde"] >= 0.0
    assert out["clears_zero"] is True  # perfect signal vs random baseline
    # Reproducible (seeded bootstrap).
    again = metrics.minimum_detectable_effect(y_true, y_true, baseline, days, n_boot=300, seed=2)
    assert again["mde"] == out["mde"]
    # Fewer than two blocks -> no spread -> MDE collapses to 0.
    one_block = np.zeros(days.size, dtype=int)
    degen = metrics.minimum_detectable_effect(y_true, y_true, baseline, one_block, n_boot=50, seed=2)
    assert degen["mde"] == pytest.approx(0.0)
    assert degen["n_blocks"] == 1


def test_same_row_delta_sentinels_collapse_under_shuffle() -> None:
    rng = np.random.default_rng(5)
    days = np.repeat(np.arange(12), 10)
    y_true = rng.integers(0, 2, days.size)
    y_pred = y_true.copy()                     # perfect row-level signal
    baseline = rng.integers(0, 2, days.size)   # random baseline
    out = metrics.same_row_delta_sentinels(y_true, y_pred, baseline, days, n_perm=200, seed=7)
    assert out["observed_delta"] > 0.3
    # Within-block label shuffle destroys the row-level match -> null collapses.
    assert out["label_shuffle_mean"] < out["observed_delta"] - 0.25
    assert out["label_shuffle_p_value"] <= 0.02       # observed exceeds the null band
    # Time-reversing predictions also breaks the perfect alignment.
    assert out["time_reverse_delta"] < out["observed_delta"]
    assert out["n_blocks"] == 12 and out["n_perm"] == 200


def test_same_row_delta_sentinels_zero_when_model_equals_baseline() -> None:
    rng = np.random.default_rng(6)
    days = np.repeat(np.arange(8), 8)
    y_true = rng.integers(0, 2, days.size)
    preds = rng.integers(0, 2, days.size)
    out = metrics.same_row_delta_sentinels(y_true, preds, preds, days, n_perm=50, seed=1)
    # model == baseline -> delta is identically 0 under every permutation.
    assert out["observed_delta"] == pytest.approx(0.0)
    assert out["label_shuffle_mean"] == pytest.approx(0.0)
    again = metrics.same_row_delta_sentinels(y_true, preds, preds, days, n_perm=50, seed=1)
    assert again["label_shuffle_p_value"] == out["label_shuffle_p_value"]  # reproducible


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


def test_reliability_bins_and_ece_equal_width_golden() -> None:
    y_true = np.array([1, 0, 1, 1, 0, 0, 1, 0])
    p_up = np.array([0.9, 0.8, 0.7, 0.65, 0.3, 0.2, 0.25, 0.1])
    bins = metrics.reliability_bins(y_true, p_up, n_bins=2, scheme="equal_width")
    # bin [0,0.5): p={0.3,0.2,0.25,0.1} -> mean_p=0.2125, freq=1/4
    # bin [0.5,1]: p={0.9,0.8,0.7,0.65} -> mean_p=0.7625, freq=3/4
    assert bins["n_rows"].tolist() == [4, 4]
    assert bins["mean_predicted"].tolist() == pytest.approx([0.2125, 0.7625])
    assert bins["empirical_frequency"].tolist() == pytest.approx([0.25, 0.75])
    assert bins["abs_gap"].tolist() == pytest.approx([0.0375, 0.0125])
    ece = metrics.expected_calibration_error(bins)
    assert ece == pytest.approx(0.5 * 0.0375 + 0.5 * 0.0125)
    assert metrics.maximum_calibration_error(bins) == pytest.approx(0.0375)


def test_reliability_bins_equal_mass_drops_empty_and_keeps_total() -> None:
    y_true = np.array([0, 1, 0, 1, 1, 0, 1, 1])
    p_up = np.array([0.05, 0.05, 0.05, 0.55, 0.55, 0.6, 0.9, 0.95])
    bins = metrics.reliability_bins(y_true, p_up, n_bins=4, scheme="equal_mass")
    assert int(bins["n_rows"].sum()) == len(p_up)
    assert (bins["n_rows"] > 0).all()
    assert (bins["bin_lower"] <= bins["bin_upper"]).all()


def test_brier_decomposition_identity_golden() -> None:
    y_true = np.array([1, 0, 1, 0])
    p_up = np.array([0.8, 0.8, 0.4, 0.4])
    out = metrics.brier_score_decomposition(y_true, p_up, n_bins=2, scheme="equal_mass")
    assert out["brier_score"] == pytest.approx(float(np.mean((p_up - y_true) ** 2)))
    recomposed = out["brier_reliability"] - out["brier_resolution"] + out["brier_uncertainty"]
    # exact identity because forecasts are constant within each bin
    assert recomposed == pytest.approx(out["brier_score"], abs=1e-12)
    assert out["brier_uncertainty"] == pytest.approx(0.25)


def test_top_label_confidence_and_prediction_convention() -> None:
    p_up = np.array([0.9, 0.4, 0.5])
    confidence = metrics.top_label_confidence(p_up)
    assert confidence.tolist() == pytest.approx([0.9, 0.6, 0.5])


def test_risk_coverage_and_aurc_golden() -> None:
    correct = np.array([1, 1, 0, 1], dtype=bool)
    confidence = np.array([0.9, 0.8, 0.7, 0.6])
    curve = metrics.risk_coverage_curve(confidence, correct)
    assert curve["coverage"].tolist() == pytest.approx([0.25, 0.5, 0.75, 1.0])
    assert curve["selective_risk"].tolist() == pytest.approx([0.0, 0.0, 1 / 3, 0.25])
    assert curve["selective_accuracy"].tolist() == pytest.approx([1.0, 1.0, 2 / 3, 0.75])
    assert curve["confidence_at_coverage"].tolist() == pytest.approx([0.9, 0.8, 0.7, 0.6])
    out = metrics.aurc_metrics(confidence, correct)
    assert out["aurc"] == pytest.approx(float(np.mean([0.0, 0.0, 1 / 3, 0.25])))
    # oracle: the single error sorted last -> risks [0, 0, 0, 0.25]
    assert out["oracle_aurc"] == pytest.approx(0.0625)
    assert out["e_aurc"] == pytest.approx(out["aurc"] - 0.0625)
    assert out["full_coverage_risk"] == pytest.approx(0.25)


def test_augrc_golden() -> None:
    # Same canonical example as the AURC golden above.
    correct = np.array([1, 1, 0, 1], dtype=bool)
    confidence = np.array([0.9, 0.8, 0.7, 0.6])
    # generalized risk per prefix = selective_risk * coverage
    #   = [0*0.25, 0*0.5, (1/3)*0.75, 0.25*1.0] = [0, 0, 0.25, 0.25]
    #   = errors_in_prefix / n_total = [0/4, 0/4, 1/4, 1/4]
    # AUGRC = mean = 0.125
    assert metrics.augrc(confidence, correct) == pytest.approx(0.125)
    # Generalized risk <= selective risk pointwise (coverage <= 1) -> AUGRC <= AURC.
    aurc = metrics.aurc_metrics(confidence, correct)["aurc"]
    assert metrics.augrc(confidence, correct) <= aurc + 1e-12


def test_risk_coverage_tie_break_is_deterministic() -> None:
    correct = np.array([1, 0, 1, 0], dtype=bool)
    confidence = np.array([0.7, 0.7, 0.7, 0.7])
    tie_break = np.array(["d", "c", "b", "a"])
    curve_a = metrics.risk_coverage_curve(confidence, correct, tie_break=tie_break)
    curve_b = metrics.risk_coverage_curve(confidence, correct, tie_break=tie_break)
    assert curve_a["selective_risk"].tolist() == curve_b["selective_risk"].tolist()
    # ties resolved by ascending tie_break key: a(0), b(1), c(0), d(1)
    assert curve_a["selective_risk"].tolist() == pytest.approx([1.0, 0.5, 2 / 3, 0.5])
