from __future__ import annotations

import math

import pandas as pd
import pytest

from veridian_quant.v2.external_models.kronos.output_validity import (
    AMOUNT_NEGATIVE,
    CLOSE_NONPOSITIVE_OR_MISSING,
    HIGH_LT_CLOSE,
    HIGH_LT_LOW,
    HIGH_LT_OPEN,
    INVALID_OUTPUT,
    LOW_GT_CLOSE,
    LOW_GT_OPEN,
    OPEN_NONPOSITIVE_OR_MISSING,
    OUTPUT_VALIDITY_FAILED,
    OUTPUT_VALIDITY_PASS,
    OUTPUT_VALIDITY_WARNING,
    REPAIR_SCOPE_VISUALIZATION_ONLY,
    VALID_OUTPUT,
    VOLUME_NEGATIVE,
    filter_signal_metric_eligible_diagnostics,
    repair_ohlc_for_visualization,
    summarize_forecast_runs,
    summarize_output_validity,
    validate_forecast_paths,
)


def test_valid_row_passes_without_mutating_caller_frame() -> None:
    frame = _paths([_row()])

    result = validate_forecast_paths(frame)

    assert "invalid_ohlc_row" not in frame.columns
    assert result.loc[0, "invalid_ohlc_row"] is False
    assert result.loc[0, "invalid_ohlc_reasons"] == ""
    assert math.isnan(result.loc[0, "invalid_violation_magnitude_abs"])


@pytest.mark.parametrize(
    ("updates", "reason"),
    [
        ({"high": 95, "low": 96}, HIGH_LT_LOW),
        ({"high": 99, "open": 100}, HIGH_LT_OPEN),
        ({"high": 101, "close": 102}, HIGH_LT_CLOSE),
        ({"low": 101, "open": 100}, LOW_GT_OPEN),
        ({"low": 103, "close": 102}, LOW_GT_CLOSE),
    ],
)
def test_core_invalid_relations_are_reported(updates: dict[str, float], reason: str) -> None:
    row = _row()
    row.update(updates)

    result = validate_forecast_paths(_paths([row]))

    assert result.loc[0, "invalid_ohlc_row"] is True
    assert reason in result.loc[0, "invalid_ohlc_reasons"].split(";")
    assert result.loc[0, "invalid_violation_magnitude_abs"] > 0


@pytest.mark.parametrize(
    ("updates", "reason"),
    [
        ({"open": 0}, OPEN_NONPOSITIVE_OR_MISSING),
        ({"close": None}, CLOSE_NONPOSITIVE_OR_MISSING),
        ({"high": "not-a-number"}, "high_nonpositive_or_missing"),
        ({"low": -1}, "low_nonpositive_or_missing"),
    ],
)
def test_nonpositive_missing_or_nonnumeric_required_ohlc_is_invalid(
    updates: dict[str, object],
    reason: str,
) -> None:
    row = _row()
    row.update(updates)

    result = validate_forecast_paths(_paths([row]))

    assert result.loc[0, "invalid_ohlc_row"] is True
    assert reason in result.loc[0, "invalid_ohlc_reasons"].split(";")


def test_optional_negative_volume_and_amount_are_invalid() -> None:
    row = _row(volume=-1, amount=-10)

    result = validate_forecast_paths(_paths([row]))

    reasons = result.loc[0, "invalid_ohlc_reasons"].split(";")
    assert VOLUME_NEGATIVE in reasons
    assert AMOUNT_NEGATIVE in reasons


def test_optional_volume_and_amount_absent_do_not_fail() -> None:
    frame = _paths([_row()]).drop(columns=["volume", "amount"])

    result = validate_forecast_paths(frame)

    assert result.loc[0, "invalid_ohlc_row"] is False


def test_invalid_reason_output_is_deterministic_policy_order() -> None:
    row = _row(open=100, high=90, low=110, close=105)

    result = validate_forecast_paths(_paths([row]))

    assert result.loc[0, "invalid_ohlc_reasons"] == (
        "high_lt_low;high_lt_open;high_lt_close;low_gt_open;low_gt_close"
    )


def test_run_level_status_marks_entire_run_invalid_when_any_path_row_invalid() -> None:
    frame = _paths(
        [
            _row(forecast_step=1),
            _row(forecast_step=2, high=99, open=100),
        ]
    )

    summary = summarize_forecast_runs(frame, group_keys=["symbol", "inference_date", "seed"])

    assert len(summary) == 1
    assert summary.loc[0, "output_status"] == INVALID_OUTPUT
    assert summary.loc[0, "total_path_rows"] == 2
    assert summary.loc[0, "invalid_path_rows"] == 1
    assert summary.loc[0, "invalid_reasons_combined"] == f"{HIGH_LT_OPEN};{HIGH_LT_CLOSE}"


def test_run_level_status_remains_valid_when_all_rows_valid() -> None:
    frame = _paths([_row(forecast_step=1), _row(forecast_step=2)])

    summary = summarize_forecast_runs(frame, group_keys=["symbol", "inference_date", "seed"])

    assert summary.loc[0, "output_status"] == VALID_OUTPUT
    assert summary.loc[0, "invalid_path_rows"] == 0


def test_run_summary_raises_clear_error_for_missing_group_key() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        summarize_forecast_runs(_paths([_row()]), group_keys=["missing_key"])


def test_diagnostic_summary_passes_with_zero_invalid_rows() -> None:
    run_summary = summarize_forecast_runs(_paths([_row()]), group_keys=["symbol", "inference_date", "seed"])

    summary = summarize_output_validity(run_summary)

    assert summary.loc[0, "output_validity_status"] == OUTPUT_VALIDITY_PASS
    assert summary.loc[0, "invalid_forecast_runs"] == 0


def test_diagnostic_summary_warns_for_small_nonzero_invalid_path_rate() -> None:
    rows = [_row(run_id=f"r{i}", seed=i) for i in range(100)]
    rows[0]["high"] = 98
    rows[0]["open"] = 99
    run_summary = summarize_forecast_runs(_paths(rows), group_keys=["run_id"])

    summary = summarize_output_validity(run_summary)

    assert summary.loc[0, "output_validity_status"] == OUTPUT_VALIDITY_WARNING
    assert summary.loc[0, "invalid_path_row_rate_pct"] == pytest.approx(1.0)


def test_diagnostic_summary_fails_when_invalid_forecast_run_rate_exceeds_threshold() -> None:
    rows = [
        _row(run_id="valid_1", seed=1),
        _row(run_id="valid_2", seed=2),
        _row(run_id="invalid", seed=3, high=99, open=100),
    ]
    run_summary = summarize_forecast_runs(_paths(rows), group_keys=["run_id"])

    summary = summarize_output_validity(run_summary)

    assert summary.loc[0, "output_validity_status"] == OUTPUT_VALIDITY_FAILED
    assert summary.loc[0, "invalid_forecast_run_rate_pct"] == pytest.approx(100 / 3)


def test_diagnostic_summary_fails_when_invalid_path_row_rate_exceeds_threshold() -> None:
    rows = [_row(run_id="same", forecast_step=i) for i in range(20)]
    rows[0]["high"] = 99
    rows[0]["open"] = 100
    rows[1]["high"] = 98
    rows[1]["open"] = 100
    run_summary = summarize_forecast_runs(_paths(rows), group_keys=["run_id"])

    summary = summarize_output_validity(run_summary)

    assert summary.loc[0, "output_validity_status"] == OUTPUT_VALIDITY_FAILED
    assert summary.loc[0, "invalid_path_row_rate_pct"] == pytest.approx(10.0)


def test_signal_eligibility_excludes_invalid_runs_and_reports_counts() -> None:
    paths = _paths(
        [
            _row(run_id="valid", seed=1),
            _row(run_id="invalid", seed=2, high=99, open=100),
        ]
    )
    run_summary = summarize_forecast_runs(paths, group_keys=["run_id"])
    diagnostics = pd.DataFrame(
        [
            {"run_id": "valid", "pred_close_return": 0.01},
            {"run_id": "invalid", "pred_close_return": -0.02},
        ]
    )

    result = filter_signal_metric_eligible_diagnostics(run_summary, diagnostics, group_keys=["run_id"])

    assert result.planned_rows == 2
    assert result.valid_rows == 1
    assert result.excluded_invalid_rows == 1
    assert result.invalid_exclusion_rate_pct == pytest.approx(50.0)
    assert result.eligible_diagnostics["run_id"].tolist() == ["valid"]


def test_repair_helper_preserves_raw_columns_and_adds_visualization_only_fields() -> None:
    frame = _paths([_row(open=100, high=99, low=101, close=102)])

    repaired = repair_ohlc_for_visualization(frame)

    assert repaired.loc[0, "high"] == 99
    assert repaired.loc[0, "low"] == 101
    assert repaired.loc[0, "repaired_high"] == 102
    assert repaired.loc[0, "repaired_low"] == 99
    assert repaired.loc[0, "repair_applied"] is True
    assert repaired.loc[0, "repair_scope"] == REPAIR_SCOPE_VISUALIZATION_ONLY


def _paths(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _row(
    *,
    run_id: str = "run_1",
    symbol: str = "HDFCBANK",
    inference_date: str = "2024-01-15",
    seed: int = 7,
    config_name: str = "deterministic_low_randomness",
    forecast_step: int = 1,
    open: object = 100.0,
    high: object = 105.0,
    low: object = 95.0,
    close: object = 102.0,
    volume: object = 1000.0,
    amount: object = 102000.0,
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "symbol": symbol,
        "inference_date": inference_date,
        "seed": seed,
        "config_name": config_name,
        "forecast_step": forecast_step,
        "open": open,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "amount": amount,
    }
