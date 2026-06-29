# Cross-Strategy Overlap / Confirmation Audit

## Purpose

This document records the Phase 35B/35C closeout for cross-strategy overlap,
same-day confirmation, and narrow S2/S4 confirmation robustness.

This is a research audit only. It does not approve a voting ensemble, strategy
weights, capital allocation, production behavior, or any implementation change.

---

## Phase 35B Executed-Trade Evidence

Broad executed-trade confirmation was weak or negative.

Core findings:

- S2 confirmed trades were worse than S2 unconfirmed trades.
- S2 confirmed trades: 99 trades, about 0.893 PF, about -Rs 1.07L net PnL, and
  about 40.4% win rate.
- S2 unconfirmed trades: 478 trades, about 1.260 PF, about +Rs 10.79L net PnL,
  and about 46.2% win rate.
- Broad 2+ strategy confirmation was also weak: 16 trades, about 0.766 PF, and
  about -Rs 38.5K net PnL.
- Same-day executed-trade overlap was sparse: only 11 same-symbol/same-day
  overlap rows across all strategies, and only 8 involved S2.

Decision:

- Drop broad voting ensemble research from the current branch.
- Drop generic 2+ strategy consensus as an implementation candidate.
- Do not treat sparse executed-trade overlap as evidence for ensemble approval.

---

## Phase 35B Signal-Overlap Evidence

Signal overlap existed and is useful diagnostically, but it did not translate
into approval for a realized portfolio ensemble.

Signal-overlap findings:

- 1,654 same-symbol/same-date signal overlap events.
- 200 symbols.
- 894 dates.
- 2-strategy consensus dominated with 1,624 events.
- 3+ consensus was rare with 30 events.
- No 4+ or 5-strategy consensus appeared.

Strongest signal-overlap pairs:

| Pair | Signal-overlap events |
| --- | ---: |
| S4-S5 | 398 |
| S2-S3 | 372 |
| S2-S4 | 279 |
| S2-S5 | 274 |
| S1-S2 | 212 |

Interpretation:

- Signal overlap is a diagnostic map of where strategy families observe the
  same symbol/date.
- Signal overlap is not realized PnL and must not be substituted for executed
  trade performance.
- The signal-overlap table can inform later risk-model, universe, or regime
  research, but it does not authorize voting, weights, or portfolio blending.

---

## Phase 35C S2/S4 Confirmation Robustness

Phase 35C pre-registered a trading-session lookback robustness audit to test
whether the narrow S2/S4 finding from Phase 35B survived stricter confirmation
checks.

S2/S4 remained positive across 0, 1, 3, and 5 trading-session lookbacks, but
quality deteriorated as sample size became more usable:

| Lookback | Trades | PF | Net PnL | Interpretation |
| --- | ---: | ---: | ---: | --- |
| 0 sessions | 5 | inf | about +Rs 104.8K | Too small to trust |
| 1 session | 10 | about 3.13 | about +Rs 100.9K | Too small to trust |
| 3 sessions | 35 | about 1.54 | about +Rs 161.3K | Positive but limited |
| 5 sessions | 54 | about 1.23 | about +Rs 113.3K | Most usable, not clean |

The 5-session result had 54 trades, about 42.6% win rate, about -Rs 7.66K
median PnL, and about +Rs 2.10K average PnL. Positive PF survived, but trade
quality was not clean.

Stability and concentration findings:

- Yearly stability was weak: strong in 2020, 2021, and 2023; bad in 2022;
  weak/negative in 2024; bad in 2025; and one negative trade in partial 2026.
- S2/S4 did not fix S2's fragile years.
- The 5-session sample had 54 trades across 36 symbols.
- Top 5 winners contributed more than 2x total net PnL, making the finding
  moderately fragile despite not being one-symbol-only.
- S4 was diversifying versus S2, with S2-S4 equity correlation about 0.275, but
  S4 standalone drawdown was weak at about -39.1%.

Controls:

- S1 was almost flat at 5 sessions.
- S5 was clearly bad.
- S3 became competitive at 5 sessions with 63 trades, about 1.22 PF, and about
  +Rs 137.2K net PnL.
- S4 is therefore not uniquely proven as the confirmer.

Decision:

- Retain S2/S4 only as `PROMISING_DIAGNOSTIC` / parked observation.
- Do not approve S2/S4 as an ensemble, filter, allocation rule, or production
  rule.

---

## Future / After-Entry Confirmation Evidence

Future or after-entry confirmation was diagnostic only and is not implementable
as signal-time behavior.

Observed diagnostic result:

- 120 trades.
- About 1.04 PF.
- About +Rs 53.1K net PnL.
- About -Rs 8.14K median PnL.

Interpretation:

- Future confirmation may help describe what happened after entry.
- It cannot be used as an implementable signal-time rule.
- Its weak median and near-flat PF do not justify a production or ensemble
  decision.

---

## Rejected Implementation Decisions

Rejected or closed for now:

- Broad voting ensemble: dropped / not supported.
- Generic 2+ strategy consensus: dropped / not supported.
- S2/S4 confirmation: retained only as diagnostic and parked observation.
- No ensemble implementation.
- No capital allocation change.
- No strategy weights.
- No production approval.
- No immediate continuation into another voting variant.

Anti-overfitting cautions:

- Do not cherry-pick S2/S4 0-session or 1-session results.
- Do not introduce new lookbacks after seeing the Phase 35C results.
- Do not use future or after-entry confirmation as an implementable rule.
- Do not optimize by net PnL alone.
- Do not treat signal overlap as realized PnL.
- Do not rescue weak strategies using post-hoc strategy combinations.

Next direction:

- The current S1-S5 strategy stack remains benchmark/research infrastructure,
  not production-ready alpha.
- The ensemble branch is closed for now.
- Preferred next work should move toward Cross-Strategy Risk Model Input
  Discovery, Universe/Regime Segmentation Research, or S2 Risk Model Research.
