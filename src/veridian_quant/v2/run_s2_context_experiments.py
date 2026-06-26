"""CLI for the fixed Phase 33G.1 S2 context experiment batch."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Iterable

from veridian_quant.v2.backtesting.markov_portfolio_runner import (
    run_s2_markov_portfolio_backtest,
)
from veridian_quant.v2.backtesting.s2_candidate_ranking import (
    S2_CANDIDATE_RANKING_NONE,
)
from veridian_quant.v2.data.loaders import SQLAlchemyDailyOHLCVLoader
from veridian_quant.v2.data.market_index_reader import SQLAlchemyMarketIndexDailyReader
from veridian_quant.v2.experiments.s2_context_experiments import (
    ALL_PREDECLARED,
    ALL_PREDECLARED_VARIANTS,
    build_s2_context_signal_filter,
    needed_sector_indices_for_symbols,
    validate_s2_context_experiment_variant,
    variant_metadata,
)
from veridian_quant.v2.reporting.exporters import export_portfolio_backtest_csvs
from veridian_quant.v2.reporting.progress import ProgressReporter


DEFAULT_SYMBOLS_FILE = Path("config/universes/research/nse_eq_research_200_2018_2026.csv")
DEFAULT_CLASSIFICATION_FILE = Path(
    "config/universes/research/nse_eq_research_200_static_classification.csv"
)
DEFAULT_OUTPUT_DIR = Path("reports/v2/s2_context_experiments")
NIFTY_50_INSTRUMENT_KEY = "NSE_INDEX|Nifty 50"
CONTEXT_LOOKBACK_BUFFER_DAYS = 365
BASELINE_MARKOV_SIGNAL_FILTER = "exclude_ret_down"


def main(argv: Iterable[str] | None = None) -> int:
    """Run one pre-declared S2 context experiment variant."""

    total_started = perf_counter()
    args = _parse_args(argv)
    reporter = ProgressReporter(args.verbosity)
    variants = (
        list(ALL_PREDECLARED_VARIANTS)
        if args.variant == ALL_PREDECLARED
        else [validate_s2_context_experiment_variant(args.variant).value]
    )
    symbols = _selected_symbols(args)
    classifications = load_classifications(args.classification_file)

    reporter.info(
        "Starting Phase 33G.1 S2 context experiments "
        f"variants={','.join(variants)} symbols={len(symbols)} "
        f"benchmark_index={args.benchmark_index}"
    )

    engine = _get_database_engine()
    stock_loader = SQLAlchemyDailyOHLCVLoader(engine=engine)
    stock_loader.lookback_buffer_days = CONTEXT_LOOKBACK_BUFFER_DAYS
    index_reader = SQLAlchemyMarketIndexDailyReader(engine)

    reporter.info("Loading stock OHLCV data...")
    data_by_symbol = stock_loader.load_symbols(symbols, args.start_date, args.end_date)
    reporter.info(f"Loaded stock symbols: {len(data_by_symbol)}")

    reporter.info(f"Loading benchmark index data: {args.benchmark_index}")
    benchmark_data = index_reader.load(
        index_symbol=args.benchmark_index,
        start_date=args.start_date,
        end_date=args.end_date,
    ).frame

    reporter.info("Loading Nifty 50 signal-context data...")
    try:
        nifty_data = stock_loader.load_instrument_key(
            NIFTY_50_INSTRUMENT_KEY,
            args.start_date,
            args.end_date,
        )
    except Exception as error:  # pragma: no cover - defensive CLI fallback
        reporter.info(f"Nifty 50 context data unavailable: {error}")
        nifty_data = None

    reporter.info("Loading mapped sector index data without benchmark fallback...")
    sector_index_data = _load_sector_index_data(
        index_reader=index_reader,
        symbols=symbols,
        classifications=classifications,
        start_date=args.start_date,
        end_date=args.end_date,
        benchmark_index=args.benchmark_index,
        reporter=reporter,
    )

    for variant in variants:
        variant_output_dir = (
            args.output_dir / variant if args.variant == ALL_PREDECLARED else args.output_dir
        )
        _run_variant(
            variant=variant,
            args=args,
            data_by_symbol=data_by_symbol,
            benchmark_data=benchmark_data,
            classifications=classifications,
            sector_index_data=sector_index_data,
            nifty_data=nifty_data,
            output_dir=variant_output_dir,
            reporter=reporter,
        )

    reporter.complete(
        f"Completed Phase 33G.1 setup/run wrapper in "
        f"{perf_counter() - total_started:.2f}s"
    )
    return 0


def _run_variant(
    *,
    variant: str,
    args: argparse.Namespace,
    data_by_symbol: dict,
    benchmark_data,
    classifications: dict[str, dict[str, str]],
    sector_index_data: dict,
    nifty_data,
    output_dir: Path,
    reporter: ProgressReporter,
) -> None:
    reporter.info(f"Running S2 context experiment variant: {variant}")
    context_filter = None
    if variant != "S2_BASELINE":
        context_filter = build_s2_context_signal_filter(
            variant=variant,
            data_by_symbol=data_by_symbol,
            benchmark_data=benchmark_data,
            benchmark_index=args.benchmark_index,
            classifications=classifications,
            sector_index_data=sector_index_data,
        )
    result = run_s2_markov_portfolio_backtest(
        data_by_symbol=data_by_symbol,
        start_date=args.start_date,
        end_date=args.end_date,
        starting_equity=args.starting_equity,
        risk_per_trade=args.risk_per_trade,
        max_concurrent_positions=args.max_concurrent_positions,
        state_lookback_sessions=args.state_lookback_sessions,
        min_state_observations=args.min_state_observations,
        forward_return_sessions=args.forward_return_sessions,
        positive_return_threshold_pct=args.positive_return_threshold_pct,
        signal_probability_threshold=args.signal_probability_threshold,
        signal_average_forward_return_threshold_pct=(
            args.signal_average_forward_return_threshold_pct
        ),
        atr_window=14,
        atr_multiplier=Decimal("2"),
        reward_risk_ratio=Decimal("2"),
        max_holding_sessions=20,
        round_trip_cost_pct=Decimal("0.004"),
        progress_reporter=reporter,
        markov_signal_filter=BASELINE_MARKOV_SIGNAL_FILTER,
        s2_candidate_ranking_mode=S2_CANDIDATE_RANKING_NONE,
        nifty_data=nifty_data,
        signal_context_filter=context_filter,
    )
    result = replace(result, strategy_variant=variant)
    paths = export_portfolio_backtest_csvs(
        result,
        output_dir,
        stock_data_by_symbol=data_by_symbol,
        nifty_data=nifty_data,
        progress_reporter=reporter,
        include_all_signal_diagnostics=not args.skip_all_signal_diagnostics,
    )
    _write_metadata(
        output_dir / "s2_context_experiment_metadata.json",
        variant_metadata(
            variant=variant,
            benchmark_index=args.benchmark_index,
            classification_file=str(args.classification_file),
        ),
    )
    reporter.info(f"Wrote {len(paths)} CSV files to {output_dir}")


def _load_sector_index_data(
    *,
    index_reader: SQLAlchemyMarketIndexDailyReader,
    symbols: list[str],
    classifications: dict[str, dict[str, str]],
    start_date: date,
    end_date: date,
    benchmark_index: str,
    reporter: ProgressReporter,
) -> dict[str, object]:
    resolutions = needed_sector_indices_for_symbols(symbols, classifications)
    needed_indices = sorted(
        {
            resolution.sector_proxy
            for resolution in resolutions.values()
            if resolution.sector_proxy is not None
            and resolution.sector_proxy != benchmark_index
        }
    )
    frames: dict[str, object] = {}
    for index_symbol in needed_indices:
        try:
            frames[index_symbol] = index_reader.load(
                index_symbol=index_symbol,
                start_date=start_date,
                end_date=end_date,
            ).frame
        except Exception as error:  # pragma: no cover - defensive CLI fallback
            reporter.info(f"Sector index unavailable: {index_symbol}: {error}")
    reporter.info(f"Loaded mapped sector index frames: {len(frames)}")
    return frames


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run pre-declared Phase 33G.1 S2 context experiments."
    )
    parser.add_argument("--start-date", required=True, type=_parse_date)
    parser.add_argument("--end-date", required=True, type=_parse_date)
    parser.add_argument("--symbols")
    parser.add_argument("--symbols-file", type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--variant",
        required=True,
        choices=(*ALL_PREDECLARED_VARIANTS, ALL_PREDECLARED),
    )
    parser.add_argument("--benchmark-index", default="NIFTY_500")
    parser.add_argument(
        "--classification-file",
        type=Path,
        default=DEFAULT_CLASSIFICATION_FILE,
    )
    parser.add_argument(
        "--starting-equity",
        default=Decimal("1000000"),
        type=Decimal,
    )
    parser.add_argument(
        "--risk-per-trade",
        default=Decimal("0.01"),
        type=Decimal,
    )
    parser.add_argument("--max-concurrent-positions", default=5, type=int)
    parser.add_argument("--state-lookback-sessions", default=252, type=int)
    parser.add_argument("--min-state-observations", default=10, type=int)
    parser.add_argument("--forward-return-sessions", default=10, type=int)
    parser.add_argument(
        "--positive-return-threshold-pct",
        default=3.0,
        type=float,
    )
    parser.add_argument(
        "--signal-probability-threshold",
        default=0.60,
        type=float,
    )
    parser.add_argument(
        "--signal-average-forward-return-threshold-pct",
        default=1.0,
        type=float,
    )
    parser.add_argument(
        "--verbosity",
        choices=["quiet", "normal", "verbose"],
        default="normal",
    )
    parser.add_argument(
        "--skip-all-signal-diagnostics",
        action="store_true",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if bool(args.symbols) == bool(args.symbols_file):
        parser.error("provide exactly one of --symbols or --symbols-file")
    if args.end_date < args.start_date:
        parser.error("--end-date must be on or after --start-date")
    if args.state_lookback_sessions <= 0:
        parser.error("--state-lookback-sessions must be positive")
    if args.min_state_observations <= 0:
        parser.error("--min-state-observations must be positive")
    if args.forward_return_sessions <= 0:
        parser.error("--forward-return-sessions must be positive")
    return args


def _selected_symbols(args: argparse.Namespace) -> list[str]:
    if args.symbols:
        return _parse_symbols(args.symbols)
    return load_symbols_file(args.symbols_file)


def load_symbols_file(path: Path) -> list[str]:
    rows = _read_csv(path)
    symbols = [
        _clean(row.get("symbol") or row.get("trading_symbol")).upper()
        for row in rows
    ]
    return [symbol for symbol in symbols if symbol]


def load_classifications(path: Path) -> dict[str, dict[str, str]]:
    return {
        _clean(row.get("symbol")).upper(): row
        for row in _read_csv(path)
        if _clean(row.get("symbol"))
    }


def _parse_symbols(value: str) -> list[str]:
    symbols = [symbol.strip().upper() for symbol in value.split(",")]
    return [symbol for symbol in symbols if symbol]


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("dates must use YYYY-MM-DD format") from error


def _read_csv(path: Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _write_metadata(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _get_database_engine() -> object:
    try:
        from veridian_quant.data.db_client import DatabaseClient
    except ImportError as error:
        raise RuntimeError(
            "Could not import veridian_quant.data.db_client.DatabaseClient"
        ) from error

    engine = DatabaseClient().get_engine()
    if engine is None:
        raise RuntimeError("DatabaseClient().get_engine() returned None")
    return engine


if __name__ == "__main__":
    raise SystemExit(main())
