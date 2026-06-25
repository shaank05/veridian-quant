# Company Fundamentals Ingestion and Audit Status

## Purpose

This document records the Phase 33D.3 company fundamentals ingestion result and
the Phase 33D.4 audit status for the Research200 universe.

This is research data documentation only. It does not approve any strategy
upgrade, ranking rule, filter, signal, backtest behavior, exporter change, or
production decision.

---

## Phase 33D.3 Ingestion Summary

Upstox company profile and fundamentals ingestion was run for the Research200
universe.

Run summary:

- symbols_requested: 200
- isins_found: 200
- endpoint_successes: 1353
- endpoint_failures: 0
- endpoint_no_data: 247
- dry_run: false
- company_profiles: 200
- company_key_ratios: 1218
- company_financial_statements: 2139
- company_shareholding: 0
- company_corporate_actions: 250
- company_competitors: 1935
- classification_csv_rows_updated: 195
- classification_csv_fields_updated: 389

Created or populated research layers:

- `company_profiles`
- `company_key_ratios`
- `company_financial_statements`
- `company_shareholding`
- `company_corporate_actions`
- `company_competitors`

The static Research200 classification CSV was also refreshed:

- `config/universes/research/nse_eq_research_200_static_classification.csv`

---

## Phase 33D.4 Audit Summary

Audit verdict: **APPROVED** for research-data readiness.

Coverage:

- Profiles: 200/200 symbols.
- Key ratios: 199/200 symbols; missing `HDFCSENSEX`.
- Financial statements: 184/200 symbols.
- Shareholding: 0/200 symbols.
- Corporate actions: 154/200 symbols.
- Competitors: 200/200 symbols.

Classification CSV:

- Rows: 200.
- Sector: 199 known / 1 unknown.
- Remaining unknown sector symbol: `HDFCSENSEX`.
- Industry: 0 known / 200 unknown.
- Basic industry: 0 known / 200 unknown.
- Market-cap bucket: 0 known / 200 unknown.
- Index membership: 0 known / 200 unknown.
- Duplicate symbols: 0.
- Duplicate ISINs: 0.
- Profile-versus-CSV sector mismatches: 0.

Duplicate logical keys:

- Profiles: 0.
- Key ratios: 0.
- Financial statements: 0.
- Shareholding: 0.
- Corporate actions: 0.
- Competitors: 0.

Metadata and lookahead safety:

- Current snapshot layers preserve `source`, `fetched_at`, `snapshot_date`, and
  `is_point_in_time_safe = false` where expected.
- Financial statements preserve `period_end_date` and are marked
  point-in-time safe.
- Corporate actions preserve `ex_date` and are marked point-in-time safe.
- Shareholding table exists and has zero rows.

---

## Known Gaps

Known gaps preserved after audit:

- Shareholding data is unavailable from the current Upstox route. The endpoint
  returned HTTP 404 Resource not Found and is parked for now.
- Competitor names are all `UNKNOWN`, but `competitor_key` and
  `competitor_isin` are populated and uniqueness is safe.
- Financial statements are stored as period-level raw payload rows, not
  normalized `line_item` / `value` rows.
- `industry`, `basic_industry`, `market_cap_bucket`, and `index_membership`
  remain unknown in the static classification CSV.
- Current key ratios and profile classifications are current snapshots, not
  historical point-in-time facts for 2018 historical signals.

---

## Allowed Use

Allowed research uses:

- Current/static context and diagnostics.
- Research200 classification completeness checks.
- Benchmark, sector, and market-cap context preparation.
- Future fundamentals research layer design.
- Future enrichment and normalization work.

Allowed audited layers:

- Profiles and classification fields may support current/static context labels
  when reports clearly label them as current/static.
- Financial statements and corporate actions may support future historical
  research only through fields that are available by event or period date and
  handled with explicit signal-time rules.

---

## Prohibited Use

Do not use this data to:

- Change S1/S2/S3/S4/S5 strategy behavior.
- Generate historical 2018-2026 signals from current snapshot ratios.
- Treat current sector, market-cap, index-membership, or profile metadata as
  point-in-time historical truth.
- Promote any strategy, filter, ranking rule, or production decision.
- Mix current snapshot fundamentals into historical backtests without explicit
  leakage controls.

---

## Next Recommended Use in Phase 33E

Phase 33E should continue with benchmark/context feature utilities, using the
fundamentals and classification layers only as audited research context.

Recommended Phase 33E handling:

- Keep classification labels explicit: current/static versus point-in-time.
- Use the company fundamentals tables as reference data, not strategy logic.
- Preserve leakage-safe feature timing rules.
- Avoid current snapshot ratios in historical signal generation.
- Carry normalization gaps as future data-model work.

---

## Related Documents

- `docs/00_foundation/v2_research_roadmap.md`
- `docs/04_validation/benchmark_sector_cap_context.md`
- `docs/03_research/feature_ideas.md`
- `docs/05_decisions/decision_log.md`
- `docs/02_audits/strategy_audit_master.md`
