"""Leakage-safe signal-time RAWRS overlay utilities.

The overlay evaluates one symbol's feature history only through the candidate
signal timestamp. It never derives thresholds from completed trades or a full
backtest-period distribution.
"""

from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

from veridian_quant.v2.intelligence.rawrs import (
    log_returns,
    rawrs_feature_frame,
    rolling_fft_spectral_concentration,
)


DEFAULT_RAWRS_OVERLAY_FEATURE = "rawrs_fft_spectral_concentration"
RAWRS_OVERLAY_ALLOW = "ALLOW"
RAWRS_OVERLAY_ALLOW_INSUFFICIENT = "ALLOW_INSUFFICIENT_OBSERVATIONS"
RAWRS_OVERLAY_ALLOW_MISSING = "ALLOW_MISSING_FEATURE_VALUE"
RAWRS_OVERLAY_REJECT = "REJECT"


@dataclass(frozen=True, slots=True)
class RawrsOverlayConfig:
    """Validated configuration for the optional S3 RAWRS experiment."""

    feature: str = DEFAULT_RAWRS_OVERLAY_FEATURE
    avoid_percentile_lte: float = 0.20
    percentile_lookback: int = 252
    min_observations: int = 126

    def __post_init__(self) -> None:
        if not self.feature.startswith("rawrs_"):
            raise ValueError("RAWRS overlay feature must start with 'rawrs_'")
        if not 0.0 <= self.avoid_percentile_lte <= 1.0:
            raise ValueError("RAWRS avoid percentile must be between 0 and 1")
        if self.percentile_lookback < 1:
            raise ValueError("RAWRS percentile lookback must be positive")
        if self.min_observations < 1:
            raise ValueError("RAWRS minimum observations must be positive")
        if self.min_observations > self.percentile_lookback:
            raise ValueError(
                "RAWRS minimum observations cannot exceed percentile lookback"
            )


@dataclass(frozen=True, slots=True)
class RawrsOverlayDecision:
    """One causal signal-time RAWRS overlay decision."""

    decision: str
    feature: str
    feature_value: float | None
    feature_percentile: float | None
    observation_count: int
    signal_timestamp: pd.Timestamp

    @property
    def rejected(self) -> bool:
        return self.decision == RAWRS_OVERLAY_REJECT


def build_rawrs_overlay_feature_frame(
    data: pd.DataFrame,
    *,
    feature: str = DEFAULT_RAWRS_OVERLAY_FEATURE,
) -> pd.DataFrame:
    """Compute RAWRS features on a chronological, timestamp-indexed OHLCV copy."""

    timestamp_col = "date" if "date" in data.columns else "timestamp"
    if timestamp_col not in data.columns:
        raise ValueError("RAWRS overlay requires a date or timestamp column")
    feature_input = data.copy(deep=True)
    feature_input[timestamp_col] = pd.to_datetime(
        feature_input[timestamp_col], errors="coerce", utc=True
    ).dt.tz_localize(None)
    feature_input = feature_input.loc[feature_input[timestamp_col].notna()]
    feature_input = feature_input.sort_values(timestamp_col, kind="mergesort")
    feature_input = feature_input.set_index(timestamp_col)
    if feature == DEFAULT_RAWRS_OVERLAY_FEATURE:
        returns = log_returns(feature_input)
        return pd.DataFrame(
            {feature: rolling_fft_spectral_concentration(returns, window=64)},
            index=feature_input.index,
        )
    features = rawrs_feature_frame(feature_input)
    if feature not in features.columns:
        raise ValueError(f"missing RAWRS overlay feature: {feature}")
    return features.loc[:, [feature]]


def evaluate_rawrs_overlay(
    feature_frame: pd.DataFrame,
    signal_timestamp: date | datetime | pd.Timestamp,
    *,
    config: RawrsOverlayConfig | None = None,
) -> RawrsOverlayDecision:
    """Evaluate a candidate using only feature rows at or before its timestamp."""

    selected = config or RawrsOverlayConfig()
    if selected.feature not in feature_frame.columns:
        raise ValueError(f"missing RAWRS overlay feature: {selected.feature}")

    timestamp = _normalize_timestamp(signal_timestamp)
    features = feature_frame.loc[:, [selected.feature]].copy(deep=True)
    features.index = _normalize_index(features.index)
    features = features.loc[features.index.notna()].sort_index(kind="mergesort")

    # This slice is the critical leakage guard. No later feature observation is
    # eligible for either the current value or its trailing percentile.
    causal = features.loc[features.index <= timestamp]
    if causal.empty:
        return _allow_missing(selected.feature, timestamp, 0)

    current = pd.to_numeric(causal[selected.feature].iloc[-1:], errors="coerce")
    window = pd.to_numeric(
        causal[selected.feature].tail(selected.percentile_lookback),
        errors="coerce",
    ).dropna()
    observation_count = int(len(window))
    if current.empty or pd.isna(current.iloc[0]):
        return _allow_missing(selected.feature, timestamp, observation_count)

    feature_value = float(current.iloc[0])
    if observation_count < selected.min_observations:
        return RawrsOverlayDecision(
            decision=RAWRS_OVERLAY_ALLOW_INSUFFICIENT,
            feature=selected.feature,
            feature_value=feature_value,
            feature_percentile=None,
            observation_count=observation_count,
            signal_timestamp=timestamp,
        )

    less = int((window < feature_value).sum())
    equal = int((window == feature_value).sum())
    percentile = (less + ((equal + 1) / 2.0)) / observation_count
    decision = (
        RAWRS_OVERLAY_REJECT
        if percentile <= selected.avoid_percentile_lte
        else RAWRS_OVERLAY_ALLOW
    )
    return RawrsOverlayDecision(
        decision=decision,
        feature=selected.feature,
        feature_value=feature_value,
        feature_percentile=float(percentile),
        observation_count=observation_count,
        signal_timestamp=timestamp,
    )


def rawrs_overlay_metadata(
    decision: RawrsOverlayDecision,
    config: RawrsOverlayConfig,
) -> dict[str, object]:
    """Return passive signal metadata describing one overlay evaluation."""

    return {
        "rawrs_overlay_enabled": True,
        "rawrs_feature": decision.feature,
        "rawrs_feature_value": decision.feature_value,
        "rawrs_feature_percentile": decision.feature_percentile,
        "rawrs_feature_observation_count": decision.observation_count,
        "rawrs_avoid_percentile_lte": config.avoid_percentile_lte,
        "rawrs_percentile_lookback": config.percentile_lookback,
        "rawrs_min_observations": config.min_observations,
        "rawrs_overlay_decision": decision.decision,
    }


def _allow_missing(
    feature: str,
    timestamp: pd.Timestamp,
    observation_count: int,
) -> RawrsOverlayDecision:
    return RawrsOverlayDecision(
        decision=RAWRS_OVERLAY_ALLOW_MISSING,
        feature=feature,
        feature_value=None,
        feature_percentile=None,
        observation_count=observation_count,
        signal_timestamp=timestamp,
    )


def _normalize_timestamp(value: date | datetime | pd.Timestamp) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert("UTC").tz_localize(None)
    return timestamp


def _normalize_index(index: pd.Index) -> pd.DatetimeIndex:
    normalized = pd.to_datetime(index, errors="coerce", utc=True)
    return pd.DatetimeIndex(normalized).tz_localize(None)
