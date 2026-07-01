# Phase 37Q — Kronos Output Validity Policy Design

## 1. Status / Verdict

Phase 37Q is docs/design only.

- No new inference is approved.
- No diagnostic retry is approved.
- No Research200 run is approved.
- No strategy integration is approved.
- No production use is approved.

Current decision from 37P: design an output-validity and decoding policy before
any further Kronos diagnostics.

Recommended next phase:
`PROCEED_TO_37R_OUTPUT_VALIDITY_POLICY_IMPLEMENTATION`.

Reason: the policy below needs reusable implementation in the future Kronos
helper/adapter layer before any small diagnostic retry. Phase 37Q does not
approve that implementation or any inference.

Phase 37R implementation update:

- Reusable policy helpers were added in
  `src/veridian_quant/v2/external_models/kronos/output_validity.py`.
- Synthetic-data tests were added in
  `tests/v2/test_kronos_output_validity.py`.
- The implementation is policy/helper only. It does not run Kronos inference,
  load models, modify the cloned Kronos repository, generate reports, run
  backtests, or change strategy logic.
- The next selected gated step is
  `PROCEED_TO_37S_POLICY_COMPLIANT_RETRY_DESIGN`, not diagnostic execution.

Phase 37S retry-design update:

- The policy-compliant retry design is documented in
  `docs/03_research/external_model_kronos_policy_compliant_retry_design.md`.
- It requires explicit eval when supported, deterministic-ish decoding, and
  37R helper-based output-validity gating before any future retry.
- It selects `PROCEED_TO_37T_POLICY_COMPLIANT_RETRY_APPROVAL`; this remains an
  approval gate, not execution approval.

## 2. Why 37Q Exists

The Kronos lane is technically runnable, but output validity has repeatedly
failed or remained uncertain.

Numeric evidence:

- 37K invalid OHLC rows: 17 / 150 = 11.33%.
- 37N invalid OHLC rows: 16 / 90 = 17.78%.
- 37N forecasts with invalid OHLC: 8 / 18 = 44.44%.
- 37P `baseline_37n_like` invalid OHLC: 3 / 15 = 20.00%.
- 37P `explicit_eval` invalid OHLC: 1 / 15 = 6.67%.
- 37P `deterministic_low_randomness` invalid OHLC: 0 / 15 = 0.00%.

37P also showed decoding choice changes output direction:

- Baseline: `down;up;up`.
- Explicit eval: `up;down;down`.
- Deterministic low-randomness: `up;up;up`.

Therefore output validity and decoding policy must be pre-registered before
further evaluation. The purpose is structural validity and reproducibility, not
return optimization.

## 3. Primary Policy Questions

Phase 37Q answers or frames these questions:

- Should future Kronos diagnostics require explicit `.eval()`?
- Should deterministic-ish decoding be mandatory?
- Should stochastic multi-sample decoding be disallowed until a stronger
  validity protocol exists?
- Should invalid OHLC rows invalidate only the row, the forecast run, the
  symbol/date, or the entire diagnostic?
- Is non-leaky OHLC repair allowed, and if so only for visualization or also
  for metrics?
- Should close-return diagnostics be allowed if OHLC path shape is invalid?
- What audit fields must be exported for every future Kronos run?
- What threshold makes an experiment fail due to invalid outputs?

## 4. Explicit Non-Goals

Phase 37Q is not:

- Alpha validation.
- A trading strategy.
- Raw candle trading.
- A repair-and-trade policy.
- `Kronos-base` approval.
- Full Research200 approval.
- Threshold tuning for returns.
- Fine-tuning.
- Production readiness.
- Best-seed or best-decoding cherry-picking.

## 5. Required Future API / Decoding Defaults

Future Kronos diagnostic helpers must use these defaults unless a later
approved design explicitly changes them:

- Always call `.eval()` on tokenizer/model if supported.
- Record whether `.eval()` is supported and applied for each object.
- Record tokenizer/model training flags before and after the eval call.
- Use CPU-first unless separately approved.
- Use pinned tokenizer/model revisions.
- Use deterministic-ish decoding as the default candidate for diagnostic retry
  if supported:
  - `top_k=1`
  - `top_p=1.0`
  - `sample_count=1`, unless separately approved
  - record `T` / temperature and every other decoding setting
- Do not choose decoding settings after seeing results.
- Do not compare many decoding settings and pick the best-performing one.
- If multiple configurations are tested, treat them as separate pre-registered
  configurations, not optimization.

Stochastic multi-sample decoding should remain disallowed for signal-quality
diagnostics until a stronger validity/reproducibility protocol exists. It may
be studied later only as a separately approved output-stability experiment.

## 6. OHLC Validity Rules

Every future Kronos forecast path row must be checked with these rules:

- `open > 0`
- `high > 0`
- `low > 0`
- `close > 0`
- `high >= low`
- `high >= open`
- `high >= close`
- `low <= open`
- `low <= close`
- `volume >= 0` if volume exists
- `amount >= 0` if amount exists

Required row-level audit fields:

- `invalid_ohlc_row`
- `invalid_ohlc_reasons`
- `invalid_violation_magnitude_abs`
- `invalid_violation_magnitude_pct_close`
- `forecast_step`
- `config_name`
- `seed`
- `symbol`
- `inference_date`

The canonical validity check must run on raw Kronos output before any optional
visualization repair.

## 7. Default Invalid-Output Handling Policy

Conservative default:

- If any forecast path row for a symbol/date/run has invalid OHLC, mark the
  entire forecast run as `INVALID_OUTPUT`.
- Do not use that forecast run for directional accuracy, rank IC, top/bottom
  spread, forecast-error, or other signal-quality metrics.
- Still include that forecast run in output-validity metrics.
- Do not silently repair invalid OHLC for signal metrics.
- Do not drop invalid rows without counting the forecast run as invalid.
- Do not use repaired candles for trading, strategy logic, stops, targets, or
  entries.

This treats invalid output as a run-level quality failure, not as a row-level
inconvenience.

## 8. Repair / Coercion Policy

Non-leaky OHLC repair formula, if a future phase approves display repair:

- `repaired_high = max(open, high, low, close)`
- `repaired_low = min(open, high, low, close)`

Policy:

- Repair may be acceptable only for visualization or sanity display.
- Repair must not be used for signal-quality metrics unless separately
  approved and clearly marked.
- Repair must never be used to create tradable stop/target/entry logic.
- Raw and repaired values must both be preserved if repair is ever used.
- Repair rate must be reported.
- Repaired outputs must be labeled as derived display artifacts, not canonical
  model output.

No "repair and trade" interpretation is allowed.

## 9. Close-Return-Only Policy

Conservative recommendation:

- Close-return metrics may only be computed on forecast runs with valid OHLC
  path rows, unless a future doc explicitly approves close-only mode.
- A close-only mode would need separate labeling:
  `CLOSE_ONLY_DIAGNOSTIC`.
- Close-only mode must ignore predicted high/low path shape.
- Close-only mode must not support raw candle trading.
- Close-only mode must report planned runs, valid runs, invalid/excluded runs,
  and exclusion rate.

Do not use close-return-only metrics to hide invalid path output. If a run has
invalid OHLC, default policy excludes that run from signal-quality metrics even
if its final close is numerically available.

## 10. Experiment Failure Thresholds

Pre-registered validity thresholds:

- Any future diagnostic with invalid forecast-run rate > 0% must not be used
  for raw OHLC/path metrics.
- If invalid forecast-run rate > 5%, diagnostic is
  `OUTPUT_VALIDITY_FAILED`.
- If invalid path-row rate > 1%, diagnostic is at minimum
  `OUTPUT_VALIDITY_WARNING`.
- If invalid path-row rate > 5%, diagnostic is
  `OUTPUT_VALIDITY_FAILED`.
- If deterministic/eval mode still produces invalid outputs in repeated
  checks, do not scale without policy revision.

These are validity gates, not trading thresholds. They must not be tuned to
improve rank IC, directional accuracy, spread, or PnL.

## 11. Required Output Files for Future Kronos Diagnostic

Any future Kronos diagnostic run must produce:

- Metadata JSON.
- Input manifest CSV.
- Raw forecast paths CSV.
- Diagnostics CSV.
- Invalid OHLC summary CSV.
- Config/seed settings CSV if applicable.
- Metric summary CSV.
- Runtime notes TXT.
- Leakage/misuse checklist.

Generated outputs remain ignored and are not for commit unless separately
approved.

## 12. Required Metadata for Future Kronos Run

Future metadata must include:

- Model/tokenizer names and revisions.
- Kronos repo commit.
- Python/dependency versions.
- CPU/GPU mode.
- Eval mode status.
- Exact decoding settings.
- Seed list.
- Symbol/date selection rule.
- Lookback/horizon.
- Forecast run count.
- Invalid-output policy version.
- Output folder.
- Runtime.
- Warnings/caveats.

Recommended policy version label:
`kronos_output_validity_policy_37q_v1`.

## 13. Signal-Metric Eligibility Rules

Signal-quality metrics may only be reported on valid forecast runs.

Every future metric table must report:

- Planned forecast runs.
- Completed forecast runs.
- Valid forecast runs.
- Invalid forecast runs.
- Excluded forecast runs.
- Valid forecast-run rate.
- Invalid path-row rate.

If valid forecast count is too small, rank IC/top-bottom metrics are not
meaningful and must be labeled as unavailable or illustrative only.

Do not compare a filtered valid-only result against a prior unfiltered result
as evidence of improvement. Do not tune the validity policy based on better
signal metrics.

## 14. Decoding-Choice Anti-Cherry-Picking Rules

Decoding policy must be selected for structural validity and reproducibility
only.

Rules:

- Never select decoding mode because it improves directional accuracy, rank IC,
  spread, or PnL.
- If deterministic mode is selected, document that stochastic diversity is
  sacrificed.
- Do not compare many `top_k` / `top_p` / temperature combinations.
- Do not choose the best seed.
- Seed list must be pre-registered.
- Any multi-configuration run must define each configuration before inference
  and report all configurations, not only the best-looking one.

## 15. Approval Requirements Before Future Execution

Before any future Kronos execution, the user must approve:

- Whether inference is allowed.
- Exact sample size.
- Exact symbols/dates or deterministic selection rule.
- Decoding settings.
- Seed list.
- Output-validity policy.
- Runtime cap.
- Generated output path.
- No full Research200.
- No strategy integration.
- No production use.
- No raw forecast trading.

Any approval must also restate no model download, no Kronos repo modification,
no generated report commit, no threshold tuning, and no fine-tuning unless a
later phase explicitly changes those boundaries.

## 16. Recommended Next Phase

Decision: `PROCEED_TO_37R_OUTPUT_VALIDITY_POLICY_IMPLEMENTATION`.

Reason:

- Phase 37Q is docs-only.
- No reusable tracked adapter/output-validity implementation exists yet.
- Existing 37K/37N/37P helpers are generated scripts in ignored report folders.
- Before any small diagnostic retry, the project needs a reusable, auditable
  policy implementation or explicitly approved helper-script template that
  applies eval mode, deterministic decoding defaults, run-level invalid-output
  exclusion, and required audit exports.

Do not choose immediate execution. Do not proceed to a small diagnostic retry
until the policy is implemented or a future phase explicitly approves a
policy-compliant generated helper.

Phase 37R implemented the reusable validity helpers and synthetic tests. The
policy remains a gate: any future retry still requires a separate
policy-compliant retry design and approval.

## 17. Anti-Misuse Guardrails

- No production claims.
- No raw predicted-candle trading.
- No full Research200.
- No threshold tuning.
- No best-seed selection.
- No decoding cherry-picking.
- No repair-and-trade.
- No strategy logic.
- No generated reports/model-weight commits.
- No fine-tuning before separate leakage/split audit.
- No signal-quality conclusion while output validity policy is not implemented.
