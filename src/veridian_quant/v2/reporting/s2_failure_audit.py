"""S2 2025 failure-audit diagnostics for completed accepted trades.

These helpers are diagnostic only. They summarize already-accepted S2 trades
using entry_date as the period basis so comparisons align with trade selection
timing, and they do not alter signals, filters, ranking, entries, exits, sizing,
or PnL.
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from statistics import median
from typing import Any, Callable

import pandas as pd

from veridian_quant.v2.reporting.s2_markov_filter_simulation import (
    S2_STRATEGY_NAME,
    parse_state_label,
)


S2_FAILURE_AUDIT_BY_YEAR_COLUMNS = [
    "year",
    "trades",
    "net_pnl",
    "avg_net_pnl",
    "win_rate_pct",
    "avg_r",
    "median_r",
    "profit_factor",
    "max_single_trade_loss",
    "stop_loss_trades",
    "stop_gap_trades",
    "target_hit_trades",
    "time_stop_trades",
]
S2_FAILURE_AUDIT_BY_MONTH_COLUMNS = [
    "year",
    "month",
    "trades",
    "net_pnl",
    "avg_net_pnl",
    "win_rate_pct",
    "avg_r",
    "median_r",
    "profit_factor",
    "cumulative_year_pnl",
]
S2_FAILURE_AUDIT_COMPARISON_COLUMNS = [
    "bucket_type",
    "bucket",
    "pre_target_trades",
    "pre_target_net_pnl",
    "pre_target_avg_net_pnl",
    "pre_target_win_rate_pct",
    "pre_target_avg_r",
    "pre_target_median_r",
    "pre_target_profit_factor",
    "target_year",
    "target_trades",
    "target_net_pnl",
    "target_avg_net_pnl",
    "target_win_rate_pct",
    "target_avg_r",
    "target_median_r",
    "target_profit_factor",
    "delta_net_pnl",
    "delta_avg_r",
    "failure_score",
    "weighted_failure_score",
]
S2_FAILURE_AUDIT_STATE_COMPONENT_COLUMNS = [
    "component_type",
    "component_value",
    *S2_FAILURE_AUDIT_COMPARISON_COLUMNS,
]


ContextPredicate = Callable[[dict[str, object]], bool]


def build_s2_failure_audit_by_year_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return accepted S2 trade summaries grouped by entry year."""

    grouped: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in _s2_trade_rows(trade_context_rows):
        row_year = _year(row.get("entry_date"))
        if row_year is not None:
            grouped[row_year].append(row)

    return [
        {
            "year": year,
            **_year_summary(rows),
        }
        for year, rows in sorted(grouped.items())
    ]


def build_s2_failure_audit_by_month_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return accepted S2 trade summaries grouped by entry year-month."""

    grouped: dict[tuple[int, int], list[dict[str, object]]] = defaultdict(list)
    for row in _s2_trade_rows(trade_context_rows):
        row_date = _date(row.get("entry_date"))
        if row_date is not None:
            grouped[(row_date.year, row_date.month)].append(row)

    cumulative_by_year: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    output = []
    for (year, month), rows in sorted(grouped.items()):
        summary = _performance_summary(rows)
        cumulative_by_year[year] += summary["net_pnl"]
        output.append(
            {
                "year": year,
                "month": month,
                "trades": len(rows),
                "net_pnl": summary["net_pnl"],
                "avg_net_pnl": summary["avg_net_pnl"],
                "win_rate_pct": summary["win_rate_pct"],
                "avg_r": summary["avg_r"],
                "median_r": summary["median_r"],
                "profit_factor": summary["profit_factor"],
                "cumulative_year_pnl": cumulative_by_year[year],
            }
        )
    return output


def build_s2_failure_audit_by_state_label_rows(
    trade_context_rows: list[dict[str, object]],
    target_year: int = 2025,
) -> list[dict[str, object]]:
    """Return pre-target vs target-year comparison by full Markov state label."""

    return _comparison_rows(
        _s2_trade_rows(trade_context_rows),
        "state_label",
        lambda row: str(row.get("state_label") or "UNKNOWN"),
        target_year,
    )


def build_s2_failure_audit_by_state_component_rows(
    trade_context_rows: list[dict[str, object]],
    target_year: int = 2025,
) -> list[dict[str, object]]:
    """Return pre-target vs target-year comparison for each state component."""

    rows = _s2_trade_rows(trade_context_rows)
    output = []
    for component_type in ("ret_state", "vol_state", "dd_state", "low_state"):
        for row in _comparison_rows(
            rows,
            component_type,
            lambda source, component_type=component_type: str(
                source.get(component_type) or "UNKNOWN"
            ),
            target_year,
        ):
            output.append(
                {
                    "component_type": component_type,
                    "component_value": row["bucket"],
                    **row,
                }
            )
    return sorted(
        output,
        key=lambda row: (
            -_sort_decimal(row["weighted_failure_score"]),
            row["component_type"],
            row["component_value"],
        ),
    )


def build_s2_failure_audit_by_exit_reason_rows(
    trade_context_rows: list[dict[str, object]],
    target_year: int = 2025,
) -> list[dict[str, object]]:
    """Return pre-target vs target-year comparison by exit reason."""

    return _comparison_rows(
        _s2_trade_rows(trade_context_rows),
        "exit_reason",
        lambda row: str(row.get("exit_reason") or "UNKNOWN"),
        target_year,
    )


def build_s2_failure_audit_by_symbol_rows(
    trade_context_rows: list[dict[str, object]],
    target_year: int = 2025,
) -> list[dict[str, object]]:
    """Return pre-target vs target-year comparison by symbol."""

    rows = _comparison_rows(
        _s2_trade_rows(trade_context_rows),
        "symbol",
        lambda row: str(row.get("symbol") or "UNKNOWN"),
        target_year,
    )
    return sorted(
        rows,
        key=lambda row: (
            -_sort_decimal(row["weighted_failure_score"]),
            _sort_decimal(row["target_net_pnl"]),
            row["bucket"],
        ),
    )


def build_s2_failure_audit_context_comparison_rows(
    trade_context_rows: list[dict[str, object]],
    target_year: int = 2025,
) -> list[dict[str, object]]:
    """Return pre-target vs target-year comparison for available context buckets."""

    rows = _s2_trade_rows(trade_context_rows)
    output = []
    for bucket_type, bucket, predicate, required_columns in _context_bucket_specs():
        if not _has_any_required_column(rows, required_columns):
            continue
        bucket_rows = [row for row in rows if predicate(row)]
        if not bucket_rows:
            continue
        output.append(_comparison_row(bucket_type, bucket, bucket_rows, target_year))
    return sorted(
        output,
        key=lambda row: (
            -_sort_decimal(row["weighted_failure_score"]),
            row["bucket_type"],
            row["bucket"],
        ),
    )


def _s2_trade_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows = []
    has_state_metadata = False
    for row in trade_context_rows:
        if not _is_s2_row(row):
            continue
        if not _is_missing(row.get("state_label")):
            has_state_metadata = True
        rows.append({**row, **parse_state_label(row.get("state_label"))})
    return rows if has_state_metadata else []


def _is_s2_row(row: dict[str, object]) -> bool:
    return (
        row.get("strategy_name") == S2_STRATEGY_NAME
        or row.get("strategy_family") == S2_STRATEGY_NAME
    )


def _comparison_rows(
    rows: list[dict[str, object]],
    bucket_type: str,
    bucket_func: Callable[[dict[str, object]], str],
    target_year: int,
) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[bucket_func(row)].append(row)

    output = [
        _comparison_row(bucket_type, bucket, bucket_rows, target_year)
        for bucket, bucket_rows in grouped.items()
    ]
    return sorted(
        output,
        key=lambda row: (
            -_sort_decimal(row["weighted_failure_score"]),
            row["bucket"],
        ),
    )


def _comparison_row(
    bucket_type: str,
    bucket: str,
    rows: list[dict[str, object]],
    target_year: int,
) -> dict[str, object]:
    pre_target = []
    target = []
    for row in rows:
        row_year = _year(row.get("entry_date"))
        if row_year is None:
            continue
        if row_year < target_year:
            pre_target.append(row)
        elif row_year == target_year:
            target.append(row)

    pre_summary = _performance_summary(pre_target)
    target_summary = _performance_summary(target)
    delta_avg_r = _subtract(target_summary["avg_r"], pre_summary["avg_r"])
    failure_score = _failure_score(pre_summary["avg_r"], target_summary["avg_r"])
    return {
        "bucket_type": bucket_type,
        "bucket": bucket,
        "pre_target_trades": len(pre_target),
        "pre_target_net_pnl": pre_summary["net_pnl"],
        "pre_target_avg_net_pnl": pre_summary["avg_net_pnl"],
        "pre_target_win_rate_pct": pre_summary["win_rate_pct"],
        "pre_target_avg_r": pre_summary["avg_r"],
        "pre_target_median_r": pre_summary["median_r"],
        "pre_target_profit_factor": pre_summary["profit_factor"],
        "target_year": target_year,
        "target_trades": len(target),
        "target_net_pnl": target_summary["net_pnl"],
        "target_avg_net_pnl": target_summary["avg_net_pnl"],
        "target_win_rate_pct": target_summary["win_rate_pct"],
        "target_avg_r": target_summary["avg_r"],
        "target_median_r": target_summary["median_r"],
        "target_profit_factor": target_summary["profit_factor"],
        "delta_net_pnl": target_summary["net_pnl"] - pre_summary["net_pnl"],
        "delta_avg_r": delta_avg_r,
        "failure_score": failure_score,
        "weighted_failure_score": failure_score
        * (Decimal(min(len(target), 30)) / Decimal("30")),
    }


def _year_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    summary = _performance_summary(rows)
    exit_reason_counts = defaultdict(int)
    for row in rows:
        exit_reason_counts[str(row.get("exit_reason") or "UNKNOWN")] += 1
    return {
        "trades": len(rows),
        "net_pnl": summary["net_pnl"],
        "avg_net_pnl": summary["avg_net_pnl"],
        "win_rate_pct": summary["win_rate_pct"],
        "avg_r": summary["avg_r"],
        "median_r": summary["median_r"],
        "profit_factor": summary["profit_factor"],
        "max_single_trade_loss": summary["max_single_trade_loss"],
        "stop_loss_trades": exit_reason_counts["stop_loss_hit"],
        "stop_gap_trades": exit_reason_counts["stop_gap_hit"],
        "target_hit_trades": exit_reason_counts["target_hit"],
        "time_stop_trades": exit_reason_counts["time_stop"],
    }


def _performance_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    pnls = tuple(
        value
        for row in rows
        if (value := _to_decimal(row.get("net_pnl"))) is not None
    )
    r_values = tuple(
        value
        for row in rows
        if (value := _to_decimal(row.get("r_multiple"))) is not None
    )
    winners = tuple(value for value in pnls if value > 0)
    losers = tuple(value for value in pnls if value < 0)
    gross_profit = sum(winners, Decimal("0"))
    gross_loss = sum(losers, Decimal("0"))
    return {
        "net_pnl": sum(pnls, Decimal("0")),
        "avg_net_pnl": _average(pnls),
        "win_rate_pct": _ratio_pct(len(winners), len(pnls)),
        "avg_r": _average(r_values),
        "median_r": _median(r_values),
        "profit_factor": None if gross_loss == 0 else gross_profit / abs(gross_loss),
        "max_single_trade_loss": min(losers) if losers else Decimal("0"),
    }


def _context_bucket_specs(
) -> tuple[tuple[str, str, ContextPredicate, tuple[str, ...]], ...]:
    return (
        *_signed_specs("stock_above_sma50", "stock_close_vs_sma50_pct"),
        *_signed_specs("stock_above_sma200", "stock_close_vs_sma200_pct"),
        *_signed_specs("stock_sma50_slope_positive", "stock_sma50_slope_20d_pct"),
        *_signed_specs("stock_sma200_slope_positive", "stock_sma200_slope_20d_pct"),
        *_signed_specs("nifty_above_sma50", "nifty_close_vs_sma50_pct"),
        *_signed_specs("nifty_above_sma200", "nifty_close_vs_sma200_pct"),
        *_signed_specs("nifty_sma50_slope_positive", "nifty_sma50_slope_20d_pct"),
        *_signed_specs("nifty_sma200_slope_positive", "nifty_sma200_slope_20d_pct"),
        *_signed_specs(
            "relative_strength_20d_positive",
            "relative_strength_20d_vs_nifty",
        ),
        *_signed_specs(
            "relative_strength_60d_positive",
            "relative_strength_60d_vs_nifty",
        ),
        *_signed_specs(
            "relative_strength_120d_positive",
            "relative_strength_120d_vs_nifty",
        ),
        *_boolean_specs("fresh_20d_low", "stock_is_20d_low"),
        *_boolean_specs("fresh_60d_low", "stock_is_60d_low"),
        *_boolean_specs("fresh_120d_low", "stock_is_120d_low"),
        *_range_specs(
            "atr_stretch_bucket",
            "stock_atr14_pct",
            (
                ("atr_pct_below_2", None, "2"),
                ("atr_pct_2_to_4", "2", "4"),
                ("atr_pct_4_to_6", "4", "6"),
                ("atr_pct_above_6", "6", None),
            ),
        ),
        *_range_specs(
            "drawdown_depth_bucket",
            "stock_drawdown_60d_pct",
            (
                ("drawdown_0_to_minus_5", "-5", "0"),
                ("drawdown_minus_5_to_minus_10", "-10", "-5"),
                ("drawdown_minus_10_to_minus_20", "-20", "-10"),
                ("drawdown_below_minus_20", None, "-20"),
            ),
        ),
        *_range_specs(
            "consecutive_down_closes_bucket",
            "stock_consecutive_down_closes",
            (
                ("down_closes_0", "0", "0"),
                ("down_closes_1", "1", "1"),
                ("down_closes_2", "2", "2"),
                ("down_closes_3", "3", "3"),
                ("down_closes_4_or_more", "4", None),
            ),
        ),
        *_range_specs(
            "signal_candle_bucket",
            "stock_signal_day_return_pct",
            (
                ("positive", "0", None),
                ("zero_to_minus_2", "-2", "0"),
                ("minus_2_to_minus_5", "-5", "-2"),
                ("below_minus_5", None, "-5"),
            ),
        ),
        *_range_specs(
            "pre_signal_return_bucket",
            "stock_return_5d_pct",
            (
                ("return_positive", "0", None),
                ("return_0_to_minus_3", "-3", "0"),
                ("return_minus_3_to_minus_7", "-7", "-3"),
                ("return_below_minus_7", None, "-7"),
            ),
        ),
    )


def _signed_specs(
    bucket_type: str,
    column: str,
) -> tuple[tuple[str, str, ContextPredicate, tuple[str, ...]], ...]:
    return (
        (
            bucket_type,
            "true",
            lambda row, column=column: _to_decimal(row.get(column)) is not None
            and _to_decimal(row.get(column)) > 0,
            (column,),
        ),
        (
            bucket_type,
            "false",
            lambda row, column=column: _to_decimal(row.get(column)) is not None
            and _to_decimal(row.get(column)) <= 0,
            (column,),
        ),
    )


def _boolean_specs(
    bucket_type: str,
    column: str,
) -> tuple[tuple[str, str, ContextPredicate, tuple[str, ...]], ...]:
    return (
        (bucket_type, "true", lambda row, column=column: _is_true(row.get(column)), (column,)),
        (bucket_type, "false", lambda row, column=column: _is_false(row.get(column)), (column,)),
    )


def _range_specs(
    bucket_type: str,
    column: str,
    ranges: tuple[tuple[str, str | None, str | None], ...],
) -> tuple[tuple[str, str, ContextPredicate, tuple[str, ...]], ...]:
    return tuple(
        (
            bucket_type,
            bucket,
            lambda row, column=column, lower=lower, upper=upper: _in_range(
                row.get(column),
                lower,
                upper,
            ),
            (column,),
        )
        for bucket, lower, upper in ranges
    )


def _in_range(value: object, lower: str | None, upper: str | None) -> bool:
    decimal = _to_decimal(value)
    if decimal is None:
        return False
    if lower is not None and upper == lower:
        return decimal == Decimal(lower)
    if lower is not None and decimal < Decimal(lower):
        return False
    if upper is not None and decimal > Decimal(upper):
        return False
    if lower is None and upper is not None:
        return decimal <= Decimal(upper)
    if lower is not None and upper is None:
        return decimal >= Decimal(lower)
    return True


def _has_any_required_column(
    rows: list[dict[str, object]],
    columns: tuple[str, ...],
) -> bool:
    return any(
        column in row and not _is_missing(row.get(column))
        for row in rows
        for column in columns
    )


def _failure_score(pre_avg_r: object, target_avg_r: object) -> Decimal:
    pre = _to_decimal(pre_avg_r) or Decimal("0")
    target = _to_decimal(target_avg_r) or Decimal("0")
    return max(Decimal("0"), pre) - target


def _average(values: tuple[Decimal, ...]) -> Decimal | None:
    if not values:
        return None
    return sum(values, Decimal("0")) / Decimal(len(values))


def _median(values: tuple[Decimal, ...]) -> Decimal | None:
    if not values:
        return None
    return Decimal(str(median(values)))


def _ratio_pct(numerator: int, denominator: int) -> Decimal | None:
    if denominator <= 0:
        return None
    return (Decimal(numerator) / Decimal(denominator)) * Decimal("100")


def _subtract(left: object, right: object) -> Decimal | None:
    left_decimal = _to_decimal(left)
    right_decimal = _to_decimal(right)
    if left_decimal is None or right_decimal is None:
        return None
    return left_decimal - right_decimal


def _to_decimal(value: Any) -> Decimal | None:
    if _is_missing(value):
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _year(value: object) -> int | None:
    row_date = _date(value)
    return row_date.year if row_date is not None else None


def _date(value: object) -> date | None:
    if _is_missing(value):
        return None
    if isinstance(value, date):
        return value
    try:
        parsed = pd.to_datetime(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(parsed):
        return None
    return parsed.date()


def _is_true(value: object) -> bool:
    if _is_missing(value):
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return bool(value)


def _is_false(value: object) -> bool:
    if _is_missing(value):
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"false", "0", "no"}
    return not bool(value)


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _sort_decimal(value: object) -> Decimal:
    decimal = _to_decimal(value)
    return decimal if decimal is not None else Decimal("0")
