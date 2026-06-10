"""Strategy variant filters for v2 S1 research backtests.

Variant filters are evaluated at signal time using only signal-date metadata.
They do not inspect realized outcomes, portfolio state, exits, PnL, or future
bars.
"""

from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd


S1_BASELINE = "S1_BASELINE"
S1_AVOID_MESSY_MIDDLE_V1 = "S1_AVOID_MESSY_MIDDLE_V1"
S1_DRAWDOWN_60D_SHALLOW_OR_DEEP = "S1_DRAWDOWN_60D_SHALLOW_OR_DEEP"
S1_DOWN_CLOSES_GTE_3 = "S1_DOWN_CLOSES_GTE_3"
S1_BROAD_BEST_GUESS = "S1_BROAD_BEST_GUESS"

S1_STRATEGY_VARIANTS = (
    S1_BASELINE,
    S1_AVOID_MESSY_MIDDLE_V1,
    S1_DRAWDOWN_60D_SHALLOW_OR_DEEP,
    S1_DOWN_CLOSES_GTE_3,
    S1_BROAD_BEST_GUESS,
)


def validate_s1_strategy_variant(variant: str) -> str:
    """Return a valid S1 strategy variant or raise a clear ValueError."""

    if variant not in S1_STRATEGY_VARIANTS:
        allowed = ", ".join(S1_STRATEGY_VARIANTS)
        raise ValueError(f"unknown S1 strategy variant {variant!r}; expected one of: {allowed}")
    return variant


def s1_variant_rejection_reason(
    metadata: Any,
    variant: str = S1_BASELINE,
) -> str | None:
    """Return a variant rejection reason, or None when the signal is eligible."""

    validate_s1_strategy_variant(variant)
    if variant == S1_BASELINE:
        return None
    if metadata is None or not hasattr(metadata, "get"):
        return "FILTER_CONTEXT_MISSING"

    if variant == S1_AVOID_MESSY_MIDDLE_V1:
        return _avoid_messy_middle_reason(metadata)
    if variant == S1_DRAWDOWN_60D_SHALLOW_OR_DEEP:
        drawdown = _decimal(metadata.get("stock_drawdown_60d_pct"))
        if drawdown is None:
            return "FILTER_CONTEXT_MISSING"
        if drawdown > Decimal("-5") or drawdown <= Decimal("-20"):
            return None
        return "FILTER_DRAWDOWN_60D_NOT_SHALLOW_OR_DEEP"
    if variant == S1_DOWN_CLOSES_GTE_3:
        down_closes = _decimal(metadata.get("stock_consecutive_down_closes"))
        if down_closes is None:
            return "FILTER_CONTEXT_MISSING"
        if down_closes >= Decimal("3"):
            return None
        return "FILTER_DOWN_CLOSES_LT_3"

    return _broad_best_guess_reason(metadata)


def _avoid_messy_middle_reason(metadata: Any) -> str | None:
    drawdown = _decimal(metadata.get("stock_drawdown_60d_pct"))
    low_distance = _decimal(metadata.get("stock_close_vs_60d_low_pct"))
    if drawdown is None or low_distance is None:
        return "FILTER_CONTEXT_MISSING"
    if Decimal("-20") < drawdown <= Decimal("-5"):
        return "FILTER_MESSY_MIDDLE_DRAWDOWN"
    if Decimal("1") < low_distance <= Decimal("7"):
        return "FILTER_MESSY_MIDDLE_LOW_DISTANCE"
    return None


def _broad_best_guess_reason(metadata: Any) -> str | None:
    z_score = _decimal(metadata.get("z_score"))
    down_closes = _decimal(metadata.get("stock_consecutive_down_closes"))
    atr_change = _decimal(metadata.get("stock_atr14_change_10d_pct"))
    if z_score is None or down_closes is None or atr_change is None:
        return "FILTER_CONTEXT_MISSING"
    if z_score <= Decimal("-3.0"):
        return "FILTER_ZSCORE_TOO_DEEP"
    if down_closes < Decimal("3"):
        return "FILTER_DOWN_CLOSES_LT_3"
    messy_reason = _avoid_messy_middle_reason(metadata)
    if messy_reason is not None:
        return messy_reason
    if atr_change > Decimal("20"):
        return "FILTER_ATR_EXPANSION_TOO_HIGH"
    return None


def _decimal(value: Any) -> Decimal | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
