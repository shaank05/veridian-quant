"""V2 Upstox ingestion support for market index OHLC bars."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, time as datetime_time, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

import pandas as pd
import requests
from sqlalchemy import text

from veridian_quant.v2.data.ingestion_config import IngestionConfig
from veridian_quant.v2.data.market_context_models import MarketIndexBar
from veridian_quant.v2.data.market_index_registry import (
    MarketIndexDefinition,
    get_market_index,
)
from veridian_quant.v2.data.price_ingestion import (
    DateChunk,
    PriceOHLCWriter,
    ValidatedCandle,
    generate_date_chunks,
)
from veridian_quant.v2.data.upstox_history import HistoricalChunkResult


logger = logging.getLogger(__name__)

SUPPORTED_INDEX_INTERVALS = frozenset({"day"})


@dataclass(frozen=True, slots=True)
class ResolvedMarketIndex:
    """Resolved internal index symbol to Upstox instrument metadata."""

    definition: MarketIndexDefinition
    instrument_key: str
    name: str | None
    exchange: str | None = None
    trading_symbol: str | None = None
    segment: str | None = None


@dataclass(frozen=True, slots=True)
class AmbiguousMarketIndex:
    """Ambiguous index instrument resolution details."""

    index_symbol: str
    candidates: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MarketIndexResolution:
    """Resolution result for requested market indices."""

    resolved: tuple[ResolvedMarketIndex, ...]
    unresolved: tuple[str, ...]
    ambiguous: tuple[AmbiguousMarketIndex, ...]


@dataclass(slots=True)
class MarketIndexIngestionSummary:
    """Operational summary for one market index ingestion run."""

    requested_indices: list[str] = field(default_factory=list)
    resolved_indices: list[str] = field(default_factory=list)
    unresolved_indices: list[str] = field(default_factory=list)
    ambiguous_indices: dict[str, list[str]] = field(default_factory=dict)
    start_date: date | None = None
    end_date: date | None = None
    interval: str = "day"
    dry_run: bool = True
    chunks_planned: int = 0
    chunks_fetched: int = 0
    chunks_failed: int = 0
    candles_fetched: int = 0
    candles_inserted: int = 0
    invalid_candles_rejected: int = 0
    failures_by_index: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_indices": self.requested_indices,
            "resolved_indices": self.resolved_indices,
            "unresolved_indices": self.unresolved_indices,
            "ambiguous_indices": self.ambiguous_indices,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "interval": self.interval,
            "dry_run": self.dry_run,
            "chunks_planned": self.chunks_planned,
            "chunks_fetched": self.chunks_fetched,
            "chunks_failed": self.chunks_failed,
            "candles_fetched": self.candles_fetched,
            "candles_inserted": self.candles_inserted,
            "invalid_candles_rejected": self.invalid_candles_rejected,
            "failures_by_index": self.failures_by_index,
        }


class MarketIndexInstrumentResolver:
    """Resolve internal market index symbols to existing Upstox instrument keys."""

    def __init__(self, engine: object, instrument_table: str = "instruments") -> None:
        self.engine = engine
        self.instrument_table = _validate_identifier(instrument_table)

    def resolve(self, index_symbols: Iterable[str]) -> MarketIndexResolution:
        definitions = [get_market_index(symbol) for symbol in index_symbols]
        candidates = self._load_index_instruments()
        resolved: list[ResolvedMarketIndex] = []
        unresolved: list[str] = []
        ambiguous: list[AmbiguousMarketIndex] = []

        for definition in definitions:
            matches = _matching_candidates(definition, candidates)
            if len(matches) == 1:
                row = matches[0]
                resolved.append(
                    ResolvedMarketIndex(
                        definition=definition,
                        instrument_key=str(row["instrument_key"]),
                        name=_optional_text(row.get("name")),
                        exchange=_optional_text(row.get("exchange")),
                        trading_symbol=_optional_text(row.get("trading_symbol")),
                        segment=_optional_text(row.get("segment")),
                    )
                )
            elif not matches:
                unresolved.append(definition.index_symbol)
            else:
                ambiguous.append(
                    AmbiguousMarketIndex(
                        index_symbol=definition.index_symbol,
                        candidates=tuple(str(row["instrument_key"]) for row in matches),
                    )
                )

        return MarketIndexResolution(
            resolved=tuple(resolved),
            unresolved=tuple(unresolved),
            ambiguous=tuple(ambiguous),
        )

    def _load_index_instruments(self) -> list[dict[str, Any]]:
        query = text(
            f"""
            SELECT
                instrument_key,
                symbol,
                trading_symbol,
                name,
                exchange,
                segment,
                instrument_type
            FROM {self.instrument_table}
            WHERE instrument_key LIKE 'NSE_INDEX|%'
                OR exchange = 'NSE_INDEX'
                OR segment = 'NSE_INDEX'
            ORDER BY instrument_key ASC
            """
        )
        with self.engine.connect() as conn:
            return [dict(row) for row in conn.execute(query).mappings().all()]


class MarketIndexIngestionRunner:
    """Resolve, fetch, validate, and persist market index daily OHLC bars."""

    def __init__(
        self,
        engine: object,
        config: IngestionConfig,
        resolver: MarketIndexInstrumentResolver | None = None,
        history_client: object | None = None,
        writer: PriceOHLCWriter | None = None,
    ) -> None:
        self.engine = engine
        self.config = config
        self.resolver = resolver or MarketIndexInstrumentResolver(engine)
        self.history_client = history_client
        self.writer = writer or PriceOHLCWriter(engine)

    def run(
        self,
        index_symbols: Iterable[str],
        start_date: date,
        end_date: date,
        interval: str = "day",
        dry_run: bool = True,
    ) -> MarketIndexIngestionSummary:
        if interval not in SUPPORTED_INDEX_INTERVALS:
            raise ValueError("market index ingestion only supports daily interval: day")
        if start_date > end_date:
            raise ValueError("start_date must be on or before end_date")
        if not dry_run:
            self.config.require_access_token("backfill")
            if self.history_client is None:
                raise ValueError("history_client is required for market index ingestion")

        requested = [get_market_index(symbol).index_symbol for symbol in index_symbols]
        resolution = self.resolver.resolve(requested)
        chunks = generate_date_chunks(start_date, end_date, self.config.max_days_1d)
        summary = MarketIndexIngestionSummary(
            requested_indices=requested,
            resolved_indices=[item.definition.index_symbol for item in resolution.resolved],
            unresolved_indices=list(resolution.unresolved),
            ambiguous_indices={
                item.index_symbol: list(item.candidates) for item in resolution.ambiguous
            },
            start_date=start_date,
            end_date=end_date,
            interval=interval,
            dry_run=dry_run,
            chunks_planned=len(resolution.resolved) * len(chunks),
        )
        if dry_run:
            return summary

        for resolved in resolution.resolved:
            for chunk in chunks:
                result = self._fetch_chunk(resolved, interval, chunk)
                if not result.ok:
                    summary.chunks_failed += 1
                    summary.failures_by_index[resolved.definition.index_symbol] = (
                        result.error or "unknown Upstox error"
                    )
                    continue
                summary.chunks_fetched += 1
                summary.candles_fetched += len(result.candles)
                valid, rejected = convert_index_candles(
                    result.candles,
                    resolved.definition.index_symbol,
                    resolved.instrument_key,
                    interval,
                )
                summary.invalid_candles_rejected += rejected
                summary.candles_inserted += self.writer.upsert_candles(valid)
                if self.config.throttle_seconds:
                    time.sleep(self.config.throttle_seconds)

        return summary

    def _fetch_chunk(
        self,
        resolved: ResolvedMarketIndex,
        interval: str,
        chunk: DateChunk,
    ) -> HistoricalChunkResult:
        try:
            return self.history_client.fetch_candles(
                resolved.instrument_key,
                interval,
                chunk.start_date,
                chunk.end_date,
            )
        except requests.RequestException as error:
            return HistoricalChunkResult(
                instrument_key=resolved.instrument_key,
                interval=interval,
                start_date=chunk.start_date,
                end_date=chunk.end_date,
                candles=[],
                ok=False,
                error=str(error),
            )


def convert_index_candles(
    raw_candles: Iterable[Any],
    index_symbol: str,
    instrument_key: str,
    interval: str = "day",
) -> tuple[list[ValidatedCandle], int]:
    """Convert Upstox candles into validated DB-ready index OHLC rows."""

    valid: list[ValidatedCandle] = []
    rejected = 0
    for raw in raw_candles:
        try:
            valid.append(_convert_index_candle(raw, index_symbol, instrument_key, interval))
        except (ValueError, TypeError, InvalidOperation):
            rejected += 1
            logger.warning("Skipping malformed index candle for %s: %s", index_symbol, raw)
    return valid, rejected


def _convert_index_candle(
    raw: Any,
    index_symbol: str,
    instrument_key: str,
    interval: str,
) -> ValidatedCandle:
    values = _candle_values(raw)
    if len(values) < 6:
        raise ValueError("candle must contain timestamp and OHLCV")
    timestamp = _parse_timestamp(values[0])
    volume = _integer(values[5])
    bar = MarketIndexBar(
        index_symbol=index_symbol,
        date=timestamp.date(),
        open=Decimal(str(values[1])),
        high=Decimal(str(values[2])),
        low=Decimal(str(values[3])),
        close=Decimal(str(values[4])),
        volume=volume,
        source="UPSTOX",
    )
    open_interest = (
        _integer(values[6]) if len(values) > 6 and values[6] is not None else None
    )
    return ValidatedCandle(
        timestamp=datetime.combine(bar.date, datetime_time.min, tzinfo=timezone.utc),
        instrument_key=instrument_key,
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        volume=volume,
        open_interest=open_interest,
        interval=interval,
    )


def _matching_candidates(
    definition: MarketIndexDefinition,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    aliases = {_match_key(definition.index_symbol), _match_key(definition.index_name)}
    aliases.update(_match_key(alias) for alias in definition.aliases)
    matches = []
    for row in candidates:
        candidate_values = {
            _match_key(row.get("instrument_key")),
            _match_key(row.get("symbol")),
            _match_key(row.get("trading_symbol")),
            _match_key(row.get("name")),
        }
        if aliases & candidate_values:
            matches.append(row)
    return matches


def _candle_values(raw: Any) -> list[Any]:
    if isinstance(raw, dict):
        return [
            raw.get("timestamp") or raw.get("time") or raw.get("date"),
            raw.get("open"),
            raw.get("high"),
            raw.get("low"),
            raw.get("close"),
            raw.get("volume"),
            raw.get("open_interest", raw.get("oi")),
        ]
    return list(raw)


def _parse_timestamp(value: object) -> datetime:
    if value is None or value == "":
        raise ValueError("timestamp is required")
    timestamp = pd.to_datetime(value, utc=True)
    if pd.isna(timestamp):
        raise ValueError("timestamp is invalid")
    return timestamp.to_pydatetime()


def _integer(value: object) -> int:
    if value is None or value == "":
        raise ValueError("integer value is required")
    return int(Decimal(str(value)))


def _match_key(value: object) -> str:
    if value is None:
        return ""
    text_value = str(value).upper()
    if "|" in text_value:
        text_value = text_value.split("|", 1)[1]
    return "".join(char for char in text_value if char.isalnum())


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text_value = str(value).strip()
    return text_value or None


def _validate_identifier(identifier: str) -> str:
    if not identifier.replace("_", "").isalnum():
        raise ValueError(f"invalid SQL identifier: {identifier}")
    return identifier
