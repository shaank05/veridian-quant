"""Benchmark, sector, and cap-relative context feature utilities.

These helpers are pure pandas transformations. They align rows by session date,
use only current and prior closes, preserve insufficient-lookback ``NaN``
values, and do not mutate caller-provided data. They do not generate signals,
rank candidates, run backtests, or change strategy behavior.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from veridian_quant.v2.data.sector_proxy_mapping import (
    SectorProxyResolution,
    resolve_sector_proxy,
)


DEFAULT_CONTEXT_WINDOWS = (5, 20, 60, 120, 252)
UNKNOWN_MARKET_CAP_BUCKET = "unknown"


def compute_returns_by_window(
    data: pd.DataFrame,
    windows: Iterable[int] = DEFAULT_CONTEXT_WINDOWS,
    *,
    price_col: str = "close",
    prefix: str = "ret",
) -> pd.DataFrame:
    """Return simple close-to-close returns for each requested window."""

    normalized_windows = _validate_windows(windows)
    frame = _normalize_price_frame(data, required_columns=(price_col,))
    result = pd.DataFrame({"session_date": frame["session_date"]})
    close = frame[price_col]
    for window in normalized_windows:
        prior_close = close.shift(window).replace(0.0, np.nan)
        result[f"{prefix}_{window}d"] = close / prior_close - 1.0
    return result


def align_stock_with_index(
    stock_df: pd.DataFrame,
    index_df: pd.DataFrame,
    *,
    stock_close_col: str = "close",
    index_close_col: str = "close",
    index_close_output_col: str = "index_close",
) -> pd.DataFrame:
    """Inner-align stock and index closes on ``session_date``."""

    stock = _normalize_price_frame(stock_df, required_columns=(stock_close_col,))
    index = _normalize_price_frame(index_df, required_columns=(index_close_col,))
    stock = stock.rename(columns={stock_close_col: "stock_close"})
    index = index.rename(columns={index_close_col: index_close_output_col})
    aligned = stock[["session_date", "stock_close"]].merge(
        index[["session_date", index_close_output_col]],
        on="session_date",
        how="inner",
        sort=True,
    )
    return aligned.reset_index(drop=True)


def compute_market_relative_context(
    stock_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    windows: Iterable[int] = DEFAULT_CONTEXT_WINDOWS,
    *,
    benchmark_name: str = "NIFTY_500",
) -> pd.DataFrame:
    """Compute stock-versus-benchmark return context."""

    normalized_windows = _validate_windows(windows)
    result = align_stock_with_index(
        stock_df,
        benchmark_df,
        index_close_output_col="benchmark_close",
    )
    result["benchmark"] = _clean_text(benchmark_name, "benchmark_name")
    _attach_relative_return_columns(
        result,
        windows=normalized_windows,
        stock_prefix="ret",
        context_prefix="benchmark_ret",
        relative_prefix="rel_benchmark_ret",
        ratio_prefix="stock_return_ratio_vs_benchmark",
        context_close_col="benchmark_close",
    )
    _attach_trend_flags(
        result,
        windows=normalized_windows,
        close_col="benchmark_close",
        output_prefix="benchmark",
    )
    return result


def compute_sector_relative_context(
    stock_df: pd.DataFrame,
    sector_index_df: pd.DataFrame | None,
    windows: Iterable[int] = DEFAULT_CONTEXT_WINDOWS,
    *,
    sector: object,
    sector_proxy: str | None = None,
    fallback_to_nifty500: bool = False,
) -> pd.DataFrame:
    """Compute stock-versus-sector-proxy return context when available."""

    normalized_windows = _validate_windows(windows)
    resolution = (
        SectorProxyResolution(
            sector=_clean_optional_text(sector),
            sector_proxy=sector_proxy,
            sector_proxy_is_fallback=False,
            sector_proxy_unmapped=False,
        )
        if sector_proxy
        else resolve_sector_proxy(sector, fallback_to_nifty500=fallback_to_nifty500)
    )

    if sector_index_df is None or resolution.sector_proxy is None:
        result = _stock_base_frame(stock_df)
        _attach_sector_metadata(result, resolution)
        for window in normalized_windows:
            result[f"sector_ret_{window}d"] = np.nan
            result[f"rel_sector_ret_{window}d"] = np.nan
        return result

    result = align_stock_with_index(
        stock_df,
        sector_index_df,
        index_close_output_col="sector_close",
    )
    _attach_sector_metadata(result, resolution)
    _attach_relative_return_columns(
        result,
        windows=normalized_windows,
        stock_prefix="ret",
        context_prefix="sector_ret",
        relative_prefix="rel_sector_ret",
        ratio_prefix=None,
        context_close_col="sector_close",
    )
    _attach_trend_flags(
        result,
        windows=normalized_windows,
        close_col="sector_close",
        output_prefix="sector",
    )
    return result


def compute_cap_relative_context(
    stock_df: pd.DataFrame,
    cap_index_df: pd.DataFrame | None = None,
    windows: Iterable[int] = DEFAULT_CONTEXT_WINDOWS,
    *,
    market_cap_bucket: object = UNKNOWN_MARKET_CAP_BUCKET,
    cap_proxy: str | None = None,
) -> pd.DataFrame:
    """Compute cap-relative context, safely returning NaN for unknown buckets."""

    normalized_windows = _validate_windows(windows)
    bucket = _normalize_market_cap_bucket_text(market_cap_bucket)
    if bucket == UNKNOWN_MARKET_CAP_BUCKET or cap_index_df is None or cap_proxy is None:
        result = _stock_base_frame(stock_df)
        result["market_cap_bucket"] = bucket
        result["cap_proxy"] = cap_proxy
        result["cap_proxy_unmapped"] = bucket == UNKNOWN_MARKET_CAP_BUCKET or cap_proxy is None
        for window in normalized_windows:
            result[f"cap_ret_{window}d"] = np.nan
            result[f"rel_cap_ret_{window}d"] = np.nan
        return result

    result = align_stock_with_index(
        stock_df,
        cap_index_df,
        index_close_output_col="cap_close",
    )
    result["market_cap_bucket"] = bucket
    result["cap_proxy"] = cap_proxy
    result["cap_proxy_unmapped"] = False
    _attach_relative_return_columns(
        result,
        windows=normalized_windows,
        stock_prefix="ret",
        context_prefix="cap_ret",
        relative_prefix="rel_cap_ret",
        ratio_prefix=None,
        context_close_col="cap_close",
    )
    return result


def compute_market_context_features(
    stock_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    sector_index_df: pd.DataFrame | None = None,
    windows: Iterable[int] = DEFAULT_CONTEXT_WINDOWS,
    *,
    benchmark_name: str = "NIFTY_500",
    sector: object = "UNKNOWN",
    sector_proxy: str | None = None,
    fallback_sector_to_nifty500: bool = False,
    market_cap_bucket: object = UNKNOWN_MARKET_CAP_BUCKET,
    cap_index_df: pd.DataFrame | None = None,
    cap_proxy: str | None = None,
) -> pd.DataFrame:
    """Return combined market, sector, and cap context features."""

    market = compute_market_relative_context(
        stock_df,
        benchmark_df,
        windows,
        benchmark_name=benchmark_name,
    )
    sector_frame = compute_sector_relative_context(
        stock_df,
        sector_index_df,
        windows,
        sector=sector,
        sector_proxy=sector_proxy,
        fallback_to_nifty500=fallback_sector_to_nifty500,
    ).drop(columns=["stock_close"], errors="ignore")
    cap_frame = compute_cap_relative_context(
        stock_df,
        cap_index_df,
        windows,
        market_cap_bucket=market_cap_bucket,
        cap_proxy=cap_proxy,
    ).drop(columns=["stock_close"], errors="ignore")

    combined = market.merge(sector_frame, on="session_date", how="left", sort=True)
    combined = combined.merge(cap_frame, on="session_date", how="left", sort=True)
    return combined.reset_index(drop=True)


def _attach_relative_return_columns(
    result: pd.DataFrame,
    *,
    windows: tuple[int, ...],
    stock_prefix: str,
    context_prefix: str,
    relative_prefix: str,
    ratio_prefix: str | None,
    context_close_col: str,
) -> None:
    stock_close = result["stock_close"]
    context_close = result[context_close_col]
    for window in windows:
        stock_ret = _safe_period_return(stock_close, window)
        context_ret = _safe_period_return(context_close, window)
        result[f"{stock_prefix}_{window}d"] = stock_ret
        result[f"{context_prefix}_{window}d"] = context_ret
        result[f"{relative_prefix}_{window}d"] = stock_ret - context_ret
        if ratio_prefix is not None:
            result[f"{ratio_prefix}_{window}d"] = stock_ret / context_ret.replace(0.0, np.nan)


def _attach_trend_flags(
    result: pd.DataFrame,
    *,
    windows: tuple[int, ...],
    close_col: str,
    output_prefix: str,
) -> None:
    close = result[close_col]
    for window in windows:
        moving_average = close.rolling(window=window, min_periods=window).mean()
        trend_flag = (close > moving_average).astype(object)
        trend_flag.loc[moving_average.isna()] = np.nan
        result[f"{output_prefix}_above_sma_{window}d"] = trend_flag


def _attach_sector_metadata(
    result: pd.DataFrame,
    resolution: SectorProxyResolution,
) -> None:
    result["sector"] = resolution.sector
    result["sector_proxy"] = resolution.sector_proxy
    result["sector_proxy_is_fallback"] = resolution.sector_proxy_is_fallback
    result["sector_proxy_unmapped"] = resolution.sector_proxy_unmapped


def _stock_base_frame(stock_df: pd.DataFrame) -> pd.DataFrame:
    stock = _normalize_price_frame(stock_df, required_columns=("close",))
    return stock[["session_date", "close"]].rename(columns={"close": "stock_close"})


def _safe_period_return(close: pd.Series, window: int) -> pd.Series:
    prior_close = close.shift(window).replace(0.0, np.nan)
    return close / prior_close - 1.0


def _normalize_price_frame(
    data: pd.DataFrame,
    *,
    required_columns: Iterable[str],
) -> pd.DataFrame:
    required = tuple(required_columns)
    date_col = _resolve_date_column(data)
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")
    frame = data.copy(deep=True)
    frame["session_date"] = pd.to_datetime(frame[date_col], errors="raise").dt.normalize()
    for column in required:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.sort_values("session_date", kind="mergesort").drop_duplicates(
        subset="session_date",
        keep="last",
    ).reset_index(drop=True)


def _resolve_date_column(data: pd.DataFrame) -> str:
    for column in ("session_date", "date", "timestamp"):
        if column in data.columns:
            return column
    raise ValueError("missing required columns: session_date/date/timestamp")


def _validate_windows(windows: Iterable[int]) -> tuple[int, ...]:
    values = tuple(windows)
    if not values:
        raise ValueError("windows must contain at least one value")
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError("windows must be positive integers")
    return values


def _clean_text(value: object, field_name: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise ValueError(f"{field_name} must be non-empty")
    return text


def _clean_optional_text(value: object) -> str:
    if value is None:
        return "UNKNOWN"
    text = str(value).strip()
    return text or "UNKNOWN"


def _normalize_market_cap_bucket_text(value: object) -> str:
    text = _clean_optional_text(value).lower()
    return "_".join(text.replace("-", "_").split())
