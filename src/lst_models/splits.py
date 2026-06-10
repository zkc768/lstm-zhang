from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import pandas as pd

from lst_models.config import parse_bool_flag


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


FOLD_COLUMNS = [
    "fold_id",
    "train_start",
    "train_end_exclusive",
    "eval_start",
    "eval_end_exclusive",
    "purge_or_embargo_policy",
    "n_train_samples",
    "n_eval_samples",
    "event_overlap_count",
]


def train_valid_events(sample_events: pd.DataFrame) -> pd.DataFrame:
    valid_label = sample_events["valid_label"].map(parse_bool_flag)
    train = sample_events.loc[(sample_events["split"] == "train") & valid_label].copy()
    if train.empty:
        raise ValueError("Stage 01 found no train split rows with valid_label=true")
    train["label"] = train["label"].astype(int)
    return train.sort_values(["target_timestamp", "ticker", "sample_id"]).reset_index(drop=True)


def valid_events_for_split(sample_events: pd.DataFrame, split_name: str) -> pd.DataFrame:
    valid_label = sample_events["valid_label"].map(parse_bool_flag)
    events = sample_events.loc[(sample_events["split"] == split_name) & valid_label].copy()
    if events.empty:
        raise ValueError(f"Stage 03 found no {split_name} split rows with valid_label=true")
    events["label"] = events["label"].astype(int)
    return events.sort_values(["target_timestamp", "ticker", "sample_id"]).reset_index(drop=True)


def build_train_inner_folds(train_events: pd.DataFrame, n_folds: int) -> pd.DataFrame:
    if n_folds < 1:
        raise ValueError("train_inner.n_folds must be at least 1")
    days = sorted(train_events["trading_day"].unique())
    if len(days) < n_folds + 1:
        raise ValueError(
            f"need at least {n_folds + 1} train trading days for {n_folds} train-inner folds, "
            f"got {len(days)}"
        )

    fold_span = max(1, len(days) // (n_folds + 1))
    rows = []
    for fold_index in range(n_folds):
        train_end_idx = min(len(days) - 1, fold_span * (fold_index + 1))
        eval_end_idx = len(days) if fold_index == n_folds - 1 else min(
            len(days), fold_span * (fold_index + 2)
        )
        train_days = days[:train_end_idx]
        eval_days = days[train_end_idx:eval_end_idx]
        fold_train = train_events.loc[train_events["trading_day"].isin(train_days)]
        fold_eval = train_events.loc[train_events["trading_day"].isin(eval_days)]
        if fold_train.empty or fold_eval.empty:
            raise ValueError(f"empty train-inner fold {fold_index}")

        eval_start = fold_eval["target_timestamp"].min()
        train_end_exclusive = eval_start
        event_overlap_count = int((fold_train["target_timestamp"] >= eval_start).sum())
        rows.append(
            {
                "fold_id": f"fold_{fold_index}",
                "train_start": fold_train["target_timestamp"].min().isoformat(),
                "train_end_exclusive": train_end_exclusive.isoformat(),
                "eval_start": eval_start.isoformat(),
                "eval_end_exclusive": (
                    fold_eval["target_timestamp"].max() + pd.Timedelta(microseconds=1)
                ).isoformat(),
                "purge_or_embargo_policy": "chronological_expanding_day_block_no_overlap",
                "n_train_samples": int(len(fold_train)),
                "n_eval_samples": int(len(fold_eval)),
                "event_overlap_count": event_overlap_count,
            }
        )

    fold_frame = pd.DataFrame(rows, columns=FOLD_COLUMNS)
    if not (fold_frame["event_overlap_count"] == 0).all():
        raise ValueError("Stage 01 train-inner folds have nonzero event overlap")
    return fold_frame
