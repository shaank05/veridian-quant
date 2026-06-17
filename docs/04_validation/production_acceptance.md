# Production Acceptance Notes

## Purpose

This document records whether current strategy candidates satisfy production acceptance expectations.

No Veridian Quant v2 strategy is production-approved.

---

## S1 Status

`S1_BASELINE` remains a research benchmark.

It is not production-ready.

Reason:

- It has positive benchmark evidence.
- It still requires broader production validation, operational controls, and robustness review.

---

## S2 Status

`S2_MARKOV_STATE_TRANSITION` is researched but not production-ready.

S2 has evidence of edge, but it does not pass production acceptance yet because:

- The higher-return candidate has high drawdown, about 33.94%.
- The higher-return candidate lost about Rs 7.50L in 2025.
- The safer benchmark has better drawdown but lower return and still requires robustness validation.
- 2025/2026 regime fragility remains unresolved.
- Guard variants improved targeted failure pockets but reduced total edge too much.

Retained S2 benchmark roles:

- `exclude_ret_down + ranking none`: safer S2 benchmark.
- `exclude_ret_down + clean_state_v1`: higher-return S2 research candidate.

Production decision:

- Do not deploy S2 live.
- Keep S2 as a benchmark/research candidate.
- Freeze S2 tuning while a new independent strategy is researched.

---

## Production Acceptance Rule

Attractive returns are not enough.

A strategy can move toward production only when:

- The edge is understood.
- Regime failure modes are documented.
- Drawdown is acceptable.
- Robustness is demonstrated.
- Portfolio capacity behavior is understood.
- Live operational controls are defined.

S2 currently fails the regime-fragility and drawdown acceptance checks.
