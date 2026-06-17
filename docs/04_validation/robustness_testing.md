# Robustness Testing Notes

## Purpose

This document records robustness conclusions and open robustness requirements.

---

## S2 Robustness Conclusion

S2 Markov research through Phase 27J found evidence of edge, but not enough robustness for production acceptance.

Retained S2 benchmarks:

- Safer benchmark: `exclude_ret_down + ranking none`
- Higher-return research candidate: `exclude_ret_down + clean_state_v1`

The higher-return candidate is useful for comparison, but remains fragile:

- Net PnL: about Rs 12.32L
- CAGR: about 13.52%
- Max drawdown: about 33.94%
- Profit factor: about 1.223
- 2025 PnL: about -Rs 7.50L

---

## 2025 Failure Audit Robustness Finding

The 2025 loss was not one bad symbol and not one isolated month.

It recurred across multiple months and concentrated in a shallow bullish-pullback regime:

- `RET_UP|VOL_MID|DD_SHALLOW|LOW_FAR_FROM_LOW`
- `RET_UP|VOL_MID|DD_SHALLOW|LOW_MID_RANGE`

Context associated with failure:

- Stock above SMA50.
- Stock SMA50 slope positive.
- Nifty above SMA50.
- Nifty SMA50 slope positive.
- Shallow drawdown 0 to -5%.

Interpretation:

S2 was fooled by conditions that looked like healthy pullbacks but did not mean-revert reliably in 2025.

---

## Guard Variant Robustness Finding

Guard variants reduced some targeted 2025 loss, but weakened total profitability too much.

Rejected as benchmarks:

- `avoid_shallow_uptrend_pullback_v1`
- `exclude_ret_down + avoid_shallow_uptrend_pullback_v1`
- `exclude_ret_down + 2025_guard_v1`
- `exclude_ret_down + 2025_guard_v1 + signal-time context`

Robustness interpretation:

- A simple state exclusion or penalty did not solve the broader regime issue.
- Losses shifted to replacement candidates.
- Continued S2-only tuning risks overfitting the 2025 failure pocket.

---

## Future Robustness Work

Parked future work:

- Better market-regime detector.
- Regime-aware exposure reduction rather than only candidate penalties.
- Capacity-aware ranking validated across independent strategy families.
- Sector/industry conditioning if reliable metadata becomes available.
- S2 or S3 revisit only after additional independent strategy evidence or a materially new regime/ranking framework.
