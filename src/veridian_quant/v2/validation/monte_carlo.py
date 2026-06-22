"""Monte Carlo validation for completed strategy trade PnL.

This module is deliberately independent of strategy generation and backtest
execution. It resamples already-realized net trade PnL for robustness analysis.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd


SUPPORTED_PNL_COLUMNS = ("net_pnl", "trade_net_pnl", "pnl")
DEFAULT_DRAWDOWN_THRESHOLDS = (0.10, 0.20, 0.30, 0.40)
VALID_MODES = frozenset({"shuffle", "bootstrap"})


@dataclass(frozen=True, slots=True)
class MonteCarloSimulationResult:
    """Metrics and sampled trade sequence for one simulation."""

    simulation_id: int
    final_equity: float
    net_pnl: float
    total_return_pct: float
    max_drawdown_pct: float
    max_drawdown_amount: float
    longest_losing_streak: int
    longest_winning_streak: int
    ending_below_starting_equity: bool
    ruin_or_below_zero: bool
    trade_pnls: tuple[float, ...] = field(repr=False)

    def to_record(self) -> dict[str, object]:
        """Return the metric fields suitable for tabular export."""

        record = asdict(self)
        record.pop("trade_pnls")
        return record


@dataclass(frozen=True, slots=True)
class MonteCarloSummary:
    """Aggregate metrics for a collection of simulations."""

    mode: str
    num_simulations: int
    input_trade_count: int
    simulated_trade_count: int
    starting_equity: float
    mean_final_equity: float
    median_final_equity: float
    p05_final_equity: float
    p95_final_equity: float
    worst_final_equity: float
    best_final_equity: float
    mean_max_drawdown_pct: float
    median_max_drawdown_pct: float
    p95_max_drawdown_pct: float
    worst_max_drawdown_pct: float
    probability_ending_below_starting_equity: float
    probability_ruin_or_below_zero: float
    probability_max_drawdown_gte_10_pct: float | None
    probability_max_drawdown_gte_20_pct: float | None
    probability_max_drawdown_gte_30_pct: float | None
    probability_max_drawdown_gte_40_pct: float | None
    median_longest_losing_streak: float
    p95_longest_losing_streak: float
    worst_longest_losing_streak: int
    drawdown_threshold_probabilities: Mapping[float, float] = field(repr=False)

    def to_record(self) -> dict[str, object]:
        """Return a flat record suitable for CSV export."""

        record = asdict(self)
        probabilities = record.pop("drawdown_threshold_probabilities")
        for threshold, probability in probabilities.items():
            key = f"probability_max_drawdown_gte_{threshold * 100:g}_pct"
            record[key] = probability
        return record


@dataclass(frozen=True, slots=True)
class MonteCarloValidationResult:
    """Complete validation result including input-cleaning metadata."""

    summary: MonteCarloSummary
    simulations: tuple[MonteCarloSimulationResult, ...]
    pnl_column: str | None
    dropped_nan_count: int
    random_seed: int | None
    drawdown_thresholds: tuple[float, ...]


def calculate_equity_path(
    trade_pnls: Iterable[float | Decimal], starting_equity: float | Decimal
) -> np.ndarray:
    """Return equity including starting equity followed by each completed trade."""

    start = _validate_starting_equity(starting_equity)
    pnls, _ = _coerce_pnls(trade_pnls)
    return np.concatenate(([start], start + np.cumsum(pnls, dtype=float)))


def calculate_max_drawdown(equity_path: Sequence[float]) -> float:
    """Return maximum peak-to-trough drawdown as a positive fraction."""

    drawdown_pct, _ = _drawdown_metrics(equity_path)
    return drawdown_pct


def calculate_longest_streaks(
    trade_pnls: Iterable[float | Decimal],
) -> tuple[int, int]:
    """Return longest losing and winning streaks; zero breaks either streak."""

    pnls, _ = _coerce_pnls(trade_pnls)
    longest_loss = longest_win = current_loss = current_win = 0
    for pnl in pnls:
        if pnl < 0:
            current_loss += 1
            current_win = 0
            longest_loss = max(longest_loss, current_loss)
        elif pnl > 0:
            current_win += 1
            current_loss = 0
            longest_win = max(longest_win, current_win)
        else:
            current_loss = current_win = 0
    return longest_loss, longest_win


def run_monte_carlo_simulation(
    trade_pnls: Iterable[float | Decimal],
    *,
    starting_equity: float | Decimal,
    num_simulations: int,
    random_seed: int | None = None,
    mode: str = "shuffle",
    num_trades: int | None = None,
) -> tuple[MonteCarloSimulationResult, ...]:
    """Run reproducible shuffle or bootstrap simulations."""

    pnls, _ = _coerce_pnls(trade_pnls)
    start = _validate_starting_equity(starting_equity)
    _validate_positive_integer(num_simulations, "num_simulations")
    normalized_mode = _validate_mode(mode)
    if num_trades is not None:
        _validate_positive_integer(num_trades, "num_trades")

    sample_size = len(pnls) if normalized_mode == "shuffle" else (num_trades or len(pnls))
    rng = np.random.default_rng(random_seed)
    results: list[MonteCarloSimulationResult] = []

    for simulation_id in range(1, num_simulations + 1):
        if normalized_mode == "shuffle":
            sampled = rng.permutation(pnls)
        else:
            sampled = rng.choice(pnls, size=sample_size, replace=True)

        equity_path = np.concatenate(
            ([start], start + np.cumsum(sampled, dtype=float))
        )
        max_drawdown_pct, max_drawdown_amount = _drawdown_metrics(equity_path)
        longest_losing, longest_winning = calculate_longest_streaks(sampled)
        final_equity = float(equity_path[-1])
        net_pnl = final_equity - start

        results.append(
            MonteCarloSimulationResult(
                simulation_id=simulation_id,
                final_equity=final_equity,
                net_pnl=net_pnl,
                total_return_pct=net_pnl / start,
                max_drawdown_pct=max_drawdown_pct,
                max_drawdown_amount=max_drawdown_amount,
                longest_losing_streak=longest_losing,
                longest_winning_streak=longest_winning,
                ending_below_starting_equity=final_equity < start,
                ruin_or_below_zero=bool(np.any(equity_path <= 0)),
                trade_pnls=tuple(float(value) for value in sampled),
            )
        )

    return tuple(results)


def summarize_monte_carlo_results(
    simulations: Sequence[MonteCarloSimulationResult],
    *,
    mode: str,
    input_trade_count: int,
    starting_equity: float | Decimal,
    drawdown_thresholds: Iterable[float] = DEFAULT_DRAWDOWN_THRESHOLDS,
) -> MonteCarloSummary:
    """Aggregate Monte Carlo results into downside-focused summary metrics."""

    if not simulations:
        raise ValueError("simulations must not be empty")
    normalized_mode = _validate_mode(mode)
    start = _validate_starting_equity(starting_equity)
    _validate_positive_integer(input_trade_count, "input_trade_count")
    thresholds = _validate_drawdown_thresholds(drawdown_thresholds)

    final_equities = np.asarray([result.final_equity for result in simulations])
    max_drawdowns = np.asarray([result.max_drawdown_pct for result in simulations])
    losing_streaks = np.asarray(
        [result.longest_losing_streak for result in simulations]
    )
    threshold_probabilities = {
        threshold: float(np.mean(max_drawdowns >= threshold))
        for threshold in thresholds
    }

    return MonteCarloSummary(
        mode=normalized_mode,
        num_simulations=len(simulations),
        input_trade_count=input_trade_count,
        simulated_trade_count=len(simulations[0].trade_pnls),
        starting_equity=start,
        mean_final_equity=float(np.mean(final_equities)),
        median_final_equity=float(np.median(final_equities)),
        p05_final_equity=float(np.percentile(final_equities, 5)),
        p95_final_equity=float(np.percentile(final_equities, 95)),
        worst_final_equity=float(np.min(final_equities)),
        best_final_equity=float(np.max(final_equities)),
        mean_max_drawdown_pct=float(np.mean(max_drawdowns)),
        median_max_drawdown_pct=float(np.median(max_drawdowns)),
        p95_max_drawdown_pct=float(np.percentile(max_drawdowns, 95)),
        worst_max_drawdown_pct=float(np.max(max_drawdowns)),
        probability_ending_below_starting_equity=float(
            np.mean([result.ending_below_starting_equity for result in simulations])
        ),
        probability_ruin_or_below_zero=float(
            np.mean([result.ruin_or_below_zero for result in simulations])
        ),
        probability_max_drawdown_gte_10_pct=threshold_probabilities.get(0.10),
        probability_max_drawdown_gte_20_pct=threshold_probabilities.get(0.20),
        probability_max_drawdown_gte_30_pct=threshold_probabilities.get(0.30),
        probability_max_drawdown_gte_40_pct=threshold_probabilities.get(0.40),
        median_longest_losing_streak=float(np.median(losing_streaks)),
        p95_longest_losing_streak=float(np.percentile(losing_streaks, 95)),
        worst_longest_losing_streak=int(np.max(losing_streaks)),
        drawdown_threshold_probabilities=threshold_probabilities,
    )


def run_monte_carlo_validation(
    trade_pnls: pd.DataFrame | pd.Series | Iterable[float | Decimal],
    *,
    starting_equity: float | Decimal,
    num_simulations: int,
    random_seed: int | None = None,
    mode: str = "shuffle",
    drawdown_thresholds: Iterable[float] = DEFAULT_DRAWDOWN_THRESHOLDS,
    num_trades: int | None = None,
) -> MonteCarloValidationResult:
    """Clean input, run simulations, and produce an aggregate validation result."""

    values, pnl_column = _extract_pnl_values(trade_pnls)
    pnls, dropped_nan_count = _coerce_pnls(values)
    thresholds = _validate_drawdown_thresholds(drawdown_thresholds)
    simulations = run_monte_carlo_simulation(
        pnls,
        starting_equity=starting_equity,
        num_simulations=num_simulations,
        random_seed=random_seed,
        mode=mode,
        num_trades=num_trades,
    )
    summary = summarize_monte_carlo_results(
        simulations,
        mode=mode,
        input_trade_count=len(pnls),
        starting_equity=starting_equity,
        drawdown_thresholds=thresholds,
    )
    return MonteCarloValidationResult(
        summary=summary,
        simulations=simulations,
        pnl_column=pnl_column,
        dropped_nan_count=dropped_nan_count,
        random_seed=random_seed,
        drawdown_thresholds=thresholds,
    )


def simulation_results_frame(
    simulations: Sequence[MonteCarloSimulationResult],
) -> pd.DataFrame:
    """Build a metric-only DataFrame for simulation CSV output."""

    return pd.DataFrame(result.to_record() for result in simulations)


def _extract_pnl_values(
    trade_pnls: pd.DataFrame | pd.Series | Iterable[float | Decimal],
) -> tuple[Iterable[object], str | None]:
    if isinstance(trade_pnls, pd.DataFrame):
        pnl_column = next(
            (column for column in SUPPORTED_PNL_COLUMNS if column in trade_pnls.columns),
            None,
        )
        if pnl_column is None:
            supported = ", ".join(SUPPORTED_PNL_COLUMNS)
            raise ValueError(f"missing PnL column; expected one of: {supported}")
        return trade_pnls[pnl_column], pnl_column
    if isinstance(trade_pnls, pd.Series):
        return trade_pnls, trade_pnls.name
    return trade_pnls, None


def _coerce_pnls(values: Iterable[object]) -> tuple[np.ndarray, int]:
    try:
        raw_values = list(values)
    except TypeError as exc:
        raise ValueError("trade PnL input must be an iterable") from exc
    if not raw_values:
        raise ValueError("trade PnL input must not be empty")

    numeric_values: list[float] = []
    dropped_nan_count = 0
    for index, value in enumerate(raw_values):
        if pd.isna(value):
            dropped_nan_count += 1
            continue
        if isinstance(value, (bool, np.bool_)):
            raise ValueError(f"non-numeric trade PnL at position {index}: {value!r}")
        try:
            numeric = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(
                f"non-numeric trade PnL at position {index}: {value!r}"
            ) from exc
        if not np.isfinite(numeric):
            raise ValueError(
                f"trade PnL must be finite at position {index}: {value!r}"
            )
        numeric_values.append(numeric)

    if not numeric_values:
        raise ValueError("trade PnL input contains only NaN values")
    return np.asarray(numeric_values, dtype=float), dropped_nan_count


def _drawdown_metrics(equity_path: Sequence[float]) -> tuple[float, float]:
    equity = np.asarray(equity_path, dtype=float)
    if equity.ndim != 1 or equity.size == 0:
        raise ValueError("equity_path must be a non-empty one-dimensional sequence")
    if not np.all(np.isfinite(equity)):
        raise ValueError("equity_path must contain only finite values")
    if equity[0] <= 0:
        raise ValueError("equity_path must start with positive equity")

    running_peak = np.maximum.accumulate(equity)
    drawdown_amounts = running_peak - equity
    drawdown_percentages = drawdown_amounts / running_peak
    return float(np.max(drawdown_percentages)), float(np.max(drawdown_amounts))


def _validate_starting_equity(value: float | Decimal) -> float:
    try:
        starting_equity = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("starting_equity must be a positive finite number") from exc
    if not np.isfinite(starting_equity) or starting_equity <= 0:
        raise ValueError("starting_equity must be a positive finite number")
    return starting_equity


def _validate_positive_integer(value: int, name: str) -> None:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be a positive integer")
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _validate_mode(mode: str) -> str:
    normalized_mode = str(mode).strip().lower()
    if normalized_mode not in VALID_MODES:
        raise ValueError("mode must be 'shuffle' or 'bootstrap'")
    return normalized_mode


def _validate_drawdown_thresholds(
    thresholds: Iterable[float],
) -> tuple[float, ...]:
    try:
        normalized = tuple(float(threshold) for threshold in thresholds)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("drawdown_thresholds must contain numeric values") from exc
    if any(not np.isfinite(value) or value <= 0 or value >= 1 for value in normalized):
        raise ValueError("drawdown_thresholds must be greater than 0 and less than 1")
    if len(set(normalized)) != len(normalized):
        raise ValueError("drawdown_thresholds must not contain duplicates")
    return normalized
