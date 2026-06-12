"""V2 price ingestion orchestration and database persistence."""

from __future__ import annotations

import csv
import logging
import shutil
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import requests
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
COMPLETED_CHUNK_STATUSES = frozenset(
    {"INSERTED", "INSERTED_WITH_SKIPS", "SKIPPED_ALREADY_COMPLETE", "NO_CANDLES"}
)
STATUS_COLUMNS = (
    "run_id",
    "symbol",
    "instrument_key",
    "interval",
    "chunk_start_date",
    "chunk_end_date",
    "status",
    "attempt_count",
    "candles_received",
    "candles_inserted",
    "candles_skipped",
    "error",
    "started_at",
    "finished_at",
    "updated_at",
)

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
    chunks_skipped_existing: int = 0
    status_file_path: str | None = None
    run_id: str | None = None
    run_dir: str | None = None
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
            "chunks_skipped_existing": self.chunks_skipped_existing,
            "status_file_path": self.status_file_path,
            "run_id": self.run_id,
            "run_dir": self.run_dir,
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
        run_id: str | None = None,
        run_dir: str | Path | None = None,
        resume: bool = False,
        skip_existing_chunks: bool = True,
        network_retry: str | None = None,
        network_wait_seconds: int | None = None,
        network_max_wait_minutes: int | None = None,
        chunk_min_coverage_pct: float | None = None,
    ) -> IngestionSummary:
        """Run V2 ingestion for requested symbols."""

        _validate_mode_interval(mode, interval)
        self.config.require_access_token(mode)
        if mode == "backfill" and start_date is None:
            raise ValueError("backfill mode requires --start-date")

        requested_symbols = normalize_symbols(symbols)
        effective_end = end_date or datetime.now(timezone.utc).date()
        effective_run_id = run_id
        effective_run_dir = Path(run_dir) if run_dir is not None else None
        summary = IngestionSummary(
            requested_symbols=len(requested_symbols),
            unresolved_symbols=[],
            status_file_path=(
                str(effective_run_dir / "ingestion_chunk_status.csv")
                if effective_run_dir is not None
                else None
            ),
            run_id=effective_run_id,
            run_dir=str(effective_run_dir) if effective_run_dir is not None else None,
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
        status_store = (
            ChunkStatusStore(effective_run_dir / "ingestion_chunk_status.csv", effective_run_id or "")
            if effective_run_dir is not None and effective_run_id is not None
            else None
        )
        if status_store is not None:
            status_store.initialize(plans, interval, "DRY_RUN_PLANNED" if mode == "dry-run" else "PENDING")

        if mode == "dry-run":
            logger.info("Dry-run complete; no Upstox calls or database writes performed")
            return summary

        if self.history_client is None:
            raise ValueError("history_client is required for real ingestion modes")

        completeness_checker = (
            ChunkCompletenessChecker(self.engine)
            if skip_existing_chunks and hasattr(self.engine, "connect")
            else None
        )
        effective_network_retry = network_retry or self.config.network_retry
        effective_network_wait_seconds = (
            network_wait_seconds
            if network_wait_seconds is not None
            else self.config.network_wait_seconds
        )
        effective_network_max_wait_minutes = (
            network_max_wait_minutes
            if network_max_wait_minutes is not None
            else self.config.network_max_wait_minutes
        )
        effective_chunk_min_coverage_pct = (
            chunk_min_coverage_pct
            if chunk_min_coverage_pct is not None
            else self.config.chunk_min_coverage_pct
        )

        for instrument, chunks in plans:
            logger.info(
                "Fetching %s (%s): %s chunks",
                instrument.symbol,
                instrument.instrument_key,
                len(chunks),
            )
            for chunk in chunks:
                if resume and status_store is not None and status_store.is_completed(
                    instrument,
                    interval,
                    chunk,
                ):
                    logger.info(
                        "Skipping completed status for %s chunk %s..%s",
                        instrument.symbol,
                        chunk.start_date,
                        chunk.end_date,
                    )
                    continue

                if completeness_checker is not None:
                    completeness = completeness_checker.check(
                        instrument.instrument_key,
                        interval,
                        chunk,
                        effective_chunk_min_coverage_pct,
                    )
                    if completeness.is_complete:
                        summary.chunks_skipped_existing += 1
                        if status_store is not None:
                            status_store.update(
                                instrument,
                                interval,
                                chunk,
                                status="SKIPPED_ALREADY_COMPLETE",
                                candles_inserted=0,
                                error="",
                                finished=True,
                            )
                        logger.info(
                            "Skipping existing chunk for %s %s..%s: %.2f%% coverage",
                            instrument.symbol,
                            chunk.start_date,
                            chunk.end_date,
                            completeness.coverage_pct,
                        )
                        continue

                if status_store is not None:
                    status_store.mark_started(instrument, interval, chunk)

                result = self._fetch_chunk_with_network_recovery(
                    instrument,
                    interval,
                    chunk,
                    effective_network_retry,
                    effective_network_wait_seconds,
                    effective_network_max_wait_minutes,
                    status_store,
                )
                if not result.ok:
                    summary.chunks_failed += 1
                    if status_store is not None:
                        status_store.update(
                            instrument,
                            interval,
                            chunk,
                            status="FETCH_FAILED_FINAL",
                            error=result.error or "",
                            finished=True,
                        )
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
                if status_store is not None:
                    if not result.candles:
                        status = "NO_CANDLES"
                    elif skipped:
                        status = "INSERTED_WITH_SKIPS"
                    else:
                        status = "INSERTED"
                    status_store.update(
                        instrument,
                        interval,
                        chunk,
                        status=status,
                        candles_received=len(result.candles),
                        candles_inserted=inserted,
                        candles_skipped=skipped,
                        error="",
                        finished=True,
                    )
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

    def _fetch_chunk_with_network_recovery(
        self,
        instrument: ResolvedInstrument,
        interval: str,
        chunk: DateChunk,
        network_retry: str,
        network_wait_seconds: int,
        network_max_wait_minutes: int,
        status_store: "ChunkStatusStore | None",
    ) -> HistoricalChunkResult:
        started = time.monotonic()
        while True:
            try:
                return self.history_client.fetch_candles(
                    instrument.instrument_key,
                    interval,
                    chunk.start_date,
                    chunk.end_date,
                )
            except requests.RequestException as error:
                if (
                    network_retry == "fail-fast"
                    or not _is_network_like_error(error)
                    or _network_wait_exceeded(started, network_max_wait_minutes)
                ):
                    return HistoricalChunkResult(
                        instrument_key=instrument.instrument_key,
                        interval=interval,
                        start_date=chunk.start_date,
                        end_date=chunk.end_date,
                        candles=[],
                        ok=False,
                        error=str(error),
                    )
                logger.warning(
                    "Network error for %s chunk %s..%s; retrying after %ss: %s",
                    instrument.symbol,
                    chunk.start_date,
                    chunk.end_date,
                    network_wait_seconds,
                    error,
                )
                if status_store is not None:
                    status_store.update(
                        instrument,
                        interval,
                        chunk,
                        status="FETCH_FAILED_RETRYABLE",
                        error=str(error),
                    )
                time.sleep(network_wait_seconds)

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


@dataclass(frozen=True, slots=True)
class ChunkCompleteness:
    existing_rows: int
    expected_calendar_days: int
    coverage_pct: float
    is_complete: bool


class ChunkCompletenessChecker:
    """Calendar-day based completeness check for already-present chunks."""

    def __init__(self, engine: object) -> None:
        self.engine = engine

    def check(
        self,
        instrument_key: str,
        interval: str,
        chunk: DateChunk,
        min_coverage_pct: float,
    ) -> ChunkCompleteness:
        expected_days = (chunk.end_date - chunk.start_date).days + 1
        query = text(
            """
            SELECT COUNT(*) AS existing_rows
            FROM prices_ohlc
            WHERE instrument_key = :instrument_key
                AND interval = :interval
                AND timestamp >= :start_ts
                AND timestamp < :end_ts
            """
        )
        with self.engine.connect() as conn:
            existing_rows = int(
                conn.execute(
                    query,
                    {
                        "instrument_key": instrument_key,
                        "interval": interval,
                        "start_ts": datetime.combine(
                            chunk.start_date,
                            datetime.min.time(),
                            tzinfo=timezone.utc,
                        ),
                        "end_ts": datetime.combine(
                            chunk.end_date + timedelta(days=1),
                            datetime.min.time(),
                            tzinfo=timezone.utc,
                        ),
                    },
                ).scalar()
                or 0
            )
        coverage_pct = (existing_rows / expected_days * 100) if expected_days else 0.0
        return ChunkCompleteness(
            existing_rows=existing_rows,
            expected_calendar_days=expected_days,
            coverage_pct=coverage_pct,
            is_complete=coverage_pct >= min_coverage_pct,
        )


class ChunkStatusStore:
    """CSV-backed chunk status tracking for resumable ingestion runs."""

    def __init__(self, path: Path, run_id: str) -> None:
        self.path = path
        self.run_id = run_id
        self.rows: dict[tuple[str, str, str, str, str], dict[str, str]] = {}
        self._load()

    def initialize(
        self,
        plans: list[tuple[ResolvedInstrument, list[DateChunk]]],
        interval: str,
        status: str,
    ) -> None:
        for instrument, chunks in plans:
            for chunk in chunks:
                key = self._key(instrument, interval, chunk)
                if key not in self.rows:
                    now = _utc_now()
                    self.rows[key] = {
                        "run_id": self.run_id,
                        "symbol": instrument.symbol,
                        "instrument_key": instrument.instrument_key,
                        "interval": interval,
                        "chunk_start_date": chunk.start_date.isoformat(),
                        "chunk_end_date": chunk.end_date.isoformat(),
                        "status": status,
                        "attempt_count": "0",
                        "candles_received": "0",
                        "candles_inserted": "0",
                        "candles_skipped": "0",
                        "error": "",
                        "started_at": "",
                        "finished_at": now if status == "DRY_RUN_PLANNED" else "",
                        "updated_at": now,
                    }
        self.write()

    def is_completed(
        self,
        instrument: ResolvedInstrument,
        interval: str,
        chunk: DateChunk,
    ) -> bool:
        row = self.rows.get(self._key(instrument, interval, chunk))
        return bool(row and row.get("status") in COMPLETED_CHUNK_STATUSES)

    def mark_started(
        self,
        instrument: ResolvedInstrument,
        interval: str,
        chunk: DateChunk,
    ) -> None:
        row = self._row(instrument, interval, chunk)
        now = _utc_now()
        row["status"] = "PENDING"
        row["started_at"] = row.get("started_at") or now
        row["attempt_count"] = str(int(row.get("attempt_count") or "0") + 1)
        row["updated_at"] = now
        self.write()

    def update(
        self,
        instrument: ResolvedInstrument,
        interval: str,
        chunk: DateChunk,
        status: str,
        candles_received: int | None = None,
        candles_inserted: int | None = None,
        candles_skipped: int | None = None,
        error: str | None = None,
        finished: bool = False,
    ) -> None:
        row = self._row(instrument, interval, chunk)
        now = _utc_now()
        row["status"] = status
        if candles_received is not None:
            row["candles_received"] = str(candles_received)
        if candles_inserted is not None:
            row["candles_inserted"] = str(candles_inserted)
        if candles_skipped is not None:
            row["candles_skipped"] = str(candles_skipped)
        if error is not None:
            row["error"] = error
        if finished:
            row["finished_at"] = now
        row["updated_at"] = now
        self.write()

    def write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        with temp_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=STATUS_COLUMNS)
            writer.writeheader()
            for row in sorted(self.rows.values(), key=_status_sort_key):
                writer.writerow({column: row.get(column, "") for column in STATUS_COLUMNS})
        shutil.move(str(temp_path), str(self.path))

    def _load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                key = (
                    row.get("symbol", ""),
                    row.get("instrument_key", ""),
                    row.get("interval", ""),
                    row.get("chunk_start_date", ""),
                    row.get("chunk_end_date", ""),
                )
                self.rows[key] = {column: row.get(column, "") for column in STATUS_COLUMNS}

    def _row(
        self,
        instrument: ResolvedInstrument,
        interval: str,
        chunk: DateChunk,
    ) -> dict[str, str]:
        key = self._key(instrument, interval, chunk)
        if key not in self.rows:
            now = _utc_now()
            self.rows[key] = {
                "run_id": self.run_id,
                "symbol": instrument.symbol,
                "instrument_key": instrument.instrument_key,
                "interval": interval,
                "chunk_start_date": chunk.start_date.isoformat(),
                "chunk_end_date": chunk.end_date.isoformat(),
                "status": "PENDING",
                "attempt_count": "0",
                "candles_received": "0",
                "candles_inserted": "0",
                "candles_skipped": "0",
                "error": "",
                "started_at": "",
                "finished_at": "",
                "updated_at": now,
            }
        return self.rows[key]

    @staticmethod
    def _key(
        instrument: ResolvedInstrument,
        interval: str,
        chunk: DateChunk,
    ) -> tuple[str, str, str, str, str]:
        return (
            instrument.symbol,
            instrument.instrument_key,
            interval,
            chunk.start_date.isoformat(),
            chunk.end_date.isoformat(),
        )


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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _status_sort_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        row.get("symbol", ""),
        row.get("instrument_key", ""),
        row.get("chunk_start_date", ""),
        row.get("chunk_end_date", ""),
    )


def _is_network_like_error(error: requests.RequestException) -> bool:
    return isinstance(error, (requests.ConnectionError, requests.Timeout)) or (
        isinstance(error, requests.RequestException)
        and getattr(error, "response", None) is None
    )


def _network_wait_exceeded(started: float, max_wait_minutes: int) -> bool:
    if max_wait_minutes == 0:
        return False
    return (time.monotonic() - started) >= max_wait_minutes * 60
