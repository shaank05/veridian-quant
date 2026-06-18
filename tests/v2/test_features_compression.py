"""Unit tests for S4 compression and breakout feature calculations."""

import numpy as np
import pandas as pd
import pytest

from veridian_quant.v2.features.compression import (
    atr_percentage,
    atr_percentile,
    close_above_prior_high,
    prior_n_day_high,
    range_percentile,
    return_sign_entropy,
    rolling_percentile_rank,
    rolling_range_percentage,
)
from veridian_quant.v2.features.technical import atr


def _sample_ohlc() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [9.0, 11.0, 13.0, 15.0, 17.0],
            "high": [12.0, 14.0, 16.0, 18.0, 20.0],
            "low": [8.0, 10.0, 12.0, 14.0, 16.0],
            "close": [10.0, 12.0, 14.0, 16.0, 18.0],
            "volume": [100, 110, 120, 130, 140],
        },
        index=pd.Index(pd.date_range("2026-01-01", periods=5), name="date"),
    )


def test_compression_feature_functions_do_not_mutate_input_dataframe() -> None:
    data = _sample_ohlc()
    original = data.copy(deep=True)

    atr_percentage(data, atr_window=2)
    atr_percentile(data, atr_window=2, percentile_window=2)
    rolling_range_percentage(data, window=2)
    range_percentile(data, range_window=2, percentile_window=2)
    prior_n_day_high(data, window=2)
    close_above_prior_high(data, window=2)
    return_sign_entropy(data, window=2)

    pd.testing.assert_frame_equal(data, original)


def test_missing_required_columns_raise_clear_error() -> None:
    data = pd.DataFrame({"high": [12.0], "close": [10.0]})

    with pytest.raises(ValueError, match="missing required columns: low"):
        atr_percentage(data, atr_window=2)

    with pytest.raises(ValueError, match="missing required columns: close"):
        close_above_prior_high(pd.DataFrame({"high": [12.0]}), window=2)


def test_insufficient_lookback_returns_nan_or_false() -> None:
    data = _sample_ohlc().iloc[:2]

    assert atr_percentage(data, atr_window=3).isna().all()
    assert rolling_range_percentage(data, window=3).isna().all()
    assert prior_n_day_high(data, window=2).isna().all()
    assert not close_above_prior_high(data, window=2).any()
    assert return_sign_entropy(data, window=2).isna().all()


def test_atr_percentage_returns_percentage_points_not_raw_fraction() -> None:
    data = _sample_ohlc()

    result = atr_percentage(data, atr_window=3)

    expected = 100.0 * atr(data, window=3) / data["close"]
    raw_fraction = atr(data, window=3) / data["close"]
    pd.testing.assert_series_equal(result, expected)
    assert result.dropna().iloc[0] == pytest.approx(raw_fraction.dropna().iloc[0] * 100.0)


def test_rolling_percentile_rank_simple_increasing_series() -> None:
    series = pd.Series([1.0, 2.0, 3.0, 4.0])

    result = rolling_percentile_rank(series, window=3)

    expected = pd.Series([np.nan, np.nan, 1.0, 1.0])
    pd.testing.assert_series_equal(result, expected)


def test_rolling_percentile_rank_preserves_index_alignment() -> None:
    index = pd.Index(["a", "b", "c", "d"], name="row")
    series = pd.Series([4.0, 3.0, 2.0, 1.0], index=index)

    result = rolling_percentile_rank(series, window=2)

    assert result.index.equals(index)


def test_prior_n_day_high_excludes_current_row() -> None:
    data = pd.DataFrame({"high": [10.0, 11.0, 12.0, 50.0]})

    result = prior_n_day_high(data, window=3)

    expected = pd.Series([np.nan, np.nan, np.nan, 12.0], name="high")
    pd.testing.assert_series_equal(result, expected)


def test_close_above_prior_high_detects_only_true_breakout() -> None:
    data = pd.DataFrame(
        {
            "high": [10.0, 11.0, 12.0, 13.0, 14.0],
            "close": [9.0, 10.0, 11.0, 12.0, 12.0],
        }
    )

    result = close_above_prior_high(data, window=3)

    expected = pd.Series([False, False, False, False, False])
    pd.testing.assert_series_equal(result, expected)

    breakout_data = data.copy()
    breakout_data.loc[4, "close"] = 13.5
    breakout_result = close_above_prior_high(breakout_data, window=3)
    assert breakout_result.tolist() == [False, False, False, False, True]


def test_rolling_range_percentage_returns_percentage_points_not_raw_fraction() -> None:
    data = _sample_ohlc()

    result = rolling_range_percentage(data, window=3)

    rolling_high = data["high"].rolling(window=3, min_periods=3).max()
    rolling_low = data["low"].rolling(window=3, min_periods=3).min()
    expected = 100.0 * (rolling_high - rolling_low) / data["close"]
    raw_fraction = (rolling_high - rolling_low) / data["close"]
    pd.testing.assert_series_equal(result, expected)
    assert result.dropna().iloc[0] == pytest.approx(raw_fraction.dropna().iloc[0] * 100.0)


def test_range_percentile_returns_low_value_for_compressed_range() -> None:
    data = pd.DataFrame(
        {
            "high": [20.0, 20.0, 20.0, 11.0],
            "low": [10.0, 10.0, 10.0, 10.0],
            "close": [10.0, 10.0, 10.0, 10.0],
        }
    )

    result = range_percentile(data, range_window=1, percentile_window=4)

    assert result.iloc[-1] == pytest.approx(0.0)


def test_atr_percentile_returns_low_value_for_compressed_volatility() -> None:
    data = pd.DataFrame(
        {
            "high": [20.0, 20.0, 20.0, 11.0],
            "low": [10.0, 10.0, 10.0, 10.0],
            "close": [10.0, 10.0, 10.0, 10.0],
        }
    )

    result = atr_percentile(data, atr_window=1, percentile_window=4)

    assert result.iloc[-1] == pytest.approx(0.0)


def test_return_sign_entropy_lower_for_one_sided_than_mixed_movement() -> None:
    one_sided = pd.DataFrame({"close": [10.0, 11.0, 12.0, 13.0, 14.0]})
    mixed = pd.DataFrame({"close": [10.0, 11.0, 10.0, 10.0, 11.0]})

    one_sided_entropy = return_sign_entropy(one_sided, window=4).iloc[-1]
    mixed_entropy = return_sign_entropy(mixed, window=4).iloc[-1]

    assert one_sided_entropy == pytest.approx(0.0)
    assert mixed_entropy > one_sided_entropy


def test_return_sign_entropy_treats_flat_threshold_as_percentage_points() -> None:
    data = pd.DataFrame({"close": [100.0, 100.04, 99.99, 100.01]})

    result = return_sign_entropy(data, window=3, flat_threshold=0.05)

    assert result.iloc[-1] == pytest.approx(0.0)


def test_compression_functions_preserve_index_alignment() -> None:
    data = _sample_ohlc()

    functions = [
        atr_percentage(data, atr_window=2),
        atr_percentile(data, atr_window=2, percentile_window=2),
        rolling_range_percentage(data, window=2),
        range_percentile(data, range_window=2, percentile_window=2),
        prior_n_day_high(data, window=2),
        close_above_prior_high(data, window=2),
        return_sign_entropy(data, window=2),
    ]

    for result in functions:
        assert result.index.equals(data.index)
