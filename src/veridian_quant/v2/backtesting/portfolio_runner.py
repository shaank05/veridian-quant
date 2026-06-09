"""Multi-symbol S1 portfolio backtest runner for Veridian Quant v2.

This module orchestrates existing v2 research components across in-memory
one-symbol OHLCV dataframes. It does not load databases, export files, calculate
performance metrics, or add non-S1 filters.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Mapping

import pandas as pd

from veridian_quant.v2.backtesting.execution import create_open_trade
from veridian_quant.v2.backtesting.exits import resolve_trade_exit
from veridian_quant.v2.backtesting.ledger import (
    PortfolioLedger,
    apply_trade_pnl,
    create_portfolio_ledger,
)
from veridian_quant.v2.backtesting.pnl import TradePnL, calculate_trade_pnl
from veridian_quant.v2.backtesting.setup import build_trade_setup
from veridian_quant.v2.backtesting.sizing import build_position_plan
from veridian_quant.v2.backtesting.trade import Trade
from veridian_quant.v2.data.models import Signal
from veridian_quant.v2.strategies.s1_zscore_mean_reversion import (
    STRATEGY_NAME,
    generate_s1_zscore_signals,
)


@dataclass(frozen=True, slots=True)
class PortfolioRejectedSignal:
    """Portfolio-level signal rejection record."""

    symbol: str
    signal_date: date | None
    strategy_name: str
    reason: str


@dataclass(frozen=True, slots=True)
class PortfolioBacktestResult:
    """Passive result bundle from multi-symbol S1 portfolio orchestration."""

    strategy_name: str
    start_date: date
    end_date: date
    starting_equity: Decimal
    ending_equity: Decimal
    symbols: tuple[str, ...]
    trade_pnls: tuple[TradePnL, ...] = field(default_factory=tuple)
    trades: tuple[Trade, ...] = field(default_factory=tuple)
    signals: tuple[Signal, ...] = field(default_factory=tuple)
    rejected_signals: tuple[PortfolioRejectedSignal, ...] = field(
        default_factory=tuple
    )
    ledger: PortfolioLedger | None = None


@dataclass(frozen=True, slots=True)
class _PendingTrade:
    """Accepted trade waiting for realized ledger application."""

    signal: Signal
    trade: Trade
    trade_pnl: TradePnL


def run_s1_portfolio_backtest(
    data_by_symbol: Mapping[str, pd.DataFrame],
    start_date: date,
    end_date: date,
    starting_equity: Decimal | int | str | float = Decimal("1000000"),
    risk_per_trade: Decimal | int | str | float = Decimal("0.01"),
    max_concurrent_positions: int = 5,
    zscore_window: int = 20,
    entry_threshold: float = -2.0,
    atr_window: int = 14,
    atr_multiplier: Decimal | int | str | float = Decimal("2"),
    reward_risk_ratio: Decimal | int | str | float = Decimal("2"),
    max_holding_sessions: int = 20,
    round_trip_cost_pct: Decimal | int | str | float = Decimal("0.004"),
) -> PortfolioBacktestResult:
    """Run a deterministic multi-symbol S1 research portfolio backtest."""

    ledger = create_portfolio_ledger(starting_equity)
    symbols = tuple(sorted(data_by_symbol))
    data_by_valid_symbol: dict[str, pd.DataFrame] = {}
    rejected_signals: list[PortfolioRejectedSignal] = []
    signals: list[Signal] = []

    for symbol in symbols:
        data = data_by_symbol[symbol]
        try:
            _validate_input(data)
            sorted_data = _sort_chronologically(data)
            backtest_data = _rows_on_or_before(sorted_data, end_date)
            data_by_valid_symbol[symbol] = backtest_data
            signals.extend(
                signal
                for signal in generate_s1_zscore_signals(
                    symbol=symbol,
                    data=backtest_data,
                    window=zscore_window,
                    entry_threshold=entry_threshold,
                )
                if start_date <= signal.generated_on <= end_date
            )
        except ValueError:
            rejected_signals.append(
                PortfolioRejectedSignal(
                    symbol=symbol,
                    signal_date=None,
                    strategy_name=STRATEGY_NAME,
                    reason="DATA_UNAVAILABLE",
                )
            )

    ordered_signals = tuple(sorted(signals, key=_signal_sort_key))
    pending_trades: list[_PendingTrade] = []
    trades: list[Trade] = []
    trade_pnls: list[TradePnL] = []

    for signal in ordered_signals:
        ledger, pending_trades = _apply_due_trade_pnls(
            ledger=ledger,
            pending_trades=pending_trades,
            signal_date=signal.generated_on,
            trades=trades,
            trade_pnls=trade_pnls,
            rejected_signals=rejected_signals,
        )

        active_symbols = {pending.signal.symbol for pending in pending_trades}
        if signal.symbol in active_symbols:
            rejected_signals.append(_reject(signal, "ACTIVE_SYMBOL_TRADE_EXISTS"))
            continue
        if len(pending_trades) >= max_concurrent_positions:
            rejected_signals.append(_reject(signal, "PORTFOLIO_CAPACITY_FULL"))
            continue

        data = data_by_valid_symbol.get(signal.symbol)
        if data is None:
            rejected_signals.append(_reject(signal, "DATA_UNAVAILABLE"))
            continue

        setup = build_trade_setup(
            signal=signal,
            data=data,
            atr_window=atr_window,
            atr_multiplier=atr_multiplier,
            reward_risk_ratio=reward_risk_ratio,
        )
        if setup is None:
            rejected_signals.append(_reject(signal, "SETUP_UNAVAILABLE"))
            continue

        position_plan = build_position_plan(
            setup=setup,
            portfolio_equity=ledger.current_equity,
            risk_per_trade=risk_per_trade,
        )
        if position_plan is None:
            rejected_signals.append(_reject(signal, "POSITION_PLAN_UNAVAILABLE"))
            continue

        open_trade = create_open_trade(position_plan)
        closed_trade = resolve_trade_exit(
            trade=open_trade,
            position_plan=position_plan,
            data=data,
            max_holding_sessions=max_holding_sessions,
        )
        if closed_trade is None:
            rejected_signals.append(_reject(signal, "EXIT_UNAVAILABLE"))
            continue

        trade_pnl = calculate_trade_pnl(
            trade=closed_trade,
            round_trip_cost_pct=round_trip_cost_pct,
        )
        if trade_pnl is None:
            rejected_signals.append(_reject(signal, "PNL_UNAVAILABLE"))
            continue

        pending_trades.append(
            _PendingTrade(
                signal=signal,
                trade=closed_trade,
                trade_pnl=trade_pnl,
            )
        )

    ledger, pending_trades = _apply_due_trade_pnls(
        ledger=ledger,
        pending_trades=pending_trades,
        signal_date=None,
        trades=trades,
        trade_pnls=trade_pnls,
        rejected_signals=rejected_signals,
    )

    return PortfolioBacktestResult(
        strategy_name=STRATEGY_NAME,
        start_date=start_date,
        end_date=end_date,
        starting_equity=ledger.starting_equity,
        ending_equity=ledger.current_equity,
        symbols=symbols,
        trade_pnls=tuple(trade_pnls),
        trades=tuple(trades),
        signals=ordered_signals,
        rejected_signals=tuple(rejected_signals),
        ledger=ledger,
    )


def _apply_due_trade_pnls(
    ledger: PortfolioLedger,
    pending_trades: list[_PendingTrade],
    signal_date: date | None,
    trades: list[Trade],
    trade_pnls: list[TradePnL],
    rejected_signals: list[PortfolioRejectedSignal],
) -> tuple[PortfolioLedger, list[_PendingTrade]]:
    """Apply pending trade PnLs that closed before the signal date."""

    remaining: list[_PendingTrade] = []
    for pending in sorted(pending_trades, key=lambda item: item.trade.exit_date):
        exit_date = pending.trade.exit_date
        is_due = signal_date is None or (
            exit_date is not None and exit_date < signal_date
        )
        if not is_due:
            remaining.append(pending)
            continue

        updated_ledger = apply_trade_pnl(ledger, pending.trade_pnl)
        if updated_ledger is None:
            rejected_signals.append(
                _reject(pending.signal, "LEDGER_UPDATE_FAILED")
            )
            continue

        ledger = updated_ledger
        trades.append(pending.trade)
        trade_pnls.append(pending.trade_pnl)

    return ledger, remaining


def _reject(signal: Signal, reason: str) -> PortfolioRejectedSignal:
    """Build a portfolio-level rejected-signal record."""

    return PortfolioRejectedSignal(
        symbol=signal.symbol,
        signal_date=signal.generated_on,
        strategy_name=signal.strategy_name,
        reason=reason,
    )


def _signal_sort_key(signal: Signal) -> tuple[date, float, str]:
    """Sort by date, then most negative z-score, then symbol."""

    return (
        signal.generated_on,
        float(signal.metadata.get("z_score", 0.0)),
        signal.symbol,
    )


def _validate_input(data: pd.DataFrame) -> None:
    """Validate the minimum OHLC columns needed by the runner."""

    required = ["open", "high", "low", "close"]
    missing = [column for column in required if column not in data.columns]
    if "date" not in data.columns and "timestamp" not in data.columns:
        missing.append("date or timestamp")
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")


def _sort_chronologically(data: pd.DataFrame) -> pd.DataFrame:
    """Return a date-sorted copy of the input dataframe."""

    date_column = "date" if "date" in data.columns else "timestamp"
    return data.copy(deep=True).sort_values(date_column).reset_index(drop=True)


def _rows_on_or_before(data: pd.DataFrame, end_date: date) -> pd.DataFrame:
    """Return rows through the end date while preserving pre-start lookback."""

    row_dates = data.apply(_row_date, axis=1)
    return data.loc[row_dates <= end_date]


def _row_date(row: pd.Series) -> date:
    """Return a Python date from the row's date or timestamp field."""

    value = row["date"] if "date" in row.index else row["timestamp"]
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()
