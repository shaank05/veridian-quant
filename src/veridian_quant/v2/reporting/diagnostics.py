"""Diagnostic summaries for completed Veridian Quant v2 portfolio backtests.

These helpers summarize already-computed backtest outputs. They do not run
strategies, generate signals, size positions, resolve exits, or calculate PnL.
"""

from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
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
R_MULTIPLE_SUMMARY_COLUMNS = [
    "trades_with_r",
    "winning_trades",
    "losing_trades",
    "average_r",
    "average_winner_r",
    "average_loser_r",
    "best_r",
    "worst_r",
    "positive_r_rate_pct",
]
R_MULTIPLE_BY_EXIT_REASON_COLUMNS = [
    "exit_reason",
    "trades_with_r",
    "average_r",
    "average_winner_r",
    "average_loser_r",
    "best_r",
    "worst_r",
]
R_MULTIPLE_GROUP_COLUMNS = [
    "trades_with_r",
    "winning_trades",
    "losing_trades",
    "positive_r_rate_pct",
    "average_r",
    "average_winner_r",
    "average_loser_r",
    "best_r",
    "worst_r",
]
R_MULTIPLE_BY_SYMBOL_COLUMNS = [
    "symbol",
    *R_MULTIPLE_GROUP_COLUMNS,
]
R_MULTIPLE_BY_YEAR_COLUMNS = [
    "year",
    *R_MULTIPLE_GROUP_COLUMNS,
]
R_MULTIPLE_BY_SYMBOL_YEAR_COLUMNS = [
    "symbol",
    "year",
    *R_MULTIPLE_GROUP_COLUMNS,
]


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


def build_r_multiple_summary_rows(result: Any) -> list[dict[str, object]]:
    """Return one R-multiple summary row when risk metadata is available."""

    r_values = _r_multiple_values(result.trade_pnls)
    if not r_values:
        return []

    return [_r_multiple_group_summary(r_values)]


def build_r_multiple_by_exit_reason_rows(result: Any) -> list[dict[str, object]]:
    """Return R-multiple summary rows grouped by exit reason."""

    grouped: dict[str, list[Decimal]] = defaultdict(list)
    for pnl in result.trade_pnls:
        r_multiple = _r_multiple(pnl)
        if r_multiple is None:
            continue
        grouped[_enum_value(pnl.exit_reason)].append(r_multiple)

    return [
        {
            "exit_reason": exit_reason,
            **_r_multiple_group_summary(tuple(r_values)),
        }
        for exit_reason, r_values in sorted(grouped.items())
    ]


def build_r_multiple_by_symbol_rows(result: Any) -> list[dict[str, object]]:
    """Return R-multiple summary rows grouped by symbol."""

    grouped: dict[str, list[Decimal]] = defaultdict(list)
    for pnl in result.trade_pnls:
        r_multiple = _r_multiple(pnl)
        if r_multiple is None:
            continue
        grouped[pnl.symbol].append(r_multiple)

    return [
        {
            "symbol": symbol,
            **_r_multiple_group_summary(tuple(r_values)),
        }
        for symbol, r_values in sorted(grouped.items())
    ]


def build_r_multiple_by_year_rows(result: Any) -> list[dict[str, object]]:
    """Return R-multiple summary rows grouped by trade exit year."""

    grouped: dict[int, list[Decimal]] = defaultdict(list)
    for pnl in result.trade_pnls:
        r_multiple = _r_multiple(pnl)
        if r_multiple is None:
            continue
        grouped[pnl.exit_date.year].append(r_multiple)

    return [
        {
            "year": year,
            **_r_multiple_group_summary(tuple(r_values)),
        }
        for year, r_values in sorted(grouped.items())
    ]


def build_r_multiple_by_symbol_year_rows(result: Any) -> list[dict[str, object]]:
    """Return R-multiple summary rows grouped by symbol and trade exit year."""

    grouped: dict[tuple[str, int], list[Decimal]] = defaultdict(list)
    for pnl in result.trade_pnls:
        r_multiple = _r_multiple(pnl)
        if r_multiple is None:
            continue
        grouped[(pnl.symbol, pnl.exit_date.year)].append(r_multiple)

    return [
        {
            "symbol": symbol,
            "year": year,
            **_r_multiple_group_summary(tuple(r_values)),
        }
        for (symbol, year), r_values in sorted(grouped.items())
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


def _r_multiple_values(pnls: tuple[Any, ...]) -> tuple[Decimal, ...]:
    """Return calculable R multiples for trade PnLs with risk metadata."""

    r_values = []
    for pnl in pnls:
        r_multiple = _r_multiple(pnl)
        if r_multiple is not None:
            r_values.append(r_multiple)
    return tuple(r_values)


def _r_multiple(pnl: Any) -> Decimal | None:
    """Return realized R multiple, or None when initial risk is unavailable."""

    initial_risk = _initial_risk_amount(pnl)
    if initial_risk is None or initial_risk <= 0:
        return None
    return pnl.net_pnl / initial_risk


def _initial_risk_amount(pnl: Any) -> Decimal | None:
    """Return planned initial risk from direct fields or legacy metadata."""

    initial_risk = _to_decimal(getattr(pnl, "initial_risk_amount", None))
    if initial_risk is not None:
        return initial_risk

    per_share_risk = _per_share_risk(pnl)
    quantity = _to_decimal(getattr(pnl, "quantity", None))
    if per_share_risk is None or quantity is None:
        return None
    return quantity * per_share_risk


def _per_share_risk(pnl: Any) -> Decimal | None:
    """Return per-share planned risk from direct fields or legacy metadata."""

    direct_per_share_risk = _to_decimal(getattr(pnl, "per_share_risk", None))
    if direct_per_share_risk is not None:
        return direct_per_share_risk

    metadata = getattr(pnl, "metadata", None)
    if metadata is None or not hasattr(metadata, "get"):
        return None

    per_share_risk = _to_decimal(metadata.get("per_share_risk"))
    if per_share_risk is not None:
        return per_share_risk

    stop_loss = _to_decimal(metadata.get("stop_loss"))
    entry_price = _to_decimal(getattr(pnl, "entry_price", None))
    if stop_loss is None or entry_price is None:
        return None
    return entry_price - stop_loss


def _r_multiple_group_summary(r_values: tuple[Decimal, ...]) -> dict[str, object]:
    """Return common R-multiple summary fields for a non-empty group."""

    winning_r = tuple(r_value for r_value in r_values if r_value > 0)
    losing_r = tuple(r_value for r_value in r_values if r_value < 0)
    return {
        "trades_with_r": len(r_values),
        "winning_trades": len(winning_r),
        "losing_trades": len(losing_r),
        "positive_r_rate_pct": _ratio_pct(len(winning_r), len(r_values)),
        "average_r": _average(r_values),
        "average_winner_r": _average(winning_r),
        "average_loser_r": _average(losing_r),
        "best_r": max(r_values),
        "worst_r": min(r_values),
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


def _to_decimal(value: Any) -> Decimal | None:
    """Convert a numeric value to Decimal, or None for unavailable values."""

    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _enum_value(value: Any) -> Any:
    """Return enum value when present, otherwise the original value."""

    return getattr(value, "value", value)
