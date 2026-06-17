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
    "z_score_depth_bucket_source",
    "z_score_prior_1d",
    "z_score_prior_2d",
    "z_score_prior_3d",
    "z_score_change_1d",
    "z_score_change_3d",
    "strategy_family",
    "state_label",
    "state_observation_count",
    "positive_transition_probability",
    "average_forward_return_pct",
    "median_forward_return_pct",
    "current_5d_return_pct",
    "current_atr_pct",
    "current_drawdown_60d_pct",
    "current_close_vs_60d_low_pct",
    "close_vs_sma50_pct",
    "close_vs_sma200_pct",
    "sma50_slope_20d_pct",
    "sma200_slope_20d_pct",
    "return_3d_pct",
    "return_5d_pct",
    "return_10d_pct",
    "drawdown_20d_pct",
    "drawdown_60d_pct",
    "close_vs_20d_high_pct",
    "close_vs_60d_low_pct",
    "is_60d_low",
    "atr14_pct",
    "atr14_change_5d_pct",
    "stock_open",
    "stock_high",
    "stock_low",
    "stock_close",
    "stock_signal_day_return_pct",
    "stock_signal_intraday_return_pct",
    "stock_signal_close_location_pct",
    "stock_signal_range_pct",
    "stock_signal_body_pct",
    "stock_gap_from_prev_close_pct",
    "stock_return_1d_pct",
    "stock_return_3d_pct",
    "stock_return_5d_pct",
    "stock_return_10d_pct",
    "stock_sma50",
    "stock_sma200",
    "stock_close_vs_sma50_pct",
    "stock_close_vs_sma200_pct",
    "stock_sma50_slope_20d_pct",
    "stock_sma200_slope_20d_pct",
    "stock_return_20d_pct",
    "stock_return_60d_pct",
    "stock_return_120d_pct",
    "stock_drawdown_20d_pct",
    "stock_drawdown_60d_pct",
    "stock_drawdown_120d_pct",
    "stock_atr14",
    "stock_atr14_pct",
    "stock_atr14_change_5d_pct",
    "stock_atr14_change_10d_pct",
    "stock_consecutive_down_closes",
    "stock_is_20d_low",
    "stock_is_60d_low",
    "stock_is_120d_low",
    "stock_close_vs_20d_low_pct",
    "stock_close_vs_60d_low_pct",
    "stock_close_vs_120d_low_pct",
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
            "z_score_depth_bucket_source": metadata.get(
                "z_score_depth_bucket_source",
                "signal_metadata" if metadata.get("z_score") is not None else None,
            ),
            "z_score_prior_1d": metadata.get("z_score_prior_1d"),
            "z_score_prior_2d": metadata.get("z_score_prior_2d"),
            "z_score_prior_3d": metadata.get("z_score_prior_3d"),
            "z_score_change_1d": metadata.get("z_score_change_1d"),
            "z_score_change_3d": metadata.get("z_score_change_3d"),
            "strategy_family": metadata.get("strategy_family"),
            "state_label": metadata.get("state_label"),
            "state_observation_count": metadata.get("state_observation_count"),
            "positive_transition_probability": metadata.get(
                "positive_transition_probability"
            ),
            "average_forward_return_pct": metadata.get(
                "average_forward_return_pct"
            ),
            "median_forward_return_pct": metadata.get(
                "median_forward_return_pct"
            ),
            "current_5d_return_pct": metadata.get("current_5d_return_pct"),
            "current_atr_pct": metadata.get("current_atr_pct"),
            "current_drawdown_60d_pct": metadata.get(
                "current_drawdown_60d_pct"
            ),
            "current_close_vs_60d_low_pct": metadata.get(
                "current_close_vs_60d_low_pct"
            ),
            "close_vs_sma50_pct": metadata.get("close_vs_sma50_pct"),
            "close_vs_sma200_pct": metadata.get("close_vs_sma200_pct"),
            "sma50_slope_20d_pct": metadata.get("sma50_slope_20d_pct"),
            "sma200_slope_20d_pct": metadata.get("sma200_slope_20d_pct"),
            "return_3d_pct": metadata.get("return_3d_pct"),
            "return_5d_pct": metadata.get("return_5d_pct"),
            "return_10d_pct": metadata.get("return_10d_pct"),
            "drawdown_20d_pct": metadata.get("drawdown_20d_pct"),
            "drawdown_60d_pct": metadata.get("drawdown_60d_pct"),
            "close_vs_20d_high_pct": metadata.get("close_vs_20d_high_pct"),
            "close_vs_60d_low_pct": metadata.get("close_vs_60d_low_pct"),
            "is_60d_low": metadata.get("is_60d_low"),
            "atr14_pct": metadata.get("atr14_pct"),
            "atr14_change_5d_pct": metadata.get("atr14_change_5d_pct"),
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


def build_r_by_zscore_depth_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return R summaries for current signal z-score depth buckets."""

    return _bucket_rows(
        trade_context_rows,
        (
            (
                "z_score",
                "zscore_-2_to_-2_5",
                lambda row: _between(row.get("z_score"), "-2.5", "-2.0", lower_open=True),
            ),
            (
                "z_score",
                "zscore_-2_5_to_-3",
                lambda row: _between(row.get("z_score"), "-3.0", "-2.5", lower_open=True),
            ),
            (
                "z_score",
                "zscore_below_-3",
                lambda row: _to_decimal(row.get("z_score")) is not None
                and _to_decimal(row.get("z_score")) <= Decimal("-3.0"),
            ),
        ),
    )


def build_r_by_pre_signal_return_context_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return R summaries for pre-signal stock return severity buckets."""

    return _bucket_rows(
        trade_context_rows,
        _bucket_specs(
            ("stock_return_3d_pct", "stock_return_5d_pct", "stock_return_10d_pct"),
            (
                ("return_positive", lambda value: value > 0),
                ("return_0_to_minus_3", lambda value: Decimal("-3") < value <= 0),
                ("return_minus_3_to_minus_7", lambda value: Decimal("-7") < value <= Decimal("-3")),
                ("return_below_minus_7", lambda value: value <= Decimal("-7")),
            ),
        ),
    )


def build_r_by_drawdown_depth_context_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return R summaries for stock drawdown depth buckets."""

    return _bucket_rows(
        trade_context_rows,
        _bucket_specs(
            ("stock_drawdown_20d_pct", "stock_drawdown_60d_pct", "stock_drawdown_120d_pct"),
            (
                ("drawdown_0_to_minus_5", lambda value: Decimal("-5") < value <= 0),
                ("drawdown_minus_5_to_minus_10", lambda value: Decimal("-10") < value <= Decimal("-5")),
                ("drawdown_minus_10_to_minus_20", lambda value: Decimal("-20") < value <= Decimal("-10")),
                ("drawdown_below_minus_20", lambda value: value <= Decimal("-20")),
            ),
        ),
    )


def build_r_by_atr_stretch_context_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return R summaries for ATR percentage and ATR expansion buckets."""

    return _bucket_rows(
        trade_context_rows,
        (
            *_bucket_specs(
                ("stock_atr14_pct",),
                (
                    ("atr_pct_below_2", lambda value: value < Decimal("2")),
                    ("atr_pct_2_to_4", lambda value: Decimal("2") <= value < Decimal("4")),
                    ("atr_pct_4_to_6", lambda value: Decimal("4") <= value < Decimal("6")),
                    ("atr_pct_above_6", lambda value: value >= Decimal("6")),
                ),
            ),
            *_bucket_specs(
                ("stock_atr14_change_5d_pct", "stock_atr14_change_10d_pct"),
                (
                    ("atr_change_negative_or_flat", lambda value: value <= 0),
                    ("atr_change_0_to_20", lambda value: 0 < value <= Decimal("20")),
                    ("atr_change_20_to_50", lambda value: Decimal("20") < value <= Decimal("50")),
                    ("atr_change_above_50", lambda value: value > Decimal("50")),
                ),
            ),
        ),
    )


def build_r_by_signal_candle_context_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return R summaries for signal candle severity buckets."""

    return _bucket_rows(
        trade_context_rows,
        (
            *_bucket_specs(
                (
                    "stock_signal_day_return_pct",
                    "stock_signal_intraday_return_pct",
                    "stock_signal_body_pct",
                ),
                (
                    ("positive", lambda value: value > 0),
                    ("zero_to_minus_2", lambda value: Decimal("-2") < value <= 0),
                    ("minus_2_to_minus_5", lambda value: Decimal("-5") < value <= Decimal("-2")),
                    ("below_minus_5", lambda value: value <= Decimal("-5")),
                ),
            ),
            *_bucket_specs(
                ("stock_signal_close_location_pct",),
                (
                    ("close_near_low_0_25", lambda value: 0 <= value < Decimal("25")),
                    ("close_mid_low_25_50", lambda value: Decimal("25") <= value < Decimal("50")),
                    ("close_mid_high_50_75", lambda value: Decimal("50") <= value < Decimal("75")),
                    ("close_near_high_75_100", lambda value: Decimal("75") <= value <= Decimal("100")),
                ),
            ),
            *_bucket_specs(
                ("stock_signal_range_pct",),
                (
                    ("range_below_2", lambda value: value < Decimal("2")),
                    ("range_2_to_4", lambda value: Decimal("2") <= value < Decimal("4")),
                    ("range_4_to_7", lambda value: Decimal("4") <= value < Decimal("7")),
                    ("range_above_7", lambda value: value >= Decimal("7")),
                ),
            ),
        ),
    )


def build_r_by_consecutive_down_closes_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return R summaries for consecutive down closes into signal date."""

    return _bucket_rows(
        trade_context_rows,
        _bucket_specs(
            ("stock_consecutive_down_closes",),
            (
                ("down_closes_0", lambda value: value == 0),
                ("down_closes_1", lambda value: value == 1),
                ("down_closes_2", lambda value: value == 2),
                ("down_closes_3", lambda value: value == 3),
                ("down_closes_4_or_more", lambda value: value >= 4),
            ),
        ),
    )


def build_r_by_fresh_low_context_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return R summaries for fresh lows and distance from rolling lows."""

    return _bucket_rows(
        trade_context_rows,
        (
            *_bucket_specs(
                ("stock_is_20d_low", "stock_is_60d_low", "stock_is_120d_low"),
                (
                    ("true", _is_true),
                    ("false", _is_false),
                ),
                convert=False,
            ),
            *_bucket_specs(
                (
                    "stock_close_vs_20d_low_pct",
                    "stock_close_vs_60d_low_pct",
                    "stock_close_vs_120d_low_pct",
                ),
                (
                    ("within_1_pct_of_low", lambda value: 0 <= value <= Decimal("1")),
                    ("1_to_3_pct_above_low", lambda value: Decimal("1") < value <= Decimal("3")),
                    ("3_to_7_pct_above_low", lambda value: Decimal("3") < value <= Decimal("7")),
                    ("more_than_7_pct_above_low", lambda value: value > Decimal("7")),
                ),
            ),
        ),
    )


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
    previous_close = close.shift(1)
    frame["signal_day_return_pct"] = ((close / previous_close) - 1) * 100
    frame["signal_intraday_return_pct"] = ((close / frame["open"]) - 1) * 100
    candle_range = frame["high"] - frame["low"]
    frame["signal_close_location_pct"] = ((close - frame["low"]) / candle_range) * 100
    frame.loc[candle_range == 0, "signal_close_location_pct"] = pd.NA
    frame["signal_range_pct"] = (candle_range / previous_close) * 100
    frame["signal_body_pct"] = ((close / frame["open"]) - 1) * 100
    frame["gap_from_prev_close_pct"] = ((frame["open"] / previous_close) - 1) * 100
    frame["return_1d_pct"] = frame["signal_day_return_pct"]
    frame["return_3d_pct"] = ((close / close.shift(3)) - 1) * 100
    frame["return_5d_pct"] = ((close / close.shift(5)) - 1) * 100
    frame["return_10d_pct"] = ((close / close.shift(10)) - 1) * 100
    frame["sma50"] = close.rolling(window=50, min_periods=50).mean()
    frame["sma200"] = close.rolling(window=200, min_periods=200).mean()
    frame["close_vs_sma50_pct"] = ((close / frame["sma50"]) - 1) * 100
    frame["close_vs_sma200_pct"] = ((close / frame["sma200"]) - 1) * 100
    frame["sma50_slope_20d_pct"] = ((frame["sma50"] / frame["sma50"].shift(20)) - 1) * 100
    frame["sma200_slope_20d_pct"] = ((frame["sma200"] / frame["sma200"].shift(20)) - 1) * 100
    frame["return_20d_pct"] = ((close / close.shift(20)) - 1) * 100
    frame["return_60d_pct"] = ((close / close.shift(60)) - 1) * 100
    frame["return_120d_pct"] = ((close / close.shift(120)) - 1) * 100
    frame["drawdown_20d_pct"] = ((close / close.rolling(window=20, min_periods=20).max()) - 1) * 100
    frame["drawdown_60d_pct"] = ((close / close.rolling(window=60, min_periods=60).max()) - 1) * 100
    frame["drawdown_120d_pct"] = ((close / close.rolling(window=120, min_periods=120).max()) - 1) * 100
    frame["atr14"] = atr(frame, 14)
    frame["atr14_pct"] = (frame["atr14"] / close) * 100
    frame["atr14_change_5d_pct"] = ((frame["atr14"] / frame["atr14"].shift(5)) - 1) * 100
    frame["atr14_change_10d_pct"] = ((frame["atr14"] / frame["atr14"].shift(10)) - 1) * 100
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
            "open",
            "high",
            "low",
            "close",
            "signal_day_return_pct",
            "signal_intraday_return_pct",
            "signal_close_location_pct",
            "signal_range_pct",
            "signal_body_pct",
            "gap_from_prev_close_pct",
            "return_1d_pct",
            "return_3d_pct",
            "return_5d_pct",
            "return_10d_pct",
            "sma50",
            "sma200",
            "close_vs_sma50_pct",
            "close_vs_sma200_pct",
            "sma50_slope_20d_pct",
            "sma200_slope_20d_pct",
            "return_20d_pct",
            "return_60d_pct",
            "return_120d_pct",
            "drawdown_20d_pct",
            "drawdown_60d_pct",
            "drawdown_120d_pct",
            "atr14",
            "atr14_pct",
            "atr14_change_5d_pct",
            "atr14_change_10d_pct",
            "consecutive_down_closes",
            "is_20d_low",
            "is_60d_low",
            "is_120d_low",
            "close_vs_20d_low_pct",
            "close_vs_60d_low_pct",
            "close_vs_120d_low_pct",
        )
    }


def _prefixed_context(prefix: str, context: dict[str, object]) -> dict[str, object]:
    """Return context feature names with stock/nifty report prefixes."""

    return {
        f"{prefix}_open": context.get("open"),
        f"{prefix}_high": context.get("high"),
        f"{prefix}_low": context.get("low"),
        f"{prefix}_close": context.get("close"),
        f"{prefix}_signal_day_return_pct": context.get("signal_day_return_pct"),
        f"{prefix}_signal_intraday_return_pct": context.get("signal_intraday_return_pct"),
        f"{prefix}_signal_close_location_pct": context.get("signal_close_location_pct"),
        f"{prefix}_signal_range_pct": context.get("signal_range_pct"),
        f"{prefix}_signal_body_pct": context.get("signal_body_pct"),
        f"{prefix}_gap_from_prev_close_pct": context.get("gap_from_prev_close_pct"),
        f"{prefix}_return_1d_pct": context.get("return_1d_pct"),
        f"{prefix}_return_3d_pct": context.get("return_3d_pct"),
        f"{prefix}_return_5d_pct": context.get("return_5d_pct"),
        f"{prefix}_return_10d_pct": context.get("return_10d_pct"),
        f"{prefix}_sma50": context.get("sma50"),
        f"{prefix}_sma200": context.get("sma200"),
        f"{prefix}_close_vs_sma50_pct": context.get("close_vs_sma50_pct"),
        f"{prefix}_close_vs_sma200_pct": context.get("close_vs_sma200_pct"),
        f"{prefix}_sma50_slope_20d_pct": context.get("sma50_slope_20d_pct"),
        f"{prefix}_sma200_slope_20d_pct": context.get("sma200_slope_20d_pct"),
        f"{prefix}_return_20d_pct": context.get("return_20d_pct"),
        f"{prefix}_return_60d_pct": context.get("return_60d_pct"),
        f"{prefix}_return_120d_pct": context.get("return_120d_pct"),
        f"{prefix}_drawdown_20d_pct": context.get("drawdown_20d_pct"),
        f"{prefix}_drawdown_60d_pct": context.get("drawdown_60d_pct"),
        f"{prefix}_drawdown_120d_pct": context.get("drawdown_120d_pct"),
        f"{prefix}_atr14": context.get("atr14"),
        f"{prefix}_atr14_pct": context.get("atr14_pct"),
        f"{prefix}_atr14_change_5d_pct": context.get("atr14_change_5d_pct"),
        f"{prefix}_atr14_change_10d_pct": context.get("atr14_change_10d_pct"),
        f"{prefix}_consecutive_down_closes": context.get("consecutive_down_closes"),
        f"{prefix}_is_20d_low": context.get("is_20d_low"),
        f"{prefix}_is_60d_low": context.get("is_60d_low"),
        f"{prefix}_is_120d_low": context.get("is_120d_low"),
        f"{prefix}_close_vs_20d_low_pct": context.get("close_vs_20d_low_pct"),
        f"{prefix}_close_vs_60d_low_pct": context.get("close_vs_60d_low_pct"),
        f"{prefix}_close_vs_120d_low_pct": context.get("close_vs_120d_low_pct"),
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


def _bucket_specs(
    contexts: tuple[str, ...],
    buckets: tuple[tuple[str, Any], ...],
    convert: bool = True,
) -> tuple[tuple[str, str, Any], ...]:
    """Return bucket specs for each context with shared bucket predicates."""

    specs = []
    for context in contexts:
        for bucket, predicate in buckets:
            if convert:
                specs.append(
                    (
                        context,
                        bucket,
                        lambda row, context=context, predicate=predicate: (
                            (value := _to_decimal(row.get(context))) is not None
                            and predicate(value)
                        ),
                    )
                )
            else:
                specs.append(
                    (
                        context,
                        bucket,
                        lambda row, context=context, predicate=predicate: predicate(
                            row.get(context)
                        ),
                    )
                )
    return tuple(specs)


def _between(
    value: object,
    lower: str,
    upper: str,
    lower_open: bool = False,
) -> bool:
    """Return whether value is in a Decimal interval ending at upper."""

    decimal = _to_decimal(value)
    if decimal is None:
        return False
    lower_decimal = Decimal(lower)
    upper_decimal = Decimal(upper)
    if lower_open:
        return lower_decimal < decimal <= upper_decimal
    return lower_decimal <= decimal <= upper_decimal


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


def _is_true(value: object) -> bool:
    """Return whether value behaves as a non-missing true boolean."""

    return value is not None and not pd.isna(value) and bool(value)


def _is_false(value: object) -> bool:
    """Return whether value behaves as a non-missing false boolean."""

    return value is not None and not pd.isna(value) and not bool(value)


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
