"""Read-only canonical daily market index OHLC helpers.

The raw ``prices_ohlc`` primary key includes the full timestamp, so historical
index data can contain multiple daily rows for the same session date when old
and new timestamp conventions coexist. This module canonicalizes at read time:
``session_date`` is the stored timestamp's date component, and one deterministic
row is kept per ``(instrument_key, session_date, interval='day')``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Iterable, Mapping

import pandas as pd
from sqlalchemy import text

from veridian_quant.v2.data.market_context_models import (
    MarketIndexBar,
    normalize_index_symbol,
)
from veridian_quant.v2.data.market_index_ingestion import MarketIndexInstrumentResolver
from veridian_quant.v2.data.market_index_registry import (
    get_market_index,
    list_market_indices,
)


OHLC_COLUMNS = ("open", "high", "low", "close")
DEFAULT_PRICE_EPSILON = Decimal("0.000001")


@dataclass(frozen=True, slots=True)
class MarketIndexDuplicateWarning:
    """Duplicate raw daily rows collapsed into one canonical session row."""

    index_symbol: str
    instrument_key: str
    session_date: date
    raw_count: int
    timestamps: tuple[str, ...]
    kept_timestamp: str
    has_conflict: bool
    examples: tuple[dict[str, object], ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "index_symbol": self.index_symbol,
            "instrument_key": self.instrument_key,
            "session_date": self.session_date.isoformat(),
            "raw_count": self.raw_count,
            "timestamps": list(self.timestamps),
            "kept_timestamp": self.kept_timestamp,
            "has_conflict": self.has_conflict,
            "examples": [dict(example) for example in self.examples],
        }


@dataclass(frozen=True, slots=True)
class CanonicalMarketIndexResult:
    """Canonical daily bars plus read-time audit counters."""

    index_symbol: str
    instrument_key: str
    raw_row_count: int
    bars: tuple[MarketIndexBar, ...]
    frame: pd.DataFrame
    warnings: tuple[MarketIndexDuplicateWarning, ...] = field(default_factory=tuple)

    @property
    def canonical_row_count(self) -> int:
        return len(self.bars)

    @property
    def duplicate_session_date_count(self) -> int:
        return len(self.warnings)

    @property
    def conflict_count(self) -> int:
        return sum(1 for warning in self.warnings if warning.has_conflict)

    @property
    def session_dates(self) -> frozenset[date]:
        return frozenset(bar.date for bar in self.bars)

    def to_summary_dict(self) -> dict[str, object]:
        return {
            "index_symbol": self.index_symbol,
            "instrument_key": self.instrument_key,
            "raw_rows": self.raw_row_count,
            "canonical_rows": self.canonical_row_count,
            "duplicate_session_dates": self.duplicate_session_date_count,
            "conflicts": self.conflict_count,
            "first_session_date": self.bars[0].date.isoformat() if self.bars else None,
            "last_session_date": self.bars[-1].date.isoformat() if self.bars else None,
        }


@dataclass(frozen=True, slots=True)
class MarketIndexAuditReport:
    """Read-only market index canonicalization audit report."""

    start_date: date
    end_date: date
    interval: str
    indices: tuple[dict[str, object], ...]
    nifty_auto: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "interval": self.interval,
            "indices": [dict(row) for row in self.indices],
            "nifty_auto": dict(self.nifty_auto),
        }


class SQLAlchemyMarketIndexDailyReader:
    """Read canonical daily market index bars from ``prices_ohlc``."""

    def __init__(self, engine: object, price_table: str = "prices_ohlc") -> None:
        self.engine = engine
        self.price_table = _validate_identifier(price_table)

    def load(
        self,
        *,
        start_date: date,
        end_date: date,
        index_symbol: str | None = None,
        instrument_key: str | None = None,
        interval: str = "day",
    ) -> CanonicalMarketIndexResult:
        if interval != "day":
            raise ValueError("market index reader only supports daily interval: day")
        if start_date > end_date:
            raise ValueError("start_date must be on or before end_date")
        resolved_symbol, resolved_key = self._resolve_index(index_symbol, instrument_key)
        raw = self._load_raw_rows(
            instrument_key=resolved_key,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
        )
        return canonicalize_market_index_rows(
            raw,
            index_symbol=resolved_symbol,
            instrument_key=resolved_key,
            start_date=start_date,
            end_date=end_date,
        )

    def _resolve_index(
        self,
        index_symbol: str | None,
        instrument_key: str | None,
    ) -> tuple[str, str]:
        if instrument_key:
            symbol = (
                normalize_index_symbol(index_symbol)
                if index_symbol
                else normalize_index_symbol(instrument_key.split("|", 1)[-1])
            )
            return symbol, instrument_key
        if not index_symbol:
            raise ValueError("index_symbol or instrument_key is required")
        symbol = get_market_index(index_symbol).index_symbol
        resolution = MarketIndexInstrumentResolver(self.engine).resolve([symbol])
        if resolution.unresolved:
            raise ValueError(f"unresolved market index symbol: {symbol}")
        if resolution.ambiguous:
            candidates = ", ".join(resolution.ambiguous[0].candidates)
            raise ValueError(f"ambiguous market index symbol: {symbol}; candidates: {candidates}")
        return symbol, resolution.resolved[0].instrument_key

    def _load_raw_rows(
        self,
        *,
        instrument_key: str,
        start_date: date,
        end_date: date,
        interval: str,
    ) -> pd.DataFrame:
        query = text(
            f"""
            SELECT
                timestamp,
                instrument_key,
                open,
                high,
                low,
                close,
                volume,
                interval
            FROM {self.price_table}
            WHERE instrument_key = :instrument_key
                AND interval = :interval
                AND timestamp >= :start_date
                AND timestamp < :exclusive_end_date
            ORDER BY timestamp ASC
            """
        )
        return pd.read_sql(
            query,
            self.engine,
            params={
                "instrument_key": instrument_key,
                "interval": interval,
                "start_date": start_date,
                "exclusive_end_date": end_date + timedelta(days=1),
            },
        )


def canonicalize_market_index_rows(
    rows: Iterable[Mapping[str, object]] | pd.DataFrame,
    *,
    index_symbol: str,
    instrument_key: str,
    start_date: date,
    end_date: date,
    source: str = "UPSTOX",
    price_epsilon: Decimal = DEFAULT_PRICE_EPSILON,
) -> CanonicalMarketIndexResult:
    """Return one canonical market index bar per stored timestamp date."""

    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date")
    symbol = normalize_index_symbol(index_symbol)
    raw = _normalize_raw_frame(rows, instrument_key)
    if raw.empty:
        frame = _empty_canonical_frame()
        return CanonicalMarketIndexResult(symbol, instrument_key, 0, (), frame, ())

    raw = raw.loc[
        (raw["session_date"] >= start_date) & (raw["session_date"] <= end_date)
    ].copy()
    if raw.empty:
        frame = _empty_canonical_frame()
        return CanonicalMarketIndexResult(symbol, instrument_key, 0, (), frame, ())

    raw = raw.sort_values(["session_date", "timestamp"], kind="mergesort")
    canonical_rows: list[dict[str, object]] = []
    warnings: list[MarketIndexDuplicateWarning] = []

    for session_date, group in raw.groupby("session_date", sort=True):
        kept = group.iloc[-1]
        if len(group) > 1:
            has_conflict = _group_has_ohlc_conflict(group, price_epsilon)
            warnings.append(
                MarketIndexDuplicateWarning(
                    index_symbol=symbol,
                    instrument_key=instrument_key,
                    session_date=session_date,
                    raw_count=len(group),
                    timestamps=tuple(_timestamp_text(value) for value in group["timestamp"]),
                    kept_timestamp=_timestamp_text(kept["timestamp"]),
                    has_conflict=has_conflict,
                    examples=_warning_examples(group) if has_conflict else (),
                )
            )
        canonical_rows.append(
            {
                "index_symbol": symbol,
                "instrument_key": instrument_key,
                "session_date": session_date,
                "timestamp": kept["timestamp"],
                "open": kept["open"],
                "high": kept["high"],
                "low": kept["low"],
                "close": kept["close"],
                "volume": kept.get("volume"),
            }
        )

    frame = pd.DataFrame(canonical_rows)
    bars = tuple(
        MarketIndexBar(
            index_symbol=symbol,
            date=row["session_date"],
            open=Decimal(str(row["open"])),
            high=Decimal(str(row["high"])),
            low=Decimal(str(row["low"])),
            close=Decimal(str(row["close"])),
            volume=_optional_int(row.get("volume")),
            source=source,
        )
        for row in canonical_rows
    )
    return CanonicalMarketIndexResult(
        index_symbol=symbol,
        instrument_key=instrument_key,
        raw_row_count=len(raw),
        bars=bars,
        frame=frame,
        warnings=tuple(warnings),
    )


def audit_market_index_daily_bars(
    engine: object,
    *,
    index_symbols: Iterable[str],
    start_date: date,
    end_date: date,
    interval: str = "day",
) -> MarketIndexAuditReport:
    """Run a read-only canonicalization audit for market index daily bars."""

    symbols = _normalize_requested_symbols(index_symbols)
    reader = SQLAlchemyMarketIndexDailyReader(engine)
    results: dict[str, CanonicalMarketIndexResult] = {}
    for symbol in symbols:
        results[symbol] = reader.load(
            index_symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
        )

    return MarketIndexAuditReport(
        start_date=start_date,
        end_date=end_date,
        interval=interval,
        indices=tuple(results[symbol].to_summary_dict() for symbol in symbols),
        nifty_auto=_build_nifty_auto_summary(results),
    )


def _build_nifty_auto_summary(
    results: Mapping[str, CanonicalMarketIndexResult],
) -> dict[str, object]:
    auto = results.get("NIFTY_AUTO")
    if auto is None:
        return {"checked": False, "reason": "NIFTY_AUTO not requested"}

    peer_symbols = [symbol for symbol in ("NIFTY_50", "NIFTY_500") if symbol in results]
    peer_dates: set[date] = set()
    missing_by_peer: dict[str, list[str]] = {}
    for symbol in peer_symbols:
        dates = results[symbol].session_dates
        peer_dates.update(dates)
        missing_by_peer[symbol] = [
            value.isoformat() for value in sorted(auto.session_dates - dates)[:10]
        ]

    extra_vs_peer_union = sorted(auto.session_dates - peer_dates) if peer_dates else []
    weekday_counts = _weekday_counts(extra_vs_peer_union)
    duplicate_examples = [
        warning.session_date.isoformat() for warning in auto.warnings[:10]
    ]
    conflict_examples = [
        warning.to_dict() for warning in auto.warnings if warning.has_conflict
    ][:5]
    return {
        "checked": True,
        "raw_rows": auto.raw_row_count,
        "canonical_rows": auto.canonical_row_count,
        "duplicate_session_dates": auto.duplicate_session_date_count,
        "conflicts": auto.conflict_count,
        "duplicate_examples": duplicate_examples,
        "peer_symbols": peer_symbols,
        "dates_missing_by_peer_examples": missing_by_peer,
        "true_extra_dates_vs_peer_union": len(extra_vs_peer_union),
        "true_extra_first_date": extra_vs_peer_union[0].isoformat()
        if extra_vs_peer_union
        else None,
        "true_extra_last_date": extra_vs_peer_union[-1].isoformat()
        if extra_vs_peer_union
        else None,
        "true_extra_weekday_counts": weekday_counts,
        "true_extra_date_examples": [value.isoformat() for value in extra_vs_peer_union[:10]],
        "conflict_examples": conflict_examples,
    }


def _weekday_counts(values: Iterable[date]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        weekday = value.strftime("%A")
        counts[weekday] = counts.get(weekday, 0) + 1
    return dict(sorted(counts.items()))


def _normalize_requested_symbols(index_symbols: Iterable[str]) -> list[str]:
    symbols = list(index_symbols)
    if len(symbols) == 1 and str(symbols[0]).strip().upper() == "ALL":
        return [definition.index_symbol for definition in list_market_indices()]
    return [get_market_index(symbol).index_symbol for symbol in symbols]


def _normalize_raw_frame(
    rows: Iterable[Mapping[str, object]] | pd.DataFrame,
    instrument_key: str,
) -> pd.DataFrame:
    frame = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(list(rows))
    if frame.empty:
        return _empty_raw_frame()
    missing = [column for column in ("timestamp", *OHLC_COLUMNS) if column not in frame.columns]
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")
    frame = frame.copy()
    if "instrument_key" not in frame.columns:
        frame["instrument_key"] = instrument_key
    frame = frame.loc[frame["instrument_key"].astype(str) == instrument_key].copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="raise")
    frame["session_date"] = frame["timestamp"].dt.date
    for column in OHLC_COLUMNS:
        frame[column] = frame[column].map(lambda value: Decimal(str(value)))
    if "volume" not in frame.columns:
        frame["volume"] = None
    return frame


def _group_has_ohlc_conflict(group: pd.DataFrame, price_epsilon: Decimal) -> bool:
    first = group.iloc[0]
    for _, row in group.iloc[1:].iterrows():
        for column in OHLC_COLUMNS:
            if abs(Decimal(str(row[column])) - Decimal(str(first[column]))) > price_epsilon:
                return True
    return False


def _warning_examples(group: pd.DataFrame) -> tuple[dict[str, object], ...]:
    examples: list[dict[str, object]] = []
    for _, row in group.head(3).iterrows():
        examples.append(
            {
                "timestamp": _timestamp_text(row["timestamp"]),
                "open": str(row["open"]),
                "high": str(row["high"]),
                "low": str(row["low"]),
                "close": str(row["close"]),
            }
        )
    return tuple(examples)


def _timestamp_text(value: object) -> str:
    return pd.Timestamp(value).isoformat()


def _optional_int(value: object) -> int | None:
    if value is None or pd.isna(value):
        return None
    return int(Decimal(str(value)))


def _empty_raw_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "timestamp",
            "instrument_key",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "session_date",
        ]
    )


def _empty_canonical_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "index_symbol",
            "instrument_key",
            "session_date",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
    )


def _validate_identifier(identifier: str) -> str:
    if not identifier.replace("_", "").isalnum():
        raise ValueError(f"invalid SQL identifier: {identifier}")
    return identifier
