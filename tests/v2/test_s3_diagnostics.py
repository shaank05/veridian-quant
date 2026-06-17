"""Tests for S3 accepted-trade diagnostics."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from tempfile import TemporaryDirectory
from types import MappingProxyType

import pandas as pd

from veridian_quant.v2.backtesting.ledger import EquityPoint, PortfolioLedger
from veridian_quant.v2.backtesting.pnl import TradePnL
from veridian_quant.v2.backtesting.portfolio_runner import PortfolioBacktestResult
from veridian_quant.v2.backtesting.trade import ExitReason
from veridian_quant.v2.data.models import Signal, SignalType
from veridian_quant.v2.reporting.exporters import export_portfolio_backtest_csvs
from veridian_quant.v2.reporting.s3_diagnostics import (
    S3_FAILURE_AUDIT_BY_YEAR_COLUMNS,
    S3_FILTER_SIMULATION_COLUMNS,
    build_s3_context_bucket_summary_rows,
    build_s3_failure_audit_by_exit_reason_rows,
    build_s3_failure_audit_by_month_rows,
    build_s3_failure_audit_by_symbol_rows,
    build_s3_failure_audit_by_year_rows,
    build_s3_filter_simulation_rows,
)


def test_non_s3_rows_return_empty_diagnostics() -> None:
    rows = build_s3_filter_simulation_rows(
        [
            _row(
                "s1",
                date(2025, 1, 10),
                Decimal("100"),
                Decimal("1"),
                strategy_name="S1_ZSCORE_MEAN_REVERSION",
            )
        ]
    )

    assert rows == []


def test_filter_simulation_counts_and_delta_vs_baseline() -> None:
    rows = build_s3_filter_simulation_rows(_rows())
    atr_row = _filter(rows, "exclude_atr14_pct_above_5")

    assert atr_row["kept_trades"] == 3
    assert atr_row["rejected_trades"] == 1
    assert atr_row["kept_net_pnl"] == Decimal("200")
    assert atr_row["rejected_net_pnl"] == Decimal("-300")
    assert atr_row["delta_net_pnl_vs_baseline"] == Decimal("300")


def test_strict_atr_filter_can_improve_deterministic_example() -> None:
    rows = build_s3_filter_simulation_rows(_rows())
    strict_atr = _filter(rows, "exclude_atr14_pct_above_5")

    assert strict_atr["kept_net_pnl"] > Decimal("-100")
    assert strict_atr["kept_profit_factor"] == Decimal("3")


def test_context_bucket_summary_places_trades_in_expected_buckets() -> None:
    rows = build_s3_context_bucket_summary_rows(_rows())
    bucket = next(
        row
        for row in rows
        if row["bucket_dimension"] == "close_vs_sma50_pct"
        and row["bucket"] == "minus_3_to_0"
    )

    assert bucket["trades"] == 2
    assert bucket["net_pnl"] == Decimal("-400")


def test_by_year_audit_groups_trades_by_entry_year() -> None:
    rows = build_s3_failure_audit_by_year_rows(_rows())
    row_2025 = next(row for row in rows if row["year"] == 2025)

    assert row_2025["trades"] == 3
    assert row_2025["net_pnl"] == Decimal("-200")
    assert row_2025["target_hit_count"] == 1
    assert row_2025["stop_loss_count"] == 1
    assert row_2025["time_stop_count"] == 1


def test_by_month_audit_groups_trades_by_entry_month_label() -> None:
    rows = build_s3_failure_audit_by_month_rows(_rows())
    jan = next(row for row in rows if row["month"] == "2025-01")

    assert jan["trades"] == 2
    assert jan["net_pnl"] == Decimal("-100")


def test_by_exit_reason_audit_groups_correctly() -> None:
    rows = build_s3_failure_audit_by_exit_reason_rows(_rows())
    stop_loss = next(row for row in rows if row["exit_reason"] == "stop_loss_hit")

    assert stop_loss["trades"] == 1
    assert stop_loss["net_pnl"] == Decimal("-300")
    assert stop_loss["average_r_multiple"] == Decimal("-1.5")


def test_by_symbol_audit_groups_and_sorts_by_net_pnl_descending() -> None:
    rows = build_s3_failure_audit_by_symbol_rows(_rows())

    assert rows[0]["symbol"] == "BBB"
    assert rows[0]["net_pnl"] == Decimal("100")
    assert rows[1]["symbol"] == "AAA"


def test_exporter_writes_all_s3_diagnostic_files() -> None:
    with TemporaryDirectory() as temp_dir:
        paths = export_portfolio_backtest_csvs(_result(), temp_dir)

        for name in (
            "s3_filter_simulation",
            "s3_filter_simulation_by_year",
            "s3_context_bucket_summary",
            "s3_failure_audit_by_year",
            "s3_failure_audit_by_month",
            "s3_failure_audit_by_exit_reason",
            "s3_failure_audit_by_symbol",
        ):
            assert paths[name].exists()


def test_exporter_preserves_empty_s3_headers_for_non_s3_result() -> None:
    with TemporaryDirectory() as temp_dir:
        paths = export_portfolio_backtest_csvs(_result(strategy_name="S1_ZSCORE"), temp_dir)

        filter_simulation = pd.read_csv(paths["s3_filter_simulation"])
        by_year = pd.read_csv(paths["s3_failure_audit_by_year"])

        assert list(filter_simulation.columns) == S3_FILTER_SIMULATION_COLUMNS
        assert filter_simulation.empty
        assert list(by_year.columns) == S3_FAILURE_AUDIT_BY_YEAR_COLUMNS
        assert by_year.empty


def test_exporter_does_not_mutate_result_object() -> None:
    result = _result()
    original = replace(result)

    with TemporaryDirectory() as temp_dir:
        export_portfolio_backtest_csvs(result, temp_dir)

    assert result == original


def _filter(rows: list[dict[str, object]], filter_name: str) -> dict[str, object]:
    return next(row for row in rows if row["filter_name"] == filter_name)


def _rows() -> list[dict[str, object]]:
    return [
        _row(
            "loss-high-atr",
            date(2025, 1, 10),
            Decimal("-300"),
            Decimal("-1.5"),
            symbol="AAA",
            exit_reason="stop_loss_hit",
            atr14_pct=Decimal("7"),
            close_vs_sma50_pct=Decimal("-2"),
        ),
        _row(
            "win-low-atr",
            date(2025, 1, 20),
            Decimal("200"),
            Decimal("2"),
            symbol="AAA",
            exit_reason="target_hit",
            atr14_pct=Decimal("4"),
            close_vs_sma50_pct=Decimal("2"),
        ),
        _row(
            "time-stop",
            date(2025, 2, 5),
            Decimal("-100"),
            Decimal("-0.5"),
            symbol="AAA",
            exit_reason="time_stop",
            atr14_pct=Decimal("5"),
            close_vs_sma50_pct=Decimal("-1"),
        ),
        _row(
            "next-year",
            date(2026, 3, 5),
            Decimal("100"),
            Decimal("1"),
            symbol="BBB",
            atr14_pct=Decimal("3"),
            close_vs_sma50_pct=Decimal("6"),
        ),
    ]


def _row(
    trade_id: str,
    entry_date: date,
    net_pnl: Decimal,
    r_multiple: Decimal | None,
    strategy_name: str = "S3_TREND_PULLBACK_CONTINUATION",
    symbol: str = "AAA",
    exit_reason: str = "target_hit",
    atr14_pct: Decimal = Decimal("4"),
    close_vs_sma50_pct: Decimal = Decimal("2"),
) -> dict[str, object]:
    return {
        "trade_id": trade_id,
        "symbol": symbol,
        "strategy_name": strategy_name,
        "strategy_family": strategy_name,
        "entry_date": entry_date,
        "exit_date": entry_date,
        "exit_reason": exit_reason,
        "net_pnl": net_pnl,
        "r_multiple": r_multiple,
        "close_vs_sma50_pct": close_vs_sma50_pct,
        "close_vs_sma200_pct": Decimal("4"),
        "sma50_slope_20d_pct": Decimal("0.8"),
        "sma200_slope_20d_pct": Decimal("1.2"),
        "return_3d_pct": Decimal("-2"),
        "return_5d_pct": Decimal("-4"),
        "return_10d_pct": Decimal("-5"),
        "drawdown_20d_pct": Decimal("-6"),
        "drawdown_60d_pct": Decimal("-9"),
        "close_vs_20d_high_pct": Decimal("-4"),
        "close_vs_60d_low_pct": Decimal("12"),
        "is_60d_low": False,
        "atr14_pct": atr14_pct,
        "atr14_change_5d_pct": Decimal("10"),
    }


def _result(strategy_name: str = "S3_TREND_PULLBACK_CONTINUATION") -> PortfolioBacktestResult:
    trade_pnls = tuple(
        TradePnL(
            trade_id=row["trade_id"],
            symbol=row["symbol"],
            strategy_name=strategy_name,
            entry_date=row["entry_date"],
            exit_date=row["exit_date"],
            entry_price=Decimal("100"),
            exit_price=Decimal("101"),
            quantity=10,
            gross_pnl=row["net_pnl"],
            gross_return_pct=Decimal("1"),
            total_cost=Decimal("0"),
            net_pnl=row["net_pnl"],
            net_return_pct=Decimal("1"),
            exit_reason=ExitReason.TARGET_HIT,
            initial_risk_amount=Decimal("100"),
        )
        for row in _rows()[:2]
    )
    signals = tuple(
        Signal(
            symbol=pnl.symbol,
            signal_type=SignalType.LONG,
            generated_on=date(2025, 1, 9),
            strategy_name=strategy_name,
            reason="fixture",
            metadata=MappingProxyType(
                {
                    "close_vs_sma50_pct": Decimal("2"),
                    "atr14_pct": Decimal("4"),
                    "return_3d_pct": Decimal("-2"),
                    "return_5d_pct": Decimal("-4"),
                    "drawdown_20d_pct": Decimal("-6"),
                    "close_vs_60d_low_pct": Decimal("12"),
                    "is_60d_low": False,
                    "strategy_family": strategy_name,
                }
            ),
        )
        for pnl in trade_pnls
    )
    ledger = PortfolioLedger(
        starting_equity=Decimal("100000"),
        current_equity=Decimal("99900"),
        realized_pnl=Decimal("-100"),
        trade_pnls=trade_pnls,
        equity_curve=(
            EquityPoint(
                date=date(2025, 1, 20),
                equity=Decimal("99900"),
                realized_pnl=Decimal("-100"),
            ),
        ),
    )
    return PortfolioBacktestResult(
        strategy_name=strategy_name,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
        starting_equity=ledger.starting_equity,
        ending_equity=ledger.current_equity,
        symbols=("AAA",),
        trade_pnls=trade_pnls,
        trades=(),
        signals=signals,
        rejected_signals=(),
        ledger=ledger,
    )
