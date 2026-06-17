"""S3 trend pullback continuation signal generation for Veridian Quant v2.

This module implements the S3 signal layer only. It identifies controlled
pullbacks inside confirmed uptrends and emits LONG signal candidates. It does
not enter trades, size positions, resolve exits, run backtests, or combine S3
with S1/S2.
"""

from dataclasses import dataclass
from datetime import date
from types import MappingProxyType

import pandas as pd

from veridian_quant.v2.data.models import Signal, SignalType
from veridian_quant.v2.features.technical import atr


STRATEGY_NAME = "S3_TREND_PULLBACK_CONTINUATION"
S3_BASELINE = "S3_TREND_PULLBACK_CONTINUATION_BASELINE"
S3_STRONG_TREND_V1 = "S3_STRONG_TREND_V1"
S3_ABOVE_SMA50_V1 = "S3_ABOVE_SMA50_V1"
S3_STRONG_TREND_ABOVE_SMA50_V1 = "S3_STRONG_TREND_ABOVE_SMA50_V1"
S3_STRATEGY_VARIANTS = (
    S3_BASELINE,
    S3_STRONG_TREND_V1,
    S3_ABOVE_SMA50_V1,
    S3_STRONG_TREND_ABOVE_SMA50_V1,
)
S3_STRONG_TREND_MIN_SMA200_SLOPE_20D_PCT = 1.0


@dataclass(frozen=True, slots=True)
class S3TrendPullbackContinuationStrategy:
    """Baseline S3 signal generator for uptrend pullback continuation."""

    sma_fast_window: int = 50
    sma_slow_window: int = 200
    sma_slope_lookback: int = 20
    pullback_lookback: int = 5
    min_pullback_return_pct: float = -10.0
    max_pullback_return_pct: float = -1.0
    max_drawdown_20d_pct: float = -3.0
    min_drawdown_20d_pct: float = -15.0
    atr_window: int = 14
    max_atr_pct: float = 8.0
    max_atr_expansion_5d_pct: float = 50.0
    fresh_low_window: int = 60
    allow_repeated_signals: bool = False
    require_recovery_day: bool = True
    strategy_variant: str = S3_BASELINE
    strategy_name: str = STRATEGY_NAME

    @property
    def name(self) -> str:
        """Return the stable S3 strategy identifier."""

        return self.strategy_name

    def generate_signals(self, symbol: str, data: pd.DataFrame) -> tuple[Signal, ...]:
        """Generate S3 LONG signals from one symbol's OHLC dataframe."""

        _validate_input(data)
        self._validate_parameters()
        validate_s3_strategy_variant(self.strategy_variant)

        working = _chronological_copy(data)
        feature_frame = build_s3_feature_frame(
            working,
            sma_fast_window=self.sma_fast_window,
            sma_slow_window=self.sma_slow_window,
            sma_slope_lookback=self.sma_slope_lookback,
            pullback_lookback=self.pullback_lookback,
            atr_window=self.atr_window,
            fresh_low_window=self.fresh_low_window,
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
                    reason="S3 trend pullback continuation setup",
                    metadata=MappingProxyType(self._metadata(features)),
                )
            )
        return tuple(signals)

    def _qualification_mask(self, features: pd.DataFrame) -> pd.Series:
        recovery_day = features["close"] > features["previous_close"]
        if not self.require_recovery_day:
            recovery_day = pd.Series(True, index=features.index)

        qualifies = (
            (features["close"] > features["sma200"])
            & (features["sma200_slope_20d_pct"] > 0)
            & (features["sma50_slope_20d_pct"] > 0)
            & (
                features["return_5d_pct"].between(
                    self.min_pullback_return_pct,
                    self.max_pullback_return_pct,
                    inclusive="both",
                )
            )
            & (
                features["drawdown_20d_pct"].between(
                    self.min_drawdown_20d_pct,
                    self.max_drawdown_20d_pct,
                    inclusive="both",
                )
            )
            & ~features["is_60d_low"]
            & (features["atr14_pct"] <= self.max_atr_pct)
            & (features["atr14_change_5d_pct"] <= self.max_atr_expansion_5d_pct)
            & recovery_day
        )
        if _variant_requires_strong_trend(self.strategy_variant):
            qualifies = qualifies & (
                features["sma200_slope_20d_pct"]
                > S3_STRONG_TREND_MIN_SMA200_SLOPE_20D_PCT
            )
        if _variant_requires_above_sma50(self.strategy_variant):
            qualifies = qualifies & (features["close_vs_sma50_pct"] >= 0)
        return qualifies

    def _metadata(self, features: pd.Series) -> dict[str, object]:
        requires_strong_trend = _variant_requires_strong_trend(self.strategy_variant)
        requires_above_sma50 = _variant_requires_above_sma50(self.strategy_variant)
        return {
            "strategy_family": STRATEGY_NAME,
            "strategy_variant": self.strategy_variant,
            "s3_variant": self.strategy_variant,
            "s3_requires_strong_trend": requires_strong_trend,
            "s3_requires_above_sma50": requires_above_sma50,
            "s3_strong_trend_min_sma200_slope_20d_pct": (
                S3_STRONG_TREND_MIN_SMA200_SLOPE_20D_PCT
                if requires_strong_trend
                else None
            ),
            "close": _blank_nan(features["close"]),
            "sma50": _blank_nan(features["sma50"]),
            "sma200": _blank_nan(features["sma200"]),
            "close_vs_sma50_pct": _blank_nan(features["close_vs_sma50_pct"]),
            "close_vs_sma200_pct": _blank_nan(features["close_vs_sma200_pct"]),
            "sma50_slope_20d_pct": _blank_nan(features["sma50_slope_20d_pct"]),
            "sma200_slope_20d_pct": _blank_nan(features["sma200_slope_20d_pct"]),
            "return_3d_pct": _blank_nan(features["return_3d_pct"]),
            "return_5d_pct": _blank_nan(features["return_5d_pct"]),
            "return_10d_pct": _blank_nan(features["return_10d_pct"]),
            "drawdown_20d_pct": _blank_nan(features["drawdown_20d_pct"]),
            "drawdown_60d_pct": _blank_nan(features["drawdown_60d_pct"]),
            "close_vs_20d_high_pct": _blank_nan(
                features["close_vs_20d_high_pct"]
            ),
            "close_vs_60d_low_pct": _blank_nan(features["close_vs_60d_low_pct"]),
            "is_60d_low": bool(features["is_60d_low"]),
            "atr14_pct": _blank_nan(features["atr14_pct"]),
            "atr14_change_5d_pct": _blank_nan(features["atr14_change_5d_pct"]),
            "pullback_lookback": self.pullback_lookback,
            "sma_fast_window": self.sma_fast_window,
            "sma_slow_window": self.sma_slow_window,
            "sma_slope_lookback": self.sma_slope_lookback,
            "min_pullback_return_pct": self.min_pullback_return_pct,
            "max_pullback_return_pct": self.max_pullback_return_pct,
            "min_drawdown_20d_pct": self.min_drawdown_20d_pct,
            "max_drawdown_20d_pct": self.max_drawdown_20d_pct,
            "max_atr_pct": self.max_atr_pct,
            "max_atr_expansion_5d_pct": self.max_atr_expansion_5d_pct,
            "require_recovery_day": self.require_recovery_day,
        }

    def _validate_parameters(self) -> None:
        for name in (
            "sma_fast_window",
            "sma_slow_window",
            "sma_slope_lookback",
            "pullback_lookback",
            "atr_window",
            "fresh_low_window",
        ):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be positive")


def generate_s3_trend_pullback_signals(
    symbol: str,
    data: pd.DataFrame,
    sma_fast_window: int = 50,
    sma_slow_window: int = 200,
    sma_slope_lookback: int = 20,
    pullback_lookback: int = 5,
    min_pullback_return_pct: float = -10.0,
    max_pullback_return_pct: float = -1.0,
    max_drawdown_20d_pct: float = -3.0,
    min_drawdown_20d_pct: float = -15.0,
    atr_window: int = 14,
    max_atr_pct: float = 8.0,
    max_atr_expansion_5d_pct: float = 50.0,
    fresh_low_window: int = 60,
    allow_repeated_signals: bool = False,
    require_recovery_day: bool = True,
    strategy_variant: str = S3_BASELINE,
) -> tuple[Signal, ...]:
    """Generate S3 signals using the default strategy class."""

    strategy = S3TrendPullbackContinuationStrategy(
        sma_fast_window=sma_fast_window,
        sma_slow_window=sma_slow_window,
        sma_slope_lookback=sma_slope_lookback,
        pullback_lookback=pullback_lookback,
        min_pullback_return_pct=min_pullback_return_pct,
        max_pullback_return_pct=max_pullback_return_pct,
        max_drawdown_20d_pct=max_drawdown_20d_pct,
        min_drawdown_20d_pct=min_drawdown_20d_pct,
        atr_window=atr_window,
        max_atr_pct=max_atr_pct,
        max_atr_expansion_5d_pct=max_atr_expansion_5d_pct,
        fresh_low_window=fresh_low_window,
        allow_repeated_signals=allow_repeated_signals,
        require_recovery_day=require_recovery_day,
        strategy_variant=strategy_variant,
    )
    return strategy.generate_signals(symbol=symbol, data=data)


def validate_s3_strategy_variant(variant: str) -> str:
    """Return a valid S3 strategy variant or raise a clear ValueError."""

    if variant not in S3_STRATEGY_VARIANTS:
        allowed = ", ".join(S3_STRATEGY_VARIANTS)
        raise ValueError(
            f"unknown S3 strategy variant {variant!r}; expected one of: {allowed}"
        )
    return variant


def _variant_requires_strong_trend(variant: str) -> bool:
    return variant in {S3_STRONG_TREND_V1, S3_STRONG_TREND_ABOVE_SMA50_V1}


def _variant_requires_above_sma50(variant: str) -> bool:
    return variant in {S3_ABOVE_SMA50_V1, S3_STRONG_TREND_ABOVE_SMA50_V1}


def build_s3_feature_frame(
    data: pd.DataFrame,
    sma_fast_window: int = 50,
    sma_slow_window: int = 200,
    sma_slope_lookback: int = 20,
    pullback_lookback: int = 5,
    atr_window: int = 14,
    fresh_low_window: int = 60,
) -> pd.DataFrame:
    """Return deterministic S3 signal-date features for each row."""

    _validate_input(data)
    close = data["close"]
    sma50 = close.rolling(window=sma_fast_window, min_periods=sma_fast_window).mean()
    sma200 = close.rolling(window=sma_slow_window, min_periods=sma_slow_window).mean()
    rolling_20d_high = close.rolling(window=20, min_periods=20).max()
    rolling_60d_high = close.rolling(window=60, min_periods=60).max()
    rolling_60d_low = close.rolling(
        window=fresh_low_window,
        min_periods=fresh_low_window,
    ).min()
    atr14 = atr(data, atr_window)

    return pd.DataFrame(
        {
            "close": close,
            "previous_close": close.shift(1),
            "sma50": sma50,
            "sma200": sma200,
            "close_vs_sma50_pct": _pct_vs(close, sma50),
            "close_vs_sma200_pct": _pct_vs(close, sma200),
            "sma50_slope_20d_pct": _pct_vs(sma50, sma50.shift(sma_slope_lookback)),
            "sma200_slope_20d_pct": _pct_vs(
                sma200,
                sma200.shift(sma_slope_lookback),
            ),
            "return_3d_pct": _pct_vs(close, close.shift(3)),
            "return_5d_pct": _pct_vs(close, close.shift(pullback_lookback)),
            "return_10d_pct": _pct_vs(close, close.shift(10)),
            "drawdown_20d_pct": _pct_vs(close, rolling_20d_high),
            "drawdown_60d_pct": _pct_vs(close, rolling_60d_high),
            "close_vs_20d_high_pct": _pct_vs(close, rolling_20d_high),
            "close_vs_60d_low_pct": _pct_vs(close, rolling_60d_low),
            "is_60d_low": close <= rolling_60d_low,
            "atr14_pct": (atr14 / close) * 100,
            "atr14_change_5d_pct": _pct_vs(atr14, atr14.shift(5)),
        },
        index=data.index,
    )


def _chronological_copy(data: pd.DataFrame) -> pd.DataFrame:
    date_column = "date" if "date" in data.columns else "timestamp"
    return (
        data.copy(deep=True)
        .assign(_s3_sort_date=pd.to_datetime(data[date_column]))
        .sort_values("_s3_sort_date", kind="mergesort")
        .drop(columns="_s3_sort_date")
        .reset_index(drop=True)
    )


def _pct_vs(current: pd.Series, reference: pd.Series) -> pd.Series:
    return ((current / reference) - 1) * 100


def _validate_input(data: pd.DataFrame) -> None:
    required = ["open", "high", "low", "close"]
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
