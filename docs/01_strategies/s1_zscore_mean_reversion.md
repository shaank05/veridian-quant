# S1 — Z-Score Mean Reversion

## 1. Strategy Status

Status:

Research Candidate

Strategy Type:

Long-only swing trading mean reversion

Phase:

Veridian Quant v2 Phase 1

---

## 2. Strategy Objective

The objective of S1 is to test whether statistically oversold securities within the current research universe exhibit positive mean-reversion expectancy over a short swing-trading horizon.

S1 is designed as the first baseline strategy.

It should answer one question:

> If a stock becomes statistically oversold relative to its own recent price history, does buying it produce positive expectancy?

---

## 3. Linked Market Hypotheses

This strategy maps to the following hypotheses from `market_hypotheses.md`:

### H1 — Panic Mean Reversion

Securities within the current research universe may temporarily overshoot downward due to panic selling, liquidity pressure, stop-loss cascades, or short-term overreaction.

### H3 — Volatility Normalization

Raw price movement is not comparable across stocks. Statistical displacement must be measured relative to each stock’s own historical behavior.

---

## 4. Strategy Scope

S1 is intentionally simple.

Allowed:

- Daily OHLC data
- Close price
- Rolling mean
- Rolling standard deviation
- Z-score
- ATR or stop-distance sizing for portfolio risk management only

Not Allowed inside S1 signal generation:

- Nifty trend filter
- India VIX filter
- Sector filter
- Regime filter
- Relative strength filter
- Volume filter
- FFT
- Wavelets
- Markov chains as an S1 filter or S1 signal component
- Machine learning
- Conviction scoring

Reason:

S1 must isolate the pure Z-score mean-reversion hypothesis.

Note:

Markov logic is now allowed as the separate standalone `S2_MARKOV_STATE_TRANSITION` strategy family. It is not part of S1 and is not an S1 filter.

---

## 5. Universe

Phase 1 research universe:

- Existing selected 20-stock daily OHLC universe
- Period approximately 2018 to May 2026
- Indian equities only

Benchmark data:

- Nifty index data available for comparison only
- Nifty data may not be used as an entry or filter condition in S1

India VIX:

- Available for future strategies
- Not used in S1

Important limitation:

This universe is manually selected and may contain selection bias.

Therefore, S1 results are classified as:

> Research Backtest — Not Production Validation

---

## 6. Data Requirements

Required columns:

- Date
- Symbol
- Open
- High
- Low
- Close
- Volume

Primary price basis:

- Close price

Corporate actions:

- Corporate action data is not currently available.
- Results must be interpreted cautiously.
- Any stock with obvious split or adjustment anomalies should be flagged.

Minimum data requirement:

- At least 252 trading sessions preferred
- At least 60 trading sessions required for Phase 1 testing

---

## 7. Signal Definition

S1 uses a rolling Z-score calculated on closing price.

Conceptually:

Z-score measures how far the latest close is from its recent rolling average, expressed in units of rolling standard deviation.

A negative Z-score indicates the stock is trading below its recent average.

An extreme negative Z-score indicates a statistically oversold condition.

---

## 8. Mathematical Specification

Rolling window:

- Default = 20 trading sessions

Mean:

- 20-day rolling mean of close price

Standard deviation:

- 20-day rolling standard deviation of close price

Z-score:

Z = (Current Close - Rolling Mean) / Rolling Standard Deviation

Signal threshold:
Z <= -2.0

---

## 9. Parameters
Parameter               Value
Z-score window	    20 trading sessions
Entry threshold     	-2.0
Price basis     	    Close
Direction	          Long only

---

## 10. Candidate Ordering and Ranking Experiments

The original S1 baseline sequencing was intentionally simple.

For baseline research, same-day S1 signal ordering used only the information available in the generated signal stream and did not promote a multi-feature ranking model.

Historical simple ordering rule:

- Most negative Z-score first when same-day signals require deterministic ordering.

`candidate-ranking s1_v1` was later implemented as an opt-in capacity-aware ranking experiment.

Result:

- `candidate-ranking s1_v1` was technically valid.
- It underperformed the unranked S1 baseline.
- It is parked.

Current decision:

- No S1 ranking method is currently promoted over the unranked baseline.
- S1 ranking v2 is future research, not current behavior.
- Future ranking work should be evidence-based and should not be treated as an accepted production rule until audited.

---

## 11. Failure Modes

S1 is expected to fail or underperform during:
- Strong bear markets
- Structural downtrends
- Company-specific negative events
- Sector-wide repricing
- Earnings shocks
- Governance shocks
- Liquidity breakdowns
- Persistent momentum selloffs

Failure in these environments does not automatically invalidate S1.

The purpose of S1 is to test the baseline mean-reversion effect before adding filters.

---

## 12. Research Questions

S1 should answer:
- Does pure Z-score oversold buying have positive expectancy?
- Is performance stable across years?
- Is performance concentrated in a few symbols?
- Does ATR risk sizing control drawdown effectively?
- Are losses mostly caused by trend continuation?
- Do time-stop exits improve or hurt results?
- Is the edge strong enough to justify future filters?

---

## 13. Robustness Tests

S1 must be tested across nearby parameter values.

Z-score window sensitivity:
10, 15, 20, 25, 30

Z-score threshold sensitivity:
-1.5, -2.0, -2.5, -3.0

ATR stop multiplier sensitivity:
1.5, 2.0, 2.5, 3.0

Holding period sensitivity:
10, 15, 20, 30

Performance should not depend on one fragile parameter combination.

---

## 14. Current Research Findings

S1 baseline remains the current Veridian Quant v2 benchmark.

Current benchmark:

- Strategy: `S1_BASELINE`
- Universe: audited 200-symbol research universe
- Period: 2020-01-01 to 2026-04-30
- Net PnL: approximately +579K
- Gross profit: approximately +4.64M
- Gross loss: approximately -4.06M
- Profit factor: approximately 1.143
- Max drawdown: approximately 23.52%
- Trades: 535
- Total signals: 7,476
- Rejected signals: 6,941
- Portfolio capacity rejections: 6,726

Important findings:

- The 200-symbol universe materially outperformed the 100-symbol universe.
- S1 hard-filter variants did not generalize reliably.
- `S1_AVOID_MESSY_MIDDLE_V1` performed badly on the broader universe despite earlier promise.
- `S1_BROAD_BEST_GUESS` was conservative but did not outperform the 200-symbol baseline.
- `candidate-ranking s1_v1` was technically valid but underperformed the unranked baseline.
- S1 ranking optimization is parked for now.

Research interpretation:

- S1 is useful as the current benchmark, not as a final strategy.
- Future S1 improvements should likely use evidence-based votes or scoring rather than premature hard filters.
- Capacity-aware opportunity selection is a major open problem, but S1 ranking v1 is not enough evidence to justify more S1-only optimization immediately.

---

## 15. Parked / Future S1 Work

The following are future research directions, not accepted production rules:

- S1 candidate ranking v2
- Feature-combination diagnostics
- Evidence-based vote/scoring systems
- Defensive regime layer for difficult 2026-like conditions
- Meta-ranking or capital allocation across multiple standalone strategy families

---

## 16. References
This strategy inherits rules and constraints from:
- `docs/00_foundation/v2_design_document.md`
- `docs/00_foundation/v2_research_roadmap.md`
- `docs/03_research/market_hypotheses.md`
- `docs/04_validation/backtest_methodology.md`

S1 specifically references:
- H1 — Panic Mean Reversion
- H3 — Volatility Normalization
