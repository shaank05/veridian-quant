"""Unit tests for v2 diagnostic report CSV exporters."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from pathlib import Path

import pandas as pd
import pytest

from veridian_quant.v2.backtesting.pnl import TradePnL
from veridian_quant.v2.backtesting.portfolio_runner import (
    PortfolioBacktestResult,
    PortfolioRejectedSignal,
)
from veridian_quant.v2.backtesting.trade import ExitReason
from veridian_quant.v2.reporting.diagnostics import (
    EXIT_REASON_SUMMARY_COLUMNS,
    REJECTION_SUMMARY_COLUMNS,
    R_MULTIPLE_BY_EXIT_REASON_COLUMNS,
    R_MULTIPLE_SUMMARY_COLUMNS,
    SYMBOL_SUMMARY_COLUMNS,
    YEARLY_SUMMARY_COLUMNS,
)
from veridian_quant.v2.reporting.exporters import export_portfolio_backtest_csvs


def test_diagnostic_csv_files_are_created() -> None:
    paths = _export_to_temp_dir(_diagnostic_result())

    assert paths["exit_reason_summary"].exists()
    assert paths["symbol_summary"].exists()
    assert paths["yearly_summary"].exists()
    assert paths["rejection_summary"].exists()
    assert paths["r_multiple_summary"].exists()
    assert paths["r_multiple_by_exit_reason"].exists()


def test_exit_reason_summary_groups_trade_pnls_correctly() -> None:
    paths = _export_to_temp_dir(_diagnostic_result())

    summary = pd.read_csv(paths["exit_reason_summary"]).set_index("exit_reason")

    assert list(summary.columns) == EXIT_REASON_SUMMARY_COLUMNS[1:]
    assert summary.loc["target_hit", "trades"] == 2
    assert summary.loc["target_hit", "wins"] == 2
    assert summary.loc["target_hit", "losses"] == 0
    assert summary.loc["target_hit", "win_rate_pct"] == 100
    assert summary.loc["target_hit", "gross_profit"] == 150
    assert summary.loc["target_hit", "gross_loss"] == 0
    assert summary.loc["target_hit", "net_pnl"] == 150
    assert summary.loc["target_hit", "average_net_pnl"] == 75
    assert summary.loc["target_hit", "best_trade"] == 100
    assert summary.loc["target_hit", "worst_trade"] == 50
    assert summary.loc["stop_loss_hit", "net_pnl"] == -40
    assert summary.loc["data_end", "net_pnl"] == -60


def test_symbol_summary_groups_trade_pnls_correctly() -> None:
    paths = _export_to_temp_dir(_diagnostic_result())

    summary = pd.read_csv(paths["symbol_summary"]).set_index("symbol")

    assert list(summary.columns) == SYMBOL_SUMMARY_COLUMNS[1:]
    assert summary.loc["RELIANCE", "trades"] == 2
    assert summary.loc["RELIANCE", "wins"] == 1
    assert summary.loc["RELIANCE", "losses"] == 1
    assert summary.loc["RELIANCE", "win_rate_pct"] == 50
    assert summary.loc["RELIANCE", "gross_profit"] == 100
    assert summary.loc["RELIANCE", "gross_loss"] == -40
    assert summary.loc["RELIANCE", "net_pnl"] == 60
    assert summary.loc["RELIANCE", "average_net_pnl"] == 30
    assert summary.loc["RELIANCE", "best_trade"] == 100
    assert summary.loc["RELIANCE", "worst_trade"] == -40
    assert summary.loc["RELIANCE", "average_holding_days"] == 4.5
    assert summary.loc["TCS", "net_pnl"] == -10
    assert summary.loc["TCS", "average_holding_days"] == 6


def test_yearly_summary_groups_by_trade_exit_year() -> None:
    paths = _export_to_temp_dir(_diagnostic_result())

    summary = pd.read_csv(paths["yearly_summary"]).set_index("year")

    assert list(summary.columns) == YEARLY_SUMMARY_COLUMNS[1:]
    assert summary.loc[2025, "trades"] == 2
    assert summary.loc[2025, "wins"] == 1
    assert summary.loc[2025, "losses"] == 1
    assert summary.loc[2025, "net_pnl"] == 40
    assert summary.loc[2025, "average_net_pnl"] == 20
    assert summary.loc[2026, "trades"] == 2
    assert summary.loc[2026, "net_pnl"] == 10
    assert summary.loc[2026, "average_net_pnl"] == 5


def test_rejection_summary_counts_reasons() -> None:
    paths = _export_to_temp_dir(_diagnostic_result())

    summary = pd.read_csv(paths["rejection_summary"]).set_index("reason")

    assert list(summary.columns) == REJECTION_SUMMARY_COLUMNS[1:]
    assert summary.loc["ACTIVE_SYMBOL_TRADE_EXISTS", "count"] == 2
    assert summary.loc["PORTFOLIO_CAPACITY_FULL", "count"] == 1


def test_empty_trade_list_writes_diagnostic_headers_without_crashing() -> None:
    paths = _export_to_temp_dir(_empty_result())

    expected_columns_by_file = {
        "exit_reason_summary": EXIT_REASON_SUMMARY_COLUMNS,
        "symbol_summary": SYMBOL_SUMMARY_COLUMNS,
        "yearly_summary": YEARLY_SUMMARY_COLUMNS,
        "rejection_summary": REJECTION_SUMMARY_COLUMNS,
        "r_multiple_summary": R_MULTIPLE_SUMMARY_COLUMNS,
        "r_multiple_by_exit_reason": R_MULTIPLE_BY_EXIT_REASON_COLUMNS,
    }
    for key, expected_columns in expected_columns_by_file.items():
        report = pd.read_csv(paths[key])
        assert list(report.columns) == expected_columns
        assert report.empty


def test_existing_exporter_outputs_remain_available() -> None:
    paths = _export_to_temp_dir(_diagnostic_result())

    assert {
        "trade_log",
        "trade_pnl_log",
        "signal_log",
        "rejected_signals",
        "equity_curve",
        "summary",
    }.issubset(paths)
    assert pd.read_csv(paths["trade_pnl_log"]).loc[0, "net_pnl"] == 100


def test_r_multiple_summary_is_empty_when_risk_metadata_is_unavailable() -> None:
    paths = _export_to_temp_dir(_diagnostic_result())

    summary = pd.read_csv(paths["r_multiple_summary"])

    assert list(summary.columns) == R_MULTIPLE_SUMMARY_COLUMNS
    assert summary.empty


def test_r_multiple_summary_uses_per_share_risk_metadata() -> None:
    paths = _export_to_temp_dir(_r_multiple_result())

    summary = pd.read_csv(paths["r_multiple_summary"])

    assert list(summary.columns) == R_MULTIPLE_SUMMARY_COLUMNS
    assert summary.loc[0, "trades_with_r"] == 3
    assert summary.loc[0, "winning_trades"] == 2
    assert summary.loc[0, "losing_trades"] == 1
    assert summary.loc[0, "average_r"] == 1
    assert summary.loc[0, "average_winner_r"] == 2
    assert summary.loc[0, "average_loser_r"] == -1
    assert summary.loc[0, "best_r"] == 3
    assert summary.loc[0, "worst_r"] == -1
    assert summary.loc[0, "positive_r_rate_pct"] == pytest.approx(66.6666666667)


def test_r_multiple_summary_can_derive_per_share_risk_from_stop_loss_metadata() -> None:
    paths = _export_to_temp_dir(_r_multiple_result_with_stop_loss())

    summary = pd.read_csv(paths["r_multiple_summary"])

    assert summary.loc[0, "trades_with_r"] == 1
    assert summary.loc[0, "average_r"] == 2


def test_r_multiple_by_exit_reason_groups_calculated_r_values() -> None:
    paths = _export_to_temp_dir(_r_multiple_result())

    summary = pd.read_csv(paths["r_multiple_by_exit_reason"]).set_index("exit_reason")

    assert list(summary.columns) == R_MULTIPLE_BY_EXIT_REASON_COLUMNS[1:]
    assert summary.loc["target_hit", "trades_with_r"] == 2
    assert summary.loc["target_hit", "average_r"] == 2
    assert summary.loc["target_hit", "average_winner_r"] == 2
    assert pd.isna(summary.loc["target_hit", "average_loser_r"])
    assert summary.loc["target_hit", "best_r"] == 3
    assert summary.loc["target_hit", "worst_r"] == 1
    assert summary.loc["stop_loss_hit", "trades_with_r"] == 1
    assert summary.loc["stop_loss_hit", "average_r"] == -1


def _export_to_temp_dir(result: PortfolioBacktestResult) -> dict[str, Path]:
    """Export the fake result into a temp directory that persists for the test."""

    temp_dir = TemporaryDirectory()
    paths = export_portfolio_backtest_csvs(result, temp_dir.name)
    _TEMP_DIRS.append(temp_dir)
    return paths


_TEMP_DIRS: list[TemporaryDirectory] = []


def _diagnostic_result() -> PortfolioBacktestResult:
    """Build a portfolio result with multiple diagnostic groups."""

    trade_pnls = (
        _pnl(
            trade_id="trade-1",
            symbol="RELIANCE",
            entry_date=date(2025, 12, 20),
            exit_date=date(2025, 12, 25),
            net_pnl=Decimal("100"),
            exit_reason=ExitReason.TARGET_HIT,
        ),
        _pnl(
            trade_id="trade-2",
            symbol="RELIANCE",
            entry_date=date(2026, 1, 6),
            exit_date=date(2026, 1, 10),
            net_pnl=Decimal("-40"),
            exit_reason=ExitReason.STOP_LOSS_HIT,
        ),
        _pnl(
            trade_id="trade-3",
            symbol="TCS",
            entry_date=date(2026, 2, 1),
            exit_date=date(2026, 2, 11),
            net_pnl=Decimal("50"),
            exit_reason=ExitReason.TARGET_HIT,
        ),
        _pnl(
            trade_id="trade-4",
            symbol="TCS",
            entry_date=date(2025, 12, 29),
            exit_date=date(2025, 12, 31),
            net_pnl=Decimal("-60"),
            exit_reason=ExitReason.DATA_END,
        ),
    )
    return PortfolioBacktestResult(
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        start_date=date(2025, 12, 1),
        end_date=date(2026, 2, 28),
        starting_equity=Decimal("100000"),
        ending_equity=Decimal("100050"),
        symbols=("RELIANCE", "TCS"),
        trade_pnls=trade_pnls,
        trades=(),
        signals=(),
        rejected_signals=(
            _rejected("RELIANCE", "ACTIVE_SYMBOL_TRADE_EXISTS"),
            _rejected("TCS", "ACTIVE_SYMBOL_TRADE_EXISTS"),
            _rejected("INFY", "PORTFOLIO_CAPACITY_FULL"),
        ),
        ledger=None,
    )


def _empty_result() -> PortfolioBacktestResult:
    """Build an empty portfolio result for header-only diagnostic exports."""

    return PortfolioBacktestResult(
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        starting_equity=Decimal("100000"),
        ending_equity=Decimal("100000"),
        symbols=(),
        trade_pnls=(),
        trades=(),
        signals=(),
        rejected_signals=(),
        ledger=None,
    )


def _r_multiple_result() -> PortfolioBacktestResult:
    """Build a portfolio result with fake PnL metadata for R diagnostics."""

    return PortfolioBacktestResult(
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        starting_equity=Decimal("100000"),
        ending_equity=Decimal("100070"),
        symbols=("RELIANCE", "TCS"),
        trade_pnls=(
            _pnl_with_metadata(
                trade_id="r-1",
                symbol="RELIANCE",
                net_pnl=Decimal("100"),
                exit_reason=ExitReason.TARGET_HIT,
                metadata={"per_share_risk": Decimal("10")},
            ),
            _pnl_with_metadata(
                trade_id="r-2",
                symbol="RELIANCE",
                net_pnl=Decimal("-100"),
                exit_reason=ExitReason.STOP_LOSS_HIT,
                metadata={"per_share_risk": Decimal("10")},
            ),
            _pnl_with_metadata(
                trade_id="r-3",
                symbol="TCS",
                net_pnl=Decimal("300"),
                exit_reason=ExitReason.TARGET_HIT,
                metadata={"per_share_risk": Decimal("10")},
            ),
            _pnl_with_metadata(
                trade_id="r-4",
                symbol="TCS",
                net_pnl=Decimal("50"),
                exit_reason=ExitReason.DATA_END,
                metadata={},
            ),
        ),
        trades=(),
        signals=(),
        rejected_signals=(),
        ledger=None,
    )


def _r_multiple_result_with_stop_loss() -> PortfolioBacktestResult:
    """Build a portfolio result with stop-loss metadata for R diagnostics."""

    return PortfolioBacktestResult(
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        starting_equity=Decimal("100000"),
        ending_equity=Decimal("100100"),
        symbols=("RELIANCE",),
        trade_pnls=(
            _pnl_with_metadata(
                trade_id="r-stop-loss",
                symbol="RELIANCE",
                net_pnl=Decimal("100"),
                exit_reason=ExitReason.TARGET_HIT,
                metadata={"stop_loss": Decimal("95")},
            ),
        ),
        trades=(),
        signals=(),
        rejected_signals=(),
        ledger=None,
    )


def _pnl(
    trade_id: str,
    symbol: str,
    entry_date: date,
    exit_date: date,
    net_pnl: Decimal,
    exit_reason: ExitReason,
) -> TradePnL:
    """Build a minimal trade PnL row for diagnostics."""

    return TradePnL(
        trade_id=trade_id,
        symbol=symbol,
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        entry_date=entry_date,
        exit_date=exit_date,
        entry_price=Decimal("100"),
        exit_price=Decimal("100"),
        quantity=1,
        gross_pnl=net_pnl,
        gross_return_pct=Decimal("0"),
        total_cost=Decimal("0"),
        net_pnl=net_pnl,
        net_return_pct=Decimal("0"),
        exit_reason=exit_reason,
    )


def _pnl_with_metadata(
    trade_id: str,
    symbol: str,
    net_pnl: Decimal,
    exit_reason: ExitReason,
    metadata: dict[str, Decimal],
) -> SimpleNamespace:
    """Build a fake trade PnL carrying optional diagnostic metadata."""

    return SimpleNamespace(
        trade_id=trade_id,
        symbol=symbol,
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        entry_date=date(2026, 1, 1),
        exit_date=date(2026, 1, 5),
        entry_price=Decimal("100"),
        exit_price=Decimal("100"),
        quantity=10,
        gross_pnl=net_pnl,
        gross_return_pct=Decimal("0"),
        total_cost=Decimal("0"),
        net_pnl=net_pnl,
        net_return_pct=Decimal("0"),
        exit_reason=exit_reason,
        metadata=metadata,
    )


def _rejected(symbol: str, reason: str) -> PortfolioRejectedSignal:
    """Build a rejected signal row for diagnostics."""

    return PortfolioRejectedSignal(
        symbol=symbol,
        signal_date=date(2026, 1, 1),
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        reason=reason,
    )
