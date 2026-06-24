"""CLI for static-current instrument classification ingestion."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Iterable

from veridian_quant.data.db_client import DatabaseClient
from veridian_quant.v2.data.instrument_classification_ingestion import (
    InstrumentClassificationIngestionRunner,
)


DEFAULT_SYMBOLS_FILE = Path("config/universes/research/nse_eq_research_200_2018_2026.csv")


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv)
    engine = DatabaseClient().get_engine()
    runner = InstrumentClassificationIngestionRunner(engine)
    summary = runner.run(
        classification_file=args.classification_file,
        symbols_file=args.symbols_file,
        classification_mode=args.classification_mode,
        source=args.source,
        effective_from=args.effective_from,
        dry_run=args.dry_run,
        audit_only=args.audit_only,
    )
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    return 0


def _parse_args(argv: Iterable[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import static_current Research200 classification metadata"
    )
    parser.add_argument("--classification-file", type=Path, required=True)
    parser.add_argument("--symbols-file", type=Path, default=DEFAULT_SYMBOLS_FILE)
    parser.add_argument(
        "--classification-mode",
        choices=("static_current",),
        default="static_current",
        help="Only static_current is supported in Phase 33D",
    )
    parser.add_argument("--source", required=True)
    parser.add_argument("--effective-from", type=_parse_date, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--audit-only", action="store_true")
    return parser.parse_args(list(argv) if argv is not None else None)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


if __name__ == "__main__":
    raise SystemExit(main())
