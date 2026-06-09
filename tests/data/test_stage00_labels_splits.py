from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lst_models.labels import make_direction_labels  # noqa: E402
from lst_models.data import read_raw_txt_file, resample_1min_to_5min  # noqa: E402
from lst_models.splits import add_split_column, parse_split_boundaries  # noqa: E402


def frame_from_closes(closes: list[float], start: str = "2020-01-02 09:30") -> pd.DataFrame:
    timestamps = pd.date_range(start=start, periods=len(closes), freq="5min")
    return pd.DataFrame(
        {
            "ticker": "ABC",
            "timestamp": timestamps,
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [100] * len(closes),
        }
    )


def boundaries(train_end: str = "2020-01-03") -> dict[str, str]:
    return {
        "train_start": "2020-01-02",
        "train_end": train_end,
        "validation_start": train_end,
        "validation_end": "2020-01-04",
        "closed_holdout_test_start": "2020-01-04",
    }


def policy(horizon_k: int = 1, no_trade_band_bps: float = 10.0) -> dict[str, object]:
    return {
        "operator": "endpoint_cumulative_return",
        "horizon_k": horizon_k,
        "no_trade_band_bps": no_trade_band_bps,
    }


def raw_config() -> dict[str, object]:
    return {
        "txt_columns": ["Date", "Time", "Open", "High", "Low", "Close", "Volume"],
        "date_format": "%m/%d/%Y",
        "time_format": "%H:%M",
    }


def test_read_raw_txt_file_handles_utf8_bom_header(tmp_path: Path) -> None:
    raw_path = tmp_path / "ABC.txt"
    raw_path.write_text(
        "\ufeffDate,Time,Open,High,Low,Close,Volume\n"
        "01/02/2020,09:30,100,101,99,100.5,123\n",
        encoding="utf-8",
    )

    frame = read_raw_txt_file(raw_path, "ABC", raw_config())

    assert list(frame.columns) == ["ticker", "timestamp", "open", "high", "low", "close", "volume"]
    assert frame.loc[0, "ticker"] == "ABC"
    assert frame.loc[0, "timestamp"] == pd.Timestamp("2020-01-02 09:30")
    assert frame.loc[0, "close"] == 100.5


def test_endpoint_cumulative_return_labels_up_down_and_no_trade() -> None:
    base = frame_from_closes([100.00, 100.20, 100.20, 99.90])
    split = add_split_column(base, parse_split_boundaries(boundaries()))
    labeled = make_direction_labels(split, policy())

    assert labeled.loc[0, "label"] == 1
    assert pd.isna(labeled.loc[1, "label"])
    assert labeled.loc[1, "invalid_no_trade_band"]
    assert labeled.loc[2, "label"] == 0


def test_label_horizon_crossing_trading_day_is_invalid() -> None:
    base = pd.concat(
        [
            frame_from_closes([100.0], start="2020-01-02 15:55"),
            frame_from_closes([101.0], start="2020-01-03 09:30"),
        ],
        ignore_index=True,
    )
    split = add_split_column(base, parse_split_boundaries(boundaries()))
    labeled = make_direction_labels(split, policy())

    assert labeled.loc[0, "invalid_cross_trading_day"]
    assert pd.isna(labeled.loc[0, "label"])


def test_label_horizon_crossing_split_is_invalid() -> None:
    base = frame_from_closes([100.0, 101.0], start="2020-01-02 09:30")
    split = add_split_column(base, parse_split_boundaries(boundaries(train_end="2020-01-02 09:35")))
    labeled = make_direction_labels(split, policy())

    assert labeled.loc[0, "invalid_cross_split"]
    assert pd.isna(labeled.loc[0, "label"])


def test_label_horizon_with_intraday_gap_is_irregular_and_invalid() -> None:
    base = pd.DataFrame(
        {
            "ticker": ["ABC", "ABC"],
            "timestamp": [pd.Timestamp("2020-01-02 09:30"), pd.Timestamp("2020-01-02 09:40")],
            "open": [100.0, 101.0],
            "high": [100.0, 101.0],
            "low": [100.0, 101.0],
            "close": [100.0, 101.0],
            "volume": [100, 100],
        }
    )
    split = add_split_column(base, parse_split_boundaries(boundaries()))

    labeled = make_direction_labels(split, policy())

    assert labeled.loc[0, "invalid_irregular_horizon"]
    assert pd.isna(labeled.loc[0, "label"])
    assert pd.isna(labeled.loc[0, "future_cumulative_return"])


def test_label_horizon_missing_future_is_invalid() -> None:
    base = frame_from_closes([100.0], start="2020-01-02 09:30")
    split = add_split_column(base, parse_split_boundaries(boundaries()))

    labeled = make_direction_labels(split, policy())

    assert labeled.loc[0, "invalid_missing_future"]
    assert pd.isna(labeled.loc[0, "label"])
    assert pd.isna(labeled.loc[0, "future_cumulative_return"])


def test_resample_excludes_partial_market_close_bucket() -> None:
    timestamps = pd.date_range("2020-01-02 09:30", "2020-01-02 16:00", freq="1min")
    one_minute = pd.DataFrame(
        {
            "ticker": "ABC",
            "timestamp": timestamps,
            "open": 1.0,
            "high": 1.0,
            "low": 1.0,
            "close": 1.0,
            "volume": 1,
        }
    )
    recipe = {
        "resample_rule": "5min",
        "market_open": "09:30",
        "market_close": "16:00",
        "agg": {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"},
        "drop_na_subset": ["open", "high", "low", "close", "volume"],
        "output_columns": ["ticker", "timestamp", "open", "high", "low", "close", "volume"],
    }

    five_minute = resample_1min_to_5min(one_minute, recipe)

    assert len(five_minute) == 78
    assert five_minute["timestamp"].iloc[0] == pd.Timestamp("2020-01-02 09:30")
    assert five_minute["timestamp"].iloc[-1] == pd.Timestamp("2020-01-02 15:55")
