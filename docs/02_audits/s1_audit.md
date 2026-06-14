# S1 Strategy Audit

## Current Audit Status

S1 Z-score mean reversion is implemented and remains the current Veridian Quant v2 benchmark.

Audit status:

- Implemented
- Backtested on audited 100-symbol and 200-symbol research universes
- Current benchmark: `S1_BASELINE` on the audited 200-symbol research universe
- Research candidate / benchmark
- Not a final production strategy

---

## Current Benchmark

Benchmark configuration:

- Strategy: `S1_BASELINE`
- Universe: audited 200-symbol research universe
- Period: 2020-01-01 to 2026-04-30

Approximate benchmark results:

- Net PnL: +579K
- Gross profit: +4.64M
- Gross loss: -4.06M
- Profit factor: 1.143
- Max drawdown: 23.52%
- Trades: 535
- Total signals: 7,476
- Rejected signals: 6,941
- Portfolio capacity rejections: 6,726

These results are research evidence. They are not production validation.

---

## Key Findings

### Universe Breadth

The audited 200-symbol universe materially outperformed the audited 100-symbol universe.

Current interpretation:

- Broader opportunity coverage improved S1 portfolio performance.
- Universe construction and data quality are material to S1 results.
- The 200-symbol audited research universe is the current main S1 benchmark universe.

### Hard-Filter Variants

S1 hard-filter variants did not generalize reliably on the broader universe.

Specific findings:

- `S1_AVOID_MESSY_MIDDLE_V1` performed badly on the broader universe despite earlier promise.
- `S1_BROAD_BEST_GUESS` was conservative but did not outperform the 200-symbol baseline.

Audit interpretation:

- Hard filters remain useful as research probes.
- No S1 filter variant is currently accepted as a production filter.
- Do not promote any S1 variant over `S1_BASELINE` yet.

### Candidate Ranking

`candidate-ranking s1_v1` was technically valid but underperformed the unranked S1 baseline.

Audit interpretation:

- S1 candidate ranking v1 is parked.
- S1 ranking v2 should not be pursued until there is stronger evidence from all-signal diagnostics, feature-combination analysis, or independent strategy-family results.
- No S1 ranking method is currently promoted over the unranked baseline.

### Portfolio Capacity

Capacity is a central S1 bottleneck.

Evidence:

- Total signals: 7,476
- Rejected signals: 6,941
- Portfolio capacity rejections: 6,726

All-signal opportunity diagnostics show that rejected capacity signals contain hidden winners, but the average rejected capacity signal has weak edge.

Audit interpretation:

- Signal generation alone is not the only research problem.
- Opportunity selection under portfolio capacity constraints is now a core open question.
- Counterfactual rejected-signal PnL is diagnostic only and must not be treated as actual portfolio PnL.

---

## Audit Conclusion

S1 remains the current benchmark strategy for Veridian Quant v2.

S1 is not final.

Do not promote:

- Any S1 hard-filter variant
- `candidate-ranking s1_v1`
- Counterfactual rejected-signal outcomes as actual portfolio performance

Parked S1 work:

- S1 candidate ranking v2
- Feature-combination diagnostics
- Evidence-based voting or scoring systems

Next valid research direction:

- Benchmark standalone S2 independently before considering any S1/S2 voting, meta-ranking, or capital allocation layer.
