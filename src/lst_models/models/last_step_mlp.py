"""Last-bar MLP (Stage 04 window-depth control).

Receives the full (batch, window, features) tensor like every sequence model
but reads ONLY the final bar inside ``forward``, so its information set is
exactly the latest timestep. Torch is imported lazily inside the factory so
this module stays importable on machines without torch.
"""

from __future__ import annotations

from typing import Any, Mapping


class LastStepMLPTiny:
    def __new__(cls, n_features: int, defaults: Mapping[str, Any]) -> Any:
        import torch.nn as nn

        hidden_size = int(defaults.get("hidden_size", 32))
        dropout = float(defaults.get("dropout", 0.10))

        class Model(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.body = nn.Sequential(
                    nn.Linear(n_features, hidden_size),
                    nn.ReLU(),
                    nn.Dropout(dropout),
                    nn.Linear(hidden_size, 2),
                )

            def forward(self, x: Any) -> Any:
                return self.body(x[:, -1, :])

        return Model()
