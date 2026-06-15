"""Unit tests for v2 report CSV exporters."""

from dataclasses import replace
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
            "exit_reason_summary",
            "symbol_summary",
            "yearly_summary",
            "rejection_summary",
            "r_multiple_summary",
            "r_multiple_by_exit_reason",
            "r_multiple_by_symbol",
            "r_multiple_by_year",
            "r_multiple_by_symbol_year",
            "trade_signal_context",
            "r_by_stock_trend_context",
            "r_by_nifty_trend_context",
            "r_by_relative_strength_context",
            "r_by_zscore_depth",
            "r_by_pre_signal_return_context",
            "r_by_drawdown_depth_context",
            "r_by_atr_stretch_context",
            "r_by_signal_candle_context",
            "r_by_consecutive_down_closes",
            "r_by_fresh_low_context",
            "candidate_filter_simulation",
            "candidate_filter_simulation_by_year",
            "candidate_filter_simulation_by_symbol",
            "candidate_filter_simulation_rejected_trades",
            "s2_markov_filter_simulation",
            "s2_markov_filter_simulation_by_year",
            "s2_markov_filter_simulation_by_symbol",
            "s2_markov_filter_simulation_rejected_trades",
            "s2_markov_state_component_summary",
            "s2_markov_state_label_summary",
            "all_signal_opportunity_log",
            "accepted_vs_rejected_signal_summary",
            "counterfactual_rejected_trade_summary",
            "counterfactual_by_year",
            "counterfactual_by_symbol",
            "same_day_candidate_pool_summary",
            "ranking_feature_diagnostics",
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
        "stop_loss",
        "target_price",
        "per_share_risk",
        "initial_risk_amount",
        "planned_reward_amount",
        "reward_risk_ratio",
        "exit_date",
        "exit_price",
        "exit_reason",
        "strategy_name",
        "candidate_ranking_mode",
        "candidate_rank",
        "candidate_score",
        "candidate_pool_size_for_date",
    ]
    assert trade_log.loc[0, "exit_reason"] == "target_hit"
    assert trade_log.loc[0, "initial_risk_amount"] == 1000


def test_trade_pnl_log_contains_risk_metadata_columns() -> None:
    paths = _export_to_temp_dir()

    trade_pnl_log = pd.read_csv(paths["trade_pnl_log"])

    assert {
        "stop_loss",
        "target_price",
        "per_share_risk",
        "initial_risk_amount",
        "planned_reward_amount",
        "reward_risk_ratio",
    }.issubset(trade_pnl_log.columns)
    assert trade_pnl_log.loc[0, "planned_reward_amount"] == 2000


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


def test_export_serializes_backtest_end_and_data_end_exit_reasons() -> None:
    paths = _export_to_temp_dir(_result_with_forced_exit_reasons())

    trade_log = pd.read_csv(paths["trade_log"])
    trade_pnl_log = pd.read_csv(paths["trade_pnl_log"])

    assert trade_log.loc[0, "exit_reason"] == "backtest_end"
    assert trade_log.loc[1, "exit_reason"] == "data_end"
    assert trade_pnl_log.loc[0, "exit_reason"] == "backtest_end"
    assert trade_pnl_log.loc[1, "exit_reason"] == "data_end"


def _export_to_temp_dir(result: PortfolioBacktestResult | None = None) -> dict[str, Path]:
    """Export the fake result into a temp directory that persists for the test."""

    temp_dir = TemporaryDirectory()
    paths = export_portfolio_backtest_csvs(result or _result(), temp_dir.name)
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
        stop_loss=Decimal("95"),
        target_price=Decimal("110"),
        per_share_risk=Decimal("5"),
        initial_risk_amount=Decimal("1000"),
        planned_reward_amount=Decimal("2000"),
        reward_risk_ratio=Decimal("2"),
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
        stop_loss=Decimal("95"),
        target_price=Decimal("110"),
        per_share_risk=Decimal("5"),
        initial_risk_amount=Decimal("1000"),
        planned_reward_amount=Decimal("2000"),
        reward_risk_ratio=Decimal("2"),
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


def _result_with_forced_exit_reasons() -> PortfolioBacktestResult:
    """Build a result containing BACKTEST_END and DATA_END exits."""

    base = _result()
    backtest_end_trade = replace(
        base.trades[0],
        exit_reason=ExitReason.BACKTEST_END,
    )
    data_end_trade = Trade(
        trade_id="trade-2",
        symbol="TCS",
        entry_date=date(2026, 1, 21),
        entry_price=Decimal("100"),
        quantity=100,
        status=TradeStatus.CLOSED,
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        exit_date=date(2026, 1, 25),
        exit_price=Decimal("99"),
        exit_reason=ExitReason.DATA_END,
    )
    backtest_end_pnl = replace(
        base.trade_pnls[0],
        exit_reason=ExitReason.BACKTEST_END,
    )
    data_end_pnl = TradePnL(
        trade_id="trade-2",
        symbol="TCS",
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        entry_date=date(2026, 1, 21),
        exit_date=date(2026, 1, 25),
        entry_price=Decimal("100"),
        exit_price=Decimal("99"),
        quantity=100,
        gross_pnl=Decimal("-100"),
        gross_return_pct=Decimal("-1"),
        total_cost=Decimal("0"),
        net_pnl=Decimal("-100"),
        net_return_pct=Decimal("-1"),
        exit_reason=ExitReason.DATA_END,
    )
    return PortfolioBacktestResult(
        strategy_name=base.strategy_name,
        start_date=base.start_date,
        end_date=base.end_date,
        starting_equity=base.starting_equity,
        ending_equity=base.ending_equity,
        symbols=("RELIANCE", "TCS"),
        trade_pnls=(backtest_end_pnl, data_end_pnl),
        trades=(backtest_end_trade, data_end_trade),
        signals=base.signals,
        rejected_signals=base.rejected_signals,
        ledger=base.ledger,
    )
