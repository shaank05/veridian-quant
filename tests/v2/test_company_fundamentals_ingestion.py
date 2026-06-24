"""Tests for company fundamentals ingestion and storage."""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine, text

from veridian_quant.v2.data.company_fundamentals_ingestion import (
    ACTIONS_TABLE,
    COMPETITORS_TABLE,
    KEY_RATIOS_TABLE,
    PROFILE_TABLE,
    SHAREHOLDING_TABLE,
    STATEMENTS_TABLE,
    CompanyFundamentalsIngestionRunner,
    CompanyFundamentalsStorage,
    CompanyUniverseEntry,
    count_classification_csv_updates,
    parse_endpoint_payload,
    update_classification_csv_from_profiles,
)
from veridian_quant.v2.data.ingestion_config import IngestionConfig
from veridian_quant.v2.data.upstox_fundamentals_client import (
    FundamentalsEndpointResult,
    UpstoxFundamentalsClient,
)


def test_profile_response_is_stored_and_can_update_classification_csv(tmp_path) -> None:
    engine = create_engine("sqlite:///:memory:")
    symbols_file = tmp_path / "symbols.csv"
    classification_file = tmp_path / "classifications.csv"
    symbols_file.write_text(
        "symbol,instrument_key,name\nAAA,NSE_EQ|INE000A01010,Alpha Ltd\n",
        encoding="utf-8",
    )
    classification_file.write_text(
        "symbol,company_name,sector,industry,basic_industry,market_cap_bucket,"
        "classification_mode,source\n"
        "AAA,Alpha Ltd,UNKNOWN,,,unknown,static_current,MANUAL\n",
        encoding="utf-8",
    )
    client = FakeClient(
        {
            ("INE000A01010", "profile"): _ok(
                "INE000A01010",
                "profile",
                {
                    "company_name": "Alpha Limited",
                    "sector": "Financial Services",
                    "industry": "Banks",
                    "basic_industry": "Private Sector Bank",
                    "snapshot_date": "2026-06-24",
                },
            )
        }
    )

    summary = CompanyFundamentalsIngestionRunner(engine, client).run(
        symbols_file=symbols_file,
        endpoints=["profile"],
        dry_run=False,
        update_classification_csv=True,
        classification_file=classification_file,
        source="UPSTOX_FUNDAMENTALS",
    )

    assert summary.rows_upserted_by_table[PROFILE_TABLE] == 1
    assert summary.classification_csv_rows_updated == 1
    with engine.connect() as conn:
        row = conn.execute(text(f"SELECT * FROM {PROFILE_TABLE}")).mappings().one()
    assert row["sector"] == "Financial Services"
    assert row["classification_mode"] == "static_current"
    assert not row["is_point_in_time_safe"]
    assert "Alpha Limited" in classification_file.read_text(encoding="utf-8")


def test_ratios_statements_shareholding_actions_and_competitors_are_stored() -> None:
    engine = create_engine("sqlite:///:memory:")
    parsed = _all_endpoint_payloads()
    storage = CompanyFundamentalsStorage(engine)

    counts_first = storage.upsert(parsed)
    counts_second = storage.upsert(parsed)

    assert counts_first[KEY_RATIOS_TABLE] == 1
    assert counts_second[KEY_RATIOS_TABLE] == 1
    with engine.connect() as conn:
        ratio = conn.execute(text(f"SELECT * FROM {KEY_RATIOS_TABLE}")).mappings().one()
        statement = conn.execute(text(f"SELECT * FROM {STATEMENTS_TABLE}")).mappings().one()
        shareholding = conn.execute(text(f"SELECT * FROM {SHAREHOLDING_TABLE}")).mappings().one()
        action_count = conn.execute(text(f"SELECT COUNT(*) FROM {ACTIONS_TABLE}")).scalar_one()
        competitor = conn.execute(text(f"SELECT * FROM {COMPETITORS_TABLE}")).mappings().one()
    assert ratio["ratio_name"] == "pe"
    assert ratio["ratio_value"] == "21.5"
    assert not ratio["is_point_in_time_safe"]
    assert statement["period_end_date"] == "Mar 2026"
    assert statement["is_point_in_time_safe"]
    assert shareholding["holder_category"] == "Promoter"
    assert action_count == 1
    assert competitor["competitor_name"] == "Beta Ltd"
    assert competitor["competitor_key"] == "NSE_EQ|INE000B01010"
    assert competitor["competitor_isin"] == "INE000B01010"


def test_competitors_with_unknown_names_use_instrument_key_for_idempotent_upsert() -> None:
    engine = create_engine("sqlite:///:memory:")
    entry = CompanyUniverseEntry(symbol="AAA", isin="INE000A01010", instrument_key="NSE_EQ|INE000A01010")
    parsed = parse_endpoint_payload(
        entry,
        "competitors",
        [
            {"instrument_key": "NSE_EQ|INE000B01010"},
            {"instrument_key": "NSE_EQ|INE000C01010"},
            {"instrument_key": "NSE_EQ|INE000B01010"},
        ],
        "UPSTOX_FUNDAMENTALS",
        datetime(2026, 6, 24),
    )
    storage = CompanyFundamentalsStorage(engine)

    first_counts = storage.upsert(parsed)
    second_counts = storage.upsert(parsed)

    assert first_counts[COMPETITORS_TABLE] == 2
    assert second_counts[COMPETITORS_TABLE] == 2
    with engine.connect() as conn:
        rows = conn.execute(
            text(f"SELECT competitor_key, competitor_name, competitor_isin FROM {COMPETITORS_TABLE}")
        ).mappings().all()
    assert {row["competitor_key"] for row in rows} == {
        "NSE_EQ|INE000B01010",
        "NSE_EQ|INE000C01010",
    }
    assert {row["competitor_name"] for row in rows} == {"UNKNOWN"}
    assert {row["competitor_isin"] for row in rows} == {"INE000B01010", "INE000C01010"}


def test_runner_handles_missing_isin_no_data_and_endpoint_failure(tmp_path) -> None:
    engine = create_engine("sqlite:///:memory:")
    symbols_file = tmp_path / "symbols.csv"
    symbols_file.write_text(
        "symbol,instrument_key\n"
        "AAA,NSE_EQ|INE000A01010\n"
        "BBB,\n"
        "CCC,NSE_EQ|INE000C01010\n",
        encoding="utf-8",
    )
    client = FakeClient(
        {
            ("INE000A01010", "profile"): FundamentalsEndpointResult(
                "INE000A01010",
                "profile",
                None,
                ok=True,
                status_code=404,
                no_data=True,
            ),
            ("INE000C01010", "profile"): FundamentalsEndpointResult(
                "INE000C01010",
                "profile",
                None,
                ok=False,
                status_code=500,
                error="HTTP 500",
            ),
        }
    )

    summary = CompanyFundamentalsIngestionRunner(engine, client).run(
        symbols_file=symbols_file,
        endpoints=["profile"],
        dry_run=True,
    )

    assert summary.symbols_requested == 3
    assert summary.endpoint_no_data == 1
    assert summary.endpoint_failures == 2
    assert summary.failures_by_symbol["BBB"] == ["missing ISIN"]
    assert "profile: HTTP 500" in summary.failures_by_symbol["CCC"]


def test_dry_run_does_not_write_db_or_classification_csv(tmp_path) -> None:
    engine = create_engine("sqlite:///:memory:")
    symbols_file = tmp_path / "symbols.csv"
    classification_file = tmp_path / "classifications.csv"
    symbols_file.write_text("symbol,instrument_key\nAAA,NSE_EQ|INE000A01010\n", encoding="utf-8")
    original_csv = (
        "symbol,company_name,sector,industry,basic_industry,market_cap_bucket,"
        "classification_mode,source\n"
        "AAA,Alpha,UNKNOWN,,,unknown,static_current,MANUAL\n"
    )
    classification_file.write_text(original_csv, encoding="utf-8")
    client = FakeClient(
        {
            ("INE000A01010", "profile"): _ok(
                "INE000A01010",
                "profile",
                {"sector": "Energy", "industry": "Oil", "snapshot_date": "2026-06-24"},
            )
        }
    )

    summary = CompanyFundamentalsIngestionRunner(engine, client).run(
        symbols_file=symbols_file,
        endpoints=["profile"],
        dry_run=True,
        update_classification_csv=True,
        classification_file=classification_file,
    )

    assert summary.rows_parsed_by_table[PROFILE_TABLE] == 1
    assert summary.rows_upserted_by_table[PROFILE_TABLE] == 0
    assert summary.classification_csv_rows_updated == 1
    assert classification_file.read_text(encoding="utf-8") == original_csv
    with engine.connect() as conn:
        tables = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
            {"name": PROFILE_TABLE},
        ).all()
    assert tables == []


def test_classification_csv_update_preserves_unknowns_when_profile_has_no_classification(tmp_path) -> None:
    classification_file = tmp_path / "classifications.csv"
    classification_file.write_text(
        "symbol,company_name,sector,industry,basic_industry,market_cap_bucket,"
        "classification_mode,source\n"
        "AAA,Alpha,UNKNOWN,,,unknown,static_current,MANUAL\n",
        encoding="utf-8",
    )

    rows_updated, fields_updated = count_classification_csv_updates(
        classification_file,
        [{"symbol": "AAA", "sector": "UNKNOWN", "industry": None}],
    )

    assert rows_updated == 1
    assert fields_updated == 1
    written_rows, written_fields = update_classification_csv_from_profiles(
        classification_file,
        [{"symbol": "AAA", "sector": "UNKNOWN", "industry": None}],
        source="UPSTOX_FUNDAMENTALS",
    )
    assert (written_rows, written_fields) == (1, 1)
    assert "UNKNOWN" in classification_file.read_text(encoding="utf-8")


def test_classification_csv_update_adds_missing_output_fields(tmp_path) -> None:
    classification_file = tmp_path / "classifications.csv"
    classification_file.write_text(
        "symbol,company_name,sector\n"
        "AAA,Alpha,UNKNOWN\n",
        encoding="utf-8",
    )

    rows_updated, fields_updated = update_classification_csv_from_profiles(
        classification_file,
        [{"symbol": "AAA", "company_name": "Alpha Ltd", "sector": "Energy"}],
        source="UPSTOX_FUNDAMENTALS",
    )

    assert (rows_updated, fields_updated) == (1, 4)
    written = classification_file.read_text(encoding="utf-8")
    assert "classification_mode" in written.splitlines()[0]
    assert "UPSTOX_FUNDAMENTALS" in written


def test_classification_csv_update_refuses_header_only_file(tmp_path) -> None:
    classification_file = tmp_path / "classifications.csv"
    classification_file.write_text("symbol,company_name,sector\n", encoding="utf-8")

    with pytest.raises(ValueError, match="no data rows"):
        update_classification_csv_from_profiles(
            classification_file,
            [{"symbol": "AAA", "sector": "Energy"}],
            source="UPSTOX_FUNDAMENTALS",
        )

    assert classification_file.read_text(encoding="utf-8") == "symbol,company_name,sector\n"


def test_client_handles_404_empty_payload_malformed_json_and_retries_transient_status(monkeypatch) -> None:
    monkeypatch.setattr("veridian_quant.v2.data.upstox_fundamentals_client.time.sleep", lambda _: None)
    session = FakeSession(
        [
            FakeResponse(500, {"error": "temporary"}),
            FakeResponse(200, {"data": {"sector": "IT"}}),
            FakeResponse(404, {"error": "missing"}),
            FakeResponse(200, {"data": []}),
            FakeResponse(200, ValueError("bad json")),
        ]
    )
    client = UpstoxFundamentalsClient(_config(), session=session, base_url="https://example.test")

    retried = client.fetch_endpoint("INE000A01010", "profile")
    missing = client.fetch_endpoint("INE000A01010", "profile")
    empty = client.fetch_endpoint("INE000A01010", "profile")
    malformed = client.fetch_endpoint("INE000A01010", "profile")

    assert retried.ok is True
    assert retried.payload == {"sector": "IT"}
    assert session.urls[0] == "https://example.test/fundamentals/INE000A01010/profile"
    assert missing.ok is False
    assert missing.status_code == 404
    assert "HTTP 404" in missing.error
    assert empty.no_data is True
    assert malformed.ok is False
    assert "malformed JSON" in malformed.error


def _all_endpoint_payloads():
    entry = CompanyUniverseEntry(symbol="AAA", isin="INE000A01010")
    fetched_at = datetime(2026, 6, 24)
    parsed = parse_endpoint_payload(
        entry,
        "key_ratios",
        [{"name": "pe", "company_value": 21.5, "sector_value": 20.1}],
        "UPSTOX_FUNDAMENTALS",
        fetched_at,
    )
    parsed.extend(
        parse_endpoint_payload(
            entry,
            "income_statement",
            {
                "type": "annual",
                "time_period": "yearly",
                "income_statement": [
                    {
                        "category": "Revenue",
                        "history": [{"period": "Mar 2026", "value": 1000, "change": 1.2}],
                    }
                ]
            },
            "UPSTOX_FUNDAMENTALS",
            fetched_at,
        )
    )
    parsed.extend(
        parse_endpoint_payload(
            entry,
            "shareholding",
            {"shareholding": [{"holder_category": "Promoter", "holding_percent": 50}]},
            "UPSTOX_FUNDAMENTALS",
            fetched_at,
        )
    )
    parsed.extend(
        parse_endpoint_payload(
            entry,
            "corporate_actions",
            [{"name": "DIVIDEND", "expiry_date": "2026-05-01", "amount": "10"}],
            "UPSTOX_FUNDAMENTALS",
            fetched_at,
        )
    )
    parsed.extend(
        parse_endpoint_payload(
            entry,
            "competitors",
            [{"company_profile": {"company_name": "Beta Ltd"}, "instrument_key": "NSE_EQ|INE000B01010"}],
            "UPSTOX_FUNDAMENTALS",
            fetched_at,
        )
    )
    return parsed


def _ok(isin: str, endpoint: str, payload):
    return FundamentalsEndpointResult(isin, endpoint, payload, ok=True)


def _config() -> IngestionConfig:
    return IngestionConfig(
        access_token="token",
        api_version="2.0",
        max_days_1d=365,
        max_days_1m=30,
        throttle_seconds=0.0,
        max_retries=1,
        backoff_base_seconds=0.0,
        log_dir="logs",
        run_dir="runs",
        network_retry="fail-fast",
        network_wait_seconds=1,
        network_max_wait_minutes=0,
        chunk_min_coverage_pct=70.0,
    )


class FakeClient:
    def __init__(self, responses):
        self.responses = responses

    def fetch_endpoint(self, isin, endpoint):
        return self.responses[(isin, endpoint)]


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.payload = payload
        self.text = str(payload)

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.urls = []

    def get(self, url, headers, timeout):
        self.urls.append(url)
        return self.responses.pop(0)
