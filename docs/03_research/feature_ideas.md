# Feature Ideas

## Purpose

This document records candidate research features before they are promoted into strategy implementations.

Feature ideas are not accepted trading rules. They must be tested through the normal strategy, backtest, audit, and robustness workflow.

---

## Benchmark, Sector, and Market-Cap Context Features

Phase 33A defined these as context and diagnostic candidates, not accepted
trading rules. Phase 33E through 33E.4 implemented the first reusable context
utility and audit layer for diagnostics only.

Design reference:

- `docs/04_validation/benchmark_sector_cap_context.md`

Benchmark-relative candidates:

- Stock return minus NIFTY 50 return over matched 21/63/126/252-session
  horizons.
- Stock return minus NIFTY 500 return over matched horizons.
- Stock return minus equal-weight Research200 return.
- Strategy equity return minus NIFTY and NIFTY 500 buy-and-hold return.
- Strategy equity return minus monthly equal-weight Research200 rebalance.
- Benchmark above SMA200 flag.
- Benchmark drawdown from recent high.
- Benchmark volatility and trend regime.

Sector-relative candidates:

- Stock return minus sector index return.
- Stock rank or percentile within sector.
- Sector momentum rank across sectors.
- Sector above SMA200 flag.
- Sector breadth if constituent data exists.
- Strategy PnL, accepted signals, rejected signals, and capacity rejections by
  sector.

Market-cap-relative candidates:

- Stock return minus cap-segment index return.
- Stock rank or percentile within market-cap bucket.
- Cap-segment momentum rank.
- Cap-segment above SMA200 flag.
- Smallcap versus largecap relative strength.
- Midcap versus largecap relative strength.
- Strategy PnL, accepted signals, rejected signals, and capacity rejections by
  market-cap bucket.

Regime and exposure candidates:

- Risk-on/risk-off regime using smallcap or midcap relative strength versus
  largecap.
- Sector leadership and cap-segment leadership rotation.
- Portfolio exposure by sector and market-cap bucket.
- Capital utilization and cash-drag diagnostics.
- Benchmark-relative performance by broad-market, sector, and cap-segment
  regime.

Current implementation status:

- Market-relative and sector-relative return utilities exist for diagnostics.
- Sector proxy mapping uses exact normalized labels and maps 25/68 Research200
  sector labels.
- 43/68 sector labels remain intentionally unmapped when no direct available
  proxy exists.
- Conservative sector fallback to `NIFTY_500` is opt-in and flagged.
- Cap-relative context remains inactive until audited cap buckets exist.
- No S1-S5 strategy signal, ranking, filter, or backtest behavior has been
  changed due to these features.

Tested/rejected context-filter work:

- Phase 33G/33G.1 tested the pre-declared S2 simple context-filter batch:
  `docs/03_research/s2_context_experiment_design.md`.
- Rejected: `S2_AVOID_BENCHMARK_20D_STRONG_NEGATIVE`.
- Rejected: `S2_REQUIRE_STOCK_OUTPERFORMING_BENCHMARK_20D`.
- Rejected: `S2_AVOID_STOCK_STRONGLY_UNDERPERFORMING_BENCHMARK_20D`.
- Rejected: `S2_AVOID_MAPPED_SECTOR_NEGATIVE_20D`.
- No S2 context-filter variant qualifies for second pass.
- Do not continue with threshold tweaks, alternate lookbacks, combined filters,
  or post-result stacking from these failed variants.

Tested/rejected S2 guard and state work:

- Rejected: `exclude_ret_down + 2025_guard_v1`.
- Rejected: `exclude_ret_down + 2025_guard_v1 + signal-time context`.
- Rejected: `exclude_ret_down + avoid_shallow_uptrend_pullback_v1`.
- Fragile benchmark only: `exclude_ret_down + clean_state_v1`.
- `clean_state_v1` improved final PnL and PF, but worsened drawdown to about
  33.94% and left 2025 severely negative at about -Rs 7.50L.
- The 2025 guard and context guard reduced or reframed a symptom while cutting
  too much edge versus the safer `exclude_ret_down` baseline.
- The shallow-uptrend-pullback variant raised final PnL but worsened PF,
  drawdown, and 2025/2026 quality.
- Future S2 work must address regime/state reliability more robustly, not
  direct label, month, symbol, sector, or shallow-pullback removal.

Future context work:

- Keep S1-S5 context audit findings diagnostic until controlled experiments are
  designed and reviewed.
- Keep Phase 35B/35C cross-strategy overlap findings diagnostic only. Broad
  voting and generic 2+ consensus are dropped, and S2/S4 confirmation is parked
  as an observation rather than a feature, filter, or allocation rule.
- Keep Phase 36B/36C risk diagnostics research-only. Liquidity is the strongest
  S2 risk diagnostic, benchmark regime remains strong context, drawdown state
  and gap risk remain important, and India VIX is retained only as secondary
  market context.
- Future S2 context work requires a genuinely new hypothesis, not minor
  benchmark/relative/sector threshold changes or renamed guard/state exclusions.
- Add R-multiple availability to future trade PnL logs or provide reliable join
  logic when R-bucket diagnostics are needed.
- Expand sector mapping only when a reliable sector/index proxy exists.
- Add cap bucket derivation after reliable company market-cap extraction and
  audit.
- Produce an optional full feature dump later if needed.
- Use market/sector context for rejection analysis and diagnostics first, not
  live signal filtering.

All features using sector, cap, or index-membership classification must label
whether the classification is point-in-time or current/static.

---

## Cross-Strategy Risk Diagnostic Candidates

Phase 36B/36C closed the current risk diagnostic branch without approving
implementation. Full audit:

- `docs/02_audits/cross_strategy_risk_diagnostic_audit.md`

Retained research candidates:

- Liquidity as strongest S2 diagnostic. S2 HIGH liquidity had 271 trades, about
  Rs 970,422 net PnL, about 1.42 PF, about 49.45% win rate, and about
  -Rs 948 median PnL.
- Benchmark regime as strong diagnostic context. S2 strong-positive benchmark
  had 127 trades, about Rs 660,713 net PnL and about 1.78 PF; strong-negative
  had 42 trades, about Rs 268,996 net PnL and about 2.11 PF; ordinary negative
  had 191 trades, about -Rs 94,265 net PnL and about 0.95 PF.
- Drawdown state as a cross-strategy throttle diagnostic candidate.
- Gap risk as important but mixed: S2 `STOP_GAP_HIT` had 35 trades and about
  -Rs 673,842 net PnL, while `TARGET_GAP_HIT` had 31 trades and about
  +Rs 966,904 net PnL.
- India VIX as secondary market context. It joined to 2,740 / 2,740 retained
  S1-S5 trades with 100% coverage and 0 missing/null/nonpositive joined values.
- VIX x drawdown as a future pre-registration candidate. S2 moderate drawdown +
  high VIX had 73 trades, about -Rs 80,885 net PnL, and about 0.88 PF.
- Rolling prior-trade R as promising but high overfit risk.

Anti-overfitting guardrails:

- Do not convert diagnostic buckets into filters without pre-registration.
- Do not optimize VIX thresholds after seeing outputs.
- Do not treat static liquidity as point-in-time truth.
- Do not use current/static sector or cap fields as historical controls.
- Do not create symbol include/exclude rules from contributor tables.
- Do not use rolling-R thresholds without strict pre-registration.
- Do not ignore target-gap gains when studying stop-gap losses.
- Do not use entry-date VIX close for next-open entries.

Possible future branches:

- Cross-strategy pre-registered risk experiment design.
- S2 state x risk input diagnostic design.
- Exact data-quality audit for liquidity if liquidity is elevated toward
  implementation.

No risk model, VIX rule, liquidity filter, drawdown throttle, dynamic sizing
change, or production behavior is approved by these candidates.

---

## Kronos External Model Diagnostic / Ranking Ideas

Phase 37B design reference:

- `docs/03_research/external_model_kronos_evaluation_design.md`
- `docs/03_research/external_model_kronos_sandbox_adapter_design.md`
- `docs/03_research/external_model_kronos_license_smoke_test_plan.md`
- `docs/03_research/external_model_kronos_license_verification_result.md`
- `docs/03_research/external_model_kronos_tiny_smoke_test_implementation_plan.md`
- `docs/03_research/external_model_kronos_execution_approval_checklist.md`
- `docs/03_research/external_model_kronos_smoke_test_review.md`
- `docs/03_research/external_model_kronos_small_diagnostic_experiment_design.md`
- `docs/03_research/external_model_kronos_small_diagnostic_result.md`
- `docs/03_research/external_model_kronos_reproducibility_validity_design.md`
- `docs/03_research/external_model_kronos_reproducibility_validity_result.md`
- `docs/03_research/external_model_kronos_adapter_output_validation_debug.md`
- `docs/03_research/external_model_kronos_adapter_debug_result.md`
- `docs/03_research/external_model_kronos_output_validity_policy.md`

Current status:

- Phase 37A repository discovery complete.
- Phase 37B is docs-only evaluation design.
- Phase 37C is docs-only sandbox / data adapter design.
- Phase 37D is docs-only license/model-weight verification and tiny smoke-test
  planning.
- Phase 37E records manual repo/model-card verification results; selected
  components appear clear for future internal offline diagnostic research
  planning only.
- Phase 37F is docs-only tiny smoke-test implementation planning.
- Phase 37G is docs-only user approval and exact execution checklist creation.
- Phase 37H executed one approved tiny smoke test.
- Phase 37I reviewed the smoke-test output: technical execution passed, but the
  single forecast row does not validate or reject Kronos model quality.
- Phase 37J designs a small offline diagnostic experiment only: recommended
  first diagnostic size is 5 HIGH-liquidity symbols x 6 dates = 30 forecasts.
- Phase 37K executed that approved small diagnostic.
- Phase 37L scrutinized the result and selected `REDESIGN_SMALL_DIAGNOSTIC`:
  directional accuracy was 13 / 30 = 43.33%, Spearman rank IC was -0.268521,
  top-minus-bottom spread was -0.043511, and 17 / 150 forecast path rows had
  invalid OHLC relationships.
- Phase 37M is docs-only reproducibility/output-validity design. It pauses
  broader diagnostics until invalid OHLC rows and seed/rank stability are
  tested in a separately approved small run.
- Phase 37N executed that bounded run and confirmed invalid OHLC rows remained
  high: 16 / 90 = 17.78%, affecting 8 / 18 forecast runs.
- Phase 37O is read-only adapter/output-validation debug design. It found no
  simple output-column swap, but identified missing explicit eval-mode usage in
  the Veridian helper scripts versus Kronos regression tests and found no
  built-in Kronos candle-validity guarantee or repair step.
- Phase 37P executed the approved tiny adapter debug on HDFCBANK /
  `2024-01-15`: baseline 37N-like output had 3 / 15 invalid rows, explicit
  eval had 1 / 15, and eval plus `top_k=1`, `top_p=1.0` had 0 / 15. This is an
  output-validity/API finding only and does not approve signal-quality retry.
- Phase 37Q defines the output-validity policy: explicit eval is required when
  supported, deterministic-ish decoding is the default candidate, invalid
  forecast runs are excluded from signal-quality metrics, repair is
  visualization-only unless separately approved, and close-only mode requires a
  separate label/approval.
- Phase 37R implements reusable Kronos output-validity helpers and
  synthetic-data tests only. The helpers validate OHLC rows, summarize run and
  aggregate validity, filter signal-metric-eligible diagnostics to valid runs,
  and provide visualization-only OHLC repair while preserving raw outputs.
  Phase 37R selects `PROCEED_TO_37S_POLICY_COMPLIANT_RETRY_DESIGN`; it does not
  approve Kronos inference or diagnostic retry.
- Kronos is not production-approved, not direct-strategy-approved, and not
  approved for raw predicted-candle execution.
- After the approved Phase 37K small diagnostic, Phase 37N validity diagnostic,
  and Phase 37O debug design, no
  additional installation, model download, Hugging Face download, inference,
  sandbox, training, fine-tuning, adapter implementation, dependency merge,
  strategy logic, or backtest logic is approved.

Candidate diagnostic features if a future phase approves a small isolated
diagnostic execution:

- Predicted close return over predeclared 5/10/20-session horizons.
- Predicted direction.
- Forecast strength score.
- Cross-sectional forecast rank.
- Predicted high-low range and forecast volatility proxy.
- Forecast dispersion if repeated samples are later feasible.
- Invalid OHLC rate and invalid reason counts.
- Seed-to-seed direction/rank/return stability.
- Realized forecast error by regime.
- Agreement/disagreement with retained S1-S5 trades.
- Spearman rank IC between predicted 5-session return and realized 5-session
  return.
- Top-minus-bottom forecast-rank realized return spread.

Safety rules:

- Do not buy/sell directly from generated candles.
- Do not set stops or targets directly from predicted OHLC.
- Do not treat generated candles as future truth.
- Do not choose symbols, horizons, thresholds, or overlays after seeing PnL.
- Do not fine-tune before a leakage and split audit.
- Do not merge Kronos dependencies into Veridian core.
- Do not start with a full Research200 sweep; any future diagnostic execution
  must be small, isolated, and separately approved.
- Do not scale beyond the small diagnostic while invalid OHLC rows remain
  unexplained.
- Do not run another signal-quality diagnostic until adapter/API usage and the
  output-validity policy are explicitly debugged.
- Do not treat the 37P deterministic tiny-sample zero-invalid result as enough
  evidence for Research200 or small diagnostic retry.
- Do not filter invalid outputs to create apparent alpha; invalid-run
  exclusion is an output-validity rule, not a return-improvement rule.
- Do not cherry-pick the best seed or decoding setting after results.
- Do not download model/tokenizer weights before license/model-card review and
  explicit user approval.

---

## Company Fundamentals Research Layer Ideas

Phase 33D.3 ingested Research200 company profile and fundamentals data. Phase
33D.4 audited the data as research-ready context, not as approved strategy
features.

Current audited status:

- Profiles cover 200/200 Research200 symbols.
- Key ratios cover 199/200 symbols, missing `HDFCSENSEX`.
- Financial statements cover 184/200 symbols.
- Corporate actions cover 154/200 symbols.
- Competitors cover 200/200 symbols.
- Shareholding is parked at 0 rows because the current Upstox route returned
  HTTP 404 Resource not Found.
- Static classification has 199 known sectors and one unknown sector
  (`HDFCSENSEX`), but industry, basic industry, market-cap bucket, and index
  membership remain unknown.

Future data-model and research candidates:

- Normalize financial statements into explicit `line_item` / `value` features.
- Derive `market_cap_bucket` if reliable company market-cap values can be
  extracted and audited.
- Enrich `industry` and `basic_industry` from NSE or another reliable source.
- Investigate an alternate shareholding source.
- Enrich competitor display names while preserving existing competitor keys.
- Build a fundamentals research layer with explicit point-in-time-safe feature
  engineering.
- Study corporate action and statement-period context only with event/period
  dates available at the signal timestamp.

Safety rules:

- Do not use current snapshot ratios for 2018 historical signals.
- Do not use current fundamentals ratios as historical context filters.
- Do not treat current/static profile or classification fields as historical
  point-in-time truth.
- Do not promote any fundamentals-derived ranking, filter, or signal without a
  separate implementation, backtest, audit, and robustness workflow.

---

## S5 Relative Strength / Momentum Rotation Candidate Features

`S5_RELATIVE_STRENGTH_MOMENTUM_ROTATION` is a standalone strategy family whose
first-pass Research200 feature set has been tested.

Current status:

- Phase 32A through 32F first-pass lane complete.
- First-pass feature set produced weak evidence.
- Simple RS 126D and Vol-Adjusted RS are rejected.
- Dual Momentum 63/126D is weak and parked only as a benchmark.
- Independent from S1/S2/S3/S4.
- No RAWRS, Kronos, TradingAgents, or other external-model inputs initially.
- S2 remains the primary robustness benchmark and was not challenged by S5.

Return momentum candidates:

- 63-session return.
- 126-session return.
- 252-session return.
- Skip-month momentum: 126-session anchor with the most recent 21 sessions
  excluded.

Trend and extension candidates:

- Distance above SMA200.
- Price above SMA200 flag.
- Proximity to trailing 52-week high.

Risk-adjusted momentum candidates:

- Momentum return divided by realized volatility over a compatible window.
- Cross-sectional percentile rank of volatility-adjusted momentum.
- Explicit invalid-score policy for missing or near-zero volatility.

Benchmark-relative candidates:

- Stock return minus NIFTY return over matched 63/126/252-session horizons.
- Cross-sectional rank of NIFTY-relative return.
- Use only when benchmark history is complete and timestamp-aligned.

Ranking metadata:

- Raw score.
- Cross-sectional rank and percentile.
- Eligible-universe count.
- Same-day candidate count.
- Accepted/rejected decision and reason.
- Deterministic tie-break value.

First-pass variants consumed only the features they declared:

- `S5_SIMPLE_RS_126D_V1`: rejected.
- `S5_DUAL_MOMENTUM_63_126D_V1`: weak / parked.
- `S5_VOL_ADJUSTED_RS_V1`: rejected.
- Optional later `S5_52W_HIGH_PROXIMITY_V1`

These are not accepted trading rules. The first-pass S5 momentum feature set is
tested with a weak result. Future momentum ideas should be kept only if they are
materially redesigned rather than small threshold, lookback, or weighting tweaks
to the rejected/parked variants.

---

## I1 RAWRS Market Structure Intelligence Feature Ideas

`I1_RAWRS_MARKET_STRUCTURE_INTELLIGENCE` is a reusable non-strategy intelligence layer.

RAWRS means:

- Regime-Aware Adaptive Wavelet Response Surface.

Current status:

- Phase 30A docs/spec only.
- Phase 30B implemented initial research feature utilities.
- Phase 30C defines signal-time diagnostic usage before ranking or overlays.
- Phase 30G implemented standalone diagnostics across compatible strategy
  outputs.
- Phase 30H found useful but mixed keep/avoid separation.
- Phase 30I rejected S3 spectral-concentration hard gates at p20 and p10 after
  true portfolio backtests underperformed baseline.
- Phase 30J consolidates the evidence in
  `docs/06_intelligence/i1_rawrs_combined_evidence_audit.md`.
- Not S5.
- Not a strategy.
- Not an entry model.
- Not a signal generator.
- Not a production rule.

Intended research use:

- Diagnostics on S1/S2/S3/S4 accepted trades.
- Diagnostics on rejected/capacity signals.
- Winner/loser separation analysis.
- Regime/context enrichment.
- Candidate-quality scoring research.
- Future ranking/capacity redesign input.
- Future market-regime overlay input.
- Future risk/path-quality context.

FFT / cycle feature candidates:

- Dominant frequency.
- Dominant cycle period.
- Cycle strength.
- Spectral concentration.
- Spectral entropy.
- Cycle stability over rolling windows.
- Cycle phase diagnostics, but not direct phase-based entries yet.

Wavelet feature candidates:

- Micro energy.
- Meso energy.
- Macro energy.
- Energy expansion.
- Energy compression.
- Multi-scale coherence.
- Micro/meso/macro energy ratios.
- Impulse vs drift topology.
- Local regime shift detection.

Entropy/noise feature candidates:

- Return sign entropy.
- Direction-change entropy.
- Spectral entropy.
- Wavelet entropy.
- Choppiness / noise proxy.
- Trend efficiency proxy.

Candidate topology labels:

- `clean_impulse`
- `noisy_impulse`
- `compression`
- `expansion`
- `cyclic_reversion`
- `trend_drift`
- `chaotic_chop`
- `volatility_transition`
- `regime_break`

These features and labels are research/intelligence concepts only. They are not accepted strategy rules, filters, entries, exits, or ranking rules.

Cross-strategy overlap note:

- Phase 35B found 1,654 same-symbol/same-date signal overlap events across
  S1-S5, dominated by 2-strategy consensus.
- This can inform risk-model, universe, or regime input discovery.
- It must not be treated as realized PnL or as approval for voting, weights, or
  portfolio blending.
- Future/after-entry confirmation is diagnostic only and not implementable as a
  signal-time feature.

Phase 30C diagnostic feature usage:

- Attach RAWRS features at the signal timestamp for accepted trades and rejected signals.
- Start with transparent feature buckets, quantile tables, mean/median comparisons, win rate by bucket, R-multiple by bucket, and profit factor by bucket.
- Compare feature behavior by year, weak regime, and strategy family before any threshold or composite score is considered.
- Keep usage research-only until independent validation supports ranking, overlay, or capacity research.

Initial signal-time diagnostic feature candidates:

- `rawrs_log_return`
- `rawrs_fft_spectral_concentration`
- `rawrs_fft_spectral_entropy`
- `rawrs_fft_dominant_period`
- `rawrs_micro_energy`
- `rawrs_meso_energy`
- `rawrs_macro_energy`
- `rawrs_micro_meso_energy_ratio`
- `rawrs_meso_macro_energy_ratio`
- `rawrs_direction_change_rate`

Current evidence treatment:

- Keep meso/macro energy and strategy-specific spectral/entropy features as
  diagnostic research candidates.
- `rawrs_macro_energy` remains the broadest, though often modest,
  cross-strategy diagnostic candidate.
- Do not use `rawrs_fft_spectral_concentration` as an S3 p20 or p10 hard gate.
- Do not infer hard-filter viability for S1/S2/S4 from completed-trade buckets.
- Prefer stability/significance work and capacity-aware ranking hypotheses over
  new hard filters.

---

## S4 Entropy / Volatility Compression Breakout Candidate Features

S4 is an independent strategy family that tested volatility/range/noise compression followed by upside breakout confirmation.

Current status:

- Researched through Phase 29F raw Research200 baselines.
- Frozen / parked after Phase 29G documentation.
- Not production-ready.
- Retained weak benchmark: `S4_ATR_COMPRESSION_BREAKOUT_V1`.
- Rejected raw baseline: `S4_RANGE_COMPRESSION_BREAKOUT_V1`.
- Not promoted: `S4_ENTROPY_GATED_BREAKOUT_V1`.
- No further near-term S4 feature or threshold tuning should be added without a materially new hypothesis.

Compression candidates:

- ATR percentile compression.
- Rolling high-low range compression.
- Optional entropy/noise compression.
- Return sign entropy.
- Direction-change count.
- Efficiency-ratio-style noise proxy.

Breakout confirmation candidates:

- Close above N-day high.
- Breakout close versus prior range high.
- Optional breakout-day range expansion.

Volume confirmation candidates:

- Breakout-day volume versus average volume.
- Breakout-day volume percentile.
- Volume expansion relative to compression-window volume.

Optional context candidates:

- Stock above SMA50 or SMA200.
- Nifty trend context.
- Relative strength versus Nifty.

Raw baseline variants:

- `S4_ATR_COMPRESSION_BREAKOUT_V1`
- `S4_RANGE_COMPRESSION_BREAKOUT_V1`
- `S4_ENTROPY_GATED_BREAKOUT_V1`

Raw S4 findings:

- ATR compression was weakly positive but had poor return-to-drawdown.
- Range compression was clearly negative.
- Entropy gating was near breakeven but negative and unstable.
- Capacity pressure and candidate selection remain major weaknesses.
- Current standard signal export does not expose S4-specific compression/breakout metadata fields, creating an auditability gap for future work.

These features are research candidates only. S4 is not promoted to production, and near-term S4 threshold tuning is parked.

---

## S3 Trend Pullback Continuation Candidate Features

S3 tested controlled pullbacks inside confirmed uptrends. Candidate features supported that distinction without turning the first baseline into an overfit scoring model.

Current status:

- S3 is researched and parked.
- Retained benchmark: `S3_STRONG_TREND_ABOVE_SMA50_V1`.
- Not production-ready.
- No further near-term S3 feature variants should be added without a materially new hypothesis.

Trend structure:

- SMA50.
- SMA200.
- Close vs SMA50 percentage.
- Close vs SMA200 percentage.
- SMA50 slope over 20 sessions.
- SMA200 slope over 20 sessions.

Pullback structure:

- 3d return percentage.
- 5d return percentage.
- 10d return percentage.
- Drawdown from 20d high.
- Drawdown from 60d high.
- Distance from SMA50.
- Distance from 60d low.
- Fresh 60d/120d low flags.

Volatility and breakdown risk:

- ATR14 percentage.
- ATR14 change over 5 sessions.
- Range expansion.
- Gap-down size.
- Consecutive down closes.

Market and relative-strength context:

- Nifty above SMA200.
- Nifty SMA200 slope.
- Nifty short-term return.
- Relative strength vs Nifty.
- Relative strength trend vs Nifty.

Initial S3 research used a simple transparent subset. Additional S3 features are parked for now because the standalone strategy did not produce production-quality results and further threshold tuning risks overfitting.
