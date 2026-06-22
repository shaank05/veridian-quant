# Monte Carlo Robustness Audit

## 1. Purpose

This Phase 31D audit compares the first common Monte Carlo robustness evidence
for the retained S1, S2, S3, and S4 ATR benchmarks. It ranks the tested runs by
return and downside behavior under a frozen, like-for-like protocol.

Monte Carlo is not a strategy. It does not generate buy or sell signals, alter
the historical backtests, or approve a strategy for production. It tests the
observed completed-trade distribution under alternative ordering and
resampling.

## 2. Scope

The audit covers the Phase 31C standalone validation outputs for:

- S1: `S1_BASELINE` on Research200.
- S2: the retained Markov benchmark using `exclude_ret_down` and no candidate
  ranking.
- S3: `S3_STRONG_TREND_ABOVE_SMA50_V1`.
- S4: `S4_ATR_COMPRESSION_BREAKOUT_V1`, retained only as a weak benchmark.

S2's higher-return `clean_state_v1` candidate, rejected S4 variants, and RAWRS
overlays are outside this comparison. RAWRS remains diagnostic-only and is not
ranked as a production overlay.

## 3. Inputs Reviewed

The following Phase 31C summary files were reviewed:

- `reports/v2/validation/monte_carlo/s1_2020_2026_research200_baseline/shuffle/monte_carlo_summary.csv`
- `reports/v2/validation/monte_carlo/s1_2020_2026_research200_baseline/bootstrap/monte_carlo_summary.csv`
- `reports/v2/validation/monte_carlo/s2_markov_2020_2026_research200_exclude_ret_down/shuffle/monte_carlo_summary.csv`
- `reports/v2/validation/monte_carlo/s2_markov_2020_2026_research200_exclude_ret_down/bootstrap/monte_carlo_summary.csv`
- `reports/v2/validation/monte_carlo/s3_trend_pullback_strong_trend_above_sma50_v1/shuffle/monte_carlo_summary.csv`
- `reports/v2/validation/monte_carlo/s3_trend_pullback_strong_trend_above_sma50_v1/bootstrap/monte_carlo_summary.csv`
- `reports/v2/validation/monte_carlo/s4_atr_compression_v1/shuffle/monte_carlo_summary.csv`
- `reports/v2/validation/monte_carlo/s4_atr_compression_v1/bootstrap/monte_carlo_summary.csv`

Each summary represents 10,000 simulations using starting equity of
₹1,000,000, random seed 42, and drawdown thresholds of 10%, 20%, 30%, and 40%.
The inputs contained 535 S1 trades, 577 S2 trades, 500 S3 trades, and 559 S4
ATR trades.

## 4. Method Summary

The standalone validator consumed realized `net_pnl` from completed trade logs.
For each simulated sequence, it reconstructed additive equity from the common
starting equity and measured final equity, maximum drawdown, threshold breaches,
and losing streaks.

The protocol used two complementary modes:

- Shuffle: random permutation without replacement.
- Bootstrap: random sampling with replacement, holding simulated trade count
  equal to the source trade count.

The same simulation count, seed, starting equity, and threshold set were used
for all four benchmarks. This supports comparison but does not remove differences
in strategy trade count, outliers, chronology, or regime exposure.

## 5. How to Interpret Shuffle Versus Bootstrap

Shuffle preserves the exact completed trade set. Because the Phase 31 baseline
adds fixed absolute trade PnL, every shuffle has the same aggregate net PnL and
final equity. Shuffle final-equity median, p05, and p95 are therefore identical
by design. Its useful evidence is path-dependent: drawdown, ruin timing, and
losing-streak risk under alternative orderings.

Bootstrap samples trades with replacement. It changes the simulated mix of
winners and losers, so it creates a distribution of final equity as well as
paths. It is useful for empirical distribution uncertainty and a limited
future-like stress, but it is not a forecast. Independent bootstrap also breaks
serial, calendar, capacity, and regime dependence.

Neither mode proves future profitability. Both are conditional on the observed
trade sample and the fixed-PnL reconstruction assumptions.

## 6. Strategy-Level Results

| Strategy | Nominal net PnL | Bootstrap median equity | Bootstrap p05 equity | Bootstrap loss probability | Bootstrap DD >=20% | Bootstrap DD >=30% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| S1 | ₹579,453.90 | ₹1,584,589.90 | ₹885,827.29 | 8.62% | 60.80% | 26.17% |
| S2 | ₹971,715.21 | ₹1,972,576.26 | ₹1,081,458.33 | 3.48% | 63.96% | 27.64% |
| S3 | ₹315,941.11 | ₹1,315,259.59 | ₹784,099.46 | 16.25% | 54.02% | 20.94% |
| S4 ATR | ₹165,312.15 | ₹1,160,234.82 | ₹467,969.43 | 35.30% | 84.74% | 56.62% |

## 7. S1 Robustness Summary

- Nominal net PnL: ₹579,453.90.
- Shuffle final equity median/p05/p95: ₹1,579,453.90 / ₹1,579,453.90 /
  ₹1,579,453.90.
- Shuffle worst maximum drawdown: 63.32%.
- Shuffle losing-streak p95/worst: 13 / 28 trades.
- Bootstrap final equity median/p05/p95: ₹1,584,589.90 / ₹885,827.29 /
  ₹2,284,372.69.
- Bootstrap probability of ending below starting equity: 8.62%.
- Bootstrap probability of maximum drawdown >=20% / >=30%: 60.80% / 26.17%.
- Bootstrap losing-streak p95/worst: 13 / 23 trades.

S1 is the second-strongest tested benchmark. Its bootstrap median remains
attractive, but its p05 falls below starting equity and its sequence-dependent
drawdown tail is material. It remains a useful baseline, not a production-ready
strategy.

## 8. S2 Robustness Summary

- Nominal net PnL: ₹971,715.21.
- Shuffle final equity median/p05/p95: ₹1,971,715.21 / ₹1,971,715.21 /
  ₹1,971,715.21.
- Shuffle worst maximum drawdown: 78.07%.
- Shuffle losing-streak p95/worst: 13 / 23 trades.
- Bootstrap final equity median/p05/p95: ₹1,972,576.26 / ₹1,081,458.33 /
  ₹2,865,041.03.
- Bootstrap probability of ending below starting equity: 3.48%.
- Bootstrap probability of maximum drawdown >=20% / >=30%: 63.96% / 27.64%.
- Bootstrap losing-streak p95/worst: 14 / 22 trades.

S2 ranks strongest overall because it combines the highest nominal and median
bootstrap equity with the lowest loss probability. It is the only tested
strategy whose bootstrap p05 remains above starting equity. This ranking does
not erase known S2 regime fragility: its 78.07% shuffle worst drawdown shows that
trade sequence risk remains meaningful.

## 9. S3 Robustness Summary

- Nominal net PnL: ₹315,941.11.
- Shuffle final equity median/p05/p95: ₹1,315,941.11 / ₹1,315,941.11 /
  ₹1,315,941.11.
- Shuffle worst maximum drawdown: 56.02%.
- Shuffle losing-streak p95/worst: 14 / 23 trades.
- Bootstrap final equity median/p05/p95: ₹1,315,259.59 / ₹784,099.46 /
  ₹1,870,463.65.
- Bootstrap probability of ending below starting equity: 16.25%.
- Bootstrap probability of maximum drawdown >=20% / >=30%: 54.02% / 20.94%.
- Bootstrap losing-streak p95/worst: 14 / 22 trades.

S3 has somewhat lower drawdown-threshold probabilities than S1 and S2, but the
benefit comes with substantially weaker return evidence and a higher probability
of finishing below starting equity. It remains a weak/moderate benchmark and is
not production-ready.

## 10. S4 ATR Robustness Summary

- Nominal net PnL: ₹165,312.15.
- Shuffle final equity median/p05/p95: ₹1,165,312.15 / ₹1,165,312.15 /
  ₹1,165,312.15.
- Shuffle worst maximum drawdown: 76.17%.
- Shuffle losing-streak p95/worst: 15 / 28 trades.
- Bootstrap final equity median/p05/p95: ₹1,160,234.82 / ₹467,969.43 /
  ₹1,866,552.47.
- Bootstrap probability of ending below starting equity: 35.30%.
- Bootstrap probability of maximum drawdown >=20% / >=30%: 84.74% / 56.62%.
- Bootstrap losing-streak p95/worst: 15 / 29 trades.

S4 ATR ranks weakest. It has the lowest nominal PnL, worst bootstrap p05 equity,
highest loss probability, highest >=30% drawdown probability, and longest
bootstrap losing-streak tail. It should remain a weak benchmark only, not a
production candidate. The rejected S4 Range and parked S4 Entropy variants are
not rehabilitated by this audit.

## 11. Cross-Strategy Ranking

| Rank | Strategy | Robustness interpretation |
| ---: | --- | --- |
| 1 | S2 retained Markov benchmark | Strongest combined return and Monte Carlo evidence; primary benchmark for future comparisons |
| 2 | S1 baseline | Good return evidence, but bootstrap p05 is below starting equity |
| 3 | S3 retained trend-pullback benchmark | Lower drawdown probabilities in places, but weaker edge and higher loss probability than S1/S2 |
| 4 | S4 ATR compression baseline | Weakest return and downside evidence; weak benchmark only |

This is a comparative validation ranking, not a production-approval ladder.

## 12. Return/Risk Interpretation

S2 offers the best tested return/risk balance: its bootstrap downside p05 still
preserves capital while its median and nominal results lead the group. S1 is a
credible second benchmark. S3's lower return does not buy enough reduction in
loss probability to overtake S1. S4 ATR's modest return is not commensurate with
its downside distribution.

## 13. Drawdown-Risk Interpretation

All four strategies show meaningful path risk. The worst shuffle drawdowns range
from 56.02% to 78.07%, demonstrating that favorable aggregate PnL does not imply
a tolerable equity path. S3 has the lowest observed >=20% and >=30% bootstrap
breach probabilities, but this does not offset its weaker terminal-return
distribution. S4 ATR is unambiguously weakest on drawdown risk.

## 14. Loss-Probability Interpretation

Bootstrap probability of ending below ₹1,000,000 ranks S2 (3.48%), S1 (8.62%),
S3 (16.25%), then S4 ATR (35.30%). These are empirical resampling frequencies,
not calibrated real-world probabilities. S2's low value is favorable evidence,
not a guarantee.

Bootstrap ruin-or-below-zero frequency was 0.00% for S1, 0.06% for S2, 0.01%
for S3, and 0.64% for S4 ATR; shuffle frequency was 0.00% for all four. The
current summaries do not expose the proposed 25% and 50% near-ruin equity-floor
probabilities, so this audit does not infer or rank those unmeasured metrics.

## 15. Losing-Streak Interpretation

The bootstrap p95 longest losing streak is 13 trades for S1, 14 for S2 and S3,
and 15 for S4 ATR. Worst observed bootstrap streaks range from 22 to 29 trades.
Operational risk limits and researcher expectations should assume materially
longer losing runs than the chronological backtest may have displayed. S4 ATR
again has the weakest streak profile.

## 16. Key Conclusions

- S2 is the strongest current retained benchmark under the Phase 31 protocol.
- S2 alone has bootstrap p05 final equity above starting equity, and it has the
  lowest bootstrap loss probability.
- S1 ranks second and remains useful as the original v2 baseline.
- S3 provides weak/moderate benchmark evidence and remains parked.
- S4 ATR remains a weak benchmark only.
- Sequence-dependent drawdown is meaningful even for S2.
- No strategy is production-approved from Monte Carlo evidence alone.

## 17. Strategy Status Updates

- **S2:** strongest retained benchmark by combined return and Monte Carlo
  robustness; primary robustness benchmark for future strategy comparisons;
  frozen, regime-fragile, and not production-ready.
- **S1:** useful baseline and second in the current robustness ranking; not
  production-ready.
- **S3:** retained weak/moderate benchmark; parked and not production-ready.
- **S4 ATR:** weak benchmark only; not a production candidate. S4 Range remains
  rejected and S4 Entropy remains parked/not promoted.
- **RAWRS:** diagnostic-only; not included in the strategy robustness ranking as
  a production overlay.

## 18. Limitations

- Monte Carlo cannot prove future profitability or production suitability.
- Results are conditional on historical completed trades and their outliers.
- Independent bootstrap ignores serial dependence, regime clustering, calendar
  structure, overlapping exposure, and portfolio capacity interactions.
- Reordered fixed PnL does not reproduce equity-dependent sizing or compounding.
- Shuffle paths may not be chronologically or operationally feasible.
- A common seed and protocol aid comparison but do not make strategy samples
  identical.
- The audit does not include walk-forward, regime-split, parameter-sensitivity,
  capacity, liquidity, or market-impact evidence.
- The current summary files do not report the proposed near-ruin equity-floor
  probabilities.
- No universal pass/fail threshold is established from these four observations.

## 19. Recommended Next Actions

- Preserve Phase 31 Monte Carlo as standard post-backtest validation for future
  strategies.
- Use the retained S2 run as the primary robustness benchmark for future S5
  comparisons.
- Do not promote any current strategy to production.
- Direct the next major independent strategy research toward S5 relative
  strength / momentum rotation rather than more near-term S2/S3/S4 threshold
  tuning.
- Later extend validation with VaR/CVaR, Sharpe/Sortino, drawdown duration,
  risk-of-ruin analysis, walk-forward testing, regime splits, parameter
  sensitivity, capacity stress, and block/regime-aware bootstrap.
- Keep Kronos, TradingAgents, and other external-model work parked until it can
  meet the same backtest and robustness standards.

## 20. References

- `docs/04_validation/portfolio_robustness_validation.md`
- `docs/04_validation/backtest_methodology.md`
- `docs/02_audits/strategy_audit_master.md`
- `docs/02_audits/s1_audit.md`
- `docs/02_audits/s2_audit.md`
- `docs/02_audits/s3_audit.md`
- `docs/02_audits/s4_audit.md`
- `docs/00_foundation/v2_research_roadmap.md`
- `docs/05_decisions/decision_log.md`
- `docs/06_intelligence/i1_rawrs_combined_evidence_audit.md`
