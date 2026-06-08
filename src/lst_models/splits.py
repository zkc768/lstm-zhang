from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import pandas as pd


@dataclass(frozen=True)
class SplitBoundaries:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    validation_start: pd.Timestamp
    validation_end: pd.Timestamp
    closed_holdout_test_start: pd.Timestamp


def parse_split_boundaries(config: Mapping[str, str]) -> SplitBoundaries:
    return SplitBoundaries(
        train_start=pd.Timestamp(config["train_start"]),
        train_end=pd.Timestamp(config["train_end"]),
        validation_start=pd.Timestamp(config["validation_start"]),
        validation_end=pd.Timestamp(config["validation_end"]),
        closed_holdout_test_start=pd.Timestamp(config["closed_holdout_test_start"]),
    )


def assign_split(timestamp: pd.Timestamp, boundaries: SplitBoundaries) -> str:
    ts = pd.Timestamp(timestamp)
    if boundaries.train_start <= ts < boundaries.train_end:
        return "train"
    if boundaries.validation_start <= ts < boundaries.validation_end:
        return "validation"
    if ts >= boundaries.closed_holdout_test_start:
        return "closed_holdout_test"
    return "outside_train_validation"


def add_split_column(frame: pd.DataFrame, boundaries: SplitBoundaries) -> pd.DataFrame:
    current = frame.copy()
    current["split"] = current["timestamp"].map(lambda ts: assign_split(ts, boundaries))
    return current


def keep_validation_only_rows(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.loc[frame["split"].isin(["train", "validation"])].copy()
