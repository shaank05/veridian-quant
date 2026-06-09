"""Diagnostic summaries for completed Veridian Quant v2 portfolio backtests.

These helpers summarize already-computed backtest outputs. They do not run
strategies, generate signals, size positions, resolve exits, or calculate PnL.
"""

from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any


EXIT_REASON_SUMMARY_COLUMNS = [
    "exit_reason",
    "trades",
    "wins",
    "losses",
    "win_rate_pct",
    "gross_profit",
    "gross_loss",
    "net_pnl",
    "average_net_pnl",
    "best_trade",
    "worst_trade",
]
SYMBOL_SUMMARY_COLUMNS = [
    "symbol",
    "trades",
    "wins",
    "losses",
    "win_rate_pct",
    "gross_profit",
    "gross_loss",
    "net_pnl",
    "average_net_pnl",
    "best_trade",
    "worst_trade",
    "average_holding_days",
]
YEARLY_SUMMARY_COLUMNS = [
    "year",
    "trades",
    "wins",
    "losses",
    "win_rate_pct",
    "gross_profit",
    "gross_loss",
    "net_pnl",
    "average_net_pnl",
    "best_trade",
    "worst_trade",
]
REJECTION_SUMMARY_COLUMNS = ["reason", "count"]


def build_exit_reason_summary_rows(result: Any) -> list[dict[str, object]]:
    """Return trade PnL summary rows grouped by exit reason."""

    grouped: dict[str, list[Any]] = defaultdict(list)
    for pnl in result.trade_pnls:
        grouped[_enum_value(pnl.exit_reason)].append(pnl)

    return [
        {
            "exit_reason": exit_reason,
            **_pnl_summary(pnls),
        }
        for exit_reason, pnls in sorted(grouped.items())
    ]


def build_symbol_summary_rows(result: Any) -> list[dict[str, object]]:
    """Return trade PnL summary rows grouped by symbol."""

    grouped: dict[str, list[Any]] = defaultdict(list)
    for pnl in result.trade_pnls:
        grouped[pnl.symbol].append(pnl)

    return [
        {
            "symbol": symbol,
            **_pnl_summary(pnls),
            "average_holding_days": _average_holding_days(pnls),
        }
        for symbol, pnls in sorted(grouped.items())
    ]


def build_yearly_summary_rows(result: Any) -> list[dict[str, object]]:
    """Return trade PnL summary rows grouped by trade exit year."""

    grouped: dict[int, list[Any]] = defaultdict(list)
    for pnl in result.trade_pnls:
        grouped[pnl.exit_date.year].append(pnl)

    return [
        {
            "year": year,
            **_pnl_summary(pnls),
        }
        for year, pnls in sorted(grouped.items())
    ]


def build_rejection_summary_rows(result: Any) -> list[dict[str, object]]:
    """Return rejected signal counts grouped by rejection reason."""

    counts = Counter(rejected.reason for rejected in result.rejected_signals)
    return [
        {
            "reason": reason,
            "count": count,
        }
        for reason, count in sorted(counts.items())
    ]


def _pnl_summary(pnls: list[Any]) -> dict[str, object]:
    """Return common net PnL summary fields for a non-empty group."""

    net_pnls = tuple(pnl.net_pnl for pnl in pnls)
    winning_pnls = tuple(net_pnl for net_pnl in net_pnls if net_pnl > 0)
    losing_pnls = tuple(net_pnl for net_pnl in net_pnls if net_pnl < 0)
    trades = len(net_pnls)
    gross_profit = sum(winning_pnls, Decimal("0"))
    gross_loss = sum(losing_pnls, Decimal("0"))
    net_pnl = sum(net_pnls, Decimal("0"))

    return {
        "trades": trades,
        "wins": len(winning_pnls),
        "losses": len(losing_pnls),
        "win_rate_pct": _ratio_pct(len(winning_pnls), trades),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "net_pnl": net_pnl,
        "average_net_pnl": _average(net_pnls),
        "best_trade": max(net_pnls),
        "worst_trade": min(net_pnls),
    }


def _average(values: tuple[Decimal, ...]) -> Decimal | None:
    """Return Decimal average, or None for empty inputs."""

    if not values:
        return None
    return sum(values, Decimal("0")) / Decimal(len(values))


def _average_holding_days(pnls: list[Any]) -> Decimal | None:
    """Return average calendar holding period in days."""

    if not pnls:
        return None
    holding_days = tuple(
        Decimal((pnl.exit_date - pnl.entry_date).days)
        for pnl in pnls
    )
    return _average(holding_days)


def _ratio_pct(numerator: int, denominator: int) -> Decimal:
    """Return integer ratio as a percentage."""

    if denominator <= 0:
        return Decimal("0")
    return (Decimal(numerator) / Decimal(denominator)) * Decimal("100")


def _enum_value(value: Any) -> Any:
    """Return enum value when present, otherwise the original value."""

    return getattr(value, "value", value)
