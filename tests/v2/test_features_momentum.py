"""Tests for leakage-safe S5 momentum feature utilities."""

import numpy as np
import pandas as pd
import pytest

from veridian_quant.v2.features.momentum import (
    add_momentum_feature_frame,
    high_proximity,
    period_return,
    relative_strength_vs_benchmark,
    rolling_realized_volatility,
    skip_period_return,
    sma_distance,
    volatility_adjusted_momentum,
)


def test_period_return_known_sequence_and_insufficient_lookback() -> None:
    data = pd.DataFrame({"close": [100.0, 110.0, 121.0, 133.1]})

    result = period_return(data, window=2)

    expected = pd.Series(
        [np.nan, np.nan, 0.21, 0.21],
        name="return_2d",
    )
    pd.testing.assert_series_equal(result, expected)


def test_period_return_supports_price_and_output_columns() -> None:
    data = pd.DataFrame({"adjusted_close": [10.0, 12.0]})

    result = period_return(
        data,
        window=1,
        price_col="adjusted_close",
        output_col="custom_return",
    )

    expected = pd.Series([np.nan, 0.2], name="custom_return")
    pd.testing.assert_series_equal(result, expected)


def test_period_return_validates_missing_column() -> None:
    with pytest.raises(ValueError, match="missing required columns: close"):
        period_return(pd.DataFrame({"open": [1.0]}), window=1)


@pytest.mark.parametrize("window", [0, -1, 1.5, True])
def test_period_return_validates_window(window: object) -> None:
    with pytest.raises(ValueError, match="window must be a positive integer"):
        period_return(pd.DataFrame({"close": [1.0]}), window=window)  # type: ignore[arg-type]


def test_skip_period_return_known_sequence() -> None:
    data = pd.DataFrame({"close": [100.0, 110.0, 121.0, 133.1, 146.41]})

    result = skip_period_return(data, window=2, skip=1)

    expected = pd.Series(
        [np.nan, np.nan, np.nan, 0.21, 0.21],
        name="skip_return_2d_1d",
    )
    pd.testing.assert_series_equal(result, expected)


def test_skip_period_return_zero_skip_matches_period_return() -> None:
    data = pd.DataFrame({"close": [10.0, 11.0, 12.0, 13.0]})

    actual = skip_period_return(data, window=2, skip=0)
    expected = period_return(data, window=2)

    pd.testing.assert_series_equal(actual, expected, check_names=False)


@pytest.mark.parametrize(
    ("window", "skip", "message"),
    [
        (0, 0, "window must be a positive integer"),
        (2, -1, "skip must be a non-negative integer"),
        (2, 1.5, "skip must be a non-negative integer"),
    ],
)
def test_skip_period_return_validates_parameters(
    window: object,
    skip: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        skip_period_return(  # type: ignore[arg-type]
            pd.DataFrame({"close": [1.0]}),
            window=window,
            skip=skip,
        )


def test_rolling_realized_volatility_known_sequence_and_nan_shape() -> None:
    data = pd.DataFrame({"close": [100.0, 110.0, 99.0, 108.9]})

    result = rolling_realized_volatility(data, window=2)

    expected_value = np.std([0.1, -0.1], ddof=1)
    expected = pd.Series(
        [np.nan, np.nan, expected_value, expected_value],
        name="realized_vol_2d",
    )
    pd.testing.assert_series_equal(result, expected)


def test_rolling_realized_volatility_annualizes() -> None:
    data = pd.DataFrame({"close": [100.0, 110.0, 99.0, 108.9]})

    raw = rolling_realized_volatility(data, window=2)
    annualized = rolling_realized_volatility(
        data,
        window=2,
        annualize=True,
        trading_days=252,
    )

    pd.testing.assert_series_equal(
        annualized,
        (raw * np.sqrt(252)).rename("realized_vol_2d"),
    )


@pytest.mark.parametrize(
    ("window", "trading_days", "message"),
    [
        (1, 252, "window must be an integer greater than 1"),
        (0, 252, "window must be an integer greater than 1"),
        (2, 0, "trading_days must be a positive integer"),
        (2, -1, "trading_days must be a positive integer"),
    ],
)
def test_rolling_realized_volatility_validates_parameters(
    window: int,
    trading_days: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        rolling_realized_volatility(
            pd.DataFrame({"close": [1.0, 2.0]}),
            window=window,
            trading_days=trading_days,
        )


def test_volatility_adjusted_momentum_zero_volatility_is_nan() -> None:
    data = pd.DataFrame({"close": [100.0, 100.0, 100.0, 100.0]})

    result = volatility_adjusted_momentum(data, return_window=2, vol_window=2)

    assert result.isna().all()


def test_volatility_adjusted_momentum_expected_finite_value() -> None:
    data = pd.DataFrame({"close": [100.0, 110.0, 99.0, 118.8]})

    result = volatility_adjusted_momentum(data, return_window=2, vol_window=2)

    expected_momentum = 118.8 / 110.0 - 1.0
    expected_volatility = np.std([-0.1, 0.2], ddof=1)
    assert result.iloc[3] == pytest.approx(expected_momentum / expected_volatility)
    assert np.isfinite(result.iloc[3])


@pytest.mark.parametrize(
    ("return_window", "vol_window", "message"),
    [
        (0, 2, "return_window must be a positive integer"),
        (2, 1, "vol_window must be an integer greater than 1"),
    ],
)
def test_volatility_adjusted_momentum_validates_windows(
    return_window: int,
    vol_window: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        volatility_adjusted_momentum(
            pd.DataFrame({"close": [1.0, 2.0]}),
            return_window=return_window,
            vol_window=vol_window,
        )


def test_sma_distance_known_sequence_and_insufficient_lookback() -> None:
    data = pd.DataFrame({"close": [1.0, 2.0, 3.0]})

    result = sma_distance(data, window=2)

    expected = pd.Series(
        [np.nan, 2.0 / 1.5 - 1.0, 3.0 / 2.5 - 1.0],
        name="sma_distance_2d",
    )
    pd.testing.assert_series_equal(result, expected)


def test_sma_distance_validates_window() -> None:
    with pytest.raises(ValueError, match="window must be a positive integer"):
        sma_distance(pd.DataFrame({"close": [1.0]}), window=0)


def test_high_proximity_uses_high_column() -> None:
    data = pd.DataFrame(
        {
            "close": [8.0, 9.0, 10.0],
            "high": [10.0, 12.0, 11.0],
        }
    )

    result = high_proximity(data, window=2)

    expected = pd.Series(
        [np.nan, 9.0 / 12.0, 10.0 / 12.0],
        name="high_proximity_2d",
    )
    pd.testing.assert_series_equal(result, expected)


def test_high_proximity_can_use_close_instead_of_high() -> None:
    data = pd.DataFrame({"close": [8.0, 9.0, 10.0]})

    result = high_proximity(data, window=2, use_high=False)

    expected = pd.Series([np.nan, 1.0, 1.0], name="high_proximity_2d")
    pd.testing.assert_series_equal(result, expected)


def test_high_proximity_requires_high_when_requested() -> None:
    with pytest.raises(ValueError, match="missing required columns: high"):
        high_proximity(pd.DataFrame({"close": [1.0, 2.0]}), window=2)


def test_relative_strength_vs_benchmark_known_returns() -> None:
    data = pd.DataFrame(
        {
            "close": [100.0, 110.0, 121.0],
            "benchmark_close": [100.0, 105.0, 110.25],
        }
    )

    result = relative_strength_vs_benchmark(data, window=2)

    expected = pd.Series(
        [np.nan, np.nan, 0.21 - 0.1025],
        name="relative_strength_2d",
    )
    pd.testing.assert_series_equal(result, expected)


def test_relative_strength_requires_benchmark_column() -> None:
    with pytest.raises(
        ValueError,
        match="missing required columns: benchmark_close",
    ):
        relative_strength_vs_benchmark(
            pd.DataFrame({"close": [1.0, 2.0]}),
            window=1,
        )


def _feature_input(rows: int = 300) -> pd.DataFrame:
    index = pd.date_range("2020-01-01", periods=rows, freq="D", name="date")
    close = 100.0 + np.linspace(0.0, 80.0, rows) + np.sin(np.arange(rows) / 7.0)
    return pd.DataFrame(
        {
            "close": close,
            "high": close + 1.0,
            "benchmark_close": 100.0 + np.linspace(0.0, 40.0, rows),
        },
        index=index,
    )


def test_add_momentum_feature_frame_adds_expected_columns_and_preserves_shape() -> None:
    data = _feature_input()

    result = add_momentum_feature_frame(data)

    expected_columns = {
        "return_63d",
        "return_126d",
        "return_252d",
        "skip_return_126d_21d",
        "realized_vol_63d",
        "vol_adj_return_126d_63d",
        "sma_distance_200d",
        "high_proximity_252d",
        "relative_strength_126d",
    }
    assert expected_columns.issubset(result.columns)
    assert len(result) == len(data)
    pd.testing.assert_index_equal(result.index, data.index)


def test_add_momentum_feature_frame_omits_optional_benchmark_feature() -> None:
    data = _feature_input().drop(columns="benchmark_close")

    result = add_momentum_feature_frame(data)

    assert "relative_strength_126d" not in result.columns


def test_momentum_features_do_not_mutate_input() -> None:
    data = _feature_input()
    original = data.copy(deep=True)

    period_return(data, 63)
    skip_period_return(data, 126, 21)
    rolling_realized_volatility(data, 63)
    volatility_adjusted_momentum(data, 126, 63)
    sma_distance(data, 200)
    high_proximity(data, 252)
    relative_strength_vs_benchmark(data, 126)
    add_momentum_feature_frame(data)

    pd.testing.assert_frame_equal(data, original)


def test_no_future_leakage_when_future_prices_change() -> None:
    data = _feature_input()
    changed = data.copy(deep=True)
    cutoff = 260
    changed.iloc[cutoff + 1 :, changed.columns.get_loc("close")] *= 10.0
    changed.iloc[cutoff + 1 :, changed.columns.get_loc("high")] *= 20.0
    changed.iloc[cutoff + 1 :, changed.columns.get_loc("benchmark_close")] *= 5.0

    baseline_features = add_momentum_feature_frame(data)
    changed_features = add_momentum_feature_frame(changed)

    pd.testing.assert_frame_equal(
        baseline_features.iloc[: cutoff + 1],
        changed_features.iloc[: cutoff + 1],
    )


def test_early_rows_remain_nan_without_backfill() -> None:
    result = add_momentum_feature_frame(_feature_input())

    assert result.loc[:, "return_63d"].iloc[:63].isna().all()
    assert result.loc[:, "return_126d"].iloc[:126].isna().all()
    assert result.loc[:, "return_252d"].iloc[:252].isna().all()
    assert result.loc[:, "skip_return_126d_21d"].iloc[:147].isna().all()
    assert result.loc[:, "realized_vol_63d"].iloc[:63].isna().all()
    assert result.loc[:, "sma_distance_200d"].iloc[:199].isna().all()
    assert result.loc[:, "high_proximity_252d"].iloc[:251].isna().all()
