"""Multi-scale DLinear branch alone (Stage 04 architectural control).

The MS-DLinear+TCN hybrid minus its TCN branch and mix layer: per-scale
trend/residual linear heads whose summed logits are averaged across scales.
Torch is imported lazily inside the factory so this module stays importable
on machines without torch.
"""

from __future__ import annotations

from typing import Any, Mapping

from lst_models.models.standard_dlinear import moving_average_same, odd_kernel_within_window


class MSDLinearOnlyTiny:
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

        class Model(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.kernels = kernels
                width = window_size * n_features
                self.trend_heads = nn.ModuleList([nn.Linear(width, 2) for _ in kernels])
                self.residual_heads = nn.ModuleList([nn.Linear(width, 2) for _ in kernels])
                self.dropout = nn.Dropout(dropout)

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
                return torch.stack(scale_logits, dim=0).mean(dim=0)

        return Model()
