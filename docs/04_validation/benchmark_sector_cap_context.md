# Benchmark, Sector, and Market-Cap Context Design

## 1. Purpose

This Phase 33A document designs a benchmark, sector, and market-cap context
layer for Veridian Quant v2.

The purpose is to make future strategy evaluation answer a deeper question than
"did this strategy make money?":

- Did it beat a passive broad-market baseline?
- Did it beat the relevant sector or market-cap segment?
- Was return driven by stock-specific alpha, sector beta, cap-segment beta, or
  broad-market exposure?
- Was performance concentrated in one sector, one market-cap bucket, or one
  risk-on regime?
- Did weak CAGR come from poor signal quality or from cash drag and
  underinvestment?

Phase 33A is documentation only. It does not implement ingestion, schema
changes, feature utilities, reporting, backtests, or strategy behavior.

## 2. Scope

The design covers:

- Index OHLCV / close history for broad, sector, and market-cap segment
  benchmarks.
- Static and later point-in-time stock classification.
- Market-cap bucket and index-membership context.
- Benchmark-relative, sector-relative, and cap-relative research features.
- Regime, exposure, concentration, and capital-utilization diagnostics.
- Future audit integration for S1 through S5 and later strategy families.
- Survivorship-bias and data-quality guardrails.

Initial use is diagnostic and validation-oriented. This layer should enrich
research context before it becomes a strategy input.

## 3. Non-goals

This design does not authorize:

- Buy or sell signals.
- Strategy filters, overlays, ranking rules, or production behavior.
- Changes to S1, S2, S3, S4, S5, RAWRS, or future strategy runners.
- Backtest reruns or report generation.
- Exporter changes.
- Config or data modifications.
- Production claims based on current/static classifications.
- Treating benchmark-relative diagnostics as proof of alpha by themselves.

## 4. Why Benchmark/Sector/Cap Context Is Needed

S1 through S5 have mostly been compared against each other. That is useful but
incomplete. A long-only Indian equity strategy can look attractive if the
underlying universe, sector, or market-cap segment is rising strongly.

Veridian needs to know whether a strategy produced:

- Stock-specific alpha beyond passive exposure.
- Sector beta, such as riding banks, IT, metals, or realty during a strong
  sector phase.
- Market-cap segment beta, such as smallcap or midcap risk-on exposure.
- Broad-market beta, such as NIFTY or NIFTY 500 exposure.
- Concentration disguised as strategy edge.
- Low CAGR because too much capital remained in cash.

This is especially important after Phase 31 and Phase 32:

- S2 is the strongest current benchmark by return and Monte Carlo robustness,
  but remains regime-fragile and not production-ready.
- S1 is useful but not production-ready.
- S3 is weak/moderate.
- S4 ATR is weak; other S4 variants are rejected or parked.
- S5 first-pass momentum did not challenge S2/S1/S3.
- RAWRS remains diagnostic-only.
- No strategy is production-approved.

Before adding more strategy families, Veridian needs passive, sector, cap, and
capital-utilization context.

## 5. Problems in Current Evaluation

Current evaluation has several known gaps:

- Strategy comparisons are mostly strategy-versus-strategy, not
  strategy-versus-passive benchmark.
- NIFTY context exists in places, but broad, cap-segment, and sector context is
  not yet a common validation layer.
- Research200 equal-weight baselines are not yet standard comparison outputs.
- Sector and market-cap concentration are not consistently measured.
- Current classifications may be available, but point-in-time classifications
  are not yet modeled.
- Current index membership can introduce survivorship bias if used historically.
- Rejected/capacity diagnostics do not yet show whether missed opportunities
  cluster by sector or cap bucket.
- Weak CAGR is hard to interpret without capital-utilization and benchmark
  opportunity context.
- Risk-on/risk-off regimes are not yet tied to smallcap/midcap versus largecap
  relative strength.

## 6. Data Types Required

### Index OHLCV / Close History

Required broad and cap-segment indices:

- NIFTY 50.
- NIFTY 500.
- NIFTY Midcap 150.
- NIFTY Smallcap 250.

Required sector indices where available:

- NIFTY Bank.
- NIFTY IT.
- NIFTY Auto.
- NIFTY Pharma.
- NIFTY FMCG.
- NIFTY Metal.
- NIFTY Energy.
- NIFTY Realty.
- Other sector indices as available.

Minimum required fields:

- index symbol.
- date.
- open, high, low, close.
- volume when available, nullable when not available.
- source.
- ingestion timestamp.

### Stock Classification

Required classification fields:

- symbol.
- sector.
- industry.
- market-cap bucket.
- index membership.
- effective_from.
- effective_to.
- source.
- confidence/status.
- notes where needed.

### Optional Later Data

Optional later data should include:

- Free-float market cap.
- Full market cap.
- Sector index weights.
- Historical index constituents.
- Delisted, demoted, or removed symbols where available.
- Point-in-time sector and industry classification changes.

## 7. Benchmark/Index OHLC Design

Index price history should be treated as first-class market data rather than as
ad hoc CSV context.

Design requirements:

- Store index metadata separately from index bars.
- Support broad, sector, cap-segment, and thematic index types.
- Preserve source and ingestion timestamp.
- Keep close-only support possible, but prefer OHLCV where available.
- Use only values available at the signal timestamp for features.
- Align index sessions to stock trading sessions.
- Detect missing index sessions before feature generation.
- Avoid mixing adjusted and unadjusted index series without explicit labels.

Index bars should support:

- Buy-and-hold benchmark returns.
- Trailing benchmark returns.
- SMA and trend features.
- Relative-strength calculations.
- Risk-on/risk-off diagnostics.
- Sector and cap-segment regime labels.

## 8. Sector Classification Design

Each traded stock should map to a sector and, where available, an industry.

Initial static classification is acceptable for diagnostics if labeled clearly.
Production-grade historical claims require point-in-time classification where
possible.

Classification design rules:

- Every classification row should have `effective_from` and `effective_to`.
- Static/current classification may use a broad effective range, but reports
  must label it as current/static.
- Unknown sector should be explicit, not inferred silently.
- Changes in sector/industry mapping should be representable as new effective
  rows.
- The classification source and confidence/status must be recorded.

Sector classification supports:

- Strategy PnL by sector.
- Accepted/rejected/capacity signal counts by sector.
- Sector-relative feature construction.
- Sector concentration limits or diagnostics in future phases.
- Sector benchmark comparison.

## 9. Market-Cap Bucket Design

Market-cap bucket context should initially use practical buckets:

- largecap.
- midcap.
- smallcap.
- microcap or other, if the universe later expands.
- unknown.

The first implementation can map buckets from current classification or index
membership, but every report must disclose whether buckets are point-in-time or
static/current.

Cap buckets support:

- PnL and drawdown by cap segment.
- Signal quality by cap segment.
- Capacity rejections by cap segment.
- Comparison against NIFTY 50, Midcap 150, and Smallcap 250.
- Risk-on/risk-off regime detection.
- Understanding whether Research200 returns are mostly smallcap/midcap beta.

## 10. Index Membership Design

Index membership should be represented independently from sector and market-cap
bucket because a stock may belong to multiple indices.

Initial classification may store a simple `index_membership` field for
diagnostics. A later normalized table should support many-to-many membership
through time.

Design requirements:

- Store index symbol and member symbol.
- Store effective date ranges.
- Allow nullable constituent weights.
- Preserve source.
- Support current/static membership as a clearly labeled fallback.
- Support historical membership where available.

Index membership enables:

- NIFTY 500 / sector / cap-segment constituent analysis.
- Equal-weight benchmark construction.
- Sector breadth if constituent data exists.
- Historical universe and survivorship-bias controls.

## 11. Survivorship-Bias Risk

Survivorship bias is a central risk for this layer.

Required warnings:

- Using today's Research200 membership for historical backtests can bias
  results.
- Using today's index membership for historical index-relative diagnostics can
  bias results.
- Using today's sector or market-cap classification historically can mislabel
  older periods if companies changed business mix, sector classification, or
  market-cap segment.
- First-pass context may use current/static classifications for diagnostics,
  but production-grade claims require historical membership and
  classification where possible.
- All benchmark/context reports must label classification as either
  point-in-time or current/static.
- Current/static classification is acceptable for exploratory diagnosis, not for
  final claims of historical alpha.

This warning applies to strategy backtests, benchmark baselines, exposure
reports, rejected-signal diagnostics, and future Kronos/TradingAgents
evaluation.

## 12. Suggested Database/Schema Design

### `market_indices`

Suggested fields:

- `index_id`.
- `index_symbol`.
- `index_name`.
- `index_type`: `broad`, `sector`, `cap_segment`, or `thematic`.
- `source`.
- `active`.

Purpose:

- Register benchmark and context indices once.
- Avoid hard-coded index lists in feature utilities.
- Allow inactive or replaced indices to remain auditable.

### `market_index_bars`

Suggested fields:

- `index_symbol`.
- `date`.
- `open`.
- `high`.
- `low`.
- `close`.
- `volume`, nullable.
- `source`.
- `ingested_at`.

Suggested constraints:

- Unique key on `index_symbol` and `date`.
- Non-null date and close.
- OHLC validity checks when OHLC is available.
- Source recorded for every row.

### `instrument_classification`

Suggested fields:

- `symbol`.
- `sector`.
- `industry`.
- `market_cap_bucket`.
- `index_membership`.
- `effective_from`.
- `effective_to`.
- `source`.
- `confidence_status`.
- `notes`.

Suggested constraints:

- No overlapping effective ranges for the same symbol and classification source
  unless explicitly allowed.
- Explicit `unknown` or null handling for unavailable sector, industry, or cap
  bucket.
- Source and date range required.

### Optional Later: `index_constituents`

Suggested fields:

- `index_symbol`.
- `symbol`.
- `effective_from`.
- `effective_to`.
- `weight`, nullable.
- `source`.

Purpose:

- Point-in-time index membership.
- Equal-weight or cap-weight proxy benchmark construction.
- Sector breadth and constituent-level diagnostics.

## 13. Suggested Ingestion Sources

Possible ingestion sources should be evaluated for legality, stability,
completeness, and point-in-time availability before use.

Candidate source categories:

- NSE index historical data pages or files.
- NSE index constituent files.
- Official NIFTY / NSE index methodology and constituent disclosures.
- Vendor-provided Indian equity metadata.
- Existing project price database for stock OHLCV.
- Manual seed files only as a temporary bootstrap, with source and date labels.

Source selection requirements:

- Record source name and retrieval method.
- Record ingestion timestamp.
- Preserve raw source files where the project later decides to store data.
- Validate symbol naming and date alignment.
- Label whether data is adjusted, unadjusted, close-only, OHLC, or total-return.
- Avoid undocumented scraping dependencies in production-grade workflows.

## 14. Benchmark-Return Features

Candidate benchmark-relative features:

- Stock return minus NIFTY 50 return over matched horizons.
- Stock return minus NIFTY 500 return over matched horizons.
- Stock return minus Research200 equal-weight return over matched horizons.
- Strategy equity return minus NIFTY buy-and-hold return.
- Strategy equity return minus NIFTY 500 buy-and-hold return.
- Trailing benchmark momentum rank.
- Benchmark above SMA200 flag.
- Benchmark drawdown from recent high.
- Benchmark volatility and realized return regime.

Benchmark baselines to design:

- NIFTY buy-and-hold.
- NIFTY 500 buy-and-hold.
- Equal-weight Research200 buy-and-hold.
- Monthly equal-weight Research200 rebalance.
- Cap-bucket benchmark comparison.
- Sector benchmark comparison.
- Simple top-N momentum allocation baseline later if desired.

## 15. Sector-Relative Features

Candidate sector-relative features:

- Stock return minus sector index return.
- Stock momentum rank within sector.
- Sector momentum rank across sectors.
- Sector above SMA200 flag.
- Sector drawdown from recent high.
- Sector realized volatility.
- Sector breadth if constituent data exists.
- Stock relative strength percentile within sector.
- Accepted/rejected signal quality by sector.

These features should initially be diagnostic. Any later use in ranking or
filtering requires a separate strategy design and leakage-safe implementation.

## 16. Market-Cap-Relative Features

Candidate market-cap-relative features:

- Stock return minus cap-segment index return.
- Stock rank within cap bucket.
- Cap-segment momentum rank.
- Cap-segment above SMA200 flag.
- Cap-segment drawdown and volatility.
- Smallcap versus largecap relative strength.
- Midcap versus largecap relative strength.
- Strategy PnL by cap bucket.
- Accepted, rejected, and capacity-rejected signals by cap bucket.

These diagnostics help identify whether a strategy is truly selecting stocks or
mainly expressing smallcap/midcap beta.

## 17. Regime Diagnostics

Benchmark, sector, and cap data should support regime diagnostics such as:

- Broad-market trend: NIFTY 50 or NIFTY 500 above/below SMA200.
- Broad-market return regime over 21, 63, 126, and 252 sessions.
- Sector risk-on/risk-off conditions.
- Smallcap versus largecap relative-strength regime.
- Midcap versus largecap relative-strength regime.
- Sector leadership rotation.
- High-volatility versus low-volatility benchmark states.
- Strategy return by broad-market, sector, and cap-segment regime.

Risk-on/risk-off candidates:

- NIFTY Smallcap 250 return minus NIFTY 50 return.
- NIFTY Midcap 150 return minus NIFTY 50 return.
- Smallcap and midcap indices above/below SMA200.
- Breadth within cap segments if historical constituent data exists.

## 18. Portfolio Exposure Diagnostics

Future benchmark/context audits should measure:

- PnL by sector.
- PnL by market-cap bucket.
- Gross and net exposure by sector/cap bucket over time.
- Accepted trades by sector/cap bucket.
- Rejected signals by sector/cap bucket.
- Capacity rejections by sector/cap bucket.
- Active-position concentration by sector/cap bucket.
- Top sector and top cap-bucket contribution to PnL.
- Time invested versus time in cash.
- Average capital utilization.
- Cash drag versus benchmark opportunity.
- Whether losing years coincide with weak broad, sector, or cap regimes.

This is critical for distinguishing true lack of alpha from low capital
deployment or wrong benchmark framing.

## 19. Strategy-Audit Integration

Future strategy audits should include benchmark/context evidence after the
required data layer exists.

Suggested audit additions:

- Compare strategy equity against NIFTY and NIFTY 500 buy-and-hold.
- Compare against equal-weight Research200 buy-and-hold.
- Compare against monthly equal-weight Research200 rebalance.
- Compare against relevant sector and cap-segment benchmarks.
- Report classification mode: point-in-time or current/static.
- Report PnL, drawdown, trade count, signals, and capacity rejections by sector.
- Report PnL, drawdown, trade count, signals, and capacity rejections by
  market-cap bucket.
- Report capital utilization and cash drag.
- Report whether strategy performance clusters in smallcap/midcap risk-on
  regimes.
- State whether benchmark-relative evidence changes retain/reject/park
  interpretation.

This applies to S1 through S5, RAWRS diagnostics where relevant, and later
external-model outputs.

## 20. Data Quality Checks

Required checks for index bars:

- Duplicate index/date rows.
- Missing dates relative to expected market sessions.
- Non-finite OHLC values.
- Negative or impossible prices.
- High below low.
- Open/high/low/close inconsistencies.
- Large one-day moves requiring source confirmation.
- Stale close values across many sessions.
- Volume missingness, where volume is expected.
- Source and ingestion timestamp present.

Required checks for classification:

- Unknown or missing sector/cap bucket counts.
- Duplicate symbol rows with overlapping effective ranges.
- Invalid effective date ranges.
- Symbols in strategy outputs without classification.
- Classifications with missing source.
- Ambiguous or many-to-one symbol aliases.
- Index membership that conflicts with declared cap bucket.
- Static/current classification used without report label.

Required feature checks:

- Matched stock/index date alignment.
- Sufficient lookback history.
- No future benchmark values in signal-time features.
- Explicit missing-benchmark behavior.
- Consistent return horizon definitions.
- No silent row drops.

## 21. Phase Implementation Plan

- **Phase 33A - Design:** docs-only specification for benchmark, sector, and
  market-cap context. No code, tests, reports, config, data, or backtests.
- **Phase 33B - Index metadata and schema/data contracts:** define index
  registry, bar contracts, classification contracts, validation expectations,
  and migration plan if needed.
- **Phase 33C - Index OHLC ingestion:** ingest broad, sector, and cap-segment
  index histories under the approved data contract.
- **Phase 33D - Static stock sector/cap classification and company
  fundamentals ingestion:** add current/static classification for Research200
  diagnostics with explicit static labels, and store Upstox company profile and
  fundamentals data in separate research layers. Phase 33D.3 ingestion and
  Phase 33D.4 audit are complete; status is documented in
  `docs/02_audits/company_fundamentals_audit.md`.
- **Phase 33E - Benchmark/context feature utilities:** complete. Reusable
  market-relative, sector-relative, and cap-relative context utilities exist
  with no-lookahead return windows, inner stock/index date alignment, no forward
  fill, explicit unmapped/fallback flags, and inactive cap context when audited
  cap buckets are unavailable.
- **Phase 33E.2 - Real-data context audit/export:** complete. The Research200
  audit runner processed 200/200 symbols against `NIFTY_500` from 2020-01-01
  through 2026-04-30 with 0 missing stock OHLC rows and 0 missing index data
  counts.
- **Phase 33E.3 - Sector proxy mapping refinement:** complete. Sector proxy
  resolution now uses exact normalized-label mapping, not broad substring
  matching. Coverage improved from 17/68 to 25/68 mapped sector labels, with
  43/68 labels intentionally unmapped and `fallback_count = 0` under the
  conservative default.
- **Phase 33E.4 - Documentation/status freeze:** complete. Documents the Phase
  33E context layer without changing strategy logic or promoting signals.
- **Phase 33F - Apply benchmark/sector context audit to S1-S5 results:**
  complete. Read-only trade context audit utilities annotate existing trade PnL
  logs with benchmark/sector context.
- **Phase 33F.2 - Retained S1-S5 trade context audit:** complete. Retained
  S1-S5 `trade_pnl_log.csv` files were audited with no sector fallback.
- **Phase 33F.3 - S1-S5 context audit documentation:** complete. Interpretation
  is frozen in `docs/02_audits/s1_s5_context_audit.md`.
- **Phase 33G - S2 controlled context experiment design:** complete. The
  pre-declared S2-only context experiment batch and acceptance criteria are
  documented in `docs/03_research/s2_context_experiment_design.md`.
- **Phase 33G.1 - Pre-declared S2 context experiment run:** implement/run only
  the fixed Phase 33G batch, compare every variant against the retained S2
  baseline, and run post-backtest context audit only where basic metrics pass.
- **Later - Historical constituents / point-in-time classification:** replace
  or supplement static classification for production-grade historical claims.

## 22. Phase 33E Completion Status

Phase 33E through 33E.3 moved this document's design into reusable diagnostic
infrastructure while preserving the original non-goals.

Implemented context utilities:

- `src/veridian_quant/v2/features/market_context.py`
- `src/veridian_quant/v2/data/sector_proxy_mapping.py`
- Market-relative return features.
- Sector-relative return features.
- Cap-relative interface.
- Sector proxy resolution with explicit unmapped and fallback metadata.
- No lookahead, no forward fill, and inner stock/index date alignment.
- Unknown or unaudited cap context remains inactive rather than inferred.

Real-data audit runner:

- `src/veridian_quant/v2/run_market_context_audit.py`
- Research200 audit processed 200/200 symbols with 0 skipped symbols.
- Benchmark: `NIFTY_500`.
- Index rows/date range: 1,570 rows from 2020-01-01 to 2026-04-29.
- Stock aligned rows/date range: 311,227 rows from 2020-01-01 to 2026-04-29.
- `missing_stock_ohlc_count = 0`.
- `missing_index_data_count = 0`.
- Cap context is inactive because current static cap buckets remain unknown.

Sector proxy mapping status:

- Sector labels: 68.
- Mapped labels: 25.
- Intentionally unmapped labels: 43.
- Conservative default uses no silent fallback; fallback is opt-in and flagged.
- Broad substring matching was removed to avoid accidental mappings such as
  `Electric Equipment -> NIFTY_ENERGY`, `Healthcare Services -> NIFTY_PHARMA`,
  and `IT - Hardware -> NIFTY_IT`.

Approved Phase 33E.3 additions:

- `BPO/ITeS -> NIFTY_IT`
- `Consumer Food -> NIFTY_FMCG`
- `Gases & Fuels -> NIFTY_ENERGY`
- `Household Products -> NIFTY_FMCG`
- `Ratings -> NIFTY_FIN_SERVICE`
- `Refineries -> NIFTY_ENERGY`
- `Tobacco -> NIFTY_FMCG`
- `Tyres & Allied -> NIFTY_AUTO`
- `Breweries -> NIFTY_FMCG`
- `Construction -> NIFTY_REALTY`
- `Minerals -> NIFTY_METAL`

Explicitly unmapped examples:

- `Electric Equipment`
- `Healthcare Services`
- `IT - Hardware`
- `Investment`
- `Lubricants`
- `Sugar`

No S1-S5 strategy has been changed or promoted due to these utilities.

## 23. Phase 33F Retained Strategy Context Audit Status

Phase 33F through 33F.3 applied the context layer to retained S1-S5 trade PnL
logs and documented the results in `docs/02_audits/s1_s5_context_audit.md`.

Key findings:

- All five retained strategies performed best in strong-positive benchmark 20D
  context.
- Plain positive benchmark context was not consistently favorable.
- S2 remained strongest and was profitable even in negative benchmark context,
  so its retained edge is not solely broad-market tailwind.
- S1, S3, S4, and S5 showed more visible dependence on strong benchmark and/or
  sector context.
- Conservative sector mapping/no fallback remains active; missing sector context
  equals intentionally unmapped sector-proxy trades.
- No context filter is approved and no strategy is promoted.

Phase 33G status: controlled S2-only context experiments are now pre-declared in
`docs/03_research/s2_context_experiment_design.md`.

Next phase: Phase 33G.1 should implement/run only the fixed S2 experiment batch
with the documented anti-overfitting guardrails. No combined filters, threshold
grids, fundamentals ratios, market-cap buckets, or production approvals are
authorized by the design.

## 24. Open Questions

- Which official or vendor source should be preferred for NSE index OHLCV?
- Are sector index histories available with reliable OHLC or only close values?
- Should benchmark baselines use price-return indices or total-return indices
  when both exist?
- How should dividends be handled in passive benchmark comparison?
- What is the exact Research200 equal-weight benchmark construction rule?
- Should equal-weight Research200 use daily buy-and-hold, monthly rebalance, or
  both?
- How should symbols with missing classification be treated in exposure audits?
- What market-cap bucket source is stable enough for first-pass diagnostics?
- Can historical sector/cap/index membership be obtained without excessive
  manual work?
- Should sector/cap diagnostics be integrated into standard strategy reports or
  kept as separate validation outputs?
- Which capital-utilization metric best distinguishes cash drag from weak alpha?
- What benchmark-relative threshold, if any, should affect future retain/park
  decisions?
- After Phase 33G.1, do any variants justify a second-pass diagnostic run
  without introducing threshold fishing or filter stacking?

## 25. References / Related Docs

- `docs/00_foundation/v2_design_document.md`
- `docs/00_foundation/v2_research_roadmap.md`
- `docs/04_validation/backtest_methodology.md`
- `docs/04_validation/portfolio_robustness_validation.md`
- `docs/04_validation/monte_carlo_robustness_audit.md`
- `docs/02_audits/strategy_audit_master.md`
- `docs/02_audits/s1_s5_context_audit.md`
- `docs/03_research/s2_context_experiment_design.md`
- `docs/01_strategies/s5_relative_strength_momentum_rotation.md`
- `docs/02_audits/s5_audit.md`
- `docs/03_research/feature_ideas.md`
- `docs/03_research/market_hypotheses.md`
- `docs/05_decisions/decision_log.md`
