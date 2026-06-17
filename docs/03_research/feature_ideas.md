# Feature Ideas

## Purpose

This document records candidate research features before they are promoted into strategy implementations.

Feature ideas are not accepted trading rules. They must be tested through the normal strategy, backtest, audit, and robustness workflow.

---

## S3 Trend Pullback Continuation Candidate Features

S3 should test controlled pullbacks inside confirmed uptrends. Candidate features should support that distinction without turning the first baseline into an overfit scoring model.

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

Initial S3 implementation should prefer a simple transparent subset. Additional features should be added only after baseline evidence shows where the strategy succeeds or fails.
