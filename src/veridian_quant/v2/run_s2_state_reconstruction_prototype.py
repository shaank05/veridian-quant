"""CLI for the Phase 36G read-only S2 state reconstruction prototype."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from veridian_quant.v2.analysis.s2_state_reconstruction import (
    DEFAULT_S2_REPORT_DIR,
    run_s2_state_reconstruction_prototype,
)


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_s2_state_reconstruction_prototype(
        report_dir=args.report_dir,
        ohlc_csv_dir=args.ohlc_csv_dir,
        output_dir=args.output_dir,
    )
    print(
        json.dumps(
            {
                "output_dir": str(result.output_dir),
                "outputs": {
                    name: str(path)
                    for name, path in sorted(result.outputs.items())
                },
                "caveat": result.metadata["caveat"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run read-only S2 daily state reconstruction prototype"
    )
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_S2_REPORT_DIR)
    parser.add_argument(
        "--ohlc-csv-dir",
        type=Path,
        required=True,
        help="Directory containing one normalized OHLC CSV per traded symbol.",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser.parse_args(list(argv) if argv is not None else None)


if __name__ == "__main__":
    raise SystemExit(main())
