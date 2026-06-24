"""CLI for Upstox company profile and fundamentals ingestion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from veridian_quant.data.db_client import DatabaseClient
from veridian_quant.v2.data.company_fundamentals_ingestion import (
    SOURCE_DEFAULT,
    CompanyFundamentalsIngestionRunner,
    parse_endpoints,
)
from veridian_quant.v2.data.ingestion_config import IngestionConfig
from veridian_quant.v2.data.upstox_fundamentals_client import UpstoxFundamentalsClient


DEFAULT_SYMBOLS_FILE = Path("config/universes/research/nse_eq_research_200_2018_2026.csv")


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv)
    config = IngestionConfig.from_env()
    if not args.dry_run:
        config.require_access_token("live")
    engine = DatabaseClient().get_engine()
    client = UpstoxFundamentalsClient(config)
    runner = CompanyFundamentalsIngestionRunner(engine, client)
    summary = runner.run(
        symbols_file=args.symbols_file,
        endpoints=args.endpoints,
        source=args.source,
        dry_run=args.dry_run,
        limit=args.limit,
        symbols=args.symbols,
        isins=args.isins,
        update_classification_csv=args.update_classification_csv,
        classification_file=args.classification_file,
    )
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    return 0


def _parse_args(argv: Iterable[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch/store Research200 Upstox company fundamentals metadata"
    )
    parser.add_argument("--symbols-file", type=Path, default=DEFAULT_SYMBOLS_FILE)
    parser.add_argument("--symbols", type=_csv_values, default=[])
    parser.add_argument("--isins", type=_csv_values, default=[])
    parser.add_argument(
        "--endpoints",
        type=parse_endpoints,
        default=["profile"],
        help="ALL or comma list: profile,key_ratios,income_statement,balance_sheet,"
        "cash_flow,shareholding,corporate_actions,competitors",
    )
    parser.add_argument("--classification-mode", choices=("static_current",), default="static_current")
    parser.add_argument("--source", default=SOURCE_DEFAULT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--update-classification-csv", action="store_true")
    parser.add_argument("--classification-file", type=Path)
    return parser.parse_args(list(argv) if argv is not None else None)


def _csv_values(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
