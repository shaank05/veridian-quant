import numpy as np
import pandas as pd
from scipy.fft import fft, fftfreq
from scipy.stats import entropy as scipy_entropy
import pywt
import traceback

def calculate_z_score(price_series: pd.Series, window: int = 20) -> pd.Series:
    """Computes rolling Z-Score for mean reversion validation."""
    rolling_mean = price_series.rolling(window=window).mean()
    rolling_std = price_series.rolling(window=window).std()
    return (price_series - rolling_mean) / rolling_std

def calculate_expected_move(price_series: pd.Series, window: int = 20) -> pd.Series:
    """Computes historical price volatility envelope using rolling mean changes (ATR Proxy)."""
    return price_series.diff().abs().rolling(window=window).mean()

def generate_statistical_signals(df: pd.DataFrame, z_threshold: float = 2.5):
    """Processes full history dataframe matrix arrays."""
    close_prices = df['close']
    df['z_score'] = calculate_z_score(close_prices)
    df['avg_move'] = calculate_expected_move(close_prices)
    df['stat_signal'] = 0
    df.loc[df['z_score'] < -z_threshold, 'stat_signal'] = -1
    df.loc[df['z_score'] > z_threshold, 'stat_signal'] = 1
    return df

def calculate_dominant_cycle(price_series: pd.Series):
    """Applies FFT to compute dominant cycle frequency parameters."""
    detrended = price_series.diff().fillna(0).values
    n = len(detrended)
    yf = fft(detrended)
    xf = fftfreq(n, 1)
    idx = np.argmax(np.abs(yf[1:n//2])) + 1 
    dominant_freq = xf[idx]
    return abs(1 / dominant_freq) if dominant_freq != 0 else 0.0

def check_cycle_phase(price_series: pd.Series):
    """Checks if historical downward velocity momentum is slowing down."""
    momentum_3d = price_series.diff(3).iloc[-1]
    momentum_10d = price_series.diff(10).iloc[-1]
    is_decelerating = momentum_3d > momentum_10d
    recent_low = price_series.tail(5).min()
    at_low = price_series.iloc[-1] <= recent_low * 1.01
    return is_decelerating or not at_low

def calculate_shannon_entropy(price_series: pd.Series, window: int = 20) -> float:
    """Measures price disorder footprints. Slated for long-term deprecation."""
    if len(price_series) < window + 1: return 0.0
    log_returns = np.log(price_series / price_series.shift(1)).dropna().tail(window)
    if log_returns.empty or np.all(log_returns == 0): return 0.0
    counts, _ = np.histogram(log_returns, bins=5)
    probabilities = counts / counts.sum()
    probabilities = probabilities[probabilities > 0]
    return float(-np.sum(probabilities * np.log2(probabilities)))

def generate_rawrs_wavelet_signature(close_series, lookback_window=5):
    """
    Regime-Aware Adaptive Wavelet Response Surface (RAWRS) Signature Engine.
    
    CRITICAL FIX 1: Volatility normalization layer completely scales out multi-scale 
    energy biases across high-beta vs. defensive assets using localized rolling volatility.
    """
    try:
        if not isinstance(close_series, pd.Series):
            series_cleaned = pd.Series(close_series).dropna()
        else:
            series_cleaned = close_series.dropna()
            
        data = series_cleaned.to_numpy(dtype=float, copy=True).flatten()
        
        # Absolute safety boundary clamp
        if len(data) < 32:
            return {
                "micro_energy": 1.0, "meso_energy": 1.0, "macro_energy": 1.0,
                "spectral_entropy": 0.5, "coherence": 1.0, "wavelet_intensity": 1.0
            }
            
        # 1. Compute rolling volatility baseline normalization factor (ATR proxy)
        rolling_changes = np.abs(np.diff(data))
        volatility_scale = float(np.mean(rolling_changes[-20:])) if len(rolling_changes) >= 20 else 1.0
        if volatility_scale <= 0 or np.isnan(volatility_scale):
            volatility_scale = 1.0
            
        # 2. Extract Multi-Scale Continuous Wavelet Space
        dense_scales = np.geomspace(2.0, 32.0, 12)
        coefs, _ = pywt.cwt(data, dense_scales, 'mexh')
        
        total_scales = len(dense_scales)
        micro_cut = int(total_scales * 0.33)
        macro_cut = int(total_scales * 0.75)
        
        # 3. Local Energy Root-Mean-Square (RMS) Window Extraction
        recent_coefs = coefs[:, -lookback_window:]
        rms_energies = np.sqrt(np.mean(recent_coefs ** 2, axis=1))
        
        # CRITICAL FIX 1: Normalize all raw spatial energies by the historical volatility baseline
        epsilon = 1e-5
        micro_energy = float(np.mean(rms_energies[0:micro_cut])) / (volatility_scale + epsilon)
        meso_energy  = float(np.mean(rms_energies[micro_cut:macro_cut])) / (volatility_scale + epsilon)
        macro_energy = float(np.mean(rms_energies[macro_cut:])) / (volatility_scale + epsilon)
        
        # 4. Localized Scale-Space Entropy Window
        local_energy_distribution = np.mean(np.abs(recent_coefs), axis=1)
        energy_sum = np.sum(local_energy_distribution)
        spectral_entropy = float(scipy_entropy(local_energy_distribution / energy_sum, base=2)) if energy_sum > 0 else 0.0
            
        # 5. Continuous Geometric Cosine Similarity Coherence Vector
        if len(data) >= lookback_window:
            price_vector = np.diff(data[-lookback_window:])
            macro_index = min(macro_cut + 1, total_scales - 1)
            macro_vector = np.diff(coefs[macro_index, -lookback_window:])
            
            norm_product = np.linalg.norm(price_vector) * np.linalg.norm(macro_vector)
            coherence = float(np.dot(price_vector, macro_vector) / norm_product) if norm_product > 0 else 1.0
            if np.isnan(coherence): coherence = 1.0
        else:
            coherence = 1.0
            
        # 6. Safety Bounded Legacy Ratio Transform
        wavelet_intensity = float(2.0 * np.tanh(micro_energy / macro_energy)) if macro_energy > 0 else 1.0
        
        return {
            "micro_energy": float(micro_energy),
            "meso_energy": float(meso_energy),
            "macro_energy": float(macro_energy),
            "spectral_entropy": float(spectral_entropy),
            "coherence": float(coherence),
            "wavelet_intensity": float(wavelet_intensity)
        }
        
    except Exception as e:
        traceback.print_exc()
        return {
            "micro_energy": 1.0, "meso_energy": 1.0, "macro_energy": 1.0,
            "spectral_entropy": 0.5, "coherence": 1.0, "wavelet_intensity": 1.0
        }

def calculate_wavelet_momentum_intensity(close_series, short_width=3, long_width=10):
    """Maintains backward compatibility with legacy tracking execution layers."""
    sig = generate_rawrs_wavelet_signature(close_series)
    return sig['wavelet_intensity']