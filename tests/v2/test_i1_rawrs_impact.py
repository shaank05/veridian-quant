"""Tests for standalone I1 RAWRS completed-trade impact diagnostics."""

import importlib

import numpy as np
import pandas as pd
import pandas.testing as pdt

from veridian_quant.v2.intelligence.rawrs_impact import (
    assign_rawrs_feature_buckets,
    build_rawrs_feature_impact_leaderboard,
    build_rawrs_keep_avoid_impact_summary,
    export_rawrs_impact_csvs,
    infer_rawrs_feature_columns,
    summarize_trade_subset,
)


def _trades() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "rawrs_alpha": range(1, 11),
            "rawrs_beta": np.arange(10, 0, -1, dtype=float),
            "rawrs_realized_r": [-2, -1, -0.5, 0, 0.5, 1, 1.5, 2, 2.5, 3],
            "net_pnl": [-20, -10, -5, 0, 5, 10, 15, 20, 25, 30],
            "initial_risk_amount": [10.0] * 10,
        },
        index=pd.Index(range(20, 30), name="trade_row"),
    )


def test_feature_inference_excludes_metadata_performance_and_non_numeric() -> None:
    frame = _trades().assign(
        rawrs_feature_timestamp=pd.Timestamp("2026-01-01"),
        rawrs_text="not numeric",
    )
    assert infer_rawrs_feature_columns(frame) == ["rawrs_alpha", "rawrs_beta"]


def test_bucket_assignment_preserves_index_and_reduces_low_unique_values() -> None:
    frame = pd.DataFrame({"rawrs_alpha": [1, 1, 2, 2, np.nan]}, index=[9, 7, 5, 3, 1])
    result = assign_rawrs_feature_buckets(frame, "rawrs_alpha")
    assert result.index.equals(frame.index)
    assert set(result.dropna()) == {1, 2}
    assert pd.isna(result.loc[1])


def test_trade_subset_summary_computes_pnl_outcome_r_and_risk_metrics() -> None:
    result = summarize_trade_subset(_trades())
    assert result["trade_count"] == 10
    assert result["net_pnl_sum"] == 70
    assert result["win_count"] == 6
    assert result["loss_count"] == 3
    assert result["win_rate"] == 0.6
    assert result["mean_r"] == 0.7
    assert result["median_r"] == 0.75
    assert result["profit_factor"] == 3.0
    assert result["total_initial_risk"] == 100


def test_keep_avoid_rules_select_expected_quantile_buckets_and_metrics() -> None:
    summary = build_rawrs_keep_avoid_impact_summary(_trades(), feature_cols=["rawrs_alpha"])
    rows = summary.set_index("rule")
    assert rows.loc["avoid_bucket_1", "kept_trade_count"] == 8
    assert rows.loc["avoid_buckets_1_2", "kept_trade_count"] == 6
    assert rows.loc["keep_bucket_5", "kept_trade_count"] == 2
    assert rows.loc["keep_buckets_4_5", "kept_trade_count"] == 4
    assert rows.loc["avoid_bucket_1", "removed_net_pnl"] == -30
    assert rows.loc["keep_bucket_5", "kept_mean_r"] == 2.75
    assert rows.loc["avoid_bucket_1", "original_trade_count"] == 10
    assert rows.loc["avoid_bucket_1", "original_net_pnl"] == 70


def test_impact_builders_do_not_mutate_inputs_and_leaderboard_is_deterministic() -> None:
    trades = _trades()
    before = trades.copy(deep=True)
    summary = build_rawrs_keep_avoid_impact_summary(trades)
    leaderboard_one = build_rawrs_feature_impact_leaderboard(summary)
    leaderboard_two = build_rawrs_feature_impact_leaderboard(summary)
    pdt.assert_frame_equal(trades, before)
    pdt.assert_frame_equal(leaderboard_one, leaderboard_two)
    assert "low_sample_warning" in leaderboard_one
    assert leaderboard_one["low_sample_warning"].any()


def test_reduced_bucket_count_is_noted() -> None:
    trades = _trades().iloc[:4].copy()
    trades["rawrs_alpha"] = [1, 1, 2, 2]
    summary = build_rawrs_keep_avoid_impact_summary(trades, feature_cols=["rawrs_alpha"])
    assert set(summary["bucket_count"]) == {2}
    assert summary["diagnostic_note"].str.contains("reduced from 5 to 2").all()


def test_export_writes_stable_filenames_without_mutation(tmp_path) -> None:
    summary = build_rawrs_keep_avoid_impact_summary(_trades())
    leaderboard = build_rawrs_feature_impact_leaderboard(summary)
    before = summary.copy(deep=True)
    paths = export_rawrs_impact_csvs(
        output_dir=tmp_path,
        keep_avoid_summary=summary,
        feature_impact_leaderboard=leaderboard,
    )
    assert paths["keep_avoid_summary"].name == "rawrs_keep_avoid_impact_summary.csv"
    assert paths["feature_impact_leaderboard"].name == "rawrs_feature_impact_leaderboard.csv"
    assert all(path.exists() for path in paths.values())
    pdt.assert_frame_equal(summary, before)


def test_impact_module_has_no_strategy_backtesting_or_reporting_imports() -> None:
    module = importlib.import_module("veridian_quant.v2.intelligence.rawrs_impact")
    imported = {
        value.__name__
        for value in vars(module).values()
        if hasattr(value, "__name__") and hasattr(value, "__dict__")
    }
    assert not any(
        name.startswith(
            (
                "veridian_quant.v2.strategies",
                "veridian_quant.v2.backtesting",
                "veridian_quant.v2.reporting",
            )
        )
        for name in imported
    )
