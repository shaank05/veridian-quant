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
- Cross-strategy overlap / confirmation: `docs/02_audits/cross_strategy_overlap_audit.md`
- Cross-strategy risk diagnostics: `docs/02_audits/cross_strategy_risk_diagnostic_audit.md`
- S2 state x risk / in-trade diagnostic design: `docs/03_research/s2_state_risk_intrade_diagnostic_design.md`
- Kronos external-model closeout: `docs/03_research/external_model_kronos_closeout.md`

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
| S2 guard/ranking variants | Rejected as benchmarks | Yes | Yes | Reject 2025 guard, 2025 context guard, and avoid shallow uptrend pullback; direct fixes lost too much edge or worsened drawdown/year fragility |
| S2 simple context-filter variants | Rejected | Yes | Yes | Phase 33G.1 benchmark/relative/sector context filters rejected; no second-pass variant |
| `S3_TREND_PULLBACK_CONTINUATION` | Parked / not production-ready | Yes | Yes | Retain `S3_STRONG_TREND_ABOVE_SMA50_V1` as benchmark only; do not continue variants now |
| `S4_ATR_COMPRESSION_BREAKOUT_V1` | Weak benchmark / parked | Yes | Yes | Retain as weak S4 benchmark only; not production-ready; do not continue tuning now |
| `S4_RANGE_COMPRESSION_BREAKOUT_V1` | Rejected raw baseline | Yes | Yes | Do not promote; negative PnL and high drawdown |
| `S4_ENTROPY_GATED_BREAKOUT_V1` | Not promoted / parked | Yes | Yes | Near breakeven but negative and unstable; do not promote |
| `S5_RELATIVE_STRENGTH_MOMENTUM_ROTATION` | First-pass audited / weak parked family | Yes | Yes | Simple RS rejected; Dual Momentum weak/parked; Vol-Adjusted rejected; does not challenge S2/S1/S3 |
| Benchmark/sector/cap context layer | Phase 33F.3 context audit documented | Yes | Diagnostic audit only | Retained S1-S5 trade PnL logs audited; S2 remains strongest; no context filter or strategy promotion approved |
| Cross-strategy voting / confirmation ensemble | Phase 35B/35C closed | No | Diagnostic audit only | Broad voting and generic 2+ consensus dropped; S2/S4 retained only as a parked diagnostic observation |
| Cross-strategy risk diagnostics | Phase 36B/36C closed | No | Diagnostic audit only | Liquidity retained as strongest S2 diagnostic; VIX retained only as secondary context; no risk model, filter, throttle, sizing change, or production approval |
| S2 state x risk / in-trade diagnostic design | Phase 36D docs-only design | No | Design only | Lane A entry-state x risk and Lane B in-trade state evolution designed; next gate is 36E metadata/reconstruction discovery; no dynamic exit, entry filter, state filter, risk filter, backtest, or strategy change approved |
| Kronos external-model lane | Closed after Phase 37W | No | Diagnostic only | `DOCS_ONLY_CLOSEOUT_AND_BIMONTHLY_REVIEW`; no further local inference, local patch, Research200 scaling, raw candle execution, strategy use, production use, or dependency merge approved |
| FFT strategy | Future research | No | No | Deferred; not an accepted production rule |
| Wavelet strategy | Future research | No | No | Deferred; not an accepted production rule |
| S1 ranking v2 | Future research / parked | No | No | Deferred until stronger evidence exists |
| S1/S2 voting layer | Dropped for current branch | No | Diagnostic audit only | Phase 35B/35C does not support broad voting or immediate ensemble research |
| Meta-ranking / capital allocation layer | Future research | No | No | Deferred; not current behavior |

---

## Benchmark/Sector/Cap Context Status

Phase 33E through 33E.4 completed the reusable context layer and documentation
freeze. Phase 33F through 33F.3 applied read-only context diagnostics to retained
S1-S5 trade PnL logs and documented the findings in
`docs/02_audits/s1_s5_context_audit.md`.

Current status:

- Sector proxy mapping is exact normalized-label based, not broad substring
  based.
- Conservative fallback is opt-in and flagged; default retained-strategy audits
  used no fallback.
- Missing stock and benchmark context are 0% across retained S1-S5 audits after
  the Phase 33F utility fix.
- Missing sector context reflects intentionally unmapped sector proxies under
  the conservative no-fallback policy.
- S1 remains baseline only; strong benchmark tailwind helped heavily.
- S2 remains the strongest retained candidate after context audit and was
  profitable even in negative benchmark context.
- Phase 33G.1 tested simple pre-declared S2 benchmark/relative/sector context
  filters; all were rejected.
- The original retained S2 baseline remains unchanged and no S2 context variant
  qualifies for second pass.
- Phase 34A reconstructed S2's failure mode from existing reports as
  regime/state non-stationarity plus broad stop-churn during fragile periods.
- Phase 34A.0 found existing S2 failure-audit tooling and retained/nearby
  reports, so no new failure-audit code is currently needed.
- Phase 34B documents prior S2 guard/state lessons: `exclude_ret_down` remains
  the safer benchmark; `clean_state_v1` remains only a fragile higher-return
  benchmark; no S2 variant is production-approved.
- S3 remains weak/moderate and context-sensitive.
- S4 remains a weak benchmark only; context did not rescue it.
- S5 remains weak/parked; gains concentrated in strong benchmark/sector
  contexts.
- No context filter, ranking rule, strategy change, or production approval is
  authorized.
- No context filter, including the Phase 33G.1 S2 context batch, is approved.

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

### Phase 36D S2 State x Risk / In-Trade Diagnostic Design

Phase 36D designs the next internal S2 diagnostic branch after the Phase
36B/36C risk diagnostic closeout and the Kronos lane closeout. Full design:
`docs/03_research/s2_state_risk_intrade_diagnostic_design.md`.

Decision:

- `PROCEED_TO_36E_STATE_METADATA_DISCOVERY`.
- Lane A will study S2 entry-state components against risk inputs.
- Lane B will study daily in-trade state deterioration and hypothetical
  next-open exits as audit evidence only.
- No dynamic exit, `exit if RET_DOWN` rule, entry filter, state exclusion, risk
  filter, risk sizing change, backtest implementation, production use, or
  strategy promotion is approved.

### Phase 37W Kronos External-Model Closeout

Phase 37A through 37W evaluated Kronos only as an offline
diagnostic/ranking/context candidate. The lane is separate from retained S1-S5
benchmarks and does not approve any strategy.

Decision:

- Final verdict: `DOCS_ONLY_CLOSEOUT_AND_BIMONTHLY_REVIEW`.
- No further local Kronos inference.
- No local Kronos patch now.
- No Research200 scaling.
- No raw predicted-candle execution.
- No strategy logic, backtest logic, runner, adapter, or production behavior
  change.
- No dependency merge into Veridian core.

Reason:

- 37K had 17 / 150 invalid OHLC rows = 11.33%.
- 37N had 16 / 90 invalid OHLC rows = 17.78%.
- 37T still failed output validity with 3 / 30 invalid forecast runs = 10.00%.
- 37T validity-gated rank IC and top/bottom spreads remained negative.
- Public evidence review found no direct invalid-OHLC fix, no official OHLC
  guarantee, no official repair guidance, and broader generation-quality /
  reproducibility concerns including CPU/GPU output mismatch.

Continue only a bi-monthly upstream repo/issues/model-card maturity review
unless a new approved design reopens the lane.

### Phase 36B/36C Risk Diagnostic Closeout

Phase 36B/36C evaluated cross-strategy risk diagnostics across retained S1-S5,
then added India VIX availability and VIX diagnostic outputs. Full closeout:
`docs/02_audits/cross_strategy_risk_diagnostic_audit.md`.

Decision:

- No risk model implementation.
- No VIX rule, liquidity filter, drawdown throttle, rolling-R threshold,
  benchmark-regime filter, gap filter, dynamic sizing, or production approval.
- Liquidity remains the strongest S2 risk diagnostic: S2 HIGH liquidity had
  271 trades, about Rs 970,422 net PnL, about 1.42 PF, about 49.45% win rate,
  and about -Rs 948 median PnL.
- Benchmark regime remains a strong diagnostic: S2 strong-positive benchmark
  had 127 trades, about Rs 660,713 net PnL, about 1.78 PF; strong-negative had
  42 trades, about Rs 268,996 net PnL, about 2.11 PF; ordinary negative had
  191 trades, about -Rs 94,265 net PnL, about 0.95 PF.
- VIX is retained only as a secondary diagnostic. VIX joined to 2,740 / 2,740
  retained trades with 100% coverage and 0 missing/null/nonpositive values.
- VIX x drawdown is a possible pre-registration candidate, not an approved
  throttle.

Anti-overfitting rules:

- Do not convert diagnostic buckets into filters without pre-registration.
- Do not optimize VIX thresholds after seeing outputs.
- Do not treat static liquidity, sector, or cap fields as point-in-time truth.
- Do not create symbol include/exclude rules from contributor tables.
- Do not use rolling-R thresholds without strict pre-registration.
- Do not use entry-date VIX close for next-open entries.

### Phase 35B/35C Cross-Strategy Overlap Closeout

Phase 35B/35C evaluated whether retained S1-S5 strategies supported a voting
ensemble or confirmation-based ensemble. Full closeout:
`docs/02_audits/cross_strategy_overlap_audit.md`.

Decision:

- Broad voting ensemble: dropped / not supported.
- Generic 2+ strategy consensus: dropped / not supported.
- Narrow S2/S4 confirmation: retained only as a parked diagnostic observation.
- No ensemble implementation, strategy weights, capital allocation, or
  production approval.
- Do not continue immediate ensemble research or another voting variant.

Evidence summary:

- Executed-trade confirmation was weak: S2 confirmed trades had about 0.893 PF
  and about -Rs 1.07L net PnL, while S2 unconfirmed trades had about 1.260 PF
  and about +Rs 10.79L net PnL.
- Generic 2+ confirmation had only 16 trades, about 0.766 PF, and about
  -Rs 38.5K net PnL.
- Executed same-symbol/same-day overlap was sparse, with only 11 overlap rows
  across all strategies.
- Signal overlap was larger and diagnostically useful, with 1,654 same-symbol/
  same-date events, but signal overlap is not realized PnL.
- S2/S4 remained positive across 0, 1, 3, and 5 trading-session lookbacks, but
  the most usable 5-session result was only 54 trades, about 1.23 PF, about
  +Rs 113.3K net PnL, and about -Rs 7.66K median PnL.
- Yearly stability and winner concentration remained fragile, and S3 was a
  competitive 5-session control, so S4 is not uniquely proven.

Anti-overfitting rules:

- Do not cherry-pick S2/S4 0-session or 1-session results.
- Do not add new lookbacks after seeing Phase 35C results.
- Do not use future/after-entry confirmation as implementable.
- Do not optimize by net PnL alone.
- Do not treat signal overlap as realized PnL.
- Do not rescue weak strategies through post-hoc combinations.

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
- Trades: 577
- Net PnL: about Rs 9.72L
- CAGR: about 11.32%
- Max drawdown: about 24.04%
- Profit factor: about 1.189
- Win rate: about 45.23%

Interpretation:

- Retain as the safer S2 benchmark.
- Better drawdown profile than the high-return S2 candidate.
- Still the retained S2 benchmark after Phase 33G.1 rejected simple
  context-filter variants.
- Not production-ready.

### S2 Higher-Return Research Candidate

- Strategy: `S2_MARKOV_STATE_TRANSITION`
- `markov_signal_filter = exclude_ret_down`
- `s2_candidate_ranking = clean_state_v1`
- Trades: 583
- Net PnL: about Rs 12.32L
- CAGR: about 13.52%
- Max drawdown: about 33.94%
- Profit factor: about 1.223
- Win rate: about 47.68%
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
- `S2_AVOID_BENCHMARK_20D_STRONG_NEGATIVE`
- `S2_REQUIRE_STOCK_OUTPERFORMING_BENCHMARK_20D`
- `S2_AVOID_STOCK_STRONGLY_UNDERPERFORMING_BENCHMARK_20D`
- `S2_AVOID_MAPPED_SECTOR_NEGATIVE_20D`

Reason:

The earlier guard variants addressed part of the 2025 problem, but reduced
overall portfolio quality too much or failed to preserve the targeted
improvement under the preferred filter context. The Phase 33G.1 simple
context-filter variants also failed the pre-declared acceptance criteria; no
second-pass context variant is retained.

Phase 34B reconstructed the prior-variant metrics:

| Variant | Trades | Net PnL | PF | Max DD | Win rate | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `exclude_ret_down + 2025_guard_v1` | 564 | about Rs 5.65L | 1.133 | 26.87% | 45.04% | reject |
| `exclude_ret_down + 2025_guard_v1 + signal-time context` | 561 | about Rs 4.78L | 1.116 | 26.87% | 44.56% | reject |
| `exclude_ret_down + clean_state_v1` | 583 | about Rs 12.32L | 1.223 | 33.94% | 47.68% | fragile higher-return benchmark only |
| `exclude_ret_down + avoid_shallow_uptrend_pullback_v1` | 573 | about Rs 11.10L | 1.185 | 37.42% | 46.07% | reject |

Do not remove months, symbols, sectors, or state labels directly from these
reports. Do not optimize by final PnL, treat 2025-specific failures as
production rules, or continue threshold-tweaking the same context/guard
filters. Future S2 work requires a genuinely new hypothesis.

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
- Do not continue simple S2 guard, context, or state-exclusion tuning unless a
  genuinely new hypothesis is defined.
- Freeze S3 and S4 research for now.
- Keep retained S3 and weak S4 benchmarks for comparison.
- Park S5 after the Phase 32F first-pass audit. Do not tune S5 immediately; use
  Dual Momentum only as a weak parked benchmark unless a later phase explicitly
  requests weak-benchmark Monte Carlo validation or a materially redesigned
  momentum hypothesis.
- Close the Phase 35 ensemble branch. Next preferred work should be
  cross-strategy risk-model input discovery, universe/regime segmentation
  research, or S2 risk model research rather than another voting variant.
- Prioritize the Phase 33 benchmark, sector, market-cap, regime, exposure, and
  capital-utilization context foundation before major new strategy-family
  exploration. Design reference:
  `docs/04_validation/benchmark_sector_cap_context.md`.
