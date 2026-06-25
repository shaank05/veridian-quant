"""Feature calculations and abstractions for Veridian Quant v2."""

from veridian_quant.v2.features.market_context import (
    DEFAULT_CONTEXT_WINDOWS,
    align_stock_with_index,
    compute_cap_relative_context,
    compute_market_context_features,
    compute_market_relative_context,
    compute_returns_by_window,
    compute_sector_relative_context,
)
from veridian_quant.v2.features.technical import (
    atr,
    price_zscore,
    rolling_mean_close,
    rolling_std_close,
    true_range,
)

__all__ = [
    "DEFAULT_CONTEXT_WINDOWS",
    "align_stock_with_index",
    "atr",
    "compute_cap_relative_context",
    "compute_market_context_features",
    "compute_market_relative_context",
    "compute_returns_by_window",
    "compute_sector_relative_context",
    "price_zscore",
    "rolling_mean_close",
    "rolling_std_close",
    "true_range",
]
