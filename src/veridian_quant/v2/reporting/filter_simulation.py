"""Candidate filter simulations over completed trade context rows.

These helpers are diagnostic only. They evaluate hypothetical eligibility
rules against already-executed trades and do not rebalance a portfolio, free
capital, create replacement trades, mutate backtest results, or affect
strategy behavior.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

import pandas as pd

from veridian_quant.v2.reporting.diagnostics import _r_multiple_group_summary


CANDIDATE_FILTER_SIMULATION_COLUMNS = [
    "filter_id",
    "filter_description",
    "filter_family",
    "trades_kept",
    "trades_removed",
    "kept_trade_pct",
    "removed_trade_pct",
    "winning_trades",
    "losing_trades",
    "positive_r_rate_pct",
    "average_r",
    "average_winner_r",
    "average_loser_r",
    "best_r",
    "worst_r",
    "total_net_pnl",
    "average_net_pnl",
    "gross_profit",
    "gross_loss",
    "profit_factor",
    "expectancy",
    "stop_loss_trades",
    "stop_gap_trades",
    "target_hit_trades",
    "target_gap_trades",
    "time_stop_trades",
    "backtest_end_trades",
    "data_end_trades",
    "notes",
]
CANDIDATE_FILTER_SIMULATION_BY_YEAR_COLUMNS = [
    "filter_id",
    "year",
    "trades_kept",
    "winning_trades",
    "losing_trades",
    "positive_r_rate_pct",
    "average_r",
    "total_net_pnl",
    "profit_factor",
    "expectancy",
]
CANDIDATE_FILTER_SIMULATION_BY_SYMBOL_COLUMNS = [
    "filter_id",
    "symbol",
    "trades_kept",
    "winning_trades",
    "losing_trades",
    "positive_r_rate_pct",
    "average_r",
    "total_net_pnl",
    "profit_factor",
    "expectancy",
]
CANDIDATE_FILTER_SIMULATION_REJECTED_TRADES_COLUMNS = [
    "filter_id",
    "trade_id",
    "symbol",
    "signal_date",
    "entry_date",
    "exit_date",
    "exit_reason",
    "net_pnl",
    "r_multiple",
    "z_score",
    "stock_consecutive_down_closes",
    "stock_return_5d_pct",
    "stock_drawdown_60d_pct",
    "stock_close_vs_60d_low_pct",
    "stock_atr14_pct",
    "stock_atr14_change_10d_pct",
]


Predicate = Callable[[dict[str, object]], bool]


@dataclass(frozen=True)
class CandidateFilter:
    """One diagnostic-only candidate eligibility rule."""

    filter_id: str
    description: str
    family: str
    predicate: Predicate
    notes: str = ""


def build_candidate_filter_simulation_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return one simulation summary row per candidate rule.

    This is a realized-trade subset diagnostic, not a portfolio-rebalanced
    simulation. It does not model freed capital, replacement trades, or changed
    order timing.
    """

    total_trades = len(trade_context_rows)
    rows = []
    for candidate in _candidate_filters():
        kept = _kept_rows(candidate, trade_context_rows)
        rows.append(
            {
                "filter_id": candidate.filter_id,
                "filter_description": candidate.description,
                "filter_family": candidate.family,
                "trades_kept": len(kept),
                "trades_removed": total_trades - len(kept),
                "kept_trade_pct": _ratio_pct(len(kept), total_trades),
                "removed_trade_pct": _ratio_pct(total_trades - len(kept), total_trades),
                **_simulation_summary(kept),
                "notes": candidate.notes,
            }
        )
    return rows


def build_candidate_filter_simulation_by_year_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return candidate simulation summaries grouped by trade exit year."""

    rows = []
    for candidate in _candidate_filters():
        grouped: dict[int, list[dict[str, object]]] = defaultdict(list)
        for row in _kept_rows(candidate, trade_context_rows):
            exit_year = _year(row.get("exit_date"))
            if exit_year is not None:
                grouped[exit_year].append(row)
        for year, kept in sorted(grouped.items()):
            rows.append(
                {
                    "filter_id": candidate.filter_id,
                    "year": year,
                    **_compact_summary(kept),
                }
            )
    return rows


def build_candidate_filter_simulation_by_symbol_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return candidate simulation summaries grouped by symbol."""

    rows = []
    for candidate in _candidate_filters():
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in _kept_rows(candidate, trade_context_rows):
            symbol = row.get("symbol")
            if symbol is not None:
                grouped[str(symbol)].append(row)
        for symbol, kept in sorted(grouped.items()):
            rows.append(
                {
                    "filter_id": candidate.filter_id,
                    "symbol": symbol,
                    **_compact_summary(kept),
                }
            )
    return rows


def build_candidate_filter_simulation_rejected_trade_rows(
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Return one removed-trade audit row per candidate rule."""

    rows = []
    for candidate in _candidate_filters():
        for trade_row in trade_context_rows:
            if candidate.predicate(trade_row):
                continue
            rows.append(
                {
                    "filter_id": candidate.filter_id,
                    **{
                        column: trade_row.get(column)
                        for column in CANDIDATE_FILTER_SIMULATION_REJECTED_TRADES_COLUMNS
                        if column != "filter_id"
                    },
                }
            )
    return rows


def _candidate_filters() -> tuple[CandidateFilter, ...]:
    missing_note = "Required positive fields missing -> trade not kept; missing exclusion fields do not remove trades."
    return (
        CandidateFilter(
            "zscore_gt_minus_3",
            "Keep trades where z_score > -3.0.",
            "zscore_depth",
            lambda row: _gt(row, "z_score", "-3.0"),
            "Missing z_score is not kept.",
        ),
        CandidateFilter(
            "zscore_minus_2_to_minus_2_5_only",
            "Keep trades where -2.5 < z_score <= -2.0.",
            "zscore_depth",
            lambda row: _between(row, "z_score", "-2.5", "-2.0", lower_open=True),
            "Missing z_score is not kept.",
        ),
        CandidateFilter(
            "zscore_exclude_below_minus_3",
            "Exclude trades where z_score <= -3.0.",
            "zscore_depth",
            lambda row: not _lte_if_present(row, "z_score", "-3.0"),
            "Missing z_score passes this exclude-style filter.",
        ),
        CandidateFilter(
            "down_closes_gte_3",
            "Keep trades where stock_consecutive_down_closes >= 3.",
            "consecutive_down_closes",
            lambda row: _gte(row, "stock_consecutive_down_closes", "3"),
            "Missing stock_consecutive_down_closes is not kept.",
        ),
        CandidateFilter(
            "down_closes_gte_4",
            "Keep trades where stock_consecutive_down_closes >= 4.",
            "consecutive_down_closes",
            lambda row: _gte(row, "stock_consecutive_down_closes", "4"),
            "Missing stock_consecutive_down_closes is not kept.",
        ),
        CandidateFilter(
            "down_closes_not_1_or_2",
            "Exclude trades where stock_consecutive_down_closes is 1 or 2.",
            "consecutive_down_closes",
            lambda row: not (
                _equals_if_present(row, "stock_consecutive_down_closes", "1")
                or _equals_if_present(row, "stock_consecutive_down_closes", "2")
            ),
            "Missing stock_consecutive_down_closes passes this exclude-style filter.",
        ),
        CandidateFilter(
            "return_5d_below_minus_7",
            "Keep trades where stock_return_5d_pct <= -7.",
            "pre_signal_return",
            lambda row: _lte(row, "stock_return_5d_pct", "-7"),
            "Missing stock_return_5d_pct is not kept.",
        ),
        CandidateFilter(
            "return_3d_below_minus_7",
            "Keep trades where stock_return_3d_pct <= -7.",
            "pre_signal_return",
            lambda row: _lte(row, "stock_return_3d_pct", "-7"),
            "Missing stock_return_3d_pct is not kept.",
        ),
        CandidateFilter(
            "return_10d_below_minus_7",
            "Keep trades where stock_return_10d_pct <= -7.",
            "pre_signal_return",
            lambda row: _lte(row, "stock_return_10d_pct", "-7"),
            "Missing stock_return_10d_pct is not kept.",
        ),
        CandidateFilter(
            "exclude_return_5d_minus_3_to_minus_7",
            "Exclude trades where -7 < stock_return_5d_pct <= -3.",
            "pre_signal_return",
            lambda row: not _between_if_present(row, "stock_return_5d_pct", "-7", "-3", lower_open=True),
            "Missing stock_return_5d_pct passes this exclude-style filter.",
        ),
        CandidateFilter(
            "exclude_return_10d_minus_3_to_minus_7",
            "Exclude trades where -7 < stock_return_10d_pct <= -3.",
            "pre_signal_return",
            lambda row: not _between_if_present(row, "stock_return_10d_pct", "-7", "-3", lower_open=True),
            "Missing stock_return_10d_pct passes this exclude-style filter.",
        ),
        CandidateFilter(
            "drawdown_60d_below_minus_20",
            "Keep trades where stock_drawdown_60d_pct <= -20.",
            "drawdown_depth",
            lambda row: _lte(row, "stock_drawdown_60d_pct", "-20"),
            "Missing stock_drawdown_60d_pct is not kept.",
        ),
        CandidateFilter(
            "drawdown_60d_shallow_or_deep",
            "Keep trades where stock_drawdown_60d_pct > -5 or <= -20.",
            "drawdown_depth",
            lambda row: _gt(row, "stock_drawdown_60d_pct", "-5")
            or _lte(row, "stock_drawdown_60d_pct", "-20"),
            "Missing stock_drawdown_60d_pct is not kept.",
        ),
        CandidateFilter(
            "exclude_drawdown_60d_minus_5_to_minus_20",
            "Exclude trades where -20 < stock_drawdown_60d_pct <= -5.",
            "drawdown_depth",
            lambda row: not _between_if_present(row, "stock_drawdown_60d_pct", "-20", "-5", lower_open=True),
            "Missing stock_drawdown_60d_pct passes this exclude-style filter.",
        ),
        CandidateFilter(
            "drawdown_120d_below_minus_20",
            "Keep trades where stock_drawdown_120d_pct <= -20.",
            "drawdown_depth",
            lambda row: _lte(row, "stock_drawdown_120d_pct", "-20"),
            "Missing stock_drawdown_120d_pct is not kept.",
        ),
        CandidateFilter(
            "atr_pct_gte_4",
            "Keep trades where stock_atr14_pct >= 4.",
            "atr_stretch",
            lambda row: _gte(row, "stock_atr14_pct", "4"),
            "Missing stock_atr14_pct is not kept.",
        ),
        CandidateFilter(
            "atr_pct_gte_6",
            "Keep trades where stock_atr14_pct >= 6.",
            "atr_stretch",
            lambda row: _gte(row, "stock_atr14_pct", "6"),
            "Missing stock_atr14_pct is not kept.",
        ),
        CandidateFilter(
            "exclude_atr_change_10d_gt_20",
            "Exclude trades where stock_atr14_change_10d_pct > 20.",
            "atr_stretch",
            lambda row: not _gt_if_present(row, "stock_atr14_change_10d_pct", "20"),
            "Missing stock_atr14_change_10d_pct passes this exclude-style filter.",
        ),
        CandidateFilter(
            "exclude_atr_change_10d_gt_50",
            "Exclude trades where stock_atr14_change_10d_pct > 50.",
            "atr_stretch",
            lambda row: not _gt_if_present(row, "stock_atr14_change_10d_pct", "50"),
            "Missing stock_atr14_change_10d_pct passes this exclude-style filter.",
        ),
        CandidateFilter(
            "is_60d_low",
            "Keep trades where stock_is_60d_low is true.",
            "fresh_low",
            lambda row: _is_true(row.get("stock_is_60d_low")),
            "Missing stock_is_60d_low is not kept.",
        ),
        CandidateFilter(
            "is_120d_low",
            "Keep trades where stock_is_120d_low is true.",
            "fresh_low",
            lambda row: _is_true(row.get("stock_is_120d_low")),
            "Missing stock_is_120d_low is not kept.",
        ),
        CandidateFilter(
            "close_within_1pct_60d_low",
            "Keep trades where stock_close_vs_60d_low_pct <= 1.",
            "fresh_low",
            lambda row: _lte(row, "stock_close_vs_60d_low_pct", "1"),
            "Missing stock_close_vs_60d_low_pct is not kept.",
        ),
        CandidateFilter(
            "exclude_close_1_to_7pct_above_60d_low",
            "Exclude trades where 1 < stock_close_vs_60d_low_pct <= 7.",
            "fresh_low",
            lambda row: not _between_if_present(row, "stock_close_vs_60d_low_pct", "1", "7", lower_open=True),
            "Missing stock_close_vs_60d_low_pct passes this exclude-style filter.",
        ),
        CandidateFilter(
            "mature_capitulation_basic",
            "Keep trades with >=3 down closes and 5d return <= -7.",
            "combined_candidate",
            lambda row: _gte(row, "stock_consecutive_down_closes", "3")
            and _lte(row, "stock_return_5d_pct", "-7"),
            missing_note,
        ),
        CandidateFilter(
            "mature_capitulation_with_z_guard",
            "Keep mature capitulation trades with z_score > -3.0.",
            "combined_candidate",
            lambda row: _gte(row, "stock_consecutive_down_closes", "3")
            and _lte(row, "stock_return_5d_pct", "-7")
            and _gt(row, "z_score", "-3.0"),
            missing_note,
        ),
        CandidateFilter(
            "deep_drawdown_capitulation",
            "Keep trades with 60d drawdown <= -20 and >=3 down closes.",
            "combined_candidate",
            lambda row: _lte(row, "stock_drawdown_60d_pct", "-20")
            and _gte(row, "stock_consecutive_down_closes", "3"),
            missing_note,
        ),
        CandidateFilter(
            "shallow_or_capitulation",
            "Keep trades with 60d drawdown > -5 or <= -20.",
            "combined_candidate",
            lambda row: _gt(row, "stock_drawdown_60d_pct", "-5")
            or _lte(row, "stock_drawdown_60d_pct", "-20"),
            missing_note,
        ),
        CandidateFilter(
            "avoid_messy_middle_v1",
            "Avoid 60d drawdown messy middle and 1-7pct above 60d low.",
            "combined_candidate",
            lambda row: not _between_if_present(row, "stock_drawdown_60d_pct", "-20", "-5", lower_open=True)
            and not _between_if_present(row, "stock_close_vs_60d_low_pct", "1", "7", lower_open=True),
            missing_note,
        ),
        CandidateFilter(
            "avoid_messy_middle_v2",
            "Avoid messy middle with z_score > -3.0 guard.",
            "combined_candidate",
            lambda row: not _between_if_present(row, "stock_drawdown_60d_pct", "-20", "-5", lower_open=True)
            and not _between_if_present(row, "stock_close_vs_60d_low_pct", "1", "7", lower_open=True)
            and _gt(row, "z_score", "-3.0"),
            missing_note,
        ),
        CandidateFilter(
            "high_vol_capitulation",
            "Keep trades with ATR pct >=4 and >=3 down closes.",
            "combined_candidate",
            lambda row: _gte(row, "stock_atr14_pct", "4")
            and _gte(row, "stock_consecutive_down_closes", "3"),
            missing_note,
        ),
        CandidateFilter(
            "high_vol_without_extreme_atr_expansion",
            "Keep trades with ATR pct >=4 and ATR 10d change <=20.",
            "combined_candidate",
            lambda row: _gte(row, "stock_atr14_pct", "4")
            and _lte(row, "stock_atr14_change_10d_pct", "20"),
            missing_note,
        ),
        CandidateFilter(
            "broad_best_guess_candidate",
            "Keep z>-3, >=3 down closes, avoid messy middle, and ATR 10d change <=20.",
            "combined_candidate",
            lambda row: _gt(row, "z_score", "-3.0")
            and _gte(row, "stock_consecutive_down_closes", "3")
            and not _between_if_present(row, "stock_drawdown_60d_pct", "-20", "-5", lower_open=True)
            and not _between_if_present(row, "stock_close_vs_60d_low_pct", "1", "7", lower_open=True)
            and _lte(row, "stock_atr14_change_10d_pct", "20"),
            missing_note,
        ),
    )


def _kept_rows(
    candidate: CandidateFilter,
    trade_context_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    return [row for row in trade_context_rows if candidate.predicate(row)]


def _simulation_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    if not rows:
        return {
            "winning_trades": None,
            "losing_trades": None,
            "positive_r_rate_pct": None,
            "average_r": None,
            "average_winner_r": None,
            "average_loser_r": None,
            "best_r": None,
            "worst_r": None,
            "total_net_pnl": None,
            "average_net_pnl": None,
            "gross_profit": None,
            "gross_loss": None,
            "profit_factor": None,
            "expectancy": None,
            "stop_loss_trades": None,
            "stop_gap_trades": None,
            "target_hit_trades": None,
            "target_gap_trades": None,
            "time_stop_trades": None,
            "backtest_end_trades": None,
            "data_end_trades": None,
        }

    summary = _r_summary(rows)
    pnl_summary = _pnl_summary(rows)
    exit_counts = Counter(str(row.get("exit_reason")) for row in rows)
    return {
        **summary,
        **pnl_summary,
        "stop_loss_trades": exit_counts.get("stop_loss_hit", 0),
        "stop_gap_trades": exit_counts.get("stop_gap_hit", 0),
        "target_hit_trades": exit_counts.get("target_hit", 0),
        "target_gap_trades": exit_counts.get("target_gap_hit", 0),
        "time_stop_trades": exit_counts.get("time_stop", 0),
        "backtest_end_trades": exit_counts.get("backtest_end", 0),
        "data_end_trades": exit_counts.get("data_end", 0),
    }


def _compact_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "trades_kept": len(rows),
        **_r_summary(rows),
        **{
            key: value
            for key, value in _pnl_summary(rows).items()
            if key in {"total_net_pnl", "profit_factor", "expectancy"}
        },
    }


def _r_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    r_values = tuple(
        r_value
        for row in rows
        if (r_value := _to_decimal(row.get("r_multiple"))) is not None
    )
    if not r_values:
        return {
            "winning_trades": None,
            "losing_trades": None,
            "positive_r_rate_pct": None,
            "average_r": None,
            "average_winner_r": None,
            "average_loser_r": None,
            "best_r": None,
            "worst_r": None,
        }
    return {
        key: value
        for key, value in _r_multiple_group_summary(r_values).items()
        if key != "trades_with_r"
    }


def _pnl_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    net_pnls = tuple(
        net_pnl
        for row in rows
        if (net_pnl := _to_decimal(row.get("net_pnl"))) is not None
    )
    if not net_pnls:
        return {
            "total_net_pnl": None,
            "average_net_pnl": None,
            "gross_profit": None,
            "gross_loss": None,
            "profit_factor": None,
            "expectancy": None,
        }
    gross_profit = sum((value for value in net_pnls if value > 0), Decimal("0"))
    gross_loss = sum((value for value in net_pnls if value < 0), Decimal("0"))
    average_net_pnl = sum(net_pnls, Decimal("0")) / Decimal(len(net_pnls))
    return {
        "total_net_pnl": sum(net_pnls, Decimal("0")),
        "average_net_pnl": average_net_pnl,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": None if gross_loss == 0 else gross_profit / abs(gross_loss),
        "expectancy": average_net_pnl,
    }


def _gt(row: dict[str, object], field: str, threshold: str) -> bool:
    value = _to_decimal(row.get(field))
    return value is not None and value > Decimal(threshold)


def _gte(row: dict[str, object], field: str, threshold: str) -> bool:
    value = _to_decimal(row.get(field))
    return value is not None and value >= Decimal(threshold)


def _lte(row: dict[str, object], field: str, threshold: str) -> bool:
    value = _to_decimal(row.get(field))
    return value is not None and value <= Decimal(threshold)


def _between(
    row: dict[str, object],
    field: str,
    lower: str,
    upper: str,
    lower_open: bool = False,
) -> bool:
    value = _to_decimal(row.get(field))
    if value is None:
        return False
    lower_decimal = Decimal(lower)
    upper_decimal = Decimal(upper)
    if lower_open:
        return lower_decimal < value <= upper_decimal
    return lower_decimal <= value <= upper_decimal


def _gt_if_present(row: dict[str, object], field: str, threshold: str) -> bool:
    value = _to_decimal(row.get(field))
    return value is not None and value > Decimal(threshold)


def _lte_if_present(row: dict[str, object], field: str, threshold: str) -> bool:
    value = _to_decimal(row.get(field))
    return value is not None and value <= Decimal(threshold)


def _equals_if_present(row: dict[str, object], field: str, expected: str) -> bool:
    value = _to_decimal(row.get(field))
    return value is not None and value == Decimal(expected)


def _between_if_present(
    row: dict[str, object],
    field: str,
    lower: str,
    upper: str,
    lower_open: bool = False,
) -> bool:
    return _between(row, field, lower, upper, lower_open=lower_open)


def _is_true(value: object) -> bool:
    if value is None or pd.isna(value):
        return False
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


def _ratio_pct(numerator: int, denominator: int) -> Decimal | None:
    if denominator <= 0:
        return None
    return (Decimal(numerator) / Decimal(denominator)) * Decimal("100")


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
