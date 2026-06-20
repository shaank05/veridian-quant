"""Focused CLI tests for the optional S3 RAWRS overlay experiment."""

from veridian_quant.v2.run_s3_backtest import _parse_args


def test_cli_parses_rawrs_overlay_flags() -> None:
    args = _parse_args(
        [
            "--start-date", "2020-01-01", "--end-date", "2026-04-30",
            "--symbols", "RELIANCE,TCS", "--enable-rawrs-overlay",
            "--rawrs-feature", "rawrs_fft_spectral_concentration",
            "--rawrs-avoid-percentile-lte", "0.20",
            "--rawrs-percentile-lookback", "252",
            "--rawrs-min-observations", "126",
        ]
    )
    assert args.enable_rawrs_overlay is True
    assert args.rawrs_feature == "rawrs_fft_spectral_concentration"
    assert args.rawrs_avoid_percentile_lte == 0.20
    assert args.rawrs_percentile_lookback == 252
    assert args.rawrs_min_observations == 126


def test_cli_defaults_leave_rawrs_overlay_disabled() -> None:
    args = _parse_args(
        [
            "--start-date", "2020-01-01", "--end-date", "2026-04-30",
            "--symbols", "RELIANCE",
        ]
    )
    assert args.enable_rawrs_overlay is False
