# Feature Ideas

## Purpose

This document records candidate research features before they are promoted into strategy implementations.

Feature ideas are not accepted trading rules. They must be tested through the normal strategy, backtest, audit, and robustness workflow.

---

## S4 Entropy / Volatility Compression Breakout Candidate Features

S4 is a Phase 29A docs-only independent strategy family. It should test volatility/range/noise compression followed by upside breakout confirmation.

Current status:

- Specification only.
- No code implementation.
- No backtest results.
- Not production-ready.
- No S2/S3 filter mixing yet.
- No portfolio blending yet.

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

Initial future benchmark variants:

- `S4_ATR_COMPRESSION_BREAKOUT_V1`
- `S4_RANGE_COMPRESSION_BREAKOUT_V1`
- `S4_ENTROPY_GATED_BREAKOUT_V1`

These features are research candidates only. Phase 29A does not promote any S4 rule to production and does not authorize parameter tuning.

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
