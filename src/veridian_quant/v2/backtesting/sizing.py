"""Risk-based position sizing for Veridian Quant v2.

This module converts a passive trade setup into a passive position plan. It
does not create trades, update portfolio state, resolve exits, or calculate PnL.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping

from veridian_quant.v2.backtesting.setup import TradeSetup


@dataclass(frozen=True, slots=True)
class PositionPlan:
    """Passive planned position size for a trade setup."""

    symbol: str
    strategy_name: str
    entry_date: date
    entry_price: Decimal
    stop_loss: Decimal
    target_price: Decimal
    quantity: int
    portfolio_equity: Decimal
    risk_per_trade: Decimal
    risk_amount: Decimal
    per_share_risk: Decimal
    planned_capital: Decimal
    metadata: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({})
    )


def build_position_plan(
    setup: TradeSetup,
    portfolio_equity: Decimal | int | str | float,
    risk_per_trade: Decimal | int | str | float = Decimal("0.01"),
) -> PositionPlan | None:
    """Build a risk-based position plan from a trade setup and equity."""

    portfolio_equity_value = _to_decimal(portfolio_equity)
    risk_per_trade_value = _to_decimal(risk_per_trade)
    if portfolio_equity_value <= 0 or risk_per_trade_value <= 0:
        return None

    per_share_risk = setup.entry_price - setup.stop_loss
    if per_share_risk <= 0:
        return None

    risk_amount = portfolio_equity_value * risk_per_trade_value
    quantity = int(risk_amount // per_share_risk)
    if quantity <= 0:
        return None

    return PositionPlan(
        symbol=setup.symbol,
        strategy_name=setup.strategy_name,
        entry_date=setup.entry_date,
        entry_price=setup.entry_price,
        stop_loss=setup.stop_loss,
        target_price=setup.target_price,
        quantity=quantity,
        portfolio_equity=portfolio_equity_value,
        risk_per_trade=risk_per_trade_value,
        risk_amount=risk_amount,
        per_share_risk=per_share_risk,
        planned_capital=setup.entry_price * quantity,
        metadata=MappingProxyType(dict(setup.metadata)),
    )


def _to_decimal(value: Decimal | int | str | float) -> Decimal:
    """Convert numeric inputs to Decimal without binary float expansion."""

    return value if isinstance(value, Decimal) else Decimal(str(value))
