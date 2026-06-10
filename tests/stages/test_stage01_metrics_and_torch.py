"""Behavioral checks the fast smoke test cannot cover.

The Stage 01 smoke test disables torch and only inspects source text for the
MS-DLinear fix. These tests actually run torch on CPU to verify (A1) the
multi-scale moving-average decomposition genuinely affects the output and (D3)
torch probes emit positive-class scores for ROC-AUC.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import lst_models.models.ms_dlinear_tcn as ms_dlinear_tcn_module  # noqa: E402
from lst_models.fitting import fit_torch_sequence_probe  # noqa: E402
from lst_models.models.ms_dlinear_tcn import MSDLinearTCNTiny  # noqa: E402

if os.environ.get("RUN_STAGE01_TORCH_TESTS") != "1":
    pytest.skip(
        "set RUN_STAGE01_TORCH_TESTS=1 to run local torch behavior checks",
        allow_module_level=True,
    )

try:
    torch = importlib.import_module("torch")
except ImportError:
    pytest.skip("torch is not installed", allow_module_level=True)
except OSError as exc:
    pytest.skip(f"torch cannot be imported in this runtime: {exc}", allow_module_level=True)


def _windows(n: int, window_size: int, n_features: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.standard_normal((n, window_size, n_features)).astype(np.float32)


def test_msdlinear_tcn_actually_uses_moving_average_decomposition(monkeypatch) -> None:
    """A1 regression: if the moving average were a no-op (the old
    `trend + residual == x` bug), replacing it would not change the output.
    With the fix, trend feeds its own head, so neutralizing the MA must move
    the logits."""
    window_size, n_features = 10, 3
    defaults = {
        "moving_avg_kernels": [3, 5],
        "tcn_channels": [4],
        "tcn_kernel_size": 3,
        "dropout": 0.0,
    }
    model = MSDLinearTCNTiny(window_size, n_features, defaults)
    model.eval()
    x = torch.as_tensor(_windows(8, window_size, n_features, seed=0), dtype=torch.float32)

    with torch.no_grad():
        baseline = model(x)
    monkeypatch.setattr(
        ms_dlinear_tcn_module, "moving_average_same", lambda tensor, kernel: tensor * 0.0
    )
    with torch.no_grad():
        neutralized = model(x)

    assert not torch.allclose(baseline, neutralized), (
        "moving-average decomposition has no effect on output; multi-scale DLinear is a no-op"
    )


def test_torch_probe_emits_unit_interval_scores() -> None:
    """D3: torch probes must return positive-class scores usable for ROC-AUC."""
    window_size, n_features, n_train = 10, 3, 40
    x_train = _windows(n_train, window_size, n_features, seed=1).reshape(n_train, -1)
    x_eval = _windows(12, window_size, n_features, seed=2).reshape(12, -1)
    y_train = np.array([0, 1] * (n_train // 2), dtype=int)
    config = {
        "lightweight_probes": {
            "standard_dlinear_tiny": {"fixed_defaults": {"moving_avg_kernel": 3, "dropout": 0.0}}
        },
        "probe_training_defaults": {
            "torch": {"epochs": 1, "batch_size": 16, "device": "cpu", "require_gpu": False}
        },
    }
    result = fit_torch_sequence_probe(
        "standard_dlinear_tiny", x_train, y_train, x_eval, config, 0, window_size, n_features
    )
    assert result.predictions.shape == (12,)
    assert result.scores.shape == (12,)
    assert float(result.scores.min()) >= 0.0
    assert float(result.scores.max()) <= 1.0
