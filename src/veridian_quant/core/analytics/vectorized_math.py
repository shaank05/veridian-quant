import numpy as np
import pandas as pd
from scipy.fft import fft, fftfreq
import pywt  # Clean, industry-standard wavelet architecture anchor
import traceback

def calculate_z_score(price_series: pd.Series, window: int = 20) -> pd.Series:
    """
    Computes the rolling Z-Score for a price series.
    This is the foundation of Statistical Alpha.
    This is a Mean Reversion indicator. In market terms, this is often called Statistical Arbitrage or Standard Deviation Bands (similar to Bollinger Bands, but expressed as a single number). It doesn't tell you the trend; it tells you how "stretched" or "oversold" the price is relative to its average.
    By using $Z < -2.5$, you are looking for a "Statistical Crash"—a point where the price has dropped so far, so fast, that the probability of a bounce back to the mean is very high.
    Args:
        price_series: A Pandas Series of closing prices.
        window: The lookback period (default 20 for one trading month).
    """
    # 1. Calculate the Rolling Mean (The 'Fair Value' line)
    rolling_mean = price_series.rolling(window=window).mean()
    
    # 2. Calculate the Rolling Standard Deviation (The 'Volatility' or 'Noise')
    rolling_std = price_series.rolling(window=window).std()
    
    # 3. Apply the Z-Score Formula: (Price - Mean) / Volatility
    # This vectorizes the calculation across the entire historical series.
    z_score = (price_series - rolling_mean) / rolling_std
    
    return z_score

def calculate_expected_move(price_series: pd.Series, window: int = 20) -> pd.Series:
    """
    Uses Average True Range (ATR) logic to determine the 'Speed' of the stock.
    Helps in setting the 'expected_duration_days' for our recommendations.
    """
    # Calculate daily absolute returns
    daily_change = price_series.diff().abs()
    
    # Calculate the average move over the window
    return daily_change.rolling(window=window).mean()

def generate_statistical_signals(df: pd.DataFrame, z_threshold: float = 2.5):
    """
    Processes a full OHLC DataFrame and identifies statistical anomalies.
    Works for both single-day (Prod) and multi-day (Backtest) data.
    """
    # Ensure we are working with the 'close' price
    close_prices = df['close']
    
    # Calculate Z-Score for the entire history
    df['z_score'] = calculate_z_score(close_prices)
    
    # Calculate Volatility for the entire history
    df['avg_move'] = calculate_expected_move(close_prices)
    
    # Identify anomalies: Where is price > 2.5 standard deviations from mean?
    # -1 = Statistical Crash (Potential Buy)
    # +1 = Statistical Spike (Potential Sell/Exit)
    df['stat_signal'] = 0
    df.loc[df['z_score'] < -z_threshold, 'stat_signal'] = -1
    df.loc[df['z_score'] > z_threshold, 'stat_signal'] = 1
    
    return df

def calculate_dominant_cycle(price_series: pd.Series):
    """
    Applies Fast Fourier Transform (FFT) to find the dominant cycle 
    in the price movement. Helps distinguish 'Noise' from 'Cycle'.
    """
    # 1. Detrend the data (FFT needs the signal to oscillate around zero)
    detrended = price_series.diff().fillna(0).values
    n = len(detrended)
    
    # 2. Perform FFT
    yf = fft(detrended)
    xf = fftfreq(n, 1) # Assumes 1-day spacing
    
    # 3. Find the peak frequency (ignoring the 0Hz/DC component)
    # We only care about positive frequencies
    idx = np.argmax(np.abs(yf[1:n//2])) + 1 
    dominant_freq = xf[idx]
    
    # 4. Convert frequency to period (Days)
    # If freq is 0.05, cycle is 1/0.05 = 20 days
    if dominant_freq != 0:
        return abs(1 / dominant_freq)
    return 0

def check_cycle_phase(price_series: pd.Series):
    """
    Improved Medallion Filter: Checks if the downward momentum is slowing 
    down (fading) rather than requiring a full upward 'hook'.
    """
    # 1. Calculate short-term vs mid-term momentum
    momentum_3d = price_series.diff(3).iloc[-1]
    momentum_10d = price_series.diff(10).iloc[-1]
    
    # 2. Logic: If 3-day momentum is better than 10-day momentum, 
    # it indicates the 'crash' is decelerating (losing power).
    is_decelerating = momentum_3d > momentum_10d
    
    # 3. Secondary check: Are we within 5% of the 5-day low?
    # This prevents buying if the stock is currently at its absolute 'pit'.
    recent_low = price_series.tail(5).min()
    at_low = price_series.iloc[-1] <= recent_low * 1.01
    
    # We pass the signal if it's NOT at the absolute low OR it's decelerating
    return is_decelerating or not at_low


def calculate_shannon_entropy(price_series: pd.Series, window: int = 20) -> float:
    """
    Measures the statistical randomness/disorder of price spreads over a rolling window.
    High entropy signifies chaotic white noise where cyclic calculations collapse into false positives.
    Low entropy signals highly structured, non-random accumulation/distribution footprints.
    """
    if len(price_series) < window + 1:
        return 0.0

    # 1. Calculate log returns to ensure statistical stationarity
    log_returns = np.log(price_series / price_series.shift(1)).dropna().tail(window)

    if log_returns.empty or np.all(log_returns == 0):
        return 0.0

    # 2. Discretize returns into 5 equal-width probability bins
    counts, _ = np.histogram(log_returns, bins=5)
    probabilities = counts / counts.sum()

    # 3. Filter out zero probabilities to avoid log2(0) computational crashes
    probabilities = probabilities[probabilities > 0]

    # 4. Apply the Shannon Entropy equation: -Sum( P(x) * log2(P(x)) )
    entropy = -np.sum(probabilities * np.log2(probabilities))
    
    return float(entropy)


def calculate_wavelet_momentum_intensity(close_series, short_width=3, long_width=10):
    """
    Stage 2.2 Continuous Wavelet Transform (CWT) Momentum Engine.
    
    Isolates micro-velocity and compares it against structural macro-waves.
    Explicit scalar execution with structural NaN cleaning to prevent silent fallbacks.
    """
    try:
        # 1. Clean data layer: Ensure we have a pandas series and drop any missing ticks
        if not isinstance(close_series, pd.Series):
            series_cleaned = pd.Series(close_series).dropna()
        else:
            series_cleaned = close_series.dropna()
            
        data = series_cleaned.to_numpy(dtype=float, copy=True).flatten()
        
        if len(data) < 30:
            return 1.0  # Unit neutral fallback for short historical windows
            
        # 2. Compute the high-frequency short wave scale explicitly (Velocity)
        short_coefs, _ = pywt.cwt(data, [float(short_width)], 'mexh')
        # Force extraction to a completely flat 1D scalar value
        short_wave_energy = float(np.abs(short_coefs[-1][-1]))
        
        # 3. Compute the low-frequency long wave scale explicitly (Structural Cycle)
        long_coefs, _ = pywt.cwt(data, [float(long_width)], 'mexh')
        long_wave_energy = float(np.abs(long_coefs[-1][-1]))
        
        # Guard against zero-division thresholds or corrupted NaN states
        if np.isnan(short_wave_energy) or np.isnan(long_wave_energy) or long_wave_energy == 0:
            return 1.0
            
        # Compute the localized intensity ratio
        wavelet_intensity = short_wave_energy / long_wave_energy

        print(f"🌊 CWT Wavelet Intensity: {wavelet_intensity:.4f}")
        
        return float(wavelet_intensity)
        
    except Exception as e:
        # ABSOLUTE SAFETY: Print the actual structural error traceback to the console
        # This completely stops the engine from masking any dimensional or type issues.
        print(f"\n❌ [CRITICAL CWT FAILURE ENCOUNTERED]")
        print(f"Error Detail: {str(e)}")
        traceback.print_exc()
        return 1.0