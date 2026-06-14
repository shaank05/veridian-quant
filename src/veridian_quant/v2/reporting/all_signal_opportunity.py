"""All-signal opportunity diagnostics for v2 portfolio backtests.

These helpers build export-only diagnostics from an already-computed
``PortfolioBacktestResult``. Counterfactual rows simulate rejected capacity
signals without mutating the portfolio ledger, trades, PnLs, or strategy path.
"""

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping

import pandas as pd

from veridian_quant.v2.backtesting.execution import create_open_trade
from veridian_quant.v2.backtesting.exits import resolve_trade_exit
from veridian_quant.v2.backtesting.pnl import TradePnL, calculate_trade_pnl
from veridian_quant.v2.backtesting.setup import build_trade_setup
from veridian_quant.v2.backtesting.sizing import build_position_plan
from veridian_quant.v2.data.models import Signal
from veridian_quant.v2.features.technical import atr


ALL_SIGNAL_OPPORTUNITY_LOG_COLUMNS = [
    "symbol",
    "signal_date",
    "generated_on",
    "strategy_name",
    "strategy_variant",
    "signal_status",
    "rejection_reason",
    "is_accepted_trade",
    "is_rejected_capacity",
    "is_rejected_active_symbol",
    "is_counterfactual_simulated",
    "entry_date",
    "z_score",
    "close",
    "atr14",
    "atr_pct",
    "rolling_avg_volume_20",
    "candidate_ranking_mode",
    "candidate_rank",
    "candidate_score",
    "candidate_pool_size_for_date",
    "accepted_trade_id",
    "accepted_net_pnl",
    "accepted_r_multiple",
    "accepted_exit_reason",
    "counterfactual_net_pnl",
    "counterfactual_r_multiple",
    "counterfactual_exit_reason",
    "counterfactual_entry_price",
    "counterfactual_exit_price",
    "counterfactual_initial_risk_amount",
    "year",
    "month",
]
ACCEPTED_VS_REJECTED_SIGNAL_SUMMARY_COLUMNS = [
    "signal_group",
    "signal_count",
    "simulated_count",
    "gross_profit",
    "gross_loss",
    "net_pnl",
    "win_count",
    "loss_count",
    "win_rate_pct",
    "average_net_pnl",
    "median_net_pnl",
    "average_r_multiple",
    "median_r_multiple",
    "profit_factor",
]
COUNTERFACTUAL_REJECTED_TRADE_SUMMARY_COLUMNS = [
    "total_capacity_rejected",
    "simulated_capacity_rejected",
    "simulation_success_pct",
    "counterfactual_net_pnl",
    "counterfactual_gross_profit",
    "counterfactual_gross_loss",
    "counterfactual_profit_factor",
    "counterfactual_win_rate_pct",
    "counterfactual_average_r",
    "counterfactual_median_r",
    "counterfactual_best_trade",
    "counterfactual_worst_trade",
]
COUNTERFACTUAL_GROUP_COLUMNS = [
    "signal_count",
    "simulated_count",
    "gross_profit",
    "gross_loss",
    "net_pnl",
    "win_rate_pct",
    "average_r_multiple",
    "median_r_multiple",
    "profit_factor",
]
COUNTERFACTUAL_BY_YEAR_COLUMNS = ["year", *COUNTERFACTUAL_GROUP_COLUMNS]
COUNTERFACTUAL_BY_SYMBOL_COLUMNS = ["symbol", *COUNTERFACTUAL_GROUP_COLUMNS]
SAME_DAY_CANDIDATE_POOL_SUMMARY_COLUMNS = [
    "entry_date",
    "total_signal_count",
    "accepted_trade_count",
    "rejected_capacity_count",
    "rejected_active_symbol_count",
    "other_rejected_count",
    "accepted_net_pnl",
    "rejected_capacity_counterfactual_net_pnl",
    "best_counterfactual_symbol",
    "best_counterfactual_net_pnl",
    "worst_counterfactual_symbol",
    "worst_counterfactual_net_pnl",
    "average_candidate_score",
    "max_candidate_score",
    "min_candidate_score",
]
RANKING_FEATURE_DIAGNOSTICS_COLUMNS = [
    "feature_name",
    "bucket",
    "signal_group",
    "signal_count",
    "simulated_count",
    "gross_profit",
    "gross_loss",
    "net_pnl",
    "win_rate_pct",
    "average_r_multiple",
    "median_r_multiple",
    "profit_factor",
]

OPPORTUNITY_EXPORT_COLUMNS = {
    "all_signal_opportunity_log": ALL_SIGNAL_OPPORTUNITY_LOG_COLUMNS,
    "accepted_vs_rejected_signal_summary": (
        ACCEPTED_VS_REJECTED_SIGNAL_SUMMARY_COLUMNS
    ),
    "counterfactual_rejected_trade_summary": (
        COUNTERFACTUAL_REJECTED_TRADE_SUMMARY_COLUMNS
    ),
    "counterfactual_by_year": COUNTERFACTUAL_BY_YEAR_COLUMNS,
    "counterfactual_by_symbol": COUNTERFACTUAL_BY_SYMBOL_COLUMNS,
    "same_day_candidate_pool_summary": SAME_DAY_CANDIDATE_POOL_SUMMARY_COLUMNS,
    "ranking_feature_diagnostics": RANKING_FEATURE_DIAGNOSTICS_COLUMNS,
}

_CAPACITY_REASON = "PORTFOLIO_CAPACITY_FULL"
_ACTIVE_SYMBOL_REASON = "ACTIVE_SYMBOL_TRADE_EXISTS"
_SUMMARY_GROUPS = [
    "ACCEPTED_TRADE",
    "REJECTED_CAPACITY_COUNTERFACTUAL",
    "REJECTED_ACTIVE_SYMBOL",
    "OTHER_REJECTED",
]


@dataclass(frozen=True, slots=True)
class OpportunityDiagnostics:
    """Container for all opportunity diagnostic export rows."""

    all_signal_opportunity_log: list[dict[str, object]]
    accepted_vs_rejected_signal_summary: list[dict[str, object]]
    counterfactual_rejected_trade_summary: list[dict[str, object]]
    counterfactual_by_year: list[dict[str, object]]
    counterfactual_by_symbol: list[dict[str, object]]
    same_day_candidate_pool_summary: list[dict[str, object]]
    ranking_feature_diagnostics: list[dict[str, object]]


@dataclass(frozen=True, slots=True)
class _AcceptedOutcome:
    trade_id: str
    net_pnl: Decimal
    r_multiple: Decimal | None
    exit_reason: object


@dataclass(frozen=True, slots=True)
class _CounterfactualOutcome:
    net_pnl: Decimal
    r_multiple: Decimal | None
    exit_reason: object
    entry_price: Decimal
    exit_price: Decimal
    initial_risk_amount: Decimal | None


def build_all_signal_opportunity_diagnostics(
    result: Any,
    stock_data_by_symbol: Mapping[str, pd.DataFrame] | None = None,
) -> OpportunityDiagnostics:
    """Return all all-signal opportunity diagnostic export rows."""

    if stock_data_by_symbol is None:
        return _empty_diagnostics()

    normalized_data = _normalized_stock_data(stock_data_by_symbol, result.end_date)
    market_end_date = _effective_market_end_date(normalized_data)
    rejected_by_signal = _rejected_signal_queues(result)
    accepted_by_signal = _accepted_outcome_queues(result, normalized_data)

    rows: list[dict[str, object]] = []
    for signal in result.signals:
        rejected = _pop_rejected(rejected_by_signal, signal)
        accepted = None if rejected is not None else _pop_accepted(
            accepted_by_signal,
            signal,
        )
        rejection_reason = getattr(rejected, "reason", None)
        signal_status = _signal_status(rejection_reason, accepted)
        counterfactual = None
        if rejection_reason == _CAPACITY_REASON:
            counterfactual = _simulate_capacity_counterfactual(
                signal=signal,
                data=normalized_data.get(signal.symbol),
                starting_equity=getattr(result, "starting_equity", Decimal("0")),
                market_end_date=market_end_date,
            )
        row = _opportunity_row(
            result=result,
            signal=signal,
            status=signal_status,
            rejection_reason=rejection_reason,
            accepted=accepted,
            counterfactual=counterfactual,
            data=normalized_data.get(signal.symbol),
        )
        rows.append(row)

    return OpportunityDiagnostics(
        all_signal_opportunity_log=rows,
        accepted_vs_rejected_signal_summary=_accepted_vs_rejected_summary(rows),
        counterfactual_rejected_trade_summary=_counterfactual_summary(rows),
        counterfactual_by_year=_counterfactual_group_summary(rows, "year"),
        counterfactual_by_symbol=_counterfactual_group_summary(rows, "symbol"),
        same_day_candidate_pool_summary=_same_day_summary(rows),
        ranking_feature_diagnostics=_ranking_feature_diagnostics(rows),
    )


def _empty_diagnostics() -> OpportunityDiagnostics:
    return OpportunityDiagnostics(
        all_signal_opportunity_log=[],
        accepted_vs_rejected_signal_summary=[],
        counterfactual_rejected_trade_summary=[],
        counterfactual_by_year=[],
        counterfactual_by_symbol=[],
        same_day_candidate_pool_summary=[],
        ranking_feature_diagnostics=[],
    )


def _normalized_stock_data(
    stock_data_by_symbol: Mapping[str, pd.DataFrame],
    end_date: date,
) -> dict[str, pd.DataFrame]:
    output: dict[str, pd.DataFrame] = {}
    for symbol, data in stock_data_by_symbol.items():
        if data is None or data.empty:
            continue
        date_column = "date" if "date" in data.columns else "timestamp"
        if date_column not in data.columns:
            continue
        sorted_data = data.copy(deep=True).sort_values(date_column).reset_index(
            drop=True
        )
        row_dates = sorted_data.apply(_row_date, axis=1)
        output[symbol] = sorted_data.loc[row_dates <= end_date].reset_index(
            drop=True
        )
    return output


def _rejected_signal_queues(result: Any) -> dict[tuple[str, date, str], deque[Any]]:
    queues: dict[tuple[str, date, str], deque[Any]] = defaultdict(deque)
    for rejected in result.rejected_signals:
        if rejected.signal_date is None:
            continue
        queues[
            (rejected.symbol, rejected.signal_date, rejected.strategy_name)
        ].append(rejected)
    return queues


def _accepted_outcome_queues(
    result: Any,
    stock_data_by_symbol: Mapping[str, pd.DataFrame],
) -> dict[tuple[str, date, str], deque[_AcceptedOutcome]]:
    pnl_by_trade_id = {pnl.trade_id: pnl for pnl in result.trade_pnls}
    outcomes_by_entry: dict[tuple[str, date, str], deque[_AcceptedOutcome]] = (
        defaultdict(deque)
    )
    for trade in result.trades:
        pnl = pnl_by_trade_id.get(trade.trade_id)
        if pnl is None:
            continue
        outcomes_by_entry[(trade.symbol, trade.entry_date, trade.strategy_name)].append(
            _AcceptedOutcome(
                trade_id=trade.trade_id,
                net_pnl=pnl.net_pnl,
                r_multiple=_r_multiple(pnl),
                exit_reason=pnl.exit_reason,
            )
        )

    queues: dict[tuple[str, date, str], deque[_AcceptedOutcome]] = defaultdict(deque)
    for signal in result.signals:
        data = stock_data_by_symbol.get(signal.symbol)
        entry_date = _next_session_date(data, signal.generated_on)
        if entry_date is None:
            continue
        outcome_queue = outcomes_by_entry.get(
            (signal.symbol, entry_date, signal.strategy_name)
        )
        if not outcome_queue:
            continue
        queues[(signal.symbol, signal.generated_on, signal.strategy_name)].append(
            outcome_queue.popleft()
        )
    return queues


def _pop_rejected(
    queues: dict[tuple[str, date, str], deque[Any]],
    signal: Signal,
) -> Any | None:
    queue = queues.get((signal.symbol, signal.generated_on, signal.strategy_name))
    if not queue:
        return None
    return queue.popleft()


def _pop_accepted(
    queues: dict[tuple[str, date, str], deque[_AcceptedOutcome]],
    signal: Signal,
) -> _AcceptedOutcome | None:
    queue = queues.get((signal.symbol, signal.generated_on, signal.strategy_name))
    if not queue:
        return None
    return queue.popleft()


def _signal_status(
    rejection_reason: str | None,
    accepted: _AcceptedOutcome | None,
) -> str:
    if accepted is not None:
        return "ACCEPTED_TRADE"
    if rejection_reason == _CAPACITY_REASON:
        return "REJECTED_CAPACITY"
    if rejection_reason == _ACTIVE_SYMBOL_REASON:
        return "REJECTED_ACTIVE_SYMBOL"
    if rejection_reason is None:
        return "UNKNOWN"
    if rejection_reason.startswith("FILTER_"):
        return "REJECTED_FILTER"
    if "SETUP" in rejection_reason or "EXIT" in rejection_reason:
        return "REJECTED_SETUP"
    if "POSITION" in rejection_reason:
        return "REJECTED_POSITION"
    if "DATA" in rejection_reason:
        return "REJECTED_DATA"
    return "OTHER_REJECTED"


def _simulate_capacity_counterfactual(
    signal: Signal,
    data: pd.DataFrame | None,
    starting_equity: Decimal,
    market_end_date: date | None,
) -> _CounterfactualOutcome | None:
    if data is None or data.empty:
        return None
    try:
        setup = build_trade_setup(
            signal=signal,
            data=data,
            atr_window=14,
            atr_multiplier=Decimal("2"),
            reward_risk_ratio=Decimal("2"),
        )
    except ValueError:
        return None
    if setup is None:
        return None
    position_plan = build_position_plan(
        setup=setup,
        portfolio_equity=starting_equity,
        risk_per_trade=Decimal("0.01"),
    )
    if position_plan is None:
        return None
    open_trade = create_open_trade(
        position_plan,
        trade_id=(
            f"counterfactual-{signal.strategy_name}-"
            f"{signal.symbol}-{setup.entry_date.isoformat()}"
        ),
    )
    closed_trade = resolve_trade_exit(
        trade=open_trade,
        position_plan=position_plan,
        data=data,
        max_holding_sessions=20,
        backtest_end_date=market_end_date,
    )
    if closed_trade is None or closed_trade.exit_price is None:
        return None
    pnl = calculate_trade_pnl(
        trade=closed_trade,
        round_trip_cost_pct=Decimal("0.004"),
    )
    if pnl is None:
        return None
    return _CounterfactualOutcome(
        net_pnl=pnl.net_pnl,
        r_multiple=_r_multiple(pnl),
        exit_reason=pnl.exit_reason,
        entry_price=closed_trade.entry_price,
        exit_price=closed_trade.exit_price,
        initial_risk_amount=closed_trade.initial_risk_amount,
    )


def _opportunity_row(
    result: Any,
    signal: Signal,
    status: str,
    rejection_reason: str | None,
    accepted: _AcceptedOutcome | None,
    counterfactual: _CounterfactualOutcome | None,
    data: pd.DataFrame | None,
) -> dict[str, object]:
    metadata = signal.metadata
    features = _signal_time_features(signal, data)
    candidate_score = metadata.get("candidate_score")
    return {
        "symbol": signal.symbol,
        "signal_date": signal.generated_on,
        "generated_on": signal.generated_on,
        "strategy_name": signal.strategy_name,
        "strategy_variant": getattr(result, "strategy_variant", None),
        "signal_status": status,
        "rejection_reason": rejection_reason,
        "is_accepted_trade": status == "ACCEPTED_TRADE",
        "is_rejected_capacity": status == "REJECTED_CAPACITY",
        "is_rejected_active_symbol": status == "REJECTED_ACTIVE_SYMBOL",
        "is_counterfactual_simulated": counterfactual is not None,
        "entry_date": _next_session_date(data, signal.generated_on),
        "z_score": metadata.get("z_score"),
        "close": metadata.get("close", features.get("close")),
        "atr14": features.get("atr14"),
        "atr_pct": features.get("atr_pct"),
        "rolling_avg_volume_20": features.get("rolling_avg_volume_20"),
        "candidate_ranking_mode": metadata.get(
            "candidate_ranking_mode",
            getattr(result, "candidate_ranking_mode", None),
        ),
        "candidate_rank": metadata.get("candidate_rank"),
        "candidate_score": candidate_score,
        "candidate_pool_size_for_date": metadata.get(
            "candidate_pool_size_for_date"
        ),
        "accepted_trade_id": None if accepted is None else accepted.trade_id,
        "accepted_net_pnl": None if accepted is None else accepted.net_pnl,
        "accepted_r_multiple": None if accepted is None else accepted.r_multiple,
        "accepted_exit_reason": None
        if accepted is None
        else _enum_value(accepted.exit_reason),
        "counterfactual_net_pnl": None
        if counterfactual is None
        else counterfactual.net_pnl,
        "counterfactual_r_multiple": None
        if counterfactual is None
        else counterfactual.r_multiple,
        "counterfactual_exit_reason": None
        if counterfactual is None
        else _enum_value(counterfactual.exit_reason),
        "counterfactual_entry_price": None
        if counterfactual is None
        else counterfactual.entry_price,
        "counterfactual_exit_price": None
        if counterfactual is None
        else counterfactual.exit_price,
        "counterfactual_initial_risk_amount": None
        if counterfactual is None
        else counterfactual.initial_risk_amount,
        "year": signal.generated_on.year,
        "month": signal.generated_on.month,
    }


def _signal_time_features(
    signal: Signal,
    data: pd.DataFrame | None,
) -> dict[str, object]:
    if data is None or data.empty:
        return {}
    signal_index = _row_position(data, signal.generated_on)
    if signal_index is None:
        return {}
    row = data.iloc[signal_index]
    output: dict[str, object] = {"close": row.get("close")}
    try:
        atr_value = atr(data, 14).iloc[signal_index]
    except Exception:
        atr_value = None
    close = _to_decimal(row.get("close"))
    atr_decimal = _to_decimal(atr_value)
    if atr_decimal is not None:
        output["atr14"] = atr_decimal
    if atr_decimal is not None and close is not None and close > 0:
        output["atr_pct"] = (atr_decimal / close) * Decimal("100")
    if "volume" in data.columns:
        output["rolling_avg_volume_20"] = (
            data["volume"].rolling(20).mean().iloc[signal_index]
        )
    return output


def _accepted_vs_rejected_summary(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    grouped = {group: [] for group in _SUMMARY_GROUPS}
    for row in rows:
        grouped[_summary_group(row)].append(row)
    return [
        {"signal_group": group, **_row_pnl_summary(group_rows)}
        for group, group_rows in grouped.items()
    ]


def _summary_group(row: Mapping[str, object]) -> str:
    if row["signal_status"] == "ACCEPTED_TRADE":
        return "ACCEPTED_TRADE"
    if row["signal_status"] == "REJECTED_CAPACITY":
        return "REJECTED_CAPACITY_COUNTERFACTUAL"
    if row["signal_status"] == "REJECTED_ACTIVE_SYMBOL":
        return "REJECTED_ACTIVE_SYMBOL"
    return "OTHER_REJECTED"


def _counterfactual_summary(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    capacity_rows = [
        row for row in rows if row["signal_status"] == "REJECTED_CAPACITY"
    ]
    simulated = [
        row for row in capacity_rows if row["counterfactual_net_pnl"] is not None
    ]
    net_pnls = _net_pnl_values(simulated, "counterfactual_net_pnl")
    r_values = _decimal_values(simulated, "counterfactual_r_multiple")
    winning = tuple(value for value in net_pnls if value > 0)
    losing = tuple(value for value in net_pnls if value < 0)
    return [
        {
            "total_capacity_rejected": len(capacity_rows),
            "simulated_capacity_rejected": len(simulated),
            "simulation_success_pct": _ratio_pct(len(simulated), len(capacity_rows)),
            "counterfactual_net_pnl": sum(net_pnls, Decimal("0")),
            "counterfactual_gross_profit": sum(winning, Decimal("0")),
            "counterfactual_gross_loss": sum(losing, Decimal("0")),
            "counterfactual_profit_factor": _profit_factor(winning, losing),
            "counterfactual_win_rate_pct": _ratio_pct(len(winning), len(net_pnls)),
            "counterfactual_average_r": _average(r_values),
            "counterfactual_median_r": _median(r_values),
            "counterfactual_best_trade": max(net_pnls) if net_pnls else None,
            "counterfactual_worst_trade": min(net_pnls) if net_pnls else None,
        }
    ]


def _counterfactual_group_summary(
    rows: list[dict[str, object]],
    group_key: str,
) -> list[dict[str, object]]:
    grouped: dict[object, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        if row["signal_status"] == "REJECTED_CAPACITY":
            grouped[row[group_key]].append(row)
    return [
        {group_key: key, **_row_pnl_summary(group_rows, counterfactual_only=True)}
        for key, group_rows in sorted(grouped.items())
    ]


def _same_day_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[object, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[row["entry_date"]].append(row)
    output = []
    for entry_date, group_rows in sorted(
        grouped.items(),
        key=lambda item: "" if item[0] is None else str(item[0]),
    ):
        counterfactual_rows = [
            row
            for row in group_rows
            if row["counterfactual_net_pnl"] is not None
        ]
        best = _best_or_worst_counterfactual(counterfactual_rows, best=True)
        worst = _best_or_worst_counterfactual(counterfactual_rows, best=False)
        scores = _decimal_values(group_rows, "candidate_score")
        output.append(
            {
                "entry_date": entry_date,
                "total_signal_count": len(group_rows),
                "accepted_trade_count": _count_status(group_rows, "ACCEPTED_TRADE"),
                "rejected_capacity_count": _count_status(
                    group_rows,
                    "REJECTED_CAPACITY",
                ),
                "rejected_active_symbol_count": _count_status(
                    group_rows,
                    "REJECTED_ACTIVE_SYMBOL",
                ),
                "other_rejected_count": sum(
                    1
                    for row in group_rows
                    if row["signal_status"]
                    not in {
                        "ACCEPTED_TRADE",
                        "REJECTED_CAPACITY",
                        "REJECTED_ACTIVE_SYMBOL",
                    }
                ),
                "accepted_net_pnl": sum(
                    _net_pnl_values(group_rows, "accepted_net_pnl"),
                    Decimal("0"),
                ),
                "rejected_capacity_counterfactual_net_pnl": sum(
                    _net_pnl_values(group_rows, "counterfactual_net_pnl"),
                    Decimal("0"),
                ),
                "best_counterfactual_symbol": None if best is None else best["symbol"],
                "best_counterfactual_net_pnl": None
                if best is None
                else best["counterfactual_net_pnl"],
                "worst_counterfactual_symbol": None
                if worst is None
                else worst["symbol"],
                "worst_counterfactual_net_pnl": None
                if worst is None
                else worst["counterfactual_net_pnl"],
                "average_candidate_score": _average(scores),
                "max_candidate_score": max(scores) if scores else None,
                "min_candidate_score": min(scores) if scores else None,
            }
        )
    return output


def _ranking_feature_diagnostics(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    specs = (
        ("z_score", _z_score_bucket),
        ("atr_pct", _atr_pct_bucket),
        ("rolling_avg_volume_20", _volume_bucket),
        ("year", lambda value: value),
        ("candidate_pool_size_for_date", _pool_size_bucket),
    )
    output: list[dict[str, object]] = []
    for feature_name, bucket_func in specs:
        grouped: dict[tuple[object, str], list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            bucket = bucket_func(row.get(feature_name))
            grouped[(bucket, _summary_group(row))].append(row)
        for (bucket, signal_group), group_rows in sorted(
            grouped.items(),
            key=lambda item: (str(item[0][0]), item[0][1]),
        ):
            output.append(
                {
                    "feature_name": feature_name,
                    "bucket": bucket,
                    "signal_group": signal_group,
                    **_row_pnl_summary(group_rows),
                }
            )
    return output


def _row_pnl_summary(
    rows: list[dict[str, object]],
    counterfactual_only: bool = False,
) -> dict[str, object]:
    pnl_key = "counterfactual_net_pnl" if counterfactual_only else None
    r_key = "counterfactual_r_multiple" if counterfactual_only else None
    net_pnls: list[Decimal] = []
    r_values: list[Decimal] = []
    for row in rows:
        row_pnl_key = pnl_key or (
            "accepted_net_pnl"
            if row["signal_status"] == "ACCEPTED_TRADE"
            else "counterfactual_net_pnl"
        )
        row_r_key = r_key or (
            "accepted_r_multiple"
            if row["signal_status"] == "ACCEPTED_TRADE"
            else "counterfactual_r_multiple"
        )
        pnl = _to_decimal(row.get(row_pnl_key))
        r_multiple = _to_decimal(row.get(row_r_key))
        if pnl is not None:
            net_pnls.append(pnl)
        if r_multiple is not None:
            r_values.append(r_multiple)
    winning = tuple(value for value in net_pnls if value > 0)
    losing = tuple(value for value in net_pnls if value < 0)
    return {
        "signal_count": len(rows),
        "simulated_count": len(net_pnls),
        "gross_profit": sum(winning, Decimal("0")),
        "gross_loss": sum(losing, Decimal("0")),
        "net_pnl": sum(net_pnls, Decimal("0")),
        "win_count": len(winning),
        "loss_count": len(losing),
        "win_rate_pct": _ratio_pct(len(winning), len(net_pnls)),
        "average_net_pnl": _average(tuple(net_pnls)),
        "median_net_pnl": _median(tuple(net_pnls)),
        "average_r_multiple": _average(tuple(r_values)),
        "median_r_multiple": _median(tuple(r_values)),
        "profit_factor": _profit_factor(winning, losing),
    }


def _count_status(rows: Iterable[Mapping[str, object]], status: str) -> int:
    return sum(1 for row in rows if row["signal_status"] == status)


def _best_or_worst_counterfactual(
    rows: list[dict[str, object]],
    best: bool,
) -> dict[str, object] | None:
    if not rows:
        return None
    return sorted(
        rows,
        key=lambda row: _to_decimal(row["counterfactual_net_pnl"]) or Decimal("0"),
        reverse=best,
    )[0]


def _net_pnl_values(
    rows: Iterable[Mapping[str, object]],
    key: str,
) -> tuple[Decimal, ...]:
    return tuple(
        value
        for value in (_to_decimal(row.get(key)) for row in rows)
        if value is not None
    )


def _decimal_values(
    rows: Iterable[Mapping[str, object]],
    key: str,
) -> tuple[Decimal, ...]:
    return _net_pnl_values(rows, key)


def _r_multiple(pnl: TradePnL) -> Decimal | None:
    initial_risk = _to_decimal(getattr(pnl, "initial_risk_amount", None))
    if initial_risk is None or initial_risk <= 0:
        return None
    return pnl.net_pnl / initial_risk


def _next_session_date(data: pd.DataFrame | None, signal_date: date) -> date | None:
    if data is None or data.empty:
        return None
    signal_index = _row_position(data, signal_date)
    if signal_index is None or signal_index + 1 >= len(data):
        return None
    return _row_date(data.iloc[signal_index + 1])


def _row_position(data: pd.DataFrame, target_date: date) -> int | None:
    for position, (_, row) in enumerate(data.iterrows()):
        if _row_date(row) == target_date:
            return position
    return None


def _effective_market_end_date(
    stock_data_by_symbol: Mapping[str, pd.DataFrame],
) -> date | None:
    dates: list[date] = []
    for data in stock_data_by_symbol.values():
        if data.empty:
            continue
        dates.extend(_row_date(row) for _, row in data.iterrows())
    if not dates:
        return None
    return max(dates)


def _row_date(row: pd.Series) -> date:
    value = row["date"] if "date" in row.index else row["timestamp"]
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()


def _z_score_bucket(value: object) -> str:
    decimal = _to_decimal(value)
    if decimal is None:
        return "UNKNOWN"
    if decimal <= Decimal("-3"):
        return "<= -3"
    if decimal <= Decimal("-2.5"):
        return "-3 to -2.5"
    if decimal <= Decimal("-2"):
        return "-2.5 to -2"
    return "> -2"


def _atr_pct_bucket(value: object) -> str:
    decimal = _to_decimal(value)
    if decimal is None:
        return "UNKNOWN"
    if decimal < Decimal("2"):
        return "< 2"
    if decimal < Decimal("4"):
        return "2 to 4"
    if decimal < Decimal("6"):
        return "4 to 6"
    return ">= 6"


def _volume_bucket(value: object) -> str:
    decimal = _to_decimal(value)
    if decimal is None:
        return "UNKNOWN"
    if decimal < Decimal("100000"):
        return "< 100k"
    if decimal < Decimal("1000000"):
        return "100k to 1m"
    if decimal < Decimal("10000000"):
        return "1m to 10m"
    return ">= 10m"


def _pool_size_bucket(value: object) -> str:
    decimal = _to_decimal(value)
    if decimal is None:
        return "UNKNOWN"
    if decimal <= 1:
        return "1"
    if decimal <= 3:
        return "2 to 3"
    if decimal <= 5:
        return "4 to 5"
    if decimal <= 10:
        return "6 to 10"
    return "> 10"


def _average(values: tuple[Decimal, ...]) -> Decimal | None:
    if not values:
        return None
    return sum(values, Decimal("0")) / Decimal(len(values))


def _median(values: tuple[Decimal, ...]) -> Decimal | None:
    if not values:
        return None
    sorted_values = sorted(values)
    midpoint = len(sorted_values) // 2
    if len(sorted_values) % 2 == 1:
        return sorted_values[midpoint]
    return (sorted_values[midpoint - 1] + sorted_values[midpoint]) / Decimal("2")


def _profit_factor(
    winning: Iterable[Decimal],
    losing: Iterable[Decimal],
) -> Decimal | None:
    gross_profit = sum(winning, Decimal("0"))
    gross_loss = sum(losing, Decimal("0"))
    if gross_loss == 0:
        return None if gross_profit == 0 else gross_profit
    return gross_profit / abs(gross_loss)


def _ratio_pct(numerator: int, denominator: int) -> Decimal:
    if denominator <= 0:
        return Decimal("0")
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


def _enum_value(value: Any) -> object:
    return getattr(value, "value", value)
