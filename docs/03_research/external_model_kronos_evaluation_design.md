# Phase 37B — Kronos Offline Evaluation Design

## 1. Status / Verdict

Phase 37A classified Kronos as `FEASIBLE_FOR_OFFLINE_DIAGNOSTIC_RESEARCH`.

Kronos is not production-approved. It is not direct-strategy-approved. It is
not approved for direct predicted-candle execution. Phase 37B is design-only:
no installation, model download, inference, training, sandbox creation, runner,
adapter, strategy logic, backtest logic, or report artifact is approved.

Phase 37C adds the future sandbox and data-adapter boundary design in
`docs/03_research/external_model_kronos_sandbox_adapter_design.md`. That design
also remains docs-only and does not approve sandbox creation, adapter
implementation, installation, model download, or inference.

Phase 37D adds the license/model-weight verification checklist and tiny
smoke-test plan in
`docs/03_research/external_model_kronos_license_smoke_test_plan.md`. That plan
is also docs-only and does not approve installation, model download, Hugging
Face download, or inference.

Phase 37E records manual repo/model-card verification results in
`docs/03_research/external_model_kronos_license_verification_result.md`. Visible
repo and selected model-card license fields appear clear enough for future
internal offline diagnostic research planning, but Phase 37E does not approve
production use, model download, installation, or inference.

Phase 37F documents the future tiny smoke-test implementation plan in
`docs/03_research/external_model_kronos_tiny_smoke_test_implementation_plan.md`.
No evaluation run exists yet; no install, download, inference, report, or
strategy/backtest change is approved.

Phase 37H later completed the first approved tiny smoke test, and Phase 37I
reviews it in `docs/03_research/external_model_kronos_smoke_test_review.md`.
The technical smoke test passed, but the first real evaluation has not started:
one HDFCBANK forecast row is not evidence of model quality.

Phase 37J adds the small offline diagnostic experiment design in
`docs/03_research/external_model_kronos_small_diagnostic_experiment_design.md`.
It recommends a pre-registered 5-symbol x 6-date diagnostic only and does not
approve execution.

Later status update: Phase 37K executed the approved small diagnostic, Phase
37L scrutinized the weak/negative result and invalid OHLC rows, and Phase 37M
adds a stochastic reproducibility/output-validity diagnostic design in
`docs/03_research/external_model_kronos_reproducibility_validity_design.md`.
This adds an explicit validity/reproducibility gate before any larger
diagnostic, Research200 expansion, or strategy-adjacent use.

Phase 37N later confirmed invalid OHLC rows remained high. Phase 37O documents
read-only adapter/output-validation inspection in
`docs/03_research/external_model_kronos_adapter_output_validation_debug.md` and
keeps signal-quality diagnostics blocked pending adapter/API debug and a
predeclared output-validity policy.

Phase 37Q now defines that policy in
`docs/03_research/external_model_kronos_output_validity_policy.md`. Future
Kronos signal-quality metrics are eligible only on valid forecast runs unless a
later close-only mode is explicitly approved.

## 2. Why This Lane Exists

S1-S5 are retained as benchmarks only. The Phase 35 ensemble and confirmation
branch was closed: broad voting and generic consensus were dropped, and narrow
S2/S4 confirmation remains diagnostic only. Phase 36 risk diagnostics were
closed with no approved risk model, filter, throttle, VIX rule, dynamic sizing
change, or production behavior.

Internal price-pattern and risk-filter research is showing diminishing returns.
The external model lane exists to test whether a new representation or
forecasting source can add information beyond retained S1-S5 benchmarks,
benchmark/sector context, and Phase 36 risk diagnostics. It does not assume
Kronos will improve results.

## 3. Allowed Kronos Evaluation Uses

Allowed research uses:

- Offline diagnostic layer.
- Ranking feature.
- Regime/context feature.
- Confirmation/disagreement feature.
- Forecast-quality research object.
- Potential future confidence feature.
- Potential future cross-sectional rank feature.

Explicitly disallowed uses:

- Buy or sell directly from predicted candles.
- Set stops or targets directly from predicted OHLC.
- Use raw generated candles as future truth.
- Optimize thresholds after seeing PnL.
- Merge Kronos dependencies into Veridian core.
- Fine-tune before leakage and split audits.
- Run full Research200 inference before small smoke tests.

## 4. Data Mapping

Candidate Veridian daily-bar to Kronos input mapping:

- `date` / `timestamp` -> timestamp input.
- `open` -> `open`.
- `high` -> `high`.
- `low` -> `low`.
- `close` -> `close`.
- `volume` -> `volume`.
- `amount` -> optional, candidate `close * volume`.

Future evaluation should eventually use Research200, but the first smoke test
should use only 5-20 highly liquid symbols. NIFTY and India VIX can be used
later as evaluation context, not necessarily as Kronos input. Historical
Veridian price data currently has a corporate-action caveat: unless adjustment
status is audited, splits, bonuses, and other actions may distort long lookback
and forecast-quality metrics.

## 5. Lookahead / Leakage Rules

- Use only information available before the inference date.
- Do not include future bars in lookback normalization.
- Do not use entry-date close for next-open decisions.
- Do not evaluate symbols or dates that were unavailable in the intended
  historical universe.
- Do not normalize with a full window that includes the forecast target period.
- Do not fine-tune until train, validation, and test splits are explicitly
  designed and reviewed.
- Do not select thresholds or horizons after seeing full-period PnL.

## 6. Proposed Evaluation Windows

Design-only proposal:

- Full research period: 2020-01-01 to 2026-04-30.
- Initial smoke period: smaller period such as 2023-2025, or a few
  pre-selected quarterly/monthly inference dates.
- Initial symbols: 5-20 high-liquidity symbols.
- Later universe: Research200.
- Candidate lookback: 400 sessions if feasible; otherwise use a smaller
  documented alternative.
- Candidate forecast horizons: 5, 10, and 20 sessions.

Avoid choosing the best horizon after seeing results. Predefine a primary
horizon and secondary horizons before any inference run.

## 7. Derived Kronos Diagnostics

Do not use raw predicted candles directly. Convert forecast paths into
diagnostics such as:

- Predicted close return over 5/10/20 sessions.
- Predicted direction.
- Forecast strength score.
- Cross-sectional forecast rank.
- Predicted high-low range.
- Forecast volatility proxy.
- Forecast dispersion if repeated samples are later feasible.
- Output-validity diagnostics: invalid OHLC rate, invalid reason counts,
  invalid rows by symbol/date/step/seed, and forecasts with any invalid row.
- Reproducibility diagnostics: seed-to-seed direction agreement, predicted
  return dispersion, sign flips, and rank stability.
- Realized forecast error by regime.
- Agreement/disagreement with S1-S5 trades.

## 8. Evaluation Metrics

Prioritize forecast and ranking metrics before trading PnL:

- Directional accuracy.
- Rank IC / Spearman correlation.
- Decile forward-return spread.
- Top-minus-bottom forward return.
- Forecast error / MSE / MAE by horizon.
- Year-by-year stability.
- Regime stability by liquidity bucket, benchmark regime, VIX regime, drawdown
  state, and gap-risk context where applicable.

Secondary trade-overlay diagnostics:

- S2/S3/S4/S5 trades when Kronos agrees versus disagrees.
- S2 winners versus losers by Kronos rank.
- S1-S5 trade quality by Kronos forecast-strength bucket.
- Weak-year behavior, especially 2024/2025.
- Whether Kronos adds information beyond liquidity, benchmark regime, drawdown
  state, and VIX.

## 9. Success Criteria

Evidence that could justify moving past design:

- Positive rank IC across multiple years.
- Top-decile forward returns exceed bottom-decile returns consistently.
- Useful agreement/disagreement signal for retained S1-S5 trades.
- Helpful behavior in weak years, not only strong bull periods.
- Evidence that the signal is not merely duplicating liquidity or benchmark
  regime.
- Valid forecast paths with low or explainable invalid OHLC rates.
- Stable enough repeated-seed direction/rank/return outputs for diagnostic use.
- Explicit inference-mode/API usage checks and caller-side output-validity
  handling before signal diagnostics.
- Metric eligibility gated on valid forecast runs, with invalid/excluded run
  counts reported beside any directional, rank, or spread metric.
- Manageable compute cost on a small smoke test.
- Deterministic and reproducible enough under fixed seed/settings.

## 10. Failure Criteria

Failure or blocking evidence:

- No rank relationship.
- Apparent usefulness in only one year.
- Apparent usefulness only on tiny samples.
- Diagnostics only repeat liquidity, benchmark, or VIX effects.
- Highly unstable stochastic outputs.
- Compute too heavy for the user's laptop.
- Leakage cannot be ruled out.
- Model-weight or license terms block safe use.
- Raw forecast-based PnL looks good while forecast/rank diagnostics fail.

## 11. Compute / Environment Plan

Laptop-safe plan:

- No install in Phase 37B.
- Future sandbox only in a separate virtual environment.
- No dependency merge into Veridian core.
- Smallest model first.
- CPU-only smoke test if feasible.
- No web UI.
- No Qlib initially.
- No AkShare initially.
- No training or fine-tuning initially.
- No full Research200 sweep initially.
- Avoid long-running jobs on the user's laptop.

## 12. Dependency / License Caveats

Phase 37A found the Kronos repository code appears MIT licensed. Phase 37E
manually verified that the selected Hugging Face cards for
`NeoQuasar/Kronos-Tokenizer-base`, `NeoQuasar/Kronos-small`, and
`NeoQuasar/Kronos-base` visibly show `mit` license fields. This supports future
internal offline diagnostic research planning only. Production use,
redistribution, hosted serving, bundled model-weight packaging, and any durable
project dependency decision still require separate review.

Kronos dependencies include PyTorch, Hugging Face tooling, safetensors, and
optional Qlib, AkShare, and web UI components. Dependency isolation is required.

## 13. Phase Roadmap

Possible future phases, none approved by Phase 37B:

- Phase 37C - Kronos sandbox / data adapter design.
- Phase 37D - model-weight/license verification and tiny smoke-test plan.
- Phase 37E - license/model-card manual verification result.
- Phase 37F - tiny smoke-test implementation plan.
- Phase 37G - user approval and exact execution checklist.
- Phase 37H - tiny smoke-test execution, only if approved.
- Phase 37I - smoke-test output review.
- Phase 37J - small offline diagnostic experiment design, not execution.
- Phase 37K - small diagnostic execution, only if separately approved.
- Phase 37L - small diagnostic result scrutiny.
- Phase 37M - stochastic reproducibility / output-validity diagnostic design,
  not execution.
- Optional later fine-tuning lane only after leakage audit.

Historical note: Phase 37C is now documented in
`docs/03_research/external_model_kronos_sandbox_adapter_design.md`, but it does
not approve execution.
Phase 37D is now documented in
`docs/03_research/external_model_kronos_license_smoke_test_plan.md`, but it also
does not approve execution.
Phase 37E is now documented in
`docs/03_research/external_model_kronos_license_verification_result.md`, but it
does not approve installation, model download, inference, or production use.
Phase 37F is now documented in
`docs/03_research/external_model_kronos_tiny_smoke_test_implementation_plan.md`,
but it does not approve execution.
Phase 37J is now documented in
`docs/03_research/external_model_kronos_small_diagnostic_experiment_design.md`,
but it does not approve execution.
Phase 37M is now documented in
`docs/03_research/external_model_kronos_reproducibility_validity_design.md`,
but it does not approve execution.

## 14. Decision

Phase 37B decision: design Kronos evaluation only.

Next approved action after these docs can be one of:

- Stop / park the external model lane.
- Design an isolated sandbox.
- Perform model-weight/license verification.
- Prepare a tiny smoke-test plan.

No execution is approved by this document.

## 15. Anti-Overfitting Guardrails

- No raw candle execution.
- No after-the-fact threshold tuning.
- No best-horizon cherry-picking.
- No symbol cherry-picking.
- No fine-tuning before split/leakage design.
- No using future actuals in feature construction.
- No treating generated candles as future truth.
- No production claims from smoke tests.
- No merging external dependencies into core Veridian.
