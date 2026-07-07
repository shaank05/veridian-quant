# Veridian Quant v2 Research Roadmap

## Current Research State

Veridian Quant v2 has completed the S1 baseline cycle, the S2 Markov research cycle through Phase 27J/27K, the S3 Trend Pullback Continuation research cycle through Phase 28G, and the first S4 Entropy / Volatility Compression Breakout raw baseline cycle through Phase 29F/29G.

Current retained research benchmarks:

- `S1_BASELINE` remains the original v2 mean-reversion benchmark.
- `S2_MARKOV_STATE_TRANSITION` is retained as a benchmark/research candidate, but is frozen and not production-ready.
- `S3_TREND_PULLBACK_CONTINUATION` is researched and parked. Retain `S3_STRONG_TREND_ABOVE_SMA50_V1` as an S3 benchmark only.
- `S4_ENTROPY_VOLATILITY_COMPRESSION_BREAKOUT` is implemented and researched through raw Research200 baselines, but is frozen/parked and not production-ready. Retain `S4_ATR_COMPRESSION_BREAKOUT_V1` as a weak S4 benchmark only.

S2 has evidence of edge, but the research cycle found material regime fragility, especially around the 2025/2026 period. S2 should not be deployed live. It should remain available for comparison against future independent strategies.

S3 tested a different alpha source: buying structurally strong stocks after controlled pullbacks inside confirmed uptrends. The best S3 variant remained too weak for production.

S4 tested a different alpha source: long-only breakouts after prior volatility, range, or entropy/noise compression. The best raw S4 variant was positive but too weak relative to drawdown for production. S4 should remain available as a research benchmark, but immediate S4 threshold tuning is parked.

I1 RAWRS research has progressed through Phase 30J: feature utilities,
standalone diagnostics, cross-strategy keep/avoid analysis, true S3 p20/p10
overlay tests, and the combined evidence audit. RAWRS is not S5 or a signal
generator. It remains a diagnostic-only intelligence layer; the tested S3 hard
filters are rejected.

Phase 31 is complete. It designed and implemented the standalone Portfolio
Robustness Validation Layer, ran common Monte Carlo validation for retained
S1/S2/S3/S4 ATR outputs, and completed the Phase 31D cross-strategy audit. S2 is
the strongest current robustness benchmark, S1 ranks second, S3 remains a
weak/moderate benchmark, and S4 ATR ranks weakest. This is validation evidence,
not production approval; Monte Carlo does not generate signals or change
strategy behavior.

Phase 32A through 32F completed the first S5 Relative Strength / Momentum
Rotation lane. S5 is a standalone, ranked Research200 strategy family and does
not mix with S1/S2/S3/S4, RAWRS, or external models. First-pass results did not
challenge S2, S1, or S3. Simple RS and Vol-Adjusted RS are rejected, while Dual
Momentum is weak and parked only as a benchmark. No immediate S5 tuning is
planned.

Phase 33 began before new strategy-family work because benchmark, sector, and
market-cap context is now foundational. Phase 33E through 33E.4 completed the
reusable market/sector/cap context utility layer, real Research200 audit runner,
conservative sector proxy mapping refinement, and documentation/status freeze.
Phase 33F through 33F.3 applied benchmark/sector context diagnostics to retained
S1-S5 trade PnL logs and froze the interpretation in
`docs/02_audits/s1_s5_context_audit.md`. Phase 33G completed the controlled S2
context experiment design in
`docs/03_research/s2_context_experiment_design.md` before any experiment runs.
Phase 33G.1 implemented and ran the fixed batch, and Phase 33G.2 froze the
result: all simple S2 context-filter variants are rejected and the original S2
baseline remains unchanged.

Phase 34A through 34B reconstructed and documented the S2 failure-mode trail.
Phase 34A used existing retained reports to confirm that S2's current weakness
is regime/state non-stationarity plus broad stop-churn during fragile periods.
Phase 34A.0 found existing S2 failure-audit tooling and reports, so no new
failure-audit code is currently needed. Phase 34B documents prior S2 guard,
context, and state-exclusion variant lessons. The next S2 step must be a
separate decision phase, not automatic implementation.

Phase 35B/35C closed the cross-strategy overlap and confirmation branch.
Broad voting and generic 2+ strategy consensus are dropped. Narrow S2/S4
confirmation is retained only as a parked diagnostic observation. No ensemble,
weights, allocation, or production approval resulted from this work.

Phase 36B/36C closed the cross-strategy risk diagnostic branch. Liquidity is the
strongest S2 risk diagnostic, with benchmark regime, drawdown state, gap risk,
rolling R, and India VIX retained only as diagnostics. Phase 36D then documents
the next S2 diagnostic design in
`docs/03_research/s2_state_risk_intrade_diagnostic_design.md`: Lane A studies
entry-state x risk inputs, and Lane B studies in-trade Markov state evolution.
Phase 36D is docs/design only. It approves no dynamic exit, no `exit if
RET_DOWN` rule, no entry filter, no state filter, no risk filter, no sizing
change, no backtest implementation, and no strategy behavior change. The next
gate selected by Phase 36D was `PROCEED_TO_36E_STATE_METADATA_DISCOVERY`.
Phase 36E discovery is documented in
`docs/03_research/s2_state_metadata_intrade_reconstruction_discovery.md`: entry
state metadata exists with minor gaps, but in-trade state evolution needs daily
state reconstruction. The next selected gate is
`PROCEED_TO_36F_STATE_RECONSTRUCTION_PROTOTYPE_DESIGN`.
Phase 36F prototype design is documented in
`docs/03_research/s2_daily_state_reconstruction_prototype_design.md`: it defines
the future read-only reconstruction prototype, including daily state rebuild,
trade lifecycle expansion, same-day stop/target safety, deterioration
candidates, next-open feasibility, and validation gates. The next selected gate
is `PROCEED_TO_36G_STATE_RECONSTRUCTION_PROTOTYPE_IMPLEMENTATION`.
Phase 36G implements the narrow read-only prototype in
`src/veridian_quant/v2/analysis/s2_state_reconstruction.py`, with focused
synthetic tests and an optional export CLI. The implementation still approves
no dynamic exit, `exit if RET_DOWN`, entry filter, state exclusion, risk filter,
sizing change, backtest, production behavior, or threshold optimization. The
next selected gate is
`PROCEED_TO_36H_STATE_RECONSTRUCTION_PROTOTYPE_RUN`.
Phase 36H preflight is documented in
`docs/03_research/s2_state_reconstruction_prototype_run.md`. Retained S2
trades loaded cleanly, but the prototype run is blocked because the CLI
requires a caller-provided per-symbol OHLC CSV directory and no such directory
was available in the workspace. The selected gate is
`FIX_OHLC_INPUT_AND_RERUN_36H`.
Phase 36H.1 added DB-backed OHLC loading via the existing Veridian
`DatabaseClient` and `SQLAlchemyDailyOHLCVLoader` path while preserving CSV
input support. Focused tests passed, but the controlled rerun remains blocked
because the configured database connection timed out. The selected gate is
`REVISE_36H1_OHLC_INPUT_FIX`.
Phase 36H.2 reran the same controlled DB-backed prototype command after the DB
connectivity was expected to be available. The CLI and retained inputs were
confirmed, but OHLC loading again timed out connecting to the configured
database at `34.14.156.222:5432`; no reconstruction outputs were generated.
The selected gate is `FIX_DB_CONNECTIVITY_AND_RERUN_36H2`.
After DB access was fixed externally and the reconstruction timezone mismatch
was corrected, the prototype run generated
`reports/v2/s2_state_reconstruction_prototype_20260707/`. Phase 36I scrutiny
classified reconstruction as `PASS_WITH_CAVEATS`: 7,113 / 7,113 lifecycle rows
joined state, 577 / 577 entry states matched, same-day exit safety failures
were 0, and 5 terminal trades require explicit edge-case handling. Phase 36J
then created the full read-only S2 State x Risk / In-Trade audit design in
`docs/03_research/s2_state_risk_intrade_full_audit_design.md`. The selected
gate is
`PROCEED_TO_36K_FULL_READ_ONLY_S2_STATE_RISK_INTRATRADE_AUDIT_IMPLEMENTATION`.

Phase 37A through 37M opened a strictly controlled external-model intelligence
lane for Kronos. Phase 37A completed read-only repository discovery and
classified Kronos as feasible only for offline diagnostic research. Phase 37B
documents the future evaluation design in
`docs/03_research/external_model_kronos_evaluation_design.md`. Phase 37C
documents future sandbox and data-adapter boundaries in
`docs/03_research/external_model_kronos_sandbox_adapter_design.md`. Phase 37D
documents license/model-weight verification and tiny smoke-test gates in
`docs/03_research/external_model_kronos_license_smoke_test_plan.md`. Phase 37E
records manual repo/model-card verification results in
`docs/03_research/external_model_kronos_license_verification_result.md`: the
repo code and selected Hugging Face cards appear clear for future internal
offline diagnostic research planning, but not production-cleared. Phase 37F
documents the future tiny smoke-test implementation plan in
`docs/03_research/external_model_kronos_tiny_smoke_test_implementation_plan.md`.
Phase 37G documents the exact user approval and execution checklist in
`docs/03_research/external_model_kronos_execution_approval_checklist.md`. Phase
37H executed the first approved tiny smoke test on one HDFCBANK sample. Phase
37I reviews that output in
`docs/03_research/external_model_kronos_smoke_test_review.md`: the technical
smoke test passed, but the single forecast was directionally wrong and does not
validate model quality. Phase 37J designs the first small offline diagnostic
experiment in
`docs/03_research/external_model_kronos_small_diagnostic_experiment_design.md`;
it recommends 5 HIGH-liquidity symbols x 6 dates = 30 forecasts for a possible
future Phase 37K approval. Phase 37K executed that approved small diagnostic.
Phase 37L scrutinized the result: 30 / 30 forecasts completed, directional
accuracy was 13 / 30 = 43.33%, Spearman rank IC was -0.268521,
top-minus-bottom spread was -0.043511, and 17 / 150 forecast path rows had
invalid OHLC relationships. Phase 37M documents the next design-only
reproducibility/output-validity diagnostic in
`docs/03_research/external_model_kronos_reproducibility_validity_design.md`.
Phase 37N executed that bounded diagnostic and confirmed invalid OHLC rows
remained high: 16 / 90 rows = 17.78%, affecting 8 / 18 forecast runs. Phase
37O documents the read-only adapter/output-validation debug design in
`docs/03_research/external_model_kronos_adapter_output_validation_debug.md` and
selects `PROCEED_TO_37P_ADAPTER_DEBUG_EXECUTION` as the next gated step. Phase
37P executed the approved tiny adapter debug on HDFCBANK / `2024-01-15` only.
It found invalid OHLC rows fell from 3 / 15 in the 37N-like baseline to 1 / 15
with explicit eval mode and 0 / 15 with eval plus `top_k=1`, `top_p=1.0`, but
the sample is too small to approve scaling. Phase 37P selects
`PROCEED_TO_37Q_OUTPUT_VALIDITY_POLICY_DESIGN`. Phase 37Q defines the
output-validity policy in
`docs/03_research/external_model_kronos_output_validity_policy.md` and selects
`PROCEED_TO_37R_OUTPUT_VALIDITY_POLICY_IMPLEMENTATION`. Phase 37R implements
reusable tracked policy helpers in
`src/veridian_quant/v2/external_models/kronos/output_validity.py` with
synthetic-data tests in `tests/v2/test_kronos_output_validity.py` and selects
`PROCEED_TO_37S_POLICY_COMPLIANT_RETRY_DESIGN`. Phase 37S documents the
policy-compliant small diagnostic retry design in
`docs/03_research/external_model_kronos_policy_compliant_retry_design.md` and
selects `PROCEED_TO_37T_POLICY_COMPLIANT_RETRY_APPROVAL`. No small diagnostic
retry, further Kronos inference, full Research200 run, strategy integration,
raw predicted-candle trading, training, fine-tuning, or production use is
approved. Phase 37T later executed the approved policy-compliant retry and
records the result in
`docs/03_research/external_model_kronos_policy_compliant_retry_result.md`: 30 /
30 runs completed, but output validity failed with 3 / 30 invalid forecast runs
and 4 / 150 invalid path rows. Validity-gated signal metrics remained
weak/negative, and the selected next step is
`PROCEED_TO_37U_POLICY_RETRY_RESULT_SCRUTINY`. Phase 37U scrutiny and Phase
37V public evidence review supported closeout: no direct public invalid-OHLC
fix, no official OHLC guarantee, no official repair guidance, and broader
generation-quality/reproducibility concerns, including CPU/GPU output mismatch.
Phase 37W closes the lane in
`docs/03_research/external_model_kronos_closeout.md` with
`DOCS_ONLY_CLOSEOUT_AND_BIMONTHLY_REVIEW`.

---

## Completed Phases

### Phase 1-22: S1 Foundation and Portfolio Backtesting

Implemented the v2 S1 Z-score mean-reversion baseline, reusable trade setup, sizing, execution, exit resolution, PnL, ledger, exporters, and core diagnostics.

### Phase 23: S1 Filter Variants

Implemented S1 hard-filter variants to test whether signal-date context could improve baseline mean reversion.

Outcome:

- Variants were useful research probes.
- Hard filters did not generalize reliably across the broader research universe.

### Phase 24: Strategy Variant Comparison Reports

Added reporting to compare S1 variants across summary metrics, yearly performance, exit reasons, rejection reasons, symbol concentration, and derived deltas.

Outcome:

- Broader reporting made variant fragility easier to detect.
- The comparison framework remains useful for future strategy families.

### Phase 25A-25F: Data, Ingestion, Quality, and Research Universe

Added v2 price ingestion, resumable network recovery, price quality audits, raw NSE equity candidate construction, audited research universe construction, and 100-vs-200 universe comparison.

Outcome:

- The audited 200-symbol S1 baseline materially outperformed the audited 100-symbol baseline.
- Universe breadth and data quality are now core research controls.

### Phase 26A: Capacity-Aware Candidate Ranking v1

Implemented `candidate-ranking s1_v1` to rank same-day S1 candidates under portfolio capacity constraints.

Outcome:

- The ranking implementation was technically valid.
- It underperformed the unranked `S1_BASELINE`.
- S1 ranking optimization is parked until stronger evidence exists.

### Phase 26B: All-Signal Opportunity Diagnostics and Counterfactual Rejected-Signal Simulation

Added diagnostics for all generated signals, accepted trades, rejected signals, capacity rejections, same-day pools, and counterfactual outcomes for rejected capacity signals.

Outcome:

- S1 generates far more valid signals than the portfolio can take.
- Capacity rejections are the dominant rejection reason.
- Counterfactual rejected-signal PnL is diagnostic only and must not be treated as actual portfolio PnL.
- These diagnostics support future ranking and voting research.

### Phase 27A-27J: S2 Markov State Transition Research Cycle

Implemented and researched `S2_MARKOV_STATE_TRANSITION` as a standalone strategy family.

Explored:

- Raw S2 Markov baseline.
- Markov state filters.
- S2 candidate ranking modes.
- Rejected/capacity counterfactual diagnostics.
- 2025 failure audit diagnostics.
- 2025 guard ranking.
- Signal-time stock/Nifty/relative-strength context enrichment for S2 ranking.

Outcome:

- S2 has evidence of edge.
- S2 is not discarded.
- S2 is not production-ready because of regime fragility, especially in 2025/2026.
- S2 research is frozen for now.
- The next research effort should move to a new independent strategy rather than continue tuning S2 immediately.

### Phase 28A: S3 Trend Pullback Continuation Specification

Documented `S3_TREND_PULLBACK_CONTINUATION` as the next standalone strategy-family candidate.

S3 thesis:

- Buy strength after a controlled dip, not weakness after panic.
- Require trend health before considering pullback.
- Test trend persistence and continuation rather than mean reversion or Markov state recurrence.

Outcome:

- Specification added only.
- Implementation and backtesting were deferred to later Phase 28 work.

### Phase 28B-28F: S3 Implementation, Diagnostics, and Variants

Implemented and researched `S3_TREND_PULLBACK_CONTINUATION` as a standalone trend-continuation strategy.

Explored:

- Baseline S3.
- S3 diagnostics and accepted-trade filter simulations.
- Strong-trend variant.
- Above-SMA50 variant.
- Strong-trend plus above-SMA50 variant.
- Controlled-pullback variant.

Outcome:

- S3 is technically valid.
- S3 is not production-ready.
- Best S3 benchmark: `S3_STRONG_TREND_ABOVE_SMA50_V1`.
- Best approximate result: about Rs 3.16L net PnL, about 4.43% CAGR, about 28.20% max drawdown, about 1.104 PF.
- Controlled-pullback tuning did not improve realized portfolio performance.
- S3 is parked after Phase 28G documentation.

### Phase 29A-29F: S4 Entropy / Volatility Compression Breakout Specification, Implementation, and Raw Baselines

Documented, implemented, and raw-tested `S4_ENTROPY_VOLATILITY_COMPRESSION_BREAKOUT` as the next standalone strategy-family candidate.

S4 thesis:

- Research long-only breakouts after volatility, range, or optional entropy/noise compression.
- Signal on breakout close and enter next session open.
- Use conservative v2 ATR stop, R-multiple target, max-holding-period, and same-candle ambiguity handling when implementation begins later.

Raw Research200 variants tested:

- `S4_ATR_COMPRESSION_BREAKOUT_V1`
- `S4_RANGE_COMPRESSION_BREAKOUT_V1`
- `S4_ENTROPY_GATED_BREAKOUT_V1`

Outcome:

- S4 feature utilities, signal generation, portfolio runner, and CLI runner were implemented.
- First raw Research200 baselines were run for 2020-01-01 to 2026-04-30 using default v2 portfolio methodology, no ranking, and no tuning.
- `S4_ATR_COMPRESSION_BREAKOUT_V1` was the best raw S4 variant, but only weakly positive: about Rs 1.65L net PnL, about 2.45% CAGR, about 39.12% max drawdown, about 1.037 PF, and 559 trades.
- `S4_RANGE_COMPRESSION_BREAKOUT_V1` was negative and is rejected as an S4 raw baseline.
- `S4_ENTROPY_GATED_BREAKOUT_V1` was near breakeven but negative and is not promoted.
- Raw S4 is not production-ready.
- S1, S2, and S3 remain frozen or parked.
- No S4 production decision, parameter tuning, ranking, or portfolio blending is authorized.

### Phase 29G: S4 Documentation and Parking

Document raw S4 baseline results and freeze/park S4 near-term research.

Outcome:

- Retain `S4_ATR_COMPRESSION_BREAKOUT_V1` as a weak S4 benchmark/research reference only.
- Reject `S4_RANGE_COMPRESSION_BREAKOUT_V1` as an S4 raw baseline.
- Do not promote `S4_ENTROPY_GATED_BREAKOUT_V1`.
- Do not continue immediate S4 threshold tuning.
- Future S4 revisit requires a materially new hypothesis such as market-regime gating, sector context, capacity/ranking redesign, or a broader portfolio-construction reason.

### Phase 30A: I1 RAWRS Market Structure Intelligence Specification

Document `I1_RAWRS_MARKET_STRUCTURE_INTELLIGENCE` as a reusable non-strategy intelligence layer.

RAWRS means:

- Regime-Aware Adaptive Wavelet Response Surface.

I1 RAWRS purpose:

- Study multi-scale price energy, frequency/cycle behavior, entropy/noise, wavelet coherence, and regime/topology features.
- Support diagnostics on S1/S2/S3/S4 accepted trades and rejected/capacity signals.
- Support future candidate-quality, ranking/capacity, regime-overlay, and risk/path-quality research.

Outcome:

- Specification only.
- No code implementation.
- No S5 naming.
- No direct buy/sell rules.
- No backtest runner.
- No production decision.

### Phase 30B: I1 RAWRS Feature Utility Foundation

Implement the initial RAWRS feature utility foundation for research use only.

Outcome:

- Initial feature utilities exist for signal-time market-structure analysis.
- Utilities remain non-strategy intelligence infrastructure.
- No strategy behavior, runner behavior, ranking, overlay, or production decision is authorized by Phase 30B.

### Phase 30C: I1 RAWRS Signal-Time Diagnostic Design

Document `I1_RAWRS_SIGNAL_TIME_DIAGNOSTICS` as the signal-time diagnostic blueprint for future RAWRS research.

Outcome:

- Docs-only design in `docs/06_intelligence/i1_rawrs_signal_time_diagnostics.md`.
- Defines accepted-trade, rejected-signal, capacity-rejection, winner/loser, year/regime, and strategy-family diagnostic plans.
- Defines leakage and post-hoc overfitting guardrails.
- Does not implement a diagnostics runner.
- Does not implement ranking or overlays.
- Does not change strategy or backtest behavior.

### Phase 30F: I1 RAWRS Strategy Output Compatibility Audit

Document how future standalone RAWRS diagnostics should consume existing S1/S2/S3/S4 strategy output folders.

Outcome:

- Docs-only audit in `docs/06_intelligence/i1_rawrs_strategy_output_compatibility.md`.
- Defines light RAWRS diagnostics for standard accepted-trade and signal/trade outputs.
- Defines full RAWRS diagnostics for runs with rejected-signal, all-signal, capacity, and same-day candidate-pool outputs available.
- Establishes this compatibility audit as a prerequisite before standalone RAWRS CLI implementation.
- Does not implement CLI behavior.
- Does not change code, tests, strategy runners, standard exporters, backtesting logic, reports, or strategy behavior.

### Phase 30G: I1 RAWRS Standalone Diagnostic CLI

Implement a standalone RAWRS diagnostic CLI that consumes existing strategy output folders without rerunning backtests.

Outcome:

- Adds `src/veridian_quant/v2/run_rawrs_diagnostics.py`.
- Adds light/full mode validation for existing strategy output CSVs.
- Reads strategy output CSVs without modifying them.
- Infers required symbols and date range from strategy output CSVs.
- Loads DB-backed OHLCV data through the existing v2 data loader convention.
- Computes RAWRS feature frames and writes RAWRS diagnostic outputs through standalone RAWRS export helpers.
- Does not integrate into S1/S2/S3/S4 runners.
- Does not change strategy behavior, backtest behavior, standard exporters, portfolio logic, PnL, trades, exits, sizing, rejected signals, or capacity.

### Phase 30H: I1 RAWRS Keep/Avoid Impact Diagnostics

Evaluate completed-trade RAWRS buckets as diagnostic keep/avoid subsets across
S1/S2/S3/S4 outputs.

Outcome:

- Low-bucket avoidance showed several promising descriptive separations.
- Energy features were directionally broad but often modest.
- Spectral features were stronger but strategy-specific.
- Highest-bucket-only retention was considered dangerous because it removed too
  many trades.
- Results remained post-hoc diagnostics, not portfolio evidence.

### Phase 30I: I1 RAWRS True S3 Overlay Experiment

Translate the promising S3 spectral-concentration diagnostic into leakage-safe
signal-time hard filters at p20 and p10.

Outcome:

- Both overlays underperformed `S3_STRONG_TREND_ABOVE_SMA50_V1`.
- P20 reduced PnL and worsened drawdown, profit factor, and mean R.
- P10 performed worse than both baseline and P20.
- Chronology, capacity, replacement trades, sizing, and compounding explained
  why the post-hoc result did not translate.
- Reject S3 spectral-concentration p20/p10 hard filtering.

### Phase 30J: I1 RAWRS Combined Evidence Audit

Consolidate RAWRS infrastructure, cross-strategy diagnostics, keep/avoid impact,
and true S3 overlay evidence.

Outcome:

- Docs-only audit in
  `docs/06_intelligence/i1_rawrs_combined_evidence_audit.md`.
- RAWRS remains diagnostic-only and non-production.
- S3 spectral-concentration p20/p10 hard filters are rejected.
- Future work should prioritize stability, significance, and capacity-aware
  ranking research rather than hard gates.

### Phase 31A: Portfolio Robustness Validation Design

Define the standalone post-backtest validation contract and Monte Carlo methods.

Outcome:

- Docs-only design in `docs/04_validation/portfolio_robustness_validation.md`.
- Defines shuffle and bootstrap simulation, required inputs/outputs, downside
  metrics, interpretation guardrails, limitations, and open questions.
- Monte Carlo remains validation/reporting, not signal generation or parameter
  optimization.
- No code, tests, runners, backtesting logic, exporters, reports, config, or data
  are changed by Phase 31A.

### Phase 31B: Portfolio Robustness Validation Utilities

Completed standalone, reproducible Monte Carlo utilities with strict input
validation, deterministic seed handling, tests, and isolated validation
exporters without changing strategy runners or signals.

### Phase 31C: S1/S2/S3/S4 Benchmark Validation

Run the frozen Phase 31 protocol on retained S1/S2/S3/S4 completed-trade outputs.
Produce shuffle and bootstrap evidence using like-for-like settings and preserve
all source backtest artifacts.

Outcome:

- Complete: 10,000 shuffle and 10,000 bootstrap simulations for each retained
  S1, S2, S3, and S4 ATR benchmark.
- Source backtest artifacts remained unchanged; validation outputs were written
  separately under `reports/v2/validation/monte_carlo/`.

### Phase 31D: Cross-Strategy Robustness Audit

Compare downside distributions, drawdown tails, loss probability, streaks, and
ruin/near-ruin risk. Judge risk-adjusted robustness rather than highest PnL or
best simulated outcome, and document any follow-up validation requirements.

Outcome:

- Complete: `docs/04_validation/monte_carlo_robustness_audit.md`.
- S2 ranks strongest overall, S1 second, S3 weak/moderate, and S4 ATR weakest.
- S2 becomes the primary robustness benchmark for future S5 comparisons.
- No current strategy receives production approval.

### Phase 32A: S5 Relative Strength / Momentum Rotation Design

Define the standalone S5 hypothesis, Research200 scope, momentum feature
candidates, cross-sectional ranking, capacity behavior, first-pass variants,
outputs, validation plan, and acceptance/rejection boundaries.

Outcome:

- Docs-only design in
  `docs/01_strategies/s5_relative_strength_momentum_rotation.md`.
- S5 remains independent from S1/S2/S3/S4 and excludes RAWRS and external
  models from the initial research cycle.
- No implementation, backtest, report, or production decision in Phase 32A.

### Phase 32B: S5 Feature Utilities

Implement and test only the frozen return, trend, high-proximity,
volatility-adjusted, and optional benchmark-relative features required by the
declared variants. Freeze lookback endpoints, missing-history behavior, and
signal-time calculation rules.

Outcome:

- Completed for the first-pass S5 feature set.

### Phase 32C: S5 Signal Generation

Implement standalone S5 eligibility, scoring, cross-sectional ranking,
deterministic tie-breaking, next-open signal metadata, and accepted/rejected
candidate diagnostics without mixing earlier strategy logic.

Outcome:

- Completed for the first-pass S5 variants.

### Phase 32D: S5 Portfolio Runner and CLI

Connect S5 to shared v2 trade mechanics, ATR risk sizing, five-position capacity,
costs, ledger, standard exporters, and an isolated runner/CLI. Preserve ranked
candidate ordering and explicit rejection reasons.

Outcome:

- Completed for the isolated S5 runner and CLI lane.

### Phase 32E: S5 Research200 Backtests

Run frozen first-pass variants independently over 2020-01-01 through 2026-04-30.
Review performance, yearly stability, concentration, trade count, turnover, and
capacity pressure without post-result threshold tuning.

Outcome:

- Complete first-pass backtests for `S5_SIMPLE_RS_126D_V1`,
  `S5_DUAL_MOMENTUM_63_126D_V1`, and `S5_VOL_ADJUSTED_RS_V1`.
- Simple RS and Vol-Adjusted RS were negative and severe-drawdown variants.
- Dual Momentum was the only profitable S5 run, but was weak and concentrated.

### Phase 32F: S5 First-Pass Audit and Parking Decision

Reconcile outputs, audit failure modes and ranking behavior, compare S5
primarily with the S2 robustness benchmark and secondarily with S1/S3/S4 ATR,
and decide reject/park status. This phase is docs-only and does not run Monte
Carlo.

Outcome:

- Complete: `docs/02_audits/s5_audit.md`.
- Reject `S5_SIMPLE_RS_126D_V1`.
- Park `S5_DUAL_MOMENTUM_63_126D_V1` as a weak benchmark only.
- Reject `S5_VOL_ADJUSTED_RS_V1`.
- No immediate S5 tuning is planned.
- Monte Carlo for Dual Momentum remains optional only if a later phase wants
  weak-benchmark robustness validation.

### Phase 33A: Benchmark, Sector, and Market-Cap Context Design

Design the context/data layer needed to compare strategy performance against
broad-market, Research200, sector, and cap-segment baselines and to diagnose
sector/cap concentration, risk-on/risk-off dependence, and capital utilization.

Outcome:

- Complete: `docs/04_validation/benchmark_sector_cap_context.md`.
- Phase 33A is docs/design only.
- Defines index OHLCV, instrument classification, market-cap bucket, and index
  membership data requirements.
- Proposes `market_indices`, `market_index_bars`,
  `instrument_classification`, and later `index_constituents` data contracts.
- Establishes benchmark-relative, sector-relative, cap-relative, regime, and
  portfolio-exposure diagnostic ideas.
- Requires all benchmark/context reports to label classification as
  point-in-time or current/static.
- Explicitly warns that using today's Research200, index membership, sector, or
  cap classification for historical work can create survivorship bias.
- Makes no code, test, report, config, data, runner, exporter, or production
  behavior changes.

### Phase 33B-33D.5: Benchmark/Context Data Foundation

Outcome:

- **Phase 33B:** index metadata and schema/data contracts completed.
- **Phase 33C:** index OHLC ingestion for broad, sector, and cap-segment
  indices completed.
- **Phase 33D.3:** Upstox company profile and fundamentals ingestion completed
  for Research200. Populated profiles, key ratios, financial statements,
  corporate actions, competitors, and an empty shareholding layer.
- **Phase 33D.4:** company fundamentals audit completed and approved for
  research-data readiness. Duplicate logical keys were zero across audited
  tables. Profiles covered 200/200 symbols; key ratios 199/200; financial
  statements 184/200; corporate actions 154/200; competitors 200/200;
  shareholding 0/200 because the current Upstox route returned 404 no-data.
- **Phase 33D.5:** documentation/status update completed in
  `docs/02_audits/company_fundamentals_audit.md`.

Completed follow-up phases:

- **Phase 33E:** benchmark/context feature utilities completed for
  market-relative, sector-relative, and cap-relative diagnostics.
- **Phase 33E.2:** real-data audit/export runner completed and processed
  Research200 successfully.
- **Phase 33E.3:** exact normalized-label sector proxy mapping completed;
  mapped sector labels improved from 17/68 to 25/68 while 43/68 remain
  intentionally unmapped.
- **Phase 33E.4:** documentation/status freeze completed.

- **Phase 33F:** read-only trade context audit utility completed for existing
  strategy PnL logs.
- **Phase 33F.2:** retained S1-S5 trade PnL logs audited against benchmark and
  sector context.
- **Phase 33F.3:** documentation/status freeze completed in
  `docs/02_audits/s1_s5_context_audit.md`.
- **Phase 33G:** S2 controlled context experiment design completed in
  `docs/03_research/s2_context_experiment_design.md`.
- **Phase 33G.1:** pre-declared S2 context experiment implementation/run
  completed.
- **Phase 33G.2:** S2 context experiment results documented and frozen. All
  four context-filter variants are rejected; no second-pass context variant is
  retained.
- **Phase 34A:** existing-report S2 failure-mode scrutiny reconstructed. Main
  finding: regime/state non-stationarity plus broad stop-churn during fragile
  periods.
- **Phase 34A.0:** discovery found existing S2 failure-audit tooling and
  retained/nearby reports. No new failure-audit code is currently needed.
- **Phase 34B:** prior S2 improvement variant lessons documented. 2025 guard,
  2025 context guard, and avoid shallow uptrend pullback remain rejected;
  `clean_state_v1` remains only a fragile higher-return benchmark.
- **Phase 35B/35C:** cross-strategy overlap and confirmation closeout
  documented in `docs/02_audits/cross_strategy_overlap_audit.md`. Broad voting
  and generic 2+ consensus are dropped; S2/S4 is diagnostic-only.
- **Phase 36D:** S2 state x risk and in-trade state evolution diagnostic
  design completed in
  `docs/03_research/s2_state_risk_intrade_diagnostic_design.md`. Lane A covers
  entry-state x risk inputs. Lane B covers daily in-trade state deterioration
  and hypothetical next-open exit analysis. Docs/design only; no S2 rule,
  dynamic exit, state filter, risk filter, backtest implementation, or strategy
  behavior change is approved. Phase 36D selected:
  `PROCEED_TO_36E_STATE_METADATA_DISCOVERY`.
- **Phase 36E:** S2 state metadata / in-trade reconstruction discovery
  completed in
  `docs/03_research/s2_state_metadata_intrade_reconstruction_discovery.md`.
  Lane A is `READY_WITH_MINOR_GAPS`; Lane B is
  `NEEDS_DAILY_STATE_RECONSTRUCTION`. No diagnostic helper, backtest, report,
  dynamic exit, filter, rule, or strategy change is approved. Next selected
  gate: `PROCEED_TO_36F_STATE_RECONSTRUCTION_PROTOTYPE_DESIGN`.
- **Phase 36F:** S2 daily state reconstruction prototype design completed in
  `docs/03_research/s2_daily_state_reconstruction_prototype_design.md`. The
  future prototype must reconstruct daily S2 states, expand trade lifecycle
  rows, enforce same-day stop/target safety, evaluate next-open feasibility,
  and validate reconstructed entry-state match rate before any full audit
  helper. Docs/design only; no prototype code, backtest, report, dynamic exit,
  filter, rule, or strategy change is approved. Next selected gate:
  `PROCEED_TO_36G_STATE_RECONSTRUCTION_PROTOTYPE_IMPLEMENTATION`.
- **Phase 37O:** Kronos adapter/output-validation debug design completed in
  `docs/03_research/external_model_kronos_adapter_output_validation_debug.md`.
  The lane remains blocked by invalid OHLC output validity; next gated decision
  is adapter debug execution, not diagnostic scaling.
- **Phase 37P:** Approved tiny Kronos adapter debug execution completed in
  `docs/03_research/external_model_kronos_adapter_debug_result.md`. Eval mode
  and low-randomness decoding improved validity in the tiny sample, but
  caller-side output-validity policy is still required before any diagnostic
  retry.
- **Phase 37Q:** Kronos output-validity policy design completed in
  `docs/03_research/external_model_kronos_output_validity_policy.md`. Future
  diagnostics must exclude invalid forecast runs from signal metrics by
  default and implement explicit eval/decoding/validity audit requirements
  before any retry.
- **Phase 37R:** Kronos output-validity policy helpers implemented in
  `src/veridian_quant/v2/external_models/kronos/output_validity.py` and tested
  with synthetic data in `tests/v2/test_kronos_output_validity.py`. No Kronos
  inference, model loading, report generation, backtest, strategy logic change,
  or cloned-repo modification is approved. Next selected gate:
  `PROCEED_TO_37S_POLICY_COMPLIANT_RETRY_DESIGN`.
- **Phase 37S:** Kronos policy-compliant small diagnostic retry design
  completed in
  `docs/03_research/external_model_kronos_policy_compliant_retry_design.md`.
  Any future retry must use explicit eval when supported, deterministic-ish
  decoding, and the 37R output-validity helpers; invalid forecast runs remain
  excluded from signal metrics. Next selected gate:
  `PROCEED_TO_37T_POLICY_COMPLIANT_RETRY_APPROVAL`.
- **Phase 37T:** Approved policy-compliant `Kronos-small` retry executed and
  documented in
  `docs/03_research/external_model_kronos_policy_compliant_retry_result.md`.
  The run completed 30 / 30 forecasts, but 3 / 30 forecast runs were invalid
  and output validity failed under the 37Q run-rate threshold. Validity-gated
  metrics on 27 valid runs remained weak/negative. Next selected gate:
  `PROCEED_TO_37U_POLICY_RETRY_RESULT_SCRUTINY`.
- **Phase 37W:** Kronos lane closeout completed in
  `docs/03_research/external_model_kronos_closeout.md`. Final verdict:
  `DOCS_ONLY_CLOSEOUT_AND_BIMONTHLY_REVIEW`. No further Kronos inference,
  local patch, Research200 scaling, strategy integration, production use, or
  raw predicted-candle trading is approved. Review upstream repo/issues/model
  cards every two months for maturity, fixes, prediction-quality evidence, and
  output-validity/reproducibility improvements before any reopening.

Remaining planned follow-up phases:

- **Next branch:** Phase 36G S2 State Reconstruction Prototype Implementation.
  Implement only the narrow read-only reconstruction prototype described in
  Phase 36F, not the full audit helper and not any trading rule.
- **Later:** broader strategy exposure/regime audit, historical index
  constituents, and point-in-time classification.

---

## Retained S2 Benchmarks

### Safer S2 Benchmark

Configuration:

- Strategy: `S2_MARKOV_STATE_TRANSITION`
- `markov_signal_filter = exclude_ret_down`
- `s2_candidate_ranking = none`

Approximate result:

- Trades: 577
- Net PnL: about Rs 9.72L
- CAGR: about 11.32%
- Max drawdown: about 24.04%
- Profit factor: about 1.189
- Win rate: about 45.23%

Role:

- Safer S2 benchmark.
- Better drawdown profile.
- Lower return than the high-return candidate.
- Not production-approved.

### Higher-Return S2 Research Candidate

Configuration:

- Strategy: `S2_MARKOV_STATE_TRANSITION`
- `markov_signal_filter = exclude_ret_down`
- `s2_candidate_ranking = clean_state_v1`

Approximate result:

- Trades: 583
- Net PnL: about Rs 12.32L
- CAGR: about 13.52%
- Max drawdown: about 33.94%
- Profit factor: about 1.223
- Win rate: about 47.68%
- 2025 PnL: about -Rs 7.50L

Role:

- Higher-return S2 research candidate.
- Useful benchmark.
- Fragile because of 2025 regime failure.

---

## S2 Rejected Variants

The following variants are rejected as S2 benchmarks:

- `avoid_shallow_uptrend_pullback_v1`
- `exclude_ret_down + avoid_shallow_uptrend_pullback_v1`
- `exclude_ret_down + 2025_guard_v1`
- `exclude_ret_down + 2025_guard_v1 + signal-time context`
- `S2_AVOID_BENCHMARK_20D_STRONG_NEGATIVE`
- `S2_REQUIRE_STOCK_OUTPERFORMING_BENCHMARK_20D`
- `S2_AVOID_STOCK_STRONGLY_UNDERPERFORMING_BENCHMARK_20D`
- `S2_AVOID_MAPPED_SECTOR_NEGATIVE_20D`

Reasons:

- `avoid_shallow_uptrend_pullback_v1` reduced 2025 damage when used alone, but weakened total profitability too much.
- `exclude_ret_down + avoid_shallow_uptrend_pullback_v1` increased drawdown and did not preserve the 2025 fix.
- `exclude_ret_down + 2025_guard_v1` improved 2025 but reduced total PnL too much.
- `exclude_ret_down + 2025_guard_v1 + signal-time context` proved Phase 27J infrastructure worked, but the final result remained weak: about Rs 4.78L net PnL, about 6.37% CAGR, about 26.87% max drawdown, about 1.116 PF, and 2025 improved to about -Rs 156K while too much total edge was lost.
- `exclude_ret_down + avoid_shallow_uptrend_pullback_v1` had about Rs 11.10L
  net PnL, but profit factor slipped to about 1.185 and max drawdown worsened
  to about 37.42%, with worse 2025/2026 behavior.
- `exclude_ret_down + 2025_guard_v1` had about Rs 5.65L net PnL, about 1.133
  PF, and about 26.87% max drawdown, cutting too much edge versus the safer
  baseline without meaningfully fixing 2025.
- Phase 33G.1 simple benchmark/relative/sector context filters failed the
  pre-declared acceptance criteria. No variant qualified for second pass.

Frozen lesson:

- S2 cannot be rescued by simple guards, direct 2025-specific rules,
  shallow-pullback bans, or simple state exclusions.
- Do not remove months, symbols, sectors, or state labels directly from these
  reports.
- Do not optimize S2 by final PnL or promote higher-PnL variants when PF,
  drawdown, or yearly fragility worsens.
- Future S2 work must address regime/state reliability more robustly, through a
  separately approved hypothesis.

---

## Active Research Position

The current evidence says:

- S1 has positive benchmark evidence on the audited 200-symbol research universe.
- S1 is useful as a benchmark, not as a final production strategy.
- S2 has evidence of edge, but remains regime fragile.
- S2 is retained as a benchmark/research candidate, not deployed live.
- Prior S2 guard/context/state-exclusion variants do not replace the retained
  safer baseline.
- `clean_state_v1` is retained only as a fragile higher-return benchmark.
- S3 is completed as a standalone trend-continuation experiment and parked.
- The best S3 variant is retained as a benchmark only.
- S4 is completed as a raw compression-breakout experiment and parked.
- The best S4 variant is retained as a weak benchmark only.
- Portfolio capacity and accepted-trade selection remain major bottlenecks.
- Additional S2 tuning has reached diminishing returns.
- Additional S3 tuning risks overfitting.
- Additional S4 threshold tuning risks overfitting.
- S5 first-pass momentum rotation did not challenge S2/S1/S3; immediate S5
  tuning is parked.

Next direction:

- Do not continue immediate S2 or S3 tuning.
- Do not continue immediate S4 tuning.
- Keep I1 RAWRS diagnostic-only after the failed S3 p20/p10 hard-filter tests.
- Prioritize feature stability, significance, and capacity-aware ordering
  research before considering another true overlay.
- Do not convert S1/S2/S4 post-hoc RAWRS findings directly into hard filters.
- Keep S5 parked after the first-pass audit unless future work proposes a
  materially redesigned momentum hypothesis.
- Treat Phase 33E through 33G.2 as complete diagnostic/design/experiment
  context work, not as a strategy upgrade.
- Treat Phase 35B/35C as a closed ensemble branch. Broad voting and 2+
  consensus are dropped; S2/S4 is diagnostic-only and must not be cherry-picked
  from the 0-session or 1-session results.
- Treat Phase 36B/36C as a closed risk diagnostic branch. Liquidity is the
  strongest S2 risk diagnostic, benchmark regime/drawdown/gap/rolling-R remain
  research diagnostics, and India VIX is retained only as secondary context.
  No risk model, VIX rule, liquidity filter, drawdown throttle, rolling-R
  threshold, benchmark-regime filter, gap filter, dynamic sizing change, or
  production behavior is approved.
- Treat Phase 36D as a docs-only S2 diagnostic design. Entry-state x risk and
  in-trade state evolution are approved only for future discovery and
  read-only audit planning. No dynamic exit, `exit if RET_DOWN` rule, entry
  filter, state exclusion, risk filter, sizing change, backtest optimization,
  or strategy behavior change is approved. Phase 36D selected:
  `PROCEED_TO_36E_STATE_METADATA_DISCOVERY`.
- Treat Phase 36E as discovery-only. Entry-state x risk is close to ready from
  existing metadata, but in-trade state evolution requires daily state
  reconstruction design before any helper. Next selected gate:
  `PROCEED_TO_36F_STATE_RECONSTRUCTION_PROTOTYPE_DESIGN`.
- Treat Phase 36F as docs/design only. It approves only a future narrow
  reconstruction prototype implementation, not a full audit helper, dynamic
  exit, filter, rule, backtest optimization, or strategy behavior change. Next
  selected gate:
  `PROCEED_TO_36G_STATE_RECONSTRUCTION_PROTOTYPE_IMPLEMENTATION`.
- Treat Phase 37A through 37W as a closed external-model research lane for
  Kronos. Final verdict:
  `DOCS_ONLY_CLOSEOUT_AND_BIMONTHLY_REVIEW`. No further local Kronos
  inference, local patch, Research200 scaling, strategy integration,
  production use, raw predicted-candle execution, or dependency merge is
  approved. Review upstream repo/issues/model cards every two months and reopen
  only after concrete upstream maturity, output-validity/reproducibility
  improvement, prediction-quality evidence, or explicit user approval for a
  new design.
- Close the simple S2 context-filter branch. Do not continue with threshold
  fishing, filter stacking, or another minor benchmark/relative/sector context
  tweak. Company fundamentals are now ingested and audited as research context,
  but current snapshot ratios and static classifications must not be used as
  historical signal-time facts.
- Decide the next research branch separately; any future S2 work needs a
  genuinely new hypothesis.
- Revisit S3 only if a new regime model, ranking/capacity redesign, sector/relative-strength framework, or ensemble diversification requirement creates a specific reason.
- Revisit S4 only if a materially new hypothesis appears, such as better market-regime gating, sector context, capacity/ranking redesign, or a broader portfolio-construction reason.

---

## Parked / Future Work

The following are future research directions, not accepted production rules:

- S2 regime-aware exposure reduction.
- S2 controlled context-aware diagnostic experiments from Phase 33G are tested
  and rejected; future S2 work requires a new hypothesis rather than threshold
  tweaks to these filters.
- Better market-regime detector.
- More robust capacity-aware ranking.
- Use Phase 27J signal-time context infrastructure in future rankers.
- Potential S2 revisit after more independent strategy evidence.
- Potential S3 revisit only after material regime/ranking/sector/ensemble changes.
- Potential S4 revisit only after material regime/ranking/sector/portfolio-construction changes.
- I1 RAWRS market-structure intelligence diagnostics, beginning with Phase 30C signal-time diagnostic design.
- Sector/industry conditioning if metadata becomes available.
- Symbol-level robustness filters after broader strategy comparison.
- S1 candidate ranking v2.
- FFT strategy.
- Wavelet strategy.
- Cross-strategy risk-model input discovery.
- Cross-strategy pre-registered risk experiment design after Phase 36B/36C.
- Resolve S2 state reconstruction DB/OHLC reachability after Phase 36H.1.
- Exact liquidity data-quality audit before any liquidity diagnostic is elevated
  toward implementation.
- Kronos offline diagnostic/ranking/context/confirmation evaluation is closed
  for now after Phase 37W. Maintain only a bi-monthly upstream review note;
  reopen only under the documented 37W revisit conditions.
- Universe/regime segmentation research.
- S2 risk model research.
- Meta-ranking / capital allocation layer.
- Walk-forward validation, regime splits, parameter sensitivity, and capacity
  stress testing after the Phase 31 Monte Carlo baseline.
- Benchmark, sector, market-cap, capital-utilization, and exposure context from
  the Phase 33 roadmap.
- TradingAgents under a future external-model intelligence lane. It is
  postponed, not rejected, until common validation infrastructure is stronger.

These ideas may be researched later only after standalone evidence and auditability requirements are satisfied.
