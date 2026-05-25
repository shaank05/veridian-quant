# 🏛️ Project BuddhAditya: Quantitative Roadmap

## 🎯 Current Focus: Execution Infrastructure & Money Management (Stage 2.5)
The objective is to refine our entry precision and mathematically normalize capital distribution across the portfolio to establish a bulletproof execution layer before deploying advanced predictive regimes.

---

## ✅ Completed (Stage 1 - 2: Statistical & Functional Foundation)
- [x] **Infrastructure**: DB Connection Pool and SQLAlchemy Engine integration.
- [x] **Data Persistence**: `instruments` and `prices_ohlc` table architecture.
- [x] **Vectorized Math**: Implementation of `calculate_z_score` and `calculate_expected_move` (ATR).
- [x] **Core Analytics**: `EquityScanner` logic for Z-Score mean reversion ($Z < \text{Threshold}$).
- [x] **Scheduling**: `equity_recommendation_scan.py` for automated nightly population.
- [x] **Backtesting**: `backtest_engine.py` logic for historical outcome verification.
- [x] **Macro Context (v1.0)**: Low-VIX Macro Alpha Mode Matrix implementation.
- [x] **Macro Context (v1.1 - Experiment)**: Nifty Daily Z-Score Threshold Overlay (*Failed: Dropped due to severe alpha choke during secular bull runs*).
- [x] **Macro Context (v1.2)**: Normalized 50 SMA Strict Percentage Slope Velocity Hurdle ($\ge 0.10\%$). Safely stabilizes the 2025 distribution decay while maintaining high capital efficiency.
- [x] **Bug Fix**: Fixed `np.float64` engine-level schema compilation warnings and UTC-to-IST fallback loop issues inside `backtest_engine.py`.

---

## 🚀 Immediate Action Items (Phase 2.5: Operational Plumb Lines)

- [ ] **Option A (Portfolio Sizing)**: Replace static ₹100,000 trade bricks with an **ATR Risk-Equalized Position Sizing Engine**. Establish uniform account drawdown limits (e.g., 1.0% total equity risk per setup) to neutralize variance across differing high/low-beta asset scales.
- [ ] **Option C (Micro-Entry Trigger)**: Build the lower-timeframe validation pipeline. Pivot the daily scanner to log to an intraday `high_alert_watchlist` table, using 15m/1h structural turn signals (VWAP crosses or hourly high breakouts) to trigger executions.
- [ ] **Data Refill**: Run `PriceIngestor` with `HISTORICAL_LOOKBACK = 14` to bridge the April–May 2026 gap.
- [ ] **Integrity Guard**: Add a daily check for 0-volume candles on trading days to prevent "false" Z-score signals.
- [ ] **Schema Evolution**: Execute `ALTER TABLE` in PuTTy to add `exchange_token`, `trading_symbol`, and `segment` to the database schema.

---

## 🗺️ The Quant Architecture Roadmap (Future Stages)

### 🌊 Stage 2: Spectral Analysis (The "Noise" Filter)
- **Math**: Fast Fourier Transform (FFT) via `scipy.fft`.
- **Goal**: Identify dominant cyclical frequency sweeps of single equities to prevent catching falling knives while asset velocity vectors point downward.

### 🎭 Stage 3: Markov Regimes (The Context Engine Upgrade) - *UPCOMING QUANT UPGRADE*
- **Math**: Hidden Markov Models (HMM) via `hmmlearn`.
- **Goal**: Track structural market shifts (e.g., High-Velocity Bull Expansion vs. Hollow Stagnation Distribution) using a multi-variate transition probability matrix. Automatically overrides short-term index pauses in secular environments to **fully capture and resurrect lost 2023 alpha (~₹1.27L tier)** while clamping gates in exhaustion periods.

### 🎲 Stage 4: Stochastic Path Prediction
- **Math**: Geometric Brownian Motion & Monte Carlo Simulations.
- **Goal**: Execute 10,000 concurrent trajectory simulations to derive empirical Probability of Touch fields for adaptive take-profit targets ($4\times\text{ATR}$ up to $6\times\text{– }8\times\text{ATR}$ extensions in major trends).

### 🧠 Stage 5: The Ensemble (The "Medallion" Layer Master Controller)
- **Math**: Bayesian Inference Meta-Learner (Meta-Labeling Structure).
- **Goal**: A centralized machine learning meta-classifier synthesizing subsystem probabilities into a unified System Conviction Score (0% to 100%). Feeds direct torque instructions back to Option A's position engine to scale up leverage dynamically during perfect macro environments and throttle it during distribution.

---

## 🔧 Infrastructure & Execution (Future)
- [ ] **Option B (Sector Sifter)**: Implement Multi-Timeframe Sector Relative Strength Matrix to redirect scanning capital solely into groups exhibiting structural institutional inflows.
- [ ] **Websocket Streamer**: Real-time Tick-by-Tick data service for derivatives.
- [ ] **Order Management System (OMS)**: Interface for automated Upstox order placement.
- [ ] **Retention Policy**: TimescaleDB cleanup for 1-minute data older than 1 year.
- [ ] **Performance Analytics**: Script to calculate actual win-rate and Sharpe Ratio per strategy.
- [ ] **Validation Layer**: Script to identify and fill "holes" in the time-series data.
- [ ] **Order Hook**: Update `is_ordered` and `external_order_id` on successful API call.