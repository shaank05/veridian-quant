"""Small Upstox historical candle client for V2 ingestion."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date
from typing import Any

import requests

from veridian_quant.v2.data.ingestion_config import IngestionConfig


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class HistoricalChunkResult:
    """Result of one historical candle request."""

    instrument_key: str
    interval: str
    start_date: date
    end_date: date
    candles: list[list[Any]]
    ok: bool = True
    error: str | None = None


class UpstoxHistoryClient:
    """Fetch historical candles with retry handling for transient failures."""

    def __init__(
        self,
        config: IngestionConfig,
        session: requests.Session | None = None,
        base_url: str | None = None,
    ) -> None:
        self.config = config
        self.session = session or requests.Session()
        self.base_url = (base_url or self._default_base_url(config.api_version)).rstrip("/")

    def fetch_candles(
        self,
        instrument_key: str,
        interval: str,
        start_date: date,
        end_date: date,
    ) -> HistoricalChunkResult:
        """Fetch candles for one instrument/date chunk."""

        url = (
            f"{self.base_url}/historical-candle/"
            f"{instrument_key}/{interval}/{end_date.isoformat()}/{start_date.isoformat()}"
        )
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.config.access_token}",
        }

        network_started = time.monotonic()
        attempt = 0
        while True:
            try:
                response = self.session.get(url, headers=headers, timeout=30)
            except requests.RequestException as error:
                if (
                    self.config.network_retry == "wait"
                    and _is_network_like_error(error)
                    and not _network_wait_exceeded(
                        network_started,
                        self.config.network_max_wait_minutes,
                    )
                ):
                    logger.warning(
                        "Network error from Upstox; retrying after %ss: %s",
                        self.config.network_wait_seconds,
                        error,
                    )
                    time.sleep(self.config.network_wait_seconds)
                    continue
                if attempt >= self.config.max_retries:
                    return _failed(instrument_key, interval, start_date, end_date, str(error))
                self._sleep_before_retry(attempt, error)
                attempt += 1
                continue

            if response.status_code == 429 or 500 <= response.status_code < 600:
                if attempt >= self.config.max_retries:
                    return _failed(
                        instrument_key,
                        interval,
                        start_date,
                        end_date,
                        f"HTTP {response.status_code}: {response.text[:200]}",
                    )
                self._sleep_before_retry(attempt, f"HTTP {response.status_code}")
                attempt += 1
                continue

            if response.status_code >= 400:
                return _failed(
                    instrument_key,
                    interval,
                    start_date,
                    end_date,
                    f"HTTP {response.status_code}: {response.text[:200]}",
                )

            try:
                payload = response.json()
            except ValueError as error:
                return _failed(instrument_key, interval, start_date, end_date, str(error))

            candles = payload.get("data", {}).get("candles", [])
            return HistoricalChunkResult(
                instrument_key=instrument_key,
                interval=interval,
                start_date=start_date,
                end_date=end_date,
                candles=list(candles or []),
            )

        return _failed(instrument_key, interval, start_date, end_date, "retry exhausted")

    def _sleep_before_retry(self, attempt: int, reason: object) -> None:
        wait_seconds = self.config.backoff_base_seconds * (2**attempt)
        logger.warning("Retrying Upstox request after %.2fs: %s", wait_seconds, reason)
        time.sleep(wait_seconds)

    @staticmethod
    def _default_base_url(api_version: str) -> str:
        version = api_version.strip().lower().removeprefix("v")
        if version.endswith(".0"):
            version = version[:-2]
        return f"https://api.upstox.com/v{version}"


def _failed(
    instrument_key: str,
    interval: str,
    start_date: date,
    end_date: date,
    error: str,
) -> HistoricalChunkResult:
    logger.error(
        "Failed Upstox chunk for %s %s %s..%s: %s",
        instrument_key,
        interval,
        start_date,
        end_date,
        error,
    )
    return HistoricalChunkResult(
        instrument_key=instrument_key,
        interval=interval,
        start_date=start_date,
        end_date=end_date,
        candles=[],
        ok=False,
        error=error,
    )


def _is_network_like_error(error: requests.RequestException) -> bool:
    return isinstance(error, (requests.ConnectionError, requests.Timeout)) or (
        isinstance(error, requests.RequestException)
        and getattr(error, "response", None) is None
    )


def _network_wait_exceeded(started: float, max_wait_minutes: int) -> bool:
    if max_wait_minutes == 0:
        return False
    return (time.monotonic() - started) >= max_wait_minutes * 60
