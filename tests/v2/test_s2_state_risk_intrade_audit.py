from __future__ import annotations

from datetime import date

import pandas as pd

from veridian_quant.v2.analysis.s2_state_risk_intrade_audit import (
    READ_ONLY_NON_APPROVAL,
    build_entry_state_risk_frame,
    build_intrade_state_event_frame,
    build_terminal_edge_case_audit,
    sample_size_flag,
    summarize_deterioration_candidates,
    summarize_entry_state_performance,
    summarize_missed_target_vs_avoided_stop,
    summarize_next_open_feasibility,
    summarize_next_open_hypothetical_exits,
    summarize_same_day_exit_safety,
    summarize_winner_through_bad_state,
)


def test_sample_size_flag_thresholds() -> None:
    assert sample_size_flag(19) == "INSUFFICIENT"
    assert sample_size_flag(20) == "SMALL"
    assert sample_size_flag(49) == "SMALL"
    assert sample_size_flag(50) == "USABLE"
    assert sample_size_flag(99) == "USABLE"
    assert sample_size_flag(100) == "STRONG"


def test_grouped_performance_summary_handles_wins_losses_and_zero_loss_pf() -> None:
    entry = build_entry_state_risk_frame(
        _trades(),
        universe=_universe(),
        classifications=_classifications(),
    )

    summary = summarize_entry_state_performance(entry, ["state_label"])
    rows = summary.set_index("state_label")

    up = rows.loc["RET_UP|VOL_MID|DD_SHALLOW|LOW_NEAR"]
    assert up["trades"] == 2
    assert up["net_pnl"] == 50.0
    assert up["gross_profit"] == 100.0
    assert up["gross_loss"] == -50.0
    assert up["profit_factor"] == 2.0
    assert up["win_rate_pct"] == 50.0
    assert up["avg_r"] == 0.25
    assert up["median_r"] == 0.25

    strong = rows.loc["RET_STRONG_UP|VOL_LOW|DD_MILD|LOW_FAR_FROM_LOW"]
    assert pd.isna(strong["profit_factor"])
    assert strong["target_count"] == 1


def test_entry_frame_joins_optional_context_without_mutating_callers() -> None:
    trades = _trades()
    original_columns = list(trades.columns)

    entry = build_entry_state_risk_frame(
        trades,
        universe=_universe(),
        classifications=_classifications(),
    )

    assert list(trades.columns) == original_columns
    row = entry.set_index("trade_id").loc["T1"]
    assert row["liquidity_bucket"] == "HIGH"
    assert row["sector"] == "Financials"
    assert row["return_state"] == "RET_UP"

    missing = entry.set_index("trade_id").loc["T3"]
    assert missing["liquidity_bucket"] == "UNKNOWN"
    assert missing["sector"] == "UNKNOWN"


def test_lane_a_summaries_and_interaction_matrix_include_sample_sizes() -> None:
    entry = build_entry_state_risk_frame(
        _trades(),
        universe=_universe(),
        classifications=_classifications(),
    )

    by_liquidity = summarize_entry_state_performance(
        entry,
        ["state_label", "liquidity_bucket"],
    )
    matrix = summarize_entry_state_performance(
        entry,
        ["state_label", "liquidity_bucket", "benchmark_regime", "vix_regime"],
    )

    high = by_liquidity[by_liquidity["liquidity_bucket"] == "HIGH"].iloc[0]
    assert high["trades"] == 2
    assert high["sample_size_flag"] == "INSUFFICIENT"
    assert {"state_label", "liquidity_bucket", "benchmark_regime", "vix_regime"}.issubset(
        matrix.columns
    )


def test_lane_b_event_frame_joins_first_candidates_and_feasibility() -> None:
    entry = build_entry_state_risk_frame(
        _trades(),
        universe=_universe(),
        classifications=_classifications(),
    )

    event = build_intrade_state_event_frame(
        _trades(),
        _first_occurrences(),
        _feasibility(),
        entry,
    )

    row = event.set_index(["trade_id", "candidate_flag_name"]).loc[
        ("T1", "contains_ret_down")
    ]
    assert row["trigger_holding_day_index"] == 1
    assert bool(row["hypothetical_exit_feasible"]) is True
    assert bool(row["improved_pnl_candidate"]) is True
    assert bool(row["avoided_stop_candidate"]) is True
    assert row["liquidity_bucket"] == "HIGH"


def test_deterioration_summary_counts_candidates_and_outcomes() -> None:
    event = _event_frame()

    summary = summarize_deterioration_candidates(
        event,
        ["candidate_flag_name"],
        total_trades=3,
    ).set_index("candidate_flag_name")
    row = summary.loc["contains_ret_down"]

    assert row["total_trades"] == 3
    assert row["trades_with_candidate"] == 2
    assert row["trades_without_candidate"] == 1
    assert row["feasible_next_open_candidates"] == 1
    assert row["infeasible_candidates"] == 2
    assert row["trigger_before_stop_count"] == 1
    assert row["trigger_before_target_count"] == 1
    assert row["winner_through_bad_state_count"] == 1
    assert row["loser_through_bad_state_count"] == 1
    assert row["improved_count"] == 1
    assert row["worsened_count"] == 0
    assert row["avoided_stop_candidate_count"] == 1
    assert row["missed_target_candidate_count"] == 0


def test_next_open_hypothetical_and_pass_through_summaries() -> None:
    event = _event_frame()

    next_open = summarize_next_open_hypothetical_exits(event).set_index(
        "candidate_flag_name"
    )
    pass_through = summarize_winner_through_bad_state(event).set_index(
        "candidate_flag_name"
    )
    stop_target = summarize_missed_target_vs_avoided_stop(event).set_index(
        "candidate_flag_name"
    )

    assert next_open.loc["contains_ret_down"]["feasible_rows"] == 1
    assert next_open.loc["contains_ret_down"]["avg_delta_r"] == 0.4
    assert pass_through.loc["contains_ret_down"]["winner_through_bad_state_count"] == 1
    assert stop_target.loc["contains_ret_down"]["avoided_stop_candidate_count"] == 1


def test_same_day_safety_summary_returns_zero_actionable_failures() -> None:
    joined = pd.DataFrame(
        [
            {
                "actual_exit_on_holding_date": False,
                "state_actionable_after_close": True,
            },
            {
                "actual_exit_on_holding_date": True,
                "state_actionable_after_close": False,
            },
        ]
    )

    summary = summarize_same_day_exit_safety(joined).iloc[0]

    assert summary["same_day_exit_rows"] == 1
    assert summary["blocked_rows"] == 1
    assert summary["actionable_failures"] == 0
    assert summary["verdict"] == "PASS"


def test_terminal_edge_case_audit_identifies_exit_beyond_lifecycle() -> None:
    lifecycle = pd.DataFrame(
        [
            {"trade_id": "T1", "holding_date": pd.Timestamp("2026-01-05")},
            {"trade_id": "T2", "holding_date": pd.Timestamp("2026-01-06")},
        ]
    )

    audit = build_terminal_edge_case_audit(_trades(), lifecycle)

    assert audit["trade_id"].tolist() == ["T1"]
    assert audit.iloc[0]["exit_date"].date() == date(2026, 1, 6)
    assert audit.iloc[0]["max_lifecycle_date"].date() == date(2026, 1, 5)
    assert audit.iloc[0]["edge_case_reason"] == "EXIT_AFTER_RECONSTRUCTED_LIFECYCLE_MAX_DATE"


def test_next_open_feasibility_summary_counts_reasons_and_flags() -> None:
    summary = summarize_next_open_feasibility(_feasibility()).iloc[0]

    assert summary["total_candidate_rows"] == 3
    assert summary["feasible_rows"] == 1
    assert summary["infeasible_rows"] == 2
    assert summary["missing_next_open_count"] == 1
    assert "NEXT_OPEN_MISSING" in summary["infeasible_reasons"]
    assert "contains_ret_down" in summary["candidate_flag_breakdown"]


def test_non_approval_language_is_explicit() -> None:
    language = READ_ONLY_NON_APPROVAL.lower()
    assert "not a strategy backtest" in language
    assert "not a dynamic exit" in language
    assert "not approved for production behavior" in language


def _trades() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _trade("T1", "AAA", "stop_loss", -50.0, -0.5),
            _trade("T2", "AAA", "target_hit", 100.0, 1.0),
            _trade(
                "T3",
                "BBB",
                "target_hit",
                75.0,
                0.75,
                state="RET_STRONG_UP|VOL_LOW|DD_MILD|LOW_FAR_FROM_LOW",
            ),
        ]
    )


def _trade(
    trade_id: str,
    symbol: str,
    exit_reason: str,
    pnl: float,
    r_multiple: float,
    *,
    state: str = "RET_UP|VOL_MID|DD_SHALLOW|LOW_NEAR",
) -> dict[str, object]:
    return {
        "trade_id": trade_id,
        "symbol": symbol,
        "signal_date": pd.Timestamp("2026-01-01"),
        "entry_date": pd.Timestamp("2026-01-02"),
        "exit_date": pd.Timestamp("2026-01-06"),
        "exit_reason": exit_reason,
        "net_pnl": pnl,
        "r_multiple": r_multiple,
        "stored_entry_state_label": state,
        "benchmark_regime": "BENCH_UP",
        "vix_regime": "VIX_LOW",
    }


def _universe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": "AAA",
                "liquidity_bucket": "HIGH",
                "liquidity_metric": 123.0,
            }
        ]
    )


def _classifications() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": "AAA",
                "sector": "Financials",
                "industry": "Bank",
                "basic_industry": "Private Bank",
            }
        ]
    )


def _first_occurrences() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "trade_id": "T1",
                "symbol": "AAA",
                "candidate_flag_name": "contains_ret_down",
                "first_occurrence_date": pd.Timestamp("2026-01-05"),
                "holding_day_index": 1,
                "state_label": "RET_DOWN|VOL_MID|DD_SHALLOW|LOW_NEAR",
                "return_state": "RET_DOWN",
                "volatility_state": "VOL_MID",
                "drawdown_state_component": "DD_SHALLOW",
                "range_state": "LOW_NEAR",
                "actionable": True,
            },
            {
                "trade_id": "T2",
                "symbol": "AAA",
                "candidate_flag_name": "contains_ret_down",
                "first_occurrence_date": pd.Timestamp("2026-01-05"),
                "holding_day_index": 1,
                "state_label": "RET_DOWN|VOL_MID|DD_SHALLOW|LOW_NEAR",
                "return_state": "RET_DOWN",
                "volatility_state": "VOL_MID",
                "drawdown_state_component": "DD_SHALLOW",
                "range_state": "LOW_NEAR",
                "actionable": True,
            },
            {
                "trade_id": "T3",
                "symbol": "BBB",
                "candidate_flag_name": "contains_ret_down",
                "first_occurrence_date": pd.NaT,
                "holding_day_index": pd.NA,
                "state_label": pd.NA,
                "return_state": pd.NA,
                "volatility_state": pd.NA,
                "drawdown_state_component": pd.NA,
                "range_state": pd.NA,
                "actionable": False,
            },
        ]
    )


def _feasibility() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "trade_id": "T1",
                "candidate_flag_name": "contains_ret_down",
                "next_session_date": pd.Timestamp("2026-01-06"),
                "hypothetical_exit_feasible": True,
                "infeasible_reason": "",
                "hypothetical_exit_price": 95.0,
                "hypothetical_exit_pnl": -10.0,
                "hypothetical_exit_r": -0.1,
                "actual_pnl": -50.0,
                "actual_r": -0.5,
                "delta_pnl": 40.0,
                "delta_r": 0.4,
                "avoided_stop_candidate": True,
                "missed_target_candidate": False,
            },
            {
                "trade_id": "T2",
                "candidate_flag_name": "contains_ret_down",
                "next_session_date": pd.Timestamp("2026-01-06"),
                "hypothetical_exit_feasible": False,
                "infeasible_reason": "ACTUAL_EXIT_BEFORE_OR_ON_NEXT_OPEN",
                "hypothetical_exit_price": pd.NA,
                "hypothetical_exit_pnl": pd.NA,
                "hypothetical_exit_r": pd.NA,
                "actual_pnl": 100.0,
                "actual_r": 1.0,
                "delta_pnl": pd.NA,
                "delta_r": pd.NA,
                "avoided_stop_candidate": False,
                "missed_target_candidate": False,
            },
            {
                "trade_id": "T3",
                "candidate_flag_name": "contains_ret_down",
                "next_session_date": pd.NaT,
                "hypothetical_exit_feasible": False,
                "infeasible_reason": "NEXT_OPEN_MISSING",
                "hypothetical_exit_price": pd.NA,
                "hypothetical_exit_pnl": pd.NA,
                "hypothetical_exit_r": pd.NA,
                "actual_pnl": 75.0,
                "actual_r": 0.75,
                "delta_pnl": pd.NA,
                "delta_r": pd.NA,
                "avoided_stop_candidate": False,
                "missed_target_candidate": False,
            },
        ]
    )


def _event_frame() -> pd.DataFrame:
    entry = build_entry_state_risk_frame(
        _trades(),
        universe=_universe(),
        classifications=_classifications(),
    )
    return build_intrade_state_event_frame(
        _trades(),
        _first_occurrences(),
        _feasibility(),
        entry,
    )
