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
from veridian_quant.v2.features.technical import price_zscore


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
        zscores = price_zscore(data, self.window)
        signal_mask = zscores <= self.entry_threshold

        if not self.allow_repeated_signals:
            previous_above_threshold = zscores.shift(1) > self.entry_threshold
            signal_mask = signal_mask & previous_above_threshold

        signals: list[Signal] = []
        for index in data.index[signal_mask.fillna(False)]:
            row = data.loc[index]
            zscore = zscores.loc[index]
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


def _row_date(row: pd.Series) -> date:
    """Return a Python date from the row's date or timestamp field."""

    value = row["date"] if "date" in row.index else row["timestamp"]
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()
