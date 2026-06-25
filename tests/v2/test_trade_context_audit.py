from __future__ import annotations

import pandas as pd
import pytest

from veridian_quant.v2.analysis.trade_context_audit import (
    annotate_trade_context,
    build_context_bucket_summary,
    build_summary,
    resolve_trade_columns,
    run_trade_context_audit,
)


def test_required_trade_columns_resolved() -> None:
    trades = pd.DataFrame({"symbol": ["AAA"], "entry_date": ["2024-01-05"]})

    resolution = resolve_trade_columns(trades)

    assert resolution.symbol_column == "symbol"
    assert resolution.context_date_column == "entry_date"


def test_context_date_uses_entry_date_by_default_when_present() -> None:
    trades = pd.DataFrame(
        {"symbol": ["AAA"], "entry_date": ["2024-01-06"], "signal_date": ["2024-01-05"]}
    )

    annotated = _annotate(trades)

    assert annotated.loc[0, "context_date"].strftime("%Y-%m-%d") == "2024-01-06"


def test_fallback_to_signal_date_works() -> None:
    trades = pd.DataFrame({"symbol": ["AAA"], "signal_date": ["2024-01-05"]})

    annotated = _annotate(trades)

    assert annotated.loc[0, "context_date"].strftime("%Y-%m-%d") == "2024-01-05"


def test_missing_required_date_columns_fails_clearly() -> None:
    with pytest.raises(ValueError, match="missing context date column"):
        resolve_trade_columns(pd.DataFrame({"symbol": ["AAA"]}))


def test_annotation_adds_benchmark_and_sector_context() -> None:
    trades = pd.DataFrame({"symbol": ["AAA"], "entry_date": ["2024-01-08"]})

    annotated = _annotate(trades)

    assert annotated.loc[0, "sector"] == "Information Technology"
    assert annotated.loc[0, "sector_proxy"] == "NIFTY_IT"
    assert annotated.loc[0, "benchmark_ret_2d"] == pytest.approx((106 / 104) - 1)
    assert annotated.loc[0, "rel_benchmark_ret_2d"] == pytest.approx(((16 / 14) - 1) - ((106 / 104) - 1))
    assert annotated.loc[0, "sector_ret_2d"] == pytest.approx((206 / 204) - 1)
    assert "benchmark_above_sma_50" in annotated.columns
    assert "sector_above_sma_50" in annotated.columns


def test_no_lookahead_context_uses_latest_session_on_or_before_context_date() -> None:
    trades = pd.DataFrame({"symbol": ["AAA"], "entry_date": ["2024-01-07"]})

    annotated = _annotate(trades)

    assert annotated.loc[0, "session_date"].strftime("%Y-%m-%d") == "2024-01-06"
    assert annotated.loc[0, "ret_1d"] == pytest.approx((15 / 14) - 1)


def test_unmapped_sector_produces_sector_missing_flags() -> None:
    trades = pd.DataFrame({"symbol": ["BBB"], "entry_date": ["2024-01-08"]})

    annotated = _annotate(trades)

    assert annotated.loc[0, "sector_proxy"] is None
    assert bool(annotated.loc[0, "sector_proxy_unmapped"]) is True
    assert bool(annotated.loc[0, "missing_sector_context"]) is True


def test_fallback_to_benchmark_for_unmapped_sector_only_when_requested() -> None:
    trades = pd.DataFrame({"symbol": ["BBB"], "entry_date": ["2024-01-08"]})

    without_fallback = _annotate(trades)
    with_fallback = _annotate(trades, fallback=True)

    assert without_fallback.loc[0, "sector_proxy"] is None
    assert with_fallback.loc[0, "sector_proxy"] == "NIFTY_500"
    assert bool(with_fallback.loc[0, "sector_proxy_is_fallback"]) is True
    assert bool(with_fallback.loc[0, "missing_sector_context"]) is False


def test_bucket_summaries_calculate_counts_win_rate_and_avg_r() -> None:
    trades = pd.DataFrame(
        {
            "symbol": ["AAA", "AAA"],
            "entry_date": ["2024-01-08", "2024-01-09"],
            "net_pnl": [100.0, -50.0],
            "r_multiple": [1.5, -0.5],
        }
    )
    annotated = _annotate(trades)

    summary = build_context_bucket_summary(annotated)

    row = summary.loc[summary["bucket"].eq("rel_benchmark_20d_bucket")].iloc[0]
    assert int(row["trade_count"]) == 2
    assert row["win_rate"] == pytest.approx(0.5)
    assert row["avg_r_multiple"] == pytest.approx(0.5)


def test_missing_pnl_and_r_columns_handled_gracefully() -> None:
    trades = pd.DataFrame({"symbol": ["AAA"], "entry_date": ["2024-01-08"]})

    result = run_trade_context_audit(
        trades,
        stock_frames={"AAA": _stock_frame()},
        benchmark_frame=_benchmark_frame(),
        sector_index_frames={"NIFTY_IT": _sector_frame()},
        classifications=_classifications(),
        windows=(1, 2),
    )

    assert result.summary["outcome_columns"]["pnl_column"] is None
    assert result.r_multiple_by_context.empty
    assert result.pnl_by_context.empty


def test_output_summary_json_has_expected_keys() -> None:
    annotated = _annotate(pd.DataFrame({"symbol": ["AAA"], "entry_date": ["2024-01-08"]}))

    summary = build_summary(
        annotated,
        windows=(1, 2),
        benchmark_index="NIFTY_500",
        strategy_name="demo",
        pnl_column=None,
    )

    assert summary["strategy_name"] == "demo"
    assert summary["benchmark_index"] == "NIFTY_500"
    assert "missing_context_counts" in summary
    assert "sector_proxy_trade_counts" in summary


def test_input_trade_dataframe_not_mutated() -> None:
    trades = pd.DataFrame({"symbol": ["AAA"], "entry_date": ["2024-01-08"]})
    before = trades.copy(deep=True)

    _annotate(trades)

    pd.testing.assert_frame_equal(trades, before)


def _annotate(trades: pd.DataFrame, *, fallback: bool = False) -> pd.DataFrame:
    return annotate_trade_context(
        trades,
        stock_frames={"AAA": _stock_frame(), "BBB": _stock_frame()},
        benchmark_frame=_benchmark_frame(),
        sector_index_frames={"NIFTY_IT": _sector_frame()},
        classifications=_classifications(),
        windows=(1, 2),
        fallback_unmapped_sector_to_benchmark=fallback,
    )


def _classifications() -> dict[str, dict[str, str]]:
    return {
        "AAA": {"sector": "Information Technology", "market_cap_bucket": "unknown"},
        "BBB": {"sector": "Glass", "market_cap_bucket": "unknown"},
    }


def _stock_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-06", "2024-01-08", "2024-01-09"]
            ),
            "open": [10, 11, 12, 13, 14, 15, 16, 17],
            "high": [10, 11, 12, 13, 14, 15, 16, 17],
            "low": [10, 11, 12, 13, 14, 15, 16, 17],
            "close": [10, 11, 12, 13, 14, 15, 16, 17],
            "volume": [100] * 8,
        }
    )


def _benchmark_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "session_date": pd.to_datetime(
                ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-06", "2024-01-08", "2024-01-09"]
            ),
            "close": [100, 101, 102, 103, 104, 105, 106, 107],
        }
    )


def _sector_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "session_date": pd.to_datetime(
                ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-06", "2024-01-08", "2024-01-09"]
            ),
            "close": [200, 201, 202, 203, 204, 205, 206, 207],
        }
    )