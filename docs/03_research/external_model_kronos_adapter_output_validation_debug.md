# Phase 37O — Kronos Adapter / Output Validation Debug Design

## 1. Status / Verdict

Phase 37O is read-only inspection plus docs/design.

- No new inference is approved.
- No small diagnostic retry is approved.
- No Research200 run is approved.
- No strategy integration is approved.
- No production use is approved.
- Current decision after 37N: `FIX_ADAPTER_OR_OUTPUT_VALIDATION`.

Verdict: the likely issue is a combination of adapter/API usage and missing
output-validity policy, not a proven data-column swap. The Veridian scripts use
the expected `open, high, low, close, volume, amount` order and Kronos performs
normalization/de-normalization internally, but the scripts do not explicitly put
the tokenizer/model in eval mode, while Kronos' regression tests do. Kronos also
returns decoded OHLC columns directly and does not enforce candle constraints.

Recommended next phase:
`PROCEED_TO_37P_ADAPTER_DEBUG_EXECUTION`.

Later update: Phase 37P executed the approved tiny adapter debug and selected
`PROCEED_TO_37Q_OUTPUT_VALIDITY_POLICY_DESIGN`. Phase 37Q now documents the
policy in `docs/03_research/external_model_kronos_output_validity_policy.md`.
No further diagnostic retry is approved until the policy is implemented or a
future policy-compliant helper is explicitly approved.

## 2. Why 37O Exists

Phase 37K and 37N showed that signal-quality metrics are secondary until output
validity is understood.

- 37K invalid OHLC rows: 17 / 150 = 11.33%.
- 37N invalid OHLC rows: 16 / 90 = 17.78%.
- 37N forecasts with any invalid OHLC: 8 / 18 = 44.44%.
- 37N invalid rows occurred across both symbols, all dates, and all seeds.
- Main invalid reasons:
  - `high_lt_open`: 8.
  - `low_gt_close`: 7.
  - `high_lt_close`: 4.
  - `low_gt_open`: 4.
  - `high_lt_low`: 2.

Until the invalid OHLC source is isolated, 37K's weak/negative signal metrics
must not be interpreted as a stable conclusion about Kronos alpha.

## 3. Inspection Scope

Inspected Veridian-side files and artifacts:

- `reports/v2/external_models/kronos/small_diagnostic_20260701/run_kronos_small_diagnostic.py`
- `reports/v2/external_models/kronos/repro_validity_20260701/run_kronos_repro_validity.py`
- 37K/37N forecast paths, diagnostics, invalid-OHLC summary, manifest, input
  samples, actual forward paths, metadata, and runtime notes in the local
  generated output folders.
- Existing tracked Kronos lane docs in `docs/03_research/`,
  `docs/00_foundation/`, and `docs/05_decisions/`.

Inspected local Kronos repo files:

- `README.md`
- `model/kronos.py`
- `examples/prediction_example.py`
- `examples/prediction_wo_vol_example.py`
- `examples/prediction_batch_example.py`
- `tests/test_kronos_regression.py`
- `webui/app.py`
- `webui/README.md`
- relevant finetune/Qlib preprocessing and test references found by search.

Not inspected:

- No notebooks.
- No web UI execution.
- No Qlib/AkShare execution.
- No model inference.
- No dependency install/download.
- No Kronos repo modification.

## 4. Veridian Adapter / Script Findings

Script/artifact location:

- 37K script: generated/ignored local output folder
  `reports/v2/external_models/kronos/small_diagnostic_20260701/`.
- 37N script: generated/ignored local output folder
  `reports/v2/external_models/kronos/repro_validity_20260701/`.
- No tracked Veridian production Kronos adapter was found. The executed helper
  scripts appear copied into generated report folders rather than tracked
  source.

Input assembly:

- Prices are loaded from `prices_ohlc` with `timestamp AS date`, `open`,
  `high`, `low`, `close`, and `volume`.
- Rows are sorted by timestamp and de-duplicated by date.
- `amount` is computed as `close * volume`.
- Lookback is 400 sessions and horizon is 5 sessions.
- Future rows are exported separately for evaluation and timestamp alignment,
  not passed as price inputs to Kronos.

Kronos call:

- Both scripts call `predictor.predict` with a DataFrame ordered as
  `["open", "high", "low", "close", "volume", "amount"]`.
- `x_timestamp` uses the lookback dates.
- `y_timestamp` uses the future dates only as future timestamps.
- Decoding settings were `T=1.0`, `top_k=0`, `top_p=0.9`,
  `sample_count=1`, `max_context=512`.

Output export:

- Forecast path rows are written directly from Kronos' returned DataFrame.
- Veridian does not perform separate de-normalization; Kronos' predictor does.
- Veridian does not repair, clip, reject, or structurally constrain predicted
  OHLC before writing.

Validity check:

- 37N checks `open > 0`, `high > 0`, `low > 0`, `close > 0`,
  `high >= low`, `high >= open`, `high >= close`, `low <= open`,
  `low <= close`, `volume >= 0`, and `amount >= 0`.
- Those checks are correct for basic candle validity.
- The invalid rows are visible in raw `kronos_repro_validity_forecast_paths.csv`.
- The largest inspected contradiction was material, about 2.89% of close, so
  invalidity is not only a floating-point epsilon issue.

Mapping/de-normalization risks:

- A simple output-column misalignment is unlikely: both Veridian and Kronos use
  the same explicit `open, high, low, close, volume, amount` column order.
- A Veridian de-normalization bug is unlikely: the Veridian scripts do not
  de-normalize; Kronos does inverse normalization inside `predict`.
- A notable API-usage risk remains: the Veridian scripts do not explicitly call
  `tokenizer.eval()` or `model.eval()`. Kronos' regression tests do call both
  before constructing the predictor.

## 5. Kronos API / Source Findings

Files/functions inspected:

- `KronosTokenizer`
- `Kronos`
- `auto_regressive_inference`
- `KronosPredictor.generate`
- `KronosPredictor.predict`
- `KronosPredictor.predict_batch`
- README forecast examples
- regression tests
- web UI prediction path

Key findings:

- `KronosPredictor.predict` requires `open`, `high`, `low`, `close`;
  `volume` and `amount` are optional.
- If `amount` is absent but `volume` is present, Kronos computes amount as
  `volume * mean(open, high, low, close)`.
- If `volume` is absent, Kronos fills both volume and amount with zero.
- Kronos computes per-column `x_mean` and `x_std`, normalizes the six feature
  columns, clips normalized inputs, runs autoregressive token generation, then
  inverse-normalizes predictions.
- Kronos returns a DataFrame with columns
  `open, high, low, close, volume, amount`.
- The README says `KronosPredictor` handles preprocessing, normalization,
  prediction, and inverse normalization.
- The README and examples do not state that returned OHLC is guaranteed to be
  candle-valid.
- The examples and web UI plot or serialize returned OHLC directly; no repair
  or validity check was found.
- `auto_regressive_inference` samples discrete tokens using temperature,
  top-k/top-p filtering, and `torch.multinomial`; it averages across
  `sample_count`.
- The implementation has deterministic/low-randomness levers such as `top_k=1`
  and `top_p=1.0`; Kronos' regression tests use `top_k=1`, `top_p=1.0`,
  `sample_count=1`.
- Regression tests call `tokenizer.eval()` and `model.eval()` before
  prediction.
- No built-in OHLC repair, post-processing, or validity enforcement was found.

Interpretation:

Kronos appears to decode a multi-feature vector through token reconstruction,
then inverse-normalize each feature column. That does not automatically enforce
the structural constraints `high >= max(open, close)` and
`low <= min(open, close)`.

## 6. Generated Output Schema Findings

Generated output folders were present locally:

- `reports/v2/external_models/kronos/small_diagnostic_20260701/`
- `reports/v2/external_models/kronos/repro_validity_20260701/`

37N schema:

- Forecast path rows checked: 90.
- Columns include `run_id`, `symbol`, `inference_date`, `seed`,
  `forecast_step`, `date`, `open`, `high`, `low`, `close`, `volume`, `amount`,
  `invalid_ohlc`, and `invalid_reasons`.
- Invalid rows are visibly present in raw forecast-path CSV, not only in the
  summary.
- Invalid reason logic matches the raw OHLC values.
- Volume and amount were non-negative in inspected invalid rows; the observed
  blocker is OHLC structure, not negative volume/amount.
- Forecast dates align to the exported future dates by forecast step.
- Violations range from tiny (`0.0016%` of close) to material (`~2.89%` of
  close).

37K schema:

- Forecast path rows checked: 150.
- 37K did not include invalid flags in the raw path file, but 37L/37N result
  docs record 17 invalid OHLC rows from that path.

## 7. Root-Cause Assessment

| Root cause category | Status | Evidence | Next check/fix |
| --- | --- | --- | --- |
| Output-column misalignment | UNLIKELY | Veridian passes and reads `open, high, low, close, volume, amount`; Kronos returns the same explicit order. Invalids include both high/low relation failures, not a consistent swapped-column signature. | Add a one-run schema assertion around returned columns before any future inference. |
| Invalid-OHLC check bug | UNLIKELY | 37N checks match standard candle constraints, and raw invalid rows visibly violate them. | Keep the check; add a reason-by-reason sample export and magnitude fields. |
| Amount/volume mapping issue | POSSIBLE | Veridian computes `amount = close * volume`, while Kronos examples can use supplied amount or compute `volume * mean(OHLC)`. Web UI notes amount is optional/not central. No negative volume/amount was seen in invalid rows. | Compare `close * volume` vs OHLC-average amount as an adapter-only hypothesis in 37P if inference is approved. |
| Kronos API misuse | POSSIBLE | Veridian scripts do not call `tokenizer.eval()`/`model.eval()`; Kronos tests do. Decoding settings differ from regression tests (`top_k=0`, `top_p=0.9` vs `top_k=1`, `top_p=1.0`). | 37P should first patch the helper script design to force eval mode and record model/tokenizer training flags before prediction. |
| Independent OHLC decoding/no constraint enforcement | LIKELY | Kronos decodes feature vectors and inverse-normalizes outputs, but no candle validity enforcement or repair exists in predictor/examples/tests. Invalid rows appear directly in raw output. | Treat validity enforcement as caller responsibility unless upstream docs/code prove otherwise. |
| Stochastic sampling instability | LIKELY | 37N invalid rates vary by seed and output directions/ranks vary across seeds. Kronos uses multinomial sampling and top-p; README calls these probabilistic controls. | 37P should test deterministic/near-deterministic settings only if execution is explicitly approved. |
| Missing output validation/post-processing | LIKELY | Veridian writes forecast rows directly; Kronos examples do too; no validity policy exists for reject/flag/repair. | Design a non-leaky validity policy before any signal retry. |
| Normalization/de-normalization mismatch | POSSIBLE | Kronos handles normalization internally. No Veridian de-normalization exists, making a Veridian inverse-transform bug unlikely, but cross-market distribution mismatch or column scale effects could still matter. | In 37P, record input means/stds and returned ranges for each column without changing model behavior. |
| Date/step alignment issue | UNLIKELY | Future timestamps are used only for y timestamps, and output rows map step-by-step to future dates. Invalidity is within same-row OHLC relationships. | Keep existing date alignment assertions. |
| Model limitation | POSSIBLE | If eval-mode and decoding checks do not reduce invalid rows, invalid candles may be inherent to Kronos-small generation for this data/horizon. | Park or allow only validity-filtered diagnostics if invalid rate remains high after adapter correction. |

## 8. Output-Validity Policy Options

These options are discussed only; none is approved by 37O.

| Option | Pros | Cons | Leakage/misuse risk | Future diagnostic acceptability |
| --- | --- | --- | --- | --- |
| Reject/flag invalid forecast rows only | Preserves maximum data and makes invalidity explicit. | Horizon path becomes incomplete; final close-return may still come from a run with invalid intermediate candles. | Medium if users ignore invalid flags. | Acceptable only for diagnostics that do not depend on path shape. |
| Reject entire forecast run if any path row invalid | Conservative and easy to audit. | Can shrink tiny samples sharply; invalid-rate itself may dominate conclusions. | Low. | Acceptable for output-validity-first diagnostics. |
| Use close-return only and ignore OHLC path shape | Aligns with ranking use case and avoids raw candle misuse. | Ignores evidence that model output manifold may be structurally weak. | Medium/high if invalid path is hidden. | Only acceptable with explicit invalid-run flags and separate path-validity metrics. |
| Non-leaky OHLC repair using `high=max(open, high, low, close)` and `low=min(open, high, low, close)` | Produces candle-valid paths using only predicted same-row values. | Alters model output and may inflate visual/path metrics; does not fix model quality. | High if repaired candles are used as signal evidence. | Possibly acceptable for visualization only, not signal evaluation, unless separately justified. |
| Constrain output only for visualization, not signal evaluation | Avoids broken plots without changing diagnostic metrics. | Two versions of output can confuse review. | Medium unless files are clearly labeled. | Acceptable if raw output remains canonical. |
| Park Kronos if invalid rate remains high | Avoids spending effort on unreliable output. | May discard a useful close-return/ranking signal prematurely. | Low. | Appropriate if eval-mode/decoding/output-policy checks fail. |

## 9. Recommended Next Phase

Decision: `PROCEED_TO_37P_ADAPTER_DEBUG_EXECUTION`.

Reason:

- Cause is not fully proven.
- There is a concrete adapter/API issue to test: missing explicit eval mode in
  Veridian helper scripts versus Kronos regression tests.
- There is also a concrete output-policy gap: no caller-side validity handling.
- The next step should not be a small diagnostic retry, a Research200 run, or a
  validity-filter-only result pass.

37P should be a narrow debug execution only if explicitly approved. It should
edit or create only a bounded helper script/docs, avoid new model downloads,
reuse the existing local cache, and run the smallest possible already-approved
sample needed to compare:

- current settings with explicit eval mode,
- deterministic/near-deterministic settings if approved,
- raw output validity,
- no repair versus flagged/rejected policy.

37P later found eval mode reduced invalid output but did not eliminate it, and
deterministic-ish decoding produced zero invalid rows only on one tiny sample.
37Q therefore defines a conservative validity policy rather than allowing a
small diagnostic retry.

## 10. Approval Needed Before Any Execution

Before 37P, the user must approve:

- Whether 37P is execution or docs-only.
- Exact files/scripts allowed to edit.
- Whether new inference is allowed.
- Whether output-validation-only rerun is allowed.
- Exact symbols, dates, seeds, and decoding settings if rerun.
- Runtime cap.
- Reuse of existing isolated Kronos venv/cache only.
- No full Research200.
- No strategy integration.
- No production use.
- No raw forecast trading.
- No model/tokenizer download.
- No Kronos repo modification.
- No generated report/model-weight commits.

## 11. Anti-Misuse Guardrails

- No alpha conclusion while output validity is unresolved.
- No raw predicted-candle trading.
- No full Research200.
- No best-seed selection.
- No decoding cherry-picking.
- No threshold tuning.
- No strategy rules.
- No production claims.
- No generated report/model-weight commits.
- No "repair and trade" interpretation.
- Raw Kronos output remains the canonical diagnostic artifact unless a future
  phase explicitly documents a separate visualization-only repaired view.
