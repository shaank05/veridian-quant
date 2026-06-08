1. **Baseline Strategy Definition**

   * Start with one clean strategy: Z-score mean reversion.
   * No FFT, no wavelet, no Markov, no ensemble.

2. **Backtest Rules Specification**

   * Entry timing
   * Exit timing
   * Same-day target/stop ambiguity
   * Slippage
   * Brokerage/taxes
   * Expiry handling

3. **Data Contract**

   * Required columns
   * Adjusted/unadjusted prices
   * index data
   * sector data
   * VIX data

4. **Validation Protocol**

   * Train/test split
   * Walk-forward periods
   * Parameter sensitivity
   * regime-wise performance

5. **Acceptance Gates**

   * What result qualifies the baseline as valid?
   * What result rejects it?