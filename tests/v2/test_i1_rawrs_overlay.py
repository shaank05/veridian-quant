"""Tests for the leakage-safe I1 RAWRS signal-time overlay."""

import numpy as np
import pandas as pd

from veridian_quant.v2.intelligence.rawrs_overlay import (
    DEFAULT_RAWRS_OVERLAY_FEATURE,
    RAWRS_OVERLAY_ALLOW,
    RAWRS_OVERLAY_ALLOW_INSUFFICIENT,
    RAWRS_OVERLAY_ALLOW_MISSING,
    RAWRS_OVERLAY_REJECT,
    RawrsOverlayConfig,
    build_rawrs_overlay_feature_frame,
    evaluate_rawrs_overlay,
)


def _features(values: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {DEFAULT_RAWRS_OVERLAY_FEATURE: values},
        index=pd.date_range("2026-01-01", periods=len(values)),
    )


def test_low_percentile_value_is_rejected() -> None:
    decision = evaluate_rawrs_overlay(
        _features([10.0, 9.0, 8.0, 7.0, 6.0]),
        pd.Timestamp("2026-01-05"),
        config=RawrsOverlayConfig(
            percentile_lookback=5,
            min_observations=5,
            avoid_percentile_lte=0.20,
        ),
    )
    assert decision.decision == RAWRS_OVERLAY_REJECT
    assert decision.feature_percentile == 0.20


def test_value_above_threshold_is_allowed() -> None:
    decision = evaluate_rawrs_overlay(
        _features([1.0, 2.0, 3.0, 4.0, 5.0]),
        pd.Timestamp("2026-01-05"),
        config=RawrsOverlayConfig(percentile_lookback=5, min_observations=5),
    )
    assert decision.decision == RAWRS_OVERLAY_ALLOW
    assert decision.feature_percentile == 1.0


def test_insufficient_observations_allow_signal() -> None:
    decision = evaluate_rawrs_overlay(
        _features([1.0, 2.0, 3.0]),
        pd.Timestamp("2026-01-03"),
        config=RawrsOverlayConfig(percentile_lookback=10, min_observations=5),
    )
    assert decision.decision == RAWRS_OVERLAY_ALLOW_INSUFFICIENT
    assert decision.observation_count == 3
    assert decision.feature_percentile is None


def test_missing_signal_time_feature_value_allows_signal() -> None:
    decision = evaluate_rawrs_overlay(
        _features([1.0, 2.0, np.nan]),
        pd.Timestamp("2026-01-03"),
        config=RawrsOverlayConfig(percentile_lookback=3, min_observations=2),
    )
    assert decision.decision == RAWRS_OVERLAY_ALLOW_MISSING
    assert decision.feature_value is None


def test_future_feature_changes_do_not_change_earlier_decision() -> None:
    original = _features([5.0, 4.0, 3.0, 2.0, 1.0, 100.0, 200.0])
    changed = original.copy(deep=True)
    changed.iloc[5:, 0] = [-1000.0, -2000.0]
    config = RawrsOverlayConfig(percentile_lookback=5, min_observations=5)
    first = evaluate_rawrs_overlay(original, pd.Timestamp("2026-01-05"), config=config)
    second = evaluate_rawrs_overlay(changed, pd.Timestamp("2026-01-05"), config=config)
    assert first == second
    assert first.decision == RAWRS_OVERLAY_REJECT


def test_future_ohlcv_changes_do_not_change_earlier_decision() -> None:
    dates = pd.date_range("2025-01-01", periods=100)
    data = pd.DataFrame({"date": dates, "close": np.arange(100.0, 200.0)})
    changed = data.copy(deep=True)
    changed.loc[changed.index > 79, "close"] = np.arange(1000.0, 1020.0)
    config = RawrsOverlayConfig(percentile_lookback=10, min_observations=5)
    first = evaluate_rawrs_overlay(
        build_rawrs_overlay_feature_frame(data), dates[79], config=config
    )
    second = evaluate_rawrs_overlay(
        build_rawrs_overlay_feature_frame(changed), dates[79], config=config
    )
    assert first == second


def test_feature_builder_does_not_mutate_input() -> None:
    data = pd.DataFrame(
        {"date": pd.date_range("2026-01-01", periods=70), "close": range(70)}
    )
    before = data.copy(deep=True)
    build_rawrs_overlay_feature_frame(data)
    pd.testing.assert_frame_equal(data, before)
