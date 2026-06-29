"""Read-only cross-strategy risk input diagnostic audit utilities.

This module consumes existing retained strategy report folders and static config
CSVs. It does not run strategies, alter backtests, implement filters, or change
position sizing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Iterable, Literal, Mapping

import numpy as np
import pandas as pd
from sqlalchemy import text


StrategyLabel = Literal["S1", "S2", "S3", "S4", "S5"]

STRATEGY_LABELS: tuple[StrategyLabel, ...] = ("S1", "S2", "S3", "S4", "S5")

DEFAULT_STRATEGY_DIRS: dict[str, Path] = {
    "S1": Path("reports/v2/s1_2020_2026_research200_baseline_all_signal_diagnostics"),
    "S2": Path("reports/v2/s2_markov_2020_2026_research200_exclude_ret_down_full_diagnostics"),
    "S3": Path("reports/v2/s3_trend_pullback_2020_2026_research200_strong_trend_above_sma50_v1"),
    "S4": Path("reports/v2/s4/raw_baselines/research200_atr_compression_v1"),
    "S5": Path("reports/v2/s5_momentum/research200_dual_momentum_63_126d_v1"),
}
DEFAULT_UNIVERSE_CSV = Path("config/universes/research/nse_eq_research_200_2018_2026.csv")
DEFAULT_CLASSIFICATION_CSV = Path("config/universes/research/nse_eq_research_200_static_classification.csv")
DEFAULT_OUTPUT_DIR = Path("reports/v2/phase_36b_cross_strategy_risk_diagnostic_audit")

REQUIRED_ARTIFACTS = (
    "trade_log.csv",
    "trade_pnl_log.csv",
    "equity_curve.csv",
    "symbol_summary.csv",
    "yearly_summary.csv",
    "exit_reason_summary.csv",
    "rejection_summary.csv",
    "rejected_signals.csv",
    "r_multiple_summary.csv",
    "r_multiple_by_symbol.csv",
    "r_multiple_by_symbol_year.csv",
    "trade_signal_context.csv",
)
OPTIONAL_ARTIFACTS = (
    "all_signal_opportunity_log.csv",
    "accepted_vs_rejected_signal_summary.csv",
)

OUTPUT_COLUMNS: dict[str, list[str]] = {
    "risk_input_inventory.csv": [
        "strategy",
        "artifact",
        "path",
        "exists",
        "rows",
        "key_columns_present",
        "notes",
    ],
    "risk_join_coverage_by_strategy.csv": [
        "strategy",
        "trade_count",
        "universe_joined_trades",
        "universe_join_coverage_pct",
        "classification_joined_trades",
        "classification_join_coverage_pct",
        "unique_symbols",
        "universe_joined_symbols",
        "classification_joined_symbols",
        "liquidity_bucket_available_pct",
        "sector_available_pct",
        "market_cap_bucket_available_pct",
        "notes",
    ],
    "liquidity_bucket_performance.csv": [
        "strategy",
        "liquidity_bucket",
        "trades",
        "net_pnl",
        "gross_profit",
        "gross_loss",
        "profit_factor",
        "win_rate_pct",
        "avg_net_pnl",
        "median_net_pnl",
        "avg_r_multiple",
        "median_r_multiple",
        "stop_gap_trades",
        "stop_gap_net_pnl",
        "notes",
    ],
    "liquidity_bucket_by_year.csv": [
        "strategy",
        "year",
        "liquidity_bucket",
        "trades",
        "net_pnl",
        "profit_factor",
        "win_rate_pct",
        "avg_net_pnl",
        "median_net_pnl",
        "avg_r_multiple",
        "median_r_multiple",
    ],
    "symbol_concentration_summary.csv": [
        "strategy",
        "trades",
        "net_pnl",
        "unique_symbols",
        "top_5_winner_pnl",
        "top_5_winner_pnl_to_total_pnl",
        "top_10_winner_pnl",
        "top_10_winner_pnl_to_total_pnl",
        "top_5_loser_pnl",
        "top_10_loser_pnl",
        "worst_symbol_pnl",
        "best_symbol_pnl",
        "top_5_trade_count_share_pct",
        "notes",
    ],
    "top_symbol_contributors.csv": [
        "strategy",
        "side",
        "rank",
        "symbol",
        "trades",
        "net_pnl",
        "avg_net_pnl",
        "median_net_pnl",
        "win_rate_pct",
        "avg_r_multiple",
        "liquidity_bucket",
        "sector",
        "notes",
    ],
    "gap_exit_stress_summary.csv": [
        "strategy",
        "exit_reason",
        "trades",
        "net_pnl",
        "avg_net_pnl",
        "median_net_pnl",
        "avg_r_multiple",
        "median_r_multiple",
        "share_of_strategy_trades_pct",
        "share_of_strategy_pnl_pct",
        "liquidity_bucket_mix_summary",
        "notes",
    ],
    "gap_exit_by_year.csv": [
        "strategy",
        "year",
        "exit_reason",
        "trades",
        "net_pnl",
        "avg_net_pnl",
        "median_net_pnl",
        "avg_r_multiple",
        "median_r_multiple",
    ],
    "pre_entry_gap_context_summary.csv": [
        "strategy",
        "pre_entry_gap_bucket",
        "trades",
        "net_pnl",
        "profit_factor",
        "win_rate_pct",
        "avg_net_pnl",
        "median_net_pnl",
        "avg_r_multiple",
        "median_r_multiple",
    ],
    "atr_volatility_context_summary.csv": [
        "strategy",
        "atr_pct_bucket",
        "trades",
        "net_pnl",
        "profit_factor",
        "win_rate_pct",
        "avg_net_pnl",
        "median_net_pnl",
        "avg_r_multiple",
        "median_r_multiple",
    ],
    "benchmark_regime_performance.csv": [
        "strategy",
        "benchmark_column_used",
        "benchmark_regime_bucket",
        "trades",
        "net_pnl",
        "profit_factor",
        "win_rate_pct",
        "avg_net_pnl",
        "median_net_pnl",
        "avg_r_multiple",
        "median_r_multiple",
        "notes",
    ],
    "sector_diagnostic_coverage.csv": [
        "strategy",
        "sector",
        "trades",
        "net_pnl",
        "profit_factor",
        "win_rate_pct",
        "avg_net_pnl",
        "median_net_pnl",
        "avg_r_multiple",
        "median_r_multiple",
        "sector_source",
        "notes",
    ],
    "drawdown_state_performance.csv": [
        "strategy",
        "drawdown_bucket_at_entry",
        "trades",
        "net_pnl",
        "profit_factor",
        "win_rate_pct",
        "avg_net_pnl",
        "median_net_pnl",
        "avg_r_multiple",
        "median_r_multiple",
    ],
    "rolling_r_expectancy_summary.csv": [
        "strategy",
        "rolling_r_bucket",
        "trades",
        "net_pnl",
        "profit_factor",
        "win_rate_pct",
        "avg_net_pnl",
        "median_net_pnl",
        "avg_r_multiple",
        "median_r_multiple",
        "notes",
    ],
    "capacity_pressure_summary.csv": [
        "strategy",
        "rejection_reason",
        "rejected_count",
        "share_of_rejections_pct",
        "notes",
    ],
    "capacity_pressure_by_year.csv": [
        "strategy",
        "year",
        "rejection_reason",
        "rejected_count",
        "share_of_year_rejections_pct",
        "notes",
    ],
    "vix_input_coverage.csv": [
        "indicator_name",
        "first_vix_date",
        "last_vix_date",
        "vix_rows",
        "unique_vix_dates",
        "null_close_count",
        "nonpositive_close_count",
        "duplicate_date_count",
        "strategies_covered",
        "total_trades",
        "trades_with_vix",
        "trade_vix_coverage_pct",
        "notes",
    ],
    "vix_regime_performance.csv": [
        "strategy",
        "vix_percentile_bucket",
        "trades",
        "net_pnl",
        "profit_factor",
        "win_rate_pct",
        "avg_net_pnl",
        "median_net_pnl",
        "avg_r_multiple",
        "median_r_multiple",
        "stop_gap_trades",
        "stop_gap_net_pnl",
        "notes",
    ],
    "vix_change_performance.csv": [
        "strategy",
        "vix_change_horizon",
        "vix_change_bucket",
        "trades",
        "net_pnl",
        "profit_factor",
        "win_rate_pct",
        "avg_net_pnl",
        "median_net_pnl",
        "avg_r_multiple",
        "median_r_multiple",
        "stop_gap_trades",
        "stop_gap_net_pnl",
        "notes",
    ],
    "vix_by_year.csv": [
        "strategy",
        "year",
        "vix_percentile_bucket",
        "trades",
        "net_pnl",
        "profit_factor",
        "win_rate_pct",
        "avg_net_pnl",
        "median_net_pnl",
        "avg_r_multiple",
        "median_r_multiple",
        "notes",
    ],
    "vix_gap_interaction_summary.csv": [
        "strategy",
        "vix_percentile_bucket",
        "exit_reason",
        "trades",
        "net_pnl",
        "avg_net_pnl",
        "median_net_pnl",
        "avg_r_multiple",
        "median_r_multiple",
        "share_of_strategy_bucket_trades_pct",
        "notes",
    ],
    "vix_drawdown_interaction_summary.csv": [
        "strategy",
        "vix_percentile_bucket",
        "drawdown_bucket_at_entry",
        "trades",
        "net_pnl",
        "profit_factor",
        "win_rate_pct",
        "avg_net_pnl",
        "median_net_pnl",
        "avg_r_multiple",
        "median_r_multiple",
        "notes",
    ],
}

VIX_JOIN_CONVENTION = (
    "Use latest VIX session on or before signal_date when available; otherwise "
    "use latest VIX session strictly before entry_date."
)


@dataclass(frozen=True, slots=True)
class StrategyRiskReport:
    strategy: StrategyLabel
    input_dir: Path
    artifacts: Mapping[str, Path]
    frames: Mapping[str, pd.DataFrame]
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CrossStrategyRiskDiagnosticAuditResult:
    output_dir: Path
    outputs: dict[str, Path]
    metadata: dict[str, object]


def run_cross_strategy_risk_diagnostic_audit(
    strategy_dirs: Mapping[str, Path | str],
    *,
    universe_csv: Path | str,
    classification_csv: Path | str,
    output_dir: Path | str,
    include_vix: bool = False,
    vix_indicator_name: str = "INDIA_VIX",
    vix_interval: str = "day",
    vix_data: pd.DataFrame | None = None,
) -> CrossStrategyRiskDiagnosticAuditResult:
    """Run the read-only Phase 36B risk input diagnostic audit."""

    normalized_dirs = {
        normalize_strategy_label(strategy): Path(path)
        for strategy, path in strategy_dirs.items()
    }
    missing = [label for label in STRATEGY_LABELS if label not in normalized_dirs]
    if missing:
        raise ValueError(f"missing strategy directories for: {', '.join(missing)}")

    universe = load_universe(universe_csv)
    classifications = load_classification(classification_csv)
    reports = [
        load_strategy_risk_report(label, normalized_dirs[label])
        for label in STRATEGY_LABELS
    ]

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    outputs: dict[str, Path] = {}
    builders = {
        "risk_input_inventory.csv": lambda: build_risk_input_inventory(reports),
        "risk_join_coverage_by_strategy.csv": lambda: build_join_coverage(reports, universe, classifications),
        "liquidity_bucket_performance.csv": lambda: build_liquidity_bucket_performance(reports, universe),
        "liquidity_bucket_by_year.csv": lambda: build_liquidity_bucket_by_year(reports, universe),
        "symbol_concentration_summary.csv": lambda: build_symbol_concentration_summary(reports),
        "top_symbol_contributors.csv": lambda: build_top_symbol_contributors(reports, universe, classifications),
        "gap_exit_stress_summary.csv": lambda: build_gap_exit_stress_summary(reports, universe),
        "gap_exit_by_year.csv": lambda: build_gap_exit_by_year(reports),
        "pre_entry_gap_context_summary.csv": lambda: build_pre_entry_gap_context_summary(reports),
        "atr_volatility_context_summary.csv": lambda: build_atr_volatility_context_summary(reports),
        "benchmark_regime_performance.csv": lambda: build_benchmark_regime_performance(reports),
        "sector_diagnostic_coverage.csv": lambda: build_sector_diagnostic_coverage(reports, classifications),
        "drawdown_state_performance.csv": lambda: build_drawdown_state_performance(reports),
        "rolling_r_expectancy_summary.csv": lambda: build_rolling_r_expectancy_summary(reports),
        "capacity_pressure_summary.csv": lambda: build_capacity_pressure_summary(reports),
        "capacity_pressure_by_year.csv": lambda: build_capacity_pressure_by_year(reports),
    }
    for name, builder in builders.items():
        outputs[name] = _write_csv(builder(), output_path / name, OUTPUT_COLUMNS[name])

    vix_outputs_written: list[str] = []
    if include_vix:
        vix_frame = vix_data
        if vix_frame is None:
            first_trade_date, last_trade_date = _trade_date_range(reports)
            vix_frame = load_vix_market_indicator(
                indicator_name=vix_indicator_name,
                interval=vix_interval,
                start_date=first_trade_date - timedelta(days=45),
                end_date=last_trade_date,
            )
        vix_features = build_vix_features(vix_frame)
        vix_trades = build_vix_enriched_trades(reports, vix_features)
        vix_builders = {
            "vix_input_coverage.csv": lambda: build_vix_input_coverage(
                reports,
                vix_frame,
                vix_trades,
                indicator_name=vix_indicator_name,
            ),
            "vix_regime_performance.csv": lambda: build_vix_regime_performance(vix_trades),
            "vix_change_performance.csv": lambda: build_vix_change_performance(vix_trades),
            "vix_by_year.csv": lambda: build_vix_by_year(vix_trades),
            "vix_gap_interaction_summary.csv": lambda: build_vix_gap_interaction_summary(vix_trades),
            "vix_drawdown_interaction_summary.csv": lambda: build_vix_drawdown_interaction_summary(reports, vix_trades),
        }
        for name, builder in vix_builders.items():
            outputs[name] = _write_csv(builder(), output_path / name, OUTPUT_COLUMNS[name])
            vix_outputs_written.append(name)

    readme_path = output_path / "risk_diagnostic_readme.txt"
    readme_path.write_text(_readme_text(include_vix=include_vix), encoding="utf-8")
    outputs["risk_diagnostic_readme.txt"] = readme_path

    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(output_path),
        "strategy_dirs": {label: str(normalized_dirs[label]) for label in STRATEGY_LABELS},
        "universe_csv": str(universe_csv),
        "classification_csv": str(classification_csv),
        "caveat": "Read-only diagnostics only; no strategy, sizing, filter, backtest, allocation, or production change.",
        "include_vix": include_vix,
        "vix_indicator_name": vix_indicator_name,
        "vix_interval": vix_interval,
        "vix_join_convention": VIX_JOIN_CONVENTION,
        "vix_outputs_written": vix_outputs_written,
        "outputs": {name: str(path) for name, path in sorted(outputs.items())},
    }
    metadata_path = output_path / "risk_diagnostic_metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    outputs["risk_diagnostic_metadata.json"] = metadata_path
    return CrossStrategyRiskDiagnosticAuditResult(output_path, outputs, metadata)


def load_strategy_risk_report(strategy: str, input_dir: Path | str) -> StrategyRiskReport:
    label = normalize_strategy_label(strategy)
    folder = Path(input_dir)
    frames: dict[str, pd.DataFrame] = {}
    artifacts: dict[str, Path] = {}
    notes: list[str] = []
    for artifact in (*REQUIRED_ARTIFACTS, *OPTIONAL_ARTIFACTS):
        path = folder / artifact
        if path.exists():
            artifacts[artifact] = path
            frames[artifact] = pd.read_csv(path)
        else:
            frames[artifact] = pd.DataFrame()
            notes.append(f"missing {artifact}")

    trade_pnl = frames["trade_pnl_log.csv"]
    if trade_pnl.empty:
        raise ValueError(f"{label} trade_pnl_log.csv missing or empty in {folder}")
    if "symbol" not in trade_pnl.columns:
        raise ValueError(f"{label} trade_pnl_log.csv missing required symbol column")

    frames["trade_pnl_log.csv"] = _normalize_trade_frame(trade_pnl, label)
    if not frames["trade_log.csv"].empty:
        frames["trade_log.csv"] = _normalize_trade_frame(frames["trade_log.csv"], label)
    if not frames["trade_signal_context.csv"].empty:
        frames["trade_signal_context.csv"] = _normalize_context_frame(frames["trade_signal_context.csv"], label)
    if not frames["equity_curve.csv"].empty:
        frames["equity_curve.csv"] = _normalize_equity_frame(frames["equity_curve.csv"], label)
    if not frames["rejected_signals.csv"].empty:
        frames["rejected_signals.csv"] = _normalize_rejected_frame(frames["rejected_signals.csv"], label)
    if frames["all_signal_opportunity_log.csv"].empty:
        notes.append("all_signal_opportunity_log.csv missing or empty; excluded from first Phase 36B diagnostics")
    if frames["accepted_vs_rejected_signal_summary.csv"].empty:
        notes.append("accepted_vs_rejected_signal_summary.csv missing or empty; excluded from first Phase 36B diagnostics")

    return StrategyRiskReport(label, folder, artifacts, frames, tuple(notes))


def load_universe(path: Path | str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if "symbol" not in frame.columns:
        raise ValueError("universe csv missing required symbol column")
    frame = frame.copy()
    frame["symbol"] = _normalize_symbol_series(frame["symbol"])
    for column in ("liquidity_bucket", "liquidity_metric"):
        if column not in frame.columns:
            frame[column] = np.nan
    return frame.drop_duplicates("symbol", keep="first")


def load_classification(path: Path | str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if "symbol" not in frame.columns:
        raise ValueError("classification csv missing required symbol column")
    frame = frame.copy()
    frame["symbol"] = _normalize_symbol_series(frame["symbol"])
    for column in ("sector", "market_cap_bucket", "classification_mode", "source"):
        if column not in frame.columns:
            frame[column] = np.nan
    return frame.drop_duplicates("symbol", keep="first")


def build_risk_input_inventory(reports: Iterable[StrategyRiskReport]) -> pd.DataFrame:
    rows = []
    key_columns = {
        "trade_log.csv": ("symbol", "entry_date", "exit_date", "exit_reason"),
        "trade_pnl_log.csv": ("symbol", "entry_date", "exit_date", "net_pnl", "initial_risk_amount"),
        "equity_curve.csv": ("date", "equity"),
        "symbol_summary.csv": ("symbol", "trades", "net_pnl"),
        "yearly_summary.csv": ("year", "trades", "net_pnl"),
        "exit_reason_summary.csv": ("exit_reason", "trades", "net_pnl"),
        "rejection_summary.csv": ("reason", "count"),
        "rejected_signals.csv": ("symbol", "signal_date", "reason"),
        "r_multiple_summary.csv": ("trades_with_r", "average_r"),
        "r_multiple_by_symbol.csv": ("symbol", "average_r"),
        "r_multiple_by_symbol_year.csv": ("symbol", "year", "average_r"),
        "trade_signal_context.csv": ("symbol", "entry_date", "stock_gap_from_prev_close_pct", "stock_atr14_pct"),
        "all_signal_opportunity_log.csv": ("symbol", "signal_date", "signal_status"),
        "accepted_vs_rejected_signal_summary.csv": ("signal_group", "signal_count"),
    }
    for report in reports:
        for artifact in (*REQUIRED_ARTIFACTS, *OPTIONAL_ARTIFACTS):
            frame = report.frames.get(artifact, pd.DataFrame())
            expected = key_columns.get(artifact, ())
            present = [column for column in expected if column in frame.columns]
            notes = []
            if artifact not in report.artifacts:
                notes.append("missing")
            elif frame.empty:
                notes.append("empty")
            missing = [column for column in expected if column not in frame.columns]
            if missing:
                notes.append("missing key columns: " + "|".join(missing))
            rows.append(
                {
                    "strategy": report.strategy,
                    "artifact": artifact,
                    "path": str(report.input_dir / artifact),
                    "exists": artifact in report.artifacts,
                    "rows": int(len(frame)),
                    "key_columns_present": "|".join(present),
                    "notes": "; ".join(notes),
                }
            )
    return pd.DataFrame(rows)


def build_join_coverage(
    reports: Iterable[StrategyRiskReport],
    universe: pd.DataFrame,
    classifications: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    universe_symbols = set(universe["symbol"])
    class_symbols = set(classifications["symbol"])
    for report in reports:
        trades = _enriched_trades(report, universe, classifications)
        trade_count = len(trades)
        unique_symbols = trades["symbol"].nunique()
        universe_joined = trades["symbol"].isin(universe_symbols)
        class_joined = trades["symbol"].isin(class_symbols)
        rows.append(
            {
                "strategy": report.strategy,
                "trade_count": trade_count,
                "universe_joined_trades": int(universe_joined.sum()),
                "universe_join_coverage_pct": _pct(universe_joined.sum(), trade_count),
                "classification_joined_trades": int(class_joined.sum()),
                "classification_join_coverage_pct": _pct(class_joined.sum(), trade_count),
                "unique_symbols": int(unique_symbols),
                "universe_joined_symbols": int(trades.loc[universe_joined, "symbol"].nunique()),
                "classification_joined_symbols": int(trades.loc[class_joined, "symbol"].nunique()),
                "liquidity_bucket_available_pct": _pct(_known_text_mask(trades.get("liquidity_bucket")).sum(), trade_count),
                "sector_available_pct": _pct(_known_text_mask(trades.get("sector")).sum(), trade_count),
                "market_cap_bucket_available_pct": _pct(_known_market_cap_mask(trades.get("market_cap_bucket")).sum(), trade_count),
                "notes": "static liquidity/classification join by symbol; market cap unknown is treated unavailable",
            }
        )
    return pd.DataFrame(rows)


def build_liquidity_bucket_performance(reports: Iterable[StrategyRiskReport], universe: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for report in reports:
        trades = _join_universe(_trades(report), universe)
        trades["liquidity_bucket"] = trades["liquidity_bucket"].where(_known_text_mask(trades["liquidity_bucket"]), "unknown")
        for bucket, group in trades.groupby("liquidity_bucket", dropna=False, sort=True):
            row = {"strategy": report.strategy, "liquidity_bucket": _text(bucket)}
            row.update(_performance_metrics(group))
            row["stop_gap_trades"] = int((_exit_reason(group) == "stop_gap_hit").sum())
            row["stop_gap_net_pnl"] = _sum(group.loc[_exit_reason(group) == "stop_gap_hit", "net_pnl"])
            row["notes"] = "static Research200 liquidity bucket"
            rows.append(row)
    return pd.DataFrame(rows)


def build_liquidity_bucket_by_year(reports: Iterable[StrategyRiskReport], universe: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for report in reports:
        trades = _join_universe(_trades(report), universe)
        trades["liquidity_bucket"] = trades["liquidity_bucket"].where(_known_text_mask(trades["liquidity_bucket"]), "unknown")
        trades["year"] = _year_from_trade(trades)
        for (year, bucket), group in trades.groupby(["year", "liquidity_bucket"], dropna=False, sort=True):
            row = {"strategy": report.strategy, "year": _int_or_blank(year), "liquidity_bucket": _text(bucket)}
            row.update(_performance_metrics(group, include_gross=False))
            rows.append(row)
    return pd.DataFrame(rows)


def build_symbol_concentration_summary(reports: Iterable[StrategyRiskReport]) -> pd.DataFrame:
    rows = []
    for report in reports:
        trades = _trades(report)
        by_symbol = _symbol_metrics(trades)
        total_pnl = _sum(trades["net_pnl"])
        winners = by_symbol.sort_values("net_pnl", ascending=False)
        losers = by_symbol.sort_values("net_pnl", ascending=True)
        top5_winner = _sum(winners.head(5)["net_pnl"])
        top10_winner = _sum(winners.head(10)["net_pnl"])
        top5_trade_share = _pct(winners.head(5)["trades"].sum(), len(trades))
        rows.append(
            {
                "strategy": report.strategy,
                "trades": int(len(trades)),
                "net_pnl": total_pnl,
                "unique_symbols": int(trades["symbol"].nunique()),
                "top_5_winner_pnl": top5_winner,
                "top_5_winner_pnl_to_total_pnl": _safe_ratio(top5_winner, total_pnl),
                "top_10_winner_pnl": top10_winner,
                "top_10_winner_pnl_to_total_pnl": _safe_ratio(top10_winner, total_pnl),
                "top_5_loser_pnl": _sum(losers.head(5)["net_pnl"]),
                "top_10_loser_pnl": _sum(losers.head(10)["net_pnl"]),
                "worst_symbol_pnl": float(by_symbol["net_pnl"].min()) if not by_symbol.empty else 0.0,
                "best_symbol_pnl": float(by_symbol["net_pnl"].max()) if not by_symbol.empty else 0.0,
                "top_5_trade_count_share_pct": top5_trade_share,
                "notes": "winner/loser concentration uses realized retained trade_pnl_log only",
            }
        )
    return pd.DataFrame(rows)


def build_top_symbol_contributors(
    reports: Iterable[StrategyRiskReport],
    universe: pd.DataFrame,
    classifications: pd.DataFrame,
    top_n: int = 10,
) -> pd.DataFrame:
    rows = []
    for report in reports:
        by_symbol = _symbol_metrics(_enriched_trades(report, universe, classifications))
        for side, ordered in (
            ("winner", by_symbol.sort_values("net_pnl", ascending=False)),
            ("loser", by_symbol.sort_values("net_pnl", ascending=True)),
        ):
            for rank, (_, row) in enumerate(ordered.head(top_n).iterrows(), start=1):
                rows.append(
                    {
                        "strategy": report.strategy,
                        "side": side,
                        "rank": rank,
                        "symbol": row["symbol"],
                        "trades": int(row["trades"]),
                        "net_pnl": row["net_pnl"],
                        "avg_net_pnl": row["avg_net_pnl"],
                        "median_net_pnl": row["median_net_pnl"],
                        "win_rate_pct": row["win_rate_pct"],
                        "avg_r_multiple": row["avg_r_multiple"],
                        "liquidity_bucket": row.get("liquidity_bucket", ""),
                        "sector": row.get("sector", ""),
                        "notes": "static liquidity/sector labels",
                    }
                )
    return pd.DataFrame(rows)


def build_gap_exit_stress_summary(reports: Iterable[StrategyRiskReport], universe: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for report in reports:
        trades = _join_universe(_trades(report), universe)
        total_trades = len(trades)
        total_pnl = _sum(trades["net_pnl"])
        reasons = _exit_reason(trades)
        gap_trades = trades.loc[reasons.isin(("stop_gap_hit", "target_gap_hit"))].copy()
        for reason, group in gap_trades.groupby(reasons[gap_trades.index], sort=True):
            row = {"strategy": report.strategy, "exit_reason": reason}
            row.update(_performance_metrics(group, include_gross=False))
            row["share_of_strategy_trades_pct"] = _pct(len(group), total_trades)
            row["share_of_strategy_pnl_pct"] = _pct(_sum(group["net_pnl"]), total_pnl)
            row["liquidity_bucket_mix_summary"] = _mix_summary(group.get("liquidity_bucket"))
            row["notes"] = "gap exits from realized exit_reason values"
            rows.append(row)
        if gap_trades.empty:
            rows.append(_empty_gap_row(report.strategy, total_trades))
    return pd.DataFrame(rows)


def build_gap_exit_by_year(reports: Iterable[StrategyRiskReport]) -> pd.DataFrame:
    rows = []
    for report in reports:
        trades = _trades(report)
        trades["year"] = _year_from_trade(trades)
        trades["exit_reason_norm"] = _exit_reason(trades)
        gap_trades = trades.loc[trades["exit_reason_norm"].isin(("stop_gap_hit", "target_gap_hit"))]
        for (year, reason), group in gap_trades.groupby(["year", "exit_reason_norm"], dropna=False, sort=True):
            row = {"strategy": report.strategy, "year": _int_or_blank(year), "exit_reason": reason}
            row.update(_performance_metrics(group, include_gross=False))
            rows.append(row)
    return pd.DataFrame(rows)


def build_pre_entry_gap_context_summary(reports: Iterable[StrategyRiskReport]) -> pd.DataFrame:
    return _context_bucket_summary(
        reports,
        column_candidates=("stock_gap_from_prev_close_pct",),
        bucket_column="pre_entry_gap_bucket",
        bucket_func=_pre_entry_gap_bucket,
        missing_note="stock_gap_from_prev_close_pct unavailable",
    )


def build_atr_volatility_context_summary(reports: Iterable[StrategyRiskReport]) -> pd.DataFrame:
    rows = []
    for report in reports:
        context = _context_trades(report)
        if context.empty or "stock_atr14_pct" not in context.columns:
            rows.append(_empty_context_row(report.strategy, "atr_pct_bucket", "unknown", "stock_atr14_pct unavailable"))
            continue
        values = pd.to_numeric(context["stock_atr14_pct"], errors="coerce")
        context["atr_pct_bucket"] = _quantile_buckets(values)
        for bucket, group in context.groupby("atr_pct_bucket", dropna=False, sort=True):
            row = {"strategy": report.strategy, "atr_pct_bucket": _text(bucket)}
            row.update(_performance_metrics(group, include_gross=False))
            rows.append(row)
    return pd.DataFrame(rows)


def build_benchmark_regime_performance(reports: Iterable[StrategyRiskReport]) -> pd.DataFrame:
    rows = []
    candidates = ("nifty_return_20d_pct", "benchmark_ret_20d", "nifty_return_20d")
    for report in reports:
        context = _context_trades(report)
        column = _first_existing(context, candidates)
        if context.empty or column is None:
            rows.append(_empty_benchmark_row(report.strategy, "", "benchmark/NIFTY 20D return unavailable"))
            continue
        context["benchmark_regime_bucket"] = pd.to_numeric(context[column], errors="coerce").map(_benchmark_bucket)
        for bucket, group in context.groupby("benchmark_regime_bucket", dropna=False, sort=True):
            row = {"strategy": report.strategy, "benchmark_column_used": column, "benchmark_regime_bucket": _text(bucket)}
            row.update(_performance_metrics(group, include_gross=False))
            row["notes"] = "signal-time benchmark/NIFTY context"
            rows.append(row)
    return pd.DataFrame(rows)


def build_sector_diagnostic_coverage(
    reports: Iterable[StrategyRiskReport],
    classifications: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for report in reports:
        trades = _join_classification(_trades(report), classifications)
        trades["sector"] = trades["sector"].where(_known_text_mask(trades["sector"]), "UNKNOWN")
        for sector, group in trades.groupby("sector", dropna=False, sort=True):
            row = {"strategy": report.strategy, "sector": _text(sector)}
            row.update(_performance_metrics(group, include_gross=False))
            source = _mode_text(group.get("source"))
            mode = _mode_text(group.get("classification_mode"))
            row["sector_source"] = source
            row["notes"] = f"static/partial sector diagnostic; classification_mode={mode}"
            rows.append(row)
    return pd.DataFrame(rows)


def build_drawdown_state_performance(reports: Iterable[StrategyRiskReport]) -> pd.DataFrame:
    rows = []
    for report in reports:
        trades = _trades(report)
        equity = _drawdown_frame(report.frames.get("equity_curve.csv", pd.DataFrame()))
        if equity.empty:
            trades["drawdown_bucket_at_entry"] = "unknown"
        else:
            trades = _merge_drawdown_at_entry(trades, equity)
        for bucket, group in trades.groupby("drawdown_bucket_at_entry", dropna=False, sort=True):
            row = {"strategy": report.strategy, "drawdown_bucket_at_entry": _text(bucket)}
            row.update(_performance_metrics(group, include_gross=False))
            rows.append(row)
    return pd.DataFrame(rows)


def build_rolling_r_expectancy_summary(reports: Iterable[StrategyRiskReport]) -> pd.DataFrame:
    rows = []
    for report in reports:
        trades = _trades(report).sort_values(["_entry_date", "_exit_date", "trade_id"], kind="mergesort").reset_index(drop=True)
        r = _r_multiple_series(trades)
        trades["previous_10_avg_r"] = r.shift(1).rolling(10, min_periods=1).mean()
        trades["previous_20_avg_r"] = r.shift(1).rolling(20, min_periods=1).mean()
        trades["previous_50_avg_r"] = r.shift(1).rolling(50, min_periods=1).mean()
        previous_count = r.shift(1).expanding().count()
        trades["rolling_r_bucket"] = [
            "insufficient_history" if count < 20 else _rolling_r_bucket(value)
            for count, value in zip(previous_count, trades["previous_20_avg_r"])
        ]
        for bucket, group in trades.groupby("rolling_r_bucket", dropna=False, sort=True):
            row = {"strategy": report.strategy, "rolling_r_bucket": _text(bucket)}
            row.update(_performance_metrics(group, include_gross=False))
            row["notes"] = "rolling R uses previous trades only; bucket uses previous 20-trade average"
            rows.append(row)
    return pd.DataFrame(rows)


def build_capacity_pressure_summary(reports: Iterable[StrategyRiskReport]) -> pd.DataFrame:
    rows = []
    for report in reports:
        summary = report.frames.get("rejection_summary.csv", pd.DataFrame())
        if summary.empty or not {"reason", "count"}.issubset(summary.columns):
            rows.append(
                {
                    "strategy": report.strategy,
                    "rejection_reason": "",
                    "rejected_count": 0,
                    "share_of_rejections_pct": 0.0,
                    "notes": "rejection_summary.csv missing or lacks reason/count",
                }
            )
            continue
        frame = summary.copy()
        frame["count"] = pd.to_numeric(frame["count"], errors="coerce").fillna(0)
        total = frame["count"].sum()
        for _, row in frame.iterrows():
            rows.append(
                {
                    "strategy": report.strategy,
                    "rejection_reason": _text(row["reason"]),
                    "rejected_count": int(row["count"]),
                    "share_of_rejections_pct": _pct(row["count"], total),
                    "notes": "rejection pressure from retained report folder",
                }
            )
    return pd.DataFrame(rows)


def build_capacity_pressure_by_year(reports: Iterable[StrategyRiskReport]) -> pd.DataFrame:
    rows = []
    for report in reports:
        rejected = report.frames.get("rejected_signals.csv", pd.DataFrame())
        if rejected.empty or "reason" not in rejected.columns:
            continue
        rejected = rejected.copy()
        rejected["year"] = _parse_date_col(rejected, "_signal_date").dt.year
        counts = rejected.groupby(["year", "reason"], dropna=False, sort=True).size().reset_index(name="rejected_count")
        year_totals = counts.groupby("year")["rejected_count"].transform("sum")
        for idx, row in counts.iterrows():
            rows.append(
                {
                    "strategy": report.strategy,
                    "year": _int_or_blank(row["year"]),
                    "rejection_reason": _text(row["reason"]),
                    "rejected_count": int(row["rejected_count"]),
                    "share_of_year_rejections_pct": _pct(row["rejected_count"], year_totals.iloc[idx]),
                    "notes": "year from rejected signal date",
                }
            )
    return pd.DataFrame(rows)


def load_vix_market_indicator(
    *,
    indicator_name: str,
    interval: str,
    start_date: datetime | pd.Timestamp | object,
    end_date: datetime | pd.Timestamp | object,
) -> pd.DataFrame:
    """Load India VIX rows through the existing project DB client."""

    try:
        from veridian_quant.data.db_client import DatabaseClient

        engine = DatabaseClient().get_engine()
        query = text(
            """
            SELECT
                timestamp::date AS date,
                timestamp,
                indicator_name,
                open,
                high,
                low,
                close,
                value,
                interval
            FROM market_indicators
            WHERE indicator_name = :indicator_name
              AND interval = :interval
              AND timestamp::date >= :start_date
              AND timestamp::date <= :end_date
            ORDER BY timestamp ASC
            """
        )
        frame = pd.read_sql(
            query,
            engine,
            params={
                "indicator_name": indicator_name,
                "interval": interval,
                "start_date": _date_param(start_date),
                "end_date": _date_param(end_date),
            },
        )
    except Exception as error:  # pragma: no cover - message is validated by CLI usage.
        raise RuntimeError(
            "Unable to load India VIX from market_indicators. "
            "Check DB connectivity, credentials, indicator name, and interval."
        ) from error
    if frame.empty:
        raise ValueError(
            f"No VIX rows found in market_indicators for {indicator_name!r} "
            f"interval {interval!r}."
        )
    return frame


def build_vix_features(vix_data: pd.DataFrame) -> pd.DataFrame:
    """Return daily VIX features using only current and prior VIX rows."""

    frame = _normalize_vix_frame(vix_data)
    if frame.empty:
        return _empty_vix_features()
    frame["vix_change_1d_pct"] = ((frame["vix_close"] / frame["vix_close"].shift(1)) - 1.0) * 100.0
    frame["vix_change_5d_pct"] = ((frame["vix_close"] / frame["vix_close"].shift(5)) - 1.0) * 100.0
    frame["vix_rolling_20d_percentile"] = (
        frame["vix_close"]
        .rolling(window=20, min_periods=20)
        .apply(lambda values: pd.Series(values).rank(method="average", pct=True).iloc[-1], raw=False)
    )
    frame["vix_percentile_bucket"] = [
        _vix_percentile_bucket(value, idx)
        for idx, value in enumerate(frame["vix_rolling_20d_percentile"])
    ]
    frame["vix_change_1d_bucket"] = [
        _vix_change_bucket(value, idx, 1)
        for idx, value in enumerate(frame["vix_change_1d_pct"])
    ]
    frame["vix_change_5d_bucket"] = [
        _vix_change_bucket(value, idx, 5)
        for idx, value in enumerate(frame["vix_change_5d_pct"])
    ]
    frame["vix_trend_5d"] = frame["vix_change_5d_bucket"]
    return frame


def build_vix_enriched_trades(
    reports: Iterable[StrategyRiskReport],
    vix_features: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    features = vix_features.copy().sort_values("date", kind="mergesort").reset_index(drop=True)
    for report in reports:
        trades = _trades_with_signal_dates(report)
        for _, trade in trades.iterrows():
            joined = trade.to_dict()
            vix_row, convention = _vix_row_for_trade(trade, features)
            joined["vix_join_convention"] = convention
            if vix_row is None:
                joined.update(_missing_vix_values())
            else:
                for column in _vix_feature_columns():
                    joined[column] = vix_row.get(column, np.nan)
            rows.append(joined)
    output = pd.DataFrame(rows)
    if output.empty:
        return output
    output["vix_percentile_bucket"] = output["vix_percentile_bucket"].fillna("unknown")
    output["vix_change_1d_bucket"] = output["vix_change_1d_bucket"].fillna("unknown")
    output["vix_change_5d_bucket"] = output["vix_change_5d_bucket"].fillna("unknown")
    output["vix_trend_5d"] = output["vix_trend_5d"].fillna("unknown")
    return output


def build_vix_input_coverage(
    reports: Iterable[StrategyRiskReport],
    vix_data: pd.DataFrame,
    vix_trades: pd.DataFrame,
    *,
    indicator_name: str,
) -> pd.DataFrame:
    raw = _raw_vix_for_coverage(vix_data)
    total_trades = sum(len(_trades(report)) for report in reports)
    trades_with_vix = int(pd.to_numeric(vix_trades.get("vix_close"), errors="coerce").notna().sum())
    duplicate_count = int(raw.duplicated(subset=["date"]).sum()) if "date" in raw.columns else 0
    rows = [
        {
            "indicator_name": indicator_name,
            "first_vix_date": raw["date"].min().date().isoformat() if not raw.empty else "",
            "last_vix_date": raw["date"].max().date().isoformat() if not raw.empty else "",
            "vix_rows": int(len(raw)),
            "unique_vix_dates": int(raw["date"].nunique()) if "date" in raw.columns else 0,
            "null_close_count": int(pd.to_numeric(raw.get("close"), errors="coerce").isna().sum()) if "close" in raw.columns else int(len(raw)),
            "nonpositive_close_count": int((pd.to_numeric(raw.get("close"), errors="coerce") <= 0).sum()) if "close" in raw.columns else 0,
            "duplicate_date_count": duplicate_count,
            "strategies_covered": "|".join(sorted(vix_trades["strategy"].dropna().astype(str).unique())) if "strategy" in vix_trades.columns else "",
            "total_trades": total_trades,
            "trades_with_vix": trades_with_vix,
            "trade_vix_coverage_pct": _pct(trades_with_vix, total_trades),
            "notes": VIX_JOIN_CONVENTION,
        }
    ]
    return pd.DataFrame(rows)


def build_vix_regime_performance(vix_trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (strategy, bucket), group in vix_trades.groupby(["strategy", "vix_percentile_bucket"], dropna=False, sort=True):
        row = {"strategy": strategy, "vix_percentile_bucket": _text(bucket)}
        row.update(_performance_metrics(group, include_gross=False))
        row["stop_gap_trades"] = int((_exit_reason(group) == "stop_gap_hit").sum())
        row["stop_gap_net_pnl"] = _sum(group.loc[_exit_reason(group) == "stop_gap_hit", "net_pnl"])
        row["notes"] = "VIX rolling 20D percentile bucket; diagnostic only"
        rows.append(row)
    return pd.DataFrame(rows)


def build_vix_change_performance(vix_trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for horizon, column in (("1d", "vix_change_1d_bucket"), ("5d", "vix_change_5d_bucket")):
        for (strategy, bucket), group in vix_trades.groupby(["strategy", column], dropna=False, sort=True):
            row = {
                "strategy": strategy,
                "vix_change_horizon": horizon,
                "vix_change_bucket": _text(bucket),
            }
            row.update(_performance_metrics(group, include_gross=False))
            row["stop_gap_trades"] = int((_exit_reason(group) == "stop_gap_hit").sum())
            row["stop_gap_net_pnl"] = _sum(group.loc[_exit_reason(group) == "stop_gap_hit", "net_pnl"])
            row["notes"] = "VIX change direction bucket; diagnostic only"
            rows.append(row)
    return pd.DataFrame(rows)


def build_vix_by_year(vix_trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    frame = vix_trades.copy()
    frame["year"] = _year_from_trade(frame)
    for (strategy, year, bucket), group in frame.groupby(["strategy", "year", "vix_percentile_bucket"], dropna=False, sort=True):
        row = {
            "strategy": strategy,
            "year": _int_or_blank(year),
            "vix_percentile_bucket": _text(bucket),
        }
        row.update(_performance_metrics(group, include_gross=False))
        row["notes"] = "year from trade exit date when available, else entry date"
        rows.append(row)
    return pd.DataFrame(rows)


def build_vix_gap_interaction_summary(vix_trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    frame = vix_trades.copy()
    frame["exit_reason_norm"] = _exit_reason(frame)
    for (strategy, bucket, reason), group in frame.groupby(["strategy", "vix_percentile_bucket", "exit_reason_norm"], dropna=False, sort=True):
        bucket_total = len(frame[(frame["strategy"] == strategy) & (frame["vix_percentile_bucket"] == bucket)])
        row = {
            "strategy": strategy,
            "vix_percentile_bucket": _text(bucket),
            "exit_reason": _text(reason),
        }
        row.update(_performance_metrics(group, include_gross=False))
        row["share_of_strategy_bucket_trades_pct"] = _pct(len(group), bucket_total)
        row["notes"] = "exit reason clustering inside VIX percentile bucket; diagnostic only"
        rows.append(row)
    return pd.DataFrame(rows)


def build_vix_drawdown_interaction_summary(
    reports: Iterable[StrategyRiskReport],
    vix_trades: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    drawdown = _drawdown_by_trade(reports)
    frame = vix_trades.merge(drawdown, on=["strategy", "trade_id"], how="left")
    frame["drawdown_bucket_at_entry"] = frame["drawdown_bucket_at_entry"].fillna("unknown")
    for (strategy, vix_bucket, drawdown_bucket), group in frame.groupby(
        ["strategy", "vix_percentile_bucket", "drawdown_bucket_at_entry"],
        dropna=False,
        sort=True,
    ):
        row = {
            "strategy": strategy,
            "vix_percentile_bucket": _text(vix_bucket),
            "drawdown_bucket_at_entry": _text(drawdown_bucket),
        }
        row.update(_performance_metrics(group, include_gross=False))
        row["notes"] = "VIX percentile bucket crossed with strategy drawdown state; diagnostic only"
        rows.append(row)
    return pd.DataFrame(rows)


def normalize_strategy_label(value: str) -> StrategyLabel:
    label = str(value).strip().upper()
    if label not in STRATEGY_LABELS:
        raise ValueError(f"strategy label must be one of {', '.join(STRATEGY_LABELS)}; got {value!r}")
    return label  # type: ignore[return-value]


def _trade_date_range(reports: Iterable[StrategyRiskReport]) -> tuple[datetime, datetime]:
    dates = []
    for report in reports:
        trades = _trades_with_signal_dates(report)
        if "_signal_date" in trades.columns:
            dates.append(trades["_signal_date"])
        dates.append(trades["_entry_date"])
    combined = pd.concat(dates, ignore_index=True).dropna()
    if combined.empty:
        raise ValueError("cannot determine VIX query range; no trade dates found")
    return combined.min().to_pydatetime(), combined.max().to_pydatetime()


def _normalize_vix_frame(vix_data: pd.DataFrame) -> pd.DataFrame:
    if vix_data.empty:
        return _empty_vix_features()
    frame = vix_data.copy()
    frame.columns = [str(column).lower() for column in frame.columns]
    date_col = _first_existing(frame, ("date", "session_date", "timestamp"))
    if date_col is None:
        raise ValueError("VIX data requires date, session_date, or timestamp column")
    close_col = _first_existing(frame, ("vix_close", "close", "value"))
    if close_col is None:
        raise ValueError("VIX data requires vix_close, close, or value column")
    frame["date"] = pd.to_datetime(frame[date_col], errors="coerce").dt.normalize()
    frame["vix_close"] = pd.to_numeric(frame[close_col], errors="coerce")
    frame = frame.dropna(subset=["date"]).sort_values(["date"], kind="mergesort")
    frame = frame.drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)
    return frame[["date", "vix_close"]]


def _raw_vix_for_coverage(vix_data: pd.DataFrame) -> pd.DataFrame:
    if vix_data.empty:
        return pd.DataFrame(columns=["date", "close"])
    frame = vix_data.copy()
    frame.columns = [str(column).lower() for column in frame.columns]
    date_col = _first_existing(frame, ("date", "session_date", "timestamp"))
    close_col = _first_existing(frame, ("vix_close", "close", "value"))
    if date_col is None:
        frame["date"] = pd.NaT
    else:
        frame["date"] = pd.to_datetime(frame[date_col], errors="coerce").dt.normalize()
    if close_col is None:
        frame["close"] = np.nan
    else:
        frame["close"] = pd.to_numeric(frame[close_col], errors="coerce")
    return frame


def _empty_vix_features() -> pd.DataFrame:
    return pd.DataFrame(columns=_vix_feature_columns())


def _vix_feature_columns() -> list[str]:
    return [
        "date",
        "vix_close",
        "vix_change_1d_pct",
        "vix_change_5d_pct",
        "vix_rolling_20d_percentile",
        "vix_percentile_bucket",
        "vix_change_1d_bucket",
        "vix_change_5d_bucket",
        "vix_trend_5d",
    ]


def _missing_vix_values() -> dict[str, object]:
    values = {column: np.nan for column in _vix_feature_columns()}
    values["vix_percentile_bucket"] = "unknown"
    values["vix_change_1d_bucket"] = "unknown"
    values["vix_change_5d_bucket"] = "unknown"
    values["vix_trend_5d"] = "unknown"
    return values


def _vix_percentile_bucket(value: object, position: int) -> str:
    number = _float_or_nan(value)
    if np.isnan(number):
        return "insufficient_history" if position < 19 else "unknown"
    if number <= 1 / 3:
        return "low"
    if number <= 2 / 3:
        return "mid"
    return "high"


def _vix_change_bucket(value: object, position: int, horizon: int) -> str:
    number = _float_or_nan(value)
    if np.isnan(number):
        return "insufficient_history" if position < horizon else "unknown"
    if number > 0:
        return "rising"
    if number < 0:
        return "falling"
    return "flat"


def _trades_with_signal_dates(report: StrategyRiskReport) -> pd.DataFrame:
    trades = _trades(report)
    trades["_signal_date"] = _parse_date_col(trades, "signal_date")
    if trades["_signal_date"].notna().all():
        return trades
    context = _context_trades(report)
    if context.empty or "trade_id" not in context.columns:
        return trades
    context_signal = context[["trade_id", "_entry_date"]].copy()
    if "_signal_date" in context.columns:
        context_signal["_context_signal_date"] = context["_signal_date"]
    else:
        context_signal["_context_signal_date"] = _parse_date_col(context, "signal_date")
    context_signal = context_signal.drop_duplicates("trade_id", keep="first")
    trades = trades.merge(
        context_signal[["trade_id", "_context_signal_date"]],
        on="trade_id",
        how="left",
    )
    trades["_signal_date"] = trades["_signal_date"].fillna(trades["_context_signal_date"])
    trades = trades.drop(columns=["_context_signal_date"])
    return trades


def _vix_row_for_trade(
    trade: pd.Series,
    vix_features: pd.DataFrame,
) -> tuple[pd.Series | None, str]:
    if vix_features.empty:
        return None, "no_vix_data"
    signal_date = pd.to_datetime(trade.get("_signal_date"), errors="coerce")
    entry_date = pd.to_datetime(trade.get("_entry_date"), errors="coerce")
    if pd.notna(signal_date):
        available = vix_features.loc[vix_features["date"] <= signal_date]
        convention = "signal_date_on_or_before"
    elif pd.notna(entry_date):
        available = vix_features.loc[vix_features["date"] < entry_date]
        convention = "entry_date_strictly_before"
    else:
        return None, "missing_trade_date"
    if available.empty:
        return None, convention
    return available.iloc[-1], convention


def _drawdown_by_trade(reports: Iterable[StrategyRiskReport]) -> pd.DataFrame:
    rows = []
    for report in reports:
        trades = _trades(report)
        equity = _drawdown_frame(report.frames.get("equity_curve.csv", pd.DataFrame()))
        if equity.empty:
            trades["drawdown_bucket_at_entry"] = "unknown"
        else:
            trades = _merge_drawdown_at_entry(trades, equity)
        rows.append(trades[["strategy", "trade_id", "drawdown_bucket_at_entry"]])
    if not rows:
        return pd.DataFrame(columns=["strategy", "trade_id", "drawdown_bucket_at_entry"])
    return pd.concat(rows, ignore_index=True)


def _date_param(value: object) -> object:
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    return value


def _normalize_trade_frame(frame: pd.DataFrame, strategy: str) -> pd.DataFrame:
    output = frame.copy()
    output["strategy"] = strategy
    output["symbol"] = _normalize_symbol_series(output["symbol"])
    output["_entry_date"] = _parse_date_col(output, "entry_date")
    output["_exit_date"] = _parse_date_col(output, "exit_date")
    output["net_pnl"] = _numeric_series(output, "net_pnl", default=0.0)
    output["gross_pnl"] = _numeric_series(output, "gross_pnl")
    output["initial_risk_amount"] = _numeric_series(output, "initial_risk_amount")
    output["exit_reason"] = _string_series(output, "exit_reason", default="")
    if "trade_id" not in output.columns:
        output["trade_id"] = [f"{strategy}_{idx}" for idx in range(len(output))]
    output["r_multiple"] = _r_multiple_series(output)
    return output


def _normalize_context_frame(frame: pd.DataFrame, strategy: str) -> pd.DataFrame:
    output = _normalize_trade_frame(frame, strategy)
    for column in (
        "stock_gap_from_prev_close_pct",
        "stock_atr14_pct",
        "stock_atr14_change_5d_pct",
        "stock_atr14_change_10d_pct",
        "nifty_return_20d_pct",
    ):
        if column in output.columns:
            output[column] = pd.to_numeric(output[column], errors="coerce")
    return output


def _normalize_equity_frame(frame: pd.DataFrame, strategy: str) -> pd.DataFrame:
    output = frame.copy()
    output["strategy"] = strategy
    output["_date"] = _parse_date_col(output, "date")
    output["equity"] = _numeric_series(output, "equity")
    return output.dropna(subset=["_date", "equity"]).sort_values("_date", kind="mergesort")


def _normalize_rejected_frame(frame: pd.DataFrame, strategy: str) -> pd.DataFrame:
    output = frame.copy()
    output["strategy"] = strategy
    if "symbol" in output.columns:
        output["symbol"] = _normalize_symbol_series(output["symbol"])
    output["reason"] = _string_series(output, "reason", default="")
    date_col = _first_existing(output, ("signal_date", "generated_on", "date"))
    output["_signal_date"] = _parse_date_col(output, date_col)
    return output


def _trades(report: StrategyRiskReport) -> pd.DataFrame:
    return report.frames["trade_pnl_log.csv"].copy()


def _context_trades(report: StrategyRiskReport) -> pd.DataFrame:
    frame = report.frames.get("trade_signal_context.csv", pd.DataFrame())
    return frame.copy() if not frame.empty else pd.DataFrame()


def _enriched_trades(
    report: StrategyRiskReport,
    universe: pd.DataFrame,
    classifications: pd.DataFrame,
) -> pd.DataFrame:
    return _join_classification(_join_universe(_trades(report), universe), classifications)


def _join_universe(trades: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    columns = [column for column in ("symbol", "liquidity_bucket", "liquidity_metric") if column in universe.columns]
    return trades.merge(universe[columns], on="symbol", how="left")


def _join_classification(trades: pd.DataFrame, classifications: pd.DataFrame) -> pd.DataFrame:
    columns = [
        column
        for column in ("symbol", "sector", "market_cap_bucket", "classification_mode", "source")
        if column in classifications.columns
    ]
    return trades.merge(classifications[columns], on="symbol", how="left")


def _symbol_metrics(trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for symbol, group in trades.groupby("symbol", dropna=False, sort=True):
        row = {"symbol": symbol}
        row.update(_performance_metrics(group, include_gross=False))
        row["trades"] = int(len(group))
        if "liquidity_bucket" in group.columns:
            row["liquidity_bucket"] = _mode_text(group["liquidity_bucket"])
        if "sector" in group.columns:
            row["sector"] = _mode_text(group["sector"])
        rows.append(row)
    return pd.DataFrame(rows)


def _performance_metrics(frame: pd.DataFrame, *, include_gross: bool = True) -> dict[str, object]:
    pnl = _numeric_series(frame, "net_pnl", default=0.0)
    r = _r_multiple_series(frame)
    trades = int(len(frame))
    wins = int((pnl > 0).sum())
    gross_profit = _sum(pnl[pnl > 0])
    gross_loss = _sum(pnl[pnl < 0])
    metrics = {
        "trades": trades,
        "net_pnl": _sum(pnl),
        "profit_factor": _profit_factor(gross_profit, gross_loss),
        "win_rate_pct": _pct(wins, trades),
        "avg_net_pnl": float(pnl.mean()) if trades else 0.0,
        "median_net_pnl": float(pnl.median()) if trades else 0.0,
        "avg_r_multiple": float(r.mean()) if r.notna().any() else np.nan,
        "median_r_multiple": float(r.median()) if r.notna().any() else np.nan,
    }
    if include_gross:
        metrics["gross_profit"] = gross_profit
        metrics["gross_loss"] = gross_loss
    return metrics


def _r_multiple_series(frame: pd.DataFrame) -> pd.Series:
    if "r_multiple" in frame.columns:
        return _numeric_series(frame, "r_multiple")
    if {"net_pnl", "initial_risk_amount"}.issubset(frame.columns):
        risk = _numeric_series(frame, "initial_risk_amount")
        pnl = _numeric_series(frame, "net_pnl")
        return pnl / risk.replace(0, np.nan)
    if {"net_pnl", "per_share_risk", "quantity"}.issubset(frame.columns):
        risk = _numeric_series(frame, "per_share_risk") * _numeric_series(frame, "quantity")
        pnl = _numeric_series(frame, "net_pnl")
        return pnl / risk.replace(0, np.nan)
    return pd.Series(np.nan, index=frame.index, dtype=float)


def _context_bucket_summary(
    reports: Iterable[StrategyRiskReport],
    *,
    column_candidates: tuple[str, ...],
    bucket_column: str,
    bucket_func,
    missing_note: str,
) -> pd.DataFrame:
    rows = []
    for report in reports:
        context = _context_trades(report)
        column = _first_existing(context, column_candidates)
        if context.empty or column is None:
            rows.append(_empty_context_row(report.strategy, bucket_column, "unknown", missing_note))
            continue
        context[bucket_column] = pd.to_numeric(context[column], errors="coerce").map(bucket_func)
        for bucket, group in context.groupby(bucket_column, dropna=False, sort=True):
            row = {"strategy": report.strategy, bucket_column: _text(bucket)}
            row.update(_performance_metrics(group, include_gross=False))
            rows.append(row)
    return pd.DataFrame(rows)


def _drawdown_frame(equity: pd.DataFrame) -> pd.DataFrame:
    if equity.empty or "equity" not in equity.columns:
        return pd.DataFrame()
    frame = equity.copy().sort_values("_date", kind="mergesort")
    peak = frame["equity"].cummax()
    frame["drawdown_pct"] = ((frame["equity"] / peak) - 1.0) * 100.0
    frame["drawdown_bucket_at_entry"] = frame["drawdown_pct"].map(_drawdown_bucket)
    return frame[["_date", "drawdown_pct", "drawdown_bucket_at_entry"]]


def _merge_drawdown_at_entry(trades: pd.DataFrame, equity: pd.DataFrame) -> pd.DataFrame:
    left = trades.sort_values("_entry_date", kind="mergesort").copy()
    right = equity.sort_values("_date", kind="mergesort")
    merged = pd.merge_asof(
        left,
        right,
        left_on="_entry_date",
        right_on="_date",
        direction="backward",
    )
    merged["drawdown_bucket_at_entry"] = merged["drawdown_bucket_at_entry"].fillna("unknown")
    return merged


def _quantile_buckets(values: pd.Series) -> pd.Series:
    valid = values.dropna()
    result = pd.Series("unknown", index=values.index, dtype="object")
    if valid.empty:
        return result
    if valid.nunique() < 3:
        ranks = valid.rank(method="average", pct=True)
        mapped = ranks.map(lambda value: "low" if value <= 1 / 3 else "mid" if value <= 2 / 3 else "high")
    else:
        mapped = pd.qcut(valid, q=3, labels=("low", "mid", "high"), duplicates="drop")
        mapped = mapped.astype(str)
    result.loc[valid.index] = mapped
    return result


def _pre_entry_gap_bucket(value: object) -> str:
    number = _float_or_nan(value)
    if np.isnan(number):
        return "unknown"
    if number <= -3:
        return "gap_down_large"
    if number <= -1:
        return "gap_down_moderate"
    if number < 1:
        return "flat"
    if number < 3:
        return "gap_up_moderate"
    return "gap_up_large"


def _benchmark_bucket(value: object) -> str:
    number = _float_or_nan(value)
    if np.isnan(number):
        return "unknown"
    if number <= -5:
        return "strong_negative"
    if number < 0:
        return "negative"
    if number < 5:
        return "positive"
    return "strong_positive"


def _drawdown_bucket(value: object) -> str:
    number = _float_or_nan(value)
    if np.isnan(number):
        return "unknown"
    if number >= -2:
        return "at_or_near_high"
    if number >= -10:
        return "mild_drawdown"
    if number >= -20:
        return "moderate_drawdown"
    return "deep_drawdown"


def _rolling_r_bucket(value: object) -> str:
    number = _float_or_nan(value)
    if np.isnan(number):
        return "insufficient_history"
    if number <= -0.25:
        return "strong_negative"
    if number < 0:
        return "negative"
    if number < 0.25:
        return "positive"
    return "strong_positive"


def _empty_gap_row(strategy: str, total_trades: int) -> dict[str, object]:
    return {
        "strategy": strategy,
        "exit_reason": "",
        "trades": 0,
        "net_pnl": 0.0,
        "avg_net_pnl": 0.0,
        "median_net_pnl": 0.0,
        "avg_r_multiple": np.nan,
        "median_r_multiple": np.nan,
        "share_of_strategy_trades_pct": _pct(0, total_trades),
        "share_of_strategy_pnl_pct": 0.0,
        "liquidity_bucket_mix_summary": "",
        "notes": "no stop_gap_hit or target_gap_hit exits",
    }


def _empty_context_row(strategy: str, bucket_column: str, bucket: str, note: str) -> dict[str, object]:
    row = {
        "strategy": strategy,
        bucket_column: bucket,
        "trades": 0,
        "net_pnl": 0.0,
        "profit_factor": "",
        "win_rate_pct": 0.0,
        "avg_net_pnl": 0.0,
        "median_net_pnl": 0.0,
        "avg_r_multiple": np.nan,
        "median_r_multiple": np.nan,
    }
    if bucket_column == "benchmark_regime_bucket":
        row["benchmark_column_used"] = ""
        row["notes"] = note
    return row


def _empty_benchmark_row(strategy: str, column: str, note: str) -> dict[str, object]:
    row = _empty_context_row(strategy, "benchmark_regime_bucket", "unknown", note)
    row["benchmark_column_used"] = column
    row["notes"] = note
    return row


def _exit_reason(frame: pd.DataFrame) -> pd.Series:
    if "exit_reason" not in frame.columns:
        return pd.Series("", index=frame.index, dtype="object")
    return frame["exit_reason"].astype(str).str.strip().str.lower()


def _year_from_trade(frame: pd.DataFrame) -> pd.Series:
    source = frame["_exit_date"] if "_exit_date" in frame.columns else frame["_entry_date"]
    return pd.to_datetime(source, errors="coerce").dt.year


def _known_text_mask(series: pd.Series | None) -> pd.Series:
    if series is None:
        return pd.Series(dtype=bool)
    normalized = series.astype(str).str.strip()
    return normalized.ne("") & normalized.str.lower().ne("nan") & normalized.str.upper().ne("UNKNOWN")


def _known_market_cap_mask(series: pd.Series | None) -> pd.Series:
    if series is None:
        return pd.Series(dtype=bool)
    normalized = series.astype(str).str.strip().str.lower()
    return normalized.ne("") & normalized.ne("nan") & normalized.ne("unknown")


def _normalize_symbol_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.upper()


def _parse_date_col(frame: pd.DataFrame, column: str | None) -> pd.Series:
    if column is None or column not in frame.columns:
        return pd.Series(pd.NaT, index=frame.index)
    return pd.to_datetime(frame[column], errors="coerce").dt.normalize()


def _numeric_series(
    frame: pd.DataFrame,
    column: str,
    *,
    default: float | int | None = np.nan,
) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce").fillna(default)


def _string_series(
    frame: pd.DataFrame,
    column: str,
    *,
    default: str = "",
) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype="object")
    return frame[column].fillna(default).astype(str)


def _first_existing(frame: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
    return None


def _sum(values: object) -> float:
    if isinstance(values, pd.Series):
        numeric = pd.to_numeric(values, errors="coerce").fillna(0.0)
    else:
        numeric = pd.Series([values], dtype="object")
        numeric = pd.to_numeric(numeric, errors="coerce").fillna(0.0)
    return float(numeric.sum())


def _profit_factor(gross_profit: float, gross_loss: float) -> object:
    if gross_loss == 0:
        return "" if gross_profit == 0 else np.inf
    return gross_profit / abs(gross_loss)


def _pct(numerator: object, denominator: object) -> float:
    num = _float_or_nan(numerator)
    den = _float_or_nan(denominator)
    if np.isnan(num) or np.isnan(den) or den == 0:
        return 0.0
    return float(num / den * 100.0)


def _safe_ratio(numerator: float, denominator: float) -> object:
    if denominator == 0:
        return ""
    return numerator / denominator


def _float_or_nan(value: object) -> float:
    try:
        if value is None or pd.isna(value):
            return np.nan
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def _int_or_blank(value: object) -> object:
    number = _float_or_nan(value)
    return "" if np.isnan(number) else int(number)


def _text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value)


def _mode_text(series: pd.Series | None) -> str:
    if series is None:
        return ""
    valid = series.dropna().astype(str).str.strip()
    valid = valid[valid.ne("")]
    if valid.empty:
        return ""
    return str(valid.mode().iloc[0])


def _mix_summary(series: pd.Series | None) -> str:
    if series is None:
        return ""
    counts = series.fillna("unknown").astype(str).str.strip().replace("", "unknown").value_counts()
    return "|".join(f"{bucket}:{int(count)}" for bucket, count in counts.sort_index().items())


def _write_csv(frame: pd.DataFrame, path: Path, columns: list[str]) -> Path:
    output = frame.copy()
    for column in columns:
        if column not in output.columns:
            output[column] = np.nan
    output = output.loc[:, columns]
    path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(path, index=False)
    return path


def _readme_text(*, include_vix: bool = False) -> str:
    lines = [
        "Phase 36B/36C Cross-Strategy Risk Input Diagnostic Audit",
        "",
        "This is a read-only diagnostic audit.",
        "It does not implement a risk model, dynamic sizing, filters, allocation, weights, or production rules.",
        "",
        "Outputs summarize liquidity, symbol concentration, gap exits, pre-entry gap context, ATR/volatility context, benchmark regime, sector diagnostics, drawdown state, rolling prior-trade R, rejection pressure, and optional India VIX diagnostics.",
        "",
        "India VIX diagnostics:",
    ]
    if include_vix:
        lines.extend(
            [
                "- Source table: market_indicators.",
                "- Identifier: INDIA_VIX by default; stored daily interval is day.",
                "- Value used: close.",
                "- Join convention: latest VIX session on or before signal_date when available; otherwise latest VIX session strictly before entry_date.",
                "- No future or after-entry VIX data is used.",
                "- VIX diagnostics are not trading rules and no thresholds have been approved.",
                "- VIX is a broad-market implied-volatility/fear proxy, not stock-specific volatility.",
            ]
        )
    else:
        lines.append("- VIX outputs are not produced unless --include-vix is used.")
    lines.extend(
        [
            "",
            "Caveats:",
            "- Liquidity buckets and liquidity metrics come from the static Research200 universe CSV.",
            "- Sector and classification fields are static/current diagnostics, not point-in-time historical truth.",
            "- Sector coverage is partial and must remain diagnostic-only.",
            "- Market-cap diagnostics are excluded because market_cap_bucket is currently unknown/unusable.",
            "- Accepted/rejected opportunity logs are excluded from first Phase 36B cross-strategy diagnostics because retained folders are not consistently populated.",
            "- Counterfactual rejected-signal PnL is not realized portfolio PnL.",
            "- Rolling R uses previous trades only and must not be optimized into thresholds without a separate pre-registered phase.",
            "",
        ]
    )
    return "\n".join(lines)
