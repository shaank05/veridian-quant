"""Unit tests for I1 RAWRS market-structure intelligence features."""

import numpy as np
import pandas as pd
import pytest

from veridian_quant.v2.intelligence.rawrs import (
    log_returns,
    multi_scale_energy_frame,
    rawrs_feature_frame,
    rolling_direction_change_rate,
    rolling_fft_dominant_period,
    rolling_fft_spectral_concentration,
    rolling_fft_spectral_entropy,
    rolling_return_energy,
)


EXPECTED_RAWRS_COLUMNS = {
    "rawrs_log_return",
    "rawrs_fft_spectral_concentration",
    "rawrs_fft_spectral_entropy",
    "rawrs_fft_dominant_period",
    "rawrs_micro_energy",
    "rawrs_meso_energy",
    "rawrs_macro_energy",
    "rawrs_micro_meso_energy_ratio",
    "rawrs_meso_macro_energy_ratio",
    "rawrs_direction_change_rate",
}


def test_log_returns_output_and_index_alignment() -> None:
    data = _price_frame([100.0, 105.0, 110.0])

    result = log_returns(data)

    expected = pd.Series(
        [np.nan, np.log(105.0 / 100.0), np.log(110.0 / 105.0)],
        index=data.index,
        name="close",
    )
    pd.testing.assert_series_equal(result, expected)


def test_missing_close_column_raises_value_error() -> None:
    data = pd.DataFrame({"open": [100.0, 101.0]})

    with pytest.raises(ValueError, match="missing required columns: close"):
        log_returns(data)


def test_input_dataframe_is_not_mutated() -> None:
    data = _price_frame([100.0, 101.0, 102.0, 103.0, 104.0])
    original = data.copy(deep=True)

    rawrs_feature_frame(
        data,
        fft_window=3,
        micro_window=2,
        meso_window=3,
        macro_window=4,
        direction_window=3,
    )

    pd.testing.assert_frame_equal(data, original)


def test_invalid_windows_raise_value_error() -> None:
    returns = pd.Series([0.01, -0.02, 0.03])

    with pytest.raises(ValueError, match="window must be a positive integer"):
        rolling_fft_spectral_concentration(returns, window=0)
    with pytest.raises(ValueError, match="window must be a positive integer"):
        rolling_fft_spectral_entropy(returns, window=-1)
    with pytest.raises(ValueError, match="window must be a positive integer"):
        rolling_fft_dominant_period(returns, window=1.5)
    with pytest.raises(ValueError, match="window must be a positive integer"):
        rolling_return_energy(returns, window=0)
    with pytest.raises(ValueError, match="micro_window must be a positive integer"):
        multi_scale_energy_frame(returns, micro_window=0)
    with pytest.raises(ValueError, match="window must be a positive integer"):
        rolling_direction_change_rate(returns, window=0)


def test_fft_concentration_range_is_zero_to_one_where_defined() -> None:
    returns = pd.Series(np.sin(np.arange(32, dtype="float64")))

    result = rolling_fft_spectral_concentration(returns, window=8)
    defined = result.dropna()

    assert not defined.empty
    assert ((defined >= 0.0) & (defined <= 1.0)).all()


def test_fft_entropy_range_is_zero_to_one_where_defined() -> None:
    returns = pd.Series(np.sin(np.arange(32, dtype="float64")))

    result = rolling_fft_spectral_entropy(returns, window=8)
    defined = result.dropna()

    assert not defined.empty
    assert ((defined >= 0.0) & (defined <= 1.0)).all()


def test_dominant_period_is_positive_where_defined() -> None:
    returns = pd.Series(np.sin(np.arange(32, dtype="float64")))

    result = rolling_fft_dominant_period(returns, window=8)
    defined = result.dropna()

    assert not defined.empty
    assert (defined > 0.0).all()


def test_zero_return_windows_return_nan_for_fft_power_features() -> None:
    returns = pd.Series([0.0] * 10)

    concentration = rolling_fft_spectral_concentration(returns, window=4)
    entropy = rolling_fft_spectral_entropy(returns, window=4)
    period = rolling_fft_dominant_period(returns, window=4)

    assert concentration.isna().all()
    assert entropy.isna().all()
    assert period.isna().all()


def test_multi_scale_energy_columns_exist_and_preserve_index() -> None:
    returns = pd.Series(
        [0.01, -0.01, 0.02, -0.02, 0.03],
        index=pd.Index(["a", "b", "c", "d", "e"], name="row"),
    )

    result = multi_scale_energy_frame(
        returns,
        micro_window=2,
        meso_window=3,
        macro_window=4,
    )

    assert set(result.columns) == {
        "rawrs_micro_energy",
        "rawrs_meso_energy",
        "rawrs_macro_energy",
        "rawrs_micro_meso_energy_ratio",
        "rawrs_meso_macro_energy_ratio",
    }
    assert result.index.equals(returns.index)


def test_energy_ratios_are_nan_when_denominator_is_zero_or_missing() -> None:
    returns = pd.Series([0.0, 0.0, 0.0, 0.0])

    result = multi_scale_energy_frame(
        returns,
        micro_window=1,
        meso_window=2,
        macro_window=3,
    )

    assert result["rawrs_micro_meso_energy_ratio"].isna().all()
    assert result["rawrs_meso_macro_energy_ratio"].isna().all()


def test_direction_change_rate_range_is_zero_to_one_where_defined() -> None:
    returns = pd.Series([0.01, -0.01, 0.02, 0.03, -0.02, 0.01])

    result = rolling_direction_change_rate(returns, window=4)
    defined = result.dropna()

    assert not defined.empty
    assert ((defined >= 0.0) & (defined <= 1.0)).all()


def test_rawrs_feature_frame_returns_all_expected_columns() -> None:
    data = _price_frame([100.0 + np.sin(index) for index in range(80)])

    result = rawrs_feature_frame(
        data,
        fft_window=8,
        micro_window=3,
        meso_window=5,
        macro_window=8,
        direction_window=5,
    )

    assert set(result.columns) == EXPECTED_RAWRS_COLUMNS
    assert result.index.equals(data.index)


def test_no_future_leakage_when_future_rows_change() -> None:
    data = _price_frame([100.0 + np.sin(index / 2) for index in range(50)])
    modified = data.copy(deep=True)
    modified.loc[modified.index[-5:], "close"] = [150.0, 80.0, 160.0, 70.0, 170.0]

    baseline = rawrs_feature_frame(
        data,
        fft_window=8,
        micro_window=3,
        meso_window=5,
        macro_window=8,
        direction_window=5,
    )
    changed = rawrs_feature_frame(
        modified,
        fft_window=8,
        micro_window=3,
        meso_window=5,
        macro_window=8,
        direction_window=5,
    )

    pd.testing.assert_frame_equal(baseline.iloc[:44], changed.iloc[:44])


def test_no_topology_or_regime_labels_are_produced_in_phase_30b() -> None:
    data = _price_frame([100.0 + np.sin(index) for index in range(80)])

    result = rawrs_feature_frame(
        data,
        fft_window=8,
        micro_window=3,
        meso_window=5,
        macro_window=8,
        direction_window=5,
    )

    forbidden_terms = ("topology", "regime", "label")
    assert not any(
        any(term in column for term in forbidden_terms)
        for column in result.columns
    )


def _price_frame(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {"close": closes},
        index=pd.Index(pd.date_range("2026-01-01", periods=len(closes)), name="date"),
    )
