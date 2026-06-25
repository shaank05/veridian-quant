"""Conservative sector-to-index proxy mapping for Phase 33 context features."""

from __future__ import annotations

from dataclasses import dataclass
import re


DEFAULT_SECTOR_FALLBACK_INDEX = "NIFTY_500"
UNKNOWN_SECTOR_VALUES = {"", "UNKNOWN", "NA", "N/A", "NULL", "NONE"}


@dataclass(frozen=True, slots=True)
class SectorProxyResolution:
    """Resolved sector proxy metadata for audit-friendly feature columns."""

    sector: str
    sector_proxy: str | None
    sector_proxy_is_fallback: bool
    sector_proxy_unmapped: bool


SECTOR_PROXY_MAPPING: dict[str, str] = {
    "auto ancillary": "NIFTY_AUTO",
    "auto components": "NIFTY_AUTO",
    "automobile": "NIFTY_AUTO",
    "automobiles": "NIFTY_AUTO",
    "bank": "NIFTY_BANK",
    "banking": "NIFTY_BANK",
    "banks": "NIFTY_BANK",
    "bpo ites": "NIFTY_IT",
    "breweries": "NIFTY_FMCG",
    "broking": "NIFTY_FIN_SERVICE",
    "construction": "NIFTY_REALTY",
    "construction real estate": "NIFTY_REALTY",
    "consumer food": "NIFTY_FMCG",
    "consumer goods": "NIFTY_FMCG",
    "financial services": "NIFTY_FIN_SERVICE",
    "fmcg": "NIFTY_FMCG",
    "food products": "NIFTY_FMCG",
    "gases and fuels": "NIFTY_ENERGY",
    "household products": "NIFTY_FMCG",
    "housing finance": "NIFTY_FIN_SERVICE",
    "information technology": "NIFTY_IT",
    "insurance": "NIFTY_FIN_SERVICE",
    "it software": "NIFTY_IT",
    "metal": "NIFTY_METAL",
    "metals": "NIFTY_METAL",
    "minerals": "NIFTY_METAL",
    "mining": "NIFTY_METAL",
    "nbfc": "NIFTY_FIN_SERVICE",
    "oil and gas": "NIFTY_ENERGY",
    "personal care": "NIFTY_FMCG",
    "pharma": "NIFTY_PHARMA",
    "pharmaceutical": "NIFTY_PHARMA",
    "pharmaceuticals": "NIFTY_PHARMA",
    "power": "NIFTY_ENERGY",
    "ratings": "NIFTY_FIN_SERVICE",
    "real estate": "NIFTY_REALTY",
    "realty": "NIFTY_REALTY",
    "refineries": "NIFTY_ENERGY",
    "software": "NIFTY_IT",
    "steel and iron products": "NIFTY_METAL",
    "stock broking": "NIFTY_FIN_SERVICE",
    "stockbroking": "NIFTY_FIN_SERVICE",
    "tobacco": "NIFTY_FMCG",
    "tyres and allied": "NIFTY_AUTO",
}

EXPLICITLY_UNMAPPED_SECTORS = {
    "electric equipment",
    "healthcare services",
    "it hardware",
    "investment",
    "lubricants",
    "sugar",
}


def load_sector_proxy_mapping() -> dict[str, str]:
    """Return the explicit normalized-label-to-index sector proxy mapping."""

    return dict(SECTOR_PROXY_MAPPING)


def resolve_sector_proxy(
    sector: object,
    *,
    fallback_to_nifty500: bool = False,
) -> SectorProxyResolution:
    """Resolve a static sector label to a conservative index proxy.

    Unknown or unmapped sectors return ``None`` unless ``fallback_to_nifty500``
    is enabled. Fallback results are explicitly flagged.
    """

    sector_text = _clean_sector(sector)
    if sector_text.upper() in UNKNOWN_SECTOR_VALUES:
        return _unmapped_resolution(sector_text, fallback_to_nifty500)

    normalized = _normalize_sector_for_matching(sector_text)
    if normalized in EXPLICITLY_UNMAPPED_SECTORS:
        return _unmapped_resolution(sector_text, fallback_to_nifty500)

    index_symbol = SECTOR_PROXY_MAPPING.get(normalized)
    if index_symbol is not None:
        return SectorProxyResolution(
            sector=sector_text,
            sector_proxy=index_symbol,
            sector_proxy_is_fallback=False,
            sector_proxy_unmapped=False,
        )
    return _unmapped_resolution(sector_text, fallback_to_nifty500)


def _unmapped_resolution(
    sector_text: str,
    fallback_to_nifty500: bool,
) -> SectorProxyResolution:
    return SectorProxyResolution(
        sector=sector_text,
        sector_proxy=DEFAULT_SECTOR_FALLBACK_INDEX if fallback_to_nifty500 else None,
        sector_proxy_is_fallback=fallback_to_nifty500,
        sector_proxy_unmapped=True,
    )


def _clean_sector(value: object) -> str:
    if value is None:
        return "UNKNOWN"
    text = str(value).strip()
    return text or "UNKNOWN"


def _normalize_sector_for_matching(value: str) -> str:
    lowered = value.lower().replace("&", " and ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", lowered).split())
