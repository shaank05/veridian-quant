"""Unit tests for v2 open trade creation."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from types import MappingProxyType

from veridian_quant.v2.backtesting.execution import create_open_trade
from veridian_quant.v2.backtesting.sizing import PositionPlan
from veridian_quant.v2.backtesting.trade import Trade, TradeStatus


def test_valid_open_trade_is_created() -> None:
    position_plan = _position_plan()

    trade = create_open_trade(position_plan)

    assert isinstance(trade, Trade)
    assert trade.symbol == position_plan.symbol
    assert trade.strategy_name == position_plan.strategy_name


def test_trade_status_is_open() -> None:
    trade = create_open_trade(_position_plan())

    assert trade.status == TradeStatus.OPEN


def test_provided_trade_id_is_used_when_supplied() -> None:
    trade = create_open_trade(_position_plan(), trade_id="manual-trade-id")

    assert trade.trade_id == "manual-trade-id"


def test_deterministic_trade_id_is_generated_when_omitted() -> None:
    position_plan = _position_plan()

    first_trade = create_open_trade(position_plan)
    second_trade = create_open_trade(position_plan)

    assert first_trade.trade_id == "S1_ZSCORE_MEAN_REVERSION-RELIANCE-2026-01-15"
    assert second_trade.trade_id == first_trade.trade_id


def test_entry_fields_match_position_plan() -> None:
    position_plan = _position_plan()

    trade = create_open_trade(position_plan)

    assert trade.entry_date == position_plan.entry_date
    assert trade.entry_price == position_plan.entry_price
    assert trade.quantity == position_plan.quantity


def test_trade_stores_risk_metadata_from_position_plan() -> None:
    position_plan = _position_plan()

    trade = create_open_trade(position_plan)

    assert trade.stop_loss == position_plan.stop_loss
    assert trade.target_price == position_plan.target_price
    assert trade.per_share_risk == position_plan.per_share_risk
    assert trade.initial_risk_amount == Decimal("1000")
    assert trade.planned_reward_amount == Decimal("2000")
    assert trade.reward_risk_ratio == Decimal("2")


def test_exit_fields_are_none() -> None:
    trade = create_open_trade(_position_plan())

    assert trade.exit_date is None
    assert trade.exit_price is None
    assert trade.exit_reason is None


def test_position_plan_is_not_mutated() -> None:
    position_plan = _position_plan()
    original = replace(position_plan)

    create_open_trade(position_plan)

    assert position_plan == original


def _position_plan() -> PositionPlan:
    """Build a passive position plan for execution tests."""

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
