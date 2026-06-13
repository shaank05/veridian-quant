"""Optional candidate ranking for portfolio backtest signal sequencing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import log1p
from typing import Mapping

import pandas as pd

from veridian_quant.v2.data.models import Signal


CANDIDATE_RANKING_NONE = "none"
CANDIDATE_RANKING_S1_V1 = "s1_v1"
CANDIDATE_RANKING_MODES = (
    CANDIDATE_RANKING_NONE,
    CANDIDATE_RANKING_S1_V1,
)


@dataclass(frozen=True, slots=True)
class _RankedCandidate:
    signal: Signal
    entry_date: date
    original_index: int
    score: float
    score_z: float
    score_liquidity: float
    score_atr: float


def rank_entry_candidates(
    signals: tuple[Signal, ...],
    data_by_symbol: Mapping[str, pd.DataFrame],
    mode: str = CANDIDATE_RANKING_NONE,
) -> tuple[Signal, ...]:
    """Return signals ordered for portfolio processing."""

    if mode not in CANDIDATE_RANKING_MODES:
        raise ValueError(
            f"unsupported candidate ranking mode: {mode}; "
            f"expected one of {', '.join(CANDIDATE_RANKING_MODES)}"
        )
    if mode == CANDIDATE_RANKING_NONE:
        return tuple(sorted(signals, key=_signal_sort_key))

    ordered = tuple(sorted(signals, key=_signal_sort_key))
    candidates = [
        _score_candidate(
            signal=signal,
            data=data_by_symbol.get(signal.symbol),
            original_index=index,
        )
        for index, signal in enumerate(ordered)
    ]
    ranked_by_date: list[Signal] = []
    for entry_date in sorted({candidate.entry_date for candidate in candidates}):
        date_candidates = [
            candidate for candidate in candidates if candidate.entry_date == entry_date
        ]
        ranked = sorted(
            date_candidates,
            key=lambda candidate: (
                -candidate.score,
                candidate.signal.symbol,
                str(candidate.signal.metadata.get("instrument_key", "")),
                candidate.original_index,
            ),
        )
        pool_size = len(ranked)
        for rank, candidate in enumerate(ranked, start=1):
            ranked_by_date.append(
                _with_ranking_metadata(
                    candidate=candidate,
                    mode=mode,
                    rank=rank,
                    pool_size=pool_size,
                )
            )
    return tuple(ranked_by_date)


def _score_candidate(
    signal: Signal,
    data: pd.DataFrame | None,
    original_index: int,
) -> _RankedCandidate:
    entry_date = _candidate_entry_date(signal, data)
    z_score = _number(signal.metadata.get("z_score"))
    score_z = -abs(abs(z_score) - 2.75)
    rolling_volume = _rolling_avg_volume(data, signal.generated_on, window=20)
    score_liquidity = 0.1 * log1p(max(rolling_volume, 0.0))
    atr_pct = _atr_pct(data, signal.generated_on, window=14)
    score_atr = -atr_pct
    score = score_z + score_liquidity + score_atr
    return _RankedCandidate(
        signal=signal,
        entry_date=entry_date,
        original_index=original_index,
        score=score,
        score_z=score_z,
        score_liquidity=score_liquidity,
        score_atr=score_atr,
    )


def _with_ranking_metadata(
    candidate: _RankedCandidate,
    mode: str,
    rank: int,
    pool_size: int,
) -> Signal:
    metadata = dict(candidate.signal.metadata)
    metadata.update(
        {
            "candidate_ranking_mode": mode,
            "candidate_rank": rank,
            "candidate_score": candidate.score,
            "candidate_score_z": candidate.score_z,
            "candidate_score_liquidity": candidate.score_liquidity,
            "candidate_score_atr": candidate.score_atr,
            "candidate_pool_size_for_date": pool_size,
            "candidate_entry_date": candidate.entry_date.isoformat(),
        }
    )
    return Signal(
        symbol=candidate.signal.symbol,
        signal_type=candidate.signal.signal_type,
        generated_on=candidate.signal.generated_on,
        strategy_name=candidate.signal.strategy_name,
        reason=candidate.signal.reason,
        metadata=metadata,
    )


def _signal_sort_key(signal: Signal) -> tuple[date, float, str]:
    return (
        signal.generated_on,
        float(signal.metadata.get("z_score", 0.0)),
        signal.symbol,
    )


def _candidate_entry_date(signal: Signal, data: pd.DataFrame | None) -> date:
    if data is None or data.empty:
        return signal.generated_on
    row_dates = [_row_date(row) for _, row in data.iterrows()]
    future_dates = [row_date for row_date in row_dates if row_date > signal.generated_on]
    if not future_dates:
        return signal.generated_on
    return min(future_dates)


def _rolling_avg_volume(
    data: pd.DataFrame | None,
    signal_date: date,
    window: int,
) -> float:
    if data is None or data.empty or "volume" not in data.columns:
        return 0.0
    rows = _rows_on_or_before(data, signal_date).tail(window)
    if rows.empty:
        return 0.0
    return _number(pd.to_numeric(rows["volume"], errors="coerce").mean())


def _atr_pct(data: pd.DataFrame | None, signal_date: date, window: int) -> float:
    if data is None or data.empty:
        return 0.0
    required = {"high", "low", "close"}
    if any(column not in data.columns for column in required):
        return 0.0
    rows = _rows_on_or_before(data, signal_date).tail(window + 1).copy()
    if rows.empty:
        return 0.0
    high = pd.to_numeric(rows["high"], errors="coerce")
    low = pd.to_numeric(rows["low"], errors="coerce")
    close = pd.to_numeric(rows["close"], errors="coerce")
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = _number(true_range.tail(window).mean())
    latest_close = _number(close.iloc[-1])
    if latest_close <= 0:
        return 0.0
    return atr / latest_close


def _rows_on_or_before(data: pd.DataFrame, signal_date: date) -> pd.DataFrame:
    row_dates = data.apply(_row_date, axis=1)
    return data.loc[row_dates <= signal_date]


def _row_date(row: pd.Series) -> date:
    value = row["date"] if "date" in row.index else row["timestamp"]
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()


def _number(value: object) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(parsed):
        return 0.0
    return float(parsed)
