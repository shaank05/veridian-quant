"""Unit tests for v2 daily OHLCV data loaders."""

from datetime import date
from unittest.mock import patch

import pandas as pd

from veridian_quant.v2.data.loaders import (
    OHLCV_COLUMNS,
    SQLAlchemyDailyOHLCVLoader,
    normalize_ohlcv_dataframe,
)


def test_normalize_keeps_required_columns() -> None:
    normalized = normalize_ohlcv_dataframe(_raw_frame())

    assert list(normalized.columns) == list(OHLCV_COLUMNS)


def test_normalize_lowercases_columns() -> None:
    normalized = normalize_ohlcv_dataframe(_raw_frame())

    assert list(normalized.columns) == ["date", "open", "high", "low", "close", "volume"]


def test_normalize_sorts_dates() -> None:
    normalized = normalize_ohlcv_dataframe(_raw_frame())

    assert normalized["date"].tolist() == [
        pd.Timestamp("2026-01-01"),
        pd.Timestamp("2026-01-02"),
    ]


def test_normalize_drops_duplicate_dates_keeping_last() -> None:
    normalized = normalize_ohlcv_dataframe(_raw_frame())

    assert len(normalized) == 2
    assert normalized.loc[0, "open"] == 11


def test_normalize_does_not_mutate_input() -> None:
    df = _raw_frame()
    original = df.copy(deep=True)

    normalize_ohlcv_dataframe(df)

    pd.testing.assert_frame_equal(df, original)


def test_normalize_raises_value_error_on_missing_columns() -> None:
    df = _raw_frame().drop(columns=["Low"])

    try:
        normalize_ohlcv_dataframe(df)
    except ValueError as error:
        assert str(error) == "missing required columns: low"
    else:
        raise AssertionError("expected missing low column to raise ValueError")


def test_load_symbols_returns_mapping_for_requested_symbols() -> None:
    calls: list[str] = []

    def fake_read_sql(query, engine, params):
        calls.append(params["symbol"])
        if params["symbol"] == "EMPTY":
            return _empty_ohlcv_frame()
        return _raw_frame()

    loader = SQLAlchemyDailyOHLCVLoader(engine=object())

    with patch.object(pd, "read_sql", fake_read_sql):
        data_by_symbol = loader.load_symbols(
            ["RELIANCE", "EMPTY", "TCS"],
            date(2026, 1, 1),
            date(2026, 1, 31),
        )

    assert calls == ["RELIANCE", "EMPTY", "TCS"]
    assert set(data_by_symbol) == {"RELIANCE", "TCS"}
    assert all(list(data.columns) == list(OHLCV_COLUMNS) for data in data_by_symbol.values())


def test_load_symbol_passes_buffered_start_date_to_read_sql() -> None:
    captured_params = {}

    def fake_read_sql(query, engine, params):
        captured_params.update(params)
        return _raw_frame()

    loader = SQLAlchemyDailyOHLCVLoader(
        engine=object(),
        lookback_buffer_days=10,
    )

    with patch.object(pd, "read_sql", fake_read_sql):
        loader.load_symbol("RELIANCE", date(2026, 1, 31), date(2026, 2, 28))

    assert captured_params["symbol"] == "RELIANCE"
    assert captured_params["start_date"] == date(2026, 1, 21)
    assert captured_params["end_date"] == date(2026, 2, 28)


def test_load_all_available_symbols_returns_mapping_for_discovered_symbols() -> None:
    calls: list[str] = []
    discovery_params = {}

    def fake_read_sql(query, engine, params):
        if "symbol" in params:
            calls.append(params["symbol"])
            return _raw_frame()
        discovery_params.update(params)
        return pd.DataFrame({"symbol": ["RELIANCE", "TCS"]})

    loader = SQLAlchemyDailyOHLCVLoader(
        engine=object(),
        lookback_buffer_days=10,
    )

    with patch.object(pd, "read_sql", fake_read_sql):
        data_by_symbol = loader.load_all_available_symbols(
            date(2026, 1, 1),
            date(2026, 1, 31),
        )

    assert calls == ["RELIANCE", "TCS"]
    assert discovery_params == {
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 1, 31),
    }
    assert set(data_by_symbol) == {"RELIANCE", "TCS"}


def test_empty_symbol_data_is_skipped_consistently() -> None:
    def fake_read_sql(query, engine, params):
        return _empty_ohlcv_frame()

    loader = SQLAlchemyDailyOHLCVLoader(engine=object())

    with patch.object(pd, "read_sql", fake_read_sql):
        data_by_symbol = loader.load_symbols(
            ["EMPTY"],
            date(2026, 1, 1),
            date(2026, 1, 31),
        )

    assert data_by_symbol == {}


def _raw_frame() -> pd.DataFrame:
    """Build raw OHLCV data with uppercase columns and duplicate dates."""

    return pd.DataFrame(
        {
            "Date": ["2026-01-02", "2026-01-01", "2026-01-01"],
            "Open": [20, 10, 11],
            "High": [21, 11, 12],
            "Low": [19, 9, 10],
            "Close": [20, 10, 11],
            "Volume": [2000, 1000, 1100],
            "Ignored": ["a", "b", "c"],
        }
    )


def _empty_ohlcv_frame() -> pd.DataFrame:
    """Build an empty dataframe with OHLCV columns."""

    return pd.DataFrame(columns=list(OHLCV_COLUMNS))
