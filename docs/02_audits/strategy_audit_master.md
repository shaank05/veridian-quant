# Strategy Audit Master

## Purpose

This document tracks the current audit status of Veridian Quant v2 strategy families, variants, and research directions.

Only S1 baseline currently has benchmark evidence on the audited 200-symbol research universe.

---

## Strategy Status Table

| Strategy / Component | Status | Implemented | Research200 Tested | Current Decision |
| --- | --- | --- | --- | --- |
| `S1_ZSCORE_MEAN_REVERSION` / `S1_BASELINE` | Current benchmark / research candidate | Yes | Yes | Keep as benchmark; do not promote to final production strategy |
| `S1_AVOID_MESSY_MIDDLE_V1` | Rejected / parked standalone filter variant | Yes | Yes | Do not promote; failed to generalize on broader universe |
| `S1_BROAD_BEST_GUESS` | Parked filter variant | Yes | Yes | Conservative, but did not beat the 200-symbol baseline |
| `candidate-ranking s1_v1` | Parked ranking experiment | Yes | Yes | Underperformed unranked baseline; do not promote |
| `S2_MARKOV_STATE_TRANSITION` | Implemented, not benchmarked | Yes | No | Run independently before any combination with S1 |
| FFT strategy | Future research | No | No | Deferred; not an accepted production rule |
| Wavelet strategy | Future research | No | No | Deferred; not an accepted production rule |
| S1 ranking v2 | Future research / parked | No | No | Deferred until stronger evidence exists |
| S1/S2 voting layer | Future research | No | No | Deferred until S2 has standalone evidence |
| Meta-ranking / capital allocation layer | Future research | No | No | Deferred; not current behavior |

---

## Current Benchmark Evidence

Current benchmark:

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

---

## Audit Rules

No strategy, variant, ranking method, or voting layer may be promoted solely because it looks attractive in a partial diagnostic.

Promotion requires:

- Standalone implementation evidence
- Research-universe benchmark evidence
- Robustness checks
- Auditability
- Clear separation between actual portfolio PnL and diagnostic-only counterfactual PnL

S2 must be benchmarked independently before any S1/S2 combination is considered.
