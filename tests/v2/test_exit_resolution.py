"""Unit tests for v2 simulated trade exit resolution."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from types import MappingProxyType

import pandas as pd

from veridian_quant.v2.backtesting.exits import resolve_trade_exit
from veridian_quant.v2.backtesting.sizing import PositionPlan
from veridian_quant.v2.backtesting.trade import ExitReason, Trade, TradeStatus


def test_target_gap_hit_exits_at_open() -> None:
    trade = _open_trade()
    plan = _position_plan()
    data = _frame([_row("2026-01-15", open_price="112", high="113", low="108")])

    closed = resolve_trade_exit(trade, plan, data)

    assert closed is not None
    assert closed.exit_reason == ExitReason.TARGET_GAP_HIT
    assert closed.exit_price == Decimal("112")
    assert closed.exit_date == date(2026, 1, 15)


def test_stop_gap_hit_exits_at_open() -> None:
    trade = _open_trade()
    plan = _position_plan()
    data = _frame([_row("2026-01-15", open_price="94", high="100", low="93")])

    closed = resolve_trade_exit(trade, plan, data)

    assert closed is not None
    assert closed.exit_reason == ExitReason.STOP_GAP_HIT
    assert closed.exit_price == Decimal("94")
    assert closed.exit_date == date(2026, 1, 15)


def test_same_candle_target_stop_ambiguity_resolves_as_stop_loss_hit() -> None:
    trade = _open_trade()
    plan = _position_plan()
    data = _frame([_row("2026-01-15", high="111", low="94")])

    closed = resolve_trade_exit(trade, plan, data)

    assert closed is not None
    assert closed.exit_reason == ExitReason.STOP_LOSS_HIT
    assert closed.exit_price == plan.stop_loss
    assert closed.exit_date == date(2026, 1, 15)


def test_normal_target_hit() -> None:
    trade = _open_trade()
    plan = _position_plan()
    data = _frame([_row("2026-01-15", high="111", low="99")])

    closed = resolve_trade_exit(trade, plan, data)

    assert closed is not None
    assert closed.exit_reason == ExitReason.TARGET_HIT
    assert closed.exit_price == plan.target_price


def test_normal_stop_loss_hit() -> None:
    trade = _open_trade()
    plan = _position_plan()
    data = _frame([_row("2026-01-15", high="101", low="94")])

    closed = resolve_trade_exit(trade, plan, data)

    assert closed is not None
    assert closed.exit_reason == ExitReason.STOP_LOSS_HIT
    assert closed.exit_price == plan.stop_loss


def test_time_stop_exits_at_final_holding_close() -> None:
    trade = _open_trade()
    plan = _position_plan()
    data = _frame(
        [
            _row("2026-01-15", close="101"),
            _row("2026-01-16", close="102"),
            _row("2026-01-17", close="103"),
        ]
    )

    closed = resolve_trade_exit(trade, plan, data, max_holding_sessions=2)

    assert closed is not None
    assert closed.exit_reason == ExitReason.TIME_STOP
    assert closed.exit_price == Decimal("102")
    assert closed.exit_date == date(2026, 1, 16)


def test_forced_close_on_backtest_end_date_uses_backtest_end_reason() -> None:
    trade = _open_trade()
    plan = _position_plan()
    data = _frame(
        [
            _row("2026-01-15", close="101"),
            _row("2026-01-16", close="102"),
        ]
    )

    closed = resolve_trade_exit(
        trade,
        plan,
        data,
        max_holding_sessions=20,
        backtest_end_date=date(2026, 1, 16),
    )

    assert closed is not None
    assert closed.exit_reason == ExitReason.BACKTEST_END
    assert closed.exit_price == Decimal("102")
    assert closed.exit_date == date(2026, 1, 16)


def test_data_end_before_backtest_end_uses_data_end_reason() -> None:
    trade = _open_trade()
    plan = _position_plan()
    data = _frame(
        [
            _row("2026-01-15", close="101"),
            _row("2026-01-16", close="102"),
        ]
    )

    closed = resolve_trade_exit(
        trade,
        plan,
        data,
        max_holding_sessions=20,
        backtest_end_date=date(2026, 1, 20),
    )

    assert closed is not None
    assert closed.exit_reason == ExitReason.DATA_END
    assert closed.exit_price == Decimal("102")
    assert closed.exit_date == date(2026, 1, 16)


def test_data_end_used_when_backtest_end_date_is_unknown() -> None:
    trade = _open_trade()
    plan = _position_plan()
    data = _frame([_row("2026-01-15", close="101")])

    closed = resolve_trade_exit(trade, plan, data, max_holding_sessions=20)

    assert closed is not None
    assert closed.exit_reason == ExitReason.DATA_END


def test_no_data_after_entry_returns_none() -> None:
    trade = _open_trade()
    plan = _position_plan()
    data = _frame([_row("2026-01-14")])

    closed = resolve_trade_exit(trade, plan, data)

    assert closed is None


def test_input_trade_is_not_mutated() -> None:
    trade = _open_trade()
    original = replace(trade)

    resolve_trade_exit(trade, _position_plan(), _frame([_row("2026-01-15")]))

    assert trade == original


def test_input_position_plan_is_not_mutated() -> None:
    position_plan = _position_plan()
    original = replace(position_plan)

    resolve_trade_exit(_open_trade(), position_plan, _frame([_row("2026-01-15")]))

    assert position_plan == original


def test_input_dataframe_is_not_mutated() -> None:
    data = _frame([_row("2026-01-15"), _row("2026-01-16")])
    original = data.copy(deep=True)

    resolve_trade_exit(_open_trade(), _position_plan(), data)

    pd.testing.assert_frame_equal(data, original)


def test_missing_required_columns_raises_clear_value_error() -> None:
    data = pd.DataFrame(
        {
            "date": [pd.Timestamp("2026-01-15")],
            "open": [100],
            "high": [101],
            "close": [100],
        }
    )

    try:
        resolve_trade_exit(_open_trade(), _position_plan(), data)
    except ValueError as error:
        assert str(error) == "missing required columns: low"
    else:
        raise AssertionError("expected missing low column to raise ValueError")


def test_returned_trade_has_closed_status() -> None:
    closed = resolve_trade_exit(
        _open_trade(),
        _position_plan(),
        _frame([_row("2026-01-15")]),
    )

    assert closed is not None
    assert closed.status == TradeStatus.CLOSED


def _open_trade() -> Trade:
    """Build a passive open trade for exit tests."""

    return Trade(
        trade_id="S1_ZSCORE_MEAN_REVERSION-RELIANCE-2026-01-15",
        symbol="RELIANCE",
        entry_date=date(2026, 1, 15),
        entry_price=Decimal("100"),
        quantity=200,
        status=TradeStatus.OPEN,
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
    )


def _position_plan() -> PositionPlan:
    """Build a passive position plan for exit tests."""

    return PositionPlan(
        symbol="RELIANCE",
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        entry_date=date(2026, 1, 15),
        entry_price=Decimal("100"),
        stop_loss=Decimal("95"),
        target_price=Decimal("110"),
        quantity=200,
        portfolio_equity=Decimal("100000"),
        risk_per_trade=Decimal("0.01"),
        risk_amount=Decimal("1000.00"),
        per_share_risk=Decimal("5"),
        planned_capital=Decimal("20000"),
        metadata=MappingProxyType({"source": "test"}),
    )


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    """Build an OHLC dataframe from row dictionaries."""

    return pd.DataFrame(rows)


def _row(
    session_date: str,
    open_price: str = "100",
    high: str = "104",
    low: str = "96",
    close: str = "101",
) -> dict[str, object]:
    """Build a single OHLC row for exit tests."""

    return {
        "date": pd.Timestamp(session_date),
        "open": Decimal(open_price),
        "high": Decimal(high),
        "low": Decimal(low),
        "close": Decimal(close),
    }
