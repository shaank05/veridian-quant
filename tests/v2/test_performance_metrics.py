"""Unit tests for v2 portfolio performance summary metrics."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

from veridian_quant.v2.backtesting.ledger import EquityPoint, PortfolioLedger
from veridian_quant.v2.backtesting.pnl import TradePnL
from veridian_quant.v2.backtesting.portfolio_runner import (
    PortfolioBacktestResult,
    PortfolioRejectedSignal,
)
from veridian_quant.v2.backtesting.trade import ExitReason
from veridian_quant.v2.data.models import Signal, SignalType
from veridian_quant.v2.reporting.metrics import calculate_performance_summary


def test_total_return_calculation() -> None:
    summary = calculate_performance_summary(_result())

    assert summary.total_return_pct == Decimal("8.00")


def test_cagr_calculation() -> None:
    summary = calculate_performance_summary(_result())

    assert summary.cagr_pct is not None
    assert summary.cagr_pct.quantize(Decimal("0.01")) == Decimal("8.00")


def test_max_drawdown_calculation() -> None:
    summary = calculate_performance_summary(_result())

    assert summary.max_drawdown_pct.quantize(Decimal("0.01")) == Decimal("4.55")


def test_win_rate() -> None:
    summary = calculate_performance_summary(_result())

    assert summary.winning_trades == 2
    assert summary.losing_trades == 1
    assert summary.win_rate_pct.quantize(Decimal("0.01")) == Decimal("66.67")


def test_profit_factor() -> None:
    summary = calculate_performance_summary(_result())

    assert summary.gross_profit == Decimal("13000")
    assert summary.gross_loss == Decimal("-5000")
    assert summary.profit_factor == Decimal("2.6")


def test_expectancy() -> None:
    summary = calculate_performance_summary(_result())

    assert summary.expectancy == Decimal("2666.666666666666666666666667")
    assert summary.average_net_pnl == summary.expectancy


def test_average_win_loss() -> None:
    summary = calculate_performance_summary(_result())

    assert summary.average_win == Decimal("6500")
    assert summary.average_loss == Decimal("-5000")


def test_best_worst_trade() -> None:
    summary = calculate_performance_summary(_result())

    assert summary.best_trade == Decimal("10000")
    assert summary.worst_trade == Decimal("-5000")


def test_average_holding_days() -> None:
    summary = calculate_performance_summary(_result())

    assert summary.average_holding_days == Decimal("5")


def test_no_trades_safe_behavior() -> None:
    result = replace(
        _result(),
        trade_pnls=(),
        trades=(),
        starting_equity=Decimal("100000"),
        ending_equity=Decimal("100000"),
        ledger=PortfolioLedger(
            starting_equity=Decimal("100000"),
            current_equity=Decimal("100000"),
            realized_pnl=Decimal("0"),
        ),
    )

    summary = calculate_performance_summary(result)

    assert summary.total_net_pnl == Decimal("0")
    assert summary.total_return_pct == Decimal("0")
    assert summary.total_trades == 0
    assert summary.win_rate_pct == Decimal("0")
    assert summary.profit_factor is None
    assert summary.expectancy is None
    assert summary.average_win is None
    assert summary.average_loss is None
    assert summary.best_trade is None
    assert summary.worst_trade is None
    assert summary.average_holding_days is None


def test_empty_equity_curve_safe_behavior() -> None:
    result = replace(
        _result(),
        ledger=PortfolioLedger(
            starting_equity=Decimal("100000"),
            current_equity=Decimal("108000"),
            realized_pnl=Decimal("8000"),
        ),
    )

    summary = calculate_performance_summary(result)

    assert summary.max_drawdown_pct == Decimal("0")


def test_result_is_not_mutated() -> None:
    result = _result()
    original = replace(result)

    calculate_performance_summary(result)

    assert result == original


def _result() -> PortfolioBacktestResult:
    """Build a portfolio result with wins, loss, and drawdown."""

    trade_pnls = (
        _trade_pnl("win-1", date(2026, 1, 1), date(2026, 1, 6), Decimal("10000")),
        _trade_pnl("loss-1", date(2026, 2, 1), date(2026, 2, 6), Decimal("-5000")),
        _trade_pnl("win-2", date(2026, 3, 1), date(2026, 3, 6), Decimal("3000")),
    )
    ledger = PortfolioLedger(
        starting_equity=Decimal("100000"),
        current_equity=Decimal("108000"),
        realized_pnl=Decimal("8000"),
        trade_pnls=trade_pnls,
        equity_curve=(
            EquityPoint(date=date(2026, 1, 6), equity=Decimal("110000"), realized_pnl=Decimal("10000")),
            EquityPoint(date=date(2026, 2, 6), equity=Decimal("105000"), realized_pnl=Decimal("5000")),
            EquityPoint(date=date(2026, 3, 6), equity=Decimal("108000"), realized_pnl=Decimal("8000")),
        ),
    )
    return PortfolioBacktestResult(
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        start_date=date(2026, 1, 1),
        end_date=date(2027, 1, 1),
        starting_equity=Decimal("100000"),
        ending_equity=Decimal("108000"),
        symbols=("RELIANCE", "TCS"),
        trade_pnls=trade_pnls,
        trades=(),
        signals=(
            Signal(
                symbol="RELIANCE",
                signal_type=SignalType.LONG,
                generated_on=date(2026, 1, 1),
                strategy_name="S1_ZSCORE_MEAN_REVERSION",
                reason="test",
            ),
        ),
        rejected_signals=(
            PortfolioRejectedSignal(
                symbol="TCS",
                signal_date=date(2026, 1, 2),
                strategy_name="S1_ZSCORE_MEAN_REVERSION",
                reason="PORTFOLIO_CAPACITY_FULL",
            ),
        ),
        ledger=ledger,
    )


def _trade_pnl(
    trade_id: str,
    entry_date: date,
    exit_date: date,
    net_pnl: Decimal,
) -> TradePnL:
    """Build a trade PnL record for metric tests."""

    return TradePnL(
        trade_id=trade_id,
        symbol="RELIANCE",
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        entry_date=entry_date,
        exit_date=exit_date,
        entry_price=Decimal("100"),
        exit_price=Decimal("110") if net_pnl > 0 else Decimal("95"),
        quantity=100,
        gross_pnl=net_pnl,
        gross_return_pct=Decimal("0"),
        total_cost=Decimal("0"),
        net_pnl=net_pnl,
        net_return_pct=Decimal("0"),
        exit_reason=ExitReason.TARGET_HIT if net_pnl > 0 else ExitReason.STOP_LOSS_HIT,
    )
