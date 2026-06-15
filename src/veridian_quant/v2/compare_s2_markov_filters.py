"""Run S2 Markov filter experiments and write a comparison summary."""

from argparse import ArgumentParser, ArgumentTypeError, Namespace
from datetime import date
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Iterable

import pandas as pd

from veridian_quant.v2.backtesting.markov_portfolio_runner import (
    run_s2_markov_portfolio_backtest,
)
from veridian_quant.v2.data.loaders import SQLAlchemyDailyOHLCVLoader
from veridian_quant.v2.reporting.exporters import export_portfolio_backtest_csvs
from veridian_quant.v2.reporting.metrics import calculate_performance_summary
from veridian_quant.v2.reporting.progress import ProgressReporter
from veridian_quant.v2.run_s2_markov_backtest import (
    CONTEXT_LOOKBACK_BUFFER_DAYS,
    NIFTY_50_INSTRUMENT_KEY,
    _get_database_engine,
    _parse_symbols,
)
from veridian_quant.v2.strategies.s2_markov_filters import MARKOV_SIGNAL_FILTERS


DEFAULT_FILTERS = (
    "none",
    "exclude_ret_down",
    "keep_ret_flat_up_strong_up",
    "exclude_dd_deep",
    "exclude_ret_down_and_dd_deep",
    "exclude_low_near",
    "balanced_markov_v1",
)


def main(argv: Iterable[str] | None = None) -> int:
    """Run each requested S2 Markov filter and compare results."""

    args = _parse_args(argv)
    reporter = ProgressReporter(args.verbosity)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    reporter.info("Loading OHLCV data for S2 Markov filter comparison...")
    engine = _get_database_engine()
    loader = SQLAlchemyDailyOHLCVLoader(engine=engine)
    loader.lookback_buffer_days = CONTEXT_LOOKBACK_BUFFER_DAYS
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
    reporter.info(f"Loaded symbols: {len(data_by_symbol)}")

    try:
        nifty_data = loader.load_instrument_key(
            NIFTY_50_INSTRUMENT_KEY,
            args.start_date,
            args.end_date,
        )
    except Exception as error:  # pragma: no cover - defensive CLI fallback
        reporter.info(f"Nifty 50 context data unavailable: {error}")
        nifty_data = None

    summary_rows = []
    for filter_name in args.filters:
        reporter.info(f"Running S2 Markov filter experiment: {filter_name}")
        started = perf_counter()
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
            markov_signal_filter=filter_name,
        )
        export_portfolio_backtest_csvs(
            result,
            output_dir / filter_name,
            stock_data_by_symbol=data_by_symbol,
            nifty_data=nifty_data,
            progress_reporter=reporter,
            include_all_signal_diagnostics=not args.skip_all_signal_diagnostics,
        )
        runtime_seconds = perf_counter() - started
        summary_rows.append(_summary_row(filter_name, result, runtime_seconds))

    pd.DataFrame(summary_rows, columns=SUMMARY_COLUMNS).to_csv(
        output_dir / "s2_markov_filter_experiment_summary.csv",
        index=False,
    )
    reporter.complete(
        f"Completed S2 Markov filter comparison. Wrote reports to {output_dir}"
    )
    return 0


SUMMARY_COLUMNS = [
    "markov_signal_filter",
    "strategy_variant",
    "total_net_pnl",
    "total_return_pct",
    "cagr_pct",
    "max_drawdown_pct",
    "total_trades",
    "winning_trades",
    "losing_trades",
    "win_rate_pct",
    "gross_profit",
    "gross_loss",
    "profit_factor",
    "average_net_pnl",
    "total_signals",
    "total_rejected_signals",
    "filter_rejected_signals",
    "capacity_rejected_signals",
    "active_symbol_rejected_signals",
    "runtime_seconds",
]


def _summary_row(
    filter_name: str,
    result: object,
    runtime_seconds: float,
) -> dict[str, object]:
    summary = calculate_performance_summary(result)
    rejected = getattr(result, "rejected_signals", ())
    return {
        "markov_signal_filter": filter_name,
        "strategy_variant": getattr(result, "strategy_variant", None),
        "total_net_pnl": summary.total_net_pnl,
        "total_return_pct": summary.total_return_pct,
        "cagr_pct": summary.cagr_pct,
        "max_drawdown_pct": summary.max_drawdown_pct,
        "total_trades": summary.total_trades,
        "winning_trades": summary.winning_trades,
        "losing_trades": summary.losing_trades,
        "win_rate_pct": summary.win_rate_pct,
        "gross_profit": summary.gross_profit,
        "gross_loss": summary.gross_loss,
        "profit_factor": summary.profit_factor,
        "average_net_pnl": summary.average_net_pnl,
        "total_signals": summary.total_signals,
        "total_rejected_signals": summary.total_rejected_signals,
        "filter_rejected_signals": _count_rejections(
            rejected,
            "S2_MARKOV_SIGNAL_FILTERED",
        ),
        "capacity_rejected_signals": _count_rejections(
            rejected,
            "PORTFOLIO_CAPACITY_FULL",
        ),
        "active_symbol_rejected_signals": _count_rejections(
            rejected,
            "ACTIVE_SYMBOL_TRADE_EXISTS",
        ),
        "runtime_seconds": runtime_seconds,
    }


def _count_rejections(rejected_signals: object, reason: str) -> int:
    return sum(1 for rejected in rejected_signals if rejected.reason == reason)


def _parse_args(argv: Iterable[str] | None) -> Namespace:
    parser = ArgumentParser(
        description="Compare S2 Markov signal filter experiments."
    )
    parser.add_argument("--start-date", required=True, type=_parse_date)
    parser.add_argument("--end-date", required=True, type=_parse_date)
    parser.add_argument("--symbols")
    parser.add_argument("--all-symbols", action="store_true")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--filters", default=",".join(DEFAULT_FILTERS), type=_parse_filters)
    parser.add_argument("--starting-equity", default=Decimal("1000000"), type=Decimal)
    parser.add_argument("--risk-per-trade", default=Decimal("0.01"), type=Decimal)
    parser.add_argument("--max-concurrent-positions", default=5, type=int)
    parser.add_argument("--state-lookback-sessions", default=252, type=int)
    parser.add_argument("--min-state-observations", default=10, type=int)
    parser.add_argument("--forward-return-sessions", default=10, type=int)
    parser.add_argument("--positive-return-threshold-pct", default=3.0, type=float)
    parser.add_argument("--signal-probability-threshold", default=0.60, type=float)
    parser.add_argument(
        "--signal-average-forward-return-threshold-pct",
        default=1.0,
        type=float,
    )
    parser.add_argument(
        "--skip-all-signal-diagnostics",
        action="store_true",
        default=True,
    )
    parser.add_argument(
        "--include-all-signal-diagnostics",
        action="store_false",
        dest="skip_all_signal_diagnostics",
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
    return args


def _parse_filters(value: str) -> tuple[str, ...]:
    filters = tuple(item.strip() for item in value.split(",") if item.strip())
    invalid = [item for item in filters if item not in MARKOV_SIGNAL_FILTERS]
    if invalid:
        raise ArgumentTypeError(
            f"unsupported filter(s): {', '.join(invalid)}; "
            f"expected one of {', '.join(MARKOV_SIGNAL_FILTERS)}"
        )
    return filters


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ArgumentTypeError("dates must use YYYY-MM-DD format") from error


if __name__ == "__main__":
    raise SystemExit(main())
