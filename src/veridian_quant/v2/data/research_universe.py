"""Build deterministic V2 research universes from audited coverage CSVs."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd


HARD_EXCLUDED_SYMBOLS = frozenset({"MAZDOCK"})
BUCKETS = ("HIGH", "MID", "LOW")
BUCKET_WEIGHTS = {"HIGH": 0.4, "MID": 0.4, "LOW": 0.2}
PREFERRED_LIQUIDITY_COLUMNS = (
    "avg_turnover",
    "avg_turnover_60d",
    "avg_turnover_20d",
    "avg_volume",
    "avg_volume_60d",
    "avg_volume_20d",
    "row_count",
)

BASE_UNIVERSE_COLUMNS = [
    "selection_rank",
    "symbol",
    "instrument_key",
    "trading_symbol",
    "name",
    "liquidity_bucket",
    "liquidity_metric",
    "row_count",
    "first_price_date",
    "last_price_date",
    "missing_day_pct",
    "zero_volume_pct",
    "bad_ohlc_rows",
    "eligible_for_research",
    "universe_size",
    "selection_seed",
    "source_coverage_file",
]

ELIGIBLE_COLUMNS = [
    "symbol",
    "instrument_key",
    "trading_symbol",
    "name",
    "liquidity_bucket",
    "liquidity_metric",
    "row_count",
    "first_price_date",
    "last_price_date",
    "missing_day_pct",
    "zero_volume_pct",
    "bad_ohlc_rows",
    "eligible_for_research",
    "selection_seed",
    "source_coverage_file",
]

REJECTION_COLUMNS = [
    "symbol",
    "instrument_key",
    "rejection_reason",
    "eligible_for_research",
    "bad_ohlc_rows",
    "duplicate_rows",
    "first_price_date",
    "last_price_date",
]

SUMMARY_COLUMNS = [
    "source_coverage_file",
    "bad_ohlc_file",
    "start_date",
    "end_date",
    "total_coverage_rows",
    "eligible_before_bad_ohlc_exclusion",
    "bad_ohlc_symbols_excluded",
    "eligible_after_exclusions",
    "research_100_size",
    "research_200_size",
    "seed",
    "high_bucket_count",
    "mid_bucket_count",
    "low_bucket_count",
    "output_dir",
]


@dataclass(frozen=True, slots=True)
class ResearchUniverseResult:
    """In-memory frames and output paths for a universe build."""

    paths: dict[str, Path]
    eligible: pd.DataFrame
    rejections: pd.DataFrame
    summary: pd.DataFrame
    universes: dict[int, pd.DataFrame]


def build_research_universes(
    coverage_file: Path,
    output_dir: Path,
    start_date: str,
    end_date: str,
    bad_ohlc_file: Path | None = None,
    seed: int = 42,
    sizes: tuple[int, ...] = (100, 200),
) -> ResearchUniverseResult:
    """Build eligible and balanced research universe CSVs from audit outputs."""

    _validate_inputs(coverage_file, bad_ohlc_file, sizes)

    coverage = pd.read_csv(coverage_file)
    coverage = _normalize_coverage(coverage)
    bad_symbols = _load_bad_ohlc_symbols(bad_ohlc_file)
    eligible, rejections = _eligible_and_rejections(coverage, bad_symbols)

    metric_column = _liquidity_metric_column(coverage)
    eligible = _assign_liquidity_metadata(eligible, metric_column)
    universes = {
        size: _select_universe(eligible, requested_size=size, seed=seed)
        for size in sizes
    }

    source_coverage = str(coverage_file)
    for size, universe in universes.items():
        universe["universe_size"] = size
        universe["selection_seed"] = seed
        universe["source_coverage_file"] = source_coverage
        universes[size] = _with_columns(universe, BASE_UNIVERSE_COLUMNS).sort_values(
            ["symbol", "instrument_key"],
            kind="mergesort",
        )

    eligible_out = eligible.copy()
    eligible_out["selection_seed"] = seed
    eligible_out["source_coverage_file"] = source_coverage
    eligible_out = _with_columns(eligible_out, ELIGIBLE_COLUMNS).sort_values(
        ["symbol", "instrument_key"],
        kind="mergesort",
    )

    rejections = _with_columns(rejections, REJECTION_COLUMNS).sort_values(
        ["symbol", "instrument_key"],
        kind="mergesort",
    )
    summary = _build_summary(
        coverage_file=coverage_file,
        bad_ohlc_file=bad_ohlc_file,
        start_date=start_date,
        end_date=end_date,
        output_dir=output_dir,
        total_coverage_rows=len(coverage),
        eligible_before_bad_ohlc_exclusion=_eligible_before_bad_exclusion(coverage),
        bad_ohlc_symbols_excluded=len(bad_symbols),
        eligible=eligible,
        universes=universes,
        seed=seed,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "eligible": output_dir / "nse_eq_eligible_2018_2026.csv",
        "summary": output_dir / "nse_eq_research_universe_summary.csv",
        "rejections": output_dir / "nse_eq_research_universe_rejections.csv",
    }
    for size in sizes:
        paths[f"research_{size}"] = output_dir / f"nse_eq_research_{size}_2018_2026.csv"

    eligible_out.to_csv(paths["eligible"], index=False)
    for size, universe in universes.items():
        universe.to_csv(paths[f"research_{size}"], index=False)
    summary.to_csv(paths["summary"], index=False)
    rejections.to_csv(paths["rejections"], index=False)

    return ResearchUniverseResult(
        paths=paths,
        eligible=eligible_out,
        rejections=rejections,
        summary=summary,
        universes=universes,
    )


def _validate_inputs(
    coverage_file: Path,
    bad_ohlc_file: Path | None,
    sizes: tuple[int, ...],
) -> None:
    if not coverage_file.exists():
        raise FileNotFoundError(f"coverage file not found: {coverage_file}")
    if bad_ohlc_file is not None and not bad_ohlc_file.exists():
        raise FileNotFoundError(f"bad OHLC file not found: {bad_ohlc_file}")
    if not sizes:
        raise ValueError("at least one universe size is required")
    if any(size <= 0 for size in sizes):
        raise ValueError("universe sizes must be positive")


def _normalize_coverage(coverage: pd.DataFrame) -> pd.DataFrame:
    df = coverage.copy()
    for column in ("symbol", "instrument_key"):
        if column not in df.columns:
            raise ValueError(f"coverage file is missing required column: {column}")
    defaults: dict[str, Any] = {
        "eligible_for_research": False,
        "bad_ohlc_rows": 0,
        "duplicate_rows": 0,
        "stale_data": False,
        "row_count": 0,
        "first_price_date": "",
        "last_price_date": "",
    }
    for column, default in defaults.items():
        if column not in df.columns:
            df[column] = default
    for column in ("symbol", "instrument_key", "trading_symbol", "name"):
        if column not in df.columns:
            df[column] = ""
        df[column] = df[column].fillna("").astype(str).str.strip()
    for column in ("bad_ohlc_rows", "duplicate_rows", "row_count"):
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)
    if "missing_day_pct" not in df.columns:
        df["missing_day_pct"] = df.get("missing_calendar_day_pct", 0.0)
    df["eligible_for_research"] = df["eligible_for_research"].map(_truthy)
    df["stale_data"] = df["stale_data"].map(_truthy)
    return df


def _load_bad_ohlc_symbols(bad_ohlc_file: Path | None) -> set[str]:
    symbols = set(HARD_EXCLUDED_SYMBOLS)
    if bad_ohlc_file is None:
        return symbols
    bad = pd.read_csv(bad_ohlc_file)
    if "symbol" not in bad.columns:
        return symbols
    file_symbols = {
        _normalize_symbol(symbol)
        for symbol in bad["symbol"]
        if _normalize_symbol(symbol)
    }
    return symbols | file_symbols


def _eligible_and_rejections(
    coverage: pd.DataFrame,
    bad_symbols: set[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    reasons = [_rejection_reasons(row, bad_symbols) for _, row in coverage.iterrows()]
    evaluated = coverage.copy()
    evaluated["rejection_reason"] = ["|".join(row_reasons) for row_reasons in reasons]

    eligible = evaluated.loc[evaluated["rejection_reason"] == ""].copy()
    rejections = evaluated.loc[evaluated["rejection_reason"] != ""].copy()
    return eligible.reset_index(drop=True), rejections.reset_index(drop=True)


def _rejection_reasons(row: pd.Series, bad_symbols: set[str]) -> list[str]:
    reasons: list[str] = []
    symbol = _normalize_symbol(row.get("symbol"))
    instrument_key = _normalize_text(row.get("instrument_key"))

    if not symbol:
        reasons.append("BLANK_SYMBOL")
    if not instrument_key:
        reasons.append("BLANK_INSTRUMENT_KEY")
    if not _truthy(row.get("eligible_for_research")):
        reasons.append("NOT_ELIGIBLE_FOR_RESEARCH")
    if _numeric(row.get("bad_ohlc_rows")) > 0:
        reasons.append("BAD_OHLC_ROWS")
    if _numeric(row.get("duplicate_rows")) > 0:
        reasons.append("DUPLICATE_ROWS")
    if _truthy(row.get("stale_data")):
        reasons.append("STALE_DATA")
    if symbol in bad_symbols:
        reasons.append("BAD_OHLC_SYMBOL")
    return reasons


def _liquidity_metric_column(coverage: pd.DataFrame) -> str:
    for column in PREFERRED_LIQUIDITY_COLUMNS:
        if column in coverage.columns:
            return column
    return "row_count"


def _assign_liquidity_metadata(
    eligible: pd.DataFrame,
    metric_column: str,
) -> pd.DataFrame:
    df = eligible.copy()
    if df.empty:
        df["liquidity_metric"] = []
        df["liquidity_bucket"] = []
        return df

    df["liquidity_metric"] = pd.to_numeric(
        df.get(metric_column, df["row_count"]),
        errors="coerce",
    ).fillna(0.0)
    ordered = df.sort_values(
        ["liquidity_metric", "symbol", "instrument_key"],
        ascending=[False, True, True],
        kind="mergesort",
    ).copy()
    count = len(ordered)
    high_cutoff = max(1, int(round(count / 3)))
    mid_cutoff = max(high_cutoff, int(round((count * 2) / 3)))
    buckets = []
    for idx in range(count):
        if idx < high_cutoff:
            buckets.append("HIGH")
        elif idx < mid_cutoff:
            buckets.append("MID")
        else:
            buckets.append("LOW")
    ordered["liquidity_bucket"] = buckets
    return ordered.sort_index(kind="mergesort").reset_index(drop=True)


def _select_universe(
    eligible: pd.DataFrame,
    requested_size: int,
    seed: int,
) -> pd.DataFrame:
    target_size = min(requested_size, len(eligible))
    selected_indices: list[int] = []
    if target_size == 0:
        output = eligible.head(0).copy()
        output.insert(0, "selection_rank", [])
        return output

    remaining_slots = target_size
    bucket_targets = _bucket_targets(target_size)
    ranked = eligible.copy()
    ranked["_selection_score"] = [
        _stable_selection_score(seed, row["symbol"], row["liquidity_bucket"])
        for _, row in ranked.iterrows()
    ]

    for bucket in BUCKETS:
        bucket_rows = ranked.loc[ranked["liquidity_bucket"] == bucket].sort_values(
            ["_selection_score", "symbol", "instrument_key"],
            kind="mergesort",
        )
        take = min(bucket_targets[bucket], len(bucket_rows), remaining_slots)
        selected_indices.extend(bucket_rows.head(take).index.tolist())
        remaining_slots -= take

    if remaining_slots > 0:
        selected = set(selected_indices)
        fillers = ranked.loc[~ranked.index.isin(selected)].sort_values(
            ["_selection_score", "symbol", "instrument_key"],
            kind="mergesort",
        )
        selected_indices.extend(fillers.head(remaining_slots).index.tolist())

    selected = ranked.loc[selected_indices].copy()
    selected = selected.sort_values(
        ["_selection_score", "symbol", "instrument_key"],
        kind="mergesort",
    ).drop(columns=["_selection_score"])
    selected.insert(0, "selection_rank", range(1, len(selected) + 1))
    return selected.reset_index(drop=True)


def _bucket_targets(size: int) -> dict[str, int]:
    high = int(round(size * BUCKET_WEIGHTS["HIGH"]))
    mid = int(round(size * BUCKET_WEIGHTS["MID"]))
    low = size - high - mid
    return {"HIGH": high, "MID": mid, "LOW": low}


def _stable_selection_score(seed: int, symbol: str, bucket: str) -> str:
    value = f"{seed}|{bucket}|{_normalize_symbol(symbol)}"
    return sha256(value.encode("utf-8")).hexdigest()


def _build_summary(
    coverage_file: Path,
    bad_ohlc_file: Path | None,
    start_date: str,
    end_date: str,
    output_dir: Path,
    total_coverage_rows: int,
    eligible_before_bad_ohlc_exclusion: int,
    bad_ohlc_symbols_excluded: int,
    eligible: pd.DataFrame,
    universes: dict[int, pd.DataFrame],
    seed: int,
) -> pd.DataFrame:
    bucket_counts = eligible["liquidity_bucket"].value_counts().to_dict()
    summary = {
        "source_coverage_file": str(coverage_file),
        "bad_ohlc_file": "" if bad_ohlc_file is None else str(bad_ohlc_file),
        "start_date": start_date,
        "end_date": end_date,
        "total_coverage_rows": total_coverage_rows,
        "eligible_before_bad_ohlc_exclusion": eligible_before_bad_ohlc_exclusion,
        "bad_ohlc_symbols_excluded": bad_ohlc_symbols_excluded,
        "eligible_after_exclusions": len(eligible),
        "research_100_size": len(universes.get(100, pd.DataFrame())),
        "research_200_size": len(universes.get(200, pd.DataFrame())),
        "seed": seed,
        "high_bucket_count": int(bucket_counts.get("HIGH", 0)),
        "mid_bucket_count": int(bucket_counts.get("MID", 0)),
        "low_bucket_count": int(bucket_counts.get("LOW", 0)),
        "output_dir": str(output_dir),
    }
    return pd.DataFrame([summary], columns=SUMMARY_COLUMNS)


def _eligible_before_bad_exclusion(coverage: pd.DataFrame) -> int:
    mask = (
        coverage["eligible_for_research"].map(_truthy)
        & coverage["symbol"].astype(str).str.strip().ne("")
        & coverage["instrument_key"].astype(str).str.strip().ne("")
        & (pd.to_numeric(coverage["bad_ohlc_rows"], errors="coerce").fillna(0) == 0)
        & (pd.to_numeric(coverage["duplicate_rows"], errors="coerce").fillna(0) == 0)
        & ~coverage["stale_data"].map(_truthy)
    )
    return int(mask.sum())


def _with_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    output = df.copy()
    for column in columns:
        if column not in output.columns:
            output[column] = None
    return output.loc[:, columns].copy()


def _truthy(value: Any) -> bool:
    if value is None or pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def _numeric(value: Any) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(parsed):
        return 0.0
    return float(parsed)


def _normalize_symbol(value: Any) -> str:
    return _normalize_text(value).upper()


def _normalize_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()
