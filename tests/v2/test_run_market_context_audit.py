"""Tests for the Phase 33E.2 market context audit runner."""

from __future__ import annotations

import json
from datetime import date

import pandas as pd
import pytest

from veridian_quant.v2 import run_market_context_audit


def test_parse_windows_accepts_comma_separated_positive_ints() -> None:
    assert run_market_context_audit._parse_windows("5,20,60") == (5, 20, 60)


def test_parse_windows_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="windows must"):
        run_market_context_audit._parse_windows("5,0,nope")


def test_load_research_universe_applies_limit(tmp_path) -> None:
    path = tmp_path / "universe.csv"
    path.write_text(
        "symbol,instrument_key\nAAA,NSE_EQ|INE1\nBBB,NSE_EQ|INE2\n",
        encoding="utf-8",
    )

    entries = run_market_context_audit.load_research_universe(path, limit=1)

    assert len(entries) == 1
    assert entries[0].symbol == "AAA"
    assert entries[0].instrument_key == "NSE_EQ|INE1"


def test_build_sector_proxy_coverage_reports_unmapped_and_available_proxy() -> None:
    classifications = {
        "AAA": {"sector": "Information Technology"},
        "BBB": {"sector": "Glass"},
    }
    resolutions = {
        symbol: run_market_context_audit.resolve_sector_proxy(row["sector"])
        for symbol, row in classifications.items()
    }

    result = run_market_context_audit.build_sector_proxy_coverage(
        classifications,
        resolutions,
        available_indices={"NIFTY_IT"},
    )

    by_sector = {row["sector"]: row for _, row in result.iterrows()}
    assert by_sector["Information Technology"]["proxy_index"] == "NIFTY_IT"
    assert bool(by_sector["Information Technology"]["proxy_available"]) is True
    assert bool(by_sector["Glass"]["unmapped"]) is True


def test_feature_null_summary_counts_expected_features() -> None:
    features = pd.DataFrame(
        {
            "ret_5d": [None, 0.1],
            "benchmark_ret_5d": [None, 0.05],
            "rel_benchmark_ret_5d": [None, 0.05],
            "sector_ret_5d": [None, None],
        }
    )

    result = run_market_context_audit.build_feature_null_summary(features, (5,))

    nulls = {row["feature"]: row["null_count"] for _, row in result.iterrows()}
    assert nulls["ret_5d"] == 1
    assert nulls["sector_ret_5d"] == 2


def test_cli_wires_arguments_to_run_audit(monkeypatch, tmp_path, capsys) -> None:
    observed = {}

    monkeypatch.setattr(run_market_context_audit, "_get_database_engine", lambda: "engine")

    def fake_run_audit(engine, **kwargs):
        observed["engine"] = engine
        observed.update(kwargs)
        return {"symbols_requested": 1, "symbols_processed": 1}

    monkeypatch.setattr(run_market_context_audit, "run_audit", fake_run_audit)

    exit_code = run_market_context_audit.main(
        [
            "--symbols-file",
            "symbols.csv",
            "--classification-file",
            "classification.csv",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-02-01",
            "--benchmark-index",
            "NIFTY_50",
            "--windows",
            "5,20",
            "--limit",
            "10",
            "--output-dir",
            str(tmp_path),
            "--fallback-unmapped-sector-to-benchmark",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert observed["engine"] == "engine"
    assert observed["start_date"] == date(2024, 1, 1)
    assert observed["end_date"] == date(2024, 2, 1)
    assert observed["benchmark_index"] == "NIFTY_50"
    assert observed["windows"] == (5, 20)
    assert observed["limit"] == 10
    assert observed["fallback_unmapped_sector_to_benchmark"] is True
    assert payload["symbols_processed"] == 1


def test_run_audit_writes_compact_outputs_with_fakes(monkeypatch, tmp_path) -> None:
    symbols_file = tmp_path / "symbols.csv"
    classification_file = tmp_path / "classification.csv"
    output_dir = tmp_path / "out"
    symbols_file.write_text("symbol,instrument_key\nAAA,NSE_EQ|AAA\n", encoding="utf-8")
    classification_file.write_text(
        "symbol,sector,market_cap_bucket\nAAA,Information Technology,unknown\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        run_market_context_audit,
        "SQLAlchemyDailyOHLCVLoader",
        lambda *args, **kwargs: FakeStockLoader(),
    )
    monkeypatch.setattr(
        run_market_context_audit,
        "SQLAlchemyMarketIndexDailyReader",
        lambda *args, **kwargs: FakeIndexReader(),
    )

    summary = run_market_context_audit.run_audit(
        object(),
        symbols_file=symbols_file,
        classification_file=classification_file,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 10),
        benchmark_index="NIFTY_500",
        windows=(5,),
        output_dir=output_dir,
    )

    assert summary["symbols_requested"] == 1
    assert summary["symbols_processed"] == 1
    assert (output_dir / "summary.json").exists()
    assert (output_dir / "market_context_sample.csv").exists()
    assert (output_dir / "sector_proxy_coverage.csv").exists()


class FakeStockLoader:
    def load_instrument_key(self, instrument_key, start_date, end_date):
        return _frame([100, 101, 102, 103, 104, 105, 106])

    def load_symbol(self, symbol, start_date, end_date):
        return _frame([100, 101, 102, 103, 104, 105, 106])


class FakeIndexReader:
    def load(self, index_symbol, start_date, end_date):
        return FakeIndexResult(_frame([200, 201, 202, 203, 204, 205, 206]))


class FakeIndexResult:
    def __init__(self, frame):
        self.frame = frame


def _frame(values):
    return pd.DataFrame(
        {
            "session_date": pd.date_range("2024-01-01", periods=len(values), freq="D"),
            "close": values,
            "open": values,
            "high": values,
            "low": values,
            "volume": [1000] * len(values),
        }
    )
