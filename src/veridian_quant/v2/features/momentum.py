"""Leakage-safe momentum feature calculations for S5 research.

The functions in this module are pure, deterministic pandas helpers. They use
only the current and prior rows, preserve insufficient-lookback ``NaN`` values,
and do not mutate caller-provided data. They calculate features only; they do
not generate S5 signals, rankings, or portfolio decisions.
"""

from collections.abc import Iterable

import numpy as np
import pandas as pd


def period_return(
    data: pd.DataFrame,
    window: int,
    price_col: str = "close",
    output_col: str | None = None,
) -> pd.Series:
    """Return the simple price return over ``window`` prior rows.

    The result is ``price / price.shift(window) - 1``. Rows without the full
    lookback remain ``NaN``.
    """

    _validate_positive_int(window, "window")
    _validate_columns(data, (price_col,))
    result = data[price_col] / data[price_col].shift(window) - 1.0
    return result.rename(output_col or f"return_{window}d")


def skip_period_return(
    data: pd.DataFrame,
    window: int,
    skip: int,
    price_col: str = "close",
    output_col: str | None = None,
) -> pd.Series:
    """Return momentum over ``window`` rows while excluding recent rows.

    The result is ``price.shift(skip) / price.shift(window + skip) - 1``.
    Setting ``skip=0`` is equivalent to :func:`period_return`.
    """

    _validate_positive_int(window, "window")
    _validate_non_negative_int(skip, "skip")
    _validate_columns(data, (price_col,))
    result = (
        data[price_col].shift(skip) / data[price_col].shift(window + skip) - 1.0
    )
    return result.rename(output_col or f"skip_return_{window}d_{skip}d")


def rolling_realized_volatility(
    data: pd.DataFrame,
    window: int,
    price_col: str = "close",
    annualize: bool = False,
    trading_days: int = 252,
    output_col: str | None = None,
) -> pd.Series:
    """Return rolling sample standard deviation of simple daily returns.

    When ``annualize`` is true, volatility is multiplied by
    ``sqrt(trading_days)``. Initial rows and windows containing missing returns
    remain ``NaN``.
    """

    _validate_int_greater_than_one(window, "window")
    _validate_positive_int(trading_days, "trading_days")
    _validate_columns(data, (price_col,))

    daily_return = data[price_col].pct_change(fill_method=None)
    result = daily_return.rolling(window=window, min_periods=window).std()
    if annualize:
        result = result * np.sqrt(trading_days)
    return result.rename(output_col or f"realized_vol_{window}d")


def volatility_adjusted_momentum(
    data: pd.DataFrame,
    return_window: int,
    vol_window: int,
    price_col: str = "close",
    annualize_vol: bool = False,
    output_col: str | None = None,
) -> pd.Series:
    """Return period momentum divided by rolling realized volatility.

    Rows with missing or zero realized volatility return ``NaN`` rather than
    infinity.
    """

    _validate_positive_int(return_window, "return_window")
    _validate_int_greater_than_one(vol_window, "vol_window")
    _validate_columns(data, (price_col,))

    momentum = period_return(data, return_window, price_col=price_col)
    volatility = rolling_realized_volatility(
        data,
        vol_window,
        price_col=price_col,
        annualize=annualize_vol,
    ).replace(0.0, np.nan)
    result = momentum / volatility
    return result.rename(
        output_col or f"vol_adj_return_{return_window}d_{vol_window}d"
    )


def sma_distance(
    data: pd.DataFrame,
    window: int,
    price_col: str = "close",
    output_col: str | None = None,
) -> pd.Series:
    """Return price distance from its trailing simple moving average.

    The result is ``price / rolling_mean(price, window) - 1``.
    """

    _validate_positive_int(window, "window")
    _validate_columns(data, (price_col,))
    moving_average = data[price_col].rolling(
        window=window,
        min_periods=window,
    ).mean()
    result = data[price_col] / moving_average.replace(0.0, np.nan) - 1.0
    return result.rename(output_col or f"sma_distance_{window}d")


def high_proximity(
    data: pd.DataFrame,
    window: int,
    price_col: str = "close",
    high_col: str = "high",
    use_high: bool = True,
    output_col: str | None = None,
) -> pd.Series:
    """Return close divided by the current trailing rolling high.

    If ``use_high`` is true, the denominator is the rolling maximum of
    ``high_col``; otherwise it is the rolling maximum of ``price_col``. A value
    near one means close is near the trailing high.
    """

    _validate_positive_int(window, "window")
    required_columns = (price_col, high_col) if use_high else (price_col,)
    _validate_columns(data, required_columns)

    rolling_source = data[high_col] if use_high else data[price_col]
    rolling_high = rolling_source.rolling(
        window=window,
        min_periods=window,
    ).max()
    result = data[price_col] / rolling_high.replace(0.0, np.nan)
    return result.rename(output_col or f"high_proximity_{window}d")


def relative_strength_vs_benchmark(
    data: pd.DataFrame,
    window: int,
    price_col: str = "close",
    benchmark_col: str = "benchmark_close",
    output_col: str | None = None,
) -> pd.Series:
    """Return asset simple return minus benchmark simple return."""

    _validate_positive_int(window, "window")
    _validate_columns(data, (price_col, benchmark_col))
    asset_return = period_return(data, window, price_col=price_col)
    benchmark_return = period_return(data, window, price_col=benchmark_col)
    result = asset_return - benchmark_return
    return result.rename(output_col or f"relative_strength_{window}d")


def add_momentum_feature_frame(
    data: pd.DataFrame,
    price_col: str = "close",
    high_col: str = "high",
    benchmark_col: str = "benchmark_close",
) -> pd.DataFrame:
    """Return a copy of ``data`` with the common S5 research features.

    Benchmark-relative strength is attached only when ``benchmark_col`` is
    present. The helper does not create signals, ranks, or portfolio decisions.
    """

    _validate_columns(data, (price_col, high_col))
    result = data.copy()
    result["return_63d"] = period_return(data, 63, price_col=price_col)
    result["return_126d"] = period_return(data, 126, price_col=price_col)
    result["return_252d"] = period_return(data, 252, price_col=price_col)
    result["skip_return_126d_21d"] = skip_period_return(
        data,
        126,
        21,
        price_col=price_col,
    )
    result["realized_vol_63d"] = rolling_realized_volatility(
        data,
        63,
        price_col=price_col,
    )
    result["vol_adj_return_126d_63d"] = volatility_adjusted_momentum(
        data,
        126,
        63,
        price_col=price_col,
    )
    result["sma_distance_200d"] = sma_distance(data, 200, price_col=price_col)
    result["high_proximity_252d"] = high_proximity(
        data,
        252,
        price_col=price_col,
        high_col=high_col,
    )
    if benchmark_col in data.columns:
        result["relative_strength_126d"] = relative_strength_vs_benchmark(
            data,
            126,
            price_col=price_col,
            benchmark_col=benchmark_col,
        )
    return result


def _validate_positive_int(value: int, name: str) -> None:
    """Validate a strictly positive integer parameter."""

    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")


def _validate_int_greater_than_one(value: int, name: str) -> None:
    """Validate an integer parameter greater than one."""

    if isinstance(value, bool) or not isinstance(value, int) or value <= 1:
        raise ValueError(f"{name} must be an integer greater than 1")


def _validate_non_negative_int(value: int, name: str) -> None:
    """Validate a non-negative integer parameter."""

    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def _validate_columns(data: pd.DataFrame, required_columns: Iterable[str]) -> None:
    """Validate that all requested columns exist."""

    missing = [column for column in required_columns if column not in data.columns]
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")
