"""Static-current instrument classification ingestion helpers.

This module imports current sector/industry/cap metadata for diagnostics. Rows
created here are explicitly labelled ``static_current``: they are not
point-in-time historical classifications and must not be treated as historical
truth in later benchmark or exposure reports.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

from sqlalchemy import text

from veridian_quant.v2.data.market_context_models import (
    ClassificationMode,
    InstrumentClassification,
    MarketCapBucket,
    normalize_index_symbol,
    normalize_market_cap_bucket,
)
CLASSIFICATION_TABLE = "instrument_classifications"
UNKNOWN = "UNKNOWN"
INDEX_MEMBERSHIP_DELIMITER = "|"


@dataclass(frozen=True, slots=True)
class ResearchSymbol:
    symbol: str
    instrument_key: str | None = None
    trading_symbol: str | None = None
    company_name: str | None = None


@dataclass(frozen=True, slots=True)
class ClassificationRecord:
    classification: InstrumentClassification
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ClassificationParseResult:
    records: tuple[ClassificationRecord, ...]
    rows_read: int
    invalid_rows: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(slots=True)
class InstrumentClassificationIngestionSummary:
    """Compact static-current classification ingestion summary."""

    requested_symbols: int
    classification_rows_read: int
    symbols_classified: int
    symbols_missing_classification: int
    missing_symbols: list[str]
    unknown_sectors: int
    unknown_market_cap_buckets: int
    rows_inserted: int
    invalid_rows_rejected: int
    classification_mode: str
    source: str
    dry_run: bool
    audit_only: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_symbols": self.requested_symbols,
            "classification_rows_read": self.classification_rows_read,
            "symbols_classified": self.symbols_classified,
            "symbols_missing_classification": self.symbols_missing_classification,
            "missing_symbols": self.missing_symbols,
            "unknown_sectors": self.unknown_sectors,
            "unknown_market_cap_buckets": self.unknown_market_cap_buckets,
            "rows_inserted": self.rows_inserted,
            "invalid_rows_rejected": self.invalid_rows_rejected,
            "classification_mode": self.classification_mode,
            "source": self.source,
            "dry_run": self.dry_run,
            "audit_only": self.audit_only,
            "warnings": self.warnings,
        }


class InstrumentClassificationStorage:
    """Create and upsert the static classification storage table."""

    def __init__(self, engine: object, table_name: str = CLASSIFICATION_TABLE) -> None:
        self.engine = engine
        self.table_name = _validate_identifier(table_name)

    def ensure_table(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        symbol TEXT NOT NULL,
                        instrument_key TEXT,
                        isin TEXT,
                        company_name TEXT,
                        sector TEXT NOT NULL,
                        industry TEXT,
                        basic_industry TEXT,
                        market_cap_bucket TEXT NOT NULL,
                        index_membership TEXT,
                        classification_mode TEXT NOT NULL,
                        source TEXT NOT NULL,
                        effective_from DATE NOT NULL,
                        effective_to DATE,
                        notes TEXT,
                        ingested_at TIMESTAMP NOT NULL,
                        PRIMARY KEY (
                            symbol,
                            source,
                            classification_mode,
                            effective_from
                        )
                    )
                    """
                )
            )

    def upsert(self, records: Iterable[ClassificationRecord]) -> int:
        rows = [_storage_row(record.classification) for record in records]
        if not rows:
            return 0
        self.ensure_table()
        with self.engine.begin() as conn:
            for row in rows:
                conn.execute(
                    text(
                        f"""
                        DELETE FROM {self.table_name}
                        WHERE symbol = :symbol
                          AND source = :source
                          AND classification_mode = :classification_mode
                          AND effective_from = :effective_from
                        """
                    ),
                    row,
                )
            conn.execute(
                text(
                    f"""
                    INSERT INTO {self.table_name} (
                        symbol,
                        instrument_key,
                        isin,
                        company_name,
                        sector,
                        industry,
                        basic_industry,
                        market_cap_bucket,
                        index_membership,
                        classification_mode,
                        source,
                        effective_from,
                        effective_to,
                        notes,
                        ingested_at
                    )
                    VALUES (
                        :symbol,
                        :instrument_key,
                        :isin,
                        :company_name,
                        :sector,
                        :industry,
                        :basic_industry,
                        :market_cap_bucket,
                        :index_membership,
                        :classification_mode,
                        :source,
                        :effective_from,
                        :effective_to,
                        :notes,
                        :ingested_at
                    )
                    """
                ),
                rows,
            )
        return len(rows)


class InstrumentClassificationIngestionRunner:
    """Read, validate, audit, and optionally store static-current classifications."""

    def __init__(
        self,
        engine: object,
        storage: InstrumentClassificationStorage | None = None,
    ) -> None:
        self.engine = engine
        self.storage = storage or InstrumentClassificationStorage(engine)

    def run(
        self,
        *,
        classification_file: Path,
        symbols_file: Path,
        effective_from: date,
        source: str,
        classification_mode: str = ClassificationMode.STATIC_CURRENT.value,
        dry_run: bool = True,
        audit_only: bool = False,
    ) -> InstrumentClassificationIngestionSummary:
        if classification_mode != ClassificationMode.STATIC_CURRENT.value:
            raise ValueError("static classification ingestion requires classification_mode=static_current")
        source = _non_empty(source, "source")
        research_symbols = load_research_symbols(symbols_file)
        requested = set(research_symbols)
        parse_result = load_classification_file(
            classification_file,
            effective_from=effective_from,
            source=source,
            classification_mode=classification_mode,
            research_symbols=research_symbols,
        )
        records = [
            record for record in parse_result.records if record.classification.symbol in requested
        ]
        classified = {record.classification.symbol for record in records}
        missing = sorted(requested - classified)
        warnings = list(parse_result.warnings)
        for record in records:
            warnings.extend(record.warnings)

        rows_inserted = 0
        if not dry_run and not audit_only:
            rows_inserted = self.storage.upsert(records)

        return InstrumentClassificationIngestionSummary(
            requested_symbols=len(requested),
            classification_rows_read=parse_result.rows_read,
            symbols_classified=len(classified),
            symbols_missing_classification=len(missing),
            missing_symbols=missing,
            unknown_sectors=sum(1 for record in records if record.classification.sector == UNKNOWN),
            unknown_market_cap_buckets=sum(
                1
                for record in records
                if record.classification.market_cap_bucket == MarketCapBucket.UNKNOWN
            ),
            rows_inserted=rows_inserted,
            invalid_rows_rejected=len(parse_result.invalid_rows),
            classification_mode=classification_mode,
            source=source,
            dry_run=dry_run or audit_only,
            audit_only=audit_only,
            warnings=warnings,
        )


def load_research_symbols(path: Path) -> dict[str, ResearchSymbol]:
    """Load the Research200 symbol universe without modifying config/data."""

    rows = _read_csv(path)
    symbols: dict[str, ResearchSymbol] = {}
    for row in rows:
        symbol = _clean(row.get("symbol") or row.get("trading_symbol")).upper()
        if not symbol or symbol in symbols:
            continue
        symbols[symbol] = ResearchSymbol(
            symbol=symbol,
            instrument_key=_optional(row.get("instrument_key")),
            trading_symbol=_optional(row.get("trading_symbol")),
            company_name=_optional(row.get("name") or row.get("company_name")),
        )
    return symbols


def load_classification_file(
    path: Path,
    *,
    effective_from: date,
    source: str,
    classification_mode: str,
    research_symbols: dict[str, ResearchSymbol] | None = None,
) -> ClassificationParseResult:
    rows = _read_csv(path)
    records: list[ClassificationRecord] = []
    invalid_rows: list[str] = []
    warnings: list[str] = []
    research_symbols = research_symbols or {}

    if classification_mode != ClassificationMode.STATIC_CURRENT.value:
        raise ValueError("static classification ingestion requires classification_mode=static_current")

    for index, row in enumerate(rows, start=2):
        try:
            records.append(
                parse_classification_row(
                    row,
                    effective_from=effective_from,
                    source=source,
                    classification_mode=classification_mode,
                    research_symbol=research_symbols.get(
                        _clean(row.get("symbol") or row.get("trading_symbol")).upper()
                    ),
                )
            )
        except ValueError as error:
            invalid_rows.append(f"row {index}: {error}")

    duplicate_symbols = _duplicate_symbols(record.classification.symbol for record in records)
    if duplicate_symbols:
        warnings.append("duplicate classification symbols: " + ", ".join(duplicate_symbols))

    return ClassificationParseResult(
        records=tuple(records),
        rows_read=len(rows),
        invalid_rows=tuple(invalid_rows),
        warnings=tuple(warnings),
    )


def parse_classification_row(
    row: dict[str, object],
    *,
    effective_from: date,
    source: str,
    classification_mode: str = ClassificationMode.STATIC_CURRENT.value,
    research_symbol: ResearchSymbol | None = None,
) -> ClassificationRecord:
    """Parse one CSV row into a static-current ``InstrumentClassification``."""

    if classification_mode != ClassificationMode.STATIC_CURRENT.value:
        raise ValueError("static classification ingestion requires classification_mode=static_current")

    symbol = _clean(row.get("symbol") or row.get("trading_symbol")).upper()
    if not symbol:
        raise ValueError("symbol must be non-empty")

    effective_to_value = _optional(row.get("effective_to"))
    effective_to = date.fromisoformat(effective_to_value) if effective_to_value else None
    sector = _optional(row.get("sector")) or UNKNOWN
    industry = _optional(row.get("industry"))
    basic_industry = _optional(row.get("basic_industry"))
    memberships = parse_index_membership(row.get("index_membership"))
    bucket, bucket_warnings = resolve_market_cap_bucket(
        row.get("market_cap_bucket"),
        memberships,
        symbol=symbol,
    )

    metadata = research_symbol or ResearchSymbol(symbol=symbol)
    classification = InstrumentClassification(
        symbol=symbol,
        instrument_key=_optional(row.get("instrument_key")) or metadata.instrument_key,
        isin=_optional(row.get("isin")) or _isin_from_instrument_key(metadata.instrument_key),
        company_name=_optional(row.get("company_name")) or metadata.company_name,
        sector=sector,
        industry=industry,
        basic_industry=basic_industry,
        market_cap_bucket=bucket,
        index_membership=memberships,
        effective_from=effective_from,
        effective_to=effective_to,
        source=_optional(row.get("source")) or source,
        classification_mode=classification_mode,
        notes=_optional(row.get("notes")),
    )
    return ClassificationRecord(classification=classification, warnings=tuple(bucket_warnings))


def parse_index_membership(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    text_value = str(value).strip()
    if not text_value:
        return ()
    for delimiter in (";", ","):
        text_value = text_value.replace(delimiter, INDEX_MEMBERSHIP_DELIMITER)
    memberships: list[str] = []
    seen: set[str] = set()
    for part in text_value.split(INDEX_MEMBERSHIP_DELIMITER):
        if not part.strip():
            continue
        normalized = normalize_index_symbol(part)
        if normalized not in seen:
            seen.add(normalized)
            memberships.append(normalized)
    return tuple(memberships)


def resolve_market_cap_bucket(
    explicit_bucket: object,
    index_membership: Iterable[str],
    *,
    symbol: str,
) -> tuple[MarketCapBucket, list[str]]:
    warnings: list[str] = []
    explicit_text = _optional(explicit_bucket)
    derived = _derive_bucket_from_membership(index_membership)

    if explicit_text:
        explicit = normalize_market_cap_bucket(explicit_text)
        if derived and derived != explicit:
            warnings.append(
                f"{symbol}: explicit market_cap_bucket={explicit.value} conflicts with "
                f"index_membership-derived {derived.value}; kept explicit bucket"
            )
        return explicit, warnings
    if derived is not None:
        return derived, warnings
    memberships = tuple(index_membership)
    if memberships:
        warnings.append(f"{symbol}: conflicting or unclear cap membership; using unknown")
    return MarketCapBucket.UNKNOWN, warnings


def _derive_bucket_from_membership(index_membership: Iterable[str]) -> MarketCapBucket | None:
    buckets: set[MarketCapBucket] = set()
    for index_symbol in index_membership:
        if index_symbol in {"NIFTY_50", "NIFTY_100"}:
            buckets.add(MarketCapBucket.LARGE_CAP)
        elif index_symbol.startswith("NIFTY_MIDCAP"):
            buckets.add(MarketCapBucket.MID_CAP)
        elif index_symbol.startswith("NIFTY_SMALLCAP"):
            buckets.add(MarketCapBucket.SMALL_CAP)
        elif index_symbol.startswith("NIFTY_MICROCAP"):
            buckets.add(MarketCapBucket.MICRO_CAP)
    return next(iter(buckets)) if len(buckets) == 1 else None


def _storage_row(classification: InstrumentClassification) -> dict[str, object]:
    return {
        "symbol": classification.symbol,
        "instrument_key": classification.instrument_key,
        "isin": classification.isin,
        "company_name": classification.company_name,
        "sector": classification.sector,
        "industry": classification.industry,
        "basic_industry": classification.basic_industry,
        "market_cap_bucket": classification.market_cap_bucket.value,
        "index_membership": INDEX_MEMBERSHIP_DELIMITER.join(classification.index_membership),
        "classification_mode": classification.classification_mode.value,
        "source": classification.source,
        "effective_from": classification.effective_from,
        "effective_to": classification.effective_to,
        "notes": classification.notes,
        "ingested_at": datetime.now(timezone.utc).replace(tzinfo=None),
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _duplicate_symbols(symbols: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for raw_symbol in symbols:
        symbol = _clean(raw_symbol).upper()
        if not symbol:
            continue
        if symbol in seen:
            duplicates.add(symbol)
        seen.add(symbol)
    return sorted(duplicates)


def _isin_from_instrument_key(instrument_key: str | None) -> str | None:
    if not instrument_key or "|" not in instrument_key:
        return None
    exchange, token = instrument_key.split("|", 1)
    if exchange == "NSE_EQ" and token:
        return token
    return None


def _optional(value: object) -> str | None:
    text_value = _clean(value)
    return text_value or None


def _clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _non_empty(value: object, field_name: str) -> str:
    text_value = _clean(value)
    if not text_value:
        raise ValueError(f"{field_name} must be non-empty")
    return text_value


def _validate_identifier(identifier: str) -> str:
    if not identifier.replace("_", "").isalnum():
        raise ValueError(f"invalid SQL identifier: {identifier}")
    return identifier
