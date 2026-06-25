"""Read-only trade context annotation utilities for Phase 33F.

The functions in this module annotate existing trade logs with market and sector
context that was knowable on or before the trade context date. They do not run
strategies, generate signals, or mutate caller-provided dataframes.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import pandas as pd

from veridian_quant.v2.data.sector_proxy_mapping import resolve_sector_proxy
from veridian_quant.v2.features.market_context import compute_market_context_features


DEFAULT_WINDOWS = (5, 20, 60, 120)
REQUIRED_TREND_WINDOWS = (50, 200)
AUTO_CONTEXT_DATE_COLUMNS = ("entry_date", "entry_signal_date", "signal_date")
OUTCOME_COLUMNS = ("net_pnl", "pnl", "gross_pnl")


@dataclass(frozen=True, slots=True)
class TradeColumnResolution:
    """Resolved trade-log columns used by the audit."""

    symbol_column: str
    context_date_column: str


@dataclass(frozen=True, slots=True)
class TradeContextAuditResult:
    """Annotated trades, aggregate outputs, and compact summary."""

    annotated: pd.DataFrame
    context_bucket_summary: pd.DataFrame
    exit_reason_by_context: pd.DataFrame
    sector_proxy_trade_coverage: pd.DataFrame
    missing_context_summary: pd.DataFrame
    r_multiple_by_context: pd.DataFrame
    pnl_by_context: pd.DataFrame
    summary: dict[str, object]


def resolve_trade_columns(
    trades: pd.DataFrame,
    *,
    context_date_column: str = "auto",
) -> TradeColumnResolution:
    """Resolve symbol and context-date columns for common trade-log shapes."""

    if "symbol" not in trades.columns:
        raise ValueError("trade log missing required column: symbol")
    if context_date_column != "auto":
        if context_date_column not in trades.columns:
            raise ValueError(f"trade log missing requested context date column: {context_date_column}")
        return TradeColumnResolution("symbol", context_date_column)
    for column in AUTO_CONTEXT_DATE_COLUMNS:
        if column in trades.columns:
            return TradeColumnResolution("symbol", column)
    candidates = ", ".join(AUTO_CONTEXT_DATE_COLUMNS)
    raise ValueError(f"trade log missing context date column; expected one of: {candidates}")


def annotate_trade_context(
    trades: pd.DataFrame,
    *,
    stock_frames: Mapping[str, pd.DataFrame],
    benchmark_frame: pd.DataFrame,
    sector_index_frames: Mapping[str, pd.DataFrame] | None,
    classifications: Mapping[str, Mapping[str, object]],
    windows: Iterable[int] = DEFAULT_WINDOWS,
    benchmark_index: str = "NIFTY_500",
    context_date_column: str = "auto",
    fallback_unmapped_sector_to_benchmark: bool = False,
) -> pd.DataFrame:
    """Return a trade log annotated with prior benchmark and sector context."""

    selected_windows = _validate_windows(windows)
    compute_windows = tuple(sorted({*selected_windows, *REQUIRED_TREND_WINDOWS}))
    sector_index_frames = sector_index_frames or {}
    resolution = resolve_trade_columns(trades, context_date_column=context_date_column)

    result = trades.copy(deep=True).reset_index(drop=False).rename(columns={"index": "_trade_row_id"})
    result["symbol"] = result[resolution.symbol_column].astype(str).str.strip().str.upper()
    result["context_date"] = _normalize_dates(result[resolution.context_date_column])

    feature_frames: list[pd.DataFrame] = []
    for symbol in sorted(result["symbol"].dropna().unique()):
        stock_frame = stock_frames.get(symbol)
        if stock_frame is None or stock_frame.empty:
            continue
        classification = classifications.get(symbol, {})
        sector = _clean(classification.get("sector")) or "UNKNOWN"
        market_cap_bucket = _clean(classification.get("market_cap_bucket")) or "unknown"
        sector_resolution = resolve_sector_proxy(
            sector,
            fallback_to_nifty500=fallback_unmapped_sector_to_benchmark,
        )
        sector_frame = None
        if sector_resolution.sector_proxy == benchmark_index:
            sector_frame = benchmark_frame
        elif sector_resolution.sector_proxy is not None:
            sector_frame = sector_index_frames.get(sector_resolution.sector_proxy)

        features = compute_market_context_features(
            stock_frame,
            benchmark_frame,
            sector_index_df=sector_frame,
            windows=compute_windows,
            benchmark_name=benchmark_index,
            sector=sector,
            sector_proxy=None,
            fallback_sector_to_nifty500=fallback_unmapped_sector_to_benchmark,
            market_cap_bucket=market_cap_bucket,
        )
        if features.empty:
            continue
        features = features.copy()
        features.insert(0, "symbol", symbol)
        feature_frames.append(features)

    if feature_frames:
        context_features = pd.concat(feature_frames, ignore_index=True)
        annotated = _merge_context_asof(result, context_features)
    else:
        annotated = result.copy()
        annotated["session_date"] = pd.NaT

    annotated = _ensure_annotation_columns(annotated, selected_windows)
    annotated = _attach_trend_aliases(annotated)
    annotated = _attach_missing_flags(annotated, selected_windows)
    annotated = add_context_buckets(annotated)
    annotated = annotated.sort_values("_trade_row_id", kind="mergesort").drop(
        columns=["_trade_row_id"],
        errors="ignore",
    )
    return annotated.reset_index(drop=True)


def run_trade_context_audit(
    trades: pd.DataFrame,
    *,
    stock_frames: Mapping[str, pd.DataFrame],
    benchmark_frame: pd.DataFrame,
    sector_index_frames: Mapping[str, pd.DataFrame] | None,
    classifications: Mapping[str, Mapping[str, object]],
    windows: Iterable[int] = DEFAULT_WINDOWS,
    benchmark_index: str = "NIFTY_500",
    context_date_column: str = "auto",
    strategy_name: str | None = None,
    fallback_unmapped_sector_to_benchmark: bool = False,
) -> TradeContextAuditResult:
    """Annotate trades and build compact diagnostic outputs."""

    annotated = annotate_trade_context(
        trades,
        stock_frames=stock_frames,
        benchmark_frame=benchmark_frame,
        sector_index_frames=sector_index_frames,
        classifications=classifications,
        windows=windows,
        benchmark_index=benchmark_index,
        context_date_column=context_date_column,
        fallback_unmapped_sector_to_benchmark=fallback_unmapped_sector_to_benchmark,
    )
    bucket_summary = build_context_bucket_summary(annotated)
    exit_summary = build_exit_reason_by_context(annotated)
    sector_coverage = build_sector_proxy_trade_coverage(annotated)
    missing_summary = build_missing_context_summary(annotated)
    r_summary = build_metric_by_context(annotated, "r_multiple")
    pnl_column = _first_existing_column(annotated, OUTCOME_COLUMNS)
    pnl_summary = build_metric_by_context(annotated, pnl_column) if pnl_column else _empty_metric_summary()
    summary = build_summary(
        annotated,
        windows=tuple(windows),
        benchmark_index=benchmark_index,
        strategy_name=strategy_name,
        pnl_column=pnl_column,
    )
    return TradeContextAuditResult(
        annotated=annotated,
        context_bucket_summary=bucket_summary,
        exit_reason_by_context=exit_summary,
        sector_proxy_trade_coverage=sector_coverage,
        missing_context_summary=missing_summary,
        r_multiple_by_context=r_summary,
        pnl_by_context=pnl_summary,
        summary=summary,
    )


def add_context_buckets(frame: pd.DataFrame) -> pd.DataFrame:
    """Attach fixed diagnostic context buckets."""

    result = frame.copy(deep=True)
    result["benchmark_20d_bucket"] = result.get("benchmark_ret_20d", pd.Series(np.nan, index=result.index)).map(
        _return_bucket
    )
    result["rel_benchmark_20d_bucket"] = result.get(
        "rel_benchmark_ret_20d", pd.Series(np.nan, index=result.index)
    ).map(_relative_bucket)
    result["sector_20d_bucket"] = result.get("sector_ret_20d", pd.Series(np.nan, index=result.index)).map(
        _return_bucket
    )
    result["benchmark_trend_bucket"] = result.get(
        "benchmark_above_sma_50d", pd.Series(np.nan, index=result.index)
    ).map(_trend_bucket)
    result["sector_trend_bucket"] = result.get(
        "sector_above_sma_50d", pd.Series(np.nan, index=result.index)
    ).map(_trend_bucket)
    return result


def build_context_bucket_summary(annotated: pd.DataFrame) -> pd.DataFrame:
    buckets = [
        "benchmark_20d_bucket",
        "rel_benchmark_20d_bucket",
        "sector_20d_bucket",
        "benchmark_trend_bucket",
        "sector_trend_bucket",
    ]
    rows: list[dict[str, object]] = []
    for bucket in buckets:
        if bucket not in annotated.columns:
            continue
        for value, group in annotated.groupby(bucket, dropna=False, sort=True):
            rows.append(_metric_row(bucket, value, group))
    return pd.DataFrame(rows)


def build_exit_reason_by_context(annotated: pd.DataFrame) -> pd.DataFrame:
    if "exit_reason" not in annotated.columns:
        return pd.DataFrame(columns=["bucket", "bucket_value", "exit_reason", "trade_count"])
    rows: list[dict[str, object]] = []
    for bucket in ("benchmark_20d_bucket", "rel_benchmark_20d_bucket", "sector_20d_bucket"):
        if bucket not in annotated.columns:
            continue
        grouped = annotated.groupby([bucket, "exit_reason"], dropna=False, sort=True).size()
        for (bucket_value, exit_reason), count in grouped.items():
            rows.append(
                {
                    "bucket": bucket,
                    "bucket_value": _bucket_text(bucket_value),
                    "exit_reason": _bucket_text(exit_reason),
                    "trade_count": int(count),
                }
            )
    return pd.DataFrame(rows)


def build_sector_proxy_trade_coverage(annotated: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "sector",
        "sector_proxy",
        "sector_proxy_is_fallback",
        "sector_proxy_unmapped",
    ]
    if not set(columns).issubset(annotated.columns):
        return pd.DataFrame(columns=[*columns, "trade_count"])
    grouped = annotated.groupby(columns, dropna=False, sort=True).size().reset_index(name="trade_count")
    return grouped


def build_missing_context_summary(annotated: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in ("missing_stock_context", "missing_benchmark_context", "missing_sector_context"):
        if column in annotated.columns:
            rows.append(
                {
                    "flag": column,
                    "missing_count": int(annotated[column].fillna(False).sum()),
                    "trade_count": int(len(annotated)),
                    "missing_rate": float(annotated[column].fillna(False).mean()) if len(annotated) else 0.0,
                }
            )
    return pd.DataFrame(rows)


def build_metric_by_context(annotated: pd.DataFrame, metric_column: str | None) -> pd.DataFrame:
    if not metric_column or metric_column not in annotated.columns:
        return _empty_metric_summary()
    frame = annotated.copy()
    frame[metric_column] = pd.to_numeric(frame[metric_column], errors="coerce")
    rows: list[dict[str, object]] = []
    for bucket in ("benchmark_20d_bucket", "rel_benchmark_20d_bucket", "sector_20d_bucket"):
        if bucket not in frame.columns:
            continue
        for value, group in frame.groupby(bucket, dropna=False, sort=True):
            valid = group[metric_column].dropna()
            rows.append(
                {
                    "metric": metric_column,
                    "bucket": bucket,
                    "bucket_value": _bucket_text(value),
                    "trade_count": int(len(group)),
                    "non_null_count": int(len(valid)),
                    "avg_value": float(valid.mean()) if len(valid) else np.nan,
                    "sum_value": float(valid.sum()) if len(valid) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def build_summary(
    annotated: pd.DataFrame,
    *,
    windows: tuple[int, ...],
    benchmark_index: str,
    strategy_name: str | None,
    pnl_column: str | None,
) -> dict[str, object]:
    net = pd.to_numeric(annotated[pnl_column], errors="coerce") if pnl_column else None
    r_multiple = (
        pd.to_numeric(annotated["r_multiple"], errors="coerce")
        if "r_multiple" in annotated.columns
        else None
    )
    return {
        "strategy_name": strategy_name,
        "benchmark_index": benchmark_index,
        "windows": list(windows),
        "trade_count": int(len(annotated)),
        "context_date_range": _date_range_summary(annotated.get("context_date")),
        "missing_context_counts": {
            "stock": _count_true(annotated, "missing_stock_context"),
            "benchmark": _count_true(annotated, "missing_benchmark_context"),
            "sector": _count_true(annotated, "missing_sector_context"),
        },
        "sector_proxy_trade_counts": {
            "mapped": int((~annotated.get("sector_proxy_unmapped", pd.Series(True, index=annotated.index)).fillna(True)).sum()),
            "unmapped": int(annotated.get("sector_proxy_unmapped", pd.Series(True, index=annotated.index)).fillna(True).sum()),
            "fallback": int(annotated.get("sector_proxy_is_fallback", pd.Series(False, index=annotated.index)).fillna(False).sum()),
        },
        "outcome_columns": {
            "pnl_column": pnl_column,
            "has_r_multiple": "r_multiple" in annotated.columns,
        },
        "overall_metrics": _overall_metrics(net, r_multiple),
        "cap_context_status": "inactive: market_cap_bucket is unknown/unmapped; no cap buckets derived",
    }


def write_audit_outputs(result: TradeContextAuditResult, output_dir: Path) -> dict[str, str]:
    """Write standard Phase 33F audit outputs."""

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "summary_json": output_dir / "summary.json",
        "trade_context_annotated_csv": output_dir / "trade_context_annotated.csv",
        "context_bucket_summary_csv": output_dir / "context_bucket_summary.csv",
        "exit_reason_by_context_csv": output_dir / "exit_reason_by_context.csv",
        "sector_proxy_trade_coverage_csv": output_dir / "sector_proxy_trade_coverage.csv",
        "missing_context_summary_csv": output_dir / "missing_context_summary.csv",
        "r_multiple_by_context_csv": output_dir / "r_multiple_by_context.csv",
        "pnl_by_context_csv": output_dir / "pnl_by_context.csv",
    }
    outputs["summary_json"].write_text(
        json.dumps(result.summary, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    result.annotated.to_csv(outputs["trade_context_annotated_csv"], index=False)
    result.context_bucket_summary.to_csv(outputs["context_bucket_summary_csv"], index=False)
    result.exit_reason_by_context.to_csv(outputs["exit_reason_by_context_csv"], index=False)
    result.sector_proxy_trade_coverage.to_csv(outputs["sector_proxy_trade_coverage_csv"], index=False)
    result.missing_context_summary.to_csv(outputs["missing_context_summary_csv"], index=False)
    result.r_multiple_by_context.to_csv(outputs["r_multiple_by_context_csv"], index=False)
    result.pnl_by_context.to_csv(outputs["pnl_by_context_csv"], index=False)
    return {key: str(path) for key, path in outputs.items()}


def _merge_context_asof(trades: pd.DataFrame, context_features: pd.DataFrame) -> pd.DataFrame:
    left = trades.sort_values(["symbol", "context_date", "_trade_row_id"], kind="mergesort")
    right = context_features.copy()
    right["session_date"] = _normalize_dates(right["session_date"])
    right = right.sort_values(["symbol", "session_date"], kind="mergesort")
    frames = []
    for symbol, symbol_trades in left.groupby("symbol", sort=False):
        symbol_features = right.loc[right["symbol"] == symbol]
        if symbol_features.empty:
            missing = symbol_trades.copy()
            missing["session_date"] = pd.NaT
            frames.append(missing)
            continue
        frames.append(
            pd.merge_asof(
                symbol_trades.sort_values("context_date", kind="mergesort"),
                symbol_features.sort_values("session_date", kind="mergesort"),
                left_on="context_date",
                right_on="session_date",
                by="symbol",
                direction="backward",
            )
        )
    return pd.concat(frames, ignore_index=True) if frames else left


def _ensure_annotation_columns(frame: pd.DataFrame, windows: tuple[int, ...]) -> pd.DataFrame:
    result = frame.copy()
    base_columns = [
        "sector",
        "sector_proxy",
        "sector_proxy_is_fallback",
        "sector_proxy_unmapped",
        "market_cap_bucket",
        "benchmark_above_sma_50d",
        "benchmark_above_sma_200d",
        "sector_above_sma_50d",
        "sector_above_sma_200d",
    ]
    for window in windows:
        base_columns.extend(
            [
                f"ret_{window}d",
                f"benchmark_ret_{window}d",
                f"rel_benchmark_ret_{window}d",
                f"sector_ret_{window}d",
                f"rel_sector_ret_{window}d",
            ]
        )
    for window in windows:
        column = f"ret_{window}d"
        candidates = [candidate for candidate in (f"{column}_x", f"{column}_y") if candidate in result.columns]
        if column not in result.columns:
            result[column] = np.nan
        for candidate in candidates:
            result[column] = result[column].combine_first(result[candidate])
    for column in base_columns:
        if column not in result.columns:
            result[column] = np.nan
    return result


def _attach_trend_aliases(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    aliases = {
        "benchmark_above_sma_50d": "benchmark_above_sma_50",
        "benchmark_above_sma_200d": "benchmark_above_sma_200",
        "sector_above_sma_50d": "sector_above_sma_50",
        "sector_above_sma_200d": "sector_above_sma_200",
    }
    for source, alias in aliases.items():
        if alias not in result.columns:
            result[alias] = result[source] if source in result.columns else np.nan
    return result

def _attach_missing_flags(frame: pd.DataFrame, windows: tuple[int, ...]) -> pd.DataFrame:
    result = frame.copy()
    preferred = 20 if 20 in windows else windows[0]
    result["missing_stock_context"] = result["session_date"].isna() | result[f"ret_{preferred}d"].isna()
    result["missing_benchmark_context"] = result["session_date"].isna() | result[
        f"benchmark_ret_{preferred}d"
    ].isna()
    result["missing_sector_context"] = (
        result["session_date"].isna()
        | result["sector_proxy"].isna()
        | result[f"sector_ret_{preferred}d"].isna()
    )
    return result


def _metric_row(bucket: str, value: object, group: pd.DataFrame) -> dict[str, object]:
    pnl_column = _first_existing_column(group, OUTCOME_COLUMNS)
    pnl = pd.to_numeric(group[pnl_column], errors="coerce") if pnl_column else None
    r_multiple = pd.to_numeric(group["r_multiple"], errors="coerce") if "r_multiple" in group.columns else None
    row = {
        "bucket": bucket,
        "bucket_value": _bucket_text(value),
        "trade_count": int(len(group)),
    }
    row.update(_overall_metrics(pnl, r_multiple))
    return row


def _overall_metrics(pnl: pd.Series | None, r_multiple: pd.Series | None) -> dict[str, object]:
    metrics: dict[str, object] = {}
    if pnl is not None:
        valid = pnl.dropna()
        wins = valid > 0
        gross_profit = valid.loc[valid > 0].sum()
        gross_loss = valid.loc[valid < 0].sum()
        metrics.update(
            {
                "win_rate": float(wins.mean()) if len(valid) else np.nan,
                "total_net_pnl": float(valid.sum()) if len(valid) else np.nan,
                "avg_net_pnl": float(valid.mean()) if len(valid) else np.nan,
                "profit_factor": float(gross_profit / abs(gross_loss)) if gross_loss < 0 else np.nan,
            }
        )
    if r_multiple is not None:
        valid_r = r_multiple.dropna()
        metrics["avg_r_multiple"] = float(valid_r.mean()) if len(valid_r) else np.nan
    return metrics


def _return_bucket(value: object) -> str:
    if pd.isna(value):
        return "missing"
    number = float(value)
    if number > 0.05:
        return "strong_positive"
    if number > 0:
        return "positive"
    return "negative"


def _relative_bucket(value: object) -> str:
    if pd.isna(value):
        return "missing"
    return "outperforming" if float(value) > 0 else "underperforming"


def _trend_bucket(value: object) -> str:
    if pd.isna(value):
        return "missing"
    return "above_sma50" if bool(value) else "below_sma50"


def _bucket_text(value: object) -> str:
    return "missing" if pd.isna(value) else str(value)


def _first_existing_column(frame: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    for column in candidates:
        if column in frame.columns:
            return column
    return None


def _empty_metric_summary() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["metric", "bucket", "bucket_value", "trade_count", "non_null_count", "avg_value", "sum_value"]
    )


def _date_range_summary(values: pd.Series | None) -> dict[str, object]:
    if values is None:
        return {"first": None, "last": None}
    dates = pd.to_datetime(values, errors="coerce").dropna()
    if dates.empty:
        return {"first": None, "last": None}
    return {"first": dates.min().date().isoformat(), "last": dates.max().date().isoformat()}


def _count_true(frame: pd.DataFrame, column: str) -> int:
    if column not in frame.columns:
        return 0
    return int(frame[column].fillna(False).sum())


def _normalize_dates(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, errors="raise", utc=True).dt.tz_convert(None).dt.normalize()


def _validate_windows(windows: Iterable[int]) -> tuple[int, ...]:
    values = tuple(int(window) for window in windows)
    if not values or any(window < 1 for window in values):
        raise ValueError("windows must be positive integers")
    return values


def _clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()