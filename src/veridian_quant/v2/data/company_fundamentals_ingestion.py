"""Company profile and fundamentals ingestion/storage helpers."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import text

from veridian_quant.v2.data.instrument_classification_ingestion import UNKNOWN
from veridian_quant.v2.data.upstox_fundamentals_client import (
    SUPPORTED_FUNDAMENTALS_ENDPOINTS,
    FundamentalsEndpointResult,
    UpstoxFundamentalsClient,
)


SOURCE_DEFAULT = "UPSTOX_FUNDAMENTALS"
CLASSIFICATION_MODE = "static_current"
PROFILE_TABLE = "company_profiles"
KEY_RATIOS_TABLE = "company_key_ratios"
STATEMENTS_TABLE = "company_financial_statements"
SHAREHOLDING_TABLE = "company_shareholding"
ACTIONS_TABLE = "company_corporate_actions"
COMPETITORS_TABLE = "company_competitors"


@dataclass(frozen=True, slots=True)
class CompanyUniverseEntry:
    symbol: str
    isin: str | None = None
    instrument_key: str | None = None
    company_name: str | None = None


@dataclass(slots=True)
class ParsedCompanyFundamentals:
    profiles: list[dict[str, Any]] = field(default_factory=list)
    key_ratios: list[dict[str, Any]] = field(default_factory=list)
    financial_statements: list[dict[str, Any]] = field(default_factory=list)
    shareholding: list[dict[str, Any]] = field(default_factory=list)
    corporate_actions: list[dict[str, Any]] = field(default_factory=list)
    competitors: list[dict[str, Any]] = field(default_factory=list)

    def extend(self, other: "ParsedCompanyFundamentals") -> None:
        self.profiles.extend(other.profiles)
        self.key_ratios.extend(other.key_ratios)
        self.financial_statements.extend(other.financial_statements)
        self.shareholding.extend(other.shareholding)
        self.corporate_actions.extend(other.corporate_actions)
        self.competitors.extend(other.competitors)


@dataclass(slots=True)
class CompanyFundamentalsIngestionSummary:
    symbols_requested: int
    isins_found: int
    endpoints_requested: list[str]
    endpoint_successes: int
    endpoint_no_data: int
    endpoint_failures: int
    rows_parsed_by_table: dict[str, int]
    rows_upserted_by_table: dict[str, int]
    classification_csv_rows_updated: int
    classification_csv_fields_updated: int
    dry_run: bool
    source: str
    failures_by_symbol: dict[str, list[str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbols_requested": self.symbols_requested,
            "isins_found": self.isins_found,
            "endpoints_requested": self.endpoints_requested,
            "endpoint_successes": self.endpoint_successes,
            "endpoint_no_data": self.endpoint_no_data,
            "endpoint_failures": self.endpoint_failures,
            "rows_parsed_by_table": self.rows_parsed_by_table,
            "rows_upserted_by_table": self.rows_upserted_by_table,
            "classification_csv_rows_updated": self.classification_csv_rows_updated,
            "classification_csv_fields_updated": self.classification_csv_fields_updated,
            "dry_run": self.dry_run,
            "source": self.source,
            "failures_by_symbol": self.failures_by_symbol,
            "warnings": self.warnings,
        }


class CompanyFundamentalsStorage:
    """Create and idempotently upsert company fundamentals tables."""

    def __init__(self, engine: object) -> None:
        self.engine = engine

    def ensure_tables(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {PROFILE_TABLE} (
                        isin TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        company_name TEXT,
                        sector TEXT,
                        industry TEXT,
                        basic_industry TEXT,
                        business_description TEXT,
                        website TEXT,
                        market_cap TEXT,
                        snapshot_date TEXT NOT NULL,
                        source TEXT NOT NULL,
                        fetched_at TIMESTAMP NOT NULL,
                        classification_mode TEXT NOT NULL,
                        is_point_in_time_safe BOOLEAN NOT NULL,
                        raw_payload TEXT NOT NULL,
                        PRIMARY KEY (isin, source, snapshot_date)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {KEY_RATIOS_TABLE} (
                        isin TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        ratio_name TEXT NOT NULL,
                        ratio_value TEXT,
                        unit TEXT,
                        snapshot_date TEXT NOT NULL,
                        source TEXT NOT NULL,
                        fetched_at TIMESTAMP NOT NULL,
                        is_point_in_time_safe BOOLEAN NOT NULL,
                        raw_payload TEXT NOT NULL,
                        PRIMARY KEY (isin, ratio_name, source, snapshot_date)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {STATEMENTS_TABLE} (
                        isin TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        statement_type TEXT NOT NULL,
                        reporting_frequency TEXT,
                        fiscal_year TEXT,
                        fiscal_quarter TEXT,
                        period_end_date TEXT NOT NULL,
                        source TEXT NOT NULL,
                        fetched_at TIMESTAMP NOT NULL,
                        is_point_in_time_safe BOOLEAN NOT NULL,
                        raw_payload TEXT NOT NULL,
                        PRIMARY KEY (
                            isin,
                            statement_type,
                            reporting_frequency,
                            period_end_date,
                            source
                        )
                    )
                    """
                )
            )
            conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {SHAREHOLDING_TABLE} (
                        isin TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        holder_category TEXT NOT NULL,
                        holding_percent TEXT,
                        period_end_date TEXT NOT NULL,
                        source TEXT NOT NULL,
                        fetched_at TIMESTAMP NOT NULL,
                        is_point_in_time_safe BOOLEAN NOT NULL,
                        raw_payload TEXT NOT NULL,
                        PRIMARY KEY (isin, holder_category, period_end_date, source)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {ACTIONS_TABLE} (
                        isin TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        event_key TEXT NOT NULL,
                        action_type TEXT,
                        ex_date TEXT,
                        record_date TEXT,
                        announced_date TEXT,
                        value TEXT,
                        source TEXT NOT NULL,
                        fetched_at TIMESTAMP NOT NULL,
                        is_point_in_time_safe BOOLEAN NOT NULL,
                        raw_payload TEXT NOT NULL,
                        PRIMARY KEY (isin, event_key, source)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {COMPETITORS_TABLE} (
                        isin TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        competitor_name TEXT NOT NULL,
                        competitor_symbol TEXT,
                        competitor_isin TEXT,
                        snapshot_date TEXT NOT NULL,
                        source TEXT NOT NULL,
                        fetched_at TIMESTAMP NOT NULL,
                        is_point_in_time_safe BOOLEAN NOT NULL,
                        raw_payload TEXT NOT NULL,
                        PRIMARY KEY (isin, competitor_name, source, snapshot_date)
                    )
                    """
                )
            )

    def upsert(self, parsed: ParsedCompanyFundamentals) -> dict[str, int]:
        self.ensure_tables()
        rows_by_table = {
            PROFILE_TABLE: parsed.profiles,
            KEY_RATIOS_TABLE: parsed.key_ratios,
            STATEMENTS_TABLE: parsed.financial_statements,
            SHAREHOLDING_TABLE: parsed.shareholding,
            ACTIONS_TABLE: parsed.corporate_actions,
            COMPETITORS_TABLE: parsed.competitors,
        }
        with self.engine.begin() as conn:
            for table, rows in rows_by_table.items():
                if not rows:
                    continue
                delete_sql, insert_sql = _upsert_sql(table)
                for row in rows:
                    conn.execute(text(delete_sql), row)
                conn.execute(text(insert_sql), rows)
        return {table: len(rows) for table, rows in rows_by_table.items()}


class CompanyFundamentalsIngestionRunner:
    """Fetch, parse, and optionally store company fundamentals payloads."""

    def __init__(
        self,
        engine: object,
        client: UpstoxFundamentalsClient,
        storage: CompanyFundamentalsStorage | None = None,
    ) -> None:
        self.engine = engine
        self.client = client
        self.storage = storage or CompanyFundamentalsStorage(engine)

    def run(
        self,
        *,
        symbols_file: Path | None = None,
        endpoints: Iterable[str] = ("profile",),
        source: str = SOURCE_DEFAULT,
        dry_run: bool = True,
        limit: int | None = None,
        symbols: Iterable[str] | None = None,
        isins: Iterable[str] | None = None,
        update_classification_csv: bool = False,
        classification_file: Path | None = None,
    ) -> CompanyFundamentalsIngestionSummary:
        endpoint_list = parse_endpoints(endpoints)
        entries = load_company_universe(
            symbols_file=symbols_file,
            symbols=symbols,
            isins=isins,
            limit=limit,
        )
        fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)
        parsed = ParsedCompanyFundamentals()
        successes = 0
        no_data = 0
        failures = 0
        failures_by_symbol: dict[str, list[str]] = {}
        warnings: list[str] = []

        for entry in entries:
            if not entry.isin:
                failures += len(endpoint_list)
                failures_by_symbol.setdefault(entry.symbol, []).append("missing ISIN")
                continue
            for endpoint in endpoint_list:
                result = self.client.fetch_endpoint(entry.isin, endpoint)
                if result.no_data:
                    no_data += 1
                    if not result.ok:
                        failures_by_symbol.setdefault(entry.symbol, []).append(
                            f"{endpoint}: {result.error or 'no data'}"
                        )
                    continue
                if not result.ok:
                    failures += 1
                    failures_by_symbol.setdefault(entry.symbol, []).append(
                        f"{endpoint}: {result.error or 'endpoint failed'}"
                    )
                    continue
                successes += 1
                try:
                    parsed.extend(parse_endpoint_payload(entry, endpoint, result.payload, source, fetched_at))
                except ValueError as error:
                    failures += 1
                    failures_by_symbol.setdefault(entry.symbol, []).append(f"{endpoint}: {error}")

        rows_upserted = _empty_counts()
        if not dry_run:
            rows_upserted = self.storage.upsert(parsed)

        csv_rows_updated = 0
        csv_fields_updated = 0
        if update_classification_csv:
            if classification_file is None:
                warnings.append("classification CSV update requested without --classification-file")
            elif dry_run:
                csv_rows_updated, csv_fields_updated = count_classification_csv_updates(
                    classification_file,
                    parsed.profiles,
                )
            else:
                csv_rows_updated, csv_fields_updated = update_classification_csv_from_profiles(
                    classification_file,
                    parsed.profiles,
                    source=source,
                )

        return CompanyFundamentalsIngestionSummary(
            symbols_requested=len(entries),
            isins_found=sum(1 for entry in entries if entry.isin),
            endpoints_requested=endpoint_list,
            endpoint_successes=successes,
            endpoint_no_data=no_data,
            endpoint_failures=failures,
            rows_parsed_by_table=_parsed_counts(parsed),
            rows_upserted_by_table=rows_upserted,
            classification_csv_rows_updated=csv_rows_updated,
            classification_csv_fields_updated=csv_fields_updated,
            dry_run=dry_run,
            source=source,
            failures_by_symbol=failures_by_symbol,
            warnings=warnings,
        )


def parse_endpoints(endpoints: Iterable[str] | str) -> list[str]:
    if isinstance(endpoints, str):
        raw_values = [value.strip() for value in endpoints.split(",")]
    else:
        raw_values = [str(value).strip() for value in endpoints]
    values = [value.lower().replace("-", "_") for value in raw_values if value]
    if not values or "all" in values:
        return list(SUPPORTED_FUNDAMENTALS_ENDPOINTS)
    invalid = sorted(set(values) - set(SUPPORTED_FUNDAMENTALS_ENDPOINTS))
    if invalid:
        valid = ", ".join(("ALL", *SUPPORTED_FUNDAMENTALS_ENDPOINTS))
        raise ValueError(f"invalid endpoint(s): {', '.join(invalid)}; valid: {valid}")
    return values


def load_company_universe(
    *,
    symbols_file: Path | None,
    symbols: Iterable[str] | None = None,
    isins: Iterable[str] | None = None,
    limit: int | None = None,
) -> list[CompanyUniverseEntry]:
    entries: list[CompanyUniverseEntry] = []
    if symbols_file is not None:
        for row in _read_csv(symbols_file):
            symbol = _clean(row.get("symbol") or row.get("trading_symbol")).upper()
            if not symbol:
                continue
            instrument_key = _optional(row.get("instrument_key"))
            entries.append(
                CompanyUniverseEntry(
                    symbol=symbol,
                    isin=_optional(row.get("isin")) or _isin_from_instrument_key(instrument_key),
                    instrument_key=instrument_key,
                    company_name=_optional(row.get("company_name") or row.get("name")),
                )
            )
    for symbol in symbols or ():
        value = _clean(symbol).upper()
        if value:
            entries.append(CompanyUniverseEntry(symbol=value))
    for isin in isins or ():
        value = _clean(isin).upper()
        if value:
            entries.append(CompanyUniverseEntry(symbol=value, isin=value))

    symbol_filter = {_clean(symbol).upper() for symbol in (symbols or ()) if _clean(symbol)}
    if symbol_filter and symbols_file is not None:
        entries = [entry for entry in entries if entry.symbol in symbol_filter]

    deduped: list[CompanyUniverseEntry] = []
    seen: set[tuple[str, str | None]] = set()
    for entry in entries:
        key = (entry.symbol, entry.isin)
        if key not in seen:
            seen.add(key)
            deduped.append(entry)
    return deduped[:limit] if limit is not None else deduped


def parse_endpoint_payload(
    entry: CompanyUniverseEntry,
    endpoint: str,
    payload: Any,
    source: str,
    fetched_at: datetime,
) -> ParsedCompanyFundamentals:
    if payload is None:
        return ParsedCompanyFundamentals()
    endpoint = endpoint.lower()
    if endpoint == "profile":
        return ParsedCompanyFundamentals(
            profiles=[_profile_row(entry, _payload_dict(payload), source, fetched_at)]
        )
    if endpoint == "key_ratios":
        return ParsedCompanyFundamentals(
            key_ratios=[
                _key_ratio_row(entry, ratio, source, fetched_at)
                for ratio in _ratio_items(payload)
            ]
        )
    if endpoint in {"income_statement", "balance_sheet", "cash_flow"}:
        return ParsedCompanyFundamentals(
            financial_statements=[
                _statement_row(entry, endpoint, statement, source, fetched_at)
                for statement in _statement_items(payload)
            ]
        )
    if endpoint == "shareholding":
        return ParsedCompanyFundamentals(
            shareholding=[
                _shareholding_row(entry, row, source, fetched_at)
                for row in _list_items(payload, "shareholding")
            ]
        )
    if endpoint == "corporate_actions":
        return ParsedCompanyFundamentals(
            corporate_actions=[
                _corporate_action_row(entry, row, source, fetched_at)
                for row in _list_items(payload, "actions")
            ]
        )
    if endpoint == "competitors":
        return ParsedCompanyFundamentals(
            competitors=[
                _competitor_row(entry, row, source, fetched_at)
                for row in _list_items(payload, "competitors")
            ]
        )
    raise ValueError(f"unsupported endpoint: {endpoint}")


def update_classification_csv_from_profiles(
    classification_file: Path,
    profile_rows: Iterable[dict[str, Any]],
    *,
    source: str,
) -> tuple[int, int]:
    rows, fieldnames = _read_csv_with_fields(classification_file)
    rows_updated, fields_updated = _apply_profile_updates(rows, profile_rows, source)
    if rows_updated:
        with Path(classification_file).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    return rows_updated, fields_updated


def count_classification_csv_updates(
    classification_file: Path,
    profile_rows: Iterable[dict[str, Any]],
) -> tuple[int, int]:
    rows, _ = _read_csv_with_fields(classification_file)
    return _apply_profile_updates(rows, profile_rows, SOURCE_DEFAULT)


def _profile_row(
    entry: CompanyUniverseEntry,
    payload: dict[str, Any],
    source: str,
    fetched_at: datetime,
) -> dict[str, Any]:
    snapshot_date = _date_like(payload, "snapshot_date", "as_of_date", "date") or fetched_at.date().isoformat()
    return {
        "isin": entry.isin,
        "symbol": entry.symbol,
        "company_name": _first_text(payload, "company_name", "name") or entry.company_name,
        "sector": _first_text(payload, "sector") or UNKNOWN,
        "industry": _first_text(payload, "industry"),
        "basic_industry": _first_text(payload, "basic_industry", "basicIndustry"),
        "business_description": _first_text(payload, "business_description", "description"),
        "website": _first_text(payload, "website"),
        "market_cap": _scalar(payload.get("market_cap") or payload.get("marketCap")),
        "snapshot_date": snapshot_date,
        "source": source,
        "fetched_at": fetched_at,
        "classification_mode": CLASSIFICATION_MODE,
        "is_point_in_time_safe": False,
        "raw_payload": _json_dumps(payload),
    }


def _key_ratio_row(
    entry: CompanyUniverseEntry,
    ratio: dict[str, Any],
    source: str,
    fetched_at: datetime,
) -> dict[str, Any]:
    snapshot_date = _date_like(ratio, "snapshot_date", "as_of_date", "date") or fetched_at.date().isoformat()
    return {
        "isin": entry.isin,
        "symbol": entry.symbol,
        "ratio_name": _first_text(ratio, "ratio_name", "name", "key") or "UNKNOWN",
        "ratio_value": _scalar(ratio.get("ratio_value") or ratio.get("value")),
        "unit": _first_text(ratio, "unit"),
        "snapshot_date": snapshot_date,
        "source": source,
        "fetched_at": fetched_at,
        "is_point_in_time_safe": False,
        "raw_payload": _json_dumps(ratio),
    }


def _statement_row(
    entry: CompanyUniverseEntry,
    statement_type: str,
    statement: dict[str, Any],
    source: str,
    fetched_at: datetime,
) -> dict[str, Any]:
    period_end = _date_like(statement, "period_end_date", "periodEndDate", "date")
    if not period_end:
        raise ValueError(f"{statement_type} statement missing period_end_date")
    return {
        "isin": entry.isin,
        "symbol": entry.symbol,
        "statement_type": statement_type,
        "reporting_frequency": _first_text(statement, "reporting_frequency", "frequency"),
        "fiscal_year": _scalar(statement.get("fiscal_year") or statement.get("year")),
        "fiscal_quarter": _scalar(statement.get("fiscal_quarter") or statement.get("quarter")),
        "period_end_date": period_end,
        "source": source,
        "fetched_at": fetched_at,
        "is_point_in_time_safe": True,
        "raw_payload": _json_dumps(statement),
    }


def _shareholding_row(
    entry: CompanyUniverseEntry,
    row: dict[str, Any],
    source: str,
    fetched_at: datetime,
) -> dict[str, Any]:
    period_end = _date_like(row, "period_end_date", "periodEndDate", "date") or fetched_at.date().isoformat()
    return {
        "isin": entry.isin,
        "symbol": entry.symbol,
        "holder_category": _first_text(row, "holder_category", "category", "name") or "UNKNOWN",
        "holding_percent": _scalar(row.get("holding_percent") or row.get("percent")),
        "period_end_date": period_end,
        "source": source,
        "fetched_at": fetched_at,
        "is_point_in_time_safe": bool(_date_like(row, "period_end_date", "periodEndDate", "date")),
        "raw_payload": _json_dumps(row),
    }


def _corporate_action_row(
    entry: CompanyUniverseEntry,
    row: dict[str, Any],
    source: str,
    fetched_at: datetime,
) -> dict[str, Any]:
    payload_json = _json_dumps(row)
    return {
        "isin": entry.isin,
        "symbol": entry.symbol,
        "event_key": hashlib.sha256(payload_json.encode("utf-8")).hexdigest(),
        "action_type": _first_text(row, "action_type", "type"),
        "ex_date": _date_like(row, "ex_date", "exDate"),
        "record_date": _date_like(row, "record_date", "recordDate"),
        "announced_date": _date_like(row, "announced_date", "announcementDate"),
        "value": _scalar(row.get("value") or row.get("ratio")),
        "source": source,
        "fetched_at": fetched_at,
        "is_point_in_time_safe": bool(_date_like(row, "ex_date", "exDate", "record_date", "recordDate")),
        "raw_payload": payload_json,
    }


def _competitor_row(
    entry: CompanyUniverseEntry,
    row: dict[str, Any],
    source: str,
    fetched_at: datetime,
) -> dict[str, Any]:
    snapshot_date = _date_like(row, "snapshot_date", "as_of_date", "date") or fetched_at.date().isoformat()
    return {
        "isin": entry.isin,
        "symbol": entry.symbol,
        "competitor_name": _first_text(row, "competitor_name", "company_name", "name") or "UNKNOWN",
        "competitor_symbol": _first_text(row, "competitor_symbol", "symbol"),
        "competitor_isin": _first_text(row, "competitor_isin", "isin"),
        "snapshot_date": snapshot_date,
        "source": source,
        "fetched_at": fetched_at,
        "is_point_in_time_safe": False,
        "raw_payload": _json_dumps(row),
    }


def _ratio_items(payload: Any) -> list[dict[str, Any]]:
    payload = _payload_dict(payload)
    ratios = payload.get("ratios", payload)
    if isinstance(ratios, list):
        return [_payload_dict(item) for item in ratios]
    if isinstance(ratios, dict):
        return [
            {"ratio_name": name, "ratio_value": value}
            for name, value in ratios.items()
            if name not in {"snapshot_date", "as_of_date", "date"}
        ]
    raise ValueError("key_ratios payload must contain a dict or list")


def _statement_items(payload: Any) -> list[dict[str, Any]]:
    payload = _payload_dict(payload)
    statements = payload.get("statements", payload.get("periods", payload))
    if isinstance(statements, list):
        return [_payload_dict(item) for item in statements]
    if isinstance(statements, dict):
        return [_payload_dict(statements)]
    raise ValueError("statement payload must contain a dict or list")


def _list_items(payload: Any, key: str) -> list[dict[str, Any]]:
    payload = _payload_dict(payload)
    items = payload.get(key, payload)
    if isinstance(items, list):
        return [_payload_dict(item) for item in items]
    if isinstance(items, dict):
        return [_payload_dict(items)]
    raise ValueError(f"{key} payload must contain a dict or list")


def _payload_dict(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    raise ValueError("payload must be an object")


def _apply_profile_updates(
    rows: list[dict[str, str]],
    profile_rows: Iterable[dict[str, Any]],
    source: str,
) -> tuple[int, int]:
    profiles = {str(row.get("symbol", "")).upper(): row for row in profile_rows}
    rows_updated = 0
    fields_updated = 0
    for row in rows:
        profile = profiles.get(str(row.get("symbol", "")).upper())
        if not profile:
            continue
        updated_this_row = False
        for csv_field, profile_field in (
            ("company_name", "company_name"),
            ("sector", "sector"),
            ("industry", "industry"),
            ("basic_industry", "basic_industry"),
            ("source", "source"),
        ):
            value = _optional(profile.get(profile_field))
            if csv_field == "source":
                value = source
            if value and value != UNKNOWN and row.get(csv_field, "").strip() != value:
                row[csv_field] = value
                fields_updated += 1
                updated_this_row = True
        if row.get("classification_mode", "") != CLASSIFICATION_MODE:
            row["classification_mode"] = CLASSIFICATION_MODE
            fields_updated += 1
            updated_this_row = True
        if updated_this_row:
            rows_updated += 1
    return rows_updated, fields_updated


def _upsert_sql(table: str) -> tuple[str, str]:
    keys = {
        PROFILE_TABLE: ("isin", "source", "snapshot_date"),
        KEY_RATIOS_TABLE: ("isin", "ratio_name", "source", "snapshot_date"),
        STATEMENTS_TABLE: ("isin", "statement_type", "reporting_frequency", "period_end_date", "source"),
        SHAREHOLDING_TABLE: ("isin", "holder_category", "period_end_date", "source"),
        ACTIONS_TABLE: ("isin", "event_key", "source"),
        COMPETITORS_TABLE: ("isin", "competitor_name", "source", "snapshot_date"),
    }[table]
    columns = _table_columns(table)
    where = " AND ".join(f"{key} = :{key}" for key in keys)
    insert_columns = ", ".join(columns)
    values = ", ".join(f":{column}" for column in columns)
    return (
        f"DELETE FROM {table} WHERE {where}",
        f"INSERT INTO {table} ({insert_columns}) VALUES ({values})",
    )


def _table_columns(table: str) -> tuple[str, ...]:
    return {
        PROFILE_TABLE: (
            "isin",
            "symbol",
            "company_name",
            "sector",
            "industry",
            "basic_industry",
            "business_description",
            "website",
            "market_cap",
            "snapshot_date",
            "source",
            "fetched_at",
            "classification_mode",
            "is_point_in_time_safe",
            "raw_payload",
        ),
        KEY_RATIOS_TABLE: (
            "isin",
            "symbol",
            "ratio_name",
            "ratio_value",
            "unit",
            "snapshot_date",
            "source",
            "fetched_at",
            "is_point_in_time_safe",
            "raw_payload",
        ),
        STATEMENTS_TABLE: (
            "isin",
            "symbol",
            "statement_type",
            "reporting_frequency",
            "fiscal_year",
            "fiscal_quarter",
            "period_end_date",
            "source",
            "fetched_at",
            "is_point_in_time_safe",
            "raw_payload",
        ),
        SHAREHOLDING_TABLE: (
            "isin",
            "symbol",
            "holder_category",
            "holding_percent",
            "period_end_date",
            "source",
            "fetched_at",
            "is_point_in_time_safe",
            "raw_payload",
        ),
        ACTIONS_TABLE: (
            "isin",
            "symbol",
            "event_key",
            "action_type",
            "ex_date",
            "record_date",
            "announced_date",
            "value",
            "source",
            "fetched_at",
            "is_point_in_time_safe",
            "raw_payload",
        ),
        COMPETITORS_TABLE: (
            "isin",
            "symbol",
            "competitor_name",
            "competitor_symbol",
            "competitor_isin",
            "snapshot_date",
            "source",
            "fetched_at",
            "is_point_in_time_safe",
            "raw_payload",
        ),
    }[table]


def _parsed_counts(parsed: ParsedCompanyFundamentals) -> dict[str, int]:
    return {
        PROFILE_TABLE: len(parsed.profiles),
        KEY_RATIOS_TABLE: len(parsed.key_ratios),
        STATEMENTS_TABLE: len(parsed.financial_statements),
        SHAREHOLDING_TABLE: len(parsed.shareholding),
        ACTIONS_TABLE: len(parsed.corporate_actions),
        COMPETITORS_TABLE: len(parsed.competitors),
    }


def _empty_counts() -> dict[str, int]:
    return {
        PROFILE_TABLE: 0,
        KEY_RATIOS_TABLE: 0,
        STATEMENTS_TABLE: 0,
        SHAREHOLDING_TABLE: 0,
        ACTIONS_TABLE: 0,
        COMPETITORS_TABLE: 0,
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _read_csv_with_fields(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def _isin_from_instrument_key(instrument_key: str | None) -> str | None:
    if not instrument_key or "|" not in instrument_key:
        return None
    exchange, token = instrument_key.split("|", 1)
    return token if exchange == "NSE_EQ" and token else None


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))


def _first_text(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = _optional(payload.get(key))
        if value:
            return value
    return None


def _date_like(payload: dict[str, Any], *keys: str) -> str | None:
    value = _first_text(payload, *keys)
    if not value:
        return None
    return value[:10]


def _scalar(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return _json_dumps(value)
    text_value = str(value).strip()
    return text_value or None


def _optional(value: object) -> str | None:
    text_value = _clean(value)
    return text_value or None


def _clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()
