from __future__ import annotations

import pandas as pd

from veridian_quant.v2.analysis.cross_strategy_risk_diagnostic_audit import (
    build_drawdown_state_performance,
    build_gap_exit_stress_summary,
    build_liquidity_bucket_performance,
    build_rolling_r_expectancy_summary,
    build_symbol_concentration_summary,
    load_classification,
    load_strategy_risk_report,
    load_universe,
    run_cross_strategy_risk_diagnostic_audit,
)


def test_liquidity_join_and_bucket_performance(tmp_path) -> None:
    dirs, universe_csv, classification_csv = _make_audit_inputs(tmp_path)
    result = run_cross_strategy_risk_diagnostic_audit(
        dirs,
        universe_csv=universe_csv,
        classification_csv=classification_csv,
        output_dir=tmp_path / "out",
    )

    coverage = pd.read_csv(result.outputs["risk_join_coverage_by_strategy.csv"])
    liquidity = pd.read_csv(result.outputs["liquidity_bucket_performance.csv"])
    s1_coverage = coverage[coverage["strategy"] == "S1"].iloc[0]
    s1_high = liquidity[
        (liquidity["strategy"] == "S1")
        & (liquidity["liquidity_bucket"] == "HIGH")
    ].iloc[0]

    assert s1_coverage["universe_join_coverage_pct"] == 100.0
    assert s1_coverage["classification_join_coverage_pct"] == 100.0
    assert s1_high["trades"] == 2
    assert s1_high["net_pnl"] == 30.0


def test_symbol_concentration(tmp_path) -> None:
    dirs, _, _ = _make_audit_inputs(tmp_path)
    reports = [load_strategy_risk_report(label, path) for label, path in dirs.items()]

    concentration = build_symbol_concentration_summary(reports)
    s1 = concentration[concentration["strategy"] == "S1"].iloc[0]

    assert s1["trades"] == 4
    assert s1["unique_symbols"] == 3
    assert s1["best_symbol_pnl"] == 30.0
    assert s1["worst_symbol_pnl"] == -20.0


def test_gap_exit_summary(tmp_path) -> None:
    dirs, universe_csv, _ = _make_audit_inputs(tmp_path)
    reports = [load_strategy_risk_report(label, path) for label, path in dirs.items()]
    universe = load_universe(universe_csv)

    gap = build_gap_exit_stress_summary(reports, universe)
    s1_stop_gap = gap[
        (gap["strategy"] == "S1") & (gap["exit_reason"] == "stop_gap_hit")
    ].iloc[0]

    assert s1_stop_gap["trades"] == 1
    assert s1_stop_gap["net_pnl"] == -20.0
    assert s1_stop_gap["share_of_strategy_trades_pct"] == 25.0


def test_drawdown_state_mapping(tmp_path) -> None:
    dirs, _, _ = _make_audit_inputs(tmp_path)
    reports = [load_strategy_risk_report(label, path) for label, path in dirs.items()]

    drawdown = build_drawdown_state_performance(reports)
    s1_mild = drawdown[
        (drawdown["strategy"] == "S1")
        & (drawdown["drawdown_bucket_at_entry"] == "mild_drawdown")
    ].iloc[0]

    assert s1_mild["trades"] >= 1
    assert s1_mild["net_pnl"] == 5.0


def test_rolling_r_uses_previous_trades_only(tmp_path) -> None:
    dirs, _, _ = _make_audit_inputs(tmp_path, trade_count=25)
    reports = [load_strategy_risk_report(label, path) for label, path in dirs.items()]

    rolling = build_rolling_r_expectancy_summary(reports)
    s1 = rolling[rolling["strategy"] == "S1"]

    assert "insufficient_history" in set(s1["rolling_r_bucket"])
    assert "positive" in set(s1["rolling_r_bucket"])
    positive = s1[s1["rolling_r_bucket"] == "positive"].iloc[0]
    assert positive["trades"] == 5


def test_missing_optional_columns_do_not_crash(tmp_path) -> None:
    dirs, universe_csv, classification_csv = _make_audit_inputs(tmp_path)
    s1_context = dirs["S1"] / "trade_signal_context.csv"
    frame = pd.read_csv(s1_context).drop(columns=["stock_gap_from_prev_close_pct"])
    frame.to_csv(s1_context, index=False)

    result = run_cross_strategy_risk_diagnostic_audit(
        dirs,
        universe_csv=universe_csv,
        classification_csv=classification_csv,
        output_dir=tmp_path / "out",
    )
    pre_gap = pd.read_csv(result.outputs["pre_entry_gap_context_summary.csv"])

    assert "unknown" in set(pre_gap["pre_entry_gap_bucket"])


def test_full_run_writes_required_outputs(tmp_path) -> None:
    dirs, universe_csv, classification_csv = _make_audit_inputs(tmp_path)

    result = run_cross_strategy_risk_diagnostic_audit(
        dirs,
        universe_csv=universe_csv,
        classification_csv=classification_csv,
        output_dir=tmp_path / "out",
    )

    assert "risk_diagnostic_readme.txt" in result.outputs
    assert result.outputs["risk_input_inventory.csv"].exists()
    assert result.outputs["capacity_pressure_by_year.csv"].exists()


def _make_audit_inputs(tmp_path, trade_count: int = 4):
    dirs = {label: tmp_path / label.lower() for label in ("S1", "S2", "S3", "S4", "S5")}
    for label, path in dirs.items():
        path.mkdir()
        _write_strategy_folder(label, path, trade_count=trade_count)

    universe_csv = tmp_path / "universe.csv"
    universe_csv.write_text(
        "\n".join(
            [
                "symbol,liquidity_bucket,liquidity_metric",
                "AAA,HIGH,1000",
                "BBB,LOW,10",
                "CCC,MID,100",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    classification_csv = tmp_path / "classification.csv"
    classification_csv.write_text(
        "\n".join(
            [
                "symbol,sector,market_cap_bucket,classification_mode,source",
                "AAA,IT,unknown,static_current,test",
                "BBB,BANK,unknown,static_current,test",
                "CCC,PHARMA,unknown,static_current,test",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return dirs, universe_csv, classification_csv


def _write_strategy_folder(label: str, path, trade_count: int) -> None:
    rows = []
    context_rows = []
    equity_rows = ["date,equity,realized_pnl"]
    rejected_rows = ["symbol,signal_date,strategy_name,reason"]
    symbols = ["AAA", "AAA", "BBB", "CCC"]
    pnls = [10, 20, -20, -5]
    exits = ["target_hit", "target_gap_hit", "stop_gap_hit", "time_stop"]
    for idx in range(trade_count):
        symbol = symbols[idx % len(symbols)]
        pnl = pnls[idx % len(pnls)]
        exit_reason = exits[idx % len(exits)]
        day = idx + 1
        entry_date = f"2024-01-{day + 1:02d}"
        exit_date = f"2024-01-{day + 2:02d}"
        risk = 100
        rows.append(
            f"{label.lower()}{idx},{symbol},{entry_date},{exit_date},1,90,120,10,{risk},200,2,{pnl},{pnl / 100},1,{pnl},{pnl / 100},{exit_reason}"
        )
        context_rows.append(
            f"{label.lower()}{idx},{symbol},{label},{entry_date},{entry_date},{exit_date},{exit_reason},{pnl},{pnl / risk},100,110,90,120,{risk},2,{[-4,-2,0,2,4][idx % 5]},{[1,2,3,4,5][idx % 5]},{idx},{[-6,-2,1,6][idx % 4]}"
        )
        equity = 1000 if idx == 0 else 950 + idx * 10
        equity_rows.append(f"2024-01-{day:02d},{equity},{equity - 1000}")
        rejected_rows.append(f"{symbol},2024-01-{day:02d},{label},PORTFOLIO_CAPACITY_FULL")
        rejected_rows.append(f"{symbol},2024-01-{day:02d},{label},ACTIVE_SYMBOL_TRADE_EXISTS")

    trade_header = (
        "trade_id,symbol,entry_date,exit_date,quantity,stop_loss,target_price,"
        "per_share_risk,initial_risk_amount,planned_reward_amount,reward_risk_ratio,"
        "gross_pnl,gross_return_pct,total_cost,net_pnl,net_return_pct,exit_reason"
    )
    trade_text = trade_header + "\n" + "\n".join(rows) + "\n"
    (path / "trade_log.csv").write_text(trade_text, encoding="utf-8")
    (path / "trade_pnl_log.csv").write_text(trade_text, encoding="utf-8")
    (path / "equity_curve.csv").write_text("\n".join(equity_rows) + "\n", encoding="utf-8")
    (path / "trade_signal_context.csv").write_text(
        (
            "trade_id,symbol,strategy_name,signal_date,entry_date,exit_date,exit_reason,"
            "net_pnl,r_multiple,entry_price,exit_price,stop_loss,target_price,"
            "initial_risk_amount,reward_risk_ratio,stock_gap_from_prev_close_pct,"
            "stock_atr14_pct,stock_atr14_change_5d_pct,nifty_return_20d_pct\n"
            + "\n".join(context_rows)
            + "\n"
        ),
        encoding="utf-8",
    )
    (path / "rejected_signals.csv").write_text("\n".join(rejected_rows) + "\n", encoding="utf-8")
    (path / "rejection_summary.csv").write_text(
        "reason,count\nPORTFOLIO_CAPACITY_FULL,4\nACTIVE_SYMBOL_TRADE_EXISTS,4\n",
        encoding="utf-8",
    )
    _write_minimal_artifacts(path)


def _write_minimal_artifacts(path) -> None:
    for name, content in {
        "symbol_summary.csv": "symbol,trades,net_pnl\nAAA,2,30\n",
        "yearly_summary.csv": "year,trades,net_pnl\n2024,4,5\n",
        "exit_reason_summary.csv": "exit_reason,trades,net_pnl\nstop_gap_hit,1,-20\n",
        "r_multiple_summary.csv": "trades_with_r,average_r\n4,0.0125\n",
        "r_multiple_by_symbol.csv": "symbol,average_r\nAAA,0.15\n",
        "r_multiple_by_symbol_year.csv": "symbol,year,average_r\nAAA,2024,0.15\n",
        "all_signal_opportunity_log.csv": "symbol,signal_date,signal_status\n",
        "accepted_vs_rejected_signal_summary.csv": "signal_group,signal_count\n",
    }.items():
        (path / name).write_text(content, encoding="utf-8")
