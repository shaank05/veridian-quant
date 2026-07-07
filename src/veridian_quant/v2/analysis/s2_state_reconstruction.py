"""Read-only S2 daily state reconstruction prototype utilities.

This module reconstructs daily in-trade S2 state paths from existing trade
reports and OHLCV data. It does not run strategies, change S2 behavior,
implement exits, optimize thresholds, or write production trading rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

from veridian_quant.v2.data.loaders import normalize_ohlcv_dataframe
from veridian_quant.v2.strategies.s2_markov_state_transition import build_state_frame


DEFAULT_S2_REPORT_DIR = Path(
    "reports/v2/s2_markov_2020_2026_research200_exclude_ret_down_full_diagnostics"
)
DEFAULT_OUTPUT_ROOT = Path("reports/v2")
DEFAULT_OHLC_LOOKBACK_BUFFER_DAYS = 365

REQUIRED_RETAINED_TRADE_FILES = (
    "trade_log.csv",
    "trade_pnl_log.csv",
    "trade_signal_context.csv",
)

DIAGNOSTIC_ONLY_CAVEAT = (
    "Read-only S2 state reconstruction prototype. Not a strategy rule, "
    "not a backtest, and not approved for production behavior."
)

RETURN_STATE_ORDER = {
    "RET_STRONG_UP": 0,
    "RET_UP": 1,
    "RET_FLAT": 2,
    "RET_DOWN": 3,
    "RET_STRONG_DOWN": 4,
}


@dataclass(frozen=True, slots=True)
class ReconstructionRunResult:
    """Paths and metadata produced by the optional prototype exporter."""

    output_dir: Path
    outputs: dict[str, Path]
    metadata: dict[str, object]


def load_s2_retained_trades(report_dir: Path | str) -> pd.DataFrame:
    """Load retained S2 executed trades and preserve optional report metadata."""

    report_path = Path(report_dir)
    missing = [
        name for name in REQUIRED_RETAINED_TRADE_FILES if not (report_path / name).exists()
    ]
    if missing:
        raise FileNotFoundError(
            "missing required retained S2 report files in "
            f"{report_path}: {', '.join(missing)}"
        )

    trade_log = pd.read_csv(report_path / "trade_log.csv")
    pnl_log = pd.read_csv(report_path / "trade_pnl_log.csv")
    context = pd.read_csv(report_path / "trade_signal_context.csv")
    for name, frame in (
        ("trade_log.csv", trade_log),
        ("trade_pnl_log.csv", pnl_log),
        ("trade_signal_context.csv", context),
    ):
        if "trade_id" not in frame.columns:
            raise ValueError(f"{name} missing required column: trade_id")

    merged = trade_log.merge(
        pnl_log,
        on="trade_id",
        how="left",
        suffixes=("", "_pnl"),
        validate="one_to_one",
    ).merge(
        context,
        on="trade_id",
        how="left",
        suffixes=("", "_context"),
        validate="one_to_one",
    )

    loaded = pd.DataFrame(index=merged.index)
    column_specs = {
        "trade_id": ("trade_id",),
        "symbol": ("symbol", "symbol_pnl", "symbol_context"),
        "entry_date": ("entry_date", "entry_date_pnl", "entry_date_context"),
        "exit_date": ("exit_date", "exit_date_pnl", "exit_date_context"),
        "signal_date": ("signal_date",),
        "exit_reason": ("exit_reason", "exit_reason_pnl", "exit_reason_context"),
        "entry_price": ("entry_price", "entry_price_context"),
        "exit_price": ("exit_price", "exit_price_context"),
        "stop_price": ("stop_loss", "stop_loss_pnl", "stop_loss_context"),
        "target_price": ("target_price", "target_price_pnl", "target_price_context"),
        "quantity": ("quantity", "quantity_pnl"),
        "initial_risk_amount": (
            "initial_risk_amount",
            "initial_risk_amount_pnl",
            "initial_risk_amount_context",
        ),
        "net_pnl": ("net_pnl", "net_pnl_context"),
        "r_multiple": ("r_multiple",),
        "stored_entry_state_label": ("state_label", "state_label_context"),
        "strategy_name": ("strategy_name", "strategy_name_context"),
    }
    for output_column, source_columns in column_specs.items():
        loaded[output_column] = _coalesce_columns(merged, source_columns)

    loaded["stored_state_alignment"] = loaded["signal_date"].apply(
        lambda value: "SIGNAL_DATE" if _present(value) else "ENTRY_DATE_AMBIGUOUS"
    )
    loaded["source_report_dir"] = str(report_path)
    loaded["source_trade_log_rows"] = len(trade_log)
    loaded["source_trade_pnl_log_rows"] = len(pnl_log)
    loaded["source_trade_signal_context_rows"] = len(context)
    return _normalize_trade_dates_and_numbers(loaded)


def parse_s2_state_label(state_label: object) -> dict[str, object]:
    """Parse a composite S2 state label into deterministic components."""

    if not _present(state_label):
        return {
            "raw_state_label": None,
            "return_state": None,
            "volatility_state": None,
            "drawdown_state_component": None,
            "range_state": None,
            "unknown_components": [],
            "parse_status": "MISSING",
        }

    raw = str(state_label).strip()
    components = [part.strip() for part in raw.split("|") if part.strip()]
    parsed: dict[str, object] = {
        "raw_state_label": raw,
        "return_state": None,
        "volatility_state": None,
        "drawdown_state_component": None,
        "range_state": None,
        "unknown_components": [],
        "parse_status": "PARSED",
    }
    unknown: list[str] = []
    for component in components:
        if component.startswith("RET_") and parsed["return_state"] is None:
            parsed["return_state"] = component
        elif component.startswith("VOL_") and parsed["volatility_state"] is None:
            parsed["volatility_state"] = component
        elif component.startswith("DD_") and parsed["drawdown_state_component"] is None:
            parsed["drawdown_state_component"] = component
        elif component.startswith("LOW_") and parsed["range_state"] is None:
            parsed["range_state"] = component
        else:
            unknown.append(component)

    parsed["unknown_components"] = unknown
    if unknown:
        parsed["parse_status"] = "PARSED_WITH_UNKNOWN_COMPONENTS"
    if any(
        parsed[key] is None
        for key in (
            "return_state",
            "volatility_state",
            "drawdown_state_component",
            "range_state",
        )
    ):
        parsed["parse_status"] = (
            "PARTIAL" if not unknown else "PARTIAL_WITH_UNKNOWN_COMPONENTS"
        )
    return parsed


def reconstruct_symbol_state_frame(symbol: str, ohlcv: pd.DataFrame) -> pd.DataFrame:
    """Reconstruct one symbol's daily S2 state frame using existing S2 logic."""

    normalized = normalize_ohlcv_dataframe(ohlcv)
    state_frame = build_state_frame(normalized)
    reconstructed = pd.concat(
        [
            normalized.loc[:, ["date"]].reset_index(drop=True),
            state_frame.reset_index(drop=True),
        ],
        axis=1,
    )
    reconstructed.insert(0, "symbol", symbol)
    parsed = _parsed_state_frame(reconstructed["state_label"])
    reconstructed = pd.concat([reconstructed, parsed], axis=1)
    reconstructed["state_available"] = reconstructed["state_label"].notna()
    reconstructed["state_unavailable_reason"] = reconstructed["state_available"].map(
        {True: "", False: "STATE_LABEL_MISSING"}
    )
    reconstructed["source_state_builder"] = "build_state_frame"
    reconstructed["source_state_parameters"] = "S2 default benchmark parameters"
    reconstructed["date"] = _date_series(reconstructed["date"])
    return reconstructed


def reconstruct_daily_state_frames(
    ohlcv_by_symbol: Mapping[str, pd.DataFrame],
) -> pd.DataFrame:
    """Reconstruct daily S2 states for all provided symbols."""

    frames = [
        reconstruct_symbol_state_frame(symbol, frame)
        for symbol, frame in sorted(ohlcv_by_symbol.items())
        if not frame.empty
    ]
    if not frames:
        return _empty_reconstructed_state_frame()
    return pd.concat(frames, ignore_index=True)


def expand_trade_lifecycle_dates(
    trades: pd.DataFrame,
    ohlcv_by_symbol: Mapping[str, pd.DataFrame],
) -> pd.DataFrame:
    """Expand each trade to symbol trading dates from entry through exit.

    ``holding_day_index`` is zero-based: entry date is index 0.
    """

    rows: list[dict[str, object]] = []
    for _, trade in trades.copy(deep=True).iterrows():
        symbol = trade.get("symbol")
        dates = _symbol_dates(ohlcv_by_symbol.get(str(symbol)))
        entry_date = _as_timestamp(trade.get("entry_date"))
        exit_date = _as_timestamp(trade.get("exit_date"))
        if entry_date is None or exit_date is None or not dates:
            continue
        holding_dates = [d for d in dates if entry_date <= d <= exit_date]
        for index, holding_date in enumerate(holding_dates):
            row = trade.to_dict()
            row["holding_date"] = holding_date
            row["holding_day_index"] = index
            row["actual_exit_on_holding_date"] = holding_date == exit_date
            row["state_actionable_after_close"] = holding_date < exit_date
            rows.append(row)

    if not rows:
        return pd.DataFrame(
            columns=list(trades.columns)
            + [
                "holding_date",
                "holding_day_index",
                "actual_exit_on_holding_date",
                "state_actionable_after_close",
                "duplicate_trade_date",
            ]
        )
    lifecycle = pd.DataFrame(rows)
    lifecycle["duplicate_trade_date"] = lifecycle.duplicated(
        subset=["trade_id", "holding_date"],
        keep=False,
    )
    return lifecycle


def join_daily_states_to_trades(
    lifecycle: pd.DataFrame,
    reconstructed_states: pd.DataFrame,
) -> pd.DataFrame:
    """Join reconstructed symbol/date states to expanded lifecycle rows."""

    lifecycle_copy = lifecycle.copy(deep=True)
    states_copy = reconstructed_states.copy(deep=True)
    if lifecycle_copy.empty:
        return lifecycle_copy
    lifecycle_copy["holding_date"] = _date_series(lifecycle_copy["holding_date"])
    states_copy["date"] = _date_series(states_copy["date"])
    state_columns = [
        column
        for column in states_copy.columns
        if column not in {"symbol"}
    ]
    joined = lifecycle_copy.merge(
        states_copy[["symbol", *state_columns]],
        left_on=["symbol", "holding_date"],
        right_on=["symbol", "date"],
        how="left",
    )
    if "state_available" not in joined.columns:
        joined["state_available"] = False
    joined["state_join_status"] = "STATE_JOINED"
    missing_state_row = joined["date"].isna()
    state_available = joined["state_available"].fillna(False).eq(True)
    unavailable_state = ~missing_state_row & ~state_available
    joined.loc[missing_state_row, "state_join_status"] = "STATE_MISSING"
    joined.loc[unavailable_state, "state_join_status"] = "STATE_UNAVAILABLE"
    return joined


def validate_entry_state_match(
    trades: pd.DataFrame,
    reconstructed_states: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare stored entry-state metadata to reconstructed signal/entry state."""

    details: list[dict[str, object]] = []
    states = reconstructed_states.copy(deep=True)
    if not states.empty:
        states["date"] = _date_series(states["date"])
    for _, trade in trades.copy(deep=True).iterrows():
        stored = trade.get("stored_entry_state_label")
        if not _present(stored):
            details.append(_entry_match_detail(trade, None, "MISSING_STORED_STATE"))
            continue
        alignment_date, alignment_used = _entry_alignment(trade)
        if alignment_date is None:
            details.append(_entry_match_detail(trade, None, "MISSING_ALIGNMENT_DATE"))
            continue
        match = states[
            (states["symbol"] == trade.get("symbol"))
            & (states["date"] == alignment_date)
        ]
        if match.empty or not _present(match.iloc[0].get("state_label")):
            details.append(
                _entry_match_detail(
                    trade,
                    alignment_date,
                    "MISSING_RECONSTRUCTED_STATE",
                    alignment_used=alignment_used,
                    reconstructed_state_label=None,
                )
            )
            continue
        reconstructed = match.iloc[0].get("state_label")
        status = "MATCH" if str(stored) == str(reconstructed) else "MISMATCH"
        details.append(
            _entry_match_detail(
                trade,
                alignment_date,
                status,
                alignment_used=alignment_used,
                reconstructed_state_label=reconstructed,
            )
        )

    detail_frame = pd.DataFrame(details)
    checked = detail_frame["match_status"].isin(["MATCH", "MISMATCH"]).sum()
    matches = (detail_frame["match_status"] == "MATCH").sum()
    summary = pd.DataFrame(
        [
            {
                "trades_checked": int(checked),
                "matches": int(matches),
                "mismatches": int((detail_frame["match_status"] == "MISMATCH").sum()),
                "missing_stored_state": int(
                    (detail_frame["match_status"] == "MISSING_STORED_STATE").sum()
                ),
                "missing_reconstructed_state": int(
                    (
                        detail_frame["match_status"]
                        == "MISSING_RECONSTRUCTED_STATE"
                    ).sum()
                ),
                "match_rate_pct": _pct(matches, checked),
                "alignment_used": _summarize_values(detail_frame, "alignment_used"),
            }
        ]
    )
    return summary, detail_frame


def compute_deterioration_candidates(joined: pd.DataFrame) -> pd.DataFrame:
    """Add diagnostic-only state deterioration candidate flags."""

    result = joined.copy(deep=True)
    if result.empty:
        return result
    entry_by_trade = (
        result.sort_values(["trade_id", "holding_day_index"])
        .groupby("trade_id", dropna=False)
        .first()
    )
    result["entry_state_label"] = result["trade_id"].map(entry_by_trade["state_label"])
    result["entry_return_state"] = result["trade_id"].map(
        entry_by_trade["return_state"]
    )
    result["contains_ret_down"] = result["return_state"].isin(
        ["RET_DOWN", "RET_STRONG_DOWN"]
    )
    result["entered_ret_down_after_entry"] = (
        (result["holding_day_index"] > 0) & result["contains_ret_down"]
    )
    result["entered_vol_high_after_entry"] = (
        (result["holding_day_index"] > 0)
        & (result["volatility_state"] == "VOL_HIGH")
    )
    result["state_changed_from_entry"] = (
        (result["holding_day_index"] > 0)
        & result["state_label"].notna()
        & result["entry_state_label"].notna()
        & (result["state_label"] != result["entry_state_label"])
    )
    result["return_state_worse_than_entry"] = result.apply(
        lambda row: _return_state_worse(
            row.get("return_state"), row.get("entry_return_state")
        ),
        axis=1,
    )
    result["diagnostic_only"] = True
    return result


def first_deterioration_occurrences(
    candidates: pd.DataFrame,
    candidate_flags: Iterable[str] = (
        "contains_ret_down",
        "entered_ret_down_after_entry",
        "entered_vol_high_after_entry",
        "state_changed_from_entry",
        "return_state_worse_than_entry",
    ),
) -> pd.DataFrame:
    """Find each trade's first actionable occurrence for each candidate flag."""

    rows: list[dict[str, object]] = []
    for trade_id, group in candidates.copy(deep=True).groupby("trade_id", dropna=False):
        ordered = group.sort_values("holding_day_index")
        first_row = ordered.iloc[0]
        for flag in candidate_flags:
            flag_values = (
                ordered[flag].fillna(False)
                if flag in ordered
                else pd.Series(False, index=ordered.index)
            )
            actionable = ordered[
                flag_values & ordered["state_actionable_after_close"].fillna(False)
            ]
            if actionable.empty:
                rows.append(
                    {
                        "trade_id": trade_id,
                        "symbol": first_row.get("symbol"),
                        "candidate_flag_name": flag,
                        "first_occurrence_date": pd.NaT,
                        "holding_day_index": pd.NA,
                        "state_label": pd.NA,
                        "return_state": pd.NA,
                        "volatility_state": pd.NA,
                        "drawdown_state_component": pd.NA,
                        "range_state": pd.NA,
                        "actionable": False,
                        "no_occurrence_reason": "NO_ACTIONABLE_OCCURRENCE",
                    }
                )
                continue
            occurrence = actionable.iloc[0]
            rows.append(
                {
                    "trade_id": trade_id,
                    "symbol": occurrence.get("symbol"),
                    "candidate_flag_name": flag,
                    "first_occurrence_date": occurrence.get("holding_date"),
                    "holding_day_index": occurrence.get("holding_day_index"),
                    "state_label": occurrence.get("state_label"),
                    "return_state": occurrence.get("return_state"),
                    "volatility_state": occurrence.get("volatility_state"),
                    "drawdown_state_component": occurrence.get(
                        "drawdown_state_component"
                    ),
                    "range_state": occurrence.get("range_state"),
                    "actionable": True,
                    "no_occurrence_reason": "",
                }
            )
    return pd.DataFrame(rows)


def compute_next_open_exit_feasibility(
    first_occurrences: pd.DataFrame,
    trades: pd.DataFrame,
    ohlcv_by_symbol: Mapping[str, pd.DataFrame],
) -> pd.DataFrame:
    """Assess next-open hypothetical exit feasibility without executing a rule."""

    trade_lookup = trades.copy(deep=True).set_index("trade_id", drop=False)
    rows: list[dict[str, object]] = []
    for _, occurrence in first_occurrences.copy(deep=True).iterrows():
        trade_id = occurrence.get("trade_id")
        trade = trade_lookup.loc[trade_id] if trade_id in trade_lookup.index else None
        symbol = occurrence.get("symbol")
        trigger_date = _as_timestamp(occurrence.get("first_occurrence_date"))
        next_session_date = None
        next_open = None
        if trigger_date is not None:
            next_session_date, next_open = _next_session_open(
                ohlcv_by_symbol.get(str(symbol)),
                trigger_date,
            )
        actual_exit_date = (
            _as_timestamp(trade.get("exit_date")) if trade is not None else None
        )
        feasible = False
        reason = ""
        if not bool(occurrence.get("actionable")):
            reason = "NO_ACTIONABLE_OCCURRENCE"
        elif next_session_date is None or next_open is None or pd.isna(next_open):
            reason = "NEXT_OPEN_MISSING"
        elif actual_exit_date is not None and next_session_date >= actual_exit_date:
            reason = "ACTUAL_EXIT_BEFORE_OR_ON_NEXT_OPEN"
        else:
            feasible = True
            reason = ""

        hypothetical_pnl = pd.NA
        hypothetical_r = pd.NA
        delta_pnl = pd.NA
        delta_r = pd.NA
        actual_pnl = trade.get("net_pnl") if trade is not None else pd.NA
        actual_r = trade.get("r_multiple") if trade is not None else pd.NA
        if feasible and trade is not None:
            hypothetical_pnl = _hypothetical_pnl(trade, next_open)
            risk = _numeric(trade.get("initial_risk_amount"))
            if _present(hypothetical_pnl) and risk and risk > 0:
                hypothetical_r = float(hypothetical_pnl) / risk
            if _present(hypothetical_pnl) and _present(actual_pnl):
                delta_pnl = float(hypothetical_pnl) - float(actual_pnl)
            if _present(hypothetical_r) and _present(actual_r):
                delta_r = float(hypothetical_r) - float(actual_r)

        rows.append(
            {
                "trade_id": trade_id,
                "candidate_flag_name": occurrence.get("candidate_flag_name"),
                "trigger_date": trigger_date,
                "next_session_date": next_session_date,
                "next_open_available": next_open is not None and not pd.isna(next_open),
                "hypothetical_exit_feasible": feasible,
                "infeasible_reason": reason,
                "hypothetical_exit_price": next_open if feasible else pd.NA,
                "hypothetical_exit_pnl": hypothetical_pnl,
                "hypothetical_exit_r": hypothetical_r,
                "actual_exit_date": actual_exit_date,
                "actual_exit_reason": trade.get("exit_reason") if trade is not None else pd.NA,
                "actual_pnl": actual_pnl,
                "actual_r": actual_r,
                "delta_pnl": delta_pnl,
                "delta_r": delta_r,
                "avoided_stop_candidate": (
                    feasible
                    and str(trade.get("exit_reason", "")).lower() == "stop_loss"
                    if trade is not None
                    else False
                ),
                "missed_target_candidate": (
                    feasible
                    and str(trade.get("exit_reason", "")).lower() == "target_hit"
                    if trade is not None
                    else False
                ),
                "diagnostic_only": True,
            }
        )
    return pd.DataFrame(rows)


def summarize_reconstruction_coverage(
    trades: pd.DataFrame,
    lifecycle: pd.DataFrame,
    joined: pd.DataFrame,
    entry_match_summary: pd.DataFrame,
    first_occurrences: pd.DataFrame,
    feasibility: pd.DataFrame,
) -> pd.DataFrame:
    """Return one-row prototype coverage summary."""

    lifecycle_rows = len(lifecycle)
    joined_rows = int((joined.get("state_join_status") == "STATE_JOINED").sum())
    missing_rows = int((joined.get("state_join_status") == "STATE_MISSING").sum())
    first_counts = _count_by(first_occurrences, "candidate_flag_name", "actionable")
    feasible_counts = _count_by(
        feasibility, "candidate_flag_name", "hypothetical_exit_feasible"
    )
    entry_checked = (
        int(entry_match_summary.iloc[0].get("trades_checked", 0))
        if not entry_match_summary.empty
        else 0
    )
    entry_match_rate = (
        entry_match_summary.iloc[0].get("match_rate_pct")
        if not entry_match_summary.empty
        else 0.0
    )
    return pd.DataFrame(
        [
            {
                "total_trades_loaded": len(trades),
                "trades_with_lifecycle_expanded": lifecycle["trade_id"].nunique()
                if "trade_id" in lifecycle
                else 0,
                "lifecycle_rows": lifecycle_rows,
                "rows_with_state_joined": joined_rows,
                "rows_missing_state": missing_rows,
                "state_join_coverage_pct": _pct(joined_rows, lifecycle_rows),
                "entry_state_trades_checked": entry_checked,
                "entry_state_match_rate_pct": entry_match_rate,
                "first_deterioration_candidates_count_by_flag": first_counts,
                "next_open_feasible_count_by_flag": feasible_counts,
                "missing_next_open_count": int(
                    (feasibility.get("infeasible_reason") == "NEXT_OPEN_MISSING").sum()
                ),
                "same_day_exit_blocked_count": int(
                    (
                        joined.get("actual_exit_on_holding_date", pd.Series(dtype=bool))
                        & ~joined.get(
                            "state_actionable_after_close", pd.Series(dtype=bool)
                        )
                    ).sum()
                ),
                "duplicate_trade_date_rows_count": int(
                    lifecycle.get("duplicate_trade_date", pd.Series(dtype=bool)).sum()
                ),
                "notes": DIAGNOSTIC_ONLY_CAVEAT,
            }
        ]
    )


def run_s2_state_reconstruction_prototype(
    report_dir: Path | str = DEFAULT_S2_REPORT_DIR,
    ohlc_csv_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
    ohlc_source: str = "csv",
    ohlc_loader: object | None = None,
    lookback_buffer_days: int = DEFAULT_OHLC_LOOKBACK_BUFFER_DAYS,
) -> ReconstructionRunResult:
    """Export prototype outputs from retained reports and per-symbol OHLC CSVs."""

    trades = load_s2_retained_trades(report_dir)
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
    validation_summary, validation_details = validate_entry_state_match(trades, states)
    coverage = summarize_reconstruction_coverage(
        trades,
        lifecycle,
        joined,
        validation_summary,
        first,
        feasibility,
    )

    output_path = Path(output_dir) if output_dir is not None else _dated_output_dir()
    output_path.mkdir(parents=True, exist_ok=True)
    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "report_dir": str(report_dir),
        "ohlc_source": ohlc_source,
        "ohlc_csv_dir": str(ohlc_csv_dir) if ohlc_csv_dir is not None else None,
        "lookback_buffer_days": lookback_buffer_days,
        "caveat": DIAGNOSTIC_ONLY_CAVEAT,
        "scope": "Phase 36G prototype export only; no backtest executed.",
    }
    outputs = {
        "s2_state_reconstruction_metadata.json": output_path
        / "s2_state_reconstruction_metadata.json",
        "s2_reconstructed_daily_state_path.csv": output_path
        / "s2_reconstructed_daily_state_path.csv",
        "s2_intrade_state_event_candidates.csv": output_path
        / "s2_intrade_state_event_candidates.csv",
        "s2_first_deterioration_candidate.csv": output_path
        / "s2_first_deterioration_candidate.csv",
        "s2_next_open_exit_feasibility.csv": output_path
        / "s2_next_open_exit_feasibility.csv",
        "s2_reconstruction_coverage_summary.csv": output_path
        / "s2_reconstruction_coverage_summary.csv",
        "s2_reconstruction_validation_summary.csv": output_path
        / "s2_reconstruction_validation_summary.csv",
        "s2_state_reconstruction_runtime_notes.txt": output_path
        / "s2_state_reconstruction_runtime_notes.txt",
    }
    outputs["s2_state_reconstruction_metadata.json"].write_text(
        json.dumps(metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    states.to_csv(outputs["s2_reconstructed_daily_state_path.csv"], index=False)
    candidates.to_csv(outputs["s2_intrade_state_event_candidates.csv"], index=False)
    first.to_csv(outputs["s2_first_deterioration_candidate.csv"], index=False)
    feasibility.to_csv(outputs["s2_next_open_exit_feasibility.csv"], index=False)
    coverage.to_csv(outputs["s2_reconstruction_coverage_summary.csv"], index=False)
    validation_summary.to_csv(
        outputs["s2_reconstruction_validation_summary.csv"],
        index=False,
    )
    outputs["s2_state_reconstruction_runtime_notes.txt"].write_text(
        DIAGNOSTIC_ONLY_CAVEAT
        + "\nEntry-state validation details are kept in memory by the module; "
        + "the CLI exports the requested validation summary only.\n",
        encoding="utf-8",
    )
    metadata["validation_detail_rows"] = len(validation_details)
    return ReconstructionRunResult(output_path, outputs, metadata)


def load_ohlc_for_reconstruction(
    trades: pd.DataFrame,
    *,
    ohlc_source: str,
    ohlc_csv_dir: Path | str | None = None,
    ohlc_loader: object | None = None,
    lookback_buffer_days: int = DEFAULT_OHLC_LOOKBACK_BUFFER_DAYS,
) -> dict[str, pd.DataFrame]:
    """Load normalized OHLC for retained trades from CSV or an existing loader."""

    source = str(ohlc_source).strip().lower()
    symbols = trades["symbol"].dropna().unique()
    if source == "csv":
        if ohlc_csv_dir is None:
            raise ValueError(
                "ohlc_csv_dir is required when ohlc_source='csv'; provide "
                "--ohlc-csv-dir or use --ohlc-source db."
            )
        return load_ohlc_csv_dir(ohlc_csv_dir, symbols)
    if source == "db":
        if ohlc_loader is None:
            raise ValueError(
                "ohlc_loader is required when ohlc_source='db'; the CLI must "
                "construct an existing Veridian DailyOHLCVLoader."
            )
        start_date, end_date = infer_ohlc_load_window(
            trades,
            lookback_buffer_days=lookback_buffer_days,
        )
        return load_ohlc_from_daily_loader(
            ohlc_loader,
            symbols,
            start_date=start_date,
            end_date=end_date,
        )
    raise ValueError("ohlc_source must be 'csv' or 'db'")


def load_ohlc_csv_dir(
    ohlc_csv_dir: Path | str,
    symbols: Iterable[object],
) -> dict[str, pd.DataFrame]:
    """Load normalized per-symbol OHLC CSVs from a directory."""

    base = Path(ohlc_csv_dir)
    if not base.exists():
        raise FileNotFoundError(f"OHLC CSV directory does not exist: {base}")
    data: dict[str, pd.DataFrame] = {}
    missing: list[str] = []
    for symbol in sorted({str(value) for value in symbols if _present(value)}):
        path = base / f"{symbol}.csv"
        if not path.exists():
            missing.append(symbol)
            continue
        data[symbol] = normalize_ohlcv_dataframe(pd.read_csv(path))
    if missing:
        raise FileNotFoundError(
            "missing OHLC CSV files for symbols: " + ", ".join(missing[:20])
        )
    return data


def infer_ohlc_load_window(
    trades: pd.DataFrame,
    lookback_buffer_days: int = DEFAULT_OHLC_LOOKBACK_BUFFER_DAYS,
) -> tuple[date, date]:
    """Infer an OHLC load window from retained trades with pre-start buffer."""

    if lookback_buffer_days < 0:
        raise ValueError("lookback_buffer_days must be non-negative")
    start_candidates = []
    for column in ("signal_date", "entry_date"):
        if column in trades:
            start_candidates.append(_date_series(trades[column]))
    if not start_candidates or "exit_date" not in trades:
        raise ValueError("trades must include signal/entry dates and exit_date")
    start_values = pd.concat(start_candidates).dropna()
    end_values = _date_series(trades["exit_date"]).dropna()
    if start_values.empty or end_values.empty:
        raise ValueError("could not infer OHLC date range from retained trades")
    start = start_values.min().date() - timedelta(days=lookback_buffer_days)
    end = end_values.max().date()
    return start, end


def load_ohlc_from_daily_loader(
    loader: object,
    symbols: Iterable[object],
    *,
    start_date: date,
    end_date: date,
) -> dict[str, pd.DataFrame]:
    """Load normalized OHLC using an existing Veridian daily OHLC loader."""

    normalized_symbols = sorted({str(value).strip().upper() for value in symbols if _present(value)})
    if not hasattr(loader, "load_symbols"):
        raise TypeError("ohlc_loader must provide load_symbols(symbols, start_date, end_date)")
    loaded = loader.load_symbols(normalized_symbols, start_date, end_date)
    data: dict[str, pd.DataFrame] = {}
    missing: list[str] = []
    for symbol in normalized_symbols:
        frame = loaded.get(symbol) if isinstance(loaded, Mapping) else None
        if frame is None or frame.empty:
            missing.append(symbol)
            continue
        data[symbol] = normalize_ohlcv_dataframe(frame)
    if missing:
        raise FileNotFoundError(
            "missing OHLC data from loader for symbols: " + ", ".join(missing[:20])
        )
    return data


def _coalesce_columns(frame: pd.DataFrame, columns: Iterable[str]) -> pd.Series:
    result = pd.Series(pd.NA, index=frame.index)
    for column in columns:
        if column in frame.columns:
            result = result.combine_first(frame[column])
    return result


def _normalize_trade_dates_and_numbers(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy(deep=True)
    for column in ("entry_date", "exit_date", "signal_date"):
        if column in result:
            result[column] = _date_series(result[column])
    for column in (
        "entry_price",
        "exit_price",
        "stop_price",
        "target_price",
        "quantity",
        "initial_risk_amount",
        "net_pnl",
        "r_multiple",
    ):
        if column in result:
            result[column] = pd.to_numeric(result[column], errors="coerce")
    return result


def _parsed_state_frame(labels: pd.Series) -> pd.DataFrame:
    return pd.DataFrame([parse_s2_state_label(value) for value in labels])


def _empty_reconstructed_state_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "symbol",
            "date",
            "state_label",
            "raw_state_label",
            "return_state",
            "volatility_state",
            "drawdown_state_component",
            "range_state",
            "unknown_components",
            "parse_status",
            "state_available",
            "state_unavailable_reason",
            "source_state_builder",
            "source_state_parameters",
        ]
    )


def _symbol_dates(frame: pd.DataFrame | None) -> list[pd.Timestamp]:
    if frame is None or frame.empty or "date" not in frame.columns:
        return []
    return _date_series(frame["date"]).dropna().sort_values().tolist()


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


def _as_timestamp(value: object) -> pd.Timestamp | None:
    timestamp = _normalize_date_value(value)
    if pd.isna(timestamp):
        return None
    return timestamp


def _normalize_date_value(value: object) -> pd.Timestamp:
    if not _present(value):
        return pd.NaT
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return pd.NaT
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_localize(None)
    return timestamp.normalize()


def _present(value: object) -> bool:
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    return str(value).strip() != ""


def _entry_alignment(trade: pd.Series) -> tuple[pd.Timestamp | None, str]:
    signal_date = _as_timestamp(trade.get("signal_date"))
    if signal_date is not None:
        return signal_date, "SIGNAL_DATE"
    return _as_timestamp(trade.get("entry_date")), "ENTRY_DATE_AMBIGUOUS"


def _entry_match_detail(
    trade: pd.Series,
    alignment_date: pd.Timestamp | None,
    status: str,
    alignment_used: str | None = None,
    reconstructed_state_label: object = pd.NA,
) -> dict[str, object]:
    if alignment_used is None:
        _, alignment_used = _entry_alignment(trade)
    return {
        "trade_id": trade.get("trade_id"),
        "symbol": trade.get("symbol"),
        "alignment_used": alignment_used,
        "alignment_date": alignment_date,
        "stored_entry_state_label": trade.get("stored_entry_state_label"),
        "reconstructed_state_label": reconstructed_state_label,
        "match_status": status,
    }


def _return_state_worse(current: object, entry: object) -> bool:
    if current not in RETURN_STATE_ORDER or entry not in RETURN_STATE_ORDER:
        return False
    return RETURN_STATE_ORDER[str(current)] > RETURN_STATE_ORDER[str(entry)]


def _next_session_open(
    frame: pd.DataFrame | None,
    trigger_date: pd.Timestamp,
) -> tuple[pd.Timestamp | None, float | None]:
    if frame is None or frame.empty or "date" not in frame.columns or "open" not in frame:
        return None, None
    normalized = normalize_ohlcv_dataframe(frame)
    normalized["date"] = _date_series(normalized["date"])
    future = normalized[normalized["date"] > trigger_date].sort_values("date")
    if future.empty:
        return None, None
    row = future.iloc[0]
    return row["date"], _numeric(row.get("open"))


def _hypothetical_pnl(trade: pd.Series, exit_price: object) -> float | pd.NA:
    entry = _numeric(trade.get("entry_price"))
    quantity = _numeric(trade.get("quantity"))
    exit_value = _numeric(exit_price)
    if entry is None or quantity is None or exit_value is None:
        return pd.NA
    return (exit_value - entry) * quantity


def _numeric(value: object) -> float | None:
    if not _present(value):
        return None
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return None
    return float(numeric)


def _pct(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0:
        return 0.0
    return round((float(numerator) / float(denominator)) * 100, 6)


def _summarize_values(frame: pd.DataFrame, column: str) -> str:
    if frame.empty or column not in frame:
        return ""
    values = [str(value) for value in frame[column].dropna().unique()]
    return "|".join(sorted(values))


def _count_by(frame: pd.DataFrame, group_column: str, flag_column: str) -> str:
    if frame.empty or group_column not in frame or flag_column not in frame:
        return ""
    counts = (
        frame[frame[flag_column].fillna(False)]
        .groupby(group_column, dropna=False)
        .size()
        .to_dict()
    )
    return json.dumps({str(key): int(value) for key, value in sorted(counts.items())})


def _dated_output_dir() -> Path:
    return DEFAULT_OUTPUT_ROOT / (
        "s2_state_reconstruction_prototype_"
        + datetime.now().strftime("%Y%m%d")
    )
