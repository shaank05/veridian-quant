"""Daily OHLCV data loading helpers for Veridian Quant v2.

This module converts database-backed daily price data into the in-memory
lowercase OHLCV dataframe shape expected by v2 backtest runners. It does not
generate signals, run strategies, or perform backtest orchestration. The
SQLAlchemy loader filters ``prices_ohlc.interval = 'day'`` by default.
"""

from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import Iterable, Mapping

import pandas as pd
from sqlalchemy import text


OHLCV_COLUMNS = ("date", "open", "high", "low", "close", "volume")


def normalize_ohlcv_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Return a normalized daily OHLCV dataframe without mutating input."""

    normalized = df.copy(deep=True)
    normalized.columns = [str(column).lower() for column in normalized.columns]

    missing = [column for column in OHLCV_COLUMNS if column not in normalized.columns]
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")

    normalized = normalized.loc[:, OHLCV_COLUMNS].copy()
    normalized["date"] = pd.to_datetime(normalized["date"])
    normalized = normalized.sort_values("date")
    normalized = normalized.drop_duplicates(subset="date", keep="last")
    return normalized.reset_index(drop=True)


class DailyOHLCVLoader(ABC):
    """Interface for loading daily OHLCV dataframes for v2 backtests."""

    @abstractmethod
    def load_symbol(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Load one symbol's normalized daily OHLCV dataframe."""

    @abstractmethod
    def load_symbols(
        self,
        symbols: Iterable[str],
        start_date: date,
        end_date: date,
    ) -> Mapping[str, pd.DataFrame]:
        """Load normalized daily OHLCV dataframes for requested symbols."""

    @abstractmethod
    def load_all_available_symbols(
        self,
        start_date: date,
        end_date: date,
    ) -> Mapping[str, pd.DataFrame]:
        """Load normalized daily OHLCV dataframes for available symbols."""


class SQLAlchemyDailyOHLCVLoader(DailyOHLCVLoader):
    """SQLAlchemy-backed daily OHLCV loader.

    The all-symbol discovery query assumes NSE equity instrument keys use the
    ``NSE_EQ|`` prefix and excludes non-equity rows unless requested explicitly
    through ``load_symbol`` or ``load_symbols``. Symbol loads query a configurable
    pre-start buffer, so returned dataframes may contain rows before
    ``start_date`` for indicator warmup. Price rows are filtered by
    ``prices_ohlc.interval`` and default to daily bars.
    """

    def __init__(
        self,
        engine: object,
        price_table: str = "prices_ohlc",
        instrument_table: str = "instruments",
        lookback_buffer_days: int = 120,
        price_interval: str = "day",
    ) -> None:
        if lookback_buffer_days < 0:
            raise ValueError("lookback_buffer_days must be non-negative")
        if not isinstance(price_interval, str) or not price_interval:
            raise ValueError("price_interval must be a non-empty string")
        self.engine = engine
        self.price_table = _validate_identifier(price_table)
        self.instrument_table = _validate_identifier(instrument_table)
        self.lookback_buffer_days = lookback_buffer_days
        self.price_interval = price_interval

    def load_symbol(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Load normalized daily OHLCV data, including pre-start warmup rows."""

        buffered_start_date = start_date - timedelta(days=self.lookback_buffer_days)
        query = text(
            f"""
            SELECT
                p.timestamp AS date,
                p.open AS open,
                p.high AS high,
                p.low AS low,
                p.close AS close,
                p.volume AS volume
            FROM {self.price_table} p
            JOIN {self.instrument_table} i
                ON p.instrument_key = i.instrument_key
            WHERE (i.symbol = :symbol OR i.trading_symbol = :symbol)
                AND p.interval = :price_interval
                AND p.timestamp >= :start_date
                AND p.timestamp <= :end_date
            ORDER BY p.timestamp ASC
            """
        )
        df = pd.read_sql(
            query,
            self.engine,
            params={
                "symbol": symbol,
                "price_interval": self.price_interval,
                "start_date": buffered_start_date,
                "end_date": end_date,
            },
        )
        return normalize_ohlcv_dataframe(df)

    def load_symbols(
        self,
        symbols: Iterable[str],
        start_date: date,
        end_date: date,
    ) -> dict[str, pd.DataFrame]:
        """Load requested symbols, skipping symbols with no returned rows."""

        data_by_symbol: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            data = self.load_symbol(symbol, start_date, end_date)
            if not data.empty:
                data_by_symbol[symbol] = data
        return data_by_symbol

    def load_all_available_symbols(
        self,
        start_date: date,
        end_date: date,
    ) -> dict[str, pd.DataFrame]:
        """Discover symbols in the requested window, then load with warmup."""

        symbols = self._discover_available_symbols(start_date, end_date)
        return self.load_symbols(symbols, start_date, end_date)

    def _discover_available_symbols(
        self,
        start_date: date,
        end_date: date,
    ) -> list[str]:
        """Return distinct equity symbols available in the date range."""

        query = text(
            f"""
            SELECT DISTINCT COALESCE(i.trading_symbol, i.symbol) AS symbol
            FROM {self.price_table} p
            JOIN {self.instrument_table} i
                ON p.instrument_key = i.instrument_key
            WHERE p.interval = :price_interval
                AND p.timestamp >= :start_date
                AND p.timestamp <= :end_date
                AND p.instrument_key LIKE 'NSE_EQ|%'
                AND COALESCE(i.trading_symbol, i.symbol) IS NOT NULL
            ORDER BY symbol ASC
            """
        )
        df = pd.read_sql(
            query,
            self.engine,
            params={
                "price_interval": self.price_interval,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        if "symbol" not in df.columns:
            raise ValueError("missing required columns: symbol")
        return [str(symbol) for symbol in df["symbol"].dropna().tolist()]


def _validate_identifier(identifier: str) -> str:
    """Validate a SQL identifier used for table names."""

    if not identifier.replace("_", "").isalnum():
        raise ValueError(f"invalid SQL identifier: {identifier}")
    return identifier
