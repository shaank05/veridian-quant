"""CLI for the Phase 36B read-only cross-strategy risk diagnostic audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from veridian_quant.v2.analysis.cross_strategy_risk_diagnostic_audit import (
    DEFAULT_CLASSIFICATION_CSV,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_STRATEGY_DIRS,
    DEFAULT_UNIVERSE_CSV,
    run_cross_strategy_risk_diagnostic_audit,
)


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_cross_strategy_risk_diagnostic_audit(
        {
            "S1": args.s1_dir,
            "S2": args.s2_dir,
            "S3": args.s3_dir,
            "S4": args.s4_dir,
            "S5": args.s5_dir,
        },
        universe_csv=args.universe_csv,
        classification_csv=args.classification_csv,
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
        description="Run read-only cross-strategy risk input diagnostic audit"
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--s1-dir", type=Path, default=DEFAULT_STRATEGY_DIRS["S1"])
    parser.add_argument("--s2-dir", type=Path, default=DEFAULT_STRATEGY_DIRS["S2"])
    parser.add_argument("--s3-dir", type=Path, default=DEFAULT_STRATEGY_DIRS["S3"])
    parser.add_argument("--s4-dir", type=Path, default=DEFAULT_STRATEGY_DIRS["S4"])
    parser.add_argument("--s5-dir", type=Path, default=DEFAULT_STRATEGY_DIRS["S5"])
    parser.add_argument("--universe-csv", type=Path, default=DEFAULT_UNIVERSE_CSV)
    parser.add_argument(
        "--classification-csv",
        type=Path,
        default=DEFAULT_CLASSIFICATION_CSV,
    )
    return parser.parse_args(list(argv) if argv is not None else None)


if __name__ == "__main__":
    raise SystemExit(main())
