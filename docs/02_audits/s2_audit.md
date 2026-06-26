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
- Do not continue immediate S2 tuning.
- Move next research to a new independent strategy.

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
- Sector/industry conditioning if metadata becomes available.
- Symbol-level robustness filters after broader strategy comparison.
