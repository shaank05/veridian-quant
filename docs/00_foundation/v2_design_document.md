# Veridian Quant v2 Design Document

## 1. Mission Statement

Veridian Quant is a research-driven quantitative trading platform focused on identifying statistically significant swing-trading opportunities in Indian equities through robust, explainable, and auditable models.

Primary objective:

> Generate risk-adjusted returns through systematic exploitation of persistent market inefficiencies while minimizing overfitting and model fragility.

---

# 2. Core Design Principles

## Principle 1 — Hypothesis Before Indicator

No indicator may enter the system unless:

* A market hypothesis exists.
* The hypothesis can be articulated in plain English.
* Failure conditions are known.

Example:

Good:

> Panic selling creates temporary price dislocations which revert toward equilibrium.

Bad:

> RSI below 20 because backtest looked good.

---

## Principle 2 — Simplicity Wins

Given equal performance:

* simpler model beats complex model
* fewer parameters beat more parameters
* explainable beats black-box

A simple Z-score model with stable performance is preferred over a complex ensemble with marginal gains.

---

## Principle 3 — Components Must Earn Their Place

Every component must demonstrate measurable contribution.

Questions:

* Does it improve Sharpe?
* Does it reduce drawdown?
* Does it improve consistency?
* Does it improve robustness?

If not:

Remove it.

---

## Principle 4 — Portfolio First

The unit of evaluation is the portfolio.

Not:

* individual trades
* individual signals

Success is measured at portfolio level.

---

## Principle 5 — Auditability

Every decision must be explainable.

For every trade:

System should answer:

* Why entered?
* Why sized?
* Why exited?
* What regime existed?

---

## Principle 6 — Production Realism

Backtests should underestimate reality rather than overestimate it.

Assume:

* slippage
* taxes
* missed fills
* liquidity constraints

Conservative assumptions preferred.

---

# 3. Market Hypothesis

## Primary Hypothesis

Indian large-cap equities periodically experience statistically significant short-term price dislocations caused by:

* institutional rebalancing
* retail panic
* volatility shocks
* liquidity imbalances

These dislocations tend to mean revert over swing-trading horizons.

---

## Secondary Hypothesis

The probability of successful mean reversion depends on market regime.

Certain regimes favor:

* continuation

Others favor:

* reversion

Regime awareness improves risk-adjusted performance.

---

# 4. Research Pipeline

Every new idea follows:

### Stage 1

Hypothesis

↓

### Stage 2

Mathematical Representation

↓

### Stage 3

Single Signal Backtest

↓

### Stage 4

Robustness Analysis

↓

### Stage 5

Attribution Analysis

↓

### Stage 6

Portfolio Integration

↓

### Stage 7

Walk Forward Validation

↓

### Stage 8

Paper Trading

↓

### Stage 9

Production Candidate

---

# 5. v2 System Architecture

Layer 1

Data Layer

Responsibilities:

* OHLCV
* Corporate Actions
* Index Data
* VIX Data
* Sector Data

---

Layer 2

Feature Layer

Responsibilities:

Transform raw market data into measurable features.

Examples:

* Returns
* Volatility
* Z-scores
* Relative strength
* Breadth metrics

No trading decisions here.

---

Layer 3

Signal Layer

Responsibilities:

Generate trade candidates.

Output:

Signal only.

Not:

* position size
* target
* stop

---

Layer 4

Portfolio Layer

Responsibilities:

* ranking
* capital allocation
* exposure management
* risk budgeting

---

Layer 5

Execution Layer

Responsibilities:

* fills
* slippage
* commissions
* taxes

---

Layer 6

Evaluation Layer

Responsibilities:

* performance metrics
* attribution
* diagnostics

---

# 6. Initial Strategy Scope

For v2 Phase 1:

Allowed:

* Z-score mean reversion
* volatility normalization
* regime filtering

Not allowed initially:

* FFT
* Wavelets
* Markov chains
* Machine Learning
* LLMs
* Deep Learning

Reason:

Need baseline edge first.

---

# 6.1 Current Strategy Architecture Notes

Veridian Quant v2 now has two standalone research strategy families:

* S1: `S1_ZSCORE_MEAN_REVERSION`
* S2: `S2_MARKOV_STATE_TRANSITION`

S1 and S2 are independent signal-generation families.

S2 is not an S1 filter.

S1 remains the original v2 benchmark strategy.

S2 has now been researched through Phase 27J. It has evidence of edge and is retained as a benchmark/research candidate, but it is frozen and not production-ready because of regime fragility, especially in 2025/2026.

Shared components include:

* Trade setup
* Position sizing
* Trade creation
* Exit resolution
* Trade PnL
* Portfolio ledger
* CSV exporters
* Standard diagnostics where compatible

Current runner architecture:

* The S1 portfolio runner remains unchanged and continues to own S1-specific variants and S1 candidate ranking behavior.
* S2 currently has a separate Markov portfolio runner.
* Both runners use the same downstream trade mechanics after signals are generated.
* S2 ranking now has signal-time stock/Nifty/relative-strength context enrichment available before portfolio capacity decisions.
* S2 failure-audit diagnostics exist as research reporting infrastructure.

Future strategy combination, voting, meta-ranking, and capital allocation layers are future work. They are not current behavior and must not be treated as accepted production rules.

Current S2 decision:

* Keep `exclude_ret_down + ranking none` as the safer S2 benchmark.
* Keep `exclude_ret_down + clean_state_v1` as the higher-return S2 research candidate.
* Do not continue immediate S2 tuning.
* Move the next research effort to a new independent strategy family.

---

# 7. Acceptance Criteria

A component can enter production candidate status only if:

### Robustness

Parameter changes do not collapse performance.

### Stability

Works across multiple periods.

### Attribution

Adds measurable value.

### Explainability

Can be explained in plain language.

### Economic Rationale

Has believable market mechanism.

---

# 8. Known Risks

* Overfitting
* Survivorship bias
* Lookahead bias
* Regime dependency
* Data quality issues
* Signal redundancy
* Complexity creep

---

# 9. Non-Negotiable Rule

> No component enters the production strategy unless it survives hypothesis audit, mathematical audit, robustness audit, attribution audit, and portfolio audit.
