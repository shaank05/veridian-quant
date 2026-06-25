"""Read-only Research200 market context feature audit/export."""

from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

from veridian_quant.data.db_client import DatabaseClient
from veridian_quant.v2.data.loaders import SQLAlchemyDailyOHLCVLoader
from veridian_quant.v2.data.market_index_reader import SQLAlchemyMarketIndexDailyReader
from veridian_quant.v2.data.sector_proxy_mapping import (
    SectorProxyResolution,
    resolve_sector_proxy,
)
from veridian_quant.v2.features.market_context import (
    compute_cap_relative_context,
    compute_market_context_features,
)


DEFAULT_SYMBOLS_FILE = Path("config/universes/research/nse_eq_research_200_2018_2026.csv")
DEFAULT_CLASSIFICATION_FILE = Path(
    "config/universes/research/nse_eq_research_200_static_classification.csv"
)
DEFAULT_OUTPUT_DIR = Path("reports/phase_33e_market_context_audit")
DEFAULT_WINDOWS = (5, 20, 60, 120, 252)
SAMPLE_ROWS_PER_SYMBOL = 6


@dataclass(frozen=True, slots=True)
class AuditUniverseEntry:
    """Research universe entry needed by the audit runner."""

    symbol: str
    instrument_key: str | None


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv)
    engine = _get_database_engine()
    summary = run_audit(
        engine,
        symbols_file=args.symbols_file,
        classification_file=args.classification_file,
        start_date=_parse_date(args.start_date),
        end_date=_parse_date(args.end_date),
        benchmark_index=args.benchmark_index,
        windows=_parse_windows(args.windows),
        output_dir=args.output_dir,
        limit=args.limit,
        fallback_unmapped_sector_to_benchmark=args.fallback_unmapped_sector_to_benchmark,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _get_database_engine() -> object:
    """Return a SQLAlchemy engine, preferring explicit DB_* env settings."""

    load_dotenv()
    host = _clean(os.getenv("DB_HOST"))
    port = _clean(os.getenv("DB_PORT"))
    name = _clean(os.getenv("DB_NAME"))
    user = _clean(os.getenv("DB_USER"))
    password = os.getenv("DB_PASSWORD") or ""
    if host and port and name and user:
        url = (
            f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(password)}"
            f"@{host}:{port}/{name}"
        )
        return create_engine(url, pool_pre_ping=True)
    return DatabaseClient().get_engine()


def run_audit(
    engine: object,
    *,
    symbols_file: Path,
    classification_file: Path,
    start_date: date,
    end_date: date,
    benchmark_index: str,
    windows: tuple[int, ...],
    output_dir: Path,
    limit: int | None = None,
    fallback_unmapped_sector_to_benchmark: bool = False,
) -> dict[str, object]:
    """Run a read-only market context audit and write compact output files."""

    if start_date > end_date:
        raise ValueError("start-date must be on or before end-date")
    output_dir.mkdir(parents=True, exist_ok=True)

    universe = load_research_universe(symbols_file, limit=limit)
    classifications = load_classifications(classification_file)
    benchmark_symbol = benchmark_index.strip().upper()

    stock_loader = SQLAlchemyDailyOHLCVLoader(engine, lookback_buffer_days=max(windows) * 2)
    index_reader = SQLAlchemyMarketIndexDailyReader(engine)
    benchmark_result = index_reader.load(
        index_symbol=benchmark_symbol,
        start_date=start_date,
        end_date=end_date,
    )
    benchmark_frame = benchmark_result.frame

    sector_resolutions = {
        entry.symbol: resolve_sector_proxy(
            classifications.get(entry.symbol, {}).get("sector", "UNKNOWN"),
            fallback_to_nifty500=fallback_unmapped_sector_to_benchmark,
        )
        for entry in universe
    }
    needed_sector_indices = sorted(
        {
            resolution.sector_proxy
            for resolution in sector_resolutions.values()
            if resolution.sector_proxy is not None and resolution.sector_proxy != benchmark_symbol
        }
    )
    sector_index_frames: dict[str, pd.DataFrame] = {}
    index_load_errors: dict[str, str] = {}
    for index_symbol in needed_sector_indices:
        try:
            sector_index_frames[index_symbol] = index_reader.load(
                index_symbol=index_symbol,
                start_date=start_date,
                end_date=end_date,
            ).frame
        except Exception as error:  # pragma: no cover - defensive for live DB data gaps
            index_load_errors[index_symbol] = str(error)

    sample_frames: list[pd.DataFrame] = []
    feature_frames: list[pd.DataFrame] = []
    missing_rows: list[dict[str, object]] = []
    processed_symbols: list[str] = []

    for entry in universe:
        classification = classifications.get(entry.symbol, {})
        resolution = sector_resolutions[entry.symbol]
        try:
            stock_frame = _load_stock_frame(stock_loader, entry, start_date, end_date)
        except Exception as error:
            missing_rows.append(_missing_row(entry.symbol, "stock_ohlc_load_failed", str(error)))
            continue
        if stock_frame.empty:
            missing_rows.append(_missing_row(entry.symbol, "missing_stock_ohlc", "no stock rows"))
            continue

        sector_frame = _sector_frame_for_resolution(
            resolution,
            benchmark_symbol=benchmark_symbol,
            benchmark_frame=benchmark_frame,
            sector_index_frames=sector_index_frames,
        )
        if resolution.sector_proxy and sector_frame is None:
            missing_rows.append(
                _missing_row(
                    entry.symbol,
                    "missing_sector_index",
                    f"sector proxy {resolution.sector_proxy} not available",
                )
            )

        market_cap_bucket = classification.get("market_cap_bucket", "unknown")
        features = compute_market_context_features(
            stock_frame,
            benchmark_frame,
            sector_index_df=sector_frame,
            windows=windows,
            benchmark_name=benchmark_symbol,
            sector=classification.get("sector", "UNKNOWN"),
            sector_proxy=resolution.sector_proxy,
            fallback_sector_to_nifty500=fallback_unmapped_sector_to_benchmark,
            market_cap_bucket=market_cap_bucket,
        )
        if features.empty:
            missing_rows.append(_missing_row(entry.symbol, "missing_aligned_rows", "no overlap"))
            continue

        features.insert(0, "symbol", entry.symbol)
        feature_frames.append(features)
        sample_frames.append(_sample_market_context(features, windows))
        processed_symbols.append(entry.symbol)

    all_features = pd.concat(feature_frames, ignore_index=True) if feature_frames else pd.DataFrame()
    sample = pd.concat(sample_frames, ignore_index=True) if sample_frames else pd.DataFrame()
    sector_coverage = build_sector_proxy_coverage(
        classifications,
        sector_resolutions,
        available_indices={benchmark_symbol, *sector_index_frames.keys()},
    )
    feature_null_summary = build_feature_null_summary(all_features, windows)
    missing_summary = pd.DataFrame(missing_rows)

    _write_json(output_dir / "summary.json", {})
    sector_coverage.to_csv(output_dir / "sector_proxy_coverage.csv", index=False)
    sample.to_csv(output_dir / "market_context_sample.csv", index=False)
    sector_coverage.loc[
        sector_coverage["unmapped"] | sector_coverage["is_fallback"]
    ].to_csv(output_dir / "unmapped_or_fallback_sectors.csv", index=False)
    missing_summary.to_csv(output_dir / "missing_data_summary.csv", index=False)
    feature_null_summary.to_csv(output_dir / "feature_null_summary.csv", index=False)

    summary = {
        "symbols_requested": len(universe),
        "symbols_processed": len(processed_symbols),
        "symbols_skipped": len(universe) - len(processed_symbols),
        "benchmark_index": benchmark_symbol,
        "windows": list(windows),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "index_date_range": _date_range_summary(benchmark_frame),
        "stock_date_range_summary": _date_range_summary(all_features),
        "sector_proxy_coverage": {
            "sector_count": int(len(sector_coverage)),
            "mapped_sector_count": int((~sector_coverage["unmapped"]).sum())
            if not sector_coverage.empty
            else 0,
            "unmapped_sector_count": int(sector_coverage["unmapped"].sum())
            if not sector_coverage.empty
            else 0,
            "fallback_sector_count": int(sector_coverage["is_fallback"].sum())
            if not sector_coverage.empty
            else 0,
        },
        "unmapped_sectors": sector_coverage.loc[
            sector_coverage["unmapped"], "sector"
        ].tolist()
        if not sector_coverage.empty
        else [],
        "fallback_count": int(
            sum(resolution.sector_proxy_is_fallback for resolution in sector_resolutions.values())
        ),
        "missing_index_data_count": len(index_load_errors),
        "missing_stock_ohlc_count": sum(
            1 for row in missing_rows if row["reason"] in {"missing_stock_ohlc", "stock_ohlc_load_failed"}
        ),
        "feature_null_rates": _summary_null_rates(feature_null_summary),
        "sample_row_count_exported": int(len(sample)),
        "cap_context_status": "inactive: market_cap_bucket is unknown/unmapped; no cap buckets derived",
        "outputs": {
            "summary_json": str(output_dir / "summary.json"),
            "sector_proxy_coverage_csv": str(output_dir / "sector_proxy_coverage.csv"),
            "market_context_sample_csv": str(output_dir / "market_context_sample.csv"),
            "unmapped_or_fallback_sectors_csv": str(output_dir / "unmapped_or_fallback_sectors.csv"),
            "missing_data_summary_csv": str(output_dir / "missing_data_summary.csv"),
            "feature_null_summary_csv": str(output_dir / "feature_null_summary.csv"),
        },
        "index_load_errors": index_load_errors,
    }
    _write_json(output_dir / "summary.json", summary)
    return summary


def load_research_universe(path: Path, *, limit: int | None = None) -> list[AuditUniverseEntry]:
    rows = _read_csv(path)
    entries: list[AuditUniverseEntry] = []
    for row in rows:
        symbol = _clean(row.get("symbol") or row.get("trading_symbol")).upper()
        if not symbol:
            continue
        entries.append(
            AuditUniverseEntry(
                symbol=symbol,
                instrument_key=_optional(row.get("instrument_key")),
            )
        )
    return entries[:limit] if limit is not None else entries


def load_classifications(path: Path) -> dict[str, dict[str, str]]:
    return {
        _clean(row.get("symbol")).upper(): row
        for row in _read_csv(path)
        if _clean(row.get("symbol"))
    }


def build_sector_proxy_coverage(
    classifications: dict[str, dict[str, str]],
    selected_resolutions: dict[str, SectorProxyResolution],
    *,
    available_indices: set[str],
) -> pd.DataFrame:
    symbols_by_sector: dict[str, list[str]] = {}
    for symbol, row in classifications.items():
        sector = _clean(row.get("sector")) or "UNKNOWN"
        symbols_by_sector.setdefault(sector, []).append(symbol)

    rows: list[dict[str, object]] = []
    for sector, symbols in sorted(symbols_by_sector.items()):
        resolution = next(
            (
                selected_resolutions[symbol]
                for symbol in symbols
                if symbol in selected_resolutions
            ),
            resolve_sector_proxy(sector),
        )
        rows.append(
            {
                "sector": sector,
                "count_symbols": len(symbols),
                "resolved_proxy": resolution.sector_proxy,
                "proxy_index": resolution.sector_proxy,
                "proxy_available": bool(
                    resolution.sector_proxy and resolution.sector_proxy in available_indices
                ),
                "is_fallback": resolution.sector_proxy_is_fallback,
                "unmapped": resolution.sector_proxy_unmapped,
                "symbols_sample": "|".join(symbols[:10]),
            }
        )
    return pd.DataFrame(rows)


def build_feature_null_summary(features: pd.DataFrame, windows: tuple[int, ...]) -> pd.DataFrame:
    if features.empty:
        return pd.DataFrame(columns=["feature", "null_count", "row_count", "null_rate"])
    columns: list[str] = []
    for window in windows:
        columns.extend(
            [
                f"ret_{window}d",
                f"benchmark_ret_{window}d",
                f"rel_benchmark_ret_{window}d",
                f"stock_return_ratio_vs_benchmark_{window}d",
                f"sector_ret_{window}d",
                f"rel_sector_ret_{window}d",
                f"cap_ret_{window}d",
                f"rel_cap_ret_{window}d",
            ]
        )
    columns = [column for column in columns if column in features.columns]
    rows = []
    row_count = len(features)
    for column in columns:
        null_count = int(features[column].isna().sum())
        rows.append(
            {
                "feature": column,
                "null_count": null_count,
                "row_count": row_count,
                "null_rate": null_count / row_count if row_count else None,
            }
        )
    return pd.DataFrame(rows)


def _sample_market_context(features: pd.DataFrame, windows: tuple[int, ...]) -> pd.DataFrame:
    sample = pd.concat(
        [features.head(SAMPLE_ROWS_PER_SYMBOL // 2), features.tail(SAMPLE_ROWS_PER_SYMBOL // 2)],
        ignore_index=True,
    ).drop_duplicates(subset=["symbol", "session_date"], keep="first")
    preferred_window = 20 if 20 in windows else windows[0]
    columns = [
        "symbol",
        "session_date",
        "sector",
        "sector_proxy",
        "sector_proxy_is_fallback",
        "sector_proxy_unmapped",
        "stock_close",
        f"ret_{preferred_window}d",
        f"benchmark_ret_{preferred_window}d",
        f"rel_benchmark_ret_{preferred_window}d",
        f"sector_ret_{preferred_window}d",
        f"rel_sector_ret_{preferred_window}d",
        "benchmark_above_sma_50d",
        "sector_above_sma_50d",
    ]
    existing = [column for column in columns if column in sample.columns]
    return sample.loc[:, existing].rename(columns={"stock_close": "close"})


def _load_stock_frame(
    loader: SQLAlchemyDailyOHLCVLoader,
    entry: AuditUniverseEntry,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    if entry.instrument_key:
        return loader.load_instrument_key(entry.instrument_key, start_date, end_date)
    return loader.load_symbol(entry.symbol, start_date, end_date)


def _sector_frame_for_resolution(
    resolution: SectorProxyResolution,
    *,
    benchmark_symbol: str,
    benchmark_frame: pd.DataFrame,
    sector_index_frames: dict[str, pd.DataFrame],
) -> pd.DataFrame | None:
    if resolution.sector_proxy is None:
        return None
    if resolution.sector_proxy == benchmark_symbol:
        return benchmark_frame
    return sector_index_frames.get(resolution.sector_proxy)


def _date_range_summary(frame: pd.DataFrame) -> dict[str, object]:
    if frame.empty or "session_date" not in frame.columns:
        return {"first": None, "last": None, "rows": 0}
    dates = pd.to_datetime(frame["session_date"])
    return {
        "first": dates.min().date().isoformat(),
        "last": dates.max().date().isoformat(),
        "rows": int(len(frame)),
    }


def _summary_null_rates(feature_null_summary: pd.DataFrame) -> dict[str, float]:
    if feature_null_summary.empty:
        return {}
    rows = feature_null_summary.sort_values(["null_rate", "feature"], ascending=[False, True])
    return {
        str(row["feature"]): round(float(row["null_rate"]), 6)
        for _, row in rows.head(10).iterrows()
    }


def _missing_row(symbol: str, reason: str, detail: str) -> dict[str, object]:
    return {"symbol": symbol, "reason": reason, "detail": detail}


def _parse_args(argv: Iterable[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run read-only Research200 market context audit")
    parser.add_argument("--symbols-file", type=Path, default=DEFAULT_SYMBOLS_FILE)
    parser.add_argument("--classification-file", type=Path, default=DEFAULT_CLASSIFICATION_FILE)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--benchmark-index", default="NIFTY_500")
    parser.add_argument("--windows", default=",".join(str(window) for window in DEFAULT_WINDOWS))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--fallback-unmapped-sector-to-benchmark", action="store_true")
    return parser.parse_args(list(argv) if argv is not None else None)


def _parse_windows(value: str) -> tuple[int, ...]:
    try:
        windows = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    except ValueError as error:
        raise ValueError("windows must be comma-separated positive integers") from error
    if not windows or any(window < 1 for window in windows):
        raise ValueError("windows must be comma-separated positive integers")
    return windows


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, payload: dict[str, object]) -> None:
    with Path(path).open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")


def _optional(value: object) -> str | None:
    text = _clean(value)
    return text or None


def _clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


if __name__ == "__main__":
    raise SystemExit(main())
