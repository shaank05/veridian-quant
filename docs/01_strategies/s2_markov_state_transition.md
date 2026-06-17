# S2 - Markov State Transition

## Current Decision

Status:

- Researched through Phase 27J.
- Evidence of edge exists.
- Retained as benchmark/research candidate.
- Frozen / parked.
- Not production-ready.
- Not accepted as a live trading rule.

S2 should not be described as failed or useless. It found useful edge and useful infrastructure. The current conclusion is that S2 remains too regime-fragile for production and should be parked while the project explores a new independent alpha source.

---

## Purpose

S2 tests whether simple, explainable market states have historically led to favorable forward outcomes.

For each symbol, each trading day is classified into a discrete state using only information available through that day. The strategy then checks whether prior occurrences of the same state had favorable future returns.

S2 is a standalone strategy family.

It is not an S1 filter.

---

## Strategy Identifier

`S2_MARKOV_STATE_TRANSITION`

---

## Strategy Hypothesis

Market state recurrence may contain useful information about short-horizon forward returns.

The strategy asks:

> If a stock is in a current return/volatility/drawdown/low-distance state, have prior occurrences of that same state produced favorable forward returns often enough to justify a long trade?

The hypothesis is regime-dependent. It can work in some market periods and fail when state labels describe conditions that are superficially healthy but structurally fragile.

---

## State Label Format

State labels use this format:

`RET_*|VOL_*|DD_*|LOW_*`

Example:

`RET_DOWN|VOL_MID|DD_MID|LOW_NEAR`

State dimensions:

- Five-session return bucket: `RET_STRONG_DOWN`, `RET_DOWN`, `RET_FLAT`, `RET_UP`, `RET_STRONG_UP`
- ATR percent volatility bucket: `VOL_LOW`, `VOL_MID`, `VOL_HIGH`
- Sixty-session drawdown bucket: `DD_SHALLOW`, `DD_MID`, `DD_DEEP`
- Distance from sixty-session low bucket: `LOW_NEAR`, `LOW_MID_RANGE`, `LOW_FAR_FROM_LOW`

---

## Markov Transition Logic

For a current signal-date candidate:

1. Build the current state label using data available through the current row only.
2. Look back over prior rows inside the configured state lookback window.
3. Keep only prior rows with the same state label.
4. A prior row is eligible only if its forward-return window is fully completed before the current row.
5. Calculate prior same-state forward returns.
6. Generate a long signal only if same-state statistics pass the configured thresholds.

No future leakage is allowed.

Future prices after the signal date may only be used later by normal trade exit resolution, exactly as with other backtest trades.

---

## Default Parameters

- State lookback sessions: 252
- Minimum state observations: 10
- Forward return sessions: 10
- Positive return threshold: 3%
- Probability threshold: 60%
- Average forward return threshold: 1%

Signal condition:

- Same-state observation count >= 10
- Probability of forward return >= +3% is >= 60%
- Average forward return is >= +1%

---

## Signal Metadata and Context

Core S2 signals record:

- `strategy_family`
- `state_label`
- `state_lookback_sessions`
- `state_observation_count`
- `forward_return_sessions`
- `positive_return_threshold_pct`
- `positive_transition_probability`
- `average_forward_return_pct`
- `median_forward_return_pct`
- `current_5d_return_pct`
- `current_atr_pct`
- `current_drawdown_60d_pct`
- `current_close_vs_60d_low_pct`

Phase 27J added signal-time context enrichment before S2 ranking and capacity decisions:

- Stock trend, return, drawdown, low-distance, ATR, and consecutive-down-close fields.
- Nifty trend and return fields when Nifty data is available.
- Stock-vs-Nifty relative strength fields when both stock and Nifty context are available.

This enrichment is infrastructure. It respects no-lookahead by using only rows on or before the signal date. It did not by itself produce a superior S2 benchmark.

---

## Entry, Exit, and Risk Mechanics

S2 uses the same downstream portfolio mechanics as S1:

- Entry: next session open after signal
- Stop: ATR-based
- ATR window: 14
- ATR multiplier: 2
- Reward:risk: 2
- Max holding period: 20 sessions
- Round-trip cost: 0.004
- Risk per trade: 1%
- Default max concurrent positions: 5

These mechanics are shared research infrastructure. They do not imply that S2 has the same edge as S1.

---

## Final Retained Benchmarks

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
- Fragile due to 2025 regime failure.

---

## Rejected S2 Variants

The following are rejected as S2 benchmarks:

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

## 2025 Failure Audit Summary

The 2025 failure in the high-return S2 candidate was not caused by one symbol or one isolated crash month.

It was a recurring regime issue across multiple months.

Dominant bad pocket:

`RET_UP + VOL_MID + DD_SHALLOW + not truly near lows`

Specific failed states:

- `RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW`
- `RET_UP|VOL_MID|DD_SHALLOW|LOW_MID_RANGE`

These two states explained a large share of the audit-basis 2025 loss.

Context failure:

- Stock above SMA50.
- Stock SMA50 slope positive.
- Nifty above SMA50.
- Nifty SMA50 slope positive.
- Shallow drawdown 0 to -5%.

Interpretation:

S2 was fooled by shallow bullish pullbacks that looked healthy but failed to mean-revert in 2025. Later guard variants reduced the targeted pocket, but losses shifted to replacement candidates. Therefore the problem is broader than one simple state exclusion.

---

## Capacity and Ranking Conclusion

S2 produced many more signals than the portfolio could accept.

Portfolio capacity rejection dominated.

Candidate ranking is a major bottleneck:

- Accepted-trade selection materially changes S2 performance.
- Rejected capacity pools often remained profitable counterfactually.
- S2 has signal supply, but accepted-trade selection remains fragile.

This supports future capacity-aware ranking research, but S2-specific ranking tuning has reached diminishing returns for now.

---

## Known Weaknesses

- Regime fragility, especially around 2025/2026.
- High-return candidate has drawdown too high for production acceptance.
- 2025 losses are recurring across months, not isolated.
- Simple state/ranking guards can reduce one failure pocket while pushing capacity into weaker replacement trades.
- No sector/industry conditioning is currently available.
- Candidate ranking remains fragile under capacity constraints.

---

## Parked / Future Work

Future S2 work is parked until additional independent strategy evidence or a materially new regime/ranking framework creates a reason to revisit it.

Potential future work:

- S2 regime-aware exposure reduction.
- Better market-regime detector.
- More robust capacity-aware ranking.
- Use Phase 27J signal-time context infrastructure in future rankers.
- Potential S2 revisit after broader independent strategy comparison or materially new regime/ranking infrastructure.
- Sector/industry conditioning if metadata becomes available.
- Symbol-level robustness filters after broader strategy comparison.

No combination with S1 should be introduced merely because S2 has evidence of edge. Any combination must have separate portfolio-level evidence.
