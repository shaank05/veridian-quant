"""Tests for V2 market index ingestion."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
import requests

from veridian_quant.v2.data.ingestion_config import IngestionConfig
from veridian_quant.v2.data.market_index_ingestion import (
    MarketIndexIngestionRunner,
    MarketIndexInstrumentResolver,
    convert_index_candles,
)
from veridian_quant.v2.data.upstox_history import HistoricalChunkResult


def test_aliases_resolve_fake_upstox_instruments() -> None:
    resolver = MarketIndexInstrumentResolver(
        FakeEngine(
            [
                _instrument("NSE_INDEX|Nifty 50", "Nifty 50"),
                _instrument("NSE_INDEX|Nifty Bank", "NIFTY BANK", trading_symbol="BANKNIFTY"),
                _instrument("NSE_INDEX|NIFTY SMLCAP 250", "NIFTY SMLCAP 250"),
            ]
        )
    )

    result = resolver.resolve(["NIFTY_50", "NIFTY_BANK", "NIFTY_SMALLCAP_250"])

    assert [item.instrument_key for item in result.resolved] == [
        "NSE_INDEX|Nifty 50",
        "NSE_INDEX|Nifty Bank",
        "NSE_INDEX|NIFTY SMLCAP 250",
    ]
    assert result.unresolved == ()
    assert result.ambiguous == ()


def test_unresolved_index_is_reported() -> None:
    resolver = MarketIndexInstrumentResolver(FakeEngine([]))

    result = resolver.resolve(["NIFTY_50"])

    assert result.resolved == ()
    assert result.unresolved == ("NIFTY_50",)


def test_ambiguous_index_is_reported_clearly() -> None:
    resolver = MarketIndexInstrumentResolver(
        FakeEngine(
            [
                _instrument("NSE_INDEX|Nifty 50", "NIFTY 50"),
                _instrument("NSE_INDEX|NIFTY50", "NIFTY50"),
            ]
        )
    )

    result = resolver.resolve(["NIFTY_50"])

    assert result.resolved == ()
    assert result.ambiguous[0].index_symbol == "NIFTY_50"
    assert result.ambiguous[0].candidates == ("NSE_INDEX|NIFTY50", "NSE_INDEX|Nifty 50")


def test_valid_fake_upstox_candles_convert_to_validated_rows() -> None:
    valid, rejected = convert_index_candles(
        [["2026-01-01T00:00:00+05:30", "100", "110", "95", "105", "0", "0"]],
        "NIFTY_50",
        "NSE_INDEX|Nifty 50",
    )

    assert rejected == 0
    assert len(valid) == 1
    assert valid[0].instrument_key == "NSE_INDEX|Nifty 50"
    assert valid[0].open == Decimal("100")
    assert valid[0].interval == "day"


def test_malformed_candles_are_rejected() -> None:
    valid, rejected = convert_index_candles(
        [
            ["2026-01-01T00:00:00+05:30", 100, 90, 95, 105, 0],
            ["", 100, 110, 95, 105, 0],
        ],
        "NIFTY_50",
        "NSE_INDEX|Nifty 50",
    )

    assert valid == []
    assert rejected == 2


def test_empty_api_response_is_handled() -> None:
    writer = FakeWriter()
    runner = MarketIndexIngestionRunner(
        engine=object(),
        config=_config(),
        resolver=FakeResolver(),
        history_client=FakeHistoryClient(
            [
                HistoricalChunkResult(
                    instrument_key="NSE_INDEX|Nifty 50",
                    interval="day",
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 1, 2),
                    candles=[],
                )
            ]
        ),
        writer=writer,
    )

    summary = runner.run(
        ["NIFTY_50"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        dry_run=False,
    )

    assert summary.chunks_fetched == 1
    assert summary.candles_fetched == 0
    assert summary.candles_inserted == 0
    assert writer.rows == []


def test_api_failure_is_reported_without_crashing() -> None:
    runner = MarketIndexIngestionRunner(
        engine=object(),
        config=_config(),
        resolver=FakeResolver(),
        history_client=FakeHistoryClient(
            [
                HistoricalChunkResult(
                    instrument_key="NSE_INDEX|Nifty 50",
                    interval="day",
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 1, 2),
                    candles=[],
                    ok=False,
                    error="rate limited",
                )
            ]
        ),
        writer=FakeWriter(),
    )

    summary = runner.run(
        ["NIFTY_50"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        dry_run=False,
    )

    assert summary.chunks_failed == 1
    assert summary.failures_by_index == {"NIFTY_50": "rate limited"}


def test_network_exception_is_reported_as_failed_chunk() -> None:
    runner = MarketIndexIngestionRunner(
        engine=object(),
        config=_config(),
        resolver=FakeResolver(),
        history_client=ExplodingHistoryClient(),
        writer=FakeWriter(),
    )

    summary = runner.run(
        ["NIFTY_50"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        dry_run=False,
    )

    assert summary.chunks_failed == 1
    assert "network down" in summary.failures_by_index["NIFTY_50"]


def test_dry_run_resolves_and_plans_without_fetching_or_writing() -> None:
    runner = MarketIndexIngestionRunner(
        engine=object(),
        config=_config(access_token=None),
        resolver=FakeResolver(),
        history_client=ExplodingHistoryClient(),
        writer=ExplodingWriter(),
    )

    summary = runner.run(
        ["NIFTY_50"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        dry_run=True,
    )

    assert summary.resolved_indices == ["NIFTY_50"]
    assert summary.chunks_planned == 1
    assert summary.dry_run is True


def test_upsert_idempotency_delegates_to_writer_rows_once_per_valid_candle() -> None:
    writer = FakeWriter()
    runner = MarketIndexIngestionRunner(
        engine=object(),
        config=_config(),
        resolver=FakeResolver(),
        history_client=FakeHistoryClient(
            [
                HistoricalChunkResult(
                    instrument_key="NSE_INDEX|Nifty 50",
                    interval="day",
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 1, 2),
                    candles=[
                        ["2026-01-01T00:00:00+05:30", 100, 110, 95, 105, 0],
                        ["2026-01-02T00:00:00+05:30", 105, 111, 100, 108, 0],
                    ],
                )
            ]
        ),
        writer=writer,
    )

    summary = runner.run(
        ["NIFTY_50"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        dry_run=False,
    )

    assert summary.candles_inserted == 2
    assert len(writer.rows) == 2


def test_interval_other_than_day_is_rejected() -> None:
    runner = MarketIndexIngestionRunner(
        engine=object(),
        config=_config(access_token=None),
        resolver=FakeResolver(),
        history_client=None,
        writer=FakeWriter(),
    )

    with pytest.raises(ValueError, match="only supports daily interval"):
        runner.run(
            ["NIFTY_50"],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 2),
            interval="1minute",
        )


def _config(access_token: str | None = "token") -> IngestionConfig:
    return IngestionConfig(
        access_token=access_token,
        api_version="2.0",
        max_days_1d=365,
        max_days_1m=30,
        throttle_seconds=0,
        max_retries=0,
        backoff_base_seconds=0,
        log_dir="logs/v2/ingestion",
        run_dir="reports/v2/ingestion_runs",
        network_retry="wait",
        network_wait_seconds=0,
        network_max_wait_minutes=0,
        chunk_min_coverage_pct=70,
    )


def _instrument(instrument_key, name, symbol=None, trading_symbol=None):
    return {
        "instrument_key": instrument_key,
        "symbol": symbol or name,
        "trading_symbol": trading_symbol or symbol or name,
        "name": name,
        "exchange": "NSE_INDEX",
        "segment": "NSE_INDEX",
        "instrument_type": "INDEX",
    }


class FakeResolver:
    def __init__(self, unresolved=(), ambiguous=()):
        self.unresolved = unresolved
        self.ambiguous = ambiguous

    def resolve(self, index_symbols):
        from veridian_quant.v2.data.market_index_ingestion import (
            MarketIndexResolution,
            ResolvedMarketIndex,
        )
        from veridian_quant.v2.data.market_index_registry import get_market_index

        resolved = [
            ResolvedMarketIndex(
                definition=get_market_index(symbol),
                instrument_key=f"NSE_INDEX|{get_market_index(symbol).index_name}",
                name=get_market_index(symbol).index_name,
                exchange="NSE_INDEX",
            )
            for symbol in index_symbols
            if symbol not in self.unresolved
        ]
        return MarketIndexResolution(
            resolved=tuple(resolved),
            unresolved=tuple(self.unresolved),
            ambiguous=tuple(self.ambiguous),
        )


class FakeHistoryClient:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def fetch_candles(self, instrument_key, interval, start_date, end_date):
        self.calls.append((instrument_key, interval, start_date, end_date))
        return self.results.pop(0)


class ExplodingHistoryClient:
    def fetch_candles(self, *args, **kwargs):
        raise requests.ConnectionError("network down")


class FakeWriter:
    def __init__(self):
        self.rows = []

    def upsert_candles(self, candles):
        rows = list(candles)
        self.rows.extend(rows)
        return len(rows)


class ExplodingWriter:
    def upsert_candles(self, *args, **kwargs):
        raise AssertionError("dry-run must not write")


class FakeEngine:
    def __init__(self, rows):
        self.rows = sorted(rows, key=lambda row: row["instrument_key"])

    def connect(self):
        return FakeConnection(self.rows)


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query):
        return FakeResult(self.rows)


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows
