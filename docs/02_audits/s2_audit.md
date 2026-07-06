# S2 Audit — Markov State Transition

## Current Audit Decision

Strategy: `S2_MARKOV_STATE_TRANSITION`

Status:

- Researched through Phase 27J.
- Frozen / parked.
- Not production-ready.
- Retained as a benchmark/research candidate.
- Not discarded.
- Not accepted as a live trading rule.

S2 has evidence of edge but remains regime fragile.

The current audit decision is to keep S2 available for benchmark comparison and future research, but not to deploy it live or continue immediate S2-specific tuning.

---

## Phase 35B/35C Confirmation Closeout

Cross-strategy confirmation did not approve an S2 ensemble or S2 filter.

Phase 35B found that S2 confirmed trades were worse than S2 unconfirmed trades:

- S2 confirmed trades: 99 trades, about 0.893 PF, about -Rs 1.07L net PnL, and
  about 40.4% win rate.
- S2 unconfirmed trades: 478 trades, about 1.260 PF, about +Rs 10.79L net PnL,
  and about 46.2% win rate.
- Generic 2+ strategy confirmation was also weak: 16 trades, about 0.766 PF,
  and about -Rs 38.5K net PnL.

Phase 35C found that narrow S2/S4 confirmation stayed positive across tested
trading-session lookbacks, but did not become clean enough for implementation.
The 5-session result had 54 trades, about 1.23 PF, about +Rs 113.3K net PnL,
about 42.6% win rate, and about -Rs 7.66K median PnL. Yearly stability remained
weak, S2 fragile years were not fixed, and S3 became a competitive 5-session
control.

Decision:

- Broad voting ensemble: dropped.
- Generic 2+ consensus: dropped.
- S2/S4 confirmation: retained only as a parked diagnostic observation.
- No S2 ensemble, S2 allocation rule, S2 weight, or S2 production approval.

Detailed audit: `docs/02_audits/cross_strategy_overlap_audit.md`.

---

## Phase 36B/36C Risk Diagnostic Closeout

Cross-strategy risk diagnostics did not approve an S2 risk model, filter,
throttle, dynamic sizing rule, VIX rule, or production use.

Detailed audit: `docs/02_audits/cross_strategy_risk_diagnostic_audit.md`.

Key S2 findings:

- Liquidity is the strongest S2 risk diagnostic. HIGH liquidity had 271 trades,
  about Rs 970,422 net PnL, about 1.42 PF, about 49.45% win rate, and about
  -Rs 948 median PnL. LOW liquidity had about -Rs 26,697 net PnL and about
  0.96 PF. MID liquidity had about Rs 27,990 net PnL and about 1.01 PF.
- Benchmark regime remains a strong diagnostic. Strong-positive benchmark had
  127 trades, about Rs 660,713 net PnL, about 1.78 PF. Strong-negative had
  42 trades, about Rs 268,996 net PnL, about 2.11 PF. Ordinary negative had
  191 trades, about -Rs 94,265 net PnL, about 0.95 PF.
- Base gap risk is mixed. `STOP_GAP_HIT` had 35 trades and about -Rs 673,842
  net PnL, while `TARGET_GAP_HIT` had 31 trades and about +Rs 966,904 net PnL.
- India VIX joined to 2,740 / 2,740 retained S1-S5 trades with 100% coverage
  and 0 missing/null/nonpositive joined values.
- S2 low VIX had 210 trades, about Rs 654,183 net PnL, about 1.36 PF, and
  about 45.71% win rate. Mid VIX had 123 trades, about Rs 12,216 net PnL and
  about 1.01 PF. High VIX had 236 trades, about Rs 358,383 net PnL and about
  1.17 PF.
- S2 5D falling VIX had 262 trades, about Rs 762,307 net PnL, and about
  1.33 PF. S2 5D rising VIX had 303 trades, about Rs 262,844 net PnL, and
  about 1.10 PF.
- S2 high-VIX `STOP_GAP_HIT` had 19 trades and about -Rs 355,336 net PnL,
  while high-VIX `TARGET_GAP_HIT` had 17 trades and about +Rs 562,112 net PnL.
- S2 moderate drawdown + high VIX had 73 trades, about -Rs 80,885 net PnL,
  about 0.88 PF, about 45.21% win rate, and about -Rs 2,242 median PnL.
  Mild drawdown + mid VIX had 62 trades, about -Rs 135,157 net PnL, about
  0.80 PF, about 40.32% win rate, and about -Rs 9,998 median PnL.

Decision:

- Retain liquidity as the strongest S2 diagnostic.
- Retain VIX only as secondary market context.
- Retain VIX x drawdown only as a future pre-registration candidate.
- Do not pivot directly into S2-only implementation.
- Do not convert these diagnostics into rules without a new pre-registered
  design phase.

---

## Phase 36D State x Risk / In-Trade Diagnostic Design

Phase 36D creates a docs-only design for the next S2 diagnostic branch:
`docs/03_research/s2_state_risk_intrade_diagnostic_design.md`.

The design has two lanes:

- Lane A: Entry-State x Risk Input Diagnostic. Study which S2 entry states or
  components work or fail under liquidity, benchmark, drawdown, VIX, gap, year,
  and concentration contexts.
- Lane B: In-Trade State Evolution Diagnostic. Study whether open S2 trades
  deteriorate into bad Markov states before stop, target, or time stop, and
  whether a hypothetical next-open exit would have avoided losses or killed
  winners.

Decision:

- `PROCEED_TO_36E_STATE_METADATA_DISCOVERY`.
- No S2 rule is approved.
- No dynamic exit is approved.
- No `exit if RET_DOWN` rule is approved.
- No entry filter, state filter, risk filter, liquidity filter, VIX/drawdown/
  benchmark rule, risk sizing change, backtest implementation, or production
  behavior is approved.

---

## Phase 36E State Metadata / In-Trade Reconstruction Discovery

Phase 36E completed discovery for the Phase 36D diagnostic lanes:
`docs/03_research/s2_state_metadata_intrade_reconstruction_discovery.md`.

Findings:

- S2 state is built in
  `src/veridian_quant/v2/strategies/s2_markov_state_transition.py` by
  `build_state_frame`.
- Entry composite state metadata exists in retained `signal_log.csv` and
  `trade_signal_context.csv`.
- Existing parsing helpers can split `RET_*|VOL_*|DD_*|LOW_*` into state
  components.
- Trade logs, PnL logs, and trade-signal context share `trade_id`.
- Daily in-trade state paths are not stored in retained artifacts and require
  read-only reconstruction from OHLC.

Decision:

- Lane A Entry-State x Risk: `READY_WITH_MINOR_GAPS`.
- Lane B In-Trade State Evolution: `NEEDS_DAILY_STATE_RECONSTRUCTION`.
- Next selected gate:
  `PROCEED_TO_36F_STATE_RECONSTRUCTION_PROTOTYPE_DESIGN`.
- No diagnostic helper, backtest, report generation, dynamic exit, `exit if
  RET_DOWN` rule, entry filter, state exclusion, risk filter, sizing change,
  production use, or strategy promotion is approved.

---

## Phase 36F Daily State Reconstruction Prototype Design

Phase 36F designs the narrow future prototype needed before any full S2 state
risk / in-trade audit helper:
`docs/03_research/s2_daily_state_reconstruction_prototype_design.md`.

The design requires a future prototype to:

- Reconstruct daily S2 state rows from OHLC using the existing S2 state builder.
- Expand executed S2 trades into holding-period rows by `trade_id`.
- Join reconstructed state by symbol/date.
- Treat date-D state as known only after D close.
- Execute any hypothetical deterioration exit no earlier than the next session
  open.
- Exclude D-close state as actionable when the actual trade exited intraday on
  D.
- Validate reconstructed entry-state match rate against stored trade/signal
  metadata before any full audit helper.

Decision:

- `PROCEED_TO_36G_STATE_RECONSTRUCTION_PROTOTYPE_IMPLEMENTATION`.
- No full audit helper, backtest, report generation, dynamic exit, `exit if
  RET_DOWN`, entry filter, state exclusion, risk filter, sizing change,
  production use, or strategy promotion is approved.

---

## Phase 36G Daily State Reconstruction Prototype Implementation

Phase 36G implements the narrow read-only reconstruction prototype:
`src/veridian_quant/v2/analysis/s2_state_reconstruction.py`.

Implemented prototype capabilities:

- Load retained S2 executed-trade reports by `trade_id`.
- Parse `RET_*|VOL_*|DD_*|LOW_*` composite state labels.
- Reconstruct daily state frames through the existing S2 `build_state_frame`.
- Expand trades into entry-through-exit holding-date rows.
- Join reconstructed state by symbol/date without dropping missing rows.
- Validate stored entry-state metadata against reconstructed state.
- Treat actual exit dates as not actionable after close.
- Create diagnostic-only deterioration candidate flags.
- Identify first actionable deterioration occurrences.
- Assess next-open hypothetical exit feasibility without executing a rule.
- Summarize reconstruction coverage.

Decision:

- `PROCEED_TO_36H_STATE_RECONSTRUCTION_PROTOTYPE_RUN`.
- No full Lane A/B audit helper is approved yet.
- No S2 strategy behavior, dynamic exit, `exit if RET_DOWN`, entry filter,
  state exclusion, risk filter, sizing rule, threshold optimization, backtest,
  production behavior, or strategy promotion is approved.

---

## Phase 36H State Reconstruction Prototype Run

Phase 36H preflight is documented in:
`docs/03_research/s2_state_reconstruction_prototype_run.md`.

Retained S2 trade artifacts loaded successfully:

- Trades loaded: 577.
- Unique `trade_id` values: 577.
- Unique symbols: 146.
- Missing stored entry state labels: 0.

The reconstruction run did not proceed because the Phase 36G CLI requires a
caller-provided per-symbol OHLC CSV directory via `--ohlc-csv-dir`, and no such
directory was available in the workspace.

Decision:

- `FIX_OHLC_INPUT_AND_RERUN_36H`.
- No reconstruction coverage, entry-state match rate, deterioration
  candidates, or next-open feasibility outputs are available yet.
- No full Lane A/B audit helper is approved.
- No strategy backtest, S2 logic change, dynamic exit, `exit if RET_DOWN`,
  entry filter, state exclusion, risk filter, sizing rule, threshold
  optimization, production behavior, or strategy promotion is approved.

---

## Phase 36H.1 OHLC Input Fix / Prototype Rerun

Phase 36H.1 added a DB-backed OHLC input option to the reconstruction
prototype while preserving per-symbol CSV input support.

Implementation status:

- `--ohlc-source db` added to the prototype CLI.
- DB source uses existing `DatabaseClient` and `SQLAlchemyDailyOHLCVLoader`.
- Symbols and OHLC date window are inferred from retained trades.
- Focused tests passed: 17 tests.

Rerun status:

- The SQLAlchemy engine initialized.
- OHLC loading timed out connecting to the configured database at
  `34.14.156.222:5432`.
- The retry with elevated network permission failed with the same timeout.
- No prototype output folder was generated.

Decision:

- `REVISE_36H1_OHLC_INPUT_FIX`.
- Reconstruction coverage, entry-state match rate, deterioration candidates,
  and next-open feasibility remain unavailable.
- No full Lane A/B audit helper is approved.
- No strategy backtest, S2 logic change, dynamic exit, `exit if RET_DOWN`,
  entry filter, state exclusion, risk filter, sizing rule, threshold
  optimization, production behavior, or strategy promotion is approved.

---

## Strategy Summary

S2 is a standalone strategy family.

It is not an S1 filter.

S2 classifies each stock-day into Markov-style state labels using:

- Return state.
- Volatility state.
- Drawdown state.
- Low-distance state.

The strategy checks whether prior occurrences of the same state had favorable forward returns often enough to justify a long signal.

Signal generation uses no future data. A current state may only use information available through the signal date, and historical same-state examples are eligible only when their forward-return windows were already completed before the current signal date.

S2 shares downstream execution, sizing, exit, PnL, ledger, and exporter mechanics with S1. The shared mechanics make S1 and S2 comparable, but they do not make S2 an S1 variant.

---

## Retained Benchmarks

### Safer S2 Benchmark

Configuration:

- Strategy: `S2_MARKOV_STATE_TRANSITION`
- `markov_signal_filter = exclude_ret_down`
- `s2_candidate_ranking = none`

Approximate result:

- Trades: 577
- Net PnL: about Rs 9.72L
- CAGR: about 11.32%
- Max drawdown: about 24.04%
- Profit factor: about 1.189
- Win rate: about 45.23%

Role:

- Safer S2 benchmark.
- Better drawdown profile.
- Lower return than the high-return candidate.
- Retained for comparison only; not production-approved.

### Higher-Return S2 Research Candidate

Configuration:

- Strategy: `S2_MARKOV_STATE_TRANSITION`
- `markov_signal_filter = exclude_ret_down`
- `s2_candidate_ranking = clean_state_v1`

Approximate result:

- Trades: 583
- Net PnL: about Rs 12.32L
- CAGR: about 13.52%
- Max drawdown: about 33.94%
- Profit factor: about 1.223
- Win rate: about 47.68%
- 2025 PnL: about -Rs 7.50L

Role:

- Higher-return S2 research candidate.
- Useful benchmark.
- Fragile because of 2025 regime failure.

---

## Research Path

S2 explored:

- Raw Markov baseline.
- Markov state filters.
- Candidate ranking modes.
- Rejected/capacity counterfactual diagnostics.
- 2025 failure audit.
- 2025 guard ranking.
- Signal-time stock/Nifty/relative-strength context enrichment.

Later improvements helped explain S2's failure modes and produced reusable diagnostics, but they did not produce a better final S2 benchmark.

---

## Prior Improvement Variant Lessons

Phase 34B reconstructs prior S2 improvement-variant lessons so the current
project trail does not repeat already-tested guard, context, or state-exclusion
work.

Retained comparison baseline:

| Variant | Trades | Net PnL | PF | Max DD | Win rate | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `exclude_ret_down` | 577 | about Rs 9.72L | about 1.189 | about 24.04% | about 45.23% | retained safer benchmark |

Prior S2 improvement variants:

| Variant | Trades | Net PnL | PF | Max DD | Win rate | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `exclude_ret_down + 2025_guard_v1` | 564 | about Rs 5.65L | 1.133 | 26.87% | 45.04% | reject |
| `exclude_ret_down + 2025_guard_v1 + signal-time context` | 561 | about Rs 4.78L | 1.116 | 26.87% | 44.56% | reject |
| `exclude_ret_down + clean_state_v1` | 583 | about Rs 12.32L | 1.223 | 33.94% | 47.68% | fragile higher-return benchmark |
| `exclude_ret_down + avoid_shallow_uptrend_pullback_v1` | 573 | about Rs 11.10L | 1.185 | 37.42% | 46.07% | reject |

Variant lessons:

- `2025_guard_v1` cut net PnL by about Rs 4.06L versus the safer baseline,
  worsened profit factor and drawdown, and did not meaningfully fix 2025.
- `2025_guard_v1 + signal-time context` was worse than both the retained
  baseline and the pure 2025 guard, confirming that threshold/context tweaking
  was not the answer.
- `clean_state_v1` improved PnL, profit factor, and R-style quality metrics,
  but worsened drawdown badly and made 2025 severely negative. It remains only
  a fragile higher-return benchmark.
- `avoid_shallow_uptrend_pullback_v1` improved final PnL but worsened profit
  factor, sharply worsened drawdown, and made 2025/2026 behavior worse.

Frozen cross-variant lesson:

S2 cannot be rescued by simple guards, direct 2025-specific rules,
shallow-pullback bans, or simple state exclusions. Direct fixes either destroy
too much edge or move risk into worse drawdown and year fragility. The deeper
problem remains state/regime non-stationarity plus broad stop-churn during
fragile periods.

Overfitting cautions:

- Do not remove months, symbols, sectors, or state labels directly from these
  reports.
- Do not optimize by final PnL.
- Do not treat 2025-specific failures as production rules.
- Do not continue threshold-tweaking the same context or guard filters.
- Do not promote higher-PnL variants when profit factor, drawdown, or yearly
  fragility worsens.
- Future S2 work needs a genuinely new hypothesis, not a renamed version of
  these failed guards.

Current Phase 34B status:

- `exclude_ret_down` remains the retained safer S2 benchmark.
- `clean_state_v1` remains only a fragile higher-return benchmark.
- No prior S2 variant is production-approved.
- Phase 34A existing-report scrutiny reconstructed the failure mode as
  regime/state non-stationarity plus broad stop-churn during fragile periods.
- Phase 34A.0 found existing S2 failure-audit tooling and reports, so no new
  failure-audit code is currently needed.

---

## Rejected S2 Benchmark Variants

The following variants are rejected as S2 benchmarks:

- `avoid_shallow_uptrend_pullback_v1`
- `exclude_ret_down + avoid_shallow_uptrend_pullback_v1`
- `exclude_ret_down + 2025_guard_v1`
- `exclude_ret_down + 2025_guard_v1 + signal-time context`

Reasons:

- `avoid_shallow_uptrend_pullback_v1` reduced 2025 damage when used alone, but weakened total profitability too much.
- `exclude_ret_down + avoid_shallow_uptrend_pullback_v1` increased drawdown and did not preserve the 2025 fix.
- `exclude_ret_down + 2025_guard_v1` improved 2025 but reduced total PnL too much.
- `exclude_ret_down + 2025_guard_v1 + signal-time context` proved Phase 27J infrastructure worked, but final result remained weak: about Rs 4.78L net PnL, about 6.37% CAGR, about 26.87% max drawdown, about 1.116 PF, and 2025 improved to about -Rs 156K while too much total edge was lost.

---

## 2025 Failure Audit

The 2025 failure was not caused by one symbol.

It was not one isolated crash month.

Losses recurred across multiple months.

Dominant failure pocket:

`RET_UP + VOL_MID + DD_SHALLOW + not truly near lows`

Specific failed states:

- `RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW`
- `RET_UP|VOL_MID|DD_SHALLOW|LOW_MID_RANGE`

Context failure:

- Stock above SMA50.
- Stock SMA50 slope positive.
- Nifty above SMA50.
- Nifty SMA50 slope positive.
- Shallow drawdown 0 to -5%.

Interpretation:

S2 was fooled by shallow bullish pullbacks that looked healthy but failed to mean-revert in 2025. Guard variants reduced targeted failure pockets, but losses shifted to replacement candidates. The problem is broader than one simple state exclusion.

---

## Capacity and Ranking Audit

S2 produced far more signals than the portfolio could accept.

Portfolio capacity rejection dominated.

Candidate ranking materially changed results.

Capacity-rejected pools often remained profitable counterfactually, but counterfactual rejected-signal PnL is diagnostic only. It is not achievable portfolio PnL because it ignores capacity, ledger effects, and actual capital allocation.

S2 has signal supply, but accepted-trade selection remains fragile.

S2-specific ranking tuning reached diminishing returns after Phase 27J.

---

## Production Readiness

S2 is not production-ready because:

- The higher-return candidate has high drawdown, about 33.94%.
- 2025/2026 regime fragility remains.
- The high-return candidate lost about -Rs 7.50L in 2025.
- Guard variants did not solve the regime problem without damaging total edge.
- Capacity/ranking selection remains fragile.

Production decision:

- Do not deploy S2 live.
- Keep S2 as a benchmark/research candidate only.

---

## Infrastructure Produced

The S2 research cycle produced reusable research infrastructure:

- S2 Markov signal generator.
- S2 Markov filter simulation reports.
- Candidate ranking mode framework.
- All-signal / rejected capacity diagnostics.
- 2025 failure audit reports.
- Signal-time context enrichment.
- Expanded signal log metadata for stock/Nifty/relative-strength context.

These are research infrastructure. They can support future strategies and rankers, but they do not make S2 production-ready.

---

## Final Audit Decision

Decision:

- Freeze S2 research for now.
- Retain `exclude_ret_down + ranking none` as the safer S2 benchmark.
- Retain `exclude_ret_down + clean_state_v1` as the higher-return research candidate.
- Reject guard/ranking variants as benchmarks.
- Retain S2/S4 confirmation only as a diagnostic observation, not an S2
  implementation path.
- Retain Phase 36D entry-state x risk and in-trade state evolution work as a
  diagnostic design only; proceed next to metadata/reconstruction discovery.
- Retain Phase 36E as discovery-only; proceed next to read-only daily state
  reconstruction prototype design before any audit helper.
- Retain Phase 36F as docs/design only; proceed next only to the narrow
  read-only state reconstruction prototype implementation.
- Do not continue immediate S2 tuning.
- Move any next S2 work through explicit discovery/design gates rather than a
  voting variant, simple context threshold, state exclusion, or immediate
  implementation.

Rationale:

- S2 has evidence of edge.
- Additional S2 tuning produced diminishing returns.
- 2025/2026 fragility remains unresolved.
- Better to diversify research toward a different alpha source.

---

## Parked Future Work

- S2 regime-aware exposure reduction.
- Better market-regime detector.
- More robust capacity-aware ranking.
- Use Phase 27J signal-time context infrastructure in future rankers.
- Potential S2 revisit after broader independent strategy comparison or materially new regime/ranking infrastructure.
- Phase 36G S2 state reconstruction prototype implementation.
- Sector/industry conditioning if metadata becomes available.
- Symbol-level robustness filters after broader strategy comparison.
