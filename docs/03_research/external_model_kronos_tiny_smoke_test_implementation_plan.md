# Phase 37F — Kronos Tiny Smoke-Test Implementation Plan

## 1. Status / Verdict

Phase 37F is docs/planning only. No installation is approved by this phase. No
model/tokenizer download is approved by this phase. No inference is approved by
this phase. No smoke test is executed by this phase.

Kronos remains approved only for possible future offline diagnostic research.
This plan prepares a future tiny smoke test only if the user explicitly
approves execution later.

Phase 37G adds the required user approval and exact execution checklist in
`docs/03_research/external_model_kronos_execution_approval_checklist.md`.
Phase 37H must not start until that approval block is filled and approved.

Phase 37H later executed the approved 1-symbol / 1-date smoke test. Phase 37I
reviews the result in
`docs/03_research/external_model_kronos_smoke_test_review.md`: technical
execution passed, but one poor forecast does not validate or reject model
quality.

## 2. Purpose of the Future Tiny Smoke Test

The future tiny smoke test should answer only:

- Can an isolated environment be created without contaminating Veridian core?
- Can the smallest chosen Kronos model/tokenizer be loaded?
- Can 1-2 NSE daily OHLCV samples be converted into Kronos-compatible format?
- Can one tiny CPU-first inference run complete without making the laptop
  unusable?
- Are output files shaped correctly for future diagnostics?
- Can metadata capture model, revision, dependencies, seed, data window,
  runtime, and caveats?

The smoke test will not answer:

- Whether Kronos is profitable.
- Whether Kronos improves S1-S5.
- Whether Kronos should trade.
- Whether Kronos is production-ready.
- Whether full Research200 inference is feasible.

## 3. Proposed Execution Boundary

Future execution boundary:

- Veridian repo remains the core research repo.
- Kronos cloned repo remains external and unmodified.
- Future sandbox should live outside Veridian core imports, for example
  `external_sandboxes/kronos_smoke/`, or another explicitly approved local
  path.
- Future generated outputs should go to
  `reports/v2/external_models/kronos/smoke_test_YYYYMMDD/`.
- Do not commit model weights.
- Do not commit generated forecast outputs unless explicitly approved.
- Do not vendor Kronos source into Veridian.
- Do not modify Kronos source.

## 4. Proposed Environment Plan

Future environment design only; do not create it now:

- Separate virtual environment required.
- Do not use Veridian `.venv`.
- No global Python install.
- No dependency merge into Veridian core.
- Python version should match Kronos README, likely Python 3.10+.
- CPU-first attempt.
- Smallest model first.
- No web UI.
- No Qlib.
- No AkShare.
- No Flask/Plotly web UI path.
- No training/fine-tuning stack.
- No background services.
- No long-running jobs.

## 5. Proposed Model / Tokenizer Selection

- Tokenizer candidate: `NeoQuasar/Kronos-Tokenizer-base`.
- Model candidate: `NeoQuasar/Kronos-small`.
- Avoid `NeoQuasar/Kronos-base` for the first smoke test because of the user's
  hardware constraint.
- Exact model/tokenizer revisions must be pinned before download/execution.
- No floating `latest` revision.
- Record model-card license and revision in metadata.

## 6. Proposed Tiny Data Sample

Future tiny sample design:

- 1-2 highly liquid Research200 symbols only.
- Do not hardcode final symbols unless verified from existing docs/data before
  execution.
- Prefer HIGH liquidity bucket and complete data.
- 1-3 inference dates maximum.
- Stable initial period, such as 2023 or 2024.
- Each inference date must have enough lookback.
- Candidate horizon: 5 sessions only for smoke.
- Lookback target: 400 sessions if feasible.
- Fallback smaller lookback only if decided before execution and recorded.

Input schema:

- `symbol`
- `date` / `timestamp`
- `open`
- `high`
- `low`
- `close`
- `volume`
- Optional `amount = close * volume`

Rules:

- Sort by `symbol` and `date`.
- Reject duplicate `symbol` / `date` rows.
- Include no future bars in input.
- Join realized forward returns only after inference.
- Preserve corporate-action caveat: current project data lacks audited
  corporate-action adjustment.

## 7. Future Planned Steps

Checklist for a later approved phase; not executed now:

1. Confirm user approval for install/download/inference.
2. Choose exact local sandbox path.
3. Choose exact model/tokenizer and revisions.
4. Choose exact 1-2 symbols and 1-3 inference dates.
5. Create isolated environment.
6. Install only minimal Kronos inference dependencies.
7. Download/pin tokenizer and smallest model.
8. Export tiny OHLCV input sample from Veridian data.
9. Run CPU-first smoke inference.
10. Write forecast paths and diagnostics.
11. Record metadata/runtime.
12. Review laptop impact and output schema.
13. Decide whether to proceed, stop, or redesign.

## 8. Future Planned Commands

DO NOT RUN THESE IN PHASE 37F.

These are future placeholder command categories only. Exact commands must be
reviewed again before execution and require explicit user approval.

Create environment:

```powershell
# FUTURE ONLY - DO NOT RUN IN PHASE 37F
# Create an isolated environment at <approved_sandbox_env_path>.
```

Install minimal dependencies:

```powershell
# FUTURE ONLY - DO NOT RUN IN PHASE 37F
# Install only reviewed minimal Kronos inference dependencies into the isolated environment.
```

Pin model revisions:

```powershell
# FUTURE ONLY - DO NOT RUN IN PHASE 37F
# Record tokenizer/model revisions for NeoQuasar/Kronos-Tokenizer-base and NeoQuasar/Kronos-small.
```

Export tiny input:

```powershell
# FUTURE ONLY - DO NOT RUN IN PHASE 37F
# Export 1-2 symbols and 1-3 inference dates to <approved_output_folder>.
```

Run tiny inference:

```powershell
# FUTURE ONLY - DO NOT RUN IN PHASE 37F
# Run CPU-first inference with fixed seed, 5-session horizon, and abort limits.
```

Inspect metadata:

```powershell
# FUTURE ONLY - DO NOT RUN IN PHASE 37F
# Inspect output schema, metadata completeness, runtime, and laptop impact.
```

Any command that downloads model/tokenizer weights must remain blocked until
the user explicitly approves model/tokenizer download in a later phase.

## 9. Future Output Schema

Future output folder:

- `reports/v2/external_models/kronos/smoke_test_YYYYMMDD/`

Future outputs, not generated now:

- `kronos_smoke_test_metadata.json`
- `kronos_smoke_test_input_sample.csv`
- `kronos_smoke_test_forecast_paths.csv`
- `kronos_smoke_test_diagnostics.csv`
- `kronos_smoke_test_runtime_notes.txt`

Required metadata fields:

- `run_id`
- `kronos_repo_path`
- `kronos_repo_commit_hash`
- `tokenizer_name`
- `tokenizer_revision_hash`
- `model_name`
- `model_revision_hash`
- `model_card_license_observed`
- `python_version`
- `dependency_versions`
- `os`
- `cpu_gpu_mode`
- `seed`
- `decoding_settings`
- `input_symbols`
- `inference_dates`
- `lookback_sessions`
- `horizon`
- `output_folder`
- `runtime`
- `memory_notes`
- `warnings_caveats`

Required diagnostics columns:

- `run_id`
- `symbol`
- `inference_date`
- `horizon`
- `pred_close_return`
- `pred_direction`
- `pred_high_low_range`
- `pred_volatility_proxy`
- `realized_forward_return`
- `forecast_error`
- `notes`

## 10. Reproducibility Plan

- Fixed seed.
- Pinned tokenizer revision.
- Pinned model revision.
- Pinned dependencies.
- Explicit decoding settings.
- Exact input sample preserved.
- No silent overwrite of output folder.
- Metadata required before accepting results.
- Repeated run optional only if laptop impact is acceptable.

## 11. Laptop Abort Criteria

Stop immediately if any abort criterion triggers:

- Install takes too long or consumes excessive disk.
- Model download is too large.
- VS Code/Chrome becomes unusable.
- CPU remains saturated for too long.
- Memory usage causes freezing/swap.
- Inference does not finish within agreed time.
- Output files are not produced.
- Any command requires Qlib/AkShare/web UI/training.
- Any dependency wants to modify Veridian core env.
- User discomfort or system instability.

## 12. Lookahead / Leakage Rules

- Input ends at inference date only.
- No future rows in lookback.
- No target-period rows in normalization.
- Realized forward returns joined only after forecast generation.
- No future NIFTY/VIX/liquidity/drawdown labels as input.
- No selecting symbols/dates after seeing forecast quality.
- No changing horizon after seeing results.
- No using predicted candles as trade entries/exits.

## 13. Success Criteria for Future Smoke Test

Technical-only success:

- Isolated environment created without touching Veridian `.venv`.
- Model/tokenizer load succeeds.
- Inference runs on tiny sample.
- Output schema matches plan.
- Metadata complete.
- Runtime/memory acceptable.
- Reproducibility acceptable under fixed seed/settings.
- Veridian core remains unchanged.

## 14. Failure Criteria

- License/model revision cannot be pinned.
- Install too heavy.
- Model too large.
- Inference too slow/heavy.
- Output unstable or malformed.
- Dependency conflict.
- Required path pulls in Qlib/AkShare/web UI/training.
- Laptop becomes unusable.
- No clear next diagnostic value.

## 15. Approval Gates Before Future Execution

- User approves install.
- User approves model/tokenizer download.
- User approves exact model/tokenizer.
- User approves exact model/tokenizer revisions.
- User approves exact environment path.
- User approves exact symbols/dates.
- User approves abort limits.
- User approves output folder.
- User confirms no full Research200 run.
- User confirms no production use.
- User confirms no raw forecast trading.
- User fills the Phase 37G approval block before any Phase 37H execution.

## 16. Phase Roadmap After 37F

Possible future phases, none approved by Phase 37F:

- Phase 37G — user approval and exact execution checklist.
- Phase 37H — tiny smoke-test execution, only if approved.
- Phase 37I — smoke-test output review.
- Phase 37J — small offline diagnostic experiment design.
- Phase 37K — small diagnostic execution, only if smoke test is acceptable.
- Fine-tuning remains deferred until leakage/split audit.

## 17. Decision

Phase 37F creates only the tiny smoke-test implementation plan.

No execution is approved. No installation is approved. No model download is
approved. No inference is approved. No production use is approved. The next
action should be a user approval checklist, not automatic execution.

## 18. Anti-Misuse Guardrails

- No raw candle execution.
- No production claims from smoke tests.
- No full Research200 first run.
- No best-horizon cherry-picking.
- No threshold tuning.
- No symbol cherry-picking.
- No future data in input/normalization.
- No fine-tuning before split/leakage audit.
- No merging Kronos dependencies into Veridian core.
- No cloud/GPU spend without explicit approval.
- No using smoke-test forecast as trading signal.
