"""Unit tests for v2 S1 trade setup planning."""

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from veridian_quant.v2.backtesting.setup import TradeSetup, build_trade_setup
from veridian_quant.v2.data.models import Signal, SignalType


def test_valid_setup_is_created_from_signal() -> None:
    data = _frame()
    signal = _signal(date(2026, 1, 14))

    setup = build_trade_setup(signal, data)

    assert isinstance(setup, TradeSetup)
    assert setup.symbol == signal.symbol
    assert setup.strategy_name == signal.strategy_name
    assert setup.signal_date == signal.generated_on


def test_entry_date_is_next_row_after_signal_date() -> None:
    data = _frame()
    signal = _signal(date(2026, 1, 14))

    setup = build_trade_setup(signal, data)

    assert setup is not None
    assert setup.entry_date == date(2026, 1, 15)


def test_entry_price_uses_next_row_open() -> None:
    data = _frame()
    signal = _signal(date(2026, 1, 14))

    setup = build_trade_setup(signal, data)

    assert setup is not None
    assert setup.entry_price == Decimal("120.0")


def test_stop_loss_uses_entry_price_minus_two_times_atr() -> None:
    data = _frame()
    signal = _signal(date(2026, 1, 14))

    setup = build_trade_setup(signal, data)

    assert setup is not None
    assert setup.atr == Decimal("2.0")
    assert setup.stop_loss == Decimal("116.0")


def test_target_uses_two_to_one_reward_risk_ratio() -> None:
    data = _frame()
    signal = _signal(date(2026, 1, 14))

    setup = build_trade_setup(signal, data)

    assert setup is not None
    assert setup.target_price == Decimal("128.0")
    assert setup.reward_risk_ratio == Decimal("2")


def test_no_setup_if_there_is_no_next_row() -> None:
    data = _frame()
    signal = _signal(date(2026, 1, 15))

    setup = build_trade_setup(signal, data)

    assert setup is None


def test_no_setup_if_entry_open_is_missing() -> None:
    data = _frame()
    data.loc[14, "open"] = float("nan")
    signal = _signal(date(2026, 1, 14))

    setup = build_trade_setup(signal, data)

    assert setup is None


def test_no_setup_if_atr_is_unavailable() -> None:
    data = _frame(rows=10)
    signal = _signal(date(2026, 1, 9))

    setup = build_trade_setup(signal, data)

    assert setup is None


def test_no_setup_if_atr_is_zero_or_negative(monkeypatch: pytest.MonkeyPatch) -> None:
    zero_atr_data = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=15, freq="D"),
            "open": [100.0] * 15,
            "high": [100.0] * 15,
            "low": [100.0] * 15,
            "close": [100.0] * 15,
        }
    )
    valid_data = _frame()

    assert build_trade_setup(_signal(date(2026, 1, 14)), zero_atr_data) is None
    monkeypatch.setattr(
        "veridian_quant.v2.backtesting.setup.atr",
        lambda data, window: pd.Series([-1.0 for _ in range(len(data))]),
    )
    assert (
        build_trade_setup(
            _signal(date(2026, 1, 1)),
            valid_data,
            atr_window=1,
        )
        is None
    )


def test_input_dataframe_is_not_mutated() -> None:
    data = _frame()
    original = data.copy(deep=True)
    signal = _signal(date(2026, 1, 14))

    build_trade_setup(signal, data)

    pd.testing.assert_frame_equal(data, original)


def test_missing_required_columns_raises_clear_error() -> None:
    data = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=15, freq="D"),
            "open": [100.0] * 15,
            "high": [101.0] * 15,
            "close": [100.0] * 15,
        }
    )

    with pytest.raises(ValueError, match="missing required columns: low"):
        build_trade_setup(_signal(date(2026, 1, 14)), data)


def _signal(generated_on: date) -> Signal:
    """Build a LONG signal for setup tests."""

    return Signal(
        symbol="RELIANCE",
        signal_type=SignalType.LONG,
        generated_on=generated_on,
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        reason="test signal",
    )


def _frame(rows: int = 15) -> pd.DataFrame:
    """Build a one-symbol OHLC dataframe with ATR equal to 2.0."""

    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=rows, freq="D"),
            "open": [106.0 + index for index in range(rows)],
            "high": [101.0 + index for index in range(rows)],
            "low": [99.0 + index for index in range(rows)],
            "close": [100.0 + index for index in range(rows)],
        }
    )
