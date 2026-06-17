# S3 - Trend Pullback Continuation

## Current Status

Status:

- Researched through Phase 28F.
- Implementation: complete.
- Backtest: complete on research200.
- Research status: parked.
- Production status: not production-ready.
- Strategy family: standalone independent strategy.
- Not an S1/S2 filter.
- Not part of a voting ensemble yet.

S3 tested an independent trend-continuation alpha source after the S1 baseline cycle and the frozen S2 Markov research cycle.

Final research decision:

- Retain `S3_STRONG_TREND_ABOVE_SMA50_V1` as the S3 benchmark only.
- Do not promote S3 to production.
- Do not continue near-term S3 variants.
- See `docs/02_audits/s3_audit.md` for the full audit.

Reason:

- Weak profit factor.
- High drawdown relative to return.
- Unstable yearly behavior.
- Persistent stop-loss drag.
- Controlled-pullback tuning did not improve realized portfolio performance.

---

## Strategy Identifier

`S3_TREND_PULLBACK_CONTINUATION`

---

## Purpose

S3 tests whether stocks in established uptrends continue higher after controlled pullbacks, provided the pullback does not represent structural breakdown.

Plain-English thesis:

> Buy strength after a controlled dip, not weakness after panic.

---

## Hypothesis

Indian equities with confirmed positive trend and healthy structure often resume trend after short-term pullbacks caused by temporary profit-taking, minor market weakness, or liquidity noise.

Expected edge:

- Trend persistence.
- Pullback entry gives better risk/reward than chasing highs.
- Strong stocks may recover faster after controlled weakness.
- Avoids deep falling-knife mean-reversion setups.

---

## Difference From Existing Strategies

### S1

S1 buys statistically oversold mean-reversion setups.

It focuses on price displacement from a rolling mean.

### S2

S2 buys Markov state recurrence setups.

It relies on historical same-state forward returns.

### S3

S3 buys controlled pullbacks inside confirmed uptrends.

It should require trend health before considering a pullback.

It should not buy deeply broken stocks just because they are down.

This difference matters because S3 is intended to diversify the project's alpha source away from the mainly mean-reversion/regime-reversion behavior of S1 and S2.

---

## Baseline Rule Concept

The initial S3 baseline should be transparent and deliberately not overfit.

### Trend Qualification

Possible baseline trend requirements:

- Stock close above SMA200.
- SMA200 slope positive.
- Preferably SMA50 slope positive.
- Stock not making a fresh 60d or 120d low.

### Pullback Condition

Possible baseline pullback requirements:

- Recent 3d to 10d return negative or otherwise controlled pullback.
- Price near SMA50 or pulled back from a recent high.
- Pullback should not be too deep.
- Avoid severe breakdowns.

### Volatility Condition

Possible baseline volatility requirements:

- ATR% not extremely high.
- ATR expansion not excessive.
- Avoid volatility blowoff or panic conditions.

### Market Context

Optional for later:

- Nifty above SMA200 or Nifty SMA200 slope positive.
- Nifty regime supportive.
- No hard dependency in the first baseline unless implementation can support it cleanly.

### Entry

- Signal generated at close of signal day.
- Enter next session open.

### Exit

Use existing v2 shared trade mechanics initially:

- ATR stop.
- ATR target.
- Time stop.
- Conservative same-candle stop-first rule.
- Max holding default 20 sessions.
- Risk per trade default 1%.
- Round-trip cost default 0.004.

---

## Candidate Baseline Parameters

These are research defaults, not proven final thresholds.

- SMA fast: 50.
- SMA slow: 200.
- SMA slope lookback: 20 sessions.
- Pullback lookback: 5 or 10 sessions.
- Pullback return range: negative but not collapse.
- ATR window: 14.
- ATR max threshold: to be researched.
- Max holding: 20 sessions.
- Reward:risk: 2.
- ATR stop multiplier: 2.

---

## Signal Metadata To Capture Later

Useful future signal metadata:

- `close`
- `sma50`
- `sma200`
- `close_vs_sma50_pct`
- `close_vs_sma200_pct`
- `sma50_slope_20d_pct`
- `sma200_slope_20d_pct`
- `return_3d_pct`
- `return_5d_pct`
- `return_10d_pct`
- `drawdown_20d_pct`
- `drawdown_60d_pct`
- `close_vs_20d_high_pct`
- `close_vs_60d_low_pct`
- `atr14_pct`
- `atr14_change_5d_pct`
- Nifty trend context if available.
- Relative strength vs Nifty if available.

---

## Failure Modes

Possible S3 failure cases:

- Uptrend is mature and about to reverse.
- Pullback is actually the start of a breakdown.
- Stock is above SMA200 but sector is deteriorating.
- Market regime turns bearish.
- Gap-down risk after entry.
- Controlled pullback thresholds overfit.
- Chasing shallow pullbacks can create poor reward/risk.
- Too restrictive filters may remove too many trades.
- Same-day capacity conflicts may select the wrong candidates.

---

## What Success Looks Like

S3 should be judged independently on the audited research200 universe.

Success criteria:

- Positive net PnL.
- Profit factor above S1/S2 benchmarks if possible.
- Lower or comparable max drawdown.
- Stable yearly behavior.
- No single year dominating total result.
- Not overly dependent on a few symbols.
- Reasonable trade count.
- Accepted trades better than rejected capacity candidates.
- Clear economic explanation.

---

## Backtest Methodology

S3 must use the same v2 portfolio methodology:

- Audited research200 universe.
- 2020-01-01 to 2026-04-30 baseline window.
- Compounded portfolio.
- ATR-based position sizing.
- Max concurrent positions default 5.
- Same costs and exit mechanics as S1/S2.
- No lookahead.
- Pre-start lookback allowed only for indicator calculation.
- No future bars after `end_date`.

---

## Initial Audit Plan

Required reports after implementation:

- `summary.csv`
- `yearly_summary.csv`
- `symbol_summary.csv`
- `exit_reason_summary.csv`
- `rejection_summary.csv`
- `r_multiple_summary.csv`
- `r_multiple_by_year.csv`
- `trade_signal_context.csv` if compatible.
- `accepted_vs_rejected_signal_summary.csv` if all-signal diagnostics are supported.
- Candidate/rejected diagnostics if capacity becomes important.

Audit questions:

- Does trend pullback outperform S1/S2 benchmarks?
- Does it behave differently from mean reversion?
- Does it avoid 2025/S2-style regime failure?
- Are winners from trend continuation or accidental mean reversion?
- Are losses concentrated in high-volatility breakdowns?
- Does capacity ranking matter?

---

## Final Research Status

S3 is researched and parked.

Best retained benchmark:

`S3_STRONG_TREND_ABOVE_SMA50_V1`

Approximate benchmark result on research200, 2020-01-01 to 2026-04-30:

- Net PnL: about Rs 3.16L.
- CAGR: about 4.43%.
- Max drawdown: about 28.20%.
- Profit factor: about 1.104.
- Trades: about 500.

This is not production-ready. S3 remains useful only as a trend-continuation benchmark for future comparison.

No further near-term S3 variants should be added unless a materially new hypothesis appears, such as a regime model, ranking/capacity redesign, sector/relative-strength feature redesign, or ensemble diversification need.

---

## Production Note

S3 is not production-ready. Implementation and research were completed, but the standalone results did not meet production-quality expectations.
