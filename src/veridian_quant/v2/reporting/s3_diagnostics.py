"""S3 accepted-trade diagnostics and filter simulations.

These helpers summarize already-accepted S3 trades only. They do not change
signal generation, portfolio execution, sizing, exits, or realized PnL.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from statistics import median
from typing import Any, Callable

import pandas as pd


S3_STRATEGY_NAME = "S3_TREND_PULLBACK_CONTINUATION"

S3_FILTER_SIMULATION_COLUMNS = [
    "filter_name",
    "description",
    "kept_trades",
    "rejected_trades",
    "kept_net_pnl",
    "rejected_net_pnl",
    "delta_net_pnl_vs_baseline",
    "kept_profit_factor",
    "kept_win_rate_pct",
    "kept_average_net_pnl",
    "kept_average_r_multiple",
    "kept_median_r_multiple",
]
S3_FILTER_SIMULATION_BY_YEAR_COLUMNS = [
    "filter_name",
    "year",
    "kept_trades",
    "kept_net_pnl",
    "kept_profit_factor",
    "kept_average_r_multiple",
    "baseline_net_pnl",
    "delta_net_pnl_vs_baseline",
]
S3_CONTEXT_BUCKET_SUMMARY_COLUMNS = [
    "bucket_dimension",
    "bucket",
    "trades",
    "net_pnl",
    "profit_factor",
    "win_rate_pct",
    "average_net_pnl",
    "average_r_multiple",
    "median_r_multiple",
]
S3_FAILURE_AUDIT_BY_YEAR_COLUMNS = [
    "year",
    "trades",
    "net_pnl",
    "profit_factor",
    "win_rate_pct",
    "average_net_pnl",
    "average_r_multiple",
    "median_r_multiple",
    "target_hit_count",
    "stop_loss_count",
    "time_stop_count",
]
S3_FAILURE_AUDIT_BY_MONTH_COLUMNS = [
    "month",
    "trades",
    "net_pnl",
    "profit_factor",
    "win_rate_pct",
    "average_net_pnl",
    "average_r_multiple",
    "median_r_multiple",
]
S3_FAILURE_AUDIT_BY_EXIT_REASON_COLUMNS = [
    "exit_reason",
    "trades",
    "net_pnl",
    "average_net_pnl",
    "average_r_multiple",
    "median_r_multiple",
    "win_rate_pct",
]
S3_FAILURE_AUDIT_BY_SYMBOL_COLUMNS = [
    "symbol",
    "trades",
    "net_pnl",
    "profit_factor",
    "win_rate_pct",
    "average_net_pnl",
    "average_r_multiple",
    "median_r_multiple",
]


Predicate = Callable[[dict[str, object]], bool]


@dataclass(frozen=True)
class S3Filter:
    filter_name: str
    description: str
    predicate: Predicate
    required_fields: tuple[str, ...] = ()


def build_s3_filter_simulation_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return S3 accepted-trade filter simulations."""

    rows = _s3_trade_rows(trade_context_rows)
    if not rows:
        return []

    baseline = _performance_summary(rows)
    output = []
    for s3_filter in _available_filters(rows):
        kept, rejected = _split_rows(rows, s3_filter)
        kept_summary = _performance_summary(kept)
        rejected_summary = _performance_summary(rejected)
        output.append(
            {
                "filter_name": s3_filter.filter_name,
                "description": s3_filter.description,
                "kept_trades": len(kept),
                "rejected_trades": len(rejected),
                "kept_net_pnl": kept_summary["net_pnl"],
                "rejected_net_pnl": rejected_summary["net_pnl"],
                "delta_net_pnl_vs_baseline": kept_summary["net_pnl"]
                - baseline["net_pnl"],
                "kept_profit_factor": kept_summary["profit_factor"],
                "kept_win_rate_pct": kept_summary["win_rate_pct"],
                "kept_average_net_pnl": kept_summary["average_net_pnl"],
                "kept_average_r_multiple": kept_summary["average_r_multiple"],
                "kept_median_r_multiple": kept_summary["median_r_multiple"],
            }
        )
    return output


def build_s3_filter_simulation_by_year_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return S3 filter simulations grouped by trade exit year."""

    rows = _s3_trade_rows(trade_context_rows)
    if not rows:
        return []

    output = []
    for s3_filter in _available_filters(rows):
        grouped: dict[int, list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            row_year = _year(row.get("exit_date"))
            if row_year is not None:
                grouped[row_year].append(row)
        for year, group_rows in sorted(grouped.items()):
            kept, _ = _split_rows(group_rows, s3_filter)
            kept_summary = _performance_summary(kept)
            baseline_summary = _performance_summary(group_rows)
            output.append(
                {
                    "filter_name": s3_filter.filter_name,
                    "year": year,
                    "kept_trades": len(kept),
                    "kept_net_pnl": kept_summary["net_pnl"],
                    "kept_profit_factor": kept_summary["profit_factor"],
                    "kept_average_r_multiple": kept_summary["average_r_multiple"],
                    "baseline_net_pnl": baseline_summary["net_pnl"],
                    "delta_net_pnl_vs_baseline": kept_summary["net_pnl"]
                    - baseline_summary["net_pnl"],
                }
            )
    return output


def build_s3_context_bucket_summary_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return accepted S3 performance by signal metadata buckets."""

    rows = _s3_trade_rows(trade_context_rows)
    if not rows:
        return []

    output = []
    for dimension, bucket, predicate, required_fields in _bucket_specs():
        if not _has_any_field(rows, required_fields):
            continue
        bucket_rows = [row for row in rows if predicate(row)]
        if not bucket_rows:
            continue
        output.append(
            {
                "bucket_dimension": dimension,
                "bucket": bucket,
                "trades": len(bucket_rows),
                **_public_performance_summary(_performance_summary(bucket_rows)),
            }
        )
    return output


def build_s3_failure_audit_by_year_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return accepted S3 trade summaries grouped by entry year."""

    grouped: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in _s3_trade_rows(trade_context_rows):
        row_year = _year(row.get("entry_date"))
        if row_year is not None:
            grouped[row_year].append(row)

    output = []
    for year, rows in sorted(grouped.items()):
        summary = _performance_summary(rows)
        output.append(
            {
                "year": year,
                "trades": len(rows),
                **_public_performance_summary(summary),
                **_exit_reason_counts(rows),
            }
        )
    return output


def build_s3_failure_audit_by_month_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return accepted S3 trade summaries grouped by entry YYYY-MM."""

    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in _s3_trade_rows(trade_context_rows):
        row_date = _date(row.get("entry_date"))
        if row_date is not None:
            grouped[f"{row_date.year:04d}-{row_date.month:02d}"].append(row)

    return [
        {
            "month": month,
            "trades": len(rows),
            **_public_performance_summary(_performance_summary(rows)),
        }
        for month, rows in sorted(grouped.items())
    ]


def build_s3_failure_audit_by_exit_reason_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return accepted S3 trade summaries grouped by exit reason."""

    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in _s3_trade_rows(trade_context_rows):
        grouped[str(row.get("exit_reason") or "UNKNOWN")].append(row)

    return [
        {
            "exit_reason": exit_reason,
            "trades": len(rows),
            **{
                key: value
                for key, value in _public_performance_summary(
                    _performance_summary(rows)
                ).items()
                if key != "profit_factor"
            },
        }
        for exit_reason, rows in sorted(grouped.items())
    ]


def build_s3_failure_audit_by_symbol_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return accepted S3 trade summaries grouped by symbol."""

    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in _s3_trade_rows(trade_context_rows):
        grouped[str(row.get("symbol") or "UNKNOWN")].append(row)

    output = [
        {
            "symbol": symbol,
            "trades": len(rows),
            **_public_performance_summary(_performance_summary(rows)),
        }
        for symbol, rows in grouped.items()
    ]
    return sorted(output, key=lambda row: (-_sort_decimal(row["net_pnl"]), row["symbol"]))


def _filters() -> tuple[S3Filter, ...]:
    return (
        S3Filter(
            "exclude_below_sma50",
            "Exclude trades where close_vs_sma50_pct is below 0.",
            lambda row: not _lt_if_present(row, "close_vs_sma50_pct", "0"),
            ("close_vs_sma50_pct",),
        ),
        S3Filter(
            "close_vs_sma50_gte_minus_3",
            "Keep trades where close_vs_sma50_pct >= -3.",
            lambda row: _gte(row, "close_vs_sma50_pct", "-3"),
            ("close_vs_sma50_pct",),
        ),
        S3Filter(
            "close_vs_sma50_gte_minus_5",
            "Keep trades where close_vs_sma50_pct >= -5.",
            lambda row: _gte(row, "close_vs_sma50_pct", "-5"),
            ("close_vs_sma50_pct",),
        ),
        S3Filter(
            "sma50_slope_20d_gt_0_5",
            "Keep trades where sma50_slope_20d_pct > 0.5.",
            lambda row: _gt(row, "sma50_slope_20d_pct", "0.5"),
            ("sma50_slope_20d_pct",),
        ),
        S3Filter(
            "sma200_slope_20d_gt_1",
            "Keep trades where sma200_slope_20d_pct > 1.0.",
            lambda row: _gt(row, "sma200_slope_20d_pct", "1.0"),
            ("sma200_slope_20d_pct",),
        ),
        S3Filter(
            "exclude_drawdown_20d_below_minus_8",
            "Exclude trades where drawdown_20d_pct < -8.",
            lambda row: not _lt_if_present(row, "drawdown_20d_pct", "-8"),
            ("drawdown_20d_pct",),
        ),
        S3Filter(
            "exclude_drawdown_20d_below_minus_10",
            "Exclude trades where drawdown_20d_pct < -10.",
            lambda row: not _lt_if_present(row, "drawdown_20d_pct", "-10"),
            ("drawdown_20d_pct",),
        ),
        S3Filter(
            "drawdown_20d_between_minus_8_and_minus_3",
            "Keep trades where -8 <= drawdown_20d_pct <= -3.",
            lambda row: _between(row, "drawdown_20d_pct", "-8", "-3"),
            ("drawdown_20d_pct",),
        ),
        S3Filter(
            "exclude_return_5d_below_minus_6",
            "Exclude trades where return_5d_pct < -6.",
            lambda row: not _lt_if_present(row, "return_5d_pct", "-6"),
            ("return_5d_pct",),
        ),
        S3Filter(
            "exclude_return_5d_below_minus_8",
            "Exclude trades where return_5d_pct < -8.",
            lambda row: not _lt_if_present(row, "return_5d_pct", "-8"),
            ("return_5d_pct",),
        ),
        S3Filter(
            "exclude_atr14_pct_above_5",
            "Exclude trades where atr14_pct > 5.",
            lambda row: not _gt_if_present(row, "atr14_pct", "5"),
            ("atr14_pct",),
        ),
        S3Filter(
            "exclude_atr14_pct_above_6",
            "Exclude trades where atr14_pct > 6.",
            lambda row: not _gt_if_present(row, "atr14_pct", "6"),
            ("atr14_pct",),
        ),
        S3Filter(
            "exclude_atr14_change_5d_above_20",
            "Exclude trades where atr14_change_5d_pct > 20.",
            lambda row: not _gt_if_present(row, "atr14_change_5d_pct", "20"),
            ("atr14_change_5d_pct",),
        ),
        S3Filter(
            "exclude_atr14_change_5d_above_30",
            "Exclude trades where atr14_change_5d_pct > 30.",
            lambda row: not _gt_if_present(row, "atr14_change_5d_pct", "30"),
            ("atr14_change_5d_pct",),
        ),
        S3Filter(
            "exclude_close_vs_60d_low_below_5",
            "Exclude trades where close_vs_60d_low_pct < 5.",
            lambda row: not _lt_if_present(row, "close_vs_60d_low_pct", "5"),
            ("close_vs_60d_low_pct",),
        ),
        S3Filter(
            "exclude_close_vs_60d_low_below_10",
            "Exclude trades where close_vs_60d_low_pct < 10.",
            lambda row: not _lt_if_present(row, "close_vs_60d_low_pct", "10"),
            ("close_vs_60d_low_pct",),
        ),
        S3Filter(
            "exclude_is_60d_low",
            "Exclude trades where is_60d_low is true.",
            lambda row: not _is_true(row.get("is_60d_low")),
            ("is_60d_low",),
        ),
        S3Filter(
            "return_3d_gt_minus_5",
            "Keep trades where return_3d_pct > -5.",
            lambda row: _gt(row, "return_3d_pct", "-5"),
            ("return_3d_pct",),
        ),
        S3Filter(
            "signal_day_return_positive",
            "Keep trades where stock signal-day return is positive.",
            lambda row: _gt(row, "stock_signal_day_return_pct", "0"),
            ("stock_signal_day_return_pct",),
        ),
    )


def _available_filters(rows: list[dict[str, object]]) -> tuple[S3Filter, ...]:
    return tuple(
        s3_filter
        for s3_filter in _filters()
        if not s3_filter.required_fields
        or _has_any_field(rows, s3_filter.required_fields)
    )


def _bucket_specs() -> tuple[tuple[str, str, Predicate, tuple[str, ...]], ...]:
    return (
        *_range_specs(
            "close_vs_sma50_pct",
            "close_vs_sma50_pct",
            (
                ("below_minus_5", None, "-5"),
                ("minus_5_to_minus_3", "-5", "-3"),
                ("minus_3_to_0", "-3", "0"),
                ("0_to_5", "0", "5"),
                ("above_5", "5", None),
            ),
        ),
        *_range_specs(
            "close_vs_sma200_pct",
            "close_vs_sma200_pct",
            (
                ("below_minus_10", None, "-10"),
                ("minus_10_to_0", "-10", "0"),
                ("0_to_10", "0", "10"),
                ("above_10", "10", None),
            ),
        ),
        *_range_specs(
            "sma50_slope_20d_pct",
            "sma50_slope_20d_pct",
            (
                ("negative", None, "0"),
                ("0_to_0_5", "0", "0.5"),
                ("0_5_to_1", "0.5", "1"),
                ("above_1", "1", None),
            ),
        ),
        *_range_specs(
            "sma200_slope_20d_pct",
            "sma200_slope_20d_pct",
            (
                ("negative", None, "0"),
                ("0_to_1", "0", "1"),
                ("above_1", "1", None),
            ),
        ),
        *_range_specs(
            "return_3d_pct",
            "return_3d_pct",
            (
                ("below_minus_5", None, "-5"),
                ("minus_5_to_0", "-5", "0"),
                ("positive", "0", None),
            ),
        ),
        *_range_specs(
            "return_5d_pct",
            "return_5d_pct",
            (
                ("below_minus_8", None, "-8"),
                ("minus_8_to_minus_6", "-8", "-6"),
                ("minus_6_to_0", "-6", "0"),
                ("positive", "0", None),
            ),
        ),
        *_range_specs(
            "drawdown_20d_pct",
            "drawdown_20d_pct",
            (
                ("below_minus_10", None, "-10"),
                ("minus_10_to_minus_8", "-10", "-8"),
                ("minus_8_to_minus_3", "-8", "-3"),
                ("above_minus_3", "-3", None),
            ),
        ),
        *_range_specs(
            "drawdown_60d_pct",
            "drawdown_60d_pct",
            (
                ("below_minus_20", None, "-20"),
                ("minus_20_to_minus_10", "-20", "-10"),
                ("minus_10_to_0", "-10", "0"),
            ),
        ),
        *_range_specs(
            "close_vs_20d_high_pct",
            "close_vs_20d_high_pct",
            (
                ("below_minus_10", None, "-10"),
                ("minus_10_to_minus_5", "-10", "-5"),
                ("minus_5_to_0", "-5", "0"),
            ),
        ),
        *_range_specs(
            "close_vs_60d_low_pct",
            "close_vs_60d_low_pct",
            (
                ("below_5", None, "5"),
                ("5_to_10", "5", "10"),
                ("above_10", "10", None),
            ),
        ),
        *_boolean_specs("is_60d_low", "is_60d_low"),
        *_range_specs(
            "atr14_pct",
            "atr14_pct",
            (
                ("below_5", None, "5"),
                ("5_to_6", "5", "6"),
                ("above_6", "6", None),
            ),
        ),
        *_range_specs(
            "atr14_change_5d_pct",
            "atr14_change_5d_pct",
            (
                ("negative_or_flat", None, "0"),
                ("0_to_20", "0", "20"),
                ("20_to_30", "20", "30"),
                ("above_30", "30", None),
            ),
        ),
    )


def _s3_trade_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [_normalized_s3_row(row) for row in rows if _is_s3_row(row)]


def _normalized_s3_row(row: dict[str, object]) -> dict[str, object]:
    normalized = dict(row)
    for field in (
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
    ):
        if _is_missing(normalized.get(field)):
            prefixed = normalized.get(f"stock_{field}")
            if not _is_missing(prefixed):
                normalized[field] = prefixed
    return normalized


def _is_s3_row(row: dict[str, object]) -> bool:
    return (
        row.get("strategy_name") == S3_STRATEGY_NAME
        or row.get("strategy_family") == S3_STRATEGY_NAME
    )


def _split_rows(
    rows: list[dict[str, object]],
    s3_filter: S3Filter,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    kept = []
    rejected = []
    for row in rows:
        if s3_filter.predicate(row):
            kept.append(row)
        else:
            rejected.append(row)
    return kept, rejected


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
        "profit_factor": None if gross_loss == 0 else gross_profit / abs(gross_loss),
        "win_rate_pct": _ratio_pct(len(winners), len(pnls)),
        "average_net_pnl": _average(pnls),
        "average_r_multiple": _average(r_values),
        "median_r_multiple": _median(r_values),
    }


def _public_performance_summary(summary: dict[str, object]) -> dict[str, object]:
    return {
        "net_pnl": summary["net_pnl"],
        "profit_factor": summary["profit_factor"],
        "win_rate_pct": summary["win_rate_pct"],
        "average_net_pnl": summary["average_net_pnl"],
        "average_r_multiple": summary["average_r_multiple"],
        "median_r_multiple": summary["median_r_multiple"],
    }


def _exit_reason_counts(rows: list[dict[str, object]]) -> dict[str, int]:
    counts = defaultdict(int)
    for row in rows:
        counts[str(row.get("exit_reason") or "UNKNOWN")] += 1
    return {
        "target_hit_count": counts["target_hit"] + counts["target_gap_hit"],
        "stop_loss_count": counts["stop_loss_hit"] + counts["stop_gap_hit"],
        "time_stop_count": counts["time_stop"],
    }


def _range_specs(
    dimension: str,
    field: str,
    ranges: tuple[tuple[str, str | None, str | None], ...],
) -> tuple[tuple[str, str, Predicate, tuple[str, ...]], ...]:
    return tuple(
        (
            dimension,
            bucket,
            lambda row, field=field, lower=lower, upper=upper: _in_range(
                row.get(field),
                lower,
                upper,
            ),
            (field,),
        )
        for bucket, lower, upper in ranges
    )


def _boolean_specs(
    dimension: str,
    field: str,
) -> tuple[tuple[str, str, Predicate, tuple[str, ...]], ...]:
    return (
        (dimension, "true", lambda row, field=field: _is_true(row.get(field)), (field,)),
        (dimension, "false", lambda row, field=field: _is_false(row.get(field)), (field,)),
    )


def _in_range(value: object, lower: str | None, upper: str | None) -> bool:
    decimal = _to_decimal(value)
    if decimal is None:
        return False
    if lower is not None and decimal < Decimal(lower):
        return False
    if upper is not None and decimal > Decimal(upper):
        return False
    if lower is None and upper is not None:
        return decimal <= Decimal(upper)
    if lower is not None and upper is None:
        return decimal >= Decimal(lower)
    return True


def _gt(row: dict[str, object], field: str, threshold: str) -> bool:
    value = _to_decimal(row.get(field))
    return value is not None and value > Decimal(threshold)


def _gte(row: dict[str, object], field: str, threshold: str) -> bool:
    value = _to_decimal(row.get(field))
    return value is not None and value >= Decimal(threshold)


def _between(row: dict[str, object], field: str, lower: str, upper: str) -> bool:
    value = _to_decimal(row.get(field))
    return value is not None and Decimal(lower) <= value <= Decimal(upper)


def _gt_if_present(row: dict[str, object], field: str, threshold: str) -> bool:
    value = _to_decimal(row.get(field))
    return value is not None and value > Decimal(threshold)


def _lt_if_present(row: dict[str, object], field: str, threshold: str) -> bool:
    value = _to_decimal(row.get(field))
    return value is not None and value < Decimal(threshold)


def _has_any_field(
    rows: list[dict[str, object]],
    fields: tuple[str, ...],
) -> bool:
    return any(not _is_missing(row.get(field)) for row in rows for field in fields)


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
