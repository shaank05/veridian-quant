# S2 - Markov State Transition

## Purpose

S2 tests whether simple, explainable market states have historically led to favorable forward outcomes.

For each symbol, each trading day is classified into a discrete state using only information available through that day. The strategy then checks whether prior occurrences of the same state had favorable future returns.

S2 is a standalone strategy family.

It is not an S1 filter.

It is not part of the final production system.

---

## Strategy Identifier

`S2_MARKOV_STATE_TRANSITION`

---

## State Label Format

State labels use this format:

`RET_*|VOL_*|DD_*|LOW_*`

Example:

`RET_DOWN|VOL_MID|DD_MID|LOW_NEAR`

---

## State Dimensions

### 1. Five-Session Return Bucket

Measures recent price movement using trailing 5-session return.

Buckets:

- `RET_STRONG_DOWN`
- `RET_DOWN`
- `RET_FLAT`
- `RET_UP`
- `RET_STRONG_UP`

### 2. ATR Percent Volatility Bucket

Measures volatility using ATR as a percentage of close.

Buckets:

- `VOL_LOW`
- `VOL_MID`
- `VOL_HIGH`

### 3. Sixty-Session Drawdown Bucket

Measures current close relative to the trailing 60-session high.

Buckets:

- `DD_SHALLOW`
- `DD_MID`
- `DD_DEEP`

### 4. Distance From Sixty-Session Low Bucket

Measures current close relative to the trailing 60-session low.

Buckets:

- `LOW_NEAR`
- `LOW_MID_RANGE`
- `LOW_FAR_FROM_LOW`

---

## Markov Transition Logic

For a current signal-date candidate:

1. Build the current state label using data available through the current row only.
2. Look back over prior rows inside the configured state lookback window.
3. Keep only prior rows with the same state label.
4. A prior row is eligible only if its forward-return window is fully completed before the current row.
5. Calculate prior same-state forward returns.
6. Generate a long signal only if the same-state statistics pass the configured thresholds.

No future leakage is allowed.

Future prices after the signal date may only be used later by normal trade exit resolution, exactly as with other backtest trades.

---

## Default Parameters

- State lookback sessions: 252
- Minimum state observations: 10
- Forward return sessions: 10
- Positive return threshold: 3%
- Probability threshold: 60%
- Average forward return threshold: 1%

Signal condition:

- Same-state observation count >= 10
- Probability of forward return >= +3% is >= 60%
- Average forward return is >= +1%

---

## Signal Metadata

Each S2 signal records:

- `strategy_family`
- `state_label`
- `state_lookback_sessions`
- `state_observation_count`
- `forward_return_sessions`
- `positive_return_threshold_pct`
- `positive_transition_probability`
- `average_forward_return_pct`
- `median_forward_return_pct`
- `current_5d_return_pct`
- `current_atr_pct`
- `current_drawdown_60d_pct`
- `current_close_vs_60d_low_pct`

---

## Entry, Exit, and Risk Mechanics

S2 initially uses the same portfolio mechanics as S1:

- Entry: next session open after signal
- Stop: ATR-based
- ATR window: 14
- ATR multiplier: 2
- Reward:risk: 2
- Max holding period: 20 sessions
- Round-trip cost: 0.004
- Risk per trade: 1%
- Default max concurrent positions: 5

These mechanics are shared research infrastructure. They do not imply that S2 has the same edge as S1.

---

## Current Status

S2 status:

- Implemented
- Tests passed
- Not yet benchmarked on the audited 200-symbol research universe
- Not yet compared with S1
- Not yet part of the final system
- Not accepted as a production rule

The next research step is to run S2 independently on the audited research universe and evaluate whether it has standalone evidence.

---

## Parked / Future Work

The following are future research directions, not accepted production rules:

- S2 parameter sensitivity testing
- S2 yearly and regime attribution
- S2 comparison with S1
- Markov/S1 voting layer
- Meta-ranking / capital allocation layer
- Defensive regime layer

No combination with S1 should be introduced until S2 has standalone evidence.
