# Phase 36J — Full Read-Only S2 State × Risk / In-Trade Audit Design

## 1. Status / Verdict

Phase 36J is docs/design only.

The Phase 36G reconstruction prototype and later DB-backed rerun made the full
S2 State x Risk / In-Trade audit design possible. Phase 36I scrutiny classified
the reconstruction prototype as `PASS_WITH_CAVEATS`:

- Trades loaded: 577.
- Trades with lifecycle expanded: 577.
- Lifecycle rows: 7,113.
- Rows with state joined: 7,113.
- Rows missing state: 0.
- State join coverage: 100.0%.
- Duplicate trade/date rows: 0.
- Entry-state trades checked: 577.
- Entry-state matches: 577.
- Entry-state mismatches: 0.
- Entry-state match rate: 100.0%.
- Alignment used: `SIGNAL_DATE`.
- Same-day exit blocked rows: 572.
- Exit-date actionable failures: 0.
- Next-open feasibility rows: 2,885.
- Feasible next-open candidate rows: 1,854.
- Infeasible next-open candidate rows: 1,031.

The full audit helper is not implemented yet. No S2 rule, filter, dynamic exit,
backtest, sizing change, threshold optimization, production use, or strategy
promotion is approved by this phase.

Phase 36J decision:

`PROCEED_TO_36K_FULL_READ_ONLY_S2_STATE_RISK_INTRATRADE_AUDIT_IMPLEMENTATION`

## 2. Why 36J Exists

S2 remains the strongest retained internal strategy benchmark, but it is still
fragile. Prior S2 failure work showed stop churn and state/regime
non-stationarity, especially around fragile years.

Phase 36 risk diagnostics identified several possible diagnostic inputs:
liquidity, drawdown, benchmark regime, VIX, gap risk, and rolling realized
performance. Those inputs are not approved as rules; they are candidates for
read-only explanation of S2's strengths and failures.

Phase 36I proved that daily S2 state reconstruction is technically trustworthy
enough for a read-only audit:

- 7,113 / 7,113 state rows joined.
- 577 / 577 entry states matched.
- 0 duplicate trade/date rows.
- 572 / 572 same-day exits were blocked from same-day actionability.
- 1,854 next-open candidate rows were feasible for audit-only comparison.

Therefore the next step can be a full read-only design that combines Lane A
entry-state x risk diagnostics and Lane B in-trade state evolution diagnostics.

## 3. Audit Non-Goals

The full audit is not a strategy change. It must not approve or implement:

- Dynamic exits.
- `exit if RET_DOWN`.
- Entry filters.
- State exclusions.
- Liquidity, VIX, benchmark, drawdown, or risk rules.
- Risk sizing changes.
- Backtest optimization.
- Production use.
- Strategy promotion.
- Threshold tuning.

## 4. Inputs Required

Retained S2 report folder:

`reports/v2/s2_markov_2020_2026_research200_exclude_ret_down_full_diagnostics/`

Required retained files:

- `trade_log.csv`.
- `trade_pnl_log.csv`.
- `trade_signal_context.csv`.
- `signal_log.csv` if useful for supplementary signal-level context.

Other inputs:

- DB OHLC via the existing `DatabaseClient` and `SQLAlchemyDailyOHLCVLoader`
  path.
- Phase 36G reconstruction module:
  `src/veridian_quant/v2/analysis/s2_state_reconstruction.py`.
- Research200 universe:
  `config/universes/research/nse_eq_research_200_2018_2026.csv`.
- Static classification:
  `config/universes/research/nse_eq_research_200_static_classification.csv`.
- Phase 36 risk/VIX outputs or code paths where appropriate.
- Benchmark/NIFTY context.
- VIX source if used.
- Phase 36I reconstruction prototype outputs may be used as validation or
  reference artifacts, but the future helper should regenerate reconstruction
  data unless a later implementation phase explicitly chooses a cached-input
  mode.

## 5. Lane A - Entry-State x Risk Diagnostic Design

Lane A studies executed S2 trades at the signal/entry date. It is read-only and
uses realized trade outcomes only for diagnostic grouping.

State dimensions:

- Composite `state_label`.
- `return_state`.
- `volatility_state`.
- `drawdown_state_component`.
- `range_state`.
- Possible transition metadata if available later.

Risk/context dimensions:

- Liquidity bucket.
- Benchmark 20D regime.
- VIX level/regime/change if available.
- Drawdown state at entry.
- Pre-entry gap bucket.
- Sector.
- Year.
- Symbol.
- Rolling R / recent realized performance only as a high-overfit secondary
  diagnostic.
- Exit reason.

Core questions:

- Which entry states are profitable or fragile?
- Does `exclude_ret_down` success come from return state itself or from
  interaction with liquidity, benchmark, drawdown, or VIX?
- Are weak years concentrated in specific state x risk combinations?
- Are loss clusters driven by specific state x risk contexts?
- Are stop-gap and tail risks concentrated in specific state x risk buckets?

Planned Lane A outputs:

- `s2_entry_state_performance.csv`.
- `s2_entry_state_by_year.csv`.
- `s2_entry_state_by_liquidity.csv`.
- `s2_entry_state_by_benchmark_regime.csv`.
- `s2_entry_state_by_vix_regime.csv`.
- `s2_entry_state_by_drawdown_state.csv`.
- `s2_entry_state_by_gap_context.csv`.
- `s2_entry_state_by_exit_reason.csv`.
- `s2_state_risk_interaction_matrix.csv`.
- `s2_state_risk_sample_size_flags.csv`.

Metrics for each bucket:

- Trades.
- Net PnL.
- Gross profit.
- Gross loss.
- Profit factor.
- Win rate.
- Average PnL.
- Median PnL.
- Average R.
- Median R.
- Maximum loss.
- Stop-loss count and pct.
- Target count and pct.
- Time-stop count and pct.
- Gap-stop count and pct.
- Sample-size flag.

## 6. Lane B - In-Trade State Evolution Diagnostic Design

Lane B studies daily holding-period state paths after trade entry. It is
read-only and audit-only.

Inputs:

- Reconstructed lifecycle rows.
- Parsed daily state components.
- Candidate deterioration flags.
- Actual trade outcomes.
- Next-open feasibility table.

Core questions:

- Do bad or deteriorating states appear before stops more often than before
  targets?
- Do winners pass through the same bad states, making exit rules dangerous?
- Are deterioration events early enough to act at the next open?
- Are deterioration events stable by year, liquidity, benchmark, and VIX?
- Which flags are too broad and kill too many winners?
- Would next-open hypothetical exits improve or worsen outcomes, audit-only?

Candidate flags from Phase 36I:

- `contains_ret_down`.
- `entered_ret_down_after_entry`.
- `entered_vol_high_after_entry`.
- `return_state_worse_than_entry`.
- `state_changed_from_entry`.

Planned Lane B outputs:

- `s2_intrade_state_path_summary.csv`.
- `s2_deterioration_candidate_summary.csv`.
- `s2_deterioration_by_year.csv`.
- `s2_deterioration_by_liquidity.csv`.
- `s2_deterioration_by_benchmark_regime.csv`.
- `s2_deterioration_by_vix_regime.csv`.
- `s2_deterioration_by_exit_reason.csv`.
- `s2_deterioration_timing_summary.csv`.
- `s2_next_open_hypothetical_exit_summary.csv`.
- `s2_next_open_hypothetical_by_flag_year.csv`.
- `s2_winner_through_bad_state_audit.csv`.
- `s2_missed_target_vs_avoided_stop_audit.csv`.
- `s2_terminal_edge_case_audit.csv`.

Metrics:

- Trades with candidate.
- Trades without candidate.
- Feasible next-open candidates.
- Infeasible candidates.
- Average trigger holding day.
- Median trigger holding day.
- Trigger before stop count and pct.
- Trigger before target count and pct.
- Winner-through-bad-state count and pct.
- Loser-through-bad-state count and pct.
- Hypothetical exit average R.
- Actual average R.
- Delta R.
- Improved count and pct.
- Worsened count and pct.
- Avoided stop candidate count.
- Missed target candidate count.
- Year stability.
- Sample-size flag.

## 7. Terminal Edge Case Handling

Phase 36I caveat:

- 5 trades exit on 2026-04-29 while the reconstructed lifecycle/state path ends
  2026-04-28.

The full audit must label these as terminal-edge cases. It must not silently
drop them.

Allowed treatment:

- Include through the last reconstructed date but exclude exit-date
  actionability checks.
- Exclude from in-trade next-open feasibility summaries where the missing final
  calendar row makes the comparison incomplete.
- Include in Lane A entry-state diagnostics if entry/outcome metadata is
  complete.

Required export:

- `s2_terminal_edge_case_audit.csv`.

## 8. Same-Day Exit Safety Rules

Carry forward the Phase 36G/36I safety rules:

- Date-D close state is known only after D close.
- If the actual trade exits on date D, D-close state is not actionable.
- A hypothetical action can only happen at the next valid session open after D.
- If actual exit occurs before or on the next open, the candidate is infeasible
  / too late.
- Same-day exit rows must be counted and blocked.
- The audit must report actionable failures; expected value is 0.

## 9. Next-Open Hypothetical Exit Audit Rules

The next-open table is audit-only. It must not execute a strategy rule.

Rules:

- Trigger date D comes from reconstructed state after close.
- Hypothetical exit price is the next valid session open.
- Hypothetical PnL/R is computed only when the candidate is feasible.
- Actual PnL/R is compared after the fact for diagnostics.
- Do not include transaction-cost assumptions unless already available and
  consistent with retained reports.
- Do not feed hypothetical exits into a portfolio ledger.

Classification:

- `improved`.
- `worsened`.
- `avoided_stop_candidate`.
- `missed_target_candidate`.
- `too_late`.
- `no_actionable_occurrence`.

## 10. Risk/Context Join Design

Risk/context joins apply to both Lane A and Lane B. Lane A joins at
signal/entry alignment. Lane B joins at daily lifecycle rows or first-trigger
dates, depending on the output.

| Input | Source | Join key | Lane A entry join | Lane B daily/trigger join | Caveats |
| --- | --- | --- | --- | --- | --- |
| Liquidity bucket | Phase 36 risk diagnostics / retained context | Symbol or trade context | Entry trade row | Trigger trade row or trade-level bucket | Static bucket, not historical ADV |
| Sector/static classification | `nse_eq_research_200_static_classification.csv` | Symbol | Entry trade symbol | Trade symbol | Partial/static mapping possible |
| Benchmark regime | Existing benchmark/NIFTY context path | Date | Signal/entry date | Holding/trigger date | Prior direct context filters failed |
| VIX regime/change | VIX source / Phase 36 logic | Date | Signal/entry date | Holding/trigger date | Secondary diagnostic only |
| Drawdown state | S2 state component or benchmark/risk context | Date and symbol/context | Entry state/context date | Holding/trigger date | Must avoid future data |
| Pre-entry gap | Trade/signal context or OHLC | Trade/date | Entry date | Trade-level only unless daily gap is added | Gap risk is mixed |
| Exit reason/gap exit | Retained trade/PnL logs | `trade_id` | Trade outcome | Trade outcome | Outcome-only diagnostic |
| Rolling R/recent realized performance | Completed prior trades only | Trade order/date | Prior completed trades before entry | Prior completed trades before trigger if used | High-overfit risk |
| Year | Trade/lifecycle date | Date | Entry year | Holding/trigger year | Year-only findings are fragile |
| Symbol | Retained trade logs | Symbol | Trade symbol | Trade symbol | Concentration must be flagged |

Explicit caveats:

- Liquidity is a static bucket, not historical ADV.
- Sector mapping may be partial/static.
- VIX is a secondary diagnostic, not a rule.
- Rolling R is high-overfit risk.
- Benchmark context filters previously failed as direct entry filters.
- Gap risk is mixed because target gaps are profitable and stop gaps are
  damaging.

## 11. Sample-Size / Stability Rules

All outputs must include sample size.

Bucket sample-size flags:

- `INSUFFICIENT`: fewer than 20 trades.
- `SMALL`: 20 to 49 trades.
- `USABLE`: 50 to 99 trades.
- `STRONG`: 100 or more trades.

Rules:

- No promotion from tiny buckets.
- Year-level stability is required before any future experiment.
- 2025-only improvement is fragile.
- Symbol-concentrated findings must be flagged.
- Small samples can suggest follow-up questions, not rules.

## 12. Output Folder and Files

Future output folder:

`reports/v2/s2_state_risk_intrade_full_audit_YYYYMMDD/`

Metadata:

- `s2_state_risk_intrade_audit_metadata.json`.
- `s2_state_risk_intrade_audit_readme.txt`.

Lane A outputs:

- `s2_entry_state_performance.csv`.
- `s2_entry_state_by_year.csv`.
- `s2_entry_state_by_liquidity.csv`.
- `s2_entry_state_by_benchmark_regime.csv`.
- `s2_entry_state_by_vix_regime.csv`.
- `s2_entry_state_by_drawdown_state.csv`.
- `s2_entry_state_by_gap_context.csv`.
- `s2_entry_state_by_exit_reason.csv`.
- `s2_state_risk_interaction_matrix.csv`.
- `s2_state_risk_sample_size_flags.csv`.

Lane B outputs:

- `s2_intrade_state_path_summary.csv`.
- `s2_deterioration_candidate_summary.csv`.
- `s2_deterioration_by_year.csv`.
- `s2_deterioration_by_liquidity.csv`.
- `s2_deterioration_by_benchmark_regime.csv`.
- `s2_deterioration_by_vix_regime.csv`.
- `s2_deterioration_by_exit_reason.csv`.
- `s2_deterioration_timing_summary.csv`.
- `s2_next_open_hypothetical_exit_summary.csv`.
- `s2_next_open_hypothetical_by_flag_year.csv`.
- `s2_winner_through_bad_state_audit.csv`.
- `s2_missed_target_vs_avoided_stop_audit.csv`.
- `s2_terminal_edge_case_audit.csv`.

Validation outputs:

- `s2_state_reconstruction_validation_summary.csv`.
- `s2_state_path_coverage_summary.csv`.
- `s2_same_day_exit_safety_summary.csv`.
- `s2_next_open_feasibility_summary.csv`.
- `s2_terminal_edge_case_audit.csv`.

Generated reports are not for commit unless explicitly approved.

## 13. Acceptance Criteria for Future Full Audit Helper

The future Phase 36K implementation can be considered successful only if:

- State reconstruction coverage remains high.
- Entry-state match remains high.
- Terminal edge cases are explicitly handled.
- Same-day safety failure count is 0.
- Next-open feasibility summary is produced.
- Lane A outputs are generated with sample sizes and R/PnL metrics.
- Lane B outputs are generated with candidate timing and hypothetical next-open
  audit metrics.
- All outputs are read-only diagnostics.
- No strategy behavior changes occur.

## 14. Decision Framework After Full Audit

Future Phase 36L scrutiny should choose one:

- `PROCEED_TO_PRE_REGISTERED_DYNAMIC_EXIT_EXPERIMENT_DESIGN`.
- `PROCEED_TO_ENTRY_STATE_RISK_FILTER_EXPERIMENT_DESIGN`.
- `PROCEED_TO_RISK_SIZING_EXPERIMENT_DESIGN`.
- `KEEP_AS_DIAGNOSTIC_ONLY`.
- `PARK_S2_STATE_INTRATRADE_BRANCH`.
- `REVISE_AUDIT_HELPER`.

Even after the full audit, no rule is approved automatically. Any future
experiment must be pre-registered.

## 15. Anti-Overfitting Guardrails

Guardrails:

- No PnL-optimized trigger selection.
- No threshold search.
- No symbol/year removal.
- No state exclusion from small samples.
- No combining many filters.
- No using 2025 alone to approve a fix.
- Report medians, not only averages.
- Report loser/winner pass-through for bad states.
- Report missed targets as well as avoided stops.
- Treat the full audit as evidence gathering only.

## 16. Future Implementation Skeleton

Suggested future module:

`src/veridian_quant/v2/analysis/s2_state_risk_intrade_audit.py`

Suggested runner:

`src/veridian_quant/v2/run_s2_state_risk_intrade_audit.py`

Suggested tests:

`tests/v2/test_s2_state_risk_intrade_audit.py`

Likely functions:

- `run_full_s2_state_risk_intrade_audit`.
- `build_entry_state_risk_frame`.
- `summarize_entry_state_performance`.
- `join_entry_risk_context`.
- `build_intrade_state_event_frame`.
- `summarize_deterioration_candidates`.
- `summarize_next_open_hypothetical_exits`.
- `summarize_winner_through_bad_state`.
- `summarize_terminal_edge_cases`.
- `apply_sample_size_flags`.
- `export_s2_state_risk_intrade_audit`.

## 17. Explicitly Not Approved

Phase 36J does not approve:

- Dynamic exits.
- `exit if RET_DOWN`.
- Entry filters.
- State exclusions.
- Risk filters.
- Liquidity filters.
- VIX, benchmark, or drawdown rules.
- Risk sizing changes.
- Production use.
- Strategy promotion.
- Backtest optimization.

## 18. Decision

`PROCEED_TO_36K_FULL_READ_ONLY_S2_STATE_RISK_INTRATRADE_AUDIT_IMPLEMENTATION`

---

## 19. Phase 36K Implementation Reference

Phase 36K implements the full read-only S2 State x Risk / In-Trade audit helper
described here.

Implementation:

- Source module:
  `src/veridian_quant/v2/analysis/s2_state_risk_intrade_audit.py`.
- CLI runner:
  `src/veridian_quant/v2/run_s2_state_risk_intrade_audit.py`.
- Focused synthetic tests:
  `tests/v2/test_s2_state_risk_intrade_audit.py`.

The helper reuses the Phase 36G reconstruction pipeline, builds Lane A
entry-state x risk frames and summaries, builds Lane B in-trade event frames
and summaries, and exports terminal-edge-case, same-day safety, next-open
feasibility, reconstruction validation, metadata, and readme outputs.

Phase 36K remains read-only diagnostics only. It does not run a strategy
backtest, implement a dynamic exit, create `exit if RET_DOWN`, add filters,
optimize thresholds, change S2 behavior, or approve production use.

Phase 36K decision:

`PROCEED_TO_36L_FULL_READ_ONLY_S2_STATE_RISK_INTRATRADE_AUDIT_RUN`
