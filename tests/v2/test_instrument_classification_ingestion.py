"""Tests for static-current instrument classification ingestion."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

from veridian_quant.v2.data.instrument_classification_ingestion import (
    InstrumentClassificationIngestionRunner,
    InstrumentClassificationStorage,
    load_classification_file,
    load_research_symbols,
    parse_classification_row,
    parse_index_membership,
    resolve_market_cap_bucket,
)
from veridian_quant.v2.data.market_context_models import (
    ClassificationMode,
    MarketCapBucket,
)


def test_valid_classification_row_parses_into_instrument_classification() -> None:
    record = parse_classification_row(
        {
            "symbol": "reliance",
            "sector": "Energy",
            "industry": "Oil & Gas",
            "basic_industry": "Integrated Oil & Gas",
            "market_cap_bucket": "large_cap",
            "index_membership": "nifty 50;NIFTY 500",
            "company_name": "Reliance Industries Limited",
            "isin": "INE002A01018",
        },
        effective_from=date(2026, 1, 1),
        source="NSE_STATIC_FILE",
    )

    classification = record.classification
    assert classification.symbol == "RELIANCE"
    assert classification.sector == "Energy"
    assert classification.basic_industry == "Integrated Oil & Gas"
    assert classification.market_cap_bucket == MarketCapBucket.LARGE_CAP
    assert classification.index_membership == ("NIFTY_50", "NIFTY_500")
    assert classification.classification_mode == ClassificationMode.STATIC_CURRENT
    assert classification.isin == "INE002A01018"


def test_missing_symbol_is_rejected() -> None:
    with pytest.raises(ValueError, match="symbol must be non-empty"):
        parse_classification_row(
            {"sector": "Energy", "market_cap_bucket": "large_cap"},
            effective_from=date(2026, 1, 1),
            source="TEST",
        )


def test_missing_sector_becomes_explicit_unknown() -> None:
    record = parse_classification_row(
        {"symbol": "ABC", "market_cap_bucket": "unknown"},
        effective_from=date(2026, 1, 1),
        source="TEST",
    )

    assert record.classification.sector == "UNKNOWN"


def test_invalid_market_cap_bucket_is_rejected() -> None:
    with pytest.raises(ValueError, match="market_cap_bucket must be one of"):
        parse_classification_row(
            {"symbol": "ABC", "sector": "Energy", "market_cap_bucket": "mega_cap"},
            effective_from=date(2026, 1, 1),
            source="TEST",
        )


def test_static_current_classification_mode_is_enforced() -> None:
    with pytest.raises(ValueError, match="classification_mode=static_current"):
        parse_classification_row(
            {"symbol": "ABC", "sector": "Energy"},
            effective_from=date(2026, 1, 1),
            source="TEST",
            classification_mode="point_in_time",
        )


def test_effective_to_before_effective_from_is_rejected() -> None:
    with pytest.raises(ValueError, match="effective_to must be greater than or equal"):
        parse_classification_row(
            {
                "symbol": "ABC",
                "sector": "Energy",
                "effective_to": "2025-12-31",
            },
            effective_from=date(2026, 1, 1),
            source="TEST",
        )


def test_index_membership_normalization_works() -> None:
    assert parse_index_membership("nifty 50, NIFTY-MIDCAP 150|Nifty Smallcap 250") == (
        "NIFTY_50",
        "NIFTY_MIDCAP_150",
        "NIFTY_SMALLCAP_250",
    )


def test_market_cap_bucket_derives_from_clear_index_membership() -> None:
    bucket, warnings = resolve_market_cap_bucket(None, ("NIFTY_MIDCAP_150",), symbol="ABC")

    assert bucket == MarketCapBucket.MID_CAP
    assert warnings == []


def test_conflicting_cap_membership_warns_and_uses_unknown() -> None:
    bucket, warnings = resolve_market_cap_bucket(
        None,
        ("NIFTY_50", "NIFTY_SMALLCAP_250"),
        symbol="ABC",
    )

    assert bucket == MarketCapBucket.UNKNOWN
    assert "conflicting or unclear cap membership" in warnings[0]


def test_loader_detects_research_symbols_without_classification(tmp_path: Path) -> None:
    symbols_file = _write_csv(
        tmp_path / "symbols.csv",
        [
            {"symbol": "AAA", "instrument_key": "NSE_EQ|INEAAA", "name": "AAA Limited"},
            {"symbol": "BBB", "instrument_key": "NSE_EQ|INEBBB", "name": "BBB Limited"},
        ],
    )
    classification_file = _write_csv(
        tmp_path / "classifications.csv",
        [{"symbol": "AAA", "sector": "IT", "market_cap_bucket": "small_cap"}],
    )
    summary = InstrumentClassificationIngestionRunner(
        engine=object(),
        storage=ExplodingStorage(),
    ).run(
        classification_file=classification_file,
        symbols_file=symbols_file,
        effective_from=date(2026, 1, 1),
        source="TEST",
        dry_run=True,
    )

    assert summary.symbols_classified == 1
    assert summary.symbols_missing_classification == 1
    assert summary.missing_symbols == ["BBB"]


def test_dry_run_does_not_write_db(tmp_path: Path) -> None:
    symbols_file = _write_csv(tmp_path / "symbols.csv", [{"symbol": "AAA"}])
    classification_file = _write_csv(
        tmp_path / "classifications.csv",
        [{"symbol": "AAA", "sector": "IT", "market_cap_bucket": "small_cap"}],
    )

    summary = InstrumentClassificationIngestionRunner(
        engine=object(),
        storage=ExplodingStorage(),
    ).run(
        classification_file=classification_file,
        symbols_file=symbols_file,
        effective_from=date(2026, 1, 1),
        source="TEST",
        dry_run=True,
    )

    assert summary.rows_inserted == 0


def test_upsert_idempotency_replaces_existing_row(tmp_path: Path) -> None:
    engine = create_engine("sqlite:///:memory:")
    storage = InstrumentClassificationStorage(engine)
    symbols_file = _write_csv(tmp_path / "symbols.csv", [{"symbol": "AAA"}])
    classification_file = _write_csv(
        tmp_path / "classifications.csv",
        [{"symbol": "AAA", "sector": "IT", "market_cap_bucket": "small_cap"}],
    )
    runner = InstrumentClassificationIngestionRunner(engine=engine, storage=storage)

    first = runner.run(
        classification_file=classification_file,
        symbols_file=symbols_file,
        effective_from=date(2026, 1, 1),
        source="TEST",
        dry_run=False,
    )
    second = runner.run(
        classification_file=classification_file,
        symbols_file=symbols_file,
        effective_from=date(2026, 1, 1),
        source="TEST",
        dry_run=False,
    )

    stored = pd.read_sql(text("SELECT * FROM instrument_classifications"), engine)
    assert first.rows_inserted == 1
    assert second.rows_inserted == 1
    assert len(stored) == 1
    assert stored.iloc[0]["classification_mode"] == "static_current"


def test_file_loader_rejects_invalid_rows_without_network(tmp_path: Path) -> None:
    classification_file = _write_csv(
        tmp_path / "classifications.csv",
        [
            {"symbol": "AAA", "sector": "IT", "market_cap_bucket": "small_cap"},
            {"symbol": "", "sector": "Energy", "market_cap_bucket": "large_cap"},
        ],
    )

    result = load_classification_file(
        classification_file,
        effective_from=date(2026, 1, 1),
        source="TEST",
        classification_mode="static_current",
    )

    assert len(result.records) == 1
    assert len(result.invalid_rows) == 1


def test_research_symbols_load_instrument_metadata(tmp_path: Path) -> None:
    symbols_file = _write_csv(
        tmp_path / "symbols.csv",
        [{"symbol": "AAA", "instrument_key": "NSE_EQ|INEAAA", "name": "AAA Limited"}],
    )

    symbols = load_research_symbols(symbols_file)

    assert symbols["AAA"].instrument_key == "NSE_EQ|INEAAA"
    assert symbols["AAA"].company_name == "AAA Limited"


def _write_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    columns = sorted({key for row in rows for key in row})
    pd.DataFrame(rows, columns=columns).to_csv(path, index=False)
    return path


class ExplodingStorage:
    def upsert(self, *args, **kwargs):
        raise AssertionError("dry-run must not write")
