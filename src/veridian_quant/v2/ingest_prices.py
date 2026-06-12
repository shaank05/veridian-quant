"""Command line entry point for V2 price ingestion."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path

from veridian_quant.data.db_client import DatabaseClient
from veridian_quant.v2.data.ingestion_config import IngestionConfig
from veridian_quant.v2.data.price_ingestion import (
    PriceIngestionRunner,
    load_symbols_from_sources,
)
from veridian_quant.v2.data.upstox_history import UpstoxHistoryClient


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    _configure_logging(args.verbose)

    config = IngestionConfig.from_env()
    symbols = load_symbols_from_sources(args.symbols, args.symbol_file)
    if args.limit is not None:
        symbols = symbols[: args.limit]
    if not symbols:
        raise ValueError("provide at least one symbol via --symbols or --symbol-file")

    start_date = _parse_date(args.start_date) if args.start_date else None
    end_date = _parse_date(args.end_date) if args.end_date else datetime.now(timezone.utc).date()
    run_id = args.run_id or _derive_run_id(
        mode=args.mode,
        interval=args.interval,
        symbol_file=args.symbol_file,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
    )
    run_dir = args.run_dir or (config.run_dir / run_id)
    config = replace(
        config,
        network_retry=args.network_retry or config.network_retry,
        network_wait_seconds=(
            args.network_wait_seconds
            if args.network_wait_seconds is not None
            else config.network_wait_seconds
        ),
        network_max_wait_minutes=(
            args.network_max_wait_minutes
            if args.network_max_wait_minutes is not None
            else config.network_max_wait_minutes
        ),
        chunk_min_coverage_pct=(
            args.chunk_min_coverage_pct
            if args.chunk_min_coverage_pct is not None
            else config.chunk_min_coverage_pct
        ),
    )

    engine = DatabaseClient().get_engine()
    history_client = None
    if args.mode != "dry-run":
        config.require_access_token(args.mode)
        history_client = UpstoxHistoryClient(config)

    runner = PriceIngestionRunner(
        engine=engine,
        config=config,
        history_client=history_client,
    )
    summary = runner.run(
        symbols=symbols,
        mode=args.mode,
        interval=args.interval,
        start_date=start_date,
        end_date=end_date,
        exchange=args.exchange,
        run_id=run_id,
        run_dir=run_dir,
        resume=args.resume,
        skip_existing_chunks=args.skip_existing_chunks,
        network_retry=config.network_retry,
        network_wait_seconds=config.network_wait_seconds,
        network_max_wait_minutes=config.network_max_wait_minutes,
        chunk_min_coverage_pct=config.chunk_min_coverage_pct,
    )
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run V2 price ingestion")
    parser.add_argument("--symbols", help="Comma-separated symbols, e.g. RELIANCE,TCS")
    parser.add_argument("--symbol-file", type=Path, help="CSV/text file containing symbols")
    parser.add_argument("--interval", choices=("day", "1minute"), default="day")
    parser.add_argument(
        "--mode",
        choices=("backfill", "incremental", "dry-run"),
        default="dry-run",
    )
    parser.add_argument("--start-date", help="YYYY-MM-DD; required for backfill")
    parser.add_argument("--end-date", help="YYYY-MM-DD; defaults to today UTC")
    parser.add_argument("--exchange", choices=("NSE_EQ", "NSE_INDEX"), default="NSE_EQ")
    parser.add_argument("--limit", type=int, help="Cap symbols for test runs")
    parser.add_argument("--run-id", help="Stable id for this ingestion run")
    parser.add_argument(
        "--run-dir",
        type=Path,
        help="Directory for ingestion run outputs; defaults under V2_INGESTION_RUN_DIR",
    )
    parser.add_argument("--resume", action="store_true", help="Resume using chunk status CSV")
    skip_group = parser.add_mutually_exclusive_group()
    skip_group.add_argument(
        "--skip-existing-chunks",
        dest="skip_existing_chunks",
        action="store_true",
        default=True,
        help="Skip chunks already sufficiently present in prices_ohlc",
    )
    skip_group.add_argument(
        "--no-skip-existing-chunks",
        dest="skip_existing_chunks",
        action="store_false",
        help="Fetch all planned chunks without DB completeness pre-checks",
    )
    parser.add_argument(
        "--network-retry",
        choices=("fail-fast", "wait"),
        help="How to handle network-like request failures",
    )
    parser.add_argument("--network-wait-seconds", type=int, help="Seconds between network retries")
    parser.add_argument(
        "--network-max-wait-minutes",
        type=int,
        help="Maximum minutes to wait for network recovery; 0 waits indefinitely",
    )
    parser.add_argument(
        "--chunk-min-coverage-pct",
        type=float,
        help="Calendar-day coverage threshold for skipping existing chunks",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _derive_run_id(
    mode: str,
    interval: str,
    symbol_file: Path | None,
    symbols: list[str],
    start_date: date | None,
    end_date: date,
) -> str:
    symbol_part = symbol_file.stem if symbol_file else f"symbols_{len(symbols)}"
    digest = hashlib.sha1(",".join(symbols).encode("utf-8")).hexdigest()[:8]
    start_part = start_date.isoformat() if start_date else "none"
    raw = f"{mode}_{interval}_{symbol_part}_{start_part}_{end_date.isoformat()}_{digest}"
    return "".join(char.lower() if char.isalnum() else "_" for char in raw).strip("_")


if __name__ == "__main__":
    raise SystemExit(main())
