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

Not Allowed:

- Nifty trend filter
- India VIX filter
- Sector filter
- Regime filter
- Relative strength filter
- Volume filter
- FFT
- Wavelets
- Markov chains
- Machine learning
- Conviction scoring

Reason:

S1 must isolate the pure Z-score mean-reversion hypothesis.

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

## 10. Ranking Logic 

If multiple S1 signals occur on the same date and portfolio capacity is limited, signals are ranked by Z-score severity.

Priority:
Most negative Z-score first

Example:
Symbol	    Z-score	    Priority
Stock A	    -3.1	        1
Stock B	    -2.6	        2
Stock C	    -2.1	        3

No other ranking variable is allowed in S1.

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

## 14. References
This strategy inherits rules and constraints from:
- `docs/00_foundation/v2_design_document.md`
- `docs/00_foundation/v2_research_roadmap.md`
- `docs/03_research/market_hypotheses.md`
- `docs/04_validation/backtest_methodology.md`

S1 specifically references:
- H1 — Panic Mean Reversion
- H3 — Volatility Normalization