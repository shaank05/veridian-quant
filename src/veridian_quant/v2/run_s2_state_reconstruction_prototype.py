"""CLI for the Phase 36G read-only S2 state reconstruction prototype."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from veridian_quant.data.db_client import DatabaseClient
from veridian_quant.v2.analysis.s2_state_reconstruction import (
    DEFAULT_OHLC_LOOKBACK_BUFFER_DAYS,
    DEFAULT_S2_REPORT_DIR,
    run_s2_state_reconstruction_prototype,
)
from veridian_quant.v2.data.loaders import SQLAlchemyDailyOHLCVLoader


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv)
    ohlc_loader = _build_ohlc_loader(args.ohlc_source, args.lookback_buffer_days)
    result = run_s2_state_reconstruction_prototype(
        report_dir=args.report_dir,
        ohlc_csv_dir=args.ohlc_csv_dir,
        output_dir=args.output_dir,
        ohlc_source=args.ohlc_source,
        ohlc_loader=ohlc_loader,
        lookback_buffer_days=args.lookback_buffer_days,
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
        help="Directory containing one normalized OHLC CSV per traded symbol.",
    )
    parser.add_argument(
        "--ohlc-source",
        choices=["csv", "db"],
        default="csv",
        help="Read OHLC from per-symbol CSV files or the existing database loader.",
    )
    parser.add_argument(
        "--lookback-buffer-days",
        type=int,
        default=DEFAULT_OHLC_LOOKBACK_BUFFER_DAYS,
        help="Pre-start OHLC history buffer used for state reconstruction.",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.ohlc_source == "csv" and args.ohlc_csv_dir is None:
        parser.error("--ohlc-csv-dir is required when --ohlc-source csv")
    if args.lookback_buffer_days < 0:
        parser.error("--lookback-buffer-days must be non-negative")
    return args


def _build_ohlc_loader(
    ohlc_source: str,
    lookback_buffer_days: int,
) -> SQLAlchemyDailyOHLCVLoader | None:
    if ohlc_source != "db":
        return None
    engine = DatabaseClient().get_engine()
    if engine is None:
        raise RuntimeError("DatabaseClient().get_engine() returned None")
    return SQLAlchemyDailyOHLCVLoader(
        engine=engine,
        lookback_buffer_days=lookback_buffer_days,
    )


if __name__ == "__main__":
    raise SystemExit(main())
