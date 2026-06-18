"""S4 entropy / volatility compression breakout signal generation.

This module implements the S4 signal layer only. It identifies long breakout
candidates after prior volatility, range, or entropy/noise compression. It does
not enter trades, size positions, run backtests, rank candidates, or combine S4
with S1/S2/S3 logic.
"""

from dataclasses import dataclass
from datetime import date
from types import MappingProxyType

import pandas as pd

from veridian_quant.v2.data.models import Signal, SignalType
from veridian_quant.v2.features.compression import (
    atr_percentage,
    atr_percentile,
    close_above_prior_high,
    prior_n_day_high,
    range_percentile,
    return_sign_entropy,
    rolling_range_percentage,
)


STRATEGY_NAME = "S4_ENTROPY_VOLATILITY_COMPRESSION_BREAKOUT"
S4_ATR_COMPRESSION_BREAKOUT_V1 = "S4_ATR_COMPRESSION_BREAKOUT_V1"
S4_RANGE_COMPRESSION_BREAKOUT_V1 = "S4_RANGE_COMPRESSION_BREAKOUT_V1"
S4_ENTROPY_GATED_BREAKOUT_V1 = "S4_ENTROPY_GATED_BREAKOUT_V1"
S4_STRATEGY_VARIANTS = (
    S4_ATR_COMPRESSION_BREAKOUT_V1,
    S4_RANGE_COMPRESSION_BREAKOUT_V1,
    S4_ENTROPY_GATED_BREAKOUT_V1,
)


@dataclass(frozen=True, slots=True)
class S4EntropyVolatilityCompressionBreakoutStrategy:
    """Pure S4 signal generator for prior compression plus breakout close."""

    variant: str = S4_ATR_COMPRESSION_BREAKOUT_V1
    atr_window: int = 14
    range_window: int = 20
    breakout_window: int = 20
    percentile_window: int = 100
    entropy_window: int = 20
    compression_threshold: float = 0.20
    entropy_threshold: float = 0.70
    flat_threshold: float = 0.0
    allow_repeated_signals: bool = False
    strategy_name: str = STRATEGY_NAME

    @property
    def name(self) -> str:
        """Return the stable S4 strategy identifier."""

        return self.strategy_name

    def generate_signals(self, symbol: str, data: pd.DataFrame) -> tuple[Signal, ...]:
        """Generate S4 LONG signals from one symbol's OHLC dataframe."""

        _validate_input(data)
        validate_s4_strategy_variant(self.variant)

        working = _chronological_copy(data)
        feature_frame = build_s4_feature_frame(
            working,
            atr_window=self.atr_window,
            range_window=self.range_window,
            breakout_window=self.breakout_window,
            percentile_window=self.percentile_window,
            entropy_window=self.entropy_window,
            flat_threshold=self.flat_threshold,
        )
        qualifies = self._qualification_mask(feature_frame)

        if not self.allow_repeated_signals:
            qualifies = qualifies & ~qualifies.shift(1, fill_value=False)

        signals: list[Signal] = []
        for index in feature_frame.index[qualifies.fillna(False)]:
            row = working.loc[index]
            features = feature_frame.loc[index]
            signals.append(
                Signal(
                    symbol=symbol,
                    signal_type=SignalType.LONG,
                    generated_on=_row_date(row),
                    strategy_name=self.strategy_name,
                    reason="S4 compression breakout setup",
                    metadata=MappingProxyType(self._metadata(features)),
                )
            )
        return tuple(signals)

    def _qualification_mask(self, features: pd.DataFrame) -> pd.Series:
        """Return rows where the selected S4 variant qualifies."""

        breakout = features["close_above_prior_high"]
        atr_compressed = features["prior_atr_percentile"] <= self.compression_threshold
        range_compressed = (
            features["prior_range_percentile"] <= self.compression_threshold
        )

        if self.variant == S4_ATR_COMPRESSION_BREAKOUT_V1:
            qualifies = atr_compressed & breakout
        elif self.variant == S4_RANGE_COMPRESSION_BREAKOUT_V1:
            qualifies = range_compressed & breakout
        else:
            entropy_compressed = (
                features["prior_return_sign_entropy"] <= self.entropy_threshold
            )
            qualifies = (
                (atr_compressed | range_compressed)
                & entropy_compressed
                & breakout
            )
        return qualifies.fillna(False)

    def _metadata(self, features: pd.Series) -> dict[str, object]:
        """Return audit metadata for an S4 signal row."""

        return {
            "strategy_family": STRATEGY_NAME,
            "strategy_variant": self.variant,
            "s4_variant": self.variant,
            "variant": self.variant,
            "close": _blank_nan(features["close"]),
            "prior_high": _blank_nan(features["prior_high"]),
            "atr_pct": _blank_nan(features["atr_pct"]),
            "atr_percentile": _blank_nan(features["atr_percentile"]),
            "prior_atr_percentile": _blank_nan(features["prior_atr_percentile"]),
            "range_pct": _blank_nan(features["range_pct"]),
            "range_percentile": _blank_nan(features["range_percentile"]),
            "prior_range_percentile": _blank_nan(
                features["prior_range_percentile"]
            ),
            "return_sign_entropy": _blank_nan(features["return_sign_entropy"]),
            "prior_return_sign_entropy": _blank_nan(
                features["prior_return_sign_entropy"]
            ),
            "compression_threshold": self.compression_threshold,
            "entropy_threshold": self.entropy_threshold,
            "breakout_window": self.breakout_window,
            "atr_window": self.atr_window,
            "range_window": self.range_window,
            "percentile_window": self.percentile_window,
            "entropy_window": self.entropy_window,
            "flat_threshold": self.flat_threshold,
        }


def generate_s4_entropy_volatility_compression_breakout_signals(
    symbol: str,
    data: pd.DataFrame,
    variant: str = S4_ATR_COMPRESSION_BREAKOUT_V1,
    atr_window: int = 14,
    range_window: int = 20,
    breakout_window: int = 20,
    percentile_window: int = 100,
    entropy_window: int = 20,
    compression_threshold: float = 0.20,
    entropy_threshold: float = 0.70,
    flat_threshold: float = 0.0,
    allow_repeated_signals: bool = False,
) -> tuple[Signal, ...]:
    """Generate S4 signals using the default strategy class."""

    strategy = S4EntropyVolatilityCompressionBreakoutStrategy(
        variant=variant,
        atr_window=atr_window,
        range_window=range_window,
        breakout_window=breakout_window,
        percentile_window=percentile_window,
        entropy_window=entropy_window,
        compression_threshold=compression_threshold,
        entropy_threshold=entropy_threshold,
        flat_threshold=flat_threshold,
        allow_repeated_signals=allow_repeated_signals,
    )
    return strategy.generate_signals(symbol=symbol, data=data)


def build_s4_feature_frame(
    data: pd.DataFrame,
    atr_window: int = 14,
    range_window: int = 20,
    breakout_window: int = 20,
    percentile_window: int = 100,
    entropy_window: int = 20,
    flat_threshold: float = 0.0,
) -> pd.DataFrame:
    """Return deterministic S4 signal-date features for each row."""

    _validate_input(data)
    atr_pct = atr_percentage(data, atr_window=atr_window)
    atr_rank = atr_percentile(
        data,
        atr_window=atr_window,
        percentile_window=percentile_window,
    )
    range_pct = rolling_range_percentage(data, window=range_window)
    range_rank = range_percentile(
        data,
        range_window=range_window,
        percentile_window=percentile_window,
    )
    prior_high = prior_n_day_high(data, window=breakout_window)
    breakout = close_above_prior_high(data, window=breakout_window)
    entropy = return_sign_entropy(
        data,
        window=entropy_window,
        flat_threshold=flat_threshold,
    )

    return pd.DataFrame(
        {
            "close": data["close"],
            "prior_high": prior_high,
            "close_above_prior_high": breakout,
            "atr_pct": atr_pct,
            "atr_percentile": atr_rank,
            "prior_atr_percentile": atr_rank.shift(1),
            "range_pct": range_pct,
            "range_percentile": range_rank,
            "prior_range_percentile": range_rank.shift(1),
            "return_sign_entropy": entropy,
            "prior_return_sign_entropy": entropy.shift(1),
        },
        index=data.index,
    )


def validate_s4_strategy_variant(variant: str) -> str:
    """Return a valid S4 strategy variant or raise a clear ValueError."""

    if variant not in S4_STRATEGY_VARIANTS:
        allowed = ", ".join(S4_STRATEGY_VARIANTS)
        raise ValueError(
            f"unknown S4 strategy variant {variant!r}; expected one of: {allowed}"
        )
    return variant


def _chronological_copy(data: pd.DataFrame) -> pd.DataFrame:
    date_column = "date" if "date" in data.columns else "timestamp"
    return (
        data.copy(deep=True)
        .assign(_s4_sort_date=pd.to_datetime(data[date_column]))
        .sort_values("_s4_sort_date", kind="mergesort")
        .drop(columns="_s4_sort_date")
        .reset_index(drop=True)
    )


def _validate_input(data: pd.DataFrame) -> None:
    required = ["high", "low", "close"]
    missing = [column for column in required if column not in data.columns]
    if "date" not in data.columns and "timestamp" not in data.columns:
        missing.append("date or timestamp")
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")


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
