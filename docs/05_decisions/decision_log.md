# Decision Log

This log records major research and architecture decisions for Veridian Quant v2.

---

## 2026-06-14 - Expand From Narrow Universe to Audited Research Universes

Decision:

Move beyond the narrow initial universe and use audited 100-symbol and 200-symbol research universes for S1 evaluation.

Reason:

The initial narrow universe was not enough evidence for broader strategy conclusions.

Consequence:

Research universe construction and data quality audit became part of the standard validation workflow.

---

## 2026-06-14 - Use Research200 S1 Baseline as Current Benchmark

Decision:

Use `S1_BASELINE` on the audited 200-symbol research universe as the current benchmark.

Benchmark:

- Period: 2020-01-01 to 2026-04-30
- Net PnL: approximately +579K
- Gross profit: approximately +4.64M
- Gross loss: approximately -4.06M
- Profit factor: approximately 1.143
- Max drawdown: approximately 23.52%
- Trades: 535
- Total signals: 7,476
- Rejected signals: 6,941
- Portfolio capacity rejections: 6,726

Consequence:

S1 baseline remains the comparison point for future strategy families, but is not final or production-ready.

---

## 2026-06-14 - Reject / Park Hard S1 Filters After Broader-Universe Results

Decision:

Do not promote hard S1 filter variants.

Reason:

S1 hard-filter variants did not generalize reliably on the broader universe. `S1_AVOID_MESSY_MIDDLE_V1` performed badly despite earlier promise. `S1_BROAD_BEST_GUESS` was conservative but did not beat the 200-symbol baseline.

Consequence:

Hard filters remain research probes only.

---

## 2026-06-14 - Park S1 Candidate Ranking v1

Decision:

Park `candidate-ranking s1_v1`.

Reason:

It was technically valid but underperformed the unranked S1 baseline.

Consequence:

No S1 ranking method is currently promoted. S1 ranking v2 is deferred.

---

## 2026-06-14 - Add All-Signal Opportunity Diagnostics

Decision:

Add diagnostics for all generated S1 signals, including accepted trades, rejected active-symbol signals, rejected capacity signals, same-day candidate pools, and ranking feature summaries.

Reason:

Accepted-trade-only reports are incomplete when the portfolio rejects most generated signals because capacity is full.

Consequence:

Future ranking and voting research can evaluate opportunity quality across accepted and rejected candidates.

---

## 2026-06-14 - Treat Counterfactual Rejected-Signal PnL as Diagnostics Only

Decision:

Counterfactual rejected-signal PnL must not be treated as actual achievable portfolio PnL.

Reason:

Counterfactual simulations ignore portfolio capacity, ledger effects, and real capital allocation.

Consequence:

Counterfactual results may inform ranking hypotheses, but must not be mixed into actual portfolio performance metrics.

---

## 2026-06-14 - Implement S2 Markov as Standalone Strategy

Decision:

Implement `S2_MARKOV_STATE_TRANSITION` as a separate strategy family.

Reason:

The project should test genuinely different standalone strategy families before over-optimizing S1 ranking.

Consequence:

S2 is not an S1 filter and must be benchmarked independently.

---

## 2026-06-14 - Hold S2 Execution Until Docs and Audit Decisions Are Refreshed

Decision:

Do not run S2 on research200 until documentation, audits, and decision logs reflect the current research state.

Reason:

The documentation set must remain internally consistent before adding new benchmark results.

Consequence:

Phase 27B refreshed core docs. Phase 27C refreshes audit and decision records.

---

## 2026-06-14 - Defer FFT and Wavelet Until After S2 Baseline Evidence

Decision:

Defer FFT and wavelet strategy research until after S2 has standalone benchmark evidence.

Reason:

The project should avoid adding too many advanced strategy families before validating S2.

Consequence:

FFT and wavelet remain future research directions, not accepted production rules.

---

## 2026-06-17 - Freeze S2 Markov Research After Phase 27J

Decision:

Freeze `S2_MARKOV_STATE_TRANSITION` research for now.

Keep two retained S2 benchmarks:

- Safer benchmark: `markov_signal_filter = exclude_ret_down`, `s2_candidate_ranking = none`
- Higher-return research candidate: `markov_signal_filter = exclude_ret_down`, `s2_candidate_ranking = clean_state_v1`

Approximate retained benchmark results:

- Safer benchmark: about Rs 9.72L net PnL, about 11.32% CAGR, about 24.04% max drawdown, about 1.189 PF.
- Higher-return candidate: about Rs 12.32L net PnL, about 13.52% CAGR, about 33.94% max drawdown, about 1.223 PF, and about -Rs 7.50L in 2025.

What was tried:

- Raw S2 Markov baseline.
- Markov state filters.
- Candidate ranking modes.
- Rejected/capacity counterfactual diagnostics.
- 2025 failure audit.
- `avoid_shallow_uptrend_pullback_v1`.
- `2025_guard_v1`.
- Signal-time stock/Nifty/relative-strength context enrichment.

Rejected as benchmarks:

- `avoid_shallow_uptrend_pullback_v1`
- `exclude_ret_down + avoid_shallow_uptrend_pullback_v1`
- `exclude_ret_down + 2025_guard_v1`
- `exclude_ret_down + 2025_guard_v1 + signal-time context`

Reason:

S2 has evidence of edge, but remains regime fragile. The high-return candidate suffered a recurring 2025 regime failure concentrated in `RET_UP + VOL_MID + DD_SHALLOW + not truly near lows`, especially:

- `RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW`
- `RET_UP|VOL_MID|DD_SHALLOW|LOW_MID_RANGE`

Guard variants reduced the targeted pocket, but weakened total PnL too much or shifted losses to replacement candidates.

Consequence:

S2 is retained as a benchmark/research candidate, not production-ready and not deployed live.

Next:

Move the next research effort to a new independent strategy, likely S3 trend pullback continuation or another non-S2 alpha source.

---

## 2026-06-17 - Begin S3 Trend Pullback Continuation Research

Decision:

Begin `S3_TREND_PULLBACK_CONTINUATION` as the next independent strategy-family research track.

Context:

S1 remains the original v2 mean-reversion benchmark, and S2 has been frozen after Phase 27J/27K/27L as a benchmark/research candidate rather than a production-ready strategy.

The next alpha source should be independent from S1/S2 instead of continuing immediate S2 tuning.

S3 will test structured pullbacks in confirmed uptrends:

- Buy strength after a controlled dip, not weakness after panic.
- Require trend health before considering a pullback.
- Avoid deeply broken stocks that are down for structural reasons.

Consequence:

Phase 28A is specification-only. No S3 implementation or backtest has started yet.

Future Phase 28B should implement and benchmark the initial S3 baseline under the standard v2 portfolio methodology.

---

## 2026-06-17 - Freeze S3 Standalone Research

Decision:

Freeze `S3_TREND_PULLBACK_CONTINUATION` standalone research.

Retain one S3 benchmark only:

- `S3_STRONG_TREND_ABOVE_SMA50_V1`

Do not invest more implementation time into near-term S3 variants.

Approximate retained S3 benchmark result:

- Net PnL: about Rs 3.16L.
- CAGR: about 4.43%.
- Max drawdown: about 28.20%.
- Profit factor: about 1.104.
- Trades: about 500.

Rejected as production candidates:

- `S3_TREND_PULLBACK_CONTINUATION_BASELINE`
- `S3_STRONG_TREND_V1`
- `S3_ABOVE_SMA50_V1`
- `S3_STRONG_TREND_ABOVE_SMA50_V1`
- `S3_CONTROLLED_PULLBACK_V1`

Reason:

S3 is technically valid, but the standalone edge is weak. The controlled-pullback variant did not improve realized performance, despite accepted-trade diagnostics suggesting that very deep 5-day pullbacks were damaging. Best S3 remains materially weaker than retained S1/S2 candidates, and more threshold tuning risks overfitting.

Consequence:

S3 is parked as a benchmark-only strategy family. Future work should move to broader strategy research, robustness, portfolio construction, or the next independent strategy family.

---

## 2026-06-18 - Start S4 Docs-Only Independent Strategy Family

Decision:

Start Phase 29A for `S4_ENTROPY_VOLATILITY_COMPRESSION_BREAKOUT` as a new independent strategy-family specification.

Context:

S1 remains the benchmark Z-score mean-reversion strategy, not production-ready.

S2 Markov State Transition remains frozen/parked with retained safer and higher-return benchmarks, not production-ready.

S3 Trend Pullback Continuation remains parked with `S3_STRONG_TREND_ABOVE_SMA50_V1` retained as benchmark only, not production-ready.

S4 will test long-only breakouts after volatility, range, or optional entropy/noise compression:

- ATR percentile compression.
- Rolling high-low range compression.
- Optional entropy/noise compression.
- Close above N-day high.
- Optional volume confirmation.
- Optional trend context.

Initial future benchmark variants:

- `S4_ATR_COMPRESSION_BREAKOUT_V1`
- `S4_RANGE_COMPRESSION_BREAKOUT_V1`
- `S4_ENTROPY_GATED_BREAKOUT_V1`

Reason:

Further near-term S2 or S3 threshold tuning risks overfitting. The next useful step is to define a separate alpha source before any implementation work.

Consequence:

Phase 29A is docs/spec only. No production strategy code, backtest runners, tests, configs, or data files should be changed. No S2/S3 filter mixing, parameter tuning, production decision, or portfolio blending is authorized in this phase.

---

## 2026-06-18 - Freeze S4 Raw Baseline Research After Phase 29F/29G

Decision:

Freeze/park `S4_ENTROPY_VOLATILITY_COMPRESSION_BREAKOUT` raw baseline research.

Retain one weak S4 benchmark only:

- `S4_ATR_COMPRESSION_BREAKOUT_V1`

Reject as S4 raw baseline:

- `S4_RANGE_COMPRESSION_BREAKOUT_V1`

Do not promote:

- `S4_ENTROPY_GATED_BREAKOUT_V1`

Raw Research200 baseline scope:

- Period: 2020-01-01 to 2026-04-30.
- Universe: audited Research200.
- Starting equity: about Rs 10,00,000.
- Default v2 portfolio methodology.
- No ranking.
- No tuning.
- No production decision.

Approximate raw baseline results:

- `S4_ATR_COMPRESSION_BREAKOUT_V1`: about +Rs 1.65L net PnL, about 2.45% CAGR, about 39.12% max drawdown, about 1.037 PF, 559 trades, about 40.97% win rate, and about +Rs 296 average net PnL per trade.
- `S4_RANGE_COMPRESSION_BREAKOUT_V1`: about -Rs 4.13L net PnL, about -8.06% CAGR, about 57.79% max drawdown, about 0.883 PF, 590 trades, about 37.46% win rate, and about -Rs 699 average net PnL per trade.
- `S4_ENTROPY_GATED_BREAKOUT_V1`: about -Rs 1.01L net PnL, about -1.67% CAGR, about 35.76% max drawdown, about 0.975 PF, 589 trades, about 41.09% win rate, and about -Rs 172 average net PnL per trade.

Reason:

Raw S4 is technically valid but not production-ready. The ATR compression variant was the best of the three, but its edge is too weak relative to drawdown. Range compression was clearly negative. Entropy gating was near breakeven but negative and unstable.

Observed weaknesses:

- Poor return-to-drawdown.
- Weak or negative profit factor.
- Poor post-2021 stability.
- Material 2022 and/or 2025/2026 weakness.
- High capacity pressure across variants.
- Heavy dependence on candidate selection.
- Current standard signal export does not expose S4-specific compression/breakout metadata fields, creating an auditability gap for future work.

Consequence:

No more S4 tuning for now. S4 is parked/frozen like S3. `S4_ATR_COMPRESSION_BREAKOUT_V1` remains useful only as a weak research benchmark/reference, not as a production candidate. Future S4 revisit should require a materially new hypothesis such as better market-regime gating, sector context, capacity/ranking redesign, or a broader portfolio-construction reason.

---

## 2026-06-18 - Begin I1 RAWRS Market Structure Intelligence Specification

Decision:

Begin `I1_RAWRS_MARKET_STRUCTURE_INTELLIGENCE` as a non-strategy intelligence layer.

RAWRS means:

- Regime-Aware Adaptive Wavelet Response Surface.

Context:

S1 remains benchmark only. S2 remains frozen/parked. S3 remains frozen/parked. S4 remains frozen/parked after weak raw baseline evidence.

Reason:

The next useful work should study market structure, trade quality, regime context, and capacity selection without prematurely creating another direct strategy.

I1 RAWRS will focus on:

- FFT / cycle diagnostics.
- Wavelet energy and coherence.
- Entropy/noise features.
- Regime/topology concepts.
- Winner/loser separation analysis.
- Accepted versus rejected signal diagnostics.
- Future candidate-quality and regime-overlay research.

Consequence:

Create `docs/06_intelligence/` for reusable non-strategy intelligence modules. Do not call RAWRS S5. Do not create a strategy file, signal generator, backtest runner, CSV exporter, ranking rule, or production component in Phase 30A.

---

## 2026-06-18 - Design I1 RAWRS Signal-Time Diagnostics Before Ranking

Decision:

Design I1 RAWRS signal-time diagnostics before implementing any ranking, overlay, or strategy logic.

Reason:

RAWRS must first prove whether features separate winners/losers and accepted/rejected signal quality without leakage or post-hoc overfitting.

Consequence:

Phase 30C is docs-only. Future work may create diagnostic outputs, but no trading behavior changes, ranking rules, overlays, strategy logic, diagnostics runner, or production component are authorized by this decision.

---

## 2026-06-18 - Audit Strategy Output Compatibility Before RAWRS CLI

Decision:

Audit S1/S2/S3/S4 output compatibility before implementing a standalone RAWRS CLI.

Reason:

Different runners and flags may produce different CSV availability, especially when all-signal diagnostics are skipped for speed.

Consequence:

Future RAWRS CLI design should support light and full diagnostic modes. It should validate required input files for the selected mode instead of assuming one universal output shape. Missing rejected-signal files must not be interpreted as no rejections, and empty all-signal files must not be interpreted as no opportunities without checking whether diagnostics were skipped.

---

## 2026-06-18 - Implement RAWRS Diagnostics As Standalone CLI

Decision:

Implement RAWRS diagnostics as a standalone CLI with light/full mode validation before any S1/S2/S3/S4 runner integration.

Reason:

Strategy outputs differ by runner and diagnostic-skip flags. A standalone validation layer reduces coupling, keeps RAWRS optional, and protects existing strategy behavior.

Consequence:

RAWRS diagnostics can be run separately from strategy backtests. Runner integration remains deferred. The CLI should consume existing output folders, validate required files, warn on optional or incomplete inputs, write RAWRS outputs separately, and avoid changing PnL, trades, exits, sizing, rejected signals, capacity, or strategy behavior.

---

## 2026-06-19 - Reject S3 RAWRS Spectral-Concentration Hard Filters

Decision:

Reject the S3 `rawrs_fft_spectral_concentration` hard-filter overlay at p20 and
p10.

Reason:

Completed-trade diagnostics suggested that avoiding the lowest spectral-
concentration bucket might improve S3 trade quality. Leakage-safe true
backtests did not confirm that result:

- Baseline: about Rs 3.16L net PnL, 4.43% CAGR, 28.20% max drawdown, and 1.104
  profit factor.
- P20: about Rs 2.37L net PnL, 3.42% CAGR, 31.45% max drawdown, and 1.079 profit
  factor.
- P10: about Rs 0.10L net PnL, 0.15% CAGR, 31.98% max drawdown, and 1.004 profit
  factor.

The true overlays changed chronology, capacity, replacement trades,
equity-dependent sizing, and compounding. Both removed profitable baseline
trades and admitted losing replacement cohorts. The less aggressive p10 rule
did not repair the p20 failure.

Consequence:

- RAWRS remains diagnostic-only and non-production.
- Do not test additional thresholds for the same S3 hard-filter hypothesis
  unless the mechanism changes materially.
- Do not implement S1/S2/S4 RAWRS hard filters from post-hoc keep/avoid evidence
  alone.
- Future RAWRS work should focus on stability, statistical significance,
  ranking-only research, and capacity-aware ordering rather than hard gates.
- Consolidated evidence is recorded in
  `docs/06_intelligence/i1_rawrs_combined_evidence_audit.md`.

---

## 2026-06-19 - Start Portfolio Robustness Validation Before External Model Exploration

Decision:

Start the Portfolio Robustness Validation Layer before external-model
exploration. Phase 31A is docs/design only; later phases may implement and run
post-backtest Monte Carlo validation under a separately reviewed scope.

Reason:

Existing and future strategies need stronger common validation before the
project adds complex external AI/model dependencies. Completed-trade shuffle and
bootstrap analysis can expose sequence risk, adverse drawdown tails, loss
probability, streaks, and ruin/near-ruin risk without changing strategy signals
or historical portfolio results.

Consequence:

- Define the validation contract in
  `docs/04_validation/portfolio_robustness_validation.md`.
- Evaluate downside distributions and risk-adjusted robustness rather than only
  nominal PnL or best simulated outcomes.
- Do not use Monte Carlo as a signal generator, parameter optimizer, or evidence
  to excuse overfitting.
- Kronos and TradingAgents remain future candidates under an external-model
  intelligence lane. They are postponed because validation infrastructure comes
  first; they are not rejected.
- If Kronos later produces strong standalone results under disciplined testing,
  evaluate it both standalone and, where justified, as an integrated Veridian
  feature/model layer. Both forms remain subject to the normal backtest and
  robustness-validation standards.

---

## 2026-06-19 - Rank Current Benchmarks Using Monte Carlo Robustness Evidence

Decision:

Use the completed Phase 31 Monte Carlo robustness audit to rank the current
retained and benchmark strategies under a common validation protocol.

Finding:

- S2's retained `exclude_ret_down` benchmark is strongest overall. It is the
  only tested strategy with bootstrap p05 final equity above starting equity and
  has the lowest bootstrap loss probability at 3.48%.
- S1 ranks second and remains the original useful baseline.
- S3 remains a weak/moderate retained benchmark.
- S4 ATR ranks weakest and remains a weak benchmark only.
- Sequence and drawdown risk remain meaningful, including for S2.

Consequence:

- Use S2 as the primary robustness benchmark for future strategy comparisons,
  including future S5 work.
- Preserve Monte Carlo review as standard post-backtest validation.
- Grant no current strategy production approval from this audit.
- Keep S2 frozen and not production-ready despite its comparative lead.
- Keep S4 Range rejected, S4 Entropy parked/not promoted, and RAWRS
  diagnostic-only.
- Record the full evidence in
  `docs/04_validation/monte_carlo_robustness_audit.md`.

---

## 2026-06-19 - Start S5 Relative Strength / Momentum Rotation Design

Decision:

Begin Phase 32A as a docs-only design for the standalone
`S5_RELATIVE_STRENGTH_MOMENTUM_ROTATION` strategy family after completion of the
Phase 31 robustness-validation lane.

Reason:

Relative strength / intermediate-term momentum is a simple, well-known, and
portfolio-friendly independent hypothesis. It naturally supports ranked
candidate selection when the broad Research200 universe produces more signals
than the five-position portfolio can accept. This transparent strategy family
should be tested before external AI/model integrations or more threshold tuning
of S2/S3/S4.

Consequence:

- Specify S5 independently from S1/S2/S3/S4.
- Use the audited Research200 universe and standard v2 methodology.
- Make ranking and capacity-rejection diagnostics integral to S5.
- Keep first-pass variants simple and exclude RAWRS, Kronos, TradingAgents, and
  other external models.
- Use S2's retained `exclude_ret_down` run as the primary robustness benchmark;
  use S1, S3, and S4 ATR as secondary comparisons.
- Require standalone backtests and post-backtest Monte Carlo validation in later
  reviewed phases before any retain/reject/park decision.
- Make no production decision in Phase 32A.

---

## 2026-06-19 - Park S5 After First-Pass Research200 Audit

Decision:

Reject the Simple RS and Vol-Adjusted S5 variants, and park Dual Momentum as a
weak benchmark only.

Variant decisions:

- `S5_SIMPLE_RS_126D_V1`: rejected.
- `S5_DUAL_MOMENTUM_63_126D_V1`: weak / parked.
- `S5_VOL_ADJUSTED_RS_V1`: rejected.

Reason:

The Phase 32E first-pass Research200 results did not challenge S2, S1, or S3.
Simple RS and Vol-Adjusted RS were negative with weak profit factor and severe
drawdown. Dual Momentum was the only profitable S5 variant, but its edge was
thin and concentrated.

Approximate evidence:

- Simple RS: about -Rs 4.90L net PnL, about -10.08% CAGR, about 58.29% maximum
  drawdown, and about 0.819 profit factor.
- Dual Momentum: about Rs 2.01L net PnL, about 2.94% CAGR, about 29.10% maximum
  drawdown, and about 1.051 profit factor.
- Vol-Adjusted RS: about -Rs 4.19L net PnL, about -8.23% CAGR, about 51.39%
  maximum drawdown, and about 0.849 profit factor.

Consequence:

- No immediate S5 tuning.
- S2 remains the primary robustness benchmark.
- No S5 variant is production-approved.
- Do not run Monte Carlo for all S5 variants.
- Dual Momentum Monte Carlo is optional only if a later phase wants
  weak-benchmark robustness validation.
- Future work should move to a new hypothesis or materially redesigned momentum
  logic rather than small changes to these first-pass variants.

---

## 2026-06-19 - Prioritize Benchmark/Sector/Cap Context Before More Strategy Families

Decision:

Prioritize benchmark, sector, and market-cap context before major new strategy
family exploration.

Reason:

S1 through S5 comparisons are incomplete without passive broad-market,
Research200 equal-weight, cap-segment, and sector baselines. Current strategy
results may reflect stock-specific alpha, sector beta, market-cap segment beta,
broad-market exposure, risk-on/risk-off regimes, accidental concentration, cash
drag, or wrong benchmark framing.

Consequence:

- Phase 33 will build the benchmark/context foundation before major new strategy
  exploration.
- Phase 33A is docs/design only and is recorded in
  `docs/04_validation/benchmark_sector_cap_context.md`.
- Later Phase 33 work should add index metadata, index OHLC ingestion, static
  classification, benchmark/context feature utilities, S1-S5 benchmark and
  capital-utilization audits, and exposure/regime audits.
- Benchmark/context reports must label whether sector, cap, and index-membership
  classifications are point-in-time or current/static.
- Current/static classification may support first-pass diagnostics, but
  production-grade historical claims require historical membership and
  classification where possible.

---

## 2026-06-25 - Store Company Fundamentals as Separate Research Layers

Decision:

Store broader Upstox company profile and fundamentals data now for future
research convenience, but keep it in separate company fundamentals tables/layers
rather than overloading the static classification table.

Reason:

Phase 33 needs benchmark, sector, market-cap, and company context before further
strategy-family exploration. Fundamentals are useful reference data, but current
snapshot fields can create lookahead risk if used as historical signal-time
features without explicit timing controls.

Consequence:

- Company profiles, key ratios, financial statements, shareholding, corporate
  actions, and competitors are stored as separate research layers.
- The static classification CSV remains a lightweight current/static context
  file, not a general fundamentals store.
- Current key ratios are stored for research convenience but are not
  point-in-time safe for 2018 historical backtests.
- Static classification is usable for context and diagnostics only, with
  explicit current/static labeling.
- Shareholding via the current Upstox route is parked because the endpoint
  returned HTTP 404 Resource not Found.
- Competitor names are incomplete, but competitor IDs/ISINs are stored and
  uniqueness is safe.
- Financial statements are stored as raw period payload rows; normalized
  `line_item` / `value` extraction is future work.
- No strategy logic, backtesting behavior, exporters, or production decisions
  are changed by this data foundation.

---

## 2026-06-25 - Freeze Phase 33E Context Mapping as Conservative Diagnostics

Decision:

Use exact normalized-label sector proxy mapping for Phase 33E context utilities,
not broad substring matching.

Reason:

Broad matching can create incorrect sector proxies, such as mapping `Electric
Equipment` to `NIFTY_ENERGY`, `Healthcare Services` to `NIFTY_PHARMA`, or
`IT - Hardware` to `NIFTY_IT`. The context layer should prefer missing sector
relative features over false precision.

Consequence:

- Ambiguous sectors remain unmapped rather than forced into incorrect proxies.
- Sector fallback to `NIFTY_500` is opt-in and must be flagged when used.
- Research200 sector coverage is 25/68 mapped labels and 43/68 intentionally
  unmapped labels after Phase 33E.3.
- Cap context remains inactive until reliable audited cap buckets exist.
- Market/sector context utilities are approved for audit and diagnostics, not
  for strategy signals, ranking, filters, or production behavior.
- Phase 33F should apply benchmark/sector context to existing S1-S5 results
  before any strategy-family conclusions are upgraded.

---

## 2026-06-25 - Freeze S1-S5 Context Audit Interpretation Before S2 Experiments

Decision:

Treat the Phase 33F/33F.2 retained S1-S5 benchmark and sector context audit as
diagnostic evidence only. No context filter, ranking rule, strategy change, or
production approval is authorized from these findings.

Reason:

The audit showed that all retained strategies benefited from strong-positive
benchmark 20D context, but S2 remained the only retained strategy with strong
positive PnL in both negative benchmark context and strong-positive benchmark
context. S1, S3, S4, and S5 showed more visible dependence on favorable market
or sector context. These findings are useful hypotheses, but they can easily
lead to overfit filters if tested open-endedly.

Consequence:

- S2 remains the only strategy worth controlled context experiments next.
- Conservative exact-label sector mapping and no default fallback remain active.
- Missing sector context must continue to mean intentionally unmapped sector
  proxy context, not a data failure.
- Phase 33G must pre-declare S2-only context experiments, thresholds, acceptance
  criteria, and anti-overfitting guardrails before any run.
- Candidate improvements must be checked against PF, drawdown, trade count,
  yearly consistency, and rejected-trade behavior.
- Current snapshot fundamentals must not be used as historical signal filters.

---

## 2026-06-26 - Pre-Declare Controlled S2 Context Experiment Batch

Decision:

S2 is the only retained strategy entering controlled context-aware diagnostic
experiments after Phase 33F. The first experiment batch is pre-declared in
`docs/03_research/s2_context_experiment_design.md` before any implementation,
backtest, trade-context audit, or result review.

Initial batch:

- `S2_BASELINE`.
- `S2_AVOID_BENCHMARK_20D_STRONG_NEGATIVE`.
- `S2_REQUIRE_STOCK_OUTPERFORMING_BENCHMARK_20D`.
- `S2_AVOID_STOCK_STRONGLY_UNDERPERFORMING_BENCHMARK_20D`.
- `S2_AVOID_MAPPED_SECTOR_NEGATIVE_20D`.

Reason:

Phase 33F showed that S2 remains the strongest retained candidate and was
profitable even in negative benchmark context, while other retained strategies
showed weaker or more context-sensitive evidence. Context findings are useful
hypotheses, but open-ended threshold search, final-PnL optimization, and
post-result filter stacking would create high overfitting risk.

Consequence:

- The initial S2 context experiment batch is intentionally small.
- Every variant must be compared directly against the retained S2
  `exclude_ret_down` baseline.
- No combined filters, threshold grids, 5D/60D/120D alternatives, sector
  fallback filters, fundamentals ratios, market-cap buckets, S2 core logic
  changes, or post-result filter stacking are authorized in the first batch.
- No filter can be approved without strict baseline comparison, PF/drawdown/trade
  count/yearly/rejection checks, and anti-overfitting review.
- No 33G.1 result can become production-approved; allowed outcomes are
  reject, park, weak benchmark, promising diagnostic, or retain for second pass.
