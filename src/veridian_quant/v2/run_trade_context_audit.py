"""CLI for read-only Phase 33F trade context audits."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

from veridian_quant.data.db_client import DatabaseClient
from veridian_quant.v2.analysis.trade_context_audit import (
    DEFAULT_WINDOWS,
    REQUIRED_TREND_WINDOWS,
    resolve_trade_columns,
    run_trade_context_audit,
    write_audit_outputs,
)
from veridian_quant.v2.data.loaders import SQLAlchemyDailyOHLCVLoader
from veridian_quant.v2.data.market_index_reader import SQLAlchemyMarketIndexDailyReader
from veridian_quant.v2.data.sector_proxy_mapping import resolve_sector_proxy
from veridian_quant.v2.run_market_context_audit import load_classifications, load_research_universe


DEFAULT_SYMBOLS_FILE = Path("config/universes/research/nse_eq_research_200_2018_2026.csv")
DEFAULT_CLASSIFICATION_FILE = Path(
    "config/universes/research/nse_eq_research_200_static_classification.csv"
)
DEFAULT_OUTPUT_DIR = Path("reports/phase_33f_trade_context_audit")


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv)
    windows = _parse_windows(args.windows)
    trades = load_trade_log(args.trade_log, limit=args.limit)
    column_resolution = resolve_trade_columns(
        trades,
        context_date_column=args.context_date_column,
    )
    date_range = _trade_context_date_range(trades, column_resolution.context_date_column)
    engine = _get_database_engine()
    summary = run_audit(
        engine,
        trades=trades,
        symbols_file=args.symbols_file,
        classification_file=args.classification_file,
        benchmark_index=args.benchmark_index,
        windows=windows,
        output_dir=args.output_dir,
        context_date_column=args.context_date_column,
        strategy_name=args.strategy_name,
        fallback_unmapped_sector_to_benchmark=args.fallback_unmapped_sector_to_benchmark,
        start_date=date_range[0],
        end_date=date_range[1],
    )
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


def run_audit(
    engine: object,
    *,
    trades: pd.DataFrame,
    symbols_file: Path,
    classification_file: Path,
    benchmark_index: str,
    windows: tuple[int, ...],
    output_dir: Path,
    context_date_column: str = "auto",
    strategy_name: str | None = None,
    fallback_unmapped_sector_to_benchmark: bool = False,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, object]:
    """Run the read-only trade context audit and write outputs."""

    column_resolution = resolve_trade_columns(trades, context_date_column=context_date_column)
    if start_date is None or end_date is None:
        start_date, end_date = _trade_context_date_range(trades, column_resolution.context_date_column)
    buffer_days = max((*windows, *REQUIRED_TREND_WINDOWS)) * 3
    load_start = start_date - timedelta(days=buffer_days)
    load_end = end_date

    universe_by_symbol = {entry.symbol: entry for entry in load_research_universe(symbols_file)}
    classifications = load_classifications(classification_file)
    symbols = sorted(trades[column_resolution.symbol_column].astype(str).str.strip().str.upper().unique())

    stock_loader = SQLAlchemyDailyOHLCVLoader(engine, lookback_buffer_days=buffer_days)
    index_reader = SQLAlchemyMarketIndexDailyReader(engine)
    benchmark_symbol = benchmark_index.strip().upper()
    benchmark_frame = index_reader.load(
        index_symbol=benchmark_symbol,
        start_date=load_start,
        end_date=load_end,
    ).frame

    stock_frames: dict[str, pd.DataFrame] = {}
    missing_stock_symbols: list[str] = []
    for symbol in symbols:
        entry = universe_by_symbol.get(symbol)
        try:
            if entry and entry.instrument_key:
                frame = stock_loader.load_instrument_key(entry.instrument_key, load_start, load_end)
            else:
                frame = stock_loader.load_symbol(symbol, load_start, load_end)
        except Exception:
            missing_stock_symbols.append(symbol)
            continue
        if frame.empty:
            missing_stock_symbols.append(symbol)
        else:
            stock_frames[symbol] = frame

    sector_indices = _needed_sector_indices(
        symbols,
        classifications,
        benchmark_symbol=benchmark_symbol,
        fallback_unmapped_sector_to_benchmark=fallback_unmapped_sector_to_benchmark,
    )
    sector_index_frames: dict[str, pd.DataFrame] = {}
    index_load_errors: dict[str, str] = {}
    for index_symbol in sorted(sector_indices):
        try:
            sector_index_frames[index_symbol] = index_reader.load(
                index_symbol=index_symbol,
                start_date=load_start,
                end_date=load_end,
            ).frame
        except Exception as error:  # pragma: no cover - live DB defensive path
            index_load_errors[index_symbol] = str(error)

    result = run_trade_context_audit(
        trades,
        stock_frames=stock_frames,
        benchmark_frame=benchmark_frame,
        sector_index_frames=sector_index_frames,
        classifications=classifications,
        windows=windows,
        benchmark_index=benchmark_symbol,
        context_date_column=context_date_column,
        strategy_name=strategy_name,
        fallback_unmapped_sector_to_benchmark=fallback_unmapped_sector_to_benchmark,
    )
    outputs = write_audit_outputs(result, output_dir)
    summary = {
        **result.summary,
        "trade_log_rows_read": int(len(trades)),
        "symbols_requested": int(len(symbols)),
        "symbols_with_stock_context": int(len(stock_frames)),
        "missing_stock_symbols": missing_stock_symbols,
        "index_load_errors": index_load_errors,
        "audit_date_range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "load_date_range": {"start": load_start.isoformat(), "end": load_end.isoformat()},
        "outputs": outputs,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return summary


def load_trade_log(path: Path, *, limit: int | None = None) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be positive")
        frame = frame.head(limit).copy()
    return frame


def _needed_sector_indices(
    symbols: Iterable[str],
    classifications: dict[str, dict[str, str]],
    *,
    benchmark_symbol: str,
    fallback_unmapped_sector_to_benchmark: bool,
) -> set[str]:
    indices: set[str] = set()
    for symbol in symbols:
        sector = classifications.get(symbol, {}).get("sector", "UNKNOWN")
        resolution = resolve_sector_proxy(
            sector,
            fallback_to_nifty500=fallback_unmapped_sector_to_benchmark,
        )
        if resolution.sector_proxy and resolution.sector_proxy != benchmark_symbol:
            indices.add(resolution.sector_proxy)
    return indices


def _trade_context_date_range(trades: pd.DataFrame, context_date_column: str) -> tuple[date, date]:
    dates = pd.to_datetime(trades[context_date_column], errors="raise").dt.date
    return dates.min(), dates.max()


def _get_database_engine() -> object:
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


def _parse_args(argv: Iterable[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run read-only trade context audit")
    parser.add_argument("--trade-log", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--symbols-file", type=Path, default=DEFAULT_SYMBOLS_FILE)
    parser.add_argument("--classification-file", type=Path, default=DEFAULT_CLASSIFICATION_FILE)
    parser.add_argument("--benchmark-index", default="NIFTY_500")
    parser.add_argument("--windows", default=",".join(str(window) for window in DEFAULT_WINDOWS))
    parser.add_argument("--context-date-column", default="auto")
    parser.add_argument("--strategy-name")
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


def _clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


if __name__ == "__main__":
    raise SystemExit(main())