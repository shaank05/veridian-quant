"""Trade-level PnL calculation for Veridian Quant v2 backtests.

This module calculates passive per-trade results for closed simulated trades.
It does not update portfolio state, compute performance metrics, or run a
backtest engine.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from veridian_quant.v2.backtesting.trade import ExitReason, Trade, TradeStatus


@dataclass(frozen=True, slots=True)
class TradePnL:
    """Passive trade-level profit and loss result."""

    trade_id: str
    symbol: str
    strategy_name: str
    entry_date: date
    exit_date: date
    entry_price: Decimal
    exit_price: Decimal
    quantity: int
    gross_pnl: Decimal
    gross_return_pct: Decimal
    total_cost: Decimal
    net_pnl: Decimal
    net_return_pct: Decimal
    exit_reason: ExitReason
    stop_loss: Decimal | None = None
    target_price: Decimal | None = None
    per_share_risk: Decimal | None = None
    initial_risk_amount: Decimal | None = None
    planned_reward_amount: Decimal | None = None
    reward_risk_ratio: Decimal | None = None
    candidate_ranking_mode: str | None = None
    candidate_rank: int | None = None
    candidate_score: float | None = None
    candidate_pool_size_for_date: int | None = None


def calculate_trade_pnl(
    trade: Trade,
    round_trip_cost_pct: Decimal | int | str | float = Decimal("0.004"),
) -> TradePnL | None:
    """Calculate trade-level PnL for a closed simulated trade."""

    round_trip_cost_pct_value = _to_decimal(round_trip_cost_pct)
    if round_trip_cost_pct_value < 0:
        return None
    if (
        trade.status != TradeStatus.CLOSED
        or trade.exit_price is None
        or trade.exit_date is None
        or trade.exit_reason is None
        or trade.quantity <= 0
        or trade.entry_price <= 0
        or trade.exit_price <= 0
    ):
        return None

    entry_capital = trade.quantity * trade.entry_price
    price_delta = trade.exit_price - trade.entry_price
    gross_pnl = trade.quantity * price_delta
    gross_return_pct = (price_delta / trade.entry_price) * Decimal("100")
    total_cost = entry_capital * round_trip_cost_pct_value
    net_pnl = gross_pnl - total_cost
    net_return_pct = (net_pnl / entry_capital) * Decimal("100")

    return TradePnL(
        trade_id=trade.trade_id,
        symbol=trade.symbol,
        strategy_name=trade.strategy_name,
        entry_date=trade.entry_date,
        exit_date=trade.exit_date,
        entry_price=trade.entry_price,
        exit_price=trade.exit_price,
        quantity=trade.quantity,
        gross_pnl=gross_pnl,
        gross_return_pct=gross_return_pct,
        total_cost=total_cost,
        net_pnl=net_pnl,
        net_return_pct=net_return_pct,
        exit_reason=trade.exit_reason,
        stop_loss=trade.stop_loss,
        target_price=trade.target_price,
        per_share_risk=trade.per_share_risk,
        initial_risk_amount=trade.initial_risk_amount,
        planned_reward_amount=trade.planned_reward_amount,
        reward_risk_ratio=trade.reward_risk_ratio,
        candidate_ranking_mode=trade.candidate_ranking_mode,
        candidate_rank=trade.candidate_rank,
        candidate_score=trade.candidate_score,
        candidate_pool_size_for_date=trade.candidate_pool_size_for_date,
    )


def _to_decimal(value: Decimal | int | str | float) -> Decimal:
    """Convert numeric inputs to Decimal without binary float expansion."""

    return value if isinstance(value, Decimal) else Decimal(str(value))
