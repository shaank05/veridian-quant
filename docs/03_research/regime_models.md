# Regime Model Research Notes

## Purpose

This document records regime-related findings and future regime-model ideas.

---

## S2 2025 Regime Fragility Finding

The S2 Markov research cycle found that positive historical same-state statistics can fail in specific market regimes.

The most important 2025 failure pocket for the high-return S2 candidate was:

`RET_UP + VOL_MID + DD_SHALLOW + not truly near lows`

Specific failed state labels:

- `RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW`
- `RET_UP|VOL_MID|DD_SHALLOW|LOW_MID_RANGE`

Context associated with the failure:

- Stock above SMA50.
- Stock SMA50 slope positive.
- Nifty above SMA50.
- Nifty SMA50 slope positive.
- Shallow drawdown 0 to -5%.

Interpretation:

S2 was fooled by shallow bullish pullbacks that looked healthy but failed to mean-revert in 2025. The issue was not one symbol and not one isolated month. It was a recurring regime problem across multiple months.

---

## Guard-Variant Conclusion

Guard variants that targeted the 2025 pocket improved the specific failure area, but did not produce a better retained S2 benchmark.

Observed pattern:

- The targeted bad pocket could be reduced.
- Portfolio capacity then shifted toward replacement candidates.
- Overall edge weakened too much.

Conclusion:

The S2 regime problem is broader than one state exclusion or one shallow-pullback penalty.

---

## Phase 27J Context Infrastructure

Phase 27J added signal-time stock/Nifty/relative-strength context for S2 ranking.

This was technically successful:

- Context is available before ranking and capacity decisions.
- Context uses only data on or before the signal date.
- Nifty context is optional and safe when unavailable.
- Signal logs expose context metadata for diagnostics.

Research conclusion:

The infrastructure is useful for future rankers and strategies, but it did not produce a superior S2 performance variant.

---

## I1 RAWRS Market Structure Intelligence

`I1_RAWRS_MARKET_STRUCTURE_INTELLIGENCE` is a candidate market-structure and regime intelligence layer.

RAWRS means:

- Regime-Aware Adaptive Wavelet Response Surface.

Status:

- Phase 30A docs/spec only.
- Non-strategy intelligence layer.
- Not S5.
- Not a direct signal generator.
- Not a portfolio runner.
- Not production-approved.

Research purpose:

- Study multi-scale price energy.
- Study frequency/cycle behavior.
- Study entropy/noise.
- Study wavelet coherence.
- Study regime/topology features.
- Enrich future diagnostics for accepted trades and rejected/capacity signals.

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

These labels are research concepts only. They are not accepted trading rules.

Potential future use:

- Winner/loser separation analysis.
- Accepted versus rejected signal analysis.
- Capacity/ranking context.
- Regime-overlay research.
- Risk/path-quality context.

Audit requirements:

- Use only information available up to the signal timestamp.
- Use explicit trailing windows.
- Avoid future leakage.
- Avoid post-hoc filters tuned directly to final PnL.
- Separate diagnostic-only counterfactuals from actual portfolio PnL.

---

## Parked / Future Regime Work

Future work:

- I1 RAWRS market-structure intelligence diagnostics.
- Better market-regime detector.
- S2 regime-aware exposure reduction.
- Context-aware ranking that is validated outside the S2-only tuning loop.
- Sector/industry regime conditioning if metadata becomes available.
- Symbol-level robustness filters after broader strategy comparison.

No regime model is currently production-approved.
