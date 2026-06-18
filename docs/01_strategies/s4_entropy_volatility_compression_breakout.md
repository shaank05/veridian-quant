# S4 - Entropy / Volatility Compression Breakout

## Current Status

Status:

- Phase 29A specification only.
- No code implementation.
- No backtest runner changes.
- No production decision.
- Strategy family: standalone independent strategy.
- Not an S1/S2/S3 filter.
- Not part of a portfolio blend or voting ensemble yet.

S4 begins a new independent research family after S1, S2, and S3 have been retained only as benchmarks or parked research candidates.

---

## Strategy Identifier

`S4_ENTROPY_VOLATILITY_COMPRESSION_BREAKOUT`

---

## Strategy Family Thesis

S4 tests whether stocks emerging from unusually compressed volatility or noisy sideways structure can produce favorable long-only breakout trades.

Plain-English thesis:

> Periods of tight range, low realized movement, or reduced directional noise can precede expansion. A confirmed breakout after compression may capture the first leg of a new swing move.

Expected edge:

- Volatility compression can signal stored energy before range expansion.
- Breakout confirmation avoids entering during the compression itself.
- Long-only breakout logic may capture momentum expansion rather than mean reversion.
- Compression-aware entries may improve reward/risk compared with chasing already-extended moves.

---

## Why S4 Is Independent From S1/S2/S3

### S1

S1 buys statistically oversold mean-reversion setups using Z-score displacement.

S4 does not require oversold conditions. It waits for compression and a breakout close.

### S2

S2 buys based on historical same-state Markov transition evidence.

S4 does not use Markov state recurrence or same-state forward-return statistics.

### S3

S3 buys controlled pullbacks inside confirmed uptrends.

S4 does not require a pullback in an existing uptrend as the core event. Its core event is volatility or range compression followed by breakout confirmation.

This separation matters because S4 should test a new alpha source instead of continuing S2/S3 tuning or mixing prior filters into a new strategy.

---

## Initial Scope

Initial research scope:

- Long-only daily swing strategy.
- Indian equities in the current audited research universe.
- Daily OHLCV data only for the first baseline.
- Signal generated after the breakout session close.
- Entry at the next session open.
- Standard v2 portfolio and exit methodology when implementation begins later.

Out of scope for Phase 29A:

- Code implementation.
- Backtesting.
- Parameter tuning.
- Portfolio blending.
- S2/S3 filter mixing.
- Production promotion.

---

## Compression Feature Candidates

Initial candidate features:

- ATR percentile compression.
- Rolling high-low range compression.
- Optional entropy/noise compression.

### ATR Percentile Compression

Measure whether recent ATR percentage is low relative to the symbol's own historical ATR percentage distribution.

Possible future examples:

- ATR14 percentage.
- Rolling percentile of ATR14 percentage over a trailing lookback.
- Compression condition when ATR percentile is below a conservative threshold.

### Rolling High-Low Range Compression

Measure whether the recent trading range is unusually narrow.

Possible future examples:

- N-day high-low range as a percentage of close.
- Rolling percentile of N-day range percentage.
- Inside-range or multi-day tight-range conditions.

### Optional Entropy / Noise Compression

Measure whether recent returns show reduced randomness, reduced directional churn, or lower realized noise.

Possible future examples:

- Return sign entropy over a trailing window.
- Direction-change count.
- Choppiness-style or efficiency-ratio-style proxy.

Entropy/noise compression is optional for the first research cycle and should not complicate the baseline unless the simple ATR/range variants are already understood.

---

## Breakout Confirmation Candidates

Initial breakout confirmation candidates:

- Close above N-day high.
- Optional volume confirmation.
- Optional trend context.

### Close Above N-Day High

Core breakout condition:

- The signal-day close breaks above a trailing N-day high calculated only from data available through the signal timestamp.

Implementation later must define whether the trailing high excludes the signal day before comparison. The conservative default should avoid accidental self-reference.

### Optional Volume Confirmation

Future optional confirmation:

- Breakout-day volume above recent average volume.
- Breakout-day volume percentile above a trailing threshold.

Volume confirmation is not mandatory for the initial baseline.

### Optional Trend Context

Future optional context:

- Stock above SMA50 or SMA200.
- Nifty trend supportive.
- Relative strength versus Nifty.

Trend context is not part of Phase 29A and should not import S3 logic into S4 prematurely.

---

## Entry Rule

Entry concept:

1. Detect eligible compression using trailing signal-date data only.
2. Confirm breakout on the signal-day close.
3. Generate a long signal after the close.
4. Enter at the next session open.

No same-day entry is allowed.

---

## Exit Rules

S4 should initially use the existing conservative v2 trade mechanics when implementation begins:

- ATR-based stop.
- R-multiple target.
- Max holding period.
- Conservative same-candle handling consistent with current methodology.

Initial exit concept:

- Stop distance based on ATR at signal/entry setup time.
- Target defined as a fixed R multiple of initial risk.
- Time stop if neither stop nor target is reached within the maximum holding period.

Ambiguity handling:

- If target and stop are both touched in the same daily candle, assume stop first.
- If both are touched on the entry session, assume stop first.
- Gap handling should remain consistent with the existing backtest methodology.

---

## Initial Benchmark Variants To Research Later

These variants are names for future research only. They are not implemented in Phase 29A.

1. `S4_ATR_COMPRESSION_BREAKOUT_V1`
2. `S4_RANGE_COMPRESSION_BREAKOUT_V1`
3. `S4_ENTROPY_GATED_BREAKOUT_V1`

---

## Non-Goals

Explicit non-goals for Phase 29A:

- No S2/S3 filter mixing yet.
- No parameter tuning yet.
- No production decision yet.
- No portfolio blending yet.
- No code implementation in Phase 29A.
- No changes to production strategy code, backtest runners, tests, configs, or data files.

---

## Failure Modes

Possible S4 failure cases:

- False breakouts after compression.
- Breakout gaps create poor next-open entry prices.
- Tight ranges reflect illiquidity rather than useful compression.
- Low volatility persists instead of expanding.
- Breakout occurs into overhead supply or broader market weakness.
- Volume confirmation overfits or removes too many valid trades.
- Trend context turns S4 into a disguised S3 variant.
- Capacity conflicts select weaker breakouts when many symbols trigger together.

---

## What Success Looks Like Later

S4 should eventually be judged independently on the standard audited research universe and v2 portfolio methodology.

Success criteria:

- Positive net PnL.
- Profit factor competitive with retained S1/S2/S3 benchmarks.
- Max drawdown acceptable relative to return.
- Stable yearly behavior.
- Reasonable trade count.
- Clear evidence that compression plus breakout adds value.
- No dependence on hidden S2/S3 filters or post-hoc parameter tuning.

---

## References

This strategy inherits rules and constraints from:

- `docs/00_foundation/v2_design_document.md`
- `docs/00_foundation/v2_research_roadmap.md`
- `docs/03_research/market_hypotheses.md`
- `docs/03_research/feature_ideas.md`
- `docs/04_validation/backtest_methodology.md`
