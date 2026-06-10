"""Stage 04 architectural-control fitting contracts.

Covers the shared `fitting.py` surface the Stage 04 ablation arm relies on:
the last-bar slice contract, the deduplicated LightGBM tail-split fit-kwargs
wiring, and the two new torch control builders dispatched through
`fit_torch_sequence_probe`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models import fitting  # noqa: E402


def test_last_bar_slice_matches_unflattened_window() -> None:
    # synthetic block: window=3, features=2, value encodes 10*t + f
    x_flat = np.array([[t * 10 + f for t in range(3) for f in range(2)]], dtype=np.float32)
    last = fitting.last_bar_slice(x_flat, n_features=2)
    assert last.tolist() == [[20.0, 21.0]]  # t=2 features only


def test_last_bar_slice_agrees_with_materialize_window_matrix_layout() -> None:
    from lst_models.windows import CandidateDataset, materialize_window_matrix

    block = np.arange(8, dtype=np.float32).reshape(4, 2)  # 4 bars x 2 features
    metadata = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "trading_day": ["2013-01-02"],
            "window_start_position": [1],
            "window_end_position_exclusive": [4],
        }
    )
    dataset = CandidateDataset(
        metadata=metadata,
        feature_blocks={("AAA", "2013-01-02"): block},
        feature_columns=("f0", "f1"),
        window_size=3,
    )
    flat = materialize_window_matrix(dataset, np.array([0]))
    assert fitting.last_bar_slice(flat, n_features=2).tolist() == [[6.0, 7.0]]


def test_last_bar_slice_rejects_non_divisible_width() -> None:
    with pytest.raises(ValueError, match="n_features"):
        fitting.last_bar_slice(np.zeros((2, 7), dtype=np.float32), n_features=2)


def _tail_meta(n: int) -> pd.DataFrame:
    timestamps = pd.date_range("2013-01-02 10:00", periods=n, freq="5min")
    return pd.DataFrame(
        {
            "sample_id": [f"s{i:04d}" for i in range(n)],
            "ticker": ["AAA"] * n,
            "trading_day": [str(ts.date()) for ts in timestamps],
            "target_timestamp": timestamps,
        }
    )


def test_lightgbm_tail_split_and_fit_kwargs_wires_tail_only() -> None:
    pytest.importorskip("lightgbm")
    rng = np.random.default_rng(0)
    n = 600
    x_train = rng.normal(size=(n, 4)).astype(np.float32)
    y_train = rng.integers(0, 2, n)
    defaults = {
        "eval_metric": "binary_logloss",
        "early_stopping_rounds": 25,
        "early_stopping_validation_source": "inner_train_chronological_tail",
        "early_stopping_validation_fraction": 0.2,
        "minimum_early_stopping_train_samples": 128,
        "minimum_early_stopping_validation_samples": 128,
    }
    split, fit_kwargs = fitting.lightgbm_tail_split_and_fit_kwargs(
        x_train=x_train, y_train=y_train, train_meta=_tail_meta(n), training_defaults=defaults
    )
    assert split["early_stopping_used"] is True
    assert len(split["x_fit"]) + len(split["x_stop"]) == n
    eval_x, eval_y = fit_kwargs["eval_set"][0]
    assert np.array_equal(eval_x, split["x_stop"])
    assert np.array_equal(eval_y, split["y_stop"])
    assert fit_kwargs["eval_metric"] == "binary_logloss"

    tiny_split, tiny_kwargs = fitting.lightgbm_tail_split_and_fit_kwargs(
        x_train=x_train[:64], y_train=y_train[:64], train_meta=_tail_meta(64),
        training_defaults=defaults,
    )
    assert tiny_split["early_stopping_used"] is False
    assert "eval_set" not in tiny_kwargs


def test_unsupported_torch_probe_id_still_raises() -> None:
    # dispatch extension must not silently accept unknown control ids
    with pytest.raises((ValueError, ModuleNotFoundError)):
        fitting.fit_torch_sequence_probe(
            "unknown_probe",
            np.zeros((4, 6), dtype=np.float32),
            np.array([0, 1, 0, 1]),
            np.zeros((2, 6), dtype=np.float32),
            {"lightweight_probes": {}, "probe_training_defaults": {"torch": {}}},
            101,
            2,
            3,
            train_meta=_tail_meta(4),
        )
