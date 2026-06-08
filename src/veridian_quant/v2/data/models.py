"""Domain models for v2 market data and strategy signals.

The data layer owns canonical representations of instruments, OHLCV bars, and
signals emitted by strategies. These models are deliberately passive containers
and do not calculate indicators, rank candidates, or make trading decisions.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


class SignalType(str, Enum):
    """Supported signal directions for research candidates."""

    LONG = "long"
    SHORT = "short"
    EXIT = "exit"
    HOLD = "hold"


@dataclass(frozen=True, slots=True)
class Instrument:
    """Tradable security identifier and descriptive metadata."""

    symbol: str
    exchange: str
    name: str | None = None
    sector: str | None = None


@dataclass(frozen=True, slots=True)
class MarketBar:
    """Single daily OHLCV observation for one instrument."""

    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


@dataclass(frozen=True, slots=True)
class Signal:
    """Strategy output describing a trade candidate without sizing or execution."""

    symbol: str
    signal_type: SignalType
    generated_on: date
    strategy_name: str
    reason: str
    metadata: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({})
    )
