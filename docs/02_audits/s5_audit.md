# S5 First-Pass Audit

## 1. Purpose

This Phase 32F audit records the first-pass Research200 evidence for
`S5_RELATIVE_STRENGTH_MOMENTUM_ROTATION` and makes a documentation-only parking
decision.

No S5 variant is production-approved.

## 2. Scope

This audit reviews completed Phase 32E backtest reports only. It does not rerun
backtests, run Monte Carlo validation, modify reports, tune parameters, or
change source code.

## 3. Variants Tested

- `S5_SIMPLE_RS_126D_V1`
- `S5_DUAL_MOMENTUM_63_126D_V1`
- `S5_VOL_ADJUSTED_RS_V1`

All three used the audited Research200 universe, the standard 2020-01-01 to
2026-04-30 window, ranked candidate selection, five-position capacity, and the
shared ATR stop/target/time-stop portfolio mechanics.

## 4. Methodology

The audit inspected the generated CSV reports for each S5 folder and compared
the results against the retained S2 benchmark, S1 baseline, retained S3
benchmark, and weak S4 ATR benchmark.

The comparison emphasizes realized portfolio PnL, CAGR, maximum drawdown, profit
factor, trade count, yearly stability, symbol concentration, exit behavior,
R-multiple quality, and ranking/capacity diagnostics.

## 5. Report Files Reviewed

S5 report folders:

- `reports/v2/s5_momentum/research200_simple_rs_126d_v1`
- `reports/v2/s5_momentum/research200_dual_momentum_63_126d_v1`
- `reports/v2/s5_momentum/research200_vol_adjusted_rs_v1`

Core files reviewed in each S5 folder:

- `summary.csv`
- `yearly_summary.csv`
- `symbol_summary.csv`
- `exit_reason_summary.csv`
- `rejection_summary.csv`
- `r_multiple_summary.csv`
- `r_multiple_by_year.csv`
- `trade_log.csv`
- `trade_pnl_log.csv`
- `signal_log.csv`
- `equity_curve.csv`

The skipped all-signal diagnostic files were present with zero rows, consistent
with a first-pass run using the skip-all-signal-diagnostics path.

## 6. Benchmark Context

Primary benchmark:

- S2 retained Markov benchmark:
  `reports/v2/s2_markov_2020_2026_research200_exclude_ret_down_full_diagnostics`

Secondary benchmarks:

- S1 baseline: `reports/v2/s1_2020_2026_research200_baseline`
- S3 retained benchmark:
  `reports/v2/s3_trend_pullback_2020_2026_research200_strong_trend_above_sma50_v1`
- S4 ATR weak benchmark:
  `reports/v2/s4/raw_baselines/research200_atr_compression_v1`

Phase 36B/36C risk diagnostic note:

- Retained S5 trades were included in the cross-strategy risk diagnostic
  branch.
- Liquidity was useful for S2, S3, and S5, but no liquidity filter was
  approved.
- Moderate drawdown entries were weak across S2, S3, S4, and S5, but no
  drawdown throttle was approved.
- India VIX had 2,740 / 2,740 retained S1-S5 trade coverage, but remains a
  secondary diagnostic only.
- Detailed closeout:
  `docs/02_audits/cross_strategy_risk_diagnostic_audit.md`.

Benchmark summary:

| Benchmark | Net PnL | CAGR | Max DD | PF |
| --- | ---: | ---: | ---: | ---: |
| S2 retained | about Rs 971,715 | about 11.32% | about 24.04% | about 1.189 |
| S1 baseline | about Rs 579,454 | about 7.49% | about 23.52% | about 1.143 |
| S3 retained | about Rs 315,941 | about 4.43% | about 28.20% | about 1.104 |
| S4 ATR | about Rs 165,312 | about 2.45% | about 39.12% | about 1.037 |

## 7. Simple RS 126D Results

| Metric | Value |
| --- | ---: |
| Net PnL | -Rs 489,652 |
| CAGR | -10.08% |
| Max drawdown | 58.29% |
| Profit factor | 0.819 |
| Win rate | 36.49% |
| Trades | 559 |
| Average net PnL per trade | -Rs 876 |
| Signals | 4,894 |
| Rejected signals | 4,335 |
| Capacity rejections | 3,999 |
| Active-position rejections | 336 |

Simple RS failed the first-pass test. It had negative PnL, severe drawdown,
profit factor below 1.0, weak average trade quality, and poor yearly behavior.

Decision: **REJECT**.

## 8. Dual Momentum 63/126D Results

| Metric | Value |
| --- | ---: |
| Net PnL | Rs 201,219 |
| CAGR | 2.94% |
| Max drawdown | 29.10% |
| Profit factor | 1.051 |
| Win rate | 40.95% |
| Trades | 569 |
| Average net PnL per trade | Rs 354 |
| Signals | 7,027 |
| Rejected signals | 6,458 |
| Capacity rejections | 6,121 |
| Active-position rejections | 337 |

Dual Momentum was the only profitable S5 first-pass variant. However, its edge
was thin and concentrated. The top five symbols contributed about Rs 461,362,
around 229% of net PnL, while the bottom five symbols lost about -Rs 292,367,
around -145% of net PnL.

Decision: **WEAK / PARK**.

## 9. Vol-Adjusted RS Results

| Metric | Value |
| --- | ---: |
| Net PnL | -Rs 419,323 |
| CAGR | -8.23% |
| Max drawdown | 51.39% |
| Profit factor | 0.849 |
| Win rate | 37.03% |
| Trades | 559 |
| Average net PnL per trade | -Rs 750 |
| Signals | 4,894 |
| Rejected signals | 4,335 |
| Capacity rejections | 4,003 |
| Active-position rejections | 332 |

Vol-Adjusted RS was less bad than Simple RS, but still clearly failed the
first-pass test. It produced negative PnL, high drawdown, and profit factor well
below 1.0.

Decision: **REJECT**.

## 10. Cross-Variant Comparison

| Rank | Variant | Interpretation |
| ---: | --- | --- |
| 1 | Dual Momentum 63/126D | Only profitable S5 variant, but weak and concentrated |
| 2 | Vol-Adjusted RS | Negative result; better than Simple RS but still unacceptable |
| 3 | Simple RS 126D | Weakest result; negative PnL and worst drawdown |

Dual Momentum is the only S5 variant worth keeping as a weak reference. It does
not justify immediate tuning or production work.

## 11. Benchmark Comparison vs S2/S1/S3/S4

S5 does not challenge S2. S2 remains much stronger on PnL, CAGR, drawdown, and
profit factor.

S5 does not challenge S1. S1 remains stronger than all S5 variants and has a
better return/drawdown profile.

S5 does not challenge S3. Dual Momentum trails the retained S3 benchmark on PnL,
CAGR, maximum drawdown, and profit factor.

Dual Momentum beats S4 ATR only. This is not enough to promote it, because S4
ATR is already classified as a weak benchmark.

## 12. Yearly Stability

Simple RS had losing years in 2020, 2022, 2024, 2025, and 2026. Its worst year
was 2024 at about -Rs 245,052. The only strong year was 2021.

Dual Momentum was positive from 2020 through 2024, but then lost about
-Rs 264,063 in 2025 and about -Rs 125,038 in 2026. This post-2024 weakness is
material.

Vol-Adjusted RS had only one meaningfully positive year, 2021. It was negative
or near-flat across the rest of the period and especially weak in 2024.

## 13. Symbol Concentration

Simple RS was not saved by its winners. The top five symbols made about
Rs 201,048, while the bottom five lost about -Rs 224,589.

Dual Momentum showed the clearest concentration risk. The top five symbols made
about Rs 461,362, which is about 229% of total net PnL. The bottom five lost
about -Rs 292,367, about -145% of total net PnL.

Vol-Adjusted RS had a similar weak profile to Simple RS. The top five made about
Rs 227,906, while the bottom five lost about -Rs 251,642.

## 14. Exit Reason Analysis

All S5 variants made money on target hits and target gap hits. Time stops were
also positive in aggregate, which suggests that some momentum entries did
continue enough to produce partial edge.

The problem was stop-loss drag:

- Simple RS stop losses lost about -Rs 2.12M.
- Dual Momentum stop losses lost about -Rs 2.99M.
- Vol-Adjusted RS stop losses lost about -Rs 2.19M.

This profile suggests that the first-pass S5 entries sometimes captured leaders,
but the current ranking and shared exit design also admitted too many failed
momentum candidates.

## 15. R-Multiple Analysis

| Variant | Average R | Positive-R Rate | Best R | Worst R |
| --- | ---: | ---: | ---: | ---: |
| Simple RS | -0.105 | 36.49% | 4.12 | -2.58 |
| Dual Momentum | 0.045 | 40.95% | 3.05 | -2.28 |
| Vol-Adjusted RS | -0.084 | 37.03% | 4.12 | -2.58 |

Dual Momentum had the only positive average R, but the edge was small. Simple
and Vol-Adjusted had negative expectancy by R-multiple.

## 16. Ranking/Capacity Observations

All S5 signal logs contained candidate ranking metadata:

- `candidate_ranking_mode`
- `candidate_rank`
- `candidate_score`
- `candidate_pool_size_for_date`

The observed ranking mode was `s5_rank_score_desc`. No invalid-rank rejection
reason appeared in the reviewed rejection summaries.

Capacity pressure was large:

- Simple RS: 3,999 capacity rejections.
- Dual Momentum: 6,121 capacity rejections.
- Vol-Adjusted RS: 4,003 capacity rejections.

This confirms that rank order matters to S5. However, high capacity rejection
alone does not justify immediate tuning, because only Dual Momentum was even
marginally profitable and it did not beat stronger benchmarks.

## 17. Red Flags

- Simple RS and Vol-Adjusted RS had negative PnL and PF below 0.85.
- Simple RS and Vol-Adjusted RS had drawdowns above 50%.
- Dual Momentum had only 1.051 PF and about Rs 354 average net PnL per trade.
- Dual Momentum depended heavily on a few symbols.
- 2025 and 2026 were weak for Dual Momentum.
- Capacity rejections were large across all variants.
- No S5 variant challenged S2, S1, or S3.

## 18. Final Decision By Variant

| Variant | Decision | Reason |
| --- | --- | --- |
| `S5_SIMPLE_RS_126D_V1` | REJECT | Negative PnL, PF below 1.0, severe drawdown |
| `S5_DUAL_MOMENTUM_63_126D_V1` | WEAK / PARK | Only profitable S5 variant, but thin, concentrated, and weaker than S1/S2/S3 |
| `S5_VOL_ADJUSTED_RS_V1` | REJECT | Negative PnL, PF below 1.0, severe drawdown |

## 19. S5 Status After First Pass

S5 remains a researched but unapproved strategy family.

Simple RS and Vol-Adjusted RS are rejected as first-pass variants. Dual Momentum
may be kept only as a weak parked benchmark. No S5 variant is production-ready
or approved for deployment.

## 20. Recommended Next Actions

- Do not tune S5 immediately.
- Do not run Monte Carlo for all S5 variants.
- Treat Monte Carlo for Dual Momentum as optional weak-benchmark validation
  only, not a priority promotion path.
- Move future research to a new hypothesis or a materially redesigned momentum
  logic before investing in more S5 variants.
- Keep S2 as the primary robustness benchmark.

## 21. Limitations

- This is a first-pass nominal backtest audit, not a Monte Carlo robustness
  audit.
- The analysis is conditional on the Phase 32E generated reports.
- No rerun, parameter sensitivity, walk-forward, sector concentration, or
  capacity stress test was performed in this phase.
- Skipped all-signal diagnostics limit deeper accepted-versus-rejected
  opportunity analysis.
- The audit does not prove that momentum cannot work; it only rejects or parks
  these first-pass S5 definitions under the current shared portfolio design.

## 22. References

- `docs/01_strategies/s5_relative_strength_momentum_rotation.md`
- `docs/02_audits/strategy_audit_master.md`
- `docs/00_foundation/v2_research_roadmap.md`
- `docs/03_research/market_hypotheses.md`
- `docs/03_research/feature_ideas.md`
- `docs/03_research/rejected_ideas.md`
- `docs/04_validation/monte_carlo_robustness_audit.md`
- `docs/05_decisions/decision_log.md`
