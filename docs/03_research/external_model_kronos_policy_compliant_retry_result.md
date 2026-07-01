# Phase 37T - Kronos Policy-Compliant Small Diagnostic Retry Result

## Status / Verdict

Phase 37T executed the explicitly approved bounded policy-compliant
`Kronos-small` retry on July 1, 2026.

Decision: `PROCEED_TO_37U_POLICY_RETRY_RESULT_SCRUTINY`.

Reason: execution completed and the output schema is usable, but 37Q/37R
output validity failed. The retry completed 30 / 30 forecast runs, but 3 / 30
forecast runs were marked `INVALID_OUTPUT` because at least one forecast path
row violated OHLC relationships. Invalid forecast-run rate was 10.00%, above
the 37Q 5% failure threshold. Signal metrics below are validity-gated and use
only the 27 valid forecast runs.

This result does not approve Research200, strategy integration, production use,
raw predicted-candle trading, threshold tuning, training, fine-tuning, or a
larger diagnostic. Do not claim direct improvement versus 37K without caveating
the eval/decoding-policy change.

## Output Folder

Generated output folder:

- `reports/v2/external_models/kronos/policy_retry_20260701/`

Generated files:

- `kronos_policy_retry_metadata.json`
- `kronos_policy_retry_input_manifest.csv`
- `kronos_policy_retry_forecast_paths.csv`
- `kronos_policy_retry_diagnostics.csv`
- `kronos_policy_retry_run_validity_summary.csv`
- `kronos_policy_retry_invalid_ohlc_summary.csv`
- `kronos_policy_retry_metric_summary.csv`
- `kronos_policy_retry_by_symbol.csv`
- `kronos_policy_retry_by_date.csv`
- `kronos_policy_retry_runtime_notes.txt`

Additional ignored helper/intermediate files:

- `run_kronos_policy_retry.py`
- `prepare_metadata.json`
- `kronos_policy_retry_input_samples.csv`
- `kronos_policy_retry_actual_forward_paths.csv`

Generated outputs remain ignored and are not for commit unless separately
approved.

## Sample

Approved symbols:

- `HDFCBANK`
- `ICICIBANK`
- `SBIN`
- `INFY`
- `BHARTIARTL`

Approved inference dates:

- `2023-01-16`
- `2023-05-15`
- `2023-09-14`
- `2024-01-15`
- `2024-05-15`
- `2024-09-16`

Scope:

- Planned forecast runs: 30.
- Completed forecast runs: 30.
- Lookback: 400 sessions.
- Horizon: 5 sessions.
- Seed: `42`.
- Configuration: `deterministic_eval_topk1_topp1`.

Preflight confirmed the approved sample had the required 400-session lookback
and 5-session future window. No symbol/date substitution was made.

## Environment / Model

- Kronos repo:
  `C:\Users\Shika\Desktop\Shaank\BuddhAditya\external_repos\Kronos`
- Kronos commit: `67b630e67f6a18c9e9be918d9b4337c960db1e9a`
- Kronos venv:
  `C:\Users\Shika\Desktop\Shaank\BuddhAditya\external_repos\Kronos\.venv_kronos_smoke`
- HF cache:
  `C:\Users\Shika\Desktop\Shaank\BuddhAditya\external_repos\Kronos\.hf_cache_kronos_smoke`
- Tokenizer: `NeoQuasar/Kronos-Tokenizer-base`
- Tokenizer revision: `0e0117387f39004a9016484a186a908917e22426`
- Model: `NeoQuasar/Kronos-small`
- Model revision: `901c26c1332695a2a8f243eb2f37243a37bea320`
- Observed model-card license: `mit`
- CPU/GPU mode: CPU.
- `torch_cuda_available`: `false`.
- `Kronos-base` was not downloaded.

Recorded dependency versions:

- `numpy 2.5.0`
- `pandas 3.0.3`
- `torch 2.12.1+cpu`
- `einops 0.8.1`
- `huggingface_hub 0.33.1`
- `tqdm 4.67.1`
- `safetensors 0.6.2`

Eval status:

- `tokenizer.eval()` supported and applied.
- `model.eval()` supported and applied.
- Tokenizer/model training flags were `false` after eval and predictor init.

Decoding:

- `T=1.0`
- `top_k=1`
- `top_p=1.0`
- `sample_count=1`
- `max_context=512`

## Runtime

- Model/tokenizer load: 3.329 seconds.
- Total runtime: 189.482 seconds.
- Average runtime per forecast: 6.183 seconds.
- Maximum runtime per forecast: 6.837 seconds.
- Laptop impact: no sluggish/unusable behavior observed from the command
  session; detailed memory telemetry was not collected.
- Abort criteria triggered: no.

## Output-Validity Result

37R helper policy version: `37Q_v1`.

Overall:

- Planned forecast runs: 30.
- Completed forecast runs: 30.
- Valid forecast runs: 27.
- Invalid forecast runs: 3.
- Invalid forecast-run rate: 10.00%.
- Total path rows: 150.
- Invalid path rows: 4.
- Invalid path-row rate: 2.666667%.
- Output validity status: `OUTPUT_VALIDITY_FAILED`.

The run failed output validity because invalid forecast-run rate exceeded the
37Q 5% failure threshold. Invalid path-row rate was above the 1% warning
threshold but below the 5% path-row failure threshold.

Invalid rows by symbol:

| Symbol | Path rows | Invalid rows | Invalid rate | Forecasts with invalid OHLC |
| --- | ---: | ---: | ---: | ---: |
| BHARTIARTL | 30 | 0 | 0.00% | 0 |
| HDFCBANK | 30 | 0 | 0.00% | 0 |
| ICICIBANK | 30 | 1 | 3.33% | 1 |
| INFY | 30 | 0 | 0.00% | 0 |
| SBIN | 30 | 3 | 10.00% | 2 |

Invalid rows by date:

| Date | Path rows | Invalid rows | Invalid rate | Forecasts with invalid OHLC |
| --- | ---: | ---: | ---: | ---: |
| 2023-01-16 | 25 | 2 | 8.00% | 1 |
| 2023-05-15 | 25 | 0 | 0.00% | 0 |
| 2023-09-14 | 25 | 1 | 4.00% | 1 |
| 2024-01-15 | 25 | 0 | 0.00% | 0 |
| 2024-05-15 | 25 | 1 | 4.00% | 1 |
| 2024-09-16 | 25 | 0 | 0.00% | 0 |

Main invalid reasons:

- `high_lt_open`: 3 rows.
- `high_lt_close`: 1 row.

Invalid forecast runs:

- `ICICIBANK`, `2023-09-14`: 1 / 5 invalid path rows.
- `SBIN`, `2023-01-16`: 2 / 5 invalid path rows.
- `SBIN`, `2024-05-15`: 1 / 5 invalid path rows.

## Validity-Gated Signal Metrics

Signal metrics below use only `VALID_OUTPUT` / `metric_eligible` forecast runs.
They exclude 3 invalid forecast runs. These metrics are not directly comparable
to 37K without caveating the eval/decoding-policy change.

- Metric-eligible runs: 27.
- Excluded invalid runs: 3.
- Directionally correct: 11 / 27.
- Directional accuracy: 40.740741%.
- Mean forecast error: -0.037483.
- Median absolute forecast error: 0.021715.
- Spearman rank IC: -0.199634.
- Top1 realized average: -0.024687.
- Bottom1 realized average: 0.015210.
- Top1-minus-bottom1 spread: -0.039897.
- Top2 realized average: -0.004876.
- Bottom2 realized average: 0.008284.
- Top2-minus-bottom2 spread: -0.013160.

By-symbol validity-gated headline:

| Symbol | Valid runs | Invalid runs | Directional accuracy | Mean forecast error |
| --- | ---: | ---: | ---: | ---: |
| HDFCBANK | 6 | 0 | 16.67% | 0.024439 |
| ICICIBANK | 5 | 1 | 20.00% | -0.040303 |
| SBIN | 4 | 2 | 75.00% | 0.006104 |
| INFY | 6 | 0 | 50.00% | -0.011580 |
| BHARTIARTL | 6 | 0 | 50.00% | -0.152015 |

By-date validity-gated headline:

| Date | Valid runs | Invalid runs | Rank IC | Top1-minus-bottom1 spread | Directional accuracy |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2023-01-16 | 4 | 1 | 0.400000 | 0.011831 | 50.00% |
| 2023-05-15 | 5 | 0 | 0.700000 | 0.046232 | 60.00% |
| 2023-09-14 | 4 | 1 | -0.200000 | -0.051732 | 75.00% |
| 2024-01-15 | 5 | 0 | -0.600000 | -0.206618 | 20.00% |
| 2024-05-15 | 4 | 1 | 0.400000 | 0.000666 | 0.00% |
| 2024-09-16 | 5 | 0 | -0.200000 | -0.039759 | 40.00% |

The validity-gated signal pattern remains weak/negative: overall rank IC and
top/bottom spreads are negative.

## Leakage / Misuse Confirmation

Confirmed:

- Symbols, dates, seed, and decoding were fixed before inference.
- Input lookback ended at the inference date.
- No future rows were used in model input.
- Realized returns were joined only after forecast generation.
- No future labels were model input.
- No symbol/date/horizon/decoding changes were made after outputs.
- No raw forecast trading was performed.
- No threshold tuning was performed.
- No strategy rule was created.
- No full Research200 run was performed.
- No production use was performed.

## Scope Confirmation

Confirmed:

- No full Research200.
- No `Kronos-base`.
- No production use.
- No fine-tuning/training.
- No web UI, Qlib, or AkShare.
- No Kronos source modification.
- No generated reports committed.
- No strategy or backtest logic changed.

## Limitations

- Small sample: 30 planned runs, 27 metric-eligible runs.
- One model: `Kronos-small`.
- One horizon: 5 sessions.
- One deterministic-ish decoding configuration.
- CPU-only.
- Output validity still failed under the 37Q forecast-run threshold.
- Validity-gated metrics are not directly comparable to 37K without the
  eval/decoding-policy caveat.
- This is diagnostic evidence only, not alpha proof.

## Decision

Decision: `PROCEED_TO_37U_POLICY_RETRY_RESULT_SCRUTINY`.

Do not proceed to a larger diagnostic before 37U scrutiny. The immediate next
step should review output validity failure, invalid-run concentration, metric
eligibility, and weak/negative validity-gated signal metrics before deciding
whether to revise policy/debug, park Kronos, or design any further diagnostic.
