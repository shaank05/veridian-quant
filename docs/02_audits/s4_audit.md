# S4 Audit - Entropy / Volatility Compression Breakout

## Purpose

This document records the current audit status of the S4 Entropy / Volatility Compression Breakout strategy family after the first raw Research200 baseline runs.

The audit documents what was tested, what was retained only as a weak benchmark, what was rejected, and why immediate S4 tuning is parked.

No S4 variant is production-approved.

---

## Strategy Audited

Strategy family:

`S4_ENTROPY_VOLATILITY_COMPRESSION_BREAKOUT`

S4 tests long-only breakouts after prior volatility, range, or entropy/noise compression.

The strategy is independent from:

- S1 Z-score mean reversion.
- S2 Markov State Transition.
- S3 Trend Pullback Continuation.

S4 is not an S1/S2/S3 filter and is not part of a voting layer or portfolio blend.

---

## Current Status

Status:

- Implemented through feature utilities, signal generation, portfolio runner, and CLI runner.
- Raw Research200 baseline runs completed through Phase 29F.
- Documented and parked through Phase 29G.
- Technically valid.
- Frozen / parked.
- Not production-ready.
- Retained only as weak benchmark evidence.

Final current decision:

- Retain `S4_ATR_COMPRESSION_BREAKOUT_V1` as a weak S4 benchmark/research reference only.
- Reject `S4_RANGE_COMPRESSION_BREAKOUT_V1` as an S4 raw baseline.
- Do not promote `S4_ENTROPY_GATED_BREAKOUT_V1`.
- Do not continue immediate S4 threshold tuning.

---

## Raw Research200 Baseline Scope

Backtest scope:

- Universe: audited Research200.
- Period: 2020-01-01 to 2026-04-30.
- Starting equity: about Rs 10,00,000.
- Default v2 portfolio methodology.
- No ranking.
- No tuning.
- No production decision.

Methodology:

- Signal generated after breakout close.
- Entry at next session open through existing setup logic.
- ATR-based stop.
- R-multiple target.
- Max holding period.
- Position sizing.
- PnL calculation.
- Ledger/equity compounding.
- Capacity handling.
- Active-symbol conflict handling.
- Conservative exit behavior from the existing exit resolver.

---

## Variant Results Table

| Variant | Net PnL | CAGR | Max DD | PF | Trades | Win Rate | Avg Net PnL / Trade | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `S4_ATR_COMPRESSION_BREAKOUT_V1` | about +Rs 1.65L | about 2.45% | about 39.12% | about 1.037 | 559 | about 40.97% | about +Rs 296 | Retain as weak benchmark only |
| `S4_RANGE_COMPRESSION_BREAKOUT_V1` | about -Rs 4.13L | about -8.06% | about 57.79% | about 0.883 | 590 | about 37.46% | about -Rs 699 | Rejected raw baseline |
| `S4_ENTROPY_GATED_BREAKOUT_V1` | about -Rs 1.01L | about -1.67% | about 35.76% | about 0.975 | 589 | about 41.09% | about -Rs 172 | Not promoted |

---

## Variant-Level Interpretation

### `S4_ATR_COMPRESSION_BREAKOUT_V1`

Interpretation:

- Best of the three raw S4 variants.
- Positive net PnL, but the edge is weak.
- Profit factor is only about 1.037.
- Max drawdown is high at about 39.12%.
- Average net PnL per trade is small relative to portfolio volatility.

Decision:

- Retain as weak S4 benchmark/research reference only.
- Do not promote to production.
- Do not tune further for now.

### `S4_RANGE_COMPRESSION_BREAKOUT_V1`

Interpretation:

- Negative net PnL.
- Weak win rate.
- Profit factor below 1.
- Max drawdown is very high at about 57.79%.
- Average net PnL per trade is materially negative.

Decision:

- Reject as S4 raw baseline.
- Do not promote.
- Do not tune further for now.

### `S4_ENTROPY_GATED_BREAKOUT_V1`

Interpretation:

- Near breakeven but negative.
- Profit factor below 1.
- Drawdown remains high relative to return.
- Entropy gate did not produce a production-quality improvement.

Decision:

- Do not promote.
- Keep only as not-promoted research evidence.
- Do not tune further for now.

---

## Key Weaknesses

Observed weaknesses:

- Poor return-to-drawdown.
- Weak or negative profit factor.
- Poor post-2021 stability.
- Material weakness in 2022 and/or 2025/2026.
- High capacity pressure across variants.
- Candidate selection remains a major bottleneck.
- Current standard signal export does not expose S4-specific compression/breakout metadata fields, creating an auditability gap for future work.

Raw S4 is not useless, but the current evidence is not strong enough for production promotion or immediate threshold tuning.

---

## Capacity / Rejection Pressure

S4 generated enough opportunity flow for portfolio capacity to matter.

Audit interpretation:

- Same-day candidate ordering can materially affect realized results.
- Capacity pressure makes accepted-trade results sensitive to candidate selection.
- Without S4-specific ranking or better portfolio construction, raw S4 may accept weak breakouts while rejecting stronger alternatives.
- Counterfactual rejected-signal analysis, if added later, must remain diagnostic only and not be mixed into actual portfolio PnL.

No S4 ranking is accepted in the current phase.

---

## Exit / R-Multiple Concerns

S4 used the shared v2 exit framework:

- ATR stop.
- R-multiple target.
- Max holding period.
- Conservative same-candle ambiguity handling.

Audit concerns:

- Breakout entries can gap or extend before the next-session open, weakening reward/risk.
- False breakouts can hit ATR stops quickly.
- The raw variants did not show strong enough R-multiple quality to offset drawdown.
- Further exit tuning would risk overfitting unless supported by a materially new hypothesis.

---

## Yearly Stability Concerns

The raw S4 baseline evidence is not stable enough for production.

Observed concerns:

- Poor post-2021 stability.
- Material weakness in 2022 and/or 2025/2026.
- Weak or negative profit factor across raw variants.
- High drawdown relative to total return.

S4 should not be judged only by the weak positive ATR-compression total PnL. Yearly behavior and drawdown quality matter.

---

## Auditability Gap

Current standard signal export does not expose S4-specific compression/breakout metadata fields.

Audit impact:

- S4 signal logs may not fully expose ATR percentile, range percentile, entropy, prior compression values, and breakout-level fields in standard CSV exports.
- This limits future post-run diagnostics unless exporter compatibility is extended.
- The gap does not invalidate the raw baseline, but it should be addressed before any future serious S4 audit or tuning cycle.

This is future infrastructure work only. It does not authorize immediate S4 tuning.

---

## Final Audit Decision

Decision:

- S4 is technically valid but not production-ready.
- Raw S4 is frozen/parked after Phase 29F/29G.
- `S4_ATR_COMPRESSION_BREAKOUT_V1` is retained only as a weak benchmark.
- `S4_RANGE_COMPRESSION_BREAKOUT_V1` is rejected.
- `S4_ENTROPY_GATED_BREAKOUT_V1` is not promoted.
- No more immediate S4 tuning.

Rationale:

- ATR compression was weakly positive but had poor return-to-drawdown.
- Range compression was clearly negative.
- Entropy gating was near breakeven but negative and unstable.
- Capacity pressure and candidate selection remain unresolved.
- Standard export auditability for S4-specific metadata is incomplete.

---

## Future Revisit Conditions

S4 may be revisited only if a materially new hypothesis appears, such as:

- Better market-regime gating.
- Sector or industry context.
- Capacity/ranking redesign.
- Broader portfolio-construction reason.
- Exporter/audit improvements that expose S4-specific compression and breakout metadata.

Any future S4 revisit should be framed as new research, not incremental threshold tuning.

---

## Explicit Non-Goals

Current non-goals:

- No production decision.
- No immediate S4 threshold tuning.
- No S4 ranking.
- No S2/S3 filter mixing.
- No portfolio blending.
- No claims that S4 is live-ready.
- No use of S4 as anything beyond a weak benchmark/research reference.
