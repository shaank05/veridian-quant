# S5 - Relative Strength / Momentum Rotation

## 1. Purpose

S5 tests whether a simple, ranked, long-only relative-strength strategy can
capture intermediate-term momentum persistence across the audited Research200
universe. Phase 32A defines the research contract only. It does not implement,
run, tune, or approve the strategy.

## 2. Strategy Family Classification

- Identifier: `S5_RELATIVE_STRENGTH_MOMENTUM_ROTATION`.
- Family: cross-sectional relative strength / intermediate-term momentum.
- Direction: long-only.
- Frequency: daily signal evaluation with swing-position holding periods.
- Portfolio behavior: ranked candidate selection under finite capacity.
- Status: design-stage research hypothesis; no backtest evidence yet.

S5 is a standalone strategy family. It is not an S1, S2, S3, or S4 variant,
filter, overlay, vote, or blend. The initial strategy will not use RAWRS,
Kronos, TradingAgents, or another external model.

## 3. Core Hypothesis

Stocks showing strong relative performance over intermediate horizons may
continue outperforming because information diffusion, institutional flows, and
investor underreaction can persist across multiple sessions.

The audited Research200 universe may provide a materially better test of this
hypothesis than the earlier approximately 19-20-symbol Phase 23/24 universe.
With more simultaneous opportunities, ranking quality, rejected candidates,
capacity pressure, and portfolio chronology become part of the strategy's core
economic test rather than secondary diagnostics.

## 4. Why S5 Now

Phase 31 established a common Monte Carlo validation lane and ranked the retained
benchmarks. S2 is currently strongest, but remains regime-fragile and is not
production-ready. S1 remains useful, S3 is weak/moderate, and S4 ATR is weak.

Relative-strength rotation is a comparatively simple, established, and
portfolio-friendly independent hypothesis. It should be tested before adding
external AI/model complexity or resuming narrow threshold tuning in earlier
strategy families.

## 5. Non-Goals

Phase 32A does not authorize:

- Code, tests, backtests, reports, configuration, or data changes.
- Mixing S5 signals with S1/S2/S3/S4.
- RAWRS features, filters, or overlays.
- Kronos, TradingAgents, machine learning, or other external models.
- Portfolio blending, voting, or meta-allocation.
- Optimization against one year, regime, or best historical result.
- A production decision or claim of profitability.
- Many feature thresholds or a large combinatorial variant grid.

## 6. Universe and Timeframe

The first implementation should use:

- Audited Research200 universe.
- Daily OHLCV data.
- Backtest window: 2020-01-01 through 2026-04-30.
- Historical-universe and data-quality policies already defined by the project.
- NIFTY benchmark data only where available at the signal timestamp.

Long lookbacks require warm-up history before 2020-01-01. A symbol is eligible
only when the selected feature has sufficient trailing observations. Missing
history must produce explicit ineligibility, never silent forward filling.

Earlier Phase 23/24 backtests used only about 19-20 symbols. Their signal volume,
rejection rate, and capacity behavior must not be assumed to represent S5 on
Research200.

## 7. Baseline Methodology Alignment

S5 should initially follow the standard v2 methodology:

- Starting equity: ₹10,00,000.
- Current-equity risk per trade: 1%.
- Maximum concurrent positions: 5.
- Cost model: 0.4% round-trip assumption under the existing convention.
- Signal calculated after the daily close using information available then.
- Entry at the next available session open.
- Existing gap handling and conservative same-candle stop-first rule.
- Daily OHLCV only.
- Existing portfolio ledger, risk sizing, trade resolution, and reporting
  contracts where compatible.

The eventual implementation specification must confirm exact parameter names
and cost application rather than create a second interpretation of shared rules.

## 8. Candidate Momentum Definitions

All features must use split-adjusted prices consistent with the approved data
policy and must be computed without future information.

Initial candidates:

- 63-day return: `close_t / close_(t-63) - 1`.
- 126-day return: `close_t / close_(t-126) - 1`.
- 252-day return: `close_t / close_(t-252) - 1`.
- Skip-month momentum: `close_(t-21) / close_(t-126) - 1`, which excludes the
  most recent 21 sessions from the 126-session anchor.
- Distance above SMA200: `close_t / sma200_t - 1`.
- 52-week-high proximity: `close_t / rolling_252d_high_t` or its signed distance
  from one.
- Volatility-adjusted momentum: declared trailing return divided by compatible
  annualized realized volatility.
- Optional NIFTY-relative return: stock return minus NIFTY return over the same
  trailing interval, when benchmark data is complete.

The first cycle should implement only the features required by declared variants.
It should not build a large feature library merely because candidates are listed.

## 9. Relative Strength Ranking

Ranking is integral to S5, not an optional hard filter bolted onto another
signal. On each signal date:

1. Establish the eligible universe using only signal-time information.
2. Compute the declared variant score for every eligible symbol.
3. Sort descending by score.
4. Apply a deterministic tie-break rule, proposed initially as symbol ascending.
5. Exclude symbols already open or otherwise ineligible under portfolio rules.
6. Offer candidates to the portfolio in rank order until capacity is filled.
7. Log every accepted and rejected candidate with score, rank, and rejection
   reason.

The design must later freeze whether entry eligibility means a top-N list, a
top percentile, positive momentum, or a combination. That choice must be common
and simple enough to avoid tuning S5 around capacity after seeing results.

## 10. Market/Regime Filter Options

The raw S5 baseline should remain interpretable. Candidate optional filters are:

- Stock close above SMA200.
- NIFTY close above SMA200.
- Positive NIFTY intermediate-term return.
- No market filter.

The first-pass matrix should use no filter or at most one predeclared trend
filter per variant. Market filters must not import S2 state logic, S3 pullback
logic, RAWRS labels, or post-hoc bad-period exclusions.

## 11. Entry Logic Options

Common entry discipline:

- Evaluate eligible symbols after each session close.
- Require the declared momentum score and any declared trend condition.
- Consider only the highest-ranked candidates when positions are available.
- Enter at the next session open.
- Do not enter on the signal close.
- Do not replace an existing position merely because a new candidate ranks
  higher unless a future turnover rule explicitly authorizes it.

Daily checking therefore does not imply forced daily rebalancing. The first pass
should fill available capacity in rank order while open positions follow their
declared exit mechanics.

## 12. Exit Logic Options

The fair-comparison baseline should reuse existing mechanics where practical:

- ATR-based initial stop.
- Fixed reward/risk target.
- Maximum holding-period time stop.
- Existing gap and same-candle ambiguity handling.

Momentum-specific exits may later test:

- Rank deterioration below a predeclared threshold.
- Close below SMA100 or SMA200.
- Selected momentum score turning negative.
- A momentum-specific maximum holding period.

The first-pass variants should share standard ATR stop/target/time-stop logic.
Rank or trend exits should be separate later experiments so entry quality is not
confounded with a new turnover mechanism.

## 13. Portfolio Construction

S5 is a portfolio strategy rather than a collection of independent symbol
backtests. It should:

- Maintain at most five concurrent positions.
- Allocate new positions only when capital and risk constraints allow.
- Process same-day candidates in deterministic relative-strength rank order.
- Preserve cash when fewer eligible candidates exist.
- Prevent duplicate positions in the same symbol.
- Record capacity and active-symbol rejections separately.
- Recalculate portfolio equity through the existing ledger.

No sector cap, portfolio blend, or forced periodic full rebalance belongs in the
first baseline unless separately designed and justified.

## 14. Position Sizing

Use existing ATR/stop-distance risk sizing with 1% of current portfolio equity
at risk per trade. Sizing must respect available cash, current equity, entry
price, stop distance, and existing integer-quantity rules.

Volatility-adjusted momentum affects candidate order only in its declared
variant. It must not silently change the shared risk-sizing formula.

## 15. Capacity and Concurrency Considerations

Research200 may produce many more simultaneous candidates than five available
slots. Capacity pressure is expected and is part of the hypothesis test.

Required analysis includes:

- Candidates per day and rank distribution.
- Accepted, active-symbol-rejected, and capacity-rejected counts.
- PnL and forward-outcome diagnostics by accepted/rejected status.
- Whether portfolio results depend on a few same-day candidate pools.
- Turnover, holding-period overlap, and cash utilization.
- Stability when many symbols share similar ranks.

Rejected-signal counterfactual PnL remains diagnostic only and must not be mixed
with achievable portfolio PnL.

## 16. Expected Strengths

- Simple economic story and transparent feature calculations.
- Natural cross-sectional prioritization under finite capacity.
- Potential diversification from mean reversion, Markov recurrence, pullbacks,
  and compression breakouts.
- Broad-universe opportunity set.
- Compatibility with existing next-open, risk-sizing, and ledger mechanics.
- Potential to remain invested in persistent leaders rather than repeatedly
  selecting short-lived dislocations.

## 17. Expected Weaknesses

- Momentum crashes and sharp leadership reversals.
- Late entry after an extended move.
- Whipsaw in sideways or rapidly rotating markets.
- High turnover if rank exits are too reactive.
- Crowding and correlated exposure to the same market theme or sector.
- Long lookbacks reduce eligible history and react slowly to structural change.
- Broad candidate volume may make portfolio results highly ranking-dependent.

## 18. Risks and Failure Modes

- Lookahead from using an incomplete signal session or future-adjusted data.
- Survivorship bias in Research200 membership.
- Accidental self-inclusion or inconsistent lookback endpoints.
- One-period or one-regime optimization.
- Score instability from missing prices or near-zero volatility.
- A few extreme winners dominating the result.
- Uncontrolled sector, beta, or volatility concentration.
- Next-open gaps consuming intended reward/risk.
- Replacement-trade effects making diagnostic exclusions look better than true
  portfolio results.
- Momentum feature overlap creating many nominal variants with the same exposure.
- Strong nominal PnL paired with unacceptable drawdown or Monte Carlo tails.

## 19. First-Pass Variants

### `S5_SIMPLE_RS_126D_V1`

- Rank by 126-day return.
- Optional predeclared stock-above-SMA200 eligibility filter.
- Enter highest-ranked eligible candidates when capacity is available.
- Use common ATR stop, target, and time stop.

This should be the simplest primary baseline.

### `S5_DUAL_MOMENTUM_63_126D_V1`

- Combine 63-day and 126-day return using a simple declared score, proposed as
  equal-weight percentile ranks.
- Require intermediate-horizon strength rather than an extremely short-term
  reversal signal.
- Optionally test one simple market trend filter as a separate declared run.

### `S5_VOL_ADJUSTED_RS_V1`

- Rank by a declared momentum return divided by realized volatility.
- Use a volatility floor or explicit invalid-score policy to avoid division by
  zero without favoring artificially quiet symbols.
- Keep portfolio risk sizing unchanged.

### `S5_52W_HIGH_PROXIMITY_V1` - optional later variant

- Rank by closeness to the trailing 52-week high.
- Require a simple positive long-term trend condition.
- Defer until the three primary variants are understood.

No parameter sweep is authorized by this variant list.

## 20. Required Outputs

Future runs should emit the standard strategy and portfolio artifacts, including:

- Run metadata and frozen configuration.
- Signals and completed trades.
- Trade PnL log and equity curve.
- Portfolio summary and standard performance metrics.
- Yearly, symbol, exit-reason, and concentration diagnostics.
- All-signal candidate log with score, rank, eligibility, decision, and reason.
- Capacity and active-symbol rejection logs.
- Feature values used by the selected variant at signal time.
- Data-quality, warm-up, invalid-score, and missing-benchmark counts.

Monte Carlo outputs must remain separate post-backtest validation artifacts.

## 21. Validation Plan

1. Implement and unit-test feature formulas without strategy behavior changes.
2. Implement standalone S5 signal generation with leakage-safe timestamps.
3. Run each declared variant independently on the same Research200 period.
4. Verify standard outputs and reconcile signals, trades, PnL, and rejections.
5. Compare net PnL, CAGR, maximum drawdown, profit factor, win rate, expectancy,
   R-multiple, yearly stability, symbol concentration, trade count, turnover,
   and capacity rejections.
6. Compare S5 primarily with the retained S2 robustness benchmark and secondarily
   with S1, S3, and S4 ATR.
7. Audit failure years, concentration, candidate replacement, and ranking
   stability before considering variants or promotion.
8. Run the standard Monte Carlo protocol only after each backtest is complete.

## 22. Monte Carlo Robustness Comparison Plan

For retained S5 runs, use the Phase 31 standalone shuffle/bootstrap protocol
with like-for-like starting equity, simulation count, seed policy, and drawdown
thresholds. Compare at minimum:

- Bootstrap median, p05, and p95 final equity.
- Probability of ending below starting equity.
- Probability of maximum drawdown >=20% and >=30%.
- Shuffle and bootstrap drawdown tails.
- p95 and worst longest losing streak.
- Ruin/below-zero frequency when available.

S2 is the primary robustness benchmark. S1, S3, and S4 ATR provide secondary
context. Monte Carlo remains post-backtest validation, not a strategy or signal
generator, and cannot prove future profitability.

## 23. Acceptance/Rejection Criteria

S5 should not be promoted unless it improves meaningfully over current evidence.
Initial comparison rules:

- It must beat retained S3 and S4 ATR on nominal return/risk evidence.
- It should challenge S1 or S2 on either return or robustness.
- A strong candidate approaches or exceeds S2 while producing better drawdown
  behavior or lower bootstrap loss probability.
- Profit factor, expectancy, yearly behavior, symbol concentration, capacity
  pressure, and Monte Carlo downside must all remain credible.
- Reject or park variants with weak profit factor, high drawdown, unstable yearly
  performance, concentrated dependence on a few symbols/trades, or poor Monte
  Carlo robustness.
- Do not select a winner solely by best PnL, best year, or best simulated path.

These are research comparison criteria, not production thresholds. Paper-trading,
operational, capacity, and broader validation requirements still apply.

## 24. Implementation Phase Plan

- **Phase 32A - Design:** docs-only hypothesis, methodology, variants, outputs,
  validation plan, and audit boundary.
- **Phase 32B - Feature utilities:** implement and test only the momentum,
  relative-strength, trend, and volatility features required by frozen variants.
- **Phase 32C - Signal generation:** implement standalone, leakage-safe S5
  eligibility, scoring, ranking, signal metadata, and deterministic tie-breaking.
- **Phase 32D - Portfolio runner/CLI:** integrate S5 with shared trade mechanics,
  ATR risk sizing, capacity handling, diagnostics, and isolated CLI/config scope.
- **Phase 32E - Research200 backtests:** run frozen first-pass variants over the
  common window without post-result threshold tuning.
- **Phase 32F - Audit and Monte Carlo comparison:** reconcile outputs, review
  failures and concentration, run post-backtest robustness validation, compare
  with S2/S1/S3/S4 ATR, and decide retain/reject/park status.

Each later phase requires its own reviewed scope. Phase 32A authorizes none of
the implementation or execution work.

## 25. Open Questions

- Should primary eligibility use top-N, top percentile, positive score, or a
  simple combination?
- Should `S5_SIMPLE_RS_126D_V1` include the SMA200 filter in its first raw run or
  reserve it for a second declared run?
- What is the simplest comparable score for the 63/126-day dual variant?
- Which return horizon should the volatility-adjusted variant normalize?
- Should S5 fill only newly available slots or support periodic portfolio-wide
  rotation after the baseline?
- What common maximum holding period best preserves fair comparison without
  suppressing the momentum hypothesis?
- How should delisted symbols and changing Research200 membership be handled to
  minimize survivorship bias?
- Is NIFTY-relative return sufficiently complete and timestamp-aligned for an
  initial or later variant?
- Are sector identifiers available for concentration diagnostics without adding
  an entry filter?
- What minimum trade count and Monte Carlo stability are required before an S5
  result is considered publishable rather than exploratory?

## 26. References / Related Docs

- `docs/00_foundation/v2_design_document.md`
- `docs/00_foundation/v2_research_roadmap.md`
- `docs/03_research/market_hypotheses.md`
- `docs/03_research/feature_ideas.md`
- `docs/04_validation/backtest_methodology.md`
- `docs/04_validation/portfolio_robustness_validation.md`
- `docs/04_validation/monte_carlo_robustness_audit.md`
- `docs/02_audits/strategy_audit_master.md`
- `docs/01_strategies/s1_zscore_mean_reversion.md`
- `docs/01_strategies/s2_markov_state_transition.md`
- `docs/01_strategies/s3_trend_pullback_continuation.md`
- `docs/01_strategies/s4_entropy_volatility_compression_breakout.md`
- `docs/05_decisions/decision_log.md`
