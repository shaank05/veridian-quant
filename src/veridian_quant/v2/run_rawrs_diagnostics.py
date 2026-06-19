"""Standalone CLI for I1 RAWRS diagnostic compatibility checks.

The CLI consumes existing strategy output CSV folders. It does not rerun
strategy backtests, import S1/S2/S3/S4 runners, or modify source outputs.
"""

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

from veridian_quant.v2.data.loaders import SQLAlchemyDailyOHLCVLoader
from veridian_quant.v2.intelligence.rawrs import rawrs_feature_frame
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
DEFAULT_LOOKBACK_BUFFER_DAYS = 365


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


@dataclass(frozen=True, slots=True)
class RawrsRunResult:
    """Result summary for a standalone RAWRS diagnostic run."""

    mode: str
    strategy_output_dir: Path
    output_dir: Path
    generated_paths: dict[str, Path]
    warnings: list[str]
    symbols_requested: list[str]
    symbols_loaded: list[str]
    symbols_missing: list[str]


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
    trade_records = _trade_records_for_diagnostics(csv_frames)
    if trade_records is not None and _has_trade_timestamp_compatibility(trade_records):
        diagnostics["trade_diagnostics"] = build_rawrs_trade_diagnostics(
            trade_records,
            rawrs_features_by_symbol,
            signal_timestamp_col=_trade_timestamp_col(trade_records),
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


def infer_rawrs_symbols(
    csv_frames: dict[str, pd.DataFrame],
    *,
    mode: str,
) -> list[str]:
    """Infer symbols needing RAWRS features from strategy output CSV frames."""

    required_files_for_mode(mode)
    symbols: set[str] = set()
    for filename in _symbol_source_files(mode):
        frame = csv_frames.get(filename)
        if frame is None or "symbol" not in frame.columns:
            continue
        symbols.update(str(symbol).strip().upper() for symbol in frame["symbol"].dropna())
    return sorted(symbol for symbol in symbols if symbol)


def infer_rawrs_date_range(
    csv_frames: dict[str, pd.DataFrame],
    *,
    mode: str,
) -> tuple[date, date]:
    """Infer the RAWRS OHLCV date range needed for loaded strategy outputs."""

    required_files_for_mode(mode)
    timestamps: list[pd.Timestamp] = []
    for filename, columns in _timestamp_source_columns(mode).items():
        frame = csv_frames.get(filename)
        if frame is None:
            continue
        for column in columns:
            if column not in frame.columns:
                continue
            values = pd.to_datetime(frame[column], errors="coerce").dropna()
            timestamps.extend(values.tolist())
    if not timestamps:
        raise ValueError("could not infer RAWRS date range from strategy output CSVs")
    return min(timestamps).date(), max(timestamps).date()


def load_rawrs_ohlcv_by_symbol(
    symbols: Iterable[str],
    start_date: date,
    end_date: date,
    *,
    loader: object | None = None,
    lookback_buffer_days: int = DEFAULT_LOOKBACK_BUFFER_DAYS,
) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Load OHLCV data for symbols using the existing v2 DB loader convention."""

    symbol_list = [str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()]
    data_loader = loader or _create_default_ohlcv_loader(
        lookback_buffer_days=lookback_buffer_days
    )
    loaded: dict[str, pd.DataFrame] = {}
    missing: list[str] = []
    for symbol in symbol_list:
        try:
            data = data_loader.load_symbol(symbol, start_date, end_date)
        except Exception:
            missing.append(symbol)
            continue
        if data is None or data.empty:
            missing.append(symbol)
            continue
        loaded[symbol] = data
    if not loaded:
        raise ValueError("no OHLCV data could be loaded for requested RAWRS symbols")
    return loaded, missing


def compute_rawrs_features_by_symbol(
    ohlcv_by_symbol: Mapping[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """Compute RAWRS feature frames for loaded OHLCV data by symbol."""

    features: dict[str, pd.DataFrame] = {}
    for symbol, data in ohlcv_by_symbol.items():
        feature_input = data.copy(deep=True)
        if "date" in feature_input.columns:
            feature_input["date"] = pd.to_datetime(feature_input["date"])
            feature_input = feature_input.set_index("date")
        feature_input = feature_input.sort_index()
        features[symbol] = rawrs_feature_frame(feature_input)
    return features


def run_rawrs_diagnostics(
    *,
    strategy_output_dir: str | Path,
    output_dir: str | Path,
    mode: str,
    loader: object | None = None,
    lookback_buffer_days: int = DEFAULT_LOOKBACK_BUFFER_DAYS,
) -> RawrsRunResult:
    """Run standalone RAWRS diagnostics from an existing strategy output folder."""

    strategy_dir = Path(strategy_output_dir)
    rawrs_output_dir = Path(output_dir)
    validation = validate_rawrs_input_directory(strategy_dir, mode)
    warnings = list(validation.warnings)
    if not validation.is_valid:
        _raise_validation_error(validation)

    csv_frames = read_rawrs_input_csvs(strategy_dir, validation)
    symbols = infer_rawrs_symbols(csv_frames, mode=mode)
    if not symbols:
        raise ValueError("no symbols found in strategy output CSVs")
    start_date, end_date = infer_rawrs_date_range(csv_frames, mode=mode)

    trade_records = _trade_records_for_diagnostics(csv_frames)
    trade_timestamp = _trade_timestamp_col(trade_records) if trade_records is not None else None
    if trade_timestamp == "entry_date":
        warnings.append(
            "trade diagnostics are entry-time aligned because original signal "
            "timestamps were unavailable in trade records"
        )

    ohlcv_by_symbol, missing_symbols = load_rawrs_ohlcv_by_symbol(
        symbols,
        start_date,
        end_date,
        loader=loader,
        lookback_buffer_days=lookback_buffer_days,
    )
    if missing_symbols:
        warnings.append(
            "missing OHLCV data for symbols: " + ", ".join(sorted(missing_symbols))
        )
    rawrs_features = compute_rawrs_features_by_symbol(ohlcv_by_symbol)
    generated_paths = run_rawrs_diagnostics_from_frames(
        csv_frames=csv_frames,
        rawrs_features_by_symbol=rawrs_features,
        output_dir=rawrs_output_dir,
        mode=mode,
    )
    return RawrsRunResult(
        mode=mode,
        strategy_output_dir=strategy_dir,
        output_dir=rawrs_output_dir,
        generated_paths=generated_paths,
        warnings=warnings,
        symbols_requested=symbols,
        symbols_loaded=sorted(rawrs_features),
        symbols_missing=sorted(missing_symbols),
    )


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
    parser.add_argument(
        "--lookback-buffer-days",
        default=DEFAULT_LOOKBACK_BUFFER_DAYS,
        type=int,
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    """Run standalone RAWRS diagnostics from existing strategy outputs."""

    args = parse_args(argv)
    try:
        result = run_rawrs_diagnostics(
            strategy_output_dir=args.strategy_output_dir,
            output_dir=args.output_dir,
            mode=args.mode,
            lookback_buffer_days=args.lookback_buffer_days,
        )
    except Exception as error:
        print(f"ERROR: {error}")
        return 1
    _print_run_summary(result)
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


def _symbol_source_files(mode: str) -> tuple[str, ...]:
    if mode == "full":
        return ("signal_log.csv", "trade_log.csv", "trade_pnl_log.csv", "rejected_signals.csv")
    return ("signal_log.csv", "trade_log.csv", "trade_pnl_log.csv")


def _timestamp_source_columns(mode: str) -> dict[str, tuple[str, ...]]:
    columns = {
        "signal_log.csv": ("generated_on", "signal_date", "date", "timestamp"),
        "trade_log.csv": (
            "signal_date",
            "generated_on",
            "entry_signal_date",
            "entry_date",
        ),
        "trade_pnl_log.csv": (
            "signal_date",
            "generated_on",
            "entry_signal_date",
            "entry_date",
        ),
    }
    if mode == "full":
        columns["rejected_signals.csv"] = ("signal_date", "generated_on", "date")
    return columns


def _trade_records_for_diagnostics(
    csv_frames: dict[str, pd.DataFrame],
) -> pd.DataFrame | None:
    trade_log = csv_frames.get("trade_log.csv")
    if trade_log is None:
        return None
    trade_records = trade_log.copy(deep=True)
    trade_pnls = csv_frames.get("trade_pnl_log.csv")
    if (
        trade_pnls is not None
        and "trade_id" in trade_records.columns
        and "trade_id" in trade_pnls.columns
    ):
        pnl_columns = [
            column
            for column in trade_pnls.columns
            if column == "trade_id" or column not in trade_records.columns
        ]
        trade_records = trade_records.merge(
            trade_pnls.loc[:, pnl_columns],
            on="trade_id",
            how="left",
        )
    return trade_records


def _create_default_ohlcv_loader(
    *,
    lookback_buffer_days: int,
) -> SQLAlchemyDailyOHLCVLoader:
    try:
        from src.veridian_quant.data.db_client import DatabaseClient
    except ImportError as error:
        raise RuntimeError(
            "Could not import src.veridian_quant.data.db_client.DatabaseClient"
        ) from error

    engine = DatabaseClient().get_engine()
    if engine is None:
        raise RuntimeError("DatabaseClient().get_engine() returned None")
    return SQLAlchemyDailyOHLCVLoader(
        engine=engine,
        lookback_buffer_days=lookback_buffer_days,
    )


def _raise_validation_error(validation: RawrsInputValidationResult) -> None:
    messages: list[str] = []
    if validation.missing_required_files:
        messages.append(
            "missing required RAWRS input files: "
            + ", ".join(validation.missing_required_files)
        )
    empty_full_files = [
        filename
        for filename in validation.empty_required_files
        if filename in FULL_ROW_LEVEL_FILES
    ]
    if empty_full_files:
        messages.append(
            "full-mode row-level files are empty: " + ", ".join(empty_full_files)
        )
    raise ValueError("; ".join(messages) or "RAWRS input validation failed")


def _print_run_summary(result: RawrsRunResult) -> None:
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    print(f"mode: {result.mode}")
    print(f"strategy_output_dir: {result.strategy_output_dir}")
    print(f"rawrs_output_dir: {result.output_dir}")
    print("symbols_requested: " + ", ".join(result.symbols_requested))
    print("symbols_loaded: " + ", ".join(result.symbols_loaded))
    print("symbols_missing: " + ", ".join(result.symbols_missing))
    print("files_generated:")
    for name, path in sorted(result.generated_paths.items()):
        print(f"  {name}: {path}")


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
        ("r_multiple", "realized_r", "rawrs_realized_r"),
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
