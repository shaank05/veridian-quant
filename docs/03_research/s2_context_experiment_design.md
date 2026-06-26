# S2 Context Experiment Design

## Purpose

Phase 33G pre-registers a small controlled batch of S2 context-aware diagnostic
experiments before any implementation or run.

The purpose is to use Phase 33F context diagnostics to test whether simple,
pre-declared context filters improve S2 trade quality. This is diagnostic only.
No variant can receive production approval from this phase or the first
experiment run.

This document prevents open-ended tuning by fixing the experiment set,
thresholds, comparison protocol, acceptance criteria, and rejection rules before
results are generated.

## Baseline

All variants must be compared directly against the retained safer S2 benchmark:

- Strategy family: `S2_MARKOV_STATE_TRANSITION`
- Baseline run: `exclude_ret_down`
- Baseline folder:
  `reports/v2/s2_markov_2020_2026_research200_exclude_ret_down_full_diagnostics/`
- Universe: audited Research200.
- Window: same backtest window as the retained baseline.
- Execution, costs, sizing, max positions, and portfolio rules: same as the
  retained baseline.
- Core S2 Markov signal logic: unchanged.

Approximate baseline metrics:

- Trades: 577.
- Net PnL: about Rs 971,715.
- Profit factor: about 1.189.
- Maximum drawdown: about 24.04%.
- Win rate: about 45.23%.

## Pre-Declared Experiment Variants

The first experiment batch is intentionally small. Do not add variants during
the first run.

### `S2_BASELINE`

No change. Included only as the comparison anchor.

### `S2_AVOID_BENCHMARK_20D_STRONG_NEGATIVE`

Skip entries when the NIFTY 500 prior 20-session return is strongly negative:

- `benchmark_ret_20d <= -5%`

Rationale: test whether avoiding severe broad-market weakness reduces stop-loss
clustering.

Overfitting caution: the threshold is fixed from the context bucket definition,
not optimized from variant results.

### `S2_REQUIRE_STOCK_OUTPERFORMING_BENCHMARK_20D`

Allow entries only when the stock prior 20-session return is greater than the
NIFTY 500 prior 20-session return:

- `rel_benchmark_ret_20d > 0`

Rationale: Phase 33F.2 showed most retained strategies improved when the stock
was outperforming the benchmark at entry.

Caution: this may reduce trade count too much.

### `S2_AVOID_STOCK_STRONGLY_UNDERPERFORMING_BENCHMARK_20D`

Skip entries only when the stock is strongly underperforming the benchmark:

- `rel_benchmark_ret_20d <= -5%`

Rationale: this is less restrictive than requiring outperformance and tests
whether only the worst relative-context entries should be avoided.

Caution: less restrictive filters may leave most baseline behavior unchanged.

### `S2_AVOID_MAPPED_SECTOR_NEGATIVE_20D`

For symbols with a mapped sector proxy only, skip entries when the sector proxy
prior 20-session return is non-positive:

- `sector_ret_20d <= 0`

For unmapped sector symbols, do not apply a sector filter. Keep them eligible.

Rationale: test sector weakness only where sector context is reliable.

Caution: there is no fallback to the benchmark. Unmapped sectors must not be
penalized or silently reclassified.

## Excluded Optional Variant

`S2_AVOID_BENCHMARK_BELOW_SMA50` is not included in the first batch because the
Phase 33F frozen interpretation is based on benchmark/relative/sector 20-session
context buckets, not a clear SMA50 bucket result.

## Not Allowed In The First Experiment Batch

- No combined filters.
- No threshold grid.
- No 5D, 60D, or 120D alternatives.
- No sector fallback filter.
- No fundamentals ratios.
- No market-cap buckets.
- No S2 core signal logic changes.
- No ranking or capacity-ordering changes.
- No post-result filter stacking.
- No production approval.

Current snapshot fundamentals ratios must not be used as historical
signal-time facts.

## Required Outputs For Phase 33G.1

Each later experiment run should produce the standard backtest outputs:

- `summary.csv`
- `yearly_summary.csv`
- `symbol_summary.csv`
- `exit_reason_summary.csv`
- `rejection_summary.csv`
- `trade_log.csv`
- `trade_pnl_log.csv`
- `equity_curve.csv`

If a variant passes basic metrics, run the Phase 33F trade context audit after
the backtest and preserve these context outputs:

- `cross_strategy_summary.csv`
- `context_bucket_summary.csv`
- `exit_reason_by_context.csv`
- `missing_context_summary.csv`

## Acceptance Criteria

A variant should be considered promising only if most of the following hold
versus `S2_BASELINE`:

- Profit factor improves meaningfully, preferably from about 1.189 to at least
  1.22.
- Maximum drawdown does not increase.
- Net PnL does not materially fall. A material fall is worse than -10% versus
  baseline unless drawdown and PF improvement are exceptional.
- Trade count remains meaningful. Prefer at least 400 trades; apply a hard
  caution below 350.
- Yearly consistency is not worse.
- Improvement is not one-year-only.
- Stop-loss and rejection behavior improves or remains explainable.
- Context improvement survives the Phase 33F trade context audit.
- No obvious concentration appears in one symbol, sector, or year.

## Rejection Criteria

Reject or park a variant if any major failure appears:

- Profit factor improvement is tiny or absent.
- Maximum drawdown worsens.
- Trade count collapses.
- PnL improvement comes from one year only.
- The variant merely removes many trades without improving expectancy or PF.
- Gains concentrate in one symbol or sector.
- The filter rejects many winners while keeping similar losers.
- The context audit shows improvement is mainly stronger-market exposure.

## Comparison Protocol

- Compare every variant against the original S2 retained baseline.
- Do not judge success only by variant-to-variant comparison.
- Use identical dates, Research200 universe, costs, sizing, max positions, and
  execution rules.
- Preserve the same S2 Markov logic.
- Document rejected signals and capacity effects.
- Run the trade context audit after the backtest if a variant passes basic
  metrics.
- Do not stack, revise, or replace filters after seeing results in the first
  batch.

## Decision Statuses

Allowed Phase 33G.1 outcomes:

- `REJECT`
- `PARK`
- `WEAK_BENCHMARK`
- `PROMISING_DIAGNOSTIC`
- `RETAIN_FOR_SECOND_PASS`

No 33G.1 result can become production-approved.

## Phase Boundary

Phase 33G is documentation/design only. It does not implement experiment code,
run strategy backtests, run trade-context audits, modify S2 strategy logic,
modify backtesting behavior, modify exporters, modify DB/OHLC/index/fundamentals
data, use fundamentals ratios as signals, or perform API calls.
