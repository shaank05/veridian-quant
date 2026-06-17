"""Multi-symbol S2 Markov portfolio backtest runner for Veridian Quant v2."""

from dataclasses import dataclass, replace
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
from veridian_quant.v2.backtesting.s2_candidate_ranking import (
    S2_2025_GUARD_VARIANT,
    S2_AVOID_SHALLOW_UPTREND_PULLBACK_VARIANT,
    S2_CANDIDATE_RANKING_2025_GUARD_V1,
    S2_CANDIDATE_RANKING_AVOID_SHALLOW_UPTREND_PULLBACK_V1,
    S2_CANDIDATE_RANKING_NONE,
    rank_s2_entry_candidates,
    validate_s2_candidate_ranking_mode,
)
from veridian_quant.v2.backtesting.s2_signal_context import (
    enrich_s2_signals_with_context,
)
from veridian_quant.v2.backtesting.setup import build_trade_setup
from veridian_quant.v2.backtesting.sizing import build_position_plan
from veridian_quant.v2.data.models import Signal
from veridian_quant.v2.reporting.progress import NullProgressReporter
from veridian_quant.v2.strategies.s2_markov_filters import (
    MARKOV_SIGNAL_FILTER_NONE,
    apply_markov_signal_filter,
    markov_strategy_variant,
    validate_markov_signal_filter,
)
from veridian_quant.v2.strategies.s2_markov_state_transition import (
    STRATEGY_NAME,
    generate_s2_markov_signals,
)


S2_MARKOV_SIGNAL_FILTERED_REASON = "S2_MARKOV_SIGNAL_FILTERED"


@dataclass(frozen=True, slots=True)
class _PendingTrade:
    """Accepted S2 trade waiting for realized ledger application."""

    signal: Signal
    trade: object
    trade_pnl: object


def run_s2_markov_portfolio_backtest(
    data_by_symbol: Mapping[str, pd.DataFrame],
    start_date: date,
    end_date: date,
    starting_equity: Decimal | int | str | float = Decimal("1000000"),
    risk_per_trade: Decimal | int | str | float = Decimal("0.01"),
    max_concurrent_positions: int = 5,
    state_lookback_sessions: int = 252,
    min_state_observations: int = 10,
    forward_return_sessions: int = 10,
    positive_return_threshold_pct: float = 3.0,
    signal_probability_threshold: float = 0.60,
    signal_average_forward_return_threshold_pct: float = 1.0,
    atr_window: int = 14,
    atr_multiplier: Decimal | int | str | float = Decimal("2"),
    reward_risk_ratio: Decimal | int | str | float = Decimal("2"),
    max_holding_sessions: int = 20,
    round_trip_cost_pct: Decimal | int | str | float = Decimal("0.004"),
    progress_reporter: object | None = None,
    markov_signal_filter: str = MARKOV_SIGNAL_FILTER_NONE,
    s2_candidate_ranking_mode: str = S2_CANDIDATE_RANKING_NONE,
    nifty_data: pd.DataFrame | None = None,
) -> PortfolioBacktestResult:
    """Run a deterministic multi-symbol S2 Markov research backtest."""

    markov_signal_filter = validate_markov_signal_filter(markov_signal_filter)
    s2_candidate_ranking_mode = validate_s2_candidate_ranking_mode(
        s2_candidate_ranking_mode
    )
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
            generated_signals = generate_s2_markov_signals(
                symbol=symbol,
                data=backtest_data,
                state_lookback_sessions=state_lookback_sessions,
                min_state_observations=min_state_observations,
                forward_return_sessions=forward_return_sessions,
                positive_return_threshold_pct=positive_return_threshold_pct,
                signal_probability_threshold=signal_probability_threshold,
                signal_average_forward_return_threshold_pct=(
                    signal_average_forward_return_threshold_pct
                ),
            )
            total_generated_signals += len(generated_signals)
            window_signals = [
                signal
                for signal in generated_signals
                if start_date <= signal.generated_on <= end_date
            ]
            if markov_signal_filter == MARKOV_SIGNAL_FILTER_NONE:
                signals.extend(window_signals)
            else:
                for signal in window_signals:
                    decision = apply_markov_signal_filter(
                        signal,
                        markov_signal_filter,
                    )
                    signals.append(decision.signal)
                    if not decision.kept:
                        _append_rejection(
                            rejected_signals,
                            _reject(
                                decision.signal,
                                S2_MARKOV_SIGNAL_FILTERED_REASON,
                            ),
                            progress,
                        )
            progress.info(
                f"Generated S2 signals for {symbol}: rows={len(backtest_data)} "
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
        "Finished S2 signal generation in "
        f"{perf_counter() - signal_generation_started:.2f}s; "
        f"total_generated_signals={total_generated_signals}; "
        f"signals_in_backtest_window={len(signals)}"
    )
    effective_market_end_date = _effective_market_end_date(data_by_valid_symbol)
    ordered_all_signals = tuple(
        sorted(signals, key=lambda signal: (signal.generated_on, signal.symbol))
    )
    ordered_all_signals = enrich_s2_signals_with_context(
        ordered_all_signals,
        data_by_symbol=data_by_valid_symbol,
        nifty_data=nifty_data,
    )
    ordered_execution_signals = tuple(
        signal
        for signal in ordered_all_signals
        if signal.metadata.get("markov_filter_decision") != "filtered"
    )
    ordered_execution_signals = rank_s2_entry_candidates(
        ordered_execution_signals,
        mode=s2_candidate_ranking_mode,
    )
    if s2_candidate_ranking_mode == S2_CANDIDATE_RANKING_NONE:
        result_signals = ordered_all_signals
    else:
        ranked_by_identity = {
            _signal_identity(signal): signal for signal in ordered_execution_signals
        }
        result_signals = tuple(
            sorted(
                (
                    ranked_by_identity.get(_signal_identity(signal), signal)
                    for signal in ordered_all_signals
                ),
                key=_result_signal_sort_key,
            )
        )
    progress.info(f"Total ordered S2 signals: {len(ordered_execution_signals)}")
    pending_trades: list[_PendingTrade] = []
    trades = []
    trade_pnls = []
    execution_started = perf_counter()

    for signal in ordered_execution_signals:
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

        closed_trade = _with_trade_ranking_metadata(closed_trade, signal)
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
        "Finished S2 portfolio execution in "
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
        signals=result_signals,
        rejected_signals=tuple(rejected_signals),
        ledger=ledger,
        strategy_variant=_s2_strategy_variant(
            markov_signal_filter,
            s2_candidate_ranking_mode,
        ),
        candidate_ranking_mode=s2_candidate_ranking_mode,
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
        candidate_ranking_mode=signal.metadata.get("candidate_ranking_mode"),
        candidate_rank=signal.metadata.get("candidate_rank"),
        candidate_score=signal.metadata.get("candidate_score"),
        candidate_pool_size_for_date=signal.metadata.get(
            "candidate_pool_size_for_date"
        ),
        markov_signal_filter=signal.metadata.get("markov_signal_filter"),
        markov_filter_decision=signal.metadata.get("markov_filter_decision"),
    )


def _append_rejection(
    rejected_signals: list[PortfolioRejectedSignal],
    rejected_signal: PortfolioRejectedSignal,
    progress_reporter: object,
) -> None:
    rejected_signals.append(rejected_signal)
    progress_reporter.rejected(rejected_signal)


def _with_trade_ranking_metadata(trade: object, signal: Signal) -> object:
    return replace(
        trade,
        candidate_ranking_mode=signal.metadata.get("candidate_ranking_mode"),
        candidate_rank=signal.metadata.get("candidate_rank"),
        candidate_score=signal.metadata.get("candidate_score"),
        candidate_pool_size_for_date=signal.metadata.get(
            "candidate_pool_size_for_date"
        ),
    )


def _signal_identity(signal: Signal) -> tuple[date, str, str, str]:
    return (
        signal.generated_on,
        signal.symbol,
        signal.reason,
        str(signal.metadata.get("state_label", "")),
    )


def _result_signal_sort_key(signal: Signal) -> tuple[date, int, str]:
    rank = signal.metadata.get("candidate_rank")
    return (
        signal.generated_on,
        int(rank) if rank is not None else 1_000_000,
        signal.symbol,
    )


def _s2_strategy_variant(
    markov_signal_filter: str,
    s2_candidate_ranking_mode: str,
) -> str:
    if s2_candidate_ranking_mode == S2_CANDIDATE_RANKING_2025_GUARD_V1:
        if markov_signal_filter == MARKOV_SIGNAL_FILTER_NONE:
            return S2_2025_GUARD_VARIANT
        return f"{S2_2025_GUARD_VARIANT}__{markov_signal_filter}"
    if (
        s2_candidate_ranking_mode
        == S2_CANDIDATE_RANKING_AVOID_SHALLOW_UPTREND_PULLBACK_V1
    ):
        if markov_signal_filter == MARKOV_SIGNAL_FILTER_NONE:
            return S2_AVOID_SHALLOW_UPTREND_PULLBACK_VARIANT
        return f"{S2_AVOID_SHALLOW_UPTREND_PULLBACK_VARIANT}__{markov_signal_filter}"
    return markov_strategy_variant(STRATEGY_NAME, markov_signal_filter)


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
