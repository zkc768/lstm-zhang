"""Multi-scale DLinear + TCN tiny classifier.

Combines per-scale trend/residual linear heads with a causal TCN branch.
Trend and residual heads stay separate per scale; their logits are summed per
scale, averaged across scales, then mixed with the TCN logits. Torch is
imported lazily inside the factory so this module stays importable on
machines without torch.
"""

from __future__ import annotations

from typing import Any, Mapping

from lst_models.models.standard_dlinear import moving_average_same, odd_kernel_within_window
from lst_models.models.tcn import TCNTiny


class MSDLinearTCNTiny:
    def __new__(cls, window_size: int, n_features: int, defaults: Mapping[str, Any]) -> Any:
        import torch
        import torch.nn as nn

        kernels = [
            odd_kernel_within_window(int(value), window_size)
            for value in defaults.get("moving_avg_kernels", [3, 5, 9, 15])
            if int(value) <= window_size
        ]
        if not kernels:
            kernels = [3]
        dropout = float(defaults.get("dropout", 0.10))
        tcn_defaults = {
            "channels": defaults.get("tcn_channels", [32, 32]),
            "kernel_size": defaults.get("tcn_kernel_size", 3),
            "dropout": dropout,
        }

        class Model(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.kernels = kernels
                width = window_size * n_features
                self.trend_heads = nn.ModuleList([nn.Linear(width, 2) for _ in kernels])
                self.residual_heads = nn.ModuleList([nn.Linear(width, 2) for _ in kernels])
                self.tcn = TCNTiny(n_features, tcn_defaults)
                self.dropout = nn.Dropout(dropout)
                self.mix = nn.Linear(4, 2)

            def forward(self, x: Any) -> Any:
                scale_logits = []
                for kernel, trend_head, residual_head in zip(
                    self.kernels, self.trend_heads, self.residual_heads
                ):
                    trend = moving_average_same(x, kernel)
                    residual = x - trend
                    scale_logits.append(
                        trend_head(self.dropout(trend.flatten(1)))
                        + residual_head(self.dropout(residual.flatten(1)))
                    )
                dlinear_logits = torch.stack(scale_logits, dim=0).mean(dim=0)
                tcn_logits = self.tcn(x)
                return self.mix(torch.cat([dlinear_logits, tcn_logits], dim=1))

        return Model()
