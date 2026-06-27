from __future__ import annotations

import json

import pandas as pd

from veridian_quant.v2.analysis.pre_registered_confirmation_robustness_audit import (
    build_s2_trade_confirmation_detail,
    load_strategy_report,
    run_pre_registered_confirmation_robustness_audit,
    session_lookback_start,
)


def test_trading_session_lookback_skips_weekends_and_non_trading_dates() -> None:
    sessions = pd.to_datetime(["2024-01-05", "2024-01-08", "2024-01-10"])

    assert session_lookback_start(pd.Timestamp("2024-01-10"), 1, sessions) == pd.Timestamp("2024-01-08")
    assert session_lookback_start(pd.Timestamp("2024-01-10"), 2, sessions) == pd.Timestamp("2024-01-05")


def test_session_lookback_confirmation_uses_sessions_not_calendar_days(tmp_path) -> None:
    dirs = _make_strategy_dirs(tmp_path)
    reports = {label: load_strategy_report(label, path) for label, path in dirs.items()}
    sessions = pd.to_datetime(["2024-01-05", "2024-01-08", "2024-01-10"])

    detail = build_s2_trade_confirmation_detail(
        reports,
        session_dates=sessions,
        lookback_sessions=(1,),
        future_diagnostic_sessions=1,
    )

    aaa = detail[(detail["symbol"] == "AAA") & (detail["lookback_sessions"] == 1)].iloc[0]
    assert bool(aaa["confirmed_by_s4"]) is True
    assert bool(aaa["confirmed_by_any"]) is True
    assert aaa["lookback_start_session"] == "2024-01-08"
    assert aaa["sessions_since_latest_confirmation"] == 1


def test_same_day_zero_session_confirmation_only(tmp_path) -> None:
    dirs = _make_strategy_dirs(tmp_path)
    result = run_pre_registered_confirmation_robustness_audit(
        dirs,
        output_dir=tmp_path / "out",
        lookback_sessions=(0, 1),
        future_diagnostic_sessions=1,
    )

    detail = pd.read_csv(result.outputs["s2_trade_confirmation_detail.csv"])
    zero = detail[(detail["symbol"] == "AAA") & (detail["lookback_sessions"] == 0)].iloc[0]
    one = detail[(detail["symbol"] == "AAA") & (detail["lookback_sessions"] == 1)].iloc[0]

    assert bool(zero["confirmed_by_s4"]) is False
    assert bool(one["confirmed_by_s4"]) is True


def test_future_confirmations_are_diagnostic_only(tmp_path) -> None:
    dirs = _make_strategy_dirs(tmp_path)
    result = run_pre_registered_confirmation_robustness_audit(
        dirs,
        output_dir=tmp_path / "out",
        lookback_sessions=(0, 1),
        future_diagnostic_sessions=1,
    )

    detail = pd.read_csv(result.outputs["s2_trade_confirmation_detail.csv"])
    bbb = detail[(detail["symbol"] == "BBB") & (detail["lookback_sessions"] == 1)].iloc[0]
    future = pd.read_csv(result.outputs["future_diagnostic_confirmation_summary.csv"])

    assert bool(bbb["confirmed_by_any"]) is False
    assert bbb["future_diagnostic_confirmation_count"] == 1
    assert bbb["future_diagnostic_confirming_strategies"] == "S3"
    assert "Diagnostic only" in future.loc[0, "notes"]


def test_outputs_and_pre_registered_rules(tmp_path) -> None:
    dirs = _make_strategy_dirs(tmp_path)
    result = run_pre_registered_confirmation_robustness_audit(
        dirs,
        output_dir=tmp_path / "out",
        lookback_sessions=(0, 1, 3, 5),
    )

    expected = {
        "phase_35c_metadata.json",
        "phase_35c_pre_registered_rules.json",
        "strategy_report_inventory.csv",
        "s2_confirmation_by_lookback.csv",
        "s2_confirmation_by_strategy_and_lookback.csv",
        "s2_confirmation_by_count_bucket_and_lookback.csv",
        "s2_confirmation_by_year_and_lookback.csv",
        "s2_confirmation_by_symbol_and_lookback.csv",
        "s2_trade_confirmation_detail.csv",
        "future_diagnostic_confirmation_summary.csv",
        "robustness_readme.txt",
    }
    assert expected.issubset(set(result.outputs))
    rules = json.loads(result.outputs["phase_35c_pre_registered_rules.json"].read_text(encoding="utf-8"))
    metadata = json.loads(result.outputs["phase_35c_metadata.json"].read_text(encoding="utf-8"))
    by_strategy = pd.read_csv(result.outputs["s2_confirmation_by_strategy_and_lookback.csv"])

    assert rules["primary_candidate"] == "S2 confirmed by S4"
    assert "no weights or capital allocation" in rules["constraints"]
    assert metadata["session_calendar_source"].startswith("sorted union")
    assert "sample_size_warning" in by_strategy.columns


def _make_strategy_dirs(tmp_path):
    dirs = {label: tmp_path / label.lower() for label in ("S1", "S2", "S3", "S4", "S5")}
    for label, path in dirs.items():
        path.mkdir()
        _write_common_files(label, path)
    return dirs


def _write_common_files(label: str, path) -> None:
    signals = {
        "S1": "symbol,generated_on\nCCC,2024-01-08\n",
        "S2": "symbol,generated_on\nAAA,2024-01-10\nBBB,2024-01-10\n",
        "S3": "symbol,generated_on\nBBB,2024-01-11\n",
        "S4": "symbol,generated_on\nAAA,2024-01-08\nDDD,2024-01-10\n",
        "S5": "symbol,generated_on\nEEE,2024-01-10\n",
    }
    trades = {
        "S1": "trade_id,symbol,entry_date,exit_date,exit_reason,net_pnl\ns1a,CCC,2024-01-10,2024-01-12,target,1\n",
        "S2": (
            "trade_id,symbol,entry_date,exit_date,exit_reason,net_pnl\n"
            "s2a,AAA,2024-01-10,2024-01-12,target,100\n"
            "s2b,BBB,2024-01-10,2024-01-12,stop,-50\n"
        ),
        "S3": "trade_id,symbol,entry_date,exit_date,exit_reason,net_pnl\ns3a,BBB,2024-01-11,2024-01-12,target,5\n",
        "S4": "trade_id,symbol,entry_date,exit_date,exit_reason,net_pnl\ns4a,AAA,2024-01-08,2024-01-12,target,10\n",
        "S5": "trade_id,symbol,entry_date,exit_date,exit_reason,net_pnl\ns5a,EEE,2024-01-10,2024-01-12,target,2\n",
    }
    equity = (
        "date,equity\n"
        "2024-01-05,1000\n"
        "2024-01-08,1000\n"
        "2024-01-10,1000\n"
        "2024-01-11,1000\n"
    )
    (path / "signal_log.csv").write_text(signals[label], encoding="utf-8")
    (path / "trade_log.csv").write_text(trades[label], encoding="utf-8")
    (path / "trade_pnl_log.csv").write_text(trades[label], encoding="utf-8")
    (path / "equity_curve.csv").write_text(equity, encoding="utf-8")
