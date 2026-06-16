"""S2-specific same-day candidate ranking for research experiments."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from math import isfinite
from types import MappingProxyType

import pandas as pd

from veridian_quant.v2.data.models import Signal
from veridian_quant.v2.strategies.s2_markov_filters import parse_markov_state_label


S2_CANDIDATE_RANKING_NONE = "none"
S2_CANDIDATE_RANKING_STATE_EDGE_V1 = "state_edge_v1"
S2_CANDIDATE_RANKING_CLEAN_STATE_V1 = "clean_state_v1"
S2_CANDIDATE_RANKING_STATE_QUALITY_V1 = "state_quality_v1"
S2_CANDIDATE_RANKING_HYBRID_STATE_CONTEXT_V1 = "hybrid_state_context_v1"
S2_CANDIDATE_RANKING_AVOID_SHALLOW_UPTREND_PULLBACK_V1 = (
    "avoid_shallow_uptrend_pullback_v1"
)
S2_AVOID_SHALLOW_UPTREND_PULLBACK_VARIANT = (
    "S2_MARKOV_STATE_TRANSITION_AVOID_SHALLOW_UPTREND_PULLBACK_V1"
)
S2_CANDIDATE_RANKING_MODES = (
    S2_CANDIDATE_RANKING_NONE,
    S2_CANDIDATE_RANKING_STATE_EDGE_V1,
    S2_CANDIDATE_RANKING_CLEAN_STATE_V1,
    S2_CANDIDATE_RANKING_STATE_QUALITY_V1,
    S2_CANDIDATE_RANKING_HYBRID_STATE_CONTEXT_V1,
    S2_CANDIDATE_RANKING_AVOID_SHALLOW_UPTREND_PULLBACK_V1,
)


@dataclass(frozen=True, slots=True)
class _RankedS2Candidate:
    signal: Signal
    original_index: int
    score: float
    state_edge: float
    state_quality: float
    context: float
    penalty: float


def rank_s2_entry_candidates(
    signals: tuple[Signal, ...],
    mode: str = S2_CANDIDATE_RANKING_NONE,
) -> tuple[Signal, ...]:
    """Return S2 signals ordered for same-day portfolio candidate selection."""

    mode = validate_s2_candidate_ranking_mode(mode)
    ordered = tuple(sorted(signals, key=_signal_sort_key))
    if mode == S2_CANDIDATE_RANKING_NONE:
        return ordered

    candidates = [
        _score_candidate(signal=signal, original_index=index, mode=mode)
        for index, signal in enumerate(ordered)
    ]
    ranked_by_date: list[Signal] = []
    for generated_on in sorted(
        {candidate.signal.generated_on for candidate in candidates}
    ):
        date_candidates = [
            candidate
            for candidate in candidates
            if candidate.signal.generated_on == generated_on
        ]
        ranked = sorted(
            date_candidates,
            key=lambda candidate: (
                -candidate.score,
                candidate.signal.symbol,
                str(candidate.signal.metadata.get("instrument_key", "")),
                candidate.original_index,
            ),
        )
        pool_size = len(ranked)
        for rank, candidate in enumerate(ranked, start=1):
            ranked_by_date.append(
                _with_ranking_metadata(
                    candidate=candidate,
                    mode=mode,
                    rank=rank,
                    pool_size=pool_size,
                )
            )
    return tuple(ranked_by_date)


def validate_s2_candidate_ranking_mode(mode: str) -> str:
    """Return a valid S2 ranking mode or raise ValueError."""

    if mode not in S2_CANDIDATE_RANKING_MODES:
        raise ValueError(
            f"unsupported S2 candidate ranking mode: {mode}; "
            f"expected one of {', '.join(S2_CANDIDATE_RANKING_MODES)}"
        )
    return mode


def _score_candidate(
    signal: Signal,
    original_index: int,
    mode: str,
) -> _RankedS2Candidate:
    state_edge = _state_edge_score(signal)
    state_quality, state_penalty = _clean_state_score(signal)
    context, context_penalty = _context_score(signal)

    if mode == S2_CANDIDATE_RANKING_STATE_EDGE_V1:
        score = state_edge
        penalty = 0.0
        state_quality_for_export = 0.0
        context_for_export = 0.0
    elif mode == S2_CANDIDATE_RANKING_CLEAN_STATE_V1:
        score = state_quality - state_penalty
        penalty = state_penalty
        state_quality_for_export = state_quality
        context_for_export = 0.0
    elif mode == S2_CANDIDATE_RANKING_STATE_QUALITY_V1:
        score = state_edge + state_quality - state_penalty
        penalty = state_penalty
        state_quality_for_export = state_quality
        context_for_export = 0.0
    elif mode == S2_CANDIDATE_RANKING_HYBRID_STATE_CONTEXT_V1:
        penalty = state_penalty + context_penalty
        score = state_edge + state_quality + context - penalty
        state_quality_for_export = state_quality
        context_for_export = context
    else:
        uptrend_score, uptrend_penalty = _avoid_shallow_uptrend_pullback_score(
            signal
        )
        penalty = uptrend_penalty
        score = state_edge + uptrend_score - penalty
        state_quality_for_export = uptrend_score
        context_for_export = 0.0

    return _RankedS2Candidate(
        signal=signal,
        original_index=original_index,
        score=score,
        state_edge=state_edge,
        state_quality=state_quality_for_export,
        context=context_for_export,
        penalty=penalty,
    )


def _state_edge_score(signal: Signal) -> float:
    metadata = signal.metadata
    probability = _number(metadata.get("positive_transition_probability"))
    average = _number(metadata.get("average_forward_return_pct")) / 10.0
    median = _number(metadata.get("median_forward_return_pct")) / 10.0
    observations = min(
        max(_number(metadata.get("state_observation_count")), 0.0),
        50.0,
    )
    return probability + average + median + (observations / 50.0)


def _clean_state_score(signal: Signal) -> tuple[float, float]:
    state = parse_markov_state_label(signal.metadata.get("state_label"))
    if not state.valid:
        return 0.0, 0.5

    positive = 0.0
    penalty = 0.0
    if state.ret_state == "RET_UP":
        positive += 0.45
    elif state.ret_state == "RET_FLAT":
        positive += 0.35
    elif state.ret_state == "RET_STRONG_DOWN":
        positive += 0.10
    elif state.ret_state == "RET_DOWN":
        penalty += 0.35
    elif state.ret_state == "RET_STRONG_UP":
        penalty += 0.40

    if state.low_state == "LOW_FAR_FROM_LOW":
        positive += 0.35
    elif state.low_state == "LOW_MID_RANGE":
        positive += 0.10
    elif state.low_state == "LOW_NEAR":
        penalty += 0.35

    if state.dd_state == "DD_SHALLOW":
        positive += 0.30
    elif state.dd_state == "DD_DEEP":
        penalty += 0.35

    if state.vol_state == "VOL_HIGH":
        positive += 0.20
    elif state.vol_state == "VOL_MID":
        positive += 0.15
    elif state.vol_state == "VOL_LOW":
        penalty += 0.20

    return positive, penalty


def _context_score(signal: Signal) -> tuple[float, float]:
    metadata = signal.metadata
    score = 0.0
    penalty = 0.0

    five_day_return = _number(metadata.get("current_5d_return_pct"))
    atr_pct = _number(metadata.get("current_atr_pct"))
    drawdown_pct = _number(metadata.get("current_drawdown_60d_pct"))
    low_distance_pct = _number(metadata.get("current_close_vs_60d_low_pct"))
    average_forward_return_pct = _number(metadata.get("average_forward_return_pct"))

    if five_day_return <= -5.0:
        score += 0.10
    elif -1.0 <= five_day_return <= 4.0:
        score += 0.15
    elif five_day_return >= 8.0:
        penalty += 0.25

    if 2.0 <= atr_pct <= 8.0:
        score += 0.20
    elif atr_pct > 12.0:
        penalty += 0.20

    if drawdown_pct >= -10.0:
        score += 0.15
    elif drawdown_pct <= -25.0:
        penalty += 0.20

    if low_distance_pct >= 20.0:
        score += 0.20
    elif low_distance_pct <= 5.0:
        penalty += 0.25

    if average_forward_return_pct > 15.0:
        penalty += 0.15

    return score, penalty


def _avoid_shallow_uptrend_pullback_score(signal: Signal) -> tuple[float, float]:
    state = parse_markov_state_label(signal.metadata.get("state_label"))
    if not state.valid:
        return 0.0, 0.75

    score = 0.0
    penalty = 0.0
    if (
        state.ret_state == "RET_UP"
        and state.dd_state == "DD_SHALLOW"
        and state.low_state == "LOW_FAR_FROM_LOW"
    ):
        penalty += 2.00
    if state.ret_state == "RET_STRONG_UP" and state.dd_state == "DD_SHALLOW":
        penalty += 1.75
    if state.ret_state == "RET_STRONG_UP" and state.vol_state == "VOL_HIGH":
        penalty += 1.25
    if (
        state.dd_state == "DD_SHALLOW"
        and state.low_state == "LOW_FAR_FROM_LOW"
        and state.ret_state not in {"RET_FLAT", "RET_STRONG_DOWN"}
    ):
        penalty += 1.00

    if state.ret_state == "RET_FLAT":
        score += 0.75
    if state.dd_state == "DD_MID":
        score += 0.65
    elif state.dd_state == "DD_DEEP":
        score += 0.25
    if state.low_state == "LOW_MID_RANGE":
        score += 0.55
    elif state.low_state == "LOW_NEAR":
        score += 0.70

    if state.ret_state == "RET_STRONG_DOWN":
        if state.dd_state in {"DD_MID", "DD_DEEP"}:
            score += 0.35
        if state.low_state in {"LOW_NEAR", "LOW_MID_RANGE"}:
            score += 0.35
        if state.dd_state == "DD_SHALLOW" and state.low_state == "LOW_FAR_FROM_LOW":
            penalty += 0.40

    return score, penalty


def _with_ranking_metadata(
    candidate: _RankedS2Candidate,
    mode: str,
    rank: int,
    pool_size: int,
) -> Signal:
    metadata = dict(candidate.signal.metadata)
    prefixed_mode = f"s2:{mode}"
    metadata.update(
        {
            "s2_candidate_ranking_mode": mode,
            "s2_candidate_rank": rank,
            "s2_candidate_score": candidate.score,
            "s2_score_state_edge": candidate.state_edge,
            "s2_score_state_quality": candidate.state_quality,
            "s2_score_context": candidate.context,
            "s2_score_penalty": candidate.penalty,
            "candidate_ranking_mode": prefixed_mode,
            "candidate_rank": rank,
            "candidate_score": candidate.score,
            "candidate_pool_size_for_date": pool_size,
        }
    )
    return replace(candidate.signal, metadata=MappingProxyType(metadata))


def _signal_sort_key(signal: Signal) -> tuple[date, str]:
    return (signal.generated_on, signal.symbol)


def _number(value: object) -> float:
    if value is None or pd.isna(value):
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not isfinite(number):
        return 0.0
    return number
