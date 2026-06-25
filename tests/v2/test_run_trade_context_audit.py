from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from veridian_quant.v2 import run_trade_context_audit


def test_cli_wires_arguments_to_run_audit(monkeypatch, tmp_path, capsys) -> None:
    trade_log = tmp_path / "trades.csv"
    trade_log.write_text("symbol,entry_date\nAAA,2024-01-05\n", encoding="utf-8")
    observed = {}

    monkeypatch.setattr(run_trade_context_audit, "_get_database_engine", lambda: "engine")

    def fake_run_audit(engine, **kwargs):
        observed["engine"] = engine
        observed.update(kwargs)
        return {"trade_count": len(kwargs["trades"]), "benchmark_index": kwargs["benchmark_index"]}

    monkeypatch.setattr(run_trade_context_audit, "run_audit", fake_run_audit)

    exit_code = run_trade_context_audit.main(
        [
            "--trade-log",
            str(trade_log),
            "--output-dir",
            str(tmp_path / "out"),
            "--symbols-file",
            "symbols.csv",
            "--classification-file",
            "classification.csv",
            "--benchmark-index",
            "NIFTY_50",
            "--windows",
            "1,2",
            "--strategy-name",
            "demo",
            "--limit",
            "1",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert observed["engine"] == "engine"
    assert observed["benchmark_index"] == "NIFTY_50"
    assert observed["windows"] == (1, 2)
    assert observed["strategy_name"] == "demo"
    assert payload["trade_count"] == 1


def test_run_audit_writes_expected_outputs_with_fakes(monkeypatch, tmp_path) -> None:
    symbols_file = tmp_path / "symbols.csv"
    classification_file = tmp_path / "classification.csv"
    output_dir = tmp_path / "out"
    symbols_file.write_text("symbol,instrument_key\nAAA,NSE_EQ|AAA\n", encoding="utf-8")
    classification_file.write_text(
        "symbol,sector,market_cap_bucket\nAAA,Information Technology,unknown\n",
        encoding="utf-8",
    )
    trades = pd.DataFrame(
        {
            "symbol": ["AAA"],
            "entry_date": ["2024-01-08"],
            "net_pnl": [100.0],
            "r_multiple": [1.0],
            "exit_reason": ["target_hit"],
        }
    )

    monkeypatch.setattr(
        run_trade_context_audit,
        "SQLAlchemyDailyOHLCVLoader",
        lambda *args, **kwargs: FakeStockLoader(),
    )
    monkeypatch.setattr(
        run_trade_context_audit,
        "SQLAlchemyMarketIndexDailyReader",
        lambda *args, **kwargs: FakeIndexReader(),
    )

    summary = run_trade_context_audit.run_audit(
        object(),
        trades=trades,
        symbols_file=symbols_file,
        classification_file=classification_file,
        benchmark_index="NIFTY_500",
        windows=(1, 2),
        output_dir=output_dir,
    )

    assert summary["trade_count"] == 1
    assert summary["symbols_with_stock_context"] == 1
    for name in (
        "summary.json",
        "trade_context_annotated.csv",
        "context_bucket_summary.csv",
        "exit_reason_by_context.csv",
        "sector_proxy_trade_coverage.csv",
        "missing_context_summary.csv",
        "r_multiple_by_context.csv",
        "pnl_by_context.csv",
    ):
        assert (output_dir / name).exists()


class FakeStockLoader:
    def load_instrument_key(self, instrument_key, start_date, end_date):
        return _stock_frame()

    def load_symbol(self, symbol, start_date, end_date):
        return _stock_frame()


class FakeIndexReader:
    def load(self, index_symbol, start_date, end_date):
        return FakeIndexResult(_index_frame())


class FakeIndexResult:
    def __init__(self, frame):
        self.frame = frame


def _stock_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-05", "2024-01-06", "2024-01-08"]),
            "open": [10, 11, 12],
            "high": [10, 11, 12],
            "low": [10, 11, 12],
            "close": [10, 11, 12],
            "volume": [100, 100, 100],
        }
    )


def _index_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "session_date": pd.to_datetime(["2024-01-05", "2024-01-06", "2024-01-08"]),
            "close": [100, 101, 102],
        }
    )