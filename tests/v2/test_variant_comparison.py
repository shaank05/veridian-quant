"""Tests for v2 strategy variant comparison reports."""

from pathlib import Path

import pandas as pd

from veridian_quant.v2.reporting.variant_comparison import (
    compare_strategy_variant_reports,
)


def test_variant_comparison_outputs_expected_reports(tmp_path: Path) -> None:
    first = _write_report(
        tmp_path / "variant_a",
        strategy_variant="S1_ALPHA",
        total_net_pnl=1_000,
        max_drawdown_pct=10,
        total_trades=100,
        profit_factor=1.4,
        expectancy=10,
    )
    second = _write_report(
        tmp_path / "variant_b",
        strategy_variant="S1_BETA",
        total_net_pnl=1_500,
        max_drawdown_pct=8,
        total_trades=50,
        profit_factor=1.8,
        expectancy=30,
    )
    output_dir = tmp_path / "comparison"

    outputs = compare_strategy_variant_reports([first, second], output_dir)

    assert set(outputs) == {
        "variant_comparison",
        "variant_yearly_comparison",
        "variant_symbol_comparison",
        "variant_exit_reason_comparison",
        "variant_rejection_comparison",
        "variant_scorecard",
    }
    assert all(path.exists() for path in outputs.values())

    comparison = pd.read_csv(outputs["variant_comparison"])
    assert len(comparison) == 2
    assert list(comparison["strategy_variant"]) == ["S1_ALPHA", "S1_BETA"]
    assert list(comparison["variant_label"]) == ["S1_ALPHA", "S1_BETA"]
    assert comparison.loc[0, "net_pnl_per_trade"] == 10

    yearly = pd.read_csv(outputs["variant_yearly_comparison"])
    assert len(yearly) == 8
    assert set(yearly["strategy_variant"]) == {"S1_ALPHA", "S1_BETA"}
    assert yearly[yearly["strategy_variant"] == "S1_ALPHA"][
        "year_rank_by_net_pnl"
    ].min() == 1

    symbols = pd.read_csv(outputs["variant_symbol_comparison"])
    assert len(symbols) == 10
    assert symbols[subjects(symbols, "S1_ALPHA", "AAA")][
        "is_profitable_symbol"
    ].iloc[0]

    exits = pd.read_csv(outputs["variant_exit_reason_comparison"])
    assert len(exits) == 8
    assert set(exits["exit_reason"]) == {
        "stop_loss_hit",
        "stop_gap_hit",
        "target_hit",
        "target_gap_hit",
    }

    rejections = pd.read_csv(outputs["variant_rejection_comparison"])
    assert rejections.loc[
        subjects(rejections, "S1_ALPHA", "too_messy"),
        "rejection_pct_of_total_signals",
    ].iloc[0] == 25

    scorecard = pd.read_csv(outputs["variant_scorecard"])
    assert "rank_total_net_pnl" in scorecard.columns
    assert "composite_rank" in scorecard.columns
    assert scorecard.loc[
        scorecard["strategy_variant"] == "S1_BETA",
        "rank_total_net_pnl",
    ].iloc[0] == 1


def test_variant_comparison_derived_counts_and_concentration(
    tmp_path: Path,
) -> None:
    report_dir = _write_report(tmp_path / "variant_a", strategy_variant="S1_ALPHA")
    output_dir = tmp_path / "comparison"

    outputs = compare_strategy_variant_reports([report_dir], output_dir)

    comparison = pd.read_csv(outputs["variant_comparison"])
    row = comparison.iloc[0]
    assert row["positive_years"] == 2
    assert row["negative_years"] == 1
    assert row["flat_years"] == 1
    assert row["positive_year_rate_pct"] == 50
    assert row["symbols_profitable"] == 4
    assert row["symbols_losing"] == 1
    assert row["symbol_positive_rate_pct"] == 80
    assert row["symbol_concentration_top3_pct"] == 87.5
    assert row["stop_total_trade_count"] == 30
    assert row["target_total_trade_count"] == 60
    assert row["stop_total_net_pnl"] == -300
    assert row["target_total_net_pnl"] == 1200
    assert row["stop_damage_pct_of_gross_profit"] == 20
    assert row["target_contribution_pct_of_total_profit"] == 80


def test_variant_comparison_accepts_mapping_and_labels(tmp_path: Path) -> None:
    report_dir = _write_report(tmp_path / "variant_a", strategy_variant="S1_ALPHA")
    output_dir = tmp_path / "comparison"

    outputs = compare_strategy_variant_reports({"Custom Label": report_dir}, output_dir)

    comparison = pd.read_csv(outputs["variant_comparison"])
    assert comparison.loc[0, "variant_label"] == "Custom Label"
    assert comparison.loc[0, "strategy_variant"] == "S1_ALPHA"


def test_variant_comparison_missing_optional_files_leave_blanks(
    tmp_path: Path,
) -> None:
    report_dir = tmp_path / "minimal_variant"
    report_dir.mkdir()
    _write_summary(report_dir, strategy_variant="S1_MINIMAL")
    output_dir = tmp_path / "comparison"

    outputs = compare_strategy_variant_reports([report_dir], output_dir)

    comparison = pd.read_csv(outputs["variant_comparison"])
    assert len(comparison) == 1
    assert pd.isna(comparison.loc[0, "average_r"])
    assert pd.isna(comparison.loc[0, "symbols_profitable"])
    assert pd.isna(comparison.loc[0, "positive_years"])
    assert pd.read_csv(outputs["variant_yearly_comparison"]).empty
    assert pd.read_csv(outputs["variant_symbol_comparison"]).empty
    assert pd.read_csv(outputs["variant_exit_reason_comparison"]).empty
    assert pd.read_csv(outputs["variant_rejection_comparison"]).empty


def subjects(frame: pd.DataFrame, strategy_variant: str, value: str) -> pd.Series:
    key_column = "symbol" if "symbol" in frame.columns else "reason"
    return (frame["strategy_variant"] == strategy_variant) & (
        frame[key_column] == value
    )


def _write_report(
    report_dir: Path,
    *,
    strategy_variant: str = "S1_ALPHA",
    total_net_pnl: float = 1_000,
    max_drawdown_pct: float = 10,
    total_trades: int = 100,
    profit_factor: float = 1.4,
    expectancy: float = 10,
) -> Path:
    report_dir.mkdir()
    _write_summary(
        report_dir,
        strategy_variant=strategy_variant,
        total_net_pnl=total_net_pnl,
        max_drawdown_pct=max_drawdown_pct,
        total_trades=total_trades,
        profit_factor=profit_factor,
        expectancy=expectancy,
    )
    pd.DataFrame(
        [
            _summary_row(year=2020, net_pnl=500),
            _summary_row(year=2021, net_pnl=-100),
            _summary_row(year=2022, net_pnl=0),
            _summary_row(year=2023, net_pnl=600),
        ]
    ).to_csv(report_dir / "yearly_summary.csv", index=False)
    pd.DataFrame(
        [
            _summary_row(symbol="AAA", net_pnl=100),
            _summary_row(symbol="BBB", net_pnl=50),
            _summary_row(symbol="CCC", net_pnl=25),
            _summary_row(symbol="DDD", net_pnl=25),
            _summary_row(symbol="EEE", net_pnl=-20),
        ]
    ).to_csv(report_dir / "symbol_summary.csv", index=False)
    pd.DataFrame(
        [
            _summary_row(exit_reason="stop_loss_hit", trades=20, net_pnl=-200),
            _summary_row(exit_reason="stop_gap_hit", trades=10, net_pnl=-100),
            _summary_row(exit_reason="target_hit", trades=50, net_pnl=1_000),
            _summary_row(exit_reason="target_gap_hit", trades=10, net_pnl=200),
        ]
    ).to_csv(report_dir / "exit_reason_summary.csv", index=False)
    pd.DataFrame(
        [
            {"reason": "too_messy", "count": 25},
            {"reason": "liquidity", "count": 5},
        ]
    ).to_csv(report_dir / "rejection_summary.csv", index=False)
    pd.DataFrame(
        [
            {
                "trades_with_r": 90,
                "winning_trades": 55,
                "losing_trades": 35,
                "average_r": 0.4,
                "average_winner_r": 1.2,
                "average_loser_r": -0.8,
                "best_r": 3.1,
                "worst_r": -1.2,
                "positive_r_rate_pct": 61.11,
            }
        ]
    ).to_csv(report_dir / "r_multiple_summary.csv", index=False)
    return report_dir


def _write_summary(
    report_dir: Path,
    *,
    strategy_variant: str,
    total_net_pnl: float = 1_000,
    max_drawdown_pct: float = 10,
    total_trades: int = 100,
    profit_factor: float = 1.4,
    expectancy: float = 10,
) -> None:
    pd.DataFrame(
        [
            {
                "strategy_name": "S1 Z-Score Mean Reversion",
                "strategy_variant": strategy_variant,
                "start_date": "2020-01-01",
                "end_date": "2024-01-01",
                "starting_equity": 100_000,
                "ending_equity": 101_000,
                "total_net_pnl": total_net_pnl,
                "total_return_pct": 1,
                "cagr_pct": 0.25,
                "max_drawdown_pct": max_drawdown_pct,
                "total_trades": total_trades,
                "winning_trades": 60,
                "losing_trades": 40,
                "win_rate_pct": 60,
                "gross_profit": 1_500,
                "gross_loss": -500,
                "profit_factor": profit_factor,
                "expectancy": expectancy,
                "average_win": 25,
                "average_loss": -12.5,
                "average_net_pnl": expectancy,
                "best_trade": 200,
                "worst_trade": -100,
                "average_holding_days": 8,
                "total_signals": 100,
                "total_rejected_signals": 30,
                "symbols_count": 5,
            }
        ]
    ).to_csv(report_dir / "summary.csv", index=False)


def _summary_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "trades": overrides.get("trades", 10),
        "wins": 6,
        "losses": 4,
        "win_rate_pct": 60,
        "gross_profit": 100,
        "gross_loss": -50,
        "net_pnl": overrides.get("net_pnl", 50),
        "average_net_pnl": 5,
        "best_trade": 30,
        "worst_trade": -20,
        "average_holding_days": 8,
    }
    row.update(overrides)
    return row
