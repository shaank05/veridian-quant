"""Trade creation helpers for Veridian Quant v2 backtesting.

This module converts planned positions into passive open research trades. It
does not update portfolio state, resolve exits, or calculate PnL.
"""

from veridian_quant.v2.backtesting.sizing import PositionPlan
from veridian_quant.v2.backtesting.trade import Trade, TradeStatus


def create_open_trade(
    position_plan: PositionPlan,
    trade_id: str | None = None,
) -> Trade:
    """Create an open research trade from a planned position."""

    return Trade(
        trade_id=trade_id or _deterministic_trade_id(position_plan),
        symbol=position_plan.symbol,
        entry_date=position_plan.entry_date,
        entry_price=position_plan.entry_price,
        quantity=position_plan.quantity,
        status=TradeStatus.OPEN,
        strategy_name=position_plan.strategy_name,
        exit_date=None,
        exit_price=None,
        exit_reason=None,
    )


def _deterministic_trade_id(position_plan: PositionPlan) -> str:
    """Build a readable deterministic ID from strategy, symbol, and entry date."""

    return (
        f"{position_plan.strategy_name}-"
        f"{position_plan.symbol}-"
        f"{position_plan.entry_date.isoformat()}"
    )
