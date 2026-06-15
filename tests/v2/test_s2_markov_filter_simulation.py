"""Tests for S2 Markov-specific diagnostic filter simulations."""

from datetime import date
from decimal import Decimal
from tempfile import TemporaryDirectory
from types import MappingProxyType

import pandas as pd

from veridian_quant.v2.backtesting.ledger import EquityPoint, PortfolioLedger
from veridian_quant.v2.backtesting.pnl import TradePnL
from veridian_quant.v2.backtesting.portfolio_runner import PortfolioBacktestResult
from veridian_quant.v2.backtesting.trade import ExitReason, Trade, TradeStatus
from veridian_quant.v2.data.models import Signal, SignalType
from veridian_quant.v2.reporting.exporters import export_portfolio_backtest_csvs
from veridian_quant.v2.reporting.s2_markov_filter_simulation import (
    S2_MARKOV_FILTER_SIMULATION_COLUMNS,
    build_s2_markov_filter_simulation_by_symbol_rows,
    build_s2_markov_filter_simulation_by_year_rows,
    build_s2_markov_filter_simulation_rejected_trade_rows,
    build_s2_markov_filter_simulation_rows,
    build_s2_markov_state_component_summary_rows,
    build_s2_markov_state_label_summary_rows,
    parse_state_label,
)


def test_s2_markov_filter_simulation_files_are_exported() -> None:
    with TemporaryDirectory() as temp_dir:
        paths = export_portfolio_backtest_csvs(_s1_result(), temp_dir)

        assert paths["s2_markov_filter_simulation"].exists()
        assert paths["s2_markov_filter_simulation_by_year"].exists()
        assert paths["s2_markov_filter_simulation_by_symbol"].exists()
        assert paths["s2_markov_filter_simulation_rejected_trades"].exists()
        assert paths["s2_markov_state_component_summary"].exists()
        assert paths["s2_markov_state_label_summary"].exists()


def test_non_s2_result_writes_empty_s2_markov_simulation_files_with_headers() -> None:
    with TemporaryDirectory() as temp_dir:
        paths = export_portfolio_backtest_csvs(_s1_result(), temp_dir)

        simulation = pd.read_csv(paths["s2_markov_filter_simulation"])

        assert list(simulation.columns) == S2_MARKOV_FILTER_SIMULATION_COLUMNS
        assert simulation.empty


def test_state_label_parser_extracts_components() -> None:
    parsed = parse_state_label(
        "RET_UP|VOL_HIGH|DD_SHALLOW|LOW_FAR_FROM_LOW"
    )

    assert parsed == {
        "ret_state": "RET_UP",
        "vol_state": "VOL_HIGH",
        "dd_state": "DD_SHALLOW",
        "low_state": "LOW_FAR_FROM_LOW",
    }


def test_malformed_state_labels_do_not_crash() -> None:
    parsed = parse_state_label("RET_UP|VOL_HIGH")

    assert parsed == {
        "ret_state": "UNKNOWN",
        "vol_state": "UNKNOWN",
        "dd_state": "UNKNOWN",
        "low_state": "UNKNOWN",
    }
    rows = build_s2_markov_filter_simulation_rows(
        [_row("bad", "BAD_LABEL", net_pnl=Decimal("10"))]
    )
    assert rows


def test_return_state_filters_keep_and_reject_expected_trades() -> None:
    row = _simulation_row("s2_keep_ret_up_or_strong_up")

    assert row["kept_trades"] == 2
    assert row["rejected_trades"] == 3


def test_drawdown_state_filters_keep_and_reject_expected_trades() -> None:
    row = _simulation_row("s2_exclude_dd_deep")

    assert row["kept_trades"] == 4
    assert row["rejected_trades"] == 1


def test_low_distance_filters_keep_and_reject_expected_trades() -> None:
    row = _simulation_row("s2_keep_low_mid_or_far")

    assert row["kept_trades"] == 4
    assert row["rejected_trades"] == 1


def test_observation_count_filters_keep_and_reject_expected_trades() -> None:
    row = _simulation_row("s2_obs_gte_40")

    assert row["kept_trades"] == 2
    assert row["rejected_trades"] == 3


def test_probability_filters_keep_and_reject_expected_trades() -> None:
    row = _simulation_row("s2_prob_gte_0_70")

    assert row["kept_trades"] == 3
    assert row["rejected_trades"] == 2


def test_average_forward_return_filters_keep_and_reject_expected_trades() -> None:
    row = _simulation_row("s2_avg_forward_return_3_to_5")

    assert row["kept_trades"] == 1
    assert row["rejected_trades"] == 4


def test_clean_continuation_combined_filter_behaves_correctly() -> None:
    row = _simulation_row("s2_clean_continuation_v1")

    assert row["kept_trades"] == 3
    assert row["rejected_trades"] == 2


def test_balanced_markov_combined_filter_behaves_correctly() -> None:
    row = _simulation_row("s2_balanced_markov_v1")

    assert row["kept_trades"] == 3
    assert row["rejected_trades"] == 2


def test_by_year_report_groups_correctly() -> None:
    rows = build_s2_markov_filter_simulation_by_year_rows(_rows())
    row = _find(rows, "s2_keep_ret_up_or_strong_up", year=2026)

    assert row["kept_trades"] == 1
    assert row["rejected_trades"] == 1


def test_by_symbol_report_groups_correctly() -> None:
    rows = build_s2_markov_filter_simulation_by_symbol_rows(_rows())
    row = _find(rows, "s2_keep_ret_up_or_strong_up", symbol="AAA")

    assert row["kept_trades"] == 1
    assert row["rejected_trades"] == 1


def test_rejected_trades_report_contains_one_row_per_filter_rejection() -> None:
    rows = build_s2_markov_filter_simulation_rejected_trade_rows(_rows())
    rejected = [
        row
        for row in rows
        if row["filter_name"] == "s2_keep_ret_up_or_strong_up"
    ]

    assert [row["trade_id"] for row in rejected] == ["t2", "t3", "t5"]
    assert rejected[0]["ret_state"] == "RET_FLAT"


def test_state_component_summary_aggregates_correctly() -> None:
    rows = build_s2_markov_state_component_summary_rows(_rows())
    ret_up = next(
        row
        for row in rows
        if row["component_type"] == "ret_state"
        and row["component_bucket"] == "RET_UP"
    )

    assert ret_up["trades"] == 1
    assert ret_up["net_pnl"] == Decimal("100")
    assert ret_up["average_r_multiple"] == Decimal("1")


def test_state_label_summary_aggregates_correctly() -> None:
    rows = build_s2_markov_state_label_summary_rows(_rows())
    label = "RET_UP|VOL_MID|DD_SHALLOW|LOW_MID_RANGE"
    row = next(row for row in rows if row["state_label"] == label)

    assert row["trades"] == 1
    assert row["net_pnl"] == Decimal("100")
    assert row["average_state_observation_count"] == Decimal("15")
    assert row["average_positive_transition_probability"] == Decimal("0.70")


def _simulation_row(filter_name: str) -> dict[str, object]:
    rows = build_s2_markov_filter_simulation_rows(_rows())
    return next(row for row in rows if row["filter_name"] == filter_name)


def _find(
    rows: list[dict[str, object]],
    filter_name: str,
    **criteria: object,
) -> dict[str, object]:
    return next(
        row
        for row in rows
        if row["filter_name"] == filter_name
        and all(row[key] == value for key, value in criteria.items())
    )


def _rows() -> list[dict[str, object]]:
    return [
        _row(
            "t1",
            "RET_UP|VOL_MID|DD_SHALLOW|LOW_MID_RANGE",
            symbol="AAA",
            exit_date=date(2026, 1, 20),
            net_pnl=Decimal("100"),
            r_multiple=Decimal("1.0"),
            state_observation_count=15,
            positive_transition_probability=Decimal("0.70"),
            average_forward_return_pct=Decimal("4"),
        ),
        _row(
            "t2",
            "RET_FLAT|VOL_HIGH|DD_MID|LOW_FAR_FROM_LOW",
            symbol="AAA",
            exit_date=date(2026, 2, 20),
            net_pnl=Decimal("-50"),
            r_multiple=Decimal("-0.5"),
            state_observation_count=20,
            positive_transition_probability=Decimal("0.65"),
            average_forward_return_pct=Decimal("2"),
        ),
        _row(
            "t3",
            "RET_DOWN|VOL_LOW|DD_DEEP|LOW_NEAR",
            symbol="BBB",
            exit_date=date(2025, 1, 20),
            net_pnl=Decimal("-200"),
            r_multiple=Decimal("-2.0"),
            state_observation_count=30,
            positive_transition_probability=Decimal("0.55"),
            average_forward_return_pct=Decimal("1"),
        ),
        _row(
            "t4",
            "RET_STRONG_UP|VOL_HIGH|DD_SHALLOW|LOW_FAR_FROM_LOW",
            symbol="BBB",
            exit_date=date(2025, 2, 20),
            net_pnl=Decimal("300"),
            r_multiple=Decimal("3.0"),
            state_observation_count=40,
            positive_transition_probability=Decimal("0.80"),
            average_forward_return_pct=Decimal("12"),
        ),
        _row(
            "t5",
            "RET_STRONG_DOWN|VOL_MID|DD_MID|LOW_MID_RANGE",
            symbol="CCC",
            exit_date=date(2025, 3, 20),
            net_pnl=Decimal("-25"),
            r_multiple=Decimal("-0.25"),
            state_observation_count=50,
            positive_transition_probability=Decimal("0.75"),
            average_forward_return_pct=Decimal("6"),
        ),
    ]


def _row(
    trade_id: str,
    state_label: str,
    symbol: str = "AAA",
    exit_date: date = date(2026, 1, 20),
    net_pnl: Decimal = Decimal("0"),
    r_multiple: Decimal = Decimal("0"),
    state_observation_count: int = 10,
    positive_transition_probability: Decimal = Decimal("0.60"),
    average_forward_return_pct: Decimal = Decimal("1"),
) -> dict[str, object]:
    return {
        "trade_id": trade_id,
        "symbol": symbol,
        "strategy_name": "S2_MARKOV_STATE_TRANSITION",
        "strategy_family": "S2_MARKOV_STATE_TRANSITION",
        "entry_date": date(2026, 1, 15),
        "exit_date": exit_date,
        "exit_reason": "target_hit",
        "net_pnl": net_pnl,
        "r_multiple": r_multiple,
        "state_label": state_label,
        "state_observation_count": state_observation_count,
        "positive_transition_probability": positive_transition_probability,
        "average_forward_return_pct": average_forward_return_pct,
        "median_forward_return_pct": average_forward_return_pct,
        "current_5d_return_pct": Decimal("2"),
        "current_atr_pct": Decimal("3"),
        "current_drawdown_60d_pct": Decimal("-5"),
        "current_close_vs_60d_low_pct": Decimal("10"),
    }


def _s1_result() -> PortfolioBacktestResult:
    trade = Trade(
        trade_id="s1-trade",
        symbol="AAA",
        entry_date=date(2026, 1, 15),
        entry_price=Decimal("100"),
        quantity=10,
        status=TradeStatus.CLOSED,
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        exit_date=date(2026, 1, 20),
        exit_price=Decimal("110"),
        exit_reason=ExitReason.TARGET_HIT,
        stop_loss=Decimal("95"),
        target_price=Decimal("110"),
        per_share_risk=Decimal("5"),
        initial_risk_amount=Decimal("50"),
        planned_reward_amount=Decimal("100"),
        reward_risk_ratio=Decimal("2"),
    )
    pnl = TradePnL(
        trade_id=trade.trade_id,
        symbol=trade.symbol,
        strategy_name=trade.strategy_name,
        entry_date=trade.entry_date,
        exit_date=trade.exit_date,
        entry_price=trade.entry_price,
        exit_price=trade.exit_price,
        quantity=trade.quantity,
        gross_pnl=Decimal("100"),
        gross_return_pct=Decimal("10"),
        total_cost=Decimal("0"),
        net_pnl=Decimal("100"),
        net_return_pct=Decimal("10"),
        exit_reason=trade.exit_reason,
        stop_loss=trade.stop_loss,
        target_price=trade.target_price,
        per_share_risk=trade.per_share_risk,
        initial_risk_amount=trade.initial_risk_amount,
        planned_reward_amount=trade.planned_reward_amount,
        reward_risk_ratio=trade.reward_risk_ratio,
    )
    signal = Signal(
        symbol=trade.symbol,
        signal_type=SignalType.LONG,
        generated_on=date(2026, 1, 14),
        strategy_name=trade.strategy_name,
        reason="s1 test signal",
        metadata=MappingProxyType({"z_score": -2.5}),
    )
    ledger = PortfolioLedger(
        starting_equity=Decimal("100000"),
        current_equity=Decimal("100100"),
        realized_pnl=Decimal("100"),
        trade_pnls=(pnl,),
        equity_curve=(
            EquityPoint(
                date=date(2026, 1, 20),
                equity=Decimal("100100"),
                realized_pnl=Decimal("100"),
            ),
        ),
    )
    return PortfolioBacktestResult(
        strategy_name=trade.strategy_name,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        starting_equity=ledger.starting_equity,
        ending_equity=ledger.current_equity,
        symbols=(trade.symbol,),
        trade_pnls=(pnl,),
        trades=(trade,),
        signals=(signal,),
        ledger=ledger,
    )
