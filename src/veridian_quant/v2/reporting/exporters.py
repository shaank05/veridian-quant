"""CSV exporters for Veridian Quant v2 backtest artifacts.

Exporter functions serialize already-computed research results. They do not run
strategies, load data, calculate metrics, or mutate backtest outputs.
"""

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

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
from veridian_quant.v2.reporting.metrics import calculate_performance_summary


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
]
REJECTED_SIGNALS_COLUMNS = ["symbol", "signal_date", "strategy_name", "reason"]
EQUITY_CURVE_COLUMNS = ["date", "equity", "realized_pnl"]
SUMMARY_COLUMNS = [
    "strategy_name",
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
) -> dict[str, Path]:
    """Write standard portfolio backtest CSV artifacts and return file paths."""

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
    }

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
    return exports


def _write_csv(
    path: Path,
    rows: list[Mapping[str, object]],
    columns: list[str],
) -> None:
    """Write rows to CSV, preserving headers for empty outputs."""

    pd.DataFrame(rows, columns=columns).to_csv(path, index=False)


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
