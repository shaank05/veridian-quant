"""Read-only raw NSE equity candidate-list builder."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import text


SUPPORTED_EXCHANGES = frozenset({"NSE_EQ"})

RAW_COLUMNS = [
    "instrument_key",
    "symbol",
    "trading_symbol",
    "name",
    "exchange",
    "segment",
    "instrument_type",
    "lot_size",
    "last_synced",
]

CLEAN_COLUMNS = [
    "rank",
    "instrument_key",
    "symbol",
    "trading_symbol",
    "name",
    "exchange",
    "segment",
    "instrument_type",
    "lot_size",
    "last_synced",
    "exclusion_reason",
]

REJECTED_COLUMNS = [
    "instrument_key",
    "symbol",
    "trading_symbol",
    "name",
    "exchange",
    "segment",
    "instrument_type",
    "lot_size",
    "last_synced",
    "exclusion_reason",
]

SUMMARY_COLUMNS = [
    "generated_at",
    "raw_candidates",
    "clean_candidates",
    "rejected_candidates",
    "exchange_filter",
    "instrument_type_filter",
    "starts_with_digit_rejections",
    "keyword_rejections",
]

BASE_EXCLUSION_KEYWORDS = (
    "NCD",
    "BOND",
    "DEB",
    "SDL",
    "TBILL",
    "TREPS",
    "INVIT",
    "REIT",
)

ETF_EXCLUSION_KEYWORDS = (
    "ETF",
    "BEES",
    "LIQUID",
    "GOLD",
    "SILVER",
)


def build_raw_nse_equity_candidates(
    engine: object,
    output_dir: Path,
    exchange: str = "NSE_EQ",
    include_etfs: bool = False,
    limit: int | None = None,
) -> dict[str, Path]:
    """Build raw and cleaned NSE equity candidate CSVs from instruments only."""

    _validate_inputs(exchange, limit)

    raw = _load_raw_candidates(engine, exchange, limit)
    evaluated = _apply_exclusion_rules(raw, include_etfs)
    clean = evaluated.loc[evaluated["exclusion_reason"] == "", REJECTED_COLUMNS].copy()
    clean = clean.reset_index(drop=True)
    clean.insert(0, "rank", range(1, len(clean) + 1))
    clean = clean.loc[:, CLEAN_COLUMNS]

    rejected = evaluated.loc[evaluated["exclusion_reason"] != "", REJECTED_COLUMNS].copy()
    summary = _build_summary(
        raw=raw,
        clean=clean,
        rejected=rejected,
        exchange=exchange,
        include_etfs=include_etfs,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "raw_nse_eq_candidates": output_dir / "raw_nse_eq_candidates.csv",
        "clean_nse_eq_candidates": output_dir / "clean_nse_eq_candidates.csv",
        "rejected_nse_eq_candidates": output_dir / "rejected_nse_eq_candidates.csv",
        "equity_candidate_summary": output_dir / "equity_candidate_summary.csv",
    }
    raw.to_csv(paths["raw_nse_eq_candidates"], index=False)
    clean.to_csv(paths["clean_nse_eq_candidates"], index=False)
    rejected.to_csv(paths["rejected_nse_eq_candidates"], index=False)
    summary.to_csv(paths["equity_candidate_summary"], index=False)
    return paths


def _load_raw_candidates(engine: object, exchange: str, limit: int | None) -> pd.DataFrame:
    limit_sql = "\nLIMIT :limit" if limit is not None else ""
    query = text(
        f"""
        SELECT
            instrument_key,
            symbol,
            trading_symbol,
            name,
            exchange,
            segment,
            instrument_type,
            lot_size,
            last_synced
        FROM instruments
        WHERE instrument_key LIKE :instrument_prefix
            AND UPPER(instrument_type) = 'EQ'
            AND NULLIF(TRIM(symbol), '') IS NOT NULL
            AND NULLIF(TRIM(trading_symbol), '') IS NOT NULL
            AND (lot_size = 1 OR lot_size IS NULL)
        ORDER BY symbol ASC, trading_symbol ASC, instrument_key ASC
        {limit_sql}
        """
    )
    params: dict[str, Any] = {"instrument_prefix": f"{exchange}|%"}
    if limit is not None:
        params["limit"] = limit
    df = pd.read_sql(query, engine, params=params)
    raw = _with_columns(df, RAW_COLUMNS)
    if raw.empty:
        return raw
    raw = raw.drop_duplicates(subset=["trading_symbol"], keep="first")
    return raw.reset_index(drop=True)


def _apply_exclusion_rules(raw: pd.DataFrame, include_etfs: bool) -> pd.DataFrame:
    evaluated = raw.copy()
    if evaluated.empty:
        evaluated["exclusion_reason"] = []
        return _with_columns(evaluated, REJECTED_COLUMNS)

    keywords = BASE_EXCLUSION_KEYWORDS
    if not include_etfs:
        keywords = keywords + ETF_EXCLUSION_KEYWORDS

    reasons = [
        "|".join(_exclusion_reasons(row, keywords))
        for _, row in evaluated.iterrows()
    ]
    evaluated["exclusion_reason"] = reasons
    return evaluated.loc[:, REJECTED_COLUMNS].copy()


def _exclusion_reasons(row: pd.Series, keywords: tuple[str, ...]) -> list[str]:
    symbol = _normalize_text(row.get("symbol"))
    trading_symbol = _normalize_text(row.get("trading_symbol"))
    values = (symbol, trading_symbol)
    reasons: list[str] = []

    if any(value[:1].isdigit() for value in values if value):
        reasons.append("STARTS_WITH_DIGIT")

    matched_keywords = [
        keyword
        for keyword in keywords
        if any(keyword in value for value in values)
    ]
    if matched_keywords:
        reasons.append("KEYWORD_" + ",".join(matched_keywords))

    return reasons


def _build_summary(
    raw: pd.DataFrame,
    clean: pd.DataFrame,
    rejected: pd.DataFrame,
    exchange: str,
    include_etfs: bool,
) -> pd.DataFrame:
    keyword_rejections = 0
    starts_with_digit_rejections = 0
    if not rejected.empty:
        reasons = rejected["exclusion_reason"].fillna("")
        starts_with_digit_rejections = int(
            reasons.str.contains("STARTS_WITH_DIGIT", regex=False).sum()
        )
        keyword_rejections = int(reasons.str.contains("KEYWORD_", regex=False).sum())

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "raw_candidates": int(len(raw)),
        "clean_candidates": int(len(clean)),
        "rejected_candidates": int(len(rejected)),
        "exchange_filter": f"{exchange}|%",
        "instrument_type_filter": "EQ",
        "starts_with_digit_rejections": starts_with_digit_rejections,
        "keyword_rejections": keyword_rejections,
    }
    return pd.DataFrame([summary], columns=SUMMARY_COLUMNS)


def _validate_inputs(exchange: str, limit: int | None) -> None:
    if exchange not in SUPPORTED_EXCHANGES:
        raise ValueError(f"unsupported exchange: {exchange}; expected NSE_EQ")
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive when provided")


def _with_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=columns)
    for column in columns:
        if column not in df.columns:
            df[column] = None
    return df.loc[:, columns].copy()


def _normalize_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().upper()
