# I1 RAWRS Signal-Time Diagnostics

## Purpose

`I1_RAWRS_SIGNAL_TIME_DIAGNOSTICS` defines how future diagnostics should attach RAWRS market-structure features to strategy signals and trades without changing trading behavior.

This document is a design/specification artifact for `I1_RAWRS_MARKET_STRUCTURE_INTELLIGENCE`.

It exists to answer diagnostic questions before any RAWRS ranking, overlay, filter, or strategy logic is considered:

- Do RAWRS features separate winners from losers at signal time?
- Do accepted and rejected signals show different market-structure quality?
- Could same-day capacity decisions have favored better candidates using information available at the signal timestamp?
- Do weak periods such as 2022, 2025, or 2026 have distinct RAWRS signatures?

---

## Current Phase Scope

Phase 30C is docs-only.

Allowed work:

- Define the future signal-time diagnostic design.
- Define alignment, leakage, and overfitting guardrails.
- Define future output tables for later implementation.
- Link this design from the RAWRS intelligence specification and research docs.

Not allowed in Phase 30C:

- No diagnostics runner.
- No CSV exporter.
- No ranking rule.
- No strategy logic.
- No backtest behavior changes.
- No production decision.

---

## Strategy Output Compatibility

Phase 30F adds `docs/06_intelligence/i1_rawrs_strategy_output_compatibility.md` as the strategy output compatibility audit for future standalone RAWRS diagnostics.

Phase 30G adds the standalone RAWRS diagnostic CLI in `src/veridian_quant/v2/run_rawrs_diagnostics.py`. The CLI validates existing strategy output folders in `light` or `full` mode, infers required symbols and dates, loads DB-backed OHLCV data through the existing v2 data loader convention, computes RAWRS feature frames, and writes standalone RAWRS diagnostic CSVs.

Future implementation should support:

- Light RAWRS diagnostics from standard accepted-trade and signal/trade output files.
- Full RAWRS diagnostics when rejected-signal, all-signal, capacity, and same-day candidate-pool diagnostic outputs are available and populated.

Future RAWRS tooling should validate the selected mode against available strategy output files. Missing or empty rejected-signal/all-signal files must not be interpreted as no rejected opportunities.

The precomputed-feature helper path remains available for programmatic tests and future integrations, but the CLI itself now runs end to end when the existing database-backed OHLCV source is available.

---

## Why This Is Diagnostics, Not Strategy Logic

RAWRS diagnostics are descriptive research tools.

They may describe the market-structure context around existing S1/S2/S3/S4 signals, but they do not create signals or decide trades.

Diagnostic output may later support research into ranking, capacity selection, regime overlays, or risk context only if evidence is stable and auditable.

Until then:

- RAWRS features are not entries.
- RAWRS features are not exits.
- RAWRS features are not hard filters.
- RAWRS features are not production-approved.
- RAWRS is not S5.

---

## Data Inputs

Future diagnostics may consume existing or future research outputs, including:

- Portfolio backtest outputs.
- Accepted trade logs.
- Trade PnL logs.
- Signal logs.
- Rejection logs.
- Capacity-rejection logs.
- Active-symbol rejection logs.
- Symbol OHLCV data.
- RAWRS feature frames generated only from data available up to the signal timestamp.

Input requirements:

- Each accepted trade must preserve strategy family, symbol, signal date, entry date, exit date, and realized outcome fields where available.
- Each rejected signal must preserve strategy family, symbol, signal date, rejection reason, and same-day candidate context where available.
- RAWRS feature frames must be keyed by symbol and feature timestamp.
- Any future rejected-signal outcome fields must be marked diagnostic-only.

---

## Signal-Time Alignment Rules

RAWRS features must be attached as of the signal timestamp.

Alignment rules:

- No RAWRS feature may use rows after the signal date.
- If a strategy signals on close and enters next session open, RAWRS belongs to the signal date.
- Entry-date RAWRS may be studied only as a separate entry-time diagnostic, not as the default signal-time feature set.
- Rejected signals use the same signal-date alignment as accepted signals.
- Capacity-rejected signals never receive actual realized portfolio PnL.
- Same-day candidate diagnostics must separate the actual portfolio path from hypothetical candidate quality.

The default diagnostic join key should be:

- Strategy family.
- Symbol.
- Signal date.

---

## RAWRS Feature Attachment Plan

Future diagnostics should attach a compact initial feature set before adding derived labels or composite scores.

Initial RAWRS feature candidates:

- `rawrs_log_return`
- `rawrs_fft_spectral_concentration`
- `rawrs_fft_spectral_entropy`
- `rawrs_fft_dominant_period`
- `rawrs_micro_energy`
- `rawrs_meso_energy`
- `rawrs_macro_energy`
- `rawrs_micro_meso_energy_ratio`
- `rawrs_meso_macro_energy_ratio`
- `rawrs_direction_change_rate`

Attachment requirements:

- Use explicit trailing windows.
- Preserve the original signal timestamp.
- Preserve feature timestamp separately if different.
- Preserve feature availability flags.
- Do not impute unavailable signal-time features using future rows.

---

## Accepted-Trade Diagnostic Plan

Accepted-trade diagnostics should compare RAWRS values across realized trade outcomes.

Core comparisons:

- Winners versus losers.
- High-R trades versus low-R trades.
- Target exits versus stop exits.
- Time-stop exits versus target/stop exits.
- Drawdown-heavy winners versus clean winners, if path-quality fields become available later.
- Strategy-family breakdowns for S1, S2, S3, and S4.

Outcome fields may include realized PnL, R-multiple, exit reason, holding period, MAE/MFE if available, and portfolio state. These outcomes must never be used to define signal-time RAWRS features.

---

## Rejected-Signal Diagnostic Plan

Rejected-signal diagnostics should compare accepted and rejected opportunities without treating rejected outcomes as realized performance.

Core comparisons:

- Accepted signals versus rejected signals.
- Capacity-rejected signals versus accepted signals.
- Active-symbol rejected signals analyzed separately.
- Rejected outcomes used only as diagnostic counterfactuals if future infrastructure computes them.

Rejected-signal diagnostics must preserve rejection reason and same-day candidate context.

---

## Capacity-Rejection Diagnostic Plan

Capacity diagnostics should ask whether RAWRS could have identified better candidates within the same-day opportunity pool.

Allowed diagnostic questions:

- Did accepted candidates have weaker RAWRS structure than rejected same-day candidates?
- Were capacity-rejected winners identifiable at signal time?
- Were accepted losers avoidable based on signal-time RAWRS context?
- Were same-day candidate pools structurally different in weak years?

Forbidden interpretation:

- Do not treat counterfactual rejected-signal PnL as achievable actual portfolio PnL.
- Do not combine hypothetical candidate quality with actual portfolio equity curves.
- Do not claim a capacity rule is profitable before an independently validated ranking study exists.

Actual portfolio path and hypothetical candidate quality must stay separate.

---

## Winner/Loser Separation Tests

Initial separation tests should be simple, transparent, and stable.

Recommended tests:

- Binned feature analysis.
- Quantile tables.
- Median and mean comparisons.
- R-multiple by feature bucket.
- Win rate by feature bucket.
- Profit factor by feature bucket.
- Year-by-year bucket stability.
- Strategy-by-strategy bucket stability.
- Same-day rank diagnostics later.

No single bucket, threshold, or year should be treated as enough evidence for a rule.

---

## Year/Regime Stability Tests

RAWRS evidence should be tested across calendar years and known weak periods.

Required cuts:

- Full sample.
- Year-by-year.
- Strong years versus weak years.
- 2022 as a weak-regime diagnostic period where relevant.
- 2025 and 2026 as weak-regime diagnostic periods where relevant.

Useful evidence should remain directionally stable across years, not depend on one isolated calendar segment.

---

## Strategy-Family Comparison Plan

RAWRS diagnostics should be strategy-family aware.

Initial families:

- S1 Z-score mean reversion benchmark.
- S2 Markov State Transition parked benchmark/research candidate.
- S3 Trend Pullback Continuation parked benchmark.
- S4 Entropy / Volatility Compression Breakout weak parked benchmark.

Comparisons should ask whether a RAWRS feature is:

- Broadly useful across families.
- Useful only for a specific family.
- Contradictory across families.
- Driven by one strategy and one year.

No S2/S3/S4 filter mixing is authorized by this document.

---

## Required Output Tables for Future Implementation

Future implementation may create the following diagnostic outputs:

- `rawrs_signal_diagnostics.csv`
- `rawrs_trade_diagnostics.csv`
- `rawrs_rejection_diagnostics.csv`
- `rawrs_feature_bucket_summary.csv`
- `rawrs_feature_by_year_summary.csv`
- `rawrs_feature_by_strategy_summary.csv`
- `rawrs_same_day_candidate_pool_summary.csv`

These tables are future-only. Phase 30C does not implement them.

---

## Guardrails Against Future Leakage

Future diagnostics must enforce:

- No RAWRS feature uses data after the signal timestamp.
- No exit outcome defines or changes a signal-time feature.
- No rejected simulated outcome is reported as actual portfolio PnL.
- No next-open entry data is used for signal-close RAWRS features unless explicitly labeled entry-time diagnostics.
- No feature rows are forward-filled from future timestamps.
- No portfolio-level result is recomputed from diagnostic-only rejected outcomes.

Every diagnostic table should preserve enough timestamps to audit the join.

---

## Guardrails Against Post-Hoc Overfitting

RAWRS has high overfitting risk because FFT, wavelet, entropy, and topology features can generate many candidate cuts.

Guardrails:

- No direct threshold tuning from one backtest.
- No hard filter without out-of-sample or walk-forward validation.
- No production claims from descriptive diagnostics.
- No strategy mixing yet.
- No S5 naming.
- Prefer simple bucket and stability evidence before composite scores.
- Treat complex uninterpretable combinations as suspect unless they have strong independent validation.

---

## What Would Count as Useful Evidence

Useful RAWRS evidence may include:

- Consistent separation between winners and losers at signal time.
- Directionally stable separation across years.
- Directionally stable separation across multiple strategy families.
- Capacity-rejected better candidates identifiable at signal time.
- Weak regimes such as 2022, 2025, or 2026 showing distinct RAWRS signatures.
- Interpretable feature behavior that matches a plausible market-structure thesis.

Useful evidence is explanatory first. Trading changes require later validation.

---

## What Would Not Count as Useful Evidence

Weak or invalid evidence includes:

- One favorable bucket in one year.
- A threshold that improves one variant but fails elsewhere.
- Post-hoc filtering of already known bad trades.
- Counterfactual rejected profit treated as actual portfolio PnL.
- Complex feature combinations that are not interpretable or stable.
- Any result that depends on lookahead alignment.

## True-Overlay Evidence Update

Phase 30I tested the strongest S3 completed-trade diagnostic candidate,
`rawrs_fft_spectral_concentration`, as leakage-safe signal-time hard filters at
p20 and p10. Both true portfolio overlays underperformed the retained S3
baseline. The filters changed chronology, capacity, replacement trades,
equity-dependent sizing, and compounding; profitable baseline trades were
removed while weaker replacement cohorts entered.

This result confirms the design warning in this document: post-hoc bucket
separation is explanatory evidence, not proof that a causal portfolio filter
will improve results. See
`docs/06_intelligence/i1_rawrs_combined_evidence_audit.md`.

---

## Future Implementation Phases

Possible future phases:

- Phase 30D: Define diagnostic schemas and join contracts.
- Phase 30E: Implement signal/trade RAWRS enrichment exports.
- Phase 30F: Implement accepted-trade winner/loser summaries.
- Phase 30G: Implement rejected/capacity signal diagnostics.
- Phase 30H: Evaluate year, regime, and strategy-family stability.
- Phase 30I: Decide whether RAWRS justifies ranking or overlay research.

These phases are not authorized by Phase 30C.

---

## Non-Goals

Phase 30C does not authorize:

- S2/S3/S4 filter mixing.
- Parameter tuning.
- Production decisions.
- Portfolio blending.
- Strategy implementation.
- Diagnostics runner implementation.
- Ranking implementation.
- Exporter implementation.
- Backtest changes.
- S5 creation.

---

## References

Related docs:

- `docs/06_intelligence/i1_rawrs_market_structure_intelligence.md`
- `docs/06_intelligence/i1_rawrs_strategy_output_compatibility.md`
- `docs/06_intelligence/i1_rawrs_combined_evidence_audit.md`
- `docs/00_foundation/v2_research_roadmap.md`
- `docs/03_research/regime_models.md`
- `docs/03_research/feature_ideas.md`
- `docs/05_decisions/decision_log.md`
- `docs/04_validation/backtest_methodology.md`
