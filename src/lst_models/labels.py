from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd


BAR_INTERVAL_MINUTES = 5
BPS_TO_DECIMAL = 10000.0


def make_direction_labels(frame: pd.DataFrame, label_policy: Mapping[str, object]) -> pd.DataFrame:
    if label_policy["operator"] != "endpoint_cumulative_return":
        raise ValueError(f"unsupported label operator: {label_policy['operator']!r}")

    horizon_k = int(label_policy["horizon_k"])
    threshold = float(label_policy["no_trade_band_bps"]) / BPS_TO_DECIMAL
    current = frame.sort_values(["ticker", "timestamp"]).copy()
    labeled_parts = []

    for ticker, ticker_frame in current.groupby("ticker", sort=True):
        part = ticker_frame.sort_values("timestamp").copy()
        close = part["close"].astype(float)
        future_timestamp = part["timestamp"].shift(-horizon_k)
        horizon_split = part["split"].shift(-horizon_k)
        part["horizon_end_timestamp"] = future_timestamp
        part["future_cumulative_return"] = close.shift(-horizon_k) / close - 1.0

        same_day = pd.Series(True, index=part.index)
        current_day = part["timestamp"].dt.date
        for offset in range(1, horizon_k + 1):
            same_day &= current_day.shift(-offset).eq(current_day)

        expected_horizon = pd.Timedelta(minutes=BAR_INTERVAL_MINUTES * horizon_k)
        actual_horizon = future_timestamp - part["timestamp"]
        part["invalid_missing_future"] = part["future_cumulative_return"].isna()
        part["invalid_cross_trading_day"] = ~same_day
        part["invalid_irregular_horizon"] = (
            future_timestamp.notna() & same_day & actual_horizon.ne(expected_horizon)
        )
        part["invalid_cross_split"] = (
            part["future_cumulative_return"].notna() & part["split"].ne(horizon_split)
        )

        valid_before_band = ~(
            part["invalid_missing_future"]
            | part["invalid_cross_trading_day"]
            | part["invalid_irregular_horizon"]
            | part["invalid_cross_split"]
        )
        part["invalid_no_trade_band"] = (
            valid_before_band & part["future_cumulative_return"].abs().le(threshold)
        )

        invalid = ~valid_before_band | part["invalid_no_trade_band"]
        part["label"] = np.nan
        part.loc[valid_before_band & part["future_cumulative_return"].gt(threshold), "label"] = 1
        part.loc[valid_before_band & part["future_cumulative_return"].lt(-threshold), "label"] = 0
        part.loc[invalid, "future_cumulative_return"] = np.nan
        part["valid_label"] = part["label"].notna()
        part["sample_id"] = (
            part["ticker"].astype(str)
            + "|"
            + part["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")
        )
        part["trading_day"] = part["timestamp"].dt.strftime("%Y-%m-%d")
        part["horizon_k"] = horizon_k
        labeled_parts.append(part)

    return pd.concat(labeled_parts, ignore_index=True).sort_values(["ticker", "timestamp"])


def summarize_label_validity(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    invalid_columns = [
        "invalid_missing_future",
        "invalid_cross_trading_day",
        "invalid_irregular_horizon",
        "invalid_cross_split",
        "invalid_no_trade_band",
    ]
    for (ticker, split), group in frame.groupby(["ticker", "split"], sort=True):
        if split not in {"train", "validation"}:
            continue
        row = {
            "ticker": ticker,
            "split": split,
            "rows": int(len(group)),
            "valid_label_rows": int(group["valid_label"].sum()),
            "up_labels": int((group["label"] == 1).sum()),
            "down_labels": int((group["label"] == 0).sum()),
        }
        row.update({name: int(group[name].sum()) for name in invalid_columns})
        rows.append(row)
    return pd.DataFrame(rows)
