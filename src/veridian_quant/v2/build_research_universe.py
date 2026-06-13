"""Command line entry point for V2 audited research universe files."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from veridian_quant.v2.data.research_universe import build_research_universes


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    _configure_logging(args.verbose)

    result = build_research_universes(
        coverage_file=args.coverage_file,
        bad_ohlc_file=args.bad_ohlc_file,
        output_dir=args.output_dir,
        start_date=args.start_date,
        end_date=args.end_date,
        seed=args.seed,
        sizes=_parse_sizes(args.sizes),
    )
    for name, path in result.paths.items():
        print(f"{name}: {path}")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build V2 research universes from audited coverage CSVs"
    )
    parser.add_argument("--coverage-file", required=True, type=Path)
    parser.add_argument("--bad-ohlc-file", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD audit start date")
    parser.add_argument("--end-date", required=True, help="YYYY-MM-DD audit end date")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sizes", default="100,200")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def _parse_sizes(value: str) -> tuple[int, ...]:
    sizes = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    if not sizes:
        raise ValueError("at least one size is required")
    return sizes


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


if __name__ == "__main__":
    raise SystemExit(main())
