"""Standalone CLI for I1 RAWRS diagnostic compatibility checks.

The CLI consumes existing strategy output CSV folders. It does not rerun
strategy backtests, import S1/S2/S3/S4 runners, or modify source outputs.
"""

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from veridian_quant.v2.intelligence.rawrs_exports import (
    build_rawrs_feature_bucket_summary,
    build_rawrs_rejection_diagnostics,
    build_rawrs_signal_diagnostics,
    build_rawrs_trade_diagnostics,
    export_rawrs_diagnostic_csvs,
)


LIGHT_REQUIRED_FILES = [
    "trade_log.csv",
    "trade_pnl_log.csv",
    "signal_log.csv",
    "summary.csv",
    "yearly_summary.csv",
    "symbol_summary.csv",
    "equity_curve.csv",
]
FULL_REQUIRED_FILES = [
    *LIGHT_REQUIRED_FILES,
    "rejected_signals.csv",
    "rejection_summary.csv",
    "all_signal_opportunity_log.csv",
    "accepted_vs_rejected_signal_summary.csv",
    "counterfactual_rejected_trade_summary.csv",
    "same_day_candidate_pool_summary.csv",
]
OPTIONAL_INPUT_FILES = [
    "exit_reason_summary.csv",
    "r_multiple_summary.csv",
    "r_multiple_by_exit_reason.csv",
    "r_multiple_by_symbol.csv",
    "r_multiple_by_year.csv",
    "r_multiple_by_symbol_year.csv",
    "trade_signal_context.csv",
    "counterfactual_by_year.csv",
    "counterfactual_by_symbol.csv",
    "ranking_feature_diagnostics.csv",
]
FULL_ROW_LEVEL_FILES = [
    "rejected_signals.csv",
    "all_signal_opportunity_log.csv",
    "same_day_candidate_pool_summary.csv",
]
VALID_MODES = ("light", "full")


@dataclass(frozen=True, slots=True)
class RawrsInputValidationResult:
    """Validation result for an existing strategy output directory."""

    mode: str
    strategy_output_dir: Path
    required_files: list[str]
    missing_required_files: list[str]
    optional_files: list[str]
    missing_optional_files: list[str]
    empty_required_files: list[str]
    warnings: list[str]
    is_valid: bool


def required_files_for_mode(mode: str) -> list[str]:
    """Return required strategy output CSV filenames for a RAWRS mode."""

    if mode == "light":
        return list(LIGHT_REQUIRED_FILES)
    if mode == "full":
        return list(FULL_REQUIRED_FILES)
    raise ValueError("mode must be 'light' or 'full'")


def optional_rawrs_input_files() -> list[str]:
    """Return optional strategy output CSV filenames for RAWRS diagnostics."""

    return list(OPTIONAL_INPUT_FILES)


def validate_rawrs_input_directory(
    strategy_output_dir: Path,
    mode: str,
) -> RawrsInputValidationResult:
    """Validate existing strategy output CSV availability for RAWRS diagnostics."""

    required_files = required_files_for_mode(mode)
    optional_files = optional_rawrs_input_files()
    output_dir = Path(strategy_output_dir)

    missing_required = [
        filename for filename in required_files if not (output_dir / filename).exists()
    ]
    missing_optional = [
        filename for filename in optional_files if not (output_dir / filename).exists()
    ]
    empty_required = [
        filename
        for filename in required_files
        if (output_dir / filename).exists() and _csv_is_empty(output_dir / filename)
    ]

    warnings: list[str] = []
    if missing_optional:
        warnings.append(
            "missing optional RAWRS input files: " + ", ".join(missing_optional)
        )
    if mode == "light":
        warnings.append(
            "light mode cannot answer full rejected, capacity, or same-day "
            "candidate-pool questions"
        )
    if mode == "full":
        empty_full_files = [
            filename for filename in empty_required if filename in FULL_ROW_LEVEL_FILES
        ]
        if empty_full_files:
            warnings.append(
                "full-mode row-level files are empty; this may indicate "
                "all-signal diagnostics were skipped: " + ", ".join(empty_full_files)
            )

    is_valid = not missing_required
    if mode == "full" and any(
        filename in empty_required for filename in FULL_ROW_LEVEL_FILES
    ):
        is_valid = False

    return RawrsInputValidationResult(
        mode=mode,
        strategy_output_dir=output_dir,
        required_files=required_files,
        missing_required_files=missing_required,
        optional_files=optional_files,
        missing_optional_files=missing_optional,
        empty_required_files=empty_required,
        warnings=warnings,
        is_valid=is_valid,
    )


def read_rawrs_input_csvs(
    strategy_output_dir: Path,
    validation_result: RawrsInputValidationResult,
) -> dict[str, pd.DataFrame]:
    """Read required and present optional CSVs from a strategy output directory."""

    frames: dict[str, pd.DataFrame] = {}
    filenames = [
        *validation_result.required_files,
        *[
            filename
            for filename in validation_result.optional_files
            if filename not in validation_result.missing_optional_files
        ],
    ]
    for filename in filenames:
        path = Path(strategy_output_dir) / filename
        if path.exists():
            frames[filename] = _read_csv(path)
    return frames


def build_rawrs_diagnostics_from_csv_frames(
    csv_frames: dict[str, pd.DataFrame],
    rawrs_features_by_symbol: dict[str, pd.DataFrame],
    *,
    mode: str,
) -> dict[str, pd.DataFrame]:
    """Build RAWRS diagnostic DataFrames from loaded strategy CSV frames."""

    required_files_for_mode(mode)
    diagnostics: dict[str, pd.DataFrame] = {}

    signal_log = csv_frames.get("signal_log.csv")
    if signal_log is not None:
        diagnostics["signal_diagnostics"] = build_rawrs_signal_diagnostics(
            signal_log,
            rawrs_features_by_symbol,
            signal_timestamp_col="generated_on",
        )

    trade_log = csv_frames.get("trade_log.csv")
    if trade_log is not None and _has_trade_timestamp_compatibility(trade_log):
        diagnostics["trade_diagnostics"] = build_rawrs_trade_diagnostics(
            trade_log,
            rawrs_features_by_symbol,
            signal_timestamp_col=_trade_timestamp_col(trade_log),
        )

    rejected_signals = csv_frames.get("rejected_signals.csv")
    if mode == "full" and rejected_signals is not None and not rejected_signals.empty:
        diagnostics["rejection_diagnostics"] = build_rawrs_rejection_diagnostics(
            rejected_signals,
            rawrs_features_by_symbol,
            signal_timestamp_col="signal_date",
        )

    feature_bucket_summary = _build_feature_bucket_summary_if_possible(diagnostics)
    if feature_bucket_summary is not None:
        diagnostics["feature_bucket_summary"] = feature_bucket_summary

    return diagnostics


def run_rawrs_diagnostics_from_frames(
    *,
    csv_frames: dict[str, pd.DataFrame],
    rawrs_features_by_symbol: dict[str, pd.DataFrame],
    output_dir: str | Path,
    mode: str,
) -> dict[str, Path]:
    """Build and write RAWRS diagnostics from precomputed feature frames."""

    diagnostics = build_rawrs_diagnostics_from_csv_frames(
        csv_frames,
        rawrs_features_by_symbol,
        mode=mode,
    )
    if not diagnostics:
        raise ValueError("no RAWRS diagnostics could be built from provided frames")
    return export_rawrs_diagnostic_csvs(output_dir=output_dir, **diagnostics)


def parse_args(argv: Iterable[str] | None = None) -> Namespace:
    """Parse standalone RAWRS diagnostic CLI arguments."""

    parser = ArgumentParser(description="Validate standalone I1 RAWRS diagnostics.")
    parser.add_argument("--strategy-output-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--mode", required=True, choices=VALID_MODES)
    parser.add_argument("--feature-prefix", default="rawrs_")
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    """Validate strategy outputs for standalone RAWRS diagnostics."""

    args = parse_args(argv)
    validation = validate_rawrs_input_directory(
        Path(args.strategy_output_dir),
        args.mode,
    )
    for warning in validation.warnings:
        print(f"WARNING: {warning}")
    if not validation.is_valid:
        if validation.missing_required_files:
            print(
                "ERROR: missing required RAWRS input files: "
                + ", ".join(validation.missing_required_files)
            )
        empty_full_files = [
            filename
            for filename in validation.empty_required_files
            if filename in FULL_ROW_LEVEL_FILES
        ]
        if empty_full_files:
            print(
                "ERROR: full-mode row-level files are empty: "
                + ", ".join(empty_full_files)
            )
        return 1

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    read_rawrs_input_csvs(Path(args.strategy_output_dir), validation)
    print(
        "RAWRS input validation passed. External OHLCV/feature loading is deferred; "
        "use run_rawrs_diagnostics_from_frames with precomputed RAWRS features."
    )
    return 0


def _csv_is_empty(path: Path) -> bool:
    try:
        frame = pd.read_csv(path, nrows=1)
    except pd.errors.EmptyDataError:
        return True
    return frame.empty


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _has_trade_timestamp_compatibility(trade_log: pd.DataFrame) -> bool:
    return _trade_timestamp_col(trade_log) is not None


def _trade_timestamp_col(trade_log: pd.DataFrame) -> str | None:
    for column in ("signal_date", "generated_on", "entry_signal_date", "entry_date"):
        if column in trade_log.columns:
            return column
    return None


def _build_feature_bucket_summary_if_possible(
    diagnostics: dict[str, pd.DataFrame],
) -> pd.DataFrame | None:
    trade_diagnostics = diagnostics.get("trade_diagnostics")
    if trade_diagnostics is None or trade_diagnostics.empty:
        return None

    outcome_col = _first_existing_column(
        trade_diagnostics,
        ("exit_reason", "outcome", "trade_outcome"),
    )
    if outcome_col is None:
        return None

    pnl_col = _first_existing_column(trade_diagnostics, ("net_pnl", "gross_pnl"))
    r_col = _first_existing_column(
        trade_diagnostics,
        ("r_multiple", "realized_r", "reward_risk_ratio"),
    )
    try:
        return build_rawrs_feature_bucket_summary(
            trade_diagnostics,
            outcome_col=outcome_col,
            pnl_col=pnl_col,
            r_col=r_col,
        )
    except ValueError:
        return None


def _first_existing_column(
    frame: pd.DataFrame,
    candidates: tuple[str, ...],
) -> str | None:
    for column in candidates:
        if column in frame.columns:
            return column
    return None


if __name__ == "__main__":
    raise SystemExit(main())
