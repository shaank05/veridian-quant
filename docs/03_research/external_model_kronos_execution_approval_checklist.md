# Phase 37G â€” Kronos User Approval and Exact Execution Checklist

## 1. Status / Verdict

Phase 37G is docs/checklist only.

- No install is approved by this phase.
- No model/tokenizer download is approved by this phase.
- No inference is approved by this phase.
- No smoke test is executed by this phase.
- This phase creates the approval checklist for a possible Phase 37H execution.
- Kronos remains approved only for possible future offline diagnostic research.
- No production use is approved.

## 2. Execution Cannot Start Until These Are Checked

Phase 37H cannot start until every relevant item below is explicitly approved
or confirmed by the user:

- [ ] User approves creating a separate Kronos environment.
- [ ] User approves dependency installation in that separate environment.
- [ ] User approves Hugging Face model/tokenizer download.
- [ ] User approves exact tokenizer.
- [ ] User approves exact model.
- [ ] User approves exact tokenizer revision/hash.
- [ ] User approves exact model revision/hash.
- [ ] User approves exact local sandbox path.
- [ ] User approves exact output folder.
- [ ] User approves exact symbols.
- [ ] User approves exact inference dates.
- [ ] User approves horizon/lookback settings.
- [ ] User approves abort criteria.
- [ ] User confirms no full Research200 run.
- [ ] User confirms no production use.
- [ ] User confirms no raw predicted-candle trading.
- [ ] User confirms no fine-tuning/training.
- [ ] User confirms no web UI/Qlib/AkShare.

## 3. Proposed Default Execution Choices

These are proposed defaults only. They are not approved until the user confirms
them before Phase 37H.

Model/tokenizer:

- Tokenizer: `NeoQuasar/Kronos-Tokenizer-base`.
- Model: `NeoQuasar/Kronos-small`.
- Avoid `NeoQuasar/Kronos-base` for the first smoke test because of the user's
  hardware constraint.
- Exact revisions: `TBD before download`.

Environment:

- Separate local virtual environment.
- Do not use Veridian `.venv`.
- Do not install globally.
- Do not add dependencies to Veridian core.
- Future path: user-approved path only.

Execution mode:

- CPU-first.
- No web UI.
- No training/fine-tuning.
- No Qlib.
- No AkShare.
- No notebooks.
- No full Research200.
- No repeated sweeps.

Data limits:

- 1-2 symbols only.
- 1-3 inference dates only.
- High-liquidity Research200 symbols preferred.
- Horizon: 5 sessions only.
- Lookback: 400 sessions if feasible, fallback only if documented before
  execution.

## 4. Exact Items Still TBD

- Exact tokenizer revision/hash.
- Exact model revision/hash.
- Exact environment path.
- Exact Kronos repo path.
- Exact sandbox path.
- Exact symbols.
- Exact inference dates.
- Exact lookback if 400 is not feasible.
- Exact output folder.
- Exact runtime abort limit.
- Exact disk/download size limit.
- Exact memory/CPU comfort limit.

## 5. Abort Criteria

Stop immediately if any strict abort condition triggers:

- User laptop becomes sluggish/unusable.
- VS Code/Chrome becomes unstable.
- Install takes longer than agreed limit.
- Download size exceeds agreed limit.
- CPU remains saturated longer than agreed limit.
- Memory pressure/freezing/swap appears.
- Dependency tries to modify Veridian `.venv` or global Python.
- Command requires Qlib/AkShare/web UI/training.
- Model loading fails.
- Inference does not complete within agreed time.
- Output schema missing or malformed.
- User decides to stop for any reason.

## 6. Allowed Future 37H Actions If Approved

Only these actions may be allowed in Phase 37H after explicit user approval:

- Create isolated Kronos environment.
- Install minimal inference dependencies.
- Pin/download tokenizer and smallest model.
- Export tiny OHLCV input sample.
- Run CPU-first inference on 1-2 symbols and 1-3 dates.
- Generate smoke-test metadata/output files.
- Record runtime/laptop impact.
- Review output schema.

## 7. Disallowed Future 37H Actions

Even if Phase 37H is approved, these actions remain disallowed:

- Full Research200 run.
- Raw predicted-candle trading.
- Strategy-rule creation.
- Threshold tuning.
- Backtest optimization.
- Production deployment.
- Model serving.
- Web UI.
- Qlib/AkShare path.
- Training/fine-tuning.
- GPU/cloud spending.
- Installing dependencies into Veridian core env.
- Modifying Kronos source.
- Committing model weights or generated forecast reports unless explicitly
  approved.

## 8. Future Output Folder and Files

Planned output folder:

- `reports/v2/external_models/kronos/smoke_test_YYYYMMDD/`

Planned files:

- `kronos_smoke_test_metadata.json`
- `kronos_smoke_test_input_sample.csv`
- `kronos_smoke_test_forecast_paths.csv`
- `kronos_smoke_test_diagnostics.csv`
- `kronos_smoke_test_runtime_notes.txt`

Generated output files are not committed unless explicitly approved. Model
weights are never committed.

## 9. Required Metadata Before Accepting 37H Results

Phase 37H results cannot be accepted unless metadata includes:

- `run_id`
- `Kronos repo path`
- `Kronos repo commit hash`
- `tokenizer name`
- `tokenizer revision/hash`
- `model name`
- `model revision/hash`
- `license observed`
- `Python version`
- `dependency versions`
- `OS`
- `CPU/GPU mode`
- `seed`
- `decoding settings`
- `symbols`
- `inference dates`
- `lookback sessions`
- `horizon`
- `output folder`
- `runtime`
- `memory/laptop-impact notes`
- `warnings/caveats`

## 10. Lookahead / Leakage Checks

- [ ] Input ends at inference date only.
- [ ] No future rows in lookback.
- [ ] Realized forward returns joined only after forecast generation.
- [ ] No future NIFTY/VIX/liquidity/drawdown labels as input.
- [ ] No choosing symbols/dates after seeing forecast quality.
- [ ] No changing horizon after seeing results.
- [ ] No using predicted OHLC as trade entries/exits.

## 11. Success Criteria for 37H

Technical-only success:

- Separate environment created without touching Veridian `.venv`.
- Model/tokenizer load succeeds.
- Tiny inference completes.
- Output files created in expected schema.
- Metadata complete.
- Runtime/memory acceptable.
- Output reproducible enough under fixed seed/settings.
- Veridian core remains unchanged.
- User laptop remains usable.

## 12. Failure Criteria for 37H

Phase 37H fails if:

- License/revision cannot be pinned.
- Install/download too heavy.
- Model too large.
- Inference too slow.
- Laptop becomes unstable.
- Dependencies conflict.
- Output malformed.
- Reproducibility unacceptable.
- Execution requires disallowed Qlib/AkShare/web UI/training path.
- No clear diagnostic value from continuing.

## 13. User Approval Block

Copy and fill this block before any Phase 37H execution:

```text
PHASE 37H EXECUTION APPROVAL

I approve:
* creating a separate Kronos environment: yes/no
* installing minimal Kronos inference dependencies: yes/no
* downloading tokenizer `NeoQuasar/Kronos-Tokenizer-base` revision `...`: yes/no
* downloading model `NeoQuasar/Kronos-small` revision `...`: yes/no
* using environment path: ...
* using sandbox path: ...
* using output folder: ...
* symbols: ...
* inference dates: ...
* lookback sessions: ...
* horizon: ...
* max install time: ...
* max download size: ...
* max inference time: ...
* abort if laptop becomes sluggish: yes
* no full Research200 run: yes
* no production use: yes
* no raw forecast trading: yes
```

## 14. Phase Roadmap After 37G

Possible future phases, none approved by Phase 37G:

- Phase 37H â€” tiny smoke-test execution, only if user fills approval block.
- Phase 37I â€” smoke-test output review.
- Phase 37J â€” small offline diagnostic experiment design, only if smoke test
  passes.
- Phase 37K â€” small diagnostic execution, only if approved.
- Fine-tuning remains deferred until leakage/split audit.

## 15. Decision

Phase 37G creates only the exact execution approval checklist.

- No execution approved.
- No install approved.
- No download approved.
- No inference approved.
- No production approval.
- Next action must be explicit user approval before Phase 37H.

## 16. Anti-Misuse Guardrails

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
