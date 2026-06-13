"""Command line entry point for S1 baseline universe-size comparison reports."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from veridian_quant.v2.reporting.baseline_universe_comparison import (
    compare_baseline_universe_sizes,
)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    _configure_logging(args.verbose)

    result = compare_baseline_universe_sizes(
        research100_dir=args.research100_dir,
        research200_dir=args.research200_dir,
        output_dir=args.output_dir,
    )
    for name, path in result.paths.items():
        print(f"{name}: {path}")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare S1 baseline reports across 100 and 200 symbol universes"
    )
    parser.add_argument("--research100-dir", required=True, type=Path)
    parser.add_argument("--research200-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


if __name__ == "__main__":
    raise SystemExit(main())
