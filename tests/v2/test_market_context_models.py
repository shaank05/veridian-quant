"""Tests for benchmark, sector, and market-cap context contracts."""

from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal

import pytest

from veridian_quant.v2.data.market_context_models import (
    ClassificationMode,
    IndexConstituent,
    IndexType,
    InstrumentClassification,
    MarketCapBucket,
    MarketIndex,
    MarketIndexBar,
    classification_is_active_on_date,
    constituent_is_active_on_date,
    is_point_in_time_classification,
    normalize_index_symbol,
    normalize_market_cap_bucket,
)


def test_market_index_accepts_valid_broad_market_index() -> None:
    index = MarketIndex(
        index_symbol="nifty 50",
        index_name="NIFTY 50",
        index_type=IndexType.BROAD_MARKET,
        source="NSE",
    )

    assert index.index_symbol == "NIFTY_50"
    assert index.index_type == IndexType.BROAD_MARKET
    assert index.is_active is True


def test_market_index_accepts_valid_sector_index() -> None:
    index = MarketIndex(
        index_symbol="NIFTY_BANK",
        index_name="NIFTY Bank",
        index_type="sector",
        source="NSE",
        exchange="NSE_INDEX",
    )

    assert index.index_type == IndexType.SECTOR
    assert index.exchange == "NSE_INDEX"


@pytest.mark.parametrize(
    ("field", "kwargs"),
    [
        ("index_symbol", {"index_symbol": ""}),
        ("index_name", {"index_name": ""}),
        ("source", {"source": ""}),
    ],
)
def test_market_index_rejects_empty_required_fields(field: str, kwargs: dict[str, str]) -> None:
    defaults = {
        "index_symbol": "NIFTY_50",
        "index_name": "NIFTY 50",
        "index_type": "broad_market",
        "source": "NSE",
    }
    defaults.update(kwargs)

    with pytest.raises(ValueError, match=f"{field} must be non-empty"):
        MarketIndex(**defaults)


def test_market_index_rejects_invalid_index_type() -> None:
    with pytest.raises(ValueError, match="index_type must be one of"):
        MarketIndex(
            index_symbol="NIFTY_50",
            index_name="NIFTY 50",
            index_type="macro",
            source="NSE",
        )


def test_market_index_bar_accepts_valid_ohlc_bar() -> None:
    bar = MarketIndexBar(
        index_symbol="nifty-50",
        date=date(2026, 1, 2),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("95"),
        close=Decimal("105"),
        volume=0,
        source="NSE",
    )

    assert bar.index_symbol == "NIFTY_50"
    assert bar.high == Decimal("110")


@pytest.mark.parametrize("field", ["open", "high", "low", "close"])
@pytest.mark.parametrize("value", [Decimal("-1"), Decimal("0")])
def test_market_index_bar_rejects_negative_or_zero_ohlc(field: str, value: Decimal) -> None:
    kwargs = _valid_index_bar_kwargs()
    kwargs[field] = value

    with pytest.raises(ValueError, match=f"{field} must be positive"):
        MarketIndexBar(**kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"high": Decimal("99")},
        {"low": Decimal("106")},
    ],
)
def test_market_index_bar_rejects_inconsistent_high_low(kwargs: dict[str, Decimal]) -> None:
    defaults = _valid_index_bar_kwargs()
    defaults.update(kwargs)

    with pytest.raises(ValueError, match="high must|low must"):
        MarketIndexBar(**defaults)


def test_market_index_bar_rejects_negative_volume() -> None:
    kwargs = _valid_index_bar_kwargs()
    kwargs["volume"] = -1

    with pytest.raises(ValueError, match="volume must be greater than or equal to 0"):
        MarketIndexBar(**kwargs)


def test_market_index_bar_normalizes_date_like_values_to_date() -> None:
    from_datetime = MarketIndexBar(**(_valid_index_bar_kwargs(date=datetime(2026, 1, 2, 15, 30))))
    from_string = MarketIndexBar(**(_valid_index_bar_kwargs(date="2026-01-02")))

    assert from_datetime.date == date(2026, 1, 2)
    assert from_string.date == date(2026, 1, 2)


def test_instrument_classification_accepts_valid_static_classification() -> None:
    classification = InstrumentClassification(
        symbol="reliance",
        sector="Energy",
        industry="Oil & Gas",
        market_cap_bucket="large_cap",
        index_membership=["nifty 50", "NIFTY_500"],
        effective_from=date(2026, 1, 1),
        source="MANUAL",
        classification_mode="static_current",
    )

    assert classification.symbol == "RELIANCE"
    assert classification.market_cap_bucket == MarketCapBucket.LARGE_CAP
    assert classification.index_membership == ("NIFTY_50", "NIFTY_500")
    assert classification.classification_mode == ClassificationMode.STATIC_CURRENT


def test_instrument_classification_accepts_valid_point_in_time_classification() -> None:
    classification = InstrumentClassification(
        symbol="TCS",
        sector="IT",
        industry="Software",
        market_cap_bucket=MarketCapBucket.LARGE_CAP,
        effective_from="2026-01-01",
        effective_to="2026-12-31",
        source="NSE",
        classification_mode=ClassificationMode.POINT_IN_TIME,
    )

    assert is_point_in_time_classification(classification) is True


def test_instrument_classification_accepts_unknown_market_cap_bucket() -> None:
    classification = InstrumentClassification(
        symbol="ABC",
        sector="UNKNOWN",
        industry=None,
        market_cap_bucket="unknown",
        effective_from=date(2026, 1, 1),
        source="MANUAL",
    )

    assert classification.market_cap_bucket == MarketCapBucket.UNKNOWN


@pytest.mark.parametrize(
    ("field", "kwargs"),
    [
        ("symbol", {"symbol": ""}),
        ("source", {"source": ""}),
    ],
)
def test_instrument_classification_rejects_empty_symbol_or_source(
    field: str,
    kwargs: dict[str, str],
) -> None:
    defaults = _valid_classification_kwargs()
    defaults.update(kwargs)

    with pytest.raises(ValueError, match=f"{field} must be non-empty"):
        InstrumentClassification(**defaults)


def test_instrument_classification_rejects_invalid_market_cap_bucket() -> None:
    kwargs = _valid_classification_kwargs()
    kwargs["market_cap_bucket"] = "mega_cap"

    with pytest.raises(ValueError, match="market_cap_bucket must be one of"):
        InstrumentClassification(**kwargs)


def test_instrument_classification_rejects_effective_to_before_effective_from() -> None:
    kwargs = _valid_classification_kwargs()
    kwargs["effective_to"] = date(2025, 12, 31)

    with pytest.raises(ValueError, match="effective_to must be greater than or equal"):
        InstrumentClassification(**kwargs)


def test_classification_active_on_date_helper_handles_active_window() -> None:
    classification = InstrumentClassification(
        **_valid_classification_kwargs(effective_to=date(2026, 1, 31))
    )

    assert classification_is_active_on_date(classification, date(2025, 12, 31)) is False
    assert classification_is_active_on_date(classification, date(2026, 1, 1)) is True
    assert classification_is_active_on_date(classification, date(2026, 1, 31)) is True
    assert classification_is_active_on_date(classification, date(2026, 2, 1)) is False


def test_classification_mode_is_recorded_for_auditability() -> None:
    classification = InstrumentClassification(
        **_valid_classification_kwargs(classification_mode="static_current")
    )

    assert classification.classification_mode == ClassificationMode.STATIC_CURRENT
    assert is_point_in_time_classification(classification) is False


def test_index_constituent_accepts_valid_constituent() -> None:
    constituent = IndexConstituent(
        index_symbol="nifty 500",
        symbol="RELIANCE",
        effective_from=date(2026, 1, 1),
        source="NSE",
        weight=Decimal("8.5"),
    )

    assert constituent.index_symbol == "NIFTY_500"
    assert constituent.weight == Decimal("8.5")


def test_index_constituent_rejects_invalid_effective_range() -> None:
    with pytest.raises(ValueError, match="effective_to must be greater than or equal"):
        IndexConstituent(
            index_symbol="NIFTY_500",
            symbol="RELIANCE",
            effective_from=date(2026, 1, 2),
            effective_to=date(2026, 1, 1),
            source="NSE",
        )


def test_constituent_active_on_date_helper_handles_active_window() -> None:
    constituent = IndexConstituent(
        index_symbol="NIFTY_500",
        symbol="RELIANCE",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 1, 31),
        source="NSE",
    )

    assert constituent_is_active_on_date(constituent, date(2025, 12, 31)) is False
    assert constituent_is_active_on_date(constituent, date(2026, 1, 15)) is True
    assert constituent_is_active_on_date(constituent, date(2026, 2, 1)) is False


def test_index_constituent_rejects_negative_weight() -> None:
    with pytest.raises(ValueError, match="weight must be greater than or equal to 0"):
        IndexConstituent(
            index_symbol="NIFTY_500",
            symbol="RELIANCE",
            effective_from=date(2026, 1, 1),
            source="NSE",
            weight=Decimal("-0.1"),
        )


def test_market_context_models_are_asdict_serializable() -> None:
    classification = InstrumentClassification(**_valid_classification_kwargs())

    serialized = asdict(classification)

    assert serialized["symbol"] == "RELIANCE"
    assert serialized["market_cap_bucket"] == MarketCapBucket.LARGE_CAP


def test_market_context_models_have_deterministic_equality_and_repr() -> None:
    left = MarketIndex(
        index_symbol="NIFTY_50",
        index_name="NIFTY 50",
        index_type="broad_market",
        source="NSE",
    )
    right = MarketIndex(
        index_symbol="nifty 50",
        index_name="NIFTY 50",
        index_type=IndexType.BROAD_MARKET,
        source="NSE",
    )

    assert left == right
    assert repr(left) == repr(right)


def test_market_context_module_does_not_import_forbidden_runtime_modules() -> None:
    import sys
    import veridian_quant.v2.data.market_context_models  # noqa: F401

    forbidden = {
        "upstox_client",
        "veridian_quant.v2.backtesting.engine",
        "veridian_quant.v2.reporting.reports",
        "veridian_quant.v2.strategies.base",
    }

    assert forbidden.isdisjoint(sys.modules)


def test_normalizers_return_stable_contract_values() -> None:
    assert normalize_index_symbol(" nifty-bank ") == "NIFTY_BANK"
    assert normalize_market_cap_bucket("mid_cap") == MarketCapBucket.MID_CAP


def _valid_index_bar_kwargs(**overrides):
    kwargs = {
        "index_symbol": "NIFTY_50",
        "date": date(2026, 1, 1),
        "open": Decimal("100"),
        "high": Decimal("110"),
        "low": Decimal("95"),
        "close": Decimal("105"),
        "volume": 1000,
        "source": "NSE",
    }
    kwargs.update(overrides)
    return kwargs


def _valid_classification_kwargs(**overrides):
    kwargs = {
        "symbol": "RELIANCE",
        "sector": "Energy",
        "industry": "Oil & Gas",
        "market_cap_bucket": "large_cap",
        "effective_from": date(2026, 1, 1),
        "source": "MANUAL",
        "classification_mode": "manual",
    }
    kwargs.update(overrides)
    return kwargs
