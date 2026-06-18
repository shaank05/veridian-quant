# S4 - Entropy / Volatility Compression Breakout

## Current Status

Status:

- Researched through Phase 29F raw Research200 baselines.
- Phase 29G documentation/parking complete.
- Implementation exists for feature utilities, signal generation, portfolio runner, and CLI runner.
- Raw baseline research complete.
- Frozen / parked.
- Not production-ready.
- No production decision.
- Strategy family: standalone independent strategy.
- Not an S1/S2/S3 filter.
- Not part of a portfolio blend or voting ensemble yet.

S4 tested a new independent research family after S1, S2, and S3 were retained only as benchmarks or parked research candidates.

Current decision:

- Retain `S4_ATR_COMPRESSION_BREAKOUT_V1` as a weak S4 benchmark/research reference only.
- Reject `S4_RANGE_COMPRESSION_BREAKOUT_V1` as an S4 raw baseline.
- Do not promote `S4_ENTROPY_GATED_BREAKOUT_V1`.
- Do not continue near-term S4 threshold tuning.

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

## Raw Baseline Variants

These variants were raw-tested on the audited Research200 universe using the standard v2 portfolio methodology.

1. `S4_ATR_COMPRESSION_BREAKOUT_V1`
2. `S4_RANGE_COMPRESSION_BREAKOUT_V1`
3. `S4_ENTROPY_GATED_BREAKOUT_V1`

---

## Raw Research200 Baseline Results

Backtest scope:

- Universe: audited Research200.
- Period: 2020-01-01 to 2026-04-30.
- Starting equity: about Rs 10,00,000.
- Default v2 portfolio methodology.
- No ranking.
- No tuning.
- No production decision.

### `S4_ATR_COMPRESSION_BREAKOUT_V1`

Approximate result:

- Net PnL: about +Rs 1.65L.
- CAGR: about 2.45%.
- Max drawdown: about 39.12%.
- Profit factor: about 1.037.
- Trades: 559.
- Win rate: about 40.97%.
- Average net PnL per trade: about +Rs 296.

Interpretation:

- Best of the three raw S4 variants.
- Weak positive benchmark only.
- Return-to-drawdown is poor.
- Do not promote to production.
- Do not tune further for now.

### `S4_RANGE_COMPRESSION_BREAKOUT_V1`

Approximate result:

- Net PnL: about -Rs 4.13L.
- CAGR: about -8.06%.
- Max drawdown: about 57.79%.
- Profit factor: about 0.883.
- Trades: 590.
- Win rate: about 37.46%.
- Average net PnL per trade: about -Rs 699.

Interpretation:

- Rejected as an S4 raw baseline.
- Not production-ready.
- Do not continue near-term tuning.

### `S4_ENTROPY_GATED_BREAKOUT_V1`

Approximate result:

- Net PnL: about -Rs 1.01L.
- CAGR: about -1.67%.
- Max drawdown: about 35.76%.
- Profit factor: about 0.975.
- Trades: 589.
- Win rate: about 41.09%.
- Average net PnL per trade: about -Rs 172.

Interpretation:

- Near breakeven but negative and unstable.
- Not promoted.
- Not production-ready.
- Do not continue near-term tuning.

---

## Overall S4 Conclusion

Raw S4 is technically valid but not production-ready.

The best observed variant, `S4_ATR_COMPRESSION_BREAKOUT_V1`, produced weak positive results but with drawdown too high relative to return. `S4_RANGE_COMPRESSION_BREAKOUT_V1` was clearly negative, and `S4_ENTROPY_GATED_BREAKOUT_V1` was near breakeven but negative.

Key observed weaknesses:

- Poor return-to-drawdown.
- Weak or negative profit factor.
- Poor post-2021 stability.
- Material 2022 and/or 2025/2026 weakness.
- High capacity pressure across variants.
- Heavy dependence on candidate selection.
- Current standard signal export does not expose S4-specific compression/breakout metadata fields, creating an auditability gap for future S4 work.

Current decision:

- Freeze/park S4 after Phase 29F/29G.
- Retain ATR compression breakout only as a weak benchmark/research reference.
- Do not continue immediate S4 threshold tuning.
- Revisit S4 only if a materially new hypothesis appears, such as better market-regime gating, sector context, capacity/ranking redesign, or a broader portfolio-construction reason.

---

## Non-Goals

Explicit non-goals after Phase 29G:

- No S2/S3 filter mixing.
- No further S4 parameter tuning for now.
- No production decision.
- No portfolio blending.
- No S4 ranking.
- No immediate S4 feature variants.

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

S4 has now been judged on the standard audited research universe and v2 portfolio methodology for raw baselines. Any future S4 revisit should require a materially new hypothesis rather than incremental threshold tuning.

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
