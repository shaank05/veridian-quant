"""Tests for S2 signal-time context metadata enrichment."""

from datetime import date
from types import MappingProxyType
from unittest.mock import patch

import pytest

from veridian_quant.v2.backtesting.markov_portfolio_runner import (
    run_s2_markov_portfolio_backtest,
)
from veridian_quant.v2.backtesting.s2_candidate_ranking import (
    rank_s2_entry_candidates,
)
from veridian_quant.v2.backtesting.s2_signal_context import (
    enrich_s2_signals_with_context,
)
from veridian_quant.v2.data.models import Signal, SignalType
from veridian_quant.v2.strategies.s2_markov_state_transition import STRATEGY_NAME

import pandas as pd


def test_enrichment_does_not_mutate_original_signal() -> None:
    signal = _signal(date(2026, 8, 10))

    enriched = enrich_s2_signals_with_context(
        (signal,),
        {"AAA": _frame(rows=240)},
    )

    assert enriched[0] is not signal
    assert "stock_close_vs_sma50_pct" in enriched[0].metadata
    assert "stock_close_vs_sma50_pct" not in signal.metadata


def test_enrichment_uses_only_rows_on_or_before_signal_date() -> None:
    base = _frame(rows=240)
    with_future_spike = pd.concat(
        [
            base,
            pd.DataFrame(
                [
                    {
                        "date": pd.Timestamp("2026-08-11"),
                        "open": 10000.0,
                        "high": 10010.0,
                        "low": 9990.0,
                        "close": 10000.0,
                        "volume": 1000,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    signal = _signal(date(2026, 8, 10))

    baseline = enrich_s2_signals_with_context((signal,), {"AAA": base})[0]
    enriched = enrich_s2_signals_with_context(
        (signal,),
        {"AAA": with_future_spike},
    )[0]

    assert enriched.metadata["stock_return_5d_pct"] == pytest.approx(
        baseline.metadata["stock_return_5d_pct"]
    )


def test_enrichment_handles_missing_nifty_data() -> None:
    enriched = enrich_s2_signals_with_context(
        (_signal(date(2026, 8, 10)),),
        {"AAA": _frame(rows=240)},
    )[0]

    assert enriched.metadata["stock_close_vs_sma50_pct"] is not None
    assert enriched.metadata["nifty_close_vs_sma50_pct"] is None
    assert enriched.metadata["relative_strength_20d_vs_nifty"] is None


def test_enrichment_handles_insufficient_lookback() -> None:
    enriched = enrich_s2_signals_with_context(
        (_signal(date(2026, 1, 5)),),
        {"AAA": _frame(rows=10)},
    )[0]

    assert enriched.metadata["stock_close_vs_sma50_pct"] is None
    assert enriched.metadata["stock_atr14_pct"] is None


def test_stock_context_fields_are_calculated() -> None:
    enriched = enrich_s2_signals_with_context(
        (_signal(date(2026, 8, 10)),),
        {"AAA": _frame(rows=240)},
    )[0]
    metadata = enriched.metadata

    assert metadata["stock_close_vs_sma50_pct"] > 0
    assert metadata["stock_sma50_slope_20d_pct"] > 0
    assert metadata["stock_return_5d_pct"] > 0
    assert metadata["stock_drawdown_60d_pct"] == pytest.approx(0.0)
    assert metadata["stock_close_vs_60d_low_pct"] > 0
    assert metadata["stock_is_20d_low"] is False
    assert metadata["stock_atr14_pct"] > 0
    assert metadata["stock_atr14_change_5d_pct"] == pytest.approx(0.0)
    assert metadata["stock_consecutive_down_closes"] == 0
    assert metadata["stock_signal_day_return_pct"] > 0


def test_nifty_and_relative_strength_fields_are_calculated() -> None:
    enriched = enrich_s2_signals_with_context(
        (_signal(date(2026, 8, 10)),),
        {"AAA": _frame(rows=240, daily_step=2.0)},
        nifty_data=_frame(rows=240, daily_step=1.0),
    )[0]
    metadata = enriched.metadata

    assert metadata["nifty_close_vs_sma50_pct"] > 0
    assert metadata["nifty_sma50_slope_20d_pct"] > 0
    assert metadata["nifty_return_5d_pct"] > 0
    assert metadata["relative_strength_20d_vs_nifty"] > 0
    assert metadata["relative_strength_60d_vs_nifty"] > 0
    assert metadata["relative_strength_120d_vs_nifty"] > 0


def test_portfolio_runner_applies_enrichment_before_ranking() -> None:
    with patch(
        "veridian_quant.v2.backtesting.markov_portfolio_runner.generate_s2_markov_signals",
        return_value=[_signal(date(2026, 8, 10))],
    ):
        result = run_s2_markov_portfolio_backtest(
            data_by_symbol={"AAA": _frame(rows=240)},
            nifty_data=_frame(rows=240),
            start_date=date(2026, 8, 10),
            end_date=date(2026, 8, 20),
            starting_equity=100000,
            min_state_observations=1,
            forward_return_sessions=1,
            round_trip_cost_pct=0,
            s2_candidate_ranking_mode="2025_guard_v1",
        )

    signal = result.signals[0]
    assert signal.metadata["stock_close_vs_sma50_pct"] is not None
    assert signal.metadata["nifty_close_vs_sma50_pct"] is not None
    assert signal.metadata["s2_score_penalty"] > 2.0


def test_none_ranking_preserves_order_with_enriched_metadata() -> None:
    signals = (
        _signal(date(2026, 8, 11), symbol="BBB"),
        _signal(date(2026, 8, 10), symbol="AAA"),
    )
    enriched = enrich_s2_signals_with_context(
        signals,
        {"AAA": _frame(rows=240), "BBB": _frame(rows=240)},
    )

    ranked = rank_s2_entry_candidates(enriched, "none")

    assert [(signal.generated_on, signal.symbol) for signal in ranked] == [
        (date(2026, 8, 10), "AAA"),
        (date(2026, 8, 11), "BBB"),
    ]


def test_clean_state_v1_order_is_unchanged_with_enriched_metadata() -> None:
    signals = (
        _signal(
            date(2026, 8, 10),
            symbol="DIRTY",
            state_label="RET_STRONG_UP|VOL_LOW|DD_DEEP|LOW_NEAR",
        ),
        _signal(
            date(2026, 8, 10),
            symbol="CLEAN",
            state_label="RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW",
        ),
    )
    enriched = enrich_s2_signals_with_context(
        signals,
        {"DIRTY": _frame(rows=240), "CLEAN": _frame(rows=240)},
    )

    ranked = rank_s2_entry_candidates(enriched, "clean_state_v1")

    assert ranked[0].symbol == "CLEAN"


def _signal(
    generated_on: date,
    symbol: str = "AAA",
    state_label: str = "RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW",
) -> Signal:
    return Signal(
        symbol=symbol,
        signal_type=SignalType.LONG,
        generated_on=generated_on,
        strategy_name=STRATEGY_NAME,
        reason="test S2 signal",
        metadata=MappingProxyType(
            {
                "strategy_family": STRATEGY_NAME,
                "state_label": state_label,
                "state_observation_count": 20,
                "positive_transition_probability": 0.70,
                "average_forward_return_pct": 4.0,
                "median_forward_return_pct": 4.0,
                "current_5d_return_pct": 2.0,
                "current_atr_pct": 3.0,
                "current_drawdown_60d_pct": -5.0,
                "current_close_vs_60d_low_pct": 20.0,
            }
        ),
    )


def _frame(rows: int, daily_step: float = 1.0) -> pd.DataFrame:
    start = pd.Timestamp("2026-01-01")
    output = []
    for index in range(rows):
        close = 100.0 + (index * daily_step)
        output.append(
            {
                "date": start + pd.Timedelta(days=index),
                "open": close - 0.5,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1000,
            }
        )
    return pd.DataFrame(output)
