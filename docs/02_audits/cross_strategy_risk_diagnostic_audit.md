# Cross-Strategy Risk Diagnostic Audit

## Purpose

This document closes the Phase 36B / 36C.0 / 36C.1 risk diagnostic branch for
retained S1-S5 strategy reports.

This is a research diagnostic closeout only. It does not approve a risk model,
VIX rule, liquidity filter, drawdown throttle, benchmark-regime filter,
gap-risk filter, rolling-R threshold, dynamic sizing, production deployment, or
strategy/backtest change.

---

## Phase 36B Base Risk Diagnostics

Verdict:

- `ONE_OR_MORE_PROMISING_RISK_DIAGNOSTICS`.
- No implementation approved.

Phase 36B evaluated retained S1-S5 reports for risk-input diagnostics including
liquidity, symbol concentration, gap exits, pre-entry gap context, ATR/volatility
context, benchmark regime, sector diagnostics, drawdown state, rolling prior
trade R, and rejection pressure.

### Liquidity

Liquidity was the strongest S2 risk diagnostic and was also useful for S3 and
S5. It was not universal across S1 and S4.

S2 liquidity evidence:

- HIGH liquidity: 271 trades, about Rs 970,422 net PnL, about 1.42 PF, about
  49.45% win rate, and about -Rs 948 median PnL.
- LOW liquidity: about -Rs 26,697 net PnL and about 0.96 PF.
- MID liquidity: about Rs 27,990 net PnL and about 1.01 PF.
- LOW/MID liquidity deteriorated in 2024, 2025, and partial 2026.

Decision:

- Retain liquidity as the strongest S2 risk diagnostic.
- Do not implement a liquidity filter now.
- Static liquidity bucket is diagnostic only and is not point-in-time historical
  truth.

### Gap Risk

Base S2 gap-risk evidence:

- `STOP_GAP_HIT`: 35 trades, about -Rs 673,842 net PnL, about -Rs 19,253
  average PnL, about -Rs 18,962 median PnL, and about -1.23 average R.
- `TARGET_GAP_HIT`: 31 trades, about +Rs 966,904 net PnL, about Rs 31,190
  average PnL, about Rs 31,248 median PnL, and about 2.17 average R.

Decision:

- Retain gap risk as important.
- Do not implement a simple gap filter because target-gap gains are also large.
- Do not ignore target-gap gains when studying stop-gap losses.

### Drawdown State

Moderate drawdown entries were weak across S2, S3, S4, and S5.

Decision:

- Retain drawdown state as a promising cross-strategy throttle diagnostic.
- Do not implement a drawdown throttle now.

### Rolling Prior-Trade R

Strong-positive rolling R looked powerful for S2, S1, and S3.

Decision:

- Keep rolling R as promising but high overfit risk.
- Do not implement rolling-R thresholds now.
- Any future use requires strict pre-registration.

### Benchmark Regime

S2 was weak in ordinary negative NIFTY 20D regime and strong in strong-positive
and strong-negative benchmark regimes.

S2 benchmark-regime evidence:

- Strong-positive benchmark: 127 trades, about Rs 660,713 net PnL, about
  1.78 PF.
- Strong-negative benchmark: 42 trades, about Rs 268,996 net PnL, about
  2.11 PF.
- Ordinary negative benchmark: 191 trades, about -Rs 94,265 net PnL, about
  0.95 PF.

Decision:

- Retain benchmark regime as a strong diagnostic.
- Prior direct S2 context filters failed, so benchmark-regime evidence must be
  handled cautiously.
- Do not implement a benchmark-regime filter now.

### Symbol Concentration And Capacity

S2 has meaningful symbol concentration. S4 and S5 are highly dependent on a few
winners.

Capacity-full rejections are large platform-wide, but rejected trades cannot be
assumed to be achievable profits because rejected-trade PnL is counterfactual
and ignores capital, ledger, and portfolio sequencing.

Decision:

- Keep concentration and capacity diagnostics in the research layer.
- Do not create symbol include/exclude rules from contributor tables.

---

## Phase 36C.0 India VIX Data Availability

India VIX exists in the database table `market_indicators`.

Identifier:

- `indicator_name`: `INDIA_VIX`
- Upstox key: `NSE_INDEX|India VIX`
- Usable value: `close`
- Date: `timestamp::date`

Coverage:

- VIX coverage period: 2020-01-01 to 2026-04-29.
- Rows: 1,571.
- Unique dates: 1,571.
- Null/invalid/nonpositive rows: 0.
- Duplicate dates: 0.
- Missing equity session: 2025-04-25 only.

Retained trade coverage:

- S1-S5 retained trades covered: 2,740 / 2,740.
- Coverage: 100%.
- Missing/null/nonpositive joined VIX values: 0.

Safe join convention:

- Use latest VIX session on or before `signal_date` when available.
- If `signal_date` is unavailable, use latest VIX session strictly before
  `entry_date`.
- Do not use entry-date VIX close in fallback mode for next-session-open
  entries.

---

## Phase 36C.1 VIX Diagnostic Findings

Verdict:

- `VIX_PROMISING_SECONDARY_DIAGNOSTIC`.
- VIX is not approved as a standalone rule.

VIX coverage:

- Retained S1-S5 trades covered: 2,740 / 2,740.
- Coverage: 100%.
- Missing/null/nonpositive joined values: 0.

### S2 VIX Level

S2 VIX rolling-percentile bucket evidence:

- Low VIX: 210 trades, about Rs 654,183 net PnL, about 1.36 PF, about 45.71%
  win rate, and about -Rs 2,754 median PnL.
- Mid VIX: 123 trades, about Rs 12,216 net PnL, about 1.01 PF, about 43.90%
  win rate, and about -Rs 5,868 median PnL.
- High VIX: 236 trades, about Rs 358,383 net PnL, about 1.17 PF, about 46.61%
  win rate, and about -Rs 2,409 median PnL.

Decision:

- Retain VIX level as diagnostic only.
- Do not implement a VIX-level rule.

### S2 VIX 5D Trend

S2 VIX 5D trend evidence:

- 5D falling VIX: 262 trades, about Rs 762,307 net PnL, about 1.33 PF.
- 5D rising VIX: 303 trades, about Rs 262,844 net PnL, about 1.10 PF.

Cross-strategy caveat:

- S1 showed the opposite pattern: 5D rising VIX had about Rs 645,638 net PnL
  and about 1.29 PF, while 5D falling VIX had about -Rs 161,561 net PnL and
  about 0.91 PF.

Decision:

- Retain VIX 5D change as secondary context.
- Do not generalize it into a cross-strategy rule.

### VIX x Gap

S2 VIX x gap evidence:

- High-VIX `STOP_GAP_HIT`: 19 trades, about -Rs 355,336 net PnL.
- High-VIX `TARGET_GAP_HIT`: 17 trades, about +Rs 562,112 net PnL.

Interpretation:

- High VIX contains both stop-gap losses and target-gap gains.
- Base gap-risk is stronger and clearer than VIX x gap.

Decision:

- Do not implement a VIX x gap filter.

### VIX x Drawdown

S2 VIX x drawdown evidence:

- Moderate drawdown + high VIX: 73 trades, about -Rs 80,885 net PnL, about
  0.88 PF, about 45.21% win rate, and about -Rs 2,242 median PnL.
- Mild drawdown + mid VIX: 62 trades, about -Rs 135,157 net PnL, about
  0.80 PF, about 40.32% win rate, and about -Rs 9,998 median PnL.

Decision:

- VIX x drawdown is the most promising VIX interaction.
- Retain it only as a future pre-registration candidate.
- Do not implement a VIX x drawdown throttle now.

### 2024/2025/2026 S2 VIX Weakness

S2 VIX yearly evidence:

- 2024 high VIX: about -Rs 284,247 net PnL and about 0.48 PF.
- 2024 low VIX: about +Rs 394,203 net PnL and about 2.46 PF.
- 2024 mid VIX: about -Rs 187,272 net PnL and about 0.37 PF.
- 2025 high VIX: about -Rs 44,683 net PnL.
- 2025 low VIX: about -Rs 19,721 net PnL.
- 2025 mid VIX: about -Rs 94,902 net PnL.
- 2026 high VIX: about -Rs 128,103 net PnL and about 0.53 PF.
- 2026 low VIX: about +Rs 3,719 net PnL and about 1.03 PF.
- 2026 mid VIX: about +Rs 28,613 net PnL and about 2.34 PF on only 3 trades.

Decision:

- Treat yearly VIX evidence as diagnostic.
- Do not convert post-hoc yearly VIX patterns into rules.

### VIX Compared With Other Diagnostics

Liquidity remains stronger for S2:

- S2 HIGH liquidity: 271 trades, about Rs 970,422 net PnL, about 1.42 PF,
  about 49.45% win rate, and about -Rs 948 median PnL.
- S2 LOW liquidity: about -Rs 26,697 net PnL and about 0.96 PF.
- S2 MID liquidity: about Rs 27,990 net PnL and about 1.01 PF.

Benchmark regime remains clearer than VIX level:

- S2 strong-positive benchmark: 127 trades, about Rs 660,713 net PnL, about
  1.78 PF.
- S2 strong-negative benchmark: 42 trades, about Rs 268,996 net PnL, about
  2.11 PF.
- S2 ordinary negative benchmark: 191 trades, about -Rs 94,265 net PnL, about
  0.95 PF.

Decision:

- No Phase 36B candidate is invalidated by VIX.
- Liquidity, benchmark regime, drawdown state, rolling R, and gap risk remain
  stronger than VIX as primary risk diagnostics.
- VIX is retained as secondary market context.

---

## Rejected Implementation Decisions

The following are explicitly not approved:

- No risk model implementation now.
- No VIX rule now.
- No dynamic sizing now.
- No liquidity filter now.
- No drawdown throttle now.
- No rolling-R threshold now.
- No benchmark-regime filter now.
- No gap filter now.
- No sector caps.
- No market-cap bucket rule.
- No India VIX standalone rule.
- No symbol include/exclude rule.
- No dynamic sizing optimized by net PnL.
- No production use or production-readiness upgrade.

---

## Retained Future Candidates

Retained diagnostics:

- Liquidity as strongest S2 risk diagnostic.
- Benchmark regime as a strong diagnostic, with caution because prior direct
  context filters failed.
- Drawdown state as a promising cross-strategy throttle diagnostic.
- Gap risk as important but mixed because target-gap gains are also large.
- VIX as secondary diagnostic only.
- VIX x drawdown as a pre-registration candidate.
- Rolling R as promising but high overfit risk.

Possible future branches:

- Cross-strategy pre-registered risk experiment design.
- S2 state x risk input diagnostic design.
- Exact data-quality audit for liquidity if liquidity is elevated toward
  implementation.

The current risk branch should move only to design-only pre-registration if it
continues. Do not pivot directly into S2-only implementation.

---

## Anti-Overfitting Guardrails

- Do not convert diagnostic buckets into filters without pre-registration.
- Do not optimize VIX thresholds after seeing outputs.
- Do not treat static liquidity as point-in-time truth.
- Do not use current/static sector or cap fields as historical controls.
- Do not create symbol include/exclude rules from contributor tables.
- Do not use rolling-R thresholds without strict pre-registration.
- Do not ignore target-gap gains when studying gap-risk losses.
- Do not use entry-date VIX close for next-open entries.
- Do not optimize by final PnL alone.
- Do not turn yearly weakness pockets into production rules without a new,
  pre-registered experiment.

---

## Closeout Decision

Phase 36B/36C closes as a research diagnostic branch.

No risk implementation is approved. No production behavior changes are
approved. The next allowed step, if any, is design-only pre-registration of a
controlled risk experiment.
