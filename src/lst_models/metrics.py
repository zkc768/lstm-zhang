from __future__ import annotations

from typing import Mapping

import numpy as np
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
