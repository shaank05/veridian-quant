"""Exit resolution for simulated Veridian Quant v2 backtest trades.

This module closes passive open research trades from future OHLC data. It does
not calculate PnL, update portfolio state, or run a backtest engine.
"""

from datetime import date
from decimal import Decimal

import pandas as pd

from veridian_quant.v2.backtesting.sizing import PositionPlan
from veridian_quant.v2.backtesting.trade import ExitReason, Trade, TradeStatus


def resolve_trade_exit(
    trade: Trade,
    position_plan: PositionPlan,
    data: pd.DataFrame,
    max_holding_sessions: int = 20,
) -> Trade | None:
    """Resolve an open trade exit from one-symbol OHLC data."""

    _validate_input(data)
    if max_holding_sessions <= 0:
        raise ValueError("max_holding_sessions must be positive")

    holding_data = _holding_data(data, trade.entry_date, max_holding_sessions)
    if holding_data.empty:
        return None

    for _, row in holding_data.iterrows():
        session_date = _row_date(row)
        open_price = _to_decimal(row["open"])
        high_price = _to_decimal(row["high"])
        low_price = _to_decimal(row["low"])

        if open_price >= position_plan.target_price:
            return _closed_trade(
                trade,
                session_date,
                open_price,
                ExitReason.TARGET_GAP_HIT,
            )
        if open_price <= position_plan.stop_loss:
            return _closed_trade(
                trade,
                session_date,
                open_price,
                ExitReason.STOP_GAP_HIT,
            )
        if (
            high_price >= position_plan.target_price
            and low_price <= position_plan.stop_loss
        ):
            return _closed_trade(
                trade,
                session_date,
                position_plan.stop_loss,
                ExitReason.STOP_LOSS_HIT,
            )
        if high_price >= position_plan.target_price:
            return _closed_trade(
                trade,
                session_date,
                position_plan.target_price,
                ExitReason.TARGET_HIT,
            )
        if low_price <= position_plan.stop_loss:
            return _closed_trade(
                trade,
                session_date,
                position_plan.stop_loss,
                ExitReason.STOP_LOSS_HIT,
            )

    final_row = holding_data.iloc[-1]
    return _closed_trade(
        trade,
        _row_date(final_row),
        _to_decimal(final_row["close"]),
        ExitReason.TIME_STOP,
    )


def _closed_trade(
    trade: Trade,
    exit_date: date,
    exit_price: Decimal,
    exit_reason: ExitReason,
) -> Trade:
    """Return a closed copy of the input trade with resolved exit fields."""

    return Trade(
        trade_id=trade.trade_id,
        symbol=trade.symbol,
        entry_date=trade.entry_date,
        entry_price=trade.entry_price,
        quantity=trade.quantity,
        status=TradeStatus.CLOSED,
        strategy_name=trade.strategy_name,
        exit_date=exit_date,
        exit_price=exit_price,
        exit_reason=exit_reason,
    )


def _holding_data(
    data: pd.DataFrame,
    entry_date: date,
    max_holding_sessions: int,
) -> pd.DataFrame:
    """Return rows on or after entry date, limited by holding sessions."""

    date_values = data.apply(_row_date, axis=1)
    return data.loc[date_values >= entry_date].head(max_holding_sessions)


def _validate_input(data: pd.DataFrame) -> None:
    """Validate the minimum OHLC columns needed for exit resolution."""

    required = ["open", "high", "low", "close"]
    missing = [column for column in required if column not in data.columns]
    if "date" not in data.columns and "timestamp" not in data.columns:
        missing.append("date or timestamp")
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")


def _row_date(row: pd.Series) -> date:
    """Return a Python date from the row's date or timestamp field."""

    value = row["date"] if "date" in row.index else row["timestamp"]
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()


def _to_decimal(value: Decimal | int | str | float) -> Decimal:
    """Convert numeric inputs to Decimal without binary float expansion."""

    return value if isinstance(value, Decimal) else Decimal(str(value))
