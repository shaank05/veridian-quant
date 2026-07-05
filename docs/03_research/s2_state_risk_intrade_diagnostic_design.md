# Phase 36D — S2 State × Risk and In-Trade State Evolution Diagnostic Design

## 1. Status / Verdict

Phase 36D is docs/design only.

No S2 rule is approved. No entry filter is approved. No dynamic exit is
approved. No risk model is approved. No backtest implementation is approved.

This phase designs two diagnostic lanes under one umbrella:

- Lane A: Entry-State x Risk Input Diagnostic.
- Lane B: In-Trade State Evolution Diagnostic.

Decision:

`PROCEED_TO_36E_STATE_METADATA_DISCOVERY`

---

## 2. Why This Phase Exists

S2's retained safer benchmark remains the strongest retained internal strategy:

- Strategy: `S2_MARKOV_STATE_TRANSITION`.
- Retained safer benchmark: `exclude_ret_down`.
- Net PnL: about Rs 9.72L.
- Profit factor: about 1.189.
- Max drawdown: about 24.04%.
- Trades: 577.
- Win rate: about 45.23%.

The higher-return `clean_state_v1` candidate remains fragile rather than
promoted: about Rs 12.32L net PnL, about 1.223 PF, about 33.94% max drawdown,
and severe 2025 weakness.

Failure audits showed S2 fragility in 2024, 2025, and partial 2026. Phase 34
identified stop churn and state/regime non-stationarity as the main S2 problem.
Prior simple guards, state exclusions, and context thresholds did not rescue S2.

Phase 36 showed several useful diagnostics:

- Liquidity was the strongest S2 risk diagnostic. HIGH liquidity carried most
  S2 PnL, while LOW/MID deteriorated in 2024, 2025, and partial 2026.
- Benchmark regime, drawdown state, gap risk, and rolling R were promising
  cross-strategy diagnostics, with rolling R carrying high overfit risk.
- VIX was a useful secondary diagnostic, weaker than liquidity, benchmark
  regime, drawdown, and gap context.

The missing question is whether S2 state behavior explains when trades work or
fail:

- At entry.
- During the holding period.

---

## 3. Design Principles

- Diagnostics first, rules later.
- Separate entry-state evidence from in-trade state-evolution evidence.
- Every claim must include sample size and numeric evidence.
- Avoid overfitting state x risk combinations.
- Avoid threshold optimization.
- Do not cherry-pick symbols, years, sectors, months, or states.
- Do not implement strategy logic until diagnostics justify a pre-registered
  experiment.
- Classify state/risk results as one of:
  - `PROMISING_DIAGNOSTIC`.
  - `WEAK_DIAGNOSTIC`.
  - `OVERFIT_RISK`.
  - `REJECT`.
  - `INSUFFICIENT_SAMPLE`.

---

## 4. Lane A - Entry-State x Risk Input Diagnostic

Purpose:

Determine whether S2 entry-state components perform differently under risk
conditions.

Questions:

- Which S2 state components are present at entry?
- Which components or composite states contribute to PnL, PF, R, win rate, and
  drawdown?
- Did `exclude_ret_down` work because `RET_DOWN` is structurally bad, or because
  it correlates with bad risk regimes?
- Do otherwise good S2 states fail under LOW/MID liquidity, bad benchmark
  regimes, drawdown clusters, VIX regimes, or gap-risk conditions?
- Are 2024/2025 losses concentrated in specific state x risk combinations?

Candidate S2 state dimensions:

- Composite Markov state, if available.
- Return-state component:
  - `RET_UP`.
  - `RET_DOWN`.
  - `RET_STRONG_DOWN`.
- Volatility-state component:
  - `VOL_HIGH`.
  - `VOL_MID`.
  - Any other available volatility states.
- Range/location component:
  - `LOW_MID_RANGE`.
  - Any other available range states.
- Transition metadata, if available:
  - `from_state`.
  - `to_state`.
  - Transition probability.
  - Transition count/sample.

Candidate risk dimensions:

- Liquidity bucket:
  - `HIGH`.
  - `MID`.
  - `LOW`.
- Drawdown state.
- Benchmark 20D regime.
- VIX level/change regime.
- Gap-risk / pre-entry gap bucket.
- Exit reason / gap-stop exposure.
- Year.
- Symbol concentration.
- Sector only as secondary diagnostic because of coverage caveats.
- Rolling R only as secondary/high-overfit diagnostic.

Required outputs for future implementation:

- `entry_state_component_performance.csv`
- `entry_composite_state_performance.csv`
- `entry_state_by_liquidity.csv`
- `entry_state_by_year.csv`
- `entry_state_by_drawdown_state.csv`
- `entry_state_by_benchmark_regime.csv`
- `entry_state_by_vix_regime.csv`
- `entry_state_by_gap_context.csv`
- `entry_state_symbol_concentration.csv`
- `entry_state_diagnostic_readme.txt`

Required metrics:

- Trades.
- Symbol count.
- Year count.
- Net PnL.
- PF.
- Win rate.
- Average PnL.
- Median PnL.
- Average R.
- Median R.
- Target-hit rate.
- Stop-hit rate.
- Gap-stop rate.
- Time-stop contribution.
- Max drawdown contribution, if feasible.
- Rejected/insufficient-sample flags.

---

## 5. Lane B - In-Trade State Evolution Diagnostic

Purpose:

Determine whether S2 trade state deterioration after entry can identify losing
trades before stop, target, or time stop.

Important:

This is not a dynamic exit rule. It is an audit.

Core questions:

- For each open S2 trade, what daily Markov states occurred from entry through
  exit?
- How often did eventual winners enter bad states while open?
- How often did eventual losers enter bad states before stop loss?
- How many sessions before stop/target did deterioration appear?
- What happened after the first bad-state occurrence?
- Would a hypothetical next-open exit after state deterioration have reduced
  losses or cut winners too early?
- Does the effect repeat across years, symbols, and liquidity buckets?

Candidate deterioration triggers for diagnostic only:

- Current in-trade state contains `RET_DOWN`.
- Current in-trade state transitions into a historically poor state.
- Return-state worsens from entry state.
- Volatility-state worsens to `VOL_HIGH`.
- Range/location component deteriorates, if available.
- State deterioration plus bad risk context:
  - LOW/MID liquidity.
  - Benchmark negative regime.
  - High/rising VIX.
  - Moderate/severe drawdown state.

Required future outputs:

- `intrade_daily_state_path.csv`
- `intrade_state_event_summary.csv`
- `intrade_bad_state_first_occurrence.csv`
- `intrade_bad_state_by_exit_reason.csv`
- `intrade_bad_state_by_year.csv`
- `intrade_bad_state_by_liquidity.csv`
- `intrade_hypothetical_next_open_exit_summary.csv`
- `intrade_state_transition_readme.txt`

Required future event-level fields:

- `trade_id`.
- `symbol`.
- `entry_date`.
- `exit_date`.
- `holding_day_index`.
- Calendar date.
- Daily state/composite state.
- Daily state components.
- Entry state.
- State changed from entry yes/no.
- Deterioration flag.
- First deterioration date.
- Sessions from entry to deterioration.
- Sessions from deterioration to exit.
- Eventual exit reason.
- Eventual trade PnL/R.
- Next-open hypothetical exit PnL/R from deterioration date.
- Avoided stop yes/no.
- Missed target yes/no.
- Year.
- Liquidity bucket.
- Benchmark/VIX/drawdown context, if available.

Required metrics:

- Trades with trigger.
- Trades without trigger.
- Target-hit trades that triggered.
- Stop-loss trades that triggered.
- Time-stop trades that triggered.
- Average remaining PnL/R after trigger.
- Median remaining PnL/R after trigger.
- Next-open hypothetical exit average/median PnL/R.
- Avoided stop count.
- Missed target count.
- Net effect estimate.
- PF/win-rate/drawdown impact estimate for hypothetical exit.
- Year/symbol/liquidity stability.
- Sample-size flags.

---

## 6. Discovery Requirements Before Implementation

The next phase after 36D should verify:

- Where S2 state metadata is stored in signals/trades.
- Whether entry composite state/components are available in trade metadata.
- Whether daily S2 state can be reconstructed for every open-trade date without
  lookahead.
- Whether the S2 feature/state builder can be reused read-only.
- Whether `trade_id` alignment exists between trade logs, PnL logs, signal logs,
  and context logs.
- Whether next-open hypothetical exit can be computed safely.
- Whether pre-start lookback is preserved for state reconstruction.
- Whether VIX/benchmark/drawdown/liquidity context can be joined safely.
- Whether enough data exists to support Lane B without implementing strategy
  logic.

---

## 7. Lookahead / Data-Safety Rules

- Entry-state uses information known at signal/entry only.
- In-trade daily state for date D uses data available at or before D.
- If exit is triggered by state on D, hypothetical execution must be next
  session open, not same close, unless separately justified.
- Do not use future realized exit outcome to trigger exit.
- Realized outcome is joined only for analysis.
- Preserve pre-start lookback.
- Do not use rows after configured end date.
- Do not leak target/stop outcome into state classification.

---

## 8. Anti-Overfitting Rules

- Do not search many state/risk thresholds.
- Do not optimize risk buckets by PnL.
- Do not remove symbols or years because they are bad.
- Do not promote tiny buckets.
- Require minimum sample-size flags.
- Compare across years and symbols.
- Treat 2025-only improvements as fragile.
- Keep rolling R secondary because of high overfit risk.
- Any future rule must be pre-registered before backtest.

---

## 9. Candidate Findings and Interpretations

Promising evidence would include:

- Bad in-trade state appears materially more often before stop losses than
  before targets.
- Trigger appears before stop with enough lead time.
- Hypothetical next-open exit improves average/median R without sacrificing too
  many targets.
- Effect repeats across multiple years and symbols.
- Entry-state x risk buckets show stable deterioration across regimes.

Weak or rejected evidence would include:

- Bad states appear equally in winners and losers.
- Many targets pass through bad states.
- Early exit improves only 2025 but damages 2021/2023.
- Effect is concentrated in one symbol or a tiny sample.
- Hypothetical exit reduces drawdown but destroys expectancy.
- Entry-state x risk finding depends on one bucket/year.

---

## 10. Future Decision Path

After 36D:

- 36E - S2 State Metadata / In-Trade Reconstruction Discovery.
- 36F - Implement read-only diagnostic audit helper if discovery passes.
- 36G - Run audit/export CSVs.
- 36H - Separate CSV scrutiny.
- 36I - Docs closeout / decide whether pre-registered experiment is justified.

Possible post-scrutiny decisions:

- `PROCEED_TO_PRE_REGISTERED_S2_ENTRY_FILTER_EXPERIMENT_DESIGN`.
- `PROCEED_TO_PRE_REGISTERED_S2_DYNAMIC_EXIT_EXPERIMENT_DESIGN`.
- `RETAIN_AS_DIAGNOSTIC_ONLY`.
- `REJECT_ENTRY_STATE_RISK_FILTER`.
- `REJECT_DYNAMIC_STATE_EXIT`.
- `INSUFFICIENT_DATA`.

---

## 11. Explicitly Not Approved

- No dynamic exit rule.
- No `exit if RET_DOWN` rule.
- No new entry filter.
- No state exclusion.
- No liquidity filter.
- No drawdown/VIX/benchmark rule.
- No risk sizing change.
- No production use.
- No strategy promotion.
- No backtest optimization.

---

## 12. Decision

`PROCEED_TO_36E_STATE_METADATA_DISCOVERY`

Phase 36D creates the design only. The next phase should discover whether S2
state metadata and daily read-only state reconstruction are available enough to
support the two audit lanes without changing strategy behavior.

Phase 36E discovery result:

- Discovery doc:
  `docs/03_research/s2_state_metadata_intrade_reconstruction_discovery.md`.
- Lane A Entry-State x Risk classification: `READY_WITH_MINOR_GAPS`.
- Lane B In-Trade State Evolution classification:
  `NEEDS_DAILY_STATE_RECONSTRUCTION`.
- Next selected gate:
  `PROCEED_TO_36F_STATE_RECONSTRUCTION_PROTOTYPE_DESIGN`.
- No diagnostic helper, backtest, report generation, dynamic exit, entry
  filter, state exclusion, risk filter, sizing change, production use, or
  strategy promotion is approved.

Phase 36F prototype design result:

- Design doc:
  `docs/03_research/s2_daily_state_reconstruction_prototype_design.md`.
- Phase 36F defines the narrow future reconstruction prototype required before
  a full Lane A/B audit helper.
- Required prototype controls include daily state reconstruction, trade
  lifecycle expansion, D-close / next-open alignment, same-day stop/target
  safety, deterioration candidate flags, and entry-state match validation.
- Next selected gate:
  `PROCEED_TO_36G_STATE_RECONSTRUCTION_PROTOTYPE_IMPLEMENTATION`.
- No full audit helper, dynamic exit, entry filter, state exclusion, risk
  filter, sizing change, production use, strategy promotion, or backtest
  optimization is approved.
