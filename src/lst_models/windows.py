"""Per-ticker window dataset construction, materialization, and fold slicing.

``build_window_dataset`` is part of the ``feature_rebuild_code_sha256``
provenance payload built in ``lst_models.artifacts``. Behavior changes here
are research-mechanism changes and require an approved protocol update.
Output behavior is pinned by
``tests/contracts/test_refactor_equivalence_golden.py``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CandidateDataset:
    metadata: pd.DataFrame
    feature_blocks: Mapping[tuple[str, str], np.ndarray]
    feature_columns: tuple[str, ...]
    window_size: int


def build_window_dataset(
    feature_frame: pd.DataFrame,
    train_events: pd.DataFrame,
    *,
    feature_set: str,
    feature_columns: tuple[str, ...],
    window_size: int,
) -> CandidateDataset:
    rows: list[dict[str, Any]] = []
    feature_blocks: dict[tuple[str, str], np.ndarray] = {}
    events_by_group = {
        key: group.sort_values("target_timestamp")
        for key, group in train_events.groupby(["ticker", "trading_day"], sort=False)
    }
    for key, bars in feature_frame.groupby(["ticker", "trading_day"], sort=False):
        if key not in events_by_group:
            continue
        typed_key = (str(key[0]), str(key[1]))
        bar_part = bars.sort_values("timestamp").reset_index(drop=True)
        values = bar_part.loc[:, feature_columns].to_numpy(dtype=np.float32)
        feature_blocks[typed_key] = values
        finite_row = np.isfinite(values).all(axis=1)
        position_by_timestamp = {
            pd.Timestamp(timestamp): position
            for position, timestamp in enumerate(bar_part["timestamp"].tolist())
        }
        for event in events_by_group[key].to_dict(orient="records"):
            position = position_by_timestamp.get(pd.Timestamp(event["target_timestamp"]))
            if position is None or position < window_size - 1:
                continue
            start = position - window_size + 1
            end = position + 1
            if not bool(finite_row[start:end].all()):
                continue
            rows.append(
                {
                    "sample_id": event["sample_id"],
                    "ticker": event["ticker"],
                    "target_timestamp": pd.Timestamp(event["target_timestamp"]),
                    "trading_day": event["trading_day"],
                    "label": int(event["label"]),
                    "window_start_position": int(start),
                    "window_end_position_exclusive": int(end),
                    "candidate_id": f"{feature_set}_w{window_size}",
                    "feature_set": feature_set,
                    "window_size": int(window_size),
                }
            )

    metadata = pd.DataFrame(rows)
    return CandidateDataset(
        metadata=metadata.reset_index(drop=True),
        feature_blocks=feature_blocks,
        feature_columns=feature_columns,
        window_size=window_size,
    )


def materialize_window_matrix(dataset: CandidateDataset, indices: np.ndarray) -> np.ndarray:
    width = dataset.window_size * len(dataset.feature_columns)
    if len(indices) == 0:
        return np.empty((0, width), dtype=np.float32)
    rows = []
    for record in dataset.metadata.iloc[indices].to_dict(orient="records"):
        key = (str(record["ticker"]), str(record["trading_day"]))
        block = dataset.feature_blocks[key]
        start = int(record["window_start_position"])
        end = int(record["window_end_position_exclusive"])
        window = block[start:end]
        if len(window) != dataset.window_size:
            raise ValueError(
                f"materialized window has {len(window)} rows, expected {dataset.window_size}"
            )
        rows.append(window.reshape(-1))
    return np.vstack(rows).astype(np.float32, copy=False)


def fold_indices(metadata: pd.DataFrame, fold: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    if metadata.empty:
        return np.array([], dtype=int), np.array([], dtype=int)
    timestamps = metadata["target_timestamp"]
    train_start = pd.Timestamp(fold["train_start"])
    train_end = pd.Timestamp(fold["train_end_exclusive"])
    eval_start = pd.Timestamp(fold["eval_start"])
    eval_end = pd.Timestamp(fold["eval_end_exclusive"])
    train_mask = (timestamps >= train_start) & (timestamps < train_end)
    eval_mask = (timestamps >= eval_start) & (timestamps < eval_end)
    return np.flatnonzero(train_mask.to_numpy()), np.flatnonzero(eval_mask.to_numpy())


def cap_indices(metadata: pd.DataFrame, indices: np.ndarray, cap: int) -> np.ndarray:
    if cap <= 0 or len(indices) <= cap:
        return indices
    subset = metadata.iloc[indices].copy()
    subset["_source_position"] = indices
    groups = list(subset.groupby(["ticker", "label"], sort=True))
    per_group = max(1, cap // max(1, len(groups)))
    selected: list[int] = []
    for _, group in groups:
        ordered = group.sort_values(["target_timestamp", "sample_id"])
        positions = ordered["_source_position"].to_numpy(dtype=int)
        if len(positions) <= per_group:
            selected.extend(positions.tolist())
        else:
            take = np.linspace(0, len(positions) - 1, per_group, dtype=int)
            selected.extend(positions[take].tolist())
    if len(selected) > cap:
        selected = selected[:cap]
    return np.array(sorted(selected), dtype=int)


def sample_id_hash(sample_ids: list[Any]) -> str:
    payload = "\n".join(str(sample_id) for sample_id in sample_ids).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_rebuilt_candidate_counts(
    candidate: Mapping[str, Any],
    dataset: CandidateDataset,
    stage01_summary: pd.DataFrame,
) -> None:
    candidate_id = str(candidate["candidate_id"])
    matches = stage01_summary.loc[stage01_summary["candidate_id"].astype(str).eq(candidate_id)]
    if matches.empty:
        raise ValueError(f"Stage 01 summary missing candidate row for {candidate_id}")
    row = matches.iloc[0]
    expected_total = int(row["n_samples_total"])
    actual_total = int(len(dataset.metadata))
    if actual_total != expected_total:
        raise ValueError(
            f"Stage 02 rebuilt sample count mismatch for {candidate_id}: "
            f"expected {expected_total}, observed {actual_total}"
        )
    expected_by_ticker = {
        str(ticker): int(count)
        for ticker, count in json.loads(str(row["n_samples_by_ticker_json"])).items()
    }
    actual_by_ticker = {
        str(ticker): int(count)
        for ticker, count in dataset.metadata.groupby("ticker").size().to_dict().items()
    }
    if actual_by_ticker != expected_by_ticker:
        raise ValueError(
            f"Stage 02 rebuilt per-ticker sample count mismatch for {candidate_id}: "
            f"expected {expected_by_ticker}, observed {actual_by_ticker}"
        )
