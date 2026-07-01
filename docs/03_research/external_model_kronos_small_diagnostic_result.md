# Phase 37K - Kronos Small Offline Diagnostic Result

## Status

Phase 37K executed the approved small offline Kronos diagnostic on July 1, 2026.
Phase 37L later scrutinized the output and selected `REDESIGN_SMALL_DIAGNOSTIC`.
Phase 37M now designs a stochastic reproducibility/output-validity diagnostic
before any broader Kronos inference.
Phase 37N executed that bounded follow-up and found invalid OHLC rows remained
high; Phase 37O records the adapter/output-validation debug design in
`docs/03_research/external_model_kronos_adapter_output_validation_debug.md`.
Phase 37R later implemented reusable output-validity helpers, and Phase 37S
documents a policy-compliant retry design in
`docs/03_research/external_model_kronos_policy_compliant_retry_design.md`.

This was not a trading backtest. It did not create strategy rules, tune
thresholds, or approve production use. Generated outputs remain ignored under
`reports/v2/external_models/kronos/` and are not for commit unless separately
approved.

## Output Folder

- `reports/v2/external_models/kronos/small_diagnostic_20260701/`

Generated output files:

- `kronos_small_diagnostic_metadata.json`
- `kronos_small_diagnostic_input_manifest.csv`
- `kronos_small_diagnostic_forecast_paths.csv`
- `kronos_small_diagnostic_forecast_diagnostics.csv`
- `kronos_small_diagnostic_metric_summary.csv`
- `kronos_small_diagnostic_by_symbol.csv`
- `kronos_small_diagnostic_by_date.csv`
- `kronos_small_diagnostic_runtime_notes.txt`

Additional ignored helper/intermediate files in the output folder:

- `run_kronos_small_diagnostic.py`
- `prepare_metadata.json`
- `kronos_small_diagnostic_input_samples.csv`
- `kronos_small_diagnostic_actual_forward_paths.csv`

## Sample

Symbol selection rule:

Filter Research200 to `liquidity_bucket == HIGH`, sort by `liquidity_metric`
descending then symbol ascending, require each predeclared target date to have
at least 400 prior sessions and 5 future sessions, and choose the first 5
eligible symbols.

Selected symbols:

- `HDFCBANK`
- `ICICIBANK`
- `SBIN`
- `INFY`
- `BHARTIARTL`

Date selection rule:

Use six predeclared calendar targets across 2023-2024. For each target, choose
the nearest previous common market-open session present for all selected
symbols with 400-session lookback and 5-session future coverage.

Selected inference dates:

- `2023-01-16`
- `2023-05-15`
- `2023-09-14` shifted from target `2023-09-15`
- `2024-01-15`
- `2024-05-15`
- `2024-09-16`

Planned forecasts: 30. Completed forecasts: 30. Lookback: 400 sessions.
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

Dependency versions recorded in metadata:

- `numpy 2.5.0`
- `pandas 3.0.3`
- `torch 2.12.1`
- `einops 0.8.1`
- `huggingface_hub 0.33.1`
- `tqdm 4.67.1`
- `safetensors 0.6.2`

## Runtime

- Model/tokenizer load: 2.174916 seconds
- Total successful inference/output runtime: 264.955099 seconds
- Average runtime per forecast: 8.739297 seconds
- Minimum per-forecast runtime: 8.220600 seconds
- Maximum per-forecast runtime: 10.905696 seconds
- Laptop impact: no sluggish/unusable behavior observed from the command
  session; detailed memory telemetry was not collected.
- Abort criteria triggered: no.

Two pre-output issues were handled before final output generation:

- `local_files_only` was unsupported by this Hugging Face mixin and was removed
  before inference.
- Pandas attempted to use SciPy for Spearman rank correlation; the isolated
  Kronos venv does not include SciPy, so the ignored helper script computed
  Spearman as Pearson correlation of ranks.

## Metric Summary

From `kronos_small_diagnostic_metric_summary.csv`:

- Total forecasts: 30
- Directionally correct: 13
- Directional accuracy: 43.333333%
- Mean forecast error: -0.047969
- Median absolute forecast error: 0.034250
- Spearman rank IC: -0.268521
- Top 1 realized return average: -0.026200
- Bottom 1 realized return average: 0.017311
- Top-minus-bottom spread: -0.043511
- Top 2 realized return average: -0.007011
- Bottom 2 realized return average: 0.003848
- Top 2 minus bottom 2 spread: -0.010859

Phase 37L additionally found an output-validity concern:

- Forecast path rows present: 150 / 150
- Invalid OHLC forecast path rows: 17 / 150
- Invalid OHLC rate: 11.33%

This validity concern is a blocker for broader diagnostics until a separate
reproducibility/output-validity test checks whether invalid rows and unstable
rankings come from stochastic sampling, decoding settings, data mapping,
normalization/de-normalization, model behavior, or output validation.

By-symbol headline:

| Symbol | Forecasts | Directional accuracy | Avg predicted return | Avg realized return |
| --- | ---: | ---: | ---: | ---: |
| BHARTIARTL | 6 | 50.000000% | -0.144599 | 0.025420 |
| HDFCBANK | 6 | 33.333333% | -0.002064 | -0.022862 |
| ICICIBANK | 6 | 33.333333% | -0.027875 | 0.006707 |
| INFY | 6 | 66.666667% | -0.047864 | -0.001630 |
| SBIN | 6 | 33.333333% | -0.012989 | -0.003182 |

By-date headline:

| Date | Forecasts | Directional accuracy | Spearman rank IC | Top-minus-bottom spread |
| --- | ---: | ---: | ---: | ---: |
| 2023-01-16 | 5 | 20.000000% | 0.600000 | 0.011744 |
| 2023-05-15 | 5 | 100.000000% | 1.000000 | 0.046232 |
| 2023-09-14 | 5 | 60.000000% | -0.300000 | -0.064253 |
| 2024-01-15 | 5 | 40.000000% | -0.900000 | -0.206618 |
| 2024-05-15 | 5 | 20.000000% | 0.100000 | -0.008415 |
| 2024-09-16 | 5 | 20.000000% | 0.000000 | -0.039759 |

## Leakage and Misuse Confirmation

Confirmed in metadata:

- Symbols and dates were selected before inference.
- Model input windows ended at the inference date.
- No future rows were used as model input.
- No future labels were model input.
- Realized 5-session forward returns were joined only after forecast
  generation.
- No symbol/date/horizon changes were made after seeing forecast outputs.
- No raw forecast trading was performed.
- No threshold tuning was performed.
- No strategy rule was created.
- No full Research200 run was performed.
- No production use was performed.
- No fine-tuning or training was performed.
- No web UI, Qlib, or AkShare workflow was used.
- Kronos source was not modified.

## Limitations

- Only 30 forecasts.
- Only 5 HIGH-liquidity symbols.
- Only 6 inference dates.
- Only `Kronos-small`.
- Only one 5-session horizon.
- CPU-only execution.
- Stochastic sampling remains a reproducibility caveat even with seed 42.
- Benchmark, VIX, and drawdown context joins were left as `unknown` to keep
  the diagnostic lightweight.
- The metric pattern is weak/negative in this small sample and must not be
  interpreted as proof for or against production alpha.

## Decision

Phase 37K decision: `PROCEED_TO_37L_RESULT_SCRUTINY`.

Reason:

- The approved 30 forecast points completed.
- Required output files were written with valid row counts and schema.
- Leakage and misuse checks passed.
- The laptop-impact and runtime limits were acceptable.
- The decision is based on output validity and readiness for review, not on
  apparent profitability.

Phase 37L review decision: `REDESIGN_SMALL_DIAGNOSTIC`.

Phase 37M next-design decision:
`PROCEED_TO_37N_REPRO_VALIDITY_EXECUTION_APPROVAL`.

Phase 37N result decision: `FIX_ADAPTER_OR_OUTPUT_VALIDATION`.
Phase 37O debug-design decision: `PROCEED_TO_37P_ADAPTER_DEBUG_EXECUTION`.
Phase 37P adapter-debug decision:
`PROCEED_TO_37Q_OUTPUT_VALIDITY_POLICY_DESIGN`.
Phase 37Q policy-design decision:
`PROCEED_TO_37R_OUTPUT_VALIDITY_POLICY_IMPLEMENTATION`.

This does not approve execution. It only records that the next useful Kronos
step should be output-validity policy implementation, not a small diagnostic
retry. No full Research200 run, strategy integration, production use, raw
forecast trading, threshold tuning, or best-seed/decoding cherry-picking is
approved.

Later update: any future retry must be policy-compliant, must use explicit eval
when supported and deterministic-ish decoding, and must exclude invalid forecast
runs from signal metrics using the 37R output-validity helpers. Direct
comparison against 37K must be caveated because the decoding policy changes.

Phase 37W final closeout: after the policy-compliant retry and public evidence
review, the Kronos lane is closed for now with
`DOCS_ONLY_CLOSEOUT_AND_BIMONTHLY_REVIEW`. No further local inference, local
patch, Research200 scaling, strategy integration, production use, or raw
predicted-candle trading is approved.
