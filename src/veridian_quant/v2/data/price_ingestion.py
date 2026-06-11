"""V2 price ingestion orchestration and database persistence."""

from __future__ import annotations

import csv
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from sqlalchemy import text

from veridian_quant.v2.data.ingestion_config import IngestionConfig
from veridian_quant.v2.data.instruments import (
    InstrumentResolver,
    ResolvedInstrument,
    normalize_symbols,
)
from veridian_quant.v2.data.upstox_history import HistoricalChunkResult


logger = logging.getLogger(__name__)

SUPPORTED_INTERVALS = frozenset({"day", "1minute"})
SUPPORTED_MODES = frozenset({"backfill", "incremental", "dry-run"})

UPSERT_PRICES_SQL = """
INSERT INTO prices_ohlc (
    timestamp,
    instrument_key,
    open,
    high,
    low,
    close,
    volume,
    open_interest,
    interval
)
VALUES (
    :timestamp,
    :instrument_key,
    :open,
    :high,
    :low,
    :close,
    :volume,
    :open_interest,
    :interval
)
ON CONFLICT (timestamp, instrument_key, interval)
DO UPDATE SET
    open = EXCLUDED.open,
    high = EXCLUDED.high,
    low = EXCLUDED.low,
    close = EXCLUDED.close,
    volume = EXCLUDED.volume,
    open_interest = EXCLUDED.open_interest
"""


@dataclass(frozen=True, slots=True)
class DateChunk:
    """Inclusive date range chunk."""

    start_date: date
    end_date: date


@dataclass(frozen=True, slots=True)
class ValidatedCandle:
    """Database-ready OHLCV candle row."""

    timestamp: datetime
    instrument_key: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    open_interest: int | None
    interval: str


@dataclass(slots=True)
class IngestionSummary:
    """Operational summary for one V2 ingestion run."""

    requested_symbols: int = 0
    resolved_symbols: int = 0
    unresolved_symbols: list[str] | None = None
    instruments_attempted: int = 0
    chunks_planned: int = 0
    chunks_fetched: int = 0
    chunks_failed: int = 0
    candles_received: int = 0
    candles_inserted: int = 0
    candles_skipped: int = 0
    mode: str = "dry-run"
    interval: str = "day"
    start_date: date | None = None
    end_date: date | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_symbols": self.requested_symbols,
            "resolved_symbols": self.resolved_symbols,
            "unresolved_symbols": self.unresolved_symbols or [],
            "instruments_attempted": self.instruments_attempted,
            "chunks_planned": self.chunks_planned,
            "chunks_fetched": self.chunks_fetched,
            "chunks_failed": self.chunks_failed,
            "candles_received": self.candles_received,
            "candles_inserted": self.candles_inserted,
            "candles_skipped": self.candles_skipped,
            "mode": self.mode,
            "interval": self.interval,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
        }


class PriceIngestionRunner:
    """Coordinate symbol resolution, fetching, validation, and persistence."""

    def __init__(
        self,
        engine: object,
        config: IngestionConfig,
        resolver: InstrumentResolver | None = None,
        history_client: object | None = None,
        writer: "PriceOHLCWriter | None" = None,
    ) -> None:
        self.engine = engine
        self.config = config
        self.resolver = resolver or InstrumentResolver(engine)
        self.history_client = history_client
        self.writer = writer or PriceOHLCWriter(engine)

    def run(
        self,
        symbols: Iterable[str],
        mode: str = "dry-run",
        interval: str = "day",
        start_date: date | None = None,
        end_date: date | None = None,
        exchange: str = "NSE_EQ",
    ) -> IngestionSummary:
        """Run V2 ingestion for requested symbols."""

        _validate_mode_interval(mode, interval)
        self.config.require_access_token(mode)
        if mode == "backfill" and start_date is None:
            raise ValueError("backfill mode requires --start-date")

        requested_symbols = normalize_symbols(symbols)
        effective_end = end_date or datetime.now(timezone.utc).date()
        summary = IngestionSummary(
            requested_symbols=len(requested_symbols),
            unresolved_symbols=[],
            mode=mode,
            interval=interval,
            start_date=start_date,
            end_date=effective_end,
        )

        logger.info("Starting V2 price ingestion: %s", summary.to_dict())
        logger.info("Config: %s", self.config.safe_summary())

        instruments, unresolved = self.resolver.resolve_symbols(requested_symbols, exchange)
        summary.resolved_symbols = len(instruments)
        summary.unresolved_symbols = unresolved
        logger.info("Resolved %s/%s symbols", len(instruments), len(requested_symbols))
        if unresolved:
            logger.warning("Unresolved symbols: %s", ", ".join(unresolved))

        plans = self._build_plans(instruments, mode, interval, start_date, effective_end)
        summary.instruments_attempted = len(plans)
        summary.chunks_planned = sum(len(chunks) for _, chunks in plans)

        if mode == "dry-run":
            logger.info("Dry-run complete; no Upstox calls or database writes performed")
            return summary

        if self.history_client is None:
            raise ValueError("history_client is required for real ingestion modes")

        for instrument, chunks in plans:
            logger.info(
                "Fetching %s (%s): %s chunks",
                instrument.symbol,
                instrument.instrument_key,
                len(chunks),
            )
            for chunk in chunks:
                result = self.history_client.fetch_candles(
                    instrument.instrument_key,
                    interval,
                    chunk.start_date,
                    chunk.end_date,
                )
                if not result.ok:
                    summary.chunks_failed += 1
                    continue
                summary.chunks_fetched += 1
                summary.candles_received += len(result.candles)
                valid, skipped = validate_candles(
                    result.candles,
                    instrument.instrument_key,
                    interval,
                )
                summary.candles_skipped += skipped
                inserted = self.writer.upsert_candles(valid)
                summary.candles_inserted += inserted
                logger.info(
                    "Inserted %s candles for %s chunk %s..%s",
                    inserted,
                    instrument.symbol,
                    chunk.start_date,
                    chunk.end_date,
                )
                if self.config.throttle_seconds:
                    time.sleep(self.config.throttle_seconds)

        logger.info("Final V2 ingestion summary: %s", summary.to_dict())
        return summary

    def _build_plans(
        self,
        instruments: list[ResolvedInstrument],
        mode: str,
        interval: str,
        start_date: date | None,
        end_date: date,
    ) -> list[tuple[ResolvedInstrument, list[DateChunk]]]:
        plans: list[tuple[ResolvedInstrument, list[DateChunk]]] = []
        for instrument in instruments:
            instrument_start = start_date
            if mode == "incremental":
                latest = self.writer.get_latest_timestamp(
                    instrument.instrument_key,
                    interval,
                )
                if latest is None:
                    if start_date is None:
                        raise ValueError(
                            "incremental mode found no existing data for "
                            f"{instrument.instrument_key}; run backfill first or provide --start-date"
                        )
                else:
                    instrument_start = _next_start_date(latest, interval)

            if instrument_start is None:
                continue
            chunks = generate_date_chunks(
                instrument_start,
                end_date,
                _max_days_for_interval(self.config, interval),
            )
            plans.append((instrument, chunks))
        return plans


class PriceOHLCWriter:
    """Database operations for prices_ohlc ingestion."""

    def __init__(self, engine: object) -> None:
        self.engine = engine

    def get_latest_timestamp(
        self,
        instrument_key: str,
        interval: str,
    ) -> datetime | None:
        query = text(
            """
            SELECT MAX(timestamp) AS latest_timestamp
            FROM prices_ohlc
            WHERE instrument_key = :instrument_key
                AND interval = :interval
            """
        )
        with self.engine.connect() as conn:
            result = conn.execute(
                query,
                {"instrument_key": instrument_key, "interval": interval},
            ).scalar()
        return result

    def upsert_candles(self, candles: Iterable[ValidatedCandle]) -> int:
        rows = [
            {
                "timestamp": candle.timestamp,
                "instrument_key": candle.instrument_key,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
                "open_interest": candle.open_interest,
                "interval": candle.interval,
            }
            for candle in candles
        ]
        if not rows:
            return 0
        with self.engine.begin() as conn:
            conn.execute(text(UPSERT_PRICES_SQL), rows)
        return len(rows)


def load_symbols_from_sources(
    symbols_arg: str | None = None,
    symbol_file: str | Path | None = None,
) -> list[str]:
    """Load and normalize symbols from CLI comma list and optional file."""

    symbols: list[str] = []
    if symbols_arg:
        symbols.extend(part for part in symbols_arg.split(","))
    if symbol_file:
        symbols.extend(_load_symbol_file(Path(symbol_file)))
    return normalize_symbols(symbols)


def generate_date_chunks(
    start_date: date,
    end_date: date,
    max_days: int,
) -> list[DateChunk]:
    """Generate deterministic inclusive date chunks."""

    if start_date > end_date:
        return []
    chunks: list[DateChunk] = []
    cursor = start_date
    while cursor <= end_date:
        chunk_end = min(cursor + timedelta(days=max_days - 1), end_date)
        chunks.append(DateChunk(cursor, chunk_end))
        cursor = chunk_end + timedelta(days=1)
    return chunks


def validate_candles(
    raw_candles: Iterable[Any],
    instrument_key: str,
    interval: str,
) -> tuple[list[ValidatedCandle], int]:
    """Convert provider candles into DB rows, skipping malformed rows."""

    valid: list[ValidatedCandle] = []
    skipped = 0
    for raw in raw_candles:
        try:
            candle = _convert_candle(raw, instrument_key, interval)
        except (ValueError, TypeError, InvalidOperation):
            skipped += 1
            logger.warning("Skipping malformed candle for %s: %s", instrument_key, raw)
            continue
        valid.append(candle)
    return valid, skipped


def _convert_candle(
    raw: Any,
    instrument_key: str,
    interval: str,
) -> ValidatedCandle:
    if isinstance(raw, dict):
        values = [
            raw.get("timestamp") or raw.get("time") or raw.get("date"),
            raw.get("open"),
            raw.get("high"),
            raw.get("low"),
            raw.get("close"),
            raw.get("volume"),
            raw.get("open_interest", raw.get("oi")),
        ]
    else:
        values = list(raw)

    if len(values) < 6:
        raise ValueError("candle must contain timestamp and OHLCV")

    timestamp = _parse_timestamp(values[0])
    open_price = _decimal(values[1])
    high_price = _decimal(values[2])
    low_price = _decimal(values[3])
    close_price = _decimal(values[4])
    volume = _integer(values[5])
    open_interest = _integer(values[6]) if len(values) > 6 and values[6] is not None else None

    if high_price < low_price:
        raise ValueError("high must be greater than or equal to low")
    if high_price < open_price or high_price < close_price:
        raise ValueError("high must cover open and close")
    if low_price > open_price or low_price > close_price:
        raise ValueError("low must cover open and close")

    return ValidatedCandle(
        timestamp=timestamp,
        instrument_key=instrument_key,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
        open_interest=open_interest,
        interval=interval,
    )


def _load_symbol_file(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"symbol file not found: {path}")
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            sample = handle.read(2048)
            handle.seek(0)
            if "symbol" in sample.lower().splitlines()[0]:
                reader = csv.DictReader(handle)
                return [row.get("symbol", "") for row in reader]
            reader = csv.reader(handle)
            return [row[0] for row in reader if row]
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _parse_timestamp(value: object) -> datetime:
    if value is None or value == "":
        raise ValueError("timestamp is required")
    timestamp = pd.to_datetime(value, utc=True)
    if pd.isna(timestamp):
        raise ValueError("timestamp is invalid")
    return timestamp.to_pydatetime()


def _decimal(value: object) -> Decimal:
    if value is None or value == "":
        raise ValueError("numeric value is required")
    return Decimal(str(value))


def _integer(value: object) -> int:
    if value is None or value == "":
        raise ValueError("integer value is required")
    return int(Decimal(str(value)))


def _validate_mode_interval(mode: str, interval: str) -> None:
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"unsupported mode: {mode}")
    if interval not in SUPPORTED_INTERVALS:
        raise ValueError(f"unsupported interval: {interval}")


def _max_days_for_interval(config: IngestionConfig, interval: str) -> int:
    if interval == "day":
        return config.max_days_1d
    if interval == "1minute":
        return config.max_days_1m
    raise ValueError(f"unsupported interval: {interval}")


def _next_start_date(latest: datetime, interval: str) -> date:
    if interval == "day":
        return (latest + timedelta(days=1)).date()
    return (latest + timedelta(seconds=1)).date()
