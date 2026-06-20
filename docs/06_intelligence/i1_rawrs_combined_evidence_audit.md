# I1 RAWRS Combined Evidence and True Overlay Audit

## 1. Purpose

This Phase 30J audit consolidates the evidence accumulated for
`I1_RAWRS_MARKET_STRUCTURE_INTELLIGENCE` from the feature foundation through
cross-strategy diagnostics, keep/avoid impact analysis, and the first true S3
portfolio-overlay experiments.

The central question is whether descriptive RAWRS separation translated into a
credible portfolio rule. For the tested S3 spectral-concentration hard filter,
it did not.

## 2. Scope

The evidence covers:

- RAWRS feature and diagnostic infrastructure.
- Light-mode diagnostics for retained or benchmark S1/S2/S3/S4 outputs.
- Completed-trade keep/avoid impact diagnostics.
- Leakage-safe S3 spectral-concentration overlays at trailing percentiles 20%
  and 10%.
- The research decision for this hard-filter hypothesis.

This is a research audit, not a production approval. It does not promote RAWRS
to a strategy, signal generator, universal ranker, or live portfolio component.

## 3. RAWRS Status Summary

RAWRS remains a useful diagnostic intelligence layer. Energy and spectral
features sometimes separate trade quality, but no feature is robust across all
strategy families. The first hard-filter translation failed under true
portfolio chronology.

Current status:

- Diagnostic infrastructure: complete for the present research scope.
- Cross-strategy descriptive evidence: useful but mixed.
- Universal filtering or ranking evidence: absent.
- S3 spectral-concentration p20 and p10 hard filters: rejected.
- Production status: not approved.

## 4. Infrastructure Completed

The research sequence established:

- Trailing RAWRS feature utilities.
- Signal-time and as-of diagnostic attachment by symbol.
- Standalone light/full RAWRS diagnostic CLI and separate output folders.
- Trade, signal, rejection, bucket, year, strategy, and candidate-pool
  diagnostic exports where inputs support them.
- Completed-trade keep/avoid impact summaries and leaderboards.
- An optional, default-off S3 true-overlay path for a leakage-safe experiment.

Two correctness defects were found and fixed during this sequence:

- Diagnostic timestamps are normalized before as-of merges, preventing
  timezone-aware/timezone-naive merge failures.
- Realized R is derived as
  `rawrs_realized_r = net_pnl / initial_risk_amount` when a realized-R field is
  otherwise unavailable. Planned reward/risk is not treated as realized R.

## 5. Diagnostics Completed

RAWRS light-mode diagnostics were run against benchmark or retained outputs for:

- S1 Research200 baseline.
- S2 Markov `exclude_ret_down` full-diagnostics benchmark.
- S3 `S3_STRONG_TREND_ABOVE_SMA50_V1`.
- S4 ATR compression.
- S4 range compression.
- S4 entropy-gated compression.

These runs attached trailing RAWRS context without changing the source strategy
results. The outputs supported feature buckets, year comparisons, and subsequent
completed-trade subset diagnostics.

## 6. Cross-Strategy Bucket Findings

The broad findings were:

- Energy aggregates, especially `rawrs_meso_energy` and
  `rawrs_macro_energy`, showed some directional consistency across strategies.
- `rawrs_macro_energy` was the broadest cross-strategy candidate, although many
  effect sizes were modest.
- Spectral concentration, dominant period, and spectral entropy produced
  stronger separation in places but were strategy-specific.
- No single feature maintained strong, economically consistent separation across
  S1, S2, S3, and all S4 variants.

The correct interpretation is “useful diagnostic context,” not “universal
ranking or filtering layer.”

## 7. Keep/Avoid Impact Findings

The strongest balanced completed-trade subset diagnostics included:

- S1: `rawrs_meso_energy / avoid_buckets_1_2`.
- S2: `rawrs_fft_spectral_concentration / avoid_buckets_1_2`.
- S3: `rawrs_fft_spectral_concentration / avoid_bucket_1`.
- S4 ATR: `rawrs_macro_energy` low-bucket avoidance.
- S4 Range: `rawrs_direction_change_rate` low-bucket avoidance.
- S4 Entropy: `rawrs_fft_spectral_entropy` low-bucket avoidance.

Low-bucket avoidance appeared more credible than retaining only the highest
bucket or two. Highest-bucket rules commonly removed 60%-80% of completed trades
and were therefore dangerous to interpret as implementable portfolio rules.

These results were subset comparisons only. They did not model chronology,
capital reuse, capacity, replacement candidates, equity-dependent sizing, or
compounding.

## 8. True S3 Overlay Experiment Setup

The first true overlay tested the diagnostic S3 candidate under actual portfolio
flow:

- Strategy: `S3_STRONG_TREND_ABOVE_SMA50_V1`.
- Feature: `rawrs_fft_spectral_concentration`.
- Lookback: 252 observations.
- Minimum observations: 126.
- Rules: reject signal-time percentile at or below 20%, then 10%.
- Missing or insufficient feature history: allow, with a diagnostic decision.
- Rejection reason: `RAWRS_OVERLAY_REJECTED`.

The signal-time percentile used only feature observations at or before the
signal date. It did not use global completed-trade buckets or future-period
feature distributions.

## 9. S3 Baseline vs P20 Overlay Results

| Metric | Baseline | P20 |
|---|---:|---:|
| Net PnL | Rs 315,941 | Rs 237,420 |
| CAGR | 4.43% | 3.42% |
| Max drawdown | 28.20% | 31.45% |
| Profit factor | 1.104 | 1.079 |
| Win rate | 44.40% | 44.26% |
| Trades | 500 | 488 |
| Average PnL/trade | Rs 632 | Rs 487 |
| Mean R | 0.0682 | 0.0561 |
| Median R | -0.2319 | -0.1991 |
| RAWRS rejections | 0 | 1,060 |

P20 result: **FAIL**.

Trade-identity decomposition explained the failure:

- Baseline-only trades earned approximately Rs 54,091.
- P20-only replacement trades lost approximately Rs 56,309.
- Common trades gained approximately Rs 31,879 from changed equity and sizing,
  which was insufficient to offset the removed and replacement cohorts.

P20 mildly improved median R, average loser R, and the worst loss, but weakened
winner quality, expectancy, total return, and drawdown.

## 10. S3 Baseline vs P10 Overlay Results

| Metric | Baseline | P10 |
|---|---:|---:|
| Net PnL | Rs 315,941 | Rs 9,757 |
| CAGR | 4.43% | 0.15% |
| Max drawdown | 28.20% | 31.98% |
| Profit factor | 1.104 | 1.004 |
| Win rate | 44.40% | 42.60% |
| Trades | 500 | 493 |
| Average PnL/trade | Rs 632 | Rs 20 |
| Mean R | 0.0682 | 0.0154 |
| Median R | -0.2319 | -0.2330 |
| RAWRS rejections | 0 | 543 |

P10 result: **FAIL**.

Reducing the rejection threshold did not repair the portfolio effect:

- Removed baseline trades earned approximately Rs 145,311.
- P10-only replacement trades lost approximately Rs 160,247.
- Stop-loss counts barely improved.
- Target hits fell and time-stop PnL weakened.
- Only 2026 improved against baseline; 2020-2025 all worsened.

The less aggressive threshold was materially worse than both baseline and P20.

## 11. Why Post-Hoc Diagnostics Did Not Translate

The keep/avoid diagnostic asked what the baseline completed-trade sample would
look like after removing buckets. A true overlay asks a different question: what
happens when candidate rejection changes the portfolio path before execution?

The true overlay changed:

- Which positions occupied capacity.
- Which later candidates became executable.
- Active-symbol conflicts and capacity rejections.
- Equity available for subsequent sizing.
- Trade chronology and compounding.
- The actual candidate population, not merely a fixed completed-trade subset.

The rolling signal-time percentile also differed from a global quantile assigned
after the backtest. A feature can separate a fixed sample post hoc and still be
harmful when used causally. In both overlays, profitable baseline trades were
removed and weaker replacement trades entered.

## 12. Final Decision on S3 Spectral-Concentration Hard Filter

Reject S3 `rawrs_fft_spectral_concentration` hard-filter overlays at p20 and p10.

Consequences:

- Do not promote either overlay.
- Do not test more thresholds for the same hard-filter hypothesis unless a new
  mechanism materially changes the design.
- Do not infer that S1/S2/S4 hard filters will work from completed-trade
  diagnostics alone.
- Keep RAWRS diagnostic-only for now.

## 13. RAWRS Features Still Worth Future Research

The following remain research candidates, not accepted rules:

- `rawrs_macro_energy` for broad directional stability checks.
- `rawrs_meso_energy`, especially in S1 diagnostics.
- Spectral concentration for explanatory/stability analysis, not the rejected
  S3 hard gate.
- Dominant period in strategy-specific diagnostics.
- Spectral entropy for S4-specific explanatory analysis.
- Direction-change rate for S4 Range and broader path-quality diagnostics.

Future work should require year, symbol, and regime stability rather than one
aggregate leaderboard result.

## 14. RAWRS Features/Rules Rejected or Paused

Rejected:

- S3 spectral-concentration hard filter at p20.
- S3 spectral-concentration hard filter at p10.

Paused pending materially stronger evidence:

- Any RAWRS hard filter for S1, S2, or S4 derived only from completed-trade
  keep/avoid analysis.
- Highest-bucket-only rules that discard most candidates.
- Additional threshold sweeps for the rejected S3 mechanism.

## 15. Recommended Future RAWRS Direction

Before another true overlay:

1. Measure feature direction and effect-size stability by year, symbol, market
   regime, and strategy family.
2. Add statistical uncertainty and multiple-testing controls.
3. Analyze same-day capacity pools and replacement paths explicitly.
4. Prefer ranking-only or capacity-aware ordering hypotheses over hard gates.
5. Test soft context or exposure use only after stability evidence improves.
6. Preserve a clean diagnostic/portfolio-test separation.

## 16. Non-Goals and Guardrails

- RAWRS is not S5.
- RAWRS is not a standalone strategy or signal generator.
- RAWRS is not a production filter or universal ranker.
- Diagnostic counterfactual PnL is not actual portfolio PnL.
- No global future-informed quantile may be used in a causal overlay.
- No S1/S2/S4 trading change follows from this audit.
- No production claim follows from in-sample diagnostic separation.

## 17. Open Questions

- Are energy-feature effects statistically stable after controlling for year,
  symbol, and correlated features?
- Can same-day RAWRS ordering improve capacity selection without discarding the
  candidate pool?
- Which percentile definitions remain stable through time rather than merely
  over the full sample?
- Do RAWRS features add information beyond existing trend, volatility, and
  drawdown context?
- What walk-forward design is appropriate before any softer overlay is tested?

## 18. References

Documentation:

- `docs/06_intelligence/i1_rawrs_market_structure_intelligence.md`
- `docs/06_intelligence/i1_rawrs_signal_time_diagnostics.md`
- `docs/06_intelligence/i1_rawrs_strategy_output_compatibility.md`
- `docs/00_foundation/v2_research_roadmap.md`
- `docs/03_research/feature_ideas.md`
- `docs/03_research/rejected_ideas.md`
- `docs/05_decisions/decision_log.md`

Evidence folders:

- `reports/v2/i1_rawrs/impact_light_s1_2020_2026_research200_baseline/`
- `reports/v2/i1_rawrs/impact_light_s2_markov_2020_2026_research200_exclude_ret_down_full_diagnostics/`
- `reports/v2/i1_rawrs/impact_light_s3_trend_pullback_2020_2026_research200_strong_trend_above_sma50_v1/`
- `reports/v2/i1_rawrs/impact_light_s4_atr_compression_v1/`
- `reports/v2/i1_rawrs/impact_light_s4_range_compression_v1/`
- `reports/v2/i1_rawrs/impact_light_s4_entropy_gated_v1/`
- `reports/v2/s3_trend_pullback_2020_2026_research200_strong_trend_above_sma50_v1/`
- `reports/v2/s3_rawrs_overlay/fft_spectral_concentration_avoid_p20_v1/`
- `reports/v2/s3_rawrs_overlay/fft_spectral_concentration_avoid_p10_v1/`
