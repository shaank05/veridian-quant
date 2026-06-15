"""Unit tests for the S2 Markov state-transition strategy."""

from datetime import date
from decimal import Decimal
from statistics import median

import pandas as pd
import pytest

from veridian_quant.v2.backtesting.markov_portfolio_runner import (
    run_s2_markov_portfolio_backtest,
)
from veridian_quant.v2.run_s2_markov_backtest import _parse_args
from veridian_quant.v2.strategies.s2_markov_state_transition import (
    STRATEGY_NAME,
    S2MarkovStateTransitionStrategy,
    build_state_frame,
    generate_s2_markov_signals,
)


def test_state_label_generation_is_deterministic() -> None:
    data = _trend_frame(90)

    first = build_state_frame(data)
    second = build_state_frame(data)

    assert first["state_label"].tolist() == second["state_label"].tolist()


def test_state_label_uses_only_current_and_prior_rows() -> None:
    data = _trend_frame(90)
    modified = data.copy(deep=True)
    modified.loc[80:, ["open", "high", "low", "close"]] = 1000.0

    baseline_state = build_state_frame(data).loc[70, "state_label"]
    modified_state = build_state_frame(modified).loc[70, "state_label"]

    assert baseline_state == modified_state


def test_insufficient_lookback_produces_no_signal() -> None:
    signals = generate_s2_markov_signals(
        symbol="TEST",
        data=_trend_frame(20),
        state_lookback_sessions=20,
        min_state_observations=3,
        forward_return_sessions=2,
    )

    assert signals == []


def test_state_with_insufficient_observations_produces_no_signal() -> None:
    signals = generate_s2_markov_signals(
        symbol="TEST",
        data=_trend_frame(90),
        state_lookback_sessions=252,
        min_state_observations=100,
        forward_return_sessions=2,
    )

    assert signals == []


def test_positive_transition_probability_is_calculated_correctly() -> None:
    signal = _first_signal()

    assert signal.metadata["positive_transition_probability"] == 1.0
    assert signal.metadata["state_observation_count"] >= 3


def test_average_and_median_forward_return_are_calculated_from_prior_occurrences() -> None:
    signal = _first_signal()
    average = signal.metadata["average_forward_return_pct"]
    median = signal.metadata["median_forward_return_pct"]

    assert round(average, 6) == round(median, 6)
    assert round(average, 6) == round(((1.02**2) - 1) * 100, 6)


def test_signal_is_generated_when_thresholds_are_met() -> None:
    signals = _signals()

    assert signals
    assert signals[0].strategy_name == STRATEGY_NAME


def test_signal_is_not_generated_when_probability_threshold_fails() -> None:
    signals = generate_s2_markov_signals(
        symbol="TEST",
        data=_trend_frame(90),
        state_lookback_sessions=252,
        min_state_observations=3,
        forward_return_sessions=2,
        positive_return_threshold_pct=50.0,
        signal_probability_threshold=0.60,
        signal_average_forward_return_threshold_pct=1.0,
    )

    assert signals == []


def test_signal_is_not_generated_when_average_return_threshold_fails() -> None:
    signals = generate_s2_markov_signals(
        symbol="TEST",
        data=_trend_frame(90),
        state_lookback_sessions=252,
        min_state_observations=3,
        forward_return_sessions=2,
        positive_return_threshold_pct=3.0,
        signal_probability_threshold=0.60,
        signal_average_forward_return_threshold_pct=10.0,
    )

    assert signals == []


def test_signal_metadata_contains_required_markov_fields() -> None:
    metadata = _first_signal().metadata

    assert {
        "strategy_family",
        "state_label",
        "state_lookback_sessions",
        "state_observation_count",
        "forward_return_sessions",
        "positive_return_threshold_pct",
        "positive_transition_probability",
        "average_forward_return_pct",
        "median_forward_return_pct",
        "current_5d_return_pct",
        "current_atr_pct",
        "current_drawdown_60d_pct",
        "current_close_vs_60d_low_pct",
    }.issubset(metadata)


def test_no_future_leakage_in_transition_statistics() -> None:
    data = _trend_frame(90)
    modified = data.copy(deep=True)
    modified.loc[75:, ["open", "high", "low", "close"]] = 1.0

    baseline = [
        signal
        for signal in generate_s2_markov_signals(
            symbol="TEST",
            data=data,
            state_lookback_sessions=252,
            min_state_observations=3,
            forward_return_sessions=2,
            positive_return_threshold_pct=3.0,
            signal_probability_threshold=0.60,
            signal_average_forward_return_threshold_pct=1.0,
        )
        if signal.generated_on <= date(2026, 3, 15)
    ]
    changed = [
        signal
        for signal in generate_s2_markov_signals(
            symbol="TEST",
            data=modified,
            state_lookback_sessions=252,
            min_state_observations=3,
            forward_return_sessions=2,
            positive_return_threshold_pct=3.0,
            signal_probability_threshold=0.60,
            signal_average_forward_return_threshold_pct=1.0,
        )
        if signal.generated_on <= date(2026, 3, 15)
    ]

    assert [signal.generated_on for signal in baseline] == [
        signal.generated_on for signal in changed
    ]
    assert [signal.metadata for signal in baseline] == [
        signal.metadata for signal in changed
    ]


def test_cli_parses_s2_arguments() -> None:
    args = _parse_args(
        [
            "--start-date",
            "2020-01-01",
            "--end-date",
            "2026-04-30",
            "--symbols",
            "RELIANCE,TCS",
            "--output-dir",
            "reports/v2/s2",
            "--state-lookback-sessions",
            "126",
            "--min-state-observations",
            "5",
            "--forward-return-sessions",
            "7",
            "--positive-return-threshold-pct",
            "2.5",
            "--signal-probability-threshold",
            "0.55",
            "--signal-average-forward-return-threshold-pct",
            "0.75",
            "--verbosity",
            "quiet",
        ]
    )

    assert args.start_date == date(2020, 1, 1)
    assert args.end_date == date(2026, 4, 30)
    assert args.symbols == "RELIANCE,TCS"
    assert args.state_lookback_sessions == 126
    assert args.min_state_observations == 5
    assert args.forward_return_sessions == 7
    assert args.positive_return_threshold_pct == 2.5
    assert args.signal_probability_threshold == 0.55
    assert args.signal_average_forward_return_threshold_pct == 0.75
    assert args.verbosity == "quiet"


def test_s2_portfolio_run_works_with_synthetic_multi_symbol_data() -> None:
    result = run_s2_markov_portfolio_backtest(
        data_by_symbol={
            "AAA": _trend_frame(90),
            "BBB": _trend_frame(90),
        },
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 31),
        starting_equity=Decimal("100000"),
        risk_per_trade=Decimal("0.01"),
        max_concurrent_positions=2,
        state_lookback_sessions=252,
        min_state_observations=3,
        forward_return_sessions=2,
        positive_return_threshold_pct=3.0,
        signal_probability_threshold=0.60,
        signal_average_forward_return_threshold_pct=1.0,
        round_trip_cost_pct=Decimal("0"),
    )

    assert result.strategy_name == STRATEGY_NAME
    assert result.signals
    assert result.trades
    assert result.trade_pnls
    assert result.ledger is not None


def test_optimized_signal_generation_matches_reference_on_trend_data() -> None:
    _assert_optimized_matches_reference(
        _trend_frame(140),
        forward_return_sessions=2,
        state_lookback_sessions=80,
    )


def test_optimized_signal_generation_matches_reference_on_mixed_state_data() -> None:
    _assert_optimized_matches_reference(
        _mixed_state_frame(220),
        forward_return_sessions=5,
        state_lookback_sessions=60,
        min_state_observations=2,
        signal_probability_threshold=0.40,
        signal_average_forward_return_threshold_pct=-1.0,
    )


def test_optimized_signal_generation_matches_reference_with_missing_rows() -> None:
    data = _mixed_state_frame(180)
    data.loc[75, "close"] = pd.NA

    _assert_optimized_matches_reference(
        data,
        forward_return_sessions=3,
        state_lookback_sessions=70,
        min_state_observations=2,
        signal_probability_threshold=0.40,
        signal_average_forward_return_threshold_pct=-2.0,
    )


def test_performance_smoke_outputs_match_reference_on_moderate_dataset() -> None:
    _assert_optimized_matches_reference(
        _mixed_state_frame(320),
        forward_return_sessions=7,
        state_lookback_sessions=90,
        min_state_observations=2,
        signal_probability_threshold=0.35,
        signal_average_forward_return_threshold_pct=-2.0,
    )


def _first_signal():
    return _signals()[0]


def _signals():
    return generate_s2_markov_signals(
        symbol="TEST",
        data=_trend_frame(90),
        state_lookback_sessions=252,
        min_state_observations=3,
        forward_return_sessions=2,
        positive_return_threshold_pct=3.0,
        signal_probability_threshold=0.60,
        signal_average_forward_return_threshold_pct=1.0,
    )


def _trend_frame(rows: int) -> pd.DataFrame:
    close = 100.0
    output = []
    for index in range(rows):
        session_date = pd.Timestamp("2026-01-01") + pd.Timedelta(days=index)
        close *= 1.02
        output.append(
            {
                "date": session_date,
                "open": close,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1000,
            }
        )
    return pd.DataFrame(output)


def _mixed_state_frame(rows: int) -> pd.DataFrame:
    close = 100.0
    output = []
    for index in range(rows):
        session_date = pd.Timestamp("2026-01-01") + pd.Timedelta(days=index)
        if index % 37 < 8:
            close *= 0.985
        elif index % 37 < 18:
            close *= 1.018
        elif index % 37 < 28:
            close *= 0.997
        else:
            close *= 1.006
        output.append(
            {
                "date": session_date,
                "open": close * 0.995,
                "high": close * 1.015,
                "low": close * 0.985,
                "close": close,
                "volume": 1000 + index,
            }
        )
    return pd.DataFrame(output)


def _assert_optimized_matches_reference(
    data: pd.DataFrame,
    forward_return_sessions: int,
    state_lookback_sessions: int,
    min_state_observations: int = 3,
    positive_return_threshold_pct: float = 3.0,
    signal_probability_threshold: float = 0.60,
    signal_average_forward_return_threshold_pct: float = 1.0,
) -> None:
    strategy = S2MarkovStateTransitionStrategy(
        state_lookback_sessions=state_lookback_sessions,
        min_state_observations=min_state_observations,
        forward_return_sessions=forward_return_sessions,
        positive_return_threshold_pct=positive_return_threshold_pct,
        signal_probability_threshold=signal_probability_threshold,
        signal_average_forward_return_threshold_pct=(
            signal_average_forward_return_threshold_pct
        ),
    )
    optimized = _signal_summaries(strategy.generate_signals("TEST", data))
    reference = _reference_signal_summaries(strategy, "TEST", data)

    assert len(optimized) == len(reference)
    for optimized_row, reference_row in zip(optimized, reference):
        assert optimized_row.keys() == reference_row.keys()
        for key in (
            "generated_on",
            "symbol",
            "state_label",
            "state_observation_count",
        ):
            assert optimized_row[key] == reference_row[key]
        for key in (
            "positive_transition_probability",
            "average_forward_return_pct",
            "median_forward_return_pct",
        ):
            assert optimized_row[key] == pytest.approx(reference_row[key])


def _signal_summaries(signals) -> list[dict[str, object]]:
    return [
        {
            "generated_on": signal.generated_on,
            "symbol": signal.symbol,
            "state_label": signal.metadata["state_label"],
            "state_observation_count": signal.metadata[
                "state_observation_count"
            ],
            "positive_transition_probability": signal.metadata[
                "positive_transition_probability"
            ],
            "average_forward_return_pct": signal.metadata[
                "average_forward_return_pct"
            ],
            "median_forward_return_pct": signal.metadata[
                "median_forward_return_pct"
            ],
        }
        for signal in signals
    ]


def _reference_signal_summaries(
    strategy: S2MarkovStateTransitionStrategy,
    symbol: str,
    data: pd.DataFrame,
) -> list[dict[str, object]]:
    working = data.copy(deep=True).reset_index(drop=True)
    state_frame = build_state_frame(working)
    summaries = []
    for current_index, row in working.iterrows():
        state_label = state_frame.loc[current_index, "state_label"]
        if state_label is None:
            continue
        prior_returns = []
        start_index = max(0, current_index - strategy.state_lookback_sessions)
        for prior_index in range(start_index, current_index):
            forward_index = prior_index + strategy.forward_return_sessions
            if forward_index >= current_index:
                continue
            if state_frame.loc[prior_index, "state_label"] != state_label:
                continue
            entry_close = working["close"].iloc[prior_index]
            exit_close = working["close"].iloc[forward_index]
            if pd.isna(entry_close) or pd.isna(exit_close) or entry_close <= 0:
                continue
            prior_returns.append(float(((exit_close / entry_close) - 1) * 100))
        if len(prior_returns) < strategy.min_state_observations:
            continue

        probability = (
            sum(
                1
                for forward_return in prior_returns
                if forward_return >= strategy.positive_return_threshold_pct
            )
            / len(prior_returns)
        )
        average_return = sum(prior_returns) / len(prior_returns)
        median_return = median(prior_returns)
        if probability < strategy.signal_probability_threshold:
            continue
        if average_return < strategy.signal_average_forward_return_threshold_pct:
            continue

        summaries.append(
            {
                "generated_on": _row_date(row),
                "symbol": symbol,
                "state_label": state_label,
                "state_observation_count": len(prior_returns),
                "positive_transition_probability": probability,
                "average_forward_return_pct": average_return,
                "median_forward_return_pct": median_return,
            }
        )
    return summaries


def _row_date(row: pd.Series) -> date:
    value = row["date"] if "date" in row.index else row["timestamp"]
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()
