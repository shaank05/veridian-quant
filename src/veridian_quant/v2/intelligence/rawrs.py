"""I1 RAWRS market-structure intelligence feature utilities.

RAWRS means Regime-Aware Adaptive Wavelet Response Surface.

This module contains pure, deterministic, non-strategy feature helpers. The
functions do not generate signals, trades, topology labels, rankings, or
portfolio behavior.
"""

from collections.abc import Iterable

import numpy as np
import pandas as pd


def log_returns(data: pd.DataFrame, price_col: str = "close") -> pd.Series:
    """Return natural log close-to-close returns for ``price_col``.

    The first value is ``NaN``. The output preserves the input index and the
    caller-provided dataframe is not mutated.
    """

    _validate_columns(data, (price_col,))
    prices = data[price_col].astype("float64")
    return np.log(prices / prices.shift(1))


def rolling_fft_spectral_concentration(
    returns: pd.Series,
    window: int,
) -> pd.Series:
    """Return rolling non-zero FFT power concentration.

    The value is the maximum non-zero-frequency power divided by total
    non-zero-frequency power. Results range from 0.0 to 1.0 when defined.
    """

    _validate_window(window, "window")
    return returns.rolling(window=window, min_periods=window).apply(
        _fft_spectral_concentration,
        raw=True,
    )


def rolling_fft_spectral_entropy(returns: pd.Series, window: int) -> pd.Series:
    """Return normalized rolling FFT spectral entropy.

    The zero-frequency component is excluded. Lower values indicate a more
    concentrated spectrum; higher values indicate more diffuse/noisy spectral
    power. Results range from 0.0 to 1.0 when defined.
    """

    _validate_window(window, "window")
    return returns.rolling(window=window, min_periods=window).apply(
        _fft_spectral_entropy,
        raw=True,
    )


def rolling_fft_dominant_period(returns: pd.Series, window: int) -> pd.Series:
    """Return rolling dominant non-zero FFT period in sessions.

    The dominant period is ``window / dominant_frequency_bin``. This is a
    diagnostic feature only, not a trading rule.
    """

    _validate_window(window, "window")
    return returns.rolling(window=window, min_periods=window).apply(
        _fft_dominant_period,
        raw=True,
    )


def rolling_return_energy(returns: pd.Series, window: int) -> pd.Series:
    """Return rolling mean squared return."""

    _validate_window(window, "window")
    return (returns.astype("float64") ** 2).rolling(
        window=window,
        min_periods=window,
    ).mean()


def multi_scale_energy_frame(
    returns: pd.Series,
    micro_window: int = 5,
    meso_window: int = 20,
    macro_window: int = 60,
) -> pd.DataFrame:
    """Return RAWRS micro/meso/macro energy features and ratios."""

    _validate_window(micro_window, "micro_window")
    _validate_window(meso_window, "meso_window")
    _validate_window(macro_window, "macro_window")

    micro_energy = rolling_return_energy(returns, micro_window)
    meso_energy = rolling_return_energy(returns, meso_window)
    macro_energy = rolling_return_energy(returns, macro_window)

    return pd.DataFrame(
        {
            "rawrs_micro_energy": micro_energy,
            "rawrs_meso_energy": meso_energy,
            "rawrs_macro_energy": macro_energy,
            "rawrs_micro_meso_energy_ratio": _safe_ratio(
                micro_energy,
                meso_energy,
            ),
            "rawrs_meso_macro_energy_ratio": _safe_ratio(
                meso_energy,
                macro_energy,
            ),
        },
        index=returns.index,
    )


def rolling_direction_change_rate(returns: pd.Series, window: int) -> pd.Series:
    """Return trailing fraction of non-zero return-sign transitions.

    Zero and missing returns are ignored inside each full trailing window. Rows
    with fewer than two non-zero signs return ``NaN``.
    """

    _validate_window(window, "window")
    return returns.rolling(window=window, min_periods=window).apply(
        _direction_change_rate,
        raw=True,
    )


def rawrs_feature_frame(
    data: pd.DataFrame,
    *,
    fft_window: int = 64,
    micro_window: int = 5,
    meso_window: int = 20,
    macro_window: int = 60,
    direction_window: int = 20,
    price_col: str = "close",
) -> pd.DataFrame:
    """Return the Phase 30B RAWRS feature frame aligned to input data."""

    returns = log_returns(data, price_col=price_col)
    energy = multi_scale_energy_frame(
        returns,
        micro_window=micro_window,
        meso_window=meso_window,
        macro_window=macro_window,
    )

    return pd.DataFrame(
        {
            "rawrs_log_return": returns,
            "rawrs_fft_spectral_concentration": (
                rolling_fft_spectral_concentration(returns, fft_window)
            ),
            "rawrs_fft_spectral_entropy": rolling_fft_spectral_entropy(
                returns,
                fft_window,
            ),
            "rawrs_fft_dominant_period": rolling_fft_dominant_period(
                returns,
                fft_window,
            ),
            "rawrs_micro_energy": energy["rawrs_micro_energy"],
            "rawrs_meso_energy": energy["rawrs_meso_energy"],
            "rawrs_macro_energy": energy["rawrs_macro_energy"],
            "rawrs_micro_meso_energy_ratio": (
                energy["rawrs_micro_meso_energy_ratio"]
            ),
            "rawrs_meso_macro_energy_ratio": (
                energy["rawrs_meso_macro_energy_ratio"]
            ),
            "rawrs_direction_change_rate": rolling_direction_change_rate(
                returns,
                direction_window,
            ),
        },
        index=data.index,
    )


def _fft_spectral_concentration(values: np.ndarray) -> float:
    power = _non_zero_fft_power(values)
    if power is None:
        return np.nan
    total_power = power.sum()
    if total_power <= 0:
        return np.nan
    return float(power.max() / total_power)


def _fft_spectral_entropy(values: np.ndarray) -> float:
    power = _non_zero_fft_power(values)
    if power is None:
        return np.nan
    total_power = power.sum()
    if total_power <= 0:
        return np.nan
    probabilities = power / total_power
    probabilities = probabilities[probabilities > 0]
    if len(probabilities) <= 1:
        return 0.0
    entropy = -np.sum(probabilities * np.log(probabilities))
    return float(entropy / np.log(len(power)))


def _fft_dominant_period(values: np.ndarray) -> float:
    power = _non_zero_fft_power(values)
    if power is None:
        return np.nan
    total_power = power.sum()
    if total_power <= 0:
        return np.nan
    dominant_bin = int(np.argmax(power)) + 1
    return float(len(values) / dominant_bin)


def _non_zero_fft_power(values: np.ndarray) -> np.ndarray | None:
    values = values.astype("float64")
    if np.isnan(values).any():
        return None
    fft_values = np.fft.rfft(values)
    power = np.abs(fft_values) ** 2
    non_zero_power = power[1:]
    if len(non_zero_power) == 0:
        return None
    return non_zero_power


def _direction_change_rate(values: np.ndarray) -> float:
    values = values.astype("float64")
    signs = np.sign(values[~np.isnan(values)])
    signs = signs[signs != 0]
    if len(signs) < 2:
        return np.nan
    changes = np.sum(signs[1:] != signs[:-1])
    return float(changes / (len(signs) - 1))


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    safe_denominator = denominator.replace(0, np.nan)
    return numerator / safe_denominator


def _validate_window(window: int, name: str) -> None:
    """Validate that a rolling window is a positive integer."""

    if not isinstance(window, int) or window < 1:
        raise ValueError(f"{name} must be a positive integer")


def _validate_columns(data: pd.DataFrame, required_columns: Iterable[str]) -> None:
    """Validate that all required columns are present."""

    missing = [column for column in required_columns if column not in data.columns]
    if missing:
        missing_columns = ", ".join(missing)
        raise ValueError(f"missing required columns: {missing_columns}")
