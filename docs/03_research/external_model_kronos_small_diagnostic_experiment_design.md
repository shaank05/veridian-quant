# Phase 37J — Kronos Small Offline Diagnostic Experiment Design

## 1. Status / Verdict

Phase 37J is design-only.

- No new inference is approved.
- No full Research200 run is approved.
- No strategy integration is approved.
- No production use is approved.
- No raw forecast trading is approved.
- No new install, model/tokenizer download, adapter implementation, sandbox
  implementation, backtest, threshold optimization, training, or fine-tuning is
  approved.

Phase 37J designs a small diagnostic experiment for possible future Phase 37K
execution only.

## 2. Why This Experiment Exists

Phase 37H proved technical feasibility only. It showed that an isolated Kronos
environment could load pinned `Kronos-small` artifacts and run one CPU-first
forecast on one NSE OHLCV sample.

Forecast quality is unproven. The one HDFCBANK smoke-test forecast was
directionally wrong, but one row is insufficient evidence that Kronos is good or
bad.

The next question is whether Kronos outputs contain any weak but measurable
diagnostic or ranking information across a small pre-registered sample. The
experiment must test diagnostic value, not profitability.

## 3. Primary Research Questions

- Does Kronos 5-session predicted close return have any directional
  relationship with realized 5-session forward return?
- Does cross-sectional Kronos ranking separate stronger versus weaker forward
  returns?
- Does forecast error behave differently by liquidity, benchmark regime, VIX
  regime, or drawdown context?
- Do Kronos outputs agree more often with winning S1-S5 trades than losing
  S1-S5 trades?
- Does Kronos add information beyond existing risk diagnostics?
- Is runtime acceptable for a small offline batch on the user's laptop?

## 4. Explicit Non-Goals

- Not a trading strategy.
- Not a direct buy/sell signal.
- Not stop/target generation.
- Not production validation.
- Not a full backtest.
- Not a Research200 sweep.
- Not fine-tuning.
- Not threshold optimization.
- Not a model comparison between `Kronos-small` and `Kronos-base`.
- Not a profitability claim.

## 5. Proposed Experiment Size

Recommended default for future Phase 37K approval:

- Symbols: 5 HIGH-liquidity Research200 symbols.
- Inference dates: 6 dates total, spread across 2023-2024.
- Horizon: 5 sessions primary.
- Lookback: 400 sessions.
- Total inference points: 5 symbols x 6 dates = 30 forecasts.
- No expansion during Phase 37K unless separately approved.

Allowed design alternatives if the user asks to revise before approval:

- Minimum: 3 symbols x 4 dates = 12 forecasts.
- Maximum for first diagnostic: 10 symbols x 6 dates = 60 forecasts.

The recommended default remains 5 x 6 = 30 forecasts because it is large enough
for a first diagnostic table while staying small enough for the laptop
constraint.

## 6. Symbol Selection Design

Pre-register symbol selection before inference:

- Choose from Research200 only.
- Prefer HIGH liquidity bucket.
- Require complete data for all selected inference dates.
- Include the selection rule and reason for each selected symbol.
- Do not choose symbols based on expected Kronos performance.
- Do not change symbols after seeing output.
- Optionally include multiple sectors if available without forcing sector
  balance.

Codex may choose exact symbols in Phase 37K only if it:

- Chooses before inference.
- Records the selection rule.
- Records liquidity bucket.
- Verifies data completeness.
- Does not change symbols after seeing output.

## 7. Inference Date Selection Design

Pre-register inference dates before inference:

- Dates must be legitimate market-open dates with available data.
- Dates must have 400-session lookback and 5 future sessions.
- Choose dates before inference.
- Prefer stable spread across 2023-2024.
- Do not change dates after seeing output.
- Avoid using only known crash or rally dates.
- Record if a selected calendar date is shifted to the nearest previous
  market-open session.

Recommended default:

- 6 dates approximately quarterly/monthly across 2023-2024.
- Exact dates selected in Phase 37K based on actual market-open availability.

## 8. Horizon / Lookback Design

- Primary horizon: 5 sessions only.
- Lookback: 400 sessions.
- Do not test 10-session or 20-session horizons in Phase 37K.
- Do not choose a best horizon after seeing results.
- Longer horizons may be designed later only if the 5-session diagnostic shows
  value.

## 9. Kronos Output Features

Derived forecast features:

- Predicted 5D close return.
- Predicted direction.
- Predicted high-low range.
- Predicted volatility proxy.
- Forecast rank per inference date.
- Optional forecast strength bucket using pre-defined rank bins only.
- Realized 5D forward return.
- Forecast error.
- Absolute forecast error.
- Direction correctness.

Do not use raw predicted OHLC as trade entries or exits.

## 10. Primary Metrics

Pre-registered primary metrics:

- Directional accuracy: number correct / total forecasts.
- Mean forecast error.
- Median absolute forecast error.
- Spearman rank IC between predicted 5D return and realized 5D return.
- Top-minus-bottom rank spread: top rank group realized return minus bottom
  rank group realized return.
- Average realized return by forecast rank group.
- Runtime per forecast and total runtime.

All conclusions must report numeric evidence:

- Sample size.
- Counts.
- Percentages.
- Mean and median values.
- Rank IC.
- Top/bottom spread.
- Runtime.

## 11. Secondary Diagnostics

Secondary diagnostics:

- Performance by liquidity bucket if variation exists.
- Performance by benchmark regime.
- Performance by VIX regime.
- Performance by drawdown state.
- Agreement/disagreement with S1-S5 trade direction/outcome if enough overlap
  exists.
- Year/date stability.
- Symbol-level stability.

Secondary diagnostics are exploratory only. No rule can be created from them in
Phase 37K.

## 12. Success Criteria

For Phase 37K result review, the result may justify a larger diagnostic design
only if:

- At least 30 forecast points complete successfully.
- No leakage/misuse issues are found.
- The laptop remains usable.
- Directional accuracy is meaningfully above random only if the sample supports
  that claim numerically.
- Spearman rank IC is positive, with the numeric value reported.
- Top group realized return is greater than bottom group realized return, with
  numeric spread reported.
- The result is not driven by one symbol/date.
- Runtime is acceptable.
- Output schema is complete.

Thirty forecasts cannot prove alpha. Success means "worth a larger diagnostic,"
not "strategy approved."

## 13. Failure Criteria

Failure or stop conditions:

- Inference is too slow/heavy.
- Output is unstable or malformed.
- Directional accuracy is not better than random.
- Rank IC is near zero or negative.
- Top/bottom rank spread is absent or reversed.
- Result is driven by one outlier.
- Leakage or data alignment issue is found.
- Laptop impact is unacceptable.
- Generated outputs cannot join back to Veridian diagnostics.
- Repeated sample path instability is too high if repeated runs are attempted.

## 14. Output Folder and Files for Future 37K

Planned output folder:

- `reports/v2/external_models/kronos/small_diagnostic_YYYYMMDD/`

Planned files:

- `kronos_small_diagnostic_metadata.json`
- `kronos_small_diagnostic_input_manifest.csv`
- `kronos_small_diagnostic_forecast_paths.csv`
- `kronos_small_diagnostic_forecast_diagnostics.csv`
- `kronos_small_diagnostic_metric_summary.csv`
- `kronos_small_diagnostic_by_symbol.csv`
- `kronos_small_diagnostic_by_date.csv`
- `kronos_small_diagnostic_runtime_notes.txt`

Generated outputs remain ignored and not for commit unless separately approved.

## 15. Metadata Requirements

Required metadata:

- `run_id`
- Kronos repo path.
- Kronos repo commit hash.
- Tokenizer/model names and revisions.
- License observed.
- Dependency versions.
- Python version.
- OS.
- CPU/GPU mode.
- Seed.
- Decoding settings.
- Selected symbols.
- Selected dates.
- Selection rule.
- Lookback sessions.
- Horizon.
- Output folder.
- Start/end runtime.
- Per-forecast runtime.
- Laptop-impact notes.
- Warnings/caveats.

## 16. Leakage / Misuse Controls

- Input ends at inference date only.
- No future rows in lookback.
- Realized forward returns joined after inference only.
- No future benchmark/VIX/drawdown labels as input.
- No symbol/date/horizon changes after seeing forecasts.
- No threshold tuning.
- No raw forecast trading.
- No strategy rule creation.
- No full Research200 expansion.
- No production use.

## 17. Laptop / Abort Limits for Future 37K

Conservative future execution limits:

- No full Research200 run.
- Start with 5 symbols x 6 dates.
- CPU-first.
- No `Kronos-base`.
- No repeated sweeps unless separately approved.
- Abort/reassess if total run exceeds 30 minutes.
- Abort if any single inference hangs beyond the agreed limit.
- Abort if laptop becomes sluggish/unusable.
- Abort if memory pressure/freezing occurs.

## 18. 37K Approval Requirements

Before Phase 37K execution, the user must approve:

- Exact symbols.
- Exact dates.
- Exact output folder.
- Exact max runtime.
- Whether the 5 x 6 default is accepted.
- No full Research200 run.
- No production use.
- No raw forecast trading.

## 19. Decision

Decision: `PROCEED_TO_37K_SMALL_DIAGNOSTIC_EXECUTION_APPROVAL`.

This is not approval to execute. Phase 37K must begin with an explicit user
approval checklist before any inference, output generation, or additional model
use.

## 20. Anti-Misuse Guardrails

- No production claims.
- No alpha conclusion from a small sample.
- No raw predicted-candle execution.
- No full Research200 run.
- No best-horizon cherry-picking.
- No threshold tuning.
- No symbol/date cherry-picking.
- No fine-tuning before leakage/split audit.
- No committing generated reports/model weights.
- No cloud/GPU spend without approval.
