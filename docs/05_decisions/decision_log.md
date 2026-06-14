# Decision Log

This log records major research and architecture decisions for Veridian Quant v2.

---

## 2026-06-14 - Expand From Narrow Universe to Audited Research Universes

Decision:

Move beyond the narrow initial universe and use audited 100-symbol and 200-symbol research universes for S1 evaluation.

Reason:

The initial narrow universe was not enough evidence for broader strategy conclusions.

Consequence:

Research universe construction and data quality audit became part of the standard validation workflow.

---

## 2026-06-14 - Use Research200 S1 Baseline as Current Benchmark

Decision:

Use `S1_BASELINE` on the audited 200-symbol research universe as the current benchmark.

Benchmark:

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

Consequence:

S1 baseline remains the comparison point for future strategy families, but is not final or production-ready.

---

## 2026-06-14 - Reject / Park Hard S1 Filters After Broader-Universe Results

Decision:

Do not promote hard S1 filter variants.

Reason:

S1 hard-filter variants did not generalize reliably on the broader universe. `S1_AVOID_MESSY_MIDDLE_V1` performed badly despite earlier promise. `S1_BROAD_BEST_GUESS` was conservative but did not beat the 200-symbol baseline.

Consequence:

Hard filters remain research probes only.

---

## 2026-06-14 - Park S1 Candidate Ranking v1

Decision:

Park `candidate-ranking s1_v1`.

Reason:

It was technically valid but underperformed the unranked S1 baseline.

Consequence:

No S1 ranking method is currently promoted. S1 ranking v2 is deferred.

---

## 2026-06-14 - Add All-Signal Opportunity Diagnostics

Decision:

Add diagnostics for all generated S1 signals, including accepted trades, rejected active-symbol signals, rejected capacity signals, same-day candidate pools, and ranking feature summaries.

Reason:

Accepted-trade-only reports are incomplete when the portfolio rejects most generated signals because capacity is full.

Consequence:

Future ranking and voting research can evaluate opportunity quality across accepted and rejected candidates.

---

## 2026-06-14 - Treat Counterfactual Rejected-Signal PnL as Diagnostics Only

Decision:

Counterfactual rejected-signal PnL must not be treated as actual achievable portfolio PnL.

Reason:

Counterfactual simulations ignore portfolio capacity, ledger effects, and real capital allocation.

Consequence:

Counterfactual results may inform ranking hypotheses, but must not be mixed into actual portfolio performance metrics.

---

## 2026-06-14 - Implement S2 Markov as Standalone Strategy

Decision:

Implement `S2_MARKOV_STATE_TRANSITION` as a separate strategy family.

Reason:

The project should test genuinely different standalone strategy families before over-optimizing S1 ranking.

Consequence:

S2 is not an S1 filter and must be benchmarked independently.

---

## 2026-06-14 - Hold S2 Execution Until Docs and Audit Decisions Are Refreshed

Decision:

Do not run S2 on research200 until documentation, audits, and decision logs reflect the current research state.

Reason:

The documentation set must remain internally consistent before adding new benchmark results.

Consequence:

Phase 27B refreshed core docs. Phase 27C refreshes audit and decision records.

---

## 2026-06-14 - Defer FFT and Wavelet Until After S2 Baseline Evidence

Decision:

Defer FFT and wavelet strategy research until after S2 has standalone benchmark evidence.

Reason:

The project should avoid adding too many advanced strategy families before validating S2.

Consequence:

FFT and wavelet remain future research directions, not accepted production rules.
