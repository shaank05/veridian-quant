"""Tests for the market index ingestion CLI."""

from __future__ import annotations

import json
from datetime import date

from veridian_quant.v2 import run_market_index_ingestion


def test_cli_argument_parsing_supports_all_dates_and_dry_run(monkeypatch, capsys) -> None:
    observed = {}

    monkeypatch.setattr(
        run_market_index_ingestion.IngestionConfig,
        "from_env",
        staticmethod(lambda: _config()),
    )
    monkeypatch.setattr(
        run_market_index_ingestion.DatabaseClient,
        "__init__",
        lambda self: None,
    )
    monkeypatch.setattr(
        run_market_index_ingestion.DatabaseClient,
        "get_engine",
        lambda self: object(),
    )
    monkeypatch.setattr(
        run_market_index_ingestion,
        "MarketIndexIngestionRunner",
        lambda **kwargs: FakeRunner(observed),
    )

    exit_code = run_market_index_ingestion.main(
        [
            "--indices",
            "ALL",
            "--start-date",
            "2026-01-01",
            "--end-date",
            "2026-01-31",
            "--dry-run",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert observed["indices"][0] == "NIFTY_50"
    assert observed["start_date"] == date(2026, 1, 1)
    assert observed["end_date"] == date(2026, 1, 31)
    assert observed["dry_run"] is True
    assert payload["dry_run"] is True


def test_cli_argument_parsing_supports_comma_separated_indices(monkeypatch) -> None:
    observed = {}

    monkeypatch.setattr(
        run_market_index_ingestion.IngestionConfig,
        "from_env",
        staticmethod(lambda: _config()),
    )
    monkeypatch.setattr(run_market_index_ingestion.DatabaseClient, "__init__", lambda self: None)
    monkeypatch.setattr(run_market_index_ingestion.DatabaseClient, "get_engine", lambda self: object())
    monkeypatch.setattr(
        run_market_index_ingestion,
        "MarketIndexIngestionRunner",
        lambda **kwargs: FakeRunner(observed),
    )

    run_market_index_ingestion.main(
        [
            "--indices",
            "NIFTY_50,NIFTY_BANK",
            "--start-date",
            "2026-01-01",
            "--end-date",
            "2026-01-31",
            "--dry-run",
        ]
    )

    assert observed["indices"] == ["NIFTY_50", "NIFTY_BANK"]


def test_cli_audit_db_uses_read_only_audit_helper(monkeypatch, capsys) -> None:
    observed = {}

    monkeypatch.setattr(
        run_market_index_ingestion.IngestionConfig,
        "from_env",
        staticmethod(lambda: _config()),
    )
    monkeypatch.setattr(run_market_index_ingestion.DatabaseClient, "__init__", lambda self: None)
    monkeypatch.setattr(
        run_market_index_ingestion.DatabaseClient,
        "get_engine",
        lambda self: "engine",
    )
    monkeypatch.setattr(
        run_market_index_ingestion,
        "audit_market_index_daily_bars",
        lambda engine, **kwargs: FakeAuditReport(observed, engine, kwargs),
    )
    monkeypatch.setattr(
        run_market_index_ingestion,
        "MarketIndexIngestionRunner",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("audit must not ingest")),
    )

    exit_code = run_market_index_ingestion.main(
        [
            "--audit-db",
            "--indices",
            "NIFTY_50,NIFTY_AUTO",
            "--start-date",
            "2026-01-01",
            "--end-date",
            "2026-01-31",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert observed["engine"] == "engine"
    assert observed["kwargs"]["index_symbols"] == ["NIFTY_50", "NIFTY_AUTO"]
    assert payload["audit"] is True


def _config():
    from pathlib import Path

    from veridian_quant.v2.data.ingestion_config import IngestionConfig

    return IngestionConfig(
        access_token=None,
        api_version="2.0",
        max_days_1d=365,
        max_days_1m=30,
        throttle_seconds=0,
        max_retries=0,
        backoff_base_seconds=0,
        log_dir=Path("logs/v2/ingestion"),
        run_dir=Path("reports/v2/ingestion_runs"),
        network_retry="wait",
        network_wait_seconds=0,
        network_max_wait_minutes=0,
        chunk_min_coverage_pct=70,
    )


class FakeRunner:
    def __init__(self, observed):
        self.observed = observed

    def run(self, indices, start_date, end_date, interval, dry_run):
        self.observed.update(
            {
                "indices": list(indices),
                "start_date": start_date,
                "end_date": end_date,
                "interval": interval,
                "dry_run": dry_run,
            }
        )
        return FakeSummary(dry_run=dry_run)


class FakeSummary:
    def __init__(self, dry_run):
        self.dry_run = dry_run

    def to_dict(self):
        return {"dry_run": self.dry_run, "candles_inserted": 0}


class FakeAuditReport:
    def __init__(self, observed, engine, kwargs):
        observed["engine"] = engine
        observed["kwargs"] = kwargs

    def to_dict(self):
        return {"audit": True}
