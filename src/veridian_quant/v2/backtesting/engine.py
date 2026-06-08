"""Backtest engine contracts for Veridian Quant v2.

The engine boundary coordinates research runs and returns passive result
objects. Concrete implementations are intentionally absent from this Phase 1
skeleton.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from veridian_quant.v2.backtesting.portfolio import PortfolioState
from veridian_quant.v2.backtesting.trade import Trade
from veridian_quant.v2.data.models import Signal


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    """Static inputs describing a research backtest run."""

    run_id: str
    start_date: date
    end_date: date
    universe: Sequence[str]
    strategy_name: str


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Passive result bundle produced by a completed backtest."""

    config: BacktestConfig
    final_state: PortfolioState
    signals: Sequence[Signal] = ()
    trades: Sequence[Trade] = ()
    metrics: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({})
    )


class BacktestEngine(ABC):
    """Interface for running v2 research backtests."""

    @abstractmethod
    def run(self, config: BacktestConfig) -> BacktestResult:
        """Run a backtest for the supplied configuration."""
