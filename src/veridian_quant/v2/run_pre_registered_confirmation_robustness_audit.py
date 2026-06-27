"""CLI for Phase 35C pre-registered S2 confirmation robustness audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from veridian_quant.v2.analysis.pre_registered_confirmation_robustness_audit import (
    DEFAULT_LOOKBACK_SESSIONS,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_STRATEGY_DIRS,
    run_pre_registered_confirmation_robustness_audit,
)


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_pre_registered_confirmation_robustness_audit(
        {
            "S1": args.s1_dir,
            "S2": args.s2_dir,
            "S3": args.s3_dir,
            "S4": args.s4_dir,
            "S5": args.s5_dir,
        },
        output_dir=args.output_dir,
        lookback_sessions=_parse_lookbacks(args.lookback_sessions),
        future_diagnostic_sessions=args.future_diagnostic_sessions,
    )
    print(
        json.dumps(
            {
                "phase": result.metadata["phase"],
                "output_dir": str(result.output_dir),
                "lookback_sessions": result.metadata["lookback_sessions"],
                "outputs": {name: str(path) for name, path in sorted(result.outputs.items())},
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Phase 35C read-only pre-registered S2 confirmation robustness audit"
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--s1-dir", type=Path, default=DEFAULT_STRATEGY_DIRS["S1"])
    parser.add_argument("--s2-dir", type=Path, default=DEFAULT_STRATEGY_DIRS["S2"])
    parser.add_argument("--s3-dir", type=Path, default=DEFAULT_STRATEGY_DIRS["S3"])
    parser.add_argument("--s4-dir", type=Path, default=DEFAULT_STRATEGY_DIRS["S4"])
    parser.add_argument("--s5-dir", type=Path, default=DEFAULT_STRATEGY_DIRS["S5"])
    parser.add_argument(
        "--lookback-sessions",
        default=",".join(str(value) for value in DEFAULT_LOOKBACK_SESSIONS),
        help="Comma-separated trading-session lookbacks, default: 0,1,3,5",
    )
    parser.add_argument("--future-diagnostic-sessions", type=int, default=3)
    return parser.parse_args(list(argv) if argv is not None else None)


def _parse_lookbacks(value: str) -> tuple[int, ...]:
    try:
        lookbacks = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    except ValueError as error:
        raise ValueError("lookback sessions must be comma-separated non-negative integers") from error
    if not lookbacks or any(item < 0 for item in lookbacks):
        raise ValueError("lookback sessions must be comma-separated non-negative integers")
    return lookbacks


if __name__ == "__main__":
    raise SystemExit(main())
