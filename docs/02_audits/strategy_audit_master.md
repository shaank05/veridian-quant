# Strategy Audit Master

## Purpose

This document tracks the current audit status of Veridian Quant v2 strategy families, variants, and research directions.

No strategy is production-approved.

---

## Strategy Status Table

| Strategy / Component | Status | Implemented | Research Tested | Current Decision |
| --- | --- | --- | --- | --- |
| `S1_ZSCORE_MEAN_REVERSION` / `S1_BASELINE` | Current benchmark / research candidate | Yes | Yes | Keep as benchmark; do not promote to final production strategy |
| `S1_AVOID_MESSY_MIDDLE_V1` | Rejected / parked standalone filter variant | Yes | Yes | Do not promote; failed to generalize on broader universe |
| `S1_BROAD_BEST_GUESS` | Parked filter variant | Yes | Yes | Conservative, but did not beat the 200-symbol baseline |
| `candidate-ranking s1_v1` | Parked ranking experiment | Yes | Yes | Underperformed unranked baseline; do not promote |
| `S2_MARKOV_STATE_TRANSITION` safer benchmark | Frozen research benchmark | Yes | Yes | Retain `exclude_ret_down + ranking none`; not production-ready |
| `S2_MARKOV_STATE_TRANSITION` high-return candidate | Frozen research candidate | Yes | Yes | Retain `exclude_ret_down + clean_state_v1`; fragile due to 2025 |
| S2 guard/ranking variants | Rejected as benchmarks | Yes | Yes | Do not promote; improved targeted weakness but lost too much total edge |
| FFT strategy | Future research | No | No | Deferred; not an accepted production rule |
| Wavelet strategy | Future research | No | No | Deferred; not an accepted production rule |
| S1 ranking v2 | Future research / parked | No | No | Deferred until stronger evidence exists |
| S1/S2 voting layer | Future research | No | No | Deferred until strategy-family evidence improves |
| Meta-ranking / capital allocation layer | Future research | No | No | Deferred; not current behavior |

---

## Current Benchmark Evidence

### S1 Baseline

- Strategy: `S1_BASELINE`
- Universe: audited 200-symbol research universe
- Period: 2020-01-01 to 2026-04-30
- Net PnL: approximately +579K
- Gross profit: approximately +4.64M
- Gross loss: approximately -4.06M
- Profit factor: approximately 1.143
- Max drawdown: approximately 23.52%
- Trades: 535
- Total signals: 7,476
- Rejected signals: 6,941
- Portfolio capacity rejections: 6,726

Interpretation:

- S1 baseline is useful as a benchmark.
- S1 baseline is not production-ready.
- No S1 variant or ranking method currently supersedes the baseline.

### S2 Safer Benchmark

- Strategy: `S2_MARKOV_STATE_TRANSITION`
- `markov_signal_filter = exclude_ret_down`
- `s2_candidate_ranking = none`
- Net PnL: about Rs 9.72L
- CAGR: about 11.32%
- Max drawdown: about 24.04%
- Profit factor: about 1.189

Interpretation:

- Retain as the safer S2 benchmark.
- Better drawdown profile than the high-return S2 candidate.
- Not production-ready.

### S2 Higher-Return Research Candidate

- Strategy: `S2_MARKOV_STATE_TRANSITION`
- `markov_signal_filter = exclude_ret_down`
- `s2_candidate_ranking = clean_state_v1`
- Net PnL: about Rs 12.32L
- CAGR: about 13.52%
- Max drawdown: about 33.94%
- Profit factor: about 1.223
- 2025 PnL: about -Rs 7.50L

Interpretation:

- Retain as a higher-return S2 research candidate.
- Useful benchmark for future comparison.
- Not production-ready because of 2025 regime fragility and high drawdown.

---

## S2 Audit Findings

S2 has evidence of edge, but remains regime fragile.

The Phase 27H 2025 failure audit found:

- Failure was not driven by one symbol.
- Failure was not driven by one isolated crash month.
- Losses recurred across multiple 2025 months.
- Dominant bad pocket was `RET_UP + VOL_MID + DD_SHALLOW + not truly near lows`.
- Specific failed states were `RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW` and `RET_UP|VOL_MID|DD_SHALLOW|LOW_MID_RANGE`.
- Context failures included stock above SMA50, stock SMA50 slope positive, Nifty above SMA50, Nifty SMA50 slope positive, and shallow drawdown 0 to -5%.

Interpretation:

S2 was fooled by shallow bullish pullbacks that looked healthy but failed to mean-revert in 2025. Guard variants reduced the targeted pocket, but losses shifted to replacement candidates. The problem is broader than one simple state exclusion.

---

## Rejected S2 Variants

Rejected as benchmarks:

- `avoid_shallow_uptrend_pullback_v1`
- `exclude_ret_down + avoid_shallow_uptrend_pullback_v1`
- `exclude_ret_down + 2025_guard_v1`
- `exclude_ret_down + 2025_guard_v1 + signal-time context`

Reason:

Each variant addressed part of the 2025 problem, but reduced overall portfolio quality too much or failed to preserve the targeted improvement under the preferred filter context.

---

## Audit Rules

No strategy, variant, ranking method, or voting layer may be promoted solely because it looks attractive in a partial diagnostic.

Promotion requires:

- Standalone implementation evidence.
- Research-universe benchmark evidence.
- Robustness checks.
- Auditability.
- Clear separation between actual portfolio PnL and diagnostic-only counterfactual PnL.
- Regime fragility review.
- Portfolio capacity and accepted-trade-selection review.

Current decision:

- Freeze S2 research for now.
- Keep both retained S2 benchmarks for comparison.
- Move the next research effort to a new independent strategy.
