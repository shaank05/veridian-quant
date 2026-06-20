# I1 RAWRS Strategy Output Compatibility Audit

## Purpose

`I1_RAWRS_STRATEGY_OUTPUT_COMPATIBILITY` documents how future standalone RAWRS diagnostics should consume existing S1/S2/S3/S4 strategy output folders.

This audit is a prerequisite for any standalone RAWRS CLI design. RAWRS remains `I1_RAWRS_MARKET_STRUCTURE_INTELLIGENCE`: a reusable non-strategy intelligence layer, not S5, not a signal generator, not a backtest runner, and not a portfolio system.

## Current Phase Scope

Phase 30F is inspection and documentation only.

Allowed work:

- Inspect current runner, exporter, reporting, and portfolio output behavior.
- Document output compatibility for future RAWRS diagnostics.
- Define light and full diagnostic modes based on available CSV files.

Not allowed:

- No RAWRS CLI implementation.
- No code changes.
- No test changes.
- No strategy runner changes.
- No exporter changes.
- No backtest execution.
- No report generation.
- No changes to PnL, trades, exits, sizing, rejected signals, capacity, or strategy behavior.

Phase 30G adds `src/veridian_quant/v2/run_rawrs_diagnostics.py` as a standalone RAWRS diagnostic CLI. The Phase 30G CLI supports light/full input validation, CSV reading, symbol/date inference, DB-backed OHLCV loading through the existing v2 data loader convention, RAWRS feature computation, diagnostic attachment, and standalone RAWRS CSV export. It does not integrate with S1/S2/S3/S4 runners and does not rerun backtests.

The CLI reuses the existing `SQLAlchemyDailyOHLCVLoader` plus `DatabaseClient().get_engine()` convention used by strategy CLIs. The internal precomputed `rawrs_features_by_symbol` helper path remains available for tests and future programmatic use.

## Why Compatibility Audit Is Needed Before RAWRS CLI

The existing S1/S2/S3/S4 runners share the standard portfolio CSV exporter, but they do not expose identical CLI flags. S2, S3, and S4 support `--skip-all-signal-diagnostics`; S1 does not currently expose that flag.

The exporter may still write all-signal diagnostic filenames with empty rows when all-signal diagnostics are skipped. A future RAWRS CLI therefore must validate both file presence and row availability instead of assuming that an existing file means full diagnostics were produced.

## Strategy Runner Inventory

### S1

- Runner file: `src/veridian_quant/v2/run_s1_backtest.py`
- Main purpose: run the S1 Z-score mean-reversion portfolio backtest.
- Default output directory: `reports/v2/s1`
- Standard exporter: `export_portfolio_backtest_csvs`
- Known strategy-specific flags: `--strategy-variant`, `--candidate-ranking`
- Diagnostic skip flag: no `--skip-all-signal-diagnostics` flag observed.
- Light RAWRS mode: appears feasible.
- Full RAWRS mode: appears feasible if all-signal exports are produced by the standard exporter with populated inputs.
- Missing details: whether all-signal diagnostic rows are always meaningful for every S1 run depends on available `stock_data_by_symbol` and exporter behavior.

### S2 Markov

- Runner file: `src/veridian_quant/v2/run_s2_markov_backtest.py`
- Main purpose: run the S2 Markov state-transition portfolio backtest.
- Default output directory: `reports/v2/s2_markov`
- Standard exporter: `export_portfolio_backtest_csvs`
- Known strategy-specific flags: `--state-lookback-sessions`, `--min-state-observations`, `--forward-return-sessions`, `--positive-return-threshold-pct`, `--signal-probability-threshold`, `--signal-average-forward-return-threshold-pct`, `--markov-signal-filter`, `--s2-candidate-ranking`
- Diagnostic skip flag: supports `--skip-all-signal-diagnostics`
- Light RAWRS mode: appears feasible.
- Full RAWRS mode: appears feasible only when all-signal diagnostics are not skipped and the relevant files contain rows.
- Missing details: Markov-filtered signals appear in rejection outputs, but future RAWRS diagnostics should preserve filter decisions separately from capacity or active-symbol rejections.

### S3

- Runner file: `src/veridian_quant/v2/run_s3_backtest.py`
- Main purpose: run the S3 trend-pullback continuation portfolio backtest.
- Default output directory: `reports/v2/s3`
- Standard exporter: `export_portfolio_backtest_csvs`
- Known strategy-specific flags: `--sma-fast-window`, `--sma-slow-window`, `--sma-slope-lookback`, `--pullback-lookback`, `--min-pullback-return-pct`, `--max-pullback-return-pct`, `--min-drawdown-20d-pct`, `--max-drawdown-20d-pct`, `--max-atr-pct`, `--max-atr-expansion-5d-pct`, `--fresh-low-window`, `--allow-repeated-signals`, `--disable-recovery-day`, `--s3-variant`
- Diagnostic skip flag: supports `--skip-all-signal-diagnostics`
- Light RAWRS mode: appears feasible.
- Full RAWRS mode: appears feasible only when all-signal diagnostics are not skipped and the relevant files contain rows.
- Missing details: future diagnostics should verify whether S3-specific signal metadata needed for deeper analysis is present in `signal_log.csv` or only in context reports.

### S4

- Runner file: `src/veridian_quant/v2/run_s4_backtest.py`
- Main purpose: run the S4 entropy/volatility compression breakout portfolio backtest.
- Default output directory: `reports/v2/s4`
- Standard exporter: `export_portfolio_backtest_csvs`
- Known strategy-specific flags: `--atr-window`, `--range-window`, `--breakout-window`, `--percentile-window`, `--entropy-window`, `--compression-threshold`, `--entropy-threshold`, `--flat-threshold`, `--allow-repeated-signals`, `--atr-multiplier`, `--reward-risk-ratio`, `--max-holding-sessions`, `--round-trip-cost-pct`, `--s4-variant`
- Diagnostic skip flag: supports `--skip-all-signal-diagnostics`
- Light RAWRS mode: appears feasible.
- Full RAWRS mode: appears feasible only when all-signal diagnostics are not skipped and the relevant files contain rows.
- Missing details: the decision log notes that current standard signal export does not expose all S4-specific compression/breakout metadata fields.

## Strategy Output File Inventory

The current standard exporter defines these core CSV filenames:

- `trade_log.csv`
- `trade_pnl_log.csv`
- `signal_log.csv`
- `rejected_signals.csv`
- `equity_curve.csv`
- `summary.csv`
- `exit_reason_summary.csv`
- `symbol_summary.csv`
- `yearly_summary.csv`
- `rejection_summary.csv`
- `r_multiple_summary.csv`
- `r_multiple_by_exit_reason.csv`
- `r_multiple_by_symbol.csv`
- `r_multiple_by_year.csv`
- `r_multiple_by_symbol_year.csv`
- `trade_signal_context.csv`

The exporter also writes many existing non-RAWRS diagnostic files, including context, candidate-filter, S2, S3, and all-signal opportunity diagnostics. The files most relevant to future full RAWRS diagnostics are:

- `all_signal_opportunity_log.csv`
- `accepted_vs_rejected_signal_summary.csv`
- `counterfactual_rejected_trade_summary.csv`
- `counterfactual_by_year.csv`
- `counterfactual_by_symbol.csv`
- `same_day_candidate_pool_summary.csv`
- `ranking_feature_diagnostics.csv`

`rejected_signals.csv` is the current row-level rejected-signal log observed in the standard exporter. No separate filename named `capacity_rejected_signals.csv` was observed.

## Runner Flag Inventory

Common runner flags:

- `--start-date`
- `--end-date`
- `--starting-equity`
- `--risk-per-trade`
- `--max-concurrent-positions`
- `--symbols`
- `--all-symbols`
- `--output-dir`
- `--verbosity`

Observed diagnostic skip support:

- S1: no `--skip-all-signal-diagnostics` flag observed.
- S2: supports `--skip-all-signal-diagnostics`.
- S3: supports `--skip-all-signal-diagnostics`.
- S4: supports `--skip-all-signal-diagnostics`.

## Effect Of Diagnostic-Skip Flags

S2/S3/S4 pass `include_all_signal_diagnostics=not args.skip_all_signal_diagnostics` to the standard exporter.

When all-signal diagnostics are skipped, the exporter still writes the all-signal opportunity output files with their configured columns but no diagnostic rows. Future RAWRS tooling must not treat empty all-signal files as proof that no rejected opportunities existed.

## Light RAWRS Diagnostic Mode

Light RAWRS diagnostics should work on faster or standard strategy output folders.

It can:

- Attach RAWRS features to accepted trades and available signal/trade records.
- Compare winners versus losers.
- Compare target, stop, time-stop, and other exit reasons if trade logs and PnL logs exist.
- Analyze R-multiple or PnL buckets if `trade_pnl_log.csv` contains the required fields.
- Use `signal_log.csv` for signal-time attachment when available.

It cannot:

- Fully evaluate capacity-rejected opportunities.
- Fully evaluate active-symbol rejected signals versus capacity rejections.
- Fully evaluate same-day rejected candidate quality.
- Infer missing rejected-signal diagnostics from absent or empty files.

## Full RAWRS Diagnostic Mode

Full RAWRS diagnostics require the light-mode inputs plus row-level rejection and all-signal opportunity diagnostics.

It can:

- Compare accepted versus rejected signals.
- Analyze capacity-rejected signals if rejection reason fields are present.
- Analyze active-symbol rejections separately from capacity rejections if reasons are present.
- Analyze same-day candidate pools if `same_day_candidate_pool_summary.csv` or row-level opportunity files are populated.
- Study counterfactual rejected-signal diagnostics without treating them as actual portfolio PnL.

Full mode is slower and heavier because it may require strategy runs without `--skip-all-signal-diagnostics`.

## Required CSVs For Light Mode

Future light mode should require, where available:

- `trade_log.csv`
- `trade_pnl_log.csv`
- `signal_log.csv`
- `summary.csv`
- `yearly_summary.csv`
- `symbol_summary.csv`
- `equity_curve.csv`

If a strategy output folder lacks one of these, the future RAWRS CLI should fail clearly for analyses requiring that file and skip only optional analyses with warnings.

## Required CSVs For Full Mode

Future full mode should require the light-mode files plus, where available:

- `rejected_signals.csv`
- `rejection_summary.csv`
- `all_signal_opportunity_log.csv`
- `accepted_vs_rejected_signal_summary.csv`
- `counterfactual_rejected_trade_summary.csv`
- `same_day_candidate_pool_summary.csv`

The code currently exports `rejected_signals.csv` as the row-level rejected-signal log. No separate capacity-only detail filename was observed.

## Optional CSVs

Optional inputs for richer diagnostics include:

- `exit_reason_summary.csv`
- `r_multiple_summary.csv`
- `r_multiple_by_exit_reason.csv`
- `r_multiple_by_symbol.csv`
- `r_multiple_by_year.csv`
- `r_multiple_by_symbol_year.csv`
- `trade_signal_context.csv`
- existing context bucket reports
- existing S2 and S3 diagnostic reports
- `counterfactual_by_year.csv`
- `counterfactual_by_symbol.csv`
- `ranking_feature_diagnostics.csv`

Future RAWRS tooling should warn, not fail, when optional files are absent.

## Missing-File Behavior For Future RAWRS CLI

A future standalone RAWRS CLI should:

- Accept a strategy output directory.
- Accept mode: `light` or `full`.
- Validate required files for the selected mode.
- Validate that full-mode row-level files contain data rows when required for a requested analysis.
- Fail clearly if required files are missing.
- Warn for optional files.
- Never interpret missing rejected-signal files as no rejections.
- Never interpret empty all-signal files as no rejected/capacity candidates without checking whether skip flags were used.

## Signal Timestamp Compatibility

Observed signal timestamp columns:

- `signal_log.csv`: `generated_on`
- `trade_log.csv`: `entry_date`, but not necessarily the original signal date.
- `trade_pnl_log.csv`: `entry_date`, but not necessarily the original signal date.
- `rejected_signals.csv`: `signal_date`

Phase 30D RAWRS utilities support common timestamp columns such as `generated_on`, `signal_date`, `entry_signal_date`, `date`, and `timestamp`. Future RAWRS CLI code must choose the correct column per input file and preserve feature timestamp separately.

## Symbol Column Compatibility

Observed core files use `symbol` as the symbol column:

- `trade_log.csv`
- `trade_pnl_log.csv`
- `signal_log.csv`
- `rejected_signals.csv`
- symbol-level summary files

Future RAWRS diagnostics should require `symbol` unless an explicit override is provided.

## Accepted-Trade Compatibility

Accepted-trade diagnostics appear feasible for S1/S2/S3/S4 using `trade_log.csv`, `trade_pnl_log.csv`, and `signal_log.csv`.

Important compatibility issue:

- Trade logs use entry-date fields. RAWRS default alignment should be signal-time, so future tooling should prefer signal logs or a preserved signal date when available.
- If only entry dates are available, the output must be labeled as entry-time or degraded compatibility, not default signal-time RAWRS.

## Rejected-Signal Compatibility

Rejected-signal diagnostics appear feasible when `rejected_signals.csv` exists and contains row-level records with `symbol`, `signal_date`, and `reason`.

The current exporter writes `rejected_signals.csv` for all standard exports. Future tooling should still check whether rows are present and should avoid treating an empty file as proof of no rejected signals without checking run context.

## Capacity-Rejection Compatibility

Capacity-rejection diagnostics appear possible if `rejected_signals.csv` includes capacity-related `reason` values. No separate capacity-only file was observed.

Future RAWRS diagnostics should:

- Identify capacity rejections by explicit reason values.
- Keep active-symbol rejections separate from capacity rejections.
- Avoid treating capacity-rejected counterfactual outcomes as actual portfolio PnL.

## Same-Day Candidate-Pool Compatibility

Same-day candidate-pool diagnostics appear tied to all-signal opportunity outputs, especially:

- `all_signal_opportunity_log.csv`
- `same_day_candidate_pool_summary.csv`
- `accepted_vs_rejected_signal_summary.csv`

These files may be empty when all-signal diagnostics are skipped. Future RAWRS full mode should require populated files for same-day candidate-pool analysis.

## RAWRS Feature Attachment Requirements

Future RAWRS diagnostics should:

- Compute or load RAWRS feature frames by symbol.
- Attach RAWRS features as of the signal timestamp.
- Use exact date alignment where possible.
- Use latest prior RAWRS feature rows when exact signal dates are missing.
- Never use future RAWRS feature rows.
- Preserve input row order and row count.
- Preserve original signal timestamp and RAWRS feature timestamp.
- Never alter existing trade, PnL, exit, sizing, capacity, or strategy outputs.

## Recommended Future CLI Behavior

The Phase 30G standalone RAWRS CLI establishes the validation layer. Future extensions should:

- Accept a strategy output directory.
- Accept an OHLCV source or precomputed RAWRS feature source.
- Accept mode: `light` or `full`.
- Validate required files for the selected mode.
- Fail clearly if required files are missing.
- Warn for optional files.
- Detect empty full-mode files and explain that full diagnostics may require rerunning the strategy without skip flags.
- Never rerun strategy backtests.
- Never modify existing strategy outputs.
- Write RAWRS outputs to a separate output directory.
- Avoid integration into S1/S2/S3/S4 runners until standalone evidence justifies it.

Current Phase 30G status:

- Light/full required-file validation is implemented.
- Missing optional-file warnings are implemented.
- Empty full-mode row-level file detection is implemented.
- CSV reading from the strategy output directory is implemented.
- Symbol and date-range inference from strategy outputs is implemented.
- DB-backed OHLCV loading is implemented using the existing v2 data loader convention.
- RAWRS feature computation and diagnostic CSV export are implemented.
- Precomputed-feature diagnostic build/export helpers remain available.

Phase 30J evidence update:

- Standalone output compatibility enabled light-mode RAWRS diagnostics across
  retained or benchmark S1/S2/S3/S4 outputs.
- Those compatible outputs supported keep/avoid subset analysis and a true S3
  baseline-versus-overlay comparison.
- The S3 p20 and p10 spectral-concentration hard filters failed despite a
  promising completed-trade diagnostic.
- Detailed evidence is consolidated in
  `docs/06_intelligence/i1_rawrs_combined_evidence_audit.md`.

## Guardrails

- RAWRS diagnostics are diagnostic only.
- RAWRS is not S5.
- RAWRS is not a strategy.
- RAWRS is not a signal generator.
- RAWRS is not a backtest runner.
- RAWRS must not change PnL, trades, exits, sizing, rejected signals, capacity, or strategy behavior.
- Missing rejected-signal files must not be silently interpreted as no rejections.
- Empty all-signal files must not be silently interpreted as no opportunities.
- Capacity-rejected diagnostics must not be treated as actual portfolio PnL.
- Light mode must clearly state that it cannot answer full capacity-selection questions.
- Full mode may require slower strategy runs with full diagnostics enabled.
- No production claims.
- No ranking.
- No filtering.
- No topology/regime labels yet.

## Open Questions / Follow-Up Checks

- Should future strategy exports preserve original signal date directly in `trade_log.csv` and `trade_pnl_log.csv`, or should RAWRS join trades back to `signal_log.csv`?
- Which exact `reason` values should future RAWRS classify as capacity rejections across S1/S2/S3/S4?
- Are all-signal opportunity rows complete enough for S1 in all standard runs?
- Should future RAWRS full mode require non-empty `all_signal_opportunity_log.csv`, or allow accepted/rejected summaries when row-level details are missing?
- Should S4-specific compression/breakout metadata be exposed in standard signal outputs before deeper RAWRS/S4 diagnostics?
- How should future tooling record whether `--skip-all-signal-diagnostics` was used if only the output directory is available?

## Non-Goals

Phase 30F does not implement:

- RAWRS CLI.
- RAWRS CSV generation.
- RAWRS feature computation.
- Strategy runner integration.
- Backtest runner changes.
- Standard exporter changes.
- Strategy changes.
- Ranking or filtering.
- Production decisions.

## References

Related files and docs:

- `src/veridian_quant/v2/run_s1_backtest.py`
- `src/veridian_quant/v2/run_s2_markov_backtest.py`
- `src/veridian_quant/v2/run_s3_backtest.py`
- `src/veridian_quant/v2/run_s4_backtest.py`
- `src/veridian_quant/v2/reporting/exporters.py`
- `src/veridian_quant/v2/reporting/diagnostics.py`
- `src/veridian_quant/v2/backtesting/portfolio_runner.py`
- `src/veridian_quant/v2/backtesting/markov_portfolio_runner.py`
- `src/veridian_quant/v2/backtesting/s3_portfolio_runner.py`
- `src/veridian_quant/v2/backtesting/s4_portfolio_runner.py`
- `docs/06_intelligence/i1_rawrs_market_structure_intelligence.md`
- `docs/06_intelligence/i1_rawrs_signal_time_diagnostics.md`
- `docs/06_intelligence/i1_rawrs_combined_evidence_audit.md`
- `docs/00_foundation/v2_research_roadmap.md`
- `docs/05_decisions/decision_log.md`
