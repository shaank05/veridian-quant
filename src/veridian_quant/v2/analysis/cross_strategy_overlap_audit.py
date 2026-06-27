"""Read-only cross-strategy overlap and ensemble feasibility audit utilities.

This module analyzes retained strategy report CSVs only. It does not run
strategies, backtests, portfolio simulation, allocation, or voting logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import combinations
import json
from pathlib import Path
from typing import Iterable, Literal, Mapping

import numpy as np
import pandas as pd


StrategyLabel = Literal["S1", "S2", "S3", "S4", "S5"]
OverlapScope = Literal["executed_trades", "signals", "counterfactual", "all"]

STRATEGY_LABELS: tuple[StrategyLabel, ...] = ("S1", "S2", "S3", "S4", "S5")
CORE_FILES = ("signal_log.csv", "trade_log.csv", "trade_pnl_log.csv", "equity_curve.csv")
OPTIONAL_FILES = (
    "accepted_vs_rejected_signal_summary.csv",
    "all_signal_opportunity_log.csv",
    "counterfactual_rejected_trade_summary.csv",
    "counterfactual_by_symbol.csv",
    "counterfactual_by_year.csv",
)
DATE_WARNING = (
    "Prior/on-entry confirmation uses generated_on <= anchor entry_date. "
    "Future nearby overlap is diagnostic only and is not implementable confirmation."
)
ENSEMBLE_CAVEAT = (
    "This read-only audit is not an ensemble backtest, voting strategy, combined portfolio "
    "backtest, capital allocation model, or production approval."
)


@dataclass(frozen=True, slots=True)
class StrategyReport:
    strategy: StrategyLabel
    input_dir: Path
    files: Mapping[str, Path]
    missing_files: tuple[str, ...]
    detected_columns: Mapping[str, Mapping[str, str | None]]
    limitations: tuple[str, ...]
    signal_log: pd.DataFrame | None
    trade_log: pd.DataFrame | None
    trade_pnl_log: pd.DataFrame | None
    equity_curve: pd.DataFrame | None
    all_signal_opportunity_log: pd.DataFrame | None
    accepted_vs_rejected_signal_summary: pd.DataFrame | None
    counterfactual_rejected_trade_summary: pd.DataFrame | None
    counterfactual_by_symbol: pd.DataFrame | None
    counterfactual_by_year: pd.DataFrame | None
    counterfactual_schema_supported: bool
    counterfactual_limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CrossStrategyOverlapAuditResult:
    output_dir: Path
    outputs: dict[str, Path]
    metadata: dict[str, object]


def run_cross_strategy_overlap_audit(
    strategy_dirs: Mapping[str, Path | str],
    *,
    output_dir: Path | str,
    anchor_strategy: str = "S2",
    lookback_days: int = 3,
    diagnostic_window_days: int = 3,
    top_n: int = 20,
    overlap_scope: OverlapScope = "all",
) -> CrossStrategyOverlapAuditResult:
    """Load retained strategy reports and write the read-only overlap audit."""

    anchor = normalize_strategy_label(anchor_strategy)
    scope = _validate_scope(overlap_scope)
    if lookback_days < 0:
        raise ValueError("lookback_days must be >= 0")
    if diagnostic_window_days < 0:
        raise ValueError("diagnostic_window_days must be >= 0")
    if top_n < 1:
        raise ValueError("top_n must be positive")

    normalized_dirs = {
        normalize_strategy_label(strategy): Path(path)
        for strategy, path in strategy_dirs.items()
    }
    missing_labels = [label for label in STRATEGY_LABELS if label not in normalized_dirs]
    if missing_labels:
        raise ValueError(f"missing strategy directories for: {', '.join(missing_labels)}")
    if anchor not in normalized_dirs:
        raise ValueError(f"anchor strategy {anchor} is not present in strategy dirs")

    reports = [load_strategy_report(label, normalized_dirs[label]) for label in STRATEGY_LABELS]
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    outputs: dict[str, Path] = {}
    inventory = build_strategy_report_inventory(reports)
    outputs["strategy_report_inventory.csv"] = _write_csv(
        inventory,
        output_path / "strategy_report_inventory.csv",
    )

    if scope in ("signals", "all"):
        outputs.update(_write_signal_outputs(reports, output_path))

    if scope in ("executed_trades", "all"):
        outputs.update(
            _write_executed_trade_outputs(
                reports,
                output_path,
                anchor_strategy=anchor,
                lookback_days=lookback_days,
                diagnostic_window_days=diagnostic_window_days,
            )
        )

    if scope in ("counterfactual", "all"):
        outputs.update(_write_counterfactual_outputs(reports, output_path))

    if scope in ("executed_trades", "all"):
        outputs["equity_correlation_summary.csv"] = _write_csv(
            build_equity_correlation_summary(reports),
            output_path / "equity_correlation_summary.csv",
        )
        outputs["drawdown_overlap_summary.csv"] = _write_csv(
            build_drawdown_overlap_summary(reports),
            output_path / "drawdown_overlap_summary.csv",
        )

    readme_path = output_path / "overlap_readme.txt"
    readme_path.write_text(_readme_text(), encoding="utf-8")
    outputs["overlap_readme.txt"] = readme_path

    metadata = build_metadata(
        reports,
        output_dir=output_path,
        anchor_strategy=anchor,
        overlap_scope=scope,
        lookback_days=lookback_days,
        diagnostic_window_days=diagnostic_window_days,
        top_n=top_n,
        outputs=outputs,
    )
    metadata_path = output_path / "overlap_audit_metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    outputs["overlap_audit_metadata.json"] = metadata_path
    return CrossStrategyOverlapAuditResult(output_path, outputs, metadata)


def load_strategy_report(strategy: str, input_dir: Path | str) -> StrategyReport:
    """Load a single strategy report folder without mutating it."""

    label = normalize_strategy_label(strategy)
    folder = Path(input_dir)
    files: dict[str, Path] = {}
    missing: list[str] = []
    frames: dict[str, pd.DataFrame | None] = {}
    detected: dict[str, dict[str, str | None]] = {}
    limitations: list[str] = []

    for name in (*CORE_FILES, *OPTIONAL_FILES):
        path = folder / name
        if path.exists():
            files[name] = path
            frames[name] = pd.read_csv(path)
        else:
            missing.append(name)
            frames[name] = None

    signal_log = frames["signal_log.csv"]
    trade_log = frames["trade_log.csv"]
    trade_pnl_log = frames["trade_pnl_log.csv"]
    if signal_log is None and trade_log is None and trade_pnl_log is None:
        raise ValueError(f"{label} lacks both signal_log and trade logs in {folder}")

    if signal_log is not None:
        detected["signal_log.csv"] = {
            "symbol": _detect_required(signal_log, ("symbol",), label, "signal_log.csv"),
            "signal_date": _detect_required(signal_log, ("generated_on", "signal_date"), label, "signal_log.csv"),
        }
        _normalize_signal_frame(signal_log, detected["signal_log.csv"], label)

    for name, frame in (("trade_log.csv", trade_log), ("trade_pnl_log.csv", trade_pnl_log)):
        if frame is not None:
            detected[name] = {
                "symbol": _detect_required(frame, ("symbol",), label, name),
                "entry_date": _detect_required(frame, ("entry_date",), label, name),
                "exit_date": _first_existing(frame, ("exit_date",)),
                "net_pnl": _first_existing(frame, ("net_pnl",)),
                "gross_pnl": _first_existing(frame, ("gross_pnl",)),
                "exit_reason": _first_existing(frame, ("exit_reason",)),
                "trade_id": _first_existing(frame, ("trade_id", "id")),
            }
            _normalize_trade_frame(frame, detected[name], label)

    equity = frames["equity_curve.csv"]
    if equity is not None:
        detected["equity_curve.csv"] = {
            "date": _detect_required(equity, ("date",), label, "equity_curve.csv"),
            "equity": _detect_required(equity, ("equity",), label, "equity_curve.csv"),
            "realized_pnl": _first_existing(equity, ("realized_pnl",)),
        }
        _normalize_equity_frame(equity, detected["equity_curve.csv"], label)

    if frames["all_signal_opportunity_log.csv"] is not None:
        opportunity = frames["all_signal_opportunity_log.csv"]
        detected["all_signal_opportunity_log.csv"] = {
            "symbol": _first_existing(opportunity, ("symbol",)),
            "signal_date": _first_existing(opportunity, ("generated_on", "signal_date")),
        }
        if not detected["all_signal_opportunity_log.csv"]["symbol"]:
            limitations.append("all_signal_opportunity_log.csv missing symbol column")
        if not detected["all_signal_opportunity_log.csv"]["signal_date"]:
            limitations.append("all_signal_opportunity_log.csv missing generated_on/signal_date column")

    cf_supported, cf_limitations = _counterfactual_schema_status(
        frames["counterfactual_rejected_trade_summary.csv"],
        frames["counterfactual_by_symbol.csv"],
        frames["counterfactual_by_year.csv"],
    )
    limitations.extend(cf_limitations)
    if any(name in missing for name in OPTIONAL_FILES):
        missing_optional = [name for name in OPTIONAL_FILES if name in missing]
        limitations.append(f"missing optional files: {', '.join(missing_optional)}")

    return StrategyReport(
        strategy=label,
        input_dir=folder,
        files=files,
        missing_files=tuple(missing),
        detected_columns=detected,
        limitations=tuple(limitations),
        signal_log=signal_log,
        trade_log=trade_log,
        trade_pnl_log=trade_pnl_log,
        equity_curve=equity,
        all_signal_opportunity_log=frames["all_signal_opportunity_log.csv"],
        accepted_vs_rejected_signal_summary=frames["accepted_vs_rejected_signal_summary.csv"],
        counterfactual_rejected_trade_summary=frames["counterfactual_rejected_trade_summary.csv"],
        counterfactual_by_symbol=frames["counterfactual_by_symbol.csv"],
        counterfactual_by_year=frames["counterfactual_by_year.csv"],
        counterfactual_schema_supported=cf_supported,
        counterfactual_limitations=tuple(cf_limitations),
    )


def build_strategy_report_inventory(reports: Iterable[StrategyReport]) -> pd.DataFrame:
    rows = []
    for report in reports:
        signal = report.signal_log
        trades = _executed_trades(report)
        rows.append(
            {
                "strategy": report.strategy,
                "input_dir": str(report.input_dir),
                "has_signal_log": signal is not None,
                "has_trade_log": report.trade_log is not None,
                "has_trade_pnl_log": report.trade_pnl_log is not None,
                "has_equity_curve": report.equity_curve is not None,
                "has_all_signal_opportunity_log": report.all_signal_opportunity_log is not None,
                "has_accepted_vs_rejected_signal_summary": report.accepted_vs_rejected_signal_summary is not None,
                "has_counterfactual_rejected_trade_summary": report.counterfactual_rejected_trade_summary is not None,
                "has_counterfactual_by_symbol": report.counterfactual_by_symbol is not None,
                "has_counterfactual_by_year": report.counterfactual_by_year is not None,
                "signal_rows": _row_count(signal),
                "trade_rows": _row_count(report.trade_log),
                "trade_pnl_rows": _row_count(report.trade_pnl_log),
                "equity_rows": _row_count(report.equity_curve),
                "all_signal_opportunity_rows": _row_count(report.all_signal_opportunity_log),
                "min_signal_date": _min_date(signal, "_signal_date"),
                "max_signal_date": _max_date(signal, "_signal_date"),
                "min_entry_date": _min_date(trades, "_entry_date"),
                "max_entry_date": _max_date(trades, "_entry_date"),
            }
        )
    return pd.DataFrame(rows)


def build_signal_overlap_same_day(reports: Iterable[StrategyReport]) -> pd.DataFrame:
    signals = _combined_signals(reports)
    columns = ["date", "symbol", "strategies_signaling", "strategy_count", "strategy_list"]
    if signals.empty:
        return pd.DataFrame(columns=columns)
    grouped = signals.groupby(["_signal_date", "symbol"], dropna=False, sort=True)["strategy"]
    rows = []
    for (date_value, symbol), strategies in grouped:
        unique = sorted(set(strategies))
        if len(unique) < 2:
            continue
        rows.append(
            {
                "date": _date_text(date_value),
                "symbol": symbol,
                "strategies_signaling": len(unique),
                "strategy_count": len(unique),
                "strategy_list": "|".join(unique),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def build_signal_pair_overlap_summary(reports: Iterable[StrategyReport]) -> pd.DataFrame:
    signal_by_strategy = {report.strategy: _strategy_signals(report) for report in reports}
    rows = []
    for strategy_a, strategy_b in combinations(STRATEGY_LABELS, 2):
        a = signal_by_strategy.get(strategy_a, pd.DataFrame())
        b = signal_by_strategy.get(strategy_b, pd.DataFrame())
        same_day = _same_day_overlap_count(a, b, "_signal_date")
        common_symbols = len(set(a.get("symbol", pd.Series(dtype=str))).intersection(set(b.get("symbol", pd.Series(dtype=str)))))
        notes = "signal logs compared"
        if a.empty or b.empty:
            notes = "one or both signal logs missing/empty"
        rows.append(
            {
                "strategy_a": strategy_a,
                "strategy_b": strategy_b,
                "same_day_signal_overlap_count": same_day,
                "common_signal_symbols_count": common_symbols,
                "notes": notes,
            }
        )
    return pd.DataFrame(rows)


def build_signal_consensus_by_year(overlap: pd.DataFrame) -> pd.DataFrame:
    columns = ["year", "strategy_count", "consensus_group", "signal_overlap_events", "unique_symbols"]
    if overlap.empty:
        return pd.DataFrame(columns=columns)
    frame = overlap.copy()
    frame["year"] = pd.to_datetime(frame["date"], errors="coerce").dt.year
    frame["consensus_group"] = frame["strategy_count"].map(_consensus_group)
    grouped = frame.groupby(["year", "strategy_count", "consensus_group"], dropna=False, sort=True)
    rows = []
    for keys, group in grouped:
        year, strategy_count, consensus_group = keys
        rows.append(
            {
                "year": int(year) if pd.notna(year) else "",
                "strategy_count": int(strategy_count),
                "consensus_group": consensus_group,
                "signal_overlap_events": int(len(group)),
                "unique_symbols": int(group["symbol"].nunique()),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def build_signal_consensus_by_symbol(overlap: pd.DataFrame) -> pd.DataFrame:
    columns = ["symbol", "signal_overlap_events", "max_strategy_count", "strategies_seen", "years_seen"]
    if overlap.empty:
        return pd.DataFrame(columns=columns)
    frame = overlap.copy()
    frame["year"] = pd.to_datetime(frame["date"], errors="coerce").dt.year
    rows = []
    for symbol, group in frame.groupby("symbol", sort=True):
        strategies = sorted({item for value in group["strategy_list"] for item in str(value).split("|") if item})
        years = sorted({str(int(year)) for year in group["year"].dropna().unique()})
        rows.append(
            {
                "symbol": symbol,
                "signal_overlap_events": int(len(group)),
                "max_strategy_count": int(group["strategy_count"].max()),
                "strategies_seen": "|".join(strategies),
                "years_seen": "|".join(years),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def build_entry_overlap_same_day(reports: Iterable[StrategyReport]) -> pd.DataFrame:
    trades = _combined_trades(reports)
    columns = ["entry_date", "symbol", "strategies_entering", "strategy_count", "strategy_list"]
    if trades.empty:
        return pd.DataFrame(columns=columns)
    grouped = trades.groupby(["_entry_date", "symbol"], dropna=False, sort=True)["strategy"]
    rows = []
    for (date_value, symbol), strategies in grouped:
        unique = sorted(set(strategies))
        if len(unique) < 2:
            continue
        rows.append(
            {
                "entry_date": _date_text(date_value),
                "symbol": symbol,
                "strategies_entering": len(unique),
                "strategy_count": len(unique),
                "strategy_list": "|".join(unique),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def build_strategy_pair_overlap_summary(
    reports: Iterable[StrategyReport],
    *,
    anchor_strategy: StrategyLabel,
    lookback_days: int,
) -> pd.DataFrame:
    reports_by_strategy = {report.strategy: report for report in reports}
    trades_by_strategy = {strategy: _strategy_trades(report) for strategy, report in reports_by_strategy.items()}
    signals_by_strategy = {strategy: _strategy_signals(report) for strategy, report in reports_by_strategy.items()}
    rows = []
    for strategy_a, strategy_b in combinations(STRATEGY_LABELS, 2):
        a = trades_by_strategy.get(strategy_a, pd.DataFrame())
        b = trades_by_strategy.get(strategy_b, pd.DataFrame())
        anchor_prior = ""
        if strategy_a == anchor_strategy or strategy_b == anchor_strategy:
            other = strategy_b if strategy_a == anchor_strategy else strategy_a
            anchor_prior = _anchor_prior_confirmation_count(
                trades_by_strategy.get(anchor_strategy, pd.DataFrame()),
                signals_by_strategy.get(other, pd.DataFrame()),
                lookback_days=lookback_days,
            )
        notes = "executed trade logs compared"
        if a.empty or b.empty:
            notes = "one or both executed trade logs missing/empty"
        rows.append(
            {
                "strategy_a": strategy_a,
                "strategy_b": strategy_b,
                "same_day_entry_overlap_count": _same_day_overlap_count(a, b, "_entry_date"),
                "anchor_prior_confirmation_count": anchor_prior,
                "common_symbols_count": len(set(a.get("symbol", pd.Series(dtype=str))).intersection(set(b.get("symbol", pd.Series(dtype=str))))),
                "notes": notes,
            }
        )
    return pd.DataFrame(rows)


def build_anchor_confirmed_vs_unconfirmed(
    reports: Iterable[StrategyReport],
    *,
    anchor_strategy: StrategyLabel,
    lookback_days: int,
    diagnostic_window_days: int,
) -> pd.DataFrame:
    report_map = {report.strategy: report for report in reports}
    anchor_trades = _strategy_trades(report_map[anchor_strategy])
    other_signals = {
        report.strategy: _strategy_signals(report)
        for report in reports
        if report.strategy != anchor_strategy
    }
    columns = [
        "anchor_strategy",
        "trade_id",
        "symbol",
        "entry_date",
        "exit_date",
        "exit_reason",
        "net_pnl",
        "confirmed_by_any_prior_signal",
        "confirming_strategy_count",
        "confirming_strategies",
        "latest_confirming_signal_date",
        "days_since_latest_confirmation",
        "diagnostic_future_confirmation_count",
        "diagnostic_future_confirming_strategies",
    ]
    rows = []
    for idx, trade in anchor_trades.reset_index(drop=True).iterrows():
        entry_date = trade["_entry_date"]
        symbol = trade["symbol"]
        prior_strategies: list[str] = []
        prior_dates: list[pd.Timestamp] = []
        future_strategies: list[str] = []
        for strategy, signals in other_signals.items():
            if signals.empty or pd.isna(entry_date):
                continue
            same_symbol = signals[signals["symbol"] == symbol]
            prior_mask = (
                (same_symbol["_signal_date"] <= entry_date)
                & (same_symbol["_signal_date"] >= entry_date - pd.Timedelta(days=lookback_days))
            )
            prior_hits = same_symbol[prior_mask]
            if not prior_hits.empty:
                prior_strategies.append(strategy)
                prior_dates.append(prior_hits["_signal_date"].max())
            future_mask = (
                (same_symbol["_signal_date"] > entry_date)
                & (same_symbol["_signal_date"] <= entry_date + pd.Timedelta(days=diagnostic_window_days))
            )
            if not same_symbol[future_mask].empty:
                future_strategies.append(strategy)
        latest = max(prior_dates) if prior_dates else pd.NaT
        days_since = (entry_date - latest).days if pd.notna(latest) and pd.notna(entry_date) else ""
        rows.append(
            {
                "anchor_strategy": anchor_strategy,
                "trade_id": trade.get("trade_id", idx),
                "symbol": symbol,
                "entry_date": _date_text(entry_date),
                "exit_date": _date_text(trade.get("_exit_date", pd.NaT)),
                "exit_reason": trade.get("exit_reason", ""),
                "net_pnl": _number_or_blank(trade.get("net_pnl", np.nan)),
                "confirmed_by_any_prior_signal": bool(prior_strategies),
                "confirming_strategy_count": len(prior_strategies),
                "confirming_strategies": "|".join(sorted(prior_strategies)),
                "latest_confirming_signal_date": _date_text(latest),
                "days_since_latest_confirmation": days_since,
                "diagnostic_future_confirmation_count": len(future_strategies),
                "diagnostic_future_confirming_strategies": "|".join(sorted(future_strategies)),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def build_anchor_confirmation_summary(anchor_annotations: pd.DataFrame) -> pd.DataFrame:
    rows = []
    groups: dict[str, pd.DataFrame] = {
        "confirmed": anchor_annotations[anchor_annotations["confirmed_by_any_prior_signal"] == True],
        "unconfirmed": anchor_annotations[anchor_annotations["confirmed_by_any_prior_signal"] == False],
        "confirmed_by_1": anchor_annotations[anchor_annotations["confirming_strategy_count"] == 1],
        "confirmed_by_2_plus": anchor_annotations[anchor_annotations["confirming_strategy_count"] >= 2],
    }
    for group_name, group in groups.items():
        rows.append({"group": group_name, **_pnl_metrics(group)})
    return pd.DataFrame(rows)


def build_anchor_confirmation_by_strategy(anchor_annotations: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if anchor_annotations.empty:
        return pd.DataFrame(
            columns=[
                "anchor_strategy",
                "confirming_strategy",
                "confirmed_trade_count",
                "net_pnl",
                "win_rate",
                "profit_factor",
                "avg_net_pnl",
                "median_net_pnl",
            ]
        )
    anchor = str(anchor_annotations["anchor_strategy"].iloc[0])
    strategies = sorted(
        {
            strategy
            for value in anchor_annotations["confirming_strategies"]
            for strategy in str(value).split("|")
            if strategy
        }
    )
    for strategy in strategies:
        group = anchor_annotations[
            anchor_annotations["confirming_strategies"].astype(str).str.split("|").map(lambda values: strategy in values)
        ]
        metrics = _pnl_metrics(group)
        rows.append(
            {
                "anchor_strategy": anchor,
                "confirming_strategy": strategy,
                "confirmed_trade_count": int(len(group)),
                "net_pnl": metrics["net_pnl"],
                "win_rate": metrics["win_rate"],
                "profit_factor": metrics["profit_factor"],
                "avg_net_pnl": metrics["avg_net_pnl"],
                "median_net_pnl": metrics["median_net_pnl"],
            }
        )
    return pd.DataFrame(rows)


def build_anchor_confirmation_by_year(anchor_annotations: pd.DataFrame) -> pd.DataFrame:
    frame = anchor_annotations.copy()
    frame["year"] = pd.to_datetime(frame["entry_date"], errors="coerce").dt.year
    frame["confirmation_group"] = np.where(frame["confirmed_by_any_prior_signal"], "confirmed", "unconfirmed")
    return _confirmation_group_metrics(frame, ["year", "confirmation_group"])


def build_anchor_confirmation_by_symbol(anchor_annotations: pd.DataFrame) -> pd.DataFrame:
    frame = anchor_annotations.copy()
    frame["confirmation_group"] = np.where(frame["confirmed_by_any_prior_signal"], "confirmed", "unconfirmed")
    return _confirmation_group_metrics(frame, ["symbol", "confirmation_group"])


def build_counterfactual_inventory(reports: Iterable[StrategyReport]) -> pd.DataFrame:
    rows = []
    for report in reports:
        rows.append(
            {
                "strategy": report.strategy,
                "has_counterfactual_rejected_trade_summary": report.counterfactual_rejected_trade_summary is not None,
                "has_counterfactual_by_symbol": report.counterfactual_by_symbol is not None,
                "has_counterfactual_by_year": report.counterfactual_by_year is not None,
                "rejected_trade_summary_rows": _row_count(report.counterfactual_rejected_trade_summary),
                "by_symbol_rows": _row_count(report.counterfactual_by_symbol),
                "by_year_rows": _row_count(report.counterfactual_by_year),
                "schema_supported": report.counterfactual_schema_supported,
                "limitations": "; ".join(report.counterfactual_limitations),
            }
        )
    return pd.DataFrame(rows)


def build_counterfactual_summary_by_strategy(reports: Iterable[StrategyReport]) -> pd.DataFrame:
    rows = []
    for report in reports:
        summary = report.counterfactual_rejected_trade_summary
        if summary is None:
            rows.append(
                {
                    "strategy": report.strategy,
                    "counterfactual_rows": 0,
                    "available_summary_fields": "",
                    "total_rejected_or_counterfactual_trades": "",
                    "net_pnl": "",
                    "win_rate": "",
                    "profit_factor": "",
                    "notes": "counterfactual_rejected_trade_summary.csv missing; no realized PnL mixed",
                }
            )
            continue
        fields = list(summary.columns)
        rows.append(
            {
                "strategy": report.strategy,
                "counterfactual_rows": int(len(summary)),
                "available_summary_fields": "|".join(fields),
                "total_rejected_or_counterfactual_trades": _first_metric_value(
                    summary, ("total_rejected_trades", "counterfactual_trades", "trades", "trade_count")
                ),
                "net_pnl": _first_metric_value(summary, ("net_pnl", "total_net_pnl")),
                "win_rate": _first_metric_value(summary, ("win_rate",)),
                "profit_factor": _first_metric_value(summary, ("profit_factor",)),
                "notes": "counterfactual/hypothesis-generation only; no realized PnL mixed",
            }
        )
    return pd.DataFrame(rows)


def build_counterfactual_by_year_combined(reports: Iterable[StrategyReport]) -> pd.DataFrame:
    return _combine_counterfactual_frames(reports, "counterfactual_by_year", required_key="year")


def build_counterfactual_by_symbol_combined(reports: Iterable[StrategyReport]) -> pd.DataFrame:
    return _combine_counterfactual_frames(reports, "counterfactual_by_symbol", required_key="symbol")


def build_equity_correlation_summary(reports: Iterable[StrategyReport]) -> pd.DataFrame:
    returns: dict[str, pd.DataFrame] = {}
    for report in reports:
        equity = report.equity_curve
        if equity is None or equity.empty:
            continue
        frame = equity[["_date", "equity"]].copy()
        frame["equity"] = pd.to_numeric(frame["equity"], errors="coerce")
        frame = frame.dropna(subset=["_date", "equity"]).sort_values("_date")
        if "realized_pnl" in equity.columns and frame["equity"].notna().any():
            realized = pd.to_numeric(equity.loc[frame.index, "realized_pnl"], errors="coerce")
            frame["return"] = realized / frame["equity"].shift(1).replace(0, np.nan)
        else:
            frame["return"] = frame["equity"].pct_change()
        returns[report.strategy] = frame[["_date", "return"]].dropna()
    rows = []
    for strategy_a, strategy_b in combinations(STRATEGY_LABELS, 2):
        a = returns.get(strategy_a)
        b = returns.get(strategy_b)
        if a is None or b is None:
            rows.append(
                {
                    "strategy_a": strategy_a,
                    "strategy_b": strategy_b,
                    "aligned_days": 0,
                    "return_correlation": "",
                    "notes": "one or both equity curves missing/empty",
                }
            )
            continue
        merged = a.merge(b, on="_date", how="inner", suffixes=("_a", "_b")).dropna()
        corr = merged["return_a"].corr(merged["return_b"]) if len(merged) >= 2 else np.nan
        rows.append(
            {
                "strategy_a": strategy_a,
                "strategy_b": strategy_b,
                "aligned_days": int(len(merged)),
                "return_correlation": _number_or_blank(corr),
                "notes": "aligned by normalized equity dates",
            }
        )
    return pd.DataFrame(rows)


def build_drawdown_overlap_summary(reports: Iterable[StrategyReport], *, deep_threshold_pct: float = 10.0) -> pd.DataFrame:
    drawdowns: dict[str, pd.DataFrame] = {}
    rows = []
    for report in reports:
        equity = report.equity_curve
        if equity is None or equity.empty:
            rows.append(
                {
                    "row_type": "strategy",
                    "strategy": report.strategy,
                    "strategy_a": "",
                    "strategy_b": "",
                    "max_drawdown_pct": "",
                    "drawdown_days": 0,
                    "deep_drawdown_days": 0,
                    "date_range": "",
                    "overlapping_drawdown_days": "",
                    "overlapping_deep_drawdown_days": "",
                    "overlap_share_of_a_drawdown_days": "",
                    "overlap_share_of_b_drawdown_days": "",
                }
            )
            continue
        frame = equity[["_date", "equity"]].copy().dropna()
        frame["equity"] = pd.to_numeric(frame["equity"], errors="coerce")
        frame = frame.dropna(subset=["equity"]).sort_values("_date")
        frame["peak"] = frame["equity"].cummax()
        frame["drawdown_pct"] = np.where(frame["peak"] > 0, (frame["equity"] / frame["peak"] - 1.0) * 100.0, np.nan)
        frame["is_drawdown"] = frame["drawdown_pct"] < 0
        frame["is_deep_drawdown"] = frame["drawdown_pct"] <= -abs(deep_threshold_pct)
        drawdowns[report.strategy] = frame
        rows.append(
            {
                "row_type": "strategy",
                "strategy": report.strategy,
                "strategy_a": "",
                "strategy_b": "",
                "max_drawdown_pct": _number_or_blank(frame["drawdown_pct"].min()),
                "drawdown_days": int(frame["is_drawdown"].sum()),
                "deep_drawdown_days": int(frame["is_deep_drawdown"].sum()),
                "date_range": f"{_date_text(frame['_date'].min())}:{_date_text(frame['_date'].max())}",
                "overlapping_drawdown_days": "",
                "overlapping_deep_drawdown_days": "",
                "overlap_share_of_a_drawdown_days": "",
                "overlap_share_of_b_drawdown_days": "",
            }
        )
    for strategy_a, strategy_b in combinations(STRATEGY_LABELS, 2):
        a = drawdowns.get(strategy_a)
        b = drawdowns.get(strategy_b)
        if a is None or b is None:
            overlap = deep_overlap = 0
            share_a = share_b = ""
        else:
            merged = a[["_date", "is_drawdown", "is_deep_drawdown"]].merge(
                b[["_date", "is_drawdown", "is_deep_drawdown"]],
                on="_date",
                how="inner",
                suffixes=("_a", "_b"),
            )
            overlap = int((merged["is_drawdown_a"] & merged["is_drawdown_b"]).sum())
            deep_overlap = int((merged["is_deep_drawdown_a"] & merged["is_deep_drawdown_b"]).sum())
            a_days = int(a["is_drawdown"].sum())
            b_days = int(b["is_drawdown"].sum())
            share_a = overlap / a_days if a_days else ""
            share_b = overlap / b_days if b_days else ""
        rows.append(
            {
                "row_type": "pair",
                "strategy": "",
                "strategy_a": strategy_a,
                "strategy_b": strategy_b,
                "max_drawdown_pct": "",
                "drawdown_days": "",
                "deep_drawdown_days": "",
                "date_range": "",
                "overlapping_drawdown_days": overlap,
                "overlapping_deep_drawdown_days": deep_overlap,
                "overlap_share_of_a_drawdown_days": _number_or_blank(share_a),
                "overlap_share_of_b_drawdown_days": _number_or_blank(share_b),
            }
        )
    return pd.DataFrame(rows)


def build_metadata(
    reports: Iterable[StrategyReport],
    *,
    output_dir: Path,
    anchor_strategy: StrategyLabel,
    overlap_scope: OverlapScope,
    lookback_days: int,
    diagnostic_window_days: int,
    top_n: int,
    outputs: Mapping[str, Path],
) -> dict[str, object]:
    report_list = list(reports)
    return {
        "input_folders": {report.strategy: str(report.input_dir) for report in report_list},
        "output_dir": str(output_dir),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "anchor_strategy": anchor_strategy,
        "overlap_scope": overlap_scope,
        "lookback_days": lookback_days,
        "diagnostic_window_days": diagnostic_window_days,
        "top_n": top_n,
        "files": {
            report.strategy: {
                "found": sorted(report.files),
                "missing": list(report.missing_files),
            }
            for report in report_list
        },
        "optional_signal_counterfactual_files": {
            report.strategy: {
                name: name in report.files
                for name in OPTIONAL_FILES
            }
            for report in report_list
        },
        "detected_columns": {report.strategy: dict(report.detected_columns) for report in report_list},
        "counterfactual_schema_support": {
            report.strategy: report.counterfactual_schema_supported for report in report_list
        },
        "limitations": {report.strategy: list(report.limitations) for report in report_list},
        "lookahead_warning": DATE_WARNING,
        "caveat": ENSEMBLE_CAVEAT,
        "calendar_day_limitation": "Confirmation windows use calendar days; no session calendar is applied.",
        "outputs": {name: str(path) for name, path in sorted(outputs.items())},
    }


def normalize_strategy_label(value: str) -> StrategyLabel:
    label = str(value).strip().upper()
    if label not in STRATEGY_LABELS:
        raise ValueError(f"strategy label must be one of {', '.join(STRATEGY_LABELS)}; got {value!r}")
    return label  # type: ignore[return-value]


def _write_signal_outputs(reports: list[StrategyReport], output_dir: Path) -> dict[str, Path]:
    outputs = {}
    same_day = build_signal_overlap_same_day(reports)
    outputs["signal_overlap_same_day.csv"] = _write_csv(same_day, output_dir / "signal_overlap_same_day.csv")
    outputs["signal_pair_overlap_summary.csv"] = _write_csv(
        build_signal_pair_overlap_summary(reports),
        output_dir / "signal_pair_overlap_summary.csv",
    )
    outputs["signal_consensus_by_year.csv"] = _write_csv(
        build_signal_consensus_by_year(same_day),
        output_dir / "signal_consensus_by_year.csv",
    )
    outputs["signal_consensus_by_symbol.csv"] = _write_csv(
        build_signal_consensus_by_symbol(same_day),
        output_dir / "signal_consensus_by_symbol.csv",
    )
    return outputs


def _write_executed_trade_outputs(
    reports: list[StrategyReport],
    output_dir: Path,
    *,
    anchor_strategy: StrategyLabel,
    lookback_days: int,
    diagnostic_window_days: int,
) -> dict[str, Path]:
    outputs = {}
    outputs["entry_overlap_same_day.csv"] = _write_csv(
        build_entry_overlap_same_day(reports),
        output_dir / "entry_overlap_same_day.csv",
    )
    outputs["strategy_pair_overlap_summary.csv"] = _write_csv(
        build_strategy_pair_overlap_summary(
            reports,
            anchor_strategy=anchor_strategy,
            lookback_days=lookback_days,
        ),
        output_dir / "strategy_pair_overlap_summary.csv",
    )
    anchor = build_anchor_confirmed_vs_unconfirmed(
        reports,
        anchor_strategy=anchor_strategy,
        lookback_days=lookback_days,
        diagnostic_window_days=diagnostic_window_days,
    )
    outputs["anchor_confirmed_vs_unconfirmed.csv"] = _write_csv(
        anchor,
        output_dir / "anchor_confirmed_vs_unconfirmed.csv",
    )
    outputs["anchor_confirmation_summary.csv"] = _write_csv(
        build_anchor_confirmation_summary(anchor),
        output_dir / "anchor_confirmation_summary.csv",
    )
    outputs["anchor_confirmation_by_strategy.csv"] = _write_csv(
        build_anchor_confirmation_by_strategy(anchor),
        output_dir / "anchor_confirmation_by_strategy.csv",
    )
    outputs["anchor_confirmation_by_year.csv"] = _write_csv(
        build_anchor_confirmation_by_year(anchor),
        output_dir / "anchor_confirmation_by_year.csv",
    )
    outputs["anchor_confirmation_by_symbol.csv"] = _write_csv(
        build_anchor_confirmation_by_symbol(anchor),
        output_dir / "anchor_confirmation_by_symbol.csv",
    )
    return outputs


def _write_counterfactual_outputs(reports: list[StrategyReport], output_dir: Path) -> dict[str, Path]:
    return {
        "counterfactual_inventory.csv": _write_csv(
            build_counterfactual_inventory(reports),
            output_dir / "counterfactual_inventory.csv",
        ),
        "counterfactual_summary_by_strategy.csv": _write_csv(
            build_counterfactual_summary_by_strategy(reports),
            output_dir / "counterfactual_summary_by_strategy.csv",
        ),
        "counterfactual_by_year_combined.csv": _write_csv(
            build_counterfactual_by_year_combined(reports),
            output_dir / "counterfactual_by_year_combined.csv",
        ),
        "counterfactual_by_symbol_combined.csv": _write_csv(
            build_counterfactual_by_symbol_combined(reports),
            output_dir / "counterfactual_by_symbol_combined.csv",
        ),
    }


def _validate_scope(value: str) -> OverlapScope:
    if value not in ("executed_trades", "signals", "counterfactual", "all"):
        raise ValueError("overlap_scope must be one of: executed_trades, signals, counterfactual, all")
    return value  # type: ignore[return-value]


def _detect_required(frame: pd.DataFrame, candidates: Iterable[str], strategy: str, file_name: str) -> str:
    column = _first_existing(frame, candidates)
    if column is None:
        expected = ", ".join(candidates)
        raise ValueError(f"{strategy} {file_name} missing required column; expected one of: {expected}")
    return column


def _first_existing(frame: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
    return None


def _normalize_signal_frame(frame: pd.DataFrame, columns: Mapping[str, str | None], strategy: str) -> None:
    frame["symbol"] = frame[str(columns["symbol"])].astype(str).str.strip().str.upper()
    frame["_signal_date"] = _parse_dates(frame[str(columns["signal_date"])], strategy=strategy, column="signal date")
    frame["strategy"] = strategy


def _normalize_trade_frame(frame: pd.DataFrame, columns: Mapping[str, str | None], strategy: str) -> None:
    frame["symbol"] = frame[str(columns["symbol"])].astype(str).str.strip().str.upper()
    frame["_entry_date"] = _parse_dates(frame[str(columns["entry_date"])], strategy=strategy, column="entry_date")
    if columns.get("exit_date"):
        frame["_exit_date"] = _parse_dates(frame[str(columns["exit_date"])], strategy=strategy, column="exit_date")
    else:
        frame["_exit_date"] = pd.NaT
    if columns.get("net_pnl"):
        frame["net_pnl"] = pd.to_numeric(frame[str(columns["net_pnl"])], errors="coerce")
    else:
        frame["net_pnl"] = np.nan
    if columns.get("exit_reason"):
        frame["exit_reason"] = frame[str(columns["exit_reason"])].astype(str)
    else:
        frame["exit_reason"] = ""
    if columns.get("trade_id"):
        frame["trade_id"] = frame[str(columns["trade_id"])]
    frame["strategy"] = strategy


def _normalize_equity_frame(frame: pd.DataFrame, columns: Mapping[str, str | None], strategy: str) -> None:
    frame["_date"] = _parse_dates(frame[str(columns["date"])], strategy=strategy, column="equity date")
    frame["equity"] = pd.to_numeric(frame[str(columns["equity"])], errors="coerce")
    frame["strategy"] = strategy


def _parse_dates(values: pd.Series, *, strategy: str, column: str) -> pd.Series:
    parsed = pd.to_datetime(values, errors="coerce").dt.normalize()
    if parsed.isna().any() and values.notna().any():
        raise ValueError(f"{strategy} has unparseable {column} values")
    return parsed


def _counterfactual_schema_status(
    summary: pd.DataFrame | None,
    by_symbol: pd.DataFrame | None,
    by_year: pd.DataFrame | None,
) -> tuple[bool, list[str]]:
    limitations: list[str] = []
    supported = False
    if summary is not None:
        supported = True
    if by_symbol is not None:
        if "symbol" in by_symbol.columns:
            supported = True
        else:
            limitations.append("counterfactual_by_symbol.csv missing symbol column; combined symbol output limited")
    if by_year is not None:
        if "year" in by_year.columns:
            supported = True
        else:
            limitations.append("counterfactual_by_year.csv missing year column; combined year output limited")
    if summary is None and by_symbol is None and by_year is None:
        limitations.append("counterfactual files missing; schema support unavailable")
    limitations.append("counterfactual files are summarized separately from realized PnL")
    return supported, limitations


def _combined_signals(reports: Iterable[StrategyReport]) -> pd.DataFrame:
    frames = [_strategy_signals(report) for report in reports]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame(columns=["strategy", "symbol", "_signal_date"])
    return pd.concat(frames, ignore_index=True)


def _strategy_signals(report: StrategyReport) -> pd.DataFrame:
    if report.signal_log is None:
        return pd.DataFrame(columns=["strategy", "symbol", "_signal_date"])
    return report.signal_log[["strategy", "symbol", "_signal_date"]].dropna(subset=["symbol", "_signal_date"]).copy()


def _combined_trades(reports: Iterable[StrategyReport]) -> pd.DataFrame:
    frames = [_strategy_trades(report) for report in reports]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame(columns=["strategy", "symbol", "_entry_date"])
    return pd.concat(frames, ignore_index=True)


def _strategy_trades(report: StrategyReport) -> pd.DataFrame:
    trades = _executed_trades(report)
    if trades is None:
        return pd.DataFrame(columns=["strategy", "symbol", "_entry_date"])
    columns = [
        column
        for column in (
            "strategy",
            "trade_id",
            "symbol",
            "_entry_date",
            "_exit_date",
            "exit_reason",
            "net_pnl",
        )
        if column in trades.columns
    ]
    return trades[columns].dropna(subset=["symbol", "_entry_date"]).copy()


def _executed_trades(report: StrategyReport) -> pd.DataFrame | None:
    return report.trade_pnl_log if report.trade_pnl_log is not None else report.trade_log


def _same_day_overlap_count(a: pd.DataFrame, b: pd.DataFrame, date_column: str) -> int:
    if a.empty or b.empty:
        return 0
    left = a[[date_column, "symbol"]].drop_duplicates()
    right = b[[date_column, "symbol"]].drop_duplicates()
    return int(len(left.merge(right, on=[date_column, "symbol"], how="inner")))


def _anchor_prior_confirmation_count(anchor_trades: pd.DataFrame, signals: pd.DataFrame, *, lookback_days: int) -> int:
    count = 0
    if anchor_trades.empty or signals.empty:
        return count
    for _, trade in anchor_trades.iterrows():
        same_symbol = signals[signals["symbol"] == trade["symbol"]]
        entry = trade["_entry_date"]
        if same_symbol.empty or pd.isna(entry):
            continue
        hits = same_symbol[
            (same_symbol["_signal_date"] <= entry)
            & (same_symbol["_signal_date"] >= entry - pd.Timedelta(days=lookback_days))
        ]
        if not hits.empty:
            count += 1
    return count


def _confirmation_group_metrics(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    rows = []
    for group_key, group in frame.groupby(keys, dropna=False, sort=True):
        if not isinstance(group_key, tuple):
            group_key = (group_key,)
        row = {key: value for key, value in zip(keys, group_key)}
        metrics = _pnl_metrics(group)
        row.update(
            {
                "trades": metrics["trades"],
                "win_rate": metrics["win_rate"],
                "net_pnl": metrics["net_pnl"],
                "profit_factor": metrics["profit_factor"],
                "avg_net_pnl": metrics["avg_net_pnl"],
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def _pnl_metrics(frame: pd.DataFrame) -> dict[str, object]:
    pnl = pd.to_numeric(frame.get("net_pnl", pd.Series(dtype=float)), errors="coerce").dropna()
    trades = int(len(pnl))
    wins = int((pnl > 0).sum())
    losses = int((pnl < 0).sum())
    gross_profit = float(pnl[pnl > 0].sum()) if trades else 0.0
    gross_loss = float(pnl[pnl < 0].sum()) if trades else 0.0
    net_pnl = float(pnl.sum()) if trades else 0.0
    return {
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "win_rate": wins / trades if trades else "",
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "net_pnl": net_pnl,
        "profit_factor": _profit_factor(gross_profit, gross_loss),
        "avg_net_pnl": float(pnl.mean()) if trades else "",
        "median_net_pnl": float(pnl.median()) if trades else "",
        "best_trade": float(pnl.max()) if trades else "",
        "worst_trade": float(pnl.min()) if trades else "",
    }


def _profit_factor(gross_profit: float, gross_loss: float) -> object:
    if gross_loss == 0:
        return "" if gross_profit == 0 else np.inf
    return gross_profit / abs(gross_loss)


def _combine_counterfactual_frames(
    reports: Iterable[StrategyReport],
    attribute: str,
    *,
    required_key: str,
) -> pd.DataFrame:
    frames = []
    for report in reports:
        source = getattr(report, attribute)
        if source is None:
            continue
        if required_key not in source.columns:
            frames.append(
                pd.DataFrame(
                    [
                        {
                            "strategy": report.strategy,
                            required_key: "",
                            "notes": f"source missing {required_key}; not joined to realized PnL",
                        }
                    ]
                )
            )
            continue
        frame = source.copy()
        frame.insert(0, "strategy", report.strategy)
        frame["notes"] = "counterfactual/hypothesis-generation only; not realized portfolio performance"
        frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=["strategy", required_key, "notes"])
    return pd.concat(frames, ignore_index=True)


def _first_metric_value(frame: pd.DataFrame, candidates: Iterable[str]) -> object:
    column = _first_existing(frame, candidates)
    if column is None or frame.empty:
        return ""
    return frame[column].iloc[0]


def _consensus_group(count: int) -> str:
    if count <= 1:
        return "single_strategy"
    if count == 2:
        return "two_strategies"
    return "three_plus_strategies"


def _row_count(frame: pd.DataFrame | None) -> int:
    return 0 if frame is None else int(len(frame))


def _min_date(frame: pd.DataFrame | None, column: str) -> str:
    if frame is None or frame.empty or column not in frame.columns:
        return ""
    return _date_text(frame[column].min())


def _max_date(frame: pd.DataFrame | None, column: str) -> str:
    if frame is None or frame.empty or column not in frame.columns:
        return ""
    return _date_text(frame[column].max())


def _date_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return pd.Timestamp(value).date().isoformat()


def _number_or_blank(value: object) -> object:
    if value == "":
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value


def _write_csv(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def _readme_text() -> str:
    return "\n".join(
        [
            "Cross-Strategy Overlap / Ensemble Feasibility Audit",
            "",
            "- This is not an ensemble backtest.",
            "- This does not prove a voting strategy.",
            "- Executed-trade overlap uses realized backtest trades.",
            "- Signal overlap is opportunity/consensus evidence, not realized PnL.",
            "- Counterfactual outputs are hypothesis-generation only.",
            "- Counterfactual PnL is not realized portfolio performance and cannot be used as ensemble PnL without a separate capital-aware backtest.",
            "- Prior/on-entry confirmation is implementable; future nearby overlap is diagnostic only.",
            "- Trade counts may become too small.",
            "- Standalone weak strategies can still be useful as confirmation, but that must be tested later.",
            "- Any ensemble must be pre-registered before implementation.",
            "- Confirmation windows use calendar days unless a separate session-calendar audit is added.",
            "",
        ]
    )
