"""Tests for the S4 CLI runner parser and orchestration."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from veridian_quant.v2.backtesting.portfolio_runner import PortfolioBacktestResult
from veridian_quant.v2.run_s4_backtest import (
    _parse_args,
    _s4_variant_from_cli,
    main,
)
from veridian_quant.v2.strategies.s4_entropy_volatility_compression_breakout import (
    S4_ATR_COMPRESSION_BREAKOUT_V1,
    S4_ENTROPY_GATED_BREAKOUT_V1,
    S4_RANGE_COMPRESSION_BREAKOUT_V1,
    STRATEGY_NAME,
)


def test_cli_parser_accepts_required_args() -> None:
    args = _parse_args(
        [
            "--start-date",
            "2020-01-01",
            "--end-date",
            "2026-04-30",
            "--symbols",
            "reliance,tcs",
            "--output-dir",
            "reports/v2/s4",
            "--verbosity",
            "quiet",
        ]
    )

    assert args.start_date == date(2020, 1, 1)
    assert args.end_date == date(2026, 4, 30)
    assert args.symbols == "reliance,tcs"
    assert args.output_dir == "reports/v2/s4"
    assert args.verbosity == "quiet"


def test_cli_parser_accepts_s4_parameters() -> None:
    args = _parse_args(
        [
            "--start-date",
            "2020-01-01",
            "--end-date",
            "2026-04-30",
            "--symbols",
            "RELIANCE",
            "--atr-window",
            "10",
            "--range-window",
            "15",
            "--breakout-window",
            "30",
            "--percentile-window",
            "80",
            "--entropy-window",
            "12",
            "--compression-threshold",
            "0.25",
            "--entropy-threshold",
            "0.65",
            "--flat-threshold",
            "0.05",
            "--allow-repeated-signals",
            "--starting-equity",
            "2000000",
            "--risk-per-trade",
            "0.02",
            "--max-concurrent-positions",
            "3",
            "--atr-multiplier",
            "2.5",
            "--reward-risk-ratio",
            "1.8",
            "--max-holding-sessions",
            "15",
            "--round-trip-cost-pct",
            "0.005",
        ]
    )

    assert args.atr_window == 10
    assert args.range_window == 15
    assert args.breakout_window == 30
    assert args.percentile_window == 80
    assert args.entropy_window == 12
    assert args.compression_threshold == 0.25
    assert args.entropy_threshold == 0.65
    assert args.flat_threshold == 0.05
    assert args.allow_repeated_signals is True
    assert args.starting_equity == Decimal("2000000")
    assert args.risk_per_trade == Decimal("0.02")
    assert args.max_concurrent_positions == 3
    assert args.atr_multiplier == Decimal("2.5")
    assert args.reward_risk_ratio == Decimal("1.8")
    assert args.max_holding_sessions == 15
    assert args.round_trip_cost_pct == Decimal("0.005")


def test_cli_parser_maps_each_s4_variant() -> None:
    assert (
        _s4_variant_from_cli("atr_compression_breakout_v1")
        == S4_ATR_COMPRESSION_BREAKOUT_V1
    )
    assert (
        _s4_variant_from_cli("range_compression_breakout_v1")
        == S4_RANGE_COMPRESSION_BREAKOUT_V1
    )
    assert (
        _s4_variant_from_cli("entropy_gated_breakout_v1")
        == S4_ENTROPY_GATED_BREAKOUT_V1
    )
    assert (
        _s4_variant_from_cli(S4_ATR_COMPRESSION_BREAKOUT_V1)
        == S4_ATR_COMPRESSION_BREAKOUT_V1
    )


def test_unknown_s4_variant_fails_validation() -> None:
    with pytest.raises(SystemExit):
        _parse_args(
            [
                "--start-date",
                "2020-01-01",
                "--end-date",
                "2026-04-30",
                "--symbols",
                "RELIANCE",
                "--s4-variant",
                "unknown",
            ]
        )


def test_main_passes_s4_parameters_to_runner_and_exports(monkeypatch, tmp_path) -> None:
    observed: dict[str, object] = {}
    result = PortfolioBacktestResult(
        strategy_name=STRATEGY_NAME,
        start_date=date(2020, 1, 1),
        end_date=date(2026, 4, 30),
        starting_equity=Decimal("2000000"),
        ending_equity=Decimal("2000000"),
        symbols=("RELIANCE", "TCS"),
        strategy_variant=S4_RANGE_COMPRESSION_BREAKOUT_V1,
    )

    class FakeLoader:
        def __init__(self, engine: object) -> None:
            observed["engine"] = engine
            self.lookback_buffer_days = None

        def load_symbols(self, symbols, start_date, end_date):
            observed["loaded_symbols"] = symbols
            observed["load_start_date"] = start_date
            observed["load_end_date"] = end_date
            return {"RELIANCE": _frame(), "TCS": _frame()}

        def load_all_available_symbols(self, start_date, end_date):
            raise AssertionError("should not load all symbols")

        def load_instrument_key(self, instrument_key, start_date, end_date):
            observed["nifty_key"] = instrument_key
            return _frame()

    def fake_runner(**kwargs):
        observed["runner_kwargs"] = kwargs
        return result

    def fake_export(export_result, output_dir, **kwargs):
        observed["export_result"] = export_result
        observed["output_dir"] = output_dir
        observed["export_kwargs"] = kwargs
        return {"summary": Path(output_dir) / "summary.csv"}

    monkeypatch.setattr(
        "veridian_quant.v2.run_s4_backtest._get_database_engine",
        lambda: "engine",
    )
    monkeypatch.setattr(
        "veridian_quant.v2.run_s4_backtest.SQLAlchemyDailyOHLCVLoader",
        FakeLoader,
    )
    monkeypatch.setattr(
        "veridian_quant.v2.run_s4_backtest.run_s4_portfolio_backtest",
        fake_runner,
    )
    monkeypatch.setattr(
        "veridian_quant.v2.run_s4_backtest.export_portfolio_backtest_csvs",
        fake_export,
    )

    exit_code = main(
        [
            "--start-date",
            "2020-01-01",
            "--end-date",
            "2026-04-30",
            "--symbols",
            "reliance,tcs",
            "--output-dir",
            str(tmp_path),
            "--s4-variant",
            "range_compression_breakout_v1",
            "--atr-window",
            "10",
            "--range-window",
            "15",
            "--breakout-window",
            "30",
            "--percentile-window",
            "80",
            "--entropy-window",
            "12",
            "--compression-threshold",
            "0.25",
            "--entropy-threshold",
            "0.65",
            "--flat-threshold",
            "0.05",
            "--allow-repeated-signals",
            "--starting-equity",
            "2000000",
            "--risk-per-trade",
            "0.02",
            "--max-concurrent-positions",
            "3",
            "--atr-multiplier",
            "2.5",
            "--reward-risk-ratio",
            "1.8",
            "--max-holding-sessions",
            "15",
            "--round-trip-cost-pct",
            "0.005",
            "--skip-all-signal-diagnostics",
            "--verbosity",
            "quiet",
        ]
    )

    runner_kwargs = observed["runner_kwargs"]

    assert exit_code == 0
    assert observed["loaded_symbols"] == ["RELIANCE", "TCS"]
    assert runner_kwargs["strategy_variant"] == S4_RANGE_COMPRESSION_BREAKOUT_V1
    assert runner_kwargs["atr_window"] == 10
    assert runner_kwargs["range_window"] == 15
    assert runner_kwargs["breakout_window"] == 30
    assert runner_kwargs["percentile_window"] == 80
    assert runner_kwargs["entropy_window"] == 12
    assert runner_kwargs["compression_threshold"] == 0.25
    assert runner_kwargs["entropy_threshold"] == 0.65
    assert runner_kwargs["flat_threshold"] == 0.05
    assert runner_kwargs["allow_repeated_signals"] is True
    assert runner_kwargs["starting_equity"] == Decimal("2000000")
    assert runner_kwargs["risk_per_trade"] == Decimal("0.02")
    assert runner_kwargs["max_concurrent_positions"] == 3
    assert runner_kwargs["atr_multiplier"] == Decimal("2.5")
    assert runner_kwargs["reward_risk_ratio"] == Decimal("1.8")
    assert runner_kwargs["max_holding_sessions"] == 15
    assert runner_kwargs["round_trip_cost_pct"] == Decimal("0.005")
    assert observed["export_result"] is result
    assert observed["output_dir"] == str(tmp_path)
    assert observed["export_kwargs"]["include_all_signal_diagnostics"] is False
    assert observed["export_kwargs"]["stock_data_by_symbol"] == runner_kwargs[
        "data_by_symbol"
    ]


def test_main_can_load_all_symbols(monkeypatch, tmp_path) -> None:
    observed: dict[str, object] = {}
    result = PortfolioBacktestResult(
        strategy_name=STRATEGY_NAME,
        start_date=date(2020, 1, 1),
        end_date=date(2026, 4, 30),
        starting_equity=Decimal("1000000"),
        ending_equity=Decimal("1000000"),
        symbols=("AAA",),
        strategy_variant=S4_ATR_COMPRESSION_BREAKOUT_V1,
    )

    class FakeLoader:
        def __init__(self, engine: object) -> None:
            self.lookback_buffer_days = None

        def load_symbols(self, symbols, start_date, end_date):
            raise AssertionError("should not load explicit symbols")

        def load_all_available_symbols(self, start_date, end_date):
            observed["load_all"] = (start_date, end_date)
            return {"AAA": _frame()}

        def load_instrument_key(self, instrument_key, start_date, end_date):
            return _frame()

    monkeypatch.setattr(
        "veridian_quant.v2.run_s4_backtest._get_database_engine",
        lambda: "engine",
    )
    monkeypatch.setattr(
        "veridian_quant.v2.run_s4_backtest.SQLAlchemyDailyOHLCVLoader",
        FakeLoader,
    )
    monkeypatch.setattr(
        "veridian_quant.v2.run_s4_backtest.run_s4_portfolio_backtest",
        lambda **kwargs: result,
    )
    monkeypatch.setattr(
        "veridian_quant.v2.run_s4_backtest.export_portfolio_backtest_csvs",
        lambda *args, **kwargs: {"summary": tmp_path / "summary.csv"},
    )

    exit_code = main(
        [
            "--start-date",
            "2020-01-01",
            "--end-date",
            "2026-04-30",
            "--all-symbols",
            "--output-dir",
            str(tmp_path),
            "--verbosity",
            "quiet",
        ]
    )

    assert exit_code == 0
    assert observed["load_all"] == (date(2020, 1, 1), date(2026, 4, 30))


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=3, freq="D"),
            "open": [10.0, 11.0, 12.0],
            "high": [11.0, 12.0, 13.0],
            "low": [9.0, 10.0, 11.0],
            "close": [10.5, 11.5, 12.5],
            "volume": [1000, 1000, 1000],
        }
    )
