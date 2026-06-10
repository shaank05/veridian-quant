"""Signal-date regime context diagnostics for completed v2 backtests.

These helpers summarize already-computed backtest outputs with market context
known at signal generation time. They do not generate signals, run strategies,
resolve exits, size positions, or calculate trade PnL.
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

import pandas as pd

from veridian_quant.v2.features.technical import atr
from veridian_quant.v2.reporting.diagnostics import (
    _initial_risk_amount,
    _r_multiple,
    _r_multiple_group_summary,
)


TRADE_SIGNAL_CONTEXT_COLUMNS = [
    "trade_id",
    "symbol",
    "strategy_name",
    "signal_date",
    "entry_date",
    "exit_date",
    "exit_reason",
    "net_pnl",
    "r_multiple",
    "entry_price",
    "exit_price",
    "stop_loss",
    "target_price",
    "initial_risk_amount",
    "reward_risk_ratio",
    "z_score",
    "zscore_window",
    "entry_threshold",
    "signal_close",
    "stock_close",
    "stock_sma50",
    "stock_sma200",
    "stock_close_vs_sma50_pct",
    "stock_close_vs_sma200_pct",
    "stock_sma50_slope_20d_pct",
    "stock_sma200_slope_20d_pct",
    "stock_return_20d_pct",
    "stock_return_60d_pct",
    "stock_return_120d_pct",
    "stock_drawdown_60d_pct",
    "stock_atr14",
    "stock_atr14_pct",
    "nifty_close",
    "nifty_sma50",
    "nifty_sma200",
    "nifty_close_vs_sma50_pct",
    "nifty_close_vs_sma200_pct",
    "nifty_sma50_slope_20d_pct",
    "nifty_sma200_slope_20d_pct",
    "nifty_return_20d_pct",
    "nifty_return_60d_pct",
    "nifty_return_120d_pct",
    "nifty_drawdown_60d_pct",
    "nifty_atr14",
    "nifty_atr14_pct",
    "relative_strength_20d_vs_nifty",
    "relative_strength_60d_vs_nifty",
    "relative_strength_120d_vs_nifty",
]
R_CONTEXT_BUCKET_COLUMNS = [
    "context",
    "bucket",
    "trades_with_r",
    "winning_trades",
    "losing_trades",
    "positive_r_rate_pct",
    "average_r",
    "average_winner_r",
    "average_loser_r",
    "best_r",
    "worst_r",
]


def build_trade_signal_context_rows(
    result: Any,
    stock_data_by_symbol: Mapping[str, pd.DataFrame] | None = None,
    nifty_data: pd.DataFrame | None = None,
) -> list[dict[str, object]]:
    """Return one signal-date context row per executed trade PnL."""

    stock_features = {
        symbol: _context_features(data)
        for symbol, data in (stock_data_by_symbol or {}).items()
        if data is not None
    }
    nifty_features = _context_features(nifty_data) if nifty_data is not None else None

    rows = []
    for pnl in result.trade_pnls:
        signal = _nearest_previous_signal(pnl, result.signals)
        signal_date = getattr(signal, "generated_on", None)
        metadata = getattr(signal, "metadata", {}) if signal is not None else {}
        if metadata is None or not hasattr(metadata, "get"):
            metadata = {}

        stock_context = _features_as_of(stock_features.get(pnl.symbol), signal_date)
        nifty_context = _features_as_of(nifty_features, signal_date)

        row = {
            "trade_id": pnl.trade_id,
            "symbol": pnl.symbol,
            "strategy_name": pnl.strategy_name,
            "signal_date": signal_date,
            "entry_date": pnl.entry_date,
            "exit_date": pnl.exit_date,
            "exit_reason": _enum_value(pnl.exit_reason),
            "net_pnl": pnl.net_pnl,
            "r_multiple": _r_multiple(pnl),
            "entry_price": pnl.entry_price,
            "exit_price": pnl.exit_price,
            "stop_loss": getattr(pnl, "stop_loss", None),
            "target_price": getattr(pnl, "target_price", None),
            "initial_risk_amount": _initial_risk_amount(pnl),
            "reward_risk_ratio": getattr(pnl, "reward_risk_ratio", None),
            "z_score": metadata.get("z_score"),
            "zscore_window": metadata.get("zscore_window"),
            "entry_threshold": metadata.get("entry_threshold"),
            "signal_close": metadata.get("close"),
        }
        row.update(_prefixed_context("stock", stock_context))
        row.update(_prefixed_context("nifty", nifty_context))
        row.update(_relative_strength_context(stock_context, nifty_context))
        rows.append(row)
    return rows


def build_r_by_stock_trend_context_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return R summaries for stock trend context buckets."""

    buckets = (
        (
            "stock_vs_sma200",
            "stock_above_sma200",
            lambda row: _to_decimal(row.get("stock_close_vs_sma200_pct")) is not None
            and _to_decimal(row.get("stock_close_vs_sma200_pct")) > 0,
        ),
        (
            "stock_vs_sma200",
            "stock_below_sma200",
            lambda row: _to_decimal(row.get("stock_close_vs_sma200_pct")) is not None
            and _to_decimal(row.get("stock_close_vs_sma200_pct")) < 0,
        ),
        (
            "stock_sma50_slope",
            "stock_sma50_slope_positive",
            lambda row: _to_decimal(row.get("stock_sma50_slope_20d_pct")) is not None
            and _to_decimal(row.get("stock_sma50_slope_20d_pct")) > 0,
        ),
        (
            "stock_sma50_slope",
            "stock_sma50_slope_negative",
            lambda row: _to_decimal(row.get("stock_sma50_slope_20d_pct")) is not None
            and _to_decimal(row.get("stock_sma50_slope_20d_pct")) < 0,
        ),
        (
            "stock_sma200_slope",
            "stock_sma200_slope_positive",
            lambda row: _to_decimal(row.get("stock_sma200_slope_20d_pct")) is not None
            and _to_decimal(row.get("stock_sma200_slope_20d_pct")) > 0,
        ),
        (
            "stock_sma200_slope",
            "stock_sma200_slope_negative",
            lambda row: _to_decimal(row.get("stock_sma200_slope_20d_pct")) is not None
            and _to_decimal(row.get("stock_sma200_slope_20d_pct")) < 0,
        ),
    )
    return _bucket_rows(trade_context_rows, buckets)


def build_r_by_nifty_trend_context_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return R summaries for Nifty trend context buckets."""

    buckets = (
        (
            "nifty_vs_sma50",
            "nifty_above_sma50",
            lambda row: _to_decimal(row.get("nifty_close_vs_sma50_pct")) is not None
            and _to_decimal(row.get("nifty_close_vs_sma50_pct")) > 0,
        ),
        (
            "nifty_vs_sma50",
            "nifty_below_sma50",
            lambda row: _to_decimal(row.get("nifty_close_vs_sma50_pct")) is not None
            and _to_decimal(row.get("nifty_close_vs_sma50_pct")) < 0,
        ),
        (
            "nifty_vs_sma200",
            "nifty_above_sma200",
            lambda row: _to_decimal(row.get("nifty_close_vs_sma200_pct")) is not None
            and _to_decimal(row.get("nifty_close_vs_sma200_pct")) > 0,
        ),
        (
            "nifty_vs_sma200",
            "nifty_below_sma200",
            lambda row: _to_decimal(row.get("nifty_close_vs_sma200_pct")) is not None
            and _to_decimal(row.get("nifty_close_vs_sma200_pct")) < 0,
        ),
        (
            "nifty_sma50_slope",
            "nifty_sma50_slope_positive",
            lambda row: _to_decimal(row.get("nifty_sma50_slope_20d_pct")) is not None
            and _to_decimal(row.get("nifty_sma50_slope_20d_pct")) > 0,
        ),
        (
            "nifty_sma50_slope",
            "nifty_sma50_slope_negative",
            lambda row: _to_decimal(row.get("nifty_sma50_slope_20d_pct")) is not None
            and _to_decimal(row.get("nifty_sma50_slope_20d_pct")) < 0,
        ),
        (
            "nifty_sma200_slope",
            "nifty_sma200_slope_positive",
            lambda row: _to_decimal(row.get("nifty_sma200_slope_20d_pct")) is not None
            and _to_decimal(row.get("nifty_sma200_slope_20d_pct")) > 0,
        ),
        (
            "nifty_sma200_slope",
            "nifty_sma200_slope_negative",
            lambda row: _to_decimal(row.get("nifty_sma200_slope_20d_pct")) is not None
            and _to_decimal(row.get("nifty_sma200_slope_20d_pct")) < 0,
        ),
    )
    return _bucket_rows(trade_context_rows, buckets)


def build_r_by_relative_strength_context_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return R summaries for relative strength context buckets."""

    buckets = (
        (
            "relative_strength_20d",
            "rs_20d_positive",
            lambda row: _to_decimal(row.get("relative_strength_20d_vs_nifty"))
            is not None
            and _to_decimal(row.get("relative_strength_20d_vs_nifty")) > 0,
        ),
        (
            "relative_strength_20d",
            "rs_20d_negative",
            lambda row: _to_decimal(row.get("relative_strength_20d_vs_nifty"))
            is not None
            and _to_decimal(row.get("relative_strength_20d_vs_nifty")) < 0,
        ),
        (
            "relative_strength_60d",
            "rs_60d_positive",
            lambda row: _to_decimal(row.get("relative_strength_60d_vs_nifty"))
            is not None
            and _to_decimal(row.get("relative_strength_60d_vs_nifty")) > 0,
        ),
        (
            "relative_strength_60d",
            "rs_60d_negative",
            lambda row: _to_decimal(row.get("relative_strength_60d_vs_nifty"))
            is not None
            and _to_decimal(row.get("relative_strength_60d_vs_nifty")) < 0,
        ),
        (
            "relative_strength_120d",
            "rs_120d_positive",
            lambda row: _to_decimal(row.get("relative_strength_120d_vs_nifty"))
            is not None
            and _to_decimal(row.get("relative_strength_120d_vs_nifty")) > 0,
        ),
        (
            "relative_strength_120d",
            "rs_120d_negative",
            lambda row: _to_decimal(row.get("relative_strength_120d_vs_nifty"))
            is not None
            and _to_decimal(row.get("relative_strength_120d_vs_nifty")) < 0,
        ),
    )
    return _bucket_rows(trade_context_rows, buckets)


def _context_features(data: pd.DataFrame) -> pd.DataFrame:
    """Return context feature dataframe indexed by normalized trading date."""

    if data.empty:
        return pd.DataFrame()
    frame = data.copy(deep=True)
    frame["date"] = _normalize_date_series_to_naive_dates(frame["date"])
    frame = frame.sort_values("date").drop_duplicates(subset="date", keep="last")

    close = frame["close"]
    frame["sma50"] = close.rolling(window=50, min_periods=50).mean()
    frame["sma200"] = close.rolling(window=200, min_periods=200).mean()
    frame["close_vs_sma50_pct"] = ((close / frame["sma50"]) - 1) * 100
    frame["close_vs_sma200_pct"] = ((close / frame["sma200"]) - 1) * 100
    frame["sma50_slope_20d_pct"] = ((frame["sma50"] / frame["sma50"].shift(20)) - 1) * 100
    frame["sma200_slope_20d_pct"] = ((frame["sma200"] / frame["sma200"].shift(20)) - 1) * 100
    frame["return_20d_pct"] = ((close / close.shift(20)) - 1) * 100
    frame["return_60d_pct"] = ((close / close.shift(60)) - 1) * 100
    frame["return_120d_pct"] = ((close / close.shift(120)) - 1) * 100
    frame["drawdown_60d_pct"] = ((close / close.rolling(window=60, min_periods=60).max()) - 1) * 100
    frame["atr14"] = atr(frame, 14)
    frame["atr14_pct"] = (frame["atr14"] / close) * 100
    return frame.set_index("date")


def _features_as_of(
    features: pd.DataFrame | None,
    signal_date: date | None,
) -> dict[str, object]:
    """Return feature values known as of the signal date."""

    if features is None or features.empty or signal_date is None:
        return {}
    normalized_date = _normalize_scalar_to_naive_date(signal_date)
    available = features.loc[features.index <= normalized_date]
    if available.empty:
        return {}
    row = available.iloc[-1]
    return {
        key: _blank_nan(row.get(key))
        for key in (
            "close",
            "sma50",
            "sma200",
            "close_vs_sma50_pct",
            "close_vs_sma200_pct",
            "sma50_slope_20d_pct",
            "sma200_slope_20d_pct",
            "return_20d_pct",
            "return_60d_pct",
            "return_120d_pct",
            "drawdown_60d_pct",
            "atr14",
            "atr14_pct",
        )
    }


def _prefixed_context(prefix: str, context: dict[str, object]) -> dict[str, object]:
    """Return context feature names with stock/nifty report prefixes."""

    return {
        f"{prefix}_close": context.get("close"),
        f"{prefix}_sma50": context.get("sma50"),
        f"{prefix}_sma200": context.get("sma200"),
        f"{prefix}_close_vs_sma50_pct": context.get("close_vs_sma50_pct"),
        f"{prefix}_close_vs_sma200_pct": context.get("close_vs_sma200_pct"),
        f"{prefix}_sma50_slope_20d_pct": context.get("sma50_slope_20d_pct"),
        f"{prefix}_sma200_slope_20d_pct": context.get("sma200_slope_20d_pct"),
        f"{prefix}_return_20d_pct": context.get("return_20d_pct"),
        f"{prefix}_return_60d_pct": context.get("return_60d_pct"),
        f"{prefix}_return_120d_pct": context.get("return_120d_pct"),
        f"{prefix}_drawdown_60d_pct": context.get("drawdown_60d_pct"),
        f"{prefix}_atr14": context.get("atr14"),
        f"{prefix}_atr14_pct": context.get("atr14_pct"),
    }


def _relative_strength_context(
    stock_context: dict[str, object],
    nifty_context: dict[str, object],
) -> dict[str, object]:
    """Return stock return less Nifty return for 20/60/120 sessions."""

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


def _bucket_rows(
    trade_context_rows: list[dict[str, object]],
    buckets: tuple[tuple[str, str, Any], ...],
) -> list[dict[str, object]]:
    """Return deterministic R summary rows for populated context buckets."""

    grouped: dict[tuple[str, str], list[Decimal]] = defaultdict(list)
    for row in trade_context_rows:
        r_multiple = _to_decimal(row.get("r_multiple"))
        if r_multiple is None:
            continue
        for context, bucket, predicate in buckets:
            if predicate(row):
                grouped[(context, bucket)].append(r_multiple)

    return [
        {
            "context": context,
            "bucket": bucket,
            **_r_multiple_group_summary(tuple(r_values)),
        }
        for (context, bucket), r_values in sorted(grouped.items())
    ]


def _nearest_previous_signal(pnl: Any, signals: tuple[Any, ...]) -> Any | None:
    """Return nearest previous same-symbol same-strategy signal for a trade."""

    entry_date = _normalize_scalar_to_naive_date(pnl.entry_date)
    candidates = [
        signal
        for signal in signals
        if signal.symbol == pnl.symbol
        and signal.strategy_name == pnl.strategy_name
        and _normalize_scalar_to_naive_date(signal.generated_on) < entry_date
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda signal: _normalize_scalar_to_naive_date(signal.generated_on),
    )


def _normalize_date_series_to_naive_dates(series: pd.Series) -> pd.Series:
    """Return timezone-naive normalized dates for mixed date-like inputs."""

    return pd.to_datetime(series, utc=True).dt.tz_localize(None).dt.normalize()


def _normalize_scalar_to_naive_date(value: object) -> pd.Timestamp:
    """Return a timezone-naive normalized timestamp for one date-like value."""

    normalized = pd.to_datetime(
        pd.Series([value]),
        utc=True,
    ).dt.tz_localize(None)
    return normalized.dt.normalize().iloc[0]


def _subtract(left: object, right: object) -> Decimal | None:
    """Return Decimal subtraction, or None when either side is unavailable."""

    left_decimal = _to_decimal(left)
    right_decimal = _to_decimal(right)
    if left_decimal is None or right_decimal is None:
        return None
    return left_decimal - right_decimal


def _to_decimal(value: Any) -> Decimal | None:
    """Convert a numeric value to Decimal, or None for unavailable values."""

    if value is None or pd.isna(value):
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _blank_nan(value: object) -> object:
    """Return None for pandas missing values."""

    if pd.isna(value):
        return None
    return value


def _enum_value(value: Any) -> Any:
    """Return enum value when present, otherwise the original value."""

    return getattr(value, "value", value)
