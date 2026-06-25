# Strategy Audit Master

## Purpose

This document tracks the current audit status of Veridian Quant v2 strategy families, variants, and research directions.

No strategy is production-approved.

---

## Detailed Strategy Audits

- S1: `docs/02_audits/s1_audit.md`
- S2: `docs/02_audits/s2_audit.md`
- S3: `docs/02_audits/s3_audit.md`
- S4: `docs/02_audits/s4_audit.md`
- S5: `docs/02_audits/s5_audit.md`

---

## Strategy Status Table

| Strategy / Component | Status | Implemented | Research Tested | Current Decision |
| --- | --- | --- | --- | --- |
| `S1_ZSCORE_MEAN_REVERSION` / `S1_BASELINE` | Current benchmark / research candidate | Yes | Yes | Keep as benchmark; do not promote to final production strategy |
| `S1_AVOID_MESSY_MIDDLE_V1` | Rejected / parked standalone filter variant | Yes | Yes | Do not promote; failed to generalize on broader universe |
| `S1_BROAD_BEST_GUESS` | Parked filter variant | Yes | Yes | Conservative, but did not beat the 200-symbol baseline |
| `candidate-ranking s1_v1` | Parked ranking experiment | Yes | Yes | Underperformed unranked baseline; do not promote |
| `S2_MARKOV_STATE_TRANSITION` safer benchmark | Frozen research benchmark | Yes | Yes | Retain `exclude_ret_down + ranking none`; not production-ready |
| `S2_MARKOV_STATE_TRANSITION` high-return candidate | Frozen research candidate | Yes | Yes | Retain `exclude_ret_down + clean_state_v1`; fragile due to 2025 |
| S2 guard/ranking variants | Rejected as benchmarks | Yes | Yes | Do not promote; improved targeted weakness but lost too much total edge |
| `S3_TREND_PULLBACK_CONTINUATION` | Parked / not production-ready | Yes | Yes | Retain `S3_STRONG_TREND_ABOVE_SMA50_V1` as benchmark only; do not continue variants now |
| `S4_ATR_COMPRESSION_BREAKOUT_V1` | Weak benchmark / parked | Yes | Yes | Retain as weak S4 benchmark only; not production-ready; do not continue tuning now |
| `S4_RANGE_COMPRESSION_BREAKOUT_V1` | Rejected raw baseline | Yes | Yes | Do not promote; negative PnL and high drawdown |
| `S4_ENTROPY_GATED_BREAKOUT_V1` | Not promoted / parked | Yes | Yes | Near breakeven but negative and unstable; do not promote |
| `S5_RELATIVE_STRENGTH_MOMENTUM_ROTATION` | First-pass audited / weak parked family | Yes | Yes | Simple RS rejected; Dual Momentum weak/parked; Vol-Adjusted rejected; does not challenge S2/S1/S3 |
| Benchmark/sector/cap context layer | Phase 33 foundation in progress | Partial | Partial | Index/context and company fundamentals data are now ingested/audited as research context; no strategy has been upgraded or approved |
| FFT strategy | Future research | No | No | Deferred; not an accepted production rule |
| Wavelet strategy | Future research | No | No | Deferred; not an accepted production rule |
| S1 ranking v2 | Future research / parked | No | No | Deferred until stronger evidence exists |
| S1/S2 voting layer | Future research | No | No | Deferred until strategy-family evidence improves |
| Meta-ranking / capital allocation layer | Future research | No | No | Deferred; not current behavior |

---

## S5 First-Pass Status

S5 Relative Strength / Momentum Rotation has completed first-pass Research200
backtests and the Phase 32F docs-only audit.

Current status:

- Design document: `docs/01_strategies/s5_relative_strength_momentum_rotation.md`.
- First-pass audit: `docs/02_audits/s5_audit.md`.
- S5 does not mix with S1/S2/S3/S4, RAWRS, Kronos, or TradingAgents in its first
  research cycle.
- S2's retained `exclude_ret_down` run remains the primary robustness benchmark;
  S1, S3, and S4 ATR are secondary benchmarks.
- S5 first-pass results do not challenge S2, S1, or S3.
- No S5 variant is production-ready or production-approved.

First-pass variant decisions:

- `S5_SIMPLE_RS_126D_V1`: rejected.
- `S5_DUAL_MOMENTUM_63_126D_V1`: weak / parked.
- `S5_VOL_ADJUSTED_RS_V1`: rejected.
- Optional later `S5_52W_HIGH_PROXIMITY_V1`

---

## Current Benchmark Evidence

### Phase 31D Robustness Ranking

The first common Monte Carlo audit used 10,000 shuffle and 10,000 bootstrap
simulations per strategy with ₹1,000,000 starting equity, seed 42, and the same
drawdown thresholds. The validation-evidence ranking is:

1. **S2 retained Markov benchmark — strongest:** highest nominal and bootstrap
   median equity, only bootstrap p05 above starting equity, and lowest bootstrap
   loss probability at 3.48%.
2. **S1 baseline — second:** good nominal return and 8.62% bootstrap loss
   probability, but bootstrap p05 falls below starting equity.
3. **S3 retained trend-pullback benchmark — weak/moderate:** weaker return edge
   and 16.25% bootstrap loss probability, despite somewhat lower drawdown-breach
   frequencies.
4. **S4 ATR compression baseline — weakest:** lowest nominal PnL, worst
   bootstrap p05 equity, 35.30% loss probability, and 56.62% probability of
   maximum drawdown >=30%.

This ranking is validation evidence, not production approval. S2 remains
regime-fragile and shows meaningful sequence risk; no strategy is
production-approved. Full evidence and limitations are in
`docs/04_validation/monte_carlo_robustness_audit.md`.

### S1 Baseline

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

Interpretation:

- S1 baseline is useful as a benchmark.
- S1 baseline is not production-ready.
- No S1 variant or ranking method currently supersedes the baseline.

### S2 Safer Benchmark

- Strategy: `S2_MARKOV_STATE_TRANSITION`
- `markov_signal_filter = exclude_ret_down`
- `s2_candidate_ranking = none`
- Net PnL: about Rs 9.72L
- CAGR: about 11.32%
- Max drawdown: about 24.04%
- Profit factor: about 1.189

Interpretation:

- Retain as the safer S2 benchmark.
- Better drawdown profile than the high-return S2 candidate.
- Not production-ready.

### S2 Higher-Return Research Candidate

- Strategy: `S2_MARKOV_STATE_TRANSITION`
- `markov_signal_filter = exclude_ret_down`
- `s2_candidate_ranking = clean_state_v1`
- Net PnL: about Rs 12.32L
- CAGR: about 13.52%
- Max drawdown: about 33.94%
- Profit factor: about 1.223
- 2025 PnL: about -Rs 7.50L

Interpretation:

- Retain as a higher-return S2 research candidate.
- Useful benchmark for future comparison.
- Not production-ready because of 2025 regime fragility and high drawdown.

### S3 Retained Benchmark

- Strategy: `S3_TREND_PULLBACK_CONTINUATION`
- Variant: `S3_STRONG_TREND_ABOVE_SMA50_V1`
- Net PnL: about Rs 3.16L
- CAGR: about 4.43%
- Max drawdown: about 28.20%
- Profit factor: about 1.104
- Trades: about 500

Interpretation:

- Best observed S3 variant.
- Retain as an S3 family benchmark only.
- Not production-ready.
- Do not continue near-term S3 variants.

### S4 Raw Baselines

Detailed audit:

- `docs/02_audits/s4_audit.md`

Scope:

- Strategy family: `S4_ENTROPY_VOLATILITY_COMPRESSION_BREAKOUT`
- Universe: audited Research200
- Period: 2020-01-01 to 2026-04-30
- Starting equity: about Rs 10,00,000
- Default v2 portfolio methodology
- No ranking
- No tuning

#### S4 ATR Compression Breakout

- Variant: `S4_ATR_COMPRESSION_BREAKOUT_V1`
- Net PnL: about +Rs 1.65L
- CAGR: about 2.45%
- Max drawdown: about 39.12%
- Profit factor: about 1.037
- Trades: 559
- Win rate: about 40.97%
- Average net PnL per trade: about +Rs 296

Interpretation:

- Best raw S4 variant.
- Retain only as a weak benchmark/research reference.
- Not production-ready because return-to-drawdown and profit factor are too weak.

#### S4 Range Compression Breakout

- Variant: `S4_RANGE_COMPRESSION_BREAKOUT_V1`
- Net PnL: about -Rs 4.13L
- CAGR: about -8.06%
- Max drawdown: about 57.79%
- Profit factor: about 0.883
- Trades: 590
- Win rate: about 37.46%
- Average net PnL per trade: about -Rs 699

Interpretation:

- Rejected as an S4 raw baseline.
- Not production-ready.

#### S4 Entropy-Gated Breakout

- Variant: `S4_ENTROPY_GATED_BREAKOUT_V1`
- Net PnL: about -Rs 1.01L
- CAGR: about -1.67%
- Max drawdown: about 35.76%
- Profit factor: about 0.975
- Trades: 589
- Win rate: about 41.09%
- Average net PnL per trade: about -Rs 172

Interpretation:

- Near breakeven but negative and unstable.
- Not promoted.
- Not production-ready.

Overall S4 decision:

- Freeze/park S4 after raw baseline research.
- Do not continue immediate S4 threshold tuning.
- Future S4 revisit requires a materially new hypothesis such as regime gating, sector context, capacity/ranking redesign, or a broader portfolio-construction reason.
- Current standard signal export does not expose S4-specific compression/breakout metadata fields, creating an auditability gap for future work.

---

## S2 Audit Findings

S2 has evidence of edge, but remains regime fragile.

The Phase 27H 2025 failure audit found:

- Failure was not driven by one symbol.
- Failure was not driven by one isolated crash month.
- Losses recurred across multiple 2025 months.
- Dominant bad pocket was `RET_UP + VOL_MID + DD_SHALLOW + not truly near lows`.
- Specific failed states were `RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW` and `RET_UP|VOL_MID|DD_SHALLOW|LOW_MID_RANGE`.
- Context failures included stock above SMA50, stock SMA50 slope positive, Nifty above SMA50, Nifty SMA50 slope positive, and shallow drawdown 0 to -5%.

Interpretation:

S2 was fooled by shallow bullish pullbacks that looked healthy but failed to mean-revert in 2025. Guard variants reduced the targeted pocket, but losses shifted to replacement candidates. The problem is broader than one simple state exclusion.

---

## Rejected S2 Variants

Rejected as benchmarks:

- `avoid_shallow_uptrend_pullback_v1`
- `exclude_ret_down + avoid_shallow_uptrend_pullback_v1`
- `exclude_ret_down + 2025_guard_v1`
- `exclude_ret_down + 2025_guard_v1 + signal-time context`

Reason:

Each variant addressed part of the 2025 problem, but reduced overall portfolio quality too much or failed to preserve the targeted improvement under the preferred filter context.

---

## Audit Rules

No strategy, variant, ranking method, or voting layer may be promoted solely because it looks attractive in a partial diagnostic.

Company fundamentals note:

- Company profile and fundamentals data are now ingested and audited as
  Research200 research data. Status is recorded in
  `docs/02_audits/company_fundamentals_audit.md`.
- This does not upgrade any strategy or approve fundamentals-derived signals.
- Current snapshot ratios and static classifications must not be used as
  historical signal-time facts without separate point-in-time-safe feature
  engineering.

Promotion requires:

- Standalone implementation evidence.
- Research-universe benchmark evidence.
- Robustness checks.
- Auditability.
- Clear separation between actual portfolio PnL and diagnostic-only counterfactual PnL.
- Regime fragility review.
- Portfolio capacity and accepted-trade-selection review.
- Benchmark-relative review against broad-market and Research200 passive
  baselines where available.
- Sector and market-cap bucket exposure review.
- Capital-utilization and cash-drag review.
- Clear labeling of point-in-time versus current/static classification when
  sector, cap, or index-membership metadata is used.

Current decision:

- Freeze S2 research for now.
- Keep both retained S2 benchmarks for comparison.
- Freeze S3 and S4 research for now.
- Keep retained S3 and weak S4 benchmarks for comparison.
- Park S5 after the Phase 32F first-pass audit. Do not tune S5 immediately; use
  Dual Momentum only as a weak parked benchmark unless a later phase explicitly
  requests weak-benchmark Monte Carlo validation or a materially redesigned
  momentum hypothesis.
- Prioritize the Phase 33 benchmark, sector, market-cap, regime, exposure, and
  capital-utilization context foundation before major new strategy-family
  exploration. Design reference:
  `docs/04_validation/benchmark_sector_cap_context.md`.
