"""Tests for the ranked S5 momentum portfolio runner."""

from datetime import date
from types import MappingProxyType

import numpy as np
import pandas as pd
import pytest

from veridian_quant.v2.backtesting.portfolio_runner import PortfolioBacktestResult
from veridian_quant.v2.backtesting.s5_portfolio_runner import (
    S5_CANDIDATE_RANKING_MODE,
    run_s5_portfolio_backtest,
)
from veridian_quant.v2.data.models import Signal, SignalType
from veridian_quant.v2.strategies.s5_relative_strength_momentum_rotation import (
    S5_DUAL_MOMENTUM_63_126D_V1,
    S5_SIMPLE_RS_126D_V1,
    S5_VOL_ADJUSTED_RS_V1,
    STRATEGY_NAME,
)


def test_runner_accepts_each_s5_variant(monkeypatch) -> None:
    _patch_signals(monkeypatch, {})

    for variant in (
        S5_SIMPLE_RS_126D_V1,
        S5_DUAL_MOMENTUM_63_126D_V1,
        S5_VOL_ADJUSTED_RS_V1,
    ):
        result = _run({"AAA": _trade_frame()}, strategy_variant=variant)

        assert result.strategy_variant == variant
        assert result.candidate_ranking_mode == S5_CANDIDATE_RANKING_MODE


def test_invalid_variant_fails_before_signal_generation(monkeypatch) -> None:
    called = False

    def fake_generate(*args, **kwargs):
        nonlocal called
        called = True
        return ()

    monkeypatch.setattr(
        "veridian_quant.v2.backtesting.s5_portfolio_runner."
        "generate_s5_momentum_signals",
        fake_generate,
    )

    with pytest.raises(ValueError, match="unknown S5 strategy variant"):
        _run({"AAA": _trade_frame()}, strategy_variant="UNKNOWN")

    assert called is False


def test_same_day_candidates_are_ranked_descending(monkeypatch) -> None:
    signal_date = date(2026, 1, 15)
    _patch_signals(
        monkeypatch,
        {
            "AAA": [_signal("AAA", signal_date, 0.2)],
            "BBB": [_signal("BBB", signal_date, 0.9)],
            "CCC": [_signal("CCC", signal_date, 0.5)],
        },
    )

    result = _run({symbol: _trade_frame() for symbol in ("AAA", "BBB", "CCC")})

    assert [signal.symbol for signal in result.signals] == ["BBB", "CCC", "AAA"]
    assert [signal.metadata["candidate_rank"] for signal in result.signals] == [
        1,
        2,
        3,
    ]


def test_capacity_prefers_highest_rank_score(monkeypatch) -> None:
    signal_date = date(2026, 1, 15)
    _patch_signals(
        monkeypatch,
        {
            "LOW": [_signal("LOW", signal_date, 0.1)],
            "HIGH": [_signal("HIGH", signal_date, 0.9)],
        },
    )

    result = _run(
        {"LOW": _trade_frame(), "HIGH": _trade_frame()},
        max_concurrent_positions=1,
    )

    assert [trade.symbol for trade in result.trades] == ["HIGH"]
    rejected = {item.symbol: item.reason for item in result.rejected_signals}
    assert rejected == {"LOW": "PORTFOLIO_CAPACITY_FULL"}
    assert result.trades[0].candidate_score == pytest.approx(0.9)
    assert result.trades[0].candidate_rank == 1


def test_rank_score_ties_break_by_symbol(monkeypatch) -> None:
    signal_date = date(2026, 1, 15)
    _patch_signals(
        monkeypatch,
        {
            "ZZZ": [_signal("ZZZ", signal_date, 0.5)],
            "AAA": [_signal("AAA", signal_date, 0.5)],
        },
    )

    result = _run({"ZZZ": _trade_frame(), "AAA": _trade_frame()})

    assert [signal.symbol for signal in result.signals] == ["AAA", "ZZZ"]


@pytest.mark.parametrize("rank_score", [None, np.nan, np.inf, "bad"])
def test_invalid_rank_score_is_rejected(monkeypatch, rank_score: object) -> None:
    _patch_signals(
        monkeypatch,
        {"AAA": [_signal("AAA", date(2026, 1, 15), rank_score)]},
    )

    result = _run({"AAA": _trade_frame()})

    assert result.trades == ()
    assert _rejection_reasons(result) == ["INVALID_RANK_SCORE"]
    assert result.rejected_signals[0].candidate_ranking_mode == (
        S5_CANDIDATE_RANKING_MODE
    )


def test_active_and_capacity_rejections_remain_distinct(monkeypatch) -> None:
    _patch_signals(
        monkeypatch,
        {
            "AAA": [
                _signal("AAA", date(2026, 1, 15), 0.9),
                _signal("AAA", date(2026, 1, 16), 0.8),
            ],
            "BBB": [_signal("BBB", date(2026, 1, 16), 0.7)],
        },
    )

    result = _run(
        {"AAA": _trade_frame(exit_style="time"), "BBB": _trade_frame()},
        max_concurrent_positions=1,
    )

    reasons = {(item.symbol, item.reason) for item in result.rejected_signals}
    assert ("AAA", "ACTIVE_SYMBOL_TRADE_EXISTS") in reasons
    assert ("BBB", "PORTFOLIO_CAPACITY_FULL") in reasons


def test_real_s5_signal_produces_trade() -> None:
    data = _real_s5_trade_frame()

    result = run_s5_portfolio_backtest(
        {"AAA": data},
        start_date=data.loc[0, "date"].date(),
        end_date=data.loc[len(data) - 1, "date"].date(),
    )

    assert result.signals
    assert len(result.trades) == 1
    assert len(result.trade_pnls) == 1
    assert result.trades[0].strategy_name == STRATEGY_NAME


def test_runner_respects_max_concurrent_positions(monkeypatch) -> None:
    signal_date = date(2026, 1, 15)
    _patch_signals(
        monkeypatch,
        {
            symbol: [_signal(symbol, signal_date, score)]
            for symbol, score in (("AAA", 0.9), ("BBB", 0.8), ("CCC", 0.7))
        },
    )

    result = _run(
        {symbol: _trade_frame() for symbol in ("AAA", "BBB", "CCC")},
        max_concurrent_positions=2,
    )

    assert {trade.symbol for trade in result.trades} == {"AAA", "BBB"}
    assert _rejection_reasons(result) == ["PORTFOLIO_CAPACITY_FULL"]


def test_input_dataframes_are_not_mutated(monkeypatch) -> None:
    _patch_signals(
        monkeypatch,
        {"AAA": [_signal("AAA", date(2026, 1, 15), 0.8)]},
    )
    data_by_symbol = {"AAA": _trade_frame()}
    originals = {
        symbol: frame.copy(deep=True) for symbol, frame in data_by_symbol.items()
    }

    _run(data_by_symbol)

    for symbol, original in originals.items():
        pd.testing.assert_frame_equal(data_by_symbol[symbol], original)


def test_runner_calls_only_s5_signal_generator(monkeypatch) -> None:
    observed: list[str] = []

    def fake_generate(symbol: str, data: pd.DataFrame, config):
        observed.append(config.variant)
        return ()

    monkeypatch.setattr(
        "veridian_quant.v2.backtesting.s5_portfolio_runner."
        "generate_s5_momentum_signals",
        fake_generate,
    )

    result = _run(
        {"AAA": _trade_frame()},
        strategy_variant=S5_VOL_ADJUSTED_RS_V1,
    )

    assert observed == [S5_VOL_ADJUSTED_RS_V1]
    assert result.strategy_name == STRATEGY_NAME


def test_result_uses_shared_portfolio_result_structure(monkeypatch) -> None:
    _patch_signals(monkeypatch, {})

    result = _run({"AAA": _trade_frame()})

    assert isinstance(result, PortfolioBacktestResult)
    assert result.ledger is not None
    assert result.symbols == ("AAA",)


def _run(data_by_symbol: dict[str, pd.DataFrame], **kwargs) -> PortfolioBacktestResult:
    return run_s5_portfolio_backtest(
        data_by_symbol,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        **kwargs,
    )


def _patch_signals(monkeypatch, signals_by_symbol: dict[str, list[Signal]]) -> None:
    def fake_generate(symbol: str, data: pd.DataFrame, config):
        return tuple(signals_by_symbol.get(symbol, []))

    monkeypatch.setattr(
        "veridian_quant.v2.backtesting.s5_portfolio_runner."
        "generate_s5_momentum_signals",
        fake_generate,
    )


def _signal(symbol: str, signal_date: date, rank_score: object) -> Signal:
    return Signal(
        symbol=symbol,
        signal_type=SignalType.LONG,
        generated_on=signal_date,
        strategy_name=STRATEGY_NAME,
        reason="patched S5 signal",
        metadata=MappingProxyType(
            {
                "strategy_family": STRATEGY_NAME,
                "strategy_variant": S5_SIMPLE_RS_126D_V1,
                "variant": S5_SIMPLE_RS_126D_V1,
                "rank_score": rank_score,
            }
        ),
    )


def _rejection_reasons(result: PortfolioBacktestResult) -> list[str]:
    return [item.reason for item in result.rejected_signals]


def _trade_frame(rows: int = 31, exit_style: str = "target") -> pd.DataFrame:
    close = np.full(rows, 100.0)
    high = np.full(rows, 101.0)
    low = np.full(rows, 99.0)
    open_ = np.full(rows, 100.0)
    if exit_style == "target":
        high[16] = 120.0
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=rows, freq="D"),
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": np.full(rows, 1000),
        }
    )


def _real_s5_trade_frame(rows: int = 230) -> pd.DataFrame:
    close = 100.0 + 0.5 * np.arange(rows) + 0.1 * np.sin(np.arange(rows))
    high = close + 1.0
    high[201] = close[201] + 20.0
    return pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=rows, freq="D"),
            "open": close,
            "high": high,
            "low": close - 1.0,
            "close": close,
            "volume": np.full(rows, 1000),
        }
    )
