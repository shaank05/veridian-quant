# S3 Audit - Trend Pullback Continuation

## 1. Status

Strategy: `S3_TREND_PULLBACK_CONTINUATION`

Status:

- Researched through Phase 28F.
- Parked / frozen.
- Technically valid.
- Not production-ready.
- Retained only as a research benchmark.
- Not part of an ensemble, voting layer, FFT model, or wavelet model.

Final S3 decision:

- Do not continue near-term S3 variant work.
- Retain `S3_STRONG_TREND_ABOVE_SMA50_V1` as the S3 benchmark only.
- Do not deploy S3 live.

---

## Phase 36B/36C Risk Diagnostic Note

Phase 36B/36C cross-strategy risk diagnostics included retained S3 trades, but
did not approve an S3 filter, VIX rule, risk model, drawdown throttle, dynamic
sizing rule, or production use.

Relevant cross-strategy findings:

- Liquidity was useful for S2, S3, and S5, but not universal across all
  strategies.
- Moderate drawdown entries were weak across S2, S3, S4, and S5.
- India VIX had 2,740 / 2,740 retained S1-S5 trade coverage, but remains a
  secondary diagnostic only.

Detailed closeout: `docs/02_audits/cross_strategy_risk_diagnostic_audit.md`.

---

## 2. Strategy Thesis

S3 tested trend pullback continuation.

Plain-English thesis:

> Buy structurally strong stocks after controlled pullbacks, not broken stocks after panic.

The strategy uses daily OHLCV data. Signals are generated at the signal-day close, and accepted entries use the next-day open. Downstream trade setup, position sizing, exits, PnL, and ledger mechanics use the existing v2 portfolio engine.

---

## 3. Tested Universe and Methodology

Research setup:

- Universe: audited research200 NSE equity universe.
- Period: 2020-01-01 to 2026-04-30.
- Starting equity: 1,000,000.
- Risk per trade: 1%.
- Max concurrent positions: 5.
- Stop: 14-day ATR, 2x.
- Target: 2R.
- Max holding: 20 sessions.
- Round-trip cost: 0.4%.
- Equity: compounded.
- Same-candle ambiguity: conservative stop-first behavior.

The S3 tests used actual portfolio results, not only accepted-trade diagnostics.

---

## 4. Baseline Result

Variant: `S3_TREND_PULLBACK_CONTINUATION_BASELINE`

Approximate result:

- Net PnL: about Rs 1.42L.
- CAGR: about 2.11%.
- Max drawdown: about 31.61%.
- Profit factor: about 1.045.
- Trades: 515.
- Signals: 8,784.
- Rejected signals: 8,269.

Conclusion:

- Technically valid but strategically weak.
- Weak edge.
- Too much stop-loss drag.
- Not production-worthy.

---

## 5. Diagnostic Findings

Phase 28D diagnostics showed:

- Many trend-pullback entries were early breakdowns.
- Strong long-term trend helped in combination with other filters, but not by itself.
- Below-SMA50 trades were damaging, especially in 2025/2026.
- Tight ATR filters were not an obvious improvement.
- Accepted-trade diagnostics suggested controlled 5-day pullbacks were better than very deep short-term pullbacks.

Important interpretation:

Accepted-trade diagnostics generate hypotheses, but they are not portfolio PnL. Changing signal rules changes the candidate pool, same-day capacity conflicts, active-trade conflicts, ordering, compounding path, and final realized ledger. This mattered for S3: `return_5d_pct >= -6` looked promising diagnostically but did not improve the actual controlled-pullback portfolio variant.

---

## 6. Variant Comparison

| Variant | Extra rule | Net PnL | CAGR | Max DD | PF | Trades | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `S3_TREND_PULLBACK_CONTINUATION_BASELINE` | None | about Rs 1.42L | about 2.11% | about 31.61% | about 1.045 | 515 | Rejected as production candidate |
| `S3_STRONG_TREND_V1` | `sma200_slope_20d_pct > 1.0` | about Rs 0.98L | about 1.49% | about 31.48% | about 1.035 | 505 | Rejected |
| `S3_ABOVE_SMA50_V1` | `close_vs_sma50_pct >= 0` | about Rs 1.84L | about 2.70% | about 29.96% | about 1.061 | 506 | Improved but weak |
| `S3_STRONG_TREND_ABOVE_SMA50_V1` | Strong trend plus above SMA50 | about Rs 3.16L | about 4.43% | about 28.20% | about 1.104 | 500 | Retain as benchmark only |
| `S3_CONTROLLED_PULLBACK_V1` | Strong trend, above SMA50, `return_5d_pct >= -6` | about Rs 3.07L | about 4.32% | about 30.72% | about 1.100 | 497 | Rejected |

`S3_STRONG_TREND_ABOVE_SMA50_V1` also produced about 5,110 signals and 4,610 rejected signals.

`S3_CONTROLLED_PULLBACK_V1` produced about 4,582 signals, 4,085 rejected signals, and about 43.46% win rate.

---

## 7. Failure Analysis

S3's main issue is not technical implementation. It is strategic quality.

Observed failure modes:

- Stop-loss drag remained persistent.
- Drawdown stayed high relative to return.
- Yearly behavior was unstable.
- Shallow clean pullbacks were weaker than expected.
- Trend confirmation did not fully distinguish healthy pullbacks from early breakdowns.
- Filtering reduced signals, but did not reliably improve the realized portfolio path.

The best S3 result remained materially weaker than retained S1/S2 candidates.

---

## 8. Overfitting Notes

S3 variant work reached the point where additional threshold tuning risks overfitting.

Reasons:

- Improvements were small relative to drawdown.
- Some accepted-trade diagnostic hypotheses failed in actual portfolio reruns.
- Additional simple filters risk optimizing the 2020-2026 path rather than finding robust continuation edge.
- Capacity, ordering, and active-trade conflicts make single-feature conclusions fragile.

No more near-term S3 variants should be implemented without a materially new hypothesis.

---

## 9. Final Decision

Decision:

- Freeze S3 standalone research.
- Park S3 as not production-ready.
- Retain one benchmark only: `S3_STRONG_TREND_ABOVE_SMA50_V1`.
- Reject baseline, strong-trend-only, above-SMA50-only, and controlled-pullback variants as production candidates.

Rationale:

- S3 is technically valid but weak.
- Best S3 variant remains low-PF and high-drawdown.
- Controlled pullback did not improve realized performance.
- More S3 tuning is likely to overfit.

---

## 10. Retained Benchmark

Retained S3 benchmark:

`S3_STRONG_TREND_ABOVE_SMA50_V1`

Role:

- S3 family comparison benchmark.
- Not production-ready.
- Not the recommended live strategy.

Approximate benchmark result:

- Net PnL: about Rs 3.16L.
- CAGR: about 4.43%.
- Max drawdown: about 28.20%.
- Profit factor: about 1.104.
- Trades: about 500.

---

## 11. Rejected Variants

Rejected as production candidates:

- `S3_TREND_PULLBACK_CONTINUATION_BASELINE`
- `S3_STRONG_TREND_V1`
- `S3_ABOVE_SMA50_V1`
- `S3_STRONG_TREND_ABOVE_SMA50_V1`
- `S3_CONTROLLED_PULLBACK_V1`

Note:

`S3_STRONG_TREND_ABOVE_SMA50_V1` is retained as a benchmark, but rejected as a production candidate.

---

## 12. Conditions for Future Revisit

S3 may be revisited only if one of these changes materially:

- A broader market-regime model is added.
- Ranking or capacity logic materially changes.
- Sector or relative-strength features are redesigned.
- A later ensemble phase needs a trend-continuation leg for diversification.

Until then, S3 is parked.
