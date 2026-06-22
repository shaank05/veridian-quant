"""Tests for the Monte Carlo validation CLI."""

from pathlib import Path

import pandas as pd

from veridian_quant.v2.run_monte_carlo_validation import main


def test_cli_writes_summary_and_simulation_csvs(tmp_path: Path) -> None:
    trade_log = tmp_path / "trade_pnl_log.csv"
    output_dir = tmp_path / "validation"
    pd.DataFrame({"trade_net_pnl": [100.0, -50.0, 25.0]}).to_csv(
        trade_log, index=False
    )

    exit_code = main(
        [
            "--trade-pnl-log",
            str(trade_log),
            "--starting-equity",
            "1000",
            "--num-simulations",
            "7",
            "--mode",
            "bootstrap",
            "--random-seed",
            "123",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    summary = pd.read_csv(output_dir / "monte_carlo_summary.csv")
    simulations = pd.read_csv(output_dir / "monte_carlo_simulations.csv")
    assert len(summary) == 1
    assert summary.loc[0, "mode"] == "bootstrap"
    assert summary.loc[0, "pnl_column"] == "trade_net_pnl"
    assert summary.loc[0, "random_seed"] == 123
    assert len(simulations) == 7
    assert "trade_pnls" not in simulations.columns
    assert {
        "simulation_id",
        "final_equity",
        "max_drawdown_pct",
        "longest_losing_streak",
    } <= set(simulations.columns)


def test_cli_respects_custom_thresholds_and_bootstrap_length(tmp_path: Path) -> None:
    trade_log = tmp_path / "trades.csv"
    output_dir = tmp_path / "output"
    pd.DataFrame({"net_pnl": [10.0, -20.0]}).to_csv(trade_log, index=False)

    main(
        [
            "--trade-pnl-log",
            str(trade_log),
            "--starting-equity",
            "100",
            "--num-simulations",
            "3",
            "--mode",
            "bootstrap",
            "--num-trades",
            "5",
            "--drawdown-thresholds",
            "0.15,0.25",
            "--output-dir",
            str(output_dir),
        ]
    )

    summary = pd.read_csv(output_dir / "monte_carlo_summary.csv")
    assert summary.loc[0, "simulated_trade_count"] == 5
    assert "probability_max_drawdown_gte_15_pct" in summary.columns
    assert "probability_max_drawdown_gte_25_pct" in summary.columns
