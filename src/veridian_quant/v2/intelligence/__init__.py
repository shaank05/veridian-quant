"""Reusable non-strategy intelligence layers for Veridian Quant v2."""

from veridian_quant.v2.intelligence.rawrs import (
    log_returns,
    multi_scale_energy_frame,
    rawrs_feature_frame,
    rolling_direction_change_rate,
    rolling_fft_dominant_period,
    rolling_fft_spectral_concentration,
    rolling_fft_spectral_entropy,
    rolling_return_energy,
)

__all__ = [
    "log_returns",
    "multi_scale_energy_frame",
    "rawrs_feature_frame",
    "rolling_direction_change_rate",
    "rolling_fft_dominant_period",
    "rolling_fft_spectral_concentration",
    "rolling_fft_spectral_entropy",
    "rolling_return_energy",
]
