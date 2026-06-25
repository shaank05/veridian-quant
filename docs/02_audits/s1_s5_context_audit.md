# S1-S5 Benchmark/Sector Context Audit

## Purpose

This Phase 33F.3 audit freezes the interpretation of the Phase 33F and 33F.2
trade-context diagnostics before any controlled S2 context experiments.

The audit is diagnostic only. It does not approve filters, strategy changes,
production deployment, or live signal behavior.

## Scope

Phase 33F implemented a read-only trade context audit utility that annotates
existing trade logs with benchmark and sector context known on or before each
trade entry/context date.

Phase 33F.2 ran the audit on retained S1-S5 `trade_pnl_log.csv` files:

- S1: `reports/v2/s1_2020_2026_research200_baseline/trade_pnl_log.csv`
- S2: `reports/v2/s2_markov_2020_2026_research200_exclude_ret_down_full_diagnostics/trade_pnl_log.csv`
- S3: `reports/v2/s3_trend_pullback_2020_2026_research200_strong_trend_above_sma50_v1/trade_pnl_log.csv`
- S4: `reports/v2/s4/raw_baselines/research200_atr_compression_v1/trade_pnl_log.csv`
- S5: `reports/v2/s5_momentum/research200_dual_momentum_63_126d_v1/trade_pnl_log.csv`

Outputs are under `reports/phase_33f2_trade_context_audit/`, including
`cross_strategy_summary.csv`.

## Summary Table

| Strategy | Trades | Win Rate | Net PnL | PF | Mapped Sector Context | Missing Stock | Missing Benchmark | Missing Sector | Context Interpretation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| S1 baseline | 535 | 46.17% | Rs 579,454 | 1.143 | 49.35% | 0.00% | 0.00% | 50.65% | Strong benchmark 20D bucket carried most gains. |
| S2 retained exclude-ret-down | 577 | 45.23% | Rs 971,715 | 1.189 | 40.21% | 0.00% | 0.00% | 59.79% | Strongest overall and profitable even in negative benchmark context. |
| S3 retained strong trend above SMA50 | 500 | 44.40% | Rs 315,941 | 1.104 | 49.20% | 0.00% | 0.00% | 50.80% | Helped by positive/strong market and sector context. |
| S4 ATR compression | 559 | 40.97% | Rs 165,312 | 1.037 | 46.33% | 0.00% | 0.00% | 53.67% | Weak edge; mapped sector buckets did not rescue it. |
| S5 Dual Momentum | 569 | 40.95% | Rs 201,219 | 1.051 | 46.05% | 0.00% | 0.00% | 53.95% | Gains concentrated in strong benchmark and sector contexts. |

`trade_pnl_log.csv` does not include `r_multiple`, so R-multiple context
summaries are empty for this audit.

## Benchmark Context Findings

All five retained strategies performed best in strong-positive benchmark 20D
context.

Plain positive benchmark context was not consistently favorable. S2, S4, and S5
were negative in the plain positive benchmark 20D bucket.

S2 was the only retained strategy with strong positive PnL in both negative
benchmark context and strong-positive benchmark context. This means S2's retained
edge is not explained solely by broad-market tailwind, though it still benefited
substantially from strong benchmark conditions.

## Relative Benchmark Findings

S1 through S4 had better average net PnL when the stock was outperforming the
benchmark at entry.

S5 was the exception: underperforming entries were profitable while outperforming
entries were negative. This is a diagnostic observation only and does not approve
an inverse relative-strength filter.

## Sector Context Findings

Strong sector 20D context helped S1, S2, S3, and S5 where sector proxy context
was mapped.

S4 did not benefit clearly from mapped sector context. Its weak result remained
weak after context bucketing.

Missing sector context equals unmapped sector-proxy trades under the conservative
no-fallback policy. This is intentional: ambiguous sectors are left unmapped
rather than forced into unreliable proxies.

## Missing Context Notes

After the Phase 33F utility fix, missing stock context and missing benchmark
context are zero across the retained S1-S5 audits.

Missing sector context remains material because only direct sector proxy mappings
are used. Mapped sector context ranges from about 40% to 49% of trades across the
retained strategies.

## Frozen Interpretation

- S1 remains benchmark/baseline only; positive benchmark tailwind helped heavily.
- S2 remains the strongest retained candidate; it is not solely explained by
  broad-market tailwind because it was profitable in negative benchmark context.
- S3 remains weak/moderate and appears sensitive to strong market and sector
  conditions.
- S4 remains a weak benchmark only; context did not rescue it.
- S5 remains weak/parked; gains were concentrated in strong benchmark and sector
  contexts.
- No context filter is approved.
- No strategy is promoted to production.

## Anti-Overfitting Guardrails

Future context experiments must follow pre-declared guardrails:

- Do not run open-ended threshold tuning.
- Do not optimize by final PnL alone.
- Do not stack multiple filters until results look good.
- Do not change S2 core signal logic in the first context experiment phase.
- Do not use current snapshot fundamentals as historical signals.
- Pre-declare every context experiment before running it.
- Check any candidate improvement against PF, drawdown, trade count, yearly
  consistency, and rejected-trade behavior.
- Do not allow trade count to collapse below a meaningful level.
- Do not accept one-year-only improvements.
- Treat context filters as diagnostic hypotheses, not approved rules.

## Next Phase Handoff

Recommended next phase:

- Phase 33G - S2 Controlled Context Experiment Design.

Likely initial pre-declared S2 experiment candidates to design, not yet run or
approve:

- Keep S2 baseline unchanged as the control.
- Avoid worst benchmark 20D context only if the rule is clearly defined.
- Require or test stock outperforming benchmark 20D.
- Avoid strong stock underperformance versus benchmark 20D.
- Avoid mapped-sector negative 20D only where sector proxy is mapped.

Phase 33G should define the exact experiment set, acceptance criteria, and audit
requirements before any experiment run.

## Limitations

- Static sector classification is current/static context, not point-in-time
  historical truth.
- Sector context is unavailable for intentionally unmapped sectors.
- Cap context remains inactive until reliable audited cap buckets exist.
- R-multiple is unavailable in the retained `trade_pnl_log.csv` files.
- Context audit outputs are descriptive diagnostics, not production evidence.