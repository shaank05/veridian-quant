"""Data access contracts for Veridian Quant v2.

This module defines interfaces that upstream data providers and repositories
must satisfy. Implementations may live elsewhere, but v2 domain layers should
depend on these contracts rather than concrete storage or vendor APIs.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Iterable, Sequence

from veridian_quant.v2.data.models import Instrument, MarketBar


class MarketDataProvider(ABC):
    """Interface for retrieving market data used by v2 research components."""

    @abstractmethod
    def list_instruments(self) -> Sequence[Instrument]:
        """Return the instruments available to the research universe."""

    @abstractmethod
    def get_bars(
        self,
        symbols: Iterable[str],
        start_date: date,
        end_date: date,
    ) -> Sequence[MarketBar]:
        """Return OHLCV bars for symbols in the requested date range."""


class CorporateActionProvider(ABC):
    """Interface for retrieving corporate action metadata when available."""

    @abstractmethod
    def has_adjustment_data(self, symbol: str) -> bool:
        """Return whether adjustment metadata exists for a symbol."""
