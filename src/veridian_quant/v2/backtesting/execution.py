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

    initial_risk_amount = position_plan.per_share_risk * position_plan.quantity
    planned_reward_amount = (
        abs(position_plan.target_price - position_plan.entry_price)
        * position_plan.quantity
    )
    reward_risk_ratio = (
        planned_reward_amount / initial_risk_amount
        if initial_risk_amount > 0
        else None
    )

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
        stop_loss=position_plan.stop_loss,
        target_price=position_plan.target_price,
        per_share_risk=position_plan.per_share_risk,
        initial_risk_amount=initial_risk_amount,
        planned_reward_amount=planned_reward_amount,
        reward_risk_ratio=reward_risk_ratio,
    )


def _deterministic_trade_id(position_plan: PositionPlan) -> str:
    """Build a readable deterministic ID from strategy, symbol, and entry date."""

    return (
        f"{position_plan.strategy_name}-"
        f"{position_plan.symbol}-"
        f"{position_plan.entry_date.isoformat()}"
    )
