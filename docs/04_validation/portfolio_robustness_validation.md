# Portfolio Robustness Validation Layer

## 1. Purpose

The Portfolio Robustness Validation Layer is a post-backtest research and risk-validation layer. It evaluates the completed trades produced by a strategy and asks whether the observed portfolio result appears stable under alternative trade sequences and resampled trade mixes.

Its primary questions are:

- Was the observed result robust, or unusually dependent on luck?
- How sensitive was the equity path to trade order?
- What drawdown and streak behavior could occur under worse sequencing?
- How often could the strategy finish below starting equity or reach ruin?
- Which benchmark has the strongest downside-adjusted robustness rather than merely the highest nominal PnL?

This document is the Phase 31A design specification. It does not implement or run validation.

## 2. Scope

The first validation layer will consume completed strategy trade results, run reproducible Monte Carlo experiments, and summarize distributions of terminal value, drawdown, streaks, and ruin risk.

Initial scope:

- Completed S1, S2, S3, and S4 benchmark output folders.
- Trade-level realized net PnL after costs.
- Shuffle and bootstrap simulations.
- Downside-focused, comparable validation outputs.
- Standalone validation/reporting after a strategy backtest has finished.

## 3. Non-goals

This layer will not:

- Create buy or sell signals.
- Change entries, exits, sizing, capacity, execution, or portfolio accounting.
- Rerun or replace the strategy backtest.
- Optimize strategy parameters or select thresholds.
- Promote a strategy to production by itself.
- Turn post-hoc results into strategy filters.
- Treat the best simulated path as evidence of quality.
- Model unknown market regimes, liquidity shocks, or structural breaks in Phase 31.

Monte Carlo is a validation tool, not a strategy.

## 4. Why Robustness Validation Is Needed

A single historical equity curve is only one ordering and one realized mix of trades. Nominal PnL can conceal dependence on a few large winners, favorable sequencing, unusually short losing streaks, or a drawdown path that was kinder than other plausible paths.

The retained benchmarks already exhibit materially different return and drawdown profiles. A common robustness layer is needed before adding more complex external models so that current and future candidates are judged by consistent downside evidence.

## 5. Strategy Backtest Versus Robustness Validation

| Strategy backtest | Robustness validation |
| --- | --- |
| Generates signals from historical information | Starts only after trades are complete |
| Applies chronology, entry, exit, sizing, capacity, and execution rules | Does not change strategy or execution rules |
| Produces the realized trade ledger and equity curve | Resamples the realized net trade outcomes |
| Answers what the implemented strategy did historically | Answers how sensitive that realized evidence is to sequence or sample variation |

Validation results do not become portfolio PnL and must remain separate from the original ledger and reports.

## 6. Monte Carlo Trade-Sequence Simulation

Let the completed trade PnLs be `p_1, ..., p_n` and starting equity be `E_0`. For each simulation, construct a sequence `p*_1, ..., p*_n` using a declared mode and calculate:

`E_t = E_0 + sum(p*_i for i = 1..t)`

The simulation records the full path, final equity, maximum drawdown, streak lengths, and any ruin/near-ruin event. Runs must use an explicit pseudo-random seed, simulation count, mode, input fingerprint, and methodology version so results are reproducible.

The Phase 31 baseline uses realized absolute net PnL per trade. It does not retrospectively resize trades. A later method may test normalized returns or R-multiples, but it must be labeled separately and must not be mixed with the baseline.

## 7. Shuffle-Mode Monte Carlo

Shuffle mode randomly permutes the actual completed trades without replacement.

Properties:

- Every simulation contains exactly the same trades and aggregate net PnL.
- Only order changes.
- It isolates sequence risk in drawdown, ruin timing, and winning/losing streaks.
- With additive absolute trade PnL, final equity is invariant: `E_0 + sum(p_i)`. Therefore final-equity percentiles in shuffle mode are expected to be identical and must not be misrepresented as a terminal-return distribution.

Shuffle mode preserves the realized trade set but does not preserve calendar clustering, overlapping positions, capacity interactions, serial dependence, or equity-dependent sizing. It is a conditional path-stress diagnostic, not a counterfactual portfolio rerun.

## 8. Bootstrap-Mode Monte Carlo

Bootstrap mode samples `n` trades with replacement from the realized trade set.

Properties:

- A trade may appear zero, one, or several times in a simulation.
- Simulations can contain better or worse mixes than the original ledger.
- Final equity and net PnL vary across simulations.
- It tests empirical distribution/resampling risk in addition to sequence risk.

The simple independent-trade bootstrap is the Phase 31 baseline. Because it breaks serial and regime dependence, future work should consider block, stratified, or regime-aware bootstrap methods after the baseline is audited.

## 9. Required Inputs

Required:

- A completed `trade_pnl_log.csv` from one immutable strategy run.
- One finite realized net PnL value per completed trade.
- Starting equity in the same currency and units as trade PnL.
- Strategy/run identity and variant name.

Conditionally required for reliable audit:

- A stable trade identifier or a documented deterministic row-order fallback.
- Confirmation that open/unresolved trades are excluded or handled by an explicit policy.
- Confirmation that costs are already included in realized net PnL.

Optional:

- Original equity curve.
- Original maximum drawdown.
- Original chronological trade order and completion timestamps.
- Run metadata, date range, universe, and source-output fingerprint.

Input validation must reject missing or non-finite PnL, duplicate ambiguous records, currency/unit mismatches, non-positive starting equity, an empty trade set, and inconsistent declared totals. Missing optional inputs must be reported, not silently inferred.

## 10. Required Outputs

Each validation run should produce a separate, reproducible artifact set containing:

- Validation manifest: strategy, variant, source path/fingerprint, trade count, starting equity, mode, seed, simulation count, and methodology version.
- Summary metrics for each simulation mode.
- Quantile table for final equity, net PnL, maximum drawdown, and streak lengths.
- Threshold-breach probabilities and ruin/near-ruin counts.
- Original-versus-simulated comparison when the original equity curve/drawdown is available.
- Machine-readable per-simulation summary rows.
- Human-readable warnings, limitations, and interpretation notes.

Outputs must be written outside strategy output folders and must never overwrite source backtest artifacts. Phase 31A generates none of these outputs.

## 11. Core Metrics

### Terminal distributions

- Final equity distribution.
- Net PnL distribution.
- Median final equity.
- 5th and 95th percentile final equity.
- Worst and best simulated final equity.
- Probability of ending below starting equity.

For shuffle mode with absolute realized PnL, terminal metrics are invariant by design. The report must state this explicitly.

### Drawdown distributions

For each path, percentage drawdown is the decline from its running equity peak. Report:

- Maximum drawdown distribution.
- Median maximum drawdown.
- 95th percentile maximum drawdown, where a larger positive magnitude is worse.
- Worst maximum drawdown.
- Probability that maximum drawdown is greater than 10%, 20%, 30%, and 40%.

The implementation must also define behavior if a path reaches non-positive equity, because percentage drawdown ceases to be economically ordinary after ruin.

### Streak distributions

- Longest losing streak distribution.
- Longest winning streak distribution.
- Median, 95th percentile, and worst longest losing streak.
- Median, 5th percentile, and best longest winning streak where useful.

A losing trade has net PnL below zero, a winning trade has net PnL above zero, and a zero-PnL trade breaks both streaks unless a later documented policy supersedes this rule.

### Ruin and near-ruin

- Ruin event: equity reaches or falls below zero at any point.
- Probability of ruin.
- Minimum-equity distribution.
- Near-ruin probabilities at predeclared equity floors, proposed initially as 25% and 50% of starting equity.

Near-ruin thresholds must be fixed before strategy comparison and must not be tuned per strategy.

## 12. Interpretation Rules

- Emphasize downside quantiles, threshold breaches, losing streaks, and ruin risk.
- Compare like-for-like runs using the same PnL definition, starting equity convention, simulation modes, simulation count, and seed policy.
- A higher nominal-PnL strategy may be inferior if its adverse drawdown and ruin distributions are materially worse.
- A modest-PnL strategy may be more robust if it has stable drawdowns and low loss-of-capital risk.
- The 5th percentile bootstrap final equity is a downside scenario estimate, not a forecast or guarantee.
- The 95th percentile maximum drawdown is an adverse drawdown estimate because drawdown is reported as a positive loss magnitude.
- Best simulated outcomes are descriptive only and must not drive promotion.
- Original results outside the central simulated range require investigation, not automatic rejection or acceptance.
- Monte Carlo evidence supplements chronology, regime, parameter-sensitivity, and walk-forward evidence; it does not replace them.

No universal pass/fail threshold is authorized in Phase 31A. Phase 31D should establish comparison and escalation rules only after observing audited outputs without retroactively tuning rules to favor a benchmark.

## 13. Failure Modes to Detect

The layer should expose or flag:

- High probability of finishing below starting equity.
- Material ruin or near-ruin probability.
- Drawdown tails materially worse than the observed backtest.
- Long losing streaks incompatible with operational or behavioral tolerance.
- Dependence on a small number of large winners.
- Bootstrap instability caused by too few trades or extreme outliers.
- Suspicious disagreement between source totals and reconstructed totals.
- Invalid, missing, duplicated, mixed-currency, gross-PnL, or unresolved trade rows.
- Too few simulations for stable tail estimates.
- Accidental nondeterminism or unrecorded random seeds.
- Incorrect claims that shuffle mode creates a final-equity distribution under fixed additive PnL.
- Overinterpretation of independent bootstrap results when trades are serially or regime dependent.

## 14. Application to S1, S2, S3, and S4

Validation should use retained or benchmark outputs, never silently substitute rejected variants:

- **S1:** validate `S1_BASELINE` as the original v2 benchmark. Test whether its favorable aggregate result hides sequence, streak, or large-winner concentration risk.
- **S2:** validate the retained safer benchmark and higher-return research candidate separately. The key comparison is whether extra return compensates for worse downside tails; Monte Carlo does not erase S2's known regime fragility.
- **S3:** validate `S3_STRONG_TREND_ABOVE_SMA50_V1` as benchmark-only evidence. Its modest nominal edge makes probability of loss and drawdown stability especially important.
- **S4:** validate `S4_ATR_COMPRESSION_BREAKOUT_V1` only as the weak retained S4 reference unless Phase 31C explicitly includes rejected variants for diagnostic contrast. Monte Carlo cannot rehabilitate the rejected or unpromoted S4 variants.

All remain research benchmarks or parked candidates; none becomes production-approved because of Phase 31.

## 15. Future S5 and External Models

Any future S5 strategy should emit the same completed-trade contract and pass the same validation lane before cross-strategy promotion.

Kronos and TradingAgents remain future candidates under an external-model intelligence lane. They are postponed, not rejected, because the project first needs stronger common validation tools. Their complexity must not grant them different evidence standards.

If Kronos later shows strong standalone results under disciplined, leakage-safe testing, it may be evaluated both:

- Standalone, as its own model or strategy candidate.
- As an integrated Veridian feature/model layer, with the combined system backtested first and robustness validation applied to its completed trades afterward.

The same principle applies to TradingAgents or another external system. Model outputs do not bypass chronology, execution, portfolio, audit, or robustness requirements.

## 16. Limitations

- Monte Carlo cannot prove future profitability.
- It tests the realized trade sample, not unknown future regimes or structural breaks.
- Independent resampling ignores calendar context, cross-trade dependence, capacity, overlapping exposure, and regime clustering.
- Shuffle mode can generate orders that the original portfolio mechanics could not have produced.
- Fixed realized PnL ignores the effect that reordered equity would have had on compounding and position size.
- Bootstrap can be optimistic or pessimistic depending on sample quality and outliers.
- Small samples produce unstable tail estimates.
- Simulated probabilities are conditional estimates, not calibrated real-world probabilities.
- Transaction-cost, liquidity, capacity, parameter, and model risk require separate stress tests.

## 17. Phase Plan

- **Phase 31A — Design:** docs-only specification, methodology boundary, roadmap, and decision record.
- **Phase 31B — Implementation:** standalone Monte Carlo validation utilities, input validation, deterministic seeds, tests, and isolated exporters. No runner or signal integration by default.
- **Phase 31C — Benchmark execution:** run audited shuffle and bootstrap validation on retained S1/S2/S3/S4 outputs using a frozen protocol.
- **Phase 31D — Robustness audit:** compare benchmark downside distributions, document findings, and define evidence-based follow-up without selecting by best outcome.
- **Later validation:** walk-forward validation, regime splits, parameter sensitivity, block/regime-aware bootstrap, capacity and liquidity stress testing, and external-model evaluation.

## 18. Open Questions

- Which exact column in each existing `trade_pnl_log.csv` is the canonical realized net PnL field, and are units consistent across all runners?
- Is starting equity reliably recorded in run metadata, or must Phase 31B require it explicitly?
- What default simulation count provides stable 5th/95th percentile estimates within acceptable runtime? A candidate must be frozen and convergence-checked before Phase 31C.
- Should Phase 31C use one common seed set across strategies to improve comparability, alongside strategy-specific input fingerprints?
- Should the first implementation stop a path at ruin or continue arithmetically while retaining the first ruin event?
- Are 25% and 50% of starting equity suitable near-ruin floors?
- When should block or regime-stratified bootstrap supersede the independent bootstrap baseline?
- Should a later normalized-return/R-multiple mode model resizing, and how can it avoid being confused with the absolute-PnL baseline?
- What minimum trade count is required before percentile and ruin estimates are publishable rather than marked exploratory?
- Which Phase 31D thresholds should trigger rejection, further investigation, or additional validation without being tuned after seeing strategy identities?

## 19. References and Related Documents

- `docs/00_foundation/v2_design_document.md`
- `docs/00_foundation/v2_research_roadmap.md`
- `docs/04_validation/backtest_methodology.md`
- `docs/04_validation/robustness_testing.md`
- `docs/04_validation/walk_forward_protocol.md`
- `docs/02_audits/strategy_audit_master.md`
- `docs/02_audits/s1_audit.md`
- `docs/02_audits/s2_audit.md`
- `docs/02_audits/s3_audit.md`
- `docs/02_audits/s4_audit.md`
- `docs/05_decisions/decision_log.md`
- `docs/06_intelligence/i1_rawrs_combined_evidence_audit.md`

