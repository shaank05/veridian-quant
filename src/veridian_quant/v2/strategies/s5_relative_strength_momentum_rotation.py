"""S5 relative-strength / momentum-rotation candidate signal generation.

This module implements the Phase 32C signal layer only. It calculates one
symbol's leakage-safe momentum features and emits LONG candidate signals with a
serializable ``rank_score``. It does not rank across symbols, size positions,
enforce portfolio capacity, simulate entries, run backtests, or combine S5 with
another strategy or intelligence layer.
"""

from dataclasses import dataclass, field
from datetime import date
from types import MappingProxyType

import numpy as np
import pandas as pd

from veridian_quant.v2.data.models import Signal, SignalType
from veridian_quant.v2.features.momentum import (
    period_return,
    rolling_realized_volatility,
    sma_distance,
    volatility_adjusted_momentum,
)


STRATEGY_NAME = "S5_RELATIVE_STRENGTH_MOMENTUM_ROTATION"
S5_SIMPLE_RS_126D_V1 = "S5_SIMPLE_RS_126D_V1"
S5_DUAL_MOMENTUM_63_126D_V1 = "S5_DUAL_MOMENTUM_63_126D_V1"
S5_VOL_ADJUSTED_RS_V1 = "S5_VOL_ADJUSTED_RS_V1"
S5_STRATEGY_VARIANTS = (
    S5_SIMPLE_RS_126D_V1,
    S5_DUAL_MOMENTUM_63_126D_V1,
    S5_VOL_ADJUSTED_RS_V1,
)

RETURN_SHORT_WINDOW = 63
RETURN_MEDIUM_WINDOW = 126
VOLATILITY_WINDOW = 63
TREND_WINDOW = 200
DUAL_MOMENTUM_SHORT_WEIGHT = 0.5
DUAL_MOMENTUM_MEDIUM_WEIGHT = 0.5


@dataclass(frozen=True, slots=True)
class S5MomentumConfig:
    """Configuration for standalone S5 candidate signal generation."""

    variant: str = S5_SIMPLE_RS_126D_V1
    enable_trend_filter: bool = True
    min_rank_score: float | None = None
    allow_repeated_signals: bool = False
    price_col: str = "close"


@dataclass(frozen=True, slots=True)
class S5RelativeStrengthMomentumRotationStrategy:
    """Pure single-symbol S5 momentum candidate signal generator."""

    config: S5MomentumConfig = field(default_factory=S5MomentumConfig)
    strategy_name: str = STRATEGY_NAME

    @property
    def name(self) -> str:
        """Return the stable S5 strategy-family identifier."""

        return self.strategy_name

    def generate_signals(self, symbol: str, data: pd.DataFrame) -> tuple[Signal, ...]:
        """Generate deterministic LONG candidates for one symbol.

        Consecutive qualifying rows emit only the first signal by default. A new
        signal becomes eligible after the qualification condition resets, or on
        every qualifying row when ``allow_repeated_signals`` is true.
        """

        _validate_input(data, price_col=self.config.price_col)
        validate_s5_strategy_variant(self.config.variant)
        _validate_config(self.config)

        working = _chronological_copy(data)
        features = build_s5_momentum_feature_frame(
            working,
            price_col=self.config.price_col,
        )
        rank_score = _rank_score(features, self.config.variant)
        qualifies = _qualification_mask(features, rank_score, self.config)

        if not self.config.allow_repeated_signals:
            qualifies = qualifies & ~qualifies.shift(1, fill_value=False)

        signals: list[Signal] = []
        for index in features.index[qualifies.fillna(False)]:
            row = working.loc[index]
            feature_row = features.loc[index]
            score = float(rank_score.loc[index])
            signals.append(
                Signal(
                    symbol=symbol,
                    signal_type=SignalType.LONG,
                    generated_on=_row_date(row),
                    strategy_name=self.strategy_name,
                    reason=_signal_reason(self.config.variant),
                    metadata=MappingProxyType(
                        _metadata(feature_row, score, self.config)
                    ),
                )
            )
        return tuple(signals)


def generate_s5_momentum_signals(
    symbol: str,
    data: pd.DataFrame,
    config: S5MomentumConfig | None = None,
) -> tuple[Signal, ...]:
    """Generate S5 candidates with the supplied or default configuration."""

    strategy = S5RelativeStrengthMomentumRotationStrategy(
        config=config or S5MomentumConfig()
    )
    return strategy.generate_signals(symbol=symbol, data=data)


def build_s5_momentum_feature_frame(
    data: pd.DataFrame,
    price_col: str = "close",
) -> pd.DataFrame:
    """Return the fixed signal-date features required by Phase 32C variants."""

    _validate_input(data, price_col=price_col)
    return pd.DataFrame(
        {
            "close": data[price_col],
            "return_63d": period_return(data, RETURN_SHORT_WINDOW, price_col),
            "return_126d": period_return(data, RETURN_MEDIUM_WINDOW, price_col),
            "realized_vol_63d": rolling_realized_volatility(
                data,
                VOLATILITY_WINDOW,
                price_col,
            ),
            "vol_adj_return_126d_63d": volatility_adjusted_momentum(
                data,
                RETURN_MEDIUM_WINDOW,
                VOLATILITY_WINDOW,
                price_col,
            ),
            "sma_distance_200d": sma_distance(data, TREND_WINDOW, price_col),
        },
        index=data.index,
    )


def validate_s5_strategy_variant(variant: str) -> str:
    """Return a supported S5 variant or raise a clear ValueError."""

    if variant not in S5_STRATEGY_VARIANTS:
        allowed = ", ".join(S5_STRATEGY_VARIANTS)
        raise ValueError(
            f"unknown S5 strategy variant {variant!r}; expected one of: {allowed}"
        )
    return variant


def _rank_score(features: pd.DataFrame, variant: str) -> pd.Series:
    """Return the declared per-row rank score for ``variant``."""

    if variant == S5_SIMPLE_RS_126D_V1:
        return features["return_126d"].rename("rank_score")
    if variant == S5_DUAL_MOMENTUM_63_126D_V1:
        return (
            DUAL_MOMENTUM_SHORT_WEIGHT * features["return_63d"]
            + DUAL_MOMENTUM_MEDIUM_WEIGHT * features["return_126d"]
        ).rename("rank_score")
    return features["vol_adj_return_126d_63d"].rename("rank_score")


def _qualification_mask(
    features: pd.DataFrame,
    rank_score: pd.Series,
    config: S5MomentumConfig,
) -> pd.Series:
    """Return rows satisfying the selected variant's candidate rules."""

    if config.variant == S5_SIMPLE_RS_126D_V1:
        qualifies = _finite(features["return_126d"])
    elif config.variant == S5_DUAL_MOMENTUM_63_126D_V1:
        # Phase 32C uses the transparent rule that both horizons must be
        # strictly positive; rank score alone cannot rescue a negative horizon.
        qualifies = (
            _finite(features["return_63d"])
            & _finite(features["return_126d"])
            & (features["return_63d"] > 0.0)
            & (features["return_126d"] > 0.0)
        )
    else:
        qualifies = (
            _finite(features["return_126d"])
            & _finite(features["realized_vol_63d"])
            & (features["realized_vol_63d"] > 0.0)
            & _finite(features["vol_adj_return_126d_63d"])
        )

    qualifies = qualifies & _finite(rank_score)
    if config.enable_trend_filter:
        qualifies = qualifies & (features["sma_distance_200d"] > 0.0)
    if config.min_rank_score is not None:
        qualifies = qualifies & (rank_score >= config.min_rank_score)
    return qualifies.fillna(False)


def _metadata(
    features: pd.Series,
    rank_score: float,
    config: S5MomentumConfig,
) -> dict[str, object]:
    """Return deterministic, primitive-valued metadata for one candidate."""

    actual_trend_passed = bool(
        pd.notna(features["sma_distance_200d"])
        and features["sma_distance_200d"] > 0.0
    )
    configured_trend_passed = not config.enable_trend_filter or actual_trend_passed
    return {
        "strategy_family": STRATEGY_NAME,
        "strategy_variant": config.variant,
        "s5_variant": config.variant,
        "variant": config.variant,
        "close": _blank_nan(features["close"]),
        "return_63d": _blank_nan(features["return_63d"]),
        "return_126d": _blank_nan(features["return_126d"]),
        "realized_vol_63d": _blank_nan(features["realized_vol_63d"]),
        "vol_adj_return_126d_63d": _blank_nan(
            features["vol_adj_return_126d_63d"]
        ),
        "sma_distance_200d": _blank_nan(features["sma_distance_200d"]),
        "rank_score": rank_score,
        "trend_filter_enabled": config.enable_trend_filter,
        "trend_filter_passed": configured_trend_passed,
        "price_above_sma200": actual_trend_passed,
        "min_rank_score": config.min_rank_score,
        "dual_momentum_rule": "both_returns_positive",
        "return_short_window": RETURN_SHORT_WINDOW,
        "return_medium_window": RETURN_MEDIUM_WINDOW,
        "volatility_window": VOLATILITY_WINDOW,
        "trend_window": TREND_WINDOW,
    }


def _signal_reason(variant: str) -> str:
    reasons = {
        S5_SIMPLE_RS_126D_V1: "S5 126-day relative-strength candidate",
        S5_DUAL_MOMENTUM_63_126D_V1: (
            "S5 positive 63-day and 126-day dual-momentum candidate"
        ),
        S5_VOL_ADJUSTED_RS_V1: (
            "S5 volatility-adjusted momentum candidate"
        ),
    }
    return reasons[variant]


def _chronological_copy(data: pd.DataFrame) -> pd.DataFrame:
    """Return a stable chronological copy without mutating the caller."""

    date_column = "date" if "date" in data.columns else "timestamp"
    return (
        data.copy(deep=True)
        .assign(_s5_sort_date=pd.to_datetime(data[date_column]))
        .sort_values("_s5_sort_date", kind="mergesort")
        .drop(columns="_s5_sort_date")
        .reset_index(drop=True)
    )


def _validate_input(data: pd.DataFrame, price_col: str) -> None:
    required = [price_col]
    missing = [column for column in required if column not in data.columns]
    if "date" not in data.columns and "timestamp" not in data.columns:
        missing.append("date or timestamp")
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")


def _validate_config(config: S5MomentumConfig) -> None:
    if config.min_rank_score is not None and not np.isfinite(config.min_rank_score):
        raise ValueError("min_rank_score must be finite when provided")
    if not isinstance(config.price_col, str) or not config.price_col:
        raise ValueError("price_col must be a non-empty string")


def _finite(values: pd.Series) -> pd.Series:
    return pd.Series(np.isfinite(values), index=values.index)


def _row_date(row: pd.Series) -> date:
    value = row["date"] if "date" in row.index else row["timestamp"]
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()


def _blank_nan(value: object) -> object:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value
