"""Tiny causal TCN classifier.

Torch is imported lazily inside the factory so this module stays importable
on machines without torch.
"""

from __future__ import annotations

from typing import Any, Mapping


class TCNTiny:
    def __new__(cls, n_features: int, defaults: Mapping[str, Any]) -> Any:
        import torch.nn as nn

        channels = [int(value) for value in defaults.get("channels", [32, 32])]
        kernel_size = int(defaults.get("kernel_size", 3))
        dropout = float(defaults.get("dropout", 0.10))

        class CausalBlock(nn.Module):
            def __init__(self, in_channels: int, out_channels: int, dilation: int) -> None:
                super().__init__()
                self.padding = (kernel_size - 1) * dilation
                self.conv = nn.Conv1d(
                    in_channels,
                    out_channels,
                    kernel_size=kernel_size,
                    padding=self.padding,
                    dilation=dilation,
                )
                self.norm = nn.ReLU()
                self.dropout = nn.Dropout(dropout)
                self.projection = (
                    nn.Identity()
                    if in_channels == out_channels
                    else nn.Conv1d(in_channels, out_channels, kernel_size=1)
                )

            def forward(self, x: Any) -> Any:
                y = self.conv(x)
                if self.padding:
                    y = y[:, :, :-self.padding]
                y = self.dropout(self.norm(y))
                return y + self.projection(x)

        class Model(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                layers = []
                in_channels = n_features
                for layer_index, out_channels in enumerate(channels):
                    layers.append(CausalBlock(in_channels, out_channels, dilation=2**layer_index))
                    in_channels = out_channels
                self.tcn = nn.Sequential(*layers)
                self.head = nn.Linear(in_channels, 2)

            def forward(self, x: Any) -> Any:
                encoded = self.tcn(x.transpose(1, 2))
                return self.head(encoded[:, :, -1])

        return Model()
