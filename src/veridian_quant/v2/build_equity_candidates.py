"""Command line entry point for raw V2 NSE equity candidate lists."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from veridian_quant.data.db_client import DatabaseClient
from veridian_quant.v2.data.equity_candidates import build_raw_nse_equity_candidates


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    _configure_logging(args.verbose)

    engine = DatabaseClient().get_engine()
    paths = build_raw_nse_equity_candidates(
        engine=engine,
        output_dir=args.output_dir,
        exchange=args.exchange,
        include_etfs=args.include_etfs,
        limit=args.limit,
    )
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build raw V2 NSE equity candidates")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--exchange", choices=("NSE_EQ",), default="NSE_EQ")
    parser.add_argument("--include-etfs", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


if __name__ == "__main__":
    raise SystemExit(main())
