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

---

## 2026-06-26 - Reject Phase 33G.1 S2 Context Filter Variants

Decision:

Reject all four pre-declared Phase 33G.1 S2 context-filter variants and retain
the original S2 `exclude_ret_down` baseline unchanged.

Rejected variants:

- `S2_AVOID_BENCHMARK_20D_STRONG_NEGATIVE`.
- `S2_REQUIRE_STOCK_OUTPERFORMING_BENCHMARK_20D`.
- `S2_AVOID_STOCK_STRONGLY_UNDERPERFORMING_BENCHMARK_20D`.
- `S2_AVOID_MAPPED_SECTOR_NEGATIVE_20D`.

Reason:

None of the simple benchmark, relative-benchmark, or mapped-sector context
filters met the pre-declared acceptance criteria. Some reduced trade count
without improving quality, some worsened drawdown or PF, and the mapped-sector
variant's slight net PnL improvement came with worse PF and sharply worse
drawdown.

Consequence:

- The retained S2 safer benchmark remains `exclude_ret_down` with no context
  filter.
- No S2 context-filter variant qualifies for second pass.
- No context filter, ranking rule, strategy change, or production approval is
  granted.
- No deeper Phase 33F trade-context audit is needed for the failed variants.
- Do not continue tuning these filters with threshold fishing, alternate
  lookbacks, combined filters, or post-result stacking.
- Future S2 improvement work requires a genuinely new hypothesis, not minor
  threshold tweaks of the rejected context filters.

---

## 2026-06-26 - Preserve Prior S2 Variant Lessons Before Any New S2 Work

Decision:

Prior S2 improvement variants do not replace the retained safer
`exclude_ret_down` baseline. Keep `exclude_ret_down + clean_state_v1` only as a
fragile higher-return benchmark, and stop simple guard, context, and
state-exclusion tuning unless a genuinely new hypothesis is defined in a
separate decision phase.

Prior variant decisions:

- `exclude_ret_down + 2025_guard_v1`: rejected.
- `exclude_ret_down + 2025_guard_v1 + signal-time context`: rejected.
- `exclude_ret_down + clean_state_v1`: retained only as a fragile higher-return
  benchmark.
- `exclude_ret_down + avoid_shallow_uptrend_pullback_v1`: rejected.

Approximate evidence:

- Retained safer baseline `exclude_ret_down`: 577 trades, about Rs 9.72L net
  PnL, about 1.189 PF, about 24.04% max drawdown, and about 45.23% win rate.
- 2025 guard: 564 trades, about Rs 5.65L net PnL, 1.133 PF, 26.87% max
  drawdown, and 45.04% win rate.
- 2025 guard with signal-time context: 561 trades, about Rs 4.78L net PnL,
  1.116 PF, 26.87% max drawdown, and 44.56% win rate.
- Clean-state higher-return candidate: 583 trades, about Rs 12.32L net PnL,
  1.223 PF, 33.94% max drawdown, and 47.68% win rate; 2025 was about -Rs
  7.50L.
- Avoid shallow uptrend pullback: 573 trades, about Rs 11.10L net PnL, 1.185
  PF, 37.42% max drawdown, and 46.07% win rate.

Reason:

Phase 34A reconstructed the failure mode from existing reports as regime/state
non-stationarity plus broad stop-churn during fragile periods. Phase 34A.0
found existing S2 failure-audit tooling and reports, so new audit code is not
currently needed. The prior S2 guard/context/state variants either destroyed
too much edge or moved risk into worse drawdown and year fragility.

Consequence:

- The safer S2 `exclude_ret_down` baseline remains retained but not
  production-approved.
- `clean_state_v1` remains useful only as a fragile higher-return comparison.
- Do not remove months, symbols, sectors, or state labels directly from these
  reports.
- Do not optimize by final PnL or treat 2025-specific failures as production
  rules.
- Do not continue threshold-tweaking the same S2 guard/context filters.
- The next S2 step must be a separate decision phase, not automatic
  implementation.

---

## 2026-06-29 - Close Phase 35B/35C Cross-Strategy Overlap Research

Decision:

Drop broad voting ensemble research and generic 2+ strategy consensus for the
current branch. Retain narrow S2/S4 confirmation only as a parked diagnostic
observation.

Reason:

Phase 35B showed weak executed-trade confirmation. S2 confirmed trades were
worse than S2 unconfirmed trades: 99 confirmed trades had about 0.893 PF and
about -Rs 1.07L net PnL, while 478 unconfirmed trades had about 1.260 PF and
about +Rs 10.79L net PnL. Generic 2+ confirmation had only 16 trades, about
0.766 PF, and about -Rs 38.5K net PnL. Same-day executed overlap was sparse,
with only 11 same-symbol/same-day rows across all strategies.

Signal overlap was larger at 1,654 same-symbol/same-date events, but that is
diagnostic evidence, not realized PnL.

Phase 35C found that S2/S4 confirmation stayed positive across 0, 1, 3, and 5
trading-session lookbacks, but the most usable 5-session result was not clean:
54 trades, about 1.23 PF, about +Rs 113.3K net PnL, about 42.6% win rate, and
about -Rs 7.66K median PnL. Yearly stability and winner concentration remained
fragile, and S3 was a competitive 5-session control.

Consequence:

- No ensemble implementation.
- No voting rule.
- No strategy weights.
- No capital allocation change.
- No production approval.
- Do not continue immediate ensemble research or another voting variant.
- Next preferred work should be Cross-Strategy Risk Model Input Discovery,
  Universe/Regime Segmentation Research, or S2 Risk Model Research.

Detailed audit:

- `docs/02_audits/cross_strategy_overlap_audit.md`

---

## 2026-06-29 - Close Phase 36B/36C Cross-Strategy Risk Diagnostics

Decision:

Close the Phase 36B/36C risk diagnostic branch as research-only diagnostics.
Do not implement a risk model, VIX rule, dynamic sizing, liquidity filter,
drawdown throttle, rolling-R threshold, benchmark-regime filter, gap filter, or
production behavior.

Reason:

Phase 36B found one or more promising risk diagnostics, but none were clean
enough for immediate implementation. Liquidity was the strongest S2 diagnostic:
S2 HIGH liquidity had 271 trades, about Rs 970,422 net PnL, about 1.42 PF,
about 49.45% win rate, and about -Rs 948 median PnL. LOW liquidity had about
-Rs 26,697 net PnL and about 0.96 PF, while MID liquidity had about Rs 27,990
net PnL and about 1.01 PF.

Benchmark regime remained strong diagnostic context for S2: strong-positive
benchmark had 127 trades, about Rs 660,713 net PnL, about 1.78 PF;
strong-negative had 42 trades, about Rs 268,996 net PnL, about 2.11 PF; and
ordinary negative had 191 trades, about -Rs 94,265 net PnL, about 0.95 PF.

Gap risk was important but mixed. S2 `STOP_GAP_HIT` had 35 trades and about
-Rs 673,842 net PnL, while `TARGET_GAP_HIT` had 31 trades and about
+Rs 966,904 net PnL.

Phase 36C.0 confirmed India VIX availability in `market_indicators` as
`INDIA_VIX` using `close`. Phase 36C.1 joined VIX to 2,740 / 2,740 retained
S1-S5 trades with 100% coverage and 0 missing/null/nonpositive joined values.
VIX was useful as secondary context but not as a standalone rule. S2 low VIX
had 210 trades, about Rs 654,183 net PnL, about 1.36 PF, and about 45.71% win
rate; mid VIX had 123 trades, about Rs 12,216 net PnL and about 1.01 PF; high
VIX had 236 trades, about Rs 358,383 net PnL and about 1.17 PF. S2 5D falling
VIX had 262 trades, about Rs 762,307 net PnL and about 1.33 PF, while 5D rising
VIX had 303 trades, about Rs 262,844 net PnL and about 1.10 PF.

VIX x drawdown is the most promising VIX interaction, but requires
pre-registration. S2 moderate drawdown + high VIX had 73 trades, about
-Rs 80,885 net PnL and about 0.88 PF. S2 mild drawdown + mid VIX had 62 trades,
about -Rs 135,157 net PnL and about 0.80 PF.

Consequence:

- Retain liquidity as the strongest S2 risk diagnostic.
- Retain benchmark regime, drawdown state, gap risk, and rolling R as research
  diagnostics.
- Retain VIX as secondary diagnostic only.
- Retain VIX x drawdown as a future pre-registration candidate.
- Do not pivot directly into S2-only implementation.
- Do not convert any diagnostic bucket into a rule without a new
  pre-registered design phase.
- Do not treat static liquidity, current/static sector, or current/static cap
  fields as point-in-time historical truth.
- Do not use entry-date VIX close for next-open entries.

Detailed audit:

- `docs/02_audits/cross_strategy_risk_diagnostic_audit.md`

---

## 2026-06-30 - Design Kronos Offline Evaluation Framework Only

Decision:

Proceed with Phase 37B as a docs-only evaluation framework for Kronos as a
future offline diagnostic, ranking, context, and confirmation layer.

Reason:

Phase 37A found Kronos feasible for offline diagnostic research, but not
approved for production use, direct strategy use, or raw predicted-candle
execution. S1-S5 are retained as benchmarks only, the Phase 35 ensemble branch
is closed, Phase 36 risk diagnostics did not approve a risk model, and internal
price-pattern/risk-filter research is showing diminishing returns. A future
external-model lane needs explicit leakage, overfitting, compute, dependency,
and license guardrails before any installation or inference.

Consequence:

- Add `docs/03_research/external_model_kronos_evaluation_design.md`.
- Do not install Kronos dependencies.
- Do not download model weights.
- Do not run inference, notebooks, web UI, training, or fine-tuning.
- Do not create a sandbox yet.
- Do not change strategy logic, backtest logic, runners, adapters, tests, or
  reports.
- Do not merge Kronos dependencies into Veridian core.
- Future next actions must be separately approved: stop/park the lane, design a
  sandbox, verify model-weight/license terms, or prepare a tiny smoke-test plan.

---

## 2026-06-30 - Design Kronos Sandbox / Data Adapter Boundaries Only

Decision:

Proceed with Phase 37C as a docs-only sandbox and data-adapter design for
possible future Kronos evaluation.

Reason:

Kronos has heavy external ML dependencies, including PyTorch and Hugging Face
tooling, and the user's laptop constraints require any future execution to be
small, isolated, optional, and separable from Veridian core. A future adapter
must define data boundaries, leakage rules, output schemas, metadata, and join
rules before any sandbox creation, installation, model download, or inference.

Consequence:

- Add `docs/03_research/external_model_kronos_sandbox_adapter_design.md`.
- Do not create a sandbox.
- Do not implement a data adapter.
- Do not install Kronos dependencies.
- Do not download model weights.
- Do not run inference, notebooks, web UI, training, or fine-tuning.
- Do not modify the Kronos repository.
- Do not change strategy logic, backtest logic, runners, tests, or reports.
- Do not merge Kronos dependencies into Veridian core.
- Future next actions must be separately approved after review of the design.

---

## 2026-06-30 - Create Kronos License and Tiny Smoke-Test Gate Plan Only

Decision:

Proceed with Phase 37D as a docs-only license/model-weight verification
checklist and tiny smoke-test plan for possible future Kronos evaluation.

Reason:

Before any installation, Hugging Face download, model-weight use, or inference,
Veridian needs explicit approval gates for model licenses, dependency isolation,
reproducibility, user-laptop safety, tiny data scope, abort criteria, and
diagnostic-only outputs.

Consequence:

- Add `docs/03_research/external_model_kronos_license_smoke_test_plan.md`.
- Do not install Kronos dependencies.
- Do not download model weights or tokenizer weights.
- Do not open network connections from scripts.
- Do not run inference, notebooks, web UI, training, or fine-tuning.
- Do not create a sandbox or implement an adapter.
- Do not modify the Kronos repository.
- Do not change strategy logic, backtest logic, runners, tests, or reports.
- Do not approve production use or direct strategy use.
- Future execution requires separate user approval for install and model
  download after the checklist is reviewed.

---

## 2026-06-30 - Record Kronos License / Model-Card Verification Result

Decision:

Record Phase 37E manual license/model-card verification results and proceed only
to tiny smoke-test implementation planning.

Reason:

The cloned Kronos repo contains an MIT license, and manual browser inspection of
`NeoQuasar/Kronos-Tokenizer-base`, `NeoQuasar/Kronos-small`, and
`NeoQuasar/Kronos-base` showed visible `mit` license fields on the selected
Hugging Face model cards. No immutable model revisions were pinned in this
phase, and this is not legal advice or production clearance.

Consequence:

- Add `docs/03_research/external_model_kronos_license_verification_result.md`.
- Repo code and selected model/tokenizer cards are treated as
  `CLEAR_FOR_INTERNAL_RESEARCH` for planning purposes only.
- Decision option: `PROCEED_TO_37F_TINY_SMOKE_TEST_IMPLEMENTATION_PLAN`.
- Do not install dependencies.
- Do not download model or tokenizer weights.
- Do not run inference, notebooks, web UI, training, or fine-tuning.
- Do not create a sandbox or implement an adapter.
- Do not modify the Kronos repository.
- Do not approve production use, redistribution, hosted serving, or direct
  strategy use.

---

## 2026-06-30 - Create Kronos Tiny Smoke-Test Implementation Plan Only

Decision:

Proceed with Phase 37F as a docs-only tiny smoke-test implementation plan.

Reason:

Phase 37E cleared the selected repo/model-card evidence for internal research
planning only. Before any execution, Veridian needs exact future boundaries for
environment isolation, model/tokenizer choice, tiny symbol/date scope, planned
future commands, output schema, reproducibility, laptop abort criteria, leakage
rules, and approval gates.

Consequence:

- Add `docs/03_research/external_model_kronos_tiny_smoke_test_implementation_plan.md`.
- Do not install dependencies.
- Do not download model or tokenizer weights.
- Do not run inference, notebooks, web UI, Qlib, AkShare, training, or
  fine-tuning.
- Do not create a sandbox or implement an adapter.
- Do not modify the Kronos repository.
- Do not change strategy logic, backtest logic, runners, tests, or reports.
- Do not approve production use, raw forecast trading, or full Research200
  inference.
- Next action should be a user approval checklist, not automatic execution.

---

## 2026-06-30 - Create Kronos Exact Execution Approval Checklist Only

Decision:

Proceed with Phase 37G as a docs-only user approval and exact execution
checklist for a possible Phase 37H tiny smoke-test execution.

Reason:

Phase 37F defined the future smoke-test implementation plan, but the user's
laptop has tight comfort constraints and no install, download, or inference has
been approved. Before any execution can be considered, Veridian needs an exact
approval block covering environment path, model/tokenizer selection, revision
pinning, symbol/date limits, output folder, abort limits, and not-approved
boundaries.

Consequence:

- Add `docs/03_research/external_model_kronos_execution_approval_checklist.md`.
- Do not install dependencies.
- Do not download model or tokenizer weights.
- Do not run inference, notebooks, web UI, Qlib, AkShare, training, or
  fine-tuning.
- Do not create a sandbox or implement an adapter.
- Do not modify the Kronos repository.
- Do not change strategy logic, backtest logic, runners, tests, or reports.
- Do not approve production use, raw forecast trading, or full Research200
  inference.
- Next action must be explicit user approval before any Phase 37H execution.

---

## 2026-06-30 - Review Kronos Tiny Smoke-Test Output Only

Decision:

Proceed with Phase 37I as a docs-only review of the Phase 37H tiny smoke-test
output. Select `PROCEED_TO_37J_SMALL_OFFLINE_DIAGNOSTIC_DESIGN`.

Reason:

Phase 37H technically passed: the isolated Kronos environment remained outside
Veridian core, `NeoQuasar/Kronos-Tokenizer-base` and `NeoQuasar/Kronos-small`
were pinned, CPU inference completed on one HDFCBANK sample, and expected
metadata, input, forecast, diagnostics, and runtime-note files were produced.
The one forecast row was directionally wrong, with `pred_close_return` about
`0.003514363982848989` versus realized forward return about
`-0.14995235826584086`, but one row is not model-quality evidence.

Consequence:

- Add `docs/03_research/external_model_kronos_smoke_test_review.md`.
- Permit Phase 37J design work only.
- Do not approve new Kronos inference.
- Do not approve full Research200 inference.
- Do not approve production use, strategy integration, raw forecast trading, or
  threshold tuning.
- Do not interpret the Phase 37H row as evidence that Kronos is good or bad.

---

## 2026-06-30 - Design Kronos Small Offline Diagnostic Experiment Only

Decision:

Proceed with Phase 37J as a docs-only small offline diagnostic experiment
design. Select `PROCEED_TO_37K_SMALL_DIAGNOSTIC_EXECUTION_APPROVAL`.

Reason:

Phase 37H/37I established technical feasibility and usable output schema, but
forecast quality remains unproven. One HDFCBANK forecast row is insufficient
evidence. The next useful step is a pre-registered diagnostic design that asks
whether `Kronos-small` outputs have weak directional, ranking, or context value
across a small sample, without treating forecasts as trades.

Consequence:

- Add `docs/03_research/external_model_kronos_small_diagnostic_experiment_design.md`.
- Recommended future 37K default: 5 HIGH-liquidity Research200 symbols x 6
  dates = 30 forecasts, 400-session lookback, 5-session horizon.
- Do not approve Phase 37K execution yet.
- Do not approve new inference, full Research200 inference, production use,
  strategy integration, raw forecast trading, threshold tuning, training, or
  fine-tuning.
- Phase 37K must begin with explicit user approval for exact symbols, dates,
  output folder, runtime limit, and no-production/no-trading boundaries.

---

## 2026-07-01 - Design Kronos Reproducibility / Output-Validity Diagnostic Only

Decision:

Proceed with Phase 37M as a docs-only stochastic reproducibility and
output-validity diagnostic design. Select
`PROCEED_TO_37N_REPRO_VALIDITY_EXECUTION_APPROVAL`.

Reason:

Phase 37K completed 30 / 30 approved `Kronos-small` CPU forecasts, but Phase
37L scrutinized weak/negative metrics and an output-validity concern:
directional accuracy was 13 / 30 = 43.33%, Spearman rank IC was -0.268521,
top-minus-bottom spread was -0.043511, top2-minus-bottom2 spread was
-0.010859, and 17 / 150 forecast path rows had invalid OHLC relationships.
Before any broader diagnostic, Research200 expansion, or strategy-adjacent use,
the lane needs a small bounded test of whether invalid rows and ranking
instability are caused by stochastic sampling, decoding settings, data mapping,
normalization/de-normalization, model behavior, or output validation.

Consequence:

- Add `docs/03_research/external_model_kronos_reproducibility_validity_design.md`.
- Future default design is at most 18 forecast runs: 2 symbols x 3 dates x 3
  seeds/settings, with 90 forecast path rows.
- Keep Phase 37M docs/design only.
- Do not approve new Kronos inference, full Research200 inference, production
  use, strategy integration, raw forecast trading, threshold tuning, training,
  fine-tuning, model download, install, or Kronos repo modification.
- Phase 37N must begin with explicit user approval for exact symbols, dates,
  seed list, decoding settings, output folder, runtime limit, and no-production
  / no-trading boundaries.

---

## 2026-07-01 - Design Kronos Adapter / Output Validation Debug Only

Decision:

Proceed with Phase 37O as read-only adapter/output-validation inspection and
debug design. Select `PROCEED_TO_37P_ADAPTER_DEBUG_EXECUTION`.

Reason:

Phase 37N confirmed that invalid OHLC rows remained high and unexplained:
16 / 90 forecast path rows = 17.777778%, affecting 8 / 18 forecast runs and
appearing across both symbols, all three dates, and all three seeds. Phase 37O
inspected the generated Veridian helper scripts, generated forecast schemas,
and local Kronos source/examples/tests without running inference. The inspection
found no simple output-column swap and no Veridian-side de-normalization step,
but it did identify a concrete adapter/API concern: the 37K/37N helper scripts
did not explicitly call `tokenizer.eval()` or `model.eval()`, while Kronos'
regression tests do. Kronos also returns decoded OHLC directly and no built-in
OHLC repair or candle-validity guarantee was found.

Consequence:

- Add `docs/03_research/external_model_kronos_adapter_output_validation_debug.md`.
- Keep Kronos blocked by output validity.
- Do not approve a small diagnostic retry.
- Do not approve full Research200 inference.
- Do not approve production use, strategy integration, raw forecast trading,
  threshold tuning, best-seed selection, decoding cherry-picking, training,
  fine-tuning, model download, install, or Kronos repo modification.
- A future Phase 37P must receive explicit approval for whether execution is
  allowed, exact files/scripts that may be edited, whether any new inference or
  output-validation-only rerun is allowed, symbols/dates/seeds/settings,
  runtime cap, and no-production/no-trading boundaries.

---

## 2026-07-01 - Execute Kronos Adapter Debug Only

Decision:

Record Phase 37P as the approved bounded adapter/output-validation debug
execution. Select `PROCEED_TO_37Q_OUTPUT_VALIDITY_POLICY_DESIGN`.

Reason:

Phase 37P ran only the approved HDFCBANK / `2024-01-15` sample with 400-session
lookback, 5-session horizon, three seeds, and three predeclared configurations.
The 37N-like baseline produced 3 / 15 invalid OHLC rows = 20.000000%.
Explicit eval mode reduced invalid rows to 1 / 15 = 6.666667%.
Eval plus deterministic-ish `top_k=1`, `top_p=1.0` produced 0 / 15 invalid
rows in this tiny sample. This shows API/decoding settings matter, but it does
not prove output validity is solved across symbols/dates/seeds.

Consequence:

- Add `docs/03_research/external_model_kronos_adapter_debug_result.md`.
- Keep generated outputs ignored under
  `reports/v2/external_models/kronos/adapter_debug_20260701/`.
- Proceed to output-validity policy design before any diagnostic retry.
- Do not approve full Research200 inference, small diagnostic retry, production
  use, strategy integration, raw forecast trading, threshold tuning,
  best-seed/decoding cherry-picking, training, fine-tuning, model download,
  install, or Kronos repo modification.

---

## 2026-07-01 - Design Kronos Output Validity Policy Only

Decision:

Proceed with Phase 37Q as docs-only output-validity policy design. Select
`PROCEED_TO_37R_OUTPUT_VALIDITY_POLICY_IMPLEMENTATION`.

Reason:

Phase 37K, 37N, and 37P showed invalid OHLC output is a structural gate before
any further Kronos diagnostics. Phase 37P improved invalid rows from 3 / 15 in
the 37N-like baseline to 1 / 15 with explicit eval and 0 / 15 with eval plus
`top_k=1`, `top_p=1.0`, but the sample was only HDFCBANK on `2024-01-15`.
Policy must be pre-registered before retry so decoding, invalid-run exclusion,
repair/coercion, close-only mode, and failure thresholds cannot be chosen after
seeing signal metrics.

Consequence:

- Add `docs/03_research/external_model_kronos_output_validity_policy.md`.
- Require future helpers to call `.eval()` when supported, record eval status,
  and use deterministic-ish decoding as the default candidate unless a later
  design changes it.
- Mark any forecast run with invalid OHLC as `INVALID_OUTPUT` and exclude it
  from signal-quality metrics by default.
- Keep repair visualization-only unless separately approved.
- Do not approve new inference, small diagnostic retry, full Research200,
  production use, strategy integration, raw forecast trading, threshold tuning,
  best-seed/decoding cherry-picking, training, fine-tuning, model download,
  install, or Kronos repo modification.

## 2026-07-01 - Implement Kronos Output Validity Policy Helpers Only

Decision:

Proceed with Phase 37R as implementation-only reusable output-validity policy
helpers. Select `PROCEED_TO_37S_POLICY_COMPLIANT_RETRY_DESIGN`.

Reason:

Phase 37Q defined the policy, but it existed only in documentation. Future
Kronos diagnostics need tracked helper behavior for OHLC validity, invalid-run
exclusion, aggregate fail/warn/pass thresholds, and visualization-only repair
before any retry can be designed.

Consequence:

- Add `src/veridian_quant/v2/external_models/kronos/output_validity.py`.
- Add `tests/v2/test_kronos_output_validity.py`.
- Validate forecast-path OHLC rows without mutating caller data.
- Mark any forecast run with invalid OHLC as `INVALID_OUTPUT`.
- Exclude invalid runs from signal-metric-eligible diagnostics by default.
- Provide visualization-only repair fields while preserving raw forecast
  columns.
- Keep 37R policy/helper only: no Kronos inference, model loading, report
  generation, backtest, strategy logic change, dependency installation,
  cloned-repo modification, production use, or direct predicted-candle trading.

---

## 2026-07-01 - Design Kronos Policy-Compliant Retry Only

Decision:

Proceed with Phase 37S as docs-only policy-compliant small diagnostic retry
design. Select `PROCEED_TO_37T_POLICY_COMPLIANT_RETRY_APPROVAL`.

Reason:

Phase 37K had 17 / 150 invalid OHLC rows = 11.33%. Phase 37N had 16 / 90
invalid OHLC rows = 17.78%, affecting 8 / 18 forecast runs = 44.44%. Phase
37P showed that explicit eval and deterministic-ish `top_k=1`, `top_p=1.0`
decoding eliminated invalid rows only in a tiny HDFCBANK / `2024-01-15`
sample. Phase 37R then implemented reusable output-validity helpers with 22
focused tests passing. A retry can be designed only if it uses explicit eval,
deterministic-ish decoding, and 37R validity gating.

Consequence:

- Add
  `docs/03_research/external_model_kronos_policy_compliant_retry_design.md`.
- Recommended future retry: same 37K structure, 5 symbols x 6 dates = 30
  forecast runs, horizon 5, lookback 400, using the same symbols/dates unless
  preflight fails.
- Future retry metrics are computed only on valid forecast runs; invalid runs
  remain preserved in output-validity summaries.
- Direct comparison to 37K must be caveated because decoding policy changes.
- Phase 37T must be an explicit approval gate before execution.
- Do not approve inference, full Research200, `Kronos-base`, production use,
  strategy integration, raw predicted-candle trading, threshold tuning,
  best-seed/decoding cherry-picking, training, fine-tuning, generated report
  commits, or cloned Kronos repo modification.

---

## 2026-07-01 - Execute Kronos Policy-Compliant Retry Only

Decision:

Record Phase 37T as the approved bounded policy-compliant `Kronos-small` retry
execution. Select `PROCEED_TO_37U_POLICY_RETRY_RESULT_SCRUTINY`.

Reason:

The approved 37T retry completed 30 / 30 forecasts using explicit eval,
deterministic-ish decoding (`top_k=1`, `top_p=1.0`), seed `42`, and the 37R
output-validity helper. Output validity failed under the 37Q policy: 3 / 30
forecast runs were invalid = 10.00%, and 4 / 150 path rows were invalid =
2.666667%. The invalid forecast-run rate exceeded the 5% failure threshold.
Validity-gated signal metrics on 27 valid runs remained weak/negative:
directional accuracy was 11 / 27 = 40.740741%, Spearman rank IC was
-0.199634, top1-minus-bottom1 spread was -0.039897, and top2-minus-bottom2
spread was -0.013160.

Consequence:

- Add
  `docs/03_research/external_model_kronos_policy_compliant_retry_result.md`.
- Keep generated outputs ignored under
  `reports/v2/external_models/kronos/policy_retry_20260701/`.
- Preserve invalid forecast runs in validity summaries and exclude them from
  signal metrics.
- Do not claim direct improvement versus 37K without caveating the changed
  eval/decoding policy.
- Do not proceed to a larger diagnostic before 37U scrutiny.
- Do not approve full Research200, `Kronos-base`, production use, strategy
  integration, raw predicted-candle trading, threshold tuning, best-seed or
  best-decoding selection, training, fine-tuning, generated report commits, or
  cloned Kronos repo modification.

---

## 2026-07-01 - Close Out Kronos Lane With Bi-Monthly Upstream Review

Decision:

Close the Kronos external-model lane for now with
`DOCS_ONLY_CLOSEOUT_AND_BIMONTHLY_REVIEW`.

Reason:

Internal diagnostics failed both output-validity and signal-quality gates.
Phase 37K had 17 / 150 invalid OHLC rows = 11.33%. Phase 37N had 16 / 90
invalid OHLC rows = 17.78%, affecting 8 / 18 forecast runs. Phase 37T still
failed the 37Q policy under eval plus deterministic-ish decoding: 3 / 30
forecast runs were invalid = 10.00%, 4 / 150 path rows were invalid =
2.666667%, and output validity status was `OUTPUT_VALIDITY_FAILED`.
Validity-gated signal metrics remained weak/negative: 11 / 27 directional
accuracy = 40.740741%, rank IC = -0.199634, top1 spread = -0.039897, and top2
spread = -0.013160.

Phase 37V public evidence review found no direct public invalid-OHLC issue, no
maintainer-confirmed fix, no official OHLC guarantee, no official repair
guidance, and no confirmed workaround. Broader public generation-quality /
reproducibility concerns exist, including #229 implausible generated data, #319
A-share MAPE/quality concern, #156 long-horizon concern, and #184 CPU/GPU
output mismatch.

Consequence:

- Add `docs/03_research/external_model_kronos_closeout.md`.
- Close the lane for now; do not continue local inference.
- Do not patch local Kronos now.
- Do not use Kronos in strategy logic.
- Do not scale to Research200.
- Do not use raw predicted candles.
- Review upstream Kronos repo/issues/model cards every two months for maturity,
  fixes, output-validity/reproducibility improvement, CPU/GPU mismatch
  clarification, model/tokenizer revisions, and prediction-quality evidence.
- Reopen only after concrete upstream improvement or explicit user approval for
  a new design such as upstream fix validation, close-only diagnostic,
  patched-Kronos experiment, or new model revision smoke test.

---

## 2026-07-05 - Design S2 State x Risk and In-Trade State Evolution Diagnostics Only

Decision:

Proceed with Phase 36D as docs-only S2 diagnostic design. Select
`PROCEED_TO_36E_STATE_METADATA_DISCOVERY`.

Reason:

S2's retained safer `exclude_ret_down` benchmark remains the strongest retained
internal strategy, with about Rs 9.72L net PnL, about 1.189 PF, about 24.04%
max drawdown, 577 trades, and about 45.23% win rate. It remains fragile,
especially in 2024, 2025, and partial 2026, and Phase 34 found regime/state
non-stationarity plus stop churn as the core failure mode.

Phase 36B/36C identified useful risk diagnostics, especially liquidity, plus
benchmark regime, drawdown state, gap risk, rolling R, and VIX as secondary
context. The missing question is whether S2 state behavior explains trade
quality at entry and during the holding period.

Consequence:

- Add `docs/03_research/s2_state_risk_intrade_diagnostic_design.md`.
- Define Lane A: Entry-State x Risk Input Diagnostic.
- Define Lane B: In-Trade State Evolution Diagnostic.
- Require Phase 36E discovery before any implementation to verify S2 state
  metadata, daily state reconstruction, trade-id alignment, next-open
  hypothetical exit feasibility, pre-start lookback, and risk-context joins.
- Keep all future claims numeric and sample-size labeled.
- Do not approve a dynamic exit rule.
- Do not approve an `exit if RET_DOWN` rule.
- Do not approve a new entry filter, state exclusion, liquidity filter,
  drawdown/VIX/benchmark rule, risk sizing change, backtest optimization,
  production use, or strategy promotion.

---

## 2026-07-05 - Discover S2 State Metadata and In-Trade Reconstruction Feasibility Only

Decision:

Proceed with Phase 36E as discovery-only S2 state metadata / in-trade
reconstruction review. Select
`PROCEED_TO_36F_STATE_RECONSTRUCTION_PROTOTYPE_DESIGN`.

Reason:

Phase 36E found that S2 entry-state metadata already exists in retained
`signal_log.csv` and `trade_signal_context.csv` artifacts, including
`state_label`, `state_observation_count`, `positive_transition_probability`,
`average_forward_return_pct`, and `median_forward_return_pct`. Existing helpers
can parse composite `RET_*|VOL_*|DD_*|LOW_*` labels into components. Trade,
PnL, and trade-context artifacts share `trade_id`.

Daily in-trade state paths are not stored. Lane B therefore requires read-only
daily state reconstruction from OHLC using the existing S2 `build_state_frame`
logic, with explicit controls for pre-start lookback, next-session-open
hypothetical execution, and same-day realized stop/target handling.

Consequence:

- Add
  `docs/03_research/s2_state_metadata_intrade_reconstruction_discovery.md`.
- Classify Lane A Entry-State x Risk as `READY_WITH_MINOR_GAPS`.
- Classify Lane B In-Trade State Evolution as
  `NEEDS_DAILY_STATE_RECONSTRUCTION`.
- Design a reconstruction prototype before any audit helper.
- Do not implement a diagnostic helper.
- Do not run a backtest.
- Do not generate reports.
- Do not approve a dynamic exit or `exit if RET_DOWN` rule.
- Do not approve a new entry filter, state exclusion, liquidity filter,
  drawdown/VIX/benchmark rule, risk sizing change, backtest optimization,
  production use, or strategy promotion.

---

## 2026-07-05 - Design S2 Daily State Reconstruction Prototype Only

Decision:

Proceed with Phase 36F as docs-only S2 daily state reconstruction prototype
design. Select
`PROCEED_TO_36G_STATE_RECONSTRUCTION_PROTOTYPE_IMPLEMENTATION`.

Reason:

Phase 36E found that Lane B cannot use stored daily in-trade state paths because
they do not exist in retained reports. Daily reconstruction appears feasible
from OHLC using the existing `build_state_frame` logic, but implementation must
first define exact date alignment, holding-period expansion, same-day
stop/target safety, and next-open hypothetical-exit feasibility.

Consequence:

- Add `docs/03_research/s2_daily_state_reconstruction_prototype_design.md`.
- Future prototype should reconstruct one S2 state row per symbol/date, expand
  accepted S2 trades into holding-period rows, and join state by symbol/date.
- Date-D state is known only after D close; hypothetical deterioration exits
  must execute at next valid session open.
- If the actual trade exits intraday on D, D-close state is not actionable.
- Future prototype must validate reconstructed entry-state match rate against
  stored state metadata before any full audit helper.
- Do not implement prototype code in Phase 36F.
- Do not implement a full Lane A/B audit helper.
- Do not run backtests or generate reports.
- Do not approve a dynamic exit, `exit if RET_DOWN`, entry filter, state
  exclusion, liquidity filter, drawdown/VIX/benchmark rule, risk sizing change,
  backtest optimization, production use, or strategy promotion.
