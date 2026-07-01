# Phase 37M — Kronos Stochastic Reproducibility / Output Validity Diagnostic Design

## 1. Status / Verdict

Phase 37M is design-only.

- No new inference is approved.
- No full Research200 run is approved.
- No strategy integration is approved.
- No production use is approved.
- No raw forecast trading is approved.
- No install, download, adapter implementation, sandbox implementation,
  backtest, training, or fine-tuning is approved.

Phase 37M designs a future reproducibility/output-validity diagnostic only.

Phase 37N later executed that diagnostic and confirmed invalid OHLC rows
remained high. Phase 37O therefore performs read-only adapter/output-validation
inspection in
`docs/03_research/external_model_kronos_adapter_output_validation_debug.md`.
No diagnostic retry is approved until the adapter/API usage and output-validity
policy are debugged.

## 2. Why This Phase Exists

Phase 37K completed 30 / 30 approved `Kronos-small` forecast points on CPU.
Phase 37L scrutinized the result and selected `REDESIGN_SMALL_DIAGNOSTIC`.

Numeric evidence from 37K/37L:

- Directional accuracy was 13 / 30 = 43.33%.
- Spearman rank IC was -0.268521.
- Top 1 realized average was -0.026200.
- Bottom 1 realized average was 0.017311.
- Top-minus-bottom spread was -0.043511.
- Top2-minus-bottom2 spread was -0.010859.
- Forecast paths had 150 / 150 expected rows.
- 17 / 150 forecast path rows had invalid OHLC relationships.
- Invalid forecast path rows were therefore 11.33% of generated path rows.

Because signal quality was weak/negative and 11.33% of forecast path rows were
invalid, the next step should test output validity and reproducibility before
any broader diagnostic. Do not conclude Kronos is permanently bad yet. First
rule out implementation, decoding, stochastic sampling, data mapping,
normalization, de-normalization, and output-validation issues.

## 3. Primary Questions

- Are invalid OHLC rows reproducible across repeated runs?
- Are invalid OHLC rows concentrated in certain symbols, dates, or forecast
  steps?
- Are invalid rows caused by stochastic sampling settings?
- Do deterministic or near-deterministic decoding settings reduce invalid OHLC
  rows?
- Are predicted close returns stable across seeds?
- Are forecast directions stable across seeds?
- Are cross-sectional ranks stable across seeds?
- Is the negative rank IC from 37K robust, or could it be sample/sampling noise?
- Are invalid OHLC rows due to data mapping, normalization, or de-normalization
  issues?

## 4. Explicit Non-Goals

- Not a trading strategy.
- Not a profitability test.
- Not a full Research200 run.
- Not a `Kronos-base` comparison.
- Not fine-tuning.
- Not threshold optimization.
- Not raw predicted-candle trading.
- Not production validation.
- Not model promotion or rejection based on one tiny follow-up.

## 5. Proposed Future Diagnostic Size

Recommended default:

- Use a subset of the 37K sample only.
- Symbols: 2.
- Dates: 3.
- Horizon: 5 sessions.
- Lookback: 400 sessions.
- Total base forecast points: 2 x 3 = 6.
- Repeated runs: 3 pre-registered seeds or decoding runs per forecast point.
- Total generated forecast runs: 6 x 3 = 18.
- Forecast path rows: 18 x 5 = 90.

Alternative if laptop impact is a concern:

- 1 symbol x 3 dates x 3 seeds = 9 forecast runs.
- 2 symbols x 2 dates x 3 seeds = 12 forecast runs.

Hard cap:

- Maximum 18 forecast runs unless the user separately approves expansion.

## 6. Sample Selection Design

Future execution must choose from 37K symbols/dates only, not new symbols.

Recommended deterministic selection:

- Include one previously weak case:
  - `HDFCBANK` or `ICICIBANK` around `2024-01-15`.
- Include one previously better case:
  - `INFY` and/or `2023-05-15`.
- Prefer a final 2-symbol x 3-date grid that includes both a weak date and a
  better date.
- Choose symbols/dates before inference.
- Record the exact selection rule.
- Do not change symbols/dates after seeing outputs.

Candidate default for future approval:

- Symbols: `HDFCBANK`, `INFY`.
- Dates: `2023-05-15`, `2024-01-15`, and one additional 37K date selected by a
  predeclared rule such as chronological middle date among remaining 37K dates.

This candidate is not execution approval.

## 7. Decoding / Seed Design

Future execution should:

- Use the same pinned tokenizer/model revisions from 37H/37K.
- Use CPU-first execution.
- Use the same 400-session lookback and 5-session horizon.
- Use a fixed pre-registered seed list, for example `42`, `101`, `202`.
- Record exact decoding settings for every run.
- Include the 37K decoding settings as one configuration:
  - `T = 1.0`
  - `top_k = 0`
  - `top_p = 0.9`
  - `sample_count = 1`
  - `max_context = 512`
- If Kronos supports deterministic or near-deterministic decoding settings,
  include one low-randomness configuration before execution approval.
- Do not choose seed or decoding settings after seeing results.
- Do not tune settings for better returns; this is output-validity and
  reproducibility only.

## 8. Output Validity Checks

Exact OHLC validity rules:

- `open > 0`
- `high > 0`
- `low > 0`
- `close > 0`
- `high >= low`
- `high >= open`
- `high >= close`
- `low <= open`
- `low <= close`
- `volume >= 0` if volume is present
- `amount >= 0` if amount is present

Required validity metrics:

- Invalid OHLC rows / total forecast path rows.
- Forecasts with at least one invalid OHLC row.
- Invalid rows by symbol.
- Invalid rows by date.
- Invalid rows by forecast step.
- Invalid rows by seed/decoding setting.
- Invalid reason counts.

## 9. Reproducibility Metrics

Required reproducibility metrics:

- Direction agreement rate across seeds.
- Predicted close return mean/std/min/max by symbol/date.
- Rank correlation across seeds by inference date.
- Average pairwise rank correlation.
- Forecast path invalid-rate stability across seeds.
- Sign flip count across seeds.
- Whether the same symbol/date repeatedly produces invalid rows.

## 10. Signal Metrics as Secondary Only

Secondary exploratory metrics:

- Directional accuracy by seed.
- Rank IC by seed.
- Top-minus-bottom spread by seed.

These are secondary and exploratory. No trading decision should come from the
future 37N execution.

## 11. Output Files for Future Execution

Planned folder:

- `reports/v2/external_models/kronos/repro_validity_YYYYMMDD/`

Planned files:

- `kronos_repro_validity_metadata.json`
- `kronos_repro_validity_input_manifest.csv`
- `kronos_repro_validity_forecast_paths.csv`
- `kronos_repro_validity_diagnostics.csv`
- `kronos_repro_validity_invalid_ohlc_summary.csv`
- `kronos_repro_validity_seed_stability.csv`
- `kronos_repro_validity_metric_summary.csv`
- `kronos_repro_validity_runtime_notes.txt`

Generated outputs remain ignored and not for commit unless separately approved.

## 12. Metadata Requirements

Future metadata must include:

- `run_id`
- Kronos repo path
- Kronos repo commit hash
- Tokenizer/model names and revisions
- License observed
- Dependency versions
- Python version
- OS
- CPU/GPU mode
- Seed list
- Decoding settings
- Selected symbols
- Selected dates
- Selection rule
- Lookback sessions
- Horizon
- Total forecast runs planned
- Total forecast runs completed
- Output folder
- Start/end runtime
- Per-run runtime
- Laptop-impact notes
- Warnings/caveats

## 13. Leakage / Misuse Controls

Future execution must confirm:

- Input ends at inference date only.
- No future rows in lookback.
- Realized forward returns are joined only after inference.
- No future benchmark/VIX/drawdown labels are model input.
- No symbol/date/horizon/seed changes after seeing forecasts.
- No threshold tuning.
- No raw forecast trading.
- No strategy rule creation.
- No full Research200 expansion.
- No production use.

## 14. Laptop / Abort Limits for Future Execution

Conservative future limits:

- CPU-first.
- No `Kronos-base`.
- No full Research200.
- No repeated broad sweeps.
- Maximum 18 forecast runs.
- Abort/reassess if total execution exceeds 20 minutes.
- Abort if any single forecast run hangs beyond 5 minutes.
- Abort if the laptop becomes sluggish/unusable.
- Abort if memory pressure/freezing occurs.

## 15. Success Criteria

Technical/reproducibility success means:

- All planned runs complete.
- Invalid OHLC rate is low or explainable.
- Invalid OHLC rows are not pervasive.
- Repeated seeds produce stable enough direction, rank, and return outputs for
  diagnostic use.
- Output schema is complete.
- Runtime is acceptable.
- Leakage/misuse checks pass.

Success does not mean Kronos has alpha or is strategy-approved.

## 16. Failure Criteria

Failure means:

- Invalid OHLC rows remain high or unexplained.
- Invalid OHLC rows appear across many seeds/symbols/dates.
- Predicted directions/ranks are unstable across seeds.
- Output validity depends heavily on decoding setting.
- Runtime is too heavy.
- Schema/metadata are incomplete.
- Leakage or data-mapping issue is found.
- Laptop impact is unacceptable.

## 17. Decision After Future Execution

Future execution review should choose one:

- `PARK_KRONOS_LANE`
- `FIX_ADAPTER_OR_OUTPUT_VALIDATION`
- `REPEAT_REPRO_VALIDITY_TEST`
- `REDESIGN_DIAGNOSTIC_WITH_VALIDITY_FILTERS`
- `PROCEED_TO_SMALL_DIAGNOSTIC_RETRY`

Do not proceed to a larger diagnostic until output validity and reproducibility
are acceptable.

37N chose `FIX_ADAPTER_OR_OUTPUT_VALIDATION`. 37O follows up with a debug
design and selects `PROCEED_TO_37P_ADAPTER_DEBUG_EXECUTION` because the cause is
not fully proven and because explicit eval-mode/API usage plus caller-side
validity policy need to be tested before any signal-quality retry.

## 18. Approval Requirements Before Future Execution

Before execution, the user must approve:

- Exact symbols.
- Exact dates.
- Exact seed list.
- Exact decoding settings.
- Output folder.
- Max runtime.
- No full Research200.
- No strategy rules.
- No production use.
- No raw forecast trading.

## 19. Decision

Decision: `PROCEED_TO_37N_REPRO_VALIDITY_EXECUTION_APPROVAL`.

This is not approval to execute. Phase 37N must begin with an explicit user
approval checklist.

## 20. Anti-Misuse Guardrails

- No production claims.
- No alpha conclusion from a reproducibility test.
- No raw predicted-candle execution.
- No full Research200 run.
- No best-seed cherry-picking.
- No decoding cherry-picking after results.
- No threshold tuning.
- No symbol/date cherry-picking.
- No fine-tuning before leakage/split audit.
- No committing generated reports/model weights.
- No cloud/GPU spend without approval.
