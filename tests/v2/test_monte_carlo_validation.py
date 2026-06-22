"""Tests for standalone Monte Carlo robustness validation."""

from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from veridian_quant.v2.validation.monte_carlo import (
    calculate_equity_path,
    calculate_longest_streaks,
    calculate_max_drawdown,
    run_monte_carlo_simulation,
    run_monte_carlo_validation,
)


def test_calculate_equity_path_on_known_sequence() -> None:
    path = calculate_equity_path([100, -40, Decimal("25.5")], Decimal("1000"))

    assert path.tolist() == [1000.0, 1100.0, 1060.0, 1085.5]


def test_calculate_max_drawdown_on_known_sequence() -> None:
    assert calculate_max_drawdown([1000, 1200, 900, 990]) == pytest.approx(0.25)


def test_calculate_longest_losing_and_winning_streaks() -> None:
    losses, wins = calculate_longest_streaks([1, 2, -1, -2, -3, 0, 4, 5, 6])

    assert losses == 3
    assert wins == 3


def test_shuffle_preserves_exact_values_for_every_simulation() -> None:
    original = [100.0, -50.0, 25.0, -10.0]
    results = run_monte_carlo_simulation(
        original,
        starting_equity=1000,
        num_simulations=10,
        random_seed=7,
        mode="shuffle",
    )

    assert all(sorted(result.trade_pnls) == sorted(original) for result in results)
    assert all(result.final_equity == 1065.0 for result in results)


def test_bootstrap_samples_with_replacement_and_requested_length() -> None:
    results = run_monte_carlo_simulation(
        [10.0, -5.0],
        starting_equity=1000,
        num_simulations=8,
        random_seed=3,
        mode="bootstrap",
        num_trades=7,
    )

    assert all(len(result.trade_pnls) == 7 for result in results)
    assert all(set(result.trade_pnls) <= {10.0, -5.0} for result in results)
    assert all(len(result.trade_pnls) > len(set(result.trade_pnls)) for result in results)


def test_fixed_seed_is_reproducible() -> None:
    kwargs = dict(
        starting_equity=1000,
        num_simulations=12,
        random_seed=41,
        mode="bootstrap",
    )

    first = run_monte_carlo_simulation([10, -5, 20, -15], **kwargs)
    second = run_monte_carlo_simulation([10, -5, 20, -15], **kwargs)

    assert first == second


def test_different_seeds_change_sampled_sequences() -> None:
    first = run_monte_carlo_simulation(
        [10, -5, 20, -15],
        starting_equity=1000,
        num_simulations=5,
        random_seed=1,
        mode="bootstrap",
    )
    second = run_monte_carlo_simulation(
        [10, -5, 20, -15],
        starting_equity=1000,
        num_simulations=5,
        random_seed=2,
        mode="bootstrap",
    )

    assert [result.trade_pnls for result in first] != [
        result.trade_pnls for result in second
    ]


def test_summary_percentiles_and_loss_probability_are_calculated() -> None:
    result = run_monte_carlo_validation(
        [100, -200],
        starting_equity=1000,
        num_simulations=100,
        random_seed=19,
        mode="bootstrap",
    )
    summary = result.summary

    assert summary.p05_final_equity <= summary.median_final_equity
    assert summary.median_final_equity <= summary.p95_final_equity
    assert 0 < summary.probability_ending_below_starting_equity < 1


def test_drawdown_threshold_probabilities_and_ruin_are_calculated() -> None:
    result = run_monte_carlo_validation(
        [-60],
        starting_equity=100,
        num_simulations=4,
        random_seed=1,
        mode="shuffle",
    )
    summary = result.summary

    assert summary.probability_max_drawdown_gte_10_pct == 1.0
    assert summary.probability_max_drawdown_gte_40_pct == 1.0
    assert summary.probability_ruin_or_below_zero == 0.0

    ruined = run_monte_carlo_validation(
        [-100],
        starting_equity=100,
        num_simulations=2,
        mode="shuffle",
    )
    assert ruined.summary.probability_ruin_or_below_zero == 1.0


def test_dataframe_column_priority() -> None:
    frame = pd.DataFrame(
        {"pnl": [1], "trade_net_pnl": [2], "net_pnl": [3]}
    )

    result = run_monte_carlo_validation(
        frame,
        starting_equity=100,
        num_simulations=1,
        mode="shuffle",
    )

    assert result.pnl_column == "net_pnl"
    assert result.simulations[0].trade_pnls == (3.0,)


def test_nan_values_are_dropped_and_counted() -> None:
    result = run_monte_carlo_validation(
        pd.Series([10.0, np.nan, -2.0], name="pnl"),
        starting_equity=100,
        num_simulations=1,
        mode="shuffle",
    )

    assert result.dropped_nan_count == 1
    assert result.summary.input_trade_count == 2


@pytest.mark.parametrize("values", [[], [np.nan, np.nan]])
def test_empty_or_all_nan_input_raises(values: list[float]) -> None:
    with pytest.raises(ValueError, match="empty|only NaN"):
        run_monte_carlo_validation(
            values,
            starting_equity=100,
            num_simulations=1,
        )


def test_missing_pnl_column_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="missing PnL column"):
        run_monte_carlo_validation(
            pd.DataFrame({"gross_pnl": [1.0]}),
            starting_equity=100,
            num_simulations=1,
        )


def test_non_numeric_pnl_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="non-numeric trade PnL"):
        run_monte_carlo_validation(
            [1.0, "bad"],
            starting_equity=100,
            num_simulations=1,
        )


@pytest.mark.parametrize("starting_equity", [0, -1, np.inf])
def test_starting_equity_must_be_positive_finite(starting_equity: float) -> None:
    with pytest.raises(ValueError, match="starting_equity"):
        run_monte_carlo_validation(
            [1.0],
            starting_equity=starting_equity,
            num_simulations=1,
        )


@pytest.mark.parametrize("num_simulations", [0, -1, 1.5, True])
def test_simulation_count_must_be_positive_integer(num_simulations: object) -> None:
    with pytest.raises(ValueError, match="num_simulations"):
        run_monte_carlo_validation(
            [1.0],
            starting_equity=100,
            num_simulations=num_simulations,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("thresholds", [[0], [1], [-0.1], [1.1], [np.nan]])
def test_drawdown_thresholds_must_be_between_zero_and_one(
    thresholds: list[float],
) -> None:
    with pytest.raises(ValueError, match="greater than 0 and less than 1"):
        run_monte_carlo_validation(
            [1.0],
            starting_equity=100,
            num_simulations=1,
            drawdown_thresholds=thresholds,
        )


def test_invalid_mode_raises() -> None:
    with pytest.raises(ValueError, match="mode"):
        run_monte_carlo_validation(
            [1.0],
            starting_equity=100,
            num_simulations=1,
            mode="invalid",
        )


@pytest.mark.parametrize("num_trades", [0, -1])
def test_bootstrap_num_trades_must_be_positive(num_trades: int) -> None:
    with pytest.raises(ValueError, match="num_trades"):
        run_monte_carlo_validation(
            [1.0],
            starting_equity=100,
            num_simulations=1,
            mode="bootstrap",
            num_trades=num_trades,
        )
