"""Trade domain models for Veridian Quant v2 backtesting.

This module captures passive trade lifecycle state used by research backtests.
It intentionally contains no execution simulation, exit decisions, profit and
loss calculations, or broker integration.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum


class TradeStatus(str, Enum):
    """Lifecycle status for a research trade."""

    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ExitReason(str, Enum):
    """Reason a trade left the portfolio."""

    TARGET_HIT = "target_hit"
    STOP_LOSS_HIT = "stop_loss_hit"
    TIME_STOP = "time_stop"
    TARGET_GAP_HIT = "target_gap_hit"
    STOP_GAP_HIT = "stop_gap_hit"
    SIGNAL_EXIT = "signal_exit"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class Trade:
    """Executed research trade record."""

    trade_id: str
    symbol: str
    entry_date: date
    entry_price: Decimal
    quantity: int
    status: TradeStatus
    strategy_name: str
    exit_date: date | None = None
    exit_price: Decimal | None = None
    exit_reason: ExitReason | None = None
