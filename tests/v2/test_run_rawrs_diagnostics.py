"""Tests for the standalone I1 RAWRS diagnostic CLI."""

import importlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from veridian_quant.v2.run_rawrs_diagnostics import (
    FULL_REQUIRED_FILES,
    LIGHT_REQUIRED_FILES,
    build_rawrs_diagnostics_from_csv_frames,
    main,
    optional_rawrs_input_files,
    read_rawrs_input_csvs,
    required_files_for_mode,
    run_rawrs_diagnostics_from_frames,
    validate_rawrs_input_directory,
)


def test_required_files_for_light_mode_returns_expected_files() -> None:
    assert required_files_for_mode("light") == LIGHT_REQUIRED_FILES


def test_required_files_for_full_mode_returns_expected_files() -> None:
    assert required_files_for_mode("full") == FULL_REQUIRED_FILES


def test_invalid_mode_raises_value_error() -> None:
    with pytest.raises(ValueError, match="mode must be 'light' or 'full'"):
        required_files_for_mode("unknown")


def test_validation_passes_for_light_mode_directory(tmp_path) -> None:
    _write_required_files(tmp_path, "light")

    result = validate_rawrs_input_directory(tmp_path, "light")

    assert result.is_valid is True
    assert result.missing_required_files == []
    assert result.mode == "light"


def test_validation_fails_when_light_required_file_missing(tmp_path) -> None:
    _write_required_files(tmp_path, "light", skip={"signal_log.csv"})

    result = validate_rawrs_input_directory(tmp_path, "light")

    assert result.is_valid is False
    assert result.missing_required_files == ["signal_log.csv"]


def test_validation_warns_for_missing_optional_files(tmp_path) -> None:
    _write_required_files(tmp_path, "light")

    result = validate_rawrs_input_directory(tmp_path, "light")

    assert result.missing_optional_files == optional_rawrs_input_files()
    assert any("missing optional RAWRS input files" in item for item in result.warnings)


def test_validation_detects_empty_full_mode_row_level_files(tmp_path) -> None:
    _write_required_files(
        tmp_path,
        "full",
        empty={
            "rejected_signals.csv",
            "all_signal_opportunity_log.csv",
            "same_day_candidate_pool_summary.csv",
        },
    )

    result = validate_rawrs_input_directory(tmp_path, "full")

    assert result.is_valid is False
    assert set(result.empty_required_files) >= {
        "rejected_signals.csv",
        "all_signal_opportunity_log.csv",
        "same_day_candidate_pool_summary.csv",
    }
    assert any("full-mode row-level files are empty" in item for item in result.warnings)


def test_csv_reader_loads_expected_files_and_ignores_absent_optional_files(tmp_path) -> None:
    _write_required_files(tmp_path, "light")
    validation = validate_rawrs_input_directory(tmp_path, "light")

    frames = read_rawrs_input_csvs(tmp_path, validation)

    assert set(frames) == set(LIGHT_REQUIRED_FILES)
    assert frames["signal_log.csv"].loc[0, "symbol"] == "AAA"


def test_build_diagnostics_from_frames_attaches_rawrs_to_signal_log() -> None:
    frames = _csv_frames()

    result = build_rawrs_diagnostics_from_csv_frames(
        frames,
        _features_by_symbol(),
        mode="light",
    )

    signal_diagnostics = result["signal_diagnostics"]
    assert signal_diagnostics["rawrs_micro_energy"].tolist() == [1.0, 2.0]
    assert "rawrs_feature_timestamp" in signal_diagnostics.columns


def test_build_diagnostics_from_frames_attaches_rawrs_to_trade_records() -> None:
    frames = _csv_frames()

    result = build_rawrs_diagnostics_from_csv_frames(
        frames,
        _features_by_symbol(),
        mode="light",
    )

    trade_diagnostics = result["trade_diagnostics"]
    assert trade_diagnostics["trade_id"].tolist() == [1, 2]
    assert trade_diagnostics["rawrs_micro_energy"].tolist() == [1.0, 2.0]


def test_full_mode_attaches_rawrs_to_rejected_signals_when_present() -> None:
    frames = _csv_frames()
    frames["rejected_signals.csv"] = pd.DataFrame(
        {
            "symbol": ["AAA", "BBB"],
            "signal_date": ["2026-01-02", "2026-01-03"],
            "reason": ["CAPACITY", "ACTIVE_SYMBOL_TRADE_EXISTS"],
        }
    )

    result = build_rawrs_diagnostics_from_csv_frames(
        frames,
        _features_by_symbol(),
        mode="full",
    )

    rejection_diagnostics = result["rejection_diagnostics"]
    assert rejection_diagnostics["reason"].tolist() == [
        "CAPACITY",
        "ACTIVE_SYMBOL_TRADE_EXISTS",
    ]
    assert rejection_diagnostics["rawrs_micro_energy"].tolist() == [1.0, 2.0]


def test_unknown_symbols_produce_nan_rawrs_features_not_crashes() -> None:
    frames = _csv_frames()
    frames["signal_log.csv"] = pd.DataFrame(
        {"symbol": ["AAA", "ZZZ"], "generated_on": ["2026-01-02", "2026-01-02"]}
    )

    result = build_rawrs_diagnostics_from_csv_frames(
        frames,
        _features_by_symbol(),
        mode="light",
    )

    signal_diagnostics = result["signal_diagnostics"]
    assert signal_diagnostics.loc[0, "rawrs_micro_energy"] == 1.0
    assert np.isnan(signal_diagnostics.loc[1, "rawrs_micro_energy"])


def test_diagnostic_outputs_are_written_to_separate_output_dir(tmp_path) -> None:
    strategy_dir = tmp_path / "strategy"
    rawrs_dir = tmp_path / "rawrs"
    strategy_dir.mkdir()
    frames = _csv_frames()
    for filename, frame in frames.items():
        frame.to_csv(strategy_dir / filename, index=False)
    original_signal_log = (strategy_dir / "signal_log.csv").read_text()

    paths = run_rawrs_diagnostics_from_frames(
        csv_frames=frames,
        rawrs_features_by_symbol=_features_by_symbol(),
        output_dir=rawrs_dir,
        mode="light",
    )

    assert paths["signal_diagnostics"] == rawrs_dir / "rawrs_signal_diagnostics.csv"
    assert paths["trade_diagnostics"] == rawrs_dir / "rawrs_trade_diagnostics.csv"
    assert (strategy_dir / "signal_log.csv").read_text() == original_signal_log


def test_main_returns_nonzero_for_missing_required_files(tmp_path) -> None:
    output_dir = tmp_path / "rawrs"

    exit_code = main(
        [
            "--strategy-output-dir",
            str(tmp_path / "missing"),
            "--output-dir",
            str(output_dir),
            "--mode",
            "light",
        ]
    )

    assert exit_code == 1


def test_main_does_not_modify_strategy_output_files(tmp_path) -> None:
    strategy_dir = tmp_path / "strategy"
    output_dir = tmp_path / "rawrs"
    strategy_dir.mkdir()
    _write_required_files(strategy_dir, "light")
    before = {
        path.name: path.read_text()
        for path in strategy_dir.iterdir()
        if path.is_file()
    }

    exit_code = main(
        [
            "--strategy-output-dir",
            str(strategy_dir),
            "--output-dir",
            str(output_dir),
            "--mode",
            "light",
        ]
    )

    after = {
        path.name: path.read_text()
        for path in strategy_dir.iterdir()
        if path.is_file()
    }
    assert exit_code == 0
    assert after == before


def test_no_import_dependency_on_strategy_runner_modules() -> None:
    module = importlib.import_module("veridian_quant.v2.run_rawrs_diagnostics")

    imported_module_names = {
        value.__name__
        for value in vars(module).values()
        if hasattr(value, "__name__") and hasattr(value, "__dict__")
    }
    assert "veridian_quant.v2.run_s1_backtest" not in imported_module_names
    assert "veridian_quant.v2.run_s2_markov_backtest" not in imported_module_names
    assert "veridian_quant.v2.run_s3_backtest" not in imported_module_names
    assert "veridian_quant.v2.run_s4_backtest" not in imported_module_names


def test_no_topology_or_regime_labels_are_produced() -> None:
    result = build_rawrs_diagnostics_from_csv_frames(
        _csv_frames(),
        _features_by_symbol(),
        mode="light",
    )

    forbidden_terms = ("topology", "regime", "label")
    for frame in result.values():
        assert not any(
            any(term in column for term in forbidden_terms)
            for column in frame.columns
        )


def test_no_ranking_or_filtering_behavior_exists() -> None:
    result = build_rawrs_diagnostics_from_csv_frames(
        _csv_frames(),
        _features_by_symbol(),
        mode="light",
    )

    for frame in result.values():
        assert "rawrs_rank" not in frame.columns
        assert "rawrs_filter_decision" not in frame.columns


def _write_required_files(
    directory: Path,
    mode: str,
    *,
    skip: set[str] | None = None,
    empty: set[str] | None = None,
) -> None:
    skip = skip or set()
    empty = empty or set()
    for filename in required_files_for_mode(mode):
        if filename in skip:
            continue
        frame = _frame_for_filename(filename)
        if filename in empty:
            frame = frame.iloc[0:0]
        frame.to_csv(directory / filename, index=False)


def _csv_frames() -> dict[str, pd.DataFrame]:
    return {
        "signal_log.csv": pd.DataFrame(
            {
                "symbol": ["AAA", "BBB"],
                "generated_on": ["2026-01-02", "2026-01-03"],
            }
        ),
        "trade_log.csv": pd.DataFrame(
            {
                "trade_id": [1, 2],
                "symbol": ["AAA", "BBB"],
                "entry_date": ["2026-01-02", "2026-01-03"],
                "exit_reason": ["target_hit", "stop_loss"],
                "net_pnl": [100.0, -50.0],
                "r_multiple": [2.0, -1.0],
            }
        ),
    }


def _features_by_symbol() -> dict[str, pd.DataFrame]:
    return {
        "AAA": _rawrs_frame(["2026-01-02"], [1.0]),
        "BBB": _rawrs_frame(["2026-01-03"], [2.0]),
    }


def _rawrs_frame(dates: list[str], micro_energy: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "rawrs_micro_energy": micro_energy,
            "rawrs_fft_spectral_entropy": [value / 10.0 for value in micro_energy],
        },
        index=pd.to_datetime(dates),
    )


def _frame_for_filename(filename: str) -> pd.DataFrame:
    if filename == "signal_log.csv":
        return pd.DataFrame({"symbol": ["AAA"], "generated_on": ["2026-01-02"]})
    if filename == "trade_log.csv":
        return pd.DataFrame(
            {"trade_id": [1], "symbol": ["AAA"], "entry_date": ["2026-01-02"]}
        )
    if filename == "trade_pnl_log.csv":
        return pd.DataFrame(
            {"trade_id": [1], "symbol": ["AAA"], "entry_date": ["2026-01-02"]}
        )
    if filename == "rejected_signals.csv":
        return pd.DataFrame(
            {"symbol": ["AAA"], "signal_date": ["2026-01-02"], "reason": ["CAPACITY"]}
        )
    if filename == "all_signal_opportunity_log.csv":
        return pd.DataFrame(
            {"symbol": ["AAA"], "signal_date": ["2026-01-02"], "decision": ["accepted"]}
        )
    if filename == "same_day_candidate_pool_summary.csv":
        return pd.DataFrame({"signal_date": ["2026-01-02"], "candidates": [1]})
    return pd.DataFrame({"value": [1]})
