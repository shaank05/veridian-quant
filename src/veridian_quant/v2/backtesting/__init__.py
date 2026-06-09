"""Backtesting domain models and planning helpers for Veridian Quant v2."""

from veridian_quant.v2.backtesting.execution import create_open_trade
from veridian_quant.v2.backtesting.exits import resolve_trade_exit
from veridian_quant.v2.backtesting.pnl import TradePnL, calculate_trade_pnl
from veridian_quant.v2.backtesting.sizing import (
    PositionPlan,
    build_position_plan,
)
from veridian_quant.v2.backtesting.setup import TradeSetup, build_trade_setup

__all__ = [
    "PositionPlan",
    "TradeSetup",
    "TradePnL",
    "calculate_trade_pnl",
    "create_open_trade",
    "build_position_plan",
    "build_trade_setup",
    "resolve_trade_exit",
]
