"""CLI parsing tests for the Phase 33G.1 S2 context experiment runner."""

from datetime import date

import pytest

from veridian_quant.v2.run_s2_context_experiments import _parse_args


def test_cli_parses_allowed_variant() -> None:
    args = _parse_args(
        [
            "--start-date",
            "2020-01-01",
            "--end-date",
            "2026-04-30",
            "--symbols",
            "RELIANCE,TCS",
            "--variant",
            "S2_AVOID_BENCHMARK_20D_STRONG_NEGATIVE",
            "--output-dir",
            "reports/v2/s2_context_experiments/test",
        ]
    )

    assert args.start_date == date(2020, 1, 1)
    assert args.end_date == date(2026, 4, 30)
    assert args.symbols == "RELIANCE,TCS"
    assert args.variant == "S2_AVOID_BENCHMARK_20D_STRONG_NEGATIVE"


def test_cli_parses_all_predeclared() -> None:
    args = _parse_args(
        [
            "--start-date",
            "2020-01-01",
            "--end-date",
            "2026-04-30",
            "--symbols-file",
            "config/universes/research/nse_eq_research_200_2018_2026.csv",
            "--variant",
            "ALL_PREDECLARED",
        ]
    )

    assert args.variant == "ALL_PREDECLARED"


def test_cli_rejects_unknown_variant() -> None:
    with pytest.raises(SystemExit):
        _parse_args(
            [
                "--start-date",
                "2020-01-01",
                "--end-date",
                "2026-04-30",
                "--symbols",
                "RELIANCE",
                "--variant",
                "S2_GRID_SEARCH",
            ]
        )


def test_cli_requires_one_symbol_source() -> None:
    with pytest.raises(SystemExit):
        _parse_args(
            [
                "--start-date",
                "2020-01-01",
                "--end-date",
                "2026-04-30",
                "--symbols",
                "RELIANCE",
                "--symbols-file",
                "config/universes/research/nse_eq_research_200_2018_2026.csv",
                "--variant",
                "S2_BASELINE",
            ]
        )


def test_cli_does_not_accept_arbitrary_threshold_flag() -> None:
    with pytest.raises(SystemExit):
        _parse_args(
            [
                "--start-date",
                "2020-01-01",
                "--end-date",
                "2026-04-30",
                "--symbols",
                "RELIANCE",
                "--variant",
                "S2_BASELINE",
                "--benchmark-ret-20d-threshold",
                "-0.03",
            ]
        )
