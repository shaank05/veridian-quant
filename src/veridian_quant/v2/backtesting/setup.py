"""Trade setup planning for Veridian Quant v2.

This module converts an existing signal into a pre-trade plan using the S1
methodology. It does not create trades, size positions, resolve exits, calculate
PnL, perform portfolio accounting, or run a backtest.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping

import pandas as pd

from veridian_quant.v2.data.models import Signal
from veridian_quant.v2.features.technical import atr


@dataclass(frozen=True, slots=True)
class TradeSetup:
    """Passive pre-trade plan derived from a signal and entry-session data."""

    symbol: str
    strategy_name: str
    signal_date: date
    entry_date: date
    entry_price: Decimal
    stop_loss: Decimal
    target_price: Decimal
    atr: Decimal
    atr_window: int
    atr_multiplier: Decimal
    reward_risk_ratio: Decimal
    metadata: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({})
    )


def build_trade_setup(
    signal: Signal,
    data: pd.DataFrame,
    atr_window: int = 14,
    atr_multiplier: Decimal | int | str = Decimal("2"),
    reward_risk_ratio: Decimal | int | str = Decimal("2"),
) -> TradeSetup | None:
    """Build a planned trade setup from a signal and one-symbol OHLCV dataframe.

    Entry is planned for the trading session immediately after the signal date.
    The entry price is that session's open. ATR is used only for risk planning:
    stop loss is ``entry - atr_multiplier * ATR`` and target is
    ``entry + reward_risk_ratio * stop_distance``.
    """

    _validate_input(data)
    atr_values = atr(data, atr_window)
    signal_row_index = _find_signal_row_index(data, signal.generated_on)
    if signal_row_index is None:
        return None

    entry_position = signal_row_index + 1
    if entry_position >= len(data):
        return None

    entry_row = data.iloc[entry_position]
    entry_open = entry_row["open"]
    entry_atr = atr_values.iloc[entry_position]
    if not _is_positive_number(entry_open) or not _is_positive_number(entry_atr):
        return None

    entry_price = _to_decimal(entry_open)
    atr_value = _to_decimal(entry_atr)
    atr_multiplier_value = _to_decimal(atr_multiplier)
    reward_risk_ratio_value = _to_decimal(reward_risk_ratio)

    stop_distance = atr_multiplier_value * atr_value
    stop_loss = entry_price - stop_distance
    target_price = entry_price + (reward_risk_ratio_value * stop_distance)

    return TradeSetup(
        symbol=signal.symbol,
        strategy_name=signal.strategy_name,
        signal_date=signal.generated_on,
        entry_date=_row_date(entry_row),
        entry_price=entry_price,
        stop_loss=stop_loss,
        target_price=target_price,
        atr=atr_value,
        atr_window=atr_window,
        atr_multiplier=atr_multiplier_value,
        reward_risk_ratio=reward_risk_ratio_value,
        metadata=MappingProxyType(
            {
                "entry_rule": "next_session_open",
                "risk_rule": "atr_stop_and_two_to_one_target",
            }
        ),
    )


def _validate_input(data: pd.DataFrame) -> None:
    """Validate the minimum OHLC columns needed for setup planning."""

    required = ["open", "high", "low", "close"]
    missing = [column for column in required if column not in data.columns]
    if "date" not in data.columns and "timestamp" not in data.columns:
        missing.append("date or timestamp")
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")


def _find_signal_row_index(data: pd.DataFrame, signal_date: date) -> int | None:
    """Return the positional row index for the signal date, if present."""

    for position, (_, row) in enumerate(data.iterrows()):
        if _row_date(row) == signal_date:
            return position
    return None


def _row_date(row: pd.Series) -> date:
    """Return a Python date from the row's date or timestamp field."""

    value = row["date"] if "date" in row.index else row["timestamp"]
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()


def _is_positive_number(value: object) -> bool:
    """Return whether a value is finite and greater than zero."""

    if pd.isna(value):
        return False
    try:
        return Decimal(str(value)) > 0
    except Exception:
        return False


def _to_decimal(value: Decimal | int | str | float) -> Decimal:
    """Convert numeric inputs to Decimal without binary float expansion."""

    return value if isinstance(value, Decimal) else Decimal(str(value))
