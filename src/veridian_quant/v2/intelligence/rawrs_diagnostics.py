"""Signal-time diagnostics for I1 RAWRS market-structure features.

These helpers attach already-computed RAWRS feature frames to existing records.
They do not generate signals, filter trades, rank candidates, run backtests, or
change portfolio behavior.
"""

import numpy as np
import pandas as pd


RAWRS_FEATURE_TIMESTAMP_COL = "rawrs_feature_timestamp"
_SIGNAL_TIMESTAMP_COLUMNS = (
    "generated_on",
    "signal_date",
    "entry_signal_date",
    "date",
    "timestamp",
)


def normalize_signal_timestamp_column(records: pd.DataFrame) -> pd.Series:
    """Return the first recognized signal timestamp column as datetimes."""

    for column in _SIGNAL_TIMESTAMP_COLUMNS:
        if column in records.columns:
            return normalize_rawrs_join_timestamp(records[column])
    candidates = ", ".join(_SIGNAL_TIMESTAMP_COLUMNS)
    raise ValueError(f"missing signal timestamp column; expected one of: {candidates}")


def normalize_rawrs_join_timestamp(
    values: pd.Series | pd.DatetimeIndex,
) -> pd.Series | pd.DatetimeIndex:
    """Return timezone-naive UTC timestamps for RAWRS as-of joins.

    Timezone-aware inputs are converted to UTC and then made timezone-naive.
    Timezone-naive inputs stay timezone-naive. Series preserve their index,
    order, and name.
    """

    if isinstance(values, pd.DatetimeIndex):
        normalized_index = pd.to_datetime(values, utc=True).tz_localize(None)
        return pd.DatetimeIndex(normalized_index, name=values.name)

    converted = pd.to_datetime(values, utc=True)
    normalized = converted.dt.tz_localize(None)
    return pd.Series(normalized, index=values.index, name=values.name)


def attach_rawrs_features_at_signal_time(
    records: pd.DataFrame,
    rawrs_features: pd.DataFrame,
    *,
    signal_timestamp_col: str | None = None,
    feature_prefix: str = "rawrs_",
) -> pd.DataFrame:
    """Attach RAWRS feature values using exact-or-prior signal-time alignment."""

    signal_timestamps = _signal_timestamps(records, signal_timestamp_col)
    feature_cols = _rawrs_feature_columns(rawrs_features, feature_prefix)
    output = records.copy(deep=True)
    _initialize_rawrs_columns(output, feature_cols)

    if records.empty or rawrs_features.empty:
        return output

    features = rawrs_features.loc[:, feature_cols].copy(deep=True)
    features.index = normalize_rawrs_join_timestamp(
        pd.DatetimeIndex(features.index)
    )
    features = features.loc[features.index.notna()]
    if features.empty:
        return output

    features = features.sort_index(kind="mergesort")
    right = features.reset_index(names=RAWRS_FEATURE_TIMESTAMP_COL)
    left = pd.DataFrame(
        {
            "_rawrs_row_position": np.arange(len(records)),
            "_rawrs_signal_timestamp": signal_timestamps.to_numpy(),
        }
    )
    left = left.loc[left["_rawrs_signal_timestamp"].notna()]
    if left.empty:
        return output

    left = left.sort_values("_rawrs_signal_timestamp", kind="mergesort")
    attached = pd.merge_asof(
        left,
        right,
        left_on="_rawrs_signal_timestamp",
        right_on=RAWRS_FEATURE_TIMESTAMP_COL,
        direction="backward",
    )

    positions = attached["_rawrs_row_position"].to_numpy(dtype=int)
    for column in feature_cols:
        output.iloc[positions, output.columns.get_loc(column)] = attached[
            column
        ].to_numpy()
    output.iloc[
        positions,
        output.columns.get_loc(RAWRS_FEATURE_TIMESTAMP_COL),
    ] = attached[RAWRS_FEATURE_TIMESTAMP_COL].to_numpy()
    return output


def attach_rawrs_features_by_symbol(
    records: pd.DataFrame,
    rawrs_features_by_symbol: dict[str, pd.DataFrame],
    *,
    symbol_col: str = "symbol",
    signal_timestamp_col: str | None = None,
    feature_prefix: str = "rawrs_",
) -> pd.DataFrame:
    """Attach per-symbol RAWRS features while preserving record order and index."""

    if symbol_col not in records.columns:
        raise ValueError(f"missing required symbol column: {symbol_col}")

    feature_cols = _feature_columns_from_mapping(rawrs_features_by_symbol, feature_prefix)
    output = records.copy(deep=True)
    _initialize_rawrs_columns(output, feature_cols)

    for symbol, feature_frame in rawrs_features_by_symbol.items():
        symbol_mask = records[symbol_col] == symbol
        if not symbol_mask.any():
            continue
        attached = attach_rawrs_features_at_signal_time(
            records.loc[symbol_mask],
            feature_frame,
            signal_timestamp_col=signal_timestamp_col,
            feature_prefix=feature_prefix,
        )
        positions = np.flatnonzero(symbol_mask.to_numpy())
        for column in [*feature_cols, RAWRS_FEATURE_TIMESTAMP_COL]:
            if column in attached.columns:
                output.iloc[positions, output.columns.get_loc(column)] = attached[
                    column
                ].to_numpy()
    return output


def summarize_rawrs_feature_by_outcome(
    records: pd.DataFrame,
    *,
    outcome_col: str,
    feature_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Return tidy RAWRS feature distribution summaries grouped by outcome."""

    if outcome_col not in records.columns:
        raise ValueError(f"missing required outcome column: {outcome_col}")
    selected_features = _diagnostic_feature_columns(records, feature_cols)

    rows: list[dict[str, object]] = []
    for outcome, group in records.groupby(outcome_col, dropna=False, sort=True):
        for feature in selected_features:
            values = pd.to_numeric(group[feature], errors="coerce")
            rows.append(
                {
                    "outcome": outcome,
                    "feature": feature,
                    "count": int(values.count()),
                    "mean": values.mean(),
                    "median": values.median(),
                    "std": values.std(),
                    "min": values.min(),
                    "max": values.max(),
                }
            )
    return pd.DataFrame(
        rows,
        columns=["outcome", "feature", "count", "mean", "median", "std", "min", "max"],
    )


def bucket_rawrs_feature(
    records: pd.DataFrame,
    feature_col: str,
    *,
    buckets: int = 5,
) -> pd.Series:
    """Return quantile bucket labels for one RAWRS feature."""

    if not isinstance(buckets, int) or buckets < 1:
        raise ValueError("buckets must be a positive integer")
    if feature_col not in records.columns:
        raise ValueError(f"missing required feature column: {feature_col}")

    values = pd.to_numeric(records[feature_col], errors="coerce")
    bucketed = pd.Series(np.nan, index=records.index, dtype="float64")
    defined = values.dropna()
    unique_count = defined.nunique()
    if unique_count < 2:
        return bucketed

    bucket_count = min(buckets, unique_count)
    bucketed.loc[defined.index] = pd.qcut(
        defined,
        q=bucket_count,
        labels=False,
        duplicates="drop",
    ).astype("float64") + 1.0
    return bucketed


def summarize_outcome_by_rawrs_bucket(
    records: pd.DataFrame,
    *,
    feature_col: str,
    outcome_col: str,
    pnl_col: str | None = None,
    r_col: str | None = None,
    buckets: int = 5,
) -> pd.DataFrame:
    """Return outcome and optional PnL/R diagnostics by RAWRS feature bucket."""

    if outcome_col not in records.columns:
        raise ValueError(f"missing required outcome column: {outcome_col}")
    if pnl_col is not None and pnl_col not in records.columns:
        raise ValueError(f"missing required PnL column: {pnl_col}")
    if r_col is not None and r_col not in records.columns:
        raise ValueError(f"missing required R column: {r_col}")

    bucket_col = "_rawrs_bucket"
    diagnostic = records.copy(deep=True)
    diagnostic[bucket_col] = bucket_rawrs_feature(
        records,
        feature_col,
        buckets=buckets,
    )
    diagnostic = diagnostic.loc[diagnostic[bucket_col].notna()]

    rows: list[dict[str, object]] = []
    outcomes = list(pd.Series(records[outcome_col].dropna().unique()).sort_values())
    for bucket, group in diagnostic.groupby(bucket_col, sort=True):
        row: dict[str, object] = {
            "bucket": int(bucket),
            "count": int(len(group)),
        }
        for outcome in outcomes:
            count = int((group[outcome_col] == outcome).sum())
            key = str(outcome)
            row[f"outcome_{key}_count"] = count
            row[f"outcome_{key}_rate"] = count / len(group) if len(group) else np.nan
        if pnl_col is not None:
            pnl = pd.to_numeric(group[pnl_col], errors="coerce")
            row["total_pnl"] = pnl.sum()
            row["mean_pnl"] = pnl.mean()
            row["median_pnl"] = pnl.median()
        if r_col is not None:
            r_values = pd.to_numeric(group[r_col], errors="coerce")
            row["mean_r"] = r_values.mean()
            row["median_r"] = r_values.median()
        rows.append(row)

    return pd.DataFrame(rows)


def _signal_timestamps(
    records: pd.DataFrame,
    signal_timestamp_col: str | None,
) -> pd.Series:
    if signal_timestamp_col is None:
        return normalize_signal_timestamp_column(records)
    if signal_timestamp_col not in records.columns:
        raise ValueError(f"missing signal timestamp column: {signal_timestamp_col}")
    return normalize_rawrs_join_timestamp(records[signal_timestamp_col])


def _rawrs_feature_columns(
    rawrs_features: pd.DataFrame,
    feature_prefix: str,
) -> list[str]:
    feature_cols = _matching_feature_columns(rawrs_features, feature_prefix)
    if not feature_cols:
        raise ValueError(
            f"no RAWRS feature columns found with prefix: {feature_prefix}"
        )
    return feature_cols


def _feature_columns_from_mapping(
    rawrs_features_by_symbol: dict[str, pd.DataFrame],
    feature_prefix: str,
) -> list[str]:
    feature_cols: list[str] = []
    for feature_frame in rawrs_features_by_symbol.values():
        for column in _matching_feature_columns(feature_frame, feature_prefix):
            if column not in feature_cols:
                feature_cols.append(column)
    if not feature_cols:
        raise ValueError(
            f"no RAWRS feature columns found with prefix: {feature_prefix}"
        )
    return feature_cols


def _matching_feature_columns(
    rawrs_features: pd.DataFrame,
    feature_prefix: str,
) -> list[str]:
    return [
        column
        for column in rawrs_features.columns
        if column.startswith(feature_prefix) and column != RAWRS_FEATURE_TIMESTAMP_COL
    ]


def _diagnostic_feature_columns(
    records: pd.DataFrame,
    feature_cols: list[str] | None,
) -> list[str]:
    if feature_cols is None:
        feature_cols = [
            column
            for column in records.columns
            if column.startswith("rawrs_") and column != RAWRS_FEATURE_TIMESTAMP_COL
        ]
    missing = [column for column in feature_cols if column not in records.columns]
    if missing:
        missing_columns = ", ".join(missing)
        raise ValueError(f"missing RAWRS feature columns: {missing_columns}")
    if not feature_cols:
        raise ValueError("no RAWRS feature columns found")
    return feature_cols


def _initialize_rawrs_columns(output: pd.DataFrame, feature_cols: list[str]) -> None:
    for column in feature_cols:
        output[column] = np.nan
    output[RAWRS_FEATURE_TIMESTAMP_COL] = pd.NaT
