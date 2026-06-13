"""Compare S1 baseline reports across research universe sizes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


REQUIRED_FILES = {
    "summary": "summary.csv",
    "yearly": "yearly_summary.csv",
    "exit_reason": "exit_reason_summary.csv",
    "rejection": "rejection_summary.csv",
    "symbol": "symbol_summary.csv",
    "signals": "signal_log.csv",
    "rejected_signals": "rejected_signals.csv",
}

SUMMARY_COLUMNS = [
    "universe_label",
    "universe_size",
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
    "average_holding_days",
    "total_signals",
    "total_rejected_signals",
    "accepted_signal_pct",
    "rejected_signal_pct",
]

DELTA_COLUMNS = [
    "metric",
    "research100_value",
    "research200_value",
    "absolute_delta",
    "pct_delta_where_applicable",
]

YEARLY_COLUMNS = [
    "year",
    "research100_net_pnl",
    "research200_net_pnl",
    "delta_net_pnl",
    "research100_trades",
    "research200_trades",
    "delta_trades",
]

EXIT_REASON_COLUMNS = [
    "exit_reason",
    "research100_trade_count",
    "research100_net_pnl",
    "research100_gross_profit",
    "research100_gross_loss",
    "research200_trade_count",
    "research200_net_pnl",
    "research200_gross_profit",
    "research200_gross_loss",
    "delta_trade_count",
    "delta_net_pnl",
]

REJECTION_COLUMNS = [
    "rejection_reason",
    "research100_count",
    "research200_count",
    "delta_count",
    "research100_pct_of_rejections",
    "research200_pct_of_rejections",
]

SYMBOL_COLUMNS = [
    "symbol",
    "in_research100",
    "in_research200",
    "research100_trade_count",
    "research100_net_pnl",
    "research100_gross_profit",
    "research100_gross_loss",
    "research200_trade_count",
    "research200_net_pnl",
    "research200_gross_profit",
    "research200_gross_loss",
    "delta_trade_count",
    "delta_net_pnl",
]

DIAGNOSTIC_COLUMNS = ["metric", "research100_value", "research200_value", "delta"]


@dataclass(frozen=True, slots=True)
class BaselineUniverseComparisonResult:
    """Output paths and frames for a baseline universe-size comparison."""

    paths: dict[str, Path]
    summary: pd.DataFrame
    delta: pd.DataFrame
    yearly: pd.DataFrame
    exit_reason: pd.DataFrame
    rejection: pd.DataFrame
    symbol: pd.DataFrame
    diagnostic: pd.DataFrame


@dataclass(frozen=True, slots=True)
class _ReportInputs:
    label: str
    size: int
    summary: pd.DataFrame
    yearly: pd.DataFrame
    exit_reason: pd.DataFrame
    rejection: pd.DataFrame
    symbol: pd.DataFrame
    signals: pd.DataFrame
    rejected_signals: pd.DataFrame


def compare_baseline_universe_sizes(
    research100_dir: Path,
    research200_dir: Path,
    output_dir: Path,
) -> BaselineUniverseComparisonResult:
    """Create comparison CSVs for S1 baseline 100-symbol and 200-symbol reports."""

    research100 = _load_report(research100_dir, "research100", 100)
    research200 = _load_report(research200_dir, "research200", 200)

    summary = _build_summary(research100, research200)
    delta = _build_delta(summary)
    yearly = _build_yearly(research100, research200)
    exit_reason = _build_exit_reason(research100, research200)
    rejection = _build_rejection(research100, research200)
    symbol = _build_symbol(research100, research200)
    diagnostic = _build_diagnostic(research100, research200)

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "summary_comparison": output_dir
        / "baseline_universe_summary_comparison.csv",
        "delta": output_dir / "baseline_universe_delta.csv",
        "yearly_comparison": output_dir
        / "baseline_universe_yearly_comparison.csv",
        "exit_reason_comparison": output_dir
        / "baseline_universe_exit_reason_comparison.csv",
        "rejection_comparison": output_dir
        / "baseline_universe_rejection_comparison.csv",
        "symbol_comparison": output_dir
        / "baseline_universe_symbol_comparison.csv",
        "diagnostic_summary": output_dir
        / "baseline_universe_diagnostic_summary.csv",
    }
    summary.to_csv(paths["summary_comparison"], index=False)
    delta.to_csv(paths["delta"], index=False)
    yearly.to_csv(paths["yearly_comparison"], index=False)
    exit_reason.to_csv(paths["exit_reason_comparison"], index=False)
    rejection.to_csv(paths["rejection_comparison"], index=False)
    symbol.to_csv(paths["symbol_comparison"], index=False)
    diagnostic.to_csv(paths["diagnostic_summary"], index=False)

    return BaselineUniverseComparisonResult(
        paths=paths,
        summary=summary,
        delta=delta,
        yearly=yearly,
        exit_reason=exit_reason,
        rejection=rejection,
        symbol=symbol,
        diagnostic=diagnostic,
    )


def _load_report(report_dir: Path, label: str, size: int) -> _ReportInputs:
    missing = [
        report_dir / filename
        for filename in REQUIRED_FILES.values()
        if not (report_dir / filename).exists()
    ]
    if missing:
        missing_text = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"missing required baseline report file(s): {missing_text}")

    return _ReportInputs(
        label=label,
        size=size,
        summary=pd.read_csv(report_dir / REQUIRED_FILES["summary"]),
        yearly=pd.read_csv(report_dir / REQUIRED_FILES["yearly"]),
        exit_reason=pd.read_csv(report_dir / REQUIRED_FILES["exit_reason"]),
        rejection=pd.read_csv(report_dir / REQUIRED_FILES["rejection"]),
        symbol=pd.read_csv(report_dir / REQUIRED_FILES["symbol"]),
        signals=pd.read_csv(report_dir / REQUIRED_FILES["signals"]),
        rejected_signals=pd.read_csv(report_dir / REQUIRED_FILES["rejected_signals"]),
    )


def _build_summary(*reports: _ReportInputs) -> pd.DataFrame:
    rows = []
    for report in reports:
        summary = _single_row(report.summary, "summary.csv")
        total_signals = _number(summary.get("total_signals"))
        rejected_signals = _number(summary.get("total_rejected_signals"))
        total_trades = _number(summary.get("total_trades"))
        rows.append(
            {
                "universe_label": report.label,
                "universe_size": report.size,
                "ending_equity": _number(summary.get("ending_equity")),
                "total_net_pnl": _number(summary.get("total_net_pnl")),
                "total_return_pct": _number(summary.get("total_return_pct")),
                "cagr_pct": _number(summary.get("cagr_pct")),
                "max_drawdown_pct": _number(summary.get("max_drawdown_pct")),
                "total_trades": total_trades,
                "winning_trades": _number(summary.get("winning_trades")),
                "losing_trades": _number(summary.get("losing_trades")),
                "win_rate_pct": _number(summary.get("win_rate_pct")),
                "gross_profit": _number(summary.get("gross_profit")),
                "gross_loss": _number(summary.get("gross_loss")),
                "profit_factor": _number(summary.get("profit_factor")),
                "expectancy": _number(summary.get("expectancy")),
                "average_win": _number(summary.get("average_win")),
                "average_loss": _number(summary.get("average_loss")),
                "average_holding_days": _number(summary.get("average_holding_days")),
                "total_signals": total_signals,
                "total_rejected_signals": rejected_signals,
                "accepted_signal_pct": _pct(total_trades, total_signals),
                "rejected_signal_pct": _pct(rejected_signals, total_signals),
            }
        )
    return pd.DataFrame(rows, columns=SUMMARY_COLUMNS)


def _build_delta(summary: pd.DataFrame) -> pd.DataFrame:
    research100 = _summary_by_label(summary, "research100")
    research200 = _summary_by_label(summary, "research200")
    rows = []
    for metric in SUMMARY_COLUMNS:
        if metric == "universe_label":
            continue
        value100 = research100.get(metric)
        value200 = research200.get(metric)
        delta = _number(value200) - _number(value100)
        rows.append(
            {
                "metric": metric,
                "research100_value": value100,
                "research200_value": value200,
                "absolute_delta": delta,
                "pct_delta_where_applicable": _pct_delta(value100, value200),
            }
        )
    return pd.DataFrame(rows, columns=DELTA_COLUMNS)


def _build_yearly(research100: _ReportInputs, research200: _ReportInputs) -> pd.DataFrame:
    left = _rename_group(
        research100.yearly,
        key="year",
        prefix="research100",
        trades_column="trades",
    )
    right = _rename_group(
        research200.yearly,
        key="year",
        prefix="research200",
        trades_column="trades",
    )
    merged = pd.merge(left, right, on="year", how="outer").fillna(0)
    merged = merged.rename(
        columns={
            "research100_trade_count": "research100_trades",
            "research200_trade_count": "research200_trades",
        }
    )
    merged["delta_net_pnl"] = merged["research200_net_pnl"] - merged["research100_net_pnl"]
    merged["delta_trades"] = (
        merged["research200_trades"] - merged["research100_trades"]
    )
    return merged.loc[:, YEARLY_COLUMNS].sort_values("year", kind="mergesort")


def _build_exit_reason(
    research100: _ReportInputs,
    research200: _ReportInputs,
) -> pd.DataFrame:
    left = _rename_group(
        research100.exit_reason,
        key="exit_reason",
        prefix="research100",
        trades_column="trades",
    )
    right = _rename_group(
        research200.exit_reason,
        key="exit_reason",
        prefix="research200",
        trades_column="trades",
    )
    merged = pd.merge(left, right, on="exit_reason", how="outer").fillna(0)
    merged["delta_trade_count"] = (
        merged["research200_trade_count"] - merged["research100_trade_count"]
    )
    merged["delta_net_pnl"] = merged["research200_net_pnl"] - merged["research100_net_pnl"]
    return merged.loc[:, EXIT_REASON_COLUMNS].sort_values(
        "exit_reason",
        kind="mergesort",
    )


def _build_rejection(
    research100: _ReportInputs,
    research200: _ReportInputs,
) -> pd.DataFrame:
    left = _rename_rejections(research100.rejection, "research100")
    right = _rename_rejections(research200.rejection, "research200")
    merged = pd.merge(left, right, on="rejection_reason", how="outer").fillna(0)
    total100 = _number(merged["research100_count"].sum())
    total200 = _number(merged["research200_count"].sum())
    merged["delta_count"] = merged["research200_count"] - merged["research100_count"]
    merged["research100_pct_of_rejections"] = [
        _pct(value, total100) for value in merged["research100_count"]
    ]
    merged["research200_pct_of_rejections"] = [
        _pct(value, total200) for value in merged["research200_count"]
    ]
    return merged.loc[:, REJECTION_COLUMNS].sort_values(
        "rejection_reason",
        kind="mergesort",
    )


def _build_symbol(research100: _ReportInputs, research200: _ReportInputs) -> pd.DataFrame:
    left = _rename_group(
        research100.symbol,
        key="symbol",
        prefix="research100",
        trades_column="trades",
    )
    right = _rename_group(
        research200.symbol,
        key="symbol",
        prefix="research200",
        trades_column="trades",
    )
    merged = pd.merge(left, right, on="symbol", how="outer").fillna(0)
    merged["in_research100"] = merged["research100_trade_count"] > 0
    merged["in_research200"] = merged["research200_trade_count"] > 0
    merged["delta_trade_count"] = (
        merged["research200_trade_count"] - merged["research100_trade_count"]
    )
    merged["delta_net_pnl"] = merged["research200_net_pnl"] - merged["research100_net_pnl"]
    return merged.loc[:, SYMBOL_COLUMNS].sort_values("symbol", kind="mergesort")


def _build_diagnostic(
    research100: _ReportInputs,
    research200: _ReportInputs,
) -> pd.DataFrame:
    values100 = _diagnostic_values(research100)
    values200 = _diagnostic_values(research200)
    metrics = [
        "total_signals",
        "total_trades",
        "total_rejections",
        "capacity_rejections",
        "active_symbol_rejections",
        "target_net_pnl",
        "stop_net_pnl",
        "time_stop_net_pnl",
        "positive_symbols",
        "negative_symbols",
    ]
    rows = []
    for metric in metrics:
        metric_name = metric
        rows.append(
            {
                "metric": f"research100_{metric_name}",
                "research100_value": values100[metric],
                "research200_value": "",
                "delta": "",
            }
        )
        rows.append(
            {
                "metric": f"research200_{metric_name}",
                "research100_value": "",
                "research200_value": values200[metric],
                "delta": "",
            }
        )
    rows.extend(
        {
            "metric": f"delta_{metric}",
            "research100_value": values100[metric],
            "research200_value": values200[metric],
            "delta": _number(values200[metric]) - _number(values100[metric]),
        }
        for metric in metrics
    )
    return pd.DataFrame(rows, columns=DIAGNOSTIC_COLUMNS)


def _diagnostic_values(report: _ReportInputs) -> dict[str, float]:
    summary = _single_row(report.summary, "summary.csv")
    return {
        "total_signals": _number(summary.get("total_signals")),
        "total_trades": _number(summary.get("total_trades")),
        "total_rejections": _number(summary.get("total_rejected_signals")),
        "capacity_rejections": _rejection_count(report.rejection, "PORTFOLIO_CAPACITY_FULL"),
        "active_symbol_rejections": _rejection_count(
            report.rejection,
            "ACTIVE_SYMBOL_TRADE_EXISTS",
        ),
        "target_net_pnl": _exit_net_pnl(report.exit_reason, ("target_hit", "target_gap_hit")),
        "stop_net_pnl": _exit_net_pnl(report.exit_reason, ("stop_loss_hit", "stop_gap_hit")),
        "time_stop_net_pnl": _exit_net_pnl(report.exit_reason, ("time_stop",)),
        "positive_symbols": float((pd.to_numeric(report.symbol["net_pnl"], errors="coerce") > 0).sum()),
        "negative_symbols": float((pd.to_numeric(report.symbol["net_pnl"], errors="coerce") < 0).sum()),
    }


def _rename_group(
    df: pd.DataFrame,
    key: str,
    prefix: str,
    trades_column: str,
) -> pd.DataFrame:
    required = {key, trades_column, "net_pnl", "gross_profit", "gross_loss"}
    _require_columns(df, required, key)
    output = df.loc[:, [key, trades_column, "net_pnl", "gross_profit", "gross_loss"]].copy()
    for column in (trades_column, "net_pnl", "gross_profit", "gross_loss"):
        output[column] = pd.to_numeric(output[column], errors="coerce").fillna(0)
    return output.rename(
        columns={
            trades_column: f"{prefix}_trade_count",
            "net_pnl": f"{prefix}_net_pnl",
            "gross_profit": f"{prefix}_gross_profit",
            "gross_loss": f"{prefix}_gross_loss",
        }
    )


def _rename_rejections(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    _require_columns(df, {"reason", "count"}, "rejection_summary.csv")
    output = df.loc[:, ["reason", "count"]].copy()
    output["count"] = pd.to_numeric(output["count"], errors="coerce").fillna(0)
    return output.rename(
        columns={"reason": "rejection_reason", "count": f"{prefix}_count"}
    )


def _single_row(df: pd.DataFrame, name: str) -> pd.Series:
    if len(df) != 1:
        raise ValueError(f"{name} must contain exactly one row")
    return df.iloc[0]


def _summary_by_label(summary: pd.DataFrame, label: str) -> pd.Series:
    rows = summary.loc[summary["universe_label"] == label]
    if len(rows) != 1:
        raise ValueError(f"summary comparison missing row for {label}")
    return rows.iloc[0]


def _rejection_count(rejection: pd.DataFrame, reason: str) -> float:
    rows = rejection.loc[rejection["reason"] == reason]
    if rows.empty:
        return 0.0
    return _number(rows["count"].sum())


def _exit_net_pnl(exit_reason: pd.DataFrame, reasons: tuple[str, ...]) -> float:
    rows = exit_reason.loc[exit_reason["exit_reason"].isin(reasons)]
    if rows.empty:
        return 0.0
    return _number(pd.to_numeric(rows["net_pnl"], errors="coerce").fillna(0).sum())


def _require_columns(df: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = sorted(column for column in columns if column not in df.columns)
    if missing:
        raise ValueError(f"{name} is missing required column(s): {', '.join(missing)}")


def _pct(numerator: Any, denominator: Any) -> float:
    denominator_value = _number(denominator)
    if denominator_value == 0:
        return 0.0
    return (_number(numerator) / denominator_value) * 100.0


def _pct_delta(value100: Any, value200: Any) -> float | None:
    base = _number(value100)
    if base == 0:
        return None
    return ((_number(value200) - base) / abs(base)) * 100.0


def _number(value: Any) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(parsed):
        return 0.0
    return float(parsed)
