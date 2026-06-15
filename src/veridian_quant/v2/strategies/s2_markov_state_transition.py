"""S2 Markov state-transition signal generation for Veridian Quant v2.

This module creates standalone long signal candidates from historical
same-state transition outcomes. It uses only rows available through each signal
date for state construction, and only fully completed prior forward returns for
transition statistics.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from collections import defaultdict, deque
from statistics import median
from types import MappingProxyType

import pandas as pd

from veridian_quant.v2.data.models import Signal, SignalType
from veridian_quant.v2.features.technical import atr


STRATEGY_NAME = "S2_MARKOV_STATE_TRANSITION"


@dataclass(frozen=True, slots=True)
class S2MarkovStateTransitionStrategy:
    """Pure S2 signal generator based on prior same-state outcomes."""

    state_lookback_sessions: int = 252
    min_state_observations: int = 10
    forward_return_sessions: int = 10
    positive_return_threshold_pct: float = 3.0
    signal_probability_threshold: float = 0.60
    signal_average_forward_return_threshold_pct: float = 1.0
    strategy_name: str = STRATEGY_NAME

    @property
    def name(self) -> str:
        """Return the stable S2 strategy identifier."""

        return self.strategy_name

    def generate_signals(self, symbol: str, data: pd.DataFrame) -> list[Signal]:
        """Generate LONG signals from same-state prior transition statistics."""

        _validate_input(data)
        if self.state_lookback_sessions <= 0:
            raise ValueError("state_lookback_sessions must be positive")
        if self.min_state_observations <= 0:
            raise ValueError("min_state_observations must be positive")
        if self.forward_return_sessions <= 0:
            raise ValueError("forward_return_sessions must be positive")

        working = data.copy(deep=True).reset_index(drop=True)
        state_frame = build_state_frame(working)
        close_values = working["close"].tolist()
        row_dates = [_row_date(row) for _, row in working.iterrows()]
        state_labels = state_frame["state_label"].tolist()
        current_5d_returns = state_frame["current_5d_return_pct"].tolist()
        current_atr_values = state_frame["current_atr_pct"].tolist()
        current_drawdowns = state_frame["current_drawdown_60d_pct"].tolist()
        current_low_distances = state_frame[
            "current_close_vs_60d_low_pct"
        ].tolist()
        forward_returns = _forward_returns(
            close_values,
            self.forward_return_sessions,
        )
        observations_by_state: dict[str, deque[tuple[int, float]]] = defaultdict(
            deque
        )

        signals: list[Signal] = []
        for current_index, row in working.iterrows():
            _add_newly_matured_observation(
                current_index=current_index,
                forward_return_sessions=self.forward_return_sessions,
                state_labels=state_labels,
                forward_returns=forward_returns,
                observations_by_state=observations_by_state,
            )
            state_label = state_labels[current_index]
            if state_label is None or pd.isna(state_label):
                continue
            prior_returns = _active_prior_returns(
                observations_by_state=observations_by_state,
                current_index=current_index,
                state_lookback_sessions=self.state_lookback_sessions,
                state_label=state_label,
            )
            if len(prior_returns) < self.min_state_observations:
                continue

            probability = _positive_probability(
                prior_returns,
                self.positive_return_threshold_pct,
            )
            average_return = sum(prior_returns) / len(prior_returns)
            median_return = median(prior_returns)
            if probability < self.signal_probability_threshold:
                continue
            if average_return < self.signal_average_forward_return_threshold_pct:
                continue

            signals.append(
                Signal(
                    symbol=symbol,
                    signal_type=SignalType.LONG,
                    generated_on=row_dates[current_index],
                    strategy_name=self.strategy_name,
                    reason=(
                        "S2 same-state transition statistics met long "
                        "signal thresholds."
                    ),
                    metadata=MappingProxyType(
                        {
                            "strategy_family": STRATEGY_NAME,
                            "state_label": state_label,
                            "state_lookback_sessions": (
                                self.state_lookback_sessions
                            ),
                            "state_observation_count": len(prior_returns),
                            "forward_return_sessions": (
                                self.forward_return_sessions
                            ),
                            "positive_return_threshold_pct": (
                                self.positive_return_threshold_pct
                            ),
                            "positive_transition_probability": probability,
                            "average_forward_return_pct": average_return,
                            "median_forward_return_pct": median_return,
                            "current_5d_return_pct": _blank_nan(
                                current_5d_returns[current_index]
                            ),
                            "current_atr_pct": _blank_nan(
                                current_atr_values[current_index]
                            ),
                            "current_drawdown_60d_pct": _blank_nan(
                                current_drawdowns[current_index]
                            ),
                            "current_close_vs_60d_low_pct": _blank_nan(
                                current_low_distances[current_index]
                            ),
                            "close": float(row["close"]),
                        }
                    ),
                )
            )
        return signals


def generate_s2_markov_signals(
    symbol: str,
    data: pd.DataFrame,
    state_lookback_sessions: int = 252,
    min_state_observations: int = 10,
    forward_return_sessions: int = 10,
    positive_return_threshold_pct: float = 3.0,
    signal_probability_threshold: float = 0.60,
    signal_average_forward_return_threshold_pct: float = 1.0,
) -> list[Signal]:
    """Generate S2 signals using the default strategy class."""

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
    return strategy.generate_signals(symbol=symbol, data=data)


def build_state_frame(data: pd.DataFrame) -> pd.DataFrame:
    """Return deterministic S2 state features and labels for each row."""

    _validate_input(data)
    close = data["close"]
    atr_pct = (atr(data, 14) / close) * 100
    rolling_60d_high = close.rolling(window=60, min_periods=60).max()
    rolling_60d_low = close.rolling(window=60, min_periods=60).min()
    return_5d = ((close / close.shift(5)) - 1) * 100
    drawdown_60d = ((close / rolling_60d_high) - 1) * 100
    close_vs_60d_low = ((close / rolling_60d_low) - 1) * 100

    state_labels = [
        _state_label(
            return_5d.iloc[index],
            atr_pct.iloc[index],
            drawdown_60d.iloc[index],
            close_vs_60d_low.iloc[index],
        )
        for index in range(len(data))
    ]
    return pd.DataFrame(
        {
            "current_5d_return_pct": return_5d,
            "current_atr_pct": atr_pct,
            "current_drawdown_60d_pct": drawdown_60d,
            "current_close_vs_60d_low_pct": close_vs_60d_low,
            "state_label": state_labels,
        },
        index=data.index,
    )


def _prior_same_state_forward_returns(
    state_frame: pd.DataFrame,
    close: pd.Series,
    current_index: int,
    state_label: str,
    state_lookback_sessions: int,
    forward_return_sessions: int,
) -> list[float]:
    """Return fully known prior same-state forward returns."""

    start_index = max(0, current_index - state_lookback_sessions)
    prior_returns: list[float] = []
    for prior_index in range(start_index, current_index):
        forward_index = prior_index + forward_return_sessions
        if forward_index >= current_index:
            continue
        if state_frame.loc[prior_index, "state_label"] != state_label:
            continue
        entry_close = close.iloc[prior_index]
        exit_close = close.iloc[forward_index]
        if pd.isna(entry_close) or pd.isna(exit_close) or entry_close <= 0:
            continue
        prior_returns.append(float(((exit_close / entry_close) - 1) * 100))
    return prior_returns


def _forward_returns(
    close_values: list[object],
    forward_return_sessions: int,
) -> list[float | None]:
    """Return valid forward return percentages for each possible prior row."""

    returns: list[float | None] = [None] * len(close_values)
    for prior_index, entry_close in enumerate(close_values):
        forward_index = prior_index + forward_return_sessions
        if forward_index >= len(close_values):
            continue
        exit_close = close_values[forward_index]
        if pd.isna(entry_close) or pd.isna(exit_close) or entry_close <= 0:
            continue
        returns[prior_index] = float(((exit_close / entry_close) - 1) * 100)
    return returns


def _add_newly_matured_observation(
    current_index: int,
    forward_return_sessions: int,
    state_labels: list[str | None],
    forward_returns: list[float | None],
    observations_by_state: dict[str, deque[tuple[int, float]]],
) -> None:
    """Add the newest prior observation whose forward outcome is known."""

    prior_index = current_index - forward_return_sessions - 1
    if prior_index < 0:
        return
    state_label = state_labels[prior_index]
    forward_return = forward_returns[prior_index]
    if state_label is None or pd.isna(state_label) or forward_return is None:
        return
    observations_by_state[state_label].append((prior_index, forward_return))


def _active_prior_returns(
    observations_by_state: dict[str, deque[tuple[int, float]]],
    current_index: int,
    state_lookback_sessions: int,
    state_label: str,
) -> list[float]:
    """Return same-state prior returns inside the current lookback window."""

    observations = observations_by_state[state_label]
    oldest_valid_index = current_index - state_lookback_sessions
    while observations and observations[0][0] < oldest_valid_index:
        observations.popleft()
    return [forward_return for _, forward_return in observations]


def _state_label(
    return_5d: object,
    atr_pct: object,
    drawdown_60d: object,
    close_vs_60d_low: object,
) -> str | None:
    if any(pd.isna(value) for value in (return_5d, atr_pct, drawdown_60d, close_vs_60d_low)):
        return None
    return "|".join(
        (
            _return_bucket(return_5d),
            _volatility_bucket(atr_pct),
            _drawdown_bucket(drawdown_60d),
            _low_distance_bucket(close_vs_60d_low),
        )
    )


def _return_bucket(value: object) -> str:
    decimal = _to_decimal(value)
    if decimal <= Decimal("-5"):
        return "RET_STRONG_DOWN"
    if decimal < Decimal("-1"):
        return "RET_DOWN"
    if decimal <= Decimal("1"):
        return "RET_FLAT"
    if decimal < Decimal("5"):
        return "RET_UP"
    return "RET_STRONG_UP"


def _volatility_bucket(value: object) -> str:
    decimal = _to_decimal(value)
    if decimal < Decimal("2"):
        return "VOL_LOW"
    if decimal < Decimal("5"):
        return "VOL_MID"
    return "VOL_HIGH"


def _drawdown_bucket(value: object) -> str:
    decimal = _to_decimal(value)
    if decimal >= Decimal("-10"):
        return "DD_SHALLOW"
    if decimal >= Decimal("-25"):
        return "DD_MID"
    return "DD_DEEP"


def _low_distance_bucket(value: object) -> str:
    decimal = _to_decimal(value)
    if decimal <= Decimal("5"):
        return "LOW_NEAR"
    if decimal <= Decimal("20"):
        return "LOW_MID_RANGE"
    return "LOW_FAR_FROM_LOW"


def _positive_probability(
    forward_returns: list[float],
    positive_return_threshold_pct: float,
) -> float:
    positives = sum(
        1
        for forward_return in forward_returns
        if forward_return >= positive_return_threshold_pct
    )
    return positives / len(forward_returns)


def _validate_input(data: pd.DataFrame) -> None:
    required = ["open", "high", "low", "close"]
    missing = [column for column in required if column not in data.columns]
    if "date" not in data.columns and "timestamp" not in data.columns:
        missing.append("date or timestamp")
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")


def _row_date(row: pd.Series) -> date:
    value = row["date"] if "date" in row.index else row["timestamp"]
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()


def _blank_nan(value: object) -> object:
    if pd.isna(value):
        return None
    return value


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
