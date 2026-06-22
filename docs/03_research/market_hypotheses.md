# Veridian Quant v2 — Market Hypotheses

## Purpose

This document defines the market inefficiencies Veridian Quant v2 is allowed to research.

No strategy should be implemented unless it maps clearly to one or more hypotheses in this document.

---

# H1 — Panic Mean Reversion

## Hypothesis

Indian large-cap equities sometimes experience short-term oversold conditions caused by panic selling, forced exits, liquidity pressure, or broad market fear.

After the selling pressure exhausts, prices often revert toward a short-term equilibrium.

## Expected Edge

Buy statistically oversold stocks after abnormal downward movement, provided the broader market regime is not structurally hostile.

## Why This May Work

* Investors overreact to short-term bad news.
* Stop-loss cascades can temporarily push prices below fair value.
* Institutional flows may create temporary dislocations.
* Liquid large-cap names often attract dip-buying after excessive decline.

## When It May Fail

* During strong bear markets.
* During company-specific fundamental deterioration.
* During earnings shocks, fraud events, or governance issues.
* When the entire sector is repricing lower.

## Candidate Features

* Z-score
* Distance from moving average
* Short-term drawdown
* Volatility-adjusted return
* Gap-down magnitude
* Volume shock

---

# H2 — Regime-Dependent Mean Reversion

## Hypothesis

Mean reversion does not work equally in all market environments.

The same oversold signal may behave differently in bull, bear, sideways, high-volatility, and low-volatility regimes.

## Expected Edge

Filter or resize trades based on market regime.

## Why This May Work

* Bull markets reward buying pullbacks.
* Bear markets punish early dip-buying.
* High-volatility regimes increase stop-loss risk.
* Sideways markets often favor reversion.

## When It May Fail

* Regime model is late.
* Market changes abruptly.
* Nifty regime differs from individual stock regime.
* Sector-specific stress is missed.

## Candidate Features

* Nifty trend
* Nifty volatility
* India VIX
* Market breadth
* Sector trend
* Advance-decline ratio

---

# H3 — Volatility Normalization

## Hypothesis

Raw price movement is not comparable across stocks.

A 3% fall in one stock may be normal, while a 3% fall in another may be extreme.

## Expected Edge

Normalize signals by each stock’s own volatility before ranking opportunities.

## Why This May Work

* It avoids treating high-beta and low-beta stocks equally.
* It improves comparability across the universe.
* It reduces false signals from naturally volatile stocks.

## When It May Fail

* Volatility expands suddenly.
* Historical volatility underestimates current risk.
* Low-volatility stocks break down structurally.

## Candidate Features

* Rolling standard deviation
* ATR
* Realized volatility
* Volatility-adjusted returns
* Z-score

---

# H4 — Liquidity Shock Recovery

## Hypothesis

Temporary liquidity shocks can push liquid stocks away from fair short-term value.

Once liquidity normalizes, price may recover.

## Expected Edge

Identify excessive price movement with abnormal volume or abnormal range, then wait for stabilization.

## Why This May Work

* Large sell orders can temporarily overwhelm demand.
* Index rebalancing or institutional flow can create temporary pressure.
* Liquidity often returns in large-cap stocks.

## When It May Fail

* Selling is information-driven.
* Liquidity does not return.
* Shock is part of a larger breakdown.

## Candidate Features

* Volume spike
* Range expansion
* Gap-down
* Intraday recovery
* Close location within candle

---

# H5 — Relative Weakness Reversion

## Hypothesis

A stock that becomes unusually weak relative to the index or sector may revert if the weakness is temporary rather than structural.

## Expected Edge

Identify stocks that underperform sharply versus benchmark but remain inside a supportive market or sector regime.

## Why This May Work

* Temporary flow pressure can create relative dislocation.
* Pair and basket rebalancing may normalize relative performance.
* Strong stocks often recover faster after temporary underperformance.

## When It May Fail

* Stock-specific weakness is fundamental.
* Sector is structurally weakening.
* Relative weakness continues into momentum breakdown.

## Candidate Features

* Stock vs Nifty relative return
* Stock vs sector relative return
* Relative strength percentile
* Rolling beta-adjusted residual

---

# H6 - Opportunity Selection Under Capital Constraints

## Hypothesis

S1's key bottleneck is not only signal generation. It is opportunity selection under capital constraints.

When the strategy generates more valid signals than the portfolio can take, portfolio results depend heavily on which candidates are selected and which are rejected.

## Expected Edge

Improve portfolio performance by ranking, scoring, or voting among same-day candidates without changing the underlying signal-generation rules.

## Current Evidence

All-signal diagnostics show that rejected capacity signals contain hidden winners, but the average rejected capacity signal has weak edge.

This supports future candidate ranking and voting systems, but does not prove that simple ranking is enough.

`candidate-ranking s1_v1` underperformed the unranked S1 baseline, so more evidence or separate strategy families are needed before optimizing S1 ranking further.

Standalone strategies should be tested independently before combining them as votes.

## Candidate Features

* Signal depth
* Volatility-adjusted displacement
* Liquidity
* Same-day candidate pool context
* Historical same-state outcomes
* Regime context
* Strategy-family agreement

## When It May Fail

* Ranking features are noisy.
* Winners are not predictable from signal-time data.
* Hard filters remove too many profitable trades.
* Ranking overfits one universe or period.
* Capacity constraints change in live deployment.

---

# H7 - Trend Pullback Continuation

## Hypothesis

Strong stocks in confirmed uptrends often resume their trend after controlled pullbacks.

S3 tested whether structurally healthy stocks can be bought after temporary weakness without drifting into falling-knife mean reversion.

Audit status:

S3 is technically valid but parked as a standalone production candidate. The best retained benchmark is `S3_STRONG_TREND_ABOVE_SMA50_V1`, but it is benchmark-only.

## Expected Edge

Expected edge comes from:

* Trend persistence.
* Better entry price than chasing highs.
* Strong stocks recovering faster after controlled weakness.
* Avoiding deeply broken stocks that are down for structural reasons.

## Why This May Work

* Institutional accumulation can persist across multiple swing cycles.
* Healthy uptrends often include short profit-taking pauses.
* Pullbacks toward intermediate trend support can improve reward/risk.
* Relative strength can remain durable even after short-term weakness.

## When It May Fail

* The pullback becomes a trend breakdown.
* The broader market regime turns hostile.
* A stock is above SMA200 but its sector is deteriorating.
* Volatility expansion signals panic rather than controlled weakness.
* Pullback-depth thresholds overfit one market period.

## Candidate Features

* SMA50/SMA200 trend.
* SMA slope.
* Controlled pullback return.
* Drawdown from 20d/60d high.
* Distance from SMA50.
* Distance from 60d low.
* ATR expansion.
* Relative strength vs Nifty.
* Nifty trend confirmation.

---

# H8 - Volatility Compression Breakout

## Hypothesis

Stocks that spend time in unusually compressed volatility, tight ranges, or reduced directional noise may produce favorable long-only breakout opportunities once price confirms expansion.

S4 will test this as `S4_ENTROPY_VOLATILITY_COMPRESSION_BREAKOUT`.

Audit status:

S4 has been implemented and raw-tested through Phase 29F/29G as an independent strategy family, not an S1/S2/S3 filter.

Current conclusion:

S4 is technically valid but parked after weak raw baseline evidence. `S4_ATR_COMPRESSION_BREAKOUT_V1` is retained only as a weak benchmark/research reference. `S4_RANGE_COMPRESSION_BREAKOUT_V1` is rejected as an S4 raw baseline, and `S4_ENTROPY_GATED_BREAKOUT_V1` is not promoted. S4 is not production-ready.

## Expected Edge

Expected edge comes from:

* Volatility expansion after unusually quiet periods.
* Breakout confirmation after compression rather than prediction during compression.
* Capturing early continuation after a range resolves upward.
* Avoiding direct dependence on oversold mean reversion, Markov recurrence, or pullback-continuation logic.

## Why This May Work

* Market participants often accumulate or distribute before visible range expansion.
* Tight ranges can create clustered stops and momentum follow-through after a breakout.
* Low recent volatility can allow tighter initial risk definition.
* Breakout confirmation can reduce premature entries inside unresolved ranges.

## When It May Fail

* Breakout fails quickly and returns inside the range.
* Compression reflects illiquidity rather than useful setup quality.
* Entry at next open suffers from unfavorable breakout gaps.
* Low volatility persists rather than expanding.
* Broader market weakness overwhelms individual breakouts.
* Added volume or trend filters overfit and blur S4's independent thesis.

## Candidate Features

* ATR percentile compression.
* Rolling high-low range compression.
* Optional entropy/noise compression.
* Close above N-day high.
* Optional volume confirmation.
* Optional trend context.

---

# H9 - Intermediate-Term Relative Strength / Momentum Persistence

## Hypothesis

Stocks that outperform peers over intermediate horizons may continue to
outperform because information diffusion, institutional positioning, and
investor underreaction can persist across multiple sessions.

S5 will test this hypothesis as the standalone
`S5_RELATIVE_STRENGTH_MOMENTUM_ROTATION` strategy family.

The audited Research200 universe is central to the test. Earlier Phase 23/24
work used only approximately 19-20 symbols; Research200 should materially change
candidate volume, rank dispersion, rejected opportunities, capacity pressure,
and portfolio chronology.

## Expected Edge

- Hold or enter the strongest eligible stocks rather than treating simultaneous
  candidates as interchangeable.
- Use cross-sectional ranking to allocate scarce portfolio slots.
- Capture persistent intermediate-term leadership without relying on oversold
  mean reversion, Markov recurrence, pullback depth, or compression breakouts.

## Why This May Work

- Institutional accumulation and capital flows may persist.
- Investors may underreact to information, allowing trends to continue.
- Broad-universe ranking may identify leadership more effectively than isolated
  absolute thresholds.
- Relative comparison can direct finite capacity toward stronger opportunities.

## When It May Fail

- Momentum leadership reverses abruptly.
- Crowded trades unwind together.
- Sideways markets cause rank churn and whipsaw.
- The strategy enters after trends are already exhausted.
- A broad market or sector reversal overwhelms stock-level momentum.
- Ranking overfits one lookback, period, or universe.
- Capacity constraints and replacement trades erase signal-level advantage.

## Candidate Features

- 63-day, 126-day, and 252-day returns.
- 126-day return excluding the most recent 21 sessions.
- Distance above SMA200.
- Proximity to the trailing 52-week high.
- Volatility-adjusted momentum.
- Optional NIFTY-relative return when benchmark data is available.
- Cross-sectional rank and percentile.

Audit status:

- Phase 32A design only.
- No implementation or backtest evidence yet.
- S5 is independent from S1/S2/S3/S4.
- No RAWRS or external-model features in the first research cycle.
- S2 is the primary robustness benchmark for later comparison.

---

# Rejected or Deferred Hypotheses

The following are not accepted production rules.

## Exact Price Prediction

Rejected for Phase 1.

Reason:

Veridian Quant v2 should first validate robust behavioral/statistical edges before attempting direct forecasting.

## Black-Box ML Prediction

Deferred.

Reason:

Machine learning may be useful later, but only after clean baselines and audit framework are established.

## FFT / Wavelet Entry

Deferred.

Reason:

These may be researched later, but they must independently prove contribution beyond simple volatility-normalized mean reversion.

---

## Markov-Based Entry

Research implementation exists as standalone S2 Markov State Transition.

Status:

Researched through Phase 27J, retained as benchmark/research candidate, frozen for now, and not accepted as a production rule.

Reason:

S2 has evidence of edge, but the research cycle found material regime fragility, especially in 2025/2026.

Retained S2 benchmarks:

* Safer benchmark: `exclude_ret_down + ranking none`
* Higher-return research candidate: `exclude_ret_down + clean_state_v1`

The 2025 failure audit found that S2 was vulnerable to shallow bullish pullbacks that looked healthy but failed to mean-revert:

* `RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW`
* `RET_UP|VOL_MID|DD_SHALLOW|LOW_MID_RANGE`

S2 is useful for future comparison, but immediate S2 tuning is parked.

---

# Current Priority

The current research priority is:

## Broader strategy research, robustness, and portfolio construction

Meaning:

S1 remains the current volatility-normalized mean-reversion benchmark, while opportunity selection under capital constraints is now a core research problem.

S2 Markov State Transition has now been tested independently and is frozen as a benchmark/research candidate, not a production strategy.

S3 Trend Pullback Continuation has now been tested independently and is parked as a benchmark-only strategy family, not a production strategy.

S4 Entropy / Volatility Compression Breakout has now been raw-tested independently and is parked as a weak benchmark-only strategy family, not a production strategy.

The next research priority should not be more S2, S3, or S4 threshold tuning.
Phase 32A begins the independent S5 Relative Strength / Momentum Rotation design
after completion of the Phase 31 robustness audit. S5 remains design-stage only
and must be tested independently on Research200 before any promotion or strategy
combination.
