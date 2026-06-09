"""Unit tests for v2 single-symbol S1 backtest orchestration."""

from datetime import date
from decimal import Decimal

import pandas as pd

from veridian_quant.v2.backtesting.single_symbol import (
    SingleSymbolBacktestResult,
    run_s1_single_symbol_backtest,
)
from veridian_quant.v2.backtesting.trade import ExitReason


def test_successful_end_to_end_single_symbol_backtest() -> None:
    result = _run(_two_signal_frame())

    assert isinstance(result, SingleSymbolBacktestResult)
    assert result.symbol == "RELIANCE"
    assert len(result.signals) >= 1
    assert len(result.trade_setups) == 1
    assert len(result.position_plans) == 1
    assert len(result.trades) == 1
    assert len(result.trade_pnls) == 1
    assert result.ledger is not None


def test_start_date_end_date_filtering() -> None:
    result = _run(
        _two_signal_frame(),
        start_date=date(2026, 1, 11),
        end_date=date(2026, 1, 11),
    )

    assert [signal.generated_on for signal in result.signals] == [date(2026, 1, 11)]
    assert all(
        result.start_date <= signal.generated_on <= result.end_date
        for signal in result.signals
    )


def test_lookback_data_before_start_date_is_preserved_for_indicator_calculation() -> None:
    result = _run(
        _two_signal_frame(),
        start_date=date(2026, 1, 11),
        end_date=date(2026, 1, 11),
    )

    assert len(result.signals) == 1
    assert result.signals[0].generated_on == date(2026, 1, 11)


def test_input_dataframe_is_not_mutated() -> None:
    data = _two_signal_frame()
    original = data.copy(deep=True)

    _run(data)

    pd.testing.assert_frame_equal(data, original)


def test_rejected_signal_when_setup_cannot_be_created() -> None:
    data = _frame([10, 12, 14, 8])

    result = _run(
        data,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 4),
    )

    assert result.trade_setups == ()
    assert len(result.rejected_signals) == 1
    assert result.rejected_signals[0].reason == "SETUP_UNAVAILABLE"


def test_rejected_signal_when_active_trade_already_exists() -> None:
    result = _run(_two_signal_frame())

    assert len(result.signals) == 2
    assert len(result.trades) == 1
    assert len(result.rejected_signals) == 1
    assert result.rejected_signals[0].reason == "ACTIVE_TRADE_EXISTS"


def test_ledger_equity_updates_after_trade_pnl() -> None:
    result = _run(_two_signal_frame())

    assert result.trade_pnls
    assert result.ledger is not None
    assert result.ending_equity == result.starting_equity + result.trade_pnls[0].net_pnl
    assert result.ledger.current_equity == result.ending_equity


def test_no_trades_when_no_signals() -> None:
    result = _run(_frame([10, 11, 12, 13, 14, 15]))

    assert result.signals == ()
    assert result.trades == ()
    assert result.trade_pnls == ()
    assert result.rejected_signals == ()


def test_data_is_sorted_internally_before_processing() -> None:
    sorted_result = _run(_two_signal_frame())
    unsorted_result = _run(_two_signal_frame().sample(frac=1, random_state=42))

    assert [signal.generated_on for signal in unsorted_result.signals] == [
        signal.generated_on for signal in sorted_result.signals
    ]
    assert [trade.exit_date for trade in unsorted_result.trades] == [
        trade.exit_date for trade in sorted_result.trades
    ]


def test_trade_near_end_date_does_not_use_rows_after_end_date_for_exit() -> None:
    result = _run(
        _post_window_target_frame(),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 5),
        atr_multiplier=Decimal("1"),
    )

    assert len(result.trades) == 1
    assert result.trades[0].exit_date == date(2026, 1, 5)
    assert result.trades[0].exit_price == Decimal("9.0")
    assert result.trades[0].exit_reason == ExitReason.TIME_STOP


def test_missing_required_columns_raises_clear_value_error() -> None:
    data = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=4, freq="D"),
            "open": [10, 12, 14, 8],
            "high": [11, 13, 15, 9],
            "close": [10, 12, 14, 8],
        }
    )

    try:
        _run(data)
    except ValueError as error:
        assert str(error) == "missing required columns: low"
    else:
        raise AssertionError("expected missing low column to raise ValueError")


def _run(
    data: pd.DataFrame,
    start_date: date = date(2026, 1, 1),
    end_date: date = date(2026, 1, 20),
    atr_multiplier: Decimal = Decimal("10"),
) -> SingleSymbolBacktestResult:
    """Run the single-symbol backtest with compact deterministic settings."""

    return run_s1_single_symbol_backtest(
        symbol="RELIANCE",
        data=data,
        start_date=start_date,
        end_date=end_date,
        starting_equity=Decimal("100000"),
        risk_per_trade=Decimal("0.01"),
        zscore_window=3,
        entry_threshold=-1.0,
        atr_window=1,
        atr_multiplier=atr_multiplier,
        reward_risk_ratio=Decimal("1"),
        max_holding_sessions=20,
        round_trip_cost_pct=Decimal("0"),
    )


def _two_signal_frame() -> pd.DataFrame:
    """Build data with two in-window S1 signals while the first trade is active."""

    return _frame(
        [
            10,
            12,
            14,
            8,
            7,
            8,
            9,
            11,
            13,
            15,
            9,
            10,
            11,
            12,
            13,
            14,
        ]
    )


def _post_window_target_frame() -> pd.DataFrame:
    """Build data where only the row after end date would hit the target."""

    data = _frame([10, 12, 14, 8, 9, 100])
    data.loc[5, "open"] = 100.0
    data.loc[5, "high"] = 101.0
    data.loc[5, "low"] = 99.0
    data.loc[5, "close"] = 100.0
    return data


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
