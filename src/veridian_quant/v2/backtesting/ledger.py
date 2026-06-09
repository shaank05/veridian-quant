"""Passive portfolio ledger accounting for Veridian Quant v2 backtests.

This module tracks realized closed-trade PnL and resulting portfolio equity.
It does not size positions, resolve exits, calculate performance metrics, or
run a backtest engine.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from veridian_quant.v2.backtesting.pnl import TradePnL


@dataclass(frozen=True, slots=True)
class EquityPoint:
    """Point on the realized equity curve."""

    date: date
    equity: Decimal
    realized_pnl: Decimal


@dataclass(frozen=True, slots=True)
class PortfolioLedger:
    """Passive realized-PnL portfolio ledger."""

    starting_equity: Decimal
    current_equity: Decimal
    realized_pnl: Decimal
    trade_pnls: tuple[TradePnL, ...] = field(default_factory=tuple)
    equity_curve: tuple[EquityPoint, ...] = field(default_factory=tuple)


def create_portfolio_ledger(
    starting_equity: Decimal | int | str | float,
) -> PortfolioLedger:
    """Create an empty realized-PnL ledger with positive starting equity."""

    starting_equity_value = _to_decimal(starting_equity)
    if starting_equity_value <= 0:
        raise ValueError("starting_equity must be positive")

    return PortfolioLedger(
        starting_equity=starting_equity_value,
        current_equity=starting_equity_value,
        realized_pnl=Decimal("0"),
    )


def apply_trade_pnl(
    ledger: PortfolioLedger,
    trade_pnl: TradePnL,
) -> PortfolioLedger | None:
    """Return a new ledger snapshot after applying one realized trade PnL."""

    current_equity = ledger.current_equity + trade_pnl.net_pnl
    if current_equity <= 0:
        return None

    realized_pnl = ledger.realized_pnl + trade_pnl.net_pnl
    equity_point = EquityPoint(
        date=trade_pnl.exit_date,
        equity=current_equity,
        realized_pnl=realized_pnl,
    )

    return PortfolioLedger(
        starting_equity=ledger.starting_equity,
        current_equity=current_equity,
        realized_pnl=realized_pnl,
        trade_pnls=ledger.trade_pnls + (trade_pnl,),
        equity_curve=ledger.equity_curve + (equity_point,),
    )


def _to_decimal(value: Decimal | int | str | float) -> Decimal:
    """Convert numeric inputs to Decimal without binary float expansion."""

    return value if isinstance(value, Decimal) else Decimal(str(value))
