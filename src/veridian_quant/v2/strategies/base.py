"""Strategy layer contracts for Veridian Quant v2.

Strategies consume data and features to produce signal candidates only. They do
not size positions, simulate fills, calculate portfolio metrics, or mutate
external state.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Sequence

from veridian_quant.v2.data.models import MarketBar, Signal
from veridian_quant.v2.features.base import FeatureSet


@dataclass(frozen=True, slots=True)
class StrategyContext:
    """Read-only context supplied to strategy signal generation."""

    as_of: date
    universe: Sequence[str]
    run_label: str


class Strategy(ABC):
    """Base class for v2 signal-generating strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable strategy name used for audit and reporting."""

    @abstractmethod
    def generate_signals(
        self,
        context: StrategyContext,
        bars: Sequence[MarketBar],
        features: Sequence[FeatureSet],
    ) -> Sequence[Signal]:
        """Generate signal candidates for the supplied context."""
