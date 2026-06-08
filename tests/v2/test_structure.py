"""Structural tests for the Veridian Quant v2 architecture skeleton."""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType

from veridian_quant.v2.backtesting.engine import BacktestConfig, BacktestResult
from veridian_quant.v2.backtesting.portfolio import PortfolioState, Position
from veridian_quant.v2.backtesting.trade import ExitReason, Trade, TradeStatus
from veridian_quant.v2.config.settings import (
    DataSettings,
    PortfolioSettings,
    V2Settings,
)
from veridian_quant.v2.data.contracts import MarketDataProvider
from veridian_quant.v2.data.models import Instrument, MarketBar, Signal, SignalType
from veridian_quant.v2.features.base import FeatureSet, FeatureTransformer
from veridian_quant.v2.reporting.metrics import MetricReport, MetricValue
from veridian_quant.v2.reporting.reports import BacktestReport, ReportSection
from veridian_quant.v2.strategies.base import Strategy, StrategyContext
from veridian_quant.v2.strategies.s1_zscore_mean_reversion import (
    S1ZScoreMeanReversionStrategy,
)


def test_v2_modules_import() -> None:
    """Verify public v2 architecture modules are importable."""

    assert MarketDataProvider
    assert FeatureTransformer
    assert Strategy
    assert S1ZScoreMeanReversionStrategy


def test_domain_dataclasses_can_be_instantiated() -> None:
    """Verify passive domain models can be constructed without logic."""

    data_settings = DataSettings(
        universe_name="phase1",
        start_date=date(2018, 1, 1),
        end_date=date(2026, 5, 31),
    )
    portfolio_settings = PortfolioSettings(
        initial_cash=Decimal("1000000"),
        max_positions=5,
    )
    settings = V2Settings(data=data_settings, portfolio=portfolio_settings)

    instrument = Instrument(symbol="RELIANCE", exchange="NSE")
    bar = MarketBar(
        symbol=instrument.symbol,
        timestamp=datetime(2026, 5, 29, 15, 30),
        open=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("99"),
        close=Decimal("104"),
        volume=1000,
    )
    signal = Signal(
        symbol=instrument.symbol,
        signal_type=SignalType.LONG,
        generated_on=date(2026, 5, 29),
        strategy_name="s1_zscore_mean_reversion",
        reason="research candidate",
    )
    feature_set = FeatureSet(
        symbol=instrument.symbol,
        observed_on=date(2026, 5, 29),
        values=MappingProxyType({"example": Decimal("1.0")}),
    )
    position = Position(
        symbol=instrument.symbol,
        quantity=10,
        average_price=Decimal("104"),
        opened_on=date(2026, 5, 29),
        strategy_name=signal.strategy_name,
    )
    trade = Trade(
        trade_id="T1",
        symbol=instrument.symbol,
        entry_date=date(2026, 5, 29),
        entry_price=Decimal("104"),
        quantity=10,
        status=TradeStatus.CLOSED,
        strategy_name=signal.strategy_name,
        exit_date=date(2026, 6, 5),
        exit_price=Decimal("108"),
        exit_reason=ExitReason.SIGNAL_EXIT,
    )
    state = PortfolioState(
        as_of=date(2026, 6, 5),
        cash=Decimal("1000000"),
        positions=MappingProxyType({position.symbol: position}),
    )
    config = BacktestConfig(
        run_id="run-1",
        start_date=data_settings.start_date,
        end_date=data_settings.end_date,
        universe=(instrument.symbol,),
        strategy_name=signal.strategy_name,
    )
    result = BacktestResult(
        config=config,
        final_state=state,
        signals=(signal,),
        trades=(trade,),
    )
    metric = MetricValue(name="sample", value=1)
    metric_report = MetricReport(
        run_id=config.run_id,
        metrics=MappingProxyType({metric.name: metric}),
    )
    report = BacktestReport(
        run_id=config.run_id,
        metrics=metric_report,
        sections=(ReportSection(title="Summary", body="Research skeleton"),),
    )
    context = StrategyContext(
        as_of=date(2026, 5, 29),
        universe=(instrument.symbol,),
        run_label=settings.run_label,
    )

    assert bar.symbol == "RELIANCE"
    assert feature_set.symbol == instrument.symbol
    assert result.final_state == state
    assert report.run_id == config.run_id
    assert context.universe == ("RELIANCE",)


def test_requested_v2_project_structure_exists() -> None:
    """Verify the requested v2 source and test files exist."""

    root = Path(__file__).resolve().parents[2]
    expected_files = [
        "src/veridian_quant/v2/config/settings.py",
        "src/veridian_quant/v2/data/models.py",
        "src/veridian_quant/v2/data/contracts.py",
        "src/veridian_quant/v2/features/base.py",
        "src/veridian_quant/v2/strategies/base.py",
        "src/veridian_quant/v2/strategies/s1_zscore_mean_reversion.py",
        "src/veridian_quant/v2/backtesting/trade.py",
        "src/veridian_quant/v2/backtesting/portfolio.py",
        "src/veridian_quant/v2/backtesting/engine.py",
        "src/veridian_quant/v2/reporting/metrics.py",
        "src/veridian_quant/v2/reporting/reports.py",
        "tests/v2/test_structure.py",
    ]

    for relative_path in expected_files:
        assert (root / relative_path).is_file()
