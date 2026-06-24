"""Upstox company profile and fundamentals client.

This client is intentionally data-layer only. It does not feed strategies,
backtests, exporters, reports, or OHLC ingestion.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import requests

from veridian_quant.v2.data.ingestion_config import IngestionConfig


logger = logging.getLogger(__name__)

SUPPORTED_FUNDAMENTALS_ENDPOINTS = (
    "profile",
    "key_ratios",
    "income_statement",
    "balance_sheet",
    "cash_flow",
    "shareholding",
    "corporate_actions",
    "competitors",
)

DEFAULT_ENDPOINT_PATHS = {
    "profile": "/company/profile/{isin}",
    "key_ratios": "/company/key-ratios/{isin}",
    "income_statement": "/company/income-statement/{isin}",
    "balance_sheet": "/company/balance-sheet/{isin}",
    "cash_flow": "/company/cash-flow/{isin}",
    "shareholding": "/company/shareholding/{isin}",
    "corporate_actions": "/company/corporate-actions/{isin}",
    "competitors": "/company/competitors/{isin}",
}


@dataclass(frozen=True, slots=True)
class FundamentalsEndpointResult:
    """Result of one Upstox company/fundamentals endpoint request."""

    isin: str
    endpoint: str
    payload: Any | None
    ok: bool = True
    status_code: int | None = None
    error: str | None = None
    no_data: bool = False


class UpstoxFundamentalsClient:
    """Fetch company profile/fundamentals payloads with retry handling."""

    def __init__(
        self,
        config: IngestionConfig,
        session: requests.Session | None = None,
        base_url: str | None = None,
        endpoint_paths: dict[str, str] | None = None,
    ) -> None:
        self.config = config
        self.session = session or requests.Session()
        self.base_url = (base_url or self._default_base_url(config.api_version)).rstrip("/")
        self.endpoint_paths = {**DEFAULT_ENDPOINT_PATHS, **(endpoint_paths or {})}

    def fetch_endpoint(self, isin: str | None, endpoint: str) -> FundamentalsEndpointResult:
        """Fetch one supported fundamentals endpoint for one ISIN."""

        endpoint = _normalize_endpoint(endpoint)
        isin = (isin or "").strip().upper()
        if not isin:
            return FundamentalsEndpointResult(
                isin="",
                endpoint=endpoint,
                payload=None,
                ok=False,
                error="missing ISIN",
                no_data=True,
            )

        url = self.base_url + self.endpoint_paths[endpoint].format(isin=isin)
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.config.access_token or ''}",
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
                        "Network error from Upstox fundamentals; retrying after %ss: %s",
                        self.config.network_wait_seconds,
                        error,
                    )
                    time.sleep(self.config.network_wait_seconds)
                    continue
                if attempt >= self.config.max_retries:
                    return _failed(isin, endpoint, str(error))
                self._sleep_before_retry(attempt, error)
                attempt += 1
                continue

            if response.status_code == 404:
                return FundamentalsEndpointResult(
                    isin=isin,
                    endpoint=endpoint,
                    payload=None,
                    ok=True,
                    status_code=response.status_code,
                    no_data=True,
                )

            if response.status_code == 429 or 500 <= response.status_code < 600:
                if attempt >= self.config.max_retries:
                    return _failed(
                        isin,
                        endpoint,
                        f"HTTP {response.status_code}: {response.text[:200]}",
                        response.status_code,
                    )
                self._sleep_before_retry(attempt, f"HTTP {response.status_code}")
                attempt += 1
                continue

            if response.status_code >= 400:
                return _failed(
                    isin,
                    endpoint,
                    f"HTTP {response.status_code}: {response.text[:200]}",
                    response.status_code,
                )

            try:
                payload = response.json()
            except ValueError as error:
                return _failed(isin, endpoint, f"malformed JSON: {error}", response.status_code)

            return FundamentalsEndpointResult(
                isin=isin,
                endpoint=endpoint,
                payload=_extract_data(payload),
                status_code=response.status_code,
            )

    def fetch_profile(self, isin: str | None) -> FundamentalsEndpointResult:
        return self.fetch_endpoint(isin, "profile")

    def fetch_key_ratios(self, isin: str | None) -> FundamentalsEndpointResult:
        return self.fetch_endpoint(isin, "key_ratios")

    def fetch_income_statement(self, isin: str | None) -> FundamentalsEndpointResult:
        return self.fetch_endpoint(isin, "income_statement")

    def fetch_balance_sheet(self, isin: str | None) -> FundamentalsEndpointResult:
        return self.fetch_endpoint(isin, "balance_sheet")

    def fetch_cash_flow(self, isin: str | None) -> FundamentalsEndpointResult:
        return self.fetch_endpoint(isin, "cash_flow")

    def fetch_shareholding(self, isin: str | None) -> FundamentalsEndpointResult:
        return self.fetch_endpoint(isin, "shareholding")

    def fetch_corporate_actions(self, isin: str | None) -> FundamentalsEndpointResult:
        return self.fetch_endpoint(isin, "corporate_actions")

    def fetch_competitors(self, isin: str | None) -> FundamentalsEndpointResult:
        return self.fetch_endpoint(isin, "competitors")

    def _sleep_before_retry(self, attempt: int, reason: object) -> None:
        wait_seconds = self.config.backoff_base_seconds * (2**attempt)
        logger.warning("Retrying Upstox fundamentals after %.2fs: %s", wait_seconds, reason)
        time.sleep(wait_seconds)

    @staticmethod
    def _default_base_url(api_version: str) -> str:
        version = api_version.strip().lower().removeprefix("v")
        if version.endswith(".0"):
            version = version[:-2]
        return f"https://api.upstox.com/v{version}"


def _normalize_endpoint(endpoint: str) -> str:
    value = endpoint.strip().lower().replace("-", "_")
    if value not in SUPPORTED_FUNDAMENTALS_ENDPOINTS:
        valid = ", ".join(SUPPORTED_FUNDAMENTALS_ENDPOINTS)
        raise ValueError(f"endpoint must be one of: {valid}")
    return value


def _extract_data(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def _failed(
    isin: str,
    endpoint: str,
    error: str,
    status_code: int | None = None,
) -> FundamentalsEndpointResult:
    logger.error("Failed Upstox fundamentals endpoint %s for %s: %s", endpoint, isin, error)
    return FundamentalsEndpointResult(
        isin=isin,
        endpoint=endpoint,
        payload=None,
        ok=False,
        status_code=status_code,
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
