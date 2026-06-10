"""Unit tests for signal-date context diagnostic reports."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType

import pandas as pd
import pytest

from veridian_quant.v2.backtesting.pnl import TradePnL
from veridian_quant.v2.backtesting.portfolio_runner import PortfolioBacktestResult
from veridian_quant.v2.backtesting.trade import ExitReason
from veridian_quant.v2.data.models import Signal, SignalType
from veridian_quant.v2.reporting.context import (
    R_CONTEXT_BUCKET_COLUMNS,
    TRADE_SIGNAL_CONTEXT_COLUMNS,
)
from veridian_quant.v2.reporting.exporters import export_portfolio_backtest_csvs


_DEFAULT_NIFTY = object()


def test_trade_signal_context_is_written_one_row_per_executed_trade() -> None:
    paths = _export_to_temp_dir()

    context = pd.read_csv(paths["trade_signal_context"])

    assert paths["trade_signal_context"].exists()
    assert list(context.columns) == TRADE_SIGNAL_CONTEXT_COLUMNS
    assert len(context) == 2
    assert context["trade_id"].tolist() == ["trade-1", "trade-2"]


def test_signal_linkage_uses_nearest_previous_same_symbol_strategy_signal() -> None:
    paths = _export_to_temp_dir()

    context = pd.read_csv(paths["trade_signal_context"]).set_index("trade_id")

    assert context.loc["trade-1", "signal_date"] == "2026-01-20"
    assert context.loc["trade-1", "z_score"] == -2.7
    assert context.loc["trade-1", "zscore_window"] == 20
    assert context.loc["trade-1", "entry_threshold"] == -2
    assert context.loc["trade-1", "signal_close"] == 319


def test_context_uses_signal_date_not_entry_date() -> None:
    paths = _export_to_temp_dir()

    context = pd.read_csv(paths["trade_signal_context"]).set_index("trade_id")

    assert context.loc["trade-1", "entry_date"] == "2026-01-21"
    assert context.loc["trade-1", "stock_close"] == 319
    assert context.loc["trade-1", "stock_close"] != 320


def test_context_accepts_timezone_aware_utc_stock_and_nifty_dates() -> None:
    stock = _ohlcv_frame_ending(
        date(2026, 1, 21),
        periods=221,
        close_start=100,
        step=1,
        timezone="UTC",
    )
    nifty = _ohlcv_frame_ending(
        date(2026, 1, 21),
        periods=221,
        close_start=80,
        step=0.5,
        timezone="UTC",
    )
    paths = _export_to_temp_dir(
        stock_data_by_symbol={"RELIANCE": stock},
        nifty_data=nifty,
    )

    context = pd.read_csv(paths["trade_signal_context"]).set_index("trade_id")

    assert context.loc["trade-1", "signal_date"] == "2026-01-20"
    assert context.loc["trade-1", "entry_date"] == "2026-01-21"
    assert context.loc["trade-1", "stock_close"] == 319
    assert context.loc["trade-1", "nifty_close"] == 189.5
    assert context.loc["trade-1", "stock_close"] != 320


def test_sma_returns_drawdown_atr_and_relative_strength_are_calculated() -> None:
    stock = _ohlcv_frame_ending(date(2026, 1, 21), periods=221, close_start=100, step=1)
    nifty = _ohlcv_frame_ending(date(2026, 1, 21), periods=221, close_start=80, step=0.5)
    paths = _export_to_temp_dir(stock_data_by_symbol={"RELIANCE": stock}, nifty_data=nifty)

    row = pd.read_csv(paths["trade_signal_context"]).set_index("trade_id").loc["trade-1"]
    stock_close = Decimal("319")
    nifty_close = Decimal("189.5")

    assert row["stock_sma50"] == pytest.approx(stock.loc[170:219, "close"].mean())
    assert row["stock_sma200"] == pytest.approx(stock.loc[20:219, "close"].mean())
    assert row["nifty_sma50"] == pytest.approx(nifty.loc[170:219, "close"].mean())
    assert row["nifty_sma200"] == pytest.approx(nifty.loc[20:219, "close"].mean())

    assert row["stock_return_20d_pct"] == pytest.approx(((319 / 299) - 1) * 100)
    assert row["stock_return_60d_pct"] == pytest.approx(((319 / 259) - 1) * 100)
    assert row["stock_return_120d_pct"] == pytest.approx(((319 / 199) - 1) * 100)
    assert row["stock_drawdown_60d_pct"] == 0
    assert row["stock_atr14"] == 2
    assert row["stock_atr14_pct"] == pytest.approx((2 / 319) * 100)

    nifty_return_20d = ((float(nifty_close) / 179.5) - 1) * 100
    assert row["nifty_return_20d_pct"] == pytest.approx(nifty_return_20d)
    assert row["relative_strength_20d_vs_nifty"] == pytest.approx(
        row["stock_return_20d_pct"] - row["nifty_return_20d_pct"]
    )
    assert row["relative_strength_60d_vs_nifty"] == pytest.approx(
        row["stock_return_60d_pct"] - row["nifty_return_60d_pct"]
    )
    assert row["relative_strength_120d_vs_nifty"] == pytest.approx(
        row["stock_return_120d_pct"] - row["nifty_return_120d_pct"]
    )
    assert stock_close == Decimal(str(row["stock_close"]))


def test_missing_signal_and_context_data_write_blank_fields_safely() -> None:
    result = _result(signals=())
    paths = _export_to_temp_dir(result=result, stock_data_by_symbol={}, nifty_data=None)

    context = pd.read_csv(paths["trade_signal_context"])

    assert len(context) == 2
    assert pd.isna(context.loc[0, "signal_date"])
    assert pd.isna(context.loc[0, "z_score"])
    assert pd.isna(context.loc[0, "stock_close"])
    assert pd.isna(context.loc[0, "nifty_close"])
    assert pd.isna(context.loc[0, "relative_strength_20d_vs_nifty"])


def test_insufficient_context_lookback_writes_blank_fields_safely() -> None:
    short_stock = _ohlcv_frame(date(2026, 1, 22), periods=5, close_start=100, step=1)
    paths = _export_to_temp_dir(
        stock_data_by_symbol={"RELIANCE": short_stock},
        nifty_data=None,
    )

    context = pd.read_csv(paths["trade_signal_context"]).set_index("trade_id")

    assert pd.isna(context.loc["trade-1", "stock_close"])
    assert pd.isna(context.loc["trade-1", "stock_sma50"])
    assert pd.isna(context.loc["trade-1", "stock_atr14_pct"])


def test_bucket_reports_are_created_and_summarize_r() -> None:
    paths = _export_to_temp_dir()

    for key in (
        "r_by_stock_trend_context",
        "r_by_nifty_trend_context",
        "r_by_relative_strength_context",
    ):
        assert paths[key].exists()
        assert list(pd.read_csv(paths[key]).columns) == R_CONTEXT_BUCKET_COLUMNS

    stock_buckets = pd.read_csv(paths["r_by_stock_trend_context"]).set_index("bucket")
    assert stock_buckets.loc["stock_above_sma200", "trades_with_r"] == 2
    assert stock_buckets.loc["stock_above_sma200", "winning_trades"] == 1
    assert stock_buckets.loc["stock_above_sma200", "losing_trades"] == 1
    assert stock_buckets.loc["stock_above_sma200", "positive_r_rate_pct"] == 50
    assert stock_buckets.loc["stock_above_sma200", "average_r"] == 0.5
    assert stock_buckets.loc["stock_above_sma200", "average_winner_r"] == 2
    assert stock_buckets.loc["stock_above_sma200", "average_loser_r"] == -1
    assert stock_buckets.loc["stock_above_sma200", "best_r"] == 2
    assert stock_buckets.loc["stock_above_sma200", "worst_r"] == -1

    nifty_buckets = pd.read_csv(paths["r_by_nifty_trend_context"]).set_index("bucket")
    assert nifty_buckets.loc["nifty_above_sma200", "trades_with_r"] == 2

    rs_buckets = pd.read_csv(paths["r_by_relative_strength_context"]).set_index("bucket")
    assert rs_buckets.loc["rs_20d_positive", "trades_with_r"] == 2


def _export_to_temp_dir(
    result: PortfolioBacktestResult | None = None,
    stock_data_by_symbol: dict[str, pd.DataFrame] | None = None,
    nifty_data: pd.DataFrame | None | object = _DEFAULT_NIFTY,
) -> dict[str, Path]:
    """Export a fake result into a temp directory that persists for the test."""

    temp_dir = TemporaryDirectory()
    if stock_data_by_symbol is None:
        stock_data_by_symbol = {
            "RELIANCE": _ohlcv_frame_ending(
                date(2026, 1, 21),
                periods=221,
                close_start=100,
                step=1,
            ),
        }
    if nifty_data is _DEFAULT_NIFTY:
        nifty_data = _ohlcv_frame_ending(
            date(2026, 1, 21),
            periods=221,
            close_start=80,
            step=0.5,
        )
    paths = export_portfolio_backtest_csvs(
        result or _result(),
        temp_dir.name,
        stock_data_by_symbol=stock_data_by_symbol,
        nifty_data=nifty_data,
    )
    _TEMP_DIRS.append(temp_dir)
    return paths


_TEMP_DIRS: list[TemporaryDirectory] = []


def _result(signals: tuple[Signal, ...] | None = None) -> PortfolioBacktestResult:
    """Build a result with two closed trades and linkable S1 signals."""

    signals = _signals() if signals is None else signals
    trade_pnls = (
        _pnl(
            trade_id="trade-1",
            net_pnl=Decimal("100"),
            entry_date=date(2026, 1, 21),
            exit_date=date(2026, 1, 26),
            exit_reason=ExitReason.TARGET_HIT,
        ),
        _pnl(
            trade_id="trade-2",
            net_pnl=Decimal("-50"),
            entry_date=date(2026, 1, 22),
            exit_date=date(2026, 1, 27),
            exit_reason=ExitReason.STOP_LOSS_HIT,
        ),
    )
    return PortfolioBacktestResult(
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        starting_equity=Decimal("100000"),
        ending_equity=Decimal("100050"),
        symbols=("RELIANCE",),
        trade_pnls=trade_pnls,
        trades=(),
        signals=signals,
        rejected_signals=(),
        ledger=None,
    )


def _signals() -> tuple[Signal, ...]:
    """Build signals that prove nearest previous same-symbol matching."""

    return (
        _signal(date(2026, 1, 15), z_score=Decimal("-2.1")),
        _signal(date(2026, 1, 20), z_score=Decimal("-2.7")),
        _signal(date(2026, 1, 21), z_score=Decimal("-2.4")),
        _signal(date(2026, 1, 20), symbol="TCS", z_score=Decimal("-3")),
        _signal(
            date(2026, 1, 20),
            strategy_name="OTHER_STRATEGY",
            z_score=Decimal("-4"),
        ),
    )


def _signal(
    generated_on: date,
    z_score: Decimal,
    symbol: str = "RELIANCE",
    strategy_name: str = "S1_ZSCORE_MEAN_REVERSION",
) -> Signal:
    """Build a signal with metadata used by context diagnostics."""

    close_by_date = {
        date(2026, 1, 15): Decimal("314"),
        date(2026, 1, 20): Decimal("319"),
        date(2026, 1, 21): Decimal("320"),
    }
    return Signal(
        symbol=symbol,
        signal_type=SignalType.LONG,
        generated_on=generated_on,
        strategy_name=strategy_name,
        reason="test signal",
        metadata=MappingProxyType(
            {
                "z_score": z_score,
                "zscore_window": 20,
                "entry_threshold": Decimal("-2"),
                "close": close_by_date.get(generated_on, Decimal("0")),
            }
        ),
    )


def _pnl(
    trade_id: str,
    net_pnl: Decimal,
    entry_date: date,
    exit_date: date,
    exit_reason: ExitReason,
) -> TradePnL:
    """Build a trade PnL with direct risk metadata."""

    return TradePnL(
        trade_id=trade_id,
        symbol="RELIANCE",
        strategy_name="S1_ZSCORE_MEAN_REVERSION",
        entry_date=entry_date,
        exit_date=exit_date,
        entry_price=Decimal("320"),
        exit_price=Decimal("330"),
        quantity=10,
        gross_pnl=net_pnl,
        gross_return_pct=Decimal("0"),
        total_cost=Decimal("0"),
        net_pnl=net_pnl,
        net_return_pct=Decimal("0"),
        exit_reason=exit_reason,
        stop_loss=Decimal("315"),
        target_price=Decimal("330"),
        per_share_risk=Decimal("5"),
        initial_risk_amount=Decimal("50"),
        planned_reward_amount=Decimal("100"),
        reward_risk_ratio=Decimal("2"),
    )


def _ohlcv_frame(
    start_date: date,
    periods: int,
    close_start: float,
    step: float,
) -> pd.DataFrame:
    """Build deterministic business-day OHLCV data."""

    dates = pd.bdate_range(start=start_date, periods=periods)
    closes = [close_start + index * step for index in range(periods)]
    return pd.DataFrame(
        {
            "date": dates,
            "open": closes,
            "high": [close + 1 for close in closes],
            "low": [close - 1 for close in closes],
            "close": closes,
            "volume": [1000] * periods,
        }
    )


def _ohlcv_frame_ending(
    end_date: date,
    periods: int,
    close_start: float,
    step: float,
    timezone: str | None = None,
) -> pd.DataFrame:
    """Build deterministic business-day OHLCV data ending on a date."""

    dates = pd.bdate_range(end=end_date, periods=periods)
    if timezone is not None:
        dates = dates.tz_localize(timezone)
    closes = [close_start + index * step for index in range(periods)]
    return pd.DataFrame(
        {
            "date": dates,
            "open": closes,
            "high": [close + 1 for close in closes],
            "low": [close - 1 for close in closes],
            "close": closes,
            "volume": [1000] * periods,
        }
    )
