# Rejected and Parked Research Ideas

## Purpose

This document records ideas that were tested and rejected, or deliberately parked, so they are not rediscovered as if they were new.

Rejected here means rejected as a benchmark or production candidate. It does not necessarily mean the idea has no research value.

---

## Phase 36B/36C Risk Diagnostic Implementation Rejections

The Phase 36B/36C risk diagnostic branch is closed as diagnostics only. Full
audit: `docs/02_audits/cross_strategy_risk_diagnostic_audit.md`.

Rejected or not approved for implementation:

- Risk model implementation now.
- India VIX standalone rule.
- VIX level rule.
- VIX 5D change rule.
- VIX x gap rule.
- VIX x drawdown throttle without pre-registration.
- Dynamic sizing optimized by net PnL.
- Liquidity filter now.
- Drawdown throttle now.
- Rolling-R threshold now.
- Benchmark-regime filter now.
- Gap-risk filter now.
- Sector caps.
- Market-cap bucket rules.
- Symbol include/exclude rules from contributor tables.

Reason:

The diagnostics are promising but not clean enough for direct implementation.
Liquidity is the strongest S2 diagnostic, but static liquidity is not
point-in-time historical truth. VIX joined 2,740 / 2,740 retained trades with
100% coverage, but VIX effects were secondary and not universal across
strategies. Gap risk is mixed because S2 `STOP_GAP_HIT` lost about
-Rs 673,842 while `TARGET_GAP_HIT` gained about +Rs 966,904. Rolling R looked
powerful but carries high overfit risk.

Consequence:

Future risk work must begin with design-only pre-registration. Do not optimize
thresholds after seeing Phase 36 outputs, and do not use entry-date VIX close
for next-open entries.

---

## Phase 36D Immediate S2 State/Exit Rule Rejections

Phase 36D creates a diagnostic design only. Full design:
`docs/03_research/s2_state_risk_intrade_diagnostic_design.md`.

Rejected or not approved for implementation now:

- Immediate dynamic S2 exit rule.
- `exit if RET_DOWN`.
- Immediate in-trade Markov state monitoring as live trading logic.
- New S2 entry-state filter.
- New S2 state exclusion.
- Entry-state x risk filter.
- Liquidity filter.
- Drawdown/VIX/benchmark rule.
- Risk sizing change.
- Production use or strategy promotion.
- Backtest optimization before diagnostic evidence exists.

Reason:

The idea is plausible but untested. A bad in-trade state may also occur inside
winning trades, and a next-open exit after deterioration may avoid stops while
also cutting targets. Entry-state x risk findings may be unstable across years,
symbols, liquidity buckets, and small state combinations.

Consequence:

Phase 36D allowed only `PROCEED_TO_36E_STATE_METADATA_DISCOVERY`: verify state
metadata, daily state reconstruction, trade-id alignment, next-open
hypothetical exit feasibility, pre-start lookback, and safe risk-context joins
before any read-only audit helper is implemented. Any future rule must be
pre-registered after diagnostics, not inferred directly from Phase 36D.

Phase 36E update:

- Discovery reference:
  `docs/03_research/s2_state_metadata_intrade_reconstruction_discovery.md`.
- Entry-state metadata exists, but in-trade daily state paths are not stored.
- Proceed only to
  `PROCEED_TO_36F_STATE_RECONSTRUCTION_PROTOTYPE_DESIGN`.
- Still rejected/not approved: dynamic exit, `exit if RET_DOWN`, entry filter,
  state exclusion, liquidity/risk/VIX/drawdown/benchmark rule, sizing change,
  backtest optimization, production use, and strategy promotion.

---

## Phase 37B External-Model Misuse Rejections / Deferrals

Kronos is allowed only as a future offline diagnostic/ranking/context/
confirmation research candidate. Phase 37B does not approve any execution, and
Phase 37C does not approve sandbox or adapter implementation. Phase 37D does
not approve installation, model download, Hugging Face download, or inference.
Phase 37F does not approve smoke-test execution. Phase 37G creates the exact
approval checklist only and does not approve install, download, inference, or
smoke-test execution.

Phase 37H executed one explicitly approved tiny smoke test, Phase 37I reviewed
it, and Phase 37J designs a small diagnostic experiment only. These later phases
do not approve additional inference, full Research200 execution, production use,
raw forecast trading, threshold tuning, or strategy integration.

Phase 37K later executed an approved 30-forecast small diagnostic, Phase 37L
scrutinized weak/negative metrics and 17 / 150 invalid OHLC forecast path rows,
and Phase 37M designs a reproducibility/output-validity diagnostic only. These
later phases still do not approve broader inference, full Research200
execution, production use, raw forecast trading, threshold tuning, strategy
integration, or best-seed/decoding cherry-picking.

Phase 37N executed the bounded reproducibility/output-validity diagnostic and
confirmed invalid OHLC rows remained high. Phase 37O then inspected Veridian
helper scripts, local generated output schemas, and Kronos source/examples in
read-only mode. It keeps the lane blocked and selects adapter/output-validation
debug as the next gated step.

Phase 37P executed the approved tiny adapter debug and Phase 37Q defines the
output-validity policy. The policy does not approve scaling; it requires
invalid forecast runs to be excluded from signal metrics and repair to remain
visualization-only unless separately approved.

Phase 37R implements reusable output-validity helpers, and Phase 37S designs a
policy-compliant retry only. They do not approve inference. Phase 37T approval
is required before any retry execution.

Phase 37T executed the approved policy-compliant retry, but output validity
failed and validity-gated metrics remained weak/negative. Phase 37V found no
direct public invalid-OHLC fix, no official OHLC guarantee, no official repair
guidance, and broader generation-quality/reproducibility concerns including a
CPU/GPU output mismatch issue. Phase 37W closes the lane for now with
`DOCS_ONLY_CLOSEOUT_AND_BIMONTHLY_REVIEW`.

Rejected or not approved:

- Raw predicted-candle execution.
- Buy/sell rules directly from generated candles.
- Stops or targets directly from predicted OHLC.
- Treating generated candles as future truth.
- Threshold, horizon, or symbol selection after seeing PnL.
- Fine-tuning before train/validation/test split and leakage audit.
- Merging Kronos dependencies into Veridian core.
- Full Research200 inference before tiny smoke tests.
- Model download without license/model-card verification and explicit user
  approval.
- Installing Kronos dependencies into the Veridian core environment.
- Using smoke-test forecasts as strategy signals.
- Creating a production dependency on Kronos from the Veridian core package.
- Long-running GPU/cloud workflows without explicit approval.
- Running Phase 37H without a filled user approval block.
- Downloading models or tokenizers without pinned revisions.
- Changing symbols or dates after seeing smoke-test output.
- Treating smoke-test output as a trading signal.
- Treating one Phase 37H smoke-test row as evidence that Kronos is good or bad
  as a model.
- Treating a future small Phase 37K diagnostic sample as alpha proof or
  production evidence.
- Jumping from tiny/small Kronos diagnostics directly to a full Research200
  sweep.
- Scaling Kronos diagnostics after invalid OHLC rows before output validity and
  reproducibility are understood.
- Running a policy-bypassing Kronos retry.
- Filtering invalid forecast runs to improve apparent alpha rather than to
  enforce output-validity policy.
- Claiming a direct 37K-versus-retry improvement without caveating the changed
  eval/decoding policy.
- Local Kronos patching now.
- Repair-and-trade.
- Research200 scaling without concrete upstream maturity/output-validity
  improvement and separate approval.
- Reopening Kronos merely because time passed.
- Choosing the best seed or decoding setting after seeing forecast quality,
  PnL, rank IC, or invalid-row rates.
- Filtering out invalid forecast rows and then treating the remaining rows as
  strategy evidence without a predeclared validity policy.
- Scaling, retrying signal diagnostics, or running Research200 while invalid
  OHLC output validity remains unresolved.
- Repairing generated OHLC rows and then trading or evaluating alpha from the
  repaired candles without a separately approved, non-leaky policy.
- Treating visualization-only repaired candles as canonical model output.
- Comparing valid-only filtered metrics against prior unfiltered metrics as if
  the filter improved alpha.
- Choosing deterministic decoding because it improves returns rather than
  because it improves structural validity/reproducibility.

Reason:

Kronos is a forecasting model, not a trading agent. Raw forecast paths can look
attractive while failing forecast/ranking diagnostics, and stochastic inference,
normalization, de-normalization, data availability, output validity,
model-weight terms, and compute cost all need separate controls before use.

Consequence:

Any future Kronos work must start from a new approved design and must not
change S1-S5 strategy behavior. The only ongoing Kronos action after 37W is a
bi-monthly upstream review of repo/issues/model-card maturity, fixes,
prediction-quality evidence, and output-validity/reproducibility improvements.

---

## S1 Rejected / Parked Items

- `S1_AVOID_MESSY_MIDDLE_V1`: rejected as a promoted filter because it failed to generalize on the broader research universe.
- `S1_BROAD_BEST_GUESS`: parked because it was conservative but did not beat the 200-symbol baseline.
- `candidate-ranking s1_v1`: parked because it was technically valid but underperformed the unranked S1 baseline.

---

## S2 Rejected Benchmark Variants

The following S2 variants are rejected as benchmarks:

- `avoid_shallow_uptrend_pullback_v1`
- `exclude_ret_down + avoid_shallow_uptrend_pullback_v1`
- `exclude_ret_down + 2025_guard_v1`
- `exclude_ret_down + 2025_guard_v1 + signal-time context`

Reasons:

- `avoid_shallow_uptrend_pullback_v1` reduced 2025 damage when used alone, but weakened total profitability too much.
- `exclude_ret_down + avoid_shallow_uptrend_pullback_v1` improved final PnL to
  about Rs 11.10L, but PF slipped to about 1.185, max drawdown worsened to
  about 37.42%, and 2025/2026 behavior deteriorated.
- `exclude_ret_down + 2025_guard_v1` cut too much edge: about 564 trades, about
  Rs 5.65L net PnL, 1.133 PF, 26.87% max drawdown, and 45.04% win rate versus
  the safer baseline's about Rs 9.72L net PnL, 1.189 PF, and 24.04% max
  drawdown.
- `exclude_ret_down + 2025_guard_v1 + signal-time context` proved Phase 27J
  infrastructure worked, but final result remained weak: about 561 trades,
  about Rs 4.78L net PnL, about 1.116 PF, about 26.87% max drawdown, and about
  44.56% win rate. It was worse than the retained baseline and worse than the
  pure 2025 guard.

Do not revive these as direct label/month/symbol/sector removals, threshold
tweaks, or renamed guard variants.

---

## S2 Parked, Not Rejected Entirely

`S2_MARKOV_STATE_TRANSITION` itself is not rejected.

Current S2 decision:

- Retain `exclude_ret_down + ranking none` as safer S2 benchmark.
- Retain `exclude_ret_down + clean_state_v1` as higher-return research
  candidate only; it is fragile, not a safer candidate.
- Freeze S2 research for now.
- Do not continue immediate S2 tuning.
- Move to a new independent strategy.

Reason:

S2 has evidence of edge, but remains regime fragile and not production-ready.
The clean-state candidate has stronger final PnL and PF, but drawdown worsened
to about 33.94% and 2025 was about -Rs 7.50L, so it does not replace the safer
baseline. Future S2 work needs a genuinely new regime/state reliability
hypothesis rather than direct 2025-specific rules or simple state exclusions.

---

## S3 Rejected / Parked Items

`S3_TREND_PULLBACK_CONTINUATION` is technically valid but parked as a standalone strategy family.

Rejected as production candidates:

- `S3_TREND_PULLBACK_CONTINUATION_BASELINE`: weak edge, about 1.045 PF, about 31.61% max drawdown.
- `S3_STRONG_TREND_V1`: strong SMA200 slope alone worsened results versus baseline.
- `S3_ABOVE_SMA50_V1`: improved over baseline, but remained too weak as a standalone production candidate.
- `S3_CONTROLLED_PULLBACK_V1`: reduced signals but did not improve realized portfolio performance; drawdown worsened versus the retained S3 benchmark.

Benchmark-only:

- `S3_STRONG_TREND_ABOVE_SMA50_V1`: retained as the S3 benchmark, but rejected as a production candidate. Approximate result: about Rs 3.16L net PnL, about 1.104 PF, about 28.20% max drawdown.

Current S3 decision:

- Freeze S3 standalone research.
- Do not continue near-term S3 variants.
- Revisit only if regime modeling, ranking/capacity logic, sector/relative-strength features, or ensemble needs materially change.

### Rejected S3 RAWRS Hard-Filter Overlay

Rejected:

- `rawrs_fft_spectral_concentration` signal-time hard filter at p20.
- `rawrs_fft_spectral_concentration` signal-time hard filter at p10.

Reason:

- Both true portfolio backtests underperformed the retained S3 baseline despite
  promising completed-trade keep/avoid diagnostics.
- P20 worsened PnL, drawdown, profit factor, and mean R.
- P10 rejected fewer signals but performed materially worse than P20 and nearly
  eliminated total PnL.
- The filters removed profitable baseline trades, admitted losing replacement
  trades, and changed chronology, capacity, sizing, and compounding.

Decision:

- Do not test more thresholds for the same S3 hard-filter mechanism without a
  materially new hypothesis.
- RAWRS remains diagnostic-only.
- Do not implement S1/S2/S4 RAWRS hard filters from post-hoc evidence alone.

---

## S4 Rejected / Parked Items

`S4_ENTROPY_VOLATILITY_COMPRESSION_BREAKOUT` is technically valid but parked as a standalone strategy family after raw Research200 baselines.

Raw baseline scope:

- Universe: audited Research200.
- Period: 2020-01-01 to 2026-04-30.
- Default v2 portfolio methodology.
- No ranking.
- No tuning.
- No production decision.

Rejected as S4 raw baseline:

- `S4_RANGE_COMPRESSION_BREAKOUT_V1`: about -Rs 4.13L net PnL, about -8.06% CAGR, about 57.79% max drawdown, about 0.883 PF, 590 trades, and about -Rs 699 average net PnL per trade.

Not promoted:

- `S4_ENTROPY_GATED_BREAKOUT_V1`: about -Rs 1.01L net PnL, about -1.67% CAGR, about 35.76% max drawdown, about 0.975 PF, 589 trades, and about -Rs 172 average net PnL per trade. It was near breakeven but negative and unstable.

Benchmark-only:

- `S4_ATR_COMPRESSION_BREAKOUT_V1`: retained only as a weak S4 benchmark/research reference. Approximate result: about +Rs 1.65L net PnL, about 2.45% CAGR, about 39.12% max drawdown, about 1.037 PF, 559 trades, and about +Rs 296 average net PnL per trade.

Current S4 decision:

- Freeze/park S4 after Phase 29F/29G.
- Do not continue immediate S4 threshold tuning.
- Do not promote raw S4 to production.
- Revisit only if regime modeling, sector context, capacity/ranking redesign, or portfolio-construction needs materially change.

---

## S5 Rejected / Parked Items

`S5_RELATIVE_STRENGTH_MOMENTUM_ROTATION` completed its first-pass Research200
audit in Phase 32F. S5 is not production-approved.

Rejected first-pass variants:

- `S5_SIMPLE_RS_126D_V1`: rejected because it produced about -Rs 4.90L net PnL,
  about -10.08% CAGR, about 58.29% maximum drawdown, and about 0.819 profit
  factor.
- `S5_VOL_ADJUSTED_RS_V1`: rejected because it produced about -Rs 4.19L net
  PnL, about -8.23% CAGR, about 51.39% maximum drawdown, and about 0.849 profit
  factor.

Parked, not rejected:

- `S5_DUAL_MOMENTUM_63_126D_V1`: weak / parked. It was the only profitable S5
  first-pass variant, at about Rs 2.01L net PnL, about 2.94% CAGR, about 29.10%
  maximum drawdown, and about 1.051 profit factor, but it did not challenge
  S2/S1/S3 and was highly symbol-concentrated.

Current S5 decision:

- Do not tune S5 immediately.
- Do not run Monte Carlo for all S5 variants.
- Treat Dual Momentum Monte Carlo as optional weak-benchmark validation only if
  a later phase explicitly requests it.
- Revisit S5 only with a materially redesigned momentum hypothesis.

---

## Deferred Advanced Strategy Families

The following remain future research directions:

- FFT strategy.
- Wavelet strategy.
- Meta-ranking / capital allocation layer.

These are not accepted production rules.

## Cross-Strategy Voting / Confirmation Ensemble

Phase 35B/35C closes the current ensemble branch.

Rejected for current branch:

- Broad voting ensemble.
- Generic 2+ strategy consensus.
- Immediate continuation into another voting variant.

Parked diagnostic only:

- Narrow S2/S4 confirmation.

Reason:

- S2 confirmed trades were worse than S2 unconfirmed trades: 99 confirmed
  trades had about 0.893 PF and about -Rs 1.07L net PnL, while 478 unconfirmed
  trades had about 1.260 PF and about +Rs 10.79L net PnL.
- Generic 2+ confirmation had only 16 trades, about 0.766 PF, and about
  -Rs 38.5K net PnL.
- Same-day executed overlap was sparse, with only 11 same-symbol/same-day rows
  across all strategies.
- Signal overlap was diagnostically useful but is not realized PnL.
- S2/S4 survived the 5-session robustness check only weakly: 54 trades, about
  1.23 PF, about +Rs 113.3K net PnL, about 42.6% win rate, and about -Rs 7.66K
  median PnL.
- Yearly stability and winner concentration remained fragile, and S3 was a
  competitive 5-session control.

Do not use this branch to approve an ensemble, weights, allocation, production
behavior, future/after-entry confirmation, or post-hoc strategy combinations.
