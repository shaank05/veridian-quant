"""Configuration for V2 price ingestion."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_API_VERSION = "2.0"
DEFAULT_MAX_DAYS_1D = 365
DEFAULT_MAX_DAYS_1M = 30
DEFAULT_THROTTLE_SECONDS = 0.5
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE_SECONDS = 5.0
DEFAULT_LOG_DIR = "logs/v2/ingestion"


@dataclass(frozen=True, slots=True)
class IngestionConfig:
    """Typed environment-backed settings for V2 ingestion."""

    access_token: str | None
    api_version: str
    max_days_1d: int
    max_days_1m: int
    throttle_seconds: float
    max_retries: int
    backoff_base_seconds: float
    log_dir: Path

    @classmethod
    def from_env(cls) -> "IngestionConfig":
        """Build config from environment variables with safe defaults."""

        return cls(
            access_token=_optional_env("UPSTOX_ACCESS_TOKEN"),
            api_version=_env_str("UPSTOX_API_VERSION", DEFAULT_API_VERSION),
            max_days_1d=_env_int("V2_INGESTION_MAX_DAYS_1D", DEFAULT_MAX_DAYS_1D),
            max_days_1m=_env_int("V2_INGESTION_MAX_DAYS_1M", DEFAULT_MAX_DAYS_1M),
            throttle_seconds=_env_float(
                "V2_INGESTION_THROTTLE_SECONDS",
                DEFAULT_THROTTLE_SECONDS,
            ),
            max_retries=_env_int("V2_INGESTION_MAX_RETRIES", DEFAULT_MAX_RETRIES),
            backoff_base_seconds=_env_float(
                "V2_INGESTION_BACKOFF_BASE_SECONDS",
                DEFAULT_BACKOFF_BASE_SECONDS,
            ),
            log_dir=Path(_env_str("V2_INGESTION_LOG_DIR", DEFAULT_LOG_DIR)),
        )

    def require_access_token(self, mode: str) -> None:
        """Reject real ingestion runs without an Upstox access token."""

        if mode != "dry-run" and not self.access_token:
            raise ValueError(
                "UPSTOX_ACCESS_TOKEN is required for backfill and incremental modes"
            )

    def safe_summary(self) -> dict[str, object]:
        """Return loggable settings without secrets."""

        return {
            "api_version": self.api_version,
            "max_days_1d": self.max_days_1d,
            "max_days_1m": self.max_days_1m,
            "throttle_seconds": self.throttle_seconds,
            "max_retries": self.max_retries,
            "backoff_base_seconds": self.backoff_base_seconds,
            "log_dir": str(self.log_dir),
            "has_access_token": bool(self.access_token),
        }


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or not value.strip() or value.strip().lower() == "none":
        return None
    return value.strip()


def _env_str(name: str, default: str) -> str:
    value = _optional_env(name)
    return value if value is not None else default


def _env_int(name: str, default: int) -> int:
    value = _optional_env(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error
    if parsed <= 0:
        raise ValueError(f"{name} must be positive")
    return parsed


def _env_float(name: str, default: float) -> float:
    value = _optional_env(name)
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError as error:
        raise ValueError(f"{name} must be a number") from error
    if parsed < 0:
        raise ValueError(f"{name} must be non-negative")
    return parsed
