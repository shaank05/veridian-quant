"""Report contracts for Veridian Quant v2.

Report components format completed research artifacts for review and audit.
They must not run strategies, compute indicators, or calculate backtest
performance.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Sequence

from veridian_quant.v2.backtesting.engine import BacktestResult
from veridian_quant.v2.reporting.metrics import MetricReport


@dataclass(frozen=True, slots=True)
class ReportSection:
    """Named section in a generated research report."""

    title: str
    body: str


@dataclass(frozen=True, slots=True)
class BacktestReport:
    """Structured report for a completed v2 backtest."""

    run_id: str
    metrics: MetricReport
    sections: Sequence[ReportSection] = ()


class ReportRenderer(ABC):
    """Interface for converting backtest results into report artifacts."""

    @abstractmethod
    def render(self, result: BacktestResult) -> BacktestReport:
        """Render a structured report from a completed backtest result."""
