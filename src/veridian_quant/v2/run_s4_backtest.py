"""Command-line runner for Veridian Quant v2 S4 portfolio backtests."""

from argparse import ArgumentParser, ArgumentTypeError, Namespace
from datetime import date
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Iterable

from veridian_quant.v2.backtesting.s4_portfolio_runner import (
    run_s4_portfolio_backtest,
)
from veridian_quant.v2.data.loaders import SQLAlchemyDailyOHLCVLoader
from veridian_quant.v2.reporting.exporters import export_portfolio_backtest_csvs
from veridian_quant.v2.reporting.progress import ProgressReporter
from veridian_quant.v2.strategies.s4_entropy_volatility_compression_breakout import (
    S4_ATR_COMPRESSION_BREAKOUT_V1,
    S4_ENTROPY_GATED_BREAKOUT_V1,
    S4_RANGE_COMPRESSION_BREAKOUT_V1,
)


NIFTY_50_INSTRUMENT_KEY = "NSE_INDEX|Nifty 50"
S4_LOOKBACK_BUFFER_DAYS = 365
S4_CLI_VARIANTS = {
    "atr_compression_breakout_v1": S4_ATR_COMPRESSION_BREAKOUT_V1,
    "range_compression_breakout_v1": S4_RANGE_COMPRESSION_BREAKOUT_V1,
    "entropy_gated_breakout_v1": S4_ENTROPY_GATED_BREAKOUT_V1,
    S4_ATR_COMPRESSION_BREAKOUT_V1: S4_ATR_COMPRESSION_BREAKOUT_V1,
    S4_RANGE_COMPRESSION_BREAKOUT_V1: S4_RANGE_COMPRESSION_BREAKOUT_V1,
    S4_ENTROPY_GATED_BREAKOUT_V1: S4_ENTROPY_GATED_BREAKOUT_V1,
}


def main(argv: Iterable[str] | None = None) -> int:
    """Run the S4 portfolio backtest CLI."""

    total_started = perf_counter()
    args = _parse_args(argv)
    s4_variant = _s4_variant_from_cli(args.s4_variant)
    reporter = ProgressReporter(args.verbosity)
    reporter.info(
        "Starting S4 Compression Breakout backtest "
        f"{args.start_date} to {args.end_date} "
        f"equity={args.starting_equity} "
        f"risk={args.risk_per_trade} "
        f"max_positions={args.max_concurrent_positions} "
        f"s4_variant={s4_variant}"
    )

    setup_started = perf_counter()
    engine = _get_database_engine()
    loader = SQLAlchemyDailyOHLCVLoader(engine=engine)
    loader.lookback_buffer_days = S4_LOOKBACK_BUFFER_DAYS
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

    reporter.info("Running S4 portfolio backtest...")
    backtest_started = perf_counter()
    result = run_s4_portfolio_backtest(
        data_by_symbol=data_by_symbol,
        start_date=args.start_date,
        end_date=args.end_date,
        starting_equity=args.starting_equity,
        risk_per_trade=args.risk_per_trade,
        max_concurrent_positions=args.max_concurrent_positions,
        strategy_variant=s4_variant,
        atr_window=args.atr_window,
        range_window=args.range_window,
        breakout_window=args.breakout_window,
        percentile_window=args.percentile_window,
        entropy_window=args.entropy_window,
        compression_threshold=args.compression_threshold,
        entropy_threshold=args.entropy_threshold,
        flat_threshold=args.flat_threshold,
        allow_repeated_signals=args.allow_repeated_signals,
        atr_multiplier=args.atr_multiplier,
        reward_risk_ratio=args.reward_risk_ratio,
        max_holding_sessions=args.max_holding_sessions,
        round_trip_cost_pct=args.round_trip_cost_pct,
        progress_reporter=reporter,
    )
    reporter.info(
        f"Finished S4 portfolio backtest in "
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
        f"Finished total S4 CLI runtime in "
        f"{perf_counter() - total_started:.2f}s"
    )
    reporter.complete(
        f"Completed S4 Compression Breakout backtest. Wrote {len(paths)} "
        f"CSV files to {Path(args.output_dir)}"
    )
    return 0


def _parse_args(argv: Iterable[str] | None) -> Namespace:
    """Parse CLI arguments."""

    parser = ArgumentParser(
        description="Run Veridian Quant v2 S4 Compression Breakout backtest."
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
    parser.add_argument("--output-dir", default="reports/v2/s4")
    parser.add_argument("--atr-window", default=14, type=int)
    parser.add_argument("--range-window", default=20, type=int)
    parser.add_argument("--breakout-window", default=20, type=int)
    parser.add_argument("--percentile-window", default=100, type=int)
    parser.add_argument("--entropy-window", default=20, type=int)
    parser.add_argument("--compression-threshold", default=0.20, type=float)
    parser.add_argument("--entropy-threshold", default=0.70, type=float)
    parser.add_argument("--flat-threshold", default=0.0, type=float)
    parser.add_argument("--allow-repeated-signals", action="store_true")
    parser.add_argument("--atr-multiplier", default=Decimal("2"), type=Decimal)
    parser.add_argument("--reward-risk-ratio", default=Decimal("2"), type=Decimal)
    parser.add_argument("--max-holding-sessions", default=20, type=int)
    parser.add_argument(
        "--round-trip-cost-pct",
        default=Decimal("0.004"),
        type=Decimal,
    )
    parser.add_argument(
        "--s4-variant",
        choices=tuple(S4_CLI_VARIANTS),
        default="atr_compression_breakout_v1",
    )
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
        "atr_window",
        "range_window",
        "breakout_window",
        "percentile_window",
        "entropy_window",
        "max_holding_sessions",
    ):
        if getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    if args.flat_threshold < 0:
        parser.error("--flat-threshold must be non-negative")
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


def _s4_variant_from_cli(value: str) -> str:
    """Return the canonical S4 variant string for a CLI variant name."""

    return S4_CLI_VARIANTS[value]


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
