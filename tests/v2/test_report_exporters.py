"""Unit tests for v2 report CSV exporters."""

from datetime import date
from decimal import Decimal
from tempfile import TemporaryDirectory
from types import MappingProxyType
from pathlib import Path

import pandas as pd

from veridian_quant.v2.backtesting.ledger import EquityPoint, PortfolioLedger
from veridian_quant.v2.backtesting.pnl import TradePnL
from veridian_quant.v2.backtesting.portfolio_runner import (
    PortfolioBacktestResult,
    PortfolioRejectedSignal,
)
from veridian_quant.v2.backtesting.trade import ExitReason, Trade, TradeStatus
from veridian_quant.v2.data.models import Signal, SignalType
from veridian_quant.v2.reporting.exporters import export_portfolio_backtest_csvs


def test_export_portfolio_backtest_csvs_writes_expected_files() -> None:
    with TemporaryDirectory() as temp_dir:
        paths = export_portfolio_backtest_csvs(_result(), temp_dir)

        assert set(paths) == {
            "trade_log",
            "trade_pnl_log",
            "signal_log",
            "rejected_signals",
            "equity_curve",
            "summary",
        }
        assert all(path.exists() for path in paths.values())


def test_trade_log_contains_expected_columns() -> None:
    paths = _export_to_temp_dir()

    trade_log = pd.read_csv(paths["trade_log"])

    assert list(trade_log.columns) == [
        "trade_id",
        "symbol",
        "entry_date",
        "entry_price",
        "quantity",
        "exit_date",
        "exit_price",
        "exit_reason",
        "strategy_name",
    ]
    assert trade_log.loc[0, "exit_reason"] == "target_hit"


def test_signal_log_flattens_metadata() -> None:
    paths = _export_to_temp_dir()

    signal_log = pd.read_csv(paths["signal_log"])

    assert signal_log.loc[0, "z_score"] == -2.5
    assert signal_log.loc[0, "zscore_window"] == 20
    assert signal_log.loc[0, "entry_threshold"] == -2.0
    assert signal_log.loc[0, "close"] == 90.0


def test_summary_contains_simple_counts_and_total_net_pnl() -> None:
    paths = _export_to_temp_dir()

    summary = pd.read_csv(paths["summary"])

    assert summary.loc[0, "total_net_pnl"] == 1920
    assert summary.loc[0, "total_trades"] == 1
    assert summary.loc[0, "total_signals"] == 1
    assert summary.loc[0, "total_rejected_signals"] == 1
    assert summary.loc[0, "symbols_count"] == 1


def _export_to_temp_dir() -> dict[str, Path]:
    """Export the fake result into a temp directory that persists for the test."""

    temp_dir = TemporaryDirectory()
    paths = export_portfolio_backtest_csvs(_result(), temp_dir.name)
    _TEMP_DIRS.append(temp_dir)
    return paths


_TEMP_DIRS: list[TemporaryDirectory] = []


def _result() -> PortfolioBacktestResult:
    """Build a small portfolio result for exporter tests."""

    trade = Trade(
        trade_id="trade-1",
        symbol="RELIANCE",
        entry_date=date(2026, 1, 15),
        entry_price=Decimal("100"),
        quantity=200,
        status=TradeStatus.CLOSED,
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        exit_date=date(2026, 1, 20),
        exit_price=Decimal("110"),
        exit_reason=ExitReason.TARGET_HIT,
    )
    trade_pnl = TradePnL(
        trade_id="trade-1",
        symbol="RELIANCE",
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        entry_date=date(2026, 1, 15),
        exit_date=date(2026, 1, 20),
        entry_price=Decimal("100"),
        exit_price=Decimal("110"),
        quantity=200,
        gross_pnl=Decimal("2000"),
        gross_return_pct=Decimal("10"),
        total_cost=Decimal("80"),
        net_pnl=Decimal("1920"),
        net_return_pct=Decimal("9.6"),
        exit_reason=ExitReason.TARGET_HIT,
    )
    signal = Signal(
        symbol="RELIANCE",
        signal_type=SignalType.LONG,
        generated_on=date(2026, 1, 14),
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        reason="test signal",
        metadata=MappingProxyType(
            {
                "z_score": -2.5,
                "zscore_window": 20,
                "entry_threshold": -2.0,
                "close": 90.0,
            }
        ),
    )
    ledger = PortfolioLedger(
        starting_equity=Decimal("100000"),
        current_equity=Decimal("101920"),
        realized_pnl=Decimal("1920"),
        trade_pnls=(trade_pnl,),
        equity_curve=(
            EquityPoint(
                date=date(2026, 1, 20),
                equity=Decimal("101920"),
                realized_pnl=Decimal("1920"),
            ),
        ),
    )
    return PortfolioBacktestResult(
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        starting_equity=Decimal("100000"),
        ending_equity=Decimal("101920"),
        symbols=("RELIANCE",),
        trade_pnls=(trade_pnl,),
        trades=(trade,),
        signals=(signal,),
        rejected_signals=(
            PortfolioRejectedSignal(
                symbol="RELIANCE",
                signal_date=date(2026, 1, 16),
                strategy_name="S1_ZSCORE_MEAN_REVERSION",
                reason="ACTIVE_SYMBOL_TRADE_EXISTS",
            ),
        ),
        ledger=ledger,
    )
