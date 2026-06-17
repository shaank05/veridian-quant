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

---

## 2026-06-17 - Freeze S2 Markov Research After Phase 27J

Decision:

Freeze `S2_MARKOV_STATE_TRANSITION` research for now.

Keep two retained S2 benchmarks:

- Safer benchmark: `markov_signal_filter = exclude_ret_down`, `s2_candidate_ranking = none`
- Higher-return research candidate: `markov_signal_filter = exclude_ret_down`, `s2_candidate_ranking = clean_state_v1`

Approximate retained benchmark results:

- Safer benchmark: about Rs 9.72L net PnL, about 11.32% CAGR, about 24.04% max drawdown, about 1.189 PF.
- Higher-return candidate: about Rs 12.32L net PnL, about 13.52% CAGR, about 33.94% max drawdown, about 1.223 PF, and about -Rs 7.50L in 2025.

What was tried:

- Raw S2 Markov baseline.
- Markov state filters.
- Candidate ranking modes.
- Rejected/capacity counterfactual diagnostics.
- 2025 failure audit.
- `avoid_shallow_uptrend_pullback_v1`.
- `2025_guard_v1`.
- Signal-time stock/Nifty/relative-strength context enrichment.

Rejected as benchmarks:

- `avoid_shallow_uptrend_pullback_v1`
- `exclude_ret_down + avoid_shallow_uptrend_pullback_v1`
- `exclude_ret_down + 2025_guard_v1`
- `exclude_ret_down + 2025_guard_v1 + signal-time context`

Reason:

S2 has evidence of edge, but remains regime fragile. The high-return candidate suffered a recurring 2025 regime failure concentrated in `RET_UP + VOL_MID + DD_SHALLOW + not truly near lows`, especially:

- `RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW`
- `RET_UP|VOL_MID|DD_SHALLOW|LOW_MID_RANGE`

Guard variants reduced the targeted pocket, but weakened total PnL too much or shifted losses to replacement candidates.

Consequence:

S2 is retained as a benchmark/research candidate, not production-ready and not deployed live.

Next:

Move the next research effort to a new independent strategy, likely S3 trend pullback continuation or another non-S2 alpha source.
