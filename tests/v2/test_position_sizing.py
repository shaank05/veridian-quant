"""Unit tests for v2 risk-based position sizing."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from types import MappingProxyType

from veridian_quant.v2.backtesting.sizing import (
    PositionPlan,
    build_position_plan,
)
from veridian_quant.v2.backtesting.setup import TradeSetup


def test_valid_position_plan_is_created() -> None:
    setup = _setup()

    plan = build_position_plan(setup, Decimal("100000"))

    assert isinstance(plan, PositionPlan)
    assert plan.symbol == setup.symbol
    assert plan.strategy_name == setup.strategy_name
    assert plan.entry_date == setup.entry_date
    assert plan.entry_price == setup.entry_price
    assert plan.stop_loss == setup.stop_loss
    assert plan.target_price == setup.target_price


def test_quantity_uses_floor_of_risk_amount_divided_by_per_share_risk() -> None:
    setup = _setup(entry_price=Decimal("101"), stop_loss=Decimal("94"))

    plan = build_position_plan(setup, Decimal("100000"))

    assert plan is not None
    assert plan.risk_amount == Decimal("1000.00")
    assert plan.per_share_risk == Decimal("7")
    assert plan.quantity == 142


def test_planned_capital_equals_quantity_times_entry_price() -> None:
    setup = _setup(entry_price=Decimal("101"), stop_loss=Decimal("94"))

    plan = build_position_plan(setup, Decimal("100000"))

    assert plan is not None
    assert plan.planned_capital == Decimal("14342")


def test_no_plan_if_portfolio_equity_is_zero_or_negative() -> None:
    assert build_position_plan(_setup(), Decimal("0")) is None
    assert build_position_plan(_setup(), Decimal("-1")) is None


def test_no_plan_if_risk_per_trade_is_zero_or_negative() -> None:
    assert build_position_plan(_setup(), Decimal("100000"), Decimal("0")) is None
    assert build_position_plan(_setup(), Decimal("100000"), Decimal("-0.01")) is None


def test_no_plan_if_per_share_risk_is_zero_or_negative() -> None:
    zero_risk_setup = _setup(entry_price=Decimal("100"), stop_loss=Decimal("100"))
    negative_risk_setup = _setup(entry_price=Decimal("100"), stop_loss=Decimal("101"))

    assert build_position_plan(zero_risk_setup, Decimal("100000")) is None
    assert build_position_plan(negative_risk_setup, Decimal("100000")) is None


def test_no_plan_if_quantity_is_zero() -> None:
    setup = _setup(entry_price=Decimal("100"), stop_loss=Decimal("90"))

    plan = build_position_plan(setup, Decimal("999"))

    assert plan is None


def test_monetary_outputs_are_decimal() -> None:
    plan = build_position_plan(_setup(), Decimal("100000"))

    assert plan is not None
    assert isinstance(plan.entry_price, Decimal)
    assert isinstance(plan.stop_loss, Decimal)
    assert isinstance(plan.target_price, Decimal)
    assert isinstance(plan.portfolio_equity, Decimal)
    assert isinstance(plan.risk_per_trade, Decimal)
    assert isinstance(plan.risk_amount, Decimal)
    assert isinstance(plan.per_share_risk, Decimal)
    assert isinstance(plan.planned_capital, Decimal)


def test_setup_is_not_mutated() -> None:
    setup = _setup()
    original = replace(setup)

    build_position_plan(setup, Decimal("100000"))

    assert setup == original


def _setup(
    entry_price: Decimal = Decimal("100"),
    stop_loss: Decimal = Decimal("95"),
) -> TradeSetup:
    """Build a passive setup for sizing tests."""

    return TradeSetup(
        symbol="RELIANCE",
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        signal_date=date(2026, 1, 14),
        entry_date=date(2026, 1, 15),
        entry_price=entry_price,
        stop_loss=stop_loss,
        target_price=Decimal("110"),
        atr=Decimal("2.5"),
        atr_window=14,
        atr_multiplier=Decimal("2"),
        reward_risk_ratio=Decimal("2"),
        metadata=MappingProxyType({"source": "test"}),
    )
