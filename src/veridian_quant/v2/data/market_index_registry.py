"""Static registry for benchmark, sector, and cap-segment indices."""

from __future__ import annotations

from dataclasses import dataclass

from veridian_quant.v2.data.market_context_models import (
    IndexType,
    MarketIndex,
    normalize_index_symbol,
)


SOURCE_UPSTOX = "UPSTOX"
INDEX_EXCHANGE = "NSE_INDEX"


@dataclass(frozen=True, slots=True)
class MarketIndexDefinition:
    """Registry row for one supported market index."""

    index_symbol: str
    index_name: str
    index_type: IndexType
    aliases: tuple[str, ...]
    source: str = SOURCE_UPSTOX
    exchange: str = INDEX_EXCHANGE
    is_active: bool = True

    def to_market_index(self) -> MarketIndex:
        return MarketIndex(
            index_symbol=self.index_symbol,
            index_name=self.index_name,
            index_type=self.index_type,
            source=self.source,
            exchange=self.exchange,
            is_active=self.is_active,
        )


MARKET_INDEX_REGISTRY: tuple[MarketIndexDefinition, ...] = (
    MarketIndexDefinition(
        "NIFTY_50",
        "NIFTY 50",
        IndexType.BROAD_MARKET,
        ("NIFTY 50", "Nifty 50", "NIFTY50"),
    ),
    MarketIndexDefinition(
        "NIFTY_500",
        "NIFTY 500",
        IndexType.BROAD_MARKET,
        ("NIFTY 500", "Nifty 500", "NIFTY500"),
    ),
    MarketIndexDefinition(
        "NIFTY_BANK",
        "NIFTY Bank",
        IndexType.SECTOR,
        ("NIFTY BANK", "Nifty Bank", "BANKNIFTY"),
    ),
    MarketIndexDefinition(
        "NIFTY_FIN_SERVICE",
        "NIFTY Financial Services",
        IndexType.SECTOR,
        ("NIFTY FIN SERVICE", "NIFTY FINANCIAL SERVICES", "FINNIFTY"),
    ),
    MarketIndexDefinition(
        "NIFTY_MIDCAP_150",
        "NIFTY Midcap 150",
        IndexType.CAP_SEGMENT,
        ("NIFTY MIDCAP 150", "Nifty Midcap 150", "MIDCAP150"),
    ),
    MarketIndexDefinition(
        "NIFTY_SMALLCAP_250",
        "NIFTY Smallcap 250",
        IndexType.CAP_SEGMENT,
        (
            "NIFTY SMALLCAP 250",
            "Nifty Smallcap 250",
            "NIFTY SMLCAP 250",
            "SMALLCAP250",
            "SMLCAP250",
        ),
    ),
    MarketIndexDefinition("NIFTY_IT", "NIFTY IT", IndexType.SECTOR, ("NIFTY IT",)),
    MarketIndexDefinition(
        "NIFTY_PHARMA",
        "NIFTY Pharma",
        IndexType.SECTOR,
        ("NIFTY PHARMA", "Nifty Pharma"),
    ),
    MarketIndexDefinition(
        "NIFTY_AUTO",
        "NIFTY Auto",
        IndexType.SECTOR,
        ("NIFTY AUTO", "Nifty Auto"),
    ),
    MarketIndexDefinition(
        "NIFTY_FMCG",
        "NIFTY FMCG",
        IndexType.SECTOR,
        ("NIFTY FMCG", "Nifty FMCG"),
    ),
    MarketIndexDefinition(
        "NIFTY_METAL",
        "NIFTY Metal",
        IndexType.SECTOR,
        ("NIFTY METAL", "Nifty Metal"),
    ),
    MarketIndexDefinition(
        "NIFTY_ENERGY",
        "NIFTY Energy",
        IndexType.SECTOR,
        ("NIFTY ENERGY", "Nifty Energy"),
    ),
    MarketIndexDefinition(
        "NIFTY_REALTY",
        "NIFTY Realty",
        IndexType.SECTOR,
        ("NIFTY REALTY", "Nifty Realty"),
    ),
)


def list_market_indices() -> tuple[MarketIndexDefinition, ...]:
    """Return supported market index definitions in stable registry order."""

    return MARKET_INDEX_REGISTRY


def get_market_index(index_symbol: str) -> MarketIndexDefinition:
    """Return one supported index definition by internal symbol."""

    normalized = normalize_index_symbol(index_symbol)
    for definition in MARKET_INDEX_REGISTRY:
        if definition.index_symbol == normalized:
            return definition
    raise ValueError(f"unknown market index symbol: {index_symbol}")


def parse_index_symbols(indices_arg: str) -> list[str]:
    """Parse CLI index selection from ALL or a comma-separated symbol list."""

    if not indices_arg or not indices_arg.strip():
        raise ValueError("indices must be ALL or a comma-separated list")
    if indices_arg.strip().upper() == "ALL":
        return [definition.index_symbol for definition in MARKET_INDEX_REGISTRY]
    symbols: list[str] = []
    seen: set[str] = set()
    for part in indices_arg.split(","):
        symbol = normalize_index_symbol(part)
        get_market_index(symbol)
        if symbol not in seen:
            seen.add(symbol)
            symbols.append(symbol)
    return symbols
