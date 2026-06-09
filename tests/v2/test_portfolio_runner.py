"""Unit tests for v2 multi-symbol S1 portfolio backtest orchestration."""

from datetime import date
from decimal import Decimal

import pandas as pd

from veridian_quant.v2.backtesting.portfolio_runner import (
    PortfolioBacktestResult,
    run_s1_portfolio_backtest,
)
from veridian_quant.v2.backtesting.trade import ExitReason


def test_successful_multi_symbol_backtest() -> None:
    result = _run({"RELIANCE": _two_signal_frame(), "TCS": _late_signal_frame()})

    assert isinstance(result, PortfolioBacktestResult)
    assert result.symbols == ("RELIANCE", "TCS")
    assert len(result.signals) >= 2
    assert len(result.trades) >= 2
    assert len(result.trade_pnls) == len(result.trades)
    assert result.ledger is not None


def test_signals_are_processed_chronologically() -> None:
    result = _run({"TCS": _late_signal_frame(), "RELIANCE": _two_signal_frame()})

    signal_dates = [signal.generated_on for signal in result.signals]

    assert signal_dates == sorted(signal_dates)


def test_same_day_signals_are_ranked_by_most_negative_zscore_first() -> None:
    result = _run(
        {
            "LESS_NEGATIVE": _same_day_signal_frame([10, 12, 14, 8, 9]),
            "MORE_NEGATIVE": _same_day_signal_frame([10, 20, 21, 5, 6]),
        },
        max_concurrent_positions=1,
    )

    assert [signal.symbol for signal in result.signals[:2]] == [
        "MORE_NEGATIVE",
        "LESS_NEGATIVE",
    ]
    assert result.trades[0].symbol == "MORE_NEGATIVE"
    assert result.rejected_signals[0].symbol == "LESS_NEGATIVE"
    assert result.rejected_signals[0].reason == "PORTFOLIO_CAPACITY_FULL"


def test_max_concurrent_positions_is_respected() -> None:
    result = _run(
        {
            "A": _same_day_signal_frame([10, 20, 21, 5, 6]),
            "B": _same_day_signal_frame([10, 12, 14, 8, 9]),
        },
        max_concurrent_positions=1,
    )

    assert len(result.trades) == 1
    assert any(
        rejected.reason == "PORTFOLIO_CAPACITY_FULL"
        for rejected in result.rejected_signals
    )


def test_active_same_symbol_trade_is_rejected() -> None:
    result = _run({"RELIANCE": _two_signal_frame()})

    assert len(result.signals) == 2
    assert len(result.trades) == 1
    assert result.rejected_signals[0].reason == "ACTIVE_SYMBOL_TRADE_EXISTS"


def test_current_equity_compounds_after_closed_trades() -> None:
    result = _run({"RELIANCE": _early_winner_frame(), "TCS": _late_signal_frame()})

    assert len(result.trade_pnls) == 2
    assert result.ending_equity == (
        result.starting_equity
        + result.trade_pnls[0].net_pnl
        + result.trade_pnls[1].net_pnl
    )
    assert result.ledger is not None
    assert len(result.ledger.equity_curve) == 2


def test_no_data_after_end_date_is_used() -> None:
    result = _run(
        {"RELIANCE": _post_window_target_frame()},
        end_date=date(2026, 1, 5),
        atr_multiplier=Decimal("1"),
    )

    assert len(result.trades) == 1
    assert result.trades[0].exit_date == date(2026, 1, 5)
    assert result.trades[0].exit_price == Decimal("9.0")
    assert result.trades[0].exit_reason == ExitReason.BACKTEST_END


def test_data_ending_before_backtest_end_uses_data_end_reason() -> None:
    result = _run(
        {"RELIANCE": _post_window_target_frame().iloc[:5].copy()},
        end_date=date(2026, 1, 20),
        atr_multiplier=Decimal("1"),
    )

    assert len(result.trades) == 1
    assert result.trades[0].exit_date == date(2026, 1, 5)
    assert result.trades[0].exit_reason == ExitReason.DATA_END


def test_symbol_with_invalid_data_is_rejected_safely() -> None:
    invalid = _same_day_signal_frame([10, 12, 14, 8, 9]).drop(columns=["low"])

    result = _run({"BAD": invalid, "GOOD": _same_day_signal_frame([10, 12, 14, 8, 9])})

    assert len(result.trades) == 1
    assert any(
        rejected.symbol == "BAD" and rejected.reason == "DATA_UNAVAILABLE"
        for rejected in result.rejected_signals
    )


def test_input_dataframes_are_not_mutated() -> None:
    data_by_symbol = {"RELIANCE": _two_signal_frame(), "TCS": _late_signal_frame()}
    originals = {
        symbol: data.copy(deep=True)
        for symbol, data in data_by_symbol.items()
    }

    _run(data_by_symbol)

    for symbol, original in originals.items():
        pd.testing.assert_frame_equal(data_by_symbol[symbol], original)


def test_result_contains_combined_artifacts() -> None:
    result = _run({"RELIANCE": _two_signal_frame(), "TCS": _late_signal_frame()})

    assert result.signals
    assert result.trades
    assert result.trade_pnls
    assert result.rejected_signals
    assert result.ledger is not None
    assert result.ledger.trade_pnls == result.trade_pnls


def _run(
    data_by_symbol: dict[str, pd.DataFrame],
    start_date: date = date(2026, 1, 1),
    end_date: date = date(2026, 1, 20),
    max_concurrent_positions: int = 5,
    atr_multiplier: Decimal = Decimal("10"),
) -> PortfolioBacktestResult:
    """Run the portfolio backtest with compact deterministic settings."""

    return run_s1_portfolio_backtest(
        data_by_symbol=data_by_symbol,
        start_date=start_date,
        end_date=end_date,
        starting_equity=Decimal("100000"),
        risk_per_trade=Decimal("0.01"),
        max_concurrent_positions=max_concurrent_positions,
        zscore_window=3,
        entry_threshold=-1.0,
        atr_window=1,
        atr_multiplier=atr_multiplier,
        reward_risk_ratio=Decimal("1"),
        max_holding_sessions=20,
        round_trip_cost_pct=Decimal("0"),
    )


def _two_signal_frame() -> pd.DataFrame:
    """Build data with two signals while the first same-symbol trade is active."""

    return _frame([10, 12, 14, 8, 7, 8, 9, 11, 13, 15, 9, 10, 11, 12, 13, 14])


def _late_signal_frame() -> pd.DataFrame:
    """Build data with a later S1 signal."""

    return _frame([10, 11, 12, 13, 14, 15, 16, 18, 20, 12, 13, 14, 15])


def _early_winner_frame() -> pd.DataFrame:
    """Build data where the first signal closes before the later symbol signal."""

    data = _frame([10, 12, 14, 8, 12, 13, 14, 15])
    data.loc[4, "high"] = 13.0
    return data


def _post_window_target_frame() -> pd.DataFrame:
    """Build data where only the row after end date would hit the target."""

    data = _frame([10, 12, 14, 8, 9, 100])
    data.loc[5, "open"] = 100.0
    data.loc[5, "high"] = 101.0
    data.loc[5, "low"] = 99.0
    data.loc[5, "close"] = 100.0
    return data


def _same_day_signal_frame(closes: list[float]) -> pd.DataFrame:
    """Build data with a signal on the fourth row."""

    return _frame(closes)


def _frame(closes: list[float]) -> pd.DataFrame:
    """Build one-symbol lowercase OHLC data with controlled exit behavior."""

    rows = []
    for index, close in enumerate(closes):
        session_date = pd.Timestamp("2026-01-01") + pd.Timedelta(days=index)
        rows.append(
            {
                "date": session_date,
                "open": float(close),
                "high": float(close) + 0.5,
                "low": float(close) - 0.5,
                "close": float(close),
                "volume": 1000,
            }
        )
    return pd.DataFrame(rows)
