"""Tests for S1 baseline universe-size comparison reports."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

from veridian_quant.v2.reporting.baseline_universe_comparison import (
    compare_baseline_universe_sizes,
)


def test_summary_comparison_file_is_created(tmp_path: Path) -> None:
    dirs = _write_report_dirs(tmp_path)

    result = _run_compare(dirs, tmp_path / "out")

    assert result.paths["summary_comparison"].exists()
    assert list(result.summary["universe_label"]) == ["research100", "research200"]


def test_delta_file_computes_200_minus_100(tmp_path: Path) -> None:
    dirs = _write_report_dirs(tmp_path)

    result = _run_compare(dirs, tmp_path / "out")
    row = result.delta.loc[result.delta["metric"] == "total_net_pnl"].iloc[0]

    assert row["research100_value"] == 100.0
    assert row["research200_value"] == 250.0
    assert row["absolute_delta"] == 150.0


def test_signal_percentages_are_computed(tmp_path: Path) -> None:
    dirs = _write_report_dirs(tmp_path)

    result = _run_compare(dirs, tmp_path / "out")
    row = result.summary.loc[result.summary["universe_label"] == "research100"].iloc[0]

    assert row["accepted_signal_pct"] == 20.0
    assert row["rejected_signal_pct"] == 80.0


def test_yearly_comparison_is_created(tmp_path: Path) -> None:
    dirs = _write_report_dirs(tmp_path)

    result = _run_compare(dirs, tmp_path / "out")

    assert result.paths["yearly_comparison"].exists()
    assert list(result.yearly["year"]) == [2020, 2021]
    assert result.yearly.loc[result.yearly["year"] == 2021, "delta_net_pnl"].iloc[0] == 80.0


def test_exit_reason_comparison_separates_profit_and_loss(tmp_path: Path) -> None:
    dirs = _write_report_dirs(tmp_path)

    result = _run_compare(dirs, tmp_path / "out")
    row = result.exit_reason.loc[result.exit_reason["exit_reason"] == "stop_loss_hit"].iloc[0]

    assert row["research100_gross_profit"] == 0.0
    assert row["research100_gross_loss"] == -50.0
    assert row["research200_gross_loss"] == -70.0


def test_rejection_comparison_includes_capacity_rejections(tmp_path: Path) -> None:
    dirs = _write_report_dirs(tmp_path)

    result = _run_compare(dirs, tmp_path / "out")

    reasons = set(result.rejection["rejection_reason"])
    assert "PORTFOLIO_CAPACITY_FULL" in reasons


def test_symbol_comparison_marks_symbols_in_one_or_both_reports(tmp_path: Path) -> None:
    dirs = _write_report_dirs(tmp_path)

    result = _run_compare(dirs, tmp_path / "out")
    aaa = result.symbol.loc[result.symbol["symbol"] == "AAA"].iloc[0]
    bbb = result.symbol.loc[result.symbol["symbol"] == "BBB"].iloc[0]
    ccc = result.symbol.loc[result.symbol["symbol"] == "CCC"].iloc[0]

    assert bool(aaa["in_research100"]) is True
    assert bool(aaa["in_research200"]) is True
    assert bool(bbb["in_research100"]) is True
    assert bool(bbb["in_research200"]) is False
    assert bool(ccc["in_research100"]) is False
    assert bool(ccc["in_research200"]) is True


def test_diagnostic_summary_includes_target_stop_and_time_stop_pnl(
    tmp_path: Path,
) -> None:
    dirs = _write_report_dirs(tmp_path)

    result = _run_compare(dirs, tmp_path / "out")

    metrics = set(result.diagnostic["metric"])
    assert "research100_target_net_pnl" in metrics
    assert "research100_stop_net_pnl" in metrics
    assert "research100_time_stop_net_pnl" in metrics
    assert "research200_target_net_pnl" in metrics
    assert "research200_stop_net_pnl" in metrics
    assert "research200_time_stop_net_pnl" in metrics


def test_cli_works_with_synthetic_report_folders(tmp_path: Path) -> None:
    dirs = _write_report_dirs(tmp_path)
    output_dir = tmp_path / "cli-out"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "veridian_quant.v2.compare_baseline_universe_sizes",
            "--research100-dir",
            str(dirs["research100"]),
            "--research200-dir",
            str(dirs["research200"]),
            "--output-dir",
            str(output_dir),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert (output_dir / "baseline_universe_summary_comparison.csv").exists()
    assert (output_dir / "baseline_universe_diagnostic_summary.csv").exists()


def _run_compare(dirs: dict[str, Path], output_dir: Path):
    return compare_baseline_universe_sizes(
        research100_dir=dirs["research100"],
        research200_dir=dirs["research200"],
        output_dir=output_dir,
    )


def _write_report_dirs(tmp_path: Path) -> dict[str, Path]:
    research100 = tmp_path / "research100"
    research200 = tmp_path / "research200"
    research100.mkdir()
    research200.mkdir()
    _write_report(
        research100,
        total_net_pnl=100,
        gross_profit=200,
        gross_loss=-100,
        total_trades=2,
        total_signals=10,
        total_rejections=8,
        years=[(2020, 40, 1), (2021, 60, 1)],
        exits=[
            ("target_hit", 1, 150, 150, 0),
            ("stop_loss_hit", 1, -50, 0, -50),
            ("time_stop", 0, 0, 0, 0),
        ],
        rejections=[
            ("PORTFOLIO_CAPACITY_FULL", 6),
            ("ACTIVE_SYMBOL_TRADE_EXISTS", 2),
        ],
        symbols=[("AAA", 1, 150, 150, 0), ("BBB", 1, -50, 0, -50)],
    )
    _write_report(
        research200,
        total_net_pnl=250,
        gross_profit=400,
        gross_loss=-150,
        total_trades=3,
        total_signals=20,
        total_rejections=17,
        years=[(2020, 110, 1), (2021, 140, 2)],
        exits=[
            ("target_hit", 1, 220, 220, 0),
            ("stop_loss_hit", 1, -70, 0, -70),
            ("time_stop", 1, 100, 180, -80),
        ],
        rejections=[
            ("PORTFOLIO_CAPACITY_FULL", 15),
            ("ACTIVE_SYMBOL_TRADE_EXISTS", 2),
        ],
        symbols=[("AAA", 1, 220, 220, 0), ("CCC", 2, 30, 180, -150)],
    )
    return {"research100": research100, "research200": research200}


def _write_report(
    report_dir: Path,
    total_net_pnl: float,
    gross_profit: float,
    gross_loss: float,
    total_trades: int,
    total_signals: int,
    total_rejections: int,
    years: list[tuple[int, float, int]],
    exits: list[tuple[str, int, float, float, float]],
    rejections: list[tuple[str, int]],
    symbols: list[tuple[str, int, float, float, float]],
) -> None:
    pd.DataFrame(
        [
            {
                "strategy_name": "S1_ZSCORE_MEAN_REVERSION",
                "strategy_variant": "S1_BASELINE",
                "start_date": "2020-01-01",
                "end_date": "2026-04-30",
                "starting_equity": 1000,
                "ending_equity": 1000 + total_net_pnl,
                "total_net_pnl": total_net_pnl,
                "total_return_pct": total_net_pnl / 10,
                "cagr_pct": 1.0,
                "max_drawdown_pct": 5.0,
                "total_trades": total_trades,
                "winning_trades": 1,
                "losing_trades": 1,
                "win_rate_pct": 50.0,
                "gross_profit": gross_profit,
                "gross_loss": gross_loss,
                "profit_factor": abs(gross_profit / gross_loss),
                "expectancy": total_net_pnl / total_trades,
                "average_win": gross_profit,
                "average_loss": gross_loss,
                "average_holding_days": 4.0,
                "total_signals": total_signals,
                "total_rejected_signals": total_rejections,
            }
        ]
    ).to_csv(report_dir / "summary.csv", index=False)
    pd.DataFrame(
        [
            {
                "year": year,
                "trades": trades,
                "gross_profit": max(net_pnl, 0),
                "gross_loss": min(net_pnl, 0),
                "net_pnl": net_pnl,
            }
            for year, net_pnl, trades in years
        ]
    ).to_csv(report_dir / "yearly_summary.csv", index=False)
    pd.DataFrame(
        [
            {
                "exit_reason": reason,
                "trades": trades,
                "gross_profit": profit,
                "gross_loss": loss,
                "net_pnl": net_pnl,
            }
            for reason, trades, net_pnl, profit, loss in exits
        ]
    ).to_csv(report_dir / "exit_reason_summary.csv", index=False)
    pd.DataFrame(
        [{"reason": reason, "count": count} for reason, count in rejections]
    ).to_csv(report_dir / "rejection_summary.csv", index=False)
    pd.DataFrame(
        [
            {
                "symbol": symbol,
                "trades": trades,
                "gross_profit": profit,
                "gross_loss": loss,
                "net_pnl": net_pnl,
            }
            for symbol, trades, net_pnl, profit, loss in symbols
        ]
    ).to_csv(report_dir / "symbol_summary.csv", index=False)
    pd.DataFrame(
        [{"symbol": f"SIG{idx}", "generated_on": "2020-01-01"} for idx in range(total_signals)]
    ).to_csv(report_dir / "signal_log.csv", index=False)
    pd.DataFrame(
        [
            {
                "symbol": f"REJ{idx}",
                "signal_date": "2020-01-01",
                "reason": "PORTFOLIO_CAPACITY_FULL",
            }
            for idx in range(total_rejections)
        ]
    ).to_csv(report_dir / "rejected_signals.csv", index=False)
