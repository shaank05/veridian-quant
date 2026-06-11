"""Instrument resolution for V2 ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import text


SUPPORTED_EXCHANGES = frozenset({"NSE_EQ", "NSE_INDEX"})


@dataclass(frozen=True, slots=True)
class ResolvedInstrument:
    """Resolved instrument metadata needed for historical ingestion."""

    symbol: str
    instrument_key: str
    name: str | None
    exchange: str
    trading_symbol: str | None = None
    segment: str | None = None
    instrument_type: str | None = None


class InstrumentResolver:
    """Resolve requested symbols from the local instruments table."""

    def __init__(self, engine: object, instrument_table: str = "instruments") -> None:
        self.engine = engine
        self.instrument_table = _validate_identifier(instrument_table)

    def resolve_symbols(
        self,
        symbols: Iterable[str],
        exchange: str = "NSE_EQ",
    ) -> tuple[list[ResolvedInstrument], list[str]]:
        """Resolve symbols for a supported NSE exchange namespace."""

        if exchange not in SUPPORTED_EXCHANGES:
            raise ValueError(
                f"unsupported exchange: {exchange}; expected NSE_EQ or NSE_INDEX"
            )

        requested = _dedupe_symbols(symbols)
        if not requested:
            return [], []

        instrument_prefix = f"{exchange}|%"
        
        query = text(
            f"""
            SELECT
                symbol,
                instrument_key,
                name,
                exchange,
                trading_symbol,
                segment,
                instrument_type
            FROM {self.instrument_table}
            WHERE instrument_key LIKE :instrument_prefix
                AND (
                    UPPER(symbol) = ANY(:symbols)
                    OR UPPER(trading_symbol) = ANY(:symbols)
                )
            ORDER BY symbol ASC, trading_symbol ASC, instrument_key ASC
            """
        )

        with self.engine.connect() as conn:
            rows = conn.execute(
                query,
                {"instrument_prefix": instrument_prefix, "symbols": requested},
            ).mappings().all()

        by_symbol: dict[str, ResolvedInstrument] = {}
        for row in rows:
            if not str(row.get("instrument_key", "")).startswith(f"{exchange}|"):
                continue
            candidates = {
                _normalize_symbol(row.get("symbol")),
                _normalize_symbol(row.get("trading_symbol")),
            }
            matched_symbol = next(
                (symbol for symbol in requested if symbol in candidates),
                None,
            )
            if matched_symbol is None or matched_symbol in by_symbol:
                continue
            by_symbol[matched_symbol] = ResolvedInstrument(
                symbol=matched_symbol,
                instrument_key=row["instrument_key"],
                name=row.get("name"),
                exchange=row["exchange"],
                trading_symbol=row.get("trading_symbol"),
                segment=row.get("segment"),
                instrument_type=row.get("instrument_type"),
            )

        unresolved = [symbol for symbol in requested if symbol not in by_symbol]
        return [by_symbol[symbol] for symbol in requested if symbol in by_symbol], unresolved


def normalize_symbols(symbols: Iterable[str]) -> list[str]:
    """Trim, uppercase, and de-duplicate symbols while preserving order."""

    return _dedupe_symbols(symbols)


def _dedupe_symbols(symbols: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for symbol in symbols:
        clean = _normalize_symbol(symbol)
        if clean and clean not in seen:
            seen.add(clean)
            normalized.append(clean)
    return normalized


def _normalize_symbol(symbol: object) -> str:
    if symbol is None:
        return ""
    return str(symbol).strip().upper()


def _validate_identifier(identifier: str) -> str:
    if not identifier.replace("_", "").isalnum():
        raise ValueError(f"invalid SQL identifier: {identifier}")
    return identifier
