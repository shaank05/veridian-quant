"""Unit tests for v2 S1 backtest progress logging."""

from contextlib import redirect_stdout
from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from veridian_quant.v2.backtesting.portfolio_runner import (
    run_s1_portfolio_backtest,
)
from veridian_quant.v2.reporting.progress import ProgressReporter
from veridian_quant.v2.run_s1_backtest import main


def test_quiet_mode_produces_minimal_output() -> None:
    output = _run_cli_with_patches(
        [
            "--start-date",
            "2026-01-01",
            "--end-date",
            "2026-01-20",
            "--symbols",
            "RELIANCE",
            "--verbosity",
            "quiet",
        ]
    )

    lines = [line for line in output.splitlines() if line]
    assert len(lines) == 1
    assert lines[0].startswith("Completed S1 backtest. Wrote 1 CSV files to ")


def test_normal_mode_includes_startup_and_completion_messages() -> None:
    output = _run_cli_with_patches(
        [
            "--start-date",
            "2026-01-01",
            "--end-date",
            "2026-01-20",
            "--symbols",
            "RELIANCE",
            "--verbosity",
            "normal",
        ]
    )

    assert "Starting S1 backtest 2026-01-01 to 2026-01-20" in output
    assert "Loading OHLCV data..." in output
    assert "Finished loading OHLCV data." in output
    assert "Loaded symbols: 1" in output
    assert "Running portfolio backtest..." in output
    assert "Finished portfolio backtest." in output
    assert "CSV export location:" in output
    assert "Completed S1 backtest." in output


def test_verbose_mode_includes_signal_trade_exit_and_rejected_messages() -> None:
    stream = StringIO()
    reporter = ProgressReporter("verbose", stream=stream)

    run_s1_portfolio_backtest(
        data_by_symbol={"RELIANCE": _two_signal_frame()},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 20),
        starting_equity=Decimal("100000"),
        risk_per_trade=Decimal("0.01"),
        max_concurrent_positions=5,
        zscore_window=3,
        entry_threshold=-1.0,
        atr_window=1,
        atr_multiplier=Decimal("10"),
        reward_risk_ratio=Decimal("1"),
        max_holding_sessions=20,
        round_trip_cost_pct=Decimal("0"),
        progress_reporter=reporter,
    )

    output = stream.getvalue()
    assert "[SIGNAL]" in output
    assert "[TRADE]" in output
    assert "[EXIT]" in output
    assert "[REJECTED]" in output
    assert "ACTIVE_SYMBOL_TRADE_EXISTS" in output


def test_running_with_reporter_does_not_alter_result_values() -> None:
    kwargs = {
        "data_by_symbol": {"RELIANCE": _two_signal_frame()},
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 1, 20),
        "starting_equity": Decimal("100000"),
        "risk_per_trade": Decimal("0.01"),
        "max_concurrent_positions": 5,
        "zscore_window": 3,
        "entry_threshold": -1.0,
        "atr_window": 1,
        "atr_multiplier": Decimal("10"),
        "reward_risk_ratio": Decimal("1"),
        "max_holding_sessions": 20,
        "round_trip_cost_pct": Decimal("0"),
    }

    without_reporter = run_s1_portfolio_backtest(**kwargs)
    with_reporter = run_s1_portfolio_backtest(
        **kwargs,
        progress_reporter=ProgressReporter("verbose", stream=StringIO()),
    )

    assert with_reporter == without_reporter


def _run_cli_with_patches(args: list[str]) -> str:
    """Run CLI main with external dependencies patched out."""

    output = StringIO()
    fake_result = _fake_result()

    class FakeLoader:
        def __init__(self, engine):
            self.engine = engine

        def load_symbols(self, symbols, start_date, end_date):
            return {"RELIANCE": _two_signal_frame()}

        def load_all_available_symbols(self, start_date, end_date):
            return {"RELIANCE": _two_signal_frame()}

    with (
        patch("veridian_quant.v2.run_s1_backtest._get_database_engine", lambda: object()),
        patch("veridian_quant.v2.run_s1_backtest.SQLAlchemyDailyOHLCVLoader", FakeLoader),
        patch("veridian_quant.v2.run_s1_backtest.run_s1_portfolio_backtest", lambda **kwargs: fake_result),
        patch(
            "veridian_quant.v2.run_s1_backtest.export_portfolio_backtest_csvs",
            lambda result, output_dir: {"summary": Path(output_dir) / "summary.csv"},
        ),
        redirect_stdout(output),
    ):
        assert main(args) == 0
    return output.getvalue()


def _fake_result() -> SimpleNamespace:
    """Build a tiny fake result for CLI progress tests."""

    return SimpleNamespace(
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 20),
        starting_equity=Decimal("100000"),
        ending_equity=Decimal("100000"),
        symbols=("RELIANCE",),
        trade_pnls=(),
        trades=(),
        signals=(),
        rejected_signals=(),
        ledger=None,
    )


def _two_signal_frame() -> pd.DataFrame:
    """Build data with two signals while the first same-symbol trade is active."""

    return _frame([10, 12, 14, 8, 7, 8, 9, 11, 13, 15, 9, 10, 11, 12, 13, 14])


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
