"""Read-only S2 state x risk / in-trade audit helper.

This module exports diagnostics only. It does not run S2, execute exits,
optimize thresholds, change strategy behavior, or produce production rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import pandas as pd

from veridian_quant.v2.analysis.s2_state_reconstruction import (
    DEFAULT_OHLC_LOOKBACK_BUFFER_DAYS,
    DEFAULT_S2_REPORT_DIR,
    DIAGNOSTIC_ONLY_CAVEAT,
    compute_deterioration_candidates,
    compute_next_open_exit_feasibility,
    expand_trade_lifecycle_dates,
    first_deterioration_occurrences,
    join_daily_states_to_trades,
    load_ohlc_for_reconstruction,
    load_s2_retained_trades,
    parse_s2_state_label,
    reconstruct_daily_state_frames,
    summarize_reconstruction_coverage,
    validate_entry_state_match,
)


DEFAULT_OUTPUT_ROOT = Path("reports/v2")
DEFAULT_UNIVERSE_CSV = Path(
    "config/universes/research/nse_eq_research_200_2018_2026.csv"
)
DEFAULT_CLASSIFICATION_CSV = Path(
    "config/universes/research/nse_eq_research_200_static_classification.csv"
)

READ_ONLY_NON_APPROVAL = (
    "Read-only S2 State x Risk / In-Trade audit diagnostics only. Not a "
    "strategy backtest, not a dynamic exit, not an entry filter, not a risk "
    "rule, and not approved for production behavior."
)

LANE_A_OUTPUTS = {
    "s2_entry_state_performance.csv": ("state_label",),
    "s2_entry_state_by_year.csv": ("state_label", "year"),
    "s2_entry_state_by_liquidity.csv": ("state_label", "liquidity_bucket"),
    "s2_entry_state_by_benchmark_regime.csv": (
        "state_label",
        "benchmark_regime",
    ),
    "s2_entry_state_by_vix_regime.csv": ("state_label", "vix_regime"),
    "s2_entry_state_by_drawdown_state.csv": (
        "state_label",
        "drawdown_state_component",
    ),
    "s2_entry_state_by_gap_context.csv": ("state_label", "pre_entry_gap_bucket"),
    "s2_entry_state_by_exit_reason.csv": ("state_label", "exit_reason"),
    "s2_state_risk_interaction_matrix.csv": (
        "state_label",
        "liquidity_bucket",
        "benchmark_regime",
        "vix_regime",
        "drawdown_state_component",
    ),
}

LANE_B_OUTPUTS = {
    "s2_deterioration_candidate_summary.csv": ("candidate_flag_name",),
    "s2_deterioration_by_year.csv": ("candidate_flag_name", "year"),
    "s2_deterioration_by_liquidity.csv": (
        "candidate_flag_name",
        "liquidity_bucket",
    ),
    "s2_deterioration_by_benchmark_regime.csv": (
        "candidate_flag_name",
        "benchmark_regime",
    ),
    "s2_deterioration_by_vix_regime.csv": ("candidate_flag_name", "vix_regime"),
    "s2_deterioration_by_exit_reason.csv": ("candidate_flag_name", "exit_reason"),
}


@dataclass(frozen=True, slots=True)
class S2StateRiskIntradeAuditResult:
    """Exported output paths and metadata for the read-only audit."""

    output_dir: Path
    outputs: dict[str, Path]
    metadata: dict[str, object]


def sample_size_flag(trades: int) -> str:
    """Return the Phase 36J sample-size flag for a trade count."""

    count = int(trades)
    if count < 20:
        return "INSUFFICIENT"
    if count < 50:
        return "SMALL"
    if count < 100:
        return "USABLE"
    return "STRONG"


def build_entry_state_risk_frame(
    trades: pd.DataFrame,
    *,
    universe: pd.DataFrame | None = None,
    classifications: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build one read-only entry-state x risk row per retained trade."""

    required = {
        "trade_id",
        "symbol",
        "signal_date",
        "entry_date",
        "exit_date",
        "exit_reason",
        "net_pnl",
        "r_multiple",
    }
    missing = sorted(required - set(trades.columns))
    if missing:
        raise ValueError("trades missing required columns: " + ", ".join(missing))

    frame = trades.copy(deep=True)
    if "state_label" not in frame.columns:
        if "stored_entry_state_label" not in frame.columns:
            raise ValueError(
                "trades must include state_label or stored_entry_state_label"
            )
        frame["state_label"] = frame["stored_entry_state_label"]

    frame = frame.drop(
        columns=[
            "return_state",
            "volatility_state",
            "drawdown_state_component",
            "range_state",
            "unknown_components",
            "parse_status",
        ],
        errors="ignore",
    )
    parsed = pd.DataFrame([parse_s2_state_label(value) for value in frame["state_label"]])
    parsed = parsed.drop(columns=["raw_state_label"], errors="ignore")
    frame = pd.concat([frame.reset_index(drop=True), parsed.reset_index(drop=True)], axis=1)

    frame["signal_date"] = _date_series(frame["signal_date"])
    frame["entry_date"] = _date_series(frame["entry_date"])
    frame["exit_date"] = _date_series(frame["exit_date"])
    frame["year"] = frame["entry_date"].dt.year
    frame["net_pnl"] = pd.to_numeric(frame["net_pnl"], errors="coerce")
    frame["r_multiple"] = pd.to_numeric(frame["r_multiple"], errors="coerce")
    frame["exit_reason"] = frame["exit_reason"].fillna("UNKNOWN").astype(str)
    frame["stop_exit"] = frame["exit_reason"].str.lower().str.contains("stop", na=False)
    frame["target_exit"] = frame["exit_reason"].str.lower().str.contains("target", na=False)
    frame["time_stop_exit"] = frame["exit_reason"].str.lower().str.contains("time", na=False)
    frame["gap_stop_exit"] = (
        frame["exit_reason"].str.lower().str.contains("gap", na=False)
        & frame["exit_reason"].str.lower().str.contains("stop", na=False)
    )

    frame = _join_optional_universe(frame, universe)
    frame = _join_optional_classification(frame, classifications)
    _ensure_optional_context_columns(frame)
    return frame.loc[:, _entry_frame_columns(frame)].copy()


def summarize_entry_state_performance(
    frame: pd.DataFrame,
    group_columns: Sequence[str],
) -> pd.DataFrame:
    """Summarize trade PnL/R by entry-state or state-risk buckets."""

    return _grouped_trade_performance(frame, group_columns)


def build_intrade_state_event_frame(
    trades: pd.DataFrame,
    first_occurrences: pd.DataFrame,
    feasibility: pd.DataFrame,
    entry_frame: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Join first deterioration candidates with next-open feasibility."""

    first = first_occurrences.copy(deep=True)
    feasible = feasibility.copy(deep=True)
    trade_cols = [
        "trade_id",
        "symbol",
        "entry_date",
        "exit_date",
        "exit_reason",
        "net_pnl",
        "r_multiple",
    ]
    trade_lookup = trades.copy(deep=True).loc[:, [c for c in trade_cols if c in trades]]
    event = first.merge(
        feasible,
        on=["trade_id", "candidate_flag_name"],
        how="left",
        suffixes=("_trigger", ""),
    )
    event = event.merge(trade_lookup, on="trade_id", how="left", suffixes=("", "_trade"))
    if "symbol_trade" in event:
        event["symbol"] = event["symbol"].combine_first(event["symbol_trade"])
        event = event.drop(columns=["symbol_trade"])

    rename = {
        "holding_day_index": "trigger_holding_day_index",
        "state_label": "trigger_state_label",
        "return_state": "trigger_return_state",
        "volatility_state": "trigger_volatility_state",
        "drawdown_state_component": "trigger_drawdown_state_component",
        "range_state": "trigger_range_state",
    }
    event = event.rename(columns=rename)
    for column in ("entry_date", "exit_date", "first_occurrence_date", "next_session_date"):
        if column in event:
            event[column] = _date_series(event[column])
    if "entry_date" in event:
        event["year"] = event["entry_date"].dt.year

    if entry_frame is not None and not entry_frame.empty:
        context_cols = [
            "trade_id",
            "liquidity_bucket",
            "liquidity_metric",
            "sector",
            "industry",
            "basic_industry",
            "benchmark_regime",
            "vix_regime",
            "drawdown_state_at_entry",
            "pre_entry_gap_bucket",
        ]
        available = [col for col in context_cols if col in entry_frame]
        event = event.merge(
            entry_frame[available].drop_duplicates("trade_id"),
            on="trade_id",
            how="left",
        )
    _ensure_optional_context_columns(event)
    event["hypothetical_exit_feasible"] = event.get(
        "hypothetical_exit_feasible", pd.Series(False, index=event.index)
    ).fillna(False)
    event["improved_pnl_candidate"] = pd.to_numeric(
        event.get("delta_pnl", pd.Series(pd.NA, index=event.index)),
        errors="coerce",
    ) > 0
    event["worsened_pnl_candidate"] = pd.to_numeric(
        event.get("delta_pnl", pd.Series(pd.NA, index=event.index)),
        errors="coerce",
    ) < 0
    return event.loc[:, _event_frame_columns(event)].copy()


def summarize_deterioration_candidates(
    event_frame: pd.DataFrame,
    group_columns: Sequence[str],
    *,
    total_trades: int | None = None,
) -> pd.DataFrame:
    """Summarize Lane B candidate/timing/next-open diagnostics."""

    if event_frame.empty:
        return pd.DataFrame(columns=[*group_columns, *_deterioration_metric_columns()])
    working = event_frame.copy(deep=True)
    for column in group_columns:
        if column not in working:
            working[column] = "UNKNOWN"
    rows: list[dict[str, object]] = []
    grouped = working.groupby(list(group_columns), dropna=False)
    denominator = total_trades if total_trades is not None else working["trade_id"].nunique()
    for keys, group in grouped:
        key_values = _key_tuple(keys, group_columns)
        actionable = group["first_occurrence_date"].notna() & group.get(
            "actionable", pd.Series(False, index=group.index)
        ).fillna(False)
        feasible = group["hypothetical_exit_feasible"].fillna(False)
        trades_with_candidate = group.loc[actionable, "trade_id"].nunique()
        rows.append(
            {
                **dict(zip(group_columns, key_values)),
                "total_trades": int(denominator),
                "trades_with_candidate": int(trades_with_candidate),
                "trades_without_candidate": int(max(denominator - trades_with_candidate, 0)),
                "feasible_next_open_candidates": int(feasible.sum()),
                "infeasible_candidates": int((~feasible).sum()),
                "avg_trigger_holding_day": _mean(group.loc[actionable, "trigger_holding_day_index"]),
                "median_trigger_holding_day": _median(group.loc[actionable, "trigger_holding_day_index"]),
                "trigger_before_stop_count": _count_trigger_outcome(group, actionable, "stop"),
                "trigger_before_stop_pct": _pct(
                    _count_trigger_outcome(group, actionable, "stop"),
                    trades_with_candidate,
                ),
                "trigger_before_target_count": _count_trigger_outcome(group, actionable, "target"),
                "trigger_before_target_pct": _pct(
                    _count_trigger_outcome(group, actionable, "target"),
                    trades_with_candidate,
                ),
                "winner_through_bad_state_count": _count_r_sign(group, actionable, positive=True),
                "winner_through_bad_state_pct": _pct(
                    _count_r_sign(group, actionable, positive=True),
                    trades_with_candidate,
                ),
                "loser_through_bad_state_count": _count_r_sign(group, actionable, positive=False),
                "loser_through_bad_state_pct": _pct(
                    _count_r_sign(group, actionable, positive=False),
                    trades_with_candidate,
                ),
                "hypothetical_exit_avg_r": _mean(group.loc[feasible, "hypothetical_exit_r"]),
                "actual_avg_r": _mean(group.loc[feasible, "actual_r"]),
                "avg_delta_r": _mean(group.loc[feasible, "delta_r"]),
                "median_delta_r": _median(group.loc[feasible, "delta_r"]),
                "improved_count": int(group["improved_pnl_candidate"].fillna(False).sum()),
                "improved_pct": _pct(
                    int(group["improved_pnl_candidate"].fillna(False).sum()),
                    int(feasible.sum()),
                ),
                "worsened_count": int(group["worsened_pnl_candidate"].fillna(False).sum()),
                "worsened_pct": _pct(
                    int(group["worsened_pnl_candidate"].fillna(False).sum()),
                    int(feasible.sum()),
                ),
                "avoided_stop_candidate_count": int(group.get("avoided_stop_candidate", pd.Series(False, index=group.index)).fillna(False).sum()),
                "missed_target_candidate_count": int(group.get("missed_target_candidate", pd.Series(False, index=group.index)).fillna(False).sum()),
                "sample_size_flag": sample_size_flag(trades_with_candidate),
            }
        )
    return pd.DataFrame(rows)


def summarize_same_day_exit_safety(joined: pd.DataFrame) -> pd.DataFrame:
    """Summarize same-day D-close actionability blocking."""

    if joined.empty:
        same_day = pd.Series(dtype=bool)
        blocked = pd.Series(dtype=bool)
    else:
        same_day = joined.get("actual_exit_on_holding_date", pd.Series(False, index=joined.index)).fillna(False)
        blocked = same_day & ~joined.get("state_actionable_after_close", pd.Series(False, index=joined.index)).fillna(False)
    failures = int((same_day & ~blocked).sum())
    return pd.DataFrame(
        [
            {
                "same_day_exit_rows": int(same_day.sum()),
                "blocked_rows": int(blocked.sum()),
                "actionable_failures": failures,
                "verdict": "PASS" if failures == 0 else "FAIL",
            }
        ]
    )


def summarize_next_open_feasibility(feasibility: pd.DataFrame) -> pd.DataFrame:
    """Summarize next-open feasibility counts and reasons."""

    if feasibility.empty:
        return pd.DataFrame(
            [
                {
                    "total_candidate_rows": 0,
                    "feasible_rows": 0,
                    "infeasible_rows": 0,
                    "infeasible_reasons": "{}",
                    "missing_next_open_count": 0,
                    "candidate_flag_breakdown": "{}",
                }
            ]
        )
    feasible = feasibility["hypothetical_exit_feasible"].fillna(False)
    reasons = (
        feasibility.loc[~feasible, "infeasible_reason"]
        .fillna("UNKNOWN")
        .replace("", "UNKNOWN")
        .value_counts()
        .sort_index()
        .to_dict()
    )
    flag_counts = (
        feasibility.groupby("candidate_flag_name", dropna=False)["hypothetical_exit_feasible"]
        .agg(total="size", feasible=lambda value: int(value.fillna(False).sum()))
        .reset_index()
    )
    breakdown = {
        str(row["candidate_flag_name"]): {
            "total": int(row["total"]),
            "feasible": int(row["feasible"]),
            "infeasible": int(row["total"] - row["feasible"]),
        }
        for _, row in flag_counts.iterrows()
    }
    return pd.DataFrame(
        [
            {
                "total_candidate_rows": len(feasibility),
                "feasible_rows": int(feasible.sum()),
                "infeasible_rows": int((~feasible).sum()),
                "infeasible_reasons": json.dumps({str(k): int(v) for k, v in reasons.items()}, sort_keys=True),
                "missing_next_open_count": int(
                    (feasibility["infeasible_reason"] == "NEXT_OPEN_MISSING").sum()
                ),
                "candidate_flag_breakdown": json.dumps(breakdown, sort_keys=True),
            }
        ]
    )


def build_terminal_edge_case_audit(
    trades: pd.DataFrame,
    lifecycle: pd.DataFrame,
) -> pd.DataFrame:
    """Identify trades whose exit date is beyond reconstructed lifecycle dates."""

    trade_copy = trades.copy(deep=True)
    trade_copy["exit_date"] = _date_series(trade_copy["exit_date"])
    if lifecycle.empty:
        max_dates = pd.DataFrame(columns=["trade_id", "max_lifecycle_date"])
    else:
        life = lifecycle.copy(deep=True)
        life["holding_date"] = _date_series(life["holding_date"])
        max_dates = (
            life.groupby("trade_id", dropna=False)["holding_date"]
            .max()
            .reset_index()
            .rename(columns={"holding_date": "max_lifecycle_date"})
        )
    audit = trade_copy.merge(max_dates, on="trade_id", how="left")
    audit["terminal_edge_case"] = (
        audit["max_lifecycle_date"].notna()
        & audit["exit_date"].notna()
        & (audit["exit_date"] > audit["max_lifecycle_date"])
    )
    audit["edge_case_reason"] = audit["terminal_edge_case"].map(
        {True: "EXIT_AFTER_RECONSTRUCTED_LIFECYCLE_MAX_DATE", False: ""}
    )
    columns = [
        "trade_id",
        "symbol",
        "entry_date",
        "exit_date",
        "max_lifecycle_date",
        "exit_reason",
        "net_pnl",
        "r_multiple",
        "terminal_edge_case",
        "edge_case_reason",
    ]
    return audit.loc[audit["terminal_edge_case"], [c for c in columns if c in audit]].copy()


def summarize_intrade_state_path(joined: pd.DataFrame) -> pd.DataFrame:
    """Summarize reconstructed in-trade state path coverage."""

    if joined.empty:
        return pd.DataFrame(
            [
                {
                    "trades": 0,
                    "lifecycle_rows": 0,
                    "rows_with_state_joined": 0,
                    "rows_missing_state": 0,
                    "state_join_coverage_pct": 0.0,
                    "duplicate_trade_date_rows": 0,
                }
            ]
        )
    rows_joined = int((joined.get("state_join_status") == "STATE_JOINED").sum())
    rows_missing = int((joined.get("state_join_status") == "STATE_MISSING").sum())
    return pd.DataFrame(
        [
            {
                "trades": int(joined["trade_id"].nunique()),
                "lifecycle_rows": len(joined),
                "rows_with_state_joined": rows_joined,
                "rows_missing_state": rows_missing,
                "state_join_coverage_pct": _pct(rows_joined, len(joined)),
                "duplicate_trade_date_rows": int(joined.get("duplicate_trade_date", pd.Series(False, index=joined.index)).fillna(False).sum()),
            }
        ]
    )


def run_full_s2_state_risk_intrade_audit(
    *,
    report_dir: Path | str = DEFAULT_S2_REPORT_DIR,
    ohlc_source: str = "csv",
    ohlc_csv_dir: Path | str | None = None,
    ohlc_loader: object | None = None,
    output_dir: Path | str | None = None,
    lookback_buffer_days: int = DEFAULT_OHLC_LOOKBACK_BUFFER_DAYS,
    universe_csv: Path | str | None = DEFAULT_UNIVERSE_CSV,
    classification_csv: Path | str | None = DEFAULT_CLASSIFICATION_CSV,
) -> S2StateRiskIntradeAuditResult:
    """Run and export the full read-only S2 State x Risk / In-Trade audit."""

    trades = load_s2_retained_trades(report_dir)
    universe = _read_optional_csv(universe_csv)
    classifications = _read_optional_csv(classification_csv)
    ohlcv_by_symbol = load_ohlc_for_reconstruction(
        trades,
        ohlc_source=ohlc_source,
        ohlc_csv_dir=ohlc_csv_dir,
        ohlc_loader=ohlc_loader,
        lookback_buffer_days=lookback_buffer_days,
    )
    states = reconstruct_daily_state_frames(ohlcv_by_symbol)
    lifecycle = expand_trade_lifecycle_dates(trades, ohlcv_by_symbol)
    joined = join_daily_states_to_trades(lifecycle, states)
    candidates = compute_deterioration_candidates(joined)
    first = first_deterioration_occurrences(candidates)
    feasibility = compute_next_open_exit_feasibility(first, trades, ohlcv_by_symbol)
    validation_summary, _ = validate_entry_state_match(trades, states)
    coverage = summarize_reconstruction_coverage(
        trades,
        lifecycle,
        joined,
        validation_summary,
        first,
        feasibility,
    )

    entry_frame = build_entry_state_risk_frame(
        trades,
        universe=universe,
        classifications=classifications,
    )
    event_frame = build_intrade_state_event_frame(
        trades,
        first,
        feasibility,
        entry_frame,
    )
    same_day = summarize_same_day_exit_safety(joined)
    next_open = summarize_next_open_feasibility(feasibility)
    terminal = build_terminal_edge_case_audit(trades, lifecycle)
    path_summary = summarize_intrade_state_path(joined)

    output_path = Path(output_dir) if output_dir is not None else _dated_output_dir()
    output_path.mkdir(parents=True, exist_ok=True)
    outputs = _output_paths(output_path)

    metadata = _metadata(
        report_dir=report_dir,
        output_dir=output_path,
        ohlc_source=ohlc_source,
        trades=trades,
        coverage=coverage,
        validation=validation_summary,
        same_day=same_day,
        terminal=terminal,
        entry_frame=entry_frame,
        universe_csv=universe_csv,
        classification_csv=classification_csv,
    )

    outputs["s2_state_risk_intrade_audit_metadata.json"].write_text(
        json.dumps(metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    outputs["s2_state_risk_intrade_audit_readme.txt"].write_text(
        _readme_text(),
        encoding="utf-8",
    )
    coverage.to_csv(outputs["s2_state_path_coverage_summary.csv"], index=False)
    validation_summary.to_csv(
        outputs["s2_state_reconstruction_validation_summary.csv"],
        index=False,
    )
    same_day.to_csv(outputs["s2_same_day_exit_safety_summary.csv"], index=False)
    next_open.to_csv(outputs["s2_next_open_feasibility_summary.csv"], index=False)
    terminal.to_csv(outputs["s2_terminal_edge_case_audit.csv"], index=False)
    path_summary.to_csv(outputs["s2_intrade_state_path_summary.csv"], index=False)

    for filename, group_columns in LANE_A_OUTPUTS.items():
        summarize_entry_state_performance(entry_frame, group_columns).to_csv(
            outputs[filename],
            index=False,
        )
    _sample_size_flags(entry_frame).to_csv(
        outputs["s2_state_risk_sample_size_flags.csv"],
        index=False,
    )

    for filename, group_columns in LANE_B_OUTPUTS.items():
        summarize_deterioration_candidates(
            event_frame,
            group_columns,
            total_trades=len(trades),
        ).to_csv(outputs[filename], index=False)
    summarize_deterioration_candidates(
        event_frame,
        ["candidate_flag_name"],
        total_trades=len(trades),
    ).to_csv(outputs["s2_deterioration_timing_summary.csv"], index=False)
    summarize_next_open_hypothetical_exits(event_frame).to_csv(
        outputs["s2_next_open_hypothetical_exit_summary.csv"],
        index=False,
    )
    summarize_next_open_hypothetical_exits(event_frame, ["candidate_flag_name", "year"]).to_csv(
        outputs["s2_next_open_hypothetical_by_flag_year.csv"],
        index=False,
    )
    summarize_winner_through_bad_state(event_frame).to_csv(
        outputs["s2_winner_through_bad_state_audit.csv"],
        index=False,
    )
    summarize_missed_target_vs_avoided_stop(event_frame).to_csv(
        outputs["s2_missed_target_vs_avoided_stop_audit.csv"],
        index=False,
    )

    return S2StateRiskIntradeAuditResult(output_path, outputs, metadata)


def summarize_next_open_hypothetical_exits(
    event_frame: pd.DataFrame,
    group_columns: Sequence[str] = ("candidate_flag_name",),
) -> pd.DataFrame:
    """Summarize audit-only next-open hypothetical outcome deltas."""

    if event_frame.empty:
        return pd.DataFrame(columns=[*group_columns, "feasible_rows"])
    rows = []
    for keys, group in event_frame.groupby(list(group_columns), dropna=False):
        key_values = _key_tuple(keys, group_columns)
        feasible = group["hypothetical_exit_feasible"].fillna(False)
        rows.append(
            {
                **dict(zip(group_columns, key_values)),
                "feasible_rows": int(feasible.sum()),
                "hypothetical_exit_avg_r": _mean(group.loc[feasible, "hypothetical_exit_r"]),
                "actual_avg_r": _mean(group.loc[feasible, "actual_r"]),
                "avg_delta_r": _mean(group.loc[feasible, "delta_r"]),
                "median_delta_r": _median(group.loc[feasible, "delta_r"]),
                "improved_count": int(group["improved_pnl_candidate"].fillna(False).sum()),
                "worsened_count": int(group["worsened_pnl_candidate"].fillna(False).sum()),
                "avoided_stop_candidate_count": int(group.get("avoided_stop_candidate", pd.Series(False, index=group.index)).fillna(False).sum()),
                "missed_target_candidate_count": int(group.get("missed_target_candidate", pd.Series(False, index=group.index)).fillna(False).sum()),
                "sample_size_flag": sample_size_flag(int(feasible.sum())),
            }
        )
    return pd.DataFrame(rows)


def summarize_winner_through_bad_state(event_frame: pd.DataFrame) -> pd.DataFrame:
    """Summarize winners/losers that pass through candidate bad states."""

    return summarize_deterioration_candidates(
        event_frame,
        ["candidate_flag_name"],
        total_trades=event_frame["trade_id"].nunique() if "trade_id" in event_frame else 0,
    ).loc[
        :,
        [
            "candidate_flag_name",
            "trades_with_candidate",
            "winner_through_bad_state_count",
            "winner_through_bad_state_pct",
            "loser_through_bad_state_count",
            "loser_through_bad_state_pct",
            "sample_size_flag",
        ],
    ]


def summarize_missed_target_vs_avoided_stop(event_frame: pd.DataFrame) -> pd.DataFrame:
    """Summarize audit-only missed-target and avoided-stop candidates."""

    if event_frame.empty:
        return pd.DataFrame(
            columns=[
                "candidate_flag_name",
                "avoided_stop_candidate_count",
                "missed_target_candidate_count",
            ]
        )
    rows = []
    for flag, group in event_frame.groupby("candidate_flag_name", dropna=False):
        rows.append(
            {
                "candidate_flag_name": flag,
                "avoided_stop_candidate_count": int(group.get("avoided_stop_candidate", pd.Series(False, index=group.index)).fillna(False).sum()),
                "missed_target_candidate_count": int(group.get("missed_target_candidate", pd.Series(False, index=group.index)).fillna(False).sum()),
            }
        )
    return pd.DataFrame(rows)


def _grouped_trade_performance(
    frame: pd.DataFrame,
    group_columns: Sequence[str],
) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=[*group_columns, *_performance_metric_columns()])
    working = frame.copy(deep=True)
    for column in group_columns:
        if column not in working:
            working[column] = "UNKNOWN"
        working[column] = working[column].fillna("UNKNOWN")
    rows = []
    for keys, group in working.groupby(list(group_columns), dropna=False):
        key_values = _key_tuple(keys, group_columns)
        pnl = pd.to_numeric(group["net_pnl"], errors="coerce").fillna(0.0)
        r_values = pd.to_numeric(group["r_multiple"], errors="coerce")
        gross_profit = float(pnl[pnl > 0].sum())
        gross_loss = float(pnl[pnl < 0].sum())
        trades = len(group)
        stop_count = _exit_contains(group, "stop")
        target_count = _exit_contains(group, "target")
        time_count = _exit_contains(group, "time")
        gap_stop_count = int(
            (
                group["exit_reason"].astype(str).str.lower().str.contains("gap", na=False)
                & group["exit_reason"].astype(str).str.lower().str.contains("stop", na=False)
            ).sum()
        )
        rows.append(
            {
                **dict(zip(group_columns, key_values)),
                "trades": trades,
                "net_pnl": float(pnl.sum()),
                "gross_profit": gross_profit,
                "gross_loss": gross_loss,
                "profit_factor": _profit_factor(gross_profit, gross_loss),
                "win_rate_pct": _pct(int((pnl > 0).sum()), trades),
                "avg_pnl": _mean(pnl),
                "median_pnl": _median(pnl),
                "avg_r": _mean(r_values),
                "median_r": _median(r_values),
                "max_loss": float(pnl.min()) if trades else 0.0,
                "stop_loss_count": stop_count,
                "stop_loss_pct": _pct(stop_count, trades),
                "target_count": target_count,
                "target_pct": _pct(target_count, trades),
                "time_stop_count": time_count,
                "time_stop_pct": _pct(time_count, trades),
                "gap_stop_count": gap_stop_count,
                "gap_stop_pct": _pct(gap_stop_count, trades),
                "sample_size_flag": sample_size_flag(trades),
            }
        )
    return pd.DataFrame(rows)


def _sample_size_flags(entry_frame: pd.DataFrame) -> pd.DataFrame:
    summaries = []
    for name, columns in LANE_A_OUTPUTS.items():
        summary = summarize_entry_state_performance(entry_frame, columns)
        if not summary.empty:
            summary = summary.loc[:, [*columns, "trades", "sample_size_flag"]].copy()
            summary.insert(0, "source_output", name)
            summaries.append(summary)
    if not summaries:
        return pd.DataFrame(
            columns=["source_output", "trades", "sample_size_flag"]
        )
    return pd.concat(summaries, ignore_index=True)


def _join_optional_universe(frame: pd.DataFrame, universe: pd.DataFrame | None) -> pd.DataFrame:
    if universe is None or universe.empty or "symbol" not in universe:
        frame["liquidity_bucket"] = "UNKNOWN"
        frame["liquidity_metric"] = pd.NA
        return frame
    columns = [
        col for col in ("symbol", "liquidity_bucket", "liquidity_metric") if col in universe
    ]
    result = frame.merge(universe[columns].drop_duplicates("symbol"), on="symbol", how="left")
    if "liquidity_bucket" not in result:
        result["liquidity_bucket"] = "UNKNOWN"
    if "liquidity_metric" not in result:
        result["liquidity_metric"] = pd.NA
    result["liquidity_bucket"] = result["liquidity_bucket"].fillna("UNKNOWN")
    return result


def _join_optional_classification(
    frame: pd.DataFrame,
    classifications: pd.DataFrame | None,
) -> pd.DataFrame:
    if classifications is None or classifications.empty or "symbol" not in classifications:
        for column in ("sector", "industry", "basic_industry"):
            frame[column] = "UNKNOWN"
        return frame
    wanted = [
        "symbol",
        "sector",
        "industry",
        "basic_industry",
        "market_cap_bucket",
        "classification_mode",
    ]
    columns = [col for col in wanted if col in classifications]
    result = frame.merge(
        classifications[columns].drop_duplicates("symbol"),
        on="symbol",
        how="left",
    )
    for column in ("sector", "industry", "basic_industry"):
        if column not in result:
            result[column] = "UNKNOWN"
        result[column] = result[column].fillna("UNKNOWN")
    return result


def _ensure_optional_context_columns(frame: pd.DataFrame) -> None:
    defaults = {
        "liquidity_bucket": "UNKNOWN",
        "liquidity_metric": pd.NA,
        "sector": "UNKNOWN",
        "industry": "UNKNOWN",
        "basic_industry": "UNKNOWN",
        "benchmark_regime": "UNKNOWN",
        "vix_regime": "UNKNOWN",
        "drawdown_state_at_entry": "UNKNOWN",
        "pre_entry_gap_bucket": "UNKNOWN",
    }
    aliases = {
        "benchmark_regime": (
            "benchmark_regime_bucket",
            "nifty_regime",
            "nifty_20d_regime",
        ),
        "vix_regime": ("vix_percentile_bucket", "vix_regime_bucket"),
        "pre_entry_gap_bucket": ("stock_gap_bucket", "pre_signal_gap_bucket"),
    }
    for target, sources in aliases.items():
        if target not in frame:
            for source in sources:
                if source in frame:
                    frame[target] = frame[source]
                    break
    if "drawdown_state_at_entry" not in frame and "drawdown_state_component" in frame:
        frame["drawdown_state_at_entry"] = frame["drawdown_state_component"]
    for column, default in defaults.items():
        if column not in frame:
            frame[column] = default
        if column != "liquidity_metric":
            frame[column] = frame[column].fillna("UNKNOWN")


def _entry_frame_columns(frame: pd.DataFrame) -> list[str]:
    preferred = [
        "trade_id",
        "symbol",
        "signal_date",
        "entry_date",
        "exit_date",
        "exit_reason",
        "net_pnl",
        "r_multiple",
        "state_label",
        "return_state",
        "volatility_state",
        "drawdown_state_component",
        "range_state",
        "year",
        "liquidity_bucket",
        "liquidity_metric",
        "sector",
        "industry",
        "basic_industry",
        "benchmark_regime",
        "vix_regime",
        "drawdown_state_at_entry",
        "pre_entry_gap_bucket",
        "stop_exit",
        "target_exit",
        "time_stop_exit",
        "gap_stop_exit",
    ]
    return [col for col in preferred if col in frame]


def _event_frame_columns(frame: pd.DataFrame) -> list[str]:
    preferred = [
        "trade_id",
        "symbol",
        "entry_date",
        "exit_date",
        "exit_reason",
        "net_pnl",
        "r_multiple",
        "candidate_flag_name",
        "first_occurrence_date",
        "trigger_holding_day_index",
        "trigger_state_label",
        "trigger_return_state",
        "trigger_volatility_state",
        "trigger_drawdown_state_component",
        "trigger_range_state",
        "actionable",
        "next_session_date",
        "hypothetical_exit_feasible",
        "infeasible_reason",
        "hypothetical_exit_price",
        "hypothetical_exit_pnl",
        "hypothetical_exit_r",
        "actual_pnl",
        "actual_r",
        "delta_pnl",
        "delta_r",
        "avoided_stop_candidate",
        "missed_target_candidate",
        "improved_pnl_candidate",
        "worsened_pnl_candidate",
        "year",
        "liquidity_bucket",
        "sector",
        "benchmark_regime",
        "vix_regime",
        "drawdown_state_at_entry",
        "pre_entry_gap_bucket",
    ]
    return [col for col in preferred if col in frame]


def _output_paths(output_dir: Path) -> dict[str, Path]:
    names = [
        "s2_state_risk_intrade_audit_metadata.json",
        "s2_state_risk_intrade_audit_readme.txt",
        "s2_state_reconstruction_validation_summary.csv",
        "s2_state_path_coverage_summary.csv",
        "s2_same_day_exit_safety_summary.csv",
        "s2_next_open_feasibility_summary.csv",
        "s2_terminal_edge_case_audit.csv",
        "s2_intrade_state_path_summary.csv",
        "s2_state_risk_sample_size_flags.csv",
        "s2_deterioration_timing_summary.csv",
        "s2_next_open_hypothetical_exit_summary.csv",
        "s2_next_open_hypothetical_by_flag_year.csv",
        "s2_winner_through_bad_state_audit.csv",
        "s2_missed_target_vs_avoided_stop_audit.csv",
        *LANE_A_OUTPUTS.keys(),
        *LANE_B_OUTPUTS.keys(),
    ]
    return {name: output_dir / name for name in sorted(set(names))}


def _metadata(
    *,
    report_dir: Path | str,
    output_dir: Path,
    ohlc_source: str,
    trades: pd.DataFrame,
    coverage: pd.DataFrame,
    validation: pd.DataFrame,
    same_day: pd.DataFrame,
    terminal: pd.DataFrame,
    entry_frame: pd.DataFrame,
    universe_csv: Path | str | None,
    classification_csv: Path | str | None,
) -> dict[str, object]:
    coverage_row = coverage.iloc[0].to_dict() if not coverage.empty else {}
    validation_row = validation.iloc[0].to_dict() if not validation.empty else {}
    same_day_row = same_day.iloc[0].to_dict() if not same_day.empty else {}
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "report_dir": str(report_dir),
        "output_dir": str(output_dir),
        "ohlc_source": ohlc_source,
        "universe_csv": str(universe_csv) if universe_csv is not None else None,
        "classification_csv": str(classification_csv) if classification_csv is not None else None,
        "retained_strategy": "S2_MARKOV_STATE_TRANSITION",
        "retained_variant": "exclude_ret_down",
        "total_trades": int(len(trades)),
        "lifecycle_rows": int(coverage_row.get("lifecycle_rows", 0)),
        "state_join_coverage_pct": coverage_row.get("state_join_coverage_pct"),
        "entry_state_match_rate_pct": validation_row.get("match_rate_pct"),
        "same_day_safety_verdict": same_day_row.get("verdict"),
        "same_day_actionable_failures": same_day_row.get("actionable_failures"),
        "terminal_edge_case_count": int(len(terminal)),
        "optional_context_coverage": _optional_context_coverage(entry_frame),
        "caveat": READ_ONLY_NON_APPROVAL,
        "reconstruction_caveat": DIAGNOSTIC_ONLY_CAVEAT,
    }


def _optional_context_coverage(entry_frame: pd.DataFrame) -> dict[str, object]:
    result = {}
    for column in (
        "liquidity_bucket",
        "sector",
        "industry",
        "basic_industry",
        "benchmark_regime",
        "vix_regime",
        "pre_entry_gap_bucket",
    ):
        if column in entry_frame:
            known = int((~entry_frame[column].fillna("UNKNOWN").eq("UNKNOWN")).sum())
            result[column] = {
                "known_rows": known,
                "total_rows": int(len(entry_frame)),
                "known_pct": _pct(known, len(entry_frame)),
            }
    return result


def _readme_text() -> str:
    return (
        "Phase 36K Full Read-Only S2 State x Risk / In-Trade Audit\n\n"
        + READ_ONLY_NON_APPROVAL
        + "\n\nOutputs are for scrutiny only. They do not approve a dynamic exit, "
        + "exit if RET_DOWN, entry filter, state exclusion, risk filter, sizing "
        + "change, backtest optimization, production use, or strategy promotion.\n"
    )


def _read_optional_csv(path: Path | str | None) -> pd.DataFrame | None:
    if path is None:
        return None
    csv_path = Path(path)
    if not csv_path.exists():
        return None
    return pd.read_csv(csv_path)


def _date_series(values: object) -> pd.Series:
    if isinstance(values, pd.Series):
        raw = values.copy(deep=True)
    elif isinstance(values, pd.Index):
        raw = pd.Series(values.to_list())
    elif isinstance(values, (list, tuple)):
        raw = pd.Series(list(values))
    else:
        raw = pd.Series([values])
    normalized = raw.apply(_normalize_date_value)
    return pd.to_datetime(normalized, errors="coerce")


def _normalize_date_value(value: object) -> pd.Timestamp:
    if value is None:
        return pd.NaT
    try:
        if pd.isna(value):
            return pd.NaT
    except (TypeError, ValueError):
        pass
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return pd.NaT
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_localize(None)
    return timestamp.normalize()


def _key_tuple(keys: object, group_columns: Sequence[str]) -> tuple[object, ...]:
    if len(group_columns) == 1:
        if isinstance(keys, tuple) and len(keys) == 1:
            return keys
        return (keys,)
    return tuple(keys)


def _performance_metric_columns() -> list[str]:
    return [
        "trades",
        "net_pnl",
        "gross_profit",
        "gross_loss",
        "profit_factor",
        "win_rate_pct",
        "avg_pnl",
        "median_pnl",
        "avg_r",
        "median_r",
        "max_loss",
        "stop_loss_count",
        "stop_loss_pct",
        "target_count",
        "target_pct",
        "time_stop_count",
        "time_stop_pct",
        "gap_stop_count",
        "gap_stop_pct",
        "sample_size_flag",
    ]


def _deterioration_metric_columns() -> list[str]:
    return [
        "total_trades",
        "trades_with_candidate",
        "trades_without_candidate",
        "feasible_next_open_candidates",
        "infeasible_candidates",
        "avg_trigger_holding_day",
        "median_trigger_holding_day",
        "trigger_before_stop_count",
        "trigger_before_stop_pct",
        "trigger_before_target_count",
        "trigger_before_target_pct",
        "winner_through_bad_state_count",
        "winner_through_bad_state_pct",
        "loser_through_bad_state_count",
        "loser_through_bad_state_pct",
        "hypothetical_exit_avg_r",
        "actual_avg_r",
        "avg_delta_r",
        "median_delta_r",
        "improved_count",
        "improved_pct",
        "worsened_count",
        "worsened_pct",
        "avoided_stop_candidate_count",
        "missed_target_candidate_count",
        "sample_size_flag",
    ]


def _exit_contains(group: pd.DataFrame, pattern: str) -> int:
    return int(group["exit_reason"].astype(str).str.lower().str.contains(pattern, na=False).sum())


def _count_trigger_outcome(group: pd.DataFrame, actionable: pd.Series, pattern: str) -> int:
    return int(
        (
            actionable
            & group["exit_reason"].astype(str).str.lower().str.contains(pattern, na=False)
        ).sum()
    )


def _count_r_sign(group: pd.DataFrame, actionable: pd.Series, *, positive: bool) -> int:
    r_values = pd.to_numeric(group["r_multiple"], errors="coerce")
    return int((actionable & (r_values > 0 if positive else r_values <= 0)).sum())


def _profit_factor(gross_profit: float, gross_loss: float) -> float | None:
    if gross_loss == 0:
        return None
    return round(gross_profit / abs(gross_loss), 6)


def _mean(values: Iterable[object]) -> float | None:
    numeric = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    if numeric.empty:
        return None
    return round(float(numeric.mean()), 6)


def _median(values: Iterable[object]) -> float | None:
    numeric = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    if numeric.empty:
        return None
    return round(float(numeric.median()), 6)


def _pct(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0:
        return 0.0
    return round((float(numerator) / float(denominator)) * 100, 6)


def _dated_output_dir() -> Path:
    return DEFAULT_OUTPUT_ROOT / (
        "s2_state_risk_intrade_full_audit_" + datetime.now().strftime("%Y%m%d")
    )
