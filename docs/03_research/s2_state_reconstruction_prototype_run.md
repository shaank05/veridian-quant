# Phase 36H - S2 State Reconstruction Prototype Run

## 1. Status

Run status: `BLOCKED_PRE_FLIGHT`.

Phase 36H attempted to run the Phase 36G read-only S2 daily state
reconstruction prototype against the retained S2 benchmark artifacts.

The retained S2 report folder exists:

`reports/v2/s2_markov_2020_2026_research200_exclude_ret_down_full_diagnostics/`

Required retained report inputs exist:

- `trade_log.csv`.
- `trade_pnl_log.csv`.
- `trade_signal_context.csv`.

The Phase 36G source module and CLI exist:

- `src/veridian_quant/v2/analysis/s2_state_reconstruction.py`.
- `src/veridian_quant/v2/run_s2_state_reconstruction_prototype.py`.

The prototype run is blocked because the CLI requires:

`--ohlc-csv-dir`

The argument must point to a directory containing one normalized OHLC CSV per
traded symbol. No such per-symbol OHLC CSV directory was found in the
workspace. Existing `reports/v2/data_quality/...` folders contain price-quality
summary outputs, not daily OHLC bar files.

No strategy backtest was run. No strategy logic was changed. No generated
prototype output folder was created.

## 2. Preflight Numbers

Retained-trade loader preflight:

- Trades loaded: 577.
- Unique `trade_id` values: 577.
- Unique symbols: 146.
- Missing `trade_id`: 0.
- Missing symbol: 0.
- Missing entry date: 0.
- Missing exit date: 0.
- Missing stored entry state label: 0.

This confirms that retained S2 trades can be loaded and joined by `trade_id`
before OHLC-dependent reconstruction begins.

## 3. Reconstruction Coverage

Not computed because OHLC input was unavailable.

- Lifecycle rows: not generated.
- Duplicate trade/date rows: not generated.
- Rows with state joined: not generated.
- Rows missing state: not generated.
- State join coverage pct: not generated.
- Trades with complete state path: not generated.
- Trades with missing state path: not generated.

## 4. Entry-State Validation

Not computed because reconstructed daily state rows were not available.

- Trades checked: not generated.
- Matches: not generated.
- Mismatches: not generated.
- Missing stored state: retained-loader preflight found 0.
- Missing reconstructed state: not generated.
- Match rate pct: not generated.
- Alignment used: not generated.

## 5. Same-Day Safety / Next-Open Feasibility

Not computed because lifecycle/state rows were not generated.

- Same-day exit blocked rows: not generated.
- First deterioration candidates by flag: not generated.
- Next-open feasible counts by flag: not generated.
- Next-open infeasible counts by reason: not generated.

## 6. Blocker Classification

Blocker type: `OHLC_INPUT_SOURCE`.

The issue is not retained report schema and not S2 state-builder integration.
The retained trade artifacts are present and loadable. The current CLI design
requires a caller-supplied per-symbol OHLC CSV directory, and Phase 36H did not
have one available.

Recommended next phase:

`FIX_OHLC_INPUT_AND_RERUN_36H`

The next step should either provide a normalized per-symbol OHLC CSV directory
for the existing CLI or revise the prototype input design to use an approved
read-only OHLC source. It should still avoid strategy backtests, S2 logic
changes, dynamic exit rules, filters, threshold optimization, and full Lane A/B
audit implementation.

## 7. Scope Confirmation

- No S2 strategy backtest was run.
- No S2 strategy logic was changed.
- No dynamic exit rule was implemented.
- No `exit if RET_DOWN` rule was created.
- No entry/state/risk filter was implemented.
- No threshold optimization was performed.
- No full Lane A/Lane B audit helper was implemented.
- No production behavior changed.

## 8. Decision

`FIX_OHLC_INPUT_AND_RERUN_36H`

---

## 9. Phase 36H.1 OHLC Input Fix

Phase 36H.1 updates the prototype to support the existing Veridian OHLC loading
path instead of requiring only pre-exported per-symbol CSVs.

Implementation:

- Existing `--ohlc-csv-dir` support is preserved.
- The CLI now supports `--ohlc-source db`.
- The DB source uses `DatabaseClient().get_engine()` and
  `SQLAlchemyDailyOHLCVLoader`, matching existing v2 runner/audit patterns.
- Retained symbols are inferred from loaded trades.
- The OHLC load window is inferred from retained signal/entry dates through
  exit dates, with a pre-start buffer for state construction.
- No strategy runner or backtest path is invoked.

Focused tests:

- `uv run pytest tests/v2/test_s2_state_reconstruction.py -v`
- Result: 17 passed.

## 10. Phase 36H.1 Rerun Status

Run status: `BLOCKED_DB_CONNECTION`.

Attempted command:

`uv run python -m veridian_quant.v2.run_s2_state_reconstruction_prototype --ohlc-source db --output-dir reports/v2/s2_state_reconstruction_prototype_20260706`

The first attempt failed before database access because Windows console output
could not encode Unicode status symbols printed by `DatabaseClient`. The retry
used `PYTHONIOENCODING=utf-8`.

The DB-backed retry initialized the SQLAlchemy engine, then timed out while
connecting to the configured database host:

- Host: `34.14.156.222`.
- Port: `5432`.
- Error class: `psycopg2.OperationalError`.
- Error: connection timed out.

The command was retried with elevated network permission and failed with the
same timeout. Therefore the remaining blocker is database reachability, not the
prototype CLI input design.

No generated prototype output folder was created.

## 11. Phase 36H.1 Coverage / Validation

Not computed because DB OHLC loading could not complete.

Retained-trade preflight from Phase 36H remains valid:

- Trades loaded: 577.
- Unique `trade_id` values: 577.
- Unique symbols: 146.
- Missing `trade_id`: 0.
- Missing symbol: 0.
- Missing entry date: 0.
- Missing exit date: 0.
- Missing stored entry state label: 0.

Lifecycle expansion, reconstructed state joins, entry-state validation,
same-day safety counts, first deterioration candidates, and next-open
feasibility remain not generated.

## 12. Phase 36H.1 Decision

`REVISE_36H1_OHLC_INPUT_FIX`

The OHLC input design now supports the existing DB loader, but the controlled
prototype run cannot complete until database connectivity is available or an
approved local/read-only OHLC source is supplied. Do not proceed to full Lane
A/B audit from this blocked run.
