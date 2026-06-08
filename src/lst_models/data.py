from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import pandas as pd


CANONICAL_COLUMNS = ["ticker", "timestamp", "open", "high", "low", "close", "volume"]


def validate_raw_columns(columns: Sequence[str], expected: Sequence[str], path: Path) -> None:
    observed = [str(col).strip() for col in columns]
    expected_list = list(expected)
    if observed != expected_list:
        raise ValueError(f"unexpected raw columns in {path}: expected {expected_list}, got {observed}")


def read_raw_txt_file(path: str | Path, ticker: str, raw_config: Mapping[str, object]) -> pd.DataFrame:
    raw_path = Path(path)
    if not raw_path.exists():
        raise FileNotFoundError(f"missing raw ticker file: {raw_path}")

    expected = list(raw_config["txt_columns"])
    with raw_path.open("r", encoding="utf-8-sig") as handle:
        first_line = handle.readline().strip()
    first_fields = [part.strip() for part in first_line.split(",")]
    has_header = first_fields == expected

    if has_header:
        frame = pd.read_csv(raw_path)
    else:
        frame = pd.read_csv(raw_path, header=None, names=expected)
    validate_raw_columns(frame.columns, expected, raw_path)

    timestamp_text = frame["Date"].astype(str).str.strip() + " " + frame["Time"].astype(str).str.strip()
    timestamp = pd.to_datetime(
        timestamp_text,
        format=f"{raw_config['date_format']} {raw_config['time_format']}",
        errors="raise",
    )

    result = pd.DataFrame(
        {
            "ticker": ticker,
            "timestamp": timestamp,
            "open": pd.to_numeric(frame["Open"], errors="raise"),
            "high": pd.to_numeric(frame["High"], errors="raise"),
            "low": pd.to_numeric(frame["Low"], errors="raise"),
            "close": pd.to_numeric(frame["Close"], errors="raise"),
            "volume": pd.to_numeric(frame["Volume"], errors="raise"),
        }
    )
    return result.sort_values(["ticker", "timestamp"]).reset_index(drop=True)


def filter_regular_session(
    frame: pd.DataFrame,
    market_open: str,
    market_close: str,
    *,
    include_close: bool,
) -> pd.DataFrame:
    open_time = pd.Timestamp(market_open).time()
    close_time = pd.Timestamp(market_close).time()
    times = frame["timestamp"].dt.time
    if include_close:
        return frame.loc[(times >= open_time) & (times <= close_time)].copy()
    return frame.loc[(times >= open_time) & (times < close_time)].copy()


def resample_1min_to_5min(frame: pd.DataFrame, recipe: Mapping[str, object]) -> pd.DataFrame:
    required = {"ticker", "timestamp", "open", "high", "low", "close", "volume"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"missing columns for 5-minute resample: {sorted(missing)}")

    current = filter_regular_session(
        frame,
        str(recipe["market_open"]),
        str(recipe["market_close"]),
        include_close=True,
    )
    rule = str(recipe["resample_rule"])
    agg = dict(recipe["agg"])
    parts = []
    for (ticker, trading_day), group in current.groupby(
        [current["ticker"], current["timestamp"].dt.date], sort=True
    ):
        day = group.sort_values("timestamp").set_index("timestamp")
        resampled = day.resample(rule, label="left", closed="left").agg(agg)
        resampled["ticker"] = ticker
        resampled["timestamp"] = resampled.index
        parts.append(resampled.reset_index(drop=True))

    if not parts:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    output = pd.concat(parts, ignore_index=True)
    output = filter_regular_session(
        output,
        str(recipe["market_open"]),
        str(recipe["market_close"]),
        include_close=False,
    )
    output = output.dropna(subset=list(recipe["drop_na_subset"]))
    output = output.loc[:, list(recipe["output_columns"])]
    return output.sort_values(["ticker", "timestamp"]).reset_index(drop=True)
