"""Backtesting domain models and planning helpers for Veridian Quant v2."""

from veridian_quant.v2.backtesting.execution import create_open_trade
from veridian_quant.v2.backtesting.exits import resolve_trade_exit
from veridian_quant.v2.backtesting.ledger import (
    EquityPoint,
    PortfolioLedger,
    apply_trade_pnl,
    create_portfolio_ledger,
)
from veridian_quant.v2.backtesting.pnl import TradePnL, calculate_trade_pnl
from veridian_quant.v2.backtesting.sizing import (
    PositionPlan,
    build_position_plan,
)
from veridian_quant.v2.backtesting.setup import TradeSetup, build_trade_setup
from veridian_quant.v2.backtesting.single_symbol import (
    RejectedSignal,
    SingleSymbolBacktestResult,
    run_s1_single_symbol_backtest,
)

__all__ = [
    "PositionPlan",
    "PortfolioLedger",
    "RejectedSignal",
    "SingleSymbolBacktestResult",
    "TradeSetup",
    "TradePnL",
    "EquityPoint",
    "apply_trade_pnl",
    "calculate_trade_pnl",
    "create_portfolio_ledger",
    "create_open_trade",
    "build_position_plan",
    "build_trade_setup",
    "resolve_trade_exit",
    "run_s1_single_symbol_backtest",
]
