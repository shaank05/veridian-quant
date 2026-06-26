"""Pre-declared Phase 33G.1 S2 context experiment support."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from enum import Enum
from types import MappingProxyType
from typing import Mapping

import pandas as pd

from veridian_quant.v2.data.models import Signal
from veridian_quant.v2.data.sector_proxy_mapping import (
    SectorProxyResolution,
    resolve_sector_proxy,
)
from veridian_quant.v2.features.market_context import compute_market_context_features


CONTEXT_WINDOW = 20
BENCHMARK_STRONG_NEGATIVE_THRESHOLD = -0.05
RELATIVE_STRONG_UNDERPERFORM_THRESHOLD = -0.05
RELATIVE_OUTPERFORM_THRESHOLD = 0.0
SECTOR_NEGATIVE_THRESHOLD = 0.0

CONTEXT_BENCHMARK_20D_STRONG_NEGATIVE = (
    "CONTEXT_BENCHMARK_20D_STRONG_NEGATIVE"
)
CONTEXT_STOCK_NOT_OUTPERFORMING_BENCHMARK_20D = (
    "CONTEXT_STOCK_NOT_OUTPERFORMING_BENCHMARK_20D"
)
CONTEXT_STOCK_20D_STRONGLY_UNDERPERFORMING_BENCHMARK = (
    "CONTEXT_STOCK_20D_STRONGLY_UNDERPERFORMING_BENCHMARK"
)
CONTEXT_MAPPED_SECTOR_20D_NEGATIVE = "CONTEXT_MAPPED_SECTOR_20D_NEGATIVE"
CONTEXT_MAPPED_SECTOR_MISSING = "CONTEXT_MAPPED_SECTOR_MISSING"


class S2ContextExperimentVariant(str, Enum):
    """Allowed Phase 33G.1 context variants."""

    BASELINE = "S2_BASELINE"
    AVOID_BENCHMARK_20D_STRONG_NEGATIVE = (
        "S2_AVOID_BENCHMARK_20D_STRONG_NEGATIVE"
    )
    REQUIRE_STOCK_OUTPERFORMING_BENCHMARK_20D = (
        "S2_REQUIRE_STOCK_OUTPERFORMING_BENCHMARK_20D"
    )
    AVOID_STOCK_STRONGLY_UNDERPERFORMING_BENCHMARK_20D = (
        "S2_AVOID_STOCK_STRONGLY_UNDERPERFORMING_BENCHMARK_20D"
    )
    AVOID_MAPPED_SECTOR_NEGATIVE_20D = "S2_AVOID_MAPPED_SECTOR_NEGATIVE_20D"


ALL_PREDECLARED_VARIANTS = tuple(variant.value for variant in S2ContextExperimentVariant)
ALL_PREDECLARED = "ALL_PREDECLARED"


@dataclass(frozen=True, slots=True)
class S2ContextFilterDecision:
    """Context-filter result for one already-generated S2 signal."""

    kept: bool
    signal: Signal
    rejection_reason: str | None = None


def validate_s2_context_experiment_variant(
    variant: str | S2ContextExperimentVariant,
) -> S2ContextExperimentVariant:
    """Return a pre-declared variant or fail clearly."""

    if isinstance(variant, S2ContextExperimentVariant):
        return variant
    try:
        return S2ContextExperimentVariant(str(variant))
    except ValueError as error:
        allowed = ", ".join(ALL_PREDECLARED_VARIANTS)
        raise ValueError(
            f"unknown S2 context experiment variant: {variant}; allowed: {allowed}"
        ) from error


def should_keep_s2_context_signal(
    row: Mapping[str, object] | pd.Series,
    variant: str | S2ContextExperimentVariant,
) -> S2ContextFilterDecision:
    """Apply the fixed Phase 33G context rule to one context row."""

    normalized_variant = validate_s2_context_experiment_variant(variant)
    signal = row.get("signal")
    if not isinstance(signal, Signal):
        raise ValueError("context row must include a Signal under key 'signal'")

    reason = _rejection_reason_for_row(row, normalized_variant)
    metadata = dict(signal.metadata)
    metadata.update(
        {
            "s2_context_experiment_variant": normalized_variant.value,
            "s2_context_filter_description": variant_description(
                normalized_variant
            ),
            "s2_context_filter_decision": "kept" if reason is None else "filtered",
            "s2_context_filter_rejection_reason": reason,
            "s2_context_filter_window": CONTEXT_WINDOW,
            "s2_context_no_threshold_optimization": True,
            "s2_context_no_sector_fallback": True,
            "benchmark_index": row.get("benchmark"),
            "benchmark_ret_20d": _optional_float(row.get("benchmark_ret_20d")),
            "rel_benchmark_ret_20d": _optional_float(
                row.get("rel_benchmark_ret_20d")
            ),
            "sector": row.get("sector"),
            "sector_proxy": row.get("sector_proxy"),
            "sector_proxy_unmapped": _optional_bool(
                row.get("sector_proxy_unmapped")
            ),
            "sector_ret_20d": _optional_float(row.get("sector_ret_20d")),
        }
    )
    context_signal = replace(signal, metadata=MappingProxyType(metadata))
    return S2ContextFilterDecision(
        kept=reason is None,
        signal=context_signal,
        rejection_reason=reason,
    )


def build_s2_context_signal_filter(
    *,
    variant: str | S2ContextExperimentVariant,
    data_by_symbol: Mapping[str, pd.DataFrame],
    benchmark_data: pd.DataFrame,
    benchmark_index: str,
    classifications: Mapping[str, Mapping[str, str]],
    sector_index_data: Mapping[str, pd.DataFrame],
) -> object:
    """Build a callable compatible with the S2 portfolio runner hook."""

    normalized_variant = validate_s2_context_experiment_variant(variant)
    context_by_symbol = build_context_by_symbol(
        data_by_symbol=data_by_symbol,
        benchmark_data=benchmark_data,
        benchmark_index=benchmark_index,
        classifications=classifications,
        sector_index_data=sector_index_data,
    )

    def _filter(signal: Signal) -> tuple[Signal, str | None]:
        context_row = context_row_for_signal(signal, context_by_symbol)
        context_row["signal"] = signal
        decision = should_keep_s2_context_signal(context_row, normalized_variant)
        return decision.signal, decision.rejection_reason

    return _filter


def build_context_by_symbol(
    *,
    data_by_symbol: Mapping[str, pd.DataFrame],
    benchmark_data: pd.DataFrame,
    benchmark_index: str,
    classifications: Mapping[str, Mapping[str, str]],
    sector_index_data: Mapping[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """Compute 20-session Phase 33E context frames for available symbols."""

    context_by_symbol: dict[str, pd.DataFrame] = {}
    for symbol, stock_frame in data_by_symbol.items():
        classification = classifications.get(symbol.upper(), {})
        resolution = resolve_sector_proxy(
            classification.get("sector", "UNKNOWN"),
            fallback_to_nifty500=False,
        )
        sector_frame = (
            sector_index_data.get(resolution.sector_proxy)
            if resolution.sector_proxy is not None
            else None
        )
        context = compute_market_context_features(
            stock_frame,
            benchmark_data,
            sector_index_df=sector_frame,
            windows=(CONTEXT_WINDOW,),
            benchmark_name=benchmark_index,
            sector=classification.get("sector", "UNKNOWN"),
            sector_proxy=resolution.sector_proxy,
            fallback_sector_to_nifty500=False,
        )
        context_by_symbol[symbol.upper()] = context
    return context_by_symbol


def context_row_for_signal(
    signal: Signal,
    context_by_symbol: Mapping[str, pd.DataFrame],
) -> dict[str, object]:
    """Return the context row for a signal date, or explicit missing context."""

    context = context_by_symbol.get(signal.symbol.upper())
    if context is None or context.empty:
        return _missing_context_row(signal, "missing_symbol_context")

    session_dates = pd.to_datetime(context["session_date"]).dt.date
    exact = context.loc[session_dates == signal.generated_on]
    if exact.empty:
        return _missing_context_row(signal, "missing_signal_date_context")
    row = exact.iloc[-1].to_dict()
    row["s2_context_missing_reason"] = None
    return row


def variant_description(variant: str | S2ContextExperimentVariant) -> str:
    """Return an audit-friendly fixed-rule description."""

    normalized_variant = validate_s2_context_experiment_variant(variant)
    descriptions = {
        S2ContextExperimentVariant.BASELINE: "No context filter.",
        S2ContextExperimentVariant.AVOID_BENCHMARK_20D_STRONG_NEGATIVE: (
            "Skip entries when benchmark_ret_20d <= -0.05."
        ),
        S2ContextExperimentVariant.REQUIRE_STOCK_OUTPERFORMING_BENCHMARK_20D: (
            "Allow entries only when rel_benchmark_ret_20d > 0."
        ),
        S2ContextExperimentVariant.AVOID_STOCK_STRONGLY_UNDERPERFORMING_BENCHMARK_20D: (
            "Skip entries when rel_benchmark_ret_20d <= -0.05."
        ),
        S2ContextExperimentVariant.AVOID_MAPPED_SECTOR_NEGATIVE_20D: (
            "For mapped sector proxies only, skip entries when sector_ret_20d <= 0."
        ),
    }
    return descriptions[normalized_variant]


def variant_metadata(
    *,
    variant: str | S2ContextExperimentVariant,
    benchmark_index: str,
    classification_file: str,
) -> dict[str, object]:
    """Return static metadata for experiment output."""

    normalized_variant = validate_s2_context_experiment_variant(variant)
    return {
        "phase": "33G.1",
        "variant": normalized_variant.value,
        "description": variant_description(normalized_variant),
        "benchmark_index": benchmark_index,
        "classification_file": classification_file,
        "context_window_sessions": CONTEXT_WINDOW,
        "benchmark_strong_negative_threshold": (
            BENCHMARK_STRONG_NEGATIVE_THRESHOLD
        ),
        "relative_outperform_threshold": RELATIVE_OUTPERFORM_THRESHOLD,
        "relative_strong_underperform_threshold": (
            RELATIVE_STRONG_UNDERPERFORM_THRESHOLD
        ),
        "sector_negative_threshold": SECTOR_NEGATIVE_THRESHOLD,
        "markov_signal_filter": "exclude_ret_down",
        "s2_candidate_ranking": "none",
        "threshold_optimization": False,
        "combined_filters": False,
        "sector_fallback": False,
        "fundamentals_ratios": False,
        "market_cap_buckets": False,
        "production_approval": False,
    }


def needed_sector_indices_for_symbols(
    symbols: list[str],
    classifications: Mapping[str, Mapping[str, str]],
) -> dict[str, SectorProxyResolution]:
    """Resolve sector proxies without benchmark fallback for selected symbols."""

    return {
        symbol.upper(): resolve_sector_proxy(
            classifications.get(symbol.upper(), {}).get("sector", "UNKNOWN"),
            fallback_to_nifty500=False,
        )
        for symbol in symbols
    }


def _rejection_reason_for_row(
    row: Mapping[str, object] | pd.Series,
    variant: S2ContextExperimentVariant,
) -> str | None:
    if variant == S2ContextExperimentVariant.BASELINE:
        return None
    if variant == S2ContextExperimentVariant.AVOID_BENCHMARK_20D_STRONG_NEGATIVE:
        benchmark_ret = _optional_float(row.get("benchmark_ret_20d"))
        if _is_missing(benchmark_ret):
            return None
        if benchmark_ret <= BENCHMARK_STRONG_NEGATIVE_THRESHOLD:
            return CONTEXT_BENCHMARK_20D_STRONG_NEGATIVE
        return None
    if variant == S2ContextExperimentVariant.REQUIRE_STOCK_OUTPERFORMING_BENCHMARK_20D:
        relative_ret = _optional_float(row.get("rel_benchmark_ret_20d"))
        if _is_missing(relative_ret) or relative_ret <= RELATIVE_OUTPERFORM_THRESHOLD:
            return CONTEXT_STOCK_NOT_OUTPERFORMING_BENCHMARK_20D
        return None
    if (
        variant
        == S2ContextExperimentVariant.AVOID_STOCK_STRONGLY_UNDERPERFORMING_BENCHMARK_20D
    ):
        relative_ret = _optional_float(row.get("rel_benchmark_ret_20d"))
        if _is_missing(relative_ret):
            return None
        if relative_ret <= RELATIVE_STRONG_UNDERPERFORM_THRESHOLD:
            return CONTEXT_STOCK_20D_STRONGLY_UNDERPERFORMING_BENCHMARK
        return None
    if variant == S2ContextExperimentVariant.AVOID_MAPPED_SECTOR_NEGATIVE_20D:
        if _optional_bool(row.get("sector_proxy_unmapped")):
            return None
        if not row.get("sector_proxy"):
            return None
        sector_ret = _optional_float(row.get("sector_ret_20d"))
        if _is_missing(sector_ret):
            return CONTEXT_MAPPED_SECTOR_MISSING
        if sector_ret <= SECTOR_NEGATIVE_THRESHOLD:
            return CONTEXT_MAPPED_SECTOR_20D_NEGATIVE
        return None
    raise AssertionError(f"unhandled S2 context variant: {variant}")


def _missing_context_row(signal: Signal, reason: str) -> dict[str, object]:
    return {
        "signal": signal,
        "s2_context_missing_reason": reason,
        "benchmark_ret_20d": float("nan"),
        "rel_benchmark_ret_20d": float("nan"),
        "sector_proxy": None,
        "sector_proxy_unmapped": True,
        "sector_ret_20d": float("nan"),
    }


def _optional_float(value: object) -> float:
    if value is None:
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _optional_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if pd.isna(value):
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y"}


def _is_missing(value: float) -> bool:
    return pd.isna(value)
