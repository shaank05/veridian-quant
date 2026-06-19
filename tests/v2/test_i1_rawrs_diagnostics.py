"""Unit tests for I1 RAWRS signal-time diagnostic utilities."""

import importlib

import numpy as np
import pandas as pd
import pytest

from veridian_quant.v2.intelligence.rawrs_diagnostics import (
    attach_rawrs_features_at_signal_time,
    attach_rawrs_features_by_symbol,
    bucket_rawrs_feature,
    normalize_rawrs_join_timestamp,
    normalize_signal_timestamp_column,
    summarize_outcome_by_rawrs_bucket,
    summarize_rawrs_feature_by_outcome,
)


def test_signal_timestamp_normalization_picks_priority_column_and_preserves_index() -> None:
    records = pd.DataFrame(
        {
            "signal_date": ["2026-01-03", "2026-01-04"],
            "date": ["2025-01-01", "2025-01-02"],
        },
        index=pd.Index(["a", "b"], name="record"),
    )

    result = normalize_signal_timestamp_column(records)

    expected = pd.Series(
        pd.to_datetime(["2026-01-03", "2026-01-04"]),
        index=records.index,
        name="signal_date",
    )
    pd.testing.assert_series_equal(result, expected)


def test_missing_timestamp_column_raises_value_error() -> None:
    records = pd.DataFrame({"symbol": ["ABC"]})

    with pytest.raises(ValueError, match="missing signal timestamp column"):
        normalize_signal_timestamp_column(records)


def test_exact_date_rawrs_feature_attachment() -> None:
    records = pd.DataFrame({"generated_on": ["2026-01-02"], "symbol": ["ABC"]})
    rawrs = _rawrs_frame(["2026-01-02"], [0.25])

    result = attach_rawrs_features_at_signal_time(records, rawrs)

    assert result.loc[0, "rawrs_micro_energy"] == 0.25
    assert result.loc[0, "rawrs_feature_timestamp"] == pd.Timestamp("2026-01-02")


def test_asof_prior_date_attachment_when_exact_date_missing() -> None:
    records = pd.DataFrame({"generated_on": ["2026-01-03"]})
    rawrs = _rawrs_frame(["2026-01-01", "2026-01-05"], [0.10, 0.90])

    result = attach_rawrs_features_at_signal_time(records, rawrs)

    assert result.loc[0, "rawrs_micro_energy"] == 0.10
    assert result.loc[0, "rawrs_feature_timestamp"] == pd.Timestamp("2026-01-01")


def test_no_future_leakage_for_records_before_first_feature() -> None:
    records = pd.DataFrame({"generated_on": ["2026-01-01", "2026-01-04"]})
    rawrs = _rawrs_frame(["2026-01-03", "2026-01-06"], [0.30, 0.60])

    result = attach_rawrs_features_at_signal_time(records, rawrs)

    assert np.isnan(result.loc[0, "rawrs_micro_energy"])
    assert pd.isna(result.loc[0, "rawrs_feature_timestamp"])
    assert result.loc[1, "rawrs_micro_energy"] == 0.30
    assert result.loc[1, "rawrs_feature_timestamp"] == pd.Timestamp("2026-01-03")


def test_timezone_aware_signal_timestamps_attach_to_naive_feature_index() -> None:
    records = pd.DataFrame(
        {"generated_on": pd.to_datetime(["2026-01-02 00:00:00+00:00"])}
    )
    rawrs = _rawrs_frame(["2026-01-02"], [0.25])

    result = attach_rawrs_features_at_signal_time(records, rawrs)

    assert result.loc[0, "rawrs_micro_energy"] == 0.25
    assert result.loc[0, "rawrs_feature_timestamp"] == pd.Timestamp("2026-01-02")


def test_timezone_naive_signal_timestamps_attach_to_aware_feature_index() -> None:
    records = pd.DataFrame({"generated_on": ["2026-01-02"]})
    rawrs = _rawrs_frame(["2026-01-02 00:00:00+00:00"], [0.25])

    result = attach_rawrs_features_at_signal_time(records, rawrs)

    assert result.loc[0, "rawrs_micro_energy"] == 0.25
    assert result.loc[0, "rawrs_feature_timestamp"] == pd.Timestamp("2026-01-02")


def test_both_timezone_aware_timestamps_attach_without_merge_dtype_error() -> None:
    records = pd.DataFrame(
        {"generated_on": pd.to_datetime(["2026-01-02 05:30:00+05:30"])}
    )
    rawrs = _rawrs_frame(["2026-01-02 00:00:00+00:00"], [0.25])

    result = attach_rawrs_features_at_signal_time(records, rawrs)

    assert result.loc[0, "rawrs_micro_energy"] == 0.25
    assert result.loc[0, "rawrs_feature_timestamp"] == pd.Timestamp("2026-01-02")


def test_timezone_normalization_preserves_series_index_and_returns_naive_utc() -> None:
    values = pd.Series(
        pd.to_datetime(["2026-01-02 05:30:00+05:30"]),
        index=pd.Index(["row-a"], name="row"),
        name="generated_on",
    )

    result = normalize_rawrs_join_timestamp(values)

    expected = pd.Series(
        pd.to_datetime(["2026-01-02 00:00:00"]),
        index=values.index,
        name="generated_on",
    )
    pd.testing.assert_series_equal(result, expected)
    assert result.dt.tz is None


def test_attachment_inputs_are_not_mutated() -> None:
    records = pd.DataFrame({"generated_on": ["2026-01-02"], "symbol": ["ABC"]})
    rawrs = _rawrs_frame(["2026-01-02"], [0.25])
    original_records = records.copy(deep=True)
    original_rawrs = rawrs.copy(deep=True)

    attach_rawrs_features_at_signal_time(records, rawrs)

    pd.testing.assert_frame_equal(records, original_records)
    pd.testing.assert_frame_equal(rawrs, original_rawrs)


def test_only_rawrs_feature_columns_attach_by_default() -> None:
    records = pd.DataFrame({"generated_on": ["2026-01-02"]})
    rawrs = _rawrs_frame(["2026-01-02"], [0.25])
    rawrs["other_feature"] = 99.0

    result = attach_rawrs_features_at_signal_time(records, rawrs)

    assert "rawrs_micro_energy" in result.columns
    assert "other_feature" not in result.columns


def test_no_matching_rawrs_feature_columns_raises_value_error() -> None:
    records = pd.DataFrame({"generated_on": ["2026-01-02"]})
    rawrs = pd.DataFrame(
        {"other_feature": [1.0]},
        index=pd.to_datetime(["2026-01-02"]),
    )

    with pytest.raises(ValueError, match="no RAWRS feature columns"):
        attach_rawrs_features_at_signal_time(records, rawrs)


def test_multi_symbol_attachment_preserves_original_row_order() -> None:
    records = pd.DataFrame(
        {
            "symbol": ["BBB", "AAA", "BBB"],
            "generated_on": ["2026-01-03", "2026-01-02", "2026-01-04"],
        },
        index=pd.Index([20, 10, 30], name="row_id"),
    )
    features_by_symbol = {
        "AAA": _rawrs_frame(["2026-01-02"], [1.0]),
        "BBB": _rawrs_frame(["2026-01-01", "2026-01-04"], [2.0, 3.0]),
    }

    result = attach_rawrs_features_by_symbol(records, features_by_symbol)

    assert result.index.equals(records.index)
    assert result["symbol"].tolist() == ["BBB", "AAA", "BBB"]
    assert result["rawrs_micro_energy"].tolist() == [2.0, 1.0, 3.0]


def test_unknown_symbol_leaves_rawrs_values_nan() -> None:
    records = pd.DataFrame(
        {"symbol": ["AAA", "ZZZ"], "generated_on": ["2026-01-02", "2026-01-02"]}
    )
    features_by_symbol = {"AAA": _rawrs_frame(["2026-01-02"], [1.0])}

    result = attach_rawrs_features_by_symbol(records, features_by_symbol)

    assert result.loc[0, "rawrs_micro_energy"] == 1.0
    assert np.isnan(result.loc[1, "rawrs_micro_energy"])
    assert pd.isna(result.loc[1, "rawrs_feature_timestamp"])


def test_missing_symbol_column_raises_value_error() -> None:
    records = pd.DataFrame({"generated_on": ["2026-01-02"]})

    with pytest.raises(ValueError, match="missing required symbol column"):
        attach_rawrs_features_by_symbol(
            records,
            {"AAA": _rawrs_frame(["2026-01-02"], [1.0])},
        )


def test_outcome_summary_groups_features_by_outcome() -> None:
    records = pd.DataFrame(
        {
            "outcome": ["win", "win", "loss"],
            "rawrs_micro_energy": [1.0, 3.0, 5.0],
            "rawrs_fft_spectral_entropy": [0.2, 0.4, 0.8],
            "rawrs_feature_timestamp": pd.to_datetime(
                ["2026-01-01", "2026-01-02", "2026-01-03"]
            ),
        }
    )

    result = summarize_rawrs_feature_by_outcome(records, outcome_col="outcome")

    win_micro = result[
        (result["outcome"] == "win")
        & (result["feature"] == "rawrs_micro_energy")
    ].iloc[0]
    assert win_micro["count"] == 2
    assert win_micro["mean"] == 2.0
    assert "rawrs_feature_timestamp" not in result["feature"].tolist()


def test_outcome_summary_rejects_missing_outcome_column() -> None:
    records = pd.DataFrame({"rawrs_micro_energy": [1.0]})

    with pytest.raises(ValueError, match="missing required outcome column"):
        summarize_rawrs_feature_by_outcome(records, outcome_col="outcome")


def test_bucket_function_returns_bounded_labels_and_handles_low_unique_values() -> None:
    records = pd.DataFrame(
        {"rawrs_micro_energy": [1.0, 1.0, 2.0, 2.0, np.nan]},
        index=pd.Index(["a", "b", "c", "d", "e"]),
    )

    result = bucket_rawrs_feature(records, "rawrs_micro_energy", buckets=5)

    assert result.index.equals(records.index)
    assert result.dropna().between(1, 2).all()
    assert pd.isna(result.loc["e"])

    constant = pd.DataFrame({"rawrs_micro_energy": [1.0, 1.0]})
    assert bucket_rawrs_feature(constant, "rawrs_micro_energy").isna().all()


def test_bucket_summary_includes_counts_and_optional_pnl_r_metrics() -> None:
    records = pd.DataFrame(
        {
            "rawrs_micro_energy": [1.0, 2.0, 3.0, 4.0],
            "outcome": ["loss", "win", "win", "loss"],
            "net_pnl": [-10.0, 20.0, 30.0, -5.0],
            "r_multiple": [-1.0, 2.0, 3.0, -0.5],
        }
    )

    result = summarize_outcome_by_rawrs_bucket(
        records,
        feature_col="rawrs_micro_energy",
        outcome_col="outcome",
        pnl_col="net_pnl",
        r_col="r_multiple",
        buckets=2,
    )

    assert result["count"].tolist() == [2, 2]
    assert {"total_pnl", "mean_pnl", "median_pnl", "mean_r", "median_r"}.issubset(
        result.columns
    )
    assert {"outcome_loss_count", "outcome_win_rate"}.issubset(result.columns)


def test_no_topology_or_regime_labels_are_produced() -> None:
    records = pd.DataFrame({"generated_on": ["2026-01-02"]})
    rawrs = _rawrs_frame(["2026-01-02"], [0.25])

    result = attach_rawrs_features_at_signal_time(records, rawrs)

    forbidden_terms = ("topology", "regime", "label")
    assert not any(
        any(term in column for term in forbidden_terms)
        for column in result.columns
    )


def test_diagnostics_module_does_not_import_forbidden_runner_or_exporter_modules() -> None:
    module = importlib.import_module("veridian_quant.v2.intelligence.rawrs_diagnostics")

    imported_module_names = {
        value.__name__
        for value in vars(module).values()
        if hasattr(value, "__name__") and hasattr(value, "__dict__")
    }
    assert "veridian_quant.v2.reporting.exporters" not in imported_module_names
    assert "veridian_quant.v2.backtesting.portfolio_runner" not in imported_module_names
    assert "veridian_quant.v2.backtesting.s4_portfolio_runner" not in imported_module_names


def _rawrs_frame(dates: list[str], micro_energy: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "rawrs_micro_energy": micro_energy,
            "rawrs_fft_spectral_entropy": [value / 10.0 for value in micro_energy],
        },
        index=pd.to_datetime(dates),
    )
