"""Output-validity policy helpers for Kronos forecast diagnostics.

These helpers implement the Phase 37Q policy only. They do not run Kronos,
load model weights, compute alpha metrics, or create trading rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


KRONOS_OUTPUT_VALIDITY_POLICY_VERSION = "37Q_v1"

VALID_OUTPUT = "VALID_OUTPUT"
INVALID_OUTPUT = "INVALID_OUTPUT"

OUTPUT_VALIDITY_PASS = "OUTPUT_VALIDITY_PASS"
OUTPUT_VALIDITY_WARNING = "OUTPUT_VALIDITY_WARNING"
OUTPUT_VALIDITY_FAILED = "OUTPUT_VALIDITY_FAILED"

INVALID_FORECAST_RUN_RATE_FAIL_PCT = 5.0
INVALID_PATH_ROW_RATE_WARNING_PCT = 1.0
INVALID_PATH_ROW_RATE_FAIL_PCT = 5.0

REPAIR_SCOPE_VISUALIZATION_ONLY = "VISUALIZATION_ONLY"

REQUIRED_OHLC_COLUMNS: tuple[str, ...] = ("open", "high", "low", "close")
OPTIONAL_NONNEGATIVE_COLUMNS: tuple[str, ...] = ("volume", "amount")
DEFAULT_RUN_KEY_CANDIDATES: tuple[str, ...] = (
    "run_id",
    "config_name",
    "seed",
    "symbol",
    "inference_date",
)

OPEN_NONPOSITIVE_OR_MISSING = "open_nonpositive_or_missing"
HIGH_NONPOSITIVE_OR_MISSING = "high_nonpositive_or_missing"
LOW_NONPOSITIVE_OR_MISSING = "low_nonpositive_or_missing"
CLOSE_NONPOSITIVE_OR_MISSING = "close_nonpositive_or_missing"
HIGH_LT_LOW = "high_lt_low"
HIGH_LT_OPEN = "high_lt_open"
HIGH_LT_CLOSE = "high_lt_close"
LOW_GT_OPEN = "low_gt_open"
LOW_GT_CLOSE = "low_gt_close"
VOLUME_NEGATIVE = "volume_negative"
AMOUNT_NEGATIVE = "amount_negative"

INVALID_REASON_NAMES: tuple[str, ...] = (
    OPEN_NONPOSITIVE_OR_MISSING,
    HIGH_NONPOSITIVE_OR_MISSING,
    LOW_NONPOSITIVE_OR_MISSING,
    CLOSE_NONPOSITIVE_OR_MISSING,
    HIGH_LT_LOW,
    HIGH_LT_OPEN,
    HIGH_LT_CLOSE,
    LOW_GT_OPEN,
    LOW_GT_CLOSE,
    VOLUME_NEGATIVE,
    AMOUNT_NEGATIVE,
)


@dataclass(frozen=True)
class EligibilityResult:
    """Filtered diagnostics plus explicit invalid-output exclusion counts."""

    eligible_diagnostics: pd.DataFrame
    planned_rows: int
    valid_rows: int
    excluded_invalid_rows: int
    invalid_exclusion_rate_pct: float


def validate_forecast_paths(paths: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with row-level Kronos OHLC validity policy fields.

    Required OHLC columns must be numeric and positive. Optional `volume` and
    `amount` columns are checked only when the column exists and the row value is
    not missing. The caller's DataFrame is not mutated.
    """

    _require_columns(paths, REQUIRED_OHLC_COLUMNS)
    result = paths.copy()
    numeric = {
        column: pd.to_numeric(result[column], errors="coerce")
        for column in REQUIRED_OHLC_COLUMNS
    }
    for column in OPTIONAL_NONNEGATIVE_COLUMNS:
        if column in result.columns:
            numeric[column] = pd.to_numeric(result[column], errors="coerce")

    invalid_flags: list[bool] = []
    reason_values: list[str] = []
    magnitude_abs_values: list[float] = []
    magnitude_pct_values: list[float] = []

    for idx in result.index:
        reasons: list[str] = []
        magnitudes: list[float] = []

        open_value = _number_at(numeric["open"], idx)
        high_value = _number_at(numeric["high"], idx)
        low_value = _number_at(numeric["low"], idx)
        close_value = _number_at(numeric["close"], idx)

        _add_positive_check(reasons, magnitudes, OPEN_NONPOSITIVE_OR_MISSING, open_value)
        _add_positive_check(reasons, magnitudes, HIGH_NONPOSITIVE_OR_MISSING, high_value)
        _add_positive_check(reasons, magnitudes, LOW_NONPOSITIVE_OR_MISSING, low_value)
        _add_positive_check(reasons, magnitudes, CLOSE_NONPOSITIVE_OR_MISSING, close_value)

        _add_relation_check(reasons, magnitudes, HIGH_LT_LOW, high_value, low_value, high_value - low_value)
        _add_relation_check(reasons, magnitudes, HIGH_LT_OPEN, high_value, open_value, high_value - open_value)
        _add_relation_check(reasons, magnitudes, HIGH_LT_CLOSE, high_value, close_value, high_value - close_value)
        _add_relation_check(reasons, magnitudes, LOW_GT_OPEN, open_value, low_value, open_value - low_value)
        _add_relation_check(reasons, magnitudes, LOW_GT_CLOSE, close_value, low_value, close_value - low_value)

        if "volume" in numeric:
            _add_optional_nonnegative_check(reasons, magnitudes, VOLUME_NEGATIVE, result.at[idx, "volume"], _number_at(numeric["volume"], idx))
        if "amount" in numeric:
            _add_optional_nonnegative_check(reasons, magnitudes, AMOUNT_NEGATIVE, result.at[idx, "amount"], _number_at(numeric["amount"], idx))

        magnitude_abs = max(magnitudes) if magnitudes else np.nan
        if _is_finite(close_value) and close_value != 0 and _is_finite(magnitude_abs):
            magnitude_pct = magnitude_abs / abs(close_value) * 100.0
        else:
            magnitude_pct = np.nan

        ordered_reasons = [reason for reason in INVALID_REASON_NAMES if reason in reasons]
        invalid_flags.append(bool(ordered_reasons))
        reason_values.append(";".join(ordered_reasons))
        magnitude_abs_values.append(float(magnitude_abs) if _is_finite(magnitude_abs) else np.nan)
        magnitude_pct_values.append(float(magnitude_pct) if _is_finite(magnitude_pct) else np.nan)

    result["invalid_ohlc_row"] = pd.Series(invalid_flags, index=result.index, dtype=object)
    result["invalid_ohlc_reasons"] = reason_values
    result["invalid_violation_magnitude_abs"] = magnitude_abs_values
    result["invalid_violation_magnitude_pct_close"] = magnitude_pct_values
    return result


def summarize_forecast_runs(
    paths: pd.DataFrame,
    group_keys: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Apply run-level invalid-output policy to validated forecast paths."""

    validated = _ensure_validated(paths)
    keys = _resolve_group_keys(validated, group_keys)
    rows: list[dict[str, object]] = []
    for key_values, group in validated.groupby(list(keys), dropna=False, sort=True):
        if not isinstance(key_values, tuple):
            key_values = (key_values,)
        invalid = group.loc[group["invalid_ohlc_row"].astype(bool)]
        invalid_reasons = _combined_reasons(invalid["invalid_ohlc_reasons"])
        rows.append(
            {
                **dict(zip(keys, key_values, strict=True)),
                "total_path_rows": int(len(group)),
                "invalid_path_rows": int(len(invalid)),
                "invalid_path_rate_pct": _pct(len(invalid), len(group)),
                "output_status": INVALID_OUTPUT if len(invalid) else VALID_OUTPUT,
                "invalid_reasons_combined": invalid_reasons,
                "max_violation_magnitude_abs": _max_or_nan(group["invalid_violation_magnitude_abs"]),
                "max_violation_magnitude_pct_close": _max_or_nan(group["invalid_violation_magnitude_pct_close"]),
            }
        )
    return pd.DataFrame(rows)


def summarize_output_validity(run_summary: pd.DataFrame) -> pd.DataFrame:
    """Return diagnostic-level output-validity summary from run-level data."""

    required = ("output_status", "total_path_rows", "invalid_path_rows")
    _require_columns(run_summary, required)
    total_runs = int(len(run_summary))
    invalid_runs = int((run_summary["output_status"] == INVALID_OUTPUT).sum())
    total_rows = int(pd.to_numeric(run_summary["total_path_rows"], errors="coerce").fillna(0).sum())
    invalid_rows = int(pd.to_numeric(run_summary["invalid_path_rows"], errors="coerce").fillna(0).sum())
    invalid_run_rate = _pct(invalid_runs, total_runs)
    invalid_row_rate = _pct(invalid_rows, total_rows)
    status = _output_validity_status(invalid_run_rate, invalid_row_rate, invalid_rows)
    return pd.DataFrame(
        [
            {
                "policy_version": KRONOS_OUTPUT_VALIDITY_POLICY_VERSION,
                "total_forecast_runs": total_runs,
                "valid_forecast_runs": total_runs - invalid_runs,
                "invalid_forecast_runs": invalid_runs,
                "invalid_forecast_run_rate_pct": invalid_run_rate,
                "total_path_rows": total_rows,
                "invalid_path_rows": invalid_rows,
                "invalid_path_row_rate_pct": invalid_row_rate,
                "output_validity_status": status,
            }
        ]
    )


def filter_signal_metric_eligible_diagnostics(
    run_summary: pd.DataFrame,
    diagnostics: pd.DataFrame,
    group_keys: Sequence[str] | None = None,
) -> EligibilityResult:
    """Return diagnostics eligible for signal metrics under the validity policy.

    This function does not compute alpha, trading, ranking, or performance
    metrics. It only excludes diagnostics rows whose forecast run is marked
    `INVALID_OUTPUT`, while returning explicit exclusion counts.
    """

    _require_columns(run_summary, ("output_status",))
    keys = _resolve_group_keys_for_join(run_summary, diagnostics, group_keys)
    valid_keys = run_summary.loc[run_summary["output_status"] == VALID_OUTPUT, list(keys)].drop_duplicates()
    eligible = diagnostics.merge(valid_keys, on=list(keys), how="inner")
    planned = int(len(diagnostics))
    valid = int(len(eligible))
    excluded = planned - valid
    return EligibilityResult(
        eligible_diagnostics=eligible,
        planned_rows=planned,
        valid_rows=valid,
        excluded_invalid_rows=excluded,
        invalid_exclusion_rate_pct=_pct(excluded, planned),
    )


def repair_ohlc_for_visualization(paths: pd.DataFrame) -> pd.DataFrame:
    """Return a visualization-only OHLC repair view without overwriting raw OHLC.

    This helper is opt-in and preserves raw `open`, `high`, `low`, and `close`
    columns. It adds `repaired_high`, `repaired_low`, `repair_applied`, and
    `repair_scope = "VISUALIZATION_ONLY"`.

    The repaired values are not approved for signal metrics, trading logic,
    stops, targets, entries, or production behavior unless a later phase
    separately approves and labels that use.
    """

    _require_columns(paths, REQUIRED_OHLC_COLUMNS)
    result = paths.copy()
    ohlc = result.loc[:, REQUIRED_OHLC_COLUMNS].apply(pd.to_numeric, errors="coerce")
    result["repaired_high"] = ohlc.max(axis=1, skipna=True)
    result["repaired_low"] = ohlc.min(axis=1, skipna=True)
    high = pd.to_numeric(result["high"], errors="coerce")
    low = pd.to_numeric(result["low"], errors="coerce")
    repair_applied = (
        (result["repaired_high"].notna() & high.notna() & (result["repaired_high"] != high))
        | (result["repaired_low"].notna() & low.notna() & (result["repaired_low"] != low))
    )
    result["repair_applied"] = pd.Series(repair_applied.tolist(), index=result.index, dtype=object)
    result["repair_scope"] = REPAIR_SCOPE_VISUALIZATION_ONLY
    return result


def _ensure_validated(paths: pd.DataFrame) -> pd.DataFrame:
    required = {"invalid_ohlc_row", "invalid_ohlc_reasons", "invalid_violation_magnitude_abs", "invalid_violation_magnitude_pct_close"}
    if required.issubset(paths.columns):
        return paths.copy()
    return validate_forecast_paths(paths)


def _resolve_group_keys(frame: pd.DataFrame, group_keys: Sequence[str] | None) -> tuple[str, ...]:
    if group_keys is not None:
        keys = tuple(group_keys)
        _require_columns(frame, keys)
        return keys
    keys = tuple(key for key in DEFAULT_RUN_KEY_CANDIDATES if key in frame.columns)
    if not keys:
        raise ValueError("no default forecast-run keys found; pass group_keys explicitly")
    return keys


def _resolve_group_keys_for_join(
    run_summary: pd.DataFrame,
    diagnostics: pd.DataFrame,
    group_keys: Sequence[str] | None,
) -> tuple[str, ...]:
    if group_keys is not None:
        keys = tuple(group_keys)
    else:
        keys = tuple(key for key in DEFAULT_RUN_KEY_CANDIDATES if key in run_summary.columns and key in diagnostics.columns)
    if not keys:
        raise ValueError("no common forecast-run keys found; pass group_keys explicitly")
    _require_columns(run_summary, keys)
    _require_columns(diagnostics, keys)
    return keys


def _require_columns(frame: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"missing required columns: {missing}")


def _number_at(series: pd.Series, index) -> float:
    value = series.at[index]
    return float(value) if _is_finite(value) else np.nan


def _is_finite(value: object) -> bool:
    try:
        return bool(np.isfinite(value))
    except TypeError:
        return False


def _add_positive_check(reasons: list[str], magnitudes: list[float], reason: str, value: float) -> None:
    if not _is_finite(value) or value <= 0:
        reasons.append(reason)
        if _is_finite(value):
            magnitudes.append(float(abs(value)))


def _add_relation_check(
    reasons: list[str],
    magnitudes: list[float],
    reason: str,
    left_value: float,
    right_value: float,
    difference: float,
) -> None:
    if _is_finite(left_value) and _is_finite(right_value) and difference < 0:
        reasons.append(reason)
        magnitudes.append(float(abs(difference)))


def _add_optional_nonnegative_check(
    reasons: list[str],
    magnitudes: list[float],
    reason: str,
    raw_value: object,
    numeric_value: float,
) -> None:
    if pd.isna(raw_value):
        return
    if not _is_finite(numeric_value) or numeric_value < 0:
        reasons.append(reason)
        if _is_finite(numeric_value):
            magnitudes.append(float(abs(numeric_value)))


def _combined_reasons(reason_series: pd.Series) -> str:
    found = set()
    for value in reason_series.dropna().astype(str):
        found.update(reason for reason in value.split(";") if reason)
    return ";".join(reason for reason in INVALID_REASON_NAMES if reason in found)


def _max_or_nan(series: pd.Series) -> float:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    return float(numeric.max()) if not numeric.empty else np.nan


def _pct(numerator: int | float, denominator: int | float) -> float:
    return float(numerator / denominator * 100.0) if denominator else 0.0


def _output_validity_status(invalid_run_rate: float, invalid_row_rate: float, invalid_rows: int) -> str:
    if (
        invalid_run_rate > INVALID_FORECAST_RUN_RATE_FAIL_PCT
        or invalid_row_rate > INVALID_PATH_ROW_RATE_FAIL_PCT
    ):
        return OUTPUT_VALIDITY_FAILED
    if invalid_rows > 0 or invalid_row_rate > INVALID_PATH_ROW_RATE_WARNING_PCT:
        return OUTPUT_VALIDITY_WARNING
    return OUTPUT_VALIDITY_PASS
