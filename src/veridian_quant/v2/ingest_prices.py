"""Command line entry point for V2 price ingestion."""

from __future__ import annotations

import argparse
import json
import logging
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
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


if __name__ == "__main__":
    raise SystemExit(main())
