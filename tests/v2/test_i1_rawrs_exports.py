"""Unit tests for standalone I1 RAWRS diagnostic exports."""

import importlib

import numpy as np
import pandas as pd
import pytest

from veridian_quant.v2.intelligence.rawrs_exports import (
    ensure_rawrs_realized_r,
    build_rawrs_feature_bucket_summary,
    build_rawrs_rejection_diagnostics,
    build_rawrs_signal_diagnostics,
    build_rawrs_trade_diagnostics,
    export_rawrs_diagnostic_csvs,
)


def test_export_creates_output_directory(tmp_path) -> None:
    output_dir = tmp_path / "nested" / "rawrs"

    paths = export_rawrs_diagnostic_csvs(
        output_dir=output_dir,
        signal_diagnostics=pd.DataFrame({"symbol": ["AAA"]}),
    )

    assert output_dir.exists()
    assert paths["signal_diagnostics"].exists()


def test_export_writes_only_provided_dataframes(tmp_path) -> None:
    paths = export_rawrs_diagnostic_csvs(
        output_dir=tmp_path,
        signal_diagnostics=pd.DataFrame({"symbol": ["AAA"]}),
        feature_bucket_summary=pd.DataFrame({"bucket": [1]}),
    )

    assert set(paths) == {"signal_diagnostics", "feature_bucket_summary"}
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "rawrs_feature_bucket_summary.csv",
        "rawrs_signal_diagnostics.csv",
    ]


def test_export_writes_stable_filenames(tmp_path) -> None:
    paths = export_rawrs_diagnostic_csvs(
        output_dir=tmp_path,
        signal_diagnostics=pd.DataFrame(),
        trade_diagnostics=pd.DataFrame(),
        rejection_diagnostics=pd.DataFrame(),
        feature_bucket_summary=pd.DataFrame(),
        feature_by_year_summary=pd.DataFrame(),
        feature_by_strategy_summary=pd.DataFrame(),
        same_day_candidate_pool_summary=pd.DataFrame(),
    )

    assert paths["signal_diagnostics"].name == "rawrs_signal_diagnostics.csv"
    assert paths["trade_diagnostics"].name == "rawrs_trade_diagnostics.csv"
    assert paths["rejection_diagnostics"].name == "rawrs_rejection_diagnostics.csv"
    assert paths["feature_bucket_summary"].name == "rawrs_feature_bucket_summary.csv"
    assert paths["feature_by_year_summary"].name == "rawrs_feature_by_year_summary.csv"
    assert (
        paths["feature_by_strategy_summary"].name
        == "rawrs_feature_by_strategy_summary.csv"
    )
    assert (
        paths["same_day_candidate_pool_summary"].name
        == "rawrs_same_day_candidate_pool_summary.csv"
    )


def test_export_returns_logical_names_and_paths(tmp_path) -> None:
    paths = export_rawrs_diagnostic_csvs(
        output_dir=tmp_path,
        trade_diagnostics=pd.DataFrame({"trade_id": [1]}),
    )

    assert list(paths) == ["trade_diagnostics"]
    assert paths["trade_diagnostics"] == tmp_path / "rawrs_trade_diagnostics.csv"


def test_export_writes_empty_dataframe_if_explicitly_provided(tmp_path) -> None:
    paths = export_rawrs_diagnostic_csvs(
        output_dir=tmp_path,
        rejection_diagnostics=pd.DataFrame(columns=["symbol", "reason"]),
    )

    written = pd.read_csv(paths["rejection_diagnostics"])
    assert list(written.columns) == ["symbol", "reason"]
    assert written.empty


def test_export_raises_value_error_when_no_dataframes_provided(tmp_path) -> None:
    with pytest.raises(ValueError, match="at least one RAWRS diagnostic DataFrame"):
        export_rawrs_diagnostic_csvs(output_dir=tmp_path)


def test_export_does_not_mutate_input_dataframes(tmp_path) -> None:
    frame = pd.DataFrame({"symbol": ["AAA"], "value": [1.0]})
    original = frame.copy(deep=True)

    export_rawrs_diagnostic_csvs(output_dir=tmp_path, signal_diagnostics=frame)

    pd.testing.assert_frame_equal(frame, original)


def test_trade_diagnostics_builder_attaches_rawrs_and_preserves_rows_order() -> None:
    trades = pd.DataFrame(
        {"symbol": ["BBB", "AAA"], "signal_date": ["2026-01-03", "2026-01-02"]},
        index=pd.Index([7, 3], name="row_id"),
    )

    result = build_rawrs_trade_diagnostics(trades, _features_by_symbol())

    assert result.index.equals(trades.index)
    assert result["symbol"].tolist() == ["BBB", "AAA"]
    assert result["rawrs_micro_energy"].tolist() == [2.0, 1.0]


def test_signal_diagnostics_builder_attaches_rawrs_and_preserves_rows_order() -> None:
    signals = pd.DataFrame(
        {"symbol": ["AAA", "BBB"], "generated_on": ["2026-01-02", "2026-01-04"]}
    )

    result = build_rawrs_signal_diagnostics(signals, _features_by_symbol())

    assert len(result) == len(signals)
    assert result["symbol"].tolist() == ["AAA", "BBB"]
    assert result["rawrs_micro_energy"].tolist() == [1.0, 3.0]


def test_rejection_diagnostics_builder_attaches_rawrs_and_preserves_rows_order() -> None:
    rejections = pd.DataFrame(
        {
            "symbol": ["AAA", "BBB"],
            "signal_date": ["2026-01-02", "2026-01-03"],
            "reason": ["capacity", "active_symbol"],
        }
    )

    result = build_rawrs_rejection_diagnostics(rejections, _features_by_symbol())

    assert len(result) == len(rejections)
    assert result["reason"].tolist() == ["capacity", "active_symbol"]
    assert result["rawrs_micro_energy"].tolist() == [1.0, 2.0]


def test_unknown_symbols_produce_nan_rawrs_values_not_crashes() -> None:
    signals = pd.DataFrame(
        {"symbol": ["AAA", "ZZZ"], "generated_on": ["2026-01-02", "2026-01-02"]}
    )

    result = build_rawrs_signal_diagnostics(signals, _features_by_symbol())

    assert result.loc[0, "rawrs_micro_energy"] == 1.0
    assert np.isnan(result.loc[1, "rawrs_micro_energy"])
    assert pd.isna(result.loc[1, "rawrs_feature_timestamp"])


def test_feature_bucket_summary_combines_per_feature_summaries() -> None:
    records = pd.DataFrame(
        {
            "outcome": ["loss", "win", "win", "loss"],
            "rawrs_micro_energy": [1.0, 2.0, 3.0, 4.0],
            "rawrs_fft_spectral_entropy": [0.1, 0.2, 0.3, 0.4],
            "net_pnl": [-10.0, 20.0, 30.0, -5.0],
            "r_multiple": [-1.0, 2.0, 3.0, -0.5],
        }
    )

    result = build_rawrs_feature_bucket_summary(
        records,
        outcome_col="outcome",
        pnl_col="net_pnl",
        r_col="r_multiple",
        buckets=2,
    )

    assert set(result["feature"]) == {
        "rawrs_micro_energy",
        "rawrs_fft_spectral_entropy",
    }
    assert result.groupby("feature")["bucket"].nunique().to_dict() == {
        "rawrs_fft_spectral_entropy": 2,
        "rawrs_micro_energy": 2,
    }
    assert {"total_pnl", "mean_r", "outcome_win_rate"}.issubset(result.columns)


def test_feature_bucket_summary_uses_r_multiple_when_available() -> None:
    records = _bucket_records()
    records["r_multiple"] = [10.0, 20.0, 30.0, 40.0]
    records["realized_r"] = [1.0, 1.0, 1.0, 1.0]

    result = build_rawrs_feature_bucket_summary(
        records,
        outcome_col="outcome",
        feature_cols=["rawrs_micro_energy"],
        buckets=2,
    )

    assert result["mean_r"].tolist() == [15.0, 35.0]


def test_feature_bucket_summary_uses_realized_r_when_r_multiple_missing() -> None:
    records = _bucket_records()
    records["realized_r"] = [1.0, -0.5, 2.0, -1.5]

    result = build_rawrs_feature_bucket_summary(
        records,
        outcome_col="outcome",
        feature_cols=["rawrs_micro_energy"],
        buckets=2,
    )

    assert result["mean_r"].tolist() == [0.25, 0.25]


def test_ensure_rawrs_realized_r_computes_from_net_pnl_and_initial_risk() -> None:
    records = pd.DataFrame(
        {
            "net_pnl": [100.0, -50.0, 25.0],
            "initial_risk_amount": [50.0, 100.0, 0.0],
        }
    )
    original = records.copy(deep=True)

    result = ensure_rawrs_realized_r(records)

    assert result["rawrs_realized_r"].iloc[0] == 2.0
    assert result["rawrs_realized_r"].iloc[1] == -0.5
    assert pd.isna(result["rawrs_realized_r"].iloc[2])
    pd.testing.assert_frame_equal(records, original)


def test_reward_risk_ratio_alone_is_not_used_as_realized_r() -> None:
    records = _bucket_records()
    records["reward_risk_ratio"] = [2.0, 2.0, 2.0, 2.0]

    result = build_rawrs_feature_bucket_summary(
        records,
        outcome_col="outcome",
        feature_cols=["rawrs_micro_energy"],
        buckets=2,
    )

    assert "mean_r" not in result.columns
    assert "median_r" not in result.columns


def test_feature_bucket_summary_uses_computed_rawrs_realized_r() -> None:
    records = _bucket_records()
    records["net_pnl"] = [100.0, -50.0, 200.0, -150.0]
    records["initial_risk_amount"] = [50.0, 100.0, 100.0, 300.0]
    records["reward_risk_ratio"] = [2.0, 2.0, 2.0, 2.0]

    result = build_rawrs_feature_bucket_summary(
        records,
        outcome_col="outcome",
        feature_cols=["rawrs_micro_energy"],
        buckets=2,
    )

    assert result["mean_r"].tolist() == [0.75, 0.75]


def test_feature_bucket_summary_raises_when_no_usable_rawrs_features() -> None:
    records = pd.DataFrame(
        {
            "outcome": ["win", "loss"],
            "rawrs_feature_timestamp": pd.to_datetime(["2026-01-01", "2026-01-02"]),
            "other_feature": [1.0, 2.0],
        }
    )

    with pytest.raises(ValueError, match="no usable RAWRS feature columns"):
        build_rawrs_feature_bucket_summary(records, outcome_col="outcome")


def test_exports_module_does_not_require_forbidden_modules() -> None:
    module = importlib.import_module("veridian_quant.v2.intelligence.rawrs_exports")

    imported_module_names = {
        value.__name__
        for value in vars(module).values()
        if hasattr(value, "__name__") and hasattr(value, "__dict__")
    }
    assert "veridian_quant.v2.reporting.exporters" not in imported_module_names
    assert "veridian_quant.v2.backtesting.portfolio_runner" not in imported_module_names
    assert "veridian_quant.v2.backtesting.s4_portfolio_runner" not in imported_module_names


def test_no_topology_or_regime_labels_are_produced() -> None:
    signals = pd.DataFrame({"symbol": ["AAA"], "generated_on": ["2026-01-02"]})

    result = build_rawrs_signal_diagnostics(signals, _features_by_symbol())

    forbidden_terms = ("topology", "regime", "label")
    assert not any(
        any(term in column for term in forbidden_terms)
        for column in result.columns
    )


def _features_by_symbol() -> dict[str, pd.DataFrame]:
    return {
        "AAA": _rawrs_frame(["2026-01-02"], [1.0]),
        "BBB": _rawrs_frame(["2026-01-01", "2026-01-04"], [2.0, 3.0]),
    }


def _rawrs_frame(dates: list[str], micro_energy: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "rawrs_micro_energy": micro_energy,
            "rawrs_fft_spectral_entropy": [value / 10.0 for value in micro_energy],
        },
        index=pd.to_datetime(dates),
    )


def _bucket_records() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "outcome": ["win", "loss", "win", "loss"],
            "rawrs_micro_energy": [1.0, 2.0, 3.0, 4.0],
        }
    )
