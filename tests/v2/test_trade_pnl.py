"""Unit tests for v2 trade-level PnL calculation."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

from veridian_quant.v2.backtesting.pnl import TradePnL, calculate_trade_pnl
from veridian_quant.v2.backtesting.trade import ExitReason, Trade, TradeStatus


def test_valid_gross_pnl_calculation() -> None:
    result = calculate_trade_pnl(_closed_trade())

    assert result is not None
    assert result.gross_pnl == Decimal("2000")


def test_valid_gross_return_percentage() -> None:
    result = calculate_trade_pnl(_closed_trade())

    assert result is not None
    assert result.gross_return_pct == Decimal("10.0")


def test_total_cost_calculation() -> None:
    result = calculate_trade_pnl(_closed_trade())

    assert result is not None
    assert result.total_cost == Decimal("80.000")


def test_net_pnl_calculation() -> None:
    result = calculate_trade_pnl(_closed_trade())

    assert result is not None
    assert result.net_pnl == Decimal("1920.000")


def test_net_return_percentage() -> None:
    result = calculate_trade_pnl(_closed_trade())

    assert result is not None
    assert result.net_return_pct == Decimal("9.600")


def test_losing_trade_calculation() -> None:
    result = calculate_trade_pnl(_closed_trade(exit_price=Decimal("95")))

    assert result is not None
    assert result.gross_pnl == Decimal("-1000")
    assert result.gross_return_pct == Decimal("-5.00")
    assert result.total_cost == Decimal("80.000")
    assert result.net_pnl == Decimal("-1080.000")
    assert result.net_return_pct == Decimal("-5.400")


def test_returns_none_for_open_trade() -> None:
    trade = replace(_closed_trade(), status=TradeStatus.OPEN)

    assert calculate_trade_pnl(trade) is None


def test_returns_none_for_missing_exit_fields() -> None:
    trade = _closed_trade()

    assert calculate_trade_pnl(replace(trade, exit_date=None)) is None
    assert calculate_trade_pnl(replace(trade, exit_price=None)) is None
    assert calculate_trade_pnl(replace(trade, exit_reason=None)) is None


def test_returns_none_for_invalid_quantity() -> None:
    assert calculate_trade_pnl(_closed_trade(quantity=0)) is None
    assert calculate_trade_pnl(_closed_trade(quantity=-1)) is None


def test_returns_none_for_invalid_prices() -> None:
    assert calculate_trade_pnl(_closed_trade(entry_price=Decimal("0"))) is None
    assert calculate_trade_pnl(_closed_trade(entry_price=Decimal("-1"))) is None
    assert calculate_trade_pnl(_closed_trade(exit_price=Decimal("0"))) is None
    assert calculate_trade_pnl(_closed_trade(exit_price=Decimal("-1"))) is None


def test_returns_none_for_negative_round_trip_cost() -> None:
    result = calculate_trade_pnl(_closed_trade(), round_trip_cost_pct=Decimal("-0.001"))

    assert result is None


def test_trade_is_not_mutated() -> None:
    trade = _closed_trade()
    original = replace(trade)

    calculate_trade_pnl(trade)

    assert trade == original


def test_monetary_fields_are_decimal() -> None:
    result = calculate_trade_pnl(_closed_trade())

    assert isinstance(result, TradePnL)
    assert isinstance(result.entry_price, Decimal)
    assert isinstance(result.exit_price, Decimal)
    assert isinstance(result.gross_pnl, Decimal)
    assert isinstance(result.gross_return_pct, Decimal)
    assert isinstance(result.total_cost, Decimal)
    assert isinstance(result.net_pnl, Decimal)
    assert isinstance(result.net_return_pct, Decimal)


def test_trade_pnl_preserves_trade_risk_metadata() -> None:
    result = calculate_trade_pnl(
        replace(
            _closed_trade(),
            stop_loss=Decimal("95"),
            target_price=Decimal("110"),
            per_share_risk=Decimal("5"),
            initial_risk_amount=Decimal("1000"),
            planned_reward_amount=Decimal("2000"),
            reward_risk_ratio=Decimal("2"),
        )
    )

    assert result is not None
    assert result.stop_loss == Decimal("95")
    assert result.target_price == Decimal("110")
    assert result.per_share_risk == Decimal("5")
    assert result.initial_risk_amount == Decimal("1000")
    assert result.planned_reward_amount == Decimal("2000")
    assert result.reward_risk_ratio == Decimal("2")


def _closed_trade(
    entry_price: Decimal = Decimal("100"),
    exit_price: Decimal = Decimal("110"),
    quantity: int = 200,
) -> Trade:
    """Build a passive closed trade for PnL tests."""

    return Trade(
        trade_id="S1_ZSCORE_MEAN_REVERSION-RELIANCE-2026-01-15",
        symbol="RELIANCE",
        entry_date=date(2026, 1, 15),
        entry_price=entry_price,
        quantity=quantity,
        status=TradeStatus.CLOSED,
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        exit_date=date(2026, 1, 20),
        exit_price=exit_price,
        exit_reason=ExitReason.TARGET_HIT,
    )
