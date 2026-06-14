"""Tests for all-signal opportunity diagnostics exports."""

from datetime import date
from decimal import Decimal
from types import MappingProxyType

import pandas as pd

from veridian_quant.v2.backtesting.ledger import PortfolioLedger
from veridian_quant.v2.backtesting.pnl import TradePnL
from veridian_quant.v2.backtesting.portfolio_runner import (
    PortfolioBacktestResult,
    PortfolioRejectedSignal,
)
from veridian_quant.v2.backtesting.trade import ExitReason, Trade, TradeStatus
from veridian_quant.v2.data.models import Signal, SignalType
from veridian_quant.v2.reporting.exporters import export_portfolio_backtest_csvs


def test_all_signal_opportunity_log_is_exported(tmp_path) -> None:
    result, data = _result_and_data()

    paths = export_portfolio_backtest_csvs(result, tmp_path, stock_data_by_symbol=data)

    assert paths["all_signal_opportunity_log"].exists()
    assert not pd.read_csv(paths["all_signal_opportunity_log"]).empty


def test_accepted_signals_are_classified_as_accepted_trades(tmp_path) -> None:
    result, data = _result_and_data()

    paths = export_portfolio_backtest_csvs(result, tmp_path, stock_data_by_symbol=data)
    log = pd.read_csv(paths["all_signal_opportunity_log"])

    accepted = log[log["symbol"] == "ACCEPT"]
    assert accepted.iloc[0]["signal_status"] == "ACCEPTED_TRADE"
    assert accepted.iloc[0]["accepted_trade_id"] == "trade-accept"
    assert accepted.iloc[0]["accepted_net_pnl"] == 1900


def test_capacity_rejected_signals_are_classified_and_simulated(tmp_path) -> None:
    result, data = _result_and_data()

    paths = export_portfolio_backtest_csvs(result, tmp_path, stock_data_by_symbol=data)
    log = pd.read_csv(paths["all_signal_opportunity_log"])

    rejected = log[log["symbol"] == "CAPACITY"].iloc[0]
    assert rejected["signal_status"] == "REJECTED_CAPACITY"
    assert rejected["rejection_reason"] == "PORTFOLIO_CAPACITY_FULL"
    assert rejected["is_counterfactual_simulated"]
    assert pd.notna(rejected["counterfactual_net_pnl"])
    assert pd.notna(rejected["counterfactual_r_multiple"])


def test_active_symbol_rejections_are_classified(tmp_path) -> None:
    result, data = _result_and_data()

    paths = export_portfolio_backtest_csvs(result, tmp_path, stock_data_by_symbol=data)
    log = pd.read_csv(paths["all_signal_opportunity_log"])

    active = log[log["symbol"] == "ACTIVE"].iloc[0]
    assert active["signal_status"] == "REJECTED_ACTIVE_SYMBOL"
    assert active["rejection_reason"] == "ACTIVE_SYMBOL_TRADE_EXISTS"


def test_counterfactual_simulation_does_not_mutate_result(tmp_path) -> None:
    result, data = _result_and_data()
    trades_before = result.trades
    pnls_before = result.trade_pnls
    ledger_before = result.ledger

    export_portfolio_backtest_csvs(result, tmp_path, stock_data_by_symbol=data)

    assert result.trades == trades_before
    assert result.trade_pnls == pnls_before
    assert result.ledger == ledger_before


def test_accepted_vs_rejected_summary_separates_actual_and_counterfactual_pnl(
    tmp_path,
) -> None:
    result, data = _result_and_data()

    paths = export_portfolio_backtest_csvs(result, tmp_path, stock_data_by_symbol=data)
    summary = pd.read_csv(paths["accepted_vs_rejected_signal_summary"])

    accepted = summary[summary["signal_group"] == "ACCEPTED_TRADE"].iloc[0]
    rejected = summary[
        summary["signal_group"] == "REJECTED_CAPACITY_COUNTERFACTUAL"
    ].iloc[0]
    assert accepted["signal_count"] == 1
    assert accepted["net_pnl"] == 1900
    assert rejected["signal_count"] == 1
    assert rejected["simulated_count"] == 1
    assert rejected["net_pnl"] != 1900


def test_counterfactual_by_year_is_created(tmp_path) -> None:
    result, data = _result_and_data()

    paths = export_portfolio_backtest_csvs(result, tmp_path, stock_data_by_symbol=data)
    by_year = pd.read_csv(paths["counterfactual_by_year"])

    assert list(by_year["year"]) == [2026]
    assert by_year.iloc[0]["simulated_count"] == 1


def test_counterfactual_by_symbol_is_created(tmp_path) -> None:
    result, data = _result_and_data()

    paths = export_portfolio_backtest_csvs(result, tmp_path, stock_data_by_symbol=data)
    by_symbol = pd.read_csv(paths["counterfactual_by_symbol"])

    assert list(by_symbol["symbol"]) == ["CAPACITY"]
    assert by_symbol.iloc[0]["simulated_count"] == 1


def test_same_day_candidate_pool_summary_is_created(tmp_path) -> None:
    result, data = _result_and_data()

    paths = export_portfolio_backtest_csvs(result, tmp_path, stock_data_by_symbol=data)
    pool = pd.read_csv(paths["same_day_candidate_pool_summary"])

    assert pool.iloc[0]["total_signal_count"] == 3
    assert pool.iloc[0]["accepted_trade_count"] == 1
    assert pool.iloc[0]["rejected_capacity_count"] == 1
    assert pool.iloc[0]["rejected_active_symbol_count"] == 1
    assert pool.iloc[0]["best_counterfactual_symbol"] == "CAPACITY"


def test_ranking_feature_diagnostics_is_created(tmp_path) -> None:
    result, data = _result_and_data()

    paths = export_portfolio_backtest_csvs(result, tmp_path, stock_data_by_symbol=data)
    diagnostics = pd.read_csv(paths["ranking_feature_diagnostics"])

    assert set(diagnostics["feature_name"]).issuperset(
        {
            "z_score",
            "atr_pct",
            "rolling_avg_volume_20",
            "year",
            "candidate_pool_size_for_date",
        }
    )
    assert "REJECTED_CAPACITY_COUNTERFACTUAL" in set(diagnostics["signal_group"])


def test_exporter_includes_all_new_output_paths(tmp_path) -> None:
    result, data = _result_and_data()

    paths = export_portfolio_backtest_csvs(result, tmp_path, stock_data_by_symbol=data)

    assert {
        "all_signal_opportunity_log",
        "accepted_vs_rejected_signal_summary",
        "counterfactual_rejected_trade_summary",
        "counterfactual_by_year",
        "counterfactual_by_symbol",
        "same_day_candidate_pool_summary",
        "ranking_feature_diagnostics",
    }.issubset(paths)


def test_missing_stock_data_writes_empty_diagnostic_headers(tmp_path) -> None:
    result, _data = _result_and_data()

    paths = export_portfolio_backtest_csvs(result, tmp_path)
    log = pd.read_csv(paths["all_signal_opportunity_log"])

    assert log.empty
    assert "counterfactual_net_pnl" in log.columns


def _result_and_data() -> tuple[PortfolioBacktestResult, dict[str, pd.DataFrame]]:
    signal_date = date(2026, 1, 15)
    entry_date = date(2026, 1, 16)
    signals = (
        _signal("ACCEPT", signal_date, rank=1, score=0.9),
        _signal("CAPACITY", signal_date, rank=2, score=0.8),
        _signal("ACTIVE", signal_date, rank=3, score=0.7),
    )
    trade = Trade(
        trade_id="trade-accept",
        symbol="ACCEPT",
        entry_date=entry_date,
        entry_price=Decimal("80"),
        quantity=100,
        status=TradeStatus.CLOSED,
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        exit_date=date(2026, 1, 20),
        exit_price=Decimal("100"),
        exit_reason=ExitReason.TARGET_HIT,
        stop_loss=Decimal("70"),
        target_price=Decimal("100"),
        per_share_risk=Decimal("10"),
        initial_risk_amount=Decimal("1000"),
        planned_reward_amount=Decimal("2000"),
        reward_risk_ratio=Decimal("2"),
    )
    trade_pnl = TradePnL(
        trade_id="trade-accept",
        symbol="ACCEPT",
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        entry_date=entry_date,
        exit_date=date(2026, 1, 20),
        entry_price=Decimal("80"),
        exit_price=Decimal("100"),
        quantity=100,
        gross_pnl=Decimal("2000"),
        gross_return_pct=Decimal("25"),
        total_cost=Decimal("100"),
        net_pnl=Decimal("1900"),
        net_return_pct=Decimal("23.75"),
        exit_reason=ExitReason.TARGET_HIT,
        stop_loss=Decimal("70"),
        target_price=Decimal("100"),
        per_share_risk=Decimal("10"),
        initial_risk_amount=Decimal("1000"),
        planned_reward_amount=Decimal("2000"),
        reward_risk_ratio=Decimal("2"),
    )
    ledger = PortfolioLedger(
        starting_equity=Decimal("100000"),
        current_equity=Decimal("101900"),
        realized_pnl=Decimal("1900"),
        trade_pnls=(trade_pnl,),
        equity_curve=(),
    )
    result = PortfolioBacktestResult(
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        starting_equity=Decimal("100000"),
        ending_equity=Decimal("101900"),
        symbols=("ACCEPT", "ACTIVE", "CAPACITY"),
        trade_pnls=(trade_pnl,),
        trades=(trade,),
        signals=signals,
        rejected_signals=(
            PortfolioRejectedSignal(
                symbol="CAPACITY",
                signal_date=signal_date,
                strategy_name="S1_ZSCORE_MEAN_REVERSION",
                reason="PORTFOLIO_CAPACITY_FULL",
                candidate_ranking_mode="s1_v1",
                candidate_rank=2,
                candidate_score=0.8,
                candidate_pool_size_for_date=3,
            ),
            PortfolioRejectedSignal(
                symbol="ACTIVE",
                signal_date=signal_date,
                strategy_name="S1_ZSCORE_MEAN_REVERSION",
                reason="ACTIVE_SYMBOL_TRADE_EXISTS",
                candidate_ranking_mode="s1_v1",
                candidate_rank=3,
                candidate_score=0.7,
                candidate_pool_size_for_date=3,
            ),
        ),
        ledger=ledger,
        candidate_ranking_mode="s1_v1",
    )
    data = {
        "ACCEPT": _frame(target_hit=True),
        "CAPACITY": _frame(target_hit=True),
        "ACTIVE": _frame(target_hit=False),
    }
    return result, data


def _signal(symbol: str, signal_date: date, rank: int, score: float) -> Signal:
    return Signal(
        symbol=symbol,
        signal_type=SignalType.LONG,
        generated_on=signal_date,
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        reason="synthetic",
        metadata=MappingProxyType(
            {
                "z_score": -2.5 - (rank / 10),
                "close": 80.0,
                "candidate_ranking_mode": "s1_v1",
                "candidate_rank": rank,
                "candidate_score": score,
                "candidate_pool_size_for_date": 3,
            }
        ),
    )


def _frame(target_hit: bool) -> pd.DataFrame:
    rows = []
    for index in range(31):
        session_date = pd.Timestamp("2026-01-01") + pd.Timedelta(days=index)
        close = 100.0 if index < 14 else 80.0
        if index > 15:
            close = 100.0 if target_hit else 78.0
        rows.append(
            {
                "date": session_date,
                "open": close,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1000000 + index,
            }
        )
    rows[15]["open"] = 80.0
    rows[15]["high"] = 81.0
    rows[15]["low"] = 79.0
    rows[15]["close"] = 80.0
    if target_hit:
        rows[16]["open"] = 100.0
        rows[16]["high"] = 101.0
        rows[16]["low"] = 99.0
        rows[16]["close"] = 100.0
    return pd.DataFrame(rows)
