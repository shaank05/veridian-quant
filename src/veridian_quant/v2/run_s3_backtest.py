"""Command-line runner for Veridian Quant v2 S3 portfolio backtests."""

from argparse import ArgumentParser, ArgumentTypeError, Namespace
from datetime import date
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Iterable

from veridian_quant.v2.backtesting.s3_portfolio_runner import (
    run_s3_portfolio_backtest,
)
from veridian_quant.v2.data.loaders import SQLAlchemyDailyOHLCVLoader
from veridian_quant.v2.reporting.exporters import export_portfolio_backtest_csvs
from veridian_quant.v2.reporting.progress import ProgressReporter


NIFTY_50_INSTRUMENT_KEY = "NSE_INDEX|Nifty 50"
S3_LOOKBACK_BUFFER_DAYS = 365


def main(argv: Iterable[str] | None = None) -> int:
    """Run the S3 portfolio backtest CLI."""

    total_started = perf_counter()
    args = _parse_args(argv)
    reporter = ProgressReporter(args.verbosity)
    reporter.info(
        "Starting S3 Trend Pullback backtest "
        f"{args.start_date} to {args.end_date} "
        f"equity={args.starting_equity} "
        f"risk={args.risk_per_trade} "
        f"max_positions={args.max_concurrent_positions}"
    )

    setup_started = perf_counter()
    engine = _get_database_engine()
    loader = SQLAlchemyDailyOHLCVLoader(engine=engine)
    loader.lookback_buffer_days = S3_LOOKBACK_BUFFER_DAYS
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

    reporter.info("Running S3 portfolio backtest...")
    backtest_started = perf_counter()
    result = run_s3_portfolio_backtest(
        data_by_symbol=data_by_symbol,
        start_date=args.start_date,
        end_date=args.end_date,
        starting_equity=args.starting_equity,
        risk_per_trade=args.risk_per_trade,
        max_concurrent_positions=args.max_concurrent_positions,
        sma_fast_window=args.sma_fast_window,
        sma_slow_window=args.sma_slow_window,
        sma_slope_lookback=args.sma_slope_lookback,
        pullback_lookback=args.pullback_lookback,
        min_pullback_return_pct=args.min_pullback_return_pct,
        max_pullback_return_pct=args.max_pullback_return_pct,
        max_drawdown_20d_pct=args.max_drawdown_20d_pct,
        min_drawdown_20d_pct=args.min_drawdown_20d_pct,
        atr_window=14,
        max_atr_pct=args.max_atr_pct,
        max_atr_expansion_5d_pct=args.max_atr_expansion_5d_pct,
        fresh_low_window=args.fresh_low_window,
        allow_repeated_signals=args.allow_repeated_signals,
        require_recovery_day=not args.disable_recovery_day,
        atr_multiplier=Decimal("2"),
        reward_risk_ratio=Decimal("2"),
        max_holding_sessions=20,
        round_trip_cost_pct=Decimal("0.004"),
        progress_reporter=reporter,
    )
    reporter.info(
        f"Finished S3 portfolio backtest in "
        f"{perf_counter() - backtest_started:.2f}s"
    )

    export_started = perf_counter()
    paths = export_portfolio_backtest_csvs(
        result,
        args.output_dir,
        stock_data_by_symbol=data_by_symbol,
        nifty_data=nifty_data,
        progress_reporter=reporter,
        include_all_signal_diagnostics=not args.skip_all_signal_diagnostics,
    )
    reporter.info(
        f"Finished CSV export in {perf_counter() - export_started:.2f}s"
    )
    reporter.info(
        f"Finished total S3 CLI runtime in "
        f"{perf_counter() - total_started:.2f}s"
    )
    reporter.complete(
        f"Completed S3 Trend Pullback backtest. Wrote {len(paths)} CSV files to "
        f"{Path(args.output_dir)}"
    )
    return 0


def _parse_args(argv: Iterable[str] | None) -> Namespace:
    """Parse CLI arguments."""

    parser = ArgumentParser(
        description="Run Veridian Quant v2 S3 Trend Pullback backtest."
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
    parser.add_argument("--output-dir", default="reports/v2/s3")
    parser.add_argument("--sma-fast-window", default=50, type=int)
    parser.add_argument("--sma-slow-window", default=200, type=int)
    parser.add_argument("--sma-slope-lookback", default=20, type=int)
    parser.add_argument("--pullback-lookback", default=5, type=int)
    parser.add_argument("--min-pullback-return-pct", default=-10.0, type=float)
    parser.add_argument("--max-pullback-return-pct", default=-1.0, type=float)
    parser.add_argument("--min-drawdown-20d-pct", default=-15.0, type=float)
    parser.add_argument("--max-drawdown-20d-pct", default=-3.0, type=float)
    parser.add_argument("--max-atr-pct", default=8.0, type=float)
    parser.add_argument("--max-atr-expansion-5d-pct", default=50.0, type=float)
    parser.add_argument("--fresh-low-window", default=60, type=int)
    parser.add_argument("--allow-repeated-signals", action="store_true")
    parser.add_argument("--disable-recovery-day", action="store_true")
    parser.add_argument("--skip-all-signal-diagnostics", action="store_true")
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
    for name in (
        "sma_fast_window",
        "sma_slow_window",
        "sma_slope_lookback",
        "pullback_lookback",
        "fresh_low_window",
    ):
        if getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} must be positive")
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
