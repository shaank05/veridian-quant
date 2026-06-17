# Architecture Decision Records

## ADR-001 - S1 Remains Current Benchmark, Not Final Strategy

Date: 2026-06-14

Status: Accepted

Decision:

`S1_BASELINE` on the audited 200-symbol research universe remains the current Veridian Quant v2 benchmark.

Context:

S1 produced approximately +579K net PnL over 2020-01-01 to 2026-04-30 on the audited 200-symbol universe, with 535 trades and profit factor of approximately 1.143.

Consequence:

S1 is retained as the benchmark for future comparisons, but it is not considered final or production-ready.

---

## ADR-002 - Audited 200-Symbol Research Universe Is Main S1 Benchmark Universe

Date: 2026-06-14

Status: Accepted

Decision:

Use the audited 200-symbol research universe as the current main S1 benchmark universe.

Context:

The 200-symbol universe materially outperformed the 100-symbol universe.

Consequence:

Future S1 benchmark comparisons should use research200 unless a phase explicitly defines another universe.

---

## ADR-003 - S1 Variants Are Research Probes, Not Accepted Filters

Date: 2026-06-14

Status: Accepted

Decision:

Treat S1 hard-filter variants as research probes only.

Context:

S1 hard-filter variants did not generalize reliably. `S1_AVOID_MESSY_MIDDLE_V1` performed badly on the broader universe, and `S1_BROAD_BEST_GUESS` was conservative but did not outperform the 200-symbol baseline.

Consequence:

No S1 variant is promoted over `S1_BASELINE`.

---

## ADR-004 - S1 Candidate Ranking v1 Is Parked

Date: 2026-06-14

Status: Accepted

Decision:

Park `candidate-ranking s1_v1`.

Context:

The implementation was technically valid but underperformed the unranked S1 baseline.

Consequence:

No S1 ranking method is currently promoted over the unranked baseline. S1 ranking v2 is future work, not current behavior.

---

## ADR-005 - Counterfactual Rejected-Signal PnL Is Diagnostic Only

Date: 2026-06-14

Status: Accepted

Decision:

Counterfactual rejected-signal simulation must remain diagnostic only and must not be mixed into actual portfolio PnL.

Context:

All-signal opportunity diagnostics simulate capacity-rejected signals to evaluate opportunity quality and ranking hypotheses.

Consequence:

Counterfactual PnL does not update the ledger, does not consume capacity, and must not appear in actual portfolio performance metrics.

---

## ADR-006 - S2 Markov Is Standalone, Not an S1 Filter

Date: 2026-06-14

Status: Accepted

Decision:

Implement and evaluate `S2_MARKOV_STATE_TRANSITION` as a standalone strategy family.

Context:

S2 has been implemented but has not yet been benchmarked on the audited 200-symbol research universe.

Consequence:

S2 is not an S1 filter. S2 must be run independently before any S1/S2 combination is considered.

---

## ADR-007 - S1 and S2 Share Mechanics but Retain Separate Identity

Date: 2026-06-14

Status: Accepted

Decision:

S1 and S2 may share downstream setup, sizing, execution, exit resolution, PnL, ledger, and exporter components while retaining separate strategy identity.

Context:

Shared mechanics reduce duplication and preserve consistent portfolio accounting. Strategy-specific signal generation remains separate.

Consequence:

S1 and S2 can be compared under consistent mechanics without merging their signal logic.

---

## ADR-008 - Strategy Combination Is Future Work

Date: 2026-06-14

Status: Accepted

Decision:

Strategy combination, voting, meta-ranking, and capital allocation layers are future work and not current behavior.

Context:

S1 ranking v1 underperformed and S2 is now frozen as a benchmark/research candidate rather than a production strategy.

Consequence:

No S1/S2 voting layer, meta-ranking layer, FFT strategy, wavelet strategy, or defensive regime layer is accepted at this stage.

---

## ADR-009 - Freeze S2 Markov Research After Phase 27J

Date: 2026-06-17

Status: Accepted

Decision:

Freeze `S2_MARKOV_STATE_TRANSITION` research for now.

Retain:

- Safer benchmark: `exclude_ret_down + ranking none`
- Higher-return research candidate: `exclude_ret_down + clean_state_v1`

Context:

S2 has evidence of edge, but the Phase 27H-27J research cycle found material regime fragility. The high-return candidate suffered about -Rs 7.50L in 2025, with losses concentrated in shallow bullish-pullback states:

- `RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW`
- `RET_UP|VOL_MID|DD_SHALLOW|LOW_MID_RANGE`

Guard variants improved targeted 2025 damage but weakened total edge too much.

Consequence:

S2 remains a benchmark/research candidate, not a production strategy. The next alpha research effort should move to a new independent strategy family.

---

## ADR-010 - S2 Context and Failure Audit Are Research Infrastructure

Date: 2026-06-17

Status: Accepted

Decision:

Keep S2 failure-audit diagnostics and signal-time context enrichment as research infrastructure.

Context:

Phase 27H added S2 failure audit CSVs to identify state, symbol, exit reason, month, and context buckets where 2025 differed from pre-2025 behavior.

Phase 27J added signal-time stock/Nifty/relative-strength context metadata before S2 ranking and portfolio capacity decisions. This enrichment respects no-lookahead and is visible in signal logs.

Consequence:

These features improve auditability and future ranker research. They are not production trading logic and do not make S2 production-ready.
