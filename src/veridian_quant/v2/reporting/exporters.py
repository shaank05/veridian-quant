"""CSV exporters for Veridian Quant v2 backtest artifacts.

Exporter functions serialize already-computed research results. They do not run
strategies, load data, calculate metrics, or mutate backtest outputs.
"""

from pathlib import Path
from time import perf_counter
from typing import Any, Mapping

import pandas as pd

from veridian_quant.v2.reporting.all_signal_opportunity import (
    OPPORTUNITY_EXPORT_COLUMNS,
    build_all_signal_opportunity_diagnostics,
)
from veridian_quant.v2.reporting.context import (
    R_CONTEXT_BUCKET_COLUMNS,
    TRADE_SIGNAL_CONTEXT_COLUMNS,
    build_r_by_atr_stretch_context_rows,
    build_r_by_consecutive_down_closes_rows,
    build_r_by_drawdown_depth_context_rows,
    build_r_by_fresh_low_context_rows,
    build_r_by_nifty_trend_context_rows,
    build_r_by_pre_signal_return_context_rows,
    build_r_by_relative_strength_context_rows,
    build_r_by_signal_candle_context_rows,
    build_r_by_stock_trend_context_rows,
    build_r_by_zscore_depth_rows,
    build_trade_signal_context_rows,
)
from veridian_quant.v2.reporting.diagnostics import (
    EXIT_REASON_SUMMARY_COLUMNS,
    REJECTION_SUMMARY_COLUMNS,
    R_MULTIPLE_BY_EXIT_REASON_COLUMNS,
    R_MULTIPLE_BY_SYMBOL_COLUMNS,
    R_MULTIPLE_BY_SYMBOL_YEAR_COLUMNS,
    R_MULTIPLE_BY_YEAR_COLUMNS,
    R_MULTIPLE_SUMMARY_COLUMNS,
    SYMBOL_SUMMARY_COLUMNS,
    YEARLY_SUMMARY_COLUMNS,
    build_exit_reason_summary_rows,
    build_r_multiple_by_exit_reason_rows,
    build_r_multiple_by_symbol_rows,
    build_r_multiple_by_symbol_year_rows,
    build_r_multiple_by_year_rows,
    build_r_multiple_summary_rows,
    build_rejection_summary_rows,
    build_symbol_summary_rows,
    build_yearly_summary_rows,
)
from veridian_quant.v2.reporting.filter_simulation import (
    CANDIDATE_FILTER_SIMULATION_BY_SYMBOL_COLUMNS,
    CANDIDATE_FILTER_SIMULATION_BY_YEAR_COLUMNS,
    CANDIDATE_FILTER_SIMULATION_COLUMNS,
    CANDIDATE_FILTER_SIMULATION_REJECTED_TRADES_COLUMNS,
    build_candidate_filter_simulation_by_symbol_rows,
    build_candidate_filter_simulation_by_year_rows,
    build_candidate_filter_simulation_rejected_trade_rows,
    build_candidate_filter_simulation_rows,
)
from veridian_quant.v2.reporting.metrics import calculate_performance_summary
from veridian_quant.v2.reporting.s2_failure_audit import (
    S2_FAILURE_AUDIT_BY_MONTH_COLUMNS,
    S2_FAILURE_AUDIT_BY_YEAR_COLUMNS,
    S2_FAILURE_AUDIT_COMPARISON_COLUMNS,
    S2_FAILURE_AUDIT_STATE_COMPONENT_COLUMNS,
    build_s2_failure_audit_by_exit_reason_rows,
    build_s2_failure_audit_by_month_rows,
    build_s2_failure_audit_by_state_component_rows,
    build_s2_failure_audit_by_state_label_rows,
    build_s2_failure_audit_by_symbol_rows,
    build_s2_failure_audit_by_year_rows,
    build_s2_failure_audit_context_comparison_rows,
)
from veridian_quant.v2.reporting.s2_markov_filter_simulation import (
    S2_MARKOV_FILTER_SIMULATION_BY_SYMBOL_COLUMNS,
    S2_MARKOV_FILTER_SIMULATION_BY_YEAR_COLUMNS,
    S2_MARKOV_FILTER_SIMULATION_COLUMNS,
    S2_MARKOV_FILTER_SIMULATION_REJECTED_TRADES_COLUMNS,
    S2_MARKOV_STATE_COMPONENT_SUMMARY_COLUMNS,
    S2_MARKOV_STATE_LABEL_SUMMARY_COLUMNS,
    build_s2_markov_filter_simulation_by_symbol_rows,
    build_s2_markov_filter_simulation_by_year_rows,
    build_s2_markov_filter_simulation_rejected_trade_rows,
    build_s2_markov_filter_simulation_rows,
    build_s2_markov_state_component_summary_rows,
    build_s2_markov_state_label_summary_rows,
)


TRADE_LOG_COLUMNS = [
    "trade_id",
    "symbol",
    "entry_date",
    "entry_price",
    "quantity",
    "stop_loss",
    "target_price",
    "per_share_risk",
    "initial_risk_amount",
    "planned_reward_amount",
    "reward_risk_ratio",
    "exit_date",
    "exit_price",
    "exit_reason",
    "strategy_name",
    "candidate_ranking_mode",
    "candidate_rank",
    "candidate_score",
    "candidate_pool_size_for_date",
]
TRADE_PNL_LOG_COLUMNS = [
    "trade_id",
    "symbol",
    "entry_date",
    "exit_date",
    "quantity",
    "stop_loss",
    "target_price",
    "per_share_risk",
    "initial_risk_amount",
    "planned_reward_amount",
    "reward_risk_ratio",
    "gross_pnl",
    "gross_return_pct",
    "total_cost",
    "net_pnl",
    "net_return_pct",
    "exit_reason",
    "candidate_ranking_mode",
    "candidate_rank",
    "candidate_score",
    "candidate_pool_size_for_date",
]
SIGNAL_LOG_COLUMNS = [
    "symbol",
    "generated_on",
    "signal_type",
    "strategy_name",
    "reason",
    "z_score",
    "zscore_window",
    "entry_threshold",
    "close",
    "candidate_ranking_mode",
    "candidate_rank",
    "candidate_score",
    "candidate_score_z",
    "candidate_score_liquidity",
    "candidate_score_atr",
    "candidate_pool_size_for_date",
    "s2_candidate_ranking_mode",
    "s2_candidate_rank",
    "s2_candidate_score",
    "s2_score_state_edge",
    "s2_score_state_quality",
    "s2_score_context",
    "s2_score_penalty",
    "strategy_family",
    "state_label",
    "state_lookback_sessions",
    "state_observation_count",
    "forward_return_sessions",
    "positive_return_threshold_pct",
    "positive_transition_probability",
    "average_forward_return_pct",
    "median_forward_return_pct",
    "current_5d_return_pct",
    "current_atr_pct",
    "current_drawdown_60d_pct",
    "current_close_vs_60d_low_pct",
    "markov_signal_filter",
    "markov_filter_decision",
]
REJECTED_SIGNALS_COLUMNS = [
    "symbol",
    "signal_date",
    "strategy_name",
    "reason",
    "candidate_ranking_mode",
    "candidate_rank",
    "candidate_score",
    "candidate_pool_size_for_date",
    "markov_signal_filter",
    "markov_filter_decision",
]
EQUITY_CURVE_COLUMNS = ["date", "equity", "realized_pnl"]
SUMMARY_COLUMNS = [
    "strategy_name",
    "strategy_variant",
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


def export_portfolio_backtest_csvs(
    result: Any,
    output_dir: str | Path,
    stock_data_by_symbol: Mapping[str, pd.DataFrame] | None = None,
    nifty_data: pd.DataFrame | None = None,
    progress_reporter: object | None = None,
    include_all_signal_diagnostics: bool = True,
) -> dict[str, Path]:
    """Write standard portfolio backtest CSV artifacts and return file paths."""

    export_started = perf_counter()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    exports = {
        "trade_log": output_path / "trade_log.csv",
        "trade_pnl_log": output_path / "trade_pnl_log.csv",
        "signal_log": output_path / "signal_log.csv",
        "rejected_signals": output_path / "rejected_signals.csv",
        "equity_curve": output_path / "equity_curve.csv",
        "summary": output_path / "summary.csv",
        "exit_reason_summary": output_path / "exit_reason_summary.csv",
        "symbol_summary": output_path / "symbol_summary.csv",
        "yearly_summary": output_path / "yearly_summary.csv",
        "rejection_summary": output_path / "rejection_summary.csv",
        "r_multiple_summary": output_path / "r_multiple_summary.csv",
        "r_multiple_by_exit_reason": output_path / "r_multiple_by_exit_reason.csv",
        "r_multiple_by_symbol": output_path / "r_multiple_by_symbol.csv",
        "r_multiple_by_year": output_path / "r_multiple_by_year.csv",
        "r_multiple_by_symbol_year": output_path
        / "r_multiple_by_symbol_year.csv",
        "trade_signal_context": output_path / "trade_signal_context.csv",
        "r_by_stock_trend_context": output_path
        / "r_by_stock_trend_context.csv",
        "r_by_nifty_trend_context": output_path
        / "r_by_nifty_trend_context.csv",
        "r_by_relative_strength_context": output_path
        / "r_by_relative_strength_context.csv",
        "r_by_zscore_depth": output_path / "r_by_zscore_depth.csv",
        "r_by_pre_signal_return_context": output_path
        / "r_by_pre_signal_return_context.csv",
        "r_by_drawdown_depth_context": output_path
        / "r_by_drawdown_depth_context.csv",
        "r_by_atr_stretch_context": output_path
        / "r_by_atr_stretch_context.csv",
        "r_by_signal_candle_context": output_path
        / "r_by_signal_candle_context.csv",
        "r_by_consecutive_down_closes": output_path
        / "r_by_consecutive_down_closes.csv",
        "r_by_fresh_low_context": output_path / "r_by_fresh_low_context.csv",
        "candidate_filter_simulation": output_path
        / "candidate_filter_simulation.csv",
        "candidate_filter_simulation_by_year": output_path
        / "candidate_filter_simulation_by_year.csv",
        "candidate_filter_simulation_by_symbol": output_path
        / "candidate_filter_simulation_by_symbol.csv",
        "candidate_filter_simulation_rejected_trades": output_path
        / "candidate_filter_simulation_rejected_trades.csv",
        "s2_markov_filter_simulation": output_path
        / "s2_markov_filter_simulation.csv",
        "s2_markov_filter_simulation_by_year": output_path
        / "s2_markov_filter_simulation_by_year.csv",
        "s2_markov_filter_simulation_by_symbol": output_path
        / "s2_markov_filter_simulation_by_symbol.csv",
        "s2_markov_filter_simulation_rejected_trades": output_path
        / "s2_markov_filter_simulation_rejected_trades.csv",
        "s2_markov_state_component_summary": output_path
        / "s2_markov_state_component_summary.csv",
        "s2_markov_state_label_summary": output_path
        / "s2_markov_state_label_summary.csv",
        "s2_failure_audit_by_year": output_path
        / "s2_failure_audit_by_year.csv",
        "s2_failure_audit_by_month": output_path
        / "s2_failure_audit_by_month.csv",
        "s2_failure_audit_by_state_label": output_path
        / "s2_failure_audit_by_state_label.csv",
        "s2_failure_audit_by_state_component": output_path
        / "s2_failure_audit_by_state_component.csv",
        "s2_failure_audit_by_exit_reason": output_path
        / "s2_failure_audit_by_exit_reason.csv",
        "s2_failure_audit_by_symbol": output_path
        / "s2_failure_audit_by_symbol.csv",
        "s2_failure_audit_context_comparison": output_path
        / "s2_failure_audit_context_comparison.csv",
        "all_signal_opportunity_log": output_path
        / "all_signal_opportunity_log.csv",
        "accepted_vs_rejected_signal_summary": output_path
        / "accepted_vs_rejected_signal_summary.csv",
        "counterfactual_rejected_trade_summary": output_path
        / "counterfactual_rejected_trade_summary.csv",
        "counterfactual_by_year": output_path / "counterfactual_by_year.csv",
        "counterfactual_by_symbol": output_path / "counterfactual_by_symbol.csv",
        "same_day_candidate_pool_summary": output_path
        / "same_day_candidate_pool_summary.csv",
        "ranking_feature_diagnostics": output_path
        / "ranking_feature_diagnostics.csv",
    }

    standard_started = perf_counter()
    _write_csv(exports["trade_log"], _trade_rows(result), TRADE_LOG_COLUMNS)
    _write_csv(
        exports["trade_pnl_log"],
        _trade_pnl_rows(result),
        TRADE_PNL_LOG_COLUMNS,
    )
    _write_csv(exports["signal_log"], _signal_rows(result), SIGNAL_LOG_COLUMNS)
    _write_csv(
        exports["rejected_signals"],
        _rejected_signal_rows(result),
        REJECTED_SIGNALS_COLUMNS,
    )
    _write_csv(
        exports["equity_curve"],
        _equity_curve_rows(result),
        EQUITY_CURVE_COLUMNS,
    )
    _write_csv(exports["summary"], _summary_rows(result), SUMMARY_COLUMNS)
    _log_elapsed(
        progress_reporter,
        "Finished standard trade/signal/equity/summary exports",
        standard_started,
    )
    diagnostic_started = perf_counter()
    _write_csv(
        exports["exit_reason_summary"],
        build_exit_reason_summary_rows(result),
        EXIT_REASON_SUMMARY_COLUMNS,
    )
    _write_csv(
        exports["symbol_summary"],
        build_symbol_summary_rows(result),
        SYMBOL_SUMMARY_COLUMNS,
    )
    _write_csv(
        exports["yearly_summary"],
        build_yearly_summary_rows(result),
        YEARLY_SUMMARY_COLUMNS,
    )
    _write_csv(
        exports["rejection_summary"],
        build_rejection_summary_rows(result),
        REJECTION_SUMMARY_COLUMNS,
    )
    _log_elapsed(
        progress_reporter,
        "Finished standard diagnostic exports",
        diagnostic_started,
    )
    r_multiple_started = perf_counter()
    _write_csv(
        exports["r_multiple_summary"],
        build_r_multiple_summary_rows(result),
        R_MULTIPLE_SUMMARY_COLUMNS,
    )
    _write_csv(
        exports["r_multiple_by_exit_reason"],
        build_r_multiple_by_exit_reason_rows(result),
        R_MULTIPLE_BY_EXIT_REASON_COLUMNS,
    )
    _write_csv(
        exports["r_multiple_by_symbol"],
        build_r_multiple_by_symbol_rows(result),
        R_MULTIPLE_BY_SYMBOL_COLUMNS,
    )
    _write_csv(
        exports["r_multiple_by_year"],
        build_r_multiple_by_year_rows(result),
        R_MULTIPLE_BY_YEAR_COLUMNS,
    )
    _write_csv(
        exports["r_multiple_by_symbol_year"],
        build_r_multiple_by_symbol_year_rows(result),
        R_MULTIPLE_BY_SYMBOL_YEAR_COLUMNS,
    )
    _log_elapsed(
        progress_reporter,
        "Finished R multiple diagnostics",
        r_multiple_started,
    )

    trade_context_started = perf_counter()
    trade_context_rows = build_trade_signal_context_rows(
        result,
        stock_data_by_symbol=stock_data_by_symbol,
        nifty_data=nifty_data,
    )
    _write_csv(
        exports["trade_signal_context"],
        trade_context_rows,
        TRADE_SIGNAL_CONTEXT_COLUMNS,
    )
    _log_elapsed(
        progress_reporter,
        "Finished trade signal context build/export",
        trade_context_started,
    )
    r_context_started = perf_counter()
    _write_csv(
        exports["r_by_stock_trend_context"],
        build_r_by_stock_trend_context_rows(trade_context_rows),
        R_CONTEXT_BUCKET_COLUMNS,
    )
    _write_csv(
        exports["r_by_nifty_trend_context"],
        build_r_by_nifty_trend_context_rows(trade_context_rows),
        R_CONTEXT_BUCKET_COLUMNS,
    )
    _write_csv(
        exports["r_by_relative_strength_context"],
        build_r_by_relative_strength_context_rows(trade_context_rows),
        R_CONTEXT_BUCKET_COLUMNS,
    )
    _write_csv(
        exports["r_by_zscore_depth"],
        build_r_by_zscore_depth_rows(trade_context_rows),
        R_CONTEXT_BUCKET_COLUMNS,
    )
    _write_csv(
        exports["r_by_pre_signal_return_context"],
        build_r_by_pre_signal_return_context_rows(trade_context_rows),
        R_CONTEXT_BUCKET_COLUMNS,
    )
    _write_csv(
        exports["r_by_drawdown_depth_context"],
        build_r_by_drawdown_depth_context_rows(trade_context_rows),
        R_CONTEXT_BUCKET_COLUMNS,
    )
    _write_csv(
        exports["r_by_atr_stretch_context"],
        build_r_by_atr_stretch_context_rows(trade_context_rows),
        R_CONTEXT_BUCKET_COLUMNS,
    )
    _write_csv(
        exports["r_by_signal_candle_context"],
        build_r_by_signal_candle_context_rows(trade_context_rows),
        R_CONTEXT_BUCKET_COLUMNS,
    )
    _write_csv(
        exports["r_by_consecutive_down_closes"],
        build_r_by_consecutive_down_closes_rows(trade_context_rows),
        R_CONTEXT_BUCKET_COLUMNS,
    )
    _write_csv(
        exports["r_by_fresh_low_context"],
        build_r_by_fresh_low_context_rows(trade_context_rows),
        R_CONTEXT_BUCKET_COLUMNS,
    )
    _log_elapsed(
        progress_reporter,
        "Finished R context reports",
        r_context_started,
    )
    candidate_filter_started = perf_counter()
    _write_csv(
        exports["candidate_filter_simulation"],
        build_candidate_filter_simulation_rows(trade_context_rows),
        CANDIDATE_FILTER_SIMULATION_COLUMNS,
    )
    _write_csv(
        exports["candidate_filter_simulation_by_year"],
        build_candidate_filter_simulation_by_year_rows(trade_context_rows),
        CANDIDATE_FILTER_SIMULATION_BY_YEAR_COLUMNS,
    )
    _write_csv(
        exports["candidate_filter_simulation_by_symbol"],
        build_candidate_filter_simulation_by_symbol_rows(trade_context_rows),
        CANDIDATE_FILTER_SIMULATION_BY_SYMBOL_COLUMNS,
    )
    _write_csv(
        exports["candidate_filter_simulation_rejected_trades"],
        build_candidate_filter_simulation_rejected_trade_rows(trade_context_rows),
        CANDIDATE_FILTER_SIMULATION_REJECTED_TRADES_COLUMNS,
    )
    _log_elapsed(
        progress_reporter,
        "Finished candidate filter simulation",
        candidate_filter_started,
    )
    s2_filter_started = perf_counter()
    _write_csv(
        exports["s2_markov_filter_simulation"],
        build_s2_markov_filter_simulation_rows(trade_context_rows),
        S2_MARKOV_FILTER_SIMULATION_COLUMNS,
    )
    _write_csv(
        exports["s2_markov_filter_simulation_by_year"],
        build_s2_markov_filter_simulation_by_year_rows(trade_context_rows),
        S2_MARKOV_FILTER_SIMULATION_BY_YEAR_COLUMNS,
    )
    _write_csv(
        exports["s2_markov_filter_simulation_by_symbol"],
        build_s2_markov_filter_simulation_by_symbol_rows(trade_context_rows),
        S2_MARKOV_FILTER_SIMULATION_BY_SYMBOL_COLUMNS,
    )
    _write_csv(
        exports["s2_markov_filter_simulation_rejected_trades"],
        build_s2_markov_filter_simulation_rejected_trade_rows(trade_context_rows),
        S2_MARKOV_FILTER_SIMULATION_REJECTED_TRADES_COLUMNS,
    )
    _write_csv(
        exports["s2_markov_state_component_summary"],
        build_s2_markov_state_component_summary_rows(trade_context_rows),
        S2_MARKOV_STATE_COMPONENT_SUMMARY_COLUMNS,
    )
    _write_csv(
        exports["s2_markov_state_label_summary"],
        build_s2_markov_state_label_summary_rows(trade_context_rows),
        S2_MARKOV_STATE_LABEL_SUMMARY_COLUMNS,
    )
    _log_elapsed(
        progress_reporter,
        "Finished S2 Markov filter simulation",
        s2_filter_started,
    )
    s2_failure_audit_started = perf_counter()
    _write_csv(
        exports["s2_failure_audit_by_year"],
        build_s2_failure_audit_by_year_rows(trade_context_rows),
        S2_FAILURE_AUDIT_BY_YEAR_COLUMNS,
    )
    _write_csv(
        exports["s2_failure_audit_by_month"],
        build_s2_failure_audit_by_month_rows(trade_context_rows),
        S2_FAILURE_AUDIT_BY_MONTH_COLUMNS,
    )
    _write_csv(
        exports["s2_failure_audit_by_state_label"],
        build_s2_failure_audit_by_state_label_rows(trade_context_rows),
        S2_FAILURE_AUDIT_COMPARISON_COLUMNS,
    )
    _write_csv(
        exports["s2_failure_audit_by_state_component"],
        build_s2_failure_audit_by_state_component_rows(trade_context_rows),
        S2_FAILURE_AUDIT_STATE_COMPONENT_COLUMNS,
    )
    _write_csv(
        exports["s2_failure_audit_by_exit_reason"],
        build_s2_failure_audit_by_exit_reason_rows(trade_context_rows),
        S2_FAILURE_AUDIT_COMPARISON_COLUMNS,
    )
    _write_csv(
        exports["s2_failure_audit_by_symbol"],
        build_s2_failure_audit_by_symbol_rows(trade_context_rows),
        S2_FAILURE_AUDIT_COMPARISON_COLUMNS,
    )
    _write_csv(
        exports["s2_failure_audit_context_comparison"],
        build_s2_failure_audit_context_comparison_rows(trade_context_rows),
        S2_FAILURE_AUDIT_COMPARISON_COLUMNS,
    )
    _log_elapsed(
        progress_reporter,
        "Finished S2 failure audit diagnostics",
        s2_failure_audit_started,
    )

    if include_all_signal_diagnostics:
        opportunity_started = perf_counter()
        opportunity_diagnostics = build_all_signal_opportunity_diagnostics(
            result,
            stock_data_by_symbol=stock_data_by_symbol,
        )
        for export_name, columns in OPPORTUNITY_EXPORT_COLUMNS.items():
            _write_csv(
                exports[export_name],
                getattr(opportunity_diagnostics, export_name),
                columns,
            )
        _log_elapsed(
            progress_reporter,
            "Finished all-signal opportunity diagnostics",
            opportunity_started,
        )
    else:
        for export_name, columns in OPPORTUNITY_EXPORT_COLUMNS.items():
            _write_csv(exports[export_name], [], columns)
        _log_info(progress_reporter, "Skipped all-signal opportunity diagnostics")
    _log_elapsed(progress_reporter, "Finished total CSV export", export_started)
    return exports


def _write_csv(
    path: Path,
    rows: list[Mapping[str, object]],
    columns: list[str],
) -> None:
    """Write rows to CSV, preserving headers for empty outputs."""

    pd.DataFrame(rows, columns=columns).to_csv(path, index=False)


def _log_elapsed(
    progress_reporter: object | None,
    message: str,
    started: float,
) -> None:
    """Log elapsed export time when a reporter is supplied."""

    if progress_reporter is None or not hasattr(progress_reporter, "info"):
        return
    progress_reporter.info(f"{message} in {perf_counter() - started:.2f}s")


def _log_info(progress_reporter: object | None, message: str) -> None:
    if progress_reporter is None or not hasattr(progress_reporter, "info"):
        return
    progress_reporter.info(message)


def _trade_rows(result: Any) -> list[dict[str, object]]:
    """Return serialized trade rows."""

    return [
        {
            "trade_id": trade.trade_id,
            "symbol": trade.symbol,
            "entry_date": trade.entry_date,
            "entry_price": trade.entry_price,
            "quantity": trade.quantity,
            "stop_loss": getattr(trade, "stop_loss", None),
            "target_price": getattr(trade, "target_price", None),
            "per_share_risk": getattr(trade, "per_share_risk", None),
            "initial_risk_amount": getattr(trade, "initial_risk_amount", None),
            "planned_reward_amount": getattr(
                trade,
                "planned_reward_amount",
                None,
            ),
            "reward_risk_ratio": getattr(trade, "reward_risk_ratio", None),
            "exit_date": trade.exit_date,
            "exit_price": trade.exit_price,
            "exit_reason": _enum_value(trade.exit_reason),
            "strategy_name": trade.strategy_name,
            "candidate_ranking_mode": getattr(
                trade,
                "candidate_ranking_mode",
                None,
            ),
            "candidate_rank": getattr(trade, "candidate_rank", None),
            "candidate_score": getattr(trade, "candidate_score", None),
            "candidate_pool_size_for_date": getattr(
                trade,
                "candidate_pool_size_for_date",
                None,
            ),
        }
        for trade in result.trades
    ]


def _trade_pnl_rows(result: Any) -> list[dict[str, object]]:
    """Return serialized trade PnL rows."""

    return [
        {
            "trade_id": pnl.trade_id,
            "symbol": pnl.symbol,
            "entry_date": pnl.entry_date,
            "exit_date": pnl.exit_date,
            "quantity": pnl.quantity,
            "stop_loss": getattr(pnl, "stop_loss", None),
            "target_price": getattr(pnl, "target_price", None),
            "per_share_risk": getattr(pnl, "per_share_risk", None),
            "initial_risk_amount": getattr(pnl, "initial_risk_amount", None),
            "planned_reward_amount": getattr(
                pnl,
                "planned_reward_amount",
                None,
            ),
            "reward_risk_ratio": getattr(pnl, "reward_risk_ratio", None),
            "gross_pnl": pnl.gross_pnl,
            "gross_return_pct": pnl.gross_return_pct,
            "total_cost": pnl.total_cost,
            "net_pnl": pnl.net_pnl,
            "net_return_pct": pnl.net_return_pct,
            "exit_reason": _enum_value(pnl.exit_reason),
            "candidate_ranking_mode": getattr(
                pnl,
                "candidate_ranking_mode",
                None,
            ),
            "candidate_rank": getattr(pnl, "candidate_rank", None),
            "candidate_score": getattr(pnl, "candidate_score", None),
            "candidate_pool_size_for_date": getattr(
                pnl,
                "candidate_pool_size_for_date",
                None,
            ),
        }
        for pnl in result.trade_pnls
    ]


def _signal_rows(result: Any) -> list[dict[str, object]]:
    """Return serialized signal rows."""

    rows: list[dict[str, object]] = []
    for signal in result.signals:
        metadata = signal.metadata
        rows.append(
            {
                "symbol": signal.symbol,
                "generated_on": signal.generated_on,
                "signal_type": _enum_value(signal.signal_type),
                "strategy_name": signal.strategy_name,
                "reason": signal.reason,
                "z_score": metadata.get("z_score"),
                "zscore_window": metadata.get("zscore_window"),
                "entry_threshold": metadata.get("entry_threshold"),
                "close": metadata.get("close"),
                "candidate_ranking_mode": metadata.get("candidate_ranking_mode"),
                "candidate_rank": metadata.get("candidate_rank"),
                "candidate_score": metadata.get("candidate_score"),
                "candidate_score_z": metadata.get("candidate_score_z"),
                "candidate_score_liquidity": metadata.get(
                    "candidate_score_liquidity"
                ),
                "candidate_score_atr": metadata.get("candidate_score_atr"),
                "candidate_pool_size_for_date": metadata.get(
                    "candidate_pool_size_for_date"
                ),
                "s2_candidate_ranking_mode": metadata.get(
                    "s2_candidate_ranking_mode"
                ),
                "s2_candidate_rank": metadata.get("s2_candidate_rank"),
                "s2_candidate_score": metadata.get("s2_candidate_score"),
                "s2_score_state_edge": metadata.get("s2_score_state_edge"),
                "s2_score_state_quality": metadata.get(
                    "s2_score_state_quality"
                ),
                "s2_score_context": metadata.get("s2_score_context"),
                "s2_score_penalty": metadata.get("s2_score_penalty"),
                "strategy_family": metadata.get("strategy_family"),
                "state_label": metadata.get("state_label"),
                "state_lookback_sessions": metadata.get(
                    "state_lookback_sessions"
                ),
                "state_observation_count": metadata.get(
                    "state_observation_count"
                ),
                "forward_return_sessions": metadata.get(
                    "forward_return_sessions"
                ),
                "positive_return_threshold_pct": metadata.get(
                    "positive_return_threshold_pct"
                ),
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
                "markov_signal_filter": metadata.get("markov_signal_filter"),
                "markov_filter_decision": metadata.get("markov_filter_decision"),
            }
        )
    return rows


def _rejected_signal_rows(result: Any) -> list[dict[str, object]]:
    """Return serialized rejected-signal rows."""

    return [
        {
            "symbol": rejected.symbol,
            "signal_date": rejected.signal_date,
            "strategy_name": rejected.strategy_name,
            "reason": rejected.reason,
            "candidate_ranking_mode": getattr(
                rejected,
                "candidate_ranking_mode",
                None,
            ),
            "candidate_rank": getattr(rejected, "candidate_rank", None),
            "candidate_score": getattr(rejected, "candidate_score", None),
            "candidate_pool_size_for_date": getattr(
                rejected,
                "candidate_pool_size_for_date",
                None,
            ),
            "markov_signal_filter": getattr(
                rejected,
                "markov_signal_filter",
                None,
            ),
            "markov_filter_decision": getattr(
                rejected,
                "markov_filter_decision",
                None,
            ),
        }
        for rejected in result.rejected_signals
    ]


def _equity_curve_rows(result: Any) -> list[dict[str, object]]:
    """Return serialized equity curve rows."""

    ledger = result.ledger
    if ledger is None:
        return []
    return [
        {
            "date": point.date,
            "equity": point.equity,
            "realized_pnl": point.realized_pnl,
        }
        for point in ledger.equity_curve
    ]


def _summary_rows(result: Any) -> list[dict[str, object]]:
    """Return one summary row with portfolio performance metrics."""

    summary = calculate_performance_summary(result)
    return [
        {
            "strategy_name": summary.strategy_name,
            "strategy_variant": getattr(result, "strategy_variant", "S1_BASELINE"),
            "start_date": summary.start_date,
            "end_date": summary.end_date,
            "starting_equity": summary.starting_equity,
            "ending_equity": summary.ending_equity,
            "total_net_pnl": summary.total_net_pnl,
            "total_return_pct": summary.total_return_pct,
            "cagr_pct": summary.cagr_pct,
            "max_drawdown_pct": summary.max_drawdown_pct,
            "total_trades": summary.total_trades,
            "winning_trades": summary.winning_trades,
            "losing_trades": summary.losing_trades,
            "win_rate_pct": summary.win_rate_pct,
            "gross_profit": summary.gross_profit,
            "gross_loss": summary.gross_loss,
            "profit_factor": summary.profit_factor,
            "expectancy": summary.expectancy,
            "average_win": summary.average_win,
            "average_loss": summary.average_loss,
            "average_net_pnl": summary.average_net_pnl,
            "best_trade": summary.best_trade,
            "worst_trade": summary.worst_trade,
            "average_holding_days": summary.average_holding_days,
            "total_signals": summary.total_signals,
            "total_rejected_signals": summary.total_rejected_signals,
            "symbols_count": summary.symbols_count,
        }
    ]


def _enum_value(value: Any) -> object:
    """Return enum value when present, otherwise the original value."""

    return getattr(value, "value", value)
