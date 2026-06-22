"""Command-line runner for Veridian Quant v2 S5 portfolio backtests."""

from argparse import ArgumentParser, ArgumentTypeError, Namespace
from datetime import date
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Iterable

from veridian_quant.v2.backtesting.s5_portfolio_runner import (
    run_s5_portfolio_backtest,
)
from veridian_quant.v2.data.loaders import SQLAlchemyDailyOHLCVLoader
from veridian_quant.v2.reporting.exporters import export_portfolio_backtest_csvs
from veridian_quant.v2.reporting.progress import ProgressReporter
from veridian_quant.v2.strategies.s5_relative_strength_momentum_rotation import (
    S5_DUAL_MOMENTUM_63_126D_V1,
    S5_SIMPLE_RS_126D_V1,
    S5_VOL_ADJUSTED_RS_V1,
)


NIFTY_50_INSTRUMENT_KEY = "NSE_INDEX|Nifty 50"
S5_LOOKBACK_BUFFER_DAYS = 450
S5_CLI_VARIANTS = {
    "simple_rs_126d_v1": S5_SIMPLE_RS_126D_V1,
    "dual_momentum_63_126d_v1": S5_DUAL_MOMENTUM_63_126D_V1,
    "vol_adjusted_rs_v1": S5_VOL_ADJUSTED_RS_V1,
    S5_SIMPLE_RS_126D_V1: S5_SIMPLE_RS_126D_V1,
    S5_DUAL_MOMENTUM_63_126D_V1: S5_DUAL_MOMENTUM_63_126D_V1,
    S5_VOL_ADJUSTED_RS_V1: S5_VOL_ADJUSTED_RS_V1,
}


def main(argv: Iterable[str] | None = None) -> int:
    """Run the independent S5 momentum portfolio backtest CLI."""

    total_started = perf_counter()
    args = _parse_args(argv)
    s5_variant = _s5_variant_from_cli(args.s5_variant)
    reporter = ProgressReporter(args.verbosity)
    reporter.info(
        "Starting S5 Relative Strength / Momentum Rotation backtest "
        f"{args.start_date} to {args.end_date} "
        f"equity={args.starting_equity} "
        f"risk={args.risk_per_trade} "
        f"max_positions={args.max_concurrent_positions} "
        f"s5_variant={s5_variant}"
    )

    setup_started = perf_counter()
    engine = _get_database_engine()
    loader = SQLAlchemyDailyOHLCVLoader(engine=engine)
    loader.lookback_buffer_days = S5_LOOKBACK_BUFFER_DAYS
    reporter.info(
        "Finished database engine/loader setup in "
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

    reporter.info("Running S5 portfolio backtest...")
    backtest_started = perf_counter()
    result = run_s5_portfolio_backtest(
        data_by_symbol=data_by_symbol,
        start_date=args.start_date,
        end_date=args.end_date,
        starting_equity=args.starting_equity,
        risk_per_trade=args.risk_per_trade,
        max_concurrent_positions=args.max_concurrent_positions,
        strategy_variant=s5_variant,
        enable_trend_filter=not args.disable_trend_filter,
        min_rank_score=args.min_rank_score,
        allow_repeated_signals=args.allow_repeated_signals,
        atr_window=args.atr_window,
        atr_multiplier=args.atr_multiplier,
        reward_risk_ratio=args.reward_risk_ratio,
        max_holding_sessions=args.max_holding_sessions,
        round_trip_cost_pct=args.round_trip_cost_pct,
        progress_reporter=reporter,
    )
    reporter.info(
        "Finished S5 portfolio backtest in "
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
    reporter.info(f"Finished CSV export in {perf_counter() - export_started:.2f}s")
    reporter.info(
        f"Finished total S5 CLI runtime in {perf_counter() - total_started:.2f}s"
    )
    reporter.complete(
        f"Completed S5 Relative Strength / Momentum Rotation backtest. "
        f"Wrote {len(paths)} CSV files to {Path(args.output_dir)}"
    )
    return 0


def _parse_args(argv: Iterable[str] | None) -> Namespace:
    """Parse and validate S5 CLI arguments."""

    parser = ArgumentParser(
        description=(
            "Run Veridian Quant v2 S5 Relative Strength / Momentum Rotation "
            "backtest."
        )
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
    parser.add_argument("--output-dir", default="reports/v2/s5")
    parser.add_argument("--atr-window", default=14, type=int)
    parser.add_argument("--atr-multiplier", default=Decimal("2"), type=Decimal)
    parser.add_argument("--reward-risk-ratio", default=Decimal("2"), type=Decimal)
    parser.add_argument("--max-holding-sessions", default=20, type=int)
    parser.add_argument(
        "--round-trip-cost-pct",
        default=Decimal("0.004"),
        type=Decimal,
    )
    parser.add_argument(
        "--s5-variant",
        choices=tuple(S5_CLI_VARIANTS),
        default="simple_rs_126d_v1",
    )
    parser.add_argument("--disable-trend-filter", action="store_true")
    parser.add_argument("--min-rank-score", type=float)
    parser.add_argument("--allow-repeated-signals", action="store_true")
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
        "max_concurrent_positions",
        "atr_window",
        "max_holding_sessions",
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


def _s5_variant_from_cli(value: str) -> str:
    """Return the canonical S5 variant string for a CLI variant name."""

    return S5_CLI_VARIANTS[value]


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
