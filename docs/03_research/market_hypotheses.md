# Veridian Quant v2 — Market Hypotheses

## Purpose

This document defines the market inefficiencies Veridian Quant v2 is allowed to research.

No strategy should be implemented unless it maps clearly to one or more hypotheses in this document.

---

# H1 — Panic Mean Reversion

## Hypothesis

Indian large-cap equities sometimes experience short-term oversold conditions caused by panic selling, forced exits, liquidity pressure, or broad market fear.

After the selling pressure exhausts, prices often revert toward a short-term equilibrium.

## Expected Edge

Buy statistically oversold stocks after abnormal downward movement, provided the broader market regime is not structurally hostile.

## Why This May Work

* Investors overreact to short-term bad news.
* Stop-loss cascades can temporarily push prices below fair value.
* Institutional flows may create temporary dislocations.
* Liquid large-cap names often attract dip-buying after excessive decline.

## When It May Fail

* During strong bear markets.
* During company-specific fundamental deterioration.
* During earnings shocks, fraud events, or governance issues.
* When the entire sector is repricing lower.

## Candidate Features

* Z-score
* Distance from moving average
* Short-term drawdown
* Volatility-adjusted return
* Gap-down magnitude
* Volume shock

---

# H2 — Regime-Dependent Mean Reversion

## Hypothesis

Mean reversion does not work equally in all market environments.

The same oversold signal may behave differently in bull, bear, sideways, high-volatility, and low-volatility regimes.

## Expected Edge

Filter or resize trades based on market regime.

## Why This May Work

* Bull markets reward buying pullbacks.
* Bear markets punish early dip-buying.
* High-volatility regimes increase stop-loss risk.
* Sideways markets often favor reversion.

## When It May Fail

* Regime model is late.
* Market changes abruptly.
* Nifty regime differs from individual stock regime.
* Sector-specific stress is missed.

## Candidate Features

* Nifty trend
* Nifty volatility
* India VIX
* Market breadth
* Sector trend
* Advance-decline ratio

## Phase 36B/36C Status Note

India VIX is available and joined to 2,740 / 2,740 retained S1-S5 trades with
100% coverage, but Phase 36C.1 retained it only as secondary market context.
It is not approved as a standalone regime rule, VIX threshold, dynamic sizing
input, or production filter. VIX x drawdown is a possible future
pre-registration candidate only.

---

# H3 — Volatility Normalization

## Hypothesis

Raw price movement is not comparable across stocks.

A 3% fall in one stock may be normal, while a 3% fall in another may be extreme.

## Expected Edge

Normalize signals by each stock’s own volatility before ranking opportunities.

## Why This May Work

* It avoids treating high-beta and low-beta stocks equally.
* It improves comparability across the universe.
* It reduces false signals from naturally volatile stocks.

## When It May Fail

* Volatility expands suddenly.
* Historical volatility underestimates current risk.
* Low-volatility stocks break down structurally.

## Candidate Features

* Rolling standard deviation
* ATR
* Realized volatility
* Volatility-adjusted returns
* Z-score

---

# H4 — Liquidity Shock Recovery

## Hypothesis

Temporary liquidity shocks can push liquid stocks away from fair short-term value.

Once liquidity normalizes, price may recover.

## Expected Edge

Identify excessive price movement with abnormal volume or abnormal range, then wait for stabilization.

## Why This May Work

* Large sell orders can temporarily overwhelm demand.
* Index rebalancing or institutional flow can create temporary pressure.
* Liquidity often returns in large-cap stocks.

## When It May Fail

* Selling is information-driven.
* Liquidity does not return.
* Shock is part of a larger breakdown.

## Candidate Features

* Volume spike
* Range expansion
* Gap-down
* Intraday recovery
* Close location within candle

---

# H5 — Relative Weakness Reversion

## Hypothesis

A stock that becomes unusually weak relative to the index or sector may revert if the weakness is temporary rather than structural.

## Expected Edge

Identify stocks that underperform sharply versus benchmark but remain inside a supportive market or sector regime.

## Why This May Work

* Temporary flow pressure can create relative dislocation.
* Pair and basket rebalancing may normalize relative performance.
* Strong stocks often recover faster after temporary underperformance.

## When It May Fail

* Stock-specific weakness is fundamental.
* Sector is structurally weakening.
* Relative weakness continues into momentum breakdown.

## Candidate Features

* Stock vs Nifty relative return
* Stock vs sector relative return
* Relative strength percentile
* Rolling beta-adjusted residual

---

# H6 - Opportunity Selection Under Capital Constraints

## Hypothesis

S1's key bottleneck is not only signal generation. It is opportunity selection under capital constraints.

When the strategy generates more valid signals than the portfolio can take, portfolio results depend heavily on which candidates are selected and which are rejected.

## Expected Edge

Improve portfolio performance by ranking, scoring, or voting among same-day candidates without changing the underlying signal-generation rules.

## Current Evidence

All-signal diagnostics show that rejected capacity signals contain hidden winners, but the average rejected capacity signal has weak edge.

This supports future candidate ranking and voting systems, but does not prove that simple ranking is enough.

`candidate-ranking s1_v1` underperformed the unranked S1 baseline, so more evidence or separate strategy families are needed before optimizing S1 ranking further.

Standalone strategies should be tested independently before combining them as votes.

Phase 35B/35C update:

Broad cross-strategy voting and generic 2+ strategy consensus are dropped for
the current branch. Executed-trade confirmation was weak, signal overlap was
diagnostic rather than realized PnL, and narrow S2/S4 confirmation remains only
a parked observation. H6 remains relevant for risk-model, universe/regime, and
capacity-selection research, but not for immediate ensemble implementation.

## Candidate Features

* Signal depth
* Volatility-adjusted displacement
* Liquidity
* Same-day candidate pool context
* Historical same-state outcomes
* Regime context
* Strategy-family agreement

## When It May Fail

* Ranking features are noisy.
* Winners are not predictable from signal-time data.
* Hard filters remove too many profitable trades.
* Ranking overfits one universe or period.
* Capacity constraints change in live deployment.

---

# H7 - Trend Pullback Continuation

## Hypothesis

Strong stocks in confirmed uptrends often resume their trend after controlled pullbacks.

S3 tested whether structurally healthy stocks can be bought after temporary weakness without drifting into falling-knife mean reversion.

Audit status:

S3 is technically valid but parked as a standalone production candidate. The best retained benchmark is `S3_STRONG_TREND_ABOVE_SMA50_V1`, but it is benchmark-only.

## Expected Edge

Expected edge comes from:

* Trend persistence.
* Better entry price than chasing highs.
* Strong stocks recovering faster after controlled weakness.
* Avoiding deeply broken stocks that are down for structural reasons.

## Why This May Work

* Institutional accumulation can persist across multiple swing cycles.
* Healthy uptrends often include short profit-taking pauses.
* Pullbacks toward intermediate trend support can improve reward/risk.
* Relative strength can remain durable even after short-term weakness.

## When It May Fail

* The pullback becomes a trend breakdown.
* The broader market regime turns hostile.
* A stock is above SMA200 but its sector is deteriorating.
* Volatility expansion signals panic rather than controlled weakness.
* Pullback-depth thresholds overfit one market period.

## Candidate Features

* SMA50/SMA200 trend.
* SMA slope.
* Controlled pullback return.
* Drawdown from 20d/60d high.
* Distance from SMA50.
* Distance from 60d low.
* ATR expansion.
* Relative strength vs Nifty.
* Nifty trend confirmation.

---

# H8 - Volatility Compression Breakout

## Hypothesis

Stocks that spend time in unusually compressed volatility, tight ranges, or reduced directional noise may produce favorable long-only breakout opportunities once price confirms expansion.

S4 will test this as `S4_ENTROPY_VOLATILITY_COMPRESSION_BREAKOUT`.

Audit status:

S4 has been implemented and raw-tested through Phase 29F/29G as an independent strategy family, not an S1/S2/S3 filter.

Current conclusion:

S4 is technically valid but parked after weak raw baseline evidence. `S4_ATR_COMPRESSION_BREAKOUT_V1` is retained only as a weak benchmark/research reference. `S4_RANGE_COMPRESSION_BREAKOUT_V1` is rejected as an S4 raw baseline, and `S4_ENTROPY_GATED_BREAKOUT_V1` is not promoted. S4 is not production-ready.

## Expected Edge

Expected edge comes from:

* Volatility expansion after unusually quiet periods.
* Breakout confirmation after compression rather than prediction during compression.
* Capturing early continuation after a range resolves upward.
* Avoiding direct dependence on oversold mean reversion, Markov recurrence, or pullback-continuation logic.

## Why This May Work

* Market participants often accumulate or distribute before visible range expansion.
* Tight ranges can create clustered stops and momentum follow-through after a breakout.
* Low recent volatility can allow tighter initial risk definition.
* Breakout confirmation can reduce premature entries inside unresolved ranges.

## When It May Fail

* Breakout fails quickly and returns inside the range.
* Compression reflects illiquidity rather than useful setup quality.
* Entry at next open suffers from unfavorable breakout gaps.
* Low volatility persists rather than expanding.
* Broader market weakness overwhelms individual breakouts.
* Added volume or trend filters overfit and blur S4's independent thesis.

## Candidate Features

* ATR percentile compression.
* Rolling high-low range compression.
* Optional entropy/noise compression.
* Close above N-day high.
* Optional volume confirmation.
* Optional trend context.

---

# H9 - Intermediate-Term Relative Strength / Momentum Persistence

## Hypothesis

Stocks that outperform peers over intermediate horizons may continue to
outperform because information diffusion, institutional positioning, and
investor underreaction can persist across multiple sessions.

S5 tested this hypothesis as the standalone
`S5_RELATIVE_STRENGTH_MOMENTUM_ROTATION` strategy family.

The audited Research200 universe is central to the test. Earlier Phase 23/24
work used only approximately 19-20 symbols; Research200 should materially change
candidate volume, rank dispersion, rejected opportunities, capacity pressure,
and portfolio chronology.

## Expected Edge

- Hold or enter the strongest eligible stocks rather than treating simultaneous
  candidates as interchangeable.
- Use cross-sectional ranking to allocate scarce portfolio slots.
- Capture persistent intermediate-term leadership without relying on oversold
  mean reversion, Markov recurrence, pullback depth, or compression breakouts.

## Why This May Work

- Institutional accumulation and capital flows may persist.
- Investors may underreact to information, allowing trends to continue.
- Broad-universe ranking may identify leadership more effectively than isolated
  absolute thresholds.
- Relative comparison can direct finite capacity toward stronger opportunities.

## When It May Fail

- Momentum leadership reverses abruptly.
- Crowded trades unwind together.
- Sideways markets cause rank churn and whipsaw.
- The strategy enters after trends are already exhausted.
- A broad market or sector reversal overwhelms stock-level momentum.
- Ranking overfits one lookback, period, or universe.
- Capacity constraints and replacement trades erase signal-level advantage.

## Candidate Features

- 63-day, 126-day, and 252-day returns.
- 126-day return excluding the most recent 21 sessions.
- Distance above SMA200.
- Proximity to the trailing 52-week high.
- Volatility-adjusted momentum.
- Optional NIFTY-relative return when benchmark data is available.
- Cross-sectional rank and percentile.

Audit status:

- Phase 32A through 32F first-pass lane complete.
- First-pass Research200 evidence is weak/mixed.
- Broad momentum rotation did not produce a strong edge under the current ATR
  stop/target/time-stop portfolio design.
- Simple RS 126D and Vol-Adjusted RS are rejected.
- Dual Momentum 63/126D is weak and parked only as a benchmark.
- S5 is independent from S1/S2/S3/S4.
- No RAWRS or external-model features in the first research cycle.
- S2 remains the primary robustness benchmark and was not challenged by S5.

---

# H10 - Sector, Market-Cap, and Benchmark Context Dependence

## Hypothesis

Strategy performance may differ materially by sector, market-cap segment, and
benchmark regime.

A strategy that appears profitable in aggregate may be expressing sector beta,
market-cap segment beta, broad-market exposure, or risk-on/risk-off exposure
rather than stock-specific alpha.

Phase 33A designs the context layer needed to study this hypothesis:

- `docs/04_validation/benchmark_sector_cap_context.md`

## Expected Edge

Expected research value comes from:

- Distinguishing stock-specific alpha from passive benchmark exposure.
- Identifying whether sector-relative strength improves candidate ranking.
- Identifying whether smallcap/midcap risk-on regimes dominate long-only
  strategy returns.
- Detecting sector or cap-bucket concentration before it is mistaken for robust
  alpha.
- Understanding whether weak CAGR is caused by low capital utilization, cash
  drag, or true lack of edge.

## Why This May Work

- Indian sector leadership can persist for long enough to affect swing strategy
  outcomes.
- Smallcap and midcap phases can materially change the opportunity set.
- Broad-market rallies can make weak stock selection look better than it is.
- Sector-relative comparison may separate true stock strength from a rising
  sector tide.
- Cap-segment-relative comparison may reveal whether a strategy is only riding
  risk appetite.

## When It May Fail

- Current/static sector or market-cap classification introduces survivorship
  bias when used historically.
- Sector indices may not match the tradable universe or classification source.
- Market-cap bucket definitions may shift through time.
- Benchmark-relative features may overfit one regime or universe.
- Passive benchmark framing may be incomplete if dividends, rebalancing, or
  total-return treatment are inconsistent.

## Candidate Features

- Stock return minus NIFTY return.
- Stock return minus sector index return.
- Stock return minus cap-segment index return.
- Sector momentum rank.
- Cap-segment momentum rank.
- Sector above SMA200 flag.
- Cap-segment above SMA200 flag.
- Smallcap versus largecap relative strength.
- Midcap versus largecap relative strength.
- Strategy PnL by sector and cap bucket.
- Accepted/rejected/capacity signals by sector and cap bucket.
- Capital utilization and cash-drag metrics.

---

# H11 - External K-Line Representation Diagnostics

## Hypothesis

An external K-line foundation model may provide ranking, regime, context, or
confirmation information not captured by S1-S5, RAWRS diagnostics, benchmark
context, liquidity, drawdown state, gap risk, or VIX.

Kronos is the first external model candidate in this lane, but Phase 37B is
design-only. Kronos is not production-approved, not direct-strategy-approved,
and not approved for raw predicted-candle execution.

Phase 37J updates this lane with a small offline diagnostic design after the
Phase 37H technical smoke test passed and Phase 37I reviewed it. The proposed
first diagnostic remains pre-registered and small: 5 HIGH-liquidity Research200
symbols x 6 dates = 30 forecasts, 400-session lookback, and 5-session horizon.
This is not execution approval and does not support production or trading
claims.

Phase 37K later executed the approved small diagnostic, and Phase 37L
scrutinized the result: 30 / 30 forecasts completed, directional accuracy was
13 / 30 = 43.33%, Spearman rank IC was -0.268521, top-minus-bottom spread was
-0.043511, top2-minus-bottom2 spread was -0.010859, and 17 / 150 forecast path
rows had invalid OHLC relationships. Phase 37M therefore adds a design-only
stochastic reproducibility/output-validity gate before any broader diagnostic.
Phase 37N executed that gate and still found 16 / 90 invalid OHLC rows =
17.78%, affecting 8 / 18 forecast runs. Phase 37O documents adapter/output
validation debug design and selects a gated adapter debug execution as the next
step. Phase 37P showed eval/decoding settings affect validity, and Phase 37Q
defines the output-validity policy required before any retry. The hypothesis is
still not accepted or rejected permanently; invalid output rows, seed stability,
rank stability, API usage, and caller-side validity policy must be understood
and implemented first. Phase 37R implemented reusable output-validity helpers,
and Phase 37S designs a policy-compliant 30-run retry only; future execution
requires explicit 37T approval and direct comparison with 37K must be caveated
because decoding policy changes. Phase 37T completed that retry but failed
output validity and retained weak/negative validity-gated metrics. Phase 37W
closes the lane for now with `DOCS_ONLY_CLOSEOUT_AND_BIMONTHLY_REVIEW`; review
upstream every two months for maturity, fixes, CPU/GPU reproducibility
clarification, output-validity improvements, and prediction-quality evidence.

## Expected Research Value

- Evaluate whether forecast-derived diagnostics have positive rank
  relationships with future returns.
- Test whether agreement/disagreement with S1-S5 separates trade quality.
- Study whether any signal persists by year and regime rather than only in
  strong bull periods.
- Determine whether external forecasts add information beyond existing
  liquidity, benchmark, drawdown, and VIX diagnostics.
- Determine whether generated forecast paths are valid and reproducible enough
  to use as diagnostics at all.

## When It May Fail

- The model only repeats broad market, liquidity, or volatility effects.
- Stochastic outputs are unstable.
- Generated OHLC paths violate basic validity relationships.
- Apparent rank or direction evidence depends on cherry-picked seed/decoding
  settings.
- Compute cost is too heavy for safe local research.
- Lookahead, normalization leakage, or split leakage cannot be ruled out.
- Model-weight terms block safe use.
- Raw forecast PnL looks attractive while forecast/ranking diagnostics fail.

## Candidate Features

- Predicted close return over predeclared horizons.
- Predicted direction.
- Forecast strength score.
- Cross-sectional forecast rank.
- Predicted range or volatility proxy.
- Forecast dispersion if repeated samples are feasible.
- Agreement/disagreement with retained benchmark trades.
- Spearman rank IC.
- Top-minus-bottom forecast-rank realized return spread.

---

# H12 - S2 State/Risk Failure and In-Trade Deterioration Diagnostics

## Hypothesis

S2 failures may be explained by entry-state x risk interactions and/or by
post-entry Markov state deterioration during the holding period.

The retained S2 safer benchmark remains useful, but weak periods in 2024, 2025,
and partial 2026 suggest that aggregate S2 performance may hide unstable
state/risk pockets and stop-churn paths.

Phase 36D designs this as diagnostics only:

- `docs/03_research/s2_state_risk_intrade_diagnostic_design.md`

## Expected Research Value

- Determine whether entry-state components perform differently under liquidity,
  benchmark, drawdown, VIX, and gap-risk contexts.
- Determine whether trades that later stop out deteriorate into poor Markov
  states before realized exit.
- Estimate whether a hypothetical next-open exit after state deterioration
  would have reduced losses or cut winners too early.
- Separate stable state/risk evidence from 2025-only or tiny-bucket artifacts.

## When It May Fail

- Bad states appear equally in winners and losers.
- Many target-hit trades pass through the same bad states.
- Hypothetical exits reduce drawdown but destroy expectancy.
- Evidence depends on one year, one symbol, or one small state/risk bucket.
- Daily state reconstruction is not available without lookahead or missing
  pre-start lookback.

## Candidate Features

- Entry composite Markov state and state components.
- Entry state x liquidity, benchmark, drawdown, VIX, and gap context.
- Daily in-trade composite state and components.
- First deterioration date and lead time before exit.
- Hypothetical next-open exit PnL/R after deterioration.
- Avoided-stop and missed-target diagnostics.

Audit status:

- Phase 36D is docs/design only.
- Phase 36E discovery is documented in
  `docs/03_research/s2_state_metadata_intrade_reconstruction_discovery.md`.
- Lane A Entry-State x Risk is `READY_WITH_MINOR_GAPS`.
- Lane B In-Trade State Evolution is `NEEDS_DAILY_STATE_RECONSTRUCTION`.
- Phase 36F prototype design is documented in
  `docs/03_research/s2_daily_state_reconstruction_prototype_design.md`.
- The in-trade deterioration hypothesis remains pending reconstruction
  coverage, entry-state match validation, and same-day stop/target safety.
- No dynamic exit, `exit if RET_DOWN` rule, entry filter, state exclusion, risk
  filter, sizing change, backtest, production use, or strategy promotion is
  approved.
- Next selected gate:
  `PROCEED_TO_36G_STATE_RECONSTRUCTION_PROTOTYPE_IMPLEMENTATION`.

---

# Rejected or Deferred Hypotheses

The following are not accepted production rules.

## Exact Price Prediction

Rejected for Phase 1.

Reason:

Veridian Quant v2 should first validate robust behavioral/statistical edges before attempting direct forecasting.

## Black-Box ML Prediction

Deferred.

Reason:

Machine learning may be useful later, but only after clean baselines and audit framework are established.

Kronos Phase 37B narrows one possible ML/model lane to offline diagnostics only:
ranking, regime/context, confirmation/disagreement, and forecast-quality
evaluation. It does not approve direct forecast execution, production use,
dependency installation, model download, or fine-tuning.

Phase 37J keeps this lane diagnostic-only. It does not approve a full
Research200 run, alpha conclusion, threshold optimization, raw forecast trading,
or small-diagnostic execution without separate 37K approval.

Phase 37M adds a further gate after the weak/negative Phase 37K/37L result and
17 / 150 invalid OHLC rows: no broader diagnostic, full Research200 run,
best-seed selection, decoding cherry-picking, production use, or strategy use
is appropriate until output validity and stochastic reproducibility are
acceptable under a separately approved tiny follow-up.

Phase 37O updates that gate after 37N: invalid OHLC remained high, so no
signal-quality retry is appropriate until adapter/API usage and output
validation policy are debugged. In particular, "repair candles and continue" is
not an approved trading or alpha-evaluation path.

Phase 37Q makes that policy explicit: invalid forecast runs are excluded from
signal-quality metrics by default, repair is visualization-only unless
separately approved, and close-only diagnostics require a separate labeled mode.
Phase 37S allows only a future approval-gated, policy-compliant retry design;
it does not approve inference, Research200, strategy integration, or raw
predicted-candle trading. Phase 37W closes Kronos for now; no local patch,
further local inference, Research200 scaling, strategy integration, production
use, or raw predicted-candle trading is approved.

## FFT / Wavelet Entry

Deferred.

Reason:

These may be researched later, but they must independently prove contribution beyond simple volatility-normalized mean reversion.

---

## Markov-Based Entry

Research implementation exists as standalone S2 Markov State Transition.

Status:

Researched through Phase 27J, retained as benchmark/research candidate, frozen for now, and not accepted as a production rule.

Reason:

S2 has evidence of edge, but the research cycle found material regime fragility, especially in 2025/2026.

Retained S2 benchmarks:

* Safer benchmark: `exclude_ret_down + ranking none`
* Higher-return research candidate: `exclude_ret_down + clean_state_v1`

The 2025 failure audit found that S2 was vulnerable to shallow bullish pullbacks that looked healthy but failed to mean-revert:

* `RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW`
* `RET_UP|VOL_MID|DD_SHALLOW|LOW_MID_RANGE`

S2 is useful for future comparison, but immediate S2 tuning is parked.

---

# Current Priority

The current research priority is:

## Broader strategy research, robustness, and portfolio construction

Meaning:

S1 remains the current volatility-normalized mean-reversion benchmark, while opportunity selection under capital constraints is now a core research problem.

S2 Markov State Transition has now been tested independently and is frozen as a benchmark/research candidate, not a production strategy.

S3 Trend Pullback Continuation has now been tested independently and is parked as a benchmark-only strategy family, not a production strategy.

S4 Entropy / Volatility Compression Breakout has now been raw-tested independently and is parked as a weak benchmark-only strategy family, not a production strategy.

S5 Relative Strength / Momentum Rotation has now been first-pass tested
independently. Simple RS and Vol-Adjusted RS are rejected; Dual Momentum is weak
and parked as a benchmark only. S5 is not a production strategy.

The next research priority should not be more S2, S3, S4, or immediate S5
threshold tuning. Future S5 work should require a materially redesigned momentum
hypothesis rather than small parameter changes to the first-pass variants.

The Phase 35 ensemble branch is closed for now. The next preferred work should
be Cross-Strategy Risk Model Input Discovery, Universe/Regime Segmentation
Research, or S2 Risk Model Research rather than another voting variant.

Before major new strategy-family exploration, the project should prioritize the
Phase 33 benchmark, sector, market-cap, regime, exposure, and
capital-utilization context foundation.
