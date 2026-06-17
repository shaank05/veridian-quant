"""Unit tests for the S3 trend pullback continuation strategy."""

from datetime import date

import pandas as pd
import pytest

from veridian_quant.v2.data.models import SignalType
from veridian_quant.v2.strategies.s3_trend_pullback_continuation import (
    S3_ABOVE_SMA50_V1,
    S3_BASELINE,
    S3_STRONG_TREND_ABOVE_SMA50_V1,
    S3_STRONG_TREND_V1,
    STRATEGY_NAME,
    S3TrendPullbackContinuationStrategy,
    generate_s3_trend_pullback_signals,
)


EXPECTED_METADATA_FIELDS = {
    "strategy_family",
    "strategy_variant",
    "s3_variant",
    "s3_requires_strong_trend",
    "s3_requires_above_sma50",
    "s3_strong_trend_min_sma200_slope_20d_pct",
    "close",
    "sma50",
    "sma200",
    "close_vs_sma50_pct",
    "close_vs_sma200_pct",
    "sma50_slope_20d_pct",
    "sma200_slope_20d_pct",
    "return_3d_pct",
    "return_5d_pct",
    "return_10d_pct",
    "drawdown_20d_pct",
    "drawdown_60d_pct",
    "close_vs_20d_high_pct",
    "close_vs_60d_low_pct",
    "is_60d_low",
    "atr14_pct",
    "atr14_change_5d_pct",
    "pullback_lookback",
    "sma_fast_window",
    "sma_slow_window",
    "sma_slope_lookback",
    "min_pullback_return_pct",
    "max_pullback_return_pct",
    "min_drawdown_20d_pct",
    "max_drawdown_20d_pct",
    "max_atr_pct",
    "max_atr_expansion_5d_pct",
    "require_recovery_day",
}


def test_missing_required_columns_raise_clear_error() -> None:
    data = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=220, freq="D"),
            "open": [100.0] * 220,
            "high": [101.0] * 220,
            "close": [100.0] * 220,
        }
    )

    with pytest.raises(ValueError, match="missing required columns: low"):
        generate_s3_trend_pullback_signals("TEST", data)


def test_input_dataframe_is_not_mutated() -> None:
    data = _qualifying_frame()
    original = data.copy(deep=True)

    generate_s3_trend_pullback_signals("TEST", data)

    pd.testing.assert_frame_equal(data, original)


def test_no_signal_when_insufficient_lookback() -> None:
    data = _frame([100.0 + index for index in range(40)])

    signals = generate_s3_trend_pullback_signals("TEST", data)

    assert signals == ()


def test_signal_generated_when_all_baseline_conditions_are_met() -> None:
    signals = generate_s3_trend_pullback_signals("TEST", _qualifying_frame())

    assert len(signals) == 1
    assert signals[0].symbol == "TEST"
    assert signals[0].signal_type == SignalType.LONG
    assert signals[0].strategy_name == STRATEGY_NAME
    assert signals[0].reason == "S3 trend pullback continuation setup"


def test_baseline_variant_produces_same_signal_as_default() -> None:
    data = _qualifying_frame()

    default_signals = generate_s3_trend_pullback_signals("TEST", data)
    baseline_signals = generate_s3_trend_pullback_signals(
        "TEST",
        data,
        strategy_variant=S3_BASELINE,
    )

    assert baseline_signals == default_signals


def test_strong_trend_variant_rejects_when_sma200_slope_not_strong() -> None:
    data = _qualifying_frame()

    baseline = generate_s3_trend_pullback_signals(
        "TEST",
        data,
        sma_slope_lookback=1,
    )
    strong_trend = generate_s3_trend_pullback_signals(
        "TEST",
        data,
        sma_slope_lookback=1,
        strategy_variant=S3_STRONG_TREND_V1,
    )

    assert len(baseline) == 1
    assert baseline[0].metadata["sma200_slope_20d_pct"] <= 1.0
    assert strong_trend == ()


def test_strong_trend_variant_accepts_when_sma200_slope_is_strong() -> None:
    signals = generate_s3_trend_pullback_signals(
        "TEST",
        _qualifying_frame(),
        strategy_variant=S3_STRONG_TREND_V1,
    )

    assert len(signals) == 1
    assert signals[0].metadata["sma200_slope_20d_pct"] > 1.0


def test_above_sma50_variant_rejects_when_close_is_below_sma50() -> None:
    data = _below_sma50_baseline_qualifying_frame()

    baseline = generate_s3_trend_pullback_signals("TEST", data)
    above_sma50 = generate_s3_trend_pullback_signals(
        "TEST",
        data,
        strategy_variant=S3_ABOVE_SMA50_V1,
    )

    assert len(baseline) == 1
    assert baseline[0].metadata["close_vs_sma50_pct"] < 0
    assert above_sma50 == ()


def test_above_sma50_variant_accepts_when_close_is_above_sma50() -> None:
    signals = generate_s3_trend_pullback_signals(
        "TEST",
        _qualifying_frame(),
        strategy_variant=S3_ABOVE_SMA50_V1,
    )

    assert len(signals) == 1
    assert signals[0].metadata["close_vs_sma50_pct"] >= 0


def test_combined_variant_requires_both_extra_filters() -> None:
    strong_but_below_sma50 = generate_s3_trend_pullback_signals(
        "TEST",
        _below_sma50_baseline_qualifying_frame(),
        strategy_variant=S3_STRONG_TREND_ABOVE_SMA50_V1,
    )
    above_sma50_but_not_strong = generate_s3_trend_pullback_signals(
        "TEST",
        _qualifying_frame(),
        sma_slope_lookback=1,
        strategy_variant=S3_STRONG_TREND_ABOVE_SMA50_V1,
    )
    passes_both = generate_s3_trend_pullback_signals(
        "TEST",
        _qualifying_frame(),
        strategy_variant=S3_STRONG_TREND_ABOVE_SMA50_V1,
    )

    assert strong_but_below_sma50 == ()
    assert above_sma50_but_not_strong == ()
    assert len(passes_both) == 1


def test_unknown_s3_variant_raises_value_error() -> None:
    with pytest.raises(ValueError, match="unknown S3 strategy variant"):
        generate_s3_trend_pullback_signals(
            "TEST",
            _qualifying_frame(),
            strategy_variant="UNKNOWN",
        )


def test_no_signal_when_close_is_below_sma200() -> None:
    data = _qualifying_frame()
    data.loc[data.index[-1], ["open", "high", "low", "close"]] = [
        110.0,
        111.0,
        109.0,
        110.0,
    ]

    signals = generate_s3_trend_pullback_signals("TEST", data)

    assert signals == ()


def test_no_signal_when_sma200_slope_is_negative() -> None:
    data = _frame([300.0 - (0.4 * index) for index in range(219)])
    data.loc[218, ["open", "high", "low", "close"]] = [200.0, 201.0, 199.0, 200.0]

    signals = generate_s3_trend_pullback_signals(
        "TEST",
        data,
        require_recovery_day=False,
        max_drawdown_20d_pct=0.0,
        min_drawdown_20d_pct=-80.0,
        min_pullback_return_pct=-80.0,
        max_pullback_return_pct=80.0,
        max_atr_pct=80.0,
        max_atr_expansion_5d_pct=500.0,
    )

    assert signals == ()


def test_no_signal_when_sma50_slope_is_negative() -> None:
    data = _qualifying_frame()
    start = len(data) - 70
    for offset, index in enumerate(range(start, len(data))):
        close = 230.0 - (offset * 0.4)
        if index >= len(data) - 6:
            close = data.loc[index, "close"]
        data.loc[index, ["open", "high", "low", "close"]] = [
            close,
            close + 1.0,
            close - 1.0,
            close,
        ]

    signals = generate_s3_trend_pullback_signals("TEST", data)

    assert signals == ()


def test_no_signal_when_pullback_is_too_shallow() -> None:
    data = _qualifying_frame()
    data.loc[data.index[-6], ["open", "high", "low", "close"]] = [
        202.0,
        203.0,
        201.0,
        202.0,
    ]

    signals = generate_s3_trend_pullback_signals("TEST", data)

    assert signals == ()


def test_no_signal_when_pullback_is_too_deep() -> None:
    data = _qualifying_frame()
    data.loc[data.index[-1], ["open", "high", "low", "close"]] = [
        170.0,
        171.0,
        169.0,
        170.0,
    ]

    signals = generate_s3_trend_pullback_signals("TEST", data)

    assert signals == ()


def test_no_signal_on_fresh_60d_low() -> None:
    data = _qualifying_frame()
    data.loc[data.index[-1], ["open", "high", "low", "close"]] = [
        199.0,
        200.0,
        198.0,
        199.0,
    ]

    signals = generate_s3_trend_pullback_signals(
        "TEST",
        data,
        fresh_low_window=4,
        require_recovery_day=False,
    )

    assert signals == ()


def test_no_signal_when_atr_pct_exceeds_max_threshold() -> None:
    data = _qualifying_frame()

    signals = generate_s3_trend_pullback_signals(
        "TEST",
        data,
        max_atr_pct=0.1,
    )

    assert signals == ()


def test_no_signal_when_atr_expansion_exceeds_max_threshold() -> None:
    data = _qualifying_frame()
    for index in range(len(data) - 14, len(data)):
        close = data.loc[index, "close"]
        data.loc[index, "high"] = close + 6.0
        data.loc[index, "low"] = close - 6.0

    signals = generate_s3_trend_pullback_signals(
        "TEST",
        data,
        max_atr_expansion_5d_pct=10.0,
    )

    assert signals == ()


def test_no_signal_when_recovery_day_required_and_close_does_not_recover() -> None:
    data = _qualifying_frame()
    data.loc[data.index[-2], ["open", "high", "low", "close"]] = [
        199.0,
        200.0,
        198.0,
        199.0,
    ]
    data.loc[data.index[-1], ["open", "high", "low", "close"]] = [
        198.0,
        199.0,
        197.0,
        198.0,
    ]

    signals = generate_s3_trend_pullback_signals("TEST", data)

    assert signals == ()
    assert generate_s3_trend_pullback_signals(
        "TEST",
        data,
        require_recovery_day=False,
    )


def test_repeated_signals_emit_only_when_enabled() -> None:
    data = _qualifying_frame(include_second_qualifying_day=True)

    default_signals = generate_s3_trend_pullback_signals("TEST", data)
    repeated_signals = generate_s3_trend_pullback_signals(
        "TEST",
        data,
        allow_repeated_signals=True,
    )

    assert len(default_signals) == 1
    assert len(repeated_signals) == 2
    assert [signal.generated_on for signal in repeated_signals] == [
        date(2026, 8, 8),
        date(2026, 8, 9),
    ]


def test_metadata_contains_all_expected_fields() -> None:
    metadata = _first_signal().metadata

    assert EXPECTED_METADATA_FIELDS.issubset(metadata)
    assert metadata["strategy_family"] == STRATEGY_NAME
    assert metadata["strategy_variant"] == S3_BASELINE
    assert metadata["s3_variant"] == S3_BASELINE
    assert metadata["s3_requires_strong_trend"] is False
    assert metadata["s3_requires_above_sma50"] is False
    assert metadata["pullback_lookback"] == 5
    assert metadata["sma_fast_window"] == 50
    assert metadata["sma_slow_window"] == 200
    assert metadata["require_recovery_day"] is True


def test_variant_metadata_includes_selected_variant() -> None:
    signal = generate_s3_trend_pullback_signals(
        "TEST",
        _qualifying_frame(),
        strategy_variant=S3_STRONG_TREND_ABOVE_SMA50_V1,
    )[0]
    metadata = signal.metadata

    assert metadata["strategy_variant"] == S3_STRONG_TREND_ABOVE_SMA50_V1
    assert metadata["s3_variant"] == S3_STRONG_TREND_ABOVE_SMA50_V1
    assert metadata["s3_requires_strong_trend"] is True
    assert metadata["s3_requires_above_sma50"] is True
    assert metadata["s3_strong_trend_min_sma200_slope_20d_pct"] == 1.0


def test_signal_generated_on_equals_signal_row_date() -> None:
    signal = _first_signal()

    assert signal.generated_on == date(2026, 8, 8)


def test_metadata_values_are_deterministic() -> None:
    metadata = _first_signal().metadata

    assert metadata["close"] == 202.0
    assert metadata["sma50_slope_20d_pct"] > 0
    assert metadata["sma200_slope_20d_pct"] > 0
    assert metadata["return_5d_pct"] == pytest.approx(((202.0 / 208.0) - 1) * 100)
    assert metadata["drawdown_20d_pct"] == pytest.approx(((202.0 / 211.0) - 1) * 100)
    assert metadata["close_vs_20d_high_pct"] == pytest.approx(
        ((202.0 / 211.0) - 1) * 100
    )
    assert metadata["is_60d_low"] is False
    assert metadata["atr14_pct"] <= 8.0
    assert metadata["atr14_change_5d_pct"] <= 50.0


def test_future_rows_do_not_affect_prior_signal_decision() -> None:
    data = _qualifying_frame(include_second_qualifying_day=True)
    modified = data.copy(deep=True)
    modified.loc[modified.index[-1], ["open", "high", "low", "close"]] = [
        50.0,
        51.0,
        49.0,
        50.0,
    ]

    baseline = generate_s3_trend_pullback_signals("TEST", data)
    changed = generate_s3_trend_pullback_signals("TEST", modified)

    baseline_first = baseline[0]
    changed_first = changed[0]

    assert baseline_first.generated_on == date(2026, 8, 8)
    assert changed_first.generated_on == date(2026, 8, 8)
    assert baseline_first.metadata == changed_first.metadata


def _first_signal():
    signals = generate_s3_trend_pullback_signals("TEST", _qualifying_frame())
    assert len(signals) == 1
    return signals[0]


def _qualifying_frame(include_second_qualifying_day: bool = False) -> pd.DataFrame:
    closes = [100.0 + (0.5 * index) for index in range(210)]
    closes.extend(
        [206.0, 208.0, 211.0, 209.0, 208.0, 207.0, 201.0, 200.0, 201.0, 202.0]
    )
    if include_second_qualifying_day:
        closes.append(203.0)
    return _frame(closes)


def _below_sma50_baseline_qualifying_frame() -> pd.DataFrame:
    data = _qualifying_frame()
    data.loc[data.index[-2], ["open", "high", "low", "close"]] = [
        192.0,
        193.0,
        191.0,
        192.0,
    ]
    data.loc[data.index[-1], ["open", "high", "low", "close"]] = [
        195.0,
        196.0,
        194.0,
        195.0,
    ]
    return data


def _frame(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=len(closes), freq="D"),
            "open": closes,
            "high": [close + 1.0 for close in closes],
            "low": [close - 1.0 for close in closes],
            "close": closes,
            "volume": [1000 for _ in closes],
        }
    )
