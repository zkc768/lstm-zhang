"""Local torch behavior checks for the Stage 04 control builders.

Mirrors the env-gated pattern of ``test_stage01_metrics_and_torch.py``: the
fast GitHub suite stays CPU/torch-free; set ``RUN_STAGE04_TORCH_TESTS=1`` to
run these locally or on a torch-capable runner.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

if os.environ.get("RUN_STAGE04_TORCH_TESTS") != "1":
    pytest.skip(
        "set RUN_STAGE04_TORCH_TESTS=1 to run local torch control behavior checks",
        allow_module_level=True,
    )

try:
    torch = importlib.import_module("torch")
except ImportError:
    pytest.skip("torch is not installed", allow_module_level=True)
except OSError as exc:
    pytest.skip(f"torch import failed: {exc}", allow_module_level=True)

from lst_models import fitting  # noqa: E402
from lst_models.models.last_step_mlp import LastStepMLPTiny  # noqa: E402
from lst_models.models.ms_dlinear_only import MSDLinearOnlyTiny  # noqa: E402


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


def _control_trial_config(probe_id: str, fixed_defaults: dict) -> dict:
    return {
        "lightweight_probes": {probe_id: {"enabled": True, "fixed_defaults": fixed_defaults}},
        "probe_training_defaults": {
            "torch": {
                "epochs": 2,
                "batch_size": 64,
                "learning_rate": 0.001,
                "weight_decay": 0.0001,
                "device": "auto",
                "require_gpu": False,
                "early_stopping": "inner_train_chronological_tail",
                "early_stopping_validation_fraction": 0.2,
                "minimum_early_stopping_train_samples": 16,
                "minimum_early_stopping_validation_samples": 16,
                "early_stopping_patience": 2,
                "early_stopping_min_delta": 0.0,
                "gradient_clip_norm": 1.0,
            }
        },
    }


def _tiny_window_data(seed: int = 3) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    window, features = 5, 3
    x_train = rng.normal(size=(160, window * features)).astype(np.float32)
    y_train = rng.integers(0, 2, 160)
    x_eval = rng.normal(size=(40, window * features)).astype(np.float32)
    return x_train, y_train, x_eval


def test_torch_dispatch_supports_ms_dlinear_only_tiny() -> None:
    x_train, y_train, x_eval = _tiny_window_data()
    config = _control_trial_config(
        "ms_dlinear_only_tiny",
        {"moving_avg_kernels": [3, 5], "dropout": 0.1, "learning_rate": 0.001},
    )
    result = fitting.fit_torch_sequence_probe(
        "ms_dlinear_only_tiny", x_train, y_train, x_eval, config, 101, 5, 3,
        train_meta=_tail_meta(len(x_train)),
    )
    assert len(result.predictions) == len(x_eval)
    assert set(np.unique(result.predictions)) <= {0, 1}


def test_torch_dispatch_supports_last_step_mlp_tiny() -> None:
    x_train, y_train, x_eval = _tiny_window_data()
    config = _control_trial_config(
        "last_step_mlp_tiny", {"hidden_size": 8, "dropout": 0.1, "learning_rate": 0.001}
    )
    result = fitting.fit_torch_sequence_probe(
        "last_step_mlp_tiny", x_train, y_train, x_eval, config, 101, 5, 3,
        train_meta=_tail_meta(len(x_train)),
    )
    assert len(result.predictions) == len(x_eval)


def test_last_step_mlp_ignores_all_bars_except_the_last() -> None:
    model = LastStepMLPTiny(3, {"hidden_size": 8, "dropout": 0.0})
    model.eval()
    base = torch.randn(4, 5, 3)
    perturbed = base.clone()
    perturbed[:, :-1, :] += torch.randn(4, 4, 3) * 100.0  # scramble non-last bars
    with torch.no_grad():
        assert torch.allclose(model(base), model(perturbed))


def test_ms_dlinear_only_has_no_tcn_branch() -> None:
    model = MSDLinearOnlyTiny(20, 3, {"moving_avg_kernels": [3, 5, 9, 15], "dropout": 0.1})
    module_names = {name for name, _ in model.named_modules()}
    assert not any("tcn" in name for name in module_names)
    assert not any("mix" in name for name in module_names)
