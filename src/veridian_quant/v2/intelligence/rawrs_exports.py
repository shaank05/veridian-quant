"""Standalone CSV exports for I1 RAWRS diagnostics.

This module writes diagnostic-only RAWRS outputs from already-prepared
DataFrames. It does not import strategy, backtesting, runner, portfolio, or
standard reporting exporter modules.
"""

from pathlib import Path

import pandas as pd

from veridian_quant.v2.intelligence.rawrs_diagnostics import (
    RAWRS_FEATURE_TIMESTAMP_COL,
    attach_rawrs_features_by_symbol,
    summarize_outcome_by_rawrs_bucket,
)


RAWRS_DIAGNOSTIC_FILENAMES = {
    "signal_diagnostics": "rawrs_signal_diagnostics.csv",
    "trade_diagnostics": "rawrs_trade_diagnostics.csv",
    "rejection_diagnostics": "rawrs_rejection_diagnostics.csv",
    "feature_bucket_summary": "rawrs_feature_bucket_summary.csv",
    "feature_by_year_summary": "rawrs_feature_by_year_summary.csv",
    "feature_by_strategy_summary": "rawrs_feature_by_strategy_summary.csv",
    "same_day_candidate_pool_summary": "rawrs_same_day_candidate_pool_summary.csv",
}
RAWRS_REALIZED_R_COL = "rawrs_realized_r"


def export_rawrs_diagnostic_csvs(
    *,
    output_dir: str | Path,
    signal_diagnostics: pd.DataFrame | None = None,
    trade_diagnostics: pd.DataFrame | None = None,
    rejection_diagnostics: pd.DataFrame | None = None,
    feature_bucket_summary: pd.DataFrame | None = None,
    feature_by_year_summary: pd.DataFrame | None = None,
    feature_by_strategy_summary: pd.DataFrame | None = None,
    same_day_candidate_pool_summary: pd.DataFrame | None = None,
) -> dict[str, Path]:
    """Write provided RAWRS diagnostic DataFrames to deterministic CSV paths."""

    frames = {
        "signal_diagnostics": signal_diagnostics,
        "trade_diagnostics": trade_diagnostics,
        "rejection_diagnostics": rejection_diagnostics,
        "feature_bucket_summary": feature_bucket_summary,
        "feature_by_year_summary": feature_by_year_summary,
        "feature_by_strategy_summary": feature_by_strategy_summary,
        "same_day_candidate_pool_summary": same_day_candidate_pool_summary,
    }
    provided = {name: frame for name, frame in frames.items() if frame is not None}
    if not provided:
        raise ValueError("at least one RAWRS diagnostic DataFrame must be provided")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    written: dict[str, Path] = {}
    for name, frame in provided.items():
        csv_path = output_path / RAWRS_DIAGNOSTIC_FILENAMES[name]
        frame.copy(deep=True).to_csv(csv_path, index=False)
        written[name] = csv_path
    return written


def build_rawrs_trade_diagnostics(
    trades: pd.DataFrame,
    rawrs_features_by_symbol: dict[str, pd.DataFrame],
    *,
    symbol_col: str = "symbol",
    signal_timestamp_col: str | None = None,
) -> pd.DataFrame:
    """Attach signal-time RAWRS features to trade-level records."""

    attached = attach_rawrs_features_by_symbol(
        trades,
        rawrs_features_by_symbol,
        symbol_col=symbol_col,
        signal_timestamp_col=signal_timestamp_col,
    )
    return ensure_rawrs_realized_r(attached)


def build_rawrs_signal_diagnostics(
    signals: pd.DataFrame,
    rawrs_features_by_symbol: dict[str, pd.DataFrame],
    *,
    symbol_col: str = "symbol",
    signal_timestamp_col: str | None = None,
) -> pd.DataFrame:
    """Attach signal-time RAWRS features to signal-level records."""

    return attach_rawrs_features_by_symbol(
        signals,
        rawrs_features_by_symbol,
        symbol_col=symbol_col,
        signal_timestamp_col=signal_timestamp_col,
    )


def build_rawrs_rejection_diagnostics(
    rejections: pd.DataFrame,
    rawrs_features_by_symbol: dict[str, pd.DataFrame],
    *,
    symbol_col: str = "symbol",
    signal_timestamp_col: str | None = None,
) -> pd.DataFrame:
    """Attach signal-time RAWRS features to rejected-signal records."""

    return attach_rawrs_features_by_symbol(
        rejections,
        rawrs_features_by_symbol,
        symbol_col=symbol_col,
        signal_timestamp_col=signal_timestamp_col,
    )


def build_rawrs_feature_bucket_summary(
    records: pd.DataFrame,
    *,
    outcome_col: str,
    feature_cols: list[str] | None = None,
    pnl_col: str | None = None,
    r_col: str | None = None,
    buckets: int = 5,
) -> pd.DataFrame:
    """Build combined bucket summaries for selected RAWRS feature columns."""

    diagnostic_records = ensure_rawrs_realized_r(records)
    selected_features = _usable_rawrs_feature_columns(diagnostic_records, feature_cols)
    selected_r_col = _select_realized_r_column(diagnostic_records, r_col)
    summaries: list[pd.DataFrame] = []
    for feature in selected_features:
        summary = summarize_outcome_by_rawrs_bucket(
            diagnostic_records,
            feature_col=feature,
            outcome_col=outcome_col,
            pnl_col=pnl_col,
            r_col=selected_r_col,
            buckets=buckets,
        )
        summary.insert(0, "feature", feature)
        summaries.append(summary)

    if not summaries:
        return pd.DataFrame(columns=["feature"])
    return pd.concat(summaries, ignore_index=True)


def ensure_rawrs_realized_r(records: pd.DataFrame) -> pd.DataFrame:
    """Return records with RAWRS-local realized R when it can be derived."""

    output = records.copy(deep=True)
    if "r_multiple" in output.columns or "realized_r" in output.columns:
        return output
    if "net_pnl" not in output.columns or "initial_risk_amount" not in output.columns:
        return output

    net_pnl = pd.to_numeric(output["net_pnl"], errors="coerce")
    initial_risk = pd.to_numeric(output["initial_risk_amount"], errors="coerce")
    safe_risk = initial_risk.where(initial_risk != 0)
    output[RAWRS_REALIZED_R_COL] = net_pnl / safe_risk
    return output


def _usable_rawrs_feature_columns(
    records: pd.DataFrame,
    feature_cols: list[str] | None,
) -> list[str]:
    if feature_cols is None:
        feature_cols = [
            column
            for column in records.columns
            if column.startswith("rawrs_")
            and column not in (RAWRS_FEATURE_TIMESTAMP_COL, RAWRS_REALIZED_R_COL)
        ]

    missing = [column for column in feature_cols if column not in records.columns]
    if missing:
        missing_columns = ", ".join(missing)
        raise ValueError(f"missing RAWRS feature columns: {missing_columns}")

    usable = [
        column
        for column in feature_cols
        if pd.to_numeric(records[column], errors="coerce").notna().any()
    ]
    if not usable:
        raise ValueError("no usable RAWRS feature columns found")
    return usable


def _select_realized_r_column(
    records: pd.DataFrame,
    requested_r_col: str | None,
) -> str | None:
    if requested_r_col in ("r_multiple", "realized_r", RAWRS_REALIZED_R_COL):
        if requested_r_col in records.columns:
            return requested_r_col
    for column in ("r_multiple", "realized_r", RAWRS_REALIZED_R_COL):
        if column in records.columns:
            return column
    return None
