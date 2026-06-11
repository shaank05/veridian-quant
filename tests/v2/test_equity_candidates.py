"""Tests for raw V2 NSE equity candidate-list building."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from veridian_quant.v2.data.equity_candidates import build_raw_nse_equity_candidates


def test_candidate_builder_creates_all_required_csvs(tmp_path: Path) -> None:
    paths = _run_builder(_engine_with_instruments(), tmp_path)

    assert set(paths) == {
        "raw_nse_eq_candidates",
        "clean_nse_eq_candidates",
        "rejected_nse_eq_candidates",
        "equity_candidate_summary",
    }
    assert all(path.exists() for path in paths.values())


def test_uses_instrument_key_prefix_not_exchange_exact_value(tmp_path: Path) -> None:
    paths = _run_builder(_engine_with_instruments(), tmp_path)

    raw = pd.read_csv(paths["raw_nse_eq_candidates"])

    assert "RELIANCE" in set(raw["symbol"])
    assert "BSEPOLLUTE" not in set(raw["symbol"])
    assert raw.loc[raw["symbol"] == "RELIANCE", "exchange"].iloc[0] == "NSE"


def test_keeps_instrument_type_eq_candidates(tmp_path: Path) -> None:
    paths = _run_builder(_engine_with_instruments(), tmp_path)

    raw = pd.read_csv(paths["raw_nse_eq_candidates"])

    assert set(raw["instrument_type"]) == {"EQ"}
    assert "RELIANCE" in set(raw["symbol"])


def test_rejects_blank_or_empty_instrument_type_from_raw_candidates(tmp_path: Path) -> None:
    paths = _run_builder(_engine_with_instruments(), tmp_path)

    raw = pd.read_csv(paths["raw_nse_eq_candidates"])
    rejected = pd.read_csv(paths["rejected_nse_eq_candidates"])

    assert "BLANKTYPE" not in set(raw["symbol"])
    assert "BLANKTYPE" not in set(rejected["symbol"])


def test_rejects_symbols_starting_with_digit(tmp_path: Path) -> None:
    paths = _run_builder(_engine_with_instruments(), tmp_path)

    rejected = _rejected_row(paths["rejected_nse_eq_candidates"], "123CO")

    assert rejected["exclusion_reason"] == "STARTS_WITH_DIGIT"


def test_rejects_debt_and_security_keyword_patterns(tmp_path: Path) -> None:
    paths = _run_builder(_engine_with_instruments(), tmp_path)

    rejected = _rejected_row(paths["rejected_nse_eq_candidates"], "ABCNCD")

    assert rejected["exclusion_reason"] == "KEYWORD_NCD"


def test_excludes_etf_like_symbols_by_default(tmp_path: Path) -> None:
    paths = _run_builder(_engine_with_instruments(), tmp_path)

    rejected = pd.read_csv(paths["rejected_nse_eq_candidates"])

    assert "NIFTYETF" in set(rejected["symbol"])
    assert "GOLDBEES" in set(rejected["symbol"])


def test_include_etfs_keeps_etf_like_symbols(tmp_path: Path) -> None:
    paths = build_raw_nse_equity_candidates(
        engine=_engine_with_instruments(),
        output_dir=tmp_path,
        include_etfs=True,
    )

    clean = pd.read_csv(paths["clean_nse_eq_candidates"])
    rejected = pd.read_csv(paths["rejected_nse_eq_candidates"])

    assert "NIFTYETF" in set(clean["symbol"])
    assert "GOLDBEES" in set(clean["symbol"])
    assert "NIFTYETF" not in set(rejected["symbol"])
    assert "GOLDBEES" not in set(rejected["symbol"])


def test_deduplicates_by_trading_symbol(tmp_path: Path) -> None:
    paths = _run_builder(_engine_with_instruments(), tmp_path)

    raw = pd.read_csv(paths["raw_nse_eq_candidates"])
    clean = pd.read_csv(paths["clean_nse_eq_candidates"])

    assert list(raw.loc[raw["trading_symbol"] == "DUP", "symbol"]) == ["ADUP"]
    assert list(clean.loc[clean["trading_symbol"] == "DUP", "symbol"]) == ["ADUP"]


def test_summary_counts_are_correct(tmp_path: Path) -> None:
    paths = _run_builder(_engine_with_instruments(), tmp_path)

    summary = pd.read_csv(paths["equity_candidate_summary"]).iloc[0]

    assert summary["raw_candidates"] == 6
    assert summary["clean_candidates"] == 2
    assert summary["rejected_candidates"] == 4
    assert summary["exchange_filter"] == "NSE_EQ|%"
    assert summary["instrument_type_filter"] == "EQ"
    assert summary["starts_with_digit_rejections"] == 1
    assert summary["keyword_rejections"] == 3


def _run_builder(engine: object, tmp_path: Path) -> dict[str, Path]:
    return build_raw_nse_equity_candidates(
        engine=engine,
        output_dir=tmp_path,
        exchange="NSE_EQ",
    )


def _rejected_row(path: Path, symbol: str) -> pd.Series:
    rejected = pd.read_csv(path)
    row = rejected.loc[rejected["symbol"] == symbol]
    assert len(row) == 1
    return row.iloc[0]


def _engine_with_instruments() -> object:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE instruments (
                    instrument_key TEXT PRIMARY KEY,
                    exchange_token TEXT,
                    exchange TEXT,
                    symbol TEXT,
                    trading_symbol TEXT,
                    name TEXT,
                    segment TEXT,
                    instrument_type TEXT,
                    lot_size INTEGER,
                    last_synced TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO instruments (
                    instrument_key,
                    exchange_token,
                    exchange,
                    symbol,
                    trading_symbol,
                    name,
                    segment,
                    instrument_type,
                    lot_size,
                    last_synced
                )
                VALUES (
                    :instrument_key,
                    :exchange_token,
                    :exchange,
                    :symbol,
                    :trading_symbol,
                    :name,
                    :segment,
                    :instrument_type,
                    :lot_size,
                    :last_synced
                )
                """
            ),
            [
                _instrument("NSE_EQ|RELIANCE", "RELIANCE", exchange="NSE"),
                _instrument("NSE_EQ|ADUP", "ADUP", trading_symbol="DUP"),
                _instrument("NSE_EQ|BDUP", "BDUP", trading_symbol="DUP"),
                _instrument("NSE_EQ|123CO", "123CO"),
                _instrument("NSE_EQ|ABCNCD", "ABCNCD"),
                _instrument("NSE_EQ|NIFTYETF", "NIFTYETF"),
                _instrument("NSE_EQ|GOLDBEES", "GOLDBEES"),
                _instrument("NSE_EQ|BLANKTYPE", "BLANKTYPE", instrument_type=""),
                _instrument("NSE_EQ|LOT", "LOT", lot_size=10),
                _instrument("NSE_EQ|BLANKSYMBOL", "", trading_symbol="BLANKSYMBOL"),
                _instrument("NSE_EQ|BLANKTRADING", "BLANKTRADING", trading_symbol=""),
                _instrument("BSE_EQ|BSEPOLLUTE", "BSEPOLLUTE", exchange="NSE_EQ"),
            ],
        )
    return engine


def _instrument(
    instrument_key: str,
    symbol: str,
    trading_symbol: str | None = None,
    exchange: str = "NSE",
    instrument_type: str | None = "EQ",
    lot_size: int | None = 1,
) -> dict[str, object]:
    return {
        "instrument_key": instrument_key,
        "exchange_token": f"TOKEN-{symbol}",
        "exchange": exchange,
        "symbol": symbol,
        "trading_symbol": trading_symbol if trading_symbol is not None else symbol,
        "name": f"{symbol} Limited",
        "segment": "NSE_EQ",
        "instrument_type": instrument_type,
        "lot_size": lot_size,
        "last_synced": "2026-06-11T00:00:00+00:00",
    }
