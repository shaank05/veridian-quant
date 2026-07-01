# Phase 37S - Kronos Policy-Compliant Small Diagnostic Retry Design

## 1. Status / Verdict

Phase 37S is docs/design only.

- No inference is approved in 37S.
- No Research200 run is approved.
- No strategy integration is approved.
- No production use is approved.
- No raw predicted-candle trading is approved.
- This phase designs a future approval-gated retry using the 37Q/37R
  output-validity policy.

Recommended next phase:
`PROCEED_TO_37T_POLICY_COMPLIANT_RETRY_APPROVAL`.

Phase 37T is an approval gate first. Execution may happen only after explicit
user approval. Phase 37S does not start immediate inference.

Later closeout update: Phase 37T executed the approved retry, Phase 37U/37V
supported closeout, and Phase 37W records
`DOCS_ONLY_CLOSEOUT_AND_BIMONTHLY_REVIEW` in
`docs/03_research/external_model_kronos_closeout.md`. This design remains
historical; no further local Kronos inference is approved.

## 2. Why 37S Exists

Prior Kronos diagnostics found weak/negative signal evidence and repeated
output-validity failures:

- 37K had 17 / 150 invalid OHLC rows = 11.33%.
- 37N had 16 / 90 invalid OHLC rows = 17.78%.
- 37N had 8 / 18 forecasts with invalid OHLC = 44.44%.
- 37P `deterministic_low_randomness` had 0 / 15 invalid rows in a tiny
  one-symbol/one-date sample.
- 37R implemented reusable validation helpers with 22 focused tests passing.

Therefore a retry can be designed only if it uses explicit eval,
deterministic-ish decoding, and 37R output-validity gating.

## 3. Design Objective

The retry objective is to:

- Test whether `Kronos-small` still shows any weak diagnostic/ranking signal
  when output validity is controlled.
- Validate that deterministic-ish decoding plus policy gating keeps invalid
  output rates acceptable.
- Compare results to 37K only cautiously because the decoding policy changed.
- Avoid testing profitability.
- Avoid creating strategy rules.

## 4. Explicit Non-Goals

Phase 37S and the proposed retry are not:

- Production approval.
- A trading strategy.
- Raw predicted-candle trading.
- A Research200 sweep.
- A `Kronos-base` comparison.
- Fine-tuning or training.
- Threshold optimization.
- Best-seed or best-decoding selection.
- "Repair and trade."
- A direct improvement claim versus 37K unless the decoding-policy change is
  clearly caveated.

## 5. Proposed Future Retry Size

Recommended default, for comparability with 37K:

- Symbols: 5.
- Dates: 6.
- Forecast runs: 30.
- Horizon: 5 sessions.
- Lookback: 400 sessions.

Execution policy:

- Use deterministic-ish decoding.
- Use no seed sweep by default.
- Use one pre-registered seed if needed for reproducibility, for example
  seed `42`.
- Use no stochastic multi-seed ensemble.
- Do not expand beyond 30 runs without separate approval.

Alternative laptop-conservative fallback:

- 3 symbols x 4 dates = 12 forecast runs.
- Use only if the user prefers lower load or a 30-run retry seems too much.

Runtime estimate:

- 37K: 30 forecasts took 264.955 seconds, average 8.739 seconds/forecast.
- 37P: 9 forecasts took 79.774 seconds, average 7.375 seconds/forecast.
- A 30-run retry should likely be around 4-6 minutes, but the cap should be
  20 minutes.

## 6. Sample Selection

Recommended sample:

- Symbols: `HDFCBANK`, `ICICIBANK`, `SBIN`, `INFY`, `BHARTIARTL`.
- Dates: `2023-01-16`, `2023-05-15`, `2023-09-14`, `2024-01-15`,
  `2024-05-15`, `2024-09-16`.

Use the same 37K symbols and dates for comparability unless data availability
fails.

Rules:

- Do not change the sample after seeing outputs.
- If a date/symbol fails validation preflight, stop and ask rather than
  substitute silently.
- This avoids symbol/date cherry-picking after 37K.

## 7. Required Execution Policy for Future 37T

The future retry must:

- Use `Kronos-small` only.
- Use pinned tokenizer/model revisions from 37H/37K.
- Use CPU-first.
- Call `.eval()` on tokenizer/model if supported.
- Use deterministic-ish decoding:
  - `top_k=1`
  - `top_p=1.0`
  - record temperature and all decoding args.
- Use 37R `output_validity.py` helpers.
- Mark any forecast run with any invalid path row as `INVALID_OUTPUT`.
- Exclude invalid runs from signal metrics.
- Preserve invalid runs in output-validity summaries.
- Use no repair for metrics.
- Use repair only as visualization-only if explicitly called and clearly
  labeled.
- Use no close-only mode unless separately approved.

## 8. Required Output Files for Future 37T

Planned folder:

`reports/v2/external_models/kronos/policy_retry_YYYYMMDD/`

Required generated files:

- `kronos_policy_retry_metadata.json`
- `kronos_policy_retry_input_manifest.csv`
- `kronos_policy_retry_forecast_paths.csv`
- `kronos_policy_retry_diagnostics.csv`
- `kronos_policy_retry_run_validity_summary.csv`
- `kronos_policy_retry_invalid_ohlc_summary.csv`
- `kronos_policy_retry_metric_summary.csv`
- `kronos_policy_retry_by_symbol.csv`
- `kronos_policy_retry_by_date.csv`
- `kronos_policy_retry_runtime_notes.txt`

Generated outputs remain ignored and are not for commit unless separately
approved.

## 9. Required Metrics

Output-validity metrics:

- Planned forecast runs.
- Completed forecast runs.
- Valid forecast runs.
- Invalid forecast runs.
- Invalid forecast-run rate.
- Total path rows.
- Invalid path rows.
- Invalid path-row rate.
- Output validity status: `PASS`, `WARNING`, or `FAILED`.
- Invalid reasons and magnitudes.
- Invalids by symbol/date/forecast step.

Signal metrics, computed only on valid forecast runs:

- Valid forecast count used for metrics.
- Excluded invalid count.
- Directional correct count.
- Directional accuracy.
- Mean forecast error.
- Median absolute forecast error.
- Spearman rank IC by date and overall if the valid sample supports it.
- Top1/bottom1 realized return spread by date and overall.
- Top2/bottom2 spread if the sample supports it.
- By-symbol and by-date summaries.

All metric outputs must show planned count, valid count, and invalid/excluded
count.

## 10. Decision Rules After Future Retry

Pre-registered decisions:

- If invalid forecast-run rate > 5% or invalid path-row rate > 5%:
  `OUTPUT_VALIDITY_FAILED`; do not judge signal quality; proceed to
  policy/debug revision or park.
- If invalid path-row rate > 1%: `OUTPUT_VALIDITY_WARNING`; signal metrics may
  be reported only with caveats if invalid run rate <= 5%.
- If valid forecast count < 24 out of 30: signal metrics are too thin for a
  larger diagnostic decision.
- If rank IC remains negative and top/bottom spread remains negative on valid
  runs: do not scale; consider park or redesign.
- If output validity passes and signal metrics are weak/neutral: do not scale;
  consider park/repeat only if justified.
- If output validity passes and signal metrics are directionally positive:
  proceed only to larger diagnostic design, not execution or strategy
  integration.

## 11. Leakage / Misuse Controls

- Input lookback ends at the inference date.
- No future rows in model input.
- Realized returns joined only after inference.
- No future labels as model input.
- Sample fixed before inference.
- Decoding fixed before inference.
- No changes after outputs.
- No strategy rule.
- No threshold tuning.
- No raw predicted-candle trading.
- No production use.

## 12. Approval Requirements Before Future Execution

Before future 37T execution, the user must approve:

- Exact sample size.
- Exact symbols/dates.
- Use of deterministic-ish decoding.
- Seed if used.
- Output-validity policy.
- Runtime cap.
- Generated output folder.
- No full Research200.
- No `Kronos-base`.
- No production use.
- No strategy integration.
- No raw predicted-candle trading.
- No generated report commits.

## 13. Recommended 37T Runtime / Abort Limits

Prior runtime evidence:

- 37K: 30 forecasts = 264.955 seconds.
- 37P: 9 forecasts = 79.774 seconds.

Recommended limits:

- Max total runtime before reassess: 20 minutes.
- Max single forecast/config hang: 5 minutes.
- Abort if laptop becomes sluggish/unusable.
- Abort if `Kronos-base`, training, or web stack is requested.

## 14. Recommended Next Phase

Decision: `PROCEED_TO_37T_POLICY_COMPLIANT_RETRY_APPROVAL`.

37T is an approval gate first. Execution may happen only after explicit user
approval. No immediate inference follows from 37S.

## 15. Anti-Misuse Guardrails

- No production claims.
- No raw predicted-candle trading.
- No repair-and-trade.
- No full Research200.
- No threshold tuning.
- No best-seed/decoding selection.
- No strategy logic.
- No generated report/model-weight commits.
- No fine-tuning/training.
- No direct comparison versus 37K without caveating the decoding-policy change.

Phase 37W closeout keeps these guardrails active and adds: no local patch now,
no Research200 scaling, and only bi-monthly upstream maturity review unless a
separate reopening condition is met.
