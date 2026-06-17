"""Tests for S2 Markov signal filter experiments."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from tempfile import TemporaryDirectory
from types import MappingProxyType
from unittest.mock import patch

import pandas as pd

from veridian_quant.v2.backtesting.markov_portfolio_runner import (
    S2_MARKOV_SIGNAL_FILTERED_REASON,
    run_s2_markov_portfolio_backtest,
)
from veridian_quant.v2.backtesting.portfolio_runner import PortfolioBacktestResult
from veridian_quant.v2.backtesting.trade import ExitReason, Trade, TradeStatus
from veridian_quant.v2.backtesting.pnl import TradePnL
from veridian_quant.v2.data.models import Signal, SignalType
from veridian_quant.v2.reporting.exporters import export_portfolio_backtest_csvs
from veridian_quant.v2.run_s2_markov_backtest import _parse_args
from veridian_quant.v2.strategies.s2_markov_filters import (
    apply_markov_signal_filter,
    markov_strategy_variant,
)
from veridian_quant.v2.strategies.s2_markov_state_transition import STRATEGY_NAME


def test_none_filter_keeps_all_s2_signals() -> None:
    assert apply_markov_signal_filter(_signal("RET_DOWN|VOL_MID|DD_MID|LOW_NEAR")).kept


def test_exclude_ret_down_rejects_ret_down_and_keeps_other_states() -> None:
    assert not apply_markov_signal_filter(
        _signal("RET_DOWN|VOL_MID|DD_MID|LOW_MID_RANGE"),
        "exclude_ret_down",
    ).kept
    assert apply_markov_signal_filter(
        _signal("RET_UP|VOL_MID|DD_MID|LOW_MID_RANGE"),
        "exclude_ret_down",
    ).kept


def test_keep_ret_flat_up_strong_up_keeps_only_expected_states() -> None:
    for ret_state in ("RET_FLAT", "RET_UP", "RET_STRONG_UP"):
        assert apply_markov_signal_filter(
            _signal(f"{ret_state}|VOL_MID|DD_MID|LOW_MID_RANGE"),
            "keep_ret_flat_up_strong_up",
        ).kept
    assert not apply_markov_signal_filter(
        _signal("RET_STRONG_DOWN|VOL_MID|DD_MID|LOW_MID_RANGE"),
        "keep_ret_flat_up_strong_up",
    ).kept


def test_exclude_dd_deep_rejects_dd_deep() -> None:
    assert not apply_markov_signal_filter(
        _signal("RET_UP|VOL_MID|DD_DEEP|LOW_MID_RANGE"),
        "exclude_dd_deep",
    ).kept
    assert apply_markov_signal_filter(
        _signal("RET_UP|VOL_MID|DD_MID|LOW_MID_RANGE"),
        "exclude_dd_deep",
    ).kept


def test_exclude_ret_down_and_dd_deep_rejects_either_condition() -> None:
    assert not apply_markov_signal_filter(
        _signal("RET_DOWN|VOL_MID|DD_MID|LOW_MID_RANGE"),
        "exclude_ret_down_and_dd_deep",
    ).kept
    assert not apply_markov_signal_filter(
        _signal("RET_UP|VOL_MID|DD_DEEP|LOW_MID_RANGE"),
        "exclude_ret_down_and_dd_deep",
    ).kept
    assert apply_markov_signal_filter(
        _signal("RET_UP|VOL_MID|DD_MID|LOW_MID_RANGE"),
        "exclude_ret_down_and_dd_deep",
    ).kept


def test_exclude_low_near_rejects_low_near() -> None:
    assert not apply_markov_signal_filter(
        _signal("RET_UP|VOL_MID|DD_MID|LOW_NEAR"),
        "exclude_low_near",
    ).kept


def test_balanced_markov_v1_keeps_only_combined_conditions() -> None:
    assert apply_markov_signal_filter(
        _signal(
            "RET_FLAT|VOL_HIGH|DD_MID|LOW_FAR_FROM_LOW",
            state_observation_count=15,
        ),
        "balanced_markov_v1",
    ).kept
    assert not apply_markov_signal_filter(
        _signal(
            "RET_FLAT|VOL_LOW|DD_MID|LOW_FAR_FROM_LOW",
            state_observation_count=15,
        ),
        "balanced_markov_v1",
    ).kept
    assert not apply_markov_signal_filter(
        _signal(
            "RET_FLAT|VOL_HIGH|DD_MID|LOW_FAR_FROM_LOW",
            state_observation_count=14,
        ),
        "balanced_markov_v1",
    ).kept


def test_malformed_or_missing_state_metadata_is_kept_by_none() -> None:
    assert apply_markov_signal_filter(_signal("BAD")).kept
    assert apply_markov_signal_filter(_signal(None)).kept


def test_malformed_or_missing_state_metadata_is_rejected_by_non_none_filters() -> None:
    assert not apply_markov_signal_filter(_signal("BAD"), "exclude_ret_down").kept
    assert not apply_markov_signal_filter(_signal(None), "exclude_ret_down").kept


def test_s2_portfolio_runner_none_filter_matches_previous_behavior() -> None:
    kwargs = _runner_kwargs()

    baseline = run_s2_markov_portfolio_backtest(**kwargs)
    explicit_none = run_s2_markov_portfolio_backtest(
        **kwargs,
        markov_signal_filter="none",
    )

    assert explicit_none == baseline


def test_s2_portfolio_runner_accepts_candidate_ranking_mode() -> None:
    signals = (
        _signal("RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW"),
        _signal("RET_FLAT|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW"),
    )
    with patch(
        "veridian_quant.v2.backtesting.markov_portfolio_runner.generate_s2_markov_signals",
        return_value=list(signals),
    ):
        result = run_s2_markov_portfolio_backtest(
            data_by_symbol={"AAA": _frame()},
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 10),
            starting_equity=Decimal("100000"),
            min_state_observations=1,
            forward_return_sessions=1,
            round_trip_cost_pct=Decimal("0"),
            s2_candidate_ranking_mode="state_edge_v1",
        )

    assert result.candidate_ranking_mode == "state_edge_v1"
    assert {
        signal.metadata.get("candidate_ranking_mode")
        for signal in result.signals
    } == {"s2:state_edge_v1"}


def test_s2_portfolio_runner_ranking_none_matches_default_behavior() -> None:
    kwargs = _runner_kwargs()

    baseline = run_s2_markov_portfolio_backtest(**kwargs)
    explicit_none = run_s2_markov_portfolio_backtest(
        **kwargs,
        s2_candidate_ranking_mode="none",
    )

    assert explicit_none == baseline


def test_s2_portfolio_runner_names_avoid_shallow_uptrend_pullback_variant() -> None:
    with patch(
        "veridian_quant.v2.backtesting.markov_portfolio_runner.generate_s2_markov_signals",
        return_value=[
            _signal("RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW"),
        ],
    ):
        result = run_s2_markov_portfolio_backtest(
            data_by_symbol={"AAA": _frame()},
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 10),
            starting_equity=Decimal("100000"),
            min_state_observations=1,
            forward_return_sessions=1,
            round_trip_cost_pct=Decimal("0"),
            s2_candidate_ranking_mode="avoid_shallow_uptrend_pullback_v1",
        )

    assert (
        result.strategy_variant
        == "S2_MARKOV_STATE_TRANSITION_AVOID_SHALLOW_UPTREND_PULLBACK_V1"
    )
    assert result.candidate_ranking_mode == "avoid_shallow_uptrend_pullback_v1"


def test_s2_portfolio_runner_names_2025_guard_variant() -> None:
    with patch(
        "veridian_quant.v2.backtesting.markov_portfolio_runner.generate_s2_markov_signals",
        return_value=[
            _signal("RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW"),
        ],
    ):
        result = run_s2_markov_portfolio_backtest(
            data_by_symbol={"AAA": _frame()},
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 10),
            starting_equity=Decimal("100000"),
            min_state_observations=1,
            forward_return_sessions=1,
            round_trip_cost_pct=Decimal("0"),
            s2_candidate_ranking_mode="2025_guard_v1",
        )

    assert result.strategy_variant == "S2_MARKOV_STATE_TRANSITION_2025_GUARD_V1"
    assert result.candidate_ranking_mode == "2025_guard_v1"


def test_s2_portfolio_runner_names_2025_guard_variant_with_filter() -> None:
    with patch(
        "veridian_quant.v2.backtesting.markov_portfolio_runner.generate_s2_markov_signals",
        return_value=[
            _signal("RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW"),
        ],
    ):
        result = run_s2_markov_portfolio_backtest(
            data_by_symbol={"AAA": _frame()},
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 10),
            starting_equity=Decimal("100000"),
            min_state_observations=1,
            forward_return_sessions=1,
            round_trip_cost_pct=Decimal("0"),
            markov_signal_filter="exclude_ret_down",
            s2_candidate_ranking_mode="2025_guard_v1",
        )

    assert (
        result.strategy_variant
        == "S2_MARKOV_STATE_TRANSITION_2025_GUARD_V1__exclude_ret_down"
    )


def test_s2_portfolio_runner_records_filter_rejections() -> None:
    signals = (
        _signal("RET_DOWN|VOL_MID|DD_MID|LOW_MID_RANGE"),
        _signal("RET_UP|VOL_MID|DD_MID|LOW_MID_RANGE"),
    )
    with patch(
        "veridian_quant.v2.backtesting.markov_portfolio_runner.generate_s2_markov_signals",
        return_value=list(signals),
    ):
        result = run_s2_markov_portfolio_backtest(
            data_by_symbol={"AAA": _frame()},
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 10),
            starting_equity=Decimal("100000"),
            min_state_observations=1,
            forward_return_sessions=1,
            round_trip_cost_pct=Decimal("0"),
            markov_signal_filter="exclude_ret_down",
        )

    filtered = [
        rejected
        for rejected in result.rejected_signals
        if rejected.reason == S2_MARKOV_SIGNAL_FILTERED_REASON
    ]
    assert len(filtered) == 1
    assert filtered[0].markov_signal_filter == "exclude_ret_down"
    assert filtered[0].markov_filter_decision == "filtered"
    assert all(
        rejected.reason != "PORTFOLIO_CAPACITY_FULL" for rejected in filtered
    )


def test_summary_strategy_variant_includes_filter_name_for_filtered_runs() -> None:
    result = replace(
        _empty_result(),
        strategy_variant=markov_strategy_variant(
            STRATEGY_NAME,
            "exclude_ret_down",
        ),
    )
    with TemporaryDirectory() as temp_dir:
        paths = export_portfolio_backtest_csvs(result, temp_dir)
        summary = pd.read_csv(paths["summary"])

    assert (
        summary.loc[0, "strategy_variant"]
        == "S2_MARKOV_STATE_TRANSITION__exclude_ret_down"
    )


def test_cli_parses_markov_signal_filter() -> None:
    args = _parse_args(
        [
            "--start-date",
            "2026-01-01",
            "--end-date",
            "2026-01-31",
            "--symbols",
            "AAA",
            "--markov-signal-filter",
            "exclude_ret_down",
        ]
    )

    assert args.markov_signal_filter == "exclude_ret_down"


def test_cli_parses_s2_candidate_ranking() -> None:
    args = _parse_args(
        [
            "--start-date",
            "2026-01-01",
            "--end-date",
            "2026-01-31",
            "--symbols",
            "AAA",
            "--s2-candidate-ranking",
            "avoid_shallow_uptrend_pullback_v1",
        ]
    )

    assert args.s2_candidate_ranking == "avoid_shallow_uptrend_pullback_v1"


def test_cli_parses_2025_guard_candidate_ranking() -> None:
    args = _parse_args(
        [
            "--start-date",
            "2026-01-01",
            "--end-date",
            "2026-01-31",
            "--symbols",
            "AAA",
            "--s2-candidate-ranking",
            "2025_guard_v1",
        ]
    )

    assert args.s2_candidate_ranking == "2025_guard_v1"


def test_cli_parses_skip_all_signal_diagnostics() -> None:
    args = _parse_args(
        [
            "--start-date",
            "2026-01-01",
            "--end-date",
            "2026-01-31",
            "--symbols",
            "AAA",
            "--skip-all-signal-diagnostics",
        ]
    )

    assert args.skip_all_signal_diagnostics is True


def test_exporter_writes_empty_all_signal_diagnostics_when_skipped() -> None:
    with TemporaryDirectory() as temp_dir:
        paths = export_portfolio_backtest_csvs(
            _empty_result(signals=(_signal("RET_UP|VOL_MID|DD_MID|LOW_MID_RANGE"),)),
            temp_dir,
            stock_data_by_symbol={"AAA": _frame()},
            include_all_signal_diagnostics=False,
        )

        all_signal = pd.read_csv(paths["all_signal_opportunity_log"])
        counterfactual = pd.read_csv(paths["counterfactual_rejected_trade_summary"])

    assert all_signal.empty
    assert counterfactual.empty


def _runner_kwargs() -> dict[str, object]:
    return {
        "data_by_symbol": {"AAA": _trend_frame(90)},
        "start_date": date(2026, 3, 1),
        "end_date": date(2026, 3, 31),
        "starting_equity": Decimal("100000"),
        "risk_per_trade": Decimal("0.01"),
        "max_concurrent_positions": 2,
        "state_lookback_sessions": 252,
        "min_state_observations": 3,
        "forward_return_sessions": 2,
        "positive_return_threshold_pct": 3.0,
        "signal_probability_threshold": 0.60,
        "signal_average_forward_return_threshold_pct": 1.0,
        "round_trip_cost_pct": Decimal("0"),
    }


def _signal(
    state_label: str | None,
    state_observation_count: int = 20,
) -> Signal:
    metadata = {
        "strategy_family": STRATEGY_NAME,
        "state_label": state_label,
        "state_observation_count": state_observation_count,
        "positive_transition_probability": 0.70,
        "average_forward_return_pct": 4.0,
        "median_forward_return_pct": 4.0,
        "current_5d_return_pct": 2.0,
        "current_atr_pct": 3.0,
        "current_drawdown_60d_pct": -5.0,
        "current_close_vs_60d_low_pct": 10.0,
        "close": 100.0,
    }
    return Signal(
        symbol="AAA",
        signal_type=SignalType.LONG,
        generated_on=date(2026, 1, 2),
        strategy_name=STRATEGY_NAME,
        reason="test S2 signal",
        metadata=MappingProxyType(metadata),
    )


def _empty_result(signals: tuple[Signal, ...] = ()) -> PortfolioBacktestResult:
    return PortfolioBacktestResult(
        strategy_name=STRATEGY_NAME,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 10),
        starting_equity=Decimal("100000"),
        ending_equity=Decimal("100000"),
        symbols=("AAA",),
        trade_pnls=(),
        trades=(),
        signals=signals,
        rejected_signals=(),
        ledger=None,
        strategy_variant=STRATEGY_NAME,
    )


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2026-01-01") + pd.Timedelta(days=index),
                "open": 100.0 + index,
                "high": 101.0 + index,
                "low": 99.0 + index,
                "close": 100.0 + index,
                "volume": 1000,
            }
            for index in range(20)
        ]
    )


def _trend_frame(rows: int) -> pd.DataFrame:
    close = 100.0
    output = []
    for index in range(rows):
        close *= 1.02
        output.append(
            {
                "date": pd.Timestamp("2026-01-01") + pd.Timedelta(days=index),
                "open": close,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1000,
            }
        )
    return pd.DataFrame(output)
