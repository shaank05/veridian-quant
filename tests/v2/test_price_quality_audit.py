"""Tests for V2 price data quality audits."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from veridian_quant.v2.data.price_quality import audit_price_data


AUDIT_START = date(2026, 1, 1)
AUDIT_END = date(2026, 3, 31)


def test_audit_creates_all_required_csv_files(tmp_path: Path) -> None:
    paths = _run_audit(_engine_with_audit_data(), tmp_path)

    assert set(paths) == {
        "price_coverage",
        "bad_ohlc_rows",
        "stale_or_incomplete_symbols",
        "price_quality_summary",
    }
    assert all(path.exists() for path in paths.values())


def test_instrument_selection_uses_instrument_key_prefix_not_exchange_exact_value(
    tmp_path: Path,
) -> None:
    paths = _run_audit(_engine_with_audit_data(), tmp_path)

    coverage = pd.read_csv(paths["price_coverage"])

    assert "ELIG" in set(coverage["symbol"])
    assert set(coverage["instrument_key"]).issubset(
        {
            "NSE_EQ|ELIG",
            "NSE_EQ|NODATA",
            "NSE_EQ|SHORT",
            "NSE_EQ|STALE",
            "NSE_EQ|BAD",
            "NSE_EQ|ZERO",
        }
    )
    assert coverage.loc[coverage["symbol"] == "ELIG", "exchange"].iloc[0] == "NSE"


def test_no_data_instrument_is_rejected_with_no_data(tmp_path: Path) -> None:
    paths = _run_audit(_engine_with_audit_data(), tmp_path)

    row = _coverage_row(paths["price_coverage"], "NODATA")

    assert row["row_count"] == 0
    assert "NO_DATA" in row["rejection_reasons"]


def test_insufficient_history_instrument_is_rejected(tmp_path: Path) -> None:
    paths = _run_audit(_engine_with_audit_data(), tmp_path)

    row = _coverage_row(paths["price_coverage"], "SHORT")

    assert row["row_count"] == 10
    assert "INSUFFICIENT_HISTORY" in row["rejection_reasons"]


def test_stale_instrument_is_rejected(tmp_path: Path) -> None:
    paths = _run_audit(_engine_with_audit_data(), tmp_path)

    row = _coverage_row(paths["price_coverage"], "STALE")

    assert row["last_price_date"] == "2026-02-28"
    assert "STALE_DATA" in row["rejection_reasons"]


def test_bad_ohlc_rows_are_detected_and_exported(tmp_path: Path) -> None:
    paths = _run_audit(_engine_with_audit_data(), tmp_path)

    coverage_row = _coverage_row(paths["price_coverage"], "BAD")
    bad_rows = pd.read_csv(paths["bad_ohlc_rows"])
    bad_row = bad_rows.loc[bad_rows["symbol"] == "BAD"].iloc[0]

    assert coverage_row["bad_ohlc_rows"] == 1
    assert "BAD_OHLC" in coverage_row["rejection_reasons"]
    assert bad_row["instrument_key"] == "NSE_EQ|BAD"
    assert "HIGH_LT_CLOSE" in bad_row["reason"]


def test_zero_volume_percentage_is_calculated(tmp_path: Path) -> None:
    paths = _run_audit(_engine_with_audit_data(), tmp_path)

    row = _coverage_row(paths["price_coverage"], "ZERO")

    assert row["zero_volume_days"] == 9
    assert row["zero_volume_pct"] == 10.0
    assert "EXCESS_ZERO_VOLUME" in row["rejection_reasons"]


def test_average_volume_and_turnover_metrics_are_calculated(tmp_path: Path) -> None:
    paths = _run_audit(_engine_with_audit_data(), tmp_path)

    row = _coverage_row(paths["price_coverage"], "ELIG")

    assert row["avg_volume_20d"] == 179.5
    assert row["avg_turnover_20d"] == 16098.5
    assert row["avg_volume_60d"] == 159.5
    assert row["avg_turnover_60d"] == 11385.166667


def test_multiple_rejection_reasons_are_pipe_delimited(tmp_path: Path) -> None:
    paths = _run_audit(_engine_with_audit_data(), tmp_path)

    row = _coverage_row(paths["price_coverage"], "NODATA")

    assert "|" in row["rejection_reasons"]
    assert row["rejection_reasons"].startswith("NO_DATA|INSUFFICIENT_HISTORY")


def test_eligible_instrument_passes_all_checks(tmp_path: Path) -> None:
    paths = _run_audit(_engine_with_audit_data(), tmp_path)

    row = _coverage_row(paths["price_coverage"], "ELIG")

    assert bool(row["eligible_for_research"]) is True
    assert pd.isna(row["rejection_reasons"])


def test_summary_file_aggregates_counts_correctly(tmp_path: Path) -> None:
    paths = _run_audit(_engine_with_audit_data(), tmp_path)

    summary = pd.read_csv(paths["price_quality_summary"]).iloc[0]

    assert summary["instruments_checked"] == 6
    assert summary["eligible_instruments"] == 1
    assert summary["rejected_instruments"] == 5
    assert summary["instruments_with_no_data"] == 1
    assert summary["instruments_with_bad_ohlc"] == 1
    assert summary["instruments_with_zero_volume"] == 1


def _run_audit(engine: object, tmp_path: Path) -> dict[str, Path]:
    return audit_price_data(
        engine=engine,
        exchange="NSE_EQ",
        interval="day",
        start_date=AUDIT_START,
        end_date=AUDIT_END,
        output_dir=tmp_path,
        min_history_days=60,
        max_missing_day_pct=10.0,
        max_zero_volume_pct=5.0,
        min_avg_volume_60d=0,
        min_avg_turnover_60d=0,
    )


def _coverage_row(path: Path, symbol: str) -> pd.Series:
    coverage = pd.read_csv(path)
    row = coverage.loc[coverage["symbol"] == symbol]
    assert len(row) == 1
    return row.iloc[0]


def _engine_with_audit_data() -> object:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
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
                _instrument("NSE_EQ|ELIG", "ELIG", exchange="NSE"),
                _instrument("NSE_EQ|NODATA", "NODATA", exchange="NSE"),
                _instrument("NSE_EQ|SHORT", "SHORT", exchange="NSE"),
                _instrument("NSE_EQ|STALE", "STALE", exchange="NSE"),
                _instrument("NSE_EQ|BAD", "BAD", exchange="NSE"),
                _instrument("NSE_EQ|ZERO", "ZERO", exchange="NSE"),
                _instrument("BSE_EQ|ELIG", "BSEELIG", exchange="NSE_EQ"),
                _instrument("NSE_INDEX|NIFTY", "NIFTY", exchange="NSE"),
            ],
        )
        price_rows = []
        price_rows.extend(_price_rows("NSE_EQ|ELIG", AUDIT_START, 90))
        price_rows.extend(_price_rows("NSE_EQ|SHORT", AUDIT_START, 10))
        price_rows.extend(_price_rows("NSE_EQ|STALE", AUDIT_START, 59))
        price_rows.extend(_price_rows("NSE_EQ|BAD", AUDIT_START, 90, bad_index=10))
        price_rows.extend(_price_rows("NSE_EQ|ZERO", AUDIT_START, 90, zero_every=10))
        price_rows.extend(_price_rows("BSE_EQ|ELIG", AUDIT_START, 90))
        price_rows.extend(_price_rows("NSE_INDEX|NIFTY", AUDIT_START, 90))
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
                    :open_interest,
                    :interval
                )
                """
            ),
            price_rows,
        )
    return engine


def _instrument(instrument_key: str, symbol: str, exchange: str) -> dict[str, str]:
    return {
        "instrument_key": instrument_key,
        "symbol": symbol,
        "trading_symbol": symbol,
        "name": f"{symbol} Limited",
        "exchange": exchange,
        "segment": "NSE_EQ",
        "instrument_type": "EQ",
    }


def _price_rows(
    instrument_key: str,
    start: date,
    count: int,
    bad_index: int | None = None,
    zero_every: int | None = None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(count):
        timestamp = start + timedelta(days=index)
        close = 10.0 + index
        high = close + 1.0
        if bad_index is not None and index == bad_index:
            high = close - 1.0
        volume = 100.0 + index
        if zero_every is not None and index % zero_every == 0:
            volume = 0.0
        rows.append(
            {
                "timestamp": timestamp.isoformat(),
                "instrument_key": instrument_key,
                "open": close,
                "high": high,
                "low": close - 1.0,
                "close": close,
                "volume": volume,
                "open_interest": None,
                "interval": "day",
            }
        )
    return rows
