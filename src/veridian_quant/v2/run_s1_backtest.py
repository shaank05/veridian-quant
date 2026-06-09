"""Command-line runner for Veridian Quant v2 S1 portfolio backtests."""

from argparse import ArgumentParser, ArgumentTypeError, Namespace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from veridian_quant.v2.backtesting.portfolio_runner import (
    run_s1_portfolio_backtest,
)
from veridian_quant.v2.data.loaders import SQLAlchemyDailyOHLCVLoader
from veridian_quant.v2.reporting.exporters import export_portfolio_backtest_csvs
from veridian_quant.v2.reporting.progress import ProgressReporter


def main(argv: Iterable[str] | None = None) -> int:
    """Run the S1 portfolio backtest CLI."""

    args = _parse_args(argv)
    reporter = ProgressReporter(args.verbosity)
    reporter.info(
        "Starting S1 backtest "
        f"{args.start_date} to {args.end_date} "
        f"equity={args.starting_equity} "
        f"risk={args.risk_per_trade} "
        f"max_positions={args.max_concurrent_positions}"
    )
    engine = _get_database_engine()
    loader = SQLAlchemyDailyOHLCVLoader(engine=engine)

    reporter.info("Loading OHLCV data...")
    if args.all_symbols:
        data_by_symbol = loader.load_all_available_symbols(
            args.start_date,
            args.end_date,
        )
    else:
        data_by_symbol = loader.load_symbols(
            _parse_symbols(args.symbols),
            args.start_date,
            args.end_date,
        )
    reporter.info("Finished loading OHLCV data.")
    reporter.info(f"Loaded symbols: {len(data_by_symbol)}")

    reporter.info("Running portfolio backtest...")
    result = run_s1_portfolio_backtest(
        data_by_symbol=data_by_symbol,
        start_date=args.start_date,
        end_date=args.end_date,
        starting_equity=args.starting_equity,
        risk_per_trade=args.risk_per_trade,
        max_concurrent_positions=args.max_concurrent_positions,
        zscore_window=20,
        entry_threshold=-2.0,
        atr_window=14,
        atr_multiplier=Decimal("2"),
        reward_risk_ratio=Decimal("2"),
        max_holding_sessions=20,
        round_trip_cost_pct=Decimal("0.004"),
        progress_reporter=reporter,
    )
    reporter.info("Finished portfolio backtest.")
    paths = export_portfolio_backtest_csvs(result, args.output_dir)
    reporter.info(f"CSV export location: {Path(args.output_dir)}")
    reporter.complete(
        f"Completed S1 backtest. Wrote {len(paths)} CSV files to "
        f"{Path(args.output_dir)}"
    )
    return 0


def _parse_args(argv: Iterable[str] | None) -> Namespace:
    """Parse CLI arguments."""

    parser = ArgumentParser(description="Run Veridian Quant v2 S1 backtest.")
    parser.add_argument("--start-date", required=True, type=_parse_date)
    parser.add_argument("--end-date", required=True, type=_parse_date)
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
    parser.add_argument("--symbols")
    parser.add_argument("--all-symbols", action="store_true")
    parser.add_argument("--output-dir", default="reports/v2/s1")
    parser.add_argument(
        "--verbosity",
        choices=["quiet", "normal", "verbose"],
        default="normal",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.all_symbols == bool(args.symbols):
        parser.error("provide exactly one of --all-symbols or --symbols")
    if args.end_date < args.start_date:
        parser.error("--end-date must be on or after --start-date")
    return args


def _parse_date(value: str) -> date:
    """Parse an ISO date argument."""

    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ArgumentTypeError("dates must use YYYY-MM-DD format") from error


def _parse_symbols(value: str) -> list[str]:
    """Parse comma-separated symbols."""

    symbols = [symbol.strip().upper() for symbol in value.split(",")]
    return [symbol for symbol in symbols if symbol]


def _get_database_engine() -> object:
    """Return the existing project SQLAlchemy engine or fail clearly."""

    try:
        from src.veridian_quant.data.db_client import DatabaseClient
    except ImportError as error:
        raise RuntimeError(
            "Could not import src.veridian_quant.data.db_client.DatabaseClient"
        ) from error

    engine = DatabaseClient().get_engine()
    if engine is None:
        raise RuntimeError("DatabaseClient().get_engine() returned None")
    return engine


if __name__ == "__main__":
    raise SystemExit(main())
