"""Unit tests for v2 multi-symbol S1 portfolio backtest orchestration."""

from datetime import date
from decimal import Decimal

import pandas as pd

from veridian_quant.v2.backtesting.portfolio_runner import (
    PortfolioBacktestResult,
    run_s1_portfolio_backtest,
)
from veridian_quant.v2.backtesting.trade import ExitReason
from veridian_quant.v2.reporting.exporters import export_portfolio_backtest_csvs
from veridian_quant.v2.strategies.variants import (
    S1_AVOID_MESSY_MIDDLE_V1,
    S1_BASELINE,
    S1_BROAD_BEST_GUESS,
    S1_DOWN_CLOSES_GTE_3,
    S1_DRAWDOWN_60D_SHALLOW_OR_DEEP,
    s1_variant_rejection_reason,
)


def test_successful_multi_symbol_backtest() -> None:
    result = _run({"RELIANCE": _two_signal_frame(), "TCS": _late_signal_frame()})

    assert isinstance(result, PortfolioBacktestResult)
    assert result.symbols == ("RELIANCE", "TCS")
    assert len(result.signals) >= 2
    assert len(result.trades) >= 2
    assert len(result.trade_pnls) == len(result.trades)
    assert result.ledger is not None


def test_signals_are_processed_chronologically() -> None:
    result = _run({"TCS": _late_signal_frame(), "RELIANCE": _two_signal_frame()})

    signal_dates = [signal.generated_on for signal in result.signals]

    assert signal_dates == sorted(signal_dates)


def test_same_day_signals_are_ranked_by_most_negative_zscore_first() -> None:
    result = _run(
        {
            "LESS_NEGATIVE": _same_day_signal_frame([10, 12, 14, 8, 9]),
            "MORE_NEGATIVE": _same_day_signal_frame([10, 20, 21, 5, 6]),
        },
        max_concurrent_positions=1,
    )

    assert [signal.symbol for signal in result.signals[:2]] == [
        "MORE_NEGATIVE",
        "LESS_NEGATIVE",
    ]
    assert result.trades[0].symbol == "MORE_NEGATIVE"
    assert result.rejected_signals[0].symbol == "LESS_NEGATIVE"
    assert result.rejected_signals[0].reason == "PORTFOLIO_CAPACITY_FULL"


def test_default_candidate_ranking_none_preserves_current_ordering_behavior() -> None:
    deep = _same_day_signal_frame([10, 20, 21, 5, 6])
    liquid = _high_volume(_same_day_signal_frame([10, 12, 14, 8, 9]))

    result = _run(
        {"DEEP": deep, "LIQUID": liquid},
        max_concurrent_positions=1,
        candidate_ranking_mode="none",
    )

    assert [signal.symbol for signal in result.signals[:2]] == ["DEEP", "LIQUID"]
    assert result.trades[0].symbol == "DEEP"
    assert result.candidate_ranking_mode == "none"


def test_candidate_ranking_s1_v1_ranks_same_day_candidates_before_capacity() -> None:
    deep = _same_day_signal_frame([10, 20, 21, 5, 6])
    liquid = _high_volume(_same_day_signal_frame([10, 12, 14, 8, 9]))

    result = _run(
        {"DEEP": deep, "LIQUID": liquid},
        max_concurrent_positions=1,
        candidate_ranking_mode="s1_v1",
    )

    assert [signal.symbol for signal in result.signals[:2]] == ["LIQUID", "DEEP"]
    assert result.trades[0].symbol == "LIQUID"
    assert result.rejected_signals[0].symbol == "DEEP"
    assert result.rejected_signals[0].reason == "PORTFOLIO_CAPACITY_FULL"


def test_candidate_ranking_does_not_reorder_across_entry_dates() -> None:
    early = _same_day_signal_frame([10, 12, 14, 8, 9])
    late = _high_volume(_late_signal_frame())

    result = _run(
        {"EARLY": early, "LATE": late},
        max_concurrent_positions=5,
        candidate_ranking_mode="s1_v1",
    )

    signal_dates = [signal.generated_on for signal in result.signals]
    assert signal_dates == sorted(signal_dates)
    assert result.signals[0].symbol == "EARLY"


def test_candidate_ranking_is_deterministic() -> None:
    data = {
        "DEEP": _same_day_signal_frame([10, 20, 21, 5, 6]),
        "LIQUID": _high_volume(_same_day_signal_frame([10, 12, 14, 8, 9])),
    }

    first = _run(data, max_concurrent_positions=1, candidate_ranking_mode="s1_v1")
    second = _run(data, max_concurrent_positions=1, candidate_ranking_mode="s1_v1")

    assert first.signals == second.signals
    assert first.trades == second.trades
    assert first.rejected_signals == second.rejected_signals


def test_candidate_ranking_metadata_appears_in_signal_log(tmp_path) -> None:
    result = _run(
        {
            "DEEP": _same_day_signal_frame([10, 20, 21, 5, 6]),
            "LIQUID": _high_volume(_same_day_signal_frame([10, 12, 14, 8, 9])),
        },
        max_concurrent_positions=1,
        candidate_ranking_mode="s1_v1",
    )

    paths = export_portfolio_backtest_csvs(result, tmp_path)
    signal_log = pd.read_csv(paths["signal_log"])

    assert "candidate_ranking_mode" in signal_log.columns
    assert "candidate_rank" in signal_log.columns
    assert "candidate_score" in signal_log.columns
    assert "candidate_pool_size_for_date" in signal_log.columns
    assert set(signal_log["candidate_ranking_mode"]) == {"s1_v1"}
    assert set(signal_log["candidate_pool_size_for_date"]) == {2}


def test_max_concurrent_positions_is_respected() -> None:
    result = _run(
        {
            "A": _same_day_signal_frame([10, 20, 21, 5, 6]),
            "B": _same_day_signal_frame([10, 12, 14, 8, 9]),
        },
        max_concurrent_positions=1,
    )

    assert len(result.trades) == 1
    assert any(
        rejected.reason == "PORTFOLIO_CAPACITY_FULL"
        for rejected in result.rejected_signals
    )


def test_active_same_symbol_trade_is_rejected() -> None:
    result = _run({"RELIANCE": _two_signal_frame()})

    assert len(result.signals) == 2
    assert len(result.trades) == 1
    assert result.rejected_signals[0].reason == "ACTIVE_SYMBOL_TRADE_EXISTS"


def test_current_equity_compounds_after_closed_trades() -> None:
    result = _run({"RELIANCE": _early_winner_frame(), "TCS": _late_signal_frame()})

    assert len(result.trade_pnls) == 2
    assert result.ending_equity == (
        result.starting_equity
        + result.trade_pnls[0].net_pnl
        + result.trade_pnls[1].net_pnl
    )
    assert result.ledger is not None
    assert len(result.ledger.equity_curve) == 2


def test_no_data_after_end_date_is_used() -> None:
    result = _run(
        {"RELIANCE": _post_window_target_frame()},
        end_date=date(2026, 1, 5),
        atr_multiplier=Decimal("1"),
    )

    assert len(result.trades) == 1
    assert result.trades[0].exit_date == date(2026, 1, 5)
    assert result.trades[0].exit_price == Decimal("9.0")
    assert result.trades[0].exit_reason == ExitReason.BACKTEST_END


def test_data_ending_before_backtest_end_uses_data_end_reason() -> None:
    result = _run(
        {
            "RELIANCE": _post_window_target_frame().iloc[:5].copy(),
            "TCS": _late_signal_frame(),
        },
        end_date=date(2026, 1, 20),
        atr_multiplier=Decimal("1"),
    )

    reliance_trades = [trade for trade in result.trades if trade.symbol == "RELIANCE"]
    assert len(reliance_trades) == 1
    assert reliance_trades[0].exit_date == date(2026, 1, 5)
    assert reliance_trades[0].exit_reason == ExitReason.DATA_END


def test_requested_end_after_last_available_row_uses_effective_market_end() -> None:
    result = _run(
        {"RELIANCE": _post_window_target_frame().iloc[:5].copy()},
        end_date=date(2026, 1, 7),
        atr_multiplier=Decimal("1"),
    )

    assert len(result.trades) == 1
    assert result.trades[0].exit_date == date(2026, 1, 5)
    assert result.trades[0].exit_reason == ExitReason.BACKTEST_END


def test_symbol_with_invalid_data_is_rejected_safely() -> None:
    invalid = _same_day_signal_frame([10, 12, 14, 8, 9]).drop(columns=["low"])

    result = _run({"BAD": invalid, "GOOD": _same_day_signal_frame([10, 12, 14, 8, 9])})

    assert len(result.trades) == 1
    assert any(
        rejected.symbol == "BAD" and rejected.reason == "DATA_UNAVAILABLE"
        for rejected in result.rejected_signals
    )


def test_input_dataframes_are_not_mutated() -> None:
    data_by_symbol = {"RELIANCE": _two_signal_frame(), "TCS": _late_signal_frame()}
    originals = {
        symbol: data.copy(deep=True)
        for symbol, data in data_by_symbol.items()
    }

    _run(data_by_symbol)

    for symbol, original in originals.items():
        pd.testing.assert_frame_equal(data_by_symbol[symbol], original)


def test_result_contains_combined_artifacts() -> None:
    result = _run({"RELIANCE": _two_signal_frame(), "TCS": _late_signal_frame()})

    assert result.signals
    assert result.trades
    assert result.trade_pnls
    assert result.rejected_signals
    assert result.ledger is not None
    assert result.ledger.trade_pnls == result.trade_pnls


def test_baseline_variant_matches_default_behavior() -> None:
    data = {"RELIANCE": _two_signal_frame(), "TCS": _late_signal_frame()}

    default = _run(data)
    explicit = _run(data, strategy_variant=S1_BASELINE)

    assert explicit.signals == default.signals
    assert explicit.trades == default.trades
    assert explicit.trade_pnls == default.trade_pnls
    assert explicit.rejected_signals == default.rejected_signals
    assert explicit.strategy_variant == S1_BASELINE


def test_avoid_messy_middle_rejects_drawdown_zone() -> None:
    result = _run(
        {"RELIANCE": _variant_signal_frame([110, 100, 98, 95])},
        end_date=date(2026, 3, 20),
        strategy_variant=S1_AVOID_MESSY_MIDDLE_V1,
    )

    assert len(result.trades) == 0
    assert result.rejected_signals[0].reason == "FILTER_MESSY_MIDDLE_DRAWDOWN"


def test_avoid_messy_middle_rejects_low_distance_zone() -> None:
    result = _run(
        {"RELIANCE": _variant_signal_frame([110, 100, 95, 80], prior_low=76)},
        end_date=date(2026, 3, 20),
        strategy_variant=S1_AVOID_MESSY_MIDDLE_V1,
    )

    assert len(result.trades) == 0
    assert result.rejected_signals[0].reason == "FILTER_MESSY_MIDDLE_LOW_DISTANCE"


def test_avoid_messy_middle_allows_outside_messy_zones() -> None:
    result = _run(
        {"RELIANCE": _variant_signal_frame([110, 100, 95, 80])},
        end_date=date(2026, 3, 20),
        strategy_variant=S1_AVOID_MESSY_MIDDLE_V1,
    )

    assert len(result.trades) == 1
    assert not result.rejected_signals


def test_drawdown_shallow_or_deep_variant_allows_and_rejects_expected_zones() -> None:
    shallow = _run(
        {"RELIANCE": _variant_signal_frame([100, 101, 100, 98])},
        end_date=date(2026, 3, 20),
        strategy_variant=S1_DRAWDOWN_60D_SHALLOW_OR_DEEP,
    )
    deep = _run(
        {"RELIANCE": _variant_signal_frame([110, 100, 95, 80])},
        end_date=date(2026, 3, 20),
        strategy_variant=S1_DRAWDOWN_60D_SHALLOW_OR_DEEP,
    )
    middle = _run(
        {"RELIANCE": _variant_signal_frame([110, 100, 98, 95])},
        end_date=date(2026, 3, 20),
        strategy_variant=S1_DRAWDOWN_60D_SHALLOW_OR_DEEP,
    )

    assert len(shallow.trades) == 1
    assert len(deep.trades) == 1
    assert len(middle.trades) == 0
    assert middle.rejected_signals[0].reason == "FILTER_DRAWDOWN_60D_NOT_SHALLOW_OR_DEEP"


def test_down_closes_gte_3_variant_allows_and_rejects_expected_counts() -> None:
    allowed = _run(
        {"RELIANCE": _variant_signal_frame([110, 100, 95, 80])},
        end_date=date(2026, 3, 20),
        strategy_variant=S1_DOWN_CLOSES_GTE_3,
    )
    rejected = _run(
        {"RELIANCE": _variant_signal_frame([90, 100, 95, 80])},
        end_date=date(2026, 3, 20),
        strategy_variant=S1_DOWN_CLOSES_GTE_3,
    )

    assert len(allowed.trades) == 1
    assert len(rejected.trades) == 0
    assert rejected.rejected_signals[0].reason == "FILTER_DOWN_CLOSES_LT_3"


def test_broad_best_guess_applies_all_required_conditions() -> None:
    high_atr_expansion = _run(
        {"RELIANCE": _variant_signal_frame([110, 100, 95, 80])},
        end_date=date(2026, 3, 20),
        strategy_variant=S1_BROAD_BEST_GUESS,
    )

    assert (
        s1_variant_rejection_reason(
            {
                "z_score": -3.2,
                "stock_consecutive_down_closes": 3,
                "stock_drawdown_60d_pct": -25,
                "stock_close_vs_60d_low_pct": 0,
                "stock_atr14_change_10d_pct": 10,
            },
            S1_BROAD_BEST_GUESS,
        )
        == "FILTER_ZSCORE_TOO_DEEP"
    )
    assert high_atr_expansion.rejected_signals[0].reason == "FILTER_ATR_EXPANSION_TOO_HIGH"


def test_missing_variant_context_rejects_non_baseline_signals() -> None:
    result = _run(
        {"RELIANCE": _same_day_signal_frame([10, 12, 14, 8, 9])},
        strategy_variant=S1_AVOID_MESSY_MIDDLE_V1,
    )

    assert len(result.trades) == 0
    assert result.rejected_signals[0].reason == "FILTER_CONTEXT_MISSING"


def test_filter_rejection_happens_before_capacity_checks() -> None:
    result = _run(
        {
            "FILTERED": _variant_signal_frame([110, 100, 98, 95]),
            "KEPT": _variant_signal_frame([110, 100, 95, 80]),
        },
        end_date=date(2026, 3, 20),
        max_concurrent_positions=1,
        strategy_variant=S1_AVOID_MESSY_MIDDLE_V1,
    )

    assert result.rejected_signals[0].reason == "FILTER_MESSY_MIDDLE_DRAWDOWN"
    assert all(
        rejected.reason != "PORTFOLIO_CAPACITY_FULL"
        for rejected in result.rejected_signals
        if rejected.symbol == "FILTERED"
    )


def _run(
    data_by_symbol: dict[str, pd.DataFrame],
    start_date: date = date(2026, 1, 1),
    end_date: date = date(2026, 1, 20),
    max_concurrent_positions: int = 5,
    atr_multiplier: Decimal = Decimal("10"),
    strategy_variant: str = S1_BASELINE,
    candidate_ranking_mode: str = "none",
) -> PortfolioBacktestResult:
    """Run the portfolio backtest with compact deterministic settings."""

    return run_s1_portfolio_backtest(
        data_by_symbol=data_by_symbol,
        start_date=start_date,
        end_date=end_date,
        starting_equity=Decimal("100000"),
        risk_per_trade=Decimal("0.01"),
        max_concurrent_positions=max_concurrent_positions,
        zscore_window=3,
        entry_threshold=-1.0,
        atr_window=1,
        atr_multiplier=atr_multiplier,
        reward_risk_ratio=Decimal("1"),
        max_holding_sessions=20,
        round_trip_cost_pct=Decimal("0"),
        strategy_variant=strategy_variant,
        candidate_ranking_mode=candidate_ranking_mode,
    )


def _two_signal_frame() -> pd.DataFrame:
    """Build data with two signals while the first same-symbol trade is active."""

    return _frame([10, 12, 14, 8, 7, 8, 9, 11, 13, 15, 9, 10, 11, 12, 13, 14])


def _late_signal_frame() -> pd.DataFrame:
    """Build data with a later S1 signal."""

    return _frame([10, 11, 12, 13, 14, 15, 16, 18, 20, 12, 13, 14, 15])


def _early_winner_frame() -> pd.DataFrame:
    """Build data where the first signal closes before the later symbol signal."""

    data = _frame([10, 12, 14, 8, 12, 13, 14, 15])
    data.loc[4, "high"] = 13.0
    return data


def _post_window_target_frame() -> pd.DataFrame:
    """Build data where only the row after end date would hit the target."""

    data = _frame([10, 12, 14, 8, 9, 100])
    data.loc[5, "open"] = 100.0
    data.loc[5, "high"] = 101.0
    data.loc[5, "low"] = 99.0
    data.loc[5, "close"] = 100.0
    return data


def _same_day_signal_frame(closes: list[float]) -> pd.DataFrame:
    """Build data with a signal on the fourth row."""

    return _frame(closes)


def _high_volume(data: pd.DataFrame) -> pd.DataFrame:
    output = data.copy(deep=True)
    output["volume"] = 1_000_000_000_000
    return output


def _variant_signal_frame(
    trailing_closes: list[float],
    prior_low: float | None = None,
) -> pd.DataFrame:
    """Build long-lookback data with one final signal and optional prior low."""

    closes = [100.0] * 67 + [float(close) for close in trailing_closes]
    data = _frame(closes)
    data["date"] = pd.date_range("2026-01-01", periods=len(closes), freq="D")
    if prior_low is not None:
        data.loc[40, ["open", "high", "low", "close"]] = float(prior_low)
    data.loc[len(data)] = {
        "date": data.loc[len(data) - 1, "date"] + pd.Timedelta(days=1),
        "open": float(trailing_closes[-1]),
        "high": float(trailing_closes[-1]) + 10.0,
        "low": float(trailing_closes[-1]) - 1.0,
        "close": float(trailing_closes[-1]) + 2.0,
        "volume": 1000,
    }
    return data


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
