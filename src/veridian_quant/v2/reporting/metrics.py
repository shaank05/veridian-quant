"""Reporting metric models for Veridian Quant v2.

Metrics in this module are named containers for already-computed research
outputs. Calculation, attribution, and diagnostics are owned by concrete
evaluation components outside this skeleton.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class MetricValue:
    """Single named metric value with optional descriptive metadata."""

    name: str
    value: float | int | str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class MetricReport:
    """Collection of metric values for a research run."""

    run_id: str
    metrics: Mapping[str, MetricValue] = field(
        default_factory=lambda: MappingProxyType({})
    )
    metadata: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({})
    )
