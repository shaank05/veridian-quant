"""Tests for the S5 CLI parser and orchestration."""

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from veridian_quant.v2.backtesting.portfolio_runner import PortfolioBacktestResult
from veridian_quant.v2.run_s5_backtest import (
    S5_LOOKBACK_BUFFER_DAYS,
    _parse_args,
    _s5_variant_from_cli,
    main,
)
from veridian_quant.v2.strategies.s5_relative_strength_momentum_rotation import (
    S5_DUAL_MOMENTUM_63_126D_V1,
    S5_SIMPLE_RS_126D_V1,
    S5_VOL_ADJUSTED_RS_V1,
    STRATEGY_NAME,
)


def test_cli_parser_accepts_required_and_s5_arguments() -> None:
    args = _parse_args(
        [
            "--start-date",
            "2020-01-01",
            "--end-date",
            "2026-04-30",
            "--symbols",
            "reliance,tcs",
            "--starting-equity",
            "2000000",
            "--risk-per-trade",
            "0.02",
            "--max-concurrent-positions",
            "3",
            "--s5-variant",
            "dual_momentum_63_126d_v1",
            "--disable-trend-filter",
            "--min-rank-score",
            "0.1",
            "--allow-repeated-signals",
            "--skip-all-signal-diagnostics",
            "--output-dir",
            "reports/v2/s5/test",
        ]
    )

    assert args.start_date == date(2020, 1, 1)
    assert args.end_date == date(2026, 4, 30)
    assert args.starting_equity == Decimal("2000000")
    assert args.risk_per_trade == Decimal("0.02")
    assert args.max_concurrent_positions == 3
    assert args.disable_trend_filter is True
    assert args.min_rank_score == 0.1
    assert args.allow_repeated_signals is True
    assert args.skip_all_signal_diagnostics is True


def test_cli_maps_each_s5_variant() -> None:
    assert _s5_variant_from_cli("simple_rs_126d_v1") == S5_SIMPLE_RS_126D_V1
    assert (
        _s5_variant_from_cli("dual_momentum_63_126d_v1")
        == S5_DUAL_MOMENTUM_63_126D_V1
    )
    assert _s5_variant_from_cli("vol_adjusted_rs_v1") == S5_VOL_ADJUSTED_RS_V1
    assert _s5_variant_from_cli(S5_SIMPLE_RS_126D_V1) == S5_SIMPLE_RS_126D_V1


def test_invalid_cli_variant_exits_clearly() -> None:
    with pytest.raises(SystemExit):
        _parse_args(
            [
                "--start-date",
                "2020-01-01",
                "--end-date",
                "2026-04-30",
                "--symbols",
                "RELIANCE",
                "--s5-variant",
                "unknown",
            ]
        )


def test_main_maps_arguments_and_writes_standard_outputs(monkeypatch, tmp_path) -> None:
    observed: dict[str, object] = {}
    result = PortfolioBacktestResult(
        strategy_name=STRATEGY_NAME,
        start_date=date(2020, 1, 1),
        end_date=date(2026, 4, 30),
        starting_equity=Decimal("1000000"),
        ending_equity=Decimal("1000000"),
        symbols=("RELIANCE", "TCS"),
        strategy_variant=S5_VOL_ADJUSTED_RS_V1,
        candidate_ranking_mode="s5_rank_score_desc",
    )

    class FakeLoader:
        def __init__(self, engine: object) -> None:
            observed["engine"] = engine
            self.lookback_buffer_days = None
            observed["loader"] = self

        def load_symbols(self, symbols, start_date, end_date):
            observed["symbols"] = symbols
            return {symbol: _frame() for symbol in symbols}

        def load_all_available_symbols(self, start_date, end_date):
            raise AssertionError("should not load all symbols")

        def load_instrument_key(self, instrument_key, start_date, end_date):
            return _frame()

    def fake_runner(**kwargs):
        observed["runner_kwargs"] = kwargs
        return result

    monkeypatch.setattr(
        "veridian_quant.v2.run_s5_backtest._get_database_engine",
        lambda: "engine",
    )
    monkeypatch.setattr(
        "veridian_quant.v2.run_s5_backtest.SQLAlchemyDailyOHLCVLoader",
        FakeLoader,
    )
    monkeypatch.setattr(
        "veridian_quant.v2.run_s5_backtest.run_s5_portfolio_backtest",
        fake_runner,
    )

    exit_code = main(
        [
            "--start-date",
            "2020-01-01",
            "--end-date",
            "2026-04-30",
            "--symbols",
            "reliance,tcs",
            "--s5-variant",
            "vol_adjusted_rs_v1",
            "--disable-trend-filter",
            "--allow-repeated-signals",
            "--skip-all-signal-diagnostics",
            "--output-dir",
            str(tmp_path),
            "--verbosity",
            "quiet",
        ]
    )

    kwargs = observed["runner_kwargs"]
    assert exit_code == 0
    assert observed["symbols"] == ["RELIANCE", "TCS"]
    assert observed["loader"].lookback_buffer_days == S5_LOOKBACK_BUFFER_DAYS
    assert kwargs["strategy_variant"] == S5_VOL_ADJUSTED_RS_V1
    assert kwargs["enable_trend_filter"] is False
    assert kwargs["allow_repeated_signals"] is True

    required_files = {
        "summary.csv",
        "yearly_summary.csv",
        "symbol_summary.csv",
        "exit_reason_summary.csv",
        "rejection_summary.csv",
        "r_multiple_summary.csv",
        "r_multiple_by_year.csv",
        "trade_log.csv",
        "trade_pnl_log.csv",
        "signal_log.csv",
        "equity_curve.csv",
    }
    assert required_files.issubset({path.name for path in tmp_path.iterdir()})


def test_main_can_load_all_symbols(monkeypatch, tmp_path) -> None:
    observed: dict[str, object] = {}
    result = PortfolioBacktestResult(
        strategy_name=STRATEGY_NAME,
        start_date=date(2020, 1, 1),
        end_date=date(2026, 4, 30),
        starting_equity=Decimal("1000000"),
        ending_equity=Decimal("1000000"),
        symbols=("AAA",),
        strategy_variant=S5_SIMPLE_RS_126D_V1,
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
        "veridian_quant.v2.run_s5_backtest._get_database_engine",
        lambda: "engine",
    )
    monkeypatch.setattr(
        "veridian_quant.v2.run_s5_backtest.SQLAlchemyDailyOHLCVLoader",
        FakeLoader,
    )
    monkeypatch.setattr(
        "veridian_quant.v2.run_s5_backtest.run_s5_portfolio_backtest",
        lambda **kwargs: result,
    )

    exit_code = main(
        [
            "--start-date",
            "2020-01-01",
            "--end-date",
            "2026-04-30",
            "--all-symbols",
            "--skip-all-signal-diagnostics",
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
