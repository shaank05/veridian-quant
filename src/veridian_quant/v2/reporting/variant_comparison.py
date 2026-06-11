"""Compare completed v2 strategy variant report folders.

This module reads existing CSV reports only. It does not run strategy logic,
mutate source reports, or recalculate backtest mechanics.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


BASE_COMPARISON_COLUMNS = [
    "variant_label",
    "strategy_name",
    "strategy_variant",
    "report_dir",
    "start_date",
    "end_date",
    "starting_equity",
    "ending_equity",
    "total_net_pnl",
    "total_return_pct",
    "cagr_pct",
    "max_drawdown_pct",
    "total_trades",
    "winning_trades",
    "losing_trades",
    "win_rate_pct",
    "gross_profit",
    "gross_loss",
    "profit_factor",
    "expectancy",
    "average_win",
    "average_loss",
    "average_net_pnl",
    "best_trade",
    "worst_trade",
    "average_holding_days",
    "total_signals",
    "total_rejected_signals",
    "symbols_count",
]

DERIVED_COMPARISON_COLUMNS = [
    "trades_per_year",
    "net_pnl_per_trade",
    "return_to_drawdown",
    "pnl_to_drawdown",
    "profit_factor_x_trade_count",
    "expectancy_x_trade_count",
    "stop_loss_trade_count",
    "stop_gap_trade_count",
    "stop_total_trade_count",
    "target_hit_trade_count",
    "target_gap_trade_count",
    "target_total_trade_count",
    "time_stop_trade_count",
    "stop_total_net_pnl",
    "target_total_net_pnl",
    "time_stop_net_pnl",
    "stop_damage_pct_of_gross_profit",
    "target_contribution_pct_of_total_profit",
    "positive_years",
    "negative_years",
    "flat_years",
    "best_year",
    "best_year_net_pnl",
    "worst_year",
    "worst_year_net_pnl",
    "yearly_pnl_std",
    "yearly_pnl_mean",
    "yearly_pnl_consistency_ratio",
    "positive_year_rate_pct",
    "symbols_profitable",
    "symbols_losing",
    "symbol_positive_rate_pct",
    "best_symbol",
    "best_symbol_net_pnl",
    "worst_symbol",
    "worst_symbol_net_pnl",
    "symbol_pnl_std",
    "symbol_concentration_top3_pct",
    "average_r",
    "average_winner_r",
    "average_loser_r",
    "best_r",
    "worst_r",
    "positive_r_rate_pct",
    "trades_with_r",
]

VARIANT_COMPARISON_COLUMNS = [
    *BASE_COMPARISON_COLUMNS,
    *DERIVED_COMPARISON_COLUMNS,
]

VARIANT_YEARLY_COLUMNS = [
    "variant_label",
    "strategy_variant",
    "year",
    "trades",
    "wins",
    "losses",
    "win_rate_pct",
    "gross_profit",
    "gross_loss",
    "net_pnl",
    "average_net_pnl",
    "best_trade",
    "worst_trade",
    "year_rank_by_net_pnl",
    "is_positive_year",
]

VARIANT_SYMBOL_COLUMNS = [
    "variant_label",
    "strategy_variant",
    "symbol",
    "trades",
    "wins",
    "losses",
    "win_rate_pct",
    "gross_profit",
    "gross_loss",
    "net_pnl",
    "average_net_pnl",
    "best_trade",
    "worst_trade",
    "average_holding_days",
    "symbol_rank_by_net_pnl",
    "is_profitable_symbol",
]

VARIANT_EXIT_REASON_COLUMNS = [
    "variant_label",
    "strategy_variant",
    "exit_reason",
    "trades",
    "wins",
    "losses",
    "win_rate_pct",
    "gross_profit",
    "gross_loss",
    "net_pnl",
    "average_net_pnl",
    "best_trade",
    "worst_trade",
]

VARIANT_REJECTION_COLUMNS = [
    "variant_label",
    "strategy_variant",
    "reason",
    "count",
    "rejection_pct_of_total_signals",
]

SCORECARD_BASE_COLUMNS = [
    "variant_label",
    "strategy_variant",
    "total_net_pnl",
    "max_drawdown_pct",
    "win_rate_pct",
    "profit_factor",
    "expectancy",
    "total_trades",
    "positive_year_rate_pct",
    "symbol_positive_rate_pct",
    "return_to_drawdown",
    "stop_damage_pct_of_gross_profit",
    "symbol_concentration_top3_pct",
]

SCORECARD_RANK_COLUMNS = [
    "rank_total_net_pnl",
    "rank_max_drawdown_pct",
    "rank_win_rate_pct",
    "rank_profit_factor",
    "rank_expectancy",
    "rank_positive_year_rate_pct",
    "rank_symbol_positive_rate_pct",
    "rank_return_to_drawdown",
    "rank_stop_damage_pct",
    "rank_symbol_concentration",
]

VARIANT_SCORECARD_COLUMNS = [
    *SCORECARD_BASE_COLUMNS,
    *SCORECARD_RANK_COLUMNS,
    "composite_rank_score",
    "composite_rank",
    "suggested_role",
]


@dataclass(frozen=True, slots=True)
class VariantReportInput:
    """Input report folder with an optional display label."""

    report_dir: Path
    variant_label: str | None = None


def compare_strategy_variant_reports(
    report_dirs: Mapping[str, str | Path] | Sequence[str | Path],
    output_dir: str | Path,
    variant_labels: Sequence[str] | None = None,
) -> dict[str, Path]:
    """Create side-by-side comparison CSVs for completed report folders."""

    inputs = _normalize_inputs(report_dirs, variant_labels)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    comparison_rows: list[dict[str, Any]] = []
    yearly_rows: list[dict[str, Any]] = []
    symbol_rows: list[dict[str, Any]] = []
    exit_reason_rows: list[dict[str, Any]] = []
    rejection_rows: list[dict[str, Any]] = []

    for report_input in inputs:
        report_dir = report_input.report_dir
        summary = _read_required_first_row(report_dir / "summary.csv")
        strategy_variant = _value(summary, "strategy_variant")
        label = report_input.variant_label or strategy_variant or report_dir.name

        yearly = _read_optional_csv(report_dir / "yearly_summary.csv")
        symbols = _read_optional_csv(report_dir / "symbol_summary.csv")
        exits = _read_optional_csv(report_dir / "exit_reason_summary.csv")
        rejections = _read_optional_csv(report_dir / "rejection_summary.csv")
        r_summary = _read_optional_csv(report_dir / "r_multiple_summary.csv")

        comparison_rows.append(
            _build_comparison_row(
                label=label,
                report_dir=report_dir,
                summary=summary,
                yearly=yearly,
                symbols=symbols,
                exits=exits,
                r_summary=r_summary,
            )
        )
        yearly_rows.extend(_yearly_rows(label, strategy_variant, yearly))
        symbol_rows.extend(_symbol_rows(label, strategy_variant, symbols))
        exit_reason_rows.extend(_prefixed_rows(label, strategy_variant, exits))
        rejection_rows.extend(
            _rejection_rows(
                label,
                strategy_variant,
                rejections,
                _number(summary, "total_signals"),
            )
        )

    comparison = pd.DataFrame(comparison_rows, columns=VARIANT_COMPARISON_COLUMNS)
    yearly_comparison = pd.DataFrame(yearly_rows, columns=VARIANT_YEARLY_COLUMNS)
    symbol_comparison = pd.DataFrame(symbol_rows, columns=VARIANT_SYMBOL_COLUMNS)
    exit_reason_comparison = pd.DataFrame(
        exit_reason_rows,
        columns=VARIANT_EXIT_REASON_COLUMNS,
    )
    rejection_comparison = pd.DataFrame(
        rejection_rows,
        columns=VARIANT_REJECTION_COLUMNS,
    )
    scorecard = _build_scorecard(comparison)

    outputs = {
        "variant_comparison": output_path / "variant_comparison.csv",
        "variant_yearly_comparison": output_path
        / "variant_yearly_comparison.csv",
        "variant_symbol_comparison": output_path
        / "variant_symbol_comparison.csv",
        "variant_exit_reason_comparison": output_path
        / "variant_exit_reason_comparison.csv",
        "variant_rejection_comparison": output_path
        / "variant_rejection_comparison.csv",
        "variant_scorecard": output_path / "variant_scorecard.csv",
    }

    comparison.to_csv(outputs["variant_comparison"], index=False)
    yearly_comparison.to_csv(outputs["variant_yearly_comparison"], index=False)
    symbol_comparison.to_csv(outputs["variant_symbol_comparison"], index=False)
    exit_reason_comparison.to_csv(
        outputs["variant_exit_reason_comparison"],
        index=False,
    )
    rejection_comparison.to_csv(outputs["variant_rejection_comparison"], index=False)
    scorecard.to_csv(outputs["variant_scorecard"], index=False)
    return outputs


def _normalize_inputs(
    report_dirs: Mapping[str, str | Path] | Sequence[str | Path],
    variant_labels: Sequence[str] | None,
) -> list[VariantReportInput]:
    if isinstance(report_dirs, Mapping):
        if variant_labels is not None:
            raise ValueError("variant_labels cannot be used with mapping inputs")
        return [
            VariantReportInput(Path(report_dir), str(label))
            for label, report_dir in report_dirs.items()
        ]

    if variant_labels is not None and len(variant_labels) != len(report_dirs):
        raise ValueError("variant_labels must match report_dirs length")

    return [
        VariantReportInput(
            Path(report_dir),
            None if variant_labels is None else variant_labels[index],
        )
        for index, report_dir in enumerate(report_dirs)
    ]


def _read_required_first_row(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required report file missing: {path}")
    frame = pd.read_csv(path)
    if frame.empty:
        raise ValueError(f"Required report file has no rows: {path}")
    return frame.iloc[0].to_dict()


def _read_optional_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _build_comparison_row(
    *,
    label: str,
    report_dir: Path,
    summary: dict[str, Any],
    yearly: pd.DataFrame,
    symbols: pd.DataFrame,
    exits: pd.DataFrame,
    r_summary: pd.DataFrame,
) -> dict[str, Any]:
    row = {column: _value(summary, column) for column in BASE_COMPARISON_COLUMNS}
    row["variant_label"] = label
    row["report_dir"] = str(report_dir)
    row.update(_trade_rate_metrics(summary))
    row.update(_exit_metrics(summary, exits))
    row.update(_year_metrics(yearly))
    row.update(_symbol_metrics(symbols))
    row.update(_r_metrics(r_summary))
    return row


def _trade_rate_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    total_trades = _number(summary, "total_trades")
    total_net_pnl = _number(summary, "total_net_pnl")
    total_return_pct = _number(summary, "total_return_pct")
    max_drawdown_pct = _number(summary, "max_drawdown_pct")
    profit_factor = _number(summary, "profit_factor")
    expectancy = _number(summary, "expectancy")
    years = _duration_years(_value(summary, "start_date"), _value(summary, "end_date"))

    return {
        "trades_per_year": _safe_div(total_trades, years),
        "net_pnl_per_trade": _safe_div(total_net_pnl, total_trades),
        "return_to_drawdown": _safe_div(total_return_pct, max_drawdown_pct),
        "pnl_to_drawdown": _safe_div(total_net_pnl, max_drawdown_pct),
        "profit_factor_x_trade_count": _safe_mul(profit_factor, total_trades),
        "expectancy_x_trade_count": _safe_mul(expectancy, total_trades),
    }


def _exit_metrics(summary: dict[str, Any], exits: pd.DataFrame) -> dict[str, Any]:
    gross_profit = _number(summary, "gross_profit")
    stop_loss_count = _exit_value(exits, "stop_loss_hit", "trades")
    stop_gap_count = _exit_value(exits, "stop_gap_hit", "trades")
    target_hit_count = _exit_value(exits, "target_hit", "trades")
    target_gap_count = _exit_value(exits, "target_gap_hit", "trades")
    time_stop_count = _exit_value(exits, "time_stop", "trades")
    stop_total_net_pnl = _safe_add(
        _exit_value(exits, "stop_loss_hit", "net_pnl"),
        _exit_value(exits, "stop_gap_hit", "net_pnl"),
    )
    target_total_net_pnl = _safe_add(
        _exit_value(exits, "target_hit", "net_pnl"),
        _exit_value(exits, "target_gap_hit", "net_pnl"),
    )
    time_stop_net_pnl = _exit_value(exits, "time_stop", "net_pnl")

    return {
        "stop_loss_trade_count": stop_loss_count,
        "stop_gap_trade_count": stop_gap_count,
        "stop_total_trade_count": _safe_add(stop_loss_count, stop_gap_count),
        "target_hit_trade_count": target_hit_count,
        "target_gap_trade_count": target_gap_count,
        "target_total_trade_count": _safe_add(target_hit_count, target_gap_count),
        "time_stop_trade_count": time_stop_count,
        "stop_total_net_pnl": stop_total_net_pnl,
        "target_total_net_pnl": target_total_net_pnl,
        "time_stop_net_pnl": time_stop_net_pnl,
        "stop_damage_pct_of_gross_profit": _safe_div(
            None if stop_total_net_pnl is None else abs(stop_total_net_pnl) * 100,
            gross_profit,
        ),
        "target_contribution_pct_of_total_profit": _safe_div(
            None if target_total_net_pnl is None else target_total_net_pnl * 100,
            gross_profit,
        ),
    }


def _year_metrics(yearly: pd.DataFrame) -> dict[str, Any]:
    if yearly.empty or "net_pnl" not in yearly:
        return {column: None for column in _year_metric_columns()}

    net_pnl = pd.to_numeric(yearly["net_pnl"], errors="coerce")
    positive = int((net_pnl > 0).sum())
    negative = int((net_pnl < 0).sum())
    flat = int((net_pnl == 0).sum())
    best_index = net_pnl.idxmax() if net_pnl.notna().any() else None
    worst_index = net_pnl.idxmin() if net_pnl.notna().any() else None
    std = _series_std(net_pnl)
    mean = _series_mean(net_pnl)

    return {
        "positive_years": positive,
        "negative_years": negative,
        "flat_years": flat,
        "best_year": None if best_index is None else yearly.loc[best_index, "year"],
        "best_year_net_pnl": None if best_index is None else net_pnl.loc[best_index],
        "worst_year": None if worst_index is None else yearly.loc[worst_index, "year"],
        "worst_year_net_pnl": None if worst_index is None else net_pnl.loc[worst_index],
        "yearly_pnl_std": std,
        "yearly_pnl_mean": mean,
        "yearly_pnl_consistency_ratio": _safe_div(mean, std),
        "positive_year_rate_pct": _safe_div(positive * 100, len(yearly)),
    }


def _symbol_metrics(symbols: pd.DataFrame) -> dict[str, Any]:
    if symbols.empty or "net_pnl" not in symbols:
        return {column: None for column in _symbol_metric_columns()}

    net_pnl = pd.to_numeric(symbols["net_pnl"], errors="coerce")
    positive = int((net_pnl > 0).sum())
    losing = int((net_pnl < 0).sum())
    best_index = net_pnl.idxmax() if net_pnl.notna().any() else None
    worst_index = net_pnl.idxmin() if net_pnl.notna().any() else None
    positive_pnl = net_pnl[net_pnl > 0].sort_values(ascending=False)

    return {
        "symbols_profitable": positive,
        "symbols_losing": losing,
        "symbol_positive_rate_pct": _safe_div(positive * 100, len(symbols)),
        "best_symbol": None
        if best_index is None
        else symbols.loc[best_index, "symbol"],
        "best_symbol_net_pnl": None if best_index is None else net_pnl.loc[best_index],
        "worst_symbol": None
        if worst_index is None
        else symbols.loc[worst_index, "symbol"],
        "worst_symbol_net_pnl": None
        if worst_index is None
        else net_pnl.loc[worst_index],
        "symbol_pnl_std": _series_std(net_pnl),
        "symbol_concentration_top3_pct": _safe_div(
            positive_pnl.head(3).sum() * 100,
            positive_pnl.sum(),
        ),
    }


def _r_metrics(r_summary: pd.DataFrame) -> dict[str, Any]:
    columns = [
        "average_r",
        "average_winner_r",
        "average_loser_r",
        "best_r",
        "worst_r",
        "positive_r_rate_pct",
        "trades_with_r",
    ]
    if r_summary.empty:
        return {column: None for column in columns}
    first = r_summary.iloc[0].to_dict()
    return {column: _value(first, column) for column in columns}


def _yearly_rows(
    label: str,
    strategy_variant: Any,
    yearly: pd.DataFrame,
) -> list[dict[str, Any]]:
    if yearly.empty:
        return []
    rows = _records_with_prefix(yearly, label, strategy_variant)
    ranked = _add_rank(rows, "net_pnl", "year_rank_by_net_pnl", ascending=False)
    for row in ranked:
        row["is_positive_year"] = _number(row, "net_pnl") is not None and (
            _number(row, "net_pnl") > 0
        )
    return [{column: row.get(column) for column in VARIANT_YEARLY_COLUMNS} for row in ranked]


def _symbol_rows(
    label: str,
    strategy_variant: Any,
    symbols: pd.DataFrame,
) -> list[dict[str, Any]]:
    if symbols.empty:
        return []
    rows = _records_with_prefix(symbols, label, strategy_variant)
    ranked = _add_rank(rows, "net_pnl", "symbol_rank_by_net_pnl", ascending=False)
    for row in ranked:
        row["is_profitable_symbol"] = _number(row, "net_pnl") is not None and (
            _number(row, "net_pnl") > 0
        )
    return [{column: row.get(column) for column in VARIANT_SYMBOL_COLUMNS} for row in ranked]


def _prefixed_rows(
    label: str,
    strategy_variant: Any,
    frame: pd.DataFrame,
) -> list[dict[str, Any]]:
    return [
        {column: row.get(column) for column in VARIANT_EXIT_REASON_COLUMNS}
        for row in _records_with_prefix(frame, label, strategy_variant)
    ]


def _rejection_rows(
    label: str,
    strategy_variant: Any,
    rejections: pd.DataFrame,
    total_signals: float | None,
) -> list[dict[str, Any]]:
    rows = _records_with_prefix(rejections, label, strategy_variant)
    for row in rows:
        row["rejection_pct_of_total_signals"] = _safe_div(
            _number(row, "count") * 100 if _number(row, "count") is not None else None,
            total_signals,
        )
    return [{column: row.get(column) for column in VARIANT_REJECTION_COLUMNS} for row in rows]


def _records_with_prefix(
    frame: pd.DataFrame,
    label: str,
    strategy_variant: Any,
) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    records = frame.to_dict("records")
    return [
        {
            "variant_label": label,
            "strategy_variant": strategy_variant,
            **record,
        }
        for record in records
    ]


def _add_rank(
    rows: list[dict[str, Any]],
    value_column: str,
    rank_column: str,
    *,
    ascending: bool,
) -> list[dict[str, Any]]:
    if not rows:
        return rows
    values = pd.Series([_number(row, value_column) for row in rows])
    ranks = values.rank(method="min", ascending=ascending, na_option="bottom")
    for index, row in enumerate(rows):
        row[rank_column] = int(ranks.iloc[index]) if pd.notna(ranks.iloc[index]) else None
    return rows


def _build_scorecard(comparison: pd.DataFrame) -> pd.DataFrame:
    scorecard = comparison[SCORECARD_BASE_COLUMNS].copy()
    rank_specs = {
        "rank_total_net_pnl": ("total_net_pnl", False),
        "rank_max_drawdown_pct": ("max_drawdown_pct", True),
        "rank_win_rate_pct": ("win_rate_pct", False),
        "rank_profit_factor": ("profit_factor", False),
        "rank_expectancy": ("expectancy", False),
        "rank_positive_year_rate_pct": ("positive_year_rate_pct", False),
        "rank_symbol_positive_rate_pct": ("symbol_positive_rate_pct", False),
        "rank_return_to_drawdown": ("return_to_drawdown", False),
        "rank_stop_damage_pct": ("stop_damage_pct_of_gross_profit", True),
        "rank_symbol_concentration": ("symbol_concentration_top3_pct", True),
    }
    for rank_column, (value_column, ascending) in rank_specs.items():
        scorecard[rank_column] = pd.to_numeric(
            scorecard[value_column],
            errors="coerce",
        ).rank(method="min", ascending=ascending)

    scorecard["composite_rank_score"] = scorecard[SCORECARD_RANK_COLUMNS].mean(
        axis=1,
        skipna=True,
    )
    scorecard["composite_rank"] = scorecard["composite_rank_score"].rank(
        method="min",
        ascending=True,
    )
    scorecard["suggested_role"] = [
        _suggested_role(row, scorecard) for _, row in scorecard.iterrows()
    ]
    return scorecard[VARIANT_SCORECARD_COLUMNS]


def _suggested_role(row: pd.Series, scorecard: pd.DataFrame) -> str:
    roles: list[str] = []
    total_trades = _series_value(row, "total_trades")
    profit_factor = _series_value(row, "profit_factor")
    total_net_pnl = _series_value(row, "total_net_pnl")
    max_drawdown_pct = _series_value(row, "max_drawdown_pct")
    composite_rank = _series_value(row, "composite_rank")

    high_profit_factor = profit_factor is not None and profit_factor >= 1.5
    weak_metrics = (
        total_net_pnl is not None
        and total_net_pnl <= 0
        or profit_factor is not None
        and profit_factor < 1
    )
    if total_trades is not None and total_trades < 60 and high_profit_factor:
        roles.append("high_conviction_candidate")
    if _is_best(scorecard, "total_net_pnl", total_net_pnl, higher=True):
        roles.append("pnl_leader")
    if (
        _is_best(scorecard, "max_drawdown_pct", max_drawdown_pct, higher=False)
        and high_profit_factor
    ):
        roles.append("risk_quality_leader")
    if (
        total_trades is not None
        and total_trades >= 60
        and high_profit_factor
        and composite_rank is not None
        and composite_rank <= 2
    ):
        roles.append("risk_quality_candidate")
    if (
        total_trades is not None
        and total_trades >= 60
        and not high_profit_factor
        and not weak_metrics
    ):
        roles.append("broad_filter_candidate")
    if not roles:
        roles.append("benchmark_or_reject")
    return "|".join(roles)


def _is_best(
    frame: pd.DataFrame,
    column: str,
    value: float | None,
    *,
    higher: bool,
) -> bool:
    if value is None:
        return False
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    if values.empty:
        return False
    best = values.max() if higher else values.min()
    return value == best


def _exit_value(frame: pd.DataFrame, exit_reason: str, column: str) -> float | None:
    if frame.empty or "exit_reason" not in frame or column not in frame:
        return None
    rows = frame[frame["exit_reason"] == exit_reason]
    if rows.empty:
        return None
    return _coerce_number(rows.iloc[0][column])


def _duration_years(start_date: Any, end_date: Any) -> float | None:
    start = pd.to_datetime(start_date, errors="coerce")
    end = pd.to_datetime(end_date, errors="coerce")
    if pd.isna(start) or pd.isna(end):
        return None
    days = (end - start).days
    if days <= 0:
        return None
    return days / 365.25


def _year_metric_columns() -> list[str]:
    return [
        "positive_years",
        "negative_years",
        "flat_years",
        "best_year",
        "best_year_net_pnl",
        "worst_year",
        "worst_year_net_pnl",
        "yearly_pnl_std",
        "yearly_pnl_mean",
        "yearly_pnl_consistency_ratio",
        "positive_year_rate_pct",
    ]


def _symbol_metric_columns() -> list[str]:
    return [
        "symbols_profitable",
        "symbols_losing",
        "symbol_positive_rate_pct",
        "best_symbol",
        "best_symbol_net_pnl",
        "worst_symbol",
        "worst_symbol_net_pnl",
        "symbol_pnl_std",
        "symbol_concentration_top3_pct",
    ]


def _series_std(series: pd.Series) -> float | None:
    value = series.std()
    return None if pd.isna(value) else float(value)


def _series_mean(series: pd.Series) -> float | None:
    value = series.mean()
    return None if pd.isna(value) else float(value)


def _value(row: Mapping[str, Any], column: str) -> Any:
    value = row.get(column)
    if pd.isna(value):
        return None
    return value


def _number(row: Mapping[str, Any], column: str) -> float | None:
    return _coerce_number(row.get(column))


def _series_value(row: pd.Series, column: str) -> float | None:
    return _coerce_number(row.get(column))


def _coerce_number(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_div(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _safe_mul(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left * right


def _safe_add(left: float | None, right: float | None) -> float | None:
    if left is None and right is None:
        return None
    return (left or 0) + (right or 0)
