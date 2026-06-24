"""Tests for canonical market index daily readers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from veridian_quant.v2.data.market_index_reader import (
    SQLAlchemyMarketIndexDailyReader,
    audit_market_index_daily_bars,
    canonicalize_market_index_rows,
)


def test_one_raw_row_per_date_returns_one_canonical_bar() -> None:
    result = canonicalize_market_index_rows(
        [
            _row("2026-01-01T00:00:00Z", close=105),
            _row("2026-01-02T00:00:00Z", close=106),
        ],
        index_symbol="NIFTY_50",
        instrument_key="NSE_INDEX|Nifty 50",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
    )

    assert result.raw_row_count == 2
    assert result.canonical_row_count == 2
    assert [bar.date for bar in result.bars] == [date(2026, 1, 1), date(2026, 1, 2)]
    assert result.warnings == ()


def test_duplicate_timestamp_conventions_for_same_session_date_are_deduped() -> None:
    result = canonicalize_market_index_rows(
        [
            _row("2026-01-01T00:00:00Z", close=105),
            _row("2026-01-01T18:30:00Z", close=105),
        ],
        index_symbol="NIFTY_50",
        instrument_key="NSE_INDEX|Nifty 50",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 1),
    )

    assert result.canonical_row_count == 1
    assert result.duplicate_session_date_count == 1
    assert result.conflict_count == 0
    assert result.warnings[0].kept_timestamp == "2026-01-01T18:30:00+00:00"


def test_exact_duplicate_session_date_ohlc_does_not_create_two_output_rows() -> None:
    result = canonicalize_market_index_rows(
        [
            _row("2026-01-01T00:00:00Z", close=105),
            _row("2026-01-01T00:00:00Z", close=105),
        ],
        index_symbol="NIFTY_50",
        instrument_key="NSE_INDEX|Nifty 50",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 1),
    )

    assert result.canonical_row_count == 1
    assert result.duplicate_session_date_count == 1
    assert result.conflict_count == 0


def test_conflicting_duplicate_session_date_ohlc_is_reported() -> None:
    result = canonicalize_market_index_rows(
        [
            _row("2026-01-01T00:00:00Z", close=105),
            _row("2026-01-01T18:30:00Z", close=106),
        ],
        index_symbol="NIFTY_50",
        instrument_key="NSE_INDEX|Nifty 50",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 1),
    )

    assert result.canonical_row_count == 1
    assert result.conflict_count == 1
    assert result.warnings[0].has_conflict is True
    assert result.warnings[0].examples[0]["close"] == "105"


def test_date_range_filtering_uses_session_date() -> None:
    result = canonicalize_market_index_rows(
        [
            _row("2025-12-31T18:30:00Z", close=104),
            _row("2026-01-01T00:00:00Z", close=105),
            _row("2026-01-02T00:00:00Z", close=106),
        ],
        index_symbol="NIFTY_50",
        instrument_key="NSE_INDEX|Nifty 50",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 1),
    )

    assert result.raw_row_count == 1
    assert [bar.date for bar in result.bars] == [date(2026, 1, 1)]


def test_sqlalchemy_reader_reads_without_mutating_db(tmp_path: Path) -> None:
    engine = _engine_with_index_data()
    before = _row_count(engine)

    result = SQLAlchemyMarketIndexDailyReader(engine).load(
        index_symbol="NIFTY_50",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
    )

    assert result.canonical_row_count == 2
    assert _row_count(engine) == before


def test_nifty_auto_extra_duplicate_session_dates_are_detected_by_audit() -> None:
    report = audit_market_index_daily_bars(
        _engine_with_index_data(),
        index_symbols=["NIFTY_50", "NIFTY_500", "NIFTY_AUTO"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
    )
    payload = report.to_dict()
    auto_summary = payload["nifty_auto"]
    auto_row = _audit_row(payload, "NIFTY_AUTO")

    assert auto_row["raw_rows"] == 4
    assert auto_row["canonical_rows"] == 3
    assert auto_summary["duplicate_session_dates"] == 1
    assert auto_summary["true_extra_dates_vs_peer_union"] == 1
    assert auto_summary["true_extra_weekday_counts"] == {"Saturday": 1}
    assert auto_summary["true_extra_date_examples"] == ["2026-01-03"]


def test_audit_accepts_all_index_selection() -> None:
    engine = _engine_with_all_registry_indices()

    report = audit_market_index_daily_bars(
        engine,
        index_symbols=["ALL"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 1),
    )

    assert len(report.indices) == 13


def _audit_row(payload: dict[str, object], symbol: str) -> dict[str, object]:
    rows = [row for row in payload["indices"] if row["index_symbol"] == symbol]
    assert len(rows) == 1
    return rows[0]


def _row(timestamp: str, close: float, instrument_key: str = "NSE_INDEX|Nifty 50"):
    return {
        "timestamp": timestamp,
        "instrument_key": instrument_key,
        "open": close - 1,
        "high": close + 1,
        "low": close - 2,
        "close": close,
        "volume": 0,
        "interval": "day",
    }


def _engine_with_index_data():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        _create_tables(conn)
        conn.execute(
            text(
                """
                INSERT INTO instruments (
                    instrument_key,
                    symbol,
                    trading_symbol,
                    name,
                    exchange,
                    segment,
                    instrument_type
                )
                VALUES (
                    :instrument_key,
                    :symbol,
                    :trading_symbol,
                    :name,
                    :exchange,
                    :segment,
                    :instrument_type
                )
                """
            ),
            [
                _instrument("NSE_INDEX|Nifty 50", "NIFTY 50"),
                _instrument("NSE_INDEX|Nifty 500", "NIFTY 500"),
                _instrument("NSE_INDEX|Nifty Auto", "NIFTY AUTO"),
            ],
        )
        rows = [
            _row("2026-01-01T00:00:00Z", 105),
            _row("2026-01-01T18:30:00Z", 105),
            _row("2026-01-02T00:00:00Z", 106),
            _row("2026-01-01T00:00:00Z", 505, "NSE_INDEX|Nifty 500"),
            _row("2026-01-02T00:00:00Z", 506, "NSE_INDEX|Nifty 500"),
            _row("2026-01-01T00:00:00Z", 205, "NSE_INDEX|Nifty Auto"),
            _row("2026-01-01T18:30:00Z", 205, "NSE_INDEX|Nifty Auto"),
            _row("2026-01-02T00:00:00Z", 206, "NSE_INDEX|Nifty Auto"),
            _row("2026-01-03T00:00:00Z", 207, "NSE_INDEX|Nifty Auto"),
        ]
        _insert_prices(conn, rows)
    return engine


def _engine_with_all_registry_indices():
    from veridian_quant.v2.data.market_index_registry import list_market_indices

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        _create_tables(conn)
        instruments = [
            _instrument(f"NSE_INDEX|{definition.index_name}", definition.index_name)
            for definition in list_market_indices()
        ]
        conn.execute(
            text(
                """
                INSERT INTO instruments (
                    instrument_key,
                    symbol,
                    trading_symbol,
                    name,
                    exchange,
                    segment,
                    instrument_type
                )
                VALUES (
                    :instrument_key,
                    :symbol,
                    :trading_symbol,
                    :name,
                    :exchange,
                    :segment,
                    :instrument_type
                )
                """
            ),
            instruments,
        )
        _insert_prices(
            conn,
            [
                _row(
                    "2026-01-01T00:00:00Z",
                    100,
                    instrument_key=instrument["instrument_key"],
                )
                for instrument in instruments
            ],
        )
    return engine


def _create_tables(conn) -> None:
    conn.execute(
        text(
            """
            CREATE TABLE instruments (
                instrument_key TEXT PRIMARY KEY,
                symbol TEXT,
                trading_symbol TEXT,
                name TEXT,
                exchange TEXT,
                segment TEXT,
                instrument_type TEXT
            )
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE prices_ohlc (
                timestamp TEXT,
                instrument_key TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                open_interest REAL,
                interval TEXT
            )
            """
        )
    )


def _insert_prices(conn, rows) -> None:
    conn.execute(
        text(
            """
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
                NULL,
                :interval
            )
            """
        ),
        rows,
    )


def _instrument(instrument_key: str, name: str) -> dict[str, str]:
    return {
        "instrument_key": instrument_key,
        "symbol": name,
        "trading_symbol": name,
        "name": name,
        "exchange": "NSE_INDEX",
        "segment": "NSE_INDEX",
        "instrument_type": "INDEX",
    }


def _row_count(engine) -> int:
    return int(pd.read_sql(text("SELECT COUNT(*) AS count FROM prices_ohlc"), engine)["count"].iloc[0])
