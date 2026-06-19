from __future__ import annotations

import json
from typing import Any, Mapping

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    matthews_corrcoef,
    roc_auc_score,
)


BINARY_LABELS = (0, 1)


def binary_macro_f1(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Fast binary macro-F1 over labels {0, 1}.

    Matches ``sklearn.metrics.f1_score(average="macro", labels=[0, 1],
    zero_division=0)`` (verified in tests) but avoids sklearn call overhead so it
    can run inside the bootstrap inner loop.
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    f1_total = 0.0
    for label in BINARY_LABELS:
        true_positive = float(np.sum((y_true == label) & (y_pred == label)))
        predicted_positive = float(np.sum(y_pred == label))
        actual_positive = float(np.sum(y_true == label))
        precision = true_positive / predicted_positive if predicted_positive else 0.0
        recall = true_positive / actual_positive if actual_positive else 0.0
        f1_total += (
            2.0 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        )
    return f1_total / len(BINARY_LABELS)


def score_classifier(
    y_true: np.ndarray, y_pred: np.ndarray, y_score: np.ndarray | None = None
) -> dict[str, float]:
    """Threshold-based and threshold-free classification metrics.

    ``roc_auc`` requires ``y_score`` (positive-class score) and both classes
    present in ``y_true``; otherwise it is ``nan``.
    """
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    if len(y_true) == 0:
        return {
            "macro_f1": float("nan"),
            "balanced_accuracy": float("nan"),
            "accuracy": float("nan"),
            "mcc": float("nan"),
            "roc_auc": float("nan"),
        }
    both_classes = len(np.unique(y_true)) == 2
    roc_auc = float("nan")
    if y_score is not None and both_classes:
        roc_auc = float(roc_auc_score(y_true, np.asarray(y_score, dtype=float)))
    return {
        "macro_f1": float(f1_score(y_true, y_pred, labels=[0, 1], average="macro", zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "mcc": float(matthews_corrcoef(y_true, y_pred)) if both_classes else float("nan"),
        "roc_auc": roc_auc,
    }


def per_class_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Per-class precision/recall/F1/support over fixed labels {0, 1}."""
    from sklearn.metrics import precision_recall_fscore_support

    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=list(BINARY_LABELS), zero_division=0
    )
    return {
        "precision_down": float(precision[0]),
        "recall_down": float(recall[0]),
        "f1_down": float(f1[0]),
        "support_down": int(support[0]),
        "precision_up": float(precision[1]),
        "recall_up": float(recall[1]),
        "f1_up": float(f1[1]),
        "support_up": int(support[1]),
    }


def predict_stratified_dummy(
    y_train: np.ndarray, n_eval: int, seed: int
) -> tuple[np.ndarray, np.ndarray]:
    """Sample predictions from the empirical train label prior.

    Returns ``(predictions, scores)`` where ``scores`` is the constant
    train-prior probability of the positive class (so baseline ROC-AUC ~ 0.5).
    """
    classes, counts = np.unique(np.asarray(y_train, dtype=int), return_counts=True)
    probabilities = counts / counts.sum()
    rng = np.random.default_rng(seed)
    predictions = rng.choice(classes, size=n_eval, p=probabilities).astype(int)
    positive_prior = float(probabilities[classes == 1][0]) if (classes == 1).any() else 0.0
    scores = np.full(n_eval, positive_prior, dtype=float)
    return predictions, scores


def predict_majority(y_train: np.ndarray, n_eval: int) -> tuple[np.ndarray, np.ndarray]:
    """Always predict the most frequent train label. Constant positive-class score."""
    classes, counts = np.unique(np.asarray(y_train, dtype=int), return_counts=True)
    majority_class = int(classes[int(np.argmax(counts))])
    predictions = np.full(n_eval, majority_class, dtype=int)
    positive_prior = float(counts[classes == 1][0] / counts.sum()) if (classes == 1).any() else 0.0
    scores = np.full(n_eval, positive_prior, dtype=float)
    return predictions, scores


def block_bootstrap_macro_f1_delta(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    baseline_pred: np.ndarray,
    block_ids: np.ndarray,
    *,
    n_boot: int = 1000,
    seed: int = 12345,
) -> dict[str, float]:
    """Block (trading-day) bootstrap CI for macro-F1(model) - macro-F1(baseline).

    Resampling whole trading days (blocks) respects intraday autocorrelation
    instead of assuming i.i.d. rows. This is the honest uncertainty estimate for
    a single model family; do NOT pool heterogeneous model families into one CI.
    """
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    baseline_pred = np.asarray(baseline_pred, dtype=int)
    block_ids = np.asarray(block_ids)
    unique_blocks = np.unique(block_ids)
    point = binary_macro_f1(y_true, y_pred) - binary_macro_f1(y_true, baseline_pred)
    if len(unique_blocks) < 2 or len(y_true) == 0:
        return {"mean": point, "lcb": point, "ucb": point, "point": point, "n_blocks": int(len(unique_blocks))}

    index_by_block = {block: np.flatnonzero(block_ids == block) for block in unique_blocks}
    rng = np.random.default_rng(seed)
    deltas = np.empty(n_boot, dtype=float)
    for draw in range(n_boot):
        chosen = rng.choice(unique_blocks, size=len(unique_blocks), replace=True)
        resampled = np.concatenate([index_by_block[block] for block in chosen])
        deltas[draw] = binary_macro_f1(y_true[resampled], y_pred[resampled]) - binary_macro_f1(
            y_true[resampled], baseline_pred[resampled]
        )
    return {
        "mean": float(deltas.mean()),
        "lcb": float(np.percentile(deltas, 2.5)),
        "ucb": float(np.percentile(deltas, 97.5)),
        "point": float(point),
        "n_blocks": int(len(unique_blocks)),
    }


def minimum_detectable_effect(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    baseline_pred: np.ndarray,
    block_ids: np.ndarray,
    *,
    n_boot: int = 1000,
    seed: int = 12345,
) -> dict[str, float]:
    """Smallest macro-F1 delta the trading-day block bootstrap distinguishes
    from zero -- the noise floor of the same-row delta estimate.

    Reuses :func:`block_bootstrap_macro_f1_delta`. ``mde`` is the LOWER
    half-width of the 95% block-bootstrap CI (``mean - lcb``): holding the
    block-resampling noise structure fixed, an observed pooled delta must be at
    least this large for its one-sided lower bound to clear zero, so a reported
    delta below the MDE is within bootstrap noise. ``mde_symmetric`` is the
    two-sided half-width ``(ucb - lcb) / 2`` for reference. With fewer than two
    blocks there is no spread and the MDE is 0. Descriptive only -- NOT a
    significance test (cf. F8: the project makes no "statistically significant"
    claim and uses sign/LCB signals, not p-values).
    """
    ci = block_bootstrap_macro_f1_delta(
        y_true, y_pred, baseline_pred, block_ids, n_boot=n_boot, seed=seed
    )
    return {
        "mde": float(ci["mean"] - ci["lcb"]),
        "mde_symmetric": float((ci["ucb"] - ci["lcb"]) / 2.0),
        "point_delta": float(ci["point"]),
        "lcb": float(ci["lcb"]),
        "ucb": float(ci["ucb"]),
        "n_blocks": int(ci["n_blocks"]),
        "clears_zero": bool(ci["lcb"] > 0.0),
    }


def same_row_delta_sentinels(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    baseline_pred: np.ndarray,
    block_ids: np.ndarray,
    *,
    n_perm: int = 200,
    seed: int = 20260617,
) -> dict[str, float]:
    """Negative-control sentinels for the same-row macro-F1 delta (model minus
    baseline) -- a verification complement to the leakage hunt (register F11).

    * label-shuffle: permute ``y_true`` WITHIN each block over ``n_perm`` draws
      and recompute the delta. Permutation preserves per-block class marginals
      but destroys the row-level label/prediction correspondence, so a genuine
      row-level edge collapses toward the permutation null while a marginal-only
      artifact does not. Reports the null mean / sd / p95 and the permutation
      p-value (add-one-smoothed share of permuted deltas >= observed).
    * time-reverse: reverse ``y_pred`` WITHIN each block (each prediction matched
      to a different bar's label) and recompute the delta; a genuine edge drops.

    Measure-only: no fit, no operating point. The permutation p-value is a
    descriptive negative-control statistic, NOT a headline significance test
    (cf. F8 -- no 'statistically significant' claim is built on it). Assumes
    ``n_perm >= 1``.
    """
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    baseline_pred = np.asarray(baseline_pred, dtype=int)
    block_ids = np.asarray(block_ids)
    observed = float(
        binary_macro_f1(y_true, y_pred) - binary_macro_f1(y_true, baseline_pred)
    )
    unique_blocks = np.unique(block_ids)
    if len(y_true) == 0:
        nan = float("nan")
        return {
            "observed_delta": nan, "label_shuffle_mean": nan,
            "label_shuffle_sd": nan, "label_shuffle_p95": nan,
            "label_shuffle_p_value": nan, "time_reverse_delta": nan,
            "n_blocks": 0, "n_perm": int(n_perm),
        }
    index_by_block = [np.flatnonzero(block_ids == block) for block in unique_blocks]
    rng = np.random.default_rng(seed)
    perm_deltas = np.empty(int(n_perm), dtype=float)
    for draw in range(int(n_perm)):
        perm_y = y_true.copy()
        for idx in index_by_block:
            perm_y[idx] = rng.permutation(y_true[idx])
        perm_deltas[draw] = (
            binary_macro_f1(perm_y, y_pred) - binary_macro_f1(perm_y, baseline_pred)
        )
    rev_pred = y_pred.copy()
    for idx in index_by_block:
        rev_pred[idx] = y_pred[idx][::-1]
    time_reverse_delta = float(
        binary_macro_f1(y_true, rev_pred) - binary_macro_f1(y_true, baseline_pred)
    )
    exceed = int(np.sum(perm_deltas >= observed))
    return {
        "observed_delta": observed,
        "label_shuffle_mean": float(perm_deltas.mean()),
        "label_shuffle_sd": float(perm_deltas.std(ddof=1)) if int(n_perm) > 1 else 0.0,
        "label_shuffle_p95": float(np.percentile(perm_deltas, 95)),
        "label_shuffle_p_value": float((1 + exceed) / (int(n_perm) + 1)),
        "time_reverse_delta": time_reverse_delta,
        "n_blocks": int(len(unique_blocks)),
        "n_perm": int(n_perm),
    }


def compute_metric_lcb(values: np.ndarray) -> float:
    """Small-sample one-sided 97.5% (lower endpoint of the two-sided 95%
    Student-t interval) lower confidence bound (Student t).

    For scalar per-fold/seed summaries only. With one observation there is no
    spread, so the point value is returned.
    """
    current = np.asarray([float(value) for value in values if value == value], dtype=float)
    if current.size == 0:
        return float("nan")
    if current.size == 1:
        return float(current[0])
    from scipy.stats import t as student_t

    standard_error = current.std(ddof=1) / np.sqrt(current.size)
    quantile = float(student_t.ppf(0.975, df=current.size - 1))
    return float(current.mean() - quantile * standard_error)


def aggregate_family_delta_cis(
    family_cis: Mapping[str, Mapping[str, float]],
) -> dict[str, float]:
    """Aggregate per-family bootstrap CIs into conservative selection statistics.

    ``min_family_lcb`` is the worst implemented family's lower bound: a candidate
    is only credible if even its weakest family clears the baseline. This is the
    multiple-comparison-aware replacement for a single pooled LCB.
    """
    if not family_cis:
        return {
            "min_family_lcb": float("nan"),
            "median_family_lcb": float("nan"),
            "max_family_mean": float("nan"),
        }
    lcbs = [float(ci["lcb"]) for ci in family_cis.values()]
    means = [float(ci["mean"]) for ci in family_cis.values()]
    return {
        "min_family_lcb": float(np.min(lcbs)),
        "median_family_lcb": float(np.median(lcbs)),
        "max_family_mean": float(np.max(means)),
    }


def cscv_pbo(
    performance_matrix: np.ndarray,
    *,
    is_block_count: int | None = None,
) -> dict[str, float]:
    """Descriptive Probability of Backtest Overfitting via Combinatorially-
    Symmetric Cross-Validation (Bailey, Borwein, Lopez de Prado & Zhu 2017).

    ``performance_matrix`` is ``(n_trials, n_blocks)`` with higher = better
    (here: per-(family, period) macro-F1 deltas, families as trials, periods as
    blocks). For every way of choosing ``is_block_count`` blocks as in-sample
    (default ``n_blocks // 2``; the rest are out-of-sample), the in-sample-best
    trial's OUT-of-sample relative rank ``omega in (0,1)`` gives a logit
    ``lambda = ln(omega/(1-omega))``; PBO is the share of combinations with
    ``lambda < 0`` (the IS winner lands below the OS median). The OS rank uses
    AVERAGE ranks, so tied performance is neutral (``omega = 0.5``, ``lambda =
    0``) rather than order-biased -- an all-equal roster returns ``pbo = 0``, not
    a spurious 1. With an odd block count the split is floor/ceil
    (``is_symmetric=False``) rather than canonical symmetric CSCV -- recorded in
    ``is_block_count`` / ``os_block_count`` / ``is_symmetric``.

    DESCRIPTIVE ONLY: an overfitting discount, never a significance test. With a
    small trial/block roster the estimate is coarse (report ``n_trials`` /
    ``n_blocks`` / ``n_combinations`` alongside it). NaN when fewer than 2 trials
    or 2 blocks.
    """
    from itertools import combinations

    from scipy.stats import rankdata

    matrix = np.asarray(performance_matrix, dtype=float)
    if matrix.ndim != 2:
        raise ValueError(f"performance_matrix must be 2-D, got shape {matrix.shape}")
    n_trials, n_blocks = matrix.shape
    nan_result = {
        "pbo": float("nan"), "n_combinations": 0, "n_trials": int(n_trials),
        "n_blocks": int(n_blocks), "is_block_count": 0, "os_block_count": 0,
        "is_symmetric": False, "median_logit": float("nan"),
    }
    if n_trials < 2 or n_blocks < 2 or not np.isfinite(matrix).all():
        return nan_result
    k = n_blocks // 2 if is_block_count is None else int(is_block_count)
    k = max(1, min(k, n_blocks - 1))
    logits: list[float] = []
    below = 0
    for is_blocks in combinations(range(n_blocks), k):
        is_set = set(is_blocks)
        os_blocks = [b for b in range(n_blocks) if b not in is_set]
        is_perf = matrix[:, list(is_blocks)].mean(axis=1)
        os_perf = matrix[:, os_blocks].mean(axis=1)
        best_is = int(np.argmax(is_perf))
        # average ranks -> ties are neutral, not order-biased; 1 (worst) .. n (best)
        os_rank = float(rankdata(os_perf, method="average")[best_is])
        omega = min(max(os_rank / (n_trials + 1), 1e-12), 1.0 - 1e-12)
        lam = float(np.log(omega / (1.0 - omega)))
        logits.append(lam)
        if lam < 0.0:
            below += 1
    n_comb = len(logits)
    return {
        "pbo": float(below / n_comb),
        "n_combinations": int(n_comb),
        "n_trials": int(n_trials),
        "n_blocks": int(n_blocks),
        "is_block_count": int(k),
        "os_block_count": int(n_blocks - k),
        "is_symmetric": bool(n_blocks % 2 == 0 and k == n_blocks - k),
        "median_logit": float(np.median(logits)),
    }


def classification_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    accuracy = float((y_true == y_pred).mean()) if len(y_true) else np.nan
    return {
        "macro_f1": float(
            f1_score(y_true, y_pred, labels=[0, 1], average="macro", zero_division=0)
        )
        if len(y_true)
        else np.nan,
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred))
        if len(y_true)
        else np.nan,
        "accuracy": accuracy,
    }


def score_train_prior_baseline(
    baseline_id: str, y_train: np.ndarray, y_eval: np.ndarray, seed: int
) -> dict[str, Any]:
    if len(y_train) == 0 or len(y_eval) == 0:
        predictions = np.zeros(len(y_eval), dtype=int)
        return {
            "fit_status": "skipped_no_fold_samples",
            "macro_f1": np.nan,
            "balanced_accuracy": np.nan,
            "accuracy": np.nan,
            "roc_auc": np.nan,
            "mcc": np.nan,
            "predictions": predictions,
            "scores": np.full(len(y_eval), 0.5),
            "error_message": "baseline has no train/eval samples for this fold",
        }
    if baseline_id == "stratified_dummy_train_prior":
        predictions, prediction_scores = predict_stratified_dummy(y_train, len(y_eval), seed)
    elif baseline_id == "majority_train_prior":
        predictions, prediction_scores = predict_majority(y_train, len(y_eval))
    else:
        raise ValueError(f"unknown Stage 01 mandatory baseline: {baseline_id}")
    scored = score_classifier(y_eval.astype(int), predictions, y_score=prediction_scores)
    return {
        "fit_status": "completed_baseline",
        "predictions": predictions,
        "scores": prediction_scores,
        "error_message": "",
        **scored,
    }


def score_registry_baseline(
    baseline_id: str, y_train: np.ndarray, y_eval: np.ndarray, seed: int
) -> dict[str, Any]:
    """Score one Stage 00 registry baseline on shared evaluation rows.

    Train-prior baselines delegate to :func:`score_train_prior_baseline` (the
    stratified dummy is seeded with the trial seed); ``constant_up`` and
    ``constant_down`` learn nothing. Moved verbatim from the Stage 02 runner so
    Stage 02 HPO trials and the Stage 03 frozen readout score the identical
    baseline registry.
    """
    if baseline_id in {"stratified_dummy_train_prior", "majority_train_prior"}:
        return score_train_prior_baseline(baseline_id, y_train, y_eval, seed)
    if len(y_train) == 0 or len(y_eval) == 0:
        predictions = np.zeros(len(y_eval), dtype=int)
        return {
            "fit_status": "skipped_no_fold_samples",
            "predictions": predictions,
            "scores": np.full(len(y_eval), 0.5, dtype=float),
            "error_message": "baseline has no train/eval samples for this fold",
            "macro_f1": np.nan,
            "balanced_accuracy": np.nan,
            "accuracy": np.nan,
            "roc_auc": np.nan,
            "mcc": np.nan,
        }
    if baseline_id == "constant_up":
        predictions = np.ones(len(y_eval), dtype=int)
        scores = np.ones(len(y_eval), dtype=float)
    elif baseline_id == "constant_down":
        predictions = np.zeros(len(y_eval), dtype=int)
        scores = np.zeros(len(y_eval), dtype=float)
    else:
        raise ValueError(f"unknown Stage 02 baseline control: {baseline_id}")
    scored = score_classifier(y_eval.astype(int), predictions, y_score=scores)
    return {
        "fit_status": "completed_baseline",
        "predictions": predictions,
        "scores": scores,
        "error_message": "",
        **scored,
    }


def ticker_delta_macro_f1(
    eval_meta: pd.DataFrame, predictions: np.ndarray, baseline_predictions: np.ndarray
) -> tuple[dict[str, float], int]:
    y_eval = eval_meta["label"].to_numpy(dtype=int)
    deltas: dict[str, float] = {}
    for ticker, group in eval_meta.assign(_position=np.arange(len(eval_meta))).groupby("ticker", sort=True):
        positions = group["_position"].to_numpy(dtype=int)
        model_score = classification_metrics(y_eval[positions], predictions[positions])["macro_f1"]
        baseline_score = classification_metrics(
            y_eval[positions], baseline_predictions[positions]
        )["macro_f1"]
        deltas[str(ticker)] = float(model_score - baseline_score)
    positive = sum(1 for value in deltas.values() if value > 0)
    return deltas, positive


def block_delta_macro_f1(
    eval_meta: pd.DataFrame, predictions: np.ndarray, baseline_predictions: np.ndarray
) -> dict[str, float]:
    y_eval = eval_meta["label"].to_numpy(dtype=int)
    deltas: dict[str, float] = {}
    indexed = eval_meta.assign(_position=np.arange(len(eval_meta)))
    for (ticker, trading_day), group in indexed.groupby(["ticker", "trading_day"], sort=True):
        positions = group["_position"].to_numpy(dtype=int)
        model_score = classification_metrics(y_eval[positions], predictions[positions])["macro_f1"]
        baseline_score = classification_metrics(
            y_eval[positions], baseline_predictions[positions]
        )["macro_f1"]
        deltas[f"{ticker}|{trading_day}"] = float(model_score - baseline_score)
    return deltas


def block_bootstrap_lcb(encoded_rows: list[str], *, iterations: int = 1000) -> float:
    buckets: dict[str, list[float]] = {}
    for encoded in encoded_rows:
        if not encoded or encoded == "{}":
            continue
        decoded = json.loads(encoded)
        for block_id, value in decoded.items():
            buckets.setdefault(str(block_id), []).append(float(value))
    block_means = np.array([np.mean(values) for values in buckets.values()], dtype=float)
    block_means = block_means[np.isfinite(block_means)]
    if len(block_means) == 0:
        return np.nan
    if len(block_means) == 1:
        return float(block_means[0])
    rng = np.random.default_rng(20260608)
    draws = rng.choice(block_means, size=(iterations, len(block_means)), replace=True)
    return float(np.quantile(draws.mean(axis=1), 0.025))


CALIBRATION_BIN_SCHEMES = ("equal_width", "equal_mass")


def reliability_bins(
    y_true: np.ndarray, p_up: np.ndarray, *, n_bins: int, scheme: str
) -> pd.DataFrame:
    """Reliability-diagram bins for binary probabilities (measure-only).

    Empty bins are dropped; surviving rows keep their original ``bin_index``
    so gaps stay visible. ``scheme="equal_mass"`` uses quantile edges with
    duplicate-edge dedupe, so the effective bin count can be smaller.
    """
    if scheme not in CALIBRATION_BIN_SCHEMES:
        raise ValueError(f"unknown binning scheme {scheme!r}; expected {CALIBRATION_BIN_SCHEMES}")
    if n_bins < 1:
        raise ValueError(f"n_bins must be >= 1, got {n_bins}")
    y_true = np.asarray(y_true, dtype=int)
    p_up = np.asarray(p_up, dtype=float)
    if len(y_true) != len(p_up) or len(p_up) == 0:
        raise ValueError("y_true and p_up must be equal-length and non-empty")
    if scheme == "equal_width":
        edges = np.linspace(0.0, 1.0, n_bins + 1)
    else:
        edges = np.unique(np.quantile(p_up, np.linspace(0.0, 1.0, n_bins + 1)))
        if len(edges) < 2:
            edges = np.array([float(edges[0]), float(edges[0])])
    assignments = np.clip(np.searchsorted(edges, p_up, side="right") - 1, 0, len(edges) - 2)
    rows = []
    for bin_index in range(len(edges) - 1):
        mask = assignments == bin_index
        if not mask.any():
            continue
        rows.append(
            {
                "bin_index": int(bin_index),
                "bin_lower": float(edges[bin_index]),
                "bin_upper": float(edges[bin_index + 1]),
                "n_rows": int(mask.sum()),
                "mean_predicted": float(p_up[mask].mean()),
                "empirical_frequency": float(y_true[mask].mean()),
            }
        )
    bins = pd.DataFrame(rows)
    bins["abs_gap"] = (bins["empirical_frequency"] - bins["mean_predicted"]).abs()
    return bins


def expected_calibration_error(bins: pd.DataFrame) -> float:
    """Binned ECE: sum over bins of (n_b/N) * |freq_b - mean_pred_b|."""
    total = float(bins["n_rows"].sum())
    return float((bins["n_rows"] / total * bins["abs_gap"]).sum())


def maximum_calibration_error(bins: pd.DataFrame) -> float:
    return float(bins["abs_gap"].max())


def brier_score_decomposition(
    y_true: np.ndarray, p_up: np.ndarray, *, n_bins: int, scheme: str
) -> dict[str, float]:
    """Brier score plus the Murphy (1973) binned decomposition.

    ``brier_score`` is computed from the raw probabilities. The
    reliability/resolution/uncertainty terms are binned statistics; the
    identity ``brier = reliability - resolution + uncertainty`` is exact only
    when forecasts are constant within each bin (otherwise a within-bin
    variance remainder exists). All values are descriptive measurements.
    """
    y_true = np.asarray(y_true, dtype=int)
    p_up = np.asarray(p_up, dtype=float)
    bins = reliability_bins(y_true, p_up, n_bins=n_bins, scheme=scheme)
    total = float(bins["n_rows"].sum())
    base_rate = float(y_true.mean())
    weight = bins["n_rows"] / total
    reliability = float((weight * (bins["mean_predicted"] - bins["empirical_frequency"]) ** 2).sum())
    resolution = float((weight * (bins["empirical_frequency"] - base_rate) ** 2).sum())
    uncertainty = float(base_rate * (1.0 - base_rate))
    return {
        "brier_score": float(np.mean((p_up - y_true) ** 2)),
        "brier_reliability": reliability,
        "brier_resolution": resolution,
        "brier_uncertainty": uncertainty,
    }


def top_label_confidence(p_up: np.ndarray) -> np.ndarray:
    """Top-label confidence max(p_up, 1 - p_up); predicted label is p_up >= 0.5."""
    p_up = np.asarray(p_up, dtype=float)
    return np.maximum(p_up, 1.0 - p_up)


def _selective_order(
    confidence: np.ndarray, tie_break: np.ndarray | None
) -> np.ndarray:
    """Deterministic confidence-descending order with an optional tie key."""
    confidence = np.asarray(confidence, dtype=float)
    if tie_break is None:
        return np.argsort(-confidence, kind="stable")
    tie_break = np.asarray(tie_break)
    tie_rank = np.argsort(np.argsort(tie_break, kind="stable"), kind="stable")
    return np.lexsort((tie_rank, -confidence))


def risk_coverage_curve(
    confidence: np.ndarray,
    correct: np.ndarray,
    *,
    tie_break: np.ndarray | None = None,
) -> pd.DataFrame:
    """Full-resolution selective risk-coverage curve (whole curve, no point).

    Rows are sorted by descending confidence (ties broken by ``tie_break``
    ascending, else stable input order); row k reports the prefix of the
    k most-confident rows. Selective risk is 1 - accuracy on covered rows.
    """
    correct = np.asarray(correct, dtype=bool)
    order = _selective_order(confidence, tie_break)
    ordered_correct = correct[order].astype(float)
    ordered_confidence = np.asarray(confidence, dtype=float)[order]
    n_total = len(ordered_correct)
    n_covered = np.arange(1, n_total + 1, dtype=float)
    cumulative_accuracy = np.cumsum(ordered_correct) / n_covered
    return pd.DataFrame(
        {
            "coverage": n_covered / n_total,
            "n_covered": n_covered.astype(int),
            "confidence_at_coverage": ordered_confidence,
            "selective_risk": 1.0 - cumulative_accuracy,
            "selective_accuracy": cumulative_accuracy,
        }
    )


def aurc_metrics(
    confidence: np.ndarray,
    correct: np.ndarray,
    *,
    tie_break: np.ndarray | None = None,
) -> dict[str, float]:
    """AURC, oracle AURC, and excess AURC (Geifman, Uziel & El-Yaniv 2019).

    AURC is the mean selective risk over the full-resolution per-row curve.
    The oracle sorts the same error count last; ``e_aurc = aurc - oracle``.
    """
    curve = risk_coverage_curve(confidence, correct, tie_break=tie_break)
    correct = np.asarray(correct, dtype=bool)
    n_total = len(correct)
    oracle_correct = np.concatenate(
        [np.ones(int(correct.sum())), np.zeros(n_total - int(correct.sum()))]
    )
    n_covered = np.arange(1, n_total + 1, dtype=float)
    oracle_risk = 1.0 - np.cumsum(oracle_correct) / n_covered
    aurc = float(curve["selective_risk"].mean())
    oracle_aurc = float(oracle_risk.mean())
    return {
        "aurc": aurc,
        "oracle_aurc": oracle_aurc,
        "e_aurc": aurc - oracle_aurc,
        "full_coverage_risk": float(curve["selective_risk"].iloc[-1]),
    }


def augrc(
    confidence: np.ndarray,
    correct: np.ndarray,
    *,
    tie_break: np.ndarray | None = None,
) -> float:
    """Area Under the Generalized Risk-Coverage curve (Traub et al. 2024).

    The *generalized* risk at coverage ``c`` is the UNCONDITIONAL error
    contribution ``E[1{accepted} . wrong]`` = (errors among the ``c`` most
    confident) / n_total = ``selective_risk(c) * c`` -- in contrast to AURC's
    selective (conditional) risk ``errors / n_covered``. AUGRC is its mean over
    the full-resolution per-row curve. Lower is better; it is far less dominated
    by the tiny-coverage tail than AURC, the flaw Traub et al. (2024) raise.
    Measure-only: describes the whole curve, marks no operating point.
    """
    curve = risk_coverage_curve(confidence, correct, tie_break=tie_break)
    generalized_risk = (
        curve["selective_risk"].to_numpy() * curve["coverage"].to_numpy()
    )
    return float(generalized_risk.mean())
