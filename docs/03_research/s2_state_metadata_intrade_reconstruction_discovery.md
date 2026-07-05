# Phase 36E - S2 State Metadata / In-Trade Reconstruction Discovery

## 1. Status / Verdict

Phase 36E is discovery-only.

No diagnostic helper is implemented. No backtest is run. No report is
generated. No dynamic exit is approved. No entry filter, state filter, risk
filter, sizing rule, production behavior, or strategy promotion is approved.

Decision:

`PROCEED_TO_36F_STATE_RECONSTRUCTION_PROTOTYPE_DESIGN`

Reason:

- Lane A entry-state x risk diagnostics are close to ready because entry-state
  metadata already exists in retained S2 signal/trade context artifacts.
- Lane B in-trade state evolution is not ready from stored artifacts because
  daily open-trade state paths are not exported. It appears feasible, but it
  requires a read-only daily state reconstruction design before an audit helper.

---

## 2. Inspection Scope

Source files inspected:

- `src/veridian_quant/v2/strategies/s2_markov_state_transition.py`
- `src/veridian_quant/v2/strategies/s2_markov_filters.py`
- `src/veridian_quant/v2/backtesting/markov_portfolio_runner.py`
- `src/veridian_quant/v2/backtesting/s2_signal_context.py`
- `src/veridian_quant/v2/backtesting/setup.py`
- `src/veridian_quant/v2/backtesting/execution.py`
- `src/veridian_quant/v2/backtesting/exits.py`
- `src/veridian_quant/v2/backtesting/trade.py`
- `src/veridian_quant/v2/data/loaders.py`
- `src/veridian_quant/v2/data/models.py`
- `src/veridian_quant/v2/reporting/exporters.py`
- `src/veridian_quant/v2/reporting/context.py`
- `src/veridian_quant/v2/reporting/s2_markov_filter_simulation.py`
- `src/veridian_quant/v2/reporting/s2_failure_audit.py`
- `src/veridian_quant/v2/analysis/cross_strategy_risk_diagnostic_audit.py`
- `src/veridian_quant/v2/analysis/trade_context_audit.py`
- `src/veridian_quant/v2/features/market_context.py`
- `src/veridian_quant/v2/run_s2_markov_backtest.py`

Docs inspected:

- `docs/03_research/s2_state_risk_intrade_diagnostic_design.md`
- `docs/02_audits/s2_audit.md`
- `docs/02_audits/cross_strategy_risk_diagnostic_audit.md`
- `docs/00_foundation/v2_research_roadmap.md`
- `docs/03_research/feature_ideas.md`
- `docs/03_research/market_hypotheses.md`
- `docs/03_research/rejected_ideas.md`

Reports/artifacts inspected:

- `reports/v2/s2_markov_2020_2026_research200_exclude_ret_down_full_diagnostics/`
- `reports/v2/s2_markov_2020_2026_research200_exclude_ret_down_clean_state_v1_failure_audit/`
- `reports/v2/phase_36c1_cross_strategy_risk_diagnostic_audit_with_vix/`
- `config/universes/research/nse_eq_research_200_2018_2026.csv`
- `config/universes/research/nse_eq_research_200_static_classification.csv`

Files/folders not found:

- No daily in-trade S2 state path artifact was found.
- No retained S2 artifact with per-holding-day Markov state rows was found.
- The retained `exclude_ret_down` full diagnostics folder does not include
  `s2_failure_audit_*` files; the related `clean_state_v1_failure_audit` folder
  does include failure-audit files.

---

## 3. S2 State Construction Findings

Source location:

- S2 signal generation and state construction live in
  `src/veridian_quant/v2/strategies/s2_markov_state_transition.py`.
- The reusable state builder is `build_state_frame(data)`.

State components found:

- Return state:
  - `RET_STRONG_DOWN`: 5D return <= -5%.
  - `RET_DOWN`: 5D return < -1%.
  - `RET_FLAT`: 5D return <= 1%.
  - `RET_UP`: 5D return < 5%.
  - `RET_STRONG_UP`: otherwise.
- Volatility state:
  - `VOL_LOW`: ATR14 percent < 2%.
  - `VOL_MID`: ATR14 percent < 5%.
  - `VOL_HIGH`: otherwise.
- Drawdown state:
  - `DD_SHALLOW`: 60D drawdown >= -10%.
  - `DD_MID`: 60D drawdown >= -25%.
  - `DD_DEEP`: otherwise.
- Low-distance state:
  - `LOW_NEAR`: close within 5% of 60D low.
  - `LOW_MID_RANGE`: close within 20% of 60D low.
  - `LOW_FAR_FROM_LOW`: otherwise.

Composite state handling:

- Composite labels are stored as
  `RET_*|VOL_*|DD_*|LOW_*`.
- `parse_markov_state_label` in `s2_markov_filters.py` and
  `parse_state_label` in `s2_markov_filter_simulation.py` can parse the
  composite label into separate components.

Transition metadata availability:

- Signal metadata includes:
  - `state_label`.
  - `state_lookback_sessions`.
  - `state_observation_count`.
  - `forward_return_sessions`.
  - `positive_return_threshold_pct`.
  - `positive_transition_probability`.
  - `average_forward_return_pct`.
  - `median_forward_return_pct`.
  - `current_5d_return_pct`.
  - `current_atr_pct`.
  - `current_drawdown_60d_pct`.
  - `current_close_vs_60d_low_pct`.
- Explicit `from_state` and `to_state` fields were not found.
- A separate transition count field was not found, but
  `state_observation_count` is available as same-state sample count.

Lookahead/shift behavior:

- Current state features use current and prior rows only: 5D return uses
  `close.shift(5)`, ATR14 uses historical OHLC through the row, and 60D
  high/low windows include the current row.
- Signal statistics use only matured prior forward returns. During signal
  generation, a prior observation is added only after
  `forward_return_sessions + 1` rows have passed, so current signal statistics
  do not use incomplete future outcomes.
- Signal generation occurs on the state row date. Entry is planned for the next
  session open by `build_trade_setup`.

Daily reconstruction feasibility:

- Daily state reconstruction appears feasible by applying `build_state_frame`
  read-only to each symbol's chronological OHLC dataframe with sufficient
  pre-start lookback.
- Reconstruction must preserve enough warmup for ATR14, 60D high/low, 5D
  returns, and any future decision to recompute same-state statistics.
- For Lane B, daily state for date D is known only after D's close. A
  hypothetical trigger from date D should execute no earlier than the next
  session open.

---

## 4. Existing Report Artifact Findings

Retained S2 report folder:

`reports/v2/s2_markov_2020_2026_research200_exclude_ret_down_full_diagnostics/`

Relevant retained folder CSVs present:

- `trade_log.csv`: 577 rows.
- `trade_pnl_log.csv`: 577 rows.
- `signal_log.csv`: 13,243 rows.
- `trade_signal_context.csv`: 577 rows.
- `all_signal_opportunity_log.csv`: 13,243 rows.
- `s2_markov_state_component_summary.csv`: 13 rows.
- `s2_markov_state_label_summary.csv`: 34 rows.
- R, exit, yearly, symbol, rejected-signal, counterfactual, candidate-filter,
  and same-day candidate-pool summaries are also present.

State columns present:

- `signal_log.csv` includes `state_label`, `state_observation_count`,
  `positive_transition_probability`, `average_forward_return_pct`,
  `median_forward_return_pct`, `current_5d_return_pct`, `current_atr_pct`,
  `current_drawdown_60d_pct`, and `current_close_vs_60d_low_pct`.
- `trade_signal_context.csv` includes the same entry-state metadata for
  accepted trades, plus `signal_date`, `entry_date`, `exit_date`,
  `exit_reason`, `net_pnl`, `r_multiple`, prices, stop/target, and signal-time
  stock/Nifty context.
- `s2_markov_state_component_summary.csv` summarizes accepted-trade performance
  by parsed state component.
- `s2_markov_state_label_summary.csv` summarizes accepted-trade performance by
  full composite state label.

State columns missing:

- Stored reports do not include daily state paths for open trades.
- Stored reports do not include explicit `from_state` / `to_state` fields.
- Stored reports do not include daily transition probability/count values after
  entry.

Trade ID joinability:

- `trade_log.csv`, `trade_pnl_log.csv`, and `trade_signal_context.csv` share
  `trade_id`.
- `trade_id` is deterministic: strategy name, symbol, and entry date.
- `signal_log.csv` does not carry `trade_id`, but accepted trades can be joined
  through `trade_signal_context.csv` and nearest prior same-symbol signal logic
  used by the current exporter.

Entry/exit date availability:

- `trade_log.csv`, `trade_pnl_log.csv`, and `trade_signal_context.csv` include
  `entry_date` and `exit_date`.
- `trade_signal_context.csv` also includes `signal_date`.

R/PnL availability:

- `trade_signal_context.csv` includes `net_pnl` and `r_multiple`.
- `trade_pnl_log.csv` includes `net_pnl`, `gross_pnl`, returns, initial risk,
  stop/target, reward/risk, and exit reason. It does not directly export
  `r_multiple`, but R is computable from `net_pnl / initial_risk_amount` and is
  already present in context/R summary outputs.

Context availability:

- `trade_signal_context.csv` includes signal-time stock/Nifty context,
  pre-entry gap proxy (`stock_gap_from_prev_close_pct`), benchmark/Nifty
  context, drawdown context, ATR context, and relative strength context.
- Liquidity comes from
  `config/universes/research/nse_eq_research_200_2018_2026.csv`.
- Sector comes from
  `config/universes/research/nse_eq_research_200_static_classification.csv`.
- VIX diagnostics are available in
  `reports/v2/phase_36c1_cross_strategy_risk_diagnostic_audit_with_vix/`.

---

## 5. Lane A Feasibility - Entry-State x Risk

Available state metadata:

- Entry composite state exists in both `signal_log.csv` and
  `trade_signal_context.csv`.
- Entry state components are not stored as separate columns in the retained
  context file, but existing parsing helpers can derive `ret_state`,
  `vol_state`, `dd_state`, and `low_state` from `state_label`.
- Signal-time same-state evidence fields are stored:
  `state_observation_count`, `positive_transition_probability`,
  `average_forward_return_pct`, and `median_forward_return_pct`.

Available risk joins:

- Liquidity: join by `symbol` from the static Research200 universe CSV.
- Sector: join by `symbol` from static classification, secondary only.
- Benchmark regime: available from signal-time Nifty fields in
  `trade_signal_context.csv`.
- Drawdown state: available from equity curve at entry in risk audit code, and
  stock drawdown fields exist in `trade_signal_context.csv`.
- VIX: available via Phase 36C.1 VIX logic using latest VIX session on or
  before `signal_date`, otherwise strictly before `entry_date`.
- Pre-entry gap: available as `stock_gap_from_prev_close_pct`.
- Exit reason/gap-stop exposure: available as realized `exit_reason`.
- Rolling R: reconstructable from prior completed trades only, as in Phase 36
  risk audit code.

Required reconstruction:

- Parse `state_label` into components for entry-state x risk tables.
- Join liquidity/sector from config files.
- Recreate or reuse Phase 36 risk join logic for VIX, drawdown, benchmark, gap,
  and rolling R if a future audit helper needs unified outputs.

Blockers:

- No blocking metadata gap for entry-state diagnostics was found.
- Caveats remain: liquidity and sector are static/current diagnostics, and
  rolling R remains high overfit risk.

Feasibility classification:

`READY_WITH_MINOR_GAPS`

Evidence:

The retained S2 artifacts already contain accepted-trade entry-state metadata,
R/PnL, signal/entry/exit dates, and context fields. Minor work is needed to
parse state components and assemble risk joins into the Phase 36D output
schema.

---

## 6. Lane B Feasibility - In-Trade State Evolution

Daily state availability:

- Daily in-trade state paths are not stored in retained reports.
- Daily states must be reconstructed from OHLC using `build_state_frame`.

Trade lifecycle reconstruction:

- `trade_log.csv`, `trade_pnl_log.csv`, and `trade_signal_context.csv` expose
  `trade_id`, `symbol`, `signal_date`, `entry_date`, `exit_date`, `exit_reason`,
  `entry_price`, `exit_price`, `stop_loss`, `target_price`, and risk fields.
- The backtest mechanics make active periods reconstructable as trading-session
  rows on or after `entry_date` through `exit_date`, respecting the original
  maximum holding window.
- `resolve_trade_exit` uses holding rows on or after entry date, checks open
  gap target/stop first, then same-candle ambiguity conservatively as stop
  first, then target/stop, then time/backtest/data-end close.

Next-open hypothetical exit feasibility:

- Feasible in principle from existing OHLC data if the future helper loads
  per-symbol daily OHLC with sufficient warmup and can locate the next trading
  session after deterioration date D.
- The hypothetical exit price should be next session open after D, not D close.
- If the realized trade exits on D before D close, a state computed from D close
  must not be used as a trigger before that realized exit.
- For trades that exit on the next session open because of a gap, a hypothetical
  trigger from the prior close should be compared carefully against the realized
  gap exit.

Required OHLC joins:

- Load each traded symbol's daily OHLC through the configured end date, with
  pre-start warmup.
- Build state frames per symbol once, then join state rows to each trade's
  open holding dates.
- Use the next available trading session open after a trigger date for
  hypothetical exit PnL/R.

Risk/context daily joins:

- Daily stock state and stock technical context are reconstructable from the
  same symbol OHLC.
- Daily benchmark/VIX context is feasible if index/VIX series are joined
  as-of date D using only rows through D.
- Liquidity and sector remain static by symbol.
- Portfolio drawdown state during holding would require an explicit definition:
  as-of realized equity curve state, not future final trade outcome.
- Rolling R during holding should remain secondary/high-overfit and should use
  only previously completed trades as of date D.

Blockers:

- No stored daily state path exists.
- No future helper currently maps every trade to every holding-session date.
- Need a design for same-day exit handling so D-close state is not attributed
  before an intraday target/stop on D.
- Need output schemas and tests before implementation.

Feasibility classification:

`NEEDS_DAILY_STATE_RECONSTRUCTION`

Evidence:

The source state builder is reusable and lookahead-safe for date-D close state,
and trade lifecycle rows are recoverable. However, the required daily
open-trade state path and next-open hypothetical exit fields are absent from
existing artifacts.

---

## 7. Risk/Context Join Feasibility

| Input | Source | Join Key | Entry Join Feasible | In-Trade Daily Join Feasible | Caveats |
| --- | --- | --- | --- | --- | --- |
| Liquidity bucket | `config/universes/research/nse_eq_research_200_2018_2026.csv` | `symbol` | Yes | Yes, static by symbol | Static Research200 liquidity is not point-in-time historical truth. |
| Benchmark regime | `trade_signal_context.csv`; `features/market_context.py`; index OHLC loaders | `signal_date`/date as-of | Yes | Yes, with reconstruction | Entry fields exist; daily join needs index context as-of D. |
| VIX regime | Phase 36C.1 risk audit logic and `market_indicators` | `signal_date` or as-of date | Yes | Yes, with reconstruction | Entry join convention exists; daily holding join must use VIX rows through D only. |
| Drawdown state | Phase 36 risk audit equity-curve logic | `entry_date`/date as-of | Yes | Partial | Entry drawdown is implemented; daily drawdown requires an explicit as-of realized-equity definition. |
| Pre-entry gap | `trade_signal_context.csv` | `trade_id` / `signal_date` | Yes | No | It is an entry context, not a daily holding-period context. |
| Exit reason / gap stop | `trade_log.csv`, `trade_pnl_log.csv`, `trade_signal_context.csv` | `trade_id` | Yes, as realized outcome | Yes, as realized outcome | Outcome must be joined after the fact only, not used to trigger exits. |
| Sector | Static classification CSV | `symbol` | Yes | Yes, static by symbol | Secondary only because classification is current/static and coverage has caveats. |
| Rolling R | Phase 36 risk audit logic | trade order by entry/exit date | Yes, with reconstruction | Partial/high risk | Must use prior completed trades only; high overfit risk, secondary only. |

---

## 8. Lookahead/Data-Safety Assessment

Safe state date alignment:

- `build_state_frame` computes state from OHLC rows through the row's close.
- Entry-state diagnostics can use the signal date state because S2 enters next
  session open.
- In-trade date-D state can be known only after D close. A hypothetical
  state-triggered exit should execute at the next session open.

Safe hypothetical exit execution:

- Next-open execution is feasible if OHLC data contains the next session after
  trigger date D.
- Do not use same-close execution for a date-D state trigger unless a later
  design separately justifies and labels that convention.
- Do not use a date-D close state to trigger an exit for a trade that already
  hit stop/target intraday on D.

Pre-start lookback requirement:

- Minimum state labels require at least 60 sessions for rolling high/low and 14
  sessions for ATR, plus 5 sessions for return state.
- If future work recomputes signal-time same-state statistics, it must preserve
  the 252-session state lookback and 10-session forward-return maturation logic.
- The current SQLAlchemy loader defaults to a 120-calendar-day warmup buffer.
  A future reconstruction prototype should explicitly verify this is enough in
  trading-session terms for the chosen reconstruction scope.

End-date requirement:

- Reconstruction must not load or use rows after the configured backtest end
  date except when a later diagnostic explicitly labels that the next-session
  open is unavailable and excludes the trigger from hypothetical exit metrics.

Known risks:

- Same-day realized target/stop can occur before a date-D close state is known.
- Static liquidity/sector data can create false historical precision.
- VIX and benchmark joins must use as-of logic, not future values.
- Rolling R can overfit and must use prior completed trades only.
- Realized outcome can be joined only for analysis, never trigger generation.

---

## 9. Gaps / Required Work Before Audit

Metadata gaps:

- No explicit `from_state` / `to_state` transition fields.
- No daily post-entry state metadata in retained artifacts.
- No daily transition probability/count metadata after entry.

Reconstruction needs:

- Build a read-only state reconstruction prototype design for per-symbol daily
  state frames.
- Map each accepted S2 trade to holding-session rows.
- Define whether the entry date state path begins at signal date close, entry
  date close, or the first close after entry; the executable trigger must still
  be next session open.
- Define same-day realized-exit handling for trades that exit before D close.

Report schema gaps:

- Future Lane B outputs need `trade_id`, `holding_day_index`, calendar date,
  daily state/components, deterioration flags, first deterioration date,
  sessions-to-exit, hypothetical next-open PnL/R, avoided-stop, and
  missed-target fields.
- Future Lane A outputs need parsed state-component columns and unified
  state-by-risk buckets.

Test needs:

- Unit tests for state reconstruction alignment and component parsing.
- Unit tests for holding-day expansion.
- Unit tests for next-open lookup and missing-next-session handling.
- Unit tests ensuring D-close triggers cannot precede same-day intraday exits.
- Tests or fixtures for as-of VIX/benchmark/drawdown joins before any audit
  helper is implemented.

Output schema needs:

- Pre-register Lane A and Lane B CSV schemas before implementation.
- Include sample-size flags and `INSUFFICIENT_SAMPLE` handling.
- Include explicit `diagnostic_only` / `not_strategy_rule` notes in future
  readme outputs.

---

## 10. Recommendation

`PROCEED_TO_36F_STATE_RECONSTRUCTION_PROTOTYPE_DESIGN`

Rationale:

- Entry-state metadata exists and supports Lane A with minor parsing/join work.
- In-trade daily states are absent from reports but appear safely
  reconstructable from existing OHLC and `build_state_frame`.
- The next phase should design a read-only reconstruction prototype before a
  full audit helper so date alignment, pre-start lookback, next-open execution,
  and same-day exit caveats are nailed down first.

---

## 11. Explicitly Not Approved

- No dynamic exit.
- No `exit if RET_DOWN`.
- No new entry filter.
- No state exclusion.
- No liquidity/risk/VIX/drawdown/benchmark rule.
- No risk sizing change.
- No production use.
- No strategy promotion.
- No backtest optimization.

Phase 36F follow-up:

- Design doc:
  `docs/03_research/s2_daily_state_reconstruction_prototype_design.md`.
- Phase 36F defines the future narrow state reconstruction prototype, including
  daily state reconstruction, holding-period expansion, same-day stop/target
  safety, deterioration candidate flags, next-open feasibility, and coverage
  validation.
- Next selected gate:
  `PROCEED_TO_36G_STATE_RECONSTRUCTION_PROTOTYPE_IMPLEMENTATION`.
- Still not approved: full audit helper, dynamic exit, `exit if RET_DOWN`,
  entry filter, state exclusion, risk filter, sizing change, production use,
  strategy promotion, or backtest optimization.
