"""Portfolio domain models for Veridian Quant v2.

The portfolio layer describes holdings and portfolio state snapshots. These
models do not rank signals, allocate capital, enforce risk limits, or calculate
returns.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class Position:
    """Open portfolio exposure for one symbol."""

    symbol: str
    quantity: int
    average_price: Decimal
    opened_on: date
    strategy_name: str


@dataclass(frozen=True, slots=True)
class PortfolioState:
    """Point-in-time portfolio snapshot."""

    as_of: date
    cash: Decimal
    positions: Mapping[str, Position] = field(
        default_factory=lambda: MappingProxyType({})
    )
