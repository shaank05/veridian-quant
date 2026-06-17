"""Signal-time context enrichment for S2 Markov ranking.

These helpers add metadata known on or before each signal date. They do not
generate signals, filter signals, rank candidates, create trades, or mutate
caller-owned Signal/dataframe objects.
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Mapping

import pandas as pd

from veridian_quant.v2.data.models import Signal
from veridian_quant.v2.features.technical import atr


STOCK_CONTEXT_METADATA_FIELDS = [
    "stock_close_vs_sma50_pct",
    "stock_close_vs_sma200_pct",
    "stock_sma50_slope_20d_pct",
    "stock_sma200_slope_20d_pct",
    "stock_return_5d_pct",
    "stock_return_10d_pct",
    "stock_return_20d_pct",
    "stock_drawdown_60d_pct",
    "stock_close_vs_60d_low_pct",
    "stock_is_20d_low",
    "stock_is_60d_low",
    "stock_is_120d_low",
    "stock_atr14_pct",
    "stock_atr14_change_5d_pct",
    "stock_consecutive_down_closes",
    "stock_signal_day_return_pct",
]
NIFTY_CONTEXT_METADATA_FIELDS = [
    "nifty_close_vs_sma50_pct",
    "nifty_close_vs_sma200_pct",
    "nifty_sma50_slope_20d_pct",
    "nifty_sma200_slope_20d_pct",
    "nifty_return_5d_pct",
    "nifty_return_20d_pct",
]
RELATIVE_STRENGTH_METADATA_FIELDS = [
    "relative_strength_20d_vs_nifty",
    "relative_strength_60d_vs_nifty",
    "relative_strength_120d_vs_nifty",
]
S2_SIGNAL_CONTEXT_METADATA_FIELDS = [
    *STOCK_CONTEXT_METADATA_FIELDS,
    *NIFTY_CONTEXT_METADATA_FIELDS,
    *RELATIVE_STRENGTH_METADATA_FIELDS,
]


def enrich_s2_signals_with_context(
    signals: tuple[Signal, ...],
    data_by_symbol: Mapping[str, pd.DataFrame],
    nifty_data: pd.DataFrame | None = None,
) -> tuple[Signal, ...]:
    """Return S2 signals with signal-date stock/Nifty context metadata."""

    if not signals:
        return ()

    stock_features = {
        symbol: _context_features(data)
        for symbol, data in data_by_symbol.items()
        if data is not None
    }
    nifty_features = _context_features(nifty_data) if nifty_data is not None else None

    enriched = []
    for signal in signals:
        stock_context = _features_as_of(
            stock_features.get(signal.symbol),
            signal.generated_on,
        )
        nifty_context = _features_as_of(nifty_features, signal.generated_on)
        metadata = dict(signal.metadata)
        metadata.update(_stock_metadata(stock_context))
        metadata.update(_nifty_metadata(nifty_context))
        metadata.update(_relative_strength_metadata(stock_context, nifty_context))
        enriched.append(replace(signal, metadata=MappingProxyType(metadata)))
    return tuple(enriched)


def _context_features(data: pd.DataFrame | None) -> pd.DataFrame | None:
    if data is None or data.empty:
        return None
    required = {"date", "open", "high", "low", "close"}
    if not required.issubset(data.columns):
        return None

    frame = data.copy(deep=True)
    frame["date"] = _normalize_date_series(frame["date"])
    frame = frame.sort_values("date").drop_duplicates(subset="date", keep="last")
    close = pd.to_numeric(frame["close"], errors="coerce")
    previous_close = close.shift(1)

    frame["signal_day_return_pct"] = ((close / previous_close) - 1) * 100
    frame["return_5d_pct"] = ((close / close.shift(5)) - 1) * 100
    frame["return_10d_pct"] = ((close / close.shift(10)) - 1) * 100
    frame["return_20d_pct"] = ((close / close.shift(20)) - 1) * 100
    frame["return_60d_pct"] = ((close / close.shift(60)) - 1) * 100
    frame["return_120d_pct"] = ((close / close.shift(120)) - 1) * 100
    frame["sma50"] = close.rolling(window=50, min_periods=50).mean()
    frame["sma200"] = close.rolling(window=200, min_periods=200).mean()
    frame["close_vs_sma50_pct"] = ((close / frame["sma50"]) - 1) * 100
    frame["close_vs_sma200_pct"] = ((close / frame["sma200"]) - 1) * 100
    frame["sma50_slope_20d_pct"] = (
        (frame["sma50"] / frame["sma50"].shift(20)) - 1
    ) * 100
    frame["sma200_slope_20d_pct"] = (
        (frame["sma200"] / frame["sma200"].shift(20)) - 1
    ) * 100
    frame["drawdown_60d_pct"] = (
        (close / close.rolling(window=60, min_periods=60).max()) - 1
    ) * 100
    frame["atr14"] = atr(frame, 14)
    frame["atr14_pct"] = (frame["atr14"] / close) * 100
    frame["atr14_change_5d_pct"] = ((frame["atr14"] / frame["atr14"].shift(5)) - 1) * 100
    frame["consecutive_down_closes"] = _consecutive_down_closes(close)
    for window in (20, 60, 120):
        low = close.rolling(window=window, min_periods=window).min()
        frame[f"is_{window}d_low"] = (close == low).where(low.notna(), pd.NA)
        frame[f"close_vs_{window}d_low_pct"] = ((close / low) - 1) * 100
    return frame.set_index("date")


def _features_as_of(
    features: pd.DataFrame | None,
    signal_date: date | None,
) -> dict[str, object]:
    if features is None or features.empty or signal_date is None:
        return {}
    normalized_date = _normalize_scalar_date(signal_date)
    available = features.loc[features.index <= normalized_date]
    if available.empty:
        return {}
    row = available.iloc[-1]
    return {
        key: _blank_nan(row.get(key))
        for key in (
            "signal_day_return_pct",
            "return_5d_pct",
            "return_10d_pct",
            "return_20d_pct",
            "return_60d_pct",
            "return_120d_pct",
            "close_vs_sma50_pct",
            "close_vs_sma200_pct",
            "sma50_slope_20d_pct",
            "sma200_slope_20d_pct",
            "drawdown_60d_pct",
            "close_vs_60d_low_pct",
            "is_20d_low",
            "is_60d_low",
            "is_120d_low",
            "atr14_pct",
            "atr14_change_5d_pct",
            "consecutive_down_closes",
        )
    }


def _stock_metadata(context: dict[str, object]) -> dict[str, object]:
    return {
        "stock_close_vs_sma50_pct": context.get("close_vs_sma50_pct"),
        "stock_close_vs_sma200_pct": context.get("close_vs_sma200_pct"),
        "stock_sma50_slope_20d_pct": context.get("sma50_slope_20d_pct"),
        "stock_sma200_slope_20d_pct": context.get("sma200_slope_20d_pct"),
        "stock_return_5d_pct": context.get("return_5d_pct"),
        "stock_return_10d_pct": context.get("return_10d_pct"),
        "stock_return_20d_pct": context.get("return_20d_pct"),
        "stock_drawdown_60d_pct": context.get("drawdown_60d_pct"),
        "stock_close_vs_60d_low_pct": context.get("close_vs_60d_low_pct"),
        "stock_is_20d_low": context.get("is_20d_low"),
        "stock_is_60d_low": context.get("is_60d_low"),
        "stock_is_120d_low": context.get("is_120d_low"),
        "stock_atr14_pct": context.get("atr14_pct"),
        "stock_atr14_change_5d_pct": context.get("atr14_change_5d_pct"),
        "stock_consecutive_down_closes": context.get("consecutive_down_closes"),
        "stock_signal_day_return_pct": context.get("signal_day_return_pct"),
    }


def _nifty_metadata(context: dict[str, object]) -> dict[str, object]:
    return {
        "nifty_close_vs_sma50_pct": context.get("close_vs_sma50_pct"),
        "nifty_close_vs_sma200_pct": context.get("close_vs_sma200_pct"),
        "nifty_sma50_slope_20d_pct": context.get("sma50_slope_20d_pct"),
        "nifty_sma200_slope_20d_pct": context.get("sma200_slope_20d_pct"),
        "nifty_return_5d_pct": context.get("return_5d_pct"),
        "nifty_return_20d_pct": context.get("return_20d_pct"),
    }


def _relative_strength_metadata(
    stock_context: dict[str, object],
    nifty_context: dict[str, object],
) -> dict[str, object]:
    return {
        "relative_strength_20d_vs_nifty": _subtract(
            stock_context.get("return_20d_pct"),
            nifty_context.get("return_20d_pct"),
        ),
        "relative_strength_60d_vs_nifty": _subtract(
            stock_context.get("return_60d_pct"),
            nifty_context.get("return_60d_pct"),
        ),
        "relative_strength_120d_vs_nifty": _subtract(
            stock_context.get("return_120d_pct"),
            nifty_context.get("return_120d_pct"),
        ),
    }


def _consecutive_down_closes(close: pd.Series) -> pd.Series:
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


def _subtract(left: object, right: object) -> Decimal | None:
    left_decimal = _to_decimal(left)
    right_decimal = _to_decimal(right)
    if left_decimal is None or right_decimal is None:
        return None
    return left_decimal - right_decimal


def _to_decimal(value: object) -> Decimal | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _blank_nan(value: object) -> object:
    if pd.isna(value):
        return None
    return value


def _normalize_date_series(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True).dt.tz_localize(None).dt.normalize()


def _normalize_scalar_date(value: object) -> pd.Timestamp:
    normalized = pd.to_datetime(pd.Series([value]), utc=True).dt.tz_localize(None)
    return normalized.dt.normalize().iloc[0]
