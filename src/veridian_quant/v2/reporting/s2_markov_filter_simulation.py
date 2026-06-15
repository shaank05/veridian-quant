"""S2 Markov-specific completed-trade filter simulations.

These helpers are diagnostic only. They evaluate hypothetical Markov metadata
rules against already-accepted S2 trades and do not alter signal generation,
portfolio execution, or backtest accounting.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from statistics import median
from typing import Any, Callable

import pandas as pd


S2_STRATEGY_NAME = "S2_MARKOV_STATE_TRANSITION"

S2_MARKOV_FILTER_SIMULATION_COLUMNS = [
    "filter_name",
    "filter_description",
    "kept_trades",
    "rejected_trades",
    "baseline_trades",
    "kept_net_pnl",
    "rejected_net_pnl",
    "baseline_net_pnl",
    "pnl_delta_vs_baseline",
    "kept_gross_profit",
    "kept_gross_loss",
    "kept_profit_factor",
    "kept_win_rate_pct",
    "kept_average_net_pnl",
    "kept_average_r_multiple",
    "kept_median_r_multiple",
    "rejected_average_r_multiple",
    "rejected_median_r_multiple",
]
S2_MARKOV_FILTER_SIMULATION_BY_YEAR_COLUMNS = [
    "filter_name",
    "year",
    "kept_trades",
    "rejected_trades",
    "kept_net_pnl",
    "rejected_net_pnl",
    "kept_profit_factor",
    "kept_win_rate_pct",
    "kept_average_r_multiple",
    "kept_median_r_multiple",
]
S2_MARKOV_FILTER_SIMULATION_BY_SYMBOL_COLUMNS = [
    "filter_name",
    "symbol",
    "kept_trades",
    "rejected_trades",
    "kept_net_pnl",
    "rejected_net_pnl",
    "kept_profit_factor",
    "kept_win_rate_pct",
    "kept_average_r_multiple",
    "kept_median_r_multiple",
]
S2_MARKOV_FILTER_SIMULATION_REJECTED_TRADES_COLUMNS = [
    "filter_name",
    "trade_id",
    "symbol",
    "entry_date",
    "exit_date",
    "net_pnl",
    "r_multiple",
    "exit_reason",
    "state_label",
    "ret_state",
    "vol_state",
    "dd_state",
    "low_state",
    "state_observation_count",
    "positive_transition_probability",
    "average_forward_return_pct",
    "median_forward_return_pct",
    "current_5d_return_pct",
    "current_atr_pct",
    "current_drawdown_60d_pct",
    "current_close_vs_60d_low_pct",
]
S2_MARKOV_STATE_COMPONENT_SUMMARY_COLUMNS = [
    "component_type",
    "component_bucket",
    "trades",
    "net_pnl",
    "gross_profit",
    "gross_loss",
    "profit_factor",
    "win_rate_pct",
    "average_r_multiple",
    "median_r_multiple",
]
S2_MARKOV_STATE_LABEL_SUMMARY_COLUMNS = [
    "state_label",
    "trades",
    "net_pnl",
    "gross_profit",
    "gross_loss",
    "profit_factor",
    "win_rate_pct",
    "average_r_multiple",
    "median_r_multiple",
    "average_state_observation_count",
    "average_positive_transition_probability",
    "average_forward_return_pct",
    "median_forward_return_pct",
]


Predicate = Callable[[dict[str, object]], bool]


@dataclass(frozen=True)
class S2MarkovFilter:
    filter_name: str
    description: str
    predicate: Predicate


def parse_state_label(state_label: object) -> dict[str, str]:
    """Safely parse RET_*|VOL_*|DD_*|LOW_* state labels."""

    unknown = {
        "ret_state": "UNKNOWN",
        "vol_state": "UNKNOWN",
        "dd_state": "UNKNOWN",
        "low_state": "UNKNOWN",
    }
    if state_label is None or pd.isna(state_label):
        return unknown
    parts = str(state_label).split("|")
    if len(parts) != 4:
        return unknown
    ret_state, vol_state, dd_state, low_state = parts
    if not (
        ret_state.startswith("RET_")
        and vol_state.startswith("VOL_")
        and dd_state.startswith("DD_")
        and low_state.startswith("LOW_")
    ):
        return unknown
    return {
        "ret_state": ret_state,
        "vol_state": vol_state,
        "dd_state": dd_state,
        "low_state": low_state,
    }


def build_s2_markov_filter_simulation_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return one S2 Markov simulation row per diagnostic filter."""

    rows = _s2_trade_rows(trade_context_rows)
    if not rows:
        return []

    baseline_summary = _performance_summary(rows)
    output = []
    for markov_filter in s2_markov_filters():
        kept, rejected = _split_rows(rows, markov_filter)
        kept_summary = _performance_summary(kept)
        rejected_summary = _performance_summary(rejected)
        output.append(
            {
                "filter_name": markov_filter.filter_name,
                "filter_description": markov_filter.description,
                "kept_trades": len(kept),
                "rejected_trades": len(rejected),
                "baseline_trades": len(rows),
                "kept_net_pnl": kept_summary["net_pnl"],
                "rejected_net_pnl": rejected_summary["net_pnl"],
                "baseline_net_pnl": baseline_summary["net_pnl"],
                "pnl_delta_vs_baseline": _subtract(
                    kept_summary["net_pnl"],
                    baseline_summary["net_pnl"],
                ),
                "kept_gross_profit": kept_summary["gross_profit"],
                "kept_gross_loss": kept_summary["gross_loss"],
                "kept_profit_factor": kept_summary["profit_factor"],
                "kept_win_rate_pct": kept_summary["win_rate_pct"],
                "kept_average_net_pnl": kept_summary["average_net_pnl"],
                "kept_average_r_multiple": kept_summary["average_r_multiple"],
                "kept_median_r_multiple": kept_summary["median_r_multiple"],
                "rejected_average_r_multiple": rejected_summary[
                    "average_r_multiple"
                ],
                "rejected_median_r_multiple": rejected_summary[
                    "median_r_multiple"
                ],
            }
        )
    return output


def build_s2_markov_filter_simulation_by_year_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return S2 Markov filter simulations grouped by exit year."""

    rows = _s2_trade_rows(trade_context_rows)
    if not rows:
        return []

    output = []
    for markov_filter in s2_markov_filters():
        grouped: dict[int, list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            row_year = _year(row.get("exit_date"))
            if row_year is not None:
                grouped[row_year].append(row)
        for year, group_rows in sorted(grouped.items()):
            kept, rejected = _split_rows(group_rows, markov_filter)
            output.append(
                {
                    "filter_name": markov_filter.filter_name,
                    "year": year,
                    **_group_summary(kept, rejected),
                }
            )
    return output


def build_s2_markov_filter_simulation_by_symbol_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return S2 Markov filter simulations grouped by symbol."""

    rows = _s2_trade_rows(trade_context_rows)
    if not rows:
        return []

    output = []
    for markov_filter in s2_markov_filters():
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            symbol = row.get("symbol")
            if symbol is not None and not pd.isna(symbol):
                grouped[str(symbol)].append(row)
        for symbol, group_rows in sorted(grouped.items()):
            kept, rejected = _split_rows(group_rows, markov_filter)
            output.append(
                {
                    "filter_name": markov_filter.filter_name,
                    "symbol": symbol,
                    **_group_summary(kept, rejected),
                }
            )
    return output


def build_s2_markov_filter_simulation_rejected_trade_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return one row per accepted S2 trade rejected by each simulated filter."""

    rows = _s2_trade_rows(trade_context_rows)
    if not rows:
        return []

    output = []
    for markov_filter in s2_markov_filters():
        for row in rows:
            if markov_filter.predicate(row):
                continue
            output.append(
                {
                    "filter_name": markov_filter.filter_name,
                    **{
                        column: row.get(column)
                        for column in S2_MARKOV_FILTER_SIMULATION_REJECTED_TRADES_COLUMNS
                        if column != "filter_name"
                    },
                }
            )
    return output


def build_s2_markov_state_component_summary_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return accepted-trade performance by parsed Markov state component."""

    rows = _s2_trade_rows(trade_context_rows)
    if not rows:
        return []

    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        for component_type in ("ret_state", "vol_state", "dd_state", "low_state"):
            grouped[(component_type, str(row.get(component_type)))].append(row)

    output = []
    for (component_type, component_bucket), group_rows in grouped.items():
        summary = _performance_summary(group_rows)
        output.append(
            {
                "component_type": component_type,
                "component_bucket": component_bucket,
                "trades": len(group_rows),
                **_public_performance_summary(summary),
            }
        )
    return sorted(
        output,
        key=lambda row: (
            row["component_type"],
            -_sort_decimal(row["net_pnl"]),
            row["component_bucket"],
        ),
    )


def build_s2_markov_state_label_summary_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return accepted-trade performance by full Markov state label."""

    rows = _s2_trade_rows(trade_context_rows)
    if not rows:
        return []

    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("state_label") or "UNKNOWN")].append(row)

    output = []
    for state_label, group_rows in grouped.items():
        summary = _performance_summary(group_rows)
        output.append(
            {
                "state_label": state_label,
                "trades": len(group_rows),
                **_public_performance_summary(summary),
                "average_state_observation_count": _average_field(
                    group_rows,
                    "state_observation_count",
                ),
                "average_positive_transition_probability": _average_field(
                    group_rows,
                    "positive_transition_probability",
                ),
                "average_forward_return_pct": _average_field(
                    group_rows,
                    "average_forward_return_pct",
                ),
                "median_forward_return_pct": _median_field(
                    group_rows,
                    "median_forward_return_pct",
                ),
            }
        )
    return sorted(
        output,
        key=lambda row: (
            -_sort_decimal(row["net_pnl"]),
            row["state_label"],
        ),
    )


def s2_markov_filters() -> tuple[S2MarkovFilter, ...]:
    """Return all initial diagnostic-only S2 Markov filters."""

    return (
        S2MarkovFilter(
            "s2_keep_ret_up_or_strong_up",
            "Keep ret_state in RET_UP or RET_STRONG_UP.",
            lambda row: row.get("ret_state") in {"RET_UP", "RET_STRONG_UP"},
        ),
        S2MarkovFilter(
            "s2_keep_ret_flat_up_strong_up",
            "Keep ret_state in RET_FLAT, RET_UP, or RET_STRONG_UP.",
            lambda row: row.get("ret_state")
            in {"RET_FLAT", "RET_UP", "RET_STRONG_UP"},
        ),
        S2MarkovFilter(
            "s2_exclude_ret_down",
            "Reject ret_state RET_DOWN.",
            lambda row: row.get("ret_state") != "RET_DOWN",
        ),
        S2MarkovFilter(
            "s2_exclude_ret_down_and_strong_down",
            "Reject ret_state RET_DOWN or RET_STRONG_DOWN.",
            lambda row: row.get("ret_state")
            not in {"RET_DOWN", "RET_STRONG_DOWN"},
        ),
        S2MarkovFilter(
            "s2_keep_ret_strong_up_only",
            "Keep ret_state RET_STRONG_UP only.",
            lambda row: row.get("ret_state") == "RET_STRONG_UP",
        ),
        S2MarkovFilter(
            "s2_exclude_dd_deep",
            "Reject dd_state DD_DEEP.",
            lambda row: row.get("dd_state") != "DD_DEEP",
        ),
        S2MarkovFilter(
            "s2_keep_dd_shallow_only",
            "Keep dd_state DD_SHALLOW only.",
            lambda row: row.get("dd_state") == "DD_SHALLOW",
        ),
        S2MarkovFilter(
            "s2_keep_dd_shallow_or_mid",
            "Keep dd_state DD_SHALLOW or DD_MID.",
            lambda row: row.get("dd_state") in {"DD_SHALLOW", "DD_MID"},
        ),
        S2MarkovFilter(
            "s2_exclude_low_near",
            "Reject low_state LOW_NEAR.",
            lambda row: row.get("low_state") != "LOW_NEAR",
        ),
        S2MarkovFilter(
            "s2_keep_low_far_from_low_only",
            "Keep low_state LOW_FAR_FROM_LOW only.",
            lambda row: row.get("low_state") == "LOW_FAR_FROM_LOW",
        ),
        S2MarkovFilter(
            "s2_keep_low_mid_or_far",
            "Keep low_state LOW_MID_RANGE or LOW_FAR_FROM_LOW.",
            lambda row: row.get("low_state")
            in {"LOW_MID_RANGE", "LOW_FAR_FROM_LOW"},
        ),
        S2MarkovFilter(
            "s2_exclude_vol_low",
            "Reject vol_state VOL_LOW.",
            lambda row: row.get("vol_state") != "VOL_LOW",
        ),
        S2MarkovFilter(
            "s2_keep_vol_mid_or_high",
            "Keep vol_state VOL_MID or VOL_HIGH.",
            lambda row: row.get("vol_state") in {"VOL_MID", "VOL_HIGH"},
        ),
        S2MarkovFilter(
            "s2_keep_vol_high_only",
            "Keep vol_state VOL_HIGH only.",
            lambda row: row.get("vol_state") == "VOL_HIGH",
        ),
        *_threshold_filters(
            "state_observation_count",
            "s2_obs_gte",
            ("15", "20", "30", "40", "50"),
        ),
        *_threshold_filters(
            "positive_transition_probability",
            "s2_prob_gte",
            ("0.65", "0.70", "0.75", "0.80"),
        ),
        S2MarkovFilter(
            "s2_avg_forward_return_1_to_3",
            "Keep average_forward_return_pct from 1 to below 3.",
            lambda row: _between(row, "average_forward_return_pct", "1", "3"),
        ),
        S2MarkovFilter(
            "s2_avg_forward_return_3_to_5",
            "Keep average_forward_return_pct from 3 to below 5.",
            lambda row: _between(row, "average_forward_return_pct", "3", "5"),
        ),
        S2MarkovFilter(
            "s2_avg_forward_return_5_to_8",
            "Keep average_forward_return_pct from 5 to below 8.",
            lambda row: _between(row, "average_forward_return_pct", "5", "8"),
        ),
        S2MarkovFilter(
            "s2_avg_forward_return_8_to_12",
            "Keep average_forward_return_pct from 8 to below 12.",
            lambda row: _between(row, "average_forward_return_pct", "8", "12"),
        ),
        S2MarkovFilter(
            "s2_avg_forward_return_gte_12",
            "Keep average_forward_return_pct >= 12.",
            lambda row: _gte(row, "average_forward_return_pct", "12"),
        ),
        S2MarkovFilter(
            "s2_avg_forward_return_gte_3",
            "Keep average_forward_return_pct >= 3.",
            lambda row: _gte(row, "average_forward_return_pct", "3"),
        ),
        S2MarkovFilter(
            "s2_avg_forward_return_gte_5",
            "Keep average_forward_return_pct >= 5.",
            lambda row: _gte(row, "average_forward_return_pct", "5"),
        ),
        S2MarkovFilter(
            "s2_clean_continuation_v1",
            "Keep non-damaged continuation states.",
            lambda row: row.get("ret_state")
            in {"RET_FLAT", "RET_UP", "RET_STRONG_UP"}
            and row.get("dd_state") != "DD_DEEP"
            and row.get("low_state") != "LOW_NEAR",
        ),
        S2MarkovFilter(
            "s2_clean_strength_v1",
            "Keep strong/up shallow states far from low.",
            lambda row: row.get("ret_state") in {"RET_UP", "RET_STRONG_UP"}
            and row.get("dd_state") == "DD_SHALLOW"
            and row.get("low_state") == "LOW_FAR_FROM_LOW",
        ),
        S2MarkovFilter(
            "s2_no_structural_damage_v1",
            "Reject down returns, deep drawdown, or near-low states.",
            lambda row: not (
                row.get("ret_state") in {"RET_DOWN", "RET_STRONG_DOWN"}
                or row.get("dd_state") == "DD_DEEP"
                or row.get("low_state") == "LOW_NEAR"
            ),
        ),
        S2MarkovFilter(
            "s2_high_confidence_state_v1",
            "Keep states with observations >= 40 and probability >= 0.65.",
            lambda row: _gte(row, "state_observation_count", "40")
            and _gte(row, "positive_transition_probability", "0.65"),
        ),
        S2MarkovFilter(
            "s2_high_avg_return_state_v1",
            "Keep states with average_forward_return_pct >= 12.",
            lambda row: _gte(row, "average_forward_return_pct", "12"),
        ),
        S2MarkovFilter(
            "s2_balanced_markov_v1",
            "Keep balanced constructive Markov states with observations >= 15.",
            lambda row: row.get("ret_state")
            in {"RET_FLAT", "RET_UP", "RET_STRONG_UP"}
            and row.get("dd_state") in {"DD_SHALLOW", "DD_MID"}
            and row.get("low_state") in {"LOW_MID_RANGE", "LOW_FAR_FROM_LOW"}
            and row.get("vol_state") in {"VOL_MID", "VOL_HIGH"}
            and _gte(row, "state_observation_count", "15"),
        ),
    )


def _threshold_filters(
    field: str,
    name_prefix: str,
    thresholds: tuple[str, ...],
) -> tuple[S2MarkovFilter, ...]:
    return tuple(
        S2MarkovFilter(
            f"{name_prefix}_{threshold.replace('.', '_')}",
            f"Keep {field} >= {threshold}.",
            lambda row, field=field, threshold=threshold: _gte(
                row,
                field,
                threshold,
            ),
        )
        for threshold in thresholds
    )


def _s2_trade_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows = []
    for row in trade_context_rows:
        if not _is_s2_row(row):
            continue
        parsed = parse_state_label(row.get("state_label"))
        rows.append({**row, **parsed})
    return rows


def _is_s2_row(row: dict[str, object]) -> bool:
    return (
        row.get("strategy_name") == S2_STRATEGY_NAME
        or row.get("strategy_family") == S2_STRATEGY_NAME
    )


def _split_rows(
    rows: list[dict[str, object]],
    markov_filter: S2MarkovFilter,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    kept = []
    rejected = []
    for row in rows:
        if markov_filter.predicate(row):
            kept.append(row)
        else:
            rejected.append(row)
    return kept, rejected


def _group_summary(
    kept: list[dict[str, object]],
    rejected: list[dict[str, object]],
) -> dict[str, object]:
    kept_summary = _performance_summary(kept)
    rejected_summary = _performance_summary(rejected)
    return {
        "kept_trades": len(kept),
        "rejected_trades": len(rejected),
        "kept_net_pnl": kept_summary["net_pnl"],
        "rejected_net_pnl": rejected_summary["net_pnl"],
        "kept_profit_factor": kept_summary["profit_factor"],
        "kept_win_rate_pct": kept_summary["win_rate_pct"],
        "kept_average_r_multiple": kept_summary["average_r_multiple"],
        "kept_median_r_multiple": kept_summary["median_r_multiple"],
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
    gross_profit = sum((value for value in pnls if value > 0), Decimal("0"))
    gross_loss = sum((value for value in pnls if value < 0), Decimal("0"))
    return {
        "net_pnl": sum(pnls, Decimal("0")) if pnls else Decimal("0"),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": None if gross_loss == 0 else gross_profit / abs(gross_loss),
        "win_rate_pct": _ratio_pct(
            len(tuple(value for value in pnls if value > 0)),
            len(pnls),
        ),
        "average_net_pnl": _average(pnls),
        "average_r_multiple": _average(r_values),
        "median_r_multiple": _median(r_values),
    }


def _public_performance_summary(summary: dict[str, object]) -> dict[str, object]:
    return {
        "net_pnl": summary["net_pnl"],
        "gross_profit": summary["gross_profit"],
        "gross_loss": summary["gross_loss"],
        "profit_factor": summary["profit_factor"],
        "win_rate_pct": summary["win_rate_pct"],
        "average_r_multiple": summary["average_r_multiple"],
        "median_r_multiple": summary["median_r_multiple"],
    }


def _gte(row: dict[str, object], field: str, threshold: str) -> bool:
    value = _to_decimal(row.get(field))
    return value is not None and value >= Decimal(threshold)


def _between(row: dict[str, object], field: str, lower: str, upper: str) -> bool:
    value = _to_decimal(row.get(field))
    return value is not None and Decimal(lower) <= value < Decimal(upper)


def _average_field(rows: list[dict[str, object]], field: str) -> Decimal | None:
    return _average(
        tuple(
            value
            for row in rows
            if (value := _to_decimal(row.get(field))) is not None
        )
    )


def _median_field(rows: list[dict[str, object]], field: str) -> Decimal | None:
    return _median(
        tuple(
            value
            for row in rows
            if (value := _to_decimal(row.get(field))) is not None
        )
    )


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
    if value is None or pd.isna(value):
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _year(value: object) -> int | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, date):
        return value.year
    return pd.to_datetime(value).year


def _sort_decimal(value: object) -> Decimal:
    decimal = _to_decimal(value)
    return decimal if decimal is not None else Decimal("0")
