"""Standard DLinear tiny classifier and shared moving-average helpers.

Torch is imported lazily inside the factory so this module stays importable
on machines without torch. Models receive tensors and config values only: no
file reads, no YAML, no Drive paths, no result writing.
"""

from __future__ import annotations

from typing import Any, Mapping


def odd_kernel_within_window(kernel: int, window_size: int) -> int:
    current = max(1, min(kernel, window_size))
    if current % 2 == 0:
        current = max(1, current - 1)
    return current


def moving_average_same(x: Any, kernel: int) -> Any:
    import torch.nn.functional as functional

    left = kernel // 2
    right = kernel - 1 - left
    channel_first = x.transpose(1, 2)
    padded = functional.pad(channel_first, (left, right), mode="replicate")
    return functional.avg_pool1d(padded, kernel_size=kernel, stride=1).transpose(1, 2)


class StandardDLinearTiny:
    def __new__(cls, window_size: int, n_features: int, defaults: Mapping[str, Any]) -> Any:
        import torch.nn as nn

        class Model(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                kernel = odd_kernel_within_window(int(defaults.get("moving_avg_kernel", 5)), window_size)
                self.kernel = kernel
                dropout = float(defaults.get("dropout", 0.10))
                width = window_size * n_features
                self.trend_head = nn.Linear(width, 2)
                self.residual_head = nn.Linear(width, 2)
                self.dropout = nn.Dropout(dropout)

            def forward(self, x: Any) -> Any:
                trend = moving_average_same(x, self.kernel)
                residual = x - trend
                return self.trend_head(self.dropout(trend.flatten(1))) + self.residual_head(
                    self.dropout(residual.flatten(1))
                )

        return Model()
