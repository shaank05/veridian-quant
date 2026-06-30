# Phase 37D — Kronos License / Model-Weight Verification and Tiny Smoke-Test Plan

## 1. Status / Verdict

Phase 37D is docs-only. No installation is approved. No model download is
approved. No Hugging Face download is approved. No inference is approved. No
smoke test is run.

Kronos remains approved only for possible future offline diagnostic research.
This phase creates gates and checklists for a future tiny smoke test, not the
smoke test itself.

Phase 37E records the manual license/model-card verification result in
`docs/03_research/external_model_kronos_license_verification_result.md`. That
result appears sufficient to proceed to tiny smoke-test implementation planning,
but it does not approve installation, model download, inference, or production
use.

## 2. Why This Phase Exists

Phase 37A found Kronos feasible for offline diagnostic research. Phase 37B
defined the offline evaluation design. Phase 37C defined sandbox and data
adapter boundaries.

Before any installation or model download, Veridian needs:

- License/model-weight verification checklist.
- Dependency isolation checklist.
- Tiny smoke-test plan.
- Reproducibility plan.
- User-hardware-safe execution limits.

## 3. License / Model-Weight Verification Checklist

Future manual verification checklist before any model download or use:

- [ ] Kronos repo license file and license type.
- [ ] Hugging Face model card license for `NeoQuasar/Kronos-Tokenizer-base`.
- [ ] Hugging Face model card license for `NeoQuasar/Kronos-small`.
- [ ] Hugging Face model card license for `NeoQuasar/Kronos-base`.
- [ ] Hugging Face model card license for any other model weight explicitly
  selected later.
- [ ] Model card usage restrictions.
- [ ] Commercial/internal research terms.
- [ ] Redistribution restrictions.
- [ ] Required attribution/notices.
- [ ] Dataset/license caveats if model card mentions training data.
- [ ] Whether model weights have a separate license from repo code.
- [ ] Exact model revision/hash to pin.
- [ ] Date of license verification.
- [ ] Person/tool that verified it.
- [ ] Link or recorded source path.
- [ ] Verdict field:
  `CLEAR_FOR_INTERNAL_RESEARCH`, `CLEAR_FOR_PRODUCTION_EVALUATION`,
  `RESTRICTED`, or `UNCLEAR_NEEDS_REVIEW`.

Do not claim the license is approved unless directly verified and documented in
a later phase. This document is a checklist/plan, not a legal opinion.

## 4. Dependency / Environment Verification Checklist

Future environment verification checklist:

- [ ] Python version.
- [ ] OS compatibility.
- [ ] PyTorch version.
- [ ] CPU-only support.
- [ ] CUDA/GPU optionality.
- [ ] Hugging Face Hub dependency.
- [ ] `safetensors` dependency.
- [ ] `pandas` / `numpy` / `matplotlib` dependencies.
- [ ] Optional dependencies avoided initially: Qlib, AkShare, Flask/web UI,
  Plotly/web UI, and training/fine-tuning stack.
- [ ] Separate virtual environment required.
- [ ] Veridian `.venv` not used.
- [ ] Kronos dependencies not added to Veridian core.
- [ ] No global Python installs.
- [ ] No startup/background services.
- [ ] No web UI.

## 5. Tiny Smoke-Test Purpose

A future tiny smoke test, if approved, should answer only:

- Can Kronos load the smallest selected model in an isolated environment?
- Can one tiny NSE OHLCV sample be converted into the expected format?
- Can inference run on 1-2 symbols and a tiny date set?
- Are outputs reproducible under fixed seed/settings?
- What is the approximate runtime and memory impact on the user's laptop?
- Are output files shaped correctly for later diagnostics?

The smoke test should not answer:

- Whether Kronos is profitable.
- Whether Kronos should trade.
- Whether Kronos improves S2/S3/S4/S5.
- Whether Kronos is production-ready.
- Whether full Research200 inference is feasible.

## 6. Tiny Smoke-Test Constraints

Strict future constraints:

- Smallest Kronos model only.
- CPU-only first if feasible.
- No GPU requirement.
- No web UI.
- No Qlib.
- No AkShare.
- No fine-tuning.
- No training.
- No notebooks.
- No full Research200.
- No long-running jobs.
- No automatic repeated sweeps.
- Maximum 1-2 symbols initially.
- Maximum 1-3 inference dates initially.
- Short horizon only, such as 5 sessions.
- Fixed seed.
- Deterministic or near-deterministic decoding if supported.
- Output diagnostics only.
- Abort if runtime/memory is too heavy.

## 7. Candidate Smoke-Test Data Plan

Future tiny dataset design, not generated now:

- Candidate symbols: use 1-2 highly liquid NSE symbols from Research200. Do not
  hardcode final choices until liquidity and data completeness are checked.
- Candidate date plan: choose 1-3 inference dates from a stable period, such as
  2023 or 2024.
- Each inference date must have enough lookback.
- No future rows are included in input.
- Realized forward returns are used only for post-inference evaluation.

Candidate fields:

- `symbol`
- `date` / `timestamp`
- `open`
- `high`
- `low`
- `close`
- `volume`
- Optional `amount = close * volume`

## 8. Smoke-Test Output Plan

Candidate future output folder:

- `reports/v2/external_models/kronos/smoke_test_YYYYMMDD/`

Candidate future outputs, not generated now:

- `kronos_smoke_test_metadata.json`
- `kronos_smoke_test_input_sample.csv`
- `kronos_smoke_test_forecast_paths.csv`
- `kronos_smoke_test_diagnostics.csv`
- `kronos_smoke_test_runtime_notes.txt`

Metadata should include:

- Kronos repo commit hash.
- Model name.
- Model revision/hash.
- Tokenizer name.
- Tokenizer revision/hash.
- Dependency versions.
- Python version.
- OS.
- CPU/GPU mode.
- Seed.
- Decoding settings.
- Input symbols.
- Inference dates.
- Lookback sessions.
- Horizon.
- Runtime.
- Memory observations if available.
- Warnings/caveats.

## 9. Reproducibility Rules

- Use a fixed seed.
- Pin model revision.
- Pin tokenizer revision.
- Pin dependency versions.
- Record decoding settings.
- Record data extraction window.
- Record exact symbol/date rows.
- Do not silently overwrite output folders.
- Do not compare smoke-test output to production claims.

## 10. Lookahead / Leakage Rules

- Input ends at inference date only.
- No future target rows in lookback.
- No full-window normalization including target period.
- Realized forward returns joined only after forecast generation.
- No horizon or threshold selection based on final PnL.
- No use of future labels as features.
- No future NIFTY/VIX/liquidity/drawdown state as input.

## 11. Success Criteria for Future Smoke Test

Success means technical feasibility only:

- Environment created successfully.
- Smallest model loads.
- Inference runs on 1-2 symbols without crashing.
- Output schema is valid.
- Runtime/memory acceptable for the user's laptop.
- Fixed seed produces stable enough outputs.
- Metadata captured.
- No Veridian core dependency contamination.

## 12. Failure Criteria for Future Smoke Test

Failure or stop criteria:

- Install too heavy or breaks environment.
- Model cannot load.
- Runtime/memory unacceptable.
- Output not reproducible enough.
- Data format incompatible.
- Dependency conflicts with Veridian core.
- License/model terms unclear.
- Any step requires web UI, Qlib, AkShare, or training for basic inference.
- User laptop becomes unusable.

## 13. Required Approval Gates Before Any Future Execution

Required gates:

- User explicitly approves installation.
- User explicitly approves model download.
- License/model-weight checklist completed.
- Separate environment path chosen.
- Tiny symbol/date set chosen.
- Abort criteria agreed.
- Output folder agreed.
- No full Research200 run approved.
- No production use approved.

## 14. Phase Roadmap After 37D

Possible future phases, none approved by Phase 37D:

- Phase 37E — license/model-card manual verification result.
- Phase 37F — tiny smoke-test implementation plan.
- Phase 37G — tiny smoke-test execution, only if approved.
- Phase 37H — smoke-test output review.
- Phase 37I — small offline diagnostic experiment design.
- Fine-tuning remains deferred until leakage audit.

## 15. Decision

Phase 37D creates only the license/model-weight verification checklist and tiny
smoke-test plan.

No installation is approved. No model download is approved. No inference is
approved. No production use is approved. The next action should be selected
deliberately after reviewing this document.

## 16. Anti-Overfitting / Safety Guardrails

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
