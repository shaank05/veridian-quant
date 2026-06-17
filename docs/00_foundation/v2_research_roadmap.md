# Veridian Quant v2 Research Roadmap

## Current Research State

Veridian Quant v2 has completed the S1 baseline cycle and the S2 Markov research cycle through Phase 27J.

Current retained research benchmarks:

- `S1_BASELINE` remains the original v2 mean-reversion benchmark.
- `S2_MARKOV_STATE_TRANSITION` is retained as a benchmark/research candidate, but is frozen and not production-ready.

S2 has evidence of edge, but the research cycle found material regime fragility, especially around the 2025/2026 period. S2 should not be deployed live. It should remain available for comparison against future independent strategies.

---

## Completed Phases

### Phase 1-22: S1 Foundation and Portfolio Backtesting

Implemented the v2 S1 Z-score mean-reversion baseline, reusable trade setup, sizing, execution, exit resolution, PnL, ledger, exporters, and core diagnostics.

### Phase 23: S1 Filter Variants

Implemented S1 hard-filter variants to test whether signal-date context could improve baseline mean reversion.

Outcome:

- Variants were useful research probes.
- Hard filters did not generalize reliably across the broader research universe.

### Phase 24: Strategy Variant Comparison Reports

Added reporting to compare S1 variants across summary metrics, yearly performance, exit reasons, rejection reasons, symbol concentration, and derived deltas.

Outcome:

- Broader reporting made variant fragility easier to detect.
- The comparison framework remains useful for future strategy families.

### Phase 25A-25F: Data, Ingestion, Quality, and Research Universe

Added v2 price ingestion, resumable network recovery, price quality audits, raw NSE equity candidate construction, audited research universe construction, and 100-vs-200 universe comparison.

Outcome:

- The audited 200-symbol S1 baseline materially outperformed the audited 100-symbol baseline.
- Universe breadth and data quality are now core research controls.

### Phase 26A: Capacity-Aware Candidate Ranking v1

Implemented `candidate-ranking s1_v1` to rank same-day S1 candidates under portfolio capacity constraints.

Outcome:

- The ranking implementation was technically valid.
- It underperformed the unranked `S1_BASELINE`.
- S1 ranking optimization is parked until stronger evidence exists.

### Phase 26B: All-Signal Opportunity Diagnostics and Counterfactual Rejected-Signal Simulation

Added diagnostics for all generated signals, accepted trades, rejected signals, capacity rejections, same-day pools, and counterfactual outcomes for rejected capacity signals.

Outcome:

- S1 generates far more valid signals than the portfolio can take.
- Capacity rejections are the dominant rejection reason.
- Counterfactual rejected-signal PnL is diagnostic only and must not be treated as actual portfolio PnL.
- These diagnostics support future ranking and voting research.

### Phase 27A-27J: S2 Markov State Transition Research Cycle

Implemented and researched `S2_MARKOV_STATE_TRANSITION` as a standalone strategy family.

Explored:

- Raw S2 Markov baseline.
- Markov state filters.
- S2 candidate ranking modes.
- Rejected/capacity counterfactual diagnostics.
- 2025 failure audit diagnostics.
- 2025 guard ranking.
- Signal-time stock/Nifty/relative-strength context enrichment for S2 ranking.

Outcome:

- S2 has evidence of edge.
- S2 is not discarded.
- S2 is not production-ready because of regime fragility, especially in 2025/2026.
- S2 research is frozen for now.
- The next research effort should move to a new independent strategy rather than continue tuning S2 immediately.

---

## Retained S2 Benchmarks

### Safer S2 Benchmark

Configuration:

- Strategy: `S2_MARKOV_STATE_TRANSITION`
- `markov_signal_filter = exclude_ret_down`
- `s2_candidate_ranking = none`

Approximate result:

- Net PnL: about Rs 9.72L
- CAGR: about 11.32%
- Max drawdown: about 24.04%
- Profit factor: about 1.189

Role:

- Safer S2 benchmark.
- Better drawdown profile.
- Lower return than the high-return candidate.

### Higher-Return S2 Research Candidate

Configuration:

- Strategy: `S2_MARKOV_STATE_TRANSITION`
- `markov_signal_filter = exclude_ret_down`
- `s2_candidate_ranking = clean_state_v1`

Approximate result:

- Net PnL: about Rs 12.32L
- CAGR: about 13.52%
- Max drawdown: about 33.94%
- Profit factor: about 1.223
- 2025 PnL: about -Rs 7.50L

Role:

- Higher-return S2 research candidate.
- Useful benchmark.
- Fragile because of 2025 regime failure.

---

## S2 Rejected Variants

The following variants are rejected as S2 benchmarks:

- `avoid_shallow_uptrend_pullback_v1`
- `exclude_ret_down + avoid_shallow_uptrend_pullback_v1`
- `exclude_ret_down + 2025_guard_v1`
- `exclude_ret_down + 2025_guard_v1 + signal-time context`

Reasons:

- `avoid_shallow_uptrend_pullback_v1` reduced 2025 damage when used alone, but weakened total profitability too much.
- `exclude_ret_down + avoid_shallow_uptrend_pullback_v1` increased drawdown and did not preserve the 2025 fix.
- `exclude_ret_down + 2025_guard_v1` improved 2025 but reduced total PnL too much.
- `exclude_ret_down + 2025_guard_v1 + signal-time context` proved Phase 27J infrastructure worked, but the final result remained weak: about Rs 4.78L net PnL, about 6.37% CAGR, about 26.87% max drawdown, about 1.116 PF, and 2025 improved to about -Rs 156K while too much total edge was lost.

---

## Active Research Position

The current evidence says:

- S1 has positive benchmark evidence on the audited 200-symbol research universe.
- S1 is useful as a benchmark, not as a final production strategy.
- S2 has evidence of edge, but remains regime fragile.
- S2 is retained as a benchmark/research candidate, not deployed live.
- Portfolio capacity and accepted-trade selection remain major bottlenecks.
- Additional S2 tuning has reached diminishing returns.

Next direction:

- Move to a new independent strategy, likely S3 trend pullback continuation or another non-S2 alpha source.
- Do not continue immediate S2 tuning unless a later independent strategy comparison creates a specific reason to revisit S2.

---

## Parked / Future Work

The following are future research directions, not accepted production rules:

- S2 regime-aware exposure reduction.
- Better market-regime detector.
- More robust capacity-aware ranking.
- Use Phase 27J signal-time context infrastructure in future rankers.
- Potential S2 revisit after S3/S4 strategies are explored.
- Sector/industry conditioning if metadata becomes available.
- Symbol-level robustness filters after broader strategy comparison.
- S1 candidate ranking v2.
- FFT strategy.
- Wavelet strategy.
- Markov/S1 voting layer.
- Meta-ranking / capital allocation layer.

These ideas may be researched later only after standalone evidence and auditability requirements are satisfied.
