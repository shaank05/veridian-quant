"""Tests for the S4 compression breakout portfolio runner."""

from datetime import date
from decimal import Decimal
from types import MappingProxyType

import pandas as pd
import pytest

from veridian_quant.v2.backtesting.portfolio_runner import PortfolioBacktestResult
from veridian_quant.v2.backtesting.s4_portfolio_runner import (
    run_s4_portfolio_backtest,
)
from veridian_quant.v2.backtesting.trade import ExitReason
from veridian_quant.v2.data.models import Signal, SignalType
from veridian_quant.v2.strategies.s4_entropy_volatility_compression_breakout import (
    S4_ATR_COMPRESSION_BREAKOUT_V1,
    S4_ENTROPY_GATED_BREAKOUT_V1,
    S4_RANGE_COMPRESSION_BREAKOUT_V1,
    STRATEGY_NAME,
)


def test_runner_accepts_each_s4_variant_parameter() -> None:
    for variant in (
        S4_ATR_COMPRESSION_BREAKOUT_V1,
        S4_RANGE_COMPRESSION_BREAKOUT_V1,
        S4_ENTROPY_GATED_BREAKOUT_V1,
    ):
        result = _run_real_s4(_s4_trade_frame(), strategy_variant=variant)

        assert result.strategy_variant == variant
        assert result.candidate_ranking_mode == "none"
        assert result.strategy_name == STRATEGY_NAME


def test_runner_validates_unknown_variant_before_signal_generation(monkeypatch) -> None:
    called = False

    def fake_generate(*args, **kwargs):
        nonlocal called
        called = True
        return ()

    monkeypatch.setattr(
        "veridian_quant.v2.backtesting.s4_portfolio_runner."
        "generate_s4_entropy_volatility_compression_breakout_signals",
        fake_generate,
    )

    with pytest.raises(ValueError, match="unknown S4 strategy variant"):
        _run_real_s4(_s4_trade_frame(), strategy_variant="UNKNOWN")

    assert called is False


def test_runner_uses_s4_signal_generation_and_completes_trade() -> None:
    result = _run_real_s4(_s4_trade_frame())

    assert result.signals
    assert len(result.trades) == 1
    assert len(result.trade_pnls) == 1
    assert result.trades[0].strategy_name == STRATEGY_NAME
    assert result.trade_pnls[0].net_pnl != Decimal("0")


def test_rejects_capacity_signals_when_max_concurrent_positions_reached(
    monkeypatch,
) -> None:
    _patch_signals(
        monkeypatch,
        {
            "AAA": [_signal("AAA", date(2026, 1, 15))],
            "BBB": [_signal("BBB", date(2026, 1, 15))],
        },
    )

    result = run_s4_portfolio_backtest(
        {"AAA": _trade_frame(), "BBB": _trade_frame()},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        max_concurrent_positions=1,
    )

    assert _rejection_reasons(result) == ["PORTFOLIO_CAPACITY_FULL"]


def test_rejects_same_symbol_active_trade_conflict(monkeypatch) -> None:
    _patch_signals(
        monkeypatch,
        {
            "AAA": [
                _signal("AAA", date(2026, 1, 15)),
                _signal("AAA", date(2026, 1, 16)),
            ],
        },
    )

    result = run_s4_portfolio_backtest(
        {"AAA": _trade_frame(exit_style="time")},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        max_holding_sessions=5,
    )

    assert _rejection_reasons(result) == ["ACTIVE_SYMBOL_TRADE_EXISTS"]


def test_preserves_pre_start_lookback_for_s4_indicators() -> None:
    result = _run_real_s4(
        _s4_trade_frame(),
        start_date=date(2026, 1, 6),
        end_date=date(2026, 1, 10),
    )

    assert [signal.generated_on for signal in result.signals] == [date(2026, 1, 6)]
    assert result.signals[0].metadata["prior_atr_percentile"] <= 0.20


def test_does_not_use_signals_before_start_date(monkeypatch) -> None:
    _patch_signals(
        monkeypatch,
        {
            "AAA": [_signal("AAA", date(2026, 1, 10))],
        },
    )

    result = run_s4_portfolio_backtest(
        {"AAA": _trade_frame()},
        start_date=date(2026, 1, 11),
        end_date=date(2026, 1, 31),
    )

    assert result.signals == ()
    assert result.trades == ()


def test_does_not_use_setup_or_exit_data_after_end_date(monkeypatch) -> None:
    _patch_signals(
        monkeypatch,
        {
            "AAA": [_signal("AAA", date(2026, 1, 15))],
        },
    )
    data = _trade_frame(exit_style="target")
    data.loc[16, "high"] = 101.0
    data.loc[17, "high"] = 130.0

    result = run_s4_portfolio_backtest(
        {"AAA": data},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 17),
        max_holding_sessions=5,
    )

    assert len(result.trades) == 1
    assert result.trades[0].exit_date == date(2026, 1, 17)
    assert result.trades[0].exit_reason == ExitReason.BACKTEST_END


def test_input_dataframes_are_not_mutated(monkeypatch) -> None:
    _patch_signals(
        monkeypatch,
        {
            "AAA": [_signal("AAA", date(2026, 1, 15))],
        },
    )
    data_by_symbol = {"AAA": _trade_frame()}
    originals = {symbol: data.copy(deep=True) for symbol, data in data_by_symbol.items()}

    run_s4_portfolio_backtest(
        data_by_symbol,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    for symbol, original in originals.items():
        pd.testing.assert_frame_equal(data_by_symbol[symbol], original)


def test_returns_shared_portfolio_backtest_result_structure() -> None:
    result = _run_real_s4(_s4_trade_frame())

    assert isinstance(result, PortfolioBacktestResult)
    assert result.symbols == ("AAA",)
    assert isinstance(result.signals, tuple)
    assert isinstance(result.rejected_signals, tuple)
    assert result.ledger is not None


def test_records_rejected_signals_with_clear_reasons(monkeypatch) -> None:
    _patch_signals(
        monkeypatch,
        {
            "AAA": [_signal("AAA", date(2026, 1, 20))],
        },
    )

    result = run_s4_portfolio_backtest(
        {"AAA": _trade_frame(rows=20)},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 20),
    )

    assert _rejection_reasons(result) == ["SETUP_UNAVAILABLE"]


def test_applies_ledger_equity_updates_after_completed_trades(monkeypatch) -> None:
    _patch_signals(
        monkeypatch,
        {
            "AAA": [_signal("AAA", date(2026, 1, 15))],
        },
    )

    result = run_s4_portfolio_backtest(
        {"AAA": _trade_frame(exit_style="target")},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert len(result.trade_pnls) == 1
    assert result.ending_equity != result.starting_equity
    assert result.ledger is not None
    assert result.ledger.current_equity == result.ending_equity


def test_preserves_pct_metadata_values_as_percentage_points() -> None:
    result = _run_real_s4(_s4_trade_frame())
    metadata = result.signals[0].metadata

    assert metadata["atr_pct"] > 1.0
    assert metadata["range_pct"] > 1.0
    assert 0.0 <= metadata["prior_atr_percentile"] <= 1.0


def test_selected_s4_variant_is_passed_into_signal_generation(monkeypatch) -> None:
    observed_variants = []

    def fake_generate(symbol: str, data: pd.DataFrame, **kwargs):
        observed_variants.append(kwargs["variant"])
        return (_signal(symbol, date(2026, 1, 15)),)

    monkeypatch.setattr(
        "veridian_quant.v2.backtesting.s4_portfolio_runner."
        "generate_s4_entropy_volatility_compression_breakout_signals",
        fake_generate,
    )

    run_s4_portfolio_backtest(
        {"AAA": _trade_frame()},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        strategy_variant=S4_RANGE_COMPRESSION_BREAKOUT_V1,
    )

    assert observed_variants == [S4_RANGE_COMPRESSION_BREAKOUT_V1]


def _run_real_s4(
    data: pd.DataFrame,
    strategy_variant: str = S4_ATR_COMPRESSION_BREAKOUT_V1,
    start_date: date = date(2026, 1, 1),
    end_date: date = date(2026, 1, 31),
) -> PortfolioBacktestResult:
    return run_s4_portfolio_backtest(
        {"AAA": data},
        start_date=start_date,
        end_date=end_date,
        strategy_variant=strategy_variant,
        atr_window=1,
        range_window=1,
        breakout_window=3,
        percentile_window=3,
        entropy_window=3,
    )


def _patch_signals(monkeypatch, signals_by_symbol: dict[str, list[Signal]]) -> None:
    def fake_generate(symbol: str, data: pd.DataFrame, **kwargs):
        return tuple(signals_by_symbol.get(symbol, []))

    monkeypatch.setattr(
        "veridian_quant.v2.backtesting.s4_portfolio_runner."
        "generate_s4_entropy_volatility_compression_breakout_signals",
        fake_generate,
    )


def _signal(symbol: str, signal_date: date) -> Signal:
    return Signal(
        symbol=symbol,
        signal_type=SignalType.LONG,
        generated_on=signal_date,
        strategy_name=STRATEGY_NAME,
        reason="patched S4 signal",
        metadata=MappingProxyType(
            {
                "strategy_family": STRATEGY_NAME,
                "strategy_variant": S4_ATR_COMPRESSION_BREAKOUT_V1,
                "s4_variant": S4_ATR_COMPRESSION_BREAKOUT_V1,
                "atr_pct": 2.0,
            }
        ),
    )


def _rejection_reasons(result: PortfolioBacktestResult) -> list[str]:
    return [rejected.reason for rejected in result.rejected_signals]


def _s4_trade_frame() -> pd.DataFrame:
    highs = [12.0, 12.0, 20.0, 20.0, 10.2, 30.0, 40.0, 41.0]
    lows = [10.0, 10.0, 10.0, 10.0, 9.8, 9.0, 21.0, 29.0]
    closes = [11.0, 11.0, 10.0, 10.0, 10.0, 21.0, 30.0, 35.0]
    opens = closes.copy()
    opens[6] = 22.0
    return _frame_from_ohlc(highs=highs, lows=lows, closes=closes, opens=opens)


def _trade_frame(rows: int = 31, exit_style: str = "target") -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="D")
    close = [100.0 for _ in range(rows)]
    high = [101.0 for _ in range(rows)]
    low = [99.0 for _ in range(rows)]
    open_ = [100.0 for _ in range(rows)]

    if rows > 17 and exit_style == "target":
        high[16] = 120.0
    if rows > 17 and exit_style == "stop":
        low[16] = 90.0
    if exit_style == "time":
        high = [101.0 for _ in range(rows)]
        low = [99.0 for _ in range(rows)]

    return pd.DataFrame(
        {
            "date": dates,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": [1000 for _ in range(rows)],
        }
    )


def _frame_from_ohlc(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    opens: list[float],
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=len(closes), freq="D"),
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": [1000 for _ in closes],
        }
    )
