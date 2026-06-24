"""Contracts for benchmark, sector, and market-cap context data.

These models are passive data-layer containers. They intentionally do not
ingest vendor data, calculate benchmark features, or alter strategy behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Iterable


class IndexType(str, Enum):
    """Supported market index categories."""

    BROAD_MARKET = "broad_market"
    SECTOR = "sector"
    CAP_SEGMENT = "cap_segment"
    THEMATIC = "thematic"
    OTHER = "other"


class MarketCapBucket(str, Enum):
    """Supported market-cap context buckets."""

    LARGE_CAP = "large_cap"
    MID_CAP = "mid_cap"
    SMALL_CAP = "small_cap"
    MICRO_CAP = "micro_cap"
    UNKNOWN = "unknown"


class ClassificationMode(str, Enum):
    """Whether a classification is point-in-time or a labelled fallback."""

    POINT_IN_TIME = "point_in_time"
    STATIC_CURRENT = "static_current"
    MANUAL = "manual"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class MarketIndex:
    """Benchmark, sector, cap-segment, or thematic index metadata."""

    index_symbol: str
    index_name: str
    index_type: IndexType | str
    source: str
    is_active: bool = True
    exchange: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "index_symbol", normalize_index_symbol(self.index_symbol))
        object.__setattr__(self, "index_name", _non_empty_text(self.index_name, "index_name"))
        object.__setattr__(self, "source", _non_empty_text(self.source, "source"))
        object.__setattr__(self, "index_type", _coerce_enum(self.index_type, IndexType, "index_type"))


@dataclass(frozen=True, slots=True)
class MarketIndexBar:
    """Single daily OHLC observation for one market index."""

    index_symbol: str
    date: date | datetime | str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    source: str
    volume: int | None = None
    ingested_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "index_symbol", normalize_index_symbol(self.index_symbol))
        object.__setattr__(self, "date", _normalize_date(self.date, "date"))
        object.__setattr__(self, "source", _non_empty_text(self.source, "source"))

        open_price = _positive_decimal(self.open, "open")
        high_price = _positive_decimal(self.high, "high")
        low_price = _positive_decimal(self.low, "low")
        close_price = _positive_decimal(self.close, "close")

        if high_price < max(open_price, close_price, low_price):
            raise ValueError("high must be greater than or equal to open, close, and low")
        if low_price > min(open_price, close_price, high_price):
            raise ValueError("low must be less than or equal to open, close, and high")
        if self.volume is not None and self.volume < 0:
            raise ValueError("volume must be greater than or equal to 0")

        object.__setattr__(self, "open", open_price)
        object.__setattr__(self, "high", high_price)
        object.__setattr__(self, "low", low_price)
        object.__setattr__(self, "close", close_price)


@dataclass(frozen=True, slots=True)
class InstrumentClassification:
    """Sector, industry, market-cap, and index-membership context for a stock."""

    symbol: str
    sector: str
    industry: str | None
    market_cap_bucket: MarketCapBucket | str
    effective_from: date | datetime | str
    source: str
    index_membership: tuple[str, ...] | list[str] | str = field(default_factory=tuple)
    effective_to: date | datetime | str | None = None
    classification_mode: ClassificationMode | str = ClassificationMode.UNKNOWN
    notes: str | None = None
    instrument_key: str | None = None
    isin: str | None = None
    company_name: str | None = None
    basic_industry: str | None = None
    ingested_at: datetime | None = None

    def __post_init__(self) -> None:
        effective_from = _normalize_date(self.effective_from, "effective_from")
        effective_to = (
            _normalize_date(self.effective_to, "effective_to")
            if self.effective_to is not None
            else None
        )
        if effective_to is not None and effective_to < effective_from:
            raise ValueError("effective_to must be greater than or equal to effective_from")

        object.__setattr__(self, "symbol", _normalize_symbol(self.symbol, "symbol"))
        object.__setattr__(self, "sector", _non_empty_text(self.sector, "sector"))
        object.__setattr__(
            self,
            "market_cap_bucket",
            normalize_market_cap_bucket(self.market_cap_bucket),
        )
        object.__setattr__(self, "effective_from", effective_from)
        object.__setattr__(self, "effective_to", effective_to)
        object.__setattr__(self, "source", _non_empty_text(self.source, "source"))
        object.__setattr__(
            self,
            "index_membership",
            tuple(normalize_index_symbol(index) for index in _as_index_iterable(self.index_membership)),
        )
        object.__setattr__(
            self,
            "classification_mode",
            _coerce_enum(self.classification_mode, ClassificationMode, "classification_mode"),
        )
        object.__setattr__(self, "instrument_key", _optional_text(self.instrument_key))
        object.__setattr__(self, "isin", _optional_text(self.isin))
        object.__setattr__(self, "company_name", _optional_text(self.company_name))
        object.__setattr__(self, "basic_industry", _optional_text(self.basic_industry))


@dataclass(frozen=True, slots=True)
class IndexConstituent:
    """Point-in-time membership of an instrument in a market index."""

    index_symbol: str
    symbol: str
    effective_from: date | datetime | str
    source: str
    effective_to: date | datetime | str | None = None
    weight: Decimal | None = None

    def __post_init__(self) -> None:
        effective_from = _normalize_date(self.effective_from, "effective_from")
        effective_to = (
            _normalize_date(self.effective_to, "effective_to")
            if self.effective_to is not None
            else None
        )
        if effective_to is not None and effective_to < effective_from:
            raise ValueError("effective_to must be greater than or equal to effective_from")

        object.__setattr__(self, "index_symbol", normalize_index_symbol(self.index_symbol))
        object.__setattr__(self, "symbol", _normalize_symbol(self.symbol, "symbol"))
        object.__setattr__(self, "effective_from", effective_from)
        object.__setattr__(self, "effective_to", effective_to)
        object.__setattr__(self, "source", _non_empty_text(self.source, "source"))
        if self.weight is not None:
            weight = _decimal(self.weight, "weight")
            if weight < Decimal("0"):
                raise ValueError("weight must be greater than or equal to 0")
            object.__setattr__(self, "weight", weight)


def normalize_index_symbol(index_symbol: str) -> str:
    """Normalize index symbols into a stable uppercase underscore form."""

    value = _non_empty_text(index_symbol, "index_symbol").upper()
    return "_".join(value.replace("-", " ").split())


def normalize_market_cap_bucket(bucket: MarketCapBucket | str) -> MarketCapBucket:
    """Return a valid market-cap bucket enum from a string or enum value."""

    return _coerce_enum(bucket, MarketCapBucket, "market_cap_bucket")


def is_point_in_time_classification(classification: InstrumentClassification) -> bool:
    """Return whether the classification is explicitly point-in-time."""

    return classification.classification_mode == ClassificationMode.POINT_IN_TIME


def classification_is_active_on_date(
    classification: InstrumentClassification,
    observed_on: date | datetime | str,
) -> bool:
    """Return whether a classification row is active on the given date."""

    observed = _normalize_date(observed_on, "observed_on")
    if observed < classification.effective_from:
        return False
    return classification.effective_to is None or observed <= classification.effective_to


def constituent_is_active_on_date(
    constituent: IndexConstituent,
    observed_on: date | datetime | str,
) -> bool:
    """Return whether an index constituent row is active on the given date."""

    observed = _normalize_date(observed_on, "observed_on")
    if observed < constituent.effective_from:
        return False
    return constituent.effective_to is None or observed <= constituent.effective_to


def _as_index_iterable(index_membership: tuple[str, ...] | list[str] | str) -> Iterable[str]:
    if isinstance(index_membership, str):
        if not index_membership.strip():
            return ()
        return (index_membership,)
    return index_membership


def _coerce_enum(value: object, enum_type: type[Enum], field_name: str):
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value).strip().lower())
    except ValueError as error:
        valid = ", ".join(item.value for item in enum_type)
        raise ValueError(f"{field_name} must be one of: {valid}") from error


def _normalize_date(value: date | datetime | str, field_name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return date.fromisoformat(value.strip())
        except ValueError as error:
            raise ValueError(f"{field_name} must be an ISO date") from error
    raise ValueError(f"{field_name} must be date-like")


def _positive_decimal(value: object, field_name: str) -> Decimal:
    price = _decimal(value, field_name)
    if price <= Decimal("0"):
        raise ValueError(f"{field_name} must be positive")
    return price


def _decimal(value: object, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception as error:
        raise ValueError(f"{field_name} must be numeric") from error


def _normalize_symbol(symbol: str, field_name: str) -> str:
    return _non_empty_text(symbol, field_name).upper()


def _non_empty_text(value: object, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} must be non-empty")
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} must be non-empty")
    return text


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
