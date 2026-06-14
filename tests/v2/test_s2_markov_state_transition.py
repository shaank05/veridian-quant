"""Unit tests for the S2 Markov state-transition strategy."""

from datetime import date
from decimal import Decimal

import pandas as pd

from veridian_quant.v2.backtesting.markov_portfolio_runner import (
    run_s2_markov_portfolio_backtest,
)
from veridian_quant.v2.run_s2_markov_backtest import _parse_args
from veridian_quant.v2.strategies.s2_markov_state_transition import (
    STRATEGY_NAME,
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
