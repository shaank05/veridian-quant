"""S4 compression and breakout feature calculations.

The functions in this module are pure pandas helpers for Phase 29B research.
They calculate transparent volatility/range compression and breakout features
without generating S4 signals or mutating caller-provided data.

Fields ending in ``_pct`` are percentage-point values. For example, ``1.5``
means 1.5%, not 0.015.
"""

from collections.abc import Iterable

import numpy as np
import pandas as pd

from veridian_quant.v2.features.technical import atr


def atr_percentage(data: pd.DataFrame, atr_window: int = 14) -> pd.Series:
    """Return ATR as a percentage-point value of close.

    The result is ``100 * ATR / close``. Rows with insufficient ATR lookback,
    missing close, or zero close return ``NaN``.
    """

    _validate_window(atr_window, "atr_window")
    _validate_columns(data, ("high", "low", "close"))
    close = data["close"].replace(0, np.nan)
    return 100.0 * atr(data, window=atr_window) / close


def rolling_percentile_rank(series: pd.Series, window: int) -> pd.Series:
    """Return trailing percentile rank of the current value in ``series``.

    The current row is ranked against the current and prior rows inside the
    rolling window. Output is a fraction from 0.0 to 1.0, where 0.0 means the
    current value is the lowest value in the window and 1.0 means it is the
    highest. Ties receive the average percentile position. Any window
    containing ``NaN`` returns ``NaN``.
    """

    _validate_window(window, "window")
    return series.rolling(window=window, min_periods=window).apply(
        _percentile_rank_current,
        raw=True,
    )


def atr_percentile(
    data: pd.DataFrame,
    atr_window: int = 14,
    percentile_window: int = 100,
) -> pd.Series:
    """Return rolling percentile rank of ATR percentage.

    Low values indicate compressed volatility relative to the trailing
    percentile window.
    """

    _validate_window(percentile_window, "percentile_window")
    atr_pct = atr_percentage(data, atr_window=atr_window)
    return rolling_percentile_rank(atr_pct, window=percentile_window)


def rolling_range_percentage(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """Return rolling high-low range as a percentage-point value of close.

    The result is ``100 * (rolling_high - rolling_low) / close``. Rows with
    insufficient lookback, missing close, or zero close return ``NaN``.
    """

    _validate_window(window, "window")
    _validate_columns(data, ("high", "low", "close"))
    rolling_high = data["high"].rolling(window=window, min_periods=window).max()
    rolling_low = data["low"].rolling(window=window, min_periods=window).min()
    close = data["close"].replace(0, np.nan)
    return 100.0 * (rolling_high - rolling_low) / close


def range_percentile(
    data: pd.DataFrame,
    range_window: int = 20,
    percentile_window: int = 100,
) -> pd.Series:
    """Return rolling percentile rank of rolling range percentage.

    Low values indicate compressed range relative to the trailing percentile
    window.
    """

    _validate_window(percentile_window, "percentile_window")
    range_pct = rolling_range_percentage(data, window=range_window)
    return rolling_percentile_rank(range_pct, window=percentile_window)


def prior_n_day_high(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """Return the rolling max high over the prior ``window`` sessions.

    The current row is excluded with a one-row shift to avoid self-reference in
    breakout detection.
    """

    _validate_window(window, "window")
    _validate_columns(data, ("high",))
    return data["high"].shift(1).rolling(window=window, min_periods=window).max()


def close_above_prior_high(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """Return whether close is greater than the prior N-day high.

    Rows where the prior high is unavailable return ``False``.
    """

    _validate_window(window, "window")
    _validate_columns(data, ("high", "close"))
    prior_high = prior_n_day_high(data, window=window)
    return (data["close"] > prior_high).fillna(False)


def return_sign_entropy(
    data: pd.DataFrame,
    window: int = 20,
    flat_threshold: float = 0.0,
) -> pd.Series:
    """Return rolling entropy of close-to-close return signs.

    Returns are measured in percentage points as ``100 * close.pct_change()``.
    ``flat_threshold`` is also interpreted as percentage points, so
    ``flat_threshold=0.05`` means +/-0.05%, not 5%.

    Return signs are bucketed as up, down, and flat. Entropy uses natural log,
    so values range from 0.0 for one observed bucket to ``ln(3)`` when up,
    down, and flat are equally represented. Rows without enough return-sign
    observations return ``NaN``.
    """

    _validate_window(window, "window")
    if flat_threshold < 0:
        raise ValueError("flat_threshold must be non-negative")

    _validate_columns(data, ("close",))
    return_pct = data["close"].pct_change() * 100.0
    signs = pd.Series(np.nan, index=data.index, dtype="float64")
    signs[return_pct > flat_threshold] = 1.0
    signs[return_pct < -flat_threshold] = -1.0
    signs[return_pct.abs() <= flat_threshold] = 0.0
    return signs.rolling(window=window, min_periods=window).apply(
        _entropy_from_signs,
        raw=True,
    )


def _percentile_rank_current(values: np.ndarray) -> float:
    """Rank the final value within a NaN-free rolling window."""

    if np.isnan(values).any():
        return np.nan

    current = values[-1]
    if len(values) == 1:
        return 1.0

    less = np.sum(values < current)
    equal = np.sum(values == current)
    average_zero_based_position = less + (equal - 1) / 2.0
    return float(average_zero_based_position / (len(values) - 1))


def _entropy_from_signs(values: np.ndarray) -> float:
    """Return natural-log entropy for a NaN-free sign-code window."""

    if np.isnan(values).any():
        return np.nan

    counts = np.array([np.sum(values == -1.0), np.sum(values == 0.0), np.sum(values == 1.0)])
    probabilities = counts[counts > 0] / len(values)
    return float(-np.sum(probabilities * np.log(probabilities)))


def _validate_window(window: int, name: str) -> None:
    """Validate that a rolling window is a positive integer."""

    if not isinstance(window, int) or window < 1:
        raise ValueError(f"{name} must be a positive integer")


def _validate_columns(data: pd.DataFrame, required_columns: Iterable[str]) -> None:
    """Validate that all required lowercase columns are present."""

    missing = [column for column in required_columns if column not in data.columns]
    if missing:
        missing_columns = ", ".join(missing)
        raise ValueError(f"missing required columns: {missing_columns}")
