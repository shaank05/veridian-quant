# Feature Ideas

## Purpose

This document records candidate research features before they are promoted into strategy implementations.

Feature ideas are not accepted trading rules. They must be tested through the normal strategy, backtest, audit, and robustness workflow.

---

## S5 Relative Strength / Momentum Rotation Candidate Features

`S5_RELATIVE_STRENGTH_MOMENTUM_ROTATION` is a design-stage standalone strategy
family. Its first research cycle should use a small, transparent feature set and
cross-sectional ranking under Research200 capacity pressure.

Current status:

- Phase 32A design only.
- No implementation, backtest results, or production status.
- Independent from S1/S2/S3/S4.
- No RAWRS, Kronos, TradingAgents, or other external-model inputs initially.
- Future comparison uses S2 as the primary robustness benchmark.

Return momentum candidates:

- 63-session return.
- 126-session return.
- 252-session return.
- Skip-month momentum: 126-session anchor with the most recent 21 sessions
  excluded.

Trend and extension candidates:

- Distance above SMA200.
- Price above SMA200 flag.
- Proximity to trailing 52-week high.

Risk-adjusted momentum candidates:

- Momentum return divided by realized volatility over a compatible window.
- Cross-sectional percentile rank of volatility-adjusted momentum.
- Explicit invalid-score policy for missing or near-zero volatility.

Benchmark-relative candidates:

- Stock return minus NIFTY return over matched 63/126/252-session horizons.
- Cross-sectional rank of NIFTY-relative return.
- Use only when benchmark history is complete and timestamp-aligned.

Ranking metadata:

- Raw score.
- Cross-sectional rank and percentile.
- Eligible-universe count.
- Same-day candidate count.
- Accepted/rejected decision and reason.
- Deterministic tie-break value.

First-pass variants should consume only the features they declare:

- `S5_SIMPLE_RS_126D_V1`
- `S5_DUAL_MOMENTUM_63_126D_V1`
- `S5_VOL_ADJUSTED_RS_V1`
- Optional later `S5_52W_HIGH_PROXIMITY_V1`

These are research candidates, not accepted trading rules. Avoid large feature
composites, threshold grids, or post-hoc filters in the first cycle.

---

## I1 RAWRS Market Structure Intelligence Feature Ideas

`I1_RAWRS_MARKET_STRUCTURE_INTELLIGENCE` is a reusable non-strategy intelligence layer.

RAWRS means:

- Regime-Aware Adaptive Wavelet Response Surface.

Current status:

- Phase 30A docs/spec only.
- Phase 30B implemented initial research feature utilities.
- Phase 30C defines signal-time diagnostic usage before ranking or overlays.
- Phase 30G implemented standalone diagnostics across compatible strategy
  outputs.
- Phase 30H found useful but mixed keep/avoid separation.
- Phase 30I rejected S3 spectral-concentration hard gates at p20 and p10 after
  true portfolio backtests underperformed baseline.
- Phase 30J consolidates the evidence in
  `docs/06_intelligence/i1_rawrs_combined_evidence_audit.md`.
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

Phase 30C diagnostic feature usage:

- Attach RAWRS features at the signal timestamp for accepted trades and rejected signals.
- Start with transparent feature buckets, quantile tables, mean/median comparisons, win rate by bucket, R-multiple by bucket, and profit factor by bucket.
- Compare feature behavior by year, weak regime, and strategy family before any threshold or composite score is considered.
- Keep usage research-only until independent validation supports ranking, overlay, or capacity research.

Initial signal-time diagnostic feature candidates:

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

Current evidence treatment:

- Keep meso/macro energy and strategy-specific spectral/entropy features as
  diagnostic research candidates.
- `rawrs_macro_energy` remains the broadest, though often modest,
  cross-strategy diagnostic candidate.
- Do not use `rawrs_fft_spectral_concentration` as an S3 p20 or p10 hard gate.
- Do not infer hard-filter viability for S1/S2/S4 from completed-trade buckets.
- Prefer stability/significance work and capacity-aware ranking hypotheses over
  new hard filters.

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
