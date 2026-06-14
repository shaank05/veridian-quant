# Veridian Quant v2 Research Roadmap

## Current Research State

Veridian Quant v2 has moved beyond the initial S1 implementation into a broader research framework with audited universes, strategy variants, capacity diagnostics, and a second standalone strategy family.

The current benchmark is:

- Strategy: `S1_BASELINE`
- Universe: audited 200-symbol research universe
- Period: 2020-01-01 to 2026-04-30
- Net PnL: approximately +579K
- Gross profit: approximately +4.64M
- Gross loss: approximately -4.06M
- Profit factor: approximately 1.143
- Max drawdown: approximately 23.52%
- Trades: 535
- Total signals: 7,476
- Rejected signals: 6,941
- Portfolio capacity rejections: 6,726

S1 is the current benchmark. It is not the final strategy.

S2 Markov State Transition has been implemented as a standalone strategy family, but it has not yet been benchmarked on the 200-symbol research universe and has not been compared with S1.

---

## Completed and Current Phases

### Phase 1-22: S1 Foundation and Portfolio Backtesting

Implemented the v2 S1 Z-score mean-reversion baseline, reusable trade setup, sizing, execution, exit resolution, PnL, ledger, exporters, and core diagnostics.

### Phase 23: S1 Filter Variants

Implemented S1 hard-filter variants to test whether signal-date context could improve baseline mean reversion.

Outcome:

- Variants were useful research probes.
- Hard filters did not generalize reliably across the broader research universe.

### Phase 24: Strategy Variant Comparison Reports

Added reporting to compare S1 variants across summary metrics, yearly performance, exit reasons, rejection reasons, symbol concentration, and derived deltas.

Outcome:

- Broader reporting made variant fragility easier to detect.
- The comparison framework remains useful for future strategy families.

### Phase 25A: v2 Price Ingestion Foundation

Added the v2 price ingestion foundation and dry-run-safe ingestion workflow.

### Phase 25B: Price Data Quality Audit

Added price data quality audit reports for missing data, stale data, bad OHLC rows, volume issues, and eligibility checks.

### Phase 25C: Raw NSE Equity Candidate Universe

Built the raw NSE equity candidate universe workflow.

### Phase 25D: Resumable Ingestion and Network Recovery

Added resumable ingestion behavior and network recovery modes for robust data loading.

### Phase 25E: Audited Research Universe Builder

Implemented audited research universe construction using eligibility and quality rules.

### Phase 25F: 100 vs 200 Baseline Universe Comparison

Compared audited 100-symbol and 200-symbol S1 baselines.

Outcome:

- The 200-symbol audited research universe materially outperformed the 100-symbol universe.
- Universe breadth became a major research finding.

### Phase 26A: Capacity-Aware Candidate Ranking v1

Implemented `candidate-ranking s1_v1` to rank same-day S1 candidates under portfolio capacity constraints.

Outcome:

- The ranking implementation was technically valid.
- It underperformed the unranked `S1_BASELINE`.
- S1 ranking optimization is parked until there is more evidence.

### Phase 26B: All-Signal Opportunity Diagnostics and Counterfactual Rejected-Signal Simulation

Added diagnostics for all generated signals, accepted trades, rejected signals, capacity rejections, same-day pools, and counterfactual outcomes for rejected capacity signals.

Outcome:

- S1 generates far more valid signals than the portfolio can take.
- Capacity rejections are the dominant rejection reason.
- Rejected capacity signals contain hidden winners, but average rejected capacity edge appears weak.
- These diagnostics support future ranking and voting research, but do not alter actual portfolio performance.

### Phase 27A: Standalone S2 Markov State Transition Strategy

Implemented S2 as an independent strategy family.

Outcome:

- S2 signal generation is implemented.
- S2 has its own Markov portfolio runner.
- S2 reuses shared setup, sizing, execution, exit, PnL, ledger, and exporter components.
- S2 is not an S1 filter.
- S2 is not yet benchmarked on research200.

### Phase 27B: Documentation Refresh

Current phase.

Objective:

- Update documentation to reflect the current S1 benchmark, S1 findings, all-signal diagnostics, and S2 introduction before running S2 on the research200 universe.

---

## Active Research Position

The current evidence says:

- S1 has positive benchmark evidence on the audited 200-symbol research universe.
- S1 hard-filter variants are not yet robust enough to replace the baseline.
- S1 candidate ranking v1 did not improve the portfolio.
- Portfolio capacity is a central bottleneck.
- S2 must be evaluated independently before any combination with S1 is considered.

---

## Parked / Future Work

The following are future research directions, not accepted production rules:

- S1 candidate ranking v2
- Feature-combination diagnostics
- FFT strategy
- Wavelet strategy
- Markov/S1 voting layer
- Meta-ranking / capital allocation layer
- 2026 defensive regime layer

These ideas may be researched later only after standalone evidence and auditability requirements are satisfied.
