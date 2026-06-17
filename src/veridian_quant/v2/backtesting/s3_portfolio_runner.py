"""Multi-symbol S3 trend pullback portfolio backtest runner."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from time import perf_counter
from typing import Mapping

import pandas as pd

from veridian_quant.v2.backtesting.execution import create_open_trade
from veridian_quant.v2.backtesting.exits import resolve_trade_exit
from veridian_quant.v2.backtesting.ledger import (
    apply_trade_pnl,
    create_portfolio_ledger,
)
from veridian_quant.v2.backtesting.pnl import calculate_trade_pnl
from veridian_quant.v2.backtesting.portfolio_runner import (
    PortfolioBacktestResult,
    PortfolioRejectedSignal,
)
from veridian_quant.v2.backtesting.setup import build_trade_setup
from veridian_quant.v2.backtesting.sizing import build_position_plan
from veridian_quant.v2.data.models import Signal
from veridian_quant.v2.reporting.progress import NullProgressReporter
from veridian_quant.v2.strategies.s3_trend_pullback_continuation import (
    STRATEGY_NAME,
    generate_s3_trend_pullback_signals,
)


S3_BASELINE_VARIANT = "S3_TREND_PULLBACK_CONTINUATION_BASELINE"
S3_CANDIDATE_RANKING_NONE = "none"


@dataclass(frozen=True, slots=True)
class _PendingTrade:
    """Accepted S3 trade waiting for realized ledger application."""

    signal: Signal
    trade: object
    trade_pnl: object


def run_s3_portfolio_backtest(
    data_by_symbol: Mapping[str, pd.DataFrame],
    start_date: date,
    end_date: date,
    starting_equity: Decimal | int | str | float = Decimal("1000000"),
    risk_per_trade: Decimal | int | str | float = Decimal("0.01"),
    max_concurrent_positions: int = 5,
    sma_fast_window: int = 50,
    sma_slow_window: int = 200,
    sma_slope_lookback: int = 20,
    pullback_lookback: int = 5,
    min_pullback_return_pct: float = -10.0,
    max_pullback_return_pct: float = -1.0,
    max_drawdown_20d_pct: float = -3.0,
    min_drawdown_20d_pct: float = -15.0,
    atr_window: int = 14,
    max_atr_pct: float = 8.0,
    max_atr_expansion_5d_pct: float = 50.0,
    fresh_low_window: int = 60,
    allow_repeated_signals: bool = False,
    require_recovery_day: bool = True,
    atr_multiplier: Decimal | int | str | float = Decimal("2"),
    reward_risk_ratio: Decimal | int | str | float = Decimal("2"),
    max_holding_sessions: int = 20,
    round_trip_cost_pct: Decimal | int | str | float = Decimal("0.004"),
    progress_reporter: object | None = None,
) -> PortfolioBacktestResult:
    """Run a deterministic multi-symbol S3 research portfolio backtest."""

    progress = progress_reporter or NullProgressReporter()
    ledger = create_portfolio_ledger(starting_equity)
    symbols = tuple(sorted(data_by_symbol))
    data_by_valid_symbol: dict[str, pd.DataFrame] = {}
    rejected_signals: list[PortfolioRejectedSignal] = []
    signals: list[Signal] = []
    total_generated_signals = 0
    signal_generation_started = perf_counter()

    for symbol in symbols:
        data = data_by_symbol[symbol]
        try:
            _validate_input(data)
            sorted_data = _sort_chronologically(data)
            backtest_data = _rows_on_or_before(sorted_data, end_date)
            data_by_valid_symbol[symbol] = backtest_data
            symbol_started = perf_counter()
            generated_signals = generate_s3_trend_pullback_signals(
                symbol=symbol,
                data=backtest_data,
                sma_fast_window=sma_fast_window,
                sma_slow_window=sma_slow_window,
                sma_slope_lookback=sma_slope_lookback,
                pullback_lookback=pullback_lookback,
                min_pullback_return_pct=min_pullback_return_pct,
                max_pullback_return_pct=max_pullback_return_pct,
                max_drawdown_20d_pct=max_drawdown_20d_pct,
                min_drawdown_20d_pct=min_drawdown_20d_pct,
                atr_window=atr_window,
                max_atr_pct=max_atr_pct,
                max_atr_expansion_5d_pct=max_atr_expansion_5d_pct,
                fresh_low_window=fresh_low_window,
                allow_repeated_signals=allow_repeated_signals,
                require_recovery_day=require_recovery_day,
            )
            total_generated_signals += len(generated_signals)
            signals.extend(
                signal
                for signal in generated_signals
                if start_date <= signal.generated_on <= end_date
            )
            progress.info(
                f"Generated S3 signals for {symbol}: rows={len(backtest_data)} "
                f"signals={len(generated_signals)} "
                f"in {perf_counter() - symbol_started:.2f}s"
            )
        except ValueError:
            _append_rejection(
                rejected_signals,
                PortfolioRejectedSignal(
                    symbol=symbol,
                    signal_date=None,
                    strategy_name=STRATEGY_NAME,
                    reason="DATA_UNAVAILABLE",
                ),
                progress,
            )

    progress.info(
        "Finished S3 signal generation in "
        f"{perf_counter() - signal_generation_started:.2f}s; "
        f"total_generated_signals={total_generated_signals}; "
        f"signals_in_backtest_window={len(signals)}"
    )
    ordered_signals = tuple(
        sorted(signals, key=lambda signal: (signal.generated_on, signal.symbol))
    )
    effective_market_end_date = _effective_market_end_date(data_by_valid_symbol)
    pending_trades: list[_PendingTrade] = []
    trades = []
    trade_pnls = []
    execution_started = perf_counter()

    for signal in ordered_signals:
        progress.signal(signal)
        ledger, pending_trades = _apply_due_trade_pnls(
            ledger=ledger,
            pending_trades=pending_trades,
            signal_date=signal.generated_on,
            trades=trades,
            trade_pnls=trade_pnls,
            rejected_signals=rejected_signals,
            progress_reporter=progress,
        )

        active_symbols = {pending.signal.symbol for pending in pending_trades}
        if signal.symbol in active_symbols:
            _append_rejection(
                rejected_signals,
                _reject(signal, "ACTIVE_SYMBOL_TRADE_EXISTS"),
                progress,
            )
            continue
        if len(pending_trades) >= max_concurrent_positions:
            _append_rejection(
                rejected_signals,
                _reject(signal, "PORTFOLIO_CAPACITY_FULL"),
                progress,
            )
            continue

        data = data_by_valid_symbol.get(signal.symbol)
        if data is None:
            _append_rejection(
                rejected_signals,
                _reject(signal, "DATA_UNAVAILABLE"),
                progress,
            )
            continue

        setup = build_trade_setup(
            signal=signal,
            data=data,
            atr_window=atr_window,
            atr_multiplier=atr_multiplier,
            reward_risk_ratio=reward_risk_ratio,
        )
        if setup is None:
            _append_rejection(
                rejected_signals,
                _reject(signal, "SETUP_UNAVAILABLE"),
                progress,
            )
            continue

        position_plan = build_position_plan(
            setup=setup,
            portfolio_equity=ledger.current_equity,
            risk_per_trade=risk_per_trade,
        )
        if position_plan is None:
            _append_rejection(
                rejected_signals,
                _reject(signal, "POSITION_PLAN_UNAVAILABLE"),
                progress,
            )
            continue

        open_trade = create_open_trade(position_plan)
        progress.trade(position_plan)
        closed_trade = resolve_trade_exit(
            trade=open_trade,
            position_plan=position_plan,
            data=data,
            max_holding_sessions=max_holding_sessions,
            backtest_end_date=effective_market_end_date,
        )
        if closed_trade is None:
            _append_rejection(
                rejected_signals,
                _reject(signal, "EXIT_UNAVAILABLE"),
                progress,
            )
            continue

        trade_pnl = calculate_trade_pnl(
            trade=closed_trade,
            round_trip_cost_pct=round_trip_cost_pct,
        )
        if trade_pnl is None:
            _append_rejection(
                rejected_signals,
                _reject(signal, "PNL_UNAVAILABLE"),
                progress,
            )
            continue

        pending_trades.append(
            _PendingTrade(signal=signal, trade=closed_trade, trade_pnl=trade_pnl)
        )

    ledger, pending_trades = _apply_due_trade_pnls(
        ledger=ledger,
        pending_trades=pending_trades,
        signal_date=None,
        trades=trades,
        trade_pnls=trade_pnls,
        rejected_signals=rejected_signals,
        progress_reporter=progress,
    )
    progress.info(
        "Finished S3 portfolio execution in "
        f"{perf_counter() - execution_started:.2f}s; "
        f"accepted_trades={len(trades)}; rejected_signals={len(rejected_signals)}"
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
        strategy_variant=S3_BASELINE_VARIANT,
        candidate_ranking_mode=S3_CANDIDATE_RANKING_NONE,
    )


def _apply_due_trade_pnls(
    ledger,
    pending_trades: list[_PendingTrade],
    signal_date: date | None,
    trades: list,
    trade_pnls: list,
    rejected_signals: list[PortfolioRejectedSignal],
    progress_reporter: object,
) -> tuple[object, list[_PendingTrade]]:
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
            _append_rejection(
                rejected_signals,
                _reject(pending.signal, "LEDGER_UPDATE_FAILED"),
                progress_reporter,
            )
            continue

        ledger = updated_ledger
        trades.append(pending.trade)
        trade_pnls.append(pending.trade_pnl)
        progress_reporter.exit(
            pending.trade,
            pending.trade_pnl,
            ledger.current_equity,
        )

    return ledger, remaining


def _reject(signal: Signal, reason: str) -> PortfolioRejectedSignal:
    return PortfolioRejectedSignal(
        symbol=signal.symbol,
        signal_date=signal.generated_on,
        strategy_name=signal.strategy_name,
        reason=reason,
    )


def _append_rejection(
    rejected_signals: list[PortfolioRejectedSignal],
    rejected_signal: PortfolioRejectedSignal,
    progress_reporter: object,
) -> None:
    rejected_signals.append(rejected_signal)
    progress_reporter.rejected(rejected_signal)


def _validate_input(data: pd.DataFrame) -> None:
    required = ["open", "high", "low", "close"]
    missing = [column for column in required if column not in data.columns]
    if "date" not in data.columns and "timestamp" not in data.columns:
        missing.append("date or timestamp")
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")


def _sort_chronologically(data: pd.DataFrame) -> pd.DataFrame:
    date_column = "date" if "date" in data.columns else "timestamp"
    return data.copy(deep=True).sort_values(date_column).reset_index(drop=True)


def _rows_on_or_before(data: pd.DataFrame, end_date: date) -> pd.DataFrame:
    row_dates = data.apply(_row_date, axis=1)
    return data.loc[row_dates <= end_date]


def _effective_market_end_date(
    data_by_valid_symbol: Mapping[str, pd.DataFrame],
) -> date | None:
    dates: list[date] = []
    for data in data_by_valid_symbol.values():
        if data.empty:
            continue
        dates.extend(_row_date(row) for _, row in data.iterrows())
    if not dates:
        return None
    return max(dates)


def _row_date(row: pd.Series) -> date:
    value = row["date"] if "date" in row.index else row["timestamp"]
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()
