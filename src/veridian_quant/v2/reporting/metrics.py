"""Reporting metric models for Veridian Quant v2.

Metrics in this module summarize already-computed research outputs. They do not
run strategies, resolve trades, load data, or mutate backtest results.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class MetricValue:
    """Single named metric value with optional descriptive metadata."""

    name: str
    value: float | int | str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class MetricReport:
    """Collection of metric values for a research run."""

    run_id: str
    metrics: Mapping[str, MetricValue] = field(
        default_factory=lambda: MappingProxyType({})
    )
    metadata: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({})
    )


@dataclass(frozen=True, slots=True)
class PerformanceSummary:
    """Passive portfolio-level performance summary."""

    strategy_name: str
    start_date: date
    end_date: date
    starting_equity: Decimal
    ending_equity: Decimal
    total_net_pnl: Decimal
    total_return_pct: Decimal
    cagr_pct: Decimal | None
    max_drawdown_pct: Decimal
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: Decimal
    gross_profit: Decimal
    gross_loss: Decimal
    profit_factor: Decimal | None
    expectancy: Decimal | None
    average_win: Decimal | None
    average_loss: Decimal | None
    average_net_pnl: Decimal | None
    best_trade: Decimal | None
    worst_trade: Decimal | None
    average_holding_days: Decimal | None
    total_signals: int
    total_rejected_signals: int
    symbols_count: int


def calculate_performance_summary(result: Any) -> PerformanceSummary:
    """Calculate portfolio summary statistics from a backtest result."""

    trade_pnls = tuple(result.trade_pnls)
    net_pnls = tuple(pnl.net_pnl for pnl in trade_pnls)
    winning_pnls = tuple(pnl for pnl in net_pnls if pnl > 0)
    losing_pnls = tuple(pnl for pnl in net_pnls if pnl < 0)
    total_trades = len(trade_pnls)
    total_net_pnl = sum(net_pnls, Decimal("0"))
    total_return_pct = _pct(result.ending_equity - result.starting_equity, result.starting_equity)
    gross_profit = sum(winning_pnls, Decimal("0"))
    gross_loss = sum(losing_pnls, Decimal("0"))

    return PerformanceSummary(
        strategy_name=result.strategy_name,
        start_date=result.start_date,
        end_date=result.end_date,
        starting_equity=result.starting_equity,
        ending_equity=result.ending_equity,
        total_net_pnl=total_net_pnl,
        total_return_pct=total_return_pct,
        cagr_pct=_cagr_pct(result.start_date, result.end_date, result.starting_equity, result.ending_equity),
        max_drawdown_pct=_max_drawdown_pct(result),
        total_trades=total_trades,
        winning_trades=len(winning_pnls),
        losing_trades=len(losing_pnls),
        win_rate_pct=_ratio_pct(len(winning_pnls), total_trades),
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=_profit_factor(gross_profit, gross_loss),
        expectancy=_average(net_pnls),
        average_win=_average(winning_pnls),
        average_loss=_average(losing_pnls),
        average_net_pnl=_average(net_pnls),
        best_trade=max(net_pnls) if net_pnls else None,
        worst_trade=min(net_pnls) if net_pnls else None,
        average_holding_days=_average_holding_days(trade_pnls),
        total_signals=len(result.signals),
        total_rejected_signals=len(result.rejected_signals),
        symbols_count=len(result.symbols),
    )


def _pct(numerator: Decimal, denominator: Decimal) -> Decimal:
    """Return numerator over denominator as a percentage."""

    if denominator <= 0:
        return Decimal("0")
    return (numerator / denominator) * Decimal("100")


def _ratio_pct(numerator: int, denominator: int) -> Decimal:
    """Return integer ratio as a percentage."""

    if denominator <= 0:
        return Decimal("0")
    return (Decimal(numerator) / Decimal(denominator)) * Decimal("100")


def _cagr_pct(
    start_date: date,
    end_date: date,
    starting_equity: Decimal,
    ending_equity: Decimal,
) -> Decimal | None:
    """Return annualized return using calendar days, or None if invalid."""

    days = (end_date - start_date).days
    if days <= 0 or starting_equity <= 0 or ending_equity <= 0:
        return None

    years = Decimal(days) / Decimal("365")
    cagr = (float(ending_equity / starting_equity) ** float(Decimal("1") / years)) - 1
    return Decimal(str(cagr)) * Decimal("100")


def _max_drawdown_pct(result: Any) -> Decimal:
    """Return maximum realized equity drawdown as a positive percentage."""

    ledger = result.ledger
    if ledger is None or not ledger.equity_curve:
        return Decimal("0")

    peak = result.starting_equity
    max_drawdown = Decimal("0")
    for point in ledger.equity_curve:
        equity = point.equity
        if equity > peak:
            peak = equity
        if peak > 0:
            drawdown = ((peak - equity) / peak) * Decimal("100")
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    return max_drawdown


def _profit_factor(
    gross_profit: Decimal,
    gross_loss: Decimal,
) -> Decimal | None:
    """Return gross profit divided by absolute gross loss."""

    if gross_loss == 0:
        return None
    return gross_profit / abs(gross_loss)


def _average(values: tuple[Decimal, ...]) -> Decimal | None:
    """Return Decimal average, or None for empty inputs."""

    if not values:
        return None
    return sum(values, Decimal("0")) / Decimal(len(values))


def _average_holding_days(trade_pnls: tuple[Any, ...]) -> Decimal | None:
    """Return average calendar holding period in days."""

    if not trade_pnls:
        return None
    holding_days = [
        Decimal((pnl.exit_date - pnl.entry_date).days)
        for pnl in trade_pnls
    ]
    return sum(holding_days, Decimal("0")) / Decimal(len(holding_days))
