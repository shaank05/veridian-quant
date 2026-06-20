"""Trade-subset impact diagnostics for I1 RAWRS features.

These utilities describe completed-trade subsets only. They do not rerun a
portfolio, replace removed trades, or account for capital and capacity reuse.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype


RAWRS_IMPACT_FILENAMES = {
    "keep_avoid_summary": "rawrs_keep_avoid_impact_summary.csv",
    "feature_impact_leaderboard": "rawrs_feature_impact_leaderboard.csv",
}
_EXCLUDED_RAWRS_COLUMNS = {
    "rawrs_feature_timestamp",
    "rawrs_realized_r",
}
_SUMMARY_COLUMNS = (
    "trade_count",
    "net_pnl_sum",
    "net_pnl_mean",
    "net_pnl_median",
    "mean_r",
    "median_r",
    "win_count",
    "loss_count",
    "win_rate",
    "avg_win_pnl",
    "avg_loss_pnl",
    "profit_factor",
    "total_initial_risk",
    "average_initial_risk",
)


def infer_rawrs_feature_columns(trades: pd.DataFrame) -> list[str]:
    """Return sorted numeric RAWRS feature columns suitable for bucketing."""

    return sorted(
        column
        for column in trades.columns
        if column.startswith("rawrs_")
        and column not in _EXCLUDED_RAWRS_COLUMNS
        and is_numeric_dtype(trades[column])
    )


def assign_rawrs_feature_buckets(
    trades: pd.DataFrame,
    feature_col: str,
    *,
    buckets: int = 5,
) -> pd.Series:
    """Return quantile bucket labels, reducing the count for sparse features."""

    if not isinstance(buckets, int) or buckets < 1:
        raise ValueError("buckets must be a positive integer")
    if feature_col not in trades.columns:
        raise ValueError(f"missing required feature column: {feature_col}")

    values = pd.to_numeric(trades[feature_col], errors="coerce")
    result = pd.Series(pd.NA, index=trades.index, dtype="Int64", name=feature_col)
    valid = values.dropna()
    unique_count = int(valid.nunique())
    if unique_count < 2:
        return result

    labels = pd.qcut(
        valid,
        q=min(buckets, unique_count),
        labels=False,
        duplicates="drop",
    )
    result.loc[valid.index] = labels.astype("Int64") + 1
    return result


def summarize_trade_subset(
    trades: pd.DataFrame,
    *,
    pnl_col: str = "net_pnl",
    r_col: str = "rawrs_realized_r",
    outcome_col: str | None = None,
) -> dict[str, object]:
    """Summarize PnL, realized R, outcomes, and risk for a trade subset."""

    summary: dict[str, object] = {column: np.nan for column in _SUMMARY_COLUMNS}
    summary["trade_count"] = int(len(trades))

    pnl = _numeric_column(trades, pnl_col)
    if pnl is not None:
        valid_pnl = pnl.dropna()
        summary.update(
            net_pnl_sum=valid_pnl.sum(min_count=1),
            net_pnl_mean=valid_pnl.mean(),
            net_pnl_median=valid_pnl.median(),
        )
        if not valid_pnl.empty:
            wins = valid_pnl[valid_pnl > 0]
            losses = valid_pnl[valid_pnl < 0]
            summary.update(
                win_count=int(len(wins)),
                loss_count=int(len(losses)),
                win_rate=float((valid_pnl > 0).mean()),
                avg_win_pnl=wins.mean(),
                avg_loss_pnl=losses.mean(),
            )
            if not wins.empty and not losses.empty:
                summary["profit_factor"] = wins.sum() / abs(losses.sum())
    elif outcome_col is not None and outcome_col in trades.columns:
        outcome = trades[outcome_col].astype("string").str.strip().str.lower()
        known = outcome.isin({"win", "winner", "won", "profit", "loss", "loser", "lost"})
        if known.any():
            wins = outcome.isin({"win", "winner", "won", "profit"}) & known
            losses = outcome.isin({"loss", "loser", "lost"}) & known
            summary.update(
                win_count=int(wins.sum()),
                loss_count=int(losses.sum()),
                win_rate=float(wins.sum() / known.sum()),
            )

    realized_r = _numeric_column(trades, r_col)
    if realized_r is not None:
        summary["mean_r"] = realized_r.mean()
        summary["median_r"] = realized_r.median()

    initial_risk = _numeric_column(trades, "initial_risk_amount")
    if initial_risk is not None:
        summary["total_initial_risk"] = initial_risk.sum(min_count=1)
        summary["average_initial_risk"] = initial_risk.mean()
    return summary


def build_rawrs_keep_avoid_impact_summary(
    trades: pd.DataFrame,
    *,
    feature_cols: list[str] | None = None,
    buckets: int = 5,
    pnl_col: str = "net_pnl",
    r_col: str = "rawrs_realized_r",
) -> pd.DataFrame:
    """Compare original, retained, and removed trades under simple bucket rules."""

    if not isinstance(buckets, int) or buckets < 1:
        raise ValueError("buckets must be a positive integer")
    selected = infer_rawrs_feature_columns(trades) if feature_cols is None else sorted(feature_cols)
    missing = [column for column in selected if column not in trades.columns]
    if missing:
        raise ValueError("missing RAWRS feature columns: " + ", ".join(missing))

    original = summarize_trade_subset(trades, pnl_col=pnl_col, r_col=r_col)
    rows: list[dict[str, object]] = []
    for feature in selected:
        assigned = assign_rawrs_feature_buckets(trades, feature, buckets=buckets)
        valid = assigned.notna()
        actual_bucket_count = int(assigned.max()) if valid.any() else 0
        note = _diagnostic_note(actual_bucket_count, buckets)
        if actual_bucket_count == 0:
            rules = {rule: pd.Series(False, index=trades.index) for rule in _RULE_NAMES}
        else:
            rules = {
                "avoid_bucket_1": valid & assigned.ne(1),
                "avoid_buckets_1_2": valid & assigned.gt(min(2, actual_bucket_count)),
                "keep_bucket_5": valid & assigned.eq(actual_bucket_count),
                "keep_buckets_4_5": valid & assigned.ge(max(1, actual_bucket_count - 1)),
            }

        for rule, keep_mask in rules.items():
            kept = trades.loc[keep_mask]
            removed = trades.loc[~keep_mask]
            kept_summary = summarize_trade_subset(kept, pnl_col=pnl_col, r_col=r_col)
            removed_summary = summarize_trade_subset(removed, pnl_col=pnl_col, r_col=r_col)
            original_count = int(original["trade_count"])
            kept_count = int(kept_summary["trade_count"])
            removed_count = int(removed_summary["trade_count"])
            row = {
                "feature": feature,
                "rule": rule,
                "bucket_count": actual_bucket_count,
                "original_trade_count": original_count,
                "kept_trade_count": kept_count,
                "removed_trade_count": removed_count,
                "kept_trade_pct": kept_count / original_count if original_count else np.nan,
                "removed_trade_pct": removed_count / original_count if original_count else np.nan,
                "diagnostic_note": note,
            }
            _add_comparison_metrics(row, original, kept_summary, removed_summary)
            rows.append(row)
    return pd.DataFrame(rows, columns=_IMPACT_COLUMNS)


def build_rawrs_feature_impact_leaderboard(summary: pd.DataFrame) -> pd.DataFrame:
    """Rank diagnostic rows using transparent, non-production comparison fields."""

    required = {
        "feature", "rule", "kept_trade_count", "kept_trade_pct",
        "original_mean_r", "kept_mean_r", "original_win_rate", "kept_win_rate",
        "removed_mean_r", "removed_net_pnl",
    }
    missing = sorted(required.difference(summary.columns))
    if missing:
        raise ValueError("missing impact summary columns: " + ", ".join(missing))

    result = summary.copy(deep=True)
    result["mean_r_improvement"] = result["kept_mean_r"] - result["original_mean_r"]
    result["win_rate_improvement"] = result["kept_win_rate"] - result["original_win_rate"]
    result["low_sample_warning"] = (result["kept_trade_count"] < 10) | (result["kept_trade_pct"] < 0.10)
    result["diagnostic_usefulness_score"] = (
        result["mean_r_improvement"].fillna(0.0)
        + result["win_rate_improvement"].fillna(0.0)
    )
    result = result.sort_values(
        ["low_sample_warning", "diagnostic_usefulness_score", "kept_trade_count", "feature", "rule"],
        ascending=[True, False, False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    result.insert(0, "diagnostic_rank", np.arange(1, len(result) + 1))
    return result


def export_rawrs_impact_csvs(
    *,
    output_dir: str | Path,
    keep_avoid_summary: pd.DataFrame,
    feature_impact_leaderboard: pd.DataFrame | None = None,
) -> dict[str, Path]:
    """Write standalone RAWRS impact CSVs to deterministic filenames."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    frames = {"keep_avoid_summary": keep_avoid_summary}
    if feature_impact_leaderboard is not None:
        frames["feature_impact_leaderboard"] = feature_impact_leaderboard
    written: dict[str, Path] = {}
    for name, frame in frames.items():
        path = output_path / RAWRS_IMPACT_FILENAMES[name]
        frame.copy(deep=True).to_csv(path, index=False)
        written[name] = path
    return written


_RULE_NAMES = ("avoid_bucket_1", "avoid_buckets_1_2", "keep_bucket_5", "keep_buckets_4_5")
_IMPACT_COLUMNS = [
    "feature", "rule", "bucket_count", "original_trade_count", "kept_trade_count",
    "removed_trade_count", "kept_trade_pct", "removed_trade_pct", "original_net_pnl",
    "kept_net_pnl", "removed_net_pnl", "pnl_delta_vs_original", "original_mean_r",
    "kept_mean_r", "removed_mean_r", "original_median_r", "kept_median_r",
    "removed_median_r", "original_win_rate", "kept_win_rate", "removed_win_rate",
    "original_profit_factor", "kept_profit_factor", "removed_profit_factor", "diagnostic_note",
]


def _numeric_column(frame: pd.DataFrame, column: str) -> pd.Series | None:
    if column not in frame.columns:
        return None
    return pd.to_numeric(frame[column], errors="coerce")


def _diagnostic_note(actual: int, requested: int) -> str:
    base = "completed-trade subset diagnostic only; not a portfolio rerun"
    if actual == 0:
        return base + "; insufficient valid feature values for bucketing"
    if actual < requested:
        return base + f"; bucket count reduced from {requested} to {actual}"
    return base


def _add_comparison_metrics(
    row: dict[str, object],
    original: dict[str, object],
    kept: dict[str, object],
    removed: dict[str, object],
) -> None:
    mappings = {
        "net_pnl": "net_pnl_sum",
        "mean_r": "mean_r",
        "median_r": "median_r",
        "win_rate": "win_rate",
        "profit_factor": "profit_factor",
    }
    for output_name, summary_name in mappings.items():
        row[f"original_{output_name}"] = original[summary_name]
        row[f"kept_{output_name}"] = kept[summary_name]
        row[f"removed_{output_name}"] = removed[summary_name]
    row["pnl_delta_vs_original"] = row["kept_net_pnl"] - row["original_net_pnl"]
