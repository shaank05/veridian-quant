# Veridian Quant v2 - Backtest Methodology

## 1. Backtest Philosophy
### Principle 1 — Conservative Bias

Whenever multiple interpretations are possible, choose the interpretation that produces the worse outcome.

Backtests should underestimate reality rather than overestimate it.

---

### Principle 2 — No Future Information

At time T, the strategy may only use information available at time T.

No future price, volume, volatility, or derived information may influence decisions.

---

### Principle 3 — Tradeability Over Theoretical Accuracy

Signals must be executable in real markets.

Theoretical prices that could not realistically be achieved are not valid assumptions.

---

### Principle 4 — Portfolio Reality

Capital is finite.

All backtests must respect realistic capital allocation, position limits, and concentration constraints.

---

### Principle 5 — Reproducibility

Identical inputs must produce identical outputs.

Backtests should be deterministic and repeatable.

---

### Principle 6 — Auditability

Every trade must be explainable.

The system must retain sufficient information to reconstruct the complete decision process.

---

### Principle 7 — Simplicity Before Complexity

When two methods provide comparable performance, the simpler method is preferred.


## 2. Data Rules
**A strategy can survive a weak signal. A strategy cannot survive bad data.**

## 2.1 Approved Data Sources
Only approved datasets may be used in research, validation, and production.
Examples:

* Daily OHLCV
* Nifty 50 Index
* India VIX
* Sector indices
* Corporate actions
---

## 2.2 Corporate Action Handling
All price series must account for:
* Stock splits
* Bonus issues
* Dividends (if total-return analysis is intended)

Research must document whether prices are:

* Raw
* Split-adjusted
* Fully adjusted

A strategy may never mix adjustment methods.
---

## 2.3 Minimum Historical Depth
A stock is eligible for analysis only if sufficient history exists.
Example:
* Minimum 252 trading days for production
* Shorter windows allowed only for research experiments

Reason:
Many indicators become unstable on short histories.
---

## 2.4 Missing Data Rules
Missing observations must never be silently ignored.
Allowed:
* Explicit exclusion
* Explicit forward-fill (only when justified)

Not Allowed:
* Accidental NaN propagation
* Hidden row drops

All handling must be documented.
---

## 2.5 Universe Definition
Universe must be explicitly defined.
Examples:
* Nifty 50
* Nifty 100
* Nifty 500

Historical backtests should use historical constituents whenever practical.
Avoid using today's constituents for historical periods.

Reason:
Survivorship bias.
---

## 2.6 Benchmark Definition
Every strategy must declare its benchmark.
Examples:
* Nifty 50
* Nifty 500
* Sector benchmark

Performance without benchmark comparison is incomplete.

---

## 2.7 Timestamp Integrity
All timestamps must represent the same market session.
Research must define:
* Signal timestamp
* Entry timestamp
* Exit timestamp

No ambiguity allowed.
---

## 2.8 Data Validation Requirements
Before any backtest:
Verify:
* Duplicate rows
* Missing dates
* Invalid prices
* Negative volume
* Split anomalies
* Extreme outliers

Data validation should occur before signal generation.
---

## 2.9 Regime Data Requirements
Regime filters must be based only on information available at the signal date.
Examples:

Allowed:

* Historical Nifty trend
* Historical VIX

Not Allowed:

* Future regime classification
* Future volatility estimates
---

## 2.10 Data Provenance
Every dataset must be traceable.
Document:
* Source
* Retrieval method
* Update frequency
* Adjustment methodology

Research should always be reproducible from source data.
---

## One Additional Recommendation
Add this rule:

### 2.11 Research Universe vs Production Universe
Research Universe:
* Can be broader
* Can include experimental assets

Production Universe:
* Must satisfy liquidity requirements
* Must satisfy data quality requirements
* Must satisfy minimum history requirements

### 2.12 Benchmark, Sector, and Market-Cap Context

Future strategy audits should include benchmark, sector, and market-cap context
where data is available.

Required context should include:

* Broad-market benchmark comparison, such as Nifty 50 and Nifty 500.
* Equal-weight Research200 passive baselines where the universe is applicable.
* Sector benchmark comparison where sector index data exists.
* Market-cap segment comparison where cap-segment index data exists.
* Portfolio exposure and PnL by sector and market-cap bucket.
* Capital utilization and cash-drag diagnostics.

All reports using sector, market-cap, or index-membership classification must
label whether the classification is point-in-time or current/static.

Current/static classification may be acceptable for exploratory diagnostics, but
production-grade historical claims require point-in-time membership and
classification where practical.

Design reference:

* `docs/04_validation/benchmark_sector_cap_context.md`

## Current Data Availability

Current database contains:

- Daily OHLC data from 2018 to May 2026
- Selected universe of approximately 20 stocks
- Nifty index data
- India VIX data, likely covering a similar period
- No corporate action dataset currently available

This dataset is acceptable for Phase 1 research and framework validation.

It is not yet sufficient for final production-grade validation because:

- Universe is manually selected and may introduce selection bias.
- Corporate actions are not explicitly handled.
- Historical constituents are not available.
- Delisted or excluded securities are not represented.
- India VIX coverage must be verified.

Until these issues are resolved, all backtest results must be labeled:

> Research Backtest — Not Production Validation

## Phase 1 Data Scope

For Phase 1, Veridian Quant v2 will use the existing 20-stock daily OHLC universe, Nifty index data, and India VIX data.

The purpose of Phase 1 is not to prove final tradable edge.

The purpose is to validate:

- Backtest engine correctness
- Signal logic correctness
- Portfolio accounting correctness
- Research workflow correctness
- Initial evidence of whether the hypothesis is worth expanding

No Phase 1 result may be treated as production evidence.

## 3. Signal Generation Rules
### 3.1 Signal Evaluation Timestamp

All strategy signals are generated after the completion of a market session.

For daily strategies:

* Daily OHLCV data becomes available only after the trading session has closed.
* Indicators may use information from the completed session.
* Indicators may not use information from any future session.

---

### 3.2 Information Available To The Strategy
At signal generation time, the strategy may access:

* Historical OHLCV data up to the current session
* Historical Nifty data
* Historical India VIX data
* Historical sector data
* Historical derived indicators

The strategy may not access any information from future sessions.

---

### 3.3 Information Explicitly Forbidden
The following information is forbidden during signal generation:

* Future open prices
* Future high prices
* Future low prices
* Future close prices
* Future volume
* Future volatility
* Future regime labels
* Any value derived from future observations

Use of future information during signal generation invalidates the backtest.

---

### 3.4 Indicator Calculation Rules
All indicators must be calculated using only data available at the signal timestamp.

Rolling indicators must use trailing windows only.

Examples:

Allowed:

* 20-day rolling mean using prior observations
* 20-day rolling standard deviation
* Historical volatility

Not Allowed:

* Centered moving averages
* Future-looking smoothing
* Forward-filled future values

---

### 3.5 Signal Independence
Signal generation must be independent of trade outcome.

A signal may not be modified based on:

* Future profit
* Future drawdown
* Future regime changes

Signals must be generated before outcome evaluation.

---

### 3.6 Feature Layer Separation
Feature generation and signal generation are separate responsibilities.

Feature Layer:

* Computes measurements.
* Produces indicators.

Signal Layer:

* Consumes indicators.
* Produces trade decisions.

This separation improves auditability and prevents accidental leakage.

---

### 3.7 Regime Classification Rules
Regime classification must use only information available at the signal timestamp.

Regime models may use:

* Historical Nifty trend
* Historical volatility
* Historical VIX

Regime models may not use future market behavior.

---

### 3.8 Signal Logging Requirements
Every generated signal must record:

* Timestamp
* Symbol
* Strategy identifier
* Indicator values
* Regime classification
* Signal strength (if applicable)

Signals should be reproducible from historical data.

## 4. Trade Entry Rules
### 4.1 Entry Timing

Signals are generated after the market close of session T.

No trade may be entered during the same session that generated the signal.

Trades become eligible for execution on session T+1.

---

### 4.2 Entry Price

Phase 1 backtests will use:

Entry Price = Next Trading Session Open

This represents the earliest realistically executable price after signal generation.

---

### 4.3 Signal To Entry Relationship

A signal generated on session T may only create a trade beginning on session T+1.

No same-day execution is permitted.

---

### 4.4 Gap Risk

All overnight price gaps are considered part of the strategy.

If the market opens significantly above or below the prior close, the backtest must use the actual opening price.

No synthetic smoothing is permitted.

---

### 4.5 Missing Entry Data

If a valid opening price is unavailable:

* The trade must not be entered.
* The event should be logged.
* The signal should be marked as unexecuted.

---

### 4.6 Multiple Signals

If multiple signals are generated on the same day:

* Signals are ranked according to portfolio rules.
* Entry eligibility is determined by available capital and portfolio constraints.

---

### 4.7 Entry Audit Logging

Every executed trade must record:

* Signal date
* Entry date
* Entry price
* Symbol
* Strategy identifier
* Position size
* Market regime

## 5. Trade Exit Rules
### 5.1 Exit Philosophy

Every trade must have a predefined exit condition before entry.

The backtest may not modify exits based on future outcomes.

---

### 5.2 Profit Target Exit

A trade exits when price reaches or exceeds the predefined profit target.

Exit Reason:

TARGET_HIT

---

### 5.3 Stop Loss Exit

A trade exits when price reaches or falls below the predefined stop loss.

Exit Reason:

STOP_LOSS_HIT

---

### 5.4 Time Stop Exit

A trade exits if neither target nor stop loss has been reached within the maximum holding period.

Exit Reason:

TIME_STOP

The purpose of the time stop is to prevent capital from being trapped indefinitely in low-conviction positions.

---

### 5.5 Maximum Holding Period

The maximum holding period must be defined by the strategy specification.

Examples:

* 10 trading days
* 20 trading days
* 30 trading days

The backtest engine must enforce this limit consistently.

---

### 5.6 Exit Price Determination

Target Exit:

Exit Price = Target Price

Stop Loss Exit:

Exit Price = Stop Loss Price

Time Stop Exit:

Exit Price = Closing Price of the final holding session.

No trade may exit at the original entry price unless the market actually closes at that level.

---

### 5.7 Exit Timestamp

Every trade must record:

* Exit date
* Exit price
* Exit reason
* Holding period

---

### 5.8 Partial Exits

Phase 1 does not support partial exits.

Trades are either:

* Fully open
* Fully closed

---

### 5.9 Exit Audit Logging

Every completed trade must retain:

* Entry date
* Exit date
* Entry price
* Exit price
* Exit reason
* Holding period
* Gross return
* Net return


## 6. Ambiguity Rules
### 6.1 Ambiguity Philosophy

When price sequence cannot be known from available data, the backtest must use the conservative interpretation.

The purpose is to avoid overstating strategy performance.

---

### 6.2 Same-Candle Target And Stop Ambiguity

If both the profit target and stop loss are touched during the same daily candle, the trade must be resolved as:

Exit Reason:

STOP_LOSS_HIT

Exit Price:

Stop Loss Price

This rule applies because daily OHLC data does not reveal whether the target or stop was reached first.

---

### 6.3 Entry-Day Ambiguity

If a trade enters at the next session open and both target and stop are touched during the entry session, the same conservative rule applies:

Stop loss is assumed to occur first.

---

### 6.4 Gap Open Beyond Target

If the next session opens above the profit target, the trade exits at the opening price.

Exit Reason:

TARGET_GAP_HIT

---

### 6.5 Gap Open Below Stop Loss

If the next session opens below the stop loss, the trade exits at the opening price.

Exit Reason:

STOP_GAP_HIT

This captures overnight gap risk.

---

### 6.6 Missing Or Invalid OHLC Data

If high, low, open, or close data is missing or invalid for an active trade session:

* The trade must not be resolved using incomplete data.
* The event must be logged.
* The backtest should follow the predefined missing-data handling policy.

---

### 6.7 No Manual Override

Ambiguous outcomes may not be manually changed after reviewing results.

All ambiguity handling must be deterministic and rule-based.


## 7. Execution Costs
### 7.1 Execution Cost Philosophy

Backtests must account for trading friction.

Performance reported without execution costs is considered incomplete.

---

### 7.2 Phase 1 Cost Model

Phase 1 uses a simplified execution cost model.

The objective is to approximate real trading costs conservatively while keeping the framework simple.

---

### 7.3 Slippage Assumption

Every trade incurs slippage.

Default Phase 1 assumption:

Entry Slippage = 0.20%

Exit Slippage = 0.20%

Total Round-Trip Cost = 0.40%

These values may be adjusted during future validation studies.

---

### 7.4 Cost Application

Execution costs are applied to all completed trades.

Reported performance metrics must include:

* Gross Return
* Net Return

Net Return is the primary performance measure.

---

### 7.5 Gap Events

Gap-up and gap-down exits remain subject to execution costs.

Execution costs do not disappear during favorable gaps.

---

### 7.6 Liquidity Assumptions

Phase 1 assumes:

* Liquid large-cap equities
* Sufficient order execution capacity
* No significant market impact

Market impact models are deferred to future phases.

---

### 7.7 Cost Transparency

Every trade record should contain:

* Gross PnL
* Execution Costs
* Net PnL

This allows cost attribution analysis.

---

### 7.8 Production Validation Requirement

Before production deployment, the simplified cost model must be replaced or validated against realistic Indian market transaction costs.


## 8. Portfolio Rules

### 8.1 Portfolio Philosophy

Strategies are evaluated at the portfolio level.

The objective is not to maximize individual trade performance.

The objective is to maximize portfolio-level risk-adjusted returns while maintaining controlled and consistent risk exposure.

---

### 8.2 Initial Capital

Every backtest must declare:

- Starting Capital
- Currency
- Risk Budget
- Reinvestment Policy

Phase 1 default:

- Starting Capital = ₹10,00,000
- Currency = INR
- Capital Compounding = Enabled

---

### 8.3 Portfolio Equity

Portfolio equity represents the current account value.

Portfolio equity evolves through realized profits and losses.

Example:

Initial Equity:

₹10,00,000

After Profits:

₹11,00,000

Future position sizing calculations must use the updated portfolio equity.

The portfolio must behave as a real investment account rather than a fixed-capital simulation.

---

### 8.4 Capital Compounding

Capital compounding is enabled by default.

As portfolio equity changes, position sizing and risk budgets are recalculated using current portfolio equity.

The purpose is to simulate realistic portfolio growth and capital deployment.

---

### 8.5 Risk-Based Allocation

Phase 1 uses risk-based position sizing.

The objective is equalize portfolio risk rather than equalize capital allocation.

Position size is determined from:

- Current Portfolio Equity
- Risk Per Trade
- Entry Price
- Stop Loss Distance

Example:

Portfolio Equity = ₹10,00,000

Risk Per Trade = 1%

Maximum Risk = ₹10,000

Position size is then calculated such that a stop-loss event results in approximately ₹10,000 loss.

---

### 8.6 Volatility Normalization

Position sizing should account for volatility.

ATR-based sizing or stop-distance sizing is permitted because it is considered risk management rather than alpha generation.

The objective is to prevent highly volatile assets from consuming disproportionate portfolio risk.

---

### 8.7 Risk Budget

Every strategy must define:

- Risk Per Trade
- Maximum Portfolio Risk
- Maximum Concurrent Exposure

Phase 1 default:

- Risk Per Trade = 1% of current portfolio equity

These values may be adjusted during future validation studies.

---

### 8.8 Position Limits

The portfolio may hold multiple positions simultaneously.

The maximum number of concurrent positions must be explicitly defined by the strategy specification.

The backtest engine must enforce this limit.

---

### 8.9 Cash Handling

Unused capital remains in cash.

Cash does not generate return unless explicitly modeled.

Portfolio equity consists of:

- Cash
- Open Position Value

---

### 8.10 Signal Overflow

If more signals are generated than available portfolio capacity:

- Signals must be ranked using predefined ranking rules.
- Only the highest-ranked signals may be entered.
- Rejected signals should be logged for later analysis.

---

### 8.10.1 Counterfactual Rejected-Signal Simulation

Some research reports may simulate what would have happened if capacity-rejected signals had been taken.

These rows must be labeled as counterfactual diagnostics.

Counterfactual rejected-signal PnL is not actual portfolio PnL.

It ignores portfolio capital constraints and ledger effects. It does not update the portfolio ledger, does not consume capacity, and does not change the real trade list.

Counterfactual simulation is used only to evaluate opportunity quality and future ranking hypotheses.

It may use future prices only after the signal date, exactly like normal exit resolution for a real backtest trade.

Counterfactual PnL must not be mixed into actual portfolio performance metrics such as summary return, gross profit, gross loss, profit factor, drawdown, or equity curve.

Allowed uses:

- Estimate whether rejected capacity signals were better or worse than accepted trades.
- Diagnose same-day candidate pools.
- Evaluate future ranking or voting hypotheses.

Not allowed:

- Reporting counterfactual PnL as portfolio PnL.
- Treating counterfactual wins as executable trades.
- Using counterfactual outcomes to change historical signal generation.
- Using counterfactual outcomes as accepted production rules.

---

### 8.11 Position Independence

Each position is evaluated independently.

One position may not alter:

- Target
- Stop Loss
- Holding Period

of another position.

---

### 8.12 Sector Exposure

Phase 1 does not enforce sector limits.

Sector exposure controls may be introduced after baseline validation.

---

### 8.13 Concentration Limits

No individual position may exceed the maximum risk allocation defined by portfolio rules.

The portfolio should avoid excessive concentration in a single asset.

---

### 8.14 Research Mode vs Portfolio Mode

Backtests should support two evaluation modes.

Research Mode:

- Fixed Capital
- No Compounding

Purpose:

- Measure pure signal quality.

Portfolio Mode:

- Dynamic Portfolio Equity
- Capital Compounding Enabled

Purpose:

- Measure realistic portfolio growth.

Portfolio Mode is the default evaluation mode for Veridian Quant v2.

---

### 8.15 Portfolio Audit Logging

Every backtest must record:

- Portfolio Equity
- Cash Balance
- Open Positions
- Closed Positions
- Position Risk
- Portfolio Exposure
- Daily Equity Curve
- Drawdown Curve

Portfolio-level reporting is mandatory.

Trade-level reporting alone is insufficient.

---

### 8.16 Portfolio Capacity Release Rule

Portfolio capacity is released only after the trading session on which an existing position exits.

If a position exits on trading day T and a new signal is generated on the same trading day T, the exited position is still considered active for portfolio-capacity evaluation purposes.

Consequently:

Exit Date = T
Signal Date = T

The new signal does not inherit the released capacity from the exiting position and may be rejected if portfolio capacity is fully utilized.

Capacity becomes available starting from the next trading session.

This conservative convention prevents same-session capital reuse and avoids subtle sequencing and look-ahead biases in daily-bar backtests.

---

## 9. Performance Metrics
### 9.1 Performance Evaluation Philosophy

No single metric is sufficient to evaluate a strategy.

Strategies must be evaluated using a combination of return, risk, consistency, and capital efficiency metrics.

---

### 9.2 Primary Metrics

The following metrics are mandatory.

#### CAGR

Compound Annual Growth Rate.

Measures long-term portfolio growth.

---

#### Maximum Drawdown

Largest peak-to-trough portfolio decline.

Measures downside risk.

---

#### Sharpe Ratio

Measures risk-adjusted return using total volatility.

---

#### Sortino Ratio

Measures risk-adjusted return using downside volatility only.

---

#### Profit Factor

Profit Factor = Gross Profit / Gross Loss

Measures overall trade efficiency.

---

#### Expectancy

Average expected profit per trade.

Measures the quality of the trading edge.

---

### 9.3 Secondary Metrics

The following metrics provide additional insight.

#### Win Rate

Percentage of winning trades.

---

#### Average Win

Average profit of winning trades.

---

#### Average Loss

Average loss of losing trades.

---

#### Win/Loss Ratio

Average Win / Average Loss

Measures payoff asymmetry.

---

#### Holding Period

Average trade duration.

---

#### Exposure

Percentage of time capital is actively invested.

---

### 9.4 Portfolio Metrics

The following portfolio-level metrics are mandatory.

#### Final Portfolio Value

Portfolio value at the end of the test period.

---

#### Equity Curve

Daily portfolio value history.

---

#### Drawdown Curve

Daily drawdown history.

---

#### Capital Utilization

Average percentage of available capital deployed.

---

### 9.5 Regime Analysis

Performance must be analyzed by market regime.

Examples:

* Bull Market
* Bear Market
* High Volatility
* Low Volatility

The objective is to identify where the strategy succeeds and fails.

---

### 9.6 Attribution Analysis

Every strategy should identify the source of its edge.

Questions:

* Is performance driven by a small number of trades?
* Is performance concentrated in one market period?
* Is performance dependent on one asset?
* Is performance dependent on one regime?

---

### 9.7 Stability Analysis

Performance should be evaluated across:

* Multiple years
* Multiple market environments
* Multiple parameter configurations

Stable performance is preferred over peak performance.

### 9.7.1 Post-Backtest Monte Carlo Robustness Validation

Monte Carlo validation is applied only after a strategy has produced a completed
trade ledger. It resamples realized net trade PnL to study sequence risk,
drawdown tails, loss probability, streaks, and ruin/near-ruin risk.

Monte Carlo is not a strategy or signal generator. It does not change entries,
exits, sizing, capacity, execution, or original portfolio PnL, and it must not be
used to optimize strategy parameters or justify an overfitted strategy.

Shuffle mode permutes the same completed trades to expose sequence risk.
Bootstrap mode samples completed trades with replacement to expose empirical
mix/resampling risk. Results are conditional on the realized sample and do not
prove future profitability or model unknown future regimes.

The design contract and interpretation guardrails are defined in
`docs/04_validation/portfolio_robustness_validation.md`. The first completed
S1/S2/S3/S4 ATR comparison is documented in
`docs/04_validation/monte_carlo_robustness_audit.md`. Comparable Monte Carlo
review is now part of post-backtest validation for future strategy candidates;
it supplements, but does not replace, chronological, regime, walk-forward,
parameter-sensitivity, capacity, and production-readiness evidence.

---

### 9.8 Reporting Priority

Metrics should be reviewed in the following order:

1. Maximum Drawdown
2. Sharpe Ratio
3. Sortino Ratio
4. Profit Factor
5. Expectancy
6. CAGR
7. Win Rate

High CAGR alone is not sufficient evidence of a robust strategy.

---

### 9.9 Required Backtest Outputs

Every completed backtest should produce:

* Trade Log
* Equity Curve
* Drawdown Curve
* Summary Statistics
* Regime Analysis
* Performance Attribution Summary

Backtests without these outputs are considered incomplete.


## 10. Acceptance Criteria
### 10.1 Acceptance Philosophy

Strategies advance through a structured research pipeline.

Advancement is based on evidence rather than intuition.

A strategy must satisfy the requirements of its current stage before progressing to the next stage.

---

### 10.2 Research Candidate

A strategy qualifies as a Research Candidate when:

* A clear market hypothesis exists.
* The hypothesis is documented.
* The economic rationale is documented.
* Failure conditions are identified.
* Mathematical formulation is defined.

No implementation is required at this stage.

---

### 10.3 Validation Candidate

A strategy qualifies as a Validation Candidate when:

* Implementation is complete.
* Backtest methodology requirements are satisfied.
* No known lookahead bias exists.
* No known survivorship bias exists.
* Trade logs are available.
* Performance metrics are available.

The objective of this stage is correctness validation.

---

### 10.4 Robustness Candidate

A strategy qualifies as a Robustness Candidate when:

* Parameter sensitivity testing has been completed.
* Small parameter changes do not collapse performance.
* Performance remains stable across multiple periods.
* Performance remains stable across multiple market regimes.

The objective is to identify overfitting.

---

### 10.5 Portfolio Candidate

A strategy qualifies as a Portfolio Candidate when:

* Risk management rules are defined.
* Position sizing rules are defined.
* Portfolio-level testing has been completed.
* Capital allocation behavior is understood.

The objective is to determine whether the strategy improves portfolio performance.

---

### 10.6 Paper Trading Candidate

A strategy qualifies as a Paper Trading Candidate when:

* The strategy passes hypothesis audit.
* The strategy passes mathematical audit.
* The strategy passes robustness audit.
* The strategy passes portfolio audit.
* Monitoring requirements are defined.
* Failure conditions are defined.

The objective is real-time observation without capital risk.

---

### 10.7 Production Candidate

A strategy qualifies as a Production Candidate when:

* Paper trading results align with backtest expectations.
* No critical implementation issues exist.
* Operational procedures are documented.
* Monitoring and alerting are implemented.
* Risk controls are implemented.

Production Candidate status does not imply capital deployment approval.

---

### 10.8 Production Approved

A strategy qualifies as Production Approved when:

* Research evidence remains valid.
* Paper trading evidence remains valid.
* Portfolio behavior is understood.
* Risk behavior is understood.
* Deployment approval is explicitly granted.

Only Production Approved strategies may trade live capital.

---

### 10.9 Automatic Rejection Conditions

A strategy must be rejected or returned to research if:

* Lookahead bias is discovered.
* Survivorship bias materially impacts results.
* Parameter sensitivity indicates overfitting.
* Performance depends on a small number of trades.
* Performance depends on a single market period.
* Performance cannot be explained.

---

### 10.10 Promotion Checklist

Before moving to a higher stage, confirm:

* Hypothesis documented
* Mathematical formulation documented
* Backtest methodology followed
* Trade logs available
* Performance metrics available
* Audit completed
* Known risks documented

Incomplete documentation prevents promotion.

---

### 10.11 Veridian Quant Principle

No strategy advances because of attractive returns.

A strategy advances only when:

* The edge is understood.
* The behavior is explainable.
* The implementation is trustworthy.
* The results are reproducible.

````

---
