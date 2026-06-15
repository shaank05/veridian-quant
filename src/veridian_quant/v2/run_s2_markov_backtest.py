"""Command-line runner for Veridian Quant v2 S2 Markov backtests."""

from argparse import ArgumentParser, ArgumentTypeError, Namespace
from datetime import date
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Iterable

from veridian_quant.v2.backtesting.markov_portfolio_runner import (
    run_s2_markov_portfolio_backtest,
)
from veridian_quant.v2.data.loaders import SQLAlchemyDailyOHLCVLoader
from veridian_quant.v2.reporting.exporters import export_portfolio_backtest_csvs
from veridian_quant.v2.reporting.progress import ProgressReporter


NIFTY_50_INSTRUMENT_KEY = "NSE_INDEX|Nifty 50"
CONTEXT_LOOKBACK_BUFFER_DAYS = 365


def main(argv: Iterable[str] | None = None) -> int:
    """Run the S2 Markov portfolio backtest CLI."""

    total_started = perf_counter()
    args = _parse_args(argv)
    reporter = ProgressReporter(args.verbosity)
    reporter.info(
        "Starting S2 Markov backtest "
        f"{args.start_date} to {args.end_date} "
        f"equity={args.starting_equity} "
        f"risk={args.risk_per_trade} "
        f"max_positions={args.max_concurrent_positions}"
    )
    setup_started = perf_counter()
    engine = _get_database_engine()
    loader = SQLAlchemyDailyOHLCVLoader(engine=engine)
    loader.lookback_buffer_days = CONTEXT_LOOKBACK_BUFFER_DAYS
    reporter.info(
        f"Finished database engine/loader setup in "
        f"{perf_counter() - setup_started:.2f}s"
    )

    reporter.info("Loading OHLCV data...")
    load_started = perf_counter()
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
    reporter.info(
        f"Finished OHLCV data loading in {perf_counter() - load_started:.2f}s"
    )
    reporter.info(f"Loaded symbols: {len(data_by_symbol)}")

    reporter.info("Loading Nifty 50 context data...")
    nifty_started = perf_counter()
    try:
        nifty_data = loader.load_instrument_key(
            NIFTY_50_INSTRUMENT_KEY,
            args.start_date,
            args.end_date,
        )
    except Exception as error:  # pragma: no cover - defensive CLI fallback
        reporter.info(f"Nifty 50 context data unavailable: {error}")
        nifty_data = None
    else:
        reporter.info(f"Loaded Nifty 50 context rows: {len(nifty_data)}")
    reporter.info(
        f"Finished Nifty context loading in {perf_counter() - nifty_started:.2f}s"
    )

    reporter.info("Running S2 Markov portfolio backtest...")
    backtest_started = perf_counter()
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
    )
    reporter.info(
        f"Finished S2 portfolio backtest in "
        f"{perf_counter() - backtest_started:.2f}s"
    )
    export_started = perf_counter()
    paths = export_portfolio_backtest_csvs(
        result,
        args.output_dir,
        stock_data_by_symbol=data_by_symbol,
        nifty_data=nifty_data,
        progress_reporter=reporter,
    )
    reporter.info(
        f"Finished CSV export in {perf_counter() - export_started:.2f}s"
    )
    reporter.info(
        f"Finished total S2 CLI runtime in "
        f"{perf_counter() - total_started:.2f}s"
    )
    reporter.complete(
        f"Completed S2 Markov backtest. Wrote {len(paths)} CSV files to "
        f"{Path(args.output_dir)}"
    )
    return 0


def _parse_args(argv: Iterable[str] | None) -> Namespace:
    """Parse CLI arguments."""

    parser = ArgumentParser(
        description="Run Veridian Quant v2 S2 Markov backtest."
    )
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
    parser.add_argument(
        "--output-dir",
        default="reports/v2/s2_markov",
    )
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
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.all_symbols == bool(args.symbols):
        parser.error("provide exactly one of --all-symbols or --symbols")
    if args.end_date < args.start_date:
        parser.error("--end-date must be on or after --start-date")
    if args.state_lookback_sessions <= 0:
        parser.error("--state-lookback-sessions must be positive")
    if args.min_state_observations <= 0:
        parser.error("--min-state-observations must be positive")
    if args.forward_return_sessions <= 0:
        parser.error("--forward-return-sessions must be positive")
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
