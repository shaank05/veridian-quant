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

Phase 37A found the Kronos repository code appears MIT licensed. Model-weight
terms require Hugging Face verification before production use, redistribution,
or any durable project dependency decision.

Kronos dependencies include PyTorch, Hugging Face tooling, safetensors, and
optional Qlib, AkShare, and web UI components. Dependency isolation is required.

## 13. Phase Roadmap

Possible future phases, none approved by Phase 37B:

- Phase 37C - Kronos sandbox / data adapter design.
- Phase 37D - model-weight/license verification and tiny smoke-test plan.
- Phase 37E - license/model-card manual verification result.
- Phase 37F - tiny smoke-test implementation plan.
- Phase 37G - tiny smoke-test execution, only if approved.
- Phase 37H - smoke-test output review.
- Phase 37I - small offline diagnostic experiment design.
- Optional later fine-tuning lane only after leakage audit.

Historical note: Phase 37C is now documented in
`docs/03_research/external_model_kronos_sandbox_adapter_design.md`, but it does
not approve execution.
Phase 37D is now documented in
`docs/03_research/external_model_kronos_license_smoke_test_plan.md`, but it also
does not approve execution.

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
