"""CLI for standalone post-backtest Monte Carlo robustness validation."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

import pandas as pd

from veridian_quant.v2.validation.monte_carlo import (
    DEFAULT_DRAWDOWN_THRESHOLDS,
    run_monte_carlo_validation,
    simulation_results_frame,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--trade-pnl-log", required=True, type=Path)
    parser.add_argument("--starting-equity", required=True, type=float)
    parser.add_argument("--num-simulations", type=int, default=10_000)
    parser.add_argument("--mode", choices=("shuffle", "bootstrap"), default="shuffle")
    parser.add_argument("--random-seed", type=int, default=None)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--drawdown-thresholds",
        default=",".join(str(value) for value in DEFAULT_DRAWDOWN_THRESHOLDS),
        help="Comma-separated fractions, for example 0.10,0.20,0.30,0.40",
    )
    parser.add_argument("--num-trades", type=int, default=None)
    return parser


def run(args: Namespace) -> tuple[Path, Path]:
    trade_log = pd.read_csv(args.trade_pnl_log)
    result = run_monte_carlo_validation(
        trade_log,
        starting_equity=args.starting_equity,
        num_simulations=args.num_simulations,
        random_seed=args.random_seed,
        mode=args.mode,
        drawdown_thresholds=_parse_drawdown_thresholds(args.drawdown_thresholds),
        num_trades=args.num_trades,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / "monte_carlo_summary.csv"
    simulations_path = args.output_dir / "monte_carlo_simulations.csv"
    summary_record = result.summary.to_record()
    summary_record.update(
        {
            "pnl_column": result.pnl_column,
            "dropped_nan_count": result.dropped_nan_count,
            "random_seed": result.random_seed,
        }
    )
    pd.DataFrame([summary_record]).to_csv(summary_path, index=False)
    simulation_results_frame(result.simulations).to_csv(simulations_path, index=False)
    return summary_path, simulations_path


def main(argv: list[str] | None = None) -> int:
    run(build_parser().parse_args(argv))
    return 0


def _parse_drawdown_thresholds(value: str) -> tuple[float, ...]:
    try:
        return tuple(float(part.strip()) for part in value.split(",") if part.strip())
    except ValueError as exc:
        raise ValueError("drawdown thresholds must be comma-separated numbers") from exc


if __name__ == "__main__":
    raise SystemExit(main())
