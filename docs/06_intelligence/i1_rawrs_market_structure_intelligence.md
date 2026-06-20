# I1 RAWRS Market Structure Intelligence

## Purpose

`I1_RAWRS_MARKET_STRUCTURE_INTELLIGENCE` is a reusable non-strategy intelligence layer for studying market structure before adding new trading rules.

RAWRS means:

`Regime-Aware Adaptive Wavelet Response Surface`

The purpose of I1 RAWRS is to compute and study multi-scale price energy, frequency/cycle behavior, entropy/noise, wavelet coherence, and regime/topology features.

These features are intended for diagnostics, ranking research, and future regime overlays.

Phase 30C adds the signal-time diagnostic design in `docs/06_intelligence/i1_rawrs_signal_time_diagnostics.md`. That document defines how RAWRS features should be attached to accepted trades, rejected signals, and capacity-rejection cases before any ranking, overlay, or strategy implementation is considered.

Phase 30F adds `docs/06_intelligence/i1_rawrs_strategy_output_compatibility.md` as a docs-only prerequisite for any future standalone RAWRS CLI design. It audits S1/S2/S3/S4 output compatibility and defines light versus full diagnostic modes based on available strategy output files.

Phase 30J consolidates the implemented infrastructure, cross-strategy
diagnostics, keep/avoid findings, and true S3 overlay evidence in
`docs/06_intelligence/i1_rawrs_combined_evidence_audit.md`. RAWRS remains
diagnostic-only. The S3 spectral-concentration hard filter failed at both p20
and p10 and is rejected as an overlay hypothesis.

I1 RAWRS should help answer questions such as:

- Why did accepted trades win or lose?
- Did rejected/capacity signals contain structurally better opportunities?
- Did weak years such as 2022 and 2025/2026 have identifiable market-structure signatures?
- Can market-structure context explain trade quality before it is used in ranking or strategy logic?

---

## Identifier and Naming

Identifier:

`I1_RAWRS_MARKET_STRUCTURE_INTELLIGENCE`

Full name:

`I1 RAWRS Market Structure Intelligence`

Category:

- Intelligence layer.
- Market-structure diagnostics.
- Regime/topology context.
- Candidate-quality research input.

It belongs under:

`docs/06_intelligence/`

It does not belong under:

`docs/01_strategies/`

---

## Why I1 Is Not S5

I1 RAWRS is not S5.

Reason:

- It is not a strategy family.
- It does not generate direct buy/sell signals.
- It does not define an entry model.
- It does not own a portfolio runner.
- It does not create trades.
- It is not a production rule.

The project has already tested S1, S2, S3, and S4 as standalone strategy families.

The next useful research step is to understand market structure, trade quality, regime context, and capacity selection before prematurely creating another direct strategy.

---

## Relationship to S1/S2/S3/S4

I1 RAWRS is intended to sit beside existing strategy families as a context and diagnostics layer.

S1:

- S1 remains the Z-score mean-reversion benchmark.
- RAWRS may later analyze whether S1 winners and losers differ by cycle, entropy, or wavelet-energy state.

S2:

- S2 remains frozen/parked as a Markov State Transition benchmark/research candidate.
- RAWRS may later study whether S2 regime failures had frequency, entropy, or topology signatures not captured by state labels.

S3:

- S3 remains parked as a trend-pullback benchmark.
- RAWRS may later study whether trend-pullback failures were noisy impulses, regime breaks, or weak drift states.

S4:

- S4 remains parked as a weak compression-breakout benchmark.
- RAWRS may later study whether S4 breakouts succeeded only under specific multi-scale energy or entropy conditions.

RAWRS should not be used to mix S1/S2/S3/S4 filters without separate evidence.

---

## RAWRS Thesis

Market behavior is not fully described by simple return, volatility, or moving-average features.

The RAWRS thesis is:

> Trade quality depends partly on multi-scale market structure: frequency/cycle behavior, wavelet energy distribution, entropy/noise, coherence across scales, and regime topology.

Expected research value:

- Identify when price movement is clean impulse versus noisy chop.
- Detect compression, expansion, and regime transitions.
- Measure whether market structure differs between winners and losers.
- Improve future ranking/capacity research with context that is not tied to a single strategy family.
- Support future regime overlays without creating a premature direct trading rule.

---

## Intended Initial Use

Initial uses:

- Diagnostics on existing S1/S2/S3/S4 accepted trades.
- Diagnostics on rejected/capacity signals.
- Winner/loser separation analysis.
- Regime/context enrichment.
- Candidate-quality scoring research.
- Future ranking/capacity redesign input.
- Future market-regime overlay input.
- Future risk/path-quality context.

Initial research should be descriptive and diagnostic.

RAWRS features must prove that they explain trade quality before they are used in ranking, filters, overlays, or portfolio construction.

---

## Explicit Non-Goals

I1 RAWRS is not initially:

- A strategy.
- An S5 strategy.
- An entry model.
- A signal generator.
- A backtest runner.
- A portfolio system.
- A production rule.
- A live trading component.
- A post-hoc overfit filter.

Phase 30A does not authorize:

- Code implementation.
- Backtest runner implementation.
- CSV export changes.
- Strategy tuning.
- Ranking changes.
- Portfolio blending.
- Production promotion.

Phase 30C also does not authorize:

- Diagnostics runner implementation.
- Ranking implementation.
- Overlay implementation.
- Trading behavior changes.

---

## Candidate Feature Families

Initial RAWRS feature families:

- FFT / cycle features.
- Wavelet energy and coherence features.
- Entropy/noise features.
- Regime/topology labels.
- Path-quality context.
- Capacity/candidate-quality context.

These are research ideas only. They are not accepted trading rules.

---

## FFT Feature Candidates

FFT / cycle candidates:

- Dominant frequency.
- Dominant cycle period.
- Cycle strength.
- Spectral concentration.
- Spectral entropy.
- Cycle stability over rolling windows.
- Cycle phase diagnostics.

Important constraint:

Cycle phase diagnostics are not direct phase-based entries yet.

FFT features must be computed using trailing windows only.

Any future implementation must document window length, detrending method if any, normalization, and frequency-bin interpretation.

---

## Wavelet Feature Candidates

Wavelet candidates:

- Micro energy.
- Meso energy.
- Macro energy.
- Energy expansion.
- Energy compression.
- Multi-scale coherence.
- Micro/meso/macro energy ratios.
- Impulse vs drift topology.
- Local regime shift detection.

Interpretation goals:

- Micro energy may capture short-horizon noise or impulse.
- Meso energy may capture swing structure.
- Macro energy may capture broader regime pressure.
- Coherence across scales may distinguish clean directional movement from fragmented chop.

Wavelet features must be auditable and trailing-window based.

---

## Entropy / Noise Feature Candidates

Entropy/noise candidates:

- Return sign entropy.
- Direction-change entropy.
- Spectral entropy.
- Wavelet entropy.
- Choppiness / noise proxy.
- Trend efficiency proxy.

Research goal:

Determine whether winners and losers differ by information disorder, path efficiency, or noisy direction changes before using entropy in any ranking or overlay.

---

## RAWRS Topology / Regime Labels

Candidate topology labels:

- `clean_impulse`
- `noisy_impulse`
- `compression`
- `expansion`
- `cyclic_reversion`
- `trend_drift`
- `chaotic_chop`
- `volatility_transition`
- `regime_break`

These labels are research concepts only.

They are not accepted trading rules, entry filters, exits, position-sizing rules, or production regimes.

Any future label construction must be:

- Deterministic.
- Explainable.
- Computed only from information available at the signal timestamp.
- Stable enough to audit across years and strategy families.

---

## Diagnostic Research Plan

Initial diagnostic plan:

1. Compute RAWRS features later for existing S1/S2/S3/S4 signals and trades.
2. Compare winners versus losers.
3. Compare accepted trades versus capacity-rejected signals.
4. Compare strong years versus weak years.
5. Pay special attention to known weak periods such as 2022 and 2025/2026.
6. Test whether RAWRS features explain trade quality before using them in ranking or strategy logic.
7. Avoid allowing RAWRS to become a post-hoc overfit filter.

Diagnostics should start with descriptive separation tests, not optimized strategy rules.

The detailed Phase 30C design is maintained in `docs/06_intelligence/i1_rawrs_signal_time_diagnostics.md`.

---

## Winner / Loser Separation Tests

Future winner/loser tests should ask:

- Do profitable trades have lower entropy or higher trend efficiency at signal time?
- Do losing trades show noisy impulse, regime break, or chaotic chop topology?
- Are S4 breakout winners associated with expansion after prior multi-scale compression?
- Are S3 trend-pullback winners associated with coherent meso/macro energy?
- Are S1 mean-reversion winners associated with exhaustion or cyclic-reversion topology?
- Are S2 failure states associated with regime breaks not visible in Markov labels?

These tests must be evaluated before any RAWRS feature is promoted into ranking or filtering research.

---

## Accepted vs Rejected Signal Analysis

RAWRS may be useful for capacity research if it can explain why some same-day candidates were better than others.

Future analysis should compare:

- Accepted trades.
- Rejected capacity signals.
- Rejected active-symbol conflict signals.
- Same-day candidate pools.
- Winners that were rejected due to capacity.
- Losers that were accepted because capacity was available.

Important rule:

Counterfactual rejected-signal PnL is diagnostic only. It must not be mixed into actual portfolio PnL.

---

## Auditability Requirements

All future RAWRS features must follow these requirements:

- Use only information available up to the signal timestamp.
- Use explicit trailing windows.
- Avoid future leakage.
- Avoid same-day unavailable data.
- Document all window lengths and transformations.
- Keep feature calculations deterministic.
- Preserve symbol/date alignment.
- Avoid direct tuning against final PnL before diagnostics prove separation.
- Separate actual portfolio PnL from diagnostic-only counterfactuals.

Any future ranking or overlay must be tested independently from the diagnostic discovery step.

---

## Overfitting Risks

RAWRS has high overfitting risk because FFT, wavelet, entropy, and topology features can produce many candidate variables.

Key risks:

- Too many windows and thresholds.
- Post-hoc filters built from weak periods.
- Interpreting noisy frequency peaks as stable cycles.
- Turning topology labels into fragile hard filters.
- Optimizing against 2020-2026 only.
- Confusing diagnostic separation with deployable portfolio improvement.

Mitigation:

- Start with diagnostics.
- Keep feature definitions transparent.
- Limit parameter grids.
- Require out-of-sample or walk-forward evidence before promotion.
- Prefer ranking/context research only after stable explanatory evidence exists.

---

## Future Implementation Phases

Possible future phases:

- I1B: Define RAWRS feature calculation interfaces.
- I1C: Implement trailing FFT/cycle diagnostics.
- I1D: Implement wavelet energy/coherence diagnostics.
- I1E: Implement entropy/noise diagnostics.
- I1F: Build signal/trade enrichment exports for S1/S2/S3/S4 diagnostics.
- I1G: Run winner/loser and accepted/rejected separation studies.
- I1H: Evaluate whether RAWRS improves candidate-quality scoring.
- I1I: Consider regime-overlay research only if diagnostics justify it.

These are possible future phases, not approved implementation work in Phase 30A.

Phase 30C defines signal-time diagnostics before any ranking or overlay implementation.

---

## Promotion Rules

RAWRS components may be promoted only if they satisfy all of the following:

- Clear hypothesis.
- No-lookahead implementation.
- Stable diagnostic separation across strategies and years.
- Clear economic or market-structure explanation.
- Portfolio-level evidence if used in ranking or overlays.
- Robustness across windows and symbols.
- Auditability in exported reports.
- No reliance on diagnostic-only counterfactual PnL as actual performance.

RAWRS cannot become a production component merely because it improves an in-sample backtest.

---

## References

Related docs:

- `docs/00_foundation/v2_design_document.md`
- `docs/00_foundation/v2_research_roadmap.md`
- `docs/06_intelligence/i1_rawrs_signal_time_diagnostics.md`
- `docs/06_intelligence/i1_rawrs_strategy_output_compatibility.md`
- `docs/06_intelligence/i1_rawrs_combined_evidence_audit.md`
- `docs/03_research/feature_ideas.md`
- `docs/03_research/regime_models.md`
- `docs/03_research/portfolio_construction.md`
- `docs/03_research/market_hypotheses.md`
- `docs/05_decisions/decision_log.md`
