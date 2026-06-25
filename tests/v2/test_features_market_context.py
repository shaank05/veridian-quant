"""Tests for Phase 33E benchmark, sector, and cap context utilities."""

import numpy as np
import pandas as pd
import pytest

from veridian_quant.v2.data.sector_proxy_mapping import resolve_sector_proxy
from veridian_quant.v2.features.market_context import (
    align_stock_with_index,
    compute_cap_relative_context,
    compute_market_context_features,
    compute_market_relative_context,
    compute_returns_by_window,
    compute_sector_relative_context,
)


def test_market_relative_returns_are_computed_for_matching_windows() -> None:
    stock = _frame([100, 102, 104, 106, 108, 110, 120])
    benchmark = _frame([200, 202, 204, 206, 208, 210, 220])

    result = compute_market_relative_context(stock, benchmark, windows=(5,))

    assert result.loc[5, "ret_5d"] == pytest.approx(0.10)
    assert result.loc[5, "benchmark_ret_5d"] == pytest.approx(0.05)
    assert result.loc[5, "rel_benchmark_ret_5d"] == pytest.approx(0.05)
    assert result.loc[5, "stock_return_ratio_vs_benchmark_5d"] == pytest.approx(2.0)


def test_returns_preserve_nan_for_insufficient_lookback() -> None:
    result = compute_returns_by_window(_frame([100, 101, 102]), windows=(2,))

    assert result["ret_2d"].isna().iloc[0]
    assert result["ret_2d"].isna().iloc[1]
    assert result["ret_2d"].iloc[2] == pytest.approx(0.02)


def test_stock_and_index_are_inner_aligned_by_session_date() -> None:
    stock = _frame([100, 101, 102, 103], start="2026-01-01")
    benchmark = _frame([200, 202, 204], start="2026-01-02")

    result = align_stock_with_index(stock, benchmark)

    assert result["session_date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2026-01-02",
        "2026-01-03",
        "2026-01-04",
    ]
    assert result["stock_close"].tolist() == [101, 102, 103]


def test_no_lookahead_current_row_uses_only_current_and_past_closes() -> None:
    stock = _frame([100, 110, 1000])
    benchmark = _frame([100, 100, 100])

    result = compute_market_relative_context(stock, benchmark, windows=(1,))

    assert result.loc[1, "ret_1d"] == pytest.approx(0.10)
    assert result.loc[1, "ret_1d"] != pytest.approx((1000 / 110) - 1.0)


def test_missing_index_date_drops_only_unaligned_session() -> None:
    stock = _frame([100, 101, 102, 103])
    benchmark = _frame([200, 202, 206]).assign(
        session_date=pd.to_datetime(["2026-01-01", "2026-01-03", "2026-01-04"])
    )

    result = compute_market_relative_context(stock, benchmark, windows=(1,))

    assert result["session_date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2026-01-01",
        "2026-01-03",
        "2026-01-04",
    ]


def test_zero_prior_benchmark_close_does_not_crash_or_infinite_ratio() -> None:
    stock = _frame([100, 110])
    benchmark = _frame([0, 100])

    result = compute_market_relative_context(stock, benchmark, windows=(1,))

    assert np.isnan(result.loc[1, "benchmark_ret_1d"])
    assert np.isnan(result.loc[1, "stock_return_ratio_vs_benchmark_1d"])


@pytest.mark.parametrize(
    ("sector", "expected"),
    [
        ("Banking", "NIFTY_BANK"),
        ("Financial Services", "NIFTY_FIN_SERVICE"),
        ("Information Technology", "NIFTY_IT"),
        ("Pharmaceuticals", "NIFTY_PHARMA"),
        ("Automobile", "NIFTY_AUTO"),
        ("Consumer Goods", "NIFTY_FMCG"),
        ("Mining", "NIFTY_METAL"),
        ("Oil & Gas", "NIFTY_ENERGY"),
        ("Real Estate", "NIFTY_REALTY"),
    ],
)
def test_sector_proxy_resolution_for_known_examples(sector: str, expected: str) -> None:
    resolution = resolve_sector_proxy(sector)

    assert resolution.sector_proxy == expected
    assert resolution.sector_proxy_unmapped is False
    assert resolution.sector_proxy_is_fallback is False


@pytest.mark.parametrize(
    ("sector", "expected"),
    [
        ("BPO/ITeS", "NIFTY_IT"),
        ("Consumer Food", "NIFTY_FMCG"),
        ("Gases & Fuels", "NIFTY_ENERGY"),
        ("Household Products", "NIFTY_FMCG"),
        ("Ratings", "NIFTY_FIN_SERVICE"),
        ("Refineries", "NIFTY_ENERGY"),
        ("Tobacco", "NIFTY_FMCG"),
        ("Tyres & Allied", "NIFTY_AUTO"),
        ("Breweries", "NIFTY_FMCG"),
        ("Construction", "NIFTY_REALTY"),
        ("Minerals", "NIFTY_METAL"),
    ],
)
def test_approved_static_sector_labels_resolve_to_proxy(
    sector: str,
    expected: str,
) -> None:
    resolution = resolve_sector_proxy(sector)

    assert resolution.sector_proxy == expected
    assert resolution.sector_proxy_unmapped is False
    assert resolution.sector_proxy_is_fallback is False


@pytest.mark.parametrize(
    "sector",
    [
        "Electric Equipment",
        "Healthcare Services",
        "IT - Hardware",
        "Investment",
        "Lubricants",
        "Sugar",
    ],
)
def test_explicitly_unmapped_static_sector_labels_remain_unmapped(sector: str) -> None:
    resolution = resolve_sector_proxy(sector)

    assert resolution.sector_proxy is None
    assert resolution.sector_proxy_unmapped is True
    assert resolution.sector_proxy_is_fallback is False


def test_unknown_sector_can_return_unmapped_without_fallback() -> None:
    resolution = resolve_sector_proxy("Glass")

    assert resolution.sector_proxy is None
    assert resolution.sector_proxy_unmapped is True
    assert resolution.sector_proxy_is_fallback is False


def test_unknown_sector_can_return_nifty500_fallback_flag() -> None:
    resolution = resolve_sector_proxy("Glass", fallback_to_nifty500=True)

    assert resolution.sector_proxy == "NIFTY_500"
    assert resolution.sector_proxy_unmapped is True
    assert resolution.sector_proxy_is_fallback is True


def test_explicit_unmapped_sector_can_return_nifty500_fallback_flag() -> None:
    resolution = resolve_sector_proxy("Electric Equipment", fallback_to_nifty500=True)

    assert resolution.sector_proxy == "NIFTY_500"
    assert resolution.sector_proxy_unmapped is True
    assert resolution.sector_proxy_is_fallback is True


def test_sector_relative_context_uses_metadata_and_relative_returns() -> None:
    stock = _frame([100, 105, 110])
    sector_index = _frame([200, 202, 204])

    result = compute_sector_relative_context(
        stock,
        sector_index,
        windows=(2,),
        sector="Information Technology",
    )

    assert result.loc[2, "sector_proxy"] == "NIFTY_IT"
    assert result.loc[2, "sector_ret_2d"] == pytest.approx(0.02)
    assert result.loc[2, "rel_sector_ret_2d"] == pytest.approx(0.10 - 0.02)


def test_input_dataframes_are_not_mutated() -> None:
    stock = _frame([100, 110, 120])
    benchmark = _frame([200, 210, 220])
    stock_before = stock.copy(deep=True)
    benchmark_before = benchmark.copy(deep=True)

    compute_market_relative_context(stock, benchmark, windows=(1,))

    pd.testing.assert_frame_equal(stock, stock_before)
    pd.testing.assert_frame_equal(benchmark, benchmark_before)


def test_required_column_validation() -> None:
    with pytest.raises(ValueError, match="missing required columns: close"):
        compute_returns_by_window(pd.DataFrame({"session_date": ["2026-01-01"]}), windows=(1,))


def test_market_cap_bucket_unknown_path_is_safe() -> None:
    result = compute_cap_relative_context(
        _frame([100, 101, 102]),
        windows=(1,),
        market_cap_bucket="unknown",
    )

    assert result["market_cap_bucket"].tolist() == ["unknown", "unknown", "unknown"]
    assert result["cap_proxy_unmapped"].tolist() == [True, True, True]
    assert result["cap_ret_1d"].isna().all()
    assert result["rel_cap_ret_1d"].isna().all()


def test_combined_market_context_features_have_deterministic_columns() -> None:
    stock = _frame([100, 105, 110])
    benchmark = _frame([200, 202, 204])

    result = compute_market_context_features(
        stock,
        benchmark,
        windows=(2,),
        sector="Glass",
        fallback_sector_to_nifty500=True,
    )

    expected_columns = {
        "session_date",
        "stock_close",
        "benchmark_close",
        "benchmark",
        "ret_2d",
        "benchmark_ret_2d",
        "rel_benchmark_ret_2d",
        "stock_return_ratio_vs_benchmark_2d",
        "sector_proxy",
        "sector_proxy_is_fallback",
        "sector_proxy_unmapped",
        "market_cap_bucket",
        "cap_proxy_unmapped",
    }
    assert expected_columns.issubset(result.columns)
    assert result.loc[0, "sector_proxy"] == "NIFTY_500"
    assert bool(result.loc[0, "sector_proxy_is_fallback"]) is True


def _frame(values: list[float], start: str = "2026-01-01") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "session_date": pd.date_range(start=start, periods=len(values), freq="D"),
            "close": values,
            "open": values,
            "high": values,
            "low": values,
            "volume": [1000] * len(values),
        }
    )

