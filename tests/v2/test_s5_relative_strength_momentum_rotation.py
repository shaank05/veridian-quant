"""Unit tests for S5 momentum candidate signal generation."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from veridian_quant.v2.data.models import SignalType
from veridian_quant.v2.features.momentum import (
    period_return,
    rolling_realized_volatility,
    sma_distance,
    volatility_adjusted_momentum,
)
from veridian_quant.v2.strategies.s5_relative_strength_momentum_rotation import (
    S5_DUAL_MOMENTUM_63_126D_V1,
    S5_SIMPLE_RS_126D_V1,
    S5_VOL_ADJUSTED_RS_V1,
    STRATEGY_NAME,
    S5MomentumConfig,
    S5RelativeStrengthMomentumRotationStrategy,
    generate_s5_momentum_signals,
)


def test_simple_rs_generates_after_126d_and_200d_lookback() -> None:
    data = _rising_frame()

    signals = _signals(S5_SIMPLE_RS_126D_V1, data)

    assert len(signals) == 1
    assert signals[0].generated_on == data.loc[199, "date"].date()


def test_simple_rs_does_not_signal_before_sufficient_trend_lookback() -> None:
    signals = _signals(S5_SIMPLE_RS_126D_V1, _rising_frame(rows=199))

    assert signals == ()


def test_simple_rs_does_not_signal_when_trend_filter_fails() -> None:
    signals = _signals(S5_SIMPLE_RS_126D_V1, _falling_frame())

    assert signals == ()


def test_simple_rs_metadata_and_rank_score() -> None:
    data = _rising_frame()

    signal = _signals(S5_SIMPLE_RS_126D_V1, data)[0]
    metadata = signal.metadata

    assert metadata["variant"] == S5_SIMPLE_RS_126D_V1
    assert metadata["return_126d"] == pytest.approx(
        period_return(data, 126).iloc[199]
    )
    assert metadata["sma_distance_200d"] == pytest.approx(
        sma_distance(data, 200).iloc[199]
    )
    assert metadata["rank_score"] == pytest.approx(metadata["return_126d"])
    assert metadata["trend_filter_passed"] is True


def test_dual_momentum_generates_when_both_returns_are_positive() -> None:
    signals = _signals(S5_DUAL_MOMENTUM_63_126D_V1, _rising_frame())

    assert len(signals) == 1
    assert signals[0].metadata["return_63d"] > 0.0
    assert signals[0].metadata["return_126d"] > 0.0


def test_dual_momentum_rank_score_is_equal_weight_average() -> None:
    signal = _signals(S5_DUAL_MOMENTUM_63_126D_V1, _rising_frame())[0]
    metadata = signal.metadata

    expected = 0.5 * metadata["return_63d"] + 0.5 * metadata["return_126d"]
    assert metadata["rank_score"] == pytest.approx(expected)
    assert metadata["dual_momentum_rule"] == "both_returns_positive"


def test_dual_momentum_requires_both_returns_positive() -> None:
    config = S5MomentumConfig(
        variant=S5_DUAL_MOMENTUM_63_126D_V1,
        enable_trend_filter=False,
    )

    signals = generate_s5_momentum_signals("TEST", _falling_frame(), config)

    assert signals == ()


def test_dual_momentum_metadata_includes_both_returns() -> None:
    metadata = _signals(S5_DUAL_MOMENTUM_63_126D_V1, _rising_frame())[0].metadata

    assert metadata["return_63d"] is not None
    assert metadata["return_126d"] is not None


def test_vol_adjusted_variant_generates_with_valid_return_and_volatility() -> None:
    signals = _signals(S5_VOL_ADJUSTED_RS_V1, _rising_frame())

    assert len(signals) == 1
    assert signals[0].metadata["return_126d"] > 0.0
    assert signals[0].metadata["realized_vol_63d"] > 0.0


def test_vol_adjusted_rank_score_matches_feature() -> None:
    data = _rising_frame()

    metadata = _signals(S5_VOL_ADJUSTED_RS_V1, data)[0].metadata

    expected = volatility_adjusted_momentum(data, 126, 63).iloc[199]
    assert metadata["rank_score"] == pytest.approx(expected)
    assert metadata["vol_adj_return_126d_63d"] == pytest.approx(expected)


def test_vol_adjusted_variant_rejects_zero_volatility() -> None:
    data = _constant_frame()
    config = S5MomentumConfig(
        variant=S5_VOL_ADJUSTED_RS_V1,
        enable_trend_filter=False,
    )

    signals = generate_s5_momentum_signals("TEST", data, config)

    assert signals == ()


def test_vol_adjusted_metadata_includes_return_volatility_and_score() -> None:
    metadata = _signals(S5_VOL_ADJUSTED_RS_V1, _rising_frame())[0].metadata

    assert metadata["return_126d"] is not None
    assert metadata["realized_vol_63d"] is not None
    assert metadata["vol_adj_return_126d_63d"] is not None
    assert metadata["rank_score"] == metadata["vol_adj_return_126d_63d"]


def test_unknown_variant_raises_value_error() -> None:
    config = S5MomentumConfig(variant="UNKNOWN")

    with pytest.raises(ValueError, match="unknown S5 strategy variant"):
        generate_s5_momentum_signals("TEST", _rising_frame(), config)


def test_missing_price_column_raises_clear_error() -> None:
    data = _rising_frame().drop(columns="close")

    with pytest.raises(ValueError, match="missing required columns: close"):
        generate_s5_momentum_signals("TEST", data)


def test_missing_date_column_raises_clear_error() -> None:
    data = _rising_frame().drop(columns="date")

    with pytest.raises(ValueError, match="missing required columns: date or timestamp"):
        generate_s5_momentum_signals("TEST", data)


def test_invalid_min_rank_score_raises_value_error() -> None:
    config = S5MomentumConfig(min_rank_score=np.nan)

    with pytest.raises(ValueError, match="min_rank_score must be finite"):
        generate_s5_momentum_signals("TEST", _rising_frame(), config)


def test_default_suppresses_consecutive_qualifying_signals() -> None:
    signals = _signals(S5_SIMPLE_RS_126D_V1, _rising_frame())

    assert len(signals) == 1


def test_allow_repeated_signals_emits_each_qualifying_day() -> None:
    config = S5MomentumConfig(
        variant=S5_SIMPLE_RS_126D_V1,
        allow_repeated_signals=True,
    )

    signals = generate_s5_momentum_signals("TEST", _rising_frame(), config)

    assert len(signals) == 31
    assert signals[0].generated_on < signals[-1].generated_on


def test_future_rows_do_not_change_prior_signal_or_metadata() -> None:
    data = _rising_frame()
    changed = data.copy(deep=True)
    signal_date = data.loc[199, "date"].date()
    changed.loc[200:, "close"] *= 10.0

    baseline = _signal_by_date(_signals(S5_VOL_ADJUSTED_RS_V1, data), signal_date)
    altered = _signal_by_date(_signals(S5_VOL_ADJUSTED_RS_V1, changed), signal_date)

    assert baseline is not None
    assert altered is not None
    assert baseline.signal_type == altered.signal_type
    assert dict(baseline.metadata) == dict(altered.metadata)


def test_generated_dates_align_with_input_dates() -> None:
    data = _rising_frame()
    input_dates = set(data["date"].dt.date)

    signals = _signals(S5_SIMPLE_RS_126D_V1, data)

    assert all(signal.generated_on in input_dates for signal in signals)


def test_signal_type_name_symbol_and_variant_follow_project_conventions() -> None:
    signal = _signals(S5_SIMPLE_RS_126D_V1, _rising_frame())[0]

    assert signal.symbol == "TEST"
    assert signal.signal_type == SignalType.LONG
    assert signal.strategy_name == STRATEGY_NAME
    assert signal.metadata["strategy_family"] == STRATEGY_NAME
    assert signal.metadata["strategy_variant"] == S5_SIMPLE_RS_126D_V1
    assert signal.metadata["s5_variant"] == S5_SIMPLE_RS_126D_V1


def test_strategy_name_property_is_stable() -> None:
    strategy = S5RelativeStrengthMomentumRotationStrategy()

    assert strategy.name == STRATEGY_NAME


def test_input_dataframe_is_not_mutated() -> None:
    data = _rising_frame()
    original = data.copy(deep=True)

    _signals(S5_VOL_ADJUSTED_RS_V1, data)

    pd.testing.assert_frame_equal(data, original)


def test_trend_filter_can_be_disabled_before_sma200_is_available() -> None:
    data = _rising_frame(rows=150)
    config = S5MomentumConfig(
        variant=S5_SIMPLE_RS_126D_V1,
        enable_trend_filter=False,
    )

    signals = generate_s5_momentum_signals("TEST", data, config)

    assert len(signals) == 1
    assert signals[0].generated_on == data.loc[126, "date"].date()
    assert signals[0].metadata["sma_distance_200d"] is None
    assert signals[0].metadata["trend_filter_enabled"] is False
    assert signals[0].metadata["trend_filter_passed"] is True


def test_min_rank_score_filters_candidates() -> None:
    config = S5MomentumConfig(
        variant=S5_SIMPLE_RS_126D_V1,
        min_rank_score=10.0,
    )

    signals = generate_s5_momentum_signals("TEST", _rising_frame(), config)

    assert signals == ()


def test_chronological_sorting_keeps_signal_date_deterministic() -> None:
    data = _rising_frame()
    reversed_data = data.iloc[::-1].reset_index(drop=True)

    chronological = _signals(S5_SIMPLE_RS_126D_V1, data)
    reversed_signals = _signals(S5_SIMPLE_RS_126D_V1, reversed_data)

    assert [signal.generated_on for signal in chronological] == [
        signal.generated_on for signal in reversed_signals
    ]
    assert [dict(signal.metadata) for signal in chronological] == [
        dict(signal.metadata) for signal in reversed_signals
    ]


def _signals(variant: str, data: pd.DataFrame) -> tuple:
    return generate_s5_momentum_signals(
        "TEST",
        data,
        S5MomentumConfig(variant=variant),
    )


def _signal_by_date(signals: tuple, target: date):
    return next((signal for signal in signals if signal.generated_on == target), None)


def _rising_frame(rows: int = 230) -> pd.DataFrame:
    close = 100.0 + 0.5 * np.arange(rows) + 0.1 * np.sin(np.arange(rows))
    return _frame(close)


def _falling_frame(rows: int = 230) -> pd.DataFrame:
    close = 300.0 - 0.5 * np.arange(rows)
    return _frame(close)


def _constant_frame(rows: int = 230) -> pd.DataFrame:
    return _frame(np.full(rows, 100.0))


def _frame(close: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=len(close), freq="D"),
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": np.full(len(close), 1000),
        }
    )
