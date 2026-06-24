"""Tests for the market index registry."""

import pytest

from veridian_quant.v2.data.market_context_models import IndexType
from veridian_quant.v2.data.market_index_registry import (
    get_market_index,
    list_market_indices,
    parse_index_symbols,
)


def test_registry_contains_expected_broad_cap_and_sector_indices() -> None:
    definitions = {definition.index_symbol: definition for definition in list_market_indices()}

    expected = {
        "NIFTY_50",
        "NIFTY_500",
        "NIFTY_BANK",
        "NIFTY_FIN_SERVICE",
        "NIFTY_MIDCAP_150",
        "NIFTY_SMALLCAP_250",
        "NIFTY_IT",
        "NIFTY_PHARMA",
        "NIFTY_AUTO",
        "NIFTY_FMCG",
        "NIFTY_METAL",
        "NIFTY_ENERGY",
        "NIFTY_REALTY",
    }

    assert set(definitions) == expected
    assert definitions["NIFTY_50"].index_type == IndexType.BROAD_MARKET
    assert definitions["NIFTY_MIDCAP_150"].index_type == IndexType.CAP_SEGMENT
    assert definitions["NIFTY_BANK"].index_type == IndexType.SECTOR
    assert all(definition.source == "UPSTOX" for definition in definitions.values())


def test_get_market_index_rejects_unknown_symbol() -> None:
    with pytest.raises(ValueError, match="unknown market index symbol"):
        get_market_index("NIFTY_UNKNOWN")


def test_parse_index_symbols_supports_all() -> None:
    assert parse_index_symbols("ALL")[0] == "NIFTY_50"
    assert len(parse_index_symbols("ALL")) == len(list_market_indices())


def test_parse_index_symbols_supports_comma_list_and_dedupes() -> None:
    assert parse_index_symbols("nifty 50,NIFTY_BANK,nifty-50") == [
        "NIFTY_50",
        "NIFTY_BANK",
    ]
