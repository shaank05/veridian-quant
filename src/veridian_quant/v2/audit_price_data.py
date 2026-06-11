"""Command line entry point for V2 price data quality audits."""

from __future__ import annotations

import argparse
import logging
from datetime import date
from pathlib import Path

from veridian_quant.data.db_client import DatabaseClient
from veridian_quant.v2.data.price_quality import audit_price_data


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    _configure_logging(args.verbose)

    engine = DatabaseClient().get_engine()
    paths = audit_price_data(
        engine=engine,
        exchange=args.exchange,
        interval=args.interval,
        start_date=_parse_date(args.start_date),
        end_date=_parse_date(args.end_date),
        output_dir=args.output_dir,
        min_history_days=args.min_history_days,
        max_missing_day_pct=args.max_missing_day_pct,
        max_zero_volume_pct=args.max_zero_volume_pct,
        min_avg_volume_60d=args.min_avg_volume_60d,
        min_avg_turnover_60d=args.min_avg_turnover_60d,
        recent_days=args.recent_days,
        limit=args.limit,
    )
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit V2 price data quality")
    parser.add_argument("--exchange", choices=("NSE_EQ", "NSE_INDEX"), default="NSE_EQ")
    parser.add_argument("--interval", choices=("day", "1minute"), default="day")
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD audit start date")
    parser.add_argument("--end-date", required=True, help="YYYY-MM-DD audit end date")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--min-history-days", type=int, default=1000)
    parser.add_argument("--max-missing-day-pct", type=float, default=10.0)
    parser.add_argument("--max-zero-volume-pct", type=float, default=5.0)
    parser.add_argument("--min-avg-volume-60d", type=float, default=0)
    parser.add_argument("--min-avg-turnover-60d", type=float, default=0)
    parser.add_argument("--recent-days", type=int, default=60)
    parser.add_argument("--limit", type=int)
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
