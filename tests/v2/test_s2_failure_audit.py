"""Tests for S2 failure-audit diagnostics."""

from datetime import date
from decimal import Decimal
from tempfile import TemporaryDirectory
from types import MappingProxyType

import pandas as pd

from veridian_quant.v2.backtesting.ledger import PortfolioLedger
from veridian_quant.v2.backtesting.portfolio_runner import PortfolioBacktestResult
from veridian_quant.v2.data.models import Signal, SignalType
from veridian_quant.v2.reporting.exporters import export_portfolio_backtest_csvs
from veridian_quant.v2.reporting.s2_failure_audit import (
    S2_FAILURE_AUDIT_BY_YEAR_COLUMNS,
    S2_FAILURE_AUDIT_COMPARISON_COLUMNS,
    build_s2_failure_audit_by_exit_reason_rows,
    build_s2_failure_audit_by_month_rows,
    build_s2_failure_audit_by_state_component_rows,
    build_s2_failure_audit_by_state_label_rows,
    build_s2_failure_audit_by_symbol_rows,
    build_s2_failure_audit_by_year_rows,
    build_s2_failure_audit_context_comparison_rows,
)


def test_empty_result_writes_empty_failure_audit_with_headers() -> None:
    with TemporaryDirectory() as temp_dir:
        paths = export_portfolio_backtest_csvs(_empty_result(), temp_dir)

        by_year = pd.read_csv(paths["s2_failure_audit_by_year"])

        assert list(by_year.columns) == S2_FAILURE_AUDIT_BY_YEAR_COLUMNS
        assert by_year.empty


def test_non_s2_result_writes_empty_failure_audit_with_headers() -> None:
    with TemporaryDirectory() as temp_dir:
        paths = export_portfolio_backtest_csvs(_empty_result("S1_ZSCORE"), temp_dir)

        state_label = pd.read_csv(paths["s2_failure_audit_by_state_label"])

        assert list(state_label.columns) == S2_FAILURE_AUDIT_COMPARISON_COLUMNS
        assert state_label.empty


def test_year_audit_groups_trades_by_entry_year() -> None:
    rows = build_s2_failure_audit_by_year_rows(_rows())

    row_2025 = next(row for row in rows if row["year"] == 2025)

    assert row_2025["trades"] == 3
    assert row_2025["net_pnl"] == Decimal("-400")
    assert row_2025["stop_loss_trades"] == 1
    assert row_2025["stop_gap_trades"] == 1
    assert row_2025["target_hit_trades"] == 1
    assert row_2025["time_stop_trades"] == 0


def test_month_audit_computes_cumulative_year_pnl() -> None:
    rows = build_s2_failure_audit_by_month_rows(_rows())

    jan = next(row for row in rows if row["year"] == 2025 and row["month"] == 1)
    feb = next(row for row in rows if row["year"] == 2025 and row["month"] == 2)

    assert jan["net_pnl"] == Decimal("-500")
    assert jan["cumulative_year_pnl"] == Decimal("-500")
    assert feb["net_pnl"] == Decimal("100")
    assert feb["cumulative_year_pnl"] == Decimal("-400")


def test_state_label_audit_identifies_good_pre_target_bad_target_bucket() -> None:
    rows = build_s2_failure_audit_by_state_label_rows(_rows())
    row = next(
        row
        for row in rows
        if row["bucket"] == "RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW"
    )

    assert row["pre_target_avg_r"] == Decimal("1.5")
    assert row["target_avg_r"] == Decimal("-2.0")
    assert row["failure_score"] == Decimal("3.5")
    assert row["weighted_failure_score"] > 0


def test_state_component_audit_parses_ret_vol_dd_low_components() -> None:
    rows = build_s2_failure_audit_by_state_component_rows(_rows())

    assert _component(rows, "ret_state", "RET_UP")["target_trades"] == 2
    assert _component(rows, "vol_state", "VOL_MID")["target_trades"] == 2
    assert _component(rows, "dd_state", "DD_SHALLOW")["target_trades"] == 2
    assert _component(rows, "low_state", "LOW_FAR_FROM_LOW")["target_trades"] == 1


def test_exit_reason_audit_groups_correctly() -> None:
    rows = build_s2_failure_audit_by_exit_reason_rows(_rows())
    stop_loss = next(row for row in rows if row["bucket"] == "stop_loss_hit")

    assert stop_loss["target_trades"] == 1
    assert stop_loss["target_net_pnl"] == Decimal("-500")


def test_symbol_audit_groups_correctly() -> None:
    rows = build_s2_failure_audit_by_symbol_rows(_rows())
    aaa = next(row for row in rows if row["bucket"] == "AAA")

    assert aaa["pre_target_trades"] == 2
    assert aaa["target_trades"] == 2
    assert aaa["target_net_pnl"] == Decimal("-400")


def test_context_comparison_handles_missing_context_columns_safely() -> None:
    rows = build_s2_failure_audit_context_comparison_rows(
        [
            _row(
                "pre",
                date(2024, 1, 10),
                Decimal("100"),
                Decimal("1"),
                include_context=False,
            ),
            _row(
                "target",
                date(2025, 1, 10),
                Decimal("-100"),
                Decimal("-1"),
                include_context=False,
            ),
        ]
    )

    assert rows == []


def test_context_comparison_uses_available_context_columns() -> None:
    rows = build_s2_failure_audit_context_comparison_rows(_rows())
    row = next(
        row
        for row in rows
        if row["bucket_type"] == "stock_above_sma50"
        and row["bucket"] == "true"
    )

    assert row["pre_target_trades"] == 2
    assert row["target_trades"] == 3
    assert row["failure_score"] > 0


def test_profit_factor_handles_zero_losses() -> None:
    rows = build_s2_failure_audit_by_year_rows(
        [
            _row("win-1", date(2025, 1, 10), Decimal("100"), Decimal("1")),
            _row("win-2", date(2025, 2, 10), Decimal("200"), Decimal("2")),
        ]
    )

    assert rows[0]["profit_factor"] is None


def test_exporter_writes_all_failure_audit_files() -> None:
    with TemporaryDirectory() as temp_dir:
        paths = export_portfolio_backtest_csvs(_empty_result(), temp_dir)

        for name in (
            "s2_failure_audit_by_year",
            "s2_failure_audit_by_month",
            "s2_failure_audit_by_state_label",
            "s2_failure_audit_by_state_component",
            "s2_failure_audit_by_exit_reason",
            "s2_failure_audit_by_symbol",
            "s2_failure_audit_context_comparison",
        ):
            assert paths[name].exists()


def _component(
    rows: list[dict[str, object]],
    component_type: str,
    component_value: str,
) -> dict[str, object]:
    return next(
        row
        for row in rows
        if row["component_type"] == component_type
        and row["component_value"] == component_value
    )


def _rows() -> list[dict[str, object]]:
    label = "RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW"
    return [
        _row(
            "pre-1",
            date(2023, 12, 10),
            Decimal("100"),
            Decimal("1"),
            symbol="AAA",
            state_label=label,
        ),
        _row(
            "pre-2",
            date(2024, 6, 10),
            Decimal("200"),
            Decimal("2"),
            symbol="AAA",
            state_label=label,
        ),
        _row(
            "target-loss",
            date(2025, 1, 10),
            Decimal("-500"),
            Decimal("-2"),
            symbol="AAA",
            exit_reason="stop_loss_hit",
            state_label=label,
        ),
        _row(
            "target-win",
            date(2025, 2, 10),
            Decimal("100"),
            Decimal("1"),
            symbol="AAA",
            state_label="RET_UP|VOL_MID|DD_SHALLOW|LOW_NEAR",
        ),
        _row(
            "target-gap",
            date(2025, 1, 20),
            Decimal("-0"),
            None,
            symbol="BBB",
            exit_reason="stop_gap_hit",
            state_label="RET_FLAT|VOL_HIGH|DD_MID|LOW_NEAR",
        ),
    ]


def _row(
    trade_id: str,
    entry_date: date,
    net_pnl: Decimal,
    r_multiple: Decimal | None,
    symbol: str = "AAA",
    exit_reason: str = "target_hit",
    state_label: str = "RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW",
    include_context: bool = True,
) -> dict[str, object]:
    row = {
        "trade_id": trade_id,
        "symbol": symbol,
        "strategy_name": "S2_MARKOV_STATE_TRANSITION",
        "strategy_family": "S2_MARKOV_STATE_TRANSITION",
        "entry_date": entry_date,
        "exit_date": entry_date,
        "exit_reason": exit_reason,
        "net_pnl": net_pnl,
        "r_multiple": r_multiple,
        "state_label": state_label,
    }
    if not include_context:
        return row
    row.update(
        {
        "stock_close_vs_sma50_pct": Decimal("5"),
        "stock_close_vs_sma200_pct": Decimal("5"),
        "stock_sma50_slope_20d_pct": Decimal("1"),
        "stock_sma200_slope_20d_pct": Decimal("1"),
        "nifty_close_vs_sma50_pct": Decimal("1"),
        "nifty_close_vs_sma200_pct": Decimal("1"),
        "nifty_sma50_slope_20d_pct": Decimal("1"),
        "nifty_sma200_slope_20d_pct": Decimal("1"),
        "relative_strength_20d_vs_nifty": Decimal("1"),
        "stock_is_20d_low": False,
        "stock_atr14_pct": Decimal("3"),
        "stock_drawdown_60d_pct": Decimal("-6"),
        "stock_consecutive_down_closes": 2,
        "stock_signal_day_return_pct": Decimal("-3"),
        "stock_return_5d_pct": Decimal("-4"),
        }
    )
    return row


def _empty_result(strategy_name: str = "S2_MARKOV_STATE_TRANSITION") -> PortfolioBacktestResult:
    ledger = PortfolioLedger(
        starting_equity=Decimal("100000"),
        current_equity=Decimal("100000"),
        realized_pnl=Decimal("0"),
        trade_pnls=(),
        equity_curve=(),
    )
    return PortfolioBacktestResult(
        strategy_name=strategy_name,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        starting_equity=ledger.starting_equity,
        ending_equity=ledger.current_equity,
        symbols=(),
        trade_pnls=(),
        trades=(),
        signals=(
            Signal(
                symbol="AAA",
                signal_type=SignalType.LONG,
                generated_on=date(2025, 1, 1),
                strategy_name=strategy_name,
                reason="empty fixture",
                metadata=MappingProxyType({}),
            ),
        ),
        ledger=ledger,
    )
