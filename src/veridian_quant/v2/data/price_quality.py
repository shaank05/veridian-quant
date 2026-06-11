"""Read-only V2 price data quality audit helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import text


SUPPORTED_EXCHANGES = frozenset({"NSE_EQ", "NSE_INDEX"})
SUPPORTED_INTERVALS = frozenset({"day", "1minute"})

PRICE_COVERAGE_COLUMNS = [
    "instrument_key",
    "symbol",
    "trading_symbol",
    "name",
    "exchange",
    "segment",
    "instrument_type",
    "interval",
    "audit_start_date",
    "audit_end_date",
    "first_price_date",
    "last_price_date",
    "row_count",
    "expected_calendar_days",
    "observed_calendar_span_days",
    "missing_calendar_days",
    "missing_calendar_day_pct",
    "zero_volume_days",
    "zero_volume_pct",
    "bad_ohlc_rows",
    "duplicate_rows",
    "latest_close",
    "avg_volume_20d",
    "avg_turnover_20d",
    "avg_volume_60d",
    "avg_turnover_60d",
    "eligible_for_research",
    "rejection_reasons",
]

BAD_OHLC_COLUMNS = [
    "instrument_key",
    "symbol",
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "reason",
]

STALE_OR_INCOMPLETE_COLUMNS = [
    "instrument_key",
    "symbol",
    "first_price_date",
    "last_price_date",
    "row_count",
    "missing_calendar_day_pct",
    "zero_volume_pct",
    "rejection_reasons",
]

SUMMARY_COLUMNS = [
    "audit_start_date",
    "audit_end_date",
    "exchange",
    "interval",
    "instruments_checked",
    "eligible_instruments",
    "rejected_instruments",
    "instruments_with_no_data",
    "instruments_with_bad_ohlc",
    "instruments_with_zero_volume",
    "average_missing_calendar_day_pct",
    "median_missing_calendar_day_pct",
    "average_zero_volume_pct",
    "median_zero_volume_pct",
]


@dataclass(frozen=True, slots=True)
class PriceAuditThresholds:
    """Thresholds used to decide research eligibility."""

    min_history_days: int = 1000
    max_missing_day_pct: float = 10.0
    max_zero_volume_pct: float = 5.0
    min_avg_volume_60d: float = 0
    min_avg_turnover_60d: float = 0
    recent_days: int = 60


def audit_price_data(
    engine: object,
    exchange: str,
    interval: str,
    start_date: date,
    end_date: date,
    output_dir: Path,
    min_history_days: int = 1000,
    max_missing_day_pct: float = 10.0,
    max_zero_volume_pct: float = 5.0,
    min_avg_volume_60d: float = 0,
    min_avg_turnover_60d: float = 0,
    recent_days: int = 60,
    limit: int | None = None,
) -> dict[str, Path]:
    """Audit read-only OHLCV quality and write CSV reports."""

    _validate_inputs(
        exchange=exchange,
        interval=interval,
        start_date=start_date,
        end_date=end_date,
        min_history_days=min_history_days,
        recent_days=recent_days,
        limit=limit,
    )

    thresholds = PriceAuditThresholds(
        min_history_days=min_history_days,
        max_missing_day_pct=max_missing_day_pct,
        max_zero_volume_pct=max_zero_volume_pct,
        min_avg_volume_60d=min_avg_volume_60d,
        min_avg_turnover_60d=min_avg_turnover_60d,
        recent_days=recent_days,
    )

    instruments = _load_instruments(engine, exchange, limit)
    prices = _load_prices(engine, exchange, interval, start_date, end_date, limit)
    coverage, bad_rows = _build_audit_frames(
        instruments=instruments,
        prices=prices,
        exchange=exchange,
        interval=interval,
        start_date=start_date,
        end_date=end_date,
        thresholds=thresholds,
    )
    stale = coverage.loc[
        ~coverage["eligible_for_research"],
        STALE_OR_INCOMPLETE_COLUMNS,
    ].copy()
    summary = _build_summary(coverage, exchange, interval, start_date, end_date)

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "price_coverage": output_dir / "price_coverage.csv",
        "bad_ohlc_rows": output_dir / "bad_ohlc_rows.csv",
        "stale_or_incomplete_symbols": output_dir / "stale_or_incomplete_symbols.csv",
        "price_quality_summary": output_dir / "price_quality_summary.csv",
    }
    coverage.to_csv(paths["price_coverage"], index=False)
    bad_rows.to_csv(paths["bad_ohlc_rows"], index=False)
    stale.to_csv(paths["stale_or_incomplete_symbols"], index=False)
    summary.to_csv(paths["price_quality_summary"], index=False)
    return paths


def _load_instruments(engine: object, exchange: str, limit: int | None) -> pd.DataFrame:
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
            instrument_type
        FROM instruments
        WHERE instrument_key LIKE :instrument_prefix
        ORDER BY symbol ASC, trading_symbol ASC, instrument_key ASC
        {limit_sql}
        """
    )
    params: dict[str, Any] = {"instrument_prefix": f"{exchange}|%"}
    if limit is not None:
        params["limit"] = limit
    df = pd.read_sql(query, engine, params=params)
    return _with_columns(df, PRICE_COVERAGE_COLUMNS[:7])


def _load_prices(
    engine: object,
    exchange: str,
    interval: str,
    start_date: date,
    end_date: date,
    limit: int | None,
) -> pd.DataFrame:
    limit_sql = "\nLIMIT :limit" if limit is not None else ""
    query = text(
        f"""
        SELECT
            p.instrument_key,
            p.timestamp,
            p.open,
            p.high,
            p.low,
            p.close,
            p.volume,
            p.interval
        FROM prices_ohlc p
        JOIN (
            SELECT instrument_key
            FROM instruments
            WHERE instrument_key LIKE :instrument_prefix
            ORDER BY symbol ASC, trading_symbol ASC, instrument_key ASC
            {limit_sql}
        ) selected
            ON p.instrument_key = selected.instrument_key
        WHERE p.interval = :interval
            AND p.timestamp >= :start_date
            AND p.timestamp < :exclusive_end_date
        ORDER BY p.instrument_key ASC, p.timestamp ASC
        """
    )
    params: dict[str, Any] = {
        "instrument_prefix": f"{exchange}|%",
        "interval": interval,
        "start_date": start_date,
        "exclusive_end_date": end_date + timedelta(days=1),
    }
    if limit is not None:
        params["limit"] = limit
    df = pd.read_sql(query, engine, params=params)
    return _normalize_prices(df)


def _build_audit_frames(
    instruments: pd.DataFrame,
    prices: pd.DataFrame,
    exchange: str,
    interval: str,
    start_date: date,
    end_date: date,
    thresholds: PriceAuditThresholds,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    bad_rows: list[dict[str, Any]] = []
    expected_calendar_days = (end_date - start_date).days + 1

    prices_by_key = {
        instrument_key: group.copy()
        for instrument_key, group in prices.groupby("instrument_key", sort=False)
    }

    for _, instrument in instruments.iterrows():
        instrument_key = str(instrument["instrument_key"])
        symbol = _string_or_empty(instrument.get("symbol"))
        instrument_prices = prices_by_key.get(instrument_key, _empty_prices())
        instrument_prices = instrument_prices.sort_values("timestamp").reset_index(drop=True)

        row_bad = _bad_ohlc_rows(instrument_prices, symbol)
        bad_rows.extend(row_bad)

        coverage = _coverage_row(
            instrument=instrument,
            prices=instrument_prices,
            row_bad_count=len(row_bad),
            exchange=exchange,
            interval=interval,
            start_date=start_date,
            end_date=end_date,
            expected_calendar_days=expected_calendar_days,
            thresholds=thresholds,
        )
        rows.append(coverage)

    coverage = pd.DataFrame(rows, columns=PRICE_COVERAGE_COLUMNS)
    bad = pd.DataFrame(bad_rows, columns=BAD_OHLC_COLUMNS)
    return coverage, bad


def _coverage_row(
    instrument: pd.Series,
    prices: pd.DataFrame,
    row_bad_count: int,
    exchange: str,
    interval: str,
    start_date: date,
    end_date: date,
    expected_calendar_days: int,
    thresholds: PriceAuditThresholds,
) -> dict[str, Any]:
    row_count = int(len(prices))
    first_price_date = None
    last_price_date = None
    observed_span_days = 0
    missing_calendar_days = expected_calendar_days
    zero_volume_days = 0
    zero_volume_pct = 0.0
    duplicate_rows = 0
    latest_close = None
    avg_volume_20d = 0.0
    avg_turnover_20d = 0.0
    avg_volume_60d = 0.0
    avg_turnover_60d = 0.0

    if row_count:
        dates = prices["price_date"]
        first_price_date = dates.min()
        last_price_date = dates.max()
        observed_span_days = int((last_price_date - first_price_date).days + 1)
        observed_days = int(dates.nunique())
        missing_calendar_days = max(expected_calendar_days - observed_days, 0)
        zero_volume_days = int((prices["volume"] == 0).sum())
        zero_volume_pct = _pct(zero_volume_days, row_count)
        duplicate_rows = int(prices.duplicated(["timestamp"]).sum())
        latest_close = _float_or_none(prices.iloc[-1]["close"])
        avg_volume_20d, avg_turnover_20d = _recent_averages(prices, 20)
        avg_volume_60d, avg_turnover_60d = _recent_averages(prices, thresholds.recent_days)

    missing_calendar_day_pct = _pct(missing_calendar_days, expected_calendar_days)
    reasons = _rejection_reasons(
        row_count=row_count,
        first_price_date=first_price_date,
        last_price_date=last_price_date,
        start_date=start_date,
        end_date=end_date,
        missing_calendar_day_pct=missing_calendar_day_pct,
        zero_volume_pct=zero_volume_pct,
        bad_ohlc_rows=row_bad_count,
        avg_volume_60d=avg_volume_60d,
        avg_turnover_60d=avg_turnover_60d,
        thresholds=thresholds,
    )

    return {
        "instrument_key": instrument["instrument_key"],
        "symbol": instrument.get("symbol"),
        "trading_symbol": instrument.get("trading_symbol"),
        "name": instrument.get("name"),
        "exchange": instrument.get("exchange"),
        "segment": instrument.get("segment"),
        "instrument_type": instrument.get("instrument_type"),
        "interval": interval,
        "audit_start_date": start_date.isoformat(),
        "audit_end_date": end_date.isoformat(),
        "first_price_date": _date_string(first_price_date),
        "last_price_date": _date_string(last_price_date),
        "row_count": row_count,
        "expected_calendar_days": expected_calendar_days,
        "observed_calendar_span_days": observed_span_days,
        "missing_calendar_days": missing_calendar_days,
        "missing_calendar_day_pct": round(missing_calendar_day_pct, 6),
        "zero_volume_days": zero_volume_days,
        "zero_volume_pct": round(zero_volume_pct, 6),
        "bad_ohlc_rows": row_bad_count,
        "duplicate_rows": duplicate_rows,
        "latest_close": latest_close,
        "avg_volume_20d": round(avg_volume_20d, 6),
        "avg_turnover_20d": round(avg_turnover_20d, 6),
        "avg_volume_60d": round(avg_volume_60d, 6),
        "avg_turnover_60d": round(avg_turnover_60d, 6),
        "eligible_for_research": not reasons,
        "rejection_reasons": "|".join(reasons),
    }


def _bad_ohlc_rows(prices: pd.DataFrame, symbol: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, row in prices.iterrows():
        reasons = _bad_ohlc_reasons(row)
        if not reasons:
            continue
        rows.append(
            {
                "instrument_key": row["instrument_key"],
                "symbol": symbol,
                "timestamp": _timestamp_string(row["timestamp"]),
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": row["volume"],
                "reason": "|".join(reasons),
            }
        )
    return rows


def _bad_ohlc_reasons(row: pd.Series) -> list[str]:
    checks = [
        ("HIGH_LT_LOW", row["high"] < row["low"]),
        ("HIGH_LT_OPEN", row["high"] < row["open"]),
        ("HIGH_LT_CLOSE", row["high"] < row["close"]),
        ("LOW_GT_OPEN", row["low"] > row["open"]),
        ("LOW_GT_CLOSE", row["low"] > row["close"]),
        ("OPEN_LE_ZERO", row["open"] <= 0),
        ("HIGH_LE_ZERO", row["high"] <= 0),
        ("LOW_LE_ZERO", row["low"] <= 0),
        ("CLOSE_LE_ZERO", row["close"] <= 0),
    ]
    return [reason for reason, failed in checks if bool(failed)]


def _rejection_reasons(
    row_count: int,
    first_price_date: date | None,
    last_price_date: date | None,
    start_date: date,
    end_date: date,
    missing_calendar_day_pct: float,
    zero_volume_pct: float,
    bad_ohlc_rows: int,
    avg_volume_60d: float,
    avg_turnover_60d: float,
    thresholds: PriceAuditThresholds,
) -> list[str]:
    reasons: list[str] = []
    if row_count == 0:
        reasons.append("NO_DATA")
    if row_count < thresholds.min_history_days:
        reasons.append("INSUFFICIENT_HISTORY")
    if first_price_date is None or first_price_date > start_date + timedelta(days=30):
        reasons.append("INCOMPLETE_START")
    if last_price_date is None or last_price_date < end_date - timedelta(days=30):
        reasons.append("STALE_DATA")
    if missing_calendar_day_pct > thresholds.max_missing_day_pct:
        reasons.append("EXCESS_MISSING_DAYS")
    if zero_volume_pct > thresholds.max_zero_volume_pct:
        reasons.append("EXCESS_ZERO_VOLUME")
    if bad_ohlc_rows:
        reasons.append("BAD_OHLC")
    if avg_volume_60d < thresholds.min_avg_volume_60d:
        reasons.append("LOW_AVG_VOLUME_60D")
    if avg_turnover_60d < thresholds.min_avg_turnover_60d:
        reasons.append("LOW_AVG_TURNOVER_60D")
    return reasons


def _build_summary(
    coverage: pd.DataFrame,
    exchange: str,
    interval: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    summary = {
        "audit_start_date": start_date.isoformat(),
        "audit_end_date": end_date.isoformat(),
        "exchange": exchange,
        "interval": interval,
        "instruments_checked": int(len(coverage)),
        "eligible_instruments": int(coverage["eligible_for_research"].sum()) if not coverage.empty else 0,
        "rejected_instruments": int((~coverage["eligible_for_research"]).sum()) if not coverage.empty else 0,
        "instruments_with_no_data": int((coverage["row_count"] == 0).sum()) if not coverage.empty else 0,
        "instruments_with_bad_ohlc": int((coverage["bad_ohlc_rows"] > 0).sum()) if not coverage.empty else 0,
        "instruments_with_zero_volume": int((coverage["zero_volume_days"] > 0).sum()) if not coverage.empty else 0,
        "average_missing_calendar_day_pct": _mean(coverage, "missing_calendar_day_pct"),
        "median_missing_calendar_day_pct": _median(coverage, "missing_calendar_day_pct"),
        "average_zero_volume_pct": _mean(coverage, "zero_volume_pct"),
        "median_zero_volume_pct": _median(coverage, "zero_volume_pct"),
    }
    return pd.DataFrame([summary], columns=SUMMARY_COLUMNS)


def _normalize_prices(df: pd.DataFrame) -> pd.DataFrame:
    df = _with_columns(
        df,
        ["instrument_key", "timestamp", "open", "high", "low", "close", "volume", "interval"],
    )
    if df.empty:
        return _empty_prices()
    normalized = df.copy()
    normalized["timestamp"] = pd.to_datetime(normalized["timestamp"])
    normalized["price_date"] = normalized["timestamp"].dt.date
    for column in ("open", "high", "low", "close", "volume"):
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
    normalized = normalized.dropna(subset=["timestamp", "open", "high", "low", "close", "volume"])
    return normalized


def _recent_averages(prices: pd.DataFrame, days: int) -> tuple[float, float]:
    recent = prices.tail(days).copy()
    if recent.empty:
        return 0.0, 0.0
    turnover = recent["close"] * recent["volume"]
    return float(recent["volume"].mean()), float(turnover.mean())


def _empty_prices() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "instrument_key",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "interval",
            "price_date",
        ]
    )


def _validate_inputs(
    exchange: str,
    interval: str,
    start_date: date,
    end_date: date,
    min_history_days: int,
    recent_days: int,
    limit: int | None,
) -> None:
    if exchange not in SUPPORTED_EXCHANGES:
        raise ValueError(f"unsupported exchange: {exchange}; expected NSE_EQ or NSE_INDEX")
    if interval not in SUPPORTED_INTERVALS:
        raise ValueError(f"unsupported interval: {interval}; expected day or 1minute")
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date")
    if min_history_days < 0:
        raise ValueError("min_history_days must be non-negative")
    if recent_days <= 0:
        raise ValueError("recent_days must be positive")
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive when provided")


def _with_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=columns)
    for column in columns:
        if column not in df.columns:
            df[column] = None
    return df.loc[:, columns].copy()


def _pct(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator) * 100.0


def _mean(df: pd.DataFrame, column: str) -> float:
    if df.empty:
        return 0.0
    return round(float(df[column].mean()), 6)


def _median(df: pd.DataFrame, column: str) -> float:
    if df.empty:
        return 0.0
    return round(float(df[column].median()), 6)


def _date_string(value: date | None) -> str:
    return value.isoformat() if value is not None else ""


def _timestamp_string(value: Any) -> str:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _float_or_none(value: Any) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def _string_or_empty(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value)
