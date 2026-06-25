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


SECTOR_PROXY_MAPPING: tuple[tuple[tuple[str, ...], str], ...] = (
    (("bank", "banks", "banking"), "NIFTY_BANK"),
    (
        (
            "financial services",
            "finance",
            "financ",
            "nbfc",
            "housing finance",
            "stockbroking",
            "broking",
            "insurance",
        ),
        "NIFTY_FIN_SERVICE",
    ),
    (("it", "information technology", "software", "computer", "technology"), "NIFTY_IT"),
    (("pharma", "pharmaceutical", "pharmaceuticals", "healthcare", "health care"), "NIFTY_PHARMA"),
    (("auto", "automobile", "automobiles", "auto ancillaries", "auto components"), "NIFTY_AUTO"),
    (("fmcg", "consumer goods", "personal care", "food products"), "NIFTY_FMCG"),
    (("metal", "metals", "mining", "steel", "iron", "aluminium", "aluminum"), "NIFTY_METAL"),
    (("energy", "oil", "gas", "oil & gas", "power", "electric", "petroleum"), "NIFTY_ENERGY"),
    (("realty", "real estate", "construction real estate"), "NIFTY_REALTY"),
)


def load_sector_proxy_mapping() -> dict[str, str]:
    """Return the explicit phrase-to-index sector proxy mapping."""

    return {
        phrase: index_symbol
        for phrases, index_symbol in SECTOR_PROXY_MAPPING
        for phrase in phrases
    }


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
    for phrases, index_symbol in SECTOR_PROXY_MAPPING:
        if any(_phrase_matches(normalized, phrase) for phrase in phrases):
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


def _phrase_matches(normalized_sector: str, phrase: str) -> bool:
    normalized_phrase = _normalize_sector_for_matching(phrase)
    return bool(
        re.search(
            rf"(^|\s){re.escape(normalized_phrase)}($|\s)",
            normalized_sector,
        )
    )
