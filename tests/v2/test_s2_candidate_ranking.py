"""Tests for S2 capacity-aware candidate ranking experiments."""

from datetime import date
from types import MappingProxyType

import pytest

from veridian_quant.v2.backtesting.s2_candidate_ranking import (
    rank_s2_entry_candidates,
)
from veridian_quant.v2.data.models import Signal, SignalType
from veridian_quant.v2.strategies.s2_markov_state_transition import STRATEGY_NAME


def test_none_ranking_preserves_chronological_symbol_order() -> None:
    signals = (
        _signal("BBB", date(2026, 1, 2)),
        _signal("AAA", date(2026, 1, 1)),
    )

    ranked = rank_s2_entry_candidates(signals, "none")

    assert [(signal.generated_on, signal.symbol) for signal in ranked] == [
        (date(2026, 1, 1), "AAA"),
        (date(2026, 1, 2), "BBB"),
    ]
    assert "candidate_rank" not in ranked[0].metadata


def test_ranking_groups_only_same_day_signals() -> None:
    signals = (
        _signal("BBB", date(2026, 1, 1), probability=0.70),
        _signal("AAA", date(2026, 1, 2), probability=0.95),
        _signal("CCC", date(2026, 1, 1), probability=0.90),
    )

    ranked = rank_s2_entry_candidates(signals, "state_edge_v1")

    assert [(signal.generated_on, signal.symbol) for signal in ranked] == [
        (date(2026, 1, 1), "CCC"),
        (date(2026, 1, 1), "BBB"),
        (date(2026, 1, 2), "AAA"),
    ]
    assert ranked[0].metadata["candidate_pool_size_for_date"] == 2
    assert ranked[2].metadata["candidate_pool_size_for_date"] == 1
    assert ranked[2].metadata["candidate_rank"] == 1


def test_higher_score_ranks_first_within_day() -> None:
    ranked = rank_s2_entry_candidates(
        (
            _signal("AAA", date(2026, 1, 1), probability=0.60),
            _signal("BBB", date(2026, 1, 1), probability=0.90),
        ),
        "state_edge_v1",
    )

    assert ranked[0].symbol == "BBB"
    assert ranked[0].metadata["candidate_rank"] == 1
    assert ranked[1].metadata["candidate_rank"] == 2


def test_ranking_metadata_is_added() -> None:
    ranked = rank_s2_entry_candidates(
        (_signal("AAA", date(2026, 1, 1)),),
        "hybrid_state_context_v1",
    )
    metadata = ranked[0].metadata

    assert metadata["s2_candidate_ranking_mode"] == "hybrid_state_context_v1"
    assert metadata["candidate_ranking_mode"] == "s2:hybrid_state_context_v1"
    assert {
        "s2_candidate_rank",
        "s2_candidate_score",
        "s2_score_state_edge",
        "s2_score_state_quality",
        "s2_score_context",
        "s2_score_penalty",
        "candidate_rank",
        "candidate_score",
        "candidate_pool_size_for_date",
    }.issubset(metadata)


def test_state_edge_v1_prefers_stronger_markov_edge() -> None:
    ranked = rank_s2_entry_candidates(
        (
            _signal("LOW", date(2026, 1, 1), probability=0.62, average=2.0),
            _signal("HIGH", date(2026, 1, 1), probability=0.82, average=6.0),
        ),
        "state_edge_v1",
    )

    assert ranked[0].symbol == "HIGH"


def test_clean_state_v1_prefers_cleaner_state_components() -> None:
    ranked = rank_s2_entry_candidates(
        (
            _signal("DIRTY", date(2026, 1, 1), state_label="RET_STRONG_UP|VOL_LOW|DD_DEEP|LOW_NEAR"),
            _signal("CLEAN", date(2026, 1, 1), state_label="RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW"),
        ),
        "clean_state_v1",
    )

    assert ranked[0].symbol == "CLEAN"


def test_state_quality_v1_combines_edge_and_state_quality() -> None:
    ranked = rank_s2_entry_candidates(
        (
            _signal(
                "EDGE_ONLY",
                date(2026, 1, 1),
                probability=0.90,
                average=5.0,
                state_label="RET_STRONG_UP|VOL_LOW|DD_DEEP|LOW_NEAR",
            ),
            _signal(
                "BALANCED",
                date(2026, 1, 1),
                probability=0.80,
                average=4.0,
                state_label="RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW",
            ),
        ),
        "state_quality_v1",
    )

    assert ranked[0].symbol == "BALANCED"


def test_hybrid_state_context_v1_handles_missing_metadata_safely() -> None:
    signal = _signal("AAA", date(2026, 1, 1), metadata_overrides={"current_atr_pct": None})

    ranked = rank_s2_entry_candidates((signal,), "hybrid_state_context_v1")

    assert ranked[0].metadata["candidate_rank"] == 1
    assert isinstance(ranked[0].metadata["candidate_score"], float)


def test_malformed_state_labels_do_not_crash() -> None:
    ranked = rank_s2_entry_candidates(
        (_signal("AAA", date(2026, 1, 1), state_label="BAD"),),
        "clean_state_v1",
    )

    assert ranked[0].metadata["candidate_rank"] == 1


def test_avoid_shallow_uptrend_pullback_penalizes_ret_up_shallow_far_from_low() -> None:
    ranked = rank_s2_entry_candidates(
        (
            _signal(
                "SHALLOW_UP",
                date(2026, 1, 1),
                probability=0.90,
                average=6.0,
                state_label="RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW",
            ),
            _signal(
                "DEEPER_FLAT",
                date(2026, 1, 1),
                probability=0.70,
                average=3.0,
                state_label="RET_FLAT|VOL_MID|DD_MID|LOW_MID_RANGE",
            ),
        ),
        "avoid_shallow_uptrend_pullback_v1",
    )

    assert ranked[0].symbol == "DEEPER_FLAT"
    assert ranked[1].metadata["s2_score_penalty"] > 0


def test_avoid_shallow_uptrend_pullback_penalizes_strong_up_shallow() -> None:
    ranked = rank_s2_entry_candidates(
        (
            _signal(
                "STRONG_UP",
                date(2026, 1, 1),
                probability=0.90,
                average=6.0,
                state_label="RET_STRONG_UP|VOL_MID|DD_SHALLOW|LOW_MID_RANGE",
            ),
            _signal(
                "NEAR_LOW",
                date(2026, 1, 1),
                probability=0.70,
                average=3.0,
                state_label="RET_FLAT|VOL_MID|DD_MID|LOW_NEAR",
            ),
        ),
        "avoid_shallow_uptrend_pullback_v1",
    )

    assert ranked[0].symbol == "NEAR_LOW"
    assert ranked[1].metadata["s2_score_penalty"] > 0


def test_avoid_shallow_uptrend_pullback_boosts_flat_mid_or_low_near_setups() -> None:
    ranked = rank_s2_entry_candidates(
        (
            _signal(
                "PLAIN_UP",
                date(2026, 1, 1),
                probability=0.75,
                average=3.0,
                state_label="RET_UP|VOL_MID|DD_MID|LOW_FAR_FROM_LOW",
            ),
            _signal(
                "FLAT_NEAR",
                date(2026, 1, 1),
                probability=0.75,
                average=3.0,
                state_label="RET_FLAT|VOL_MID|DD_MID|LOW_NEAR",
            ),
        ),
        "avoid_shallow_uptrend_pullback_v1",
    )

    assert ranked[0].symbol == "FLAT_NEAR"
    assert ranked[0].metadata["s2_score_state_quality"] > 0


def test_avoid_shallow_uptrend_pullback_is_deterministic() -> None:
    signals = (
        _signal(
            "AAA",
            date(2026, 1, 1),
            state_label="RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW",
        ),
        _signal(
            "BBB",
            date(2026, 1, 1),
            state_label="RET_FLAT|VOL_MID|DD_MID|LOW_NEAR",
        ),
    )

    first = rank_s2_entry_candidates(signals, "avoid_shallow_uptrend_pullback_v1")
    second = rank_s2_entry_candidates(signals, "avoid_shallow_uptrend_pullback_v1")

    assert first == second


def test_invalid_mode_raises() -> None:
    with pytest.raises(ValueError):
        rank_s2_entry_candidates((), "unknown")


def _signal(
    symbol: str,
    generated_on: date,
    probability: float = 0.70,
    average: float = 4.0,
    median: float | None = None,
    state_label: str = "RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW",
    metadata_overrides: dict[str, object] | None = None,
) -> Signal:
    metadata = {
        "state_label": state_label,
        "state_observation_count": 20,
        "positive_transition_probability": probability,
        "average_forward_return_pct": average,
        "median_forward_return_pct": average if median is None else median,
        "current_5d_return_pct": 2.0,
        "current_atr_pct": 3.0,
        "current_drawdown_60d_pct": -5.0,
        "current_close_vs_60d_low_pct": 20.0,
    }
    if metadata_overrides:
        metadata.update(metadata_overrides)
    return Signal(
        symbol=symbol,
        signal_type=SignalType.LONG,
        generated_on=generated_on,
        strategy_name=STRATEGY_NAME,
        reason="test S2 signal",
        metadata=MappingProxyType(metadata),
    )
