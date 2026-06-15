"""Optional research-only filters for S2 Markov signals."""

from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any

import pandas as pd

from veridian_quant.v2.data.models import Signal


MARKOV_SIGNAL_FILTER_NONE = "none"
MARKOV_SIGNAL_FILTERS = (
    MARKOV_SIGNAL_FILTER_NONE,
    "exclude_ret_down",
    "keep_ret_flat_up_strong_up",
    "exclude_dd_deep",
    "exclude_ret_down_and_dd_deep",
    "exclude_low_near",
    "balanced_markov_v1",
)


@dataclass(frozen=True, slots=True)
class ParsedMarkovState:
    ret_state: str
    vol_state: str
    dd_state: str
    low_state: str
    valid: bool


@dataclass(frozen=True, slots=True)
class MarkovSignalFilterDecision:
    signal: Signal
    kept: bool


def parse_markov_state_label(state_label: object) -> ParsedMarkovState:
    """Safely parse RET_*|VOL_*|DD_*|LOW_* labels."""

    unknown = ParsedMarkovState("UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", False)
    if state_label is None or pd.isna(state_label):
        return unknown
    parts = str(state_label).split("|")
    if len(parts) != 4:
        return unknown
    ret_state, vol_state, dd_state, low_state = parts
    if not (
        ret_state.startswith("RET_")
        and vol_state.startswith("VOL_")
        and dd_state.startswith("DD_")
        and low_state.startswith("LOW_")
    ):
        return unknown
    return ParsedMarkovState(ret_state, vol_state, dd_state, low_state, True)


def apply_markov_signal_filter(
    signal: Signal,
    filter_name: str = MARKOV_SIGNAL_FILTER_NONE,
) -> MarkovSignalFilterDecision:
    """Return whether a signal is kept by the requested research filter."""

    filter_name = validate_markov_signal_filter(filter_name)
    if filter_name == MARKOV_SIGNAL_FILTER_NONE:
        return MarkovSignalFilterDecision(signal=signal, kept=True)

    kept = _is_kept(signal, filter_name)
    decision = "kept" if kept else "filtered"
    return MarkovSignalFilterDecision(
        signal=_with_filter_metadata(signal, filter_name, decision),
        kept=kept,
    )


def validate_markov_signal_filter(filter_name: str) -> str:
    """Return a valid filter name or raise ValueError."""

    if filter_name not in MARKOV_SIGNAL_FILTERS:
        raise ValueError(
            f"unsupported S2 Markov signal filter: {filter_name}; "
            f"expected one of {', '.join(MARKOV_SIGNAL_FILTERS)}"
        )
    return filter_name


def markov_strategy_variant(strategy_name: str, filter_name: str) -> str:
    """Return the strategy variant label for a filter experiment."""

    filter_name = validate_markov_signal_filter(filter_name)
    if filter_name == MARKOV_SIGNAL_FILTER_NONE:
        return strategy_name
    return f"{strategy_name}__{filter_name}"


def _is_kept(signal: Signal, filter_name: str) -> bool:
    metadata = signal.metadata
    state = parse_markov_state_label(metadata.get("state_label"))
    if not state.valid:
        return False

    if filter_name == "exclude_ret_down":
        return state.ret_state != "RET_DOWN"
    if filter_name == "keep_ret_flat_up_strong_up":
        return state.ret_state in {"RET_FLAT", "RET_UP", "RET_STRONG_UP"}
    if filter_name == "exclude_dd_deep":
        return state.dd_state != "DD_DEEP"
    if filter_name == "exclude_ret_down_and_dd_deep":
        return state.ret_state != "RET_DOWN" and state.dd_state != "DD_DEEP"
    if filter_name == "exclude_low_near":
        return state.low_state != "LOW_NEAR"
    if filter_name == "balanced_markov_v1":
        return (
            state.ret_state in {"RET_FLAT", "RET_UP", "RET_STRONG_UP"}
            and state.dd_state in {"DD_SHALLOW", "DD_MID"}
            and state.low_state in {"LOW_MID_RANGE", "LOW_FAR_FROM_LOW"}
            and state.vol_state in {"VOL_MID", "VOL_HIGH"}
            and _gte(metadata.get("state_observation_count"), 15)
        )
    raise ValueError(f"unsupported S2 Markov signal filter: {filter_name}")


def _with_filter_metadata(
    signal: Signal,
    filter_name: str,
    decision: str,
) -> Signal:
    metadata: dict[str, Any] = dict(signal.metadata)
    metadata["markov_signal_filter"] = filter_name
    metadata["markov_filter_decision"] = decision
    return replace(signal, metadata=MappingProxyType(metadata))


def _gte(value: object, threshold: int) -> bool:
    if value is None or pd.isna(value):
        return False
    try:
        return float(value) >= threshold
    except (TypeError, ValueError):
        return False
