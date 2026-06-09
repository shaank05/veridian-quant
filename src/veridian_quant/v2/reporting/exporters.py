"""CSV exporters for Veridian Quant v2 backtest artifacts.

Exporter functions serialize already-computed research results. They do not run
strategies, load data, calculate metrics, or mutate backtest outputs.
"""

from pathlib import Path
from typing import Any, Mapping

import pandas as pd


TRADE_LOG_COLUMNS = [
    "trade_id",
    "symbol",
    "entry_date",
    "entry_price",
    "quantity",
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
    "total_trades",
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
    """Return one summary row with simple counts and totals."""

    total_net_pnl = sum(
        (pnl.net_pnl for pnl in result.trade_pnls),
        result.starting_equity - result.starting_equity,
    )
    return [
        {
            "strategy_name": result.strategy_name,
            "start_date": result.start_date,
            "end_date": result.end_date,
            "starting_equity": result.starting_equity,
            "ending_equity": result.ending_equity,
            "total_net_pnl": total_net_pnl,
            "total_trades": len(result.trades),
            "total_signals": len(result.signals),
            "total_rejected_signals": len(result.rejected_signals),
            "symbols_count": len(result.symbols),
        }
    ]


def _enum_value(value: Any) -> object:
    """Return enum value when present, otherwise the original value."""

    return getattr(value, "value", value)
