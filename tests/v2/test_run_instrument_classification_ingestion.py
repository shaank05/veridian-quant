"""Tests for the instrument classification ingestion CLI."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from veridian_quant.v2 import run_instrument_classification_ingestion


def test_cli_parses_required_arguments_and_emits_summary(monkeypatch, tmp_path, capsys) -> None:
    observed = {}
    classification_file = tmp_path / "classifications.csv"
    symbols_file = tmp_path / "symbols.csv"
    classification_file.write_text("symbol,sector\nAAA,IT\n", encoding="utf-8")
    symbols_file.write_text("symbol\nAAA\n", encoding="utf-8")

    monkeypatch.setattr(
        run_instrument_classification_ingestion.DatabaseClient,
        "__init__",
        lambda self: None,
    )
    monkeypatch.setattr(
        run_instrument_classification_ingestion.DatabaseClient,
        "get_engine",
        lambda self: "engine",
    )
    monkeypatch.setattr(
        run_instrument_classification_ingestion,
        "InstrumentClassificationIngestionRunner",
        lambda engine: FakeRunner(observed, engine),
    )

    exit_code = run_instrument_classification_ingestion.main(
        [
            "--classification-file",
            str(classification_file),
            "--symbols-file",
            str(symbols_file),
            "--classification-mode",
            "static_current",
            "--source",
            "TEST_SOURCE",
            "--effective-from",
            "2026-01-01",
            "--dry-run",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert observed["engine"] == "engine"
    assert observed["classification_file"] == classification_file
    assert observed["symbols_file"] == symbols_file
    assert observed["classification_mode"] == "static_current"
    assert observed["source"] == "TEST_SOURCE"
    assert observed["effective_from"] == date(2026, 1, 1)
    assert observed["dry_run"] is True
    assert payload["classification_mode"] == "static_current"
    assert payload["dry_run"] is True


def test_cli_audit_only_forces_non_writing_summary(monkeypatch, tmp_path, capsys) -> None:
    observed = {}
    classification_file = tmp_path / "classifications.csv"
    symbols_file = tmp_path / "symbols.csv"
    classification_file.write_text("symbol,sector\nAAA,IT\n", encoding="utf-8")
    symbols_file.write_text("symbol\nAAA\n", encoding="utf-8")

    monkeypatch.setattr(run_instrument_classification_ingestion.DatabaseClient, "__init__", lambda self: None)
    monkeypatch.setattr(
        run_instrument_classification_ingestion.DatabaseClient,
        "get_engine",
        lambda self: "engine",
    )
    monkeypatch.setattr(
        run_instrument_classification_ingestion,
        "InstrumentClassificationIngestionRunner",
        lambda engine: FakeRunner(observed, engine),
    )

    run_instrument_classification_ingestion.main(
        [
            "--classification-file",
            str(classification_file),
            "--symbols-file",
            str(symbols_file),
            "--source",
            "TEST_SOURCE",
            "--effective-from",
            "2026-01-01",
            "--audit-only",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert observed["audit_only"] is True
    assert payload["audit_only"] is True


class FakeRunner:
    def __init__(self, observed, engine):
        self.observed = observed
        self.observed["engine"] = engine

    def run(
        self,
        classification_file: Path,
        symbols_file: Path,
        classification_mode: str,
        source: str,
        effective_from: date,
        dry_run: bool,
        audit_only: bool,
    ):
        self.observed.update(
            {
                "classification_file": classification_file,
                "symbols_file": symbols_file,
                "classification_mode": classification_mode,
                "source": source,
                "effective_from": effective_from,
                "dry_run": dry_run,
                "audit_only": audit_only,
            }
        )
        return FakeSummary(classification_mode, dry_run or audit_only, audit_only)


class FakeSummary:
    def __init__(self, classification_mode, dry_run, audit_only):
        self.classification_mode = classification_mode
        self.dry_run = dry_run
        self.audit_only = audit_only

    def to_dict(self):
        return {
            "classification_mode": self.classification_mode,
            "dry_run": self.dry_run,
            "audit_only": self.audit_only,
        }
