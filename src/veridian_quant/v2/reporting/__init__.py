"""Reporting helpers for Veridian Quant v2."""

from veridian_quant.v2.reporting.diagnostics import (
    EXIT_REASON_SUMMARY_COLUMNS,
    REJECTION_SUMMARY_COLUMNS,
    R_MULTIPLE_BY_EXIT_REASON_COLUMNS,
    R_MULTIPLE_BY_SYMBOL_COLUMNS,
    R_MULTIPLE_BY_SYMBOL_YEAR_COLUMNS,
    R_MULTIPLE_BY_YEAR_COLUMNS,
    R_MULTIPLE_SUMMARY_COLUMNS,
    SYMBOL_SUMMARY_COLUMNS,
    YEARLY_SUMMARY_COLUMNS,
    build_exit_reason_summary_rows,
    build_r_multiple_by_exit_reason_rows,
    build_r_multiple_by_symbol_rows,
    build_r_multiple_by_symbol_year_rows,
    build_r_multiple_by_year_rows,
    build_r_multiple_summary_rows,
    build_rejection_summary_rows,
    build_symbol_summary_rows,
    build_yearly_summary_rows,
)
from veridian_quant.v2.reporting.exporters import export_portfolio_backtest_csvs
from veridian_quant.v2.reporting.metrics import (
    PerformanceSummary,
    calculate_performance_summary,
)
from veridian_quant.v2.reporting.progress import (
    NullProgressReporter,
    ProgressReporter,
)

__all__ = [
    "EXIT_REASON_SUMMARY_COLUMNS",
    "NullProgressReporter",
    "PerformanceSummary",
    "ProgressReporter",
    "REJECTION_SUMMARY_COLUMNS",
    "R_MULTIPLE_BY_EXIT_REASON_COLUMNS",
    "R_MULTIPLE_BY_SYMBOL_COLUMNS",
    "R_MULTIPLE_BY_SYMBOL_YEAR_COLUMNS",
    "R_MULTIPLE_BY_YEAR_COLUMNS",
    "R_MULTIPLE_SUMMARY_COLUMNS",
    "SYMBOL_SUMMARY_COLUMNS",
    "YEARLY_SUMMARY_COLUMNS",
    "calculate_performance_summary",
    "build_exit_reason_summary_rows",
    "build_r_multiple_by_exit_reason_rows",
    "build_r_multiple_by_symbol_rows",
    "build_r_multiple_by_symbol_year_rows",
    "build_r_multiple_by_year_rows",
    "build_r_multiple_summary_rows",
    "build_rejection_summary_rows",
    "build_symbol_summary_rows",
    "build_yearly_summary_rows",
    "export_portfolio_backtest_csvs",
]
