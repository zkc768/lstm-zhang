"""Feature construction shared by the stage rebuild chain.

``build_feature_frame`` and ``require_feature_columns`` are part of the
``feature_rebuild_code_sha256`` provenance payload built in
``lst_models.artifacts``. Their source text is hashed into stage run
manifests: behavior changes here are research-mechanism changes and require
an approved protocol update, not a casual edit. Output behavior is pinned by
``tests/contracts/test_refactor_equivalence_golden.py``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def build_feature_frame(train_bars: pd.DataFrame) -> pd.DataFrame:
    frame = train_bars.sort_values(["ticker", "timestamp"]).copy()
    day_group = frame.groupby(["ticker", "trading_day"], sort=False)

    previous_close = day_group["close"].shift(1)
    close = frame["close"].astype(float)
    open_ = frame["open"].astype(float)
    high = frame["high"].astype(float)
    low = frame["low"].astype(float)
    volume = frame["volume"].astype(float)

    frame["log_return"] = np.log(close / previous_close)
    frame["close_to_open_return"] = np.log(close / open_)
    frame["high_low_range"] = (high - low) / close.replace(0.0, np.nan)
    frame["rolling_volatility_20"] = day_group["log_return"].transform(
        lambda series: series.rolling(20, min_periods=5).std()
    )

    delta = day_group["close"].diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.groupby([frame["ticker"], frame["trading_day"]]).transform(
        lambda series: series.rolling(14, min_periods=5).mean()
    )
    avg_loss = loss.groupby([frame["ticker"], frame["trading_day"]]).transform(
        lambda series: series.rolling(14, min_periods=5).mean()
    )
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    frame["rsi_14"] = (100.0 - (100.0 / (1.0 + rs))) / 100.0
    frame.loc[avg_loss.eq(0.0) & avg_gain.gt(0.0), "rsi_14"] = 1.0

    rolling_mean = day_group["close"].transform(lambda series: series.rolling(20, min_periods=10).mean())
    rolling_std = day_group["close"].transform(lambda series: series.rolling(20, min_periods=10).std())
    lower = rolling_mean - 2.0 * rolling_std
    upper = rolling_mean + 2.0 * rolling_std
    frame["bollinger_pctb"] = (close - lower) / (upper - lower).replace(0.0, np.nan)

    # MACD/close_scale reset per trading day like every other feature in the set,
    # so this one indicator does not silently carry overnight-gap state across
    # sessions (which would make it behave differently from the day-local rest).
    ema12 = day_group["close"].transform(lambda series: series.ewm(span=12, adjust=False).mean())
    ema26 = day_group["close"].transform(lambda series: series.ewm(span=26, adjust=False).mean())
    macd = ema12 - ema26
    signal = macd.groupby([frame["ticker"], frame["trading_day"]]).transform(
        lambda series: series.ewm(span=9, adjust=False).mean()
    )
    macd_hist = macd - signal
    close_scale = day_group["close"].transform(lambda series: series.rolling(20, min_periods=10).std())
    frame["normalized_macd_hist"] = macd_hist / close_scale.replace(0.0, np.nan)

    rolling_volume = day_group["volume"].transform(lambda series: series.rolling(20, min_periods=5).mean())
    frame["normalized_volume_20"] = volume / rolling_volume.replace(0.0, np.nan) - 1.0

    minute_of_day = frame["timestamp"].dt.hour * 60 + frame["timestamp"].dt.minute
    market_open_minute = 9 * 60 + 30
    regular_session_minutes = 6.5 * 60
    phase = 2.0 * np.pi * (minute_of_day - market_open_minute) / regular_session_minutes
    frame["time_of_day_sin"] = np.sin(phase)
    frame["time_of_day_cos"] = np.cos(phase)

    return frame.reset_index(drop=True)


def require_feature_columns(feature_columns: tuple[str, ...], feature_frame: pd.DataFrame) -> None:
    missing = sorted(set(feature_columns) - set(feature_frame.columns))
    if missing:
        raise ValueError(f"Stage 01 feature set references missing columns: {missing}")
