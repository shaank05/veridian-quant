"""Tests for the S3 trend pullback portfolio runner and CLI parser."""

from datetime import date
from decimal import Decimal
from types import MappingProxyType

import pandas as pd
import pytest

from veridian_quant.v2.backtesting.portfolio_runner import PortfolioBacktestResult
from veridian_quant.v2.backtesting.s3_portfolio_runner import (
    S3_BASELINE_VARIANT,
    run_s3_portfolio_backtest,
)
from veridian_quant.v2.data.models import Signal, SignalType
from veridian_quant.v2.reporting.exporters import export_portfolio_backtest_csvs
from veridian_quant.v2.run_s3_backtest import _parse_args
from veridian_quant.v2.run_s3_backtest import _s3_variant_from_cli
from veridian_quant.v2.strategies.s3_trend_pullback_continuation import (
    S3_CONTROLLED_PULLBACK_V1,
    S3_STRONG_TREND_V1,
    STRATEGY_NAME,
)


def test_returns_empty_result_cleanly_when_no_signals() -> None:
    result = run_s3_portfolio_backtest(
        {"AAA": _trade_frame()},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert isinstance(result, PortfolioBacktestResult)
    assert result.strategy_name == STRATEGY_NAME
    assert result.signals == ()
    assert result.trades == ()
    assert result.trade_pnls == ()
    assert result.ending_equity == Decimal("1000000")


def test_accepts_real_s3_signal_and_produces_closed_trade_and_pnl() -> None:
    data = _s3_qualifying_frame_with_future_exit()
    result = run_s3_portfolio_backtest(
        {"AAA": data},
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 20),
    )

    assert result.signals
    assert len(result.trades) == 1
    assert len(result.trade_pnls) == 1
    assert result.trades[0].strategy_name == STRATEGY_NAME
    assert result.trade_pnls[0].net_pnl != Decimal("0")


def test_preserves_lookback_before_start_date_for_sma200_slope() -> None:
    data = _s3_qualifying_frame_with_future_exit()
    result = run_s3_portfolio_backtest(
        {"AAA": data},
        start_date=date(2026, 8, 8),
        end_date=date(2026, 8, 20),
    )

    assert [signal.generated_on for signal in result.signals] == [date(2026, 8, 8)]
    assert result.signals[0].metadata["sma200_slope_20d_pct"] > 0


def test_does_not_execute_signals_before_start_date(monkeypatch) -> None:
    _patch_signals(
        monkeypatch,
        {
            "AAA": [_signal("AAA", date(2026, 1, 10))],
        },
    )

    result = run_s3_portfolio_backtest(
        {"AAA": _trade_frame()},
        start_date=date(2026, 1, 11),
        end_date=date(2026, 1, 31),
    )

    assert result.signals == ()
    assert result.trades == ()


def test_does_not_execute_signals_after_end_date(monkeypatch) -> None:
    _patch_signals(
        monkeypatch,
        {
            "AAA": [_signal("AAA", date(2026, 1, 20))],
        },
    )

    result = run_s3_portfolio_backtest(
        {"AAA": _trade_frame()},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 19),
    )

    assert result.signals == ()
    assert result.trades == ()


def test_rejects_active_symbol_overlapping_trade(monkeypatch) -> None:
    _patch_signals(
        monkeypatch,
        {
            "AAA": [
                _signal("AAA", date(2026, 1, 15)),
                _signal("AAA", date(2026, 1, 16)),
            ],
        },
    )

    result = run_s3_portfolio_backtest(
        {"AAA": _trade_frame()},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert _rejection_reasons(result) == ["ACTIVE_SYMBOL_TRADE_EXISTS"]


def test_rejects_capacity_full_same_day_candidates(monkeypatch) -> None:
    _patch_signals(
        monkeypatch,
        {
            "AAA": [_signal("AAA", date(2026, 1, 15))],
            "BBB": [_signal("BBB", date(2026, 1, 15))],
        },
    )

    result = run_s3_portfolio_backtest(
        {"AAA": _trade_frame(), "BBB": _trade_frame()},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        max_concurrent_positions=1,
    )

    assert _rejection_reasons(result) == ["PORTFOLIO_CAPACITY_FULL"]


def test_rejects_setup_unavailable(monkeypatch) -> None:
    _patch_signals(
        monkeypatch,
        {
            "AAA": [_signal("AAA", date(2026, 1, 20))],
        },
    )

    result = run_s3_portfolio_backtest(
        {"AAA": _trade_frame(rows=20)},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 20),
    )

    assert _rejection_reasons(result) == ["SETUP_UNAVAILABLE"]


def test_rejects_position_plan_unavailable(monkeypatch) -> None:
    _patch_signals(
        monkeypatch,
        {
            "AAA": [_signal("AAA", date(2026, 1, 15))],
        },
    )

    result = run_s3_portfolio_backtest(
        {"AAA": _trade_frame()},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        risk_per_trade=Decimal("0"),
    )

    assert _rejection_reasons(result) == ["POSITION_PLAN_UNAVAILABLE"]


def test_applies_ledger_in_exit_date_order(monkeypatch) -> None:
    _patch_signals(
        monkeypatch,
        {
            "LATE": [_signal("LATE", date(2026, 1, 15))],
            "EARLY": [_signal("EARLY", date(2026, 1, 15))],
        },
    )

    result = run_s3_portfolio_backtest(
        {
            "LATE": _trade_frame(exit_style="time"),
            "EARLY": _trade_frame(exit_style="stop"),
        },
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        max_concurrent_positions=2,
        max_holding_sessions=5,
    )

    assert [trade.symbol for trade in result.trades] == ["EARLY", "LATE"]
    assert result.trades[0].exit_date < result.trades[1].exit_date


def test_strategy_name_variant_and_ranking_mode_are_correct(monkeypatch) -> None:
    _patch_signals(
        monkeypatch,
        {
            "AAA": [_signal("AAA", date(2026, 1, 15))],
        },
    )

    result = run_s3_portfolio_backtest(
        {"AAA": _trade_frame()},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert result.strategy_name == STRATEGY_NAME
    assert result.strategy_variant == S3_BASELINE_VARIANT
    assert result.candidate_ranking_mode == "none"


def test_selected_s3_variant_is_recorded_and_ranking_remains_none(monkeypatch) -> None:
    _patch_signals(
        monkeypatch,
        {
            "AAA": [_signal("AAA", date(2026, 1, 15))],
        },
    )

    result = run_s3_portfolio_backtest(
        {"AAA": _trade_frame()},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        strategy_variant=S3_STRONG_TREND_V1,
    )

    assert result.strategy_variant == S3_STRONG_TREND_V1
    assert result.candidate_ranking_mode == "none"


def test_selected_controlled_pullback_variant_is_recorded(monkeypatch) -> None:
    _patch_signals(
        monkeypatch,
        {
            "AAA": [_signal("AAA", date(2026, 1, 15))],
        },
    )

    result = run_s3_portfolio_backtest(
        {"AAA": _trade_frame()},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        strategy_variant=S3_CONTROLLED_PULLBACK_V1,
    )

    assert result.strategy_variant == S3_CONTROLLED_PULLBACK_V1
    assert result.candidate_ranking_mode == "none"


def test_selected_s3_variant_is_passed_into_signal_generation(monkeypatch) -> None:
    observed_variants = []

    def fake_generate(symbol: str, data: pd.DataFrame, **kwargs):
        observed_variants.append(kwargs["strategy_variant"])
        return (_signal(symbol, date(2026, 1, 15)),)

    monkeypatch.setattr(
        "veridian_quant.v2.backtesting.s3_portfolio_runner."
        "generate_s3_trend_pullback_signals",
        fake_generate,
    )

    run_s3_portfolio_backtest(
        {"AAA": _trade_frame()},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        strategy_variant=S3_STRONG_TREND_V1,
    )

    assert observed_variants == [S3_STRONG_TREND_V1]


def test_selected_controlled_pullback_variant_is_passed_into_signal_generation(
    monkeypatch,
) -> None:
    observed_variants = []

    def fake_generate(symbol: str, data: pd.DataFrame, **kwargs):
        observed_variants.append(kwargs["strategy_variant"])
        return (_signal(symbol, date(2026, 1, 15)),)

    monkeypatch.setattr(
        "veridian_quant.v2.backtesting.s3_portfolio_runner."
        "generate_s3_trend_pullback_signals",
        fake_generate,
    )

    run_s3_portfolio_backtest(
        {"AAA": _trade_frame()},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        strategy_variant=S3_CONTROLLED_PULLBACK_V1,
    )

    assert observed_variants == [S3_CONTROLLED_PULLBACK_V1]


def test_unknown_s3_runner_variant_raises_value_error() -> None:
    with pytest.raises(ValueError, match="unknown S3 strategy variant"):
        run_s3_portfolio_backtest(
            {"AAA": _trade_frame()},
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            strategy_variant="UNKNOWN",
        )


def test_result_signals_include_s3_metadata() -> None:
    data = _s3_qualifying_frame_with_future_exit()
    result = run_s3_portfolio_backtest(
        {"AAA": data},
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 20),
    )

    metadata = result.signals[0].metadata

    assert metadata["strategy_family"] == STRATEGY_NAME
    assert metadata["strategy_variant"] == S3_BASELINE_VARIANT
    assert metadata["s3_variant"] == S3_BASELINE_VARIANT
    assert metadata["sma_fast_window"] == 50
    assert metadata["pullback_lookback"] == 5
    assert "sma200_slope_20d_pct" in metadata


def test_input_dataframes_are_not_mutated(monkeypatch) -> None:
    _patch_signals(
        monkeypatch,
        {
            "AAA": [_signal("AAA", date(2026, 1, 15))],
        },
    )
    data_by_symbol = {"AAA": _trade_frame()}
    originals = {symbol: data.copy(deep=True) for symbol, data in data_by_symbol.items()}

    run_s3_portfolio_backtest(
        data_by_symbol,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    for symbol, original in originals.items():
        pd.testing.assert_frame_equal(data_by_symbol[symbol], original)


def test_rawrs_overlay_is_not_computed_when_disabled(monkeypatch) -> None:
    _patch_signals(monkeypatch, {"AAA": [_signal("AAA", date(2026, 1, 15))]})
    monkeypatch.setattr(
        "veridian_quant.v2.backtesting.s3_portfolio_runner."
        "build_rawrs_overlay_feature_frame",
        lambda data: (_ for _ in ()).throw(AssertionError("must stay disabled")),
    )
    result = run_s3_portfolio_backtest(
        {"AAA": _trade_frame()},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )
    assert len(result.trades) == 1
    assert "rawrs_overlay_enabled" not in result.signals[0].metadata


def test_rawrs_overlay_rejects_low_percentile_before_portfolio_flow(monkeypatch) -> None:
    _patch_signals(monkeypatch, {"AAA": [_signal("AAA", date(2026, 1, 15))]})
    _patch_rawrs_overlay_features(monkeypatch, list(range(31, 0, -1)))
    result = run_s3_portfolio_backtest(
        {"AAA": _trade_frame()},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        max_concurrent_positions=0,
        enable_rawrs_overlay=True,
        rawrs_percentile_lookback=10,
        rawrs_min_observations=10,
    )
    assert result.trades == ()
    assert _rejection_reasons(result) == ["RAWRS_OVERLAY_REJECTED"]
    assert result.signals[0].metadata["rawrs_overlay_decision"] == "REJECT"


def test_rawrs_overlay_allows_value_above_threshold(monkeypatch) -> None:
    _patch_signals(monkeypatch, {"AAA": [_signal("AAA", date(2026, 1, 15))]})
    _patch_rawrs_overlay_features(monkeypatch, list(range(1, 32)))
    result = run_s3_portfolio_backtest(
        {"AAA": _trade_frame()},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        enable_rawrs_overlay=True,
        rawrs_percentile_lookback=10,
        rawrs_min_observations=10,
    )
    assert len(result.trades) == 1
    assert result.signals[0].metadata["rawrs_overlay_decision"] == "ALLOW"


def test_rawrs_overlay_allows_missing_feature_value(monkeypatch) -> None:
    _patch_signals(monkeypatch, {"AAA": [_signal("AAA", date(2026, 1, 15))]})
    _patch_rawrs_overlay_features(monkeypatch, [float("nan")] * 31)
    result = run_s3_portfolio_backtest(
        {"AAA": _trade_frame()},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        enable_rawrs_overlay=True,
        rawrs_percentile_lookback=10,
        rawrs_min_observations=10,
    )
    assert len(result.trades) == 1
    assert (
        result.signals[0].metadata["rawrs_overlay_decision"]
        == "ALLOW_MISSING_FEATURE_VALUE"
    )


def test_missing_columns_create_data_unavailable_rejection_not_crash() -> None:
    result = run_s3_portfolio_backtest(
        {"BAD": _trade_frame().drop(columns=["low"])},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert _rejection_reasons(result) == ["DATA_UNAVAILABLE"]
    assert result.trades == ()


def test_no_s1_s2_specific_metadata_is_required(monkeypatch) -> None:
    _patch_signals(
        monkeypatch,
        {
            "AAA": [
                Signal(
                    symbol="AAA",
                    signal_type=SignalType.LONG,
                    generated_on=date(2026, 1, 15),
                    strategy_name=STRATEGY_NAME,
                    reason="minimal S3 signal",
                    metadata=MappingProxyType({"strategy_family": STRATEGY_NAME}),
                )
            ],
        },
    )

    result = run_s3_portfolio_backtest(
        {"AAA": _trade_frame()},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert len(result.trades) == 1
    assert "z_score" not in result.signals[0].metadata
    assert "state_label" not in result.signals[0].metadata


def test_standard_exporter_writes_s3_signal_metadata_columns(tmp_path) -> None:
    data = _s3_qualifying_frame_with_future_exit()
    result = run_s3_portfolio_backtest(
        {"AAA": data},
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 20),
    )

    paths = export_portfolio_backtest_csvs(
        result,
        tmp_path,
        include_all_signal_diagnostics=False,
    )
    signal_log = pd.read_csv(paths["signal_log"])

    assert signal_log.loc[0, "sma_fast_window"] == 50
    assert signal_log.loc[0, "pullback_lookback"] == 5
    assert signal_log.loc[0, "strategy_variant"] == S3_BASELINE_VARIANT
    assert signal_log.loc[0, "s3_variant"] == S3_BASELINE_VARIANT
    assert "s3_requires_controlled_pullback" in signal_log.columns
    assert "s3_controlled_pullback_min_return_5d_pct" in signal_log.columns
    assert "sma200_slope_20d_pct" in signal_log.columns
    assert "atr14_change_5d_pct" in signal_log.columns


def test_cli_parser_accepts_s3_arguments() -> None:
    args = _parse_args(
        [
            "--start-date",
            "2020-01-01",
            "--end-date",
            "2026-04-30",
            "--symbols",
            "RELIANCE,TCS",
            "--output-dir",
            "reports/v2/s3",
            "--sma-fast-window",
            "40",
            "--sma-slow-window",
            "180",
            "--sma-slope-lookback",
            "15",
            "--pullback-lookback",
            "7",
            "--min-pullback-return-pct",
            "-8",
            "--max-pullback-return-pct",
            "-0.5",
            "--min-drawdown-20d-pct",
            "-12",
            "--max-drawdown-20d-pct",
            "-2",
            "--max-atr-pct",
            "7",
            "--max-atr-expansion-5d-pct",
            "40",
            "--fresh-low-window",
            "50",
            "--allow-repeated-signals",
            "--disable-recovery-day",
            "--skip-all-signal-diagnostics",
            "--s3-variant",
            "strong_trend_v1",
            "--verbosity",
            "quiet",
        ]
    )

    assert args.start_date == date(2020, 1, 1)
    assert args.end_date == date(2026, 4, 30)
    assert args.symbols == "RELIANCE,TCS"
    assert args.sma_fast_window == 40
    assert args.sma_slow_window == 180
    assert args.sma_slope_lookback == 15
    assert args.pullback_lookback == 7
    assert args.min_pullback_return_pct == -8
    assert args.max_pullback_return_pct == -0.5
    assert args.min_drawdown_20d_pct == -12
    assert args.max_drawdown_20d_pct == -2
    assert args.max_atr_pct == 7
    assert args.max_atr_expansion_5d_pct == 40
    assert args.fresh_low_window == 50
    assert args.allow_repeated_signals is True
    assert args.disable_recovery_day is True
    assert args.skip_all_signal_diagnostics is True
    assert args.s3_variant == "strong_trend_v1"
    assert _s3_variant_from_cli(args.s3_variant) == S3_STRONG_TREND_V1
    assert args.verbosity == "quiet"


def test_cli_parser_accepts_controlled_pullback_s3_variant() -> None:
    args = _parse_args(
        [
            "--start-date",
            "2020-01-01",
            "--end-date",
            "2026-04-30",
            "--symbols",
            "RELIANCE,TCS",
            "--s3-variant",
            "controlled_pullback_v1",
        ]
    )

    assert args.s3_variant == "controlled_pullback_v1"
    assert _s3_variant_from_cli(args.s3_variant) == S3_CONTROLLED_PULLBACK_V1


def test_cli_parser_rejects_invalid_s3_variant() -> None:
    with pytest.raises(SystemExit):
        _parse_args(
            [
                "--start-date",
                "2020-01-01",
                "--end-date",
                "2026-04-30",
                "--symbols",
                "RELIANCE",
                "--s3-variant",
                "invalid",
            ]
        )


def _patch_signals(monkeypatch, signals_by_symbol: dict[str, list[Signal]]) -> None:
    def fake_generate(symbol: str, data: pd.DataFrame, **kwargs):
        return tuple(signals_by_symbol.get(symbol, []))

    monkeypatch.setattr(
        "veridian_quant.v2.backtesting.s3_portfolio_runner."
        "generate_s3_trend_pullback_signals",
        fake_generate,
    )


def _patch_rawrs_overlay_features(monkeypatch, values: list[float]) -> None:
    def fake_build(data: pd.DataFrame, *, feature: str) -> pd.DataFrame:
        return pd.DataFrame(
            {feature: values[: len(data)]},
            index=pd.to_datetime(data["date"]),
        )

    monkeypatch.setattr(
        "veridian_quant.v2.backtesting.s3_portfolio_runner."
        "build_rawrs_overlay_feature_frame",
        fake_build,
    )


def _signal(symbol: str, signal_date: date) -> Signal:
    return Signal(
        symbol=symbol,
        signal_type=SignalType.LONG,
        generated_on=signal_date,
        strategy_name=STRATEGY_NAME,
        reason="patched S3 signal",
        metadata=MappingProxyType(
            {
                "strategy_family": STRATEGY_NAME,
                "sma_fast_window": 50,
                "pullback_lookback": 5,
            }
        ),
    )


def _rejection_reasons(result: PortfolioBacktestResult) -> list[str]:
    return [rejected.reason for rejected in result.rejected_signals]


def _trade_frame(rows: int = 31, exit_style: str = "target") -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="D")
    close = [100.0 for _ in range(rows)]
    high = [101.0 for _ in range(rows)]
    low = [99.0 for _ in range(rows)]
    open_ = [100.0 for _ in range(rows)]

    if rows > 17 and exit_style == "target":
        high[16] = 120.0
    if rows > 17 and exit_style == "stop":
        low[16] = 90.0
    if exit_style == "time":
        high = [101.0 for _ in range(rows)]
        low = [99.0 for _ in range(rows)]

    return pd.DataFrame(
        {
            "date": dates,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": [1000 for _ in range(rows)],
        }
    )


def _s3_qualifying_frame_with_future_exit() -> pd.DataFrame:
    closes = [100.0 + (0.5 * index) for index in range(210)]
    closes.extend(
        [
            206.0,
            208.0,
            211.0,
            209.0,
            208.0,
            207.0,
            201.0,
            200.0,
            201.0,
            202.0,
            214.0,
            220.0,
        ]
    )
    high = [close + 1.0 for close in closes]
    low = [close - 1.0 for close in closes]
    high[-1] = 230.0
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=len(closes), freq="D"),
            "open": closes,
            "high": high,
            "low": low,
            "close": closes,
            "volume": [1000 for _ in closes],
        }
    )
