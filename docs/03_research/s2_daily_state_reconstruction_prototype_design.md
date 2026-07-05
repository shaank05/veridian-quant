# Phase 36F — S2 Daily State Reconstruction Prototype Design

## 1. Status / Verdict

Phase 36F is docs/design only.

No reconstruction code is implemented. No audit helper is implemented. No
backtest is run. No report is generated. No dynamic exit is approved. No S2
rule or filter is approved.

This phase designs a future narrow prototype for reconstructing daily in-trade
S2 states.

Decision:

`PROCEED_TO_36G_STATE_RECONSTRUCTION_PROTOTYPE_IMPLEMENTATION`

---

## 2. Why 36F Exists

Phase 36E found:

- Lane A Entry-State x Risk is `READY_WITH_MINOR_GAPS`.
- Lane B In-Trade State Evolution is `NEEDS_DAILY_STATE_RECONSTRUCTION`.
- Entry state metadata exists in existing retained reports.
- Daily in-trade state paths are not stored.
- `trade_log.csv`, `trade_pnl_log.csv`, and `trade_signal_context.csv` share
  `trade_id`.
- Daily state reconstruction appears feasible using `build_state_frame`.

Phase 36F exists because Lane B cannot safely move straight to a full audit
helper. The project first needs an explicit design for date alignment,
trade-lifecycle expansion, same-day stop/target handling, and hypothetical
next-open audit-only exits.

---

## 3. Prototype Objective

The future prototype should answer:

- Can daily S2 state paths be reconstructed for open S2 trades without
  lookahead?
- Can reconstructed daily states be joined to trade lifecycle dates?
- Can state components be parsed consistently from composite `state_label`?
- Can first deterioration events be identified safely?
- Can hypothetical next-open audit-only exits be computed without using future
  information?
- Can same-day stop/target conflicts be handled safely?

Important:

The prototype is not an exit rule. It is only a reconstruction and audit
feasibility check.

---

## 4. Inputs Required

Required inputs:

- Retained S2 report folder:
  `reports/v2/s2_markov_2020_2026_research200_exclude_ret_down_full_diagnostics/`
- `trade_log.csv`
- `trade_pnl_log.csv`
- `trade_signal_context.csv`
- `signal_log.csv`, if useful for entry-state validation.
- OHLC source used by backtests.
- S2 state-builder source, especially `build_state_frame`.
- Research200 universe for liquidity bucket.

Optional risk/context sources:

- Benchmark regime.
- VIX regime.
- Drawdown state.
- Sector/static classification.
- Gap context.

---

## 5. Future Prototype Output Files

Planned folder:

`reports/v2/s2_state_reconstruction_prototype_YYYYMMDD/`

Generated outputs for future implementation:

- `s2_state_reconstruction_metadata.json`
- `s2_reconstructed_daily_state_path.csv`
- `s2_intrade_state_event_candidates.csv`
- `s2_first_deterioration_candidate.csv`
- `s2_next_open_exit_feasibility.csv`
- `s2_reconstruction_coverage_summary.csv`
- `s2_reconstruction_validation_summary.csv`
- `s2_state_reconstruction_runtime_notes.txt`

Generated reports are not for commit unless separately approved.

---

## 6. Daily State Reconstruction Design

The future prototype should:

- For each symbol, load OHLC with sufficient pre-start lookback.
- Run the S2 state builder over the symbol's full required date range.
- Preserve the same state construction parameters as the retained S2 benchmark.
- Use data available through each date D only.
- Produce one state row per symbol/date.
- Parse composite `state_label` into components:
  - Return component.
  - Volatility component.
  - Drawdown component if present.
  - Range/location component.
- Preserve raw `state_label`.

Required fields:

- `symbol`.
- `date`.
- `state_label`.
- `return_state`.
- `volatility_state`.
- `drawdown_state_component`.
- `range_state`.
- `state_available`.
- `state_unavailable_reason`.
- `source_state_builder_version` / parameters, if feasible.

---

## 7. Trade Lifecycle Expansion Design

The future prototype should:

- Use executed S2 trades from the retained report.
- Use `trade_id` as primary join key.
- For each trade, expand holding-period dates from entry date through exit date.
- Include holding-day index.
- Join reconstructed state by symbol/date.
- Preserve:
  - Entry date.
  - Exit date.
  - Exit reason.
  - Entry price.
  - Exit price.
  - Stop.
  - Target.
  - Quantity.
  - R/PnL if available.
- Mark dates where state is unavailable.

Required fields:

- `trade_id`.
- `symbol`.
- `entry_date`.
- `exit_date`.
- `holding_date`.
- `holding_day_index`.
- `state_label`.
- State components.
- `exit_reason`.
- `trade_net_pnl`.
- `trade_r_multiple`.
- `state_join_status`.

---

## 8. Same-Day Stop/Target Safety Design

Important:

If a trade exits intraday on date D because stop/target is hit, a D-close state
cannot be used to trigger an exit before that event.

Conservative rule:

- D-close state may only be considered for a hypothetical next-open exit if the
  trade remains open after date D close.
- If the actual trade exits on D, do not use D state as an actionable trigger.
- For trigger date D, hypothetical exit is the next valid session open after D.
- If no next session exists before actual exit or end date, mark infeasible.
- If the actual trade exits before the next open, the hypothetical trigger is
  infeasible or must be classified as too late.

Required fields:

- `state_actionable_after_close`.
- `actual_exit_on_holding_date`.
- `next_session_date`.
- `next_open_available`.
- `hypothetical_exit_feasible`.
- `infeasible_reason`.

---

## 9. Deterioration Candidate Design

This prototype should not choose final triggers, but may compute candidate
flags.

Candidate diagnostic-only deterioration flags:

- `contains_ret_down`.
- `return_state_worse_than_entry`.
- `entered_ret_down_after_entry`.
- `entered_vol_high_after_entry`.
- `state_changed_from_entry`.
- `entered_unseen_or_bad_state_candidate`, if historical state outcome lookup is
  available later, but do not implement outcome ranking yet.

For each candidate:

- Define exactly from current/entry state components.
- Use no PnL-optimized threshold.
- Use no future outcome to define deterioration.

Required fields:

- `entry_state_label`.
- `current_state_label`.
- `entry_return_state`.
- `current_return_state`.
- `candidate_flag_name`.
- `candidate_flag_value`.
- `first_occurrence_date`.
- `is_first_occurrence`.

---

## 10. Hypothetical Next-Open Exit Feasibility Design

This is audit-only, not strategy logic.

For each first deterioration candidate:

- Trigger is observed after close on D.
- Hypothetical execution is at next session open.
- Compute hypothetical exit price from next session open.
- Compute hypothetical PnL/R using existing trade setup details.
- Compare to actual trade PnL/R.
- Classify:
  - `avoided_stop_candidate`.
  - `missed_target_candidate`.
  - `improved_pnl_candidate`.
  - `worsened_pnl_candidate`.
- Use actual outcome only after the fact for analysis, not to trigger.

Required fields:

- `trigger_date`.
- `next_session_date`.
- `hypothetical_exit_price`.
- `hypothetical_exit_pnl`.
- `hypothetical_exit_r`.
- `actual_exit_date`.
- `actual_exit_reason`.
- `actual_pnl`.
- `actual_r`.
- `delta_pnl`.
- `delta_r`.
- `avoided_stop_candidate`.
- `missed_target_candidate`.

---

## 11. Coverage / Validation Checks

The future prototype must report:

- Total trades inspected.
- Trades with complete lifecycle.
- Trades with reconstructed state path.
- Trades missing state rows.
- State reconstruction coverage by year.
- State reconstruction coverage by symbol.
- Number of holding-day rows.
- Holding-day rows with state available.
- Next-open feasibility coverage.
- Missing OHLC/next-open cases.
- Duplicate trade/date rows.
- Mismatched `trade_id` cases.
- Entry-state match rate between reconstructed entry state and existing
  trade/signal metadata.

The entry-state match rate is critical:

- Compare reconstructed entry/signal state with stored state metadata.
- If mismatch rate is high, reconstruction is not trusted.

---

## 12. Acceptance Criteria For Future Prototype

The prototype can proceed to full audit helper only if:

- Reconstructed entry-state match rate is high.
- Holding-day state coverage is high.
- No major `trade_id` join failures exist.
- Next-open feasibility is well-defined.
- Same-day exit safety is implemented.
- Reconstruction uses no future data.
- Output schemas are complete.
- Limitations are documented.

If entry-state match is poor:

- Stop and debug state reconstruction before full audit.

---

## 13. Lookahead / Data Safety Rules

- Use no future rows in state reconstruction for date D.
- Trigger from D state can only execute at next session open.
- Do not use realized outcome to define trigger.
- Join actual outcome after trigger analysis only.
- Preserve pre-start lookback.
- Respect configured end date.
- Do not use D-close state if the trade exited intraday on D.
- Do not model execution at D close unless separately approved.

---

## 14. Anti-Overfitting Guardrails

- Do not choose triggers by PnL.
- Use no optimized thresholds.
- Do not exclude symbols or years.
- Do not promote tiny samples.
- Report sample sizes for every trigger.
- Treat 2025-only benefits as fragile.
- Any future dynamic exit experiment must be pre-registered.
- The prototype is not evidence of edge.

---

## 15. Future Implementation Skeleton

Suggested future module:

`src/veridian_quant/v2/analysis/s2_state_reconstruction.py`

Suggested future tests:

`tests/v2/test_s2_state_reconstruction.py`

Likely future functions:

- `load_s2_retained_trades`.
- `reconstruct_symbol_state_frame`.
- `parse_s2_state_label`.
- `expand_trade_lifecycle_dates`.
- `join_daily_states_to_trades`.
- `compute_deterioration_candidates`.
- `compute_next_open_exit_feasibility`.
- `summarize_reconstruction_coverage`.
- `validate_entry_state_match`.

---

## 16. Future Decision Path

After 36F:

- 36G - Implement narrow state reconstruction prototype.
- 36H - Run prototype/export reconstruction coverage CSVs.
- 36I - Scrutinize reconstruction coverage.
- 36J - If coverage passes, implement full Lane A/B read-only audit helper.

Possible decisions after prototype:

- `PROCEED_TO_FULL_S2_STATE_RISK_INTRATRADE_AUDIT_HELPER`.
- `DEBUG_STATE_RECONSTRUCTION`.
- `REVISE_INTRADE_DESIGN`.
- `PARK_INTRADE_STATE_EVOLUTION`.
- `LIMIT_TO_ENTRY_STATE_RISK_ONLY`.

---

## 17. Explicitly Not Approved

- No dynamic exit rule.
- No `exit if RET_DOWN`.
- No entry filter.
- No state exclusion.
- No risk filter.
- No liquidity filter.
- No VIX/benchmark/drawdown rule.
- No risk sizing change.
- No production use.
- No strategy promotion.
- No backtest optimization.

---

## 18. Decision

`PROCEED_TO_36G_STATE_RECONSTRUCTION_PROTOTYPE_IMPLEMENTATION`

Phase 36F approves only a future narrow reconstruction prototype
implementation. It does not approve a full Lane A/B audit helper, a dynamic
exit experiment, or any S2 trading rule.
