"""CLI for the Phase 35B read-only cross-strategy overlap audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from veridian_quant.v2.analysis.cross_strategy_overlap_audit import (
    run_cross_strategy_overlap_audit,
)


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_cross_strategy_overlap_audit(
        {
            "S1": args.s1_dir,
            "S2": args.s2_dir,
            "S3": args.s3_dir,
            "S4": args.s4_dir,
            "S5": args.s5_dir,
        },
        output_dir=args.output_dir,
        anchor_strategy=args.anchor_strategy,
        lookback_days=args.lookback_days,
        diagnostic_window_days=args.diagnostic_window_days,
        top_n=args.top_n,
        overlap_scope=args.overlap_scope,
    )
    print(
        json.dumps(
            {
                "output_dir": str(result.output_dir),
                "outputs": {name: str(path) for name, path in sorted(result.outputs.items())},
                "overlap_scope": result.metadata["overlap_scope"],
                "anchor_strategy": result.metadata["anchor_strategy"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run read-only cross-strategy overlap / ensemble feasibility audit"
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--s1-dir", type=Path, required=True)
    parser.add_argument("--s2-dir", type=Path, required=True)
    parser.add_argument("--s3-dir", type=Path, required=True)
    parser.add_argument("--s4-dir", type=Path, required=True)
    parser.add_argument("--s5-dir", type=Path, required=True)
    parser.add_argument("--anchor-strategy", default="S2")
    parser.add_argument("--lookback-days", type=int, default=3)
    parser.add_argument("--diagnostic-window-days", type=int, default=3)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument(
        "--overlap-scope",
        choices=("executed_trades", "signals", "counterfactual", "all"),
        default="all",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


if __name__ == "__main__":
    raise SystemExit(main())
