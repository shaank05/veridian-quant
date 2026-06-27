from __future__ import annotations

import json

import pandas as pd
import pytest

from veridian_quant.v2.analysis.cross_strategy_overlap_audit import (
    build_drawdown_overlap_summary,
    build_equity_correlation_summary,
    load_strategy_report,
    run_cross_strategy_overlap_audit,
)


def test_loads_strategy_folders_and_inventory_detects_optional_files(tmp_path) -> None:
    dirs = _make_strategy_dirs(tmp_path)
    (dirs["S2"] / "all_signal_opportunity_log.csv").write_text(
        "symbol,generated_on\nAAA,2024-01-09\n",
        encoding="utf-8",
    )
    (dirs["S2"] / "counterfactual_rejected_trade_summary.csv").write_text(
        "trades,net_pnl,win_rate,profit_factor\n3,12,0.67,2.0\n",
        encoding="utf-8",
    )

    result = run_cross_strategy_overlap_audit(dirs, output_dir=tmp_path / "out", overlap_scope="all")

    inventory = pd.read_csv(result.outputs["strategy_report_inventory.csv"])
    s2 = inventory[inventory["strategy"] == "S2"].iloc[0]
    assert bool(s2["has_signal_log"])
    assert bool(s2["has_all_signal_opportunity_log"])
    assert s2["signal_rows"] == 2
    metadata = json.loads(result.outputs["overlap_audit_metadata.json"].read_text(encoding="utf-8"))
    assert metadata["counterfactual_schema_support"]["S2"] is True
    assert "not an ensemble backtest" in metadata["caveat"]


def test_same_day_signal_and_entry_overlap_outputs(tmp_path) -> None:
    dirs = _make_strategy_dirs(tmp_path)
    result = run_cross_strategy_overlap_audit(dirs, output_dir=tmp_path / "out", overlap_scope="all")

    signal_overlap = pd.read_csv(result.outputs["signal_overlap_same_day.csv"])
    entry_overlap = pd.read_csv(result.outputs["entry_overlap_same_day.csv"])
    pair_summary = pd.read_csv(result.outputs["strategy_pair_overlap_summary.csv"])

    assert signal_overlap.loc[0, "symbol"] == "AAA"
    assert signal_overlap.loc[0, "strategy_count"] >= 2
    assert entry_overlap.loc[0, "symbol"] == "AAA"
    s1_s2 = pair_summary[(pair_summary["strategy_a"] == "S1") & (pair_summary["strategy_b"] == "S2")].iloc[0]
    assert s1_s2["same_day_entry_overlap_count"] == 1
    assert s1_s2["anchor_prior_confirmation_count"] == 1


def test_prior_confirmation_counted_future_is_diagnostic_only(tmp_path) -> None:
    dirs = _make_strategy_dirs(tmp_path)
    result = run_cross_strategy_overlap_audit(
        dirs,
        output_dir=tmp_path / "out",
        overlap_scope="executed_trades",
        anchor_strategy="S2",
        lookback_days=3,
        diagnostic_window_days=3,
    )

    annotated = pd.read_csv(result.outputs["anchor_confirmed_vs_unconfirmed.csv"])
    aaa = annotated[annotated["symbol"] == "AAA"].iloc[0]
    bbb = annotated[annotated["symbol"] == "BBB"].iloc[0]

    assert bool(aaa["confirmed_by_any_prior_signal"]) is True
    assert aaa["confirming_strategy_count"] == 1
    assert aaa["confirming_strategies"] == "S1"
    assert bool(bbb["confirmed_by_any_prior_signal"]) is False
    assert bbb["diagnostic_future_confirmation_count"] == 1
    assert bbb["diagnostic_future_confirming_strategies"] == "S3"


def test_anchor_confirmation_aggregation(tmp_path) -> None:
    dirs = _make_strategy_dirs(tmp_path)
    result = run_cross_strategy_overlap_audit(dirs, output_dir=tmp_path / "out", overlap_scope="executed_trades")

    summary = pd.read_csv(result.outputs["anchor_confirmation_summary.csv"])
    confirmed = summary[summary["group"] == "confirmed"].iloc[0]
    unconfirmed = summary[summary["group"] == "unconfirmed"].iloc[0]
    by_strategy = pd.read_csv(result.outputs["anchor_confirmation_by_strategy.csv"])
    by_year = pd.read_csv(result.outputs["anchor_confirmation_by_year.csv"])
    by_symbol = pd.read_csv(result.outputs["anchor_confirmation_by_symbol.csv"])

    assert confirmed["trades"] == 1
    assert confirmed["net_pnl"] == 100.0
    assert unconfirmed["trades"] == 1
    assert unconfirmed["net_pnl"] == -50.0
    assert by_strategy.loc[0, "confirming_strategy"] == "S1"
    assert by_year.loc[0, "year"] == 2024
    assert set(by_symbol["symbol"]) == {"AAA", "BBB"}


def test_scope_outputs_are_separate(tmp_path) -> None:
    dirs = _make_strategy_dirs(tmp_path)

    signal_result = run_cross_strategy_overlap_audit(
        dirs,
        output_dir=tmp_path / "signals",
        overlap_scope="signals",
    )
    executed_result = run_cross_strategy_overlap_audit(
        dirs,
        output_dir=tmp_path / "executed",
        overlap_scope="executed_trades",
    )
    counterfactual_result = run_cross_strategy_overlap_audit(
        dirs,
        output_dir=tmp_path / "counterfactual",
        overlap_scope="counterfactual",
    )

    assert "signal_overlap_same_day.csv" in signal_result.outputs
    assert "anchor_confirmed_vs_unconfirmed.csv" not in signal_result.outputs
    assert "anchor_confirmed_vs_unconfirmed.csv" in executed_result.outputs
    assert "signal_overlap_same_day.csv" not in executed_result.outputs
    assert "counterfactual_inventory.csv" in counterfactual_result.outputs
    assert "entry_overlap_same_day.csv" not in counterfactual_result.outputs


def test_counterfactual_inventory_supported_and_unsupported_schemas(tmp_path) -> None:
    dirs = _make_strategy_dirs(tmp_path)
    (dirs["S1"] / "counterfactual_by_symbol.csv").write_text(
        "symbol,net_pnl\nAAA,10\n",
        encoding="utf-8",
    )
    (dirs["S2"] / "counterfactual_by_symbol.csv").write_text(
        "ticker,net_pnl\nBBB,5\n",
        encoding="utf-8",
    )
    result = run_cross_strategy_overlap_audit(dirs, output_dir=tmp_path / "out", overlap_scope="counterfactual")

    inventory = pd.read_csv(result.outputs["counterfactual_inventory.csv"])
    s1 = inventory[inventory["strategy"] == "S1"].iloc[0]
    s2 = inventory[inventory["strategy"] == "S2"].iloc[0]
    combined = pd.read_csv(result.outputs["counterfactual_by_symbol_combined.csv"])
    summary = pd.read_csv(result.outputs["counterfactual_summary_by_strategy.csv"])

    assert bool(s1["schema_supported"]) is True
    assert bool(s2["schema_supported"]) is False
    assert "missing symbol" in s2["limitations"]
    assert "realized" in summary.loc[0, "notes"]
    assert "not realized portfolio performance" in "|".join(combined["notes"].astype(str))


def test_equity_correlation_and_drawdown_overlap(tmp_path) -> None:
    dirs = _make_strategy_dirs(tmp_path)
    reports = [load_strategy_report(label, path) for label, path in dirs.items()]

    corr = build_equity_correlation_summary(reports)
    drawdowns = build_drawdown_overlap_summary(reports)

    s1_s2_corr = corr[(corr["strategy_a"] == "S1") & (corr["strategy_b"] == "S2")].iloc[0]
    pair_drawdown = drawdowns[
        (drawdowns["row_type"] == "pair") & (drawdowns["strategy_a"] == "S1") & (drawdowns["strategy_b"] == "S2")
    ].iloc[0]
    s1_drawdown = drawdowns[(drawdowns["row_type"] == "strategy") & (drawdowns["strategy"] == "S1")].iloc[0]

    assert s1_s2_corr["aligned_days"] >= 2
    assert pd.notna(s1_s2_corr["return_correlation"])
    assert s1_drawdown["drawdown_days"] >= 1
    assert pair_drawdown["overlapping_drawdown_days"] >= 1


def test_missing_optional_file_records_limitation(tmp_path) -> None:
    dirs = _make_strategy_dirs(tmp_path)
    result = run_cross_strategy_overlap_audit(dirs, output_dir=tmp_path / "out", overlap_scope="all")

    metadata = json.loads(result.outputs["overlap_audit_metadata.json"].read_text(encoding="utf-8"))
    assert any("missing optional files" in item for item in metadata["limitations"]["S1"])


def test_missing_required_symbol_or_date_column_fails_clearly(tmp_path) -> None:
    strategy_dir = tmp_path / "bad"
    strategy_dir.mkdir()
    (strategy_dir / "signal_log.csv").write_text("generated_on\n2024-01-01\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing required column"):
        load_strategy_report("S1", strategy_dir)


def _make_strategy_dirs(tmp_path):
    dirs = {label: tmp_path / label.lower() for label in ("S1", "S2", "S3", "S4", "S5")}
    for label, path in dirs.items():
        path.mkdir()
        _write_common_files(label, path)
    return dirs


def _write_common_files(label: str, path) -> None:
    signal_rows = {
        "S1": "symbol,generated_on\nAAA,2024-01-08\nCCC,2024-01-09\n",
        "S2": "symbol,generated_on\nAAA,2024-01-08\nBBB,2024-01-10\n",
        "S3": "symbol,generated_on\nFFF,2024-01-08\nBBB,2024-01-12\n",
        "S4": "symbol,generated_on\nDDD,2024-01-08\n",
        "S5": "symbol,generated_on\nEEE,2024-01-08\n",
    }
    trade_rows = {
        "S1": "trade_id,symbol,entry_date,exit_date,exit_reason,net_pnl\ns1a,AAA,2024-01-10,2024-01-12,target,20\n",
        "S2": (
            "trade_id,symbol,entry_date,exit_date,exit_reason,net_pnl\n"
            "s2a,AAA,2024-01-10,2024-01-12,target,100\n"
            "s2b,BBB,2024-01-10,2024-01-13,stop,-50\n"
        ),
        "S3": "trade_id,symbol,entry_date,exit_date,exit_reason,net_pnl\ns3a,AAA,2024-01-11,2024-01-12,target,5\n",
        "S4": "trade_id,symbol,entry_date,exit_date,exit_reason,net_pnl\ns4a,DDD,2024-01-10,2024-01-11,stop,-1\n",
        "S5": "trade_id,symbol,entry_date,exit_date,exit_reason,net_pnl\ns5a,EEE,2024-01-10,2024-01-11,target,1\n",
    }
    equity_rows = {
        "S1": "date,equity,realized_pnl\n2024-01-09,1000,0\n2024-01-10,900,-100\n2024-01-11,1100,200\n",
        "S2": "date,equity,realized_pnl\n2024-01-09,1000,0\n2024-01-10,950,-50\n2024-01-11,1050,100\n",
        "S3": "date,equity,realized_pnl\n2024-01-09,1000,0\n2024-01-10,1010,10\n2024-01-11,990,-20\n",
        "S4": "date,equity,realized_pnl\n2024-01-09,1000,0\n2024-01-10,1005,5\n2024-01-11,1001,-4\n",
        "S5": "date,equity,realized_pnl\n2024-01-09,1000,0\n2024-01-10,999,-1\n2024-01-11,998,-1\n",
    }
    (path / "signal_log.csv").write_text(signal_rows[label], encoding="utf-8")
    (path / "trade_log.csv").write_text(trade_rows[label], encoding="utf-8")
    (path / "trade_pnl_log.csv").write_text(trade_rows[label], encoding="utf-8")
    (path / "equity_curve.csv").write_text(equity_rows[label], encoding="utf-8")
