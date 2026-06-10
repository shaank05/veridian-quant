"""S1 Z-score mean-reversion signal generation for Veridian Quant v2.

This module implements the S1 signal layer only. It converts one symbol's OHLCV
dataframe into LONG signal candidates when close-price Z-score crosses below the
configured entry threshold. It does not enter trades, size positions, resolve
exits, run backtests, or use any non-S1 filters.
"""

from dataclasses import dataclass
from datetime import date
from types import MappingProxyType

import pandas as pd

from veridian_quant.v2.data.models import Signal, SignalType
from veridian_quant.v2.features.technical import atr, price_zscore


STRATEGY_NAME = "S1_ZSCORE_MEAN_REVERSION"


@dataclass(frozen=True, slots=True)
class S1ZScoreMeanReversionStrategy:
    """Pure S1 signal generator based only on close-price Z-score."""

    window: int = 20
    entry_threshold: float = -2.0
    allow_repeated_signals: bool = False
    strategy_name: str = STRATEGY_NAME

    @property
    def name(self) -> str:
        """Return the stable S1 strategy identifier."""

        return self.strategy_name

    def generate_signals(self, symbol: str, data: pd.DataFrame) -> list[Signal]:
        """Generate LONG signals from one symbol's OHLCV dataframe.

        By default, a signal is produced only when Z-score crosses the threshold:
        previous Z-score is greater than ``entry_threshold`` and current Z-score
        is less than or equal to ``entry_threshold``. When
        ``allow_repeated_signals`` is enabled, every row at or below the
        threshold emits a signal.
        """

        _validate_input(data)
        working = data.copy(deep=True)
        zscores = price_zscore(working, self.window)
        filter_context = _filter_context_features(working)
        signal_mask = zscores <= self.entry_threshold

        if not self.allow_repeated_signals:
            previous_above_threshold = zscores.shift(1) > self.entry_threshold
            signal_mask = signal_mask & previous_above_threshold

        signals: list[Signal] = []
        for index in data.index[signal_mask.fillna(False)]:
            row = data.loc[index]
            zscore = zscores.loc[index]
            context = filter_context.loc[index]
            signals.append(
                Signal(
                    symbol=symbol,
                    signal_type=SignalType.LONG,
                    generated_on=_row_date(row),
                    strategy_name=self.strategy_name,
                    reason=(
                        "Close-price Z-score crossed at or below "
                        f"entry threshold {self.entry_threshold}."
                    ),
                    metadata=MappingProxyType(
                        {
                            "z_score": float(zscore),
                            "zscore_window": self.window,
                            "entry_threshold": self.entry_threshold,
                            "close": float(row["close"]),
                            "stock_drawdown_60d_pct": _blank_nan(
                                context.get("stock_drawdown_60d_pct")
                            ),
                            "stock_close_vs_60d_low_pct": _blank_nan(
                                context.get("stock_close_vs_60d_low_pct")
                            ),
                            "stock_consecutive_down_closes": _blank_nan(
                                context.get("stock_consecutive_down_closes")
                            ),
                            "stock_atr14_change_10d_pct": _blank_nan(
                                context.get("stock_atr14_change_10d_pct")
                            ),
                        }
                    ),
                )
            )
        return signals


def generate_s1_zscore_signals(
    symbol: str,
    data: pd.DataFrame,
    window: int = 20,
    entry_threshold: float = -2.0,
    allow_repeated_signals: bool = False,
) -> list[Signal]:
    """Generate S1 signals using the default strategy class."""

    strategy = S1ZScoreMeanReversionStrategy(
        window=window,
        entry_threshold=entry_threshold,
        allow_repeated_signals=allow_repeated_signals,
    )
    return strategy.generate_signals(symbol=symbol, data=data)


def _validate_input(data: pd.DataFrame) -> None:
    """Validate the minimum dataframe columns required by S1."""

    missing = [column for column in ("close",) if column not in data.columns]
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")
    if "date" not in data.columns and "timestamp" not in data.columns:
        raise ValueError("missing required columns: date or timestamp")


def _filter_context_features(data: pd.DataFrame) -> pd.DataFrame:
    """Return signal-date filter context using rows through each signal date."""

    close = data["close"]
    rolling_60d_high = close.rolling(window=60, min_periods=60).max()
    rolling_60d_low = close.rolling(window=60, min_periods=60).min()
    if {"high", "low"}.issubset(data.columns):
        atr14 = atr(data, 14)
    else:
        atr14 = pd.Series(pd.NA, index=data.index)
    return pd.DataFrame(
        {
            "stock_drawdown_60d_pct": ((close / rolling_60d_high) - 1) * 100,
            "stock_close_vs_60d_low_pct": ((close / rolling_60d_low) - 1) * 100,
            "stock_consecutive_down_closes": _consecutive_down_closes(close),
            "stock_atr14_change_10d_pct": ((atr14 / atr14.shift(10)) - 1) * 100,
        },
        index=data.index,
    )


def _consecutive_down_closes(close: pd.Series) -> pd.Series:
    """Return consecutive sessions where close is below the previous close."""

    counts: list[int | None] = []
    current_count = 0
    for index, value in enumerate(close):
        if index == 0 or pd.isna(value) or pd.isna(close.iloc[index - 1]):
            current_count = 0
            counts.append(None)
            continue
        if value < close.iloc[index - 1]:
            current_count += 1
        else:
            current_count = 0
        counts.append(current_count)
    return pd.Series(counts, index=close.index, dtype="object")


def _blank_nan(value: object) -> object:
    """Return None for pandas missing values."""

    if pd.isna(value):
        return None
    return value


def _row_date(row: pd.Series) -> date:
    """Return a Python date from the row's date or timestamp field."""

    value = row["date"] if "date" in row.index else row["timestamp"]
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()
