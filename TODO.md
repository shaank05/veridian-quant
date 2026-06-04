# 🏛️ Project BuddhAditya: Quantitative Roadmap

## 🎯 Current Strategic Direction
The platform is evolving from a traditional signal-based scanner into a:

# Regime-Adaptive Conditional Alpha Selection Engine

focused on:
- Indian equity swing trading,
- probabilistic opportunity ranking,
- adaptive execution filtering,
- volatility-aware capital deployment,
- cross-regime asymmetry extraction.

The architecture direction is now centered around:
- conditional feature interpretation,
- probabilistic ensemble orchestration,
- regime-aware signal modulation,
- adaptive statistical execution geometry.

The core discovery driving all future development:

```text
Feature Utility Is Regime Dependent
```

NOT:

```text
Feature Utility Is Constant
```

---

# ✅ Completed (Stage 1 - 2.1: Statistical, Functional & Noise Foundations)

- [x] **Infrastructure**: DB Connection Pool and SQLAlchemy Engine integration.
- [x] **Data Persistence**: `instruments` and `prices_ohlc` table architecture.
- [x] **Vectorized Math**: Implementation of `calculate_z_score` and `calculate_expected_move` (ATR).
- [x] **Core Analytics**: `EquityScanner` logic for Z-Score mean reversion ($Z < \text{Threshold}$).
- [x] **Scheduling**: `equity_recommendation_scan.py` for automated nightly population.
- [x] **Backtesting Infrastructure**: Parallel-matrix logging via `backtest_engine.py` for comprehensive historical outcome verification.
- [x] **Macro Context (v1.0)**: Low-VIX Macro Alpha Mode Matrix implementation.
- [x] **Macro Context (v1.1 - Experiment)**: Nifty Daily Z-Score Threshold Overlay (*Failed: Dropped due to severe alpha choke during secular bull runs*).
- [x] **Macro Context (v1.2)**: Normalized 50 SMA Strict Percentage Slope Velocity Hurdle ($\ge 0.10\%$). Safely stabilizes the 2025 distribution decay while maintaining high capital efficiency.
- [x] **Stage 2: Spectral Analysis (FFT Timing)**: Fast Fourier Transform (`check_cycle_phase`) integrated into execution pipelines to prevent catching falling knives while cyclical velocity vectors point downward.
- [x] **Stage 2.1: Shannon Information Entropy Noise Gate**: Vectorized calculation (`calculate_shannon_entropy`) live in both production scanning and backtesting loops. Blocks trades on assets showing structural chaos ($H(X) > \text{Threshold}$), ensuring cyclical calculations operate only on structured institutional setups.
- [x] **Wavelet Research Discovery**: Identified non-stationary feature utility across market regimes using backtest audit decomposition (2024–2026).
- [x] **Architectural Discovery**: Confirmed that static CWT thresholding destroys asymmetry during low-volatility institutional pullback regimes.
- [x] **Ensemble Validation**: Confirmed parallel probabilistic architecture is superior to sequential hard-filter chains.
- [x] **Bug Fix**: Fixed `np.float64` engine-level schema compilation warnings and UTC-to-IST fallback loop issues inside `backtest_engine.py`.
- [x] **Workspace Recovery**: Cleared corrupted `.gitignore` binary trailing sequences and stabilized repository untracked paths.

---

# 🚀 Immediate Action Items (Current Highest Priority)

## 🌊 Priority 1 — RAWRS (Regime-Aware Adaptive Wavelet Response Surface)

### Objective
Replace the destructive binary CWT execution shield with a:
- regime-aware,
- probabilistic,
- multi-scale,
- non-linear confidence modulation engine.

### Core Architectural Shift
OLD:

```python
if wavelet_intensity < threshold:
    reject_trade
```

NEW:

```text
CWT modifies execution conviction probabilistically
```

### Implementation Goals
- [ ] Replace scalar wavelet intensity with multi-scale wavelet decomposition.
- [ ] Add micro/meso/macro energy decomposition.
- [ ] Add spectral entropy extraction.
- [ ] Add wavelet coherence calculations.
- [ ] Build adaptive regime-conditioned wavelet scoring engine.
- [ ] Remove hard binary CWT veto logic.
- [ ] Introduce continuous conviction modulation.
- [ ] Preserve existing DB/reporting schema compatibility.
- [ ] Validate across 2024, 2025, and 2026 market distributions.

### Expected Outcome
- Preserve low-volatility institutional pullback winners.
- Preserve explosive breakout asymmetry.
- Suppress turbulent fakeout reversals.
- Improve regime stability.
- Reduce asymmetry destruction.

---

## 📊 Priority 2 — Conviction-Based Position Sizing Engine

### Objective
Replace static capital bricks with:
- dynamic exposure scaling,
- risk-equalized allocation,
- conviction-aware sizing.

### Implementation Goals
- [ ] Replace fixed ₹100,000 deployment model.
- [ ] Introduce ATR risk-normalized sizing.
- [ ] Scale exposure using Ensemble Conviction Score.
- [ ] Reduce capital during high entropy/turbulence states.
- [ ] Increase capital during cohesive high-alignment setups.

### Proposed Exposure Model
| Conviction Score | Capital Allocation |
|---|---|
| < 40 | 25% Size |
| 40–70 | 50% Size |
| > 70 | 100% Size |

### Expected Outcome
- Sharpe ratio improvement.
- Drawdown compression.
- Better capital efficiency.
- Exposure normalization across volatility regimes.

---

## 🎯 Priority 3 — Option C (Micro-Entry Trigger Layer)

### Objective
Separate:
- daily statistical discovery,
FROM:
- intraday execution timing.

### Implementation Goals
- [ ] Build `high_alert_watchlist` pipeline.
- [ ] Store daily scanner candidates.
- [ ] Add 15m/1h confirmation engine.
- [ ] Add VWAP recovery trigger.
- [ ] Add hourly breakout confirmation.
- [ ] Add micro-structure reversal detection.

### Expected Outcome
- Better execution timing.
- Lower adverse excursion.
- Reduced premature entry risk.
- Improved capital rotation efficiency.

---

## 🧪 Priority 4 — RAWRS Validation Framework

### Mandatory Validation Runs

- [ ] Baseline engine (No CWT modulation).
- [ ] Old hard-threshold CWT filter.
- [ ] RAWRS probabilistic modulation.
- [ ] RAWRS + conviction-based sizing.

### Evaluation Metrics
- Profit Factor
- Expectancy
- Exposure Efficiency
- Drawdown Compression
- Capital Efficiency
- Regime Stability

---

# 🗺️ Quant Architecture Evolution Roadmap

---

# 🌊 Stage 2.2 — RAWRS (Wavelet Evolution Layer)

## Architectural Position
RAWRS becomes:
- the probabilistic spectral intelligence layer,
NOT:
- a hard execution filter.

## Mathematical Components
- Continuous Wavelet Transform (CWT)
- Multi-scale energy decomposition
- Spectral entropy topology
- Coherence extraction
- Regime-adaptive scoring surfaces

## Core Metrics
| Metric | Meaning |
|---|---|
| Micro Energy | High-frequency turbulence |
| Meso Energy | Transitional sponsorship |
| Macro Energy | Institutional directional participation |
| Spectral Entropy | Structural fragmentation |
| Coherence | Trend sponsorship quality |

## Expected Evolution
Future RAWRS versions may eventually:
- replace FFT entirely,
- become the dominant temporal-frequency intelligence layer.

---

# 🎭 Stage 3 — Markov Regime Evolution Layer

## Current Status
Current Markov implementation is:
- directionally strong,
- but structurally underpowered.

## Existing Strength
Models:
- adverse state persistence,
- probability of remaining trapped in negative structure.

## Current Weakness
Current implementation likely uses:
- hard state bins,
- discrete transitions,
- manually segmented boundaries.

## Planned Upgrade Path
- [ ] Hidden Markov Models (HMM).
- [ ] Regime-switching Gaussian mixtures.
- [ ] Latent state discovery.
- [ ] Continuous probabilistic transitions.

## Goal
Allow market states to:
- emerge organically,
- instead of being manually bucketed.

---

# 🎲 Stage 4 — Monte Carlo Path Intelligence

## Objective
Move from:

```text
Signal Detection
```

toward:

```text
Probability Distribution Forecasting
```

## Planned Features
- [ ] 10,000-path Monte Carlo simulations.
- [ ] Probability-of-Touch (POT) estimation.
- [ ] Dynamic TP/SL probability modeling.
- [ ] ATR-adjusted trajectory simulation.

## Goal
Estimate:
- probability target hits before stop-loss.

---

# 🧠 Stage 5 — Adaptive Ensemble Intelligence Layer

## Current Status
The ensemble architecture is currently the strongest part of the system.

## Existing Strength
Correctly uses:
- parallel evidence gathering,
- concurrent feature evaluation,
- probabilistic aggregation.

## Current Weakness
Current ensemble still relies heavily on:
- equal-weight voting,
- binary node outputs.

## Planned Evolution
- [ ] Conditional feature weighting.
- [ ] Bayesian evidence fusion.
- [ ] Meta-labeling.
- [ ] Adaptive interaction surfaces.
- [ ] Regime-aware node weighting.

## Strategic Goal
Transition from:

```text
Signal Confirmation
```

to:

```text
Conditional Alpha Ranking
```

---

# 🏦 Indian Equity Market Structural Expansion

## Critical Discovery
Indian equities are NOT one statistical universe.

The current engine incorrectly treats:
- all stocks,
- all sectors,
- all volatility structures,

as statistically homogeneous.

This is mathematically incorrect.

---

# 🧩 Future Expansion — Hierarchical Regime Modeling

Future architecture must simultaneously model:

| Layer | Purpose |
|---|---|
| Market Regime | Macro volatility/trend structure |
| Sector Regime | Industry-specific dynamics |
| Stock Personality | Individual behavioral profile |

---

# 🏭 Sector Regime Intelligence Layer

## Why This Matters
Different Indian sectors exhibit radically different statistical behavior.

| Sector | Typical Statistical Behavior |
|---|---|
| FMCG | smooth low-volatility mean reversion |
| PSU Banks | violent expansion/reversion |
| Defense | momentum persistence |
| IT | macro-beta cyclical structure |
| Railways | speculative reflexive expansion |
| Small-cap Pharma | discontinuous gap structure |

## Planned Features
- [ ] Sector relative strength.
- [ ] Sector momentum slope.
- [ ] Sector volatility state.
- [ ] Sector entropy structure.
- [ ] Sector breadth analysis.

## Future DB Requirements
Potential future table:

```text
sector_regime_metrics
```

Suggested fields:
- sector_name
- timestamp
- sector_index_close
- sector_slope
- sector_volatility
- sector_relative_strength
- sector_entropy

---

# 🧬 Stock Personality Intelligence Layer

## Objective
Every stock has persistent behavioral tendencies.

Examples:

| Stock | Dominant Personality |
|---|---|
| HDFC Bank | smooth institutional mean reversion |
| HAL | explosive trend persistence |
| BEL | momentum continuation |
| Nestle | defensive compression |
| Suzlon | chaotic speculative turbulence |

## Planned Features
- [ ] Volatility classification.
- [ ] Trend persistence scoring.
- [ ] Gap frequency analysis.
- [ ] Mean-reversion strength profiling.
- [ ] Entropy baseline modeling.
- [ ] Spectral fingerprint clustering.

## Future DB Requirements
Potential future table:

```text
stock_behavioral_profiles
```

Suggested fields:
- instrument_key
- avg_volatility
- entropy_baseline
- trend_persistence_score
- gap_frequency
- mean_reversion_strength
- wavelet_profile
- regime_cluster

---

# 📈 Cross-Sectional Alpha Ranking Engine

## Current Engine Question

```text
Should we buy this stock?
```

## Future Engine Question

```text
Which opportunities are best relative to all others?
```

## Planned Features
- [ ] Cross-sectional opportunity ranking.
- [ ] Portfolio-aware signal prioritization.
- [ ] Exposure overlap reduction.
- [ ] Alpha decay monitoring.
- [ ] Relative asymmetry scoring.

## Future DB Requirements
Potential future tables:
- signal_rank_history
- portfolio_exposure_matrix
- factor_correlation_cache
- alpha_decay_tracking

---

# 🔧 Infrastructure & Execution Roadmap

- [ ] **Data Refill**: Run `PriceIngestor` with `HISTORICAL_LOOKBACK = 14` to bridge the April–May 2026 gap.
- [ ] **Integrity Guard**: Add a daily check for 0-volume candles on trading days to prevent false Z-score signals.
- [ ] **Schema Evolution**: Execute `ALTER TABLE` in PuTTy to add `exchange_token`, `trading_symbol`, and `segment` to the database schema.
- [ ] **Sector Mapping Layer**: Add sector classification metadata for all instruments.
- [ ] **Behavioral Telemetry Persistence**: Add storage for stock personality metrics.
- [ ] **Performance Analytics**: Build regime-segmented Sharpe/expectancy analysis.
- [ ] **Validation Layer**: Script to identify and repair missing time-series data.
- [ ] **OMS Integration**: Automated Upstox order execution interface.
- [ ] **Websocket Streamer**: Real-time derivatives feed infrastructure.
- [ ] **Retention Policy**: TimescaleDB cleanup policies for intraday datasets.

---

# ⚠️ Important Strategic Constraint

DO NOT:
- implement all advanced layers simultaneously,
- over-engineer prematurely,
- hyper-optimize without regime validation.

Reason:
- interpretability loss,
- overfitting risk,
- unstable optimization geometry,
- debugging complexity.

---

# 🧭 Correct Quant Development Chronology (CRITICAL)

## IMPORTANT ARCHITECTURAL REALIZATION

The system has now entered:

```text
Architecture Stabilization Phase
```

NOT:

```text
Feature Accumulation Phase
```

This distinction is critically important.

At the current maturity level:
- every new module changes the interpretation of existing modules,
- feature interactions are now interdependent,
- chronology matters more than sophistication.

The biggest current risk is NOT:
- missing indicators,
- lacking complexity,
- insufficient alpha extraction.

The biggest risk is:

# Building too many unstable adaptive abstractions simultaneously.

Therefore development must now proceed in:
- mathematically stable layers,
- strict architectural order,
- progressively validated stages.

---

# 🧱 The Three-Layer System Model

The engine now effectively consists of:

| Layer | Purpose |
|---|---|
| Layer 1 | Core Signal Mathematics |
| Layer 2 | Contextual Interpretation Intelligence |
| Layer 3 | Capital Deployment Intelligence |

---

# Layer 1 — Core Signal Mathematics

Defines:

```text
What a signal mathematically means
```

Includes:
- Z-score logic,
- entropy,
- FFT,
- wavelets,
- Markov transitions,
- volatility normalization.

This layer MUST stabilize FIRST.

---

# Layer 2 — Contextual Interpretation

Defines:

```text
When a signal matters
```

Includes:
- sector regimes,
- stock personality,
- adaptive weighting,
- conditional feature interpretation.

This layer should ONLY be implemented AFTER Layer 1 stabilizes.

---

# Layer 3 — Capital Intelligence

Defines:

```text
How capital gets deployed
```

Includes:
- dynamic sizing,
- ranking,
- portfolio optimization,
- allocation logic.

This layer must come LAST.

Reason:
- unstable signals should never be amplified with capital.

---

# 🚨 Correct Implementation Chronology

---

# ✅ PHASE A — SIGNAL STABILIZATION (IMPLEMENT NOW)

## Objective
Stabilize the mathematical meaning of signals BEFORE adding contextual complexity.

---

## A1 — RAWRS (CRITICAL FIRST PRIORITY)

### Why RAWRS Must Come First
RAWRS is NOT merely:
- a feature addition,
- a signal enhancement.

It is:

# A correction of a mathematically broken assumption.

The previous implementation incorrectly assumed:

```text
CWT utility is constant across regimes
```

This has now been proven false.

### Mandatory Tasks
- [ ] Replace scalar CWT intensity.
- [ ] Add multi-scale decomposition.
- [ ] Add micro/meso/macro energy layers.
- [ ] Add spectral entropy extraction.
- [ ] Add coherence scoring.
- [ ] Remove hard binary CWT veto logic.
- [ ] Add probabilistic conviction modulation.
- [ ] Preserve pipeline and DB compatibility.

### Files Requiring Changes
| File | Purpose |
|---|---|
| `equity_scanner.py` | RAWRS orchestration integration |
| `vectorized_math.py` | Multi-scale wavelet analytics |
| `requirements.txt` | PyWavelets dependency if missing |

---

## A2 — Spectral Entropy Upgrade (SECOND PRIORITY)

### Why It Comes After RAWRS
RAWRS naturally introduces:
- spectral decomposition,
- frequency-space topology,
- turbulence structure.

Entropy should evolve AFTER wavelet stabilization.

### Tasks
- [ ] Replace primitive scalar entropy.
- [ ] Introduce spectral entropy.
- [ ] Add multi-scale turbulence analysis.
- [ ] Add entropy-conditioned modulation.

### Important Constraint
Do NOT redesign the entire entropy engine independently.

Allow RAWRS infrastructure to become the entropy backbone.

---

## A3 — FFT Authority Reduction (THIRD PRIORITY)

### IMPORTANT
Do NOT replace FFT yet.

That would introduce:
- too many moving variables,
- unstable benchmarking,
- interpretability collapse.

### Instead
FFT should become:

```text
A weak contextual vote
```

NOT:
- an execution authority,
- a hard filter,
- a dominant signal.

### Tasks
- [ ] Reduce FFT ensemble weighting.
- [ ] Remove FFT veto authority.
- [ ] Treat FFT as secondary contextual evidence.

### Future Replacement
Eventually replace FFT with:
- Hilbert Transform,
OR
- Wavelet Ridge Tracking.

But NOT now.

---

## A4 — Markov Stabilization (FOURTH PRIORITY)

### IMPORTANT
Do NOT implement HMM yet.

Current architecture still needs interpretability stability.

### Instead
Perform minimal safe improvements:
- [ ] Smooth state transitions.
- [ ] Reduce hard-bin fragmentation.
- [ ] Improve persistence continuity.
- [ ] Reduce transition instability.

### Goal
Stabilize:

```text
State interpretation
```

before introducing:

```text
Latent probabilistic state discovery
```

---

# 🧠 PHASE B — CONTEXTUAL INTELLIGENCE (AFTER PHASE A)

## IMPORTANT
Do NOT implement these before signal stabilization.

Reason:

```text
You cannot conditionally interpret unstable signals.
```

Doing so creates:
- compounded noise,
- hidden contradictions,
- extreme overfitting risk.

---

## B1 — Sector Regime Intelligence

### Tasks
- [ ] Sector relative strength.
- [ ] Sector volatility states.
- [ ] Sector momentum slopes.
- [ ] Sector entropy structures.

### Future DB Requirement
Potential future table:

```text
sector_regime_metrics
```

---

## B2 — Stock Personality Intelligence

### Tasks
- [ ] Volatility class profiling.
- [ ] Trend persistence scoring.
- [ ] Gap behavior analysis.
- [ ] Entropy baseline modeling.
- [ ] Mean-reversion strength profiling.
- [ ] Spectral fingerprint clustering.

### Future DB Requirement
Potential future table:

```text
stock_behavioral_profiles
```

---

## B3 — Conditional Feature Weighting

### Goal
Feature interpretation becomes dependent on:
- market regime,
- sector regime,
- stock personality.

This becomes:

# Conditional Alpha Interpretation

instead of:

# Universal Static Signal Logic

---

# 💰 PHASE C — CAPITAL INTELLIGENCE (FINAL)

## IMPORTANT
Only implement AFTER:
- signal stabilization,
- contextual stabilization.

Otherwise:
- unstable signals get amplified with capital.

---

## C1 — Conviction-Based Position Sizing

### Tasks
- [ ] ATR-normalized sizing.
- [ ] Conviction-weighted exposure.
- [ ] Entropy-aware exposure reduction.
- [ ] Dynamic capital scaling.

---

## C2 — Cross-Sectional Ranking

### Goal
Transition from:

```text
Should we buy this stock?
```

To:

```text
Which opportunities are best relative to all others?
```

---

## C3 — Portfolio Optimization

### Future Goals
- exposure overlap reduction,
- factor neutrality,
- capital efficiency optimization,
- alpha decay management.

---

# ⚠️ Critical Engineering Rule

DO NOT:
- chase sophistication prematurely,
- implement all adaptive systems simultaneously,
- aggressively rewrite architecture.

The current system already has:
- strong modular structure,
- good ensemble foundations,
- strong statistical backbone.

This is:

# refinement territory

NOT:

# rewrite territory.

---

# ✅ Updated Recommended Priority Order

| Priority | Feature | Status |
|---|---|---|
| 1 | RAWRS | IMPLEMENT NOW |
| 2 | Spectral Entropy Upgrade | IMPLEMENT AFTER RAWRS |
| 3 | FFT Weight Reduction | IMPLEMENT AFTER RAWRS |
| 4 | Markov Stabilization | IMPLEMENT AFTER FFT |
| 5 | Sector Regime Layer | FUTURE |
| 6 | Stock Personality Layer | FUTURE |
| 7 | Conditional Feature Weighting | FUTURE |
| 8 | Conviction-Based Position Sizing | FUTURE |
| 9 | Cross-Sectional Ranking | FUTURE |
| 10 | Portfolio Optimization | FUTURE |

---

# 🧠 Final Strategic Vision

The platform is evolving toward:

# A Regime-Adaptive Probabilistic Alpha Selection Platform

The future edge will NOT come from:
- adding more indicators,
- stacking more filters,
- increasing arbitrary complexity.

The future edge WILL come from:
- conditional feature interpretation,
- regime-aware probabilistic weighting,
- adaptive interaction modeling,
- hierarchical volatility topology understanding.

This becomes:
- an institutional-grade adaptive intelligence engine,
NOT:
- a traditional retail strategy stack.


TODO: Capital Allocation & Post-Entry Lifecycle Architecture
├── [ ] Phase 1: Ingestion Volatility Layer
│   ├── [ ] Modify `price_ingestion.py` / `equity_recommendation_scan.py` to calculate a rolling 14-period ATR from TimescaleDB historical candles.
│   └── [ ] Append the calculated `atr` value as a column to the recommendations payload/database table.
│
├── [ ] Phase 2: Ex-Ante Position Sizing
│   ├── [ ] Integrate dynamic ATR risk-sizing math into `backtest_engine.py` to replace flat lot sizing.
│   └── [ ] Update live order payload builders to compute Quantity = (Risk Budget) / (ATR * Multiplier) at the exact millisecond of entry generation.
│
└── [ ] Phase 3: Post-Entry Background Scheduler
    ├── [ ] Create standalone worker script `portfolio_lifecycle_manager.py`.
    ├── [ ] Implement active position database scanner to track open trade states.
    ├── [ ] Build Rule B: Trailing Volatility Stop loop (modifies active SL orders via Upstox API when rawrs conditions are met).
    ├── [ ] Build Rule C: Time-Decay Early Exit module (fires market close orders for stagnant nodes exceeding time bounds).
    └── [ ] Schedule the lifecycle manager worker daemon to execute at regular intervals (e.g., hourly/5-min) during market hours.