# Portfolio Construction Research Notes

## Purpose

This document records portfolio-level research findings that are not specific to one signal formula.

---

## Capacity Is a Central Bottleneck

Both S1 and S2 generate more valid signals than the portfolio can accept under the current maximum-concurrent-position constraint.

Implications:

- Accepted-trade selection materially affects portfolio results.
- Rejected capacity pools can contain profitable trades.
- Counterfactual rejected-signal PnL is useful diagnostically, but it is not actual achievable portfolio PnL.
- Ranking methods must be evaluated at the portfolio level, not only at the individual-signal level.

---

## S2 Capacity and Ranking Conclusion

S2 produced substantial signal supply, but capacity rejection dominated.

The best higher-return S2 research candidate was:

- `S2_MARKOV_STATE_TRANSITION`
- `markov_signal_filter = exclude_ret_down`
- `s2_candidate_ranking = clean_state_v1`

Approximate result:

- Net PnL: about Rs 12.32L
- CAGR: about 13.52%
- Max drawdown: about 33.94%
- Profit factor: about 1.223
- 2025 PnL: about -Rs 7.50L

Capacity conclusion:

- Candidate ranking is a major bottleneck.
- Rejected capacity pools often remained profitable counterfactually.
- S2 has signal supply, but accepted-trade selection remains fragile.
- Later ranking/guard variants reduced targeted failure pockets but shifted capacity toward weaker replacement candidates.

---

## Current Portfolio Research Decision

Do not keep tuning S2 ranking immediately.

Reason:

- Additional S2 ranking/guard variants produced diminishing returns.
- The 2025/2026 fragility appears broader than one simple state or context exclusion.
- A new independent alpha source is more valuable than further S2 micro-optimization.

Future portfolio construction work:

- More robust capacity-aware ranking.
- Meta-ranking across independently validated strategies.
- Regime-aware exposure reduction.
- Use Phase 27J signal-time context infrastructure in future rankers.
- Sector/industry conditioning if reliable metadata becomes available.
