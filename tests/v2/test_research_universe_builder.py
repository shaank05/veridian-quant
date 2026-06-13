"""Tests for V2 research universe construction."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

from veridian_quant.v2.data.research_universe import build_research_universes


def test_eligible_pool_excludes_ineligible_rows(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path, rows=_coverage_rows(20))

    result = _run_builder(paths, tmp_path / "out", sizes=(10,))

    assert "INELIG" not in set(result.eligible["symbol"])
    assert _rejection_reason(result.rejections, "INELIG") == "NOT_ELIGIBLE_FOR_RESEARCH"


def test_eligible_pool_excludes_symbols_from_bad_ohlc_file(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path, rows=_coverage_rows(20), bad_symbols=["SYM005"])

    result = _run_builder(paths, tmp_path / "out", sizes=(10,))

    assert "SYM005" not in set(result.eligible["symbol"])
    assert "BAD_OHLC_SYMBOL" in _rejection_reason(result.rejections, "SYM005")


def test_mazdock_is_excluded_when_present_in_bad_ohlc_file(tmp_path: Path) -> None:
    rows = _coverage_rows(20) + [_row("MAZDOCK", 999_999)]
    paths = _write_inputs(tmp_path, rows=rows, bad_symbols=["MAZDOCK"])

    result = _run_builder(paths, tmp_path / "out", sizes=(10,))

    assert "MAZDOCK" not in set(result.eligible["symbol"])
    assert "BAD_OHLC_SYMBOL" in _rejection_reason(result.rejections, "MAZDOCK")


def test_selection_is_deterministic_for_fixed_seed(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path, rows=_coverage_rows(130))

    first = _run_builder(paths, tmp_path / "out1", sizes=(100,), seed=123)
    second = _run_builder(paths, tmp_path / "out2", sizes=(100,), seed=123)

    assert list(first.universes[100]["symbol"]) == list(second.universes[100]["symbol"])
    assert list(first.universes[100]["selection_rank"]) == list(
        second.universes[100]["selection_rank"]
    )


def test_requested_universe_sizes_are_created_when_enough_symbols_exist(
    tmp_path: Path,
) -> None:
    paths = _write_inputs(tmp_path, rows=_coverage_rows(230))

    result = _run_builder(paths, tmp_path / "out", sizes=(100, 200))

    assert len(result.universes[100]) == 100
    assert len(result.universes[200]) == 200


def test_insufficient_symbols_create_available_size_and_summary_reports_it(
    tmp_path: Path,
) -> None:
    paths = _write_inputs(tmp_path, rows=_coverage_rows(75))

    result = _run_builder(paths, tmp_path / "out", sizes=(100, 200))
    summary = result.summary.iloc[0]

    assert len(result.universes[100]) == 75
    assert len(result.universes[200]) == 75
    assert summary["research_100_size"] == 75
    assert summary["research_200_size"] == 75


def test_liquidity_buckets_are_assigned(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path, rows=_coverage_rows(30))

    result = _run_builder(paths, tmp_path / "out", sizes=(10,))

    assert set(result.eligible["liquidity_bucket"]) == {"HIGH", "MID", "LOW"}
    assert result.eligible["liquidity_metric"].notna().all()


def test_final_universe_files_contain_required_columns(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path, rows=_coverage_rows(130))

    result = _run_builder(paths, tmp_path / "out", sizes=(100,))
    universe = pd.read_csv(result.paths["research_100"])

    required = {
        "selection_rank",
        "symbol",
        "instrument_key",
        "trading_symbol",
        "name",
        "liquidity_bucket",
        "liquidity_metric",
        "row_count",
        "first_price_date",
        "last_price_date",
        "missing_day_pct",
        "zero_volume_pct",
        "bad_ohlc_rows",
        "eligible_for_research",
        "universe_size",
        "selection_seed",
        "source_coverage_file",
    }
    assert required.issubset(universe.columns)


def test_summary_file_is_created(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path, rows=_coverage_rows(130), bad_symbols=["SYM001"])

    result = _run_builder(paths, tmp_path / "out", sizes=(100,))

    assert result.paths["summary"].exists()
    summary = pd.read_csv(result.paths["summary"]).iloc[0]
    assert summary["bad_ohlc_symbols_excluded"] == 2


def test_rejection_file_is_created(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path, rows=_coverage_rows(20), bad_symbols=["SYM002"])

    result = _run_builder(paths, tmp_path / "out", sizes=(10,))

    assert result.paths["rejections"].exists()
    rejections = pd.read_csv(result.paths["rejections"])
    assert "SYM002" in set(rejections["symbol"])


def test_cli_works_with_synthetic_temporary_csvs(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path, rows=_coverage_rows(130), bad_symbols=["SYM003"])
    output_dir = tmp_path / "cli-out"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "veridian_quant.v2.build_research_universe",
            "--coverage-file",
            str(paths["coverage"]),
            "--bad-ohlc-file",
            str(paths["bad_ohlc"]),
            "--output-dir",
            str(output_dir),
            "--start-date",
            "2018-01-01",
            "--end-date",
            "2026-04-30",
            "--seed",
            "42",
            "--sizes",
            "100,200",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert (output_dir / "nse_eq_research_100_2018_2026.csv").exists()
    assert (output_dir / "nse_eq_research_200_2018_2026.csv").exists()


def _run_builder(
    paths: dict[str, Path],
    output_dir: Path,
    sizes: tuple[int, ...],
    seed: int = 42,
):
    return build_research_universes(
        coverage_file=paths["coverage"],
        bad_ohlc_file=paths["bad_ohlc"],
        output_dir=output_dir,
        start_date="2018-01-01",
        end_date="2026-04-30",
        seed=seed,
        sizes=sizes,
    )


def _write_inputs(
    tmp_path: Path,
    rows: list[dict[str, object]],
    bad_symbols: list[str] | None = None,
) -> dict[str, Path]:
    coverage = tmp_path / "price_coverage.csv"
    bad_ohlc = tmp_path / "bad_ohlc_rows.csv"
    all_rows = rows + [
        _row("INELIG", 10_000, eligible=False),
        _row("BADROWS", 20_000, bad_ohlc_rows=1),
    ]
    pd.DataFrame(all_rows).to_csv(coverage, index=False)
    pd.DataFrame(
        [
            {
                "instrument_key": f"NSE_EQ|{symbol}",
                "symbol": symbol,
                "timestamp": "2018-01-01T00:00:00+00:00",
                "open": 0,
                "high": 0,
                "low": 0,
                "close": 0,
                "volume": 1,
                "reason": "OPEN_LE_ZERO",
            }
            for symbol in (bad_symbols or [])
        ],
        columns=[
            "instrument_key",
            "symbol",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "reason",
        ],
    ).to_csv(bad_ohlc, index=False)
    return {"coverage": coverage, "bad_ohlc": bad_ohlc}


def _coverage_rows(count: int) -> list[dict[str, object]]:
    return [_row(f"SYM{idx:03d}", (count - idx) * 1_000) for idx in range(count)]


def _row(
    symbol: str,
    avg_turnover_60d: float,
    eligible: bool = True,
    bad_ohlc_rows: int = 0,
) -> dict[str, object]:
    return {
        "instrument_key": f"NSE_EQ|{symbol}",
        "symbol": symbol,
        "trading_symbol": symbol,
        "name": f"{symbol} Limited",
        "row_count": 2_000,
        "first_price_date": "2018-01-01",
        "last_price_date": "2026-04-30",
        "missing_calendar_day_pct": 0.5,
        "zero_volume_pct": 0.0,
        "bad_ohlc_rows": bad_ohlc_rows,
        "duplicate_rows": 0,
        "avg_turnover_60d": avg_turnover_60d,
        "eligible_for_research": eligible,
    }


def _rejection_reason(rejections: pd.DataFrame, symbol: str) -> str:
    rows = rejections.loc[rejections["symbol"] == symbol]
    assert len(rows) == 1
    return str(rows.iloc[0]["rejection_reason"])
