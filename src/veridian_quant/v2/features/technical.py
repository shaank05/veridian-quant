"""Technical feature calculations for Veridian Quant v2.

This module contains pure, deterministic feature functions required by the S1
research candidate. The functions operate on lowercase OHLCV pandas inputs and
return pandas Series without mutating caller-provided data.
"""

from collections.abc import Iterable

import numpy as np
import pandas as pd


def rolling_mean_close(data: pd.DataFrame, window: int) -> pd.Series:
    """Return the rolling mean of the lowercase ``close`` column.

    Periods without enough lookback observations are returned as ``NaN``.
    """

    _validate_window(window)
    _validate_columns(data, ("close",))
    return data["close"].rolling(window=window, min_periods=window).mean()


def rolling_std_close(data: pd.DataFrame, window: int) -> pd.Series:
    """Return the rolling sample standard deviation of the ``close`` column.

    Periods without enough lookback observations are returned as ``NaN``.
    """

    _validate_window(window)
    _validate_columns(data, ("close",))
    return data["close"].rolling(window=window, min_periods=window).std()


def price_zscore(data: pd.DataFrame, window: int) -> pd.Series:
    """Return close-price Z-scores for the requested rolling window.

    Z-score is defined as ``(close - rolling_mean_close) / rolling_std_close``.
    Rows with insufficient lookback or zero rolling standard deviation return
    ``NaN``.
    """

    _validate_window(window)
    _validate_columns(data, ("close",))
    mean = rolling_mean_close(data, window)
    std = rolling_std_close(data, window).replace(0, np.nan)
    return (data["close"] - mean) / std


def true_range(data: pd.DataFrame) -> pd.Series:
    """Return True Range using lowercase ``high``, ``low``, and ``close``.

    True Range is the maximum of ``high - low``, ``abs(high - previous_close)``,
    and ``abs(low - previous_close)``. For the first row, where no previous
    close exists, the result falls back to ``high - low``.
    """

    _validate_columns(data, ("high", "low", "close"))
    previous_close = data["close"].shift(1)
    ranges = pd.concat(
        [
            data["high"] - data["low"],
            (data["high"] - previous_close).abs(),
            (data["low"] - previous_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def atr(data: pd.DataFrame, window: int) -> pd.Series:
    """Return Average True Range as a rolling mean of True Range.

    Periods without enough lookback observations are returned as ``NaN``.
    """

    _validate_window(window)
    _validate_columns(data, ("high", "low", "close"))
    return true_range(data).rolling(window=window, min_periods=window).mean()


def _validate_window(window: int) -> None:
    """Validate that a rolling window is a positive integer."""

    if not isinstance(window, int) or window < 1:
        raise ValueError("window must be a positive integer")


def _validate_columns(data: pd.DataFrame, required_columns: Iterable[str]) -> None:
    """Validate that all required lowercase columns are present."""

    missing = [column for column in required_columns if column not in data.columns]
    if missing:
        missing_columns = ", ".join(missing)
        raise ValueError(f"missing required columns: {missing_columns}")
