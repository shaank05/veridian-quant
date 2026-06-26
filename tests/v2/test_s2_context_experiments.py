"""Tests for Phase 33G.1 S2 context experiment filters."""

from datetime import date
from types import MappingProxyType

import pytest

from veridian_quant.v2.data.models import Signal, SignalType
from veridian_quant.v2.experiments.s2_context_experiments import (
    CONTEXT_BENCHMARK_20D_STRONG_NEGATIVE,
    CONTEXT_MAPPED_SECTOR_20D_NEGATIVE,
    CONTEXT_MAPPED_SECTOR_MISSING,
    CONTEXT_STOCK_20D_STRONGLY_UNDERPERFORMING_BENCHMARK,
    CONTEXT_STOCK_NOT_OUTPERFORMING_BENCHMARK_20D,
    should_keep_s2_context_signal,
    validate_s2_context_experiment_variant,
)


def test_baseline_keeps_signal() -> None:
    decision = should_keep_s2_context_signal(_row(), "S2_BASELINE")

    assert decision.kept
    assert decision.rejection_reason is None
    assert decision.signal.metadata["s2_context_filter_decision"] == "kept"


def test_benchmark_strong_negative_boundary_rejects() -> None:
    decision = should_keep_s2_context_signal(
        _row(benchmark_ret_20d=-0.05),
        "S2_AVOID_BENCHMARK_20D_STRONG_NEGATIVE",
    )

    assert not decision.kept
    assert decision.rejection_reason == CONTEXT_BENCHMARK_20D_STRONG_NEGATIVE


def test_require_outperforming_rejects_zero_relative_return() -> None:
    decision = should_keep_s2_context_signal(
        _row(rel_benchmark_ret_20d=0.0),
        "S2_REQUIRE_STOCK_OUTPERFORMING_BENCHMARK_20D",
    )

    assert not decision.kept
    assert (
        decision.rejection_reason
        == CONTEXT_STOCK_NOT_OUTPERFORMING_BENCHMARK_20D
    )


def test_require_outperforming_keeps_positive_relative_return() -> None:
    decision = should_keep_s2_context_signal(
        _row(rel_benchmark_ret_20d=0.001),
        "S2_REQUIRE_STOCK_OUTPERFORMING_BENCHMARK_20D",
    )

    assert decision.kept


def test_strong_underperforming_boundary_rejects() -> None:
    decision = should_keep_s2_context_signal(
        _row(rel_benchmark_ret_20d=-0.05),
        "S2_AVOID_STOCK_STRONGLY_UNDERPERFORMING_BENCHMARK_20D",
    )

    assert not decision.kept
    assert (
        decision.rejection_reason
        == CONTEXT_STOCK_20D_STRONGLY_UNDERPERFORMING_BENCHMARK
    )


def test_unmapped_sector_remains_eligible_for_sector_negative_variant() -> None:
    decision = should_keep_s2_context_signal(
        _row(sector_proxy=None, sector_proxy_unmapped=True, sector_ret_20d=-0.2),
        "S2_AVOID_MAPPED_SECTOR_NEGATIVE_20D",
    )

    assert decision.kept


def test_mapped_sector_negative_boundary_rejects() -> None:
    decision = should_keep_s2_context_signal(
        _row(sector_proxy="NIFTY_IT", sector_proxy_unmapped=False, sector_ret_20d=0.0),
        "S2_AVOID_MAPPED_SECTOR_NEGATIVE_20D",
    )

    assert not decision.kept
    assert decision.rejection_reason == CONTEXT_MAPPED_SECTOR_20D_NEGATIVE


def test_mapped_sector_missing_rejects_with_separate_reason() -> None:
    decision = should_keep_s2_context_signal(
        _row(
            sector_proxy="NIFTY_IT",
            sector_proxy_unmapped=False,
            sector_ret_20d=float("nan"),
        ),
        "S2_AVOID_MAPPED_SECTOR_NEGATIVE_20D",
    )

    assert not decision.kept
    assert decision.rejection_reason == CONTEXT_MAPPED_SECTOR_MISSING


def test_unknown_variant_fails_clearly() -> None:
    with pytest.raises(ValueError, match="unknown S2 context experiment variant"):
        validate_s2_context_experiment_variant("S2_TUNED_GRID")


def test_context_row_must_include_signal() -> None:
    with pytest.raises(ValueError, match="must include a Signal"):
        should_keep_s2_context_signal({}, "S2_BASELINE")


def _row(**overrides: object) -> dict[str, object]:
    row = {
        "signal": _signal(),
        "benchmark": "NIFTY_500",
        "benchmark_ret_20d": 0.01,
        "rel_benchmark_ret_20d": 0.02,
        "sector": "Information Technology",
        "sector_proxy": "NIFTY_IT",
        "sector_proxy_unmapped": False,
        "sector_ret_20d": 0.03,
    }
    row.update(overrides)
    return row


def _signal() -> Signal:
    return Signal(
        symbol="AAA",
        signal_type=SignalType.LONG,
        generated_on=date(2026, 1, 2),
        strategy_name="S2_MARKOV_STATE_TRANSITION",
        reason="test",
        metadata=MappingProxyType({"state_label": "RET_UP|VOL_MID"}),
    )
