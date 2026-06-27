"""Phase 35C pre-registered S2 confirmation robustness audit.

This is a read-only reporting helper. It uses retained strategy report CSVs to
test pre-registered S2 confirmation candidates across trading-session lookbacks.
It does not create a strategy, optimize rules, size orders, allocate capital, or
combine strategy portfolios.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from bisect import bisect_left, bisect_right
import json
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import pandas as pd

from veridian_quant.v2.analysis.cross_strategy_overlap_audit import (
    STRATEGY_LABELS,
    StrategyLabel,
    StrategyReport,
    build_strategy_report_inventory,
    load_strategy_report,
    normalize_strategy_label,
)


DEFAULT_LOOKBACK_SESSIONS = (0, 1, 3, 5)
DEFAULT_OUTPUT_DIR = Path("reports/v2/phase_35c_pre_registered_confirmation_robustness_audit")
DEFAULT_STRATEGY_DIRS = {
    "S1": Path("reports/v2/s1_2020_2026_research200_baseline_all_signal_diagnostics"),
    "S2": Path("reports/v2/s2_markov_2020_2026_research200_exclude_ret_down_full_diagnostics"),
    "S3": Path("reports/v2/s3_trend_pullback_2020_2026_research200_strong_trend_above_sma50_v1"),
    "S4": Path("reports/v2/s4/raw_baselines/research200_atr_compression_v1"),
    "S5": Path("reports/v2/s5_momentum/research200_dual_momentum_63_126d_v1"),
}
CONFIRMERS: tuple[StrategyLabel, ...] = ("S1", "S3", "S4", "S5")
ANCHOR_STRATEGY: StrategyLabel = "S2"
IMPLEMENTABLE_CANDIDATES = (
    "S2 confirmed by S4",
    "S2 confirmed by S1",
    "S2 confirmed by S3",
    "S2 confirmed by S5",
    "S2 confirmed by any one of S1/S3/S4/S5",
    "S2 confirmed by 2+ other strategies",
)
DIAGNOSTIC_CANDIDATES = ("3+ same-day signal consensus", "future/after-entry nearby signals")
CAVEAT = (
    "Phase 35C is a pre-registered read-only robustness audit, not a voting ensemble, "
    "combined portfolio backtest, capital allocation model, optimization pass, or production approval."
)


@dataclass(frozen=True, slots=True)
class Phase35CResult:
    output_dir: Path
    outputs: dict[str, Path]
    metadata: dict[str, object]


def run_pre_registered_confirmation_robustness_audit(
    strategy_dirs: Mapping[str, Path | str] | None = None,
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    lookback_sessions: Iterable[int] = DEFAULT_LOOKBACK_SESSIONS,
    future_diagnostic_sessions: int = 3,
) -> Phase35CResult:
    """Run the Phase 35C read-only S2 confirmation robustness audit."""

    lookbacks = _validate_lookbacks(lookback_sessions)
    if future_diagnostic_sessions < 0:
        raise ValueError("future_diagnostic_sessions must be >= 0")
    normalized_dirs = _normalize_strategy_dirs(strategy_dirs or DEFAULT_STRATEGY_DIRS)
    reports = [load_strategy_report(label, normalized_dirs[label]) for label in STRATEGY_LABELS]
    report_map = {report.strategy: report for report in reports}
    if report_map[ANCHOR_STRATEGY].trade_pnl_log is None and report_map[ANCHOR_STRATEGY].trade_log is None:
        raise ValueError("S2 must have trade_pnl_log.csv or trade_log.csv for anchor outcomes")

    session_dates = derive_session_dates(reports)
    detail = build_s2_trade_confirmation_detail(
        report_map,
        session_dates=session_dates,
        lookback_sessions=lookbacks,
        future_diagnostic_sessions=future_diagnostic_sessions,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}
    outputs["phase_35c_pre_registered_rules.json"] = _write_json(
        build_pre_registered_rules(lookbacks, future_diagnostic_sessions),
        output_path / "phase_35c_pre_registered_rules.json",
    )
    outputs["strategy_report_inventory.csv"] = _write_csv(
        build_strategy_report_inventory(reports),
        output_path / "strategy_report_inventory.csv",
    )
    outputs["s2_trade_confirmation_detail.csv"] = _write_csv(
        detail,
        output_path / "s2_trade_confirmation_detail.csv",
    )
    outputs["s2_confirmation_by_lookback.csv"] = _write_csv(
        build_confirmation_by_lookback(detail),
        output_path / "s2_confirmation_by_lookback.csv",
    )
    outputs["s2_confirmation_by_strategy_and_lookback.csv"] = _write_csv(
        build_confirmation_by_strategy_and_lookback(detail),
        output_path / "s2_confirmation_by_strategy_and_lookback.csv",
    )
    outputs["s2_confirmation_by_count_bucket_and_lookback.csv"] = _write_csv(
        build_confirmation_by_count_bucket_and_lookback(detail),
        output_path / "s2_confirmation_by_count_bucket_and_lookback.csv",
    )
    outputs["s2_confirmation_by_year_and_lookback.csv"] = _write_csv(
        build_confirmation_by_year_and_lookback(detail),
        output_path / "s2_confirmation_by_year_and_lookback.csv",
    )
    outputs["s2_confirmation_by_symbol_and_lookback.csv"] = _write_csv(
        build_confirmation_by_symbol_and_lookback(detail),
        output_path / "s2_confirmation_by_symbol_and_lookback.csv",
    )
    outputs["future_diagnostic_confirmation_summary.csv"] = _write_csv(
        build_future_diagnostic_confirmation_summary(detail),
        output_path / "future_diagnostic_confirmation_summary.csv",
    )
    readme_path = output_path / "robustness_readme.txt"
    readme_path.write_text(_readme_text(), encoding="utf-8")
    outputs["robustness_readme.txt"] = readme_path

    metadata = build_metadata(
        reports,
        output_dir=output_path,
        lookback_sessions=lookbacks,
        future_diagnostic_sessions=future_diagnostic_sessions,
        session_dates=session_dates,
        outputs=outputs,
    )
    outputs["phase_35c_metadata.json"] = _write_json(metadata, output_path / "phase_35c_metadata.json")
    return Phase35CResult(output_path, outputs, metadata)


def derive_session_dates(reports: Iterable[StrategyReport]) -> tuple[pd.Timestamp, ...]:
    """Derive trading/session dates from available report dates."""

    dates: list[pd.Timestamp] = []
    for report in reports:
        if report.signal_log is not None and "_signal_date" in report.signal_log.columns:
            dates.extend(report.signal_log["_signal_date"].dropna().tolist())
        for frame in (report.trade_log, report.trade_pnl_log):
            if frame is not None and "_entry_date" in frame.columns:
                dates.extend(frame["_entry_date"].dropna().tolist())
        if report.equity_curve is not None and "_date" in report.equity_curve.columns:
            dates.extend(report.equity_curve["_date"].dropna().tolist())
    unique = sorted({pd.Timestamp(date).normalize() for date in dates})
    if not unique:
        raise ValueError("cannot derive trading sessions from empty report dates")
    return tuple(unique)


def build_s2_trade_confirmation_detail(
    reports: Mapping[str, StrategyReport],
    *,
    session_dates: Iterable[pd.Timestamp],
    lookback_sessions: Iterable[int],
    future_diagnostic_sessions: int,
) -> pd.DataFrame:
    """Annotate each S2 trade for each pre-registered session lookback."""

    sessions = tuple(sorted({pd.Timestamp(date).normalize() for date in session_dates}))
    anchor_trades = _strategy_trades(reports[ANCHOR_STRATEGY])
    signals_by_strategy = {
        strategy: _strategy_signals(reports[strategy])
        for strategy in CONFIRMERS
    }
    signal_index = {
        strategy: _build_signal_date_index(signals)
        for strategy, signals in signals_by_strategy.items()
    }
    all_signal_index = _build_all_signal_date_index(signals_by_strategy)

    rows: list[dict[str, object]] = []
    for row_id, trade in anchor_trades.reset_index(drop=True).iterrows():
        entry_date = pd.Timestamp(trade["_entry_date"]).normalize()
        symbol = trade["symbol"]
        for lookback in lookback_sessions:
            window_start = session_lookback_start(entry_date, lookback, sessions)
            confirming: list[str] = []
            latest_dates: list[pd.Timestamp] = []
            per_strategy: dict[str, bool] = {}
            for strategy in CONFIRMERS:
                dates = signal_index[strategy].get(symbol, ())
                hits = _dates_in_window(dates, window_start, entry_date)
                confirmed = bool(hits)
                per_strategy[strategy] = confirmed
                if confirmed:
                    confirming.append(strategy)
                    latest_dates.append(hits[-1])

            future_end = session_forward_end(entry_date, future_diagnostic_sessions, sessions)
            future_strategies = _strategies_in_window(
                all_signal_index.get(symbol, {}),
                entry_date,
                future_end,
                include_start=False,
            )
            same_day_consensus = len(
                _strategies_in_window(
                    all_signal_index.get(symbol, {}),
                    entry_date,
                    entry_date,
                    include_start=True,
                )
            )
            latest = max(latest_dates) if latest_dates else pd.NaT
            rows.append(
                {
                    "anchor_strategy": ANCHOR_STRATEGY,
                    "trade_id": trade.get("trade_id", row_id),
                    "symbol": symbol,
                    "entry_date": _date_text(entry_date),
                    "exit_date": _date_text(trade.get("_exit_date", pd.NaT)),
                    "entry_year": int(entry_date.year),
                    "exit_reason": trade.get("exit_reason", ""),
                    "net_pnl": _number_or_blank(trade.get("net_pnl", np.nan)),
                    "lookback_sessions": int(lookback),
                    "lookback_start_session": _date_text(window_start),
                    "confirmed_by_s1": per_strategy["S1"],
                    "confirmed_by_s3": per_strategy["S3"],
                    "confirmed_by_s4": per_strategy["S4"],
                    "confirmed_by_s5": per_strategy["S5"],
                    "confirmed_by_any": bool(confirming),
                    "confirming_strategy_count": len(confirming),
                    "confirmation_count_bucket": _count_bucket(len(confirming)),
                    "confirming_strategies": "|".join(sorted(confirming)),
                    "latest_confirming_signal_date": _date_text(latest),
                    "sessions_since_latest_confirmation": _session_distance(latest, entry_date, sessions),
                    "future_diagnostic_session_end": _date_text(future_end),
                    "future_diagnostic_confirmation_count": len(future_strategies),
                    "future_diagnostic_confirming_strategies": "|".join(sorted(future_strategies)),
                    "same_day_other_strategy_signal_count": int(same_day_consensus),
                    "diagnostic_three_plus_same_day_consensus": bool(same_day_consensus >= 3),
                }
            )
    return pd.DataFrame(rows)


def session_lookback_start(
    entry_date: pd.Timestamp,
    lookback_sessions: int,
    session_dates: Iterable[pd.Timestamp],
) -> pd.Timestamp:
    """Return the earliest allowed session for a session-count lookback."""

    sessions = tuple(sorted({pd.Timestamp(date).normalize() for date in session_dates}))
    entry = pd.Timestamp(entry_date).normalize()
    eligible = [date for date in sessions if date <= entry]
    if not eligible:
        return entry
    entry_session = eligible[-1]
    idx = sessions.index(entry_session)
    start_idx = max(0, idx - lookback_sessions)
    return sessions[start_idx]


def session_forward_end(
    entry_date: pd.Timestamp,
    forward_sessions: int,
    session_dates: Iterable[pd.Timestamp],
) -> pd.Timestamp:
    sessions = tuple(sorted({pd.Timestamp(date).normalize() for date in session_dates}))
    entry = pd.Timestamp(entry_date).normalize()
    eligible = [date for date in sessions if date >= entry]
    if not eligible:
        return entry
    entry_session = eligible[0]
    idx = sessions.index(entry_session)
    end_idx = min(len(sessions) - 1, idx + forward_sessions)
    return sessions[end_idx]


def build_confirmation_by_lookback(detail: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for lookback, frame in detail.groupby("lookback_sessions", sort=True):
        rows.append({"lookback_sessions": lookback, "confirmation_group": "confirmed_by_any", **_metrics(frame[frame["confirmed_by_any"] == True])})
        rows.append({"lookback_sessions": lookback, "confirmation_group": "unconfirmed", **_metrics(frame[frame["confirmed_by_any"] == False])})
    return pd.DataFrame(rows)


def build_confirmation_by_strategy_and_lookback(detail: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for lookback, frame in detail.groupby("lookback_sessions", sort=True):
        for strategy, column in (("S1", "confirmed_by_s1"), ("S3", "confirmed_by_s3"), ("S4", "confirmed_by_s4"), ("S5", "confirmed_by_s5")):
            rows.append(
                {
                    "lookback_sessions": lookback,
                    "confirming_strategy": strategy,
                    **_metrics(frame[frame[column] == True]),
                }
            )
    return pd.DataFrame(rows)


def build_confirmation_by_count_bucket_and_lookback(detail: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (lookback, bucket), frame in detail.groupby(["lookback_sessions", "confirmation_count_bucket"], sort=True):
        rows.append({"lookback_sessions": lookback, "confirmation_count_bucket": bucket, **_metrics(frame)})
    return pd.DataFrame(rows)


def build_confirmation_by_year_and_lookback(detail: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (lookback, year, confirmed), frame in detail.groupby(["lookback_sessions", "entry_year", "confirmed_by_any"], sort=True):
        rows.append(
            {
                "lookback_sessions": lookback,
                "year": year,
                "confirmation_group": "confirmed_by_any" if confirmed else "unconfirmed",
                **_metrics(frame),
            }
        )
    return pd.DataFrame(rows)


def build_confirmation_by_symbol_and_lookback(detail: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (lookback, symbol, confirmed), frame in detail.groupby(["lookback_sessions", "symbol", "confirmed_by_any"], sort=True):
        rows.append(
            {
                "lookback_sessions": lookback,
                "symbol": symbol,
                "confirmation_group": "confirmed_by_any" if confirmed else "unconfirmed",
                **_metrics(frame),
            }
        )
    return pd.DataFrame(rows)


def build_future_diagnostic_confirmation_summary(detail: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for lookback, frame in detail.groupby("lookback_sessions", sort=True):
        future = frame[frame["future_diagnostic_confirmation_count"] > 0]
        consensus = frame[frame["diagnostic_three_plus_same_day_consensus"] == True]
        rows.append(
            {
                "lookback_sessions": lookback,
                "diagnostic_type": "future_after_entry_confirmation",
                **_metrics(future),
                "notes": "Diagnostic only; excluded from implementable confirmation.",
            }
        )
        rows.append(
            {
                "lookback_sessions": lookback,
                "diagnostic_type": "three_plus_same_day_other_strategy_consensus",
                **_metrics(consensus),
                "notes": "Diagnostic only; not an approved voting rule.",
            }
        )
    return pd.DataFrame(rows)


def build_pre_registered_rules(
    lookback_sessions: Iterable[int],
    future_diagnostic_sessions: int,
) -> dict[str, object]:
    return {
        "phase": "35C",
        "anchor_strategy": ANCHOR_STRATEGY,
        "anchor_outcome": "S2 executed trades using realized net_pnl from retained reports",
        "lookback_type": "trading_sessions_derived_from_available_report_dates",
        "lookback_sessions": list(lookback_sessions),
        "future_diagnostic_sessions": future_diagnostic_sessions,
        "primary_candidate": "S2 confirmed by S4",
        "control_candidates": [
            "S2 confirmed by S1",
            "S2 confirmed by S3",
            "S2 confirmed by S5",
            "S2 confirmed by any one of S1/S3/S4/S5",
            "S2 confirmed by 2+ other strategies",
        ],
        "diagnostic_candidates": list(DIAGNOSTIC_CANDIDATES),
        "constraints": [
            "read-only audit/reporting only",
            "no voting ensemble implementation",
            "no combined portfolio backtest",
            "no production approval",
            "no optimization by final PnL",
            "no weights or capital allocation",
            "future/after-entry signals are diagnostic only",
        ],
    }


def build_metadata(
    reports: Iterable[StrategyReport],
    *,
    output_dir: Path,
    lookback_sessions: tuple[int, ...],
    future_diagnostic_sessions: int,
    session_dates: tuple[pd.Timestamp, ...],
    outputs: Mapping[str, Path],
) -> dict[str, object]:
    report_list = list(reports)
    return {
        "phase": "35C",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(output_dir),
        "input_folders": {report.strategy: str(report.input_dir) for report in report_list},
        "anchor_strategy": ANCHOR_STRATEGY,
        "confirming_strategies": list(CONFIRMERS),
        "lookback_sessions": list(lookback_sessions),
        "future_diagnostic_sessions": future_diagnostic_sessions,
        "session_calendar_source": "sorted union of available signal, trade entry, and equity dates in retained report CSVs",
        "session_count": len(session_dates),
        "session_min_date": _date_text(session_dates[0]),
        "session_max_date": _date_text(session_dates[-1]),
        "pre_registered_candidates": {
            "primary": "S2 confirmed by S4",
            "controls": [candidate for candidate in IMPLEMENTABLE_CANDIDATES if candidate != "S2 confirmed by S4"],
            "diagnostic_only": list(DIAGNOSTIC_CANDIDATES),
        },
        "sample_size_warning_rules": {
            "tiny": "n < 20",
            "weak": "20 <= n < 50",
            "usable_diagnostic_sample": "n >= 50",
        },
        "lookahead_warning": "Signals after S2 entry are diagnostic only and never implementable confirmation.",
        "caveat": CAVEAT,
        "conclusion_style": "Report robustness only; do not automatically approve S2xS4.",
        "outputs": {name: str(path) for name, path in sorted(outputs.items())},
    }


def _normalize_strategy_dirs(strategy_dirs: Mapping[str, Path | str]) -> dict[StrategyLabel, Path]:
    normalized = {normalize_strategy_label(strategy): Path(path) for strategy, path in strategy_dirs.items()}
    missing = [label for label in STRATEGY_LABELS if label not in normalized]
    if missing:
        raise ValueError(f"missing strategy directories for: {', '.join(missing)}")
    return normalized


def _validate_lookbacks(values: Iterable[int]) -> tuple[int, ...]:
    lookbacks = tuple(sorted({int(value) for value in values}))
    if not lookbacks:
        raise ValueError("at least one lookback session window is required")
    if any(value < 0 for value in lookbacks):
        raise ValueError("lookback session windows must be >= 0")
    return lookbacks


def _strategy_trades(report: StrategyReport) -> pd.DataFrame:
    frame = report.trade_pnl_log if report.trade_pnl_log is not None else report.trade_log
    if frame is None:
        return pd.DataFrame(columns=["strategy", "trade_id", "symbol", "_entry_date", "_exit_date", "exit_reason", "net_pnl"])
    columns = [
        column
        for column in ("strategy", "trade_id", "symbol", "_entry_date", "_exit_date", "exit_reason", "net_pnl")
        if column in frame.columns
    ]
    return frame[columns].dropna(subset=["symbol", "_entry_date"]).copy()


def _strategy_signals(report: StrategyReport) -> pd.DataFrame:
    if report.signal_log is None:
        return pd.DataFrame(columns=["strategy", "symbol", "_signal_date"])
    return report.signal_log[["strategy", "symbol", "_signal_date"]].dropna(subset=["symbol", "_signal_date"]).copy()


def _build_signal_date_index(signals: pd.DataFrame) -> dict[str, tuple[pd.Timestamp, ...]]:
    if signals.empty:
        return {}
    index: dict[str, tuple[pd.Timestamp, ...]] = {}
    for symbol, group in signals.groupby("symbol", sort=False):
        index[str(symbol)] = tuple(sorted({pd.Timestamp(value).normalize() for value in group["_signal_date"]}))
    return index


def _build_all_signal_date_index(
    signals_by_strategy: Mapping[StrategyLabel, pd.DataFrame],
) -> dict[str, dict[StrategyLabel, tuple[pd.Timestamp, ...]]]:
    index: dict[str, dict[StrategyLabel, tuple[pd.Timestamp, ...]]] = {}
    for strategy, signals in signals_by_strategy.items():
        for symbol, dates in _build_signal_date_index(signals).items():
            index.setdefault(symbol, {})[strategy] = dates
    return index


def _dates_in_window(
    dates: tuple[pd.Timestamp, ...],
    start: pd.Timestamp,
    end: pd.Timestamp,
    *,
    include_start: bool = True,
) -> tuple[pd.Timestamp, ...]:
    if not dates:
        return ()
    left = bisect_left(dates, start) if include_start else bisect_right(dates, start)
    right = bisect_right(dates, end)
    return dates[left:right]


def _strategies_in_window(
    symbol_index: Mapping[StrategyLabel, tuple[pd.Timestamp, ...]],
    start: pd.Timestamp,
    end: pd.Timestamp,
    *,
    include_start: bool,
) -> tuple[StrategyLabel, ...]:
    strategies = [
        strategy
        for strategy, dates in symbol_index.items()
        if _dates_in_window(dates, start, end, include_start=include_start)
    ]
    return tuple(sorted(strategies))


def _session_distance(start: pd.Timestamp, end: pd.Timestamp, sessions: Iterable[pd.Timestamp]) -> object:
    if pd.isna(start) or pd.isna(end):
        return ""
    session_list = tuple(sorted({pd.Timestamp(date).normalize() for date in sessions}))
    start_ts = pd.Timestamp(start).normalize()
    end_ts = pd.Timestamp(end).normalize()
    if start_ts not in session_list or end_ts not in session_list:
        return ""
    return session_list.index(end_ts) - session_list.index(start_ts)


def _count_bucket(count: int) -> str:
    if count <= 0:
        return "unconfirmed"
    if count == 1:
        return "confirmed_by_1"
    if count == 2:
        return "confirmed_by_2"
    return "confirmed_by_3_plus"


def _metrics(frame: pd.DataFrame) -> dict[str, object]:
    pnl = pd.to_numeric(frame.get("net_pnl", pd.Series(dtype=float)), errors="coerce").dropna()
    trades = int(len(pnl))
    wins = int((pnl > 0).sum())
    losses = int((pnl < 0).sum())
    gross_profit = float(pnl[pnl > 0].sum()) if trades else 0.0
    gross_loss = float(pnl[pnl < 0].sum()) if trades else 0.0
    net_pnl = float(pnl.sum()) if trades else 0.0
    return {
        "trades": trades,
        "sample_size_warning": _sample_size_warning(trades),
        "wins": wins,
        "losses": losses,
        "win_rate": wins / trades if trades else "",
        "net_pnl": net_pnl,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": _profit_factor(gross_profit, gross_loss),
        "avg_net_pnl": float(pnl.mean()) if trades else "",
        "median_net_pnl": float(pnl.median()) if trades else "",
        "best_trade": float(pnl.max()) if trades else "",
        "worst_trade": float(pnl.min()) if trades else "",
    }


def _sample_size_warning(trades: int) -> str:
    if trades < 20:
        return "tiny"
    if trades < 50:
        return "weak"
    return "usable_diagnostic_sample"


def _profit_factor(gross_profit: float, gross_loss: float) -> object:
    if gross_loss == 0:
        return "" if gross_profit == 0 else np.inf
    return gross_profit / abs(gross_loss)


def _date_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return pd.Timestamp(value).date().isoformat()


def _number_or_blank(value: object) -> object:
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


def _write_json(payload: Mapping[str, object], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return path


def _readme_text() -> str:
    return "\n".join(
        [
            "Phase 35C Pre-Registered Cross-Strategy Confirmation Robustness Audit",
            "",
            "- This is not a voting ensemble implementation.",
            "- This is not a combined portfolio backtest.",
            "- This is not production approval.",
            "- This audit uses S2 executed trades and realized S2 net_pnl as the anchor outcome.",
            "- Confirmation is based on same-symbol other-strategy signals on or before S2 entry.",
            "- Lookbacks are counted in trading/session dates derived from retained report CSVs, not calendar days.",
            "- Future/after-entry signals are diagnostic only and never implementable confirmation.",
            "- Primary pre-registered candidate: S2 confirmed by S4.",
            "- Controls: S1, S3, S5, any one confirmer, and 2+ confirmer buckets.",
            "- 3+ same-day signal consensus is diagnostic only and is not an approved voting rule.",
            "- Sample-size warnings: n < 20 tiny; n < 50 weak; n >= 50 usable diagnostic sample.",
            "- The audit should report whether S2xS4 is stable across lookbacks, years, symbols, and sample sizes; it should not automatically approve it.",
            "",
        ]
    )
