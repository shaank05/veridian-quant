"""Tests for the company fundamentals ingestion CLI."""

from __future__ import annotations

import json

from veridian_quant.v2 import run_company_fundamentals_ingestion


def test_cli_parses_endpoints_limit_dry_run_and_classification_update(monkeypatch, tmp_path, capsys):
    observed = {}
    symbols_file = tmp_path / "symbols.csv"
    classification_file = tmp_path / "classifications.csv"
    symbols_file.write_text("symbol,instrument_key\nAAA,NSE_EQ|INE000A01010\n", encoding="utf-8")
    classification_file.write_text("symbol,sector\nAAA,UNKNOWN\n", encoding="utf-8")

    monkeypatch.setattr(
        run_company_fundamentals_ingestion.IngestionConfig,
        "from_env",
        lambda: "config",
    )
    monkeypatch.setattr(run_company_fundamentals_ingestion.DatabaseClient, "__init__", lambda self: None)
    monkeypatch.setattr(
        run_company_fundamentals_ingestion.DatabaseClient,
        "get_engine",
        lambda self: "engine",
    )
    monkeypatch.setattr(
        run_company_fundamentals_ingestion,
        "UpstoxFundamentalsClient",
        lambda config: ("client", config),
    )
    monkeypatch.setattr(
        run_company_fundamentals_ingestion,
        "CompanyFundamentalsIngestionRunner",
        lambda engine, client: FakeRunner(observed, engine, client),
    )

    exit_code = run_company_fundamentals_ingestion.main(
        [
            "--symbols-file",
            str(symbols_file),
            "--symbols",
            "AAA,BBB",
            "--isins",
            "INE000B01010",
            "--endpoints",
            "profile,key_ratios",
            "--source",
            "UPSTOX_FUNDAMENTALS",
            "--dry-run",
            "--limit",
            "2",
            "--update-classification-csv",
            "--classification-file",
            str(classification_file),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert observed["engine"] == "engine"
    assert observed["client"] == ("client", "config")
    assert observed["symbols_file"] == symbols_file
    assert observed["symbols"] == ["AAA", "BBB"]
    assert observed["isins"] == ["INE000B01010"]
    assert observed["endpoints"] == ["profile", "key_ratios"]
    assert observed["dry_run"] is True
    assert observed["limit"] == 2
    assert observed["update_classification_csv"] is True
    assert observed["classification_file"] == classification_file
    assert payload["dry_run"] is True
    assert payload["endpoints_requested"] == ["profile", "key_ratios"]


def test_cli_accepts_all_endpoint_alias(monkeypatch, tmp_path, capsys):
    observed = {}
    symbols_file = tmp_path / "symbols.csv"
    symbols_file.write_text("symbol,instrument_key\nAAA,NSE_EQ|INE000A01010\n", encoding="utf-8")
    monkeypatch.setattr(run_company_fundamentals_ingestion.IngestionConfig, "from_env", lambda: "config")
    monkeypatch.setattr(run_company_fundamentals_ingestion.DatabaseClient, "__init__", lambda self: None)
    monkeypatch.setattr(run_company_fundamentals_ingestion.DatabaseClient, "get_engine", lambda self: "engine")
    monkeypatch.setattr(run_company_fundamentals_ingestion, "UpstoxFundamentalsClient", lambda config: "client")
    monkeypatch.setattr(
        run_company_fundamentals_ingestion,
        "CompanyFundamentalsIngestionRunner",
        lambda engine, client: FakeRunner(observed, engine, client),
    )

    run_company_fundamentals_ingestion.main(
        ["--symbols-file", str(symbols_file), "--endpoints", "ALL", "--dry-run"]
    )

    payload = json.loads(capsys.readouterr().out)
    assert "income_statement" in observed["endpoints"]
    assert "competitors" in payload["endpoints_requested"]


class FakeRunner:
    def __init__(self, observed, engine, client):
        self.observed = observed
        self.observed["engine"] = engine
        self.observed["client"] = client

    def run(
        self,
        *,
        symbols_file,
        endpoints,
        source,
        dry_run,
        limit,
        symbols,
        isins,
        update_classification_csv,
        classification_file,
    ):
        self.observed.update(
            {
                "symbols_file": symbols_file,
                "endpoints": endpoints,
                "source": source,
                "dry_run": dry_run,
                "limit": limit,
                "symbols": symbols,
                "isins": isins,
                "update_classification_csv": update_classification_csv,
                "classification_file": classification_file,
            }
        )
        return FakeSummary(endpoints, dry_run, source)


class FakeSummary:
    def __init__(self, endpoints, dry_run, source):
        self.endpoints = endpoints
        self.dry_run = dry_run
        self.source = source

    def to_dict(self):
        return {
            "endpoints_requested": self.endpoints,
            "dry_run": self.dry_run,
            "source": self.source,
        }
