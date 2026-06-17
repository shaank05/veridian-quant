# Rejected and Parked Research Ideas

## Purpose

This document records ideas that were tested and rejected, or deliberately parked, so they are not rediscovered as if they were new.

Rejected here means rejected as a benchmark or production candidate. It does not necessarily mean the idea has no research value.

---

## S1 Rejected / Parked Items

- `S1_AVOID_MESSY_MIDDLE_V1`: rejected as a promoted filter because it failed to generalize on the broader research universe.
- `S1_BROAD_BEST_GUESS`: parked because it was conservative but did not beat the 200-symbol baseline.
- `candidate-ranking s1_v1`: parked because it was technically valid but underperformed the unranked S1 baseline.

---

## S2 Rejected Benchmark Variants

The following S2 variants are rejected as benchmarks:

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

## S2 Parked, Not Rejected Entirely

`S2_MARKOV_STATE_TRANSITION` itself is not rejected.

Current S2 decision:

- Retain `exclude_ret_down + ranking none` as safer S2 benchmark.
- Retain `exclude_ret_down + clean_state_v1` as higher-return research candidate.
- Freeze S2 research for now.
- Do not continue immediate S2 tuning.
- Move to a new independent strategy.

Reason:

S2 has evidence of edge, but remains regime fragile and not production-ready.

---

## S3 Rejected / Parked Items

`S3_TREND_PULLBACK_CONTINUATION` is technically valid but parked as a standalone strategy family.

Rejected as production candidates:

- `S3_TREND_PULLBACK_CONTINUATION_BASELINE`: weak edge, about 1.045 PF, about 31.61% max drawdown.
- `S3_STRONG_TREND_V1`: strong SMA200 slope alone worsened results versus baseline.
- `S3_ABOVE_SMA50_V1`: improved over baseline, but remained too weak as a standalone production candidate.
- `S3_CONTROLLED_PULLBACK_V1`: reduced signals but did not improve realized portfolio performance; drawdown worsened versus the retained S3 benchmark.

Benchmark-only:

- `S3_STRONG_TREND_ABOVE_SMA50_V1`: retained as the S3 benchmark, but rejected as a production candidate. Approximate result: about Rs 3.16L net PnL, about 1.104 PF, about 28.20% max drawdown.

Current S3 decision:

- Freeze S3 standalone research.
- Do not continue near-term S3 variants.
- Revisit only if regime modeling, ranking/capacity logic, sector/relative-strength features, or ensemble needs materially change.

---

## Deferred Advanced Strategy Families

The following remain future research directions:

- FFT strategy.
- Wavelet strategy.
- S1/S2 voting layer.
- Meta-ranking / capital allocation layer.

These are not accepted production rules.
