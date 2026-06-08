"""Feature layer base abstractions for Veridian Quant v2.

Feature components transform raw market observations into research features.
They must not emit trade signals, allocate capital, or perform backtest
evaluation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from veridian_quant.v2.data.models import MarketBar


@dataclass(frozen=True, slots=True)
class FeatureSet:
    """Named feature values for one symbol on one research date."""

    symbol: str
    observed_on: date
    values: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({})
    )


class FeatureTransformer(ABC):
    """Base class for feature generators."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable feature transformer name used in audit output."""

    @abstractmethod
    def transform(self, bars: Sequence[MarketBar]) -> Sequence[FeatureSet]:
        """Transform market bars into feature sets."""
