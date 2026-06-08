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

# Rejected or Deferred Hypotheses

The following are not part of Phase 1.

## Exact Price Prediction

Rejected for Phase 1.

Reason:

Veridian Quant v2 should first validate robust behavioral/statistical edges before attempting direct forecasting.

## Black-Box ML Prediction

Deferred.

Reason:

Machine learning may be useful later, but only after clean baselines and audit framework are established.

## FFT / Wavelet / Markov-Based Entry

Deferred.

Reason:

These may be researched later, but they must independently prove contribution beyond simple volatility-normalized mean reversion.

---

# Phase 1 Priority

The first research priority is:

## H1 + H2 + H3

Meaning:

A simple volatility-normalized mean reversion strategy with basic regime awareness.

No advanced ensemble components are allowed until this baseline is validated.
