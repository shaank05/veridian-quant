"""Tests for the S2 Markov ranking comparison runner."""

from datetime import date
from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd

from veridian_quant.v2.backtesting.portfolio_runner import PortfolioBacktestResult
from veridian_quant.v2.compare_s2_markov_rankings import main
from veridian_quant.v2.strategies.s2_markov_state_transition import STRATEGY_NAME


def test_ranking_comparison_runner_writes_summary_csv() -> None:
    with TemporaryDirectory() as temp_dir:
        with (
            patch(
                "veridian_quant.v2.compare_s2_markov_rankings._get_database_engine",
                return_value=object(),
            ),
            patch(
                "veridian_quant.v2.compare_s2_markov_rankings.SQLAlchemyDailyOHLCVLoader",
                _FakeLoader,
            ),
            patch(
                "veridian_quant.v2.compare_s2_markov_rankings.run_s2_markov_portfolio_backtest",
                return_value=_empty_result(),
            ),
            patch(
                "veridian_quant.v2.compare_s2_markov_rankings.export_portfolio_backtest_csvs",
                return_value={},
            ),
        ):
            exit_code = main(
                [
                    "--start-date",
                    "2026-01-01",
                    "--end-date",
                    "2026-01-31",
                    "--symbols",
                    "AAA",
                    "--output-dir",
                    temp_dir,
                    "--rankings",
                    "none,state_edge_v1",
                    "--verbosity",
                    "quiet",
                ]
            )

        summary = pd.read_csv(
            f"{temp_dir}/s2_markov_ranking_experiment_summary.csv"
        )

    assert exit_code == 0
    assert summary["s2_candidate_ranking_mode"].tolist() == [
        "none",
        "state_edge_v1",
    ]
    assert "capacity_rejected_signals" in summary.columns


class _FakeLoader:
    lookback_buffer_days = 0

    def __init__(self, engine: object) -> None:
        self.engine = engine

    def load_symbols(
        self,
        symbols: list[str],
        start_date: date,
        end_date: date,
    ) -> dict[str, pd.DataFrame]:
        return {"AAA": pd.DataFrame()}

    def load_all_available_symbols(
        self,
        start_date: date,
        end_date: date,
    ) -> dict[str, pd.DataFrame]:
        return self.load_symbols(["AAA"], start_date, end_date)

    def load_instrument_key(
        self,
        instrument_key: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        return pd.DataFrame()


def _empty_result() -> PortfolioBacktestResult:
    return PortfolioBacktestResult(
        strategy_name=STRATEGY_NAME,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        starting_equity=Decimal("100000"),
        ending_equity=Decimal("100000"),
        symbols=("AAA",),
        strategy_variant=STRATEGY_NAME,
    )
