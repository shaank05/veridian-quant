"""Unit tests for v2 passive portfolio ledger accounting."""

from datetime import date
from decimal import Decimal

from veridian_quant.v2.backtesting.ledger import (
    EquityPoint,
    PortfolioLedger,
    apply_trade_pnl,
    create_portfolio_ledger,
)
from veridian_quant.v2.backtesting.pnl import TradePnL
from veridian_quant.v2.backtesting.trade import ExitReason


def test_valid_ledger_creation() -> None:
    ledger = create_portfolio_ledger(Decimal("100000"))

    assert isinstance(ledger, PortfolioLedger)
    assert ledger.starting_equity == Decimal("100000")
    assert ledger.current_equity == Decimal("100000")
    assert ledger.realized_pnl == Decimal("0")
    assert ledger.trade_pnls == ()
    assert ledger.equity_curve == ()


def test_invalid_starting_equity_raises_clear_value_error() -> None:
    for starting_equity in (Decimal("0"), Decimal("-1")):
        try:
            create_portfolio_ledger(starting_equity)
        except ValueError as error:
            assert str(error) == "starting_equity must be positive"
        else:
            raise AssertionError("expected invalid starting equity to raise ValueError")


def test_applying_winning_trade_increases_equity() -> None:
    ledger = create_portfolio_ledger(Decimal("100000"))

    updated = apply_trade_pnl(ledger, _trade_pnl(net_pnl=Decimal("1500")))

    assert updated is not None
    assert updated.current_equity == Decimal("101500")


def test_applying_losing_trade_decreases_equity() -> None:
    ledger = create_portfolio_ledger(Decimal("100000"))

    updated = apply_trade_pnl(ledger, _trade_pnl(net_pnl=Decimal("-1500")))

    assert updated is not None
    assert updated.current_equity == Decimal("98500")


def test_realized_pnl_accumulates() -> None:
    ledger = create_portfolio_ledger(Decimal("100000"))
    first = apply_trade_pnl(ledger, _trade_pnl(net_pnl=Decimal("1500")))
    assert first is not None

    second = apply_trade_pnl(first, _trade_pnl(net_pnl=Decimal("-400")))

    assert second is not None
    assert second.realized_pnl == Decimal("1100")


def test_trade_pnls_appends_without_mutating_previous_ledger() -> None:
    ledger = create_portfolio_ledger(Decimal("100000"))
    trade_pnl = _trade_pnl(net_pnl=Decimal("1500"))

    updated = apply_trade_pnl(ledger, trade_pnl)

    assert updated is not None
    assert ledger.trade_pnls == ()
    assert updated.trade_pnls == (trade_pnl,)


def test_equity_curve_appends_exit_date_point() -> None:
    ledger = create_portfolio_ledger(Decimal("100000"))
    trade_pnl = _trade_pnl(exit_date=date(2026, 1, 20), net_pnl=Decimal("1500"))

    updated = apply_trade_pnl(ledger, trade_pnl)

    assert updated is not None
    assert updated.equity_curve == (
        EquityPoint(
            date=date(2026, 1, 20),
            equity=Decimal("101500"),
            realized_pnl=Decimal("1500"),
        ),
    )


def test_returns_none_if_equity_would_become_zero_or_negative() -> None:
    ledger = create_portfolio_ledger(Decimal("100000"))

    assert apply_trade_pnl(ledger, _trade_pnl(net_pnl=Decimal("-100000"))) is None
    assert apply_trade_pnl(ledger, _trade_pnl(net_pnl=Decimal("-100001"))) is None


def test_decimal_monetary_fields() -> None:
    ledger = create_portfolio_ledger("100000")
    updated = apply_trade_pnl(ledger, _trade_pnl(net_pnl=Decimal("1500")))

    assert updated is not None
    assert isinstance(updated.starting_equity, Decimal)
    assert isinstance(updated.current_equity, Decimal)
    assert isinstance(updated.realized_pnl, Decimal)
    assert isinstance(updated.equity_curve[0].equity, Decimal)
    assert isinstance(updated.equity_curve[0].realized_pnl, Decimal)


def test_original_ledger_is_not_mutated() -> None:
    ledger = create_portfolio_ledger(Decimal("100000"))
    original = PortfolioLedger(
        starting_equity=ledger.starting_equity,
        current_equity=ledger.current_equity,
        realized_pnl=ledger.realized_pnl,
        trade_pnls=ledger.trade_pnls,
        equity_curve=ledger.equity_curve,
    )

    apply_trade_pnl(ledger, _trade_pnl(net_pnl=Decimal("1500")))

    assert ledger == original


def _trade_pnl(
    exit_date: date = date(2026, 1, 20),
    net_pnl: Decimal = Decimal("1500"),
) -> TradePnL:
    """Build a passive trade PnL for ledger tests."""

    return TradePnL(
        trade_id="S1_ZSCORE_MEAN_REVERSION-RELIANCE-2026-01-15",
        symbol="RELIANCE",
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        entry_date=date(2026, 1, 15),
        exit_date=exit_date,
        entry_price=Decimal("100"),
        exit_price=Decimal("110"),
        quantity=200,
        gross_pnl=Decimal("2000"),
        gross_return_pct=Decimal("10.0"),
        total_cost=Decimal("500"),
        net_pnl=net_pnl,
        net_return_pct=Decimal("7.5"),
        exit_reason=ExitReason.TARGET_HIT,
    )
