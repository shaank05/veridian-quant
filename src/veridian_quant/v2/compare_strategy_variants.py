"""CLI for comparing completed v2 strategy variant report folders."""

from __future__ import annotations

import argparse
from pathlib import Path

from veridian_quant.v2.reporting.variant_comparison import (
    compare_strategy_variant_reports,
)


def main() -> None:
    """Parse arguments and write variant comparison CSVs."""

    parser = argparse.ArgumentParser(
        description="Compare completed v2 strategy variant report folders.",
    )
    parser.add_argument(
        "--report-dir",
        action="append",
        required=True,
        help="Completed report folder. Can be repeated.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where comparison CSVs will be written.",
    )
    parser.add_argument(
        "--variant-label",
        action="append",
        help="Optional label for a report folder. Repeat in report-dir order.",
    )
    args = parser.parse_args()

    outputs = compare_strategy_variant_reports(
        [Path(report_dir) for report_dir in args.report_dir],
        Path(args.output_dir),
        variant_labels=args.variant_label,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
