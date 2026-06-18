# Feature Ideas

## Purpose

This document records candidate research features before they are promoted into strategy implementations.

Feature ideas are not accepted trading rules. They must be tested through the normal strategy, backtest, audit, and robustness workflow.

---

## I1 RAWRS Market Structure Intelligence Feature Ideas

`I1_RAWRS_MARKET_STRUCTURE_INTELLIGENCE` is a reusable non-strategy intelligence layer.

RAWRS means:

- Regime-Aware Adaptive Wavelet Response Surface.

Current status:

- Phase 30A docs/spec only.
- Not S5.
- Not a strategy.
- Not an entry model.
- Not a signal generator.
- Not a production rule.

Intended research use:

- Diagnostics on S1/S2/S3/S4 accepted trades.
- Diagnostics on rejected/capacity signals.
- Winner/loser separation analysis.
- Regime/context enrichment.
- Candidate-quality scoring research.
- Future ranking/capacity redesign input.
- Future market-regime overlay input.
- Future risk/path-quality context.

FFT / cycle feature candidates:

- Dominant frequency.
- Dominant cycle period.
- Cycle strength.
- Spectral concentration.
- Spectral entropy.
- Cycle stability over rolling windows.
- Cycle phase diagnostics, but not direct phase-based entries yet.

Wavelet feature candidates:

- Micro energy.
- Meso energy.
- Macro energy.
- Energy expansion.
- Energy compression.
- Multi-scale coherence.
- Micro/meso/macro energy ratios.
- Impulse vs drift topology.
- Local regime shift detection.

Entropy/noise feature candidates:

- Return sign entropy.
- Direction-change entropy.
- Spectral entropy.
- Wavelet entropy.
- Choppiness / noise proxy.
- Trend efficiency proxy.

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

These features and labels are research/intelligence concepts only. They are not accepted strategy rules, filters, entries, exits, or ranking rules.

---

## S4 Entropy / Volatility Compression Breakout Candidate Features

S4 is an independent strategy family that tested volatility/range/noise compression followed by upside breakout confirmation.

Current status:

- Researched through Phase 29F raw Research200 baselines.
- Frozen / parked after Phase 29G documentation.
- Not production-ready.
- Retained weak benchmark: `S4_ATR_COMPRESSION_BREAKOUT_V1`.
- Rejected raw baseline: `S4_RANGE_COMPRESSION_BREAKOUT_V1`.
- Not promoted: `S4_ENTROPY_GATED_BREAKOUT_V1`.
- No further near-term S4 feature or threshold tuning should be added without a materially new hypothesis.

Compression candidates:

- ATR percentile compression.
- Rolling high-low range compression.
- Optional entropy/noise compression.
- Return sign entropy.
- Direction-change count.
- Efficiency-ratio-style noise proxy.

Breakout confirmation candidates:

- Close above N-day high.
- Breakout close versus prior range high.
- Optional breakout-day range expansion.

Volume confirmation candidates:

- Breakout-day volume versus average volume.
- Breakout-day volume percentile.
- Volume expansion relative to compression-window volume.

Optional context candidates:

- Stock above SMA50 or SMA200.
- Nifty trend context.
- Relative strength versus Nifty.

Raw baseline variants:

- `S4_ATR_COMPRESSION_BREAKOUT_V1`
- `S4_RANGE_COMPRESSION_BREAKOUT_V1`
- `S4_ENTROPY_GATED_BREAKOUT_V1`

Raw S4 findings:

- ATR compression was weakly positive but had poor return-to-drawdown.
- Range compression was clearly negative.
- Entropy gating was near breakeven but negative and unstable.
- Capacity pressure and candidate selection remain major weaknesses.
- Current standard signal export does not expose S4-specific compression/breakout metadata fields, creating an auditability gap for future work.

These features are research candidates only. S4 is not promoted to production, and near-term S4 threshold tuning is parked.

---

## S3 Trend Pullback Continuation Candidate Features

S3 tested controlled pullbacks inside confirmed uptrends. Candidate features supported that distinction without turning the first baseline into an overfit scoring model.

Current status:

- S3 is researched and parked.
- Retained benchmark: `S3_STRONG_TREND_ABOVE_SMA50_V1`.
- Not production-ready.
- No further near-term S3 feature variants should be added without a materially new hypothesis.

Trend structure:

- SMA50.
- SMA200.
- Close vs SMA50 percentage.
- Close vs SMA200 percentage.
- SMA50 slope over 20 sessions.
- SMA200 slope over 20 sessions.

Pullback structure:

- 3d return percentage.
- 5d return percentage.
- 10d return percentage.
- Drawdown from 20d high.
- Drawdown from 60d high.
- Distance from SMA50.
- Distance from 60d low.
- Fresh 60d/120d low flags.

Volatility and breakdown risk:

- ATR14 percentage.
- ATR14 change over 5 sessions.
- Range expansion.
- Gap-down size.
- Consecutive down closes.

Market and relative-strength context:

- Nifty above SMA200.
- Nifty SMA200 slope.
- Nifty short-term return.
- Relative strength vs Nifty.
- Relative strength trend vs Nifty.

Initial S3 research used a simple transparent subset. Additional S3 features are parked for now because the standalone strategy did not produce production-quality results and further threshold tuning risks overfitting.
