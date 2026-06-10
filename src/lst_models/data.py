from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from lst_models.config import hash_file, require_mapping
from lst_models.splits import add_split_column, keep_validation_only_rows, parse_split_boundaries


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
        frame = pd.read_csv(raw_path, encoding="utf-8-sig")
    else:
        frame = pd.read_csv(raw_path, header=None, names=expected, encoding="utf-8-sig")
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


def verify_raw_file_integrity(
    raw_path: Path, file_spec: Mapping[str, Any], ticker: str
) -> None:
    expected_bytes = file_spec.get("bytes")
    if expected_bytes is not None and int(raw_path.stat().st_size) != int(expected_bytes):
        raise ValueError(
            f"raw file byte-size mismatch for {ticker}: {raw_path} "
            f"expected {int(expected_bytes)}"
        )
    expected_sha256 = file_spec.get("sha256")
    if expected_sha256:
        observed_sha256 = hash_file(raw_path)
        if observed_sha256 != str(expected_sha256).lower():
            raise ValueError(
                f"raw file sha256 mismatch for {ticker}: {raw_path} "
                f"expected {expected_sha256}"
            )


def raw_manifest_integrity_summary(raw_manifest: Mapping[str, Any]) -> dict[str, Any]:
    if "raw_source" not in raw_manifest or "tickers" not in raw_manifest:
        return {
            "status": "not_available",
            "ticker_count": 0,
            "sha256_ticker_count": 0,
            "bytes_ticker_count": 0,
            "missing_sha256_tickers": [],
            "missing_bytes_tickers": [],
        }
    raw_source = require_mapping(raw_manifest["raw_source"], "raw_source")
    files = require_mapping(raw_source["files"], "raw_source.files")
    tickers = [str(ticker) for ticker in raw_manifest.get("tickers", [])]
    sha256_tickers = []
    bytes_tickers = []
    for ticker in tickers:
        spec = require_mapping(files[ticker], f"raw_source.files.{ticker}")
        if spec.get("sha256"):
            sha256_tickers.append(ticker)
        if spec.get("bytes") is not None:
            bytes_tickers.append(ticker)
    missing_sha256 = sorted(set(tickers) - set(sha256_tickers))
    missing_bytes = sorted(set(tickers) - set(bytes_tickers))
    status = "complete" if not missing_sha256 and not missing_bytes else "metadata_missing"
    return {
        "status": status,
        "ticker_count": len(tickers),
        "sha256_ticker_count": len(sha256_tickers),
        "bytes_ticker_count": len(bytes_tickers),
        "missing_sha256_tickers": missing_sha256,
        "missing_bytes_tickers": missing_bytes,
    }


def load_sample_event_index(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required_columns = {
        "sample_id",
        "ticker",
        "target_timestamp",
        "trading_day",
        "split",
        "label",
        "valid_label",
    }
    missing = sorted(required_columns - set(frame.columns))
    if missing:
        raise ValueError(f"sample_event_index.csv missing columns: {missing}")
    frame = frame.copy()
    frame["target_timestamp"] = pd.to_datetime(frame["target_timestamp"])
    frame["trading_day"] = frame["trading_day"].astype(str)
    return frame


def load_stage01_summary(path: Path) -> pd.DataFrame:
    summary = pd.read_csv(path)
    required_columns = {"candidate_id", "n_samples_total", "n_samples_by_ticker_json"}
    missing = sorted(required_columns - set(summary.columns))
    if missing:
        raise ValueError(f"Stage 01 summary missing required columns for Stage 02: {missing}")
    return summary


def load_train_bars(
    raw_manifest: Mapping[str, Any],
    split_freeze: Mapping[str, Any],
    inputs: Mapping[str, Any],
) -> pd.DataFrame:
    raw_source = require_mapping(raw_manifest["raw_source"], "raw_source")
    recipe = require_mapping(raw_manifest["five_minute_recipe"], "five_minute_recipe")
    raw_data_dir = Path(str(inputs.get("raw_data_dir", raw_source["local_download_dir"])))
    boundaries = parse_split_boundaries(split_freeze)

    frames = []
    for ticker in raw_manifest["tickers"]:
        file_spec = require_mapping(raw_source["files"][ticker], f"raw_source.files.{ticker}")
        raw_path = raw_data_dir / str(file_spec["name"])
        verify_raw_file_integrity(raw_path, file_spec, str(ticker))
        one_minute = read_raw_txt_file(raw_path, str(ticker), raw_source)
        five_minute = resample_1min_to_5min(one_minute, recipe)
        split_frame = add_split_column(five_minute, boundaries)
        frames.append(split_frame.loc[split_frame["split"] == "train"].copy())

    if not frames:
        raise ValueError("Stage 01 raw loading produced no train bar frames")
    bars = pd.concat(frames, ignore_index=True).sort_values(["ticker", "timestamp"])
    if bars.empty:
        raise ValueError("Stage 01 found no train bars after Stage 00 split filtering")
    bars["trading_day"] = bars["timestamp"].dt.strftime("%Y-%m-%d")
    return bars.reset_index(drop=True)


def load_train_validation_bars(
    raw_manifest: Mapping[str, Any],
    split_freeze: Mapping[str, Any],
    inputs: Mapping[str, Any],
) -> pd.DataFrame:
    raw_source = require_mapping(raw_manifest["raw_source"], "raw_source")
    recipe = require_mapping(raw_manifest["five_minute_recipe"], "five_minute_recipe")
    raw_data_dir = Path(str(inputs.get("raw_data_dir", raw_source["local_download_dir"])))
    boundaries = parse_split_boundaries(split_freeze)

    frames = []
    for ticker in raw_manifest["tickers"]:
        file_spec = require_mapping(raw_source["files"][ticker], f"raw_source.files.{ticker}")
        raw_path = raw_data_dir / str(file_spec["name"])
        verify_raw_file_integrity(raw_path, file_spec, str(ticker))
        one_minute = read_raw_txt_file(raw_path, str(ticker), raw_source)
        five_minute = resample_1min_to_5min(one_minute, recipe)
        split_frame = add_split_column(five_minute, boundaries)
        frames.append(keep_validation_only_rows(split_frame))

    if not frames:
        raise ValueError("Stage 03 raw loading produced no train/validation bar frames")
    bars = pd.concat(frames, ignore_index=True).sort_values(["ticker", "timestamp"])
    if bars.empty:
        raise ValueError("Stage 03 found no train/validation bars after Stage 00 split filtering")
    bars["trading_day"] = bars["timestamp"].dt.strftime("%Y-%m-%d")
    return bars.reset_index(drop=True)
