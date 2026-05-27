# 🏛️ Project BuddhAditya: Quantitative Roadmap

## 🎯 Current Focus: Execution Infrastructure & Money Management (Stage 2.5)
The objective is to refine our entry precision and mathematically normalize capital distribution across the portfolio to establish a bulletproof execution layer before deploying advanced predictive regimes.

---

## ✅ Completed (Stage 1 - 2.1: Statistical, Functional & Noise Foundations)
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
- [x] **Bug Fix**: Fixed `np.float64` engine-level schema compilation warnings and UTC-to-IST fallback loop issues inside `backtest_engine.py`.
- [x] **Workspace Recovery**: Cleared corrupted `.gitignore` binary trailing sequences and stabilized repository untracked paths.

---

## 🚀 Immediate Action Items (Phase 2.5: Operational Plumb Lines)

- [ ] **Option A (Portfolio Sizing)**: Replace static ₹100,000 trade bricks with an **ATR Risk-Equalized Position Sizing Engine**. Establish uniform account drawdown limits (e.g., 1.0% total equity risk per setup) to neutralize variance across differing high/low-beta asset scales.
- [ ] **Option C (Micro-Entry Trigger)**: Build the lower-timeframe validation pipeline. Pivot the daily scanner to log to an intraday `high_alert_watchlist` table, using 15m/1h structural turn signals (VWAP crosses or hourly high breakouts) to trigger executions.
- [ ] **Data Refill**: Run `PriceIngestor` with `HISTORICAL_LOOKBACK = 14` to bridge the April–May 2026 gap.
- [ ] **Integrity Guard**: Add a daily check for 0-volume candles on trading days to prevent "false" Z-score signals.
- [ ] **Schema Evolution**: Execute `ALTER TABLE` in PuTTy to add `exchange_token`, `trading_symbol`, and `segment` to the database schema.

---

## 🗺️ The Quant Architecture Roadmap (Future Sequential Upgrades)

### 🌊 Stage 2.2: Continuous Wavelet Transform (CWT Timing Upgrade)
- **Math**: Mother Wavelet scaling and shifting functions ($\psi_{a,b}(t)$).
- **Integration Profile**: Serves as a direct analytical upgrade to Stage 2 (FFT). By resolving standard Fourier transform time-blindness with simultaneous time-frequency localization, CWT will pinpoint exactly *when* dominant alpha cycles are actively expanding or decaying.
- **Verification Metric**: Will be enabled side-by-side with FFT in the backtester to empirically verify if time-localized frequency decomposition increases baseline alpha or cuts down phase-lag drawdowns.

### 🎭 Stage 3: Markov Regimes (The Context Engine Upgrade)
- **Math**: Hidden Markov Models (HMM) via `hmmlearn`.
- **Goal**: Track structural market shifts (e.g., High-Velocity Bull Expansion vs. Hollow Stagnation Distribution) using a multi-variate transition probability matrix. Automatically overrides short-term index pauses in secular environments to **fully capture and resurrect lost alpha** while clamping gates in exhaustion periods.

### 🎲 Stage 4: Stochastic Path Prediction (Monte Carlo Simulations)
- **Math**: Geometric Brownian Motion (GBM) drifting algorithms.
- **Integration Profile**: Intakes the historical point-in-time volatility vectors confirmed by Stage 1, 2, and 2.1. Upon a scanner trigger, it computes 10,000 future price path trajectories over a forward-looking 30-day window.
- **Goal**: Derive empirical Probability of Touch (POT) metrics to dynamically evaluate whether an asset has a mathematically verifiable probability of striking its target ($4\times\text{ATR}$) prior to violating its stop-loss ($2\times\text{ATR}$).

### 🧠 Stage 5: The Ensemble (The "Medallion" Layer Master Controller)
- **Math**: Bayesian Inference Meta-Learner (Dynamic Prior-to-Posterior Updating).
- **Integration Profile**: Acts as the centralized execution gatekeeper. It does not look at old database recommendation tables; instead, it takes the concurrent, live probability outputs of all prior nodes (Macro Regime, Entropy Chaos, FFT Phase, VSA Accumulation, and Stage 4 Monte Carlo POT) as conditional evidence.
- **Goal**: Synthesizes multi-layered probabilities into a single, unified Ensemble Conviction Score (0% to 100%). Feeds direct torque instructions back to Option A's sizing engine to scale up capital allocation during highly cohesive setups, and throttle parameters during structural uncertainty.

Upgrade 1: Stage 2.2 Continuous Wavelet Transforms (CWT)

Upgrade 2: Activating Option C (The Watchlist Micro-Entry Trigger)

---

## 🔧 Infrastructure & Execution (Future)
- [ ] **Option B (Sector Sifter)**: Implement Multi-Timeframe Sector Relative Strength Matrix to redirect scanning capital solely into groups exhibiting structural institutional inflows.
- [ ] **Websocket Streamer**: Real-time Tick-by-Tick data service for derivatives.
- [ ] **Order Management System (OMS)**: Interface for automated Upstox order placement.
- [ ] **Retention Policy**: TimescaleDB cleanup for 1-minute data older than 1 year.
- [ ] **Performance Analytics**: Script to calculate actual win-rate and Sharpe Ratio per strategy.
- [ ] **Validation Layer**: Script to identify and fill "holes" in the time-series data.
- [ ] **Order Hook**: Update `is_ordered` and `external_order_id` on successful API call.