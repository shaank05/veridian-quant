"""S1 strategy contract for Veridian Quant v2.

S1 is represented here only as a named strategy boundary. Indicator
calculation, signal rules, ranking, exits, and portfolio behavior are outside
the Phase 1 architecture skeleton.
"""

from abc import abstractmethod
from typing import Sequence

from veridian_quant.v2.data.models import MarketBar, Signal
from veridian_quant.v2.features.base import FeatureSet
from veridian_quant.v2.strategies.base import Strategy, StrategyContext


class S1ZScoreMeanReversionStrategy(Strategy):
    """Abstract boundary for the S1 mean-reversion research candidate."""

    @property
    def name(self) -> str:
        """Return the stable S1 strategy identifier."""

        return "s1_zscore_mean_reversion"

    @abstractmethod
    def generate_signals(
        self,
        context: StrategyContext,
        bars: Sequence[MarketBar],
        features: Sequence[FeatureSet],
    ) -> Sequence[Signal]:
        """Generate S1 signal candidates."""
