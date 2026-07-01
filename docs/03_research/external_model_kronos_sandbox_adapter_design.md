# Phase 37C — Kronos Sandbox / Data Adapter Design

## 1. Status / Verdict

Phase 37C is design-only. No sandbox is implemented. No adapter is implemented.
No model is installed or downloaded. No inference is run.

Kronos remains approved only for possible future offline diagnostic research. It
is not production-approved, not direct-strategy-approved, and not approved for
raw predicted-candle execution.

Phase 37D defines the license/model-weight verification checklist and tiny
smoke-test gates in
`docs/03_research/external_model_kronos_license_smoke_test_plan.md`. Those gates
must be reviewed before any future installation, model download, or inference.

Phase 37F defines exact tiny smoke-test execution limits in
`docs/03_research/external_model_kronos_tiny_smoke_test_implementation_plan.md`.
It remains planning-only and does not implement the sandbox or adapter.

Later update: 37K/37N execution exposed persistent invalid OHLC forecast rows.
Phase 37O adds the adapter/output-validation debug design in
`docs/03_research/external_model_kronos_adapter_output_validation_debug.md`.
Any future sandbox/helper script must include an explicit output-validity gate,
record model/tokenizer eval-mode state, and avoid writing repaired candles as
canonical signal evidence.

## 2. Why a Separate Sandbox Is Required

Kronos has heavy ML dependencies such as PyTorch, Hugging Face tooling, and
model-weight files. Veridian core should not inherit those dependencies.

The user's laptop constraints require any future execution to be small,
isolated, optional, and easy to skip. External-model experiments must not
destabilize existing S1-S5 research, backtesting, tests, or the project virtual
environment. The sandbox should be separable from Veridian core and removable
without affecting retained strategy benchmarks.

## 3. Proposed Future Folder / Boundary Design

Future structure, if separately approved:

- `external_repos/Kronos/` for the cloned third-party repository. This should
  not be committed to Veridian.
- `external_sandboxes/kronos/` for isolated experiment scripts. This should not
  be core production code.
- `reports/v2/external_models/kronos/` for future generated outputs. These
  should not be committed unless explicitly approved.
- `docs/03_research/` for design documentation.

Boundary rules:

- Do not vendor Kronos code into Veridian.
- Do not modify Kronos source.
- Do not mix Kronos dependencies into Veridian `.venv`.
- Keep Veridian core import-free from Kronos until a later approved integration
  phase.

No folders are created by Phase 37C except this documentation file.

## 4. Environment Design

Future isolated environment plan, not created now:

- Separate virtual environment.
- Pinned Python version compatible with Kronos.
- Pinned dependencies.
- Local-only model cache if model download is approved later.
- No web UI.
- No Qlib initially.
- No AkShare initially.
- No training or fine-tuning initially.
- CPU-only tiny smoke test first if feasible.
- Smallest Kronos model first.
- Fixed seeds/settings for reproducibility.
- No long-running jobs on the user's laptop.

Phase 37C does not create this environment.

## 5. Veridian-to-Kronos Data Adapter Design

Future adapter input source:

- Veridian daily OHLCV bars from existing DB/research data.
- Research200 later, but the first tiny smoke test should use 5-20 highly
  liquid symbols.

Candidate input schema:

- `symbol`
- `date` / `timestamp`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `amount` optional, candidate `close * volume`

Optional context columns for evaluation only, not Kronos input:

- NIFTY regime.
- India VIX regime.
- Liquidity bucket.
- Drawdown state.
- Strategy signal/trade labels.

Adapter rules:

- Lowercase OHLCV columns if Kronos expects that.
- Sort by `symbol` and `date`.
- Reject duplicate `symbol` / `date` rows.
- Include no future rows in the lookback.
- Use no target-period rows in normalization.
- Do not use adjusted and unadjusted prices inconsistently.
- Preserve the corporate-action caveat: current project data lacks audited
  corporate-action adjustment.

## 6. Lookback / Inference Date Design

- Candidate lookback: 400 sessions if feasible.
- Smaller lookback fallback only if documented before a run.
- Candidate horizons: 5, 10, and 20 sessions.
- Initial smoke dates: a small number of monthly or quarterly inference dates,
  not a full daily sweep.
- First smoke symbols: 5-10 liquid symbols preferred.
- Later expanded test: 20 symbols, then Research200 only if compute allows.

## 7. Future Sandbox Output Schema

Possible future outputs, not implemented now:

- `kronos_forecast_paths.csv`
- `kronos_forecast_diagnostics.csv`
- `kronos_rank_diagnostics.csv`
- `kronos_trade_overlay_diagnostics.csv`
- `kronos_run_metadata.json`

Recommended columns for `kronos_forecast_diagnostics.csv`:

- `run_id`
- `symbol`
- `inference_date`
- `horizon`
- `model_name`
- `decoding_settings`
- `seed`
- `lookback_sessions`
- `pred_close_return`
- `pred_direction`
- `pred_high_low_range`
- `pred_volatility_proxy`
- `forecast_strength_score`
- `forecast_rank`
- `realized_forward_return`
- `forecast_error`
- `benchmark_regime`
- `vix_regime`
- `liquidity_bucket`
- `drawdown_state`

Recommended metadata:

- Kronos repo commit hash if available later.
- Model weight name/revision.
- Dependency versions.
- Decoding settings.
- Random seed.
- Data extraction window.
- Symbols used.
- Run timestamp.
- Hardware mode CPU/GPU.
- Warnings/caveats.

## 8. Future Evaluation Join Design

Future Kronos outputs should join back to Veridian by `symbol` and
`inference_date`.

Before any join is used for signal-quality diagnostics, forecast paths must
pass or explicitly fail an output-validity gate. Invalid rows, invalid reasons,
and the chosen reject/flag/repair-for-visualization policy must be recorded
before any downstream rank, direction, context, or trade-overlay interpretation.

Evaluation rules:

- Compare to forward returns only after the inference date.
- Compare to S1-S5 signal/trade logs without using future labels as features.
- Evaluate across year, symbol, liquidity bucket, benchmark regime, VIX regime,
  drawdown state, strategy, and winner/loser trade outcome.

## 9. What Future Smoke Test Should and Should Not Do

Allowed future smoke test, only if separately approved:

- Tiny symbol set.
- Small date set.
- CPU if possible.
- Smallest model.
- Fixed seed.
- No training or fine-tuning.
- No web UI.
- No Qlib or AkShare.
- Output diagnostics only.

Disallowed:

- Full Research200 sweep first.
- Raw predicted-candle trading.
- Strategy rule creation.
- Backtest optimization.
- Threshold tuning.
- Fine-tuning.
- Production dependency.
- Long-running GPU/cloud workflow without approval.

## 10. License / Model Weight Gate

Before any production use or redistribution:

- Repo code license and model-weight license must be verified.
- Hugging Face model terms/revisions should be recorded.
- Any future use must preserve required notices.

This document does not provide legal advice or production approval.

## 11. Production Gate

Production use cannot be considered unless a later phase establishes:

- Stable offline diagnostic value.
- Walk-forward validation.
- Reproducible inference.
- Acceptable compute/cost.
- Model-weight/license clearance.
- Failure handling.
- Monitoring plan.
- Drift checks.
- No increase in drawdown or overtrading.
- Paper/shadow validation.
- Explicit production-readiness decision.

## 12. Phase Roadmap After 37C

Possible future phases, none approved by Phase 37C:

- Phase 37D — model-weight/license verification and tiny smoke-test plan.
- Phase 37E — license/model-card manual verification result.
- Phase 37F — tiny smoke-test implementation plan.
- Phase 37G — user approval and exact execution checklist.
- Phase 37H — tiny smoke-test execution, only if approved.
- Phase 37I — smoke-test output review.
- Phase 37J — small offline diagnostic experiment design.
- Phase 37K — small diagnostic execution, only if smoke test is acceptable.
- Fine-tuning lane remains deferred until leakage audit.

Historical note: Phase 37D is now documented in
`docs/03_research/external_model_kronos_license_smoke_test_plan.md`, but it does
not approve installation, model download, or inference.

## 13. Decision

Phase 37C creates only the sandbox/adapter design.

No execution is approved. No installation is approved. No model download is
approved. No production use is approved. The next action should be chosen
deliberately after reviewing this design.

## 14. Anti-Overfitting / Safety Guardrails

- No raw candle execution.
- No best-horizon cherry-picking.
- No threshold tuning after results.
- No symbol cherry-picking.
- No using future data in normalization.
- No fine-tuning before split/leakage audit.
- No merging Kronos dependencies into Veridian core.
- No production claim from smoke tests.
- No cloud/GPU spend without explicit approval.
