"""Single-symbol S1 backtest runner for Veridian Quant v2.

This module wires existing v2 research components together for one symbol. It
does not load data, export files, run multi-symbol portfolios, or calculate
performance summary metrics.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

import pandas as pd

from veridian_quant.v2.backtesting.execution import create_open_trade
from veridian_quant.v2.backtesting.exits import resolve_trade_exit
from veridian_quant.v2.backtesting.ledger import (
    PortfolioLedger,
    apply_trade_pnl,
    create_portfolio_ledger,
)
from veridian_quant.v2.backtesting.pnl import TradePnL, calculate_trade_pnl
from veridian_quant.v2.backtesting.setup import TradeSetup, build_trade_setup
from veridian_quant.v2.backtesting.sizing import PositionPlan, build_position_plan
from veridian_quant.v2.backtesting.trade import Trade
from veridian_quant.v2.data.models import Signal
from veridian_quant.v2.strategies.s1_zscore_mean_reversion import (
    STRATEGY_NAME,
    generate_s1_zscore_signals,
)


@dataclass(frozen=True, slots=True)
class RejectedSignal:
    """Signal that could not become a completed simulated trade."""

    symbol: str
    signal_date: date
    strategy_name: str
    reason: str


@dataclass(frozen=True, slots=True)
class SingleSymbolBacktestResult:
    """Passive result bundle from one-symbol S1 backtest orchestration."""

    symbol: str
    strategy_name: str
    start_date: date
    end_date: date
    starting_equity: Decimal
    ending_equity: Decimal
    signals: tuple[Signal, ...] = field(default_factory=tuple)
    trade_setups: tuple[TradeSetup, ...] = field(default_factory=tuple)
    position_plans: tuple[PositionPlan, ...] = field(default_factory=tuple)
    trades: tuple[Trade, ...] = field(default_factory=tuple)
    trade_pnls: tuple[TradePnL, ...] = field(default_factory=tuple)
    ledger: PortfolioLedger | None = None
    rejected_signals: tuple[RejectedSignal, ...] = field(default_factory=tuple)


def run_s1_single_symbol_backtest(
    symbol: str,
    data: pd.DataFrame,
    start_date: date,
    end_date: date,
    starting_equity: Decimal | int | str | float = Decimal("1000000"),
    risk_per_trade: Decimal | int | str | float = Decimal("0.01"),
    zscore_window: int = 20,
    entry_threshold: float = -2.0,
    atr_window: int = 14,
    atr_multiplier: Decimal | int | str | float = Decimal("2"),
    reward_risk_ratio: Decimal | int | str | float = Decimal("2"),
    max_holding_sessions: int = 20,
    round_trip_cost_pct: Decimal | int | str | float = Decimal("0.004"),
) -> SingleSymbolBacktestResult:
    """Run a deterministic one-symbol S1 research backtest."""

    _validate_input(data)
    sorted_data = _sort_chronologically(data)
    backtest_data = _rows_on_or_before(sorted_data, end_date)
    signals = tuple(
        signal
        for signal in generate_s1_zscore_signals(
            symbol=symbol,
            data=backtest_data,
            window=zscore_window,
            entry_threshold=entry_threshold,
        )
        if start_date <= signal.generated_on <= end_date
    )

    ledger = create_portfolio_ledger(starting_equity)
    trade_setups: list[TradeSetup] = []
    position_plans: list[PositionPlan] = []
    trades: list[Trade] = []
    trade_pnls: list[TradePnL] = []
    rejected_signals: list[RejectedSignal] = []
    active_trade_exit_date: date | None = None

    for signal in sorted(signals, key=lambda item: item.generated_on):
        if (
            active_trade_exit_date is not None
            and signal.generated_on <= active_trade_exit_date
        ):
            rejected_signals.append(_reject(signal, "ACTIVE_TRADE_EXISTS"))
            continue

        setup = build_trade_setup(
            signal=signal,
            data=backtest_data,
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
            data=backtest_data,
            max_holding_sessions=max_holding_sessions,
            backtest_end_date=end_date,
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

        updated_ledger = apply_trade_pnl(ledger, trade_pnl)
        if updated_ledger is None:
            rejected_signals.append(_reject(signal, "LEDGER_UPDATE_FAILED"))
            continue

        ledger = updated_ledger
        active_trade_exit_date = closed_trade.exit_date
        trade_setups.append(setup)
        position_plans.append(position_plan)
        trades.append(closed_trade)
        trade_pnls.append(trade_pnl)

    return SingleSymbolBacktestResult(
        symbol=symbol,
        strategy_name=STRATEGY_NAME,
        start_date=start_date,
        end_date=end_date,
        starting_equity=ledger.starting_equity,
        ending_equity=ledger.current_equity,
        signals=signals,
        trade_setups=tuple(trade_setups),
        position_plans=tuple(position_plans),
        trades=tuple(trades),
        trade_pnls=tuple(trade_pnls),
        ledger=ledger,
        rejected_signals=tuple(rejected_signals),
    )


def _reject(signal: Signal, reason: str) -> RejectedSignal:
    """Build a rejected-signal record."""

    return RejectedSignal(
        symbol=signal.symbol,
        signal_date=signal.generated_on,
        strategy_name=signal.strategy_name,
        reason=reason,
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
