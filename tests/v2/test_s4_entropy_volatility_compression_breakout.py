"""Unit tests for the S4 compression breakout signal generator."""

from datetime import date

import pandas as pd
import pytest

from veridian_quant.v2.data.models import SignalType
from veridian_quant.v2.strategies.s4_entropy_volatility_compression_breakout import (
    S4_ATR_COMPRESSION_BREAKOUT_V1,
    S4_ENTROPY_GATED_BREAKOUT_V1,
    S4_RANGE_COMPRESSION_BREAKOUT_V1,
    STRATEGY_NAME,
    build_s4_feature_frame,
    generate_s4_entropy_volatility_compression_breakout_signals,
)


EXPECTED_METADATA_FIELDS = {
    "strategy_family",
    "strategy_variant",
    "s4_variant",
    "variant",
    "close",
    "prior_high",
    "atr_pct",
    "atr_percentile",
    "prior_atr_percentile",
    "range_pct",
    "range_percentile",
    "prior_range_percentile",
    "return_sign_entropy",
    "prior_return_sign_entropy",
    "compression_threshold",
    "entropy_threshold",
    "breakout_window",
    "atr_window",
    "range_window",
    "percentile_window",
    "entropy_window",
    "flat_threshold",
}


def test_generates_atr_compression_breakout_signal() -> None:
    signals = _signals(S4_ATR_COMPRESSION_BREAKOUT_V1, _compressed_breakout_frame())

    assert len(signals) == 1
    assert signals[0].symbol == "TEST"
    assert signals[0].signal_type == SignalType.LONG
    assert signals[0].strategy_name == STRATEGY_NAME
    assert signals[0].generated_on == date(2026, 1, 6)
    assert signals[0].reason == "S4 compression breakout setup"


def test_generates_range_compression_breakout_signal() -> None:
    signals = _signals(S4_RANGE_COMPRESSION_BREAKOUT_V1, _compressed_breakout_frame())

    assert len(signals) == 1
    assert signals[0].metadata["s4_variant"] == S4_RANGE_COMPRESSION_BREAKOUT_V1


def test_generates_entropy_gated_breakout_signal() -> None:
    signals = _signals(S4_ENTROPY_GATED_BREAKOUT_V1, _compressed_breakout_frame())

    assert len(signals) == 1
    assert signals[0].metadata["prior_return_sign_entropy"] <= 0.70


def test_does_not_signal_without_breakout() -> None:
    data = _compressed_breakout_frame()
    data.loc[data.index[-1], "close"] = 19.0

    signals = _signals(S4_ATR_COMPRESSION_BREAKOUT_V1, data)

    assert signals == ()


def test_does_not_signal_when_prior_compression_condition_is_not_met() -> None:
    signals = _signals(
        S4_ATR_COMPRESSION_BREAKOUT_V1,
        _not_compressed_breakout_frame(),
    )

    assert signals == ()


def test_does_not_signal_when_entropy_gate_fails() -> None:
    signals = _signals(
        S4_ENTROPY_GATED_BREAKOUT_V1,
        _mixed_entropy_breakout_frame(),
        entropy_threshold=0.10,
    )

    assert signals == ()


def test_compression_qualification_uses_shifted_prior_values() -> None:
    signals = _signals(S4_ATR_COMPRESSION_BREAKOUT_V1, _compressed_breakout_frame())

    metadata = signals[0].metadata

    assert metadata["prior_atr_percentile"] <= 0.20
    assert metadata["atr_percentile"] > 0.20


def test_unknown_variant_raises_value_error() -> None:
    with pytest.raises(ValueError, match="unknown S4 strategy variant"):
        generate_s4_entropy_volatility_compression_breakout_signals(
            "TEST",
            _compressed_breakout_frame(),
            variant="UNKNOWN",
            atr_window=1,
            range_window=1,
            breakout_window=3,
            percentile_window=3,
            entropy_window=3,
        )


def test_missing_required_columns_raise_clear_error() -> None:
    data = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=5, freq="D"),
            "high": [10.0] * 5,
            "close": [10.0] * 5,
        }
    )

    with pytest.raises(ValueError, match="missing required columns: low"):
        _signals(S4_ATR_COMPRESSION_BREAKOUT_V1, data)


def test_input_dataframe_is_not_mutated() -> None:
    data = _compressed_breakout_frame()
    original = data.copy(deep=True)

    _signals(S4_ATR_COMPRESSION_BREAKOUT_V1, data)

    pd.testing.assert_frame_equal(data, original)


def test_duplicate_consecutive_signals_are_suppressed_by_default() -> None:
    data = _repeated_breakout_frame()

    signals = _signals(
        S4_ATR_COMPRESSION_BREAKOUT_V1,
        data,
        compression_threshold=1.0,
    )

    assert len(signals) == 1
    assert signals[0].generated_on == date(2026, 1, 6)


def test_allow_repeated_signals_emits_repeated_eligible_signal_days() -> None:
    data = _repeated_breakout_frame()

    signals = _signals(
        S4_ATR_COMPRESSION_BREAKOUT_V1,
        data,
        compression_threshold=1.0,
        allow_repeated_signals=True,
    )

    assert len(signals) == 2
    assert [signal.generated_on for signal in signals] == [
        date(2026, 1, 6),
        date(2026, 1, 7),
    ]


def test_signal_metadata_includes_expected_feature_and_parameter_values() -> None:
    signal = _signals(S4_ATR_COMPRESSION_BREAKOUT_V1, _compressed_breakout_frame())[0]
    metadata = signal.metadata

    assert EXPECTED_METADATA_FIELDS.issubset(metadata)
    assert metadata["strategy_family"] == STRATEGY_NAME
    assert metadata["strategy_variant"] == S4_ATR_COMPRESSION_BREAKOUT_V1
    assert metadata["s4_variant"] == S4_ATR_COMPRESSION_BREAKOUT_V1
    assert metadata["variant"] == S4_ATR_COMPRESSION_BREAKOUT_V1
    assert metadata["compression_threshold"] == 0.20
    assert metadata["entropy_threshold"] == 0.70
    assert metadata["breakout_window"] == 3
    assert metadata["atr_window"] == 1
    assert metadata["range_window"] == 1
    assert metadata["percentile_window"] == 3
    assert metadata["entropy_window"] == 3
    assert metadata["flat_threshold"] == 0.0


def test_signal_metadata_includes_current_and_prior_compression_fields() -> None:
    metadata = _signals(S4_ATR_COMPRESSION_BREAKOUT_V1, _compressed_breakout_frame())[
        0
    ].metadata

    assert metadata["atr_percentile"] is not None
    assert metadata["prior_atr_percentile"] is not None
    assert metadata["range_percentile"] is not None
    assert metadata["prior_range_percentile"] is not None
    assert metadata["return_sign_entropy"] is not None
    assert metadata["prior_return_sign_entropy"] is not None


def test_breakout_level_excludes_current_row() -> None:
    frame = build_s4_feature_frame(
        _compressed_breakout_frame(),
        atr_window=1,
        range_window=1,
        breakout_window=3,
        percentile_window=3,
        entropy_window=3,
    )

    assert frame.iloc[-1]["prior_high"] == 20.0
    assert frame.iloc[-1]["close_above_prior_high"] == True


def test_pct_metadata_values_are_percentage_points_not_raw_fractions() -> None:
    metadata = _signals(S4_ATR_COMPRESSION_BREAKOUT_V1, _compressed_breakout_frame())[
        0
    ].metadata

    assert metadata["atr_pct"] > 1.0
    assert metadata["range_pct"] > 1.0


def test_return_type_is_tuple_of_signals() -> None:
    signals = _signals(S4_ATR_COMPRESSION_BREAKOUT_V1, _compressed_breakout_frame())

    assert isinstance(signals, tuple)


def _signals(
    variant: str,
    data: pd.DataFrame,
    compression_threshold: float = 0.20,
    entropy_threshold: float = 0.70,
    allow_repeated_signals: bool = False,
) -> tuple:
    return generate_s4_entropy_volatility_compression_breakout_signals(
        "TEST",
        data,
        variant=variant,
        atr_window=1,
        range_window=1,
        breakout_window=3,
        percentile_window=3,
        entropy_window=3,
        compression_threshold=compression_threshold,
        entropy_threshold=entropy_threshold,
        allow_repeated_signals=allow_repeated_signals,
    )


def _compressed_breakout_frame() -> pd.DataFrame:
    return _frame(
        highs=[12.0, 12.0, 20.0, 20.0, 10.2, 30.0],
        lows=[10.0, 10.0, 10.0, 10.0, 9.8, 9.0],
        closes=[11.0, 11.0, 10.0, 10.0, 10.0, 21.0],
    )


def _not_compressed_breakout_frame() -> pd.DataFrame:
    return _frame(
        highs=[10.2, 10.2, 10.2, 10.2, 20.0, 30.0],
        lows=[9.8, 9.8, 9.8, 9.8, 9.0, 9.0],
        closes=[10.0, 10.0, 10.0, 10.0, 10.0, 21.0],
    )


def _mixed_entropy_breakout_frame() -> pd.DataFrame:
    return _frame(
        highs=[12.0, 12.0, 20.0, 20.0, 10.2, 30.0],
        lows=[10.0, 10.0, 10.0, 10.0, 9.8, 9.0],
        closes=[10.0, 11.0, 10.0, 10.0, 10.0, 21.0],
    )


def _repeated_breakout_frame() -> pd.DataFrame:
    return _frame(
        highs=[12.0, 12.0, 20.0, 20.0, 10.2, 30.0, 31.0],
        lows=[10.0, 10.0, 10.0, 10.0, 9.8, 9.0, 20.0],
        closes=[11.0, 11.0, 10.0, 10.0, 10.0, 21.0, 30.5],
    )


def _frame(highs: list[float], lows: list[float], closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=len(closes), freq="D"),
            "open": closes,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": [1000 for _ in closes],
        }
    )
