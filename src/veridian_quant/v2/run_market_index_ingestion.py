"""Command line entry point for V2 market index ingestion."""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import replace
from datetime import date

from veridian_quant.data.db_client import DatabaseClient
from veridian_quant.v2.data.ingestion_config import IngestionConfig
from veridian_quant.v2.data.market_index_ingestion import MarketIndexIngestionRunner
from veridian_quant.v2.data.market_index_reader import audit_market_index_daily_bars
from veridian_quant.v2.data.market_index_registry import parse_index_symbols
from veridian_quant.v2.data.upstox_history import UpstoxHistoryClient


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    _configure_logging(args.verbose)

    config = IngestionConfig.from_env()
    config = replace(
        config,
        throttle_seconds=args.throttle_seconds
        if args.throttle_seconds is not None
        else config.throttle_seconds,
    )
    indices = parse_index_symbols(args.indices)
    start_date = _parse_date(args.start_date)
    end_date = _parse_date(args.end_date)

    engine = DatabaseClient().get_engine()
    if args.audit_db:
        report = audit_market_index_daily_bars(
            engine,
            index_symbols=indices,
            start_date=start_date,
            end_date=end_date,
            interval=args.interval,
        )
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return 0

    history_client = None
    if not args.dry_run:
        config.require_access_token("backfill")
        history_client = UpstoxHistoryClient(config)

    runner = MarketIndexIngestionRunner(
        engine=engine,
        config=config,
        history_client=history_client,
    )
    summary = runner.run(
        indices,
        start_date=start_date,
        end_date=end_date,
        interval=args.interval,
        dry_run=args.dry_run,
    )
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run V2 market index OHLC ingestion")
    parser.add_argument(
        "--indices",
        required=True,
        help="ALL or comma-separated internal index symbols, e.g. NIFTY_50,NIFTY_BANK",
    )
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--interval", choices=("day",), default="day")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--audit-db",
        action="store_true",
        help="Read-only canonicalization audit; does not fetch or write OHLC data",
    )
    parser.add_argument("--throttle-seconds", type=float)
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
