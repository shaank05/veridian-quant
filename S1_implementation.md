Now we have a decision point.

There are two possible paths:

### Path A — Build S1 Immediately

Start implementing:

```text
S1 → Backtest → Audit → Results
```

Then learn from actual data.

---

### Path B — Finish Research Documentation First

Create:

```text
docs/03_research/feature_ideas.md
docs/03_research/regime_models.md
docs/03_research/portfolio_construction.md
docs/03_research/rejected_ideas.md
```

before implementation.

---

For most projects I'd recommend Path B.

For Veridian Quant, I recommend **Path A**.

Reason:

We now have enough governance.

Specifically we have:

✅ Design Document

✅ Research Roadmap

✅ Market Hypotheses

✅ Backtest Methodology

✅ S1 Strategy Specification

That is already more documentation than many professional quant projects start with.

At this point the highest value information will come from data.

---

# What I Would Do Next

Create a new document:

```text
docs/02_audits/s1_audit.md
```

We won't fill it now.

Just create it.

This will become the permanent audit record for S1.

---

Then implementation begins.

The implementation order should be:

### Step 1

Build the v2 backtest engine skeleton.

Not strategy.

Just:

```text
Data
↓
Signal
↓
Entry
↓
Position
↓
Exit
↓
Portfolio
↓
Metrics
```

---

### Step 2

Implement S1 exactly as specified.

No additions.

No improvements.

No regime filter.

No VIX.

No relative strength.

No "small enhancement."

Strictly S1.

---

### Step 3

Run first backtest.

---

### Step 4

Populate:

```text
docs/02_audits/s1_audit.md
```

with:

* CAGR
* Drawdown
* Sharpe
* Trade count
* Win rate
* Expectancy
* Failure observations

---

### Step 5

Only then decide:

```text
S2 = Regime Filter
```

or

```text
S1 failed
```

or

```text
S1 needs revision
```

---

### One Important Thing Before You Start

There is one unresolved design decision in S1:

## Z-score Formula

Currently we have:

```text
20-day rolling mean of Close
20-day rolling std dev of Close
Z <= -2.0
```

But we have not yet decided whether the baseline uses:

```text
Price Z-score
```

or

```text
Return Z-score
```

or

```text
Distance-from-moving-average Z-score
```

This is actually a very important mathematical choice.

Before implementation, I'd like us to settle that question because it fundamentally changes the behavior of S1. That is the last major research decision I see before implementation starts.


Implementation order

We should not ask Codex to build everything in one prompt.

Do it in small phases:

Project structure and config
Data loader / data contract
Indicator functions
S1 signal generator
Trade and portfolio ledger
Exit resolver
Metrics engine
Backtest runner
Report generation
Tests / validation checks