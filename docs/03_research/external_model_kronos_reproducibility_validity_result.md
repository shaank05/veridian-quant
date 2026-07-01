# Phase 37N - Kronos Reproducibility / Output Validity Result

## Status

Phase 37N executed the approved bounded reproducibility/output-validity
diagnostic on July 1, 2026.

This was not a trading experiment. It did not create strategy rules, tune
thresholds, approve production use, or approve raw forecast trading. Generated
outputs remain ignored under `reports/v2/external_models/kronos/` and are not
for commit unless separately approved.

Decision: `FIX_ADAPTER_OR_OUTPUT_VALIDATION`.

Reason: invalid OHLC rows remained high and unexplained: 16 / 90 forecast path
rows = 17.777778%, affecting 8 / 18 forecast runs and appearing across both
symbols, all three dates, and all three seeds.

Phase 37O follow-up:
`docs/03_research/external_model_kronos_adapter_output_validation_debug.md`
inspects the Veridian helper scripts, local generated schemas, and Kronos
source/examples. It keeps the lane blocked and selects
`PROCEED_TO_37P_ADAPTER_DEBUG_EXECUTION`, not a small diagnostic retry.

## Output Folder

- `reports/v2/external_models/kronos/repro_validity_20260701/`

Generated output files:

- `kronos_repro_validity_metadata.json`
- `kronos_repro_validity_input_manifest.csv`
- `kronos_repro_validity_forecast_paths.csv`
- `kronos_repro_validity_diagnostics.csv`
- `kronos_repro_validity_invalid_ohlc_summary.csv`
- `kronos_repro_validity_seed_stability.csv`
- `kronos_repro_validity_metric_summary.csv`
- `kronos_repro_validity_runtime_notes.txt`

Additional ignored helper/intermediate files:

- `run_kronos_repro_validity.py`
- `prepare_metadata.json`
- `kronos_repro_validity_input_samples.csv`
- `kronos_repro_validity_actual_forward_paths.csv`

## Sample

Symbols:

- `HDFCBANK`
- `INFY`

Dates:

- `2023-05-15`
- `2023-09-14`
- `2024-01-15`

Middle date selection rule:

From remaining 37K dates, keep dates present for HDFCBANK and INFY with
400-session lookback and 5 future sessions; sort chronologically and choose the
earlier middle candidate for deterministic even-count selection. This selected
`2023-09-14`.

Seeds:

- `7`
- `42`
- `2024`

Planned forecast runs: 18. Completed forecast runs: 18. Lookback: 400 sessions.
Horizon: 5 sessions.

## Environment

- Kronos repo: `C:\Users\Shika\Desktop\Shaank\BuddhAditya\external_repos\Kronos`
- Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`
- Kronos venv: `C:\Users\Shika\Desktop\Shaank\BuddhAditya\external_repos\Kronos\.venv_kronos_smoke`
- HF cache: `C:\Users\Shika\Desktop\Shaank\BuddhAditya\external_repos\Kronos\.hf_cache_kronos_smoke`
- Tokenizer: `NeoQuasar/Kronos-Tokenizer-base`
- Tokenizer revision: `0e0117387f39004a9016484a186a908917e22426`
- Model: `NeoQuasar/Kronos-small`
- Model revision: `901c26c1332695a2a8f243eb2f37243a37bea320`
- Observed model-card license: `mit`
- CPU/GPU mode: CPU
- `torch_cuda_available`: `false`
- `Kronos-base` was not downloaded.

Recorded dependency versions:

- `numpy 2.5.0`
- `pandas 3.0.3`
- `torch 2.12.1+cpu`
- `einops 0.8.1`
- `huggingface_hub 0.33.1`
- `tqdm 4.67.1`
- `safetensors 0.6.2`

## Runtime

- Model/tokenizer load: 3.173664 seconds
- Total successful runtime: 161.794883 seconds
- Average runtime per forecast run: 8.791453 seconds
- Maximum runtime per forecast run: 10.013869 seconds
- Laptop impact: no sluggish/unusable behavior observed from the command
  session; detailed memory telemetry was not collected.
- Abort criteria triggered: no.

## Output Validity Findings

Overall:

- Total path rows: 90
- Invalid OHLC rows: 16
- Invalid OHLC rate: 17.777778%
- Forecasts with any invalid OHLC row: 8 / 18

By symbol:

| Symbol | Path rows | Invalid rows | Invalid rate | Forecasts with invalid OHLC |
| --- | ---: | ---: | ---: | ---: |
| HDFCBANK | 45 | 4 | 8.888889% | 2 |
| INFY | 45 | 12 | 26.666667% | 6 |

By date:

| Date | Path rows | Invalid rows | Invalid rate | Forecasts with invalid OHLC |
| --- | ---: | ---: | ---: | ---: |
| 2023-05-15 | 30 | 6 | 20.000000% | 3 |
| 2023-09-14 | 30 | 6 | 20.000000% | 3 |
| 2024-01-15 | 30 | 4 | 13.333333% | 2 |

By seed:

| Seed | Path rows | Invalid rows | Invalid rate | Forecasts with invalid OHLC |
| ---: | ---: | ---: | ---: | ---: |
| 7 | 30 | 7 | 23.333333% | 3 |
| 42 | 30 | 4 | 13.333333% | 2 |
| 2024 | 30 | 5 | 16.666667% | 3 |

Main invalid reasons:

- `high_lt_open`: 8 rows
- `low_gt_close`: 7 rows
- `high_lt_close`: 4 rows
- `low_gt_open`: 4 rows
- `high_lt_low`: 2 rows

Invalid rows were not isolated to one symbol, date, seed, or forecast step.
This supports an adapter/output-validation investigation before any small
diagnostic retry.

## Seed Stability Findings

Overall:

- Average direction agreement: 77.777778%
- Total sign flip count across symbol/date groups: 5
- Average predicted close-return standard deviation: 0.013429
- Average pairwise rank correlation: 0.111111
- Rank correlation count: 9

Most unstable symbol/date by return standard deviation:

- `HDFCBANK` on `2023-05-15`: std 0.020701, directions `down;up;up`,
  direction agreement 66.666667%, sign flips 1.

Most unstable symbol/date by direction transitions:

- `HDFCBANK` on `2023-09-14`: directions `down;up;down`, sign flips 2,
  direction agreement 66.666667%.

Most stable symbol/dates by direction:

- `INFY` on `2023-05-15`: directions `up;up;up`, agreement 100.000000%,
  return std 0.002753.
- `INFY` on `2024-01-15`: directions `down;down;down`, agreement 100.000000%,
  return std 0.010574.

Rank stability caveat:

Rank correlations are coarse because each date has only two symbols. The
average pairwise rank correlation was 0.111111, which is not strong enough to
support broader ranking diagnostics while invalid OHLC rows remain unresolved.

## Secondary Signal Summary

These metrics are secondary only and must not be interpreted as alpha:

- Directionally correct: 9 / 18
- Directional accuracy: 50.000000%
- Mean forecast error: 0.031484
- Median absolute forecast error: 0.039501

## Leakage and Misuse Confirmation

Confirmed in metadata:

- Symbols, dates, and seeds were selected before inference.
- Model input windows ended at the inference date.
- No future rows were used as model input.
- No future labels were model input.
- Realized 5-session forward returns were joined only after forecast
  generation.
- No symbol/date/horizon/seed changes were made after seeing outputs.
- No raw forecast trading was performed.
- No threshold tuning was performed.
- No strategy rule was created.
- No full Research200 run was performed.
- No production use was performed.
- No fine-tuning or training was performed.
- No web UI, Qlib, or AkShare workflow was used.
- Kronos source was not modified.

## Limitations

- Only 18 forecast runs.
- Only 2 symbols.
- Only 3 inference dates.
- Only `Kronos-small`.
- Only one 5-session horizon.
- CPU-only execution.
- Stochastic sampling remains a caveat even with fixed seeds.
- Rank stability uses two-symbol cross-sections.
- Benchmark, VIX, and drawdown context were not joined because this diagnostic
  focused on output validity and reproducibility.

## Decision

Decision: `FIX_ADAPTER_OR_OUTPUT_VALIDATION`.

Do not proceed to a small diagnostic retry yet. The immediate next work should
inspect the output construction and validation boundary: Kronos predicted
candle ordering, de-normalization behavior, OHLC repair/rejection policy,
whether invalid generated rows should invalidate a forecast run, and how to
record invalid-row handling before any further signal-quality experiment.

Phase 37O completed that read-only inspection. It found no simple column-order
swap and no Veridian-side de-normalization step, but did find a concrete
adapter/API concern: the 37K/37N helper scripts did not explicitly call
`tokenizer.eval()` or `model.eval()`, while Kronos' regression tests do. It also
found no built-in Kronos OHLC repair or candle-validity guarantee. The next
step remains adapter/output-validation debug only.

No full Research200 run, production use, strategy integration, raw forecast
trading, threshold tuning, best-seed selection, decoding cherry-picking, or
fine-tuning is approved.
