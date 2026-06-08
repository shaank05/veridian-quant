"""Unit tests for Veridian Quant v2 technical feature calculations."""

import pandas as pd
import pytest

from veridian_quant.v2.features.technical import (
    atr,
    price_zscore,
    rolling_mean_close,
    rolling_std_close,
    true_range,
)


def test_rolling_mean_close_returns_expected_series() -> None:
    data = pd.DataFrame({"close": [10.0, 12.0, 14.0, 16.0]})

    result = rolling_mean_close(data, window=3)

    expected = pd.Series([float("nan"), float("nan"), 12.0, 14.0])
    pd.testing.assert_series_equal(result, expected)


def test_rolling_std_close_returns_expected_series() -> None:
    data = pd.DataFrame({"close": [10.0, 12.0, 14.0, 16.0]})

    result = rolling_std_close(data, window=3)

    expected = data["close"].rolling(window=3, min_periods=3).std()
    pd.testing.assert_series_equal(result, expected)


def test_price_zscore_returns_expected_series() -> None:
    data = pd.DataFrame({"close": [10.0, 12.0, 14.0, 18.0]})

    result = price_zscore(data, window=3)

    mean = data["close"].rolling(window=3, min_periods=3).mean()
    std = data["close"].rolling(window=3, min_periods=3).std()
    expected = (data["close"] - mean) / std
    pd.testing.assert_series_equal(result, expected)


def test_price_zscore_returns_nan_for_zero_standard_deviation() -> None:
    data = pd.DataFrame({"close": [10.0, 10.0, 10.0, 10.0]})

    result = price_zscore(data, window=3)

    assert result.isna().all()


def test_true_range_and_atr_return_expected_series() -> None:
    data = pd.DataFrame(
        {
            "high": [12.0, 15.0, 14.0, 18.0],
            "low": [9.0, 11.0, 10.0, 13.0],
            "close": [10.0, 14.0, 11.0, 17.0],
        }
    )

    true_range_result = true_range(data)
    atr_result = atr(data, window=3)

    expected_true_range = pd.Series([3.0, 5.0, 4.0, 7.0])
    expected_atr = expected_true_range.rolling(window=3, min_periods=3).mean()
    pd.testing.assert_series_equal(true_range_result, expected_true_range)
    pd.testing.assert_series_equal(atr_result, expected_atr)


def test_feature_functions_do_not_mutate_input_dataframe() -> None:
    data = pd.DataFrame(
        {
            "open": [9.0, 11.0, 13.0],
            "high": [12.0, 14.0, 16.0],
            "low": [8.0, 10.0, 12.0],
            "close": [10.0, 12.0, 14.0],
            "volume": [100, 110, 120],
        }
    )
    original = data.copy(deep=True)

    rolling_mean_close(data, window=2)
    rolling_std_close(data, window=2)
    price_zscore(data, window=2)
    true_range(data)
    atr(data, window=2)

    pd.testing.assert_frame_equal(data, original)


def test_missing_required_atr_columns_raises_clear_error() -> None:
    data = pd.DataFrame({"high": [12.0], "close": [10.0]})

    with pytest.raises(ValueError, match="missing required columns: low"):
        atr(data, window=2)
