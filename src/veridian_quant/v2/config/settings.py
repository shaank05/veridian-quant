"""Configuration models for Veridian Quant v2.

This module defines immutable settings containers used to pass environment and
research configuration through the v2 system. It intentionally contains no file
loading, database access, or runtime configuration logic.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class DataSettings:
    """Static configuration describing the research data scope."""

    universe_name: str
    start_date: date
    end_date: date
    price_timezone: str = "Asia/Kolkata"


@dataclass(frozen=True, slots=True)
class PortfolioSettings:
    """Static configuration describing portfolio-level research constraints."""

    initial_cash: Decimal
    max_positions: int
    base_currency: str = "INR"


@dataclass(frozen=True, slots=True)
class V2Settings:
    """Top-level settings object for a v2 research run."""

    data: DataSettings
    portfolio: PortfolioSettings
    run_label: str = "v2-research"
