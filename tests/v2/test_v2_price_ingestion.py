"""Tests for the V2 price ingestion foundation."""

from __future__ import annotations

import csv
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
import requests

from veridian_quant.v2.data.ingestion_config import IngestionConfig
from veridian_quant.v2.data.instruments import InstrumentResolver, ResolvedInstrument
from veridian_quant.v2.data.price_ingestion import (
    PriceIngestionRunner,
    UPSERT_PRICES_SQL,
    generate_date_chunks,
    load_symbols_from_sources,
    validate_candles,
)
from veridian_quant.v2.data.upstox_history import HistoricalChunkResult, UpstoxHistoryClient


def test_env_config_defaults_are_applied(monkeypatch) -> None:
    for name in (
        "UPSTOX_ACCESS_TOKEN",
        "UPSTOX_API_VERSION",
        "V2_INGESTION_MAX_DAYS_1D",
        "V2_INGESTION_MAX_DAYS_1M",
        "V2_INGESTION_THROTTLE_SECONDS",
        "V2_INGESTION_MAX_RETRIES",
        "V2_INGESTION_BACKOFF_BASE_SECONDS",
        "V2_INGESTION_LOG_DIR",
        "V2_INGESTION_RUN_DIR",
        "V2_INGESTION_NETWORK_RETRY",
        "V2_INGESTION_NETWORK_WAIT_SECONDS",
        "V2_INGESTION_NETWORK_MAX_WAIT_MINUTES",
        "V2_INGESTION_CHUNK_MIN_COVERAGE_PCT",
    ):
        monkeypatch.delenv(name, raising=False)

    config = IngestionConfig.from_env()

    assert config.access_token is None
    assert config.api_version == "2.0"
    assert config.max_days_1d == 365
    assert config.max_days_1m == 30
    assert config.throttle_seconds == 0.5
    assert config.max_retries == 3
    assert config.backoff_base_seconds == 5
    assert str(config.log_dir) == "logs\\v2\\ingestion" or str(config.log_dir) == "logs/v2/ingestion"
    assert str(config.run_dir) == "reports\\v2\\ingestion_runs" or str(config.run_dir) == "reports/v2/ingestion_runs"
    assert config.network_retry == "wait"
    assert config.network_wait_seconds == 60
    assert config.network_max_wait_minutes == 0
    assert config.chunk_min_coverage_pct == 70


def test_api_version_none_string_uses_default(monkeypatch) -> None:
    monkeypatch.setenv("UPSTOX_API_VERSION", "None")

    assert IngestionConfig.from_env().api_version == "2.0"


def test_missing_token_allowed_for_dry_run_but_rejected_for_real_modes() -> None:
    config = _config(access_token=None)

    config.require_access_token("dry-run")
    with pytest.raises(ValueError, match="UPSTOX_ACCESS_TOKEN is required"):
        config.require_access_token("backfill")
    with pytest.raises(ValueError, match="UPSTOX_ACCESS_TOKEN is required"):
        config.require_access_token("incremental")


def test_symbol_parsing_from_comma_separated_symbols() -> None:
    assert load_symbols_from_sources(" reliance, TCS,,infy ") == [
        "RELIANCE",
        "TCS",
        "INFY",
    ]


def test_symbol_parsing_from_csv_symbol_file(tmp_path: Path) -> None:
    path = tmp_path / "symbols.csv"
    path.write_text("symbol,name\nreliance,Reliance\nTCS,Tata\n", encoding="utf-8")

    assert load_symbols_from_sources(symbol_file=path) == ["RELIANCE", "TCS"]


def test_symbol_parsing_from_text_file_and_deduplication(tmp_path: Path) -> None:
    path = tmp_path / "symbols.txt"
    path.write_text("reliance\n# comment\nTCS\nRELIANCE\n", encoding="utf-8")

    assert load_symbols_from_sources("infy,tcs", path) == ["INFY", "TCS", "RELIANCE"]


def test_instrument_resolver_restricts_exchange_and_dedupes_pollution() -> None:
    rows = [
        {
            "symbol": "RELIANCE",
            "instrument_key": "NSE_EQ|INE002A01018",
            "name": "Reliance Industries",
            "exchange": "NSE_EQ",
            "trading_symbol": "RELIANCE",
            "segment": "NSE_EQ",
            "instrument_type": "EQ",
        },
        {
            "symbol": "RELIANCE",
            "instrument_key": "BSE_EQ|500325",
            "name": "Reliance Industries",
            "exchange": "BSE_EQ",
            "trading_symbol": "RELIANCE",
            "segment": "BSE_EQ",
            "instrument_type": "EQ",
        },
    ]
    engine = FakeEngine(rows)
    resolver = InstrumentResolver(engine)

    resolved, unresolved = resolver.resolve_symbols(["reliance", "missing"], "NSE_EQ")

    assert [item.instrument_key for item in resolved] == ["NSE_EQ|INE002A01018"]
    assert unresolved == ["MISSING"]
    assert engine.last_params["instrument_prefix"] == "NSE_EQ|%"


def test_backfill_mode_requires_start_date() -> None:
    runner = PriceIngestionRunner(
        engine=object(),
        config=_config(access_token="token"),
        resolver=FakeResolver(),
        history_client=FakeHistoryClient([]),
        writer=FakeWriter(),
    )

    with pytest.raises(ValueError, match="backfill mode requires --start-date"):
        runner.run(["RELIANCE"], mode="backfill")


def test_incremental_mode_uses_existing_latest_timestamp() -> None:
    history_client = FakeHistoryClient([])
    writer = FakeWriter(latest=datetime(2026, 1, 10, tzinfo=timezone.utc))
    runner = PriceIngestionRunner(
        engine=object(),
        config=_config(access_token="token", throttle_seconds=0),
        resolver=FakeResolver(),
        history_client=history_client,
        writer=writer,
    )

    summary = runner.run(
        ["RELIANCE"],
        mode="incremental",
        interval="day",
        end_date=date(2026, 1, 12),
    )

    assert history_client.calls == [
        ("NSE_EQ|RELIANCE", "day", date(2026, 1, 11), date(2026, 1, 12))
    ]
    assert summary.chunks_fetched == 1


def test_incremental_mode_raises_when_no_prior_data_without_start_date() -> None:
    runner = PriceIngestionRunner(
        engine=object(),
        config=_config(access_token="token"),
        resolver=FakeResolver(),
        history_client=FakeHistoryClient([]),
        writer=FakeWriter(latest=None),
    )

    with pytest.raises(ValueError, match="run backfill first or provide --start-date"):
        runner.run(["RELIANCE"], mode="incremental", interval="day")


def test_chunk_generation_respects_max_days() -> None:
    chunks = generate_date_chunks(date(2026, 1, 1), date(2026, 1, 10), max_days=4)

    assert [(chunk.start_date, chunk.end_date) for chunk in chunks] == [
        (date(2026, 1, 1), date(2026, 1, 4)),
        (date(2026, 1, 5), date(2026, 1, 8)),
        (date(2026, 1, 9), date(2026, 1, 10)),
    ]


def test_candle_conversion_skips_malformed_rows() -> None:
    valid, skipped = validate_candles(
        [
            ["2026-01-01T00:00:00+05:30", 10, 12, 9, 11, "1000", 5],
            ["2026-01-02T00:00:00+05:30", 10, 8, 9, 11, 1000, 5],
            ["", 10, 12, 9, 11, 1000, 5],
        ],
        "NSE_EQ|RELIANCE",
        "day",
    )

    assert len(valid) == 1
    assert valid[0].open_interest == 5
    assert skipped == 2


def test_upsert_sql_updates_full_ohlcv_oi_fields_on_conflict() -> None:
    sql = " ".join(UPSERT_PRICES_SQL.split())

    assert "ON CONFLICT (timestamp, instrument_key, interval)" in sql
    for field in ("open", "high", "low", "close", "volume", "open_interest"):
        assert f"{field} = EXCLUDED.{field}" in sql


def test_dry_run_does_not_call_upstox_or_write_db() -> None:
    history_client = ExplodingHistoryClient()
    writer = ExplodingWriter()
    runner = PriceIngestionRunner(
        engine=object(),
        config=_config(access_token=None),
        resolver=FakeResolver(),
        history_client=history_client,
        writer=writer,
    )

    summary = runner.run(
        ["RELIANCE"],
        mode="dry-run",
        interval="day",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 10),
    )

    assert summary.chunks_planned == 1
    assert summary.candles_inserted == 0


def test_status_file_is_created_with_planned_chunks(tmp_path: Path) -> None:
    runner = PriceIngestionRunner(
        engine=object(),
        config=_config(access_token="token", throttle_seconds=0),
        resolver=FakeResolver(),
        history_client=FakeHistoryClient([]),
        writer=FakeWriter(),
    )

    summary = runner.run(
        ["RELIANCE"],
        mode="backfill",
        interval="day",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        run_id="status_test",
        run_dir=tmp_path,
        skip_existing_chunks=False,
    )

    rows = _read_status_rows(tmp_path)
    assert summary.status_file_path == str(tmp_path / "ingestion_chunk_status.csv")
    assert len(rows) == 1
    assert rows[0]["status"] == "NO_CANDLES"
    assert rows[0]["run_id"] == "status_test"


def test_completed_chunks_are_skipped_when_resume_is_enabled(tmp_path: Path) -> None:
    _write_status_row(tmp_path, status="INSERTED")
    runner = PriceIngestionRunner(
        engine=object(),
        config=_config(access_token="token"),
        resolver=FakeResolver(),
        history_client=ExplodingHistoryClient(),
        writer=FakeWriter(),
    )

    summary = runner.run(
        ["RELIANCE"],
        mode="backfill",
        interval="day",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        run_id="resume_test",
        run_dir=tmp_path,
        resume=True,
        skip_existing_chunks=False,
    )

    assert summary.chunks_fetched == 0
    assert summary.chunks_failed == 0


def test_fetch_failed_final_chunks_are_retried_on_resume(tmp_path: Path) -> None:
    _write_status_row(tmp_path, status="FETCH_FAILED_FINAL", error="old failure")
    history_client = FakeHistoryClient([])
    runner = PriceIngestionRunner(
        engine=object(),
        config=_config(access_token="token", throttle_seconds=0),
        resolver=FakeResolver(),
        history_client=history_client,
        writer=FakeWriter(),
    )

    summary = runner.run(
        ["RELIANCE"],
        mode="backfill",
        interval="day",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        run_id="resume_test",
        run_dir=tmp_path,
        resume=True,
        skip_existing_chunks=False,
    )

    assert history_client.calls == [
        ("NSE_EQ|RELIANCE", "day", date(2026, 1, 1), date(2026, 1, 2))
    ]
    assert summary.chunks_fetched == 1
    assert _read_status_rows(tmp_path)[0]["status"] == "NO_CANDLES"


def test_db_completeness_check_skips_when_coverage_is_above_threshold() -> None:
    history_client = ExplodingHistoryClient()
    runner = PriceIngestionRunner(
        engine=FakeCountEngine(existing_rows=2),
        config=_config(access_token="token"),
        resolver=FakeResolver(),
        history_client=history_client,
        writer=FakeWriter(),
    )

    summary = runner.run(
        ["RELIANCE"],
        mode="backfill",
        interval="day",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        chunk_min_coverage_pct=70,
    )

    assert summary.chunks_skipped_existing == 1
    assert summary.chunks_fetched == 0


def test_db_completeness_check_does_not_skip_below_threshold() -> None:
    history_client = FakeHistoryClient([])
    runner = PriceIngestionRunner(
        engine=FakeCountEngine(existing_rows=1),
        config=_config(access_token="token", throttle_seconds=0),
        resolver=FakeResolver(),
        history_client=history_client,
        writer=FakeWriter(),
    )

    summary = runner.run(
        ["RELIANCE"],
        mode="backfill",
        interval="day",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        chunk_min_coverage_pct=70,
    )

    assert summary.chunks_skipped_existing == 0
    assert summary.chunks_fetched == 1


def test_summary_includes_chunks_skipped_existing() -> None:
    summary = PriceIngestionRunner(
        engine=FakeCountEngine(existing_rows=2),
        config=_config(access_token="token"),
        resolver=FakeResolver(),
        history_client=ExplodingHistoryClient(),
        writer=FakeWriter(),
    ).run(
        ["RELIANCE"],
        mode="backfill",
        interval="day",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        chunk_min_coverage_pct=70,
    )

    assert summary.to_dict()["chunks_skipped_existing"] == 1


def test_dry_run_creates_planned_statuses_without_calling_upstox_or_db(tmp_path: Path) -> None:
    runner = PriceIngestionRunner(
        engine=object(),
        config=_config(access_token=None),
        resolver=FakeResolver(),
        history_client=ExplodingHistoryClient(),
        writer=ExplodingWriter(),
    )

    summary = runner.run(
        ["RELIANCE"],
        mode="dry-run",
        interval="day",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 10),
        run_id="dry_status",
        run_dir=tmp_path,
    )

    rows = _read_status_rows(tmp_path)
    assert summary.chunks_planned == 1
    assert rows[0]["status"] == "DRY_RUN_PLANNED"


def test_network_wait_mode_retries_same_chunk_after_connection_error() -> None:
    history_client = FlakyNetworkHistoryClient()
    runner = PriceIngestionRunner(
        engine=object(),
        config=_config(access_token="token", throttle_seconds=0),
        resolver=FakeResolver(),
        history_client=history_client,
        writer=FakeWriter(),
    )

    summary = runner.run(
        ["RELIANCE"],
        mode="backfill",
        interval="day",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        skip_existing_chunks=False,
        network_retry="wait",
        network_wait_seconds=0,
    )

    assert history_client.calls == 2
    assert summary.chunks_fetched == 1


def test_network_fail_fast_mode_marks_connection_error_as_failed_chunk() -> None:
    runner = PriceIngestionRunner(
        engine=object(),
        config=_config(access_token="token", throttle_seconds=0),
        resolver=FakeResolver(),
        history_client=AlwaysNetworkFailHistoryClient(),
        writer=FakeWriter(),
    )

    summary = runner.run(
        ["RELIANCE"],
        mode="backfill",
        interval="day",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        skip_existing_chunks=False,
        network_retry="fail-fast",
    )

    assert summary.chunks_failed == 1
    assert summary.chunks_fetched == 0


def test_401_and_403_responses_are_not_retried_indefinitely() -> None:
    session = FakeSession([FakeResponse(401, "unauthorized")])
    client = UpstoxHistoryClient(_config(access_token="token"), session=session)

    result = client.fetch_candles("NSE_EQ|RELIANCE", "day", date(2026, 1, 1), date(2026, 1, 2))

    assert result.ok is False
    assert "HTTP 401" in (result.error or "")
    assert session.calls == 1


def test_failed_api_chunk_does_not_crash_whole_run() -> None:
    failed = HistoricalChunkResult(
        instrument_key="NSE_EQ|RELIANCE",
        interval="day",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        candles=[],
        ok=False,
        error="rate limited",
    )
    runner = PriceIngestionRunner(
        engine=object(),
        config=_config(access_token="token", throttle_seconds=0),
        resolver=FakeResolver(),
        history_client=FakeHistoryClient([failed]),
        writer=FakeWriter(),
    )

    summary = runner.run(
        ["RELIANCE"],
        mode="backfill",
        interval="day",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
    )

    assert summary.chunks_failed == 1
    assert summary.candles_inserted == 0


def _config(access_token: str | None = "token", throttle_seconds: float = 0.0) -> IngestionConfig:
    return IngestionConfig(
        access_token=access_token,
        api_version="2.0",
        max_days_1d=365,
        max_days_1m=30,
        throttle_seconds=throttle_seconds,
        max_retries=0,
        backoff_base_seconds=0,
        log_dir=Path("logs/v2/ingestion"),
        run_dir=Path("reports/v2/ingestion_runs"),
        network_retry="wait",
        network_wait_seconds=0,
        network_max_wait_minutes=0,
        chunk_min_coverage_pct=70,
    )


def _read_status_rows(run_dir: Path) -> list[dict[str, str]]:
    with (run_dir / "ingestion_chunk_status.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_status_row(
    run_dir: Path,
    status: str,
    error: str = "",
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    columns = [
        "run_id",
        "symbol",
        "instrument_key",
        "interval",
        "chunk_start_date",
        "chunk_end_date",
        "status",
        "attempt_count",
        "candles_received",
        "candles_inserted",
        "candles_skipped",
        "error",
        "started_at",
        "finished_at",
        "updated_at",
    ]
    with (run_dir / "ingestion_chunk_status.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerow(
            {
                "run_id": "resume_test",
                "symbol": "RELIANCE",
                "instrument_key": "NSE_EQ|RELIANCE",
                "interval": "day",
                "chunk_start_date": "2026-01-01",
                "chunk_end_date": "2026-01-02",
                "status": status,
                "attempt_count": "1",
                "candles_received": "0",
                "candles_inserted": "0",
                "candles_skipped": "0",
                "error": error,
                "started_at": "",
                "finished_at": "",
                "updated_at": "2026-01-01T00:00:00+00:00",
            }
        )


class FakeResolver:
    def resolve_symbols(self, symbols, exchange="NSE_EQ"):
        requested = [str(symbol).strip().upper() for symbol in symbols]
        instruments = [
            ResolvedInstrument(
                symbol=symbol,
                instrument_key=f"{exchange}|{symbol}",
                name=symbol,
                exchange=exchange,
                trading_symbol=symbol,
            )
            for symbol in requested
            if symbol != "MISSING"
        ]
        unresolved = [symbol for symbol in requested if symbol == "MISSING"]
        return instruments, unresolved


class FakeHistoryClient:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def fetch_candles(self, instrument_key, interval, start_date, end_date):
        self.calls.append((instrument_key, interval, start_date, end_date))
        if self.results:
            return self.results.pop(0)
        return HistoricalChunkResult(
            instrument_key=instrument_key,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
            candles=[],
        )


class FakeWriter:
    def __init__(self, latest=None):
        self.latest = latest
        self.upserted = []

    def get_latest_timestamp(self, instrument_key, interval):
        return self.latest

    def upsert_candles(self, candles):
        rows = list(candles)
        self.upserted.extend(rows)
        return len(rows)


class ExplodingHistoryClient:
    def fetch_candles(self, *args, **kwargs):
        raise AssertionError("dry-run must not call Upstox")


class FlakyNetworkHistoryClient:
    def __init__(self):
        self.calls = 0

    def fetch_candles(self, instrument_key, interval, start_date, end_date):
        self.calls += 1
        if self.calls == 1:
            raise requests.ConnectionError("temporary network outage")
        return HistoricalChunkResult(
            instrument_key=instrument_key,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
            candles=[],
        )


class AlwaysNetworkFailHistoryClient:
    def fetch_candles(self, *args, **kwargs):
        raise requests.ConnectionError("network down")


class ExplodingWriter:
    def get_latest_timestamp(self, *args, **kwargs):
        raise AssertionError("dry-run must not inspect latest timestamps")

    def upsert_candles(self, *args, **kwargs):
        raise AssertionError("dry-run must not write rows")


class FakeEngine:
    def __init__(self, rows):
        self.rows = rows
        self.last_params = None

    def connect(self):
        return FakeConnection(self)


class FakeConnection:
    def __init__(self, engine):
        self.engine = engine

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params):
        self.engine.last_params = params
        return FakeResult(self.engine.rows)


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows

    def scalar(self):
        return self.rows


class FakeCountEngine:
    def __init__(self, existing_rows: int):
        self.existing_rows = existing_rows
        self.last_params = None

    def connect(self):
        return FakeCountConnection(self)


class FakeCountConnection:
    def __init__(self, engine):
        self.engine = engine

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params):
        self.engine.last_params = params
        return FakeCountResult(self.engine.existing_rows)


class FakeCountResult:
    def __init__(self, value: int):
        self.value = value

    def scalar(self):
        return self.value


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def get(self, *args, **kwargs):
        self.calls += 1
        return self.responses.pop(0)


class FakeResponse:
    def __init__(self, status_code: int, text: str = "", payload=None):
        self.status_code = status_code
        self.text = text
        self.payload = payload or {}

    def json(self):
        return self.payload
