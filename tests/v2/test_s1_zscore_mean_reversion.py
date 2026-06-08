"""Unit tests for the v2 S1 Z-score mean-reversion signal generator."""

from datetime import date

import pandas as pd
import pytest

from veridian_quant.v2.data.models import SignalType
from veridian_quant.v2.strategies.s1_zscore_mean_reversion import (
    STRATEGY_NAME,
    S1ZScoreMeanReversionStrategy,
    generate_s1_zscore_signals,
)


def test_no_signal_when_insufficient_lookback() -> None:
    data = _frame([10.0, 12.0], start="2026-01-01")
    strategy = S1ZScoreMeanReversionStrategy(window=3, entry_threshold=-1.0)

    signals = strategy.generate_signals("RELIANCE", data)

    assert signals == []


def test_signal_generated_when_zscore_crosses_below_threshold() -> None:
    data = _frame([10.0, 12.0, 14.0, 8.0], start="2026-01-01")
    strategy = S1ZScoreMeanReversionStrategy(window=3, entry_threshold=-1.0)

    signals = strategy.generate_signals("RELIANCE", data)

    assert len(signals) == 1
    assert signals[0].symbol == "RELIANCE"
    assert signals[0].signal_type == SignalType.LONG
    assert signals[0].strategy_name == STRATEGY_NAME
    assert "Z-score" in signals[0].reason
    assert "threshold" in signals[0].reason


def test_no_duplicate_signal_on_consecutive_oversold_days_by_default() -> None:
    data = _frame([10.0, 12.0, 14.0, 8.0, 6.0], start="2026-01-01")
    strategy = S1ZScoreMeanReversionStrategy(window=3, entry_threshold=-0.5)

    signals = strategy.generate_signals("RELIANCE", data)

    assert len(signals) == 1
    assert signals[0].generated_on == date(2026, 1, 4)


def test_repeated_signals_when_enabled() -> None:
    data = _frame([10.0, 12.0, 14.0, 8.0, 6.0], start="2026-01-01")
    strategy = S1ZScoreMeanReversionStrategy(
        window=3,
        entry_threshold=-0.5,
        allow_repeated_signals=True,
    )

    signals = strategy.generate_signals("RELIANCE", data)

    assert len(signals) == 2
    assert [signal.generated_on for signal in signals] == [
        date(2026, 1, 4),
        date(2026, 1, 5),
    ]


def test_metadata_contains_required_signal_context() -> None:
    data = _frame([10.0, 12.0, 14.0, 8.0], start="2026-01-01")
    signals = generate_s1_zscore_signals(
        "RELIANCE",
        data,
        window=3,
        entry_threshold=-1.0,
    )

    metadata = signals[0].metadata

    assert set(metadata) >= {
        "z_score",
        "zscore_window",
        "entry_threshold",
        "close",
    }
    assert metadata["zscore_window"] == 3
    assert metadata["entry_threshold"] == -1.0
    assert metadata["close"] == 8.0
    assert metadata["z_score"] <= -1.0


def test_input_dataframe_is_not_mutated() -> None:
    data = _frame([10.0, 12.0, 14.0, 8.0], start="2026-01-01")
    original = data.copy(deep=True)
    strategy = S1ZScoreMeanReversionStrategy(window=3, entry_threshold=-1.0)

    strategy.generate_signals("RELIANCE", data)

    pd.testing.assert_frame_equal(data, original)


def test_missing_close_column_raises_clear_error() -> None:
    data = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=3, freq="D"),
            "open": [10.0, 11.0, 12.0],
        }
    )
    strategy = S1ZScoreMeanReversionStrategy(window=3)

    with pytest.raises(ValueError, match="missing required columns: close"):
        strategy.generate_signals("RELIANCE", data)


def test_generated_on_uses_correct_row_date() -> None:
    data = _frame([10.0, 12.0, 14.0, 8.0], start="2026-03-10")
    strategy = S1ZScoreMeanReversionStrategy(window=3, entry_threshold=-1.0)

    signals = strategy.generate_signals("RELIANCE", data)

    assert signals[0].generated_on == date(2026, 3, 13)


def test_timestamp_column_can_supply_generated_on_date() -> None:
    data = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-03-10 15:30", periods=4, freq="D"),
            "close": [10.0, 12.0, 14.0, 8.0],
        }
    )
    strategy = S1ZScoreMeanReversionStrategy(window=3, entry_threshold=-1.0)

    signals = strategy.generate_signals("RELIANCE", data)

    assert signals[0].generated_on == date(2026, 3, 13)


def _frame(closes: list[float], start: str) -> pd.DataFrame:
    """Build a one-symbol lowercase OHLCV dataframe for tests."""

    return pd.DataFrame(
        {
            "date": pd.date_range(start, periods=len(closes), freq="D"),
            "open": closes,
            "high": [close + 1.0 for close in closes],
            "low": [close - 1.0 for close in closes],
            "close": closes,
            "volume": [1000 for _ in closes],
        }
    )
