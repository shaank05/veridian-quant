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
from veridian_quant.v2.intelligence.rawrs_diagnostics import (
    attach_rawrs_features_at_signal_time,
    attach_rawrs_features_by_symbol,
    bucket_rawrs_feature,
    normalize_signal_timestamp_column,
    summarize_outcome_by_rawrs_bucket,
    summarize_rawrs_feature_by_outcome,
)
from veridian_quant.v2.intelligence.rawrs_exports import (
    build_rawrs_feature_bucket_summary,
    build_rawrs_rejection_diagnostics,
    build_rawrs_signal_diagnostics,
    build_rawrs_trade_diagnostics,
    export_rawrs_diagnostic_csvs,
)

__all__ = [
    "attach_rawrs_features_at_signal_time",
    "attach_rawrs_features_by_symbol",
    "build_rawrs_feature_bucket_summary",
    "build_rawrs_rejection_diagnostics",
    "build_rawrs_signal_diagnostics",
    "build_rawrs_trade_diagnostics",
    "bucket_rawrs_feature",
    "export_rawrs_diagnostic_csvs",
    "log_returns",
    "multi_scale_energy_frame",
    "normalize_signal_timestamp_column",
    "rawrs_feature_frame",
    "rolling_direction_change_rate",
    "rolling_fft_dominant_period",
    "rolling_fft_spectral_concentration",
    "rolling_fft_spectral_entropy",
    "rolling_return_energy",
    "summarize_outcome_by_rawrs_bucket",
    "summarize_rawrs_feature_by_outcome",
]
