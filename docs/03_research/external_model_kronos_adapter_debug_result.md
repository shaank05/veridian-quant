# Phase 37P - Kronos Adapter Debug Execution Result

## Status / Verdict

Phase 37P executed the approved bounded Kronos adapter/output-validation debug
run on July 1, 2026.

Decision: `PROCEED_TO_37Q_OUTPUT_VALIDITY_POLICY_DESIGN`.

Reason: explicit eval mode reduced invalid OHLC rows versus the 37N-like
baseline on this tiny sample, and deterministic-ish decoding produced zero
invalid rows in this one-symbol/one-date run. However, invalid rows were not
eliminated by eval mode alone, and one tiny deterministic result is not enough
to approve a small diagnostic retry. Caller-side output validation and a
predeclared reject/flag/visualization policy are still required.

This was not an alpha test. No signal-quality conclusion, strategy rule,
threshold tuning, production use, or raw forecast trading is approved.

## Output Folder

Generated output folder:

- `reports/v2/external_models/kronos/adapter_debug_20260701/`

Generated files:

- `kronos_adapter_debug_metadata.json`
- `kronos_adapter_debug_input_manifest.csv`
- `kronos_adapter_debug_forecast_paths.csv`
- `kronos_adapter_debug_diagnostics.csv`
- `kronos_adapter_debug_invalid_ohlc_summary.csv`
- `kronos_adapter_debug_config_comparison.csv`
- `kronos_adapter_debug_runtime_notes.txt`
- `run_kronos_adapter_debug.py`

Generated outputs remain ignored and are not for commit unless separately
approved.

## Debug Sample

- Symbol: `HDFCBANK`
- Inference date: `2024-01-15`
- Lookback: 400 sessions
- Horizon: 5 sessions
- Seeds: `7`, `42`, `2024`
- Configurations: 3
- Planned forecast runs: 9
- Completed forecast runs: 9
- Forecast path rows: 45

The input rows were reused from the already-generated Phase 37N prepared sample
for `HDFCBANK` on `2024-01-15`, avoiding a new database extraction. The
lookback ended on the inference date and the 5 future rows were used only for
timestamps and secondary realized-return comparison.

## Environment / Model

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

Dependency versions recorded:

- `numpy 2.5.0`
- `pandas 3.0.3`
- `torch 2.12.1+cpu`
- `einops 0.8.1`
- `huggingface_hub 0.33.1`
- `tqdm 4.67.1`
- `safetensors 0.6.2`

## Configurations

| Config | Eval mode | Decoding settings | Forecast runs |
| --- | --- | --- | ---: |
| `baseline_37n_like` | No explicit eval; tokenizer/model remained in training mode | `T=1.0`, `top_k=0`, `top_p=0.9`, `sample_count=1`, `max_context=512` | 3 |
| `explicit_eval` | `tokenizer.eval()` and `model.eval()` applied | `T=1.0`, `top_k=0`, `top_p=0.9`, `sample_count=1`, `max_context=512` | 3 |
| `deterministic_low_randomness` | `tokenizer.eval()` and `model.eval()` applied | `T=1.0`, `top_k=1`, `top_p=1.0`, `sample_count=1`, `max_context=512` | 3 |

The baseline intentionally matched prior 37N behavior as closely as possible:
no explicit eval call and the same stochastic decoding settings.

## Execution Result

- Status: success
- Total runtime: 79.774 seconds
- Average runtime per forecast: 7.375 seconds
- Maximum runtime per forecast: 9.986 seconds
- Laptop impact: no sluggish/unusable behavior observed from the command
  session; detailed memory telemetry was not collected.
- Abort criteria triggered: no.
- Warnings/errors: `git rev-parse` on the external Kronos repo was blocked by
  Git safe-directory ownership checks under the sandbox user; the commit hash
  was read directly from `.git/refs/heads/master` instead.

## Output Validity Findings

Overall:

- Forecast runs: 9
- Forecast path rows: 45
- Invalid OHLC rows: 4
- Invalid OHLC rate: 8.888889%
- Forecasts with any invalid OHLC: 2 / 9

By configuration:

| Config | Path rows | Invalid OHLC rows | Invalid rate | Forecasts with any invalid OHLC |
| --- | ---: | ---: | ---: | ---: |
| `baseline_37n_like` | 15 | 3 | 20.000000% | 1 |
| `explicit_eval` | 15 | 1 | 6.666667% | 1 |
| `deterministic_low_randomness` | 15 | 0 | 0.000000% | 0 |

Main invalid reasons:

- `high_lt_close`: 2
- `high_lt_low`: 1
- `high_lt_open`: 1
- `low_gt_open`: 2

Invalid rows occurred only for seed `7` in this tiny run:

| Config | Seed | Step | Date | Invalid reasons | Largest violation | Largest violation pct of close |
| --- | ---: | ---: | --- | --- | ---: | ---: |
| `baseline_37n_like` | 7 | 3 | `2024-01-18` | `high_lt_close` | 0.596130 | 0.071517% |
| `baseline_37n_like` | 7 | 4 | `2024-01-19` | `high_lt_low;high_lt_close;low_gt_open` | 6.661499 | 0.794048% |
| `baseline_37n_like` | 7 | 5 | `2024-01-22` | `high_lt_open` | 1.060608 | 0.128205% |
| `explicit_eval` | 7 | 4 | `2024-01-19` | `low_gt_open` | 5.857727 | 0.684209% |

## API / Decoding Finding

Explicit eval mode helped but did not eliminate invalid OHLC rows:

- Baseline 37N-like: 3 / 15 invalid rows = 20.000000%.
- Explicit eval: 1 / 15 invalid rows = 6.666667%.

Deterministic-ish decoding eliminated invalid rows in this tiny sample:

- `deterministic_low_randomness`: 0 / 15 invalid rows = 0.000000%.
- All three seeds produced the same predicted close return and direction.

This does not prove that deterministic decoding solves output validity in
general. It only shows that, for `HDFCBANK` on `2024-01-15`, explicit eval mode
and `top_k=1`, `top_p=1.0` materially reduced or eliminated observed invalid
rows. A caller-side validity policy remains required because stochastic/eval
settings can still produce invalid OHLC, and any future diagnostic must define
what to do when invalid rows appear.

No approved settings were unsupported.

## Secondary Stability / Signal Notes

These are secondary only and must not be interpreted as alpha.

The realized 5-session forward return for the sample was
`-0.1499523582658408`.

| Config | Pred close return mean | Pred close return std | Direction values | Direction agreement |
| --- | ---: | ---: | --- | ---: |
| `baseline_37n_like` | 0.003404 | 0.013080 | `down;up;up` | 66.666667% |
| `explicit_eval` | 0.012474 | 0.024786 | `up;down;down` | 66.666667% |
| `deterministic_low_randomness` | 0.014081 | 0.000000 | `up;up;up` | 100.000000% |

All configurations were directionally wrong on this one sample, but that is not
the decision basis for 37P.

## Leakage / Misuse Confirmation

Confirmed:

- Configs and seeds were selected before inference.
- No future rows were used in model input.
- Input ended at the inference date only.
- Realized forward return was joined only after forecast generation.
- No future labels were model input.
- No config/seed changes were made after seeing forecasts.
- No raw forecast trading was performed.
- No threshold tuning was performed.
- No strategy rule was created.
- No full Research200 run was performed.
- No production use was performed.

## Scope Confirmation

Confirmed:

- No full Research200.
- No additional symbols/dates beyond `HDFCBANK` / `2024-01-15`.
- No `Kronos-base`.
- No production use.
- No fine-tuning/training.
- No web UI, Qlib, or AkShare.
- No Kronos source modification.
- No generated reports committed.
- No strategy or backtest logic changed.

## Limitations

- Tiny one-symbol/one-date sample.
- One model: `Kronos-small`.
- One horizon: 5 sessions.
- CPU-only.
- Uses prepared Phase 37N input rows rather than a fresh DB extraction.
- Output-validity-only debug, not alpha research.
- Deterministic-ish decoding evidence is encouraging but too narrow to approve
  scaling.
- Stochastic sampling remains a caveat for any future diagnostic.

## Decision

Decision: `PROCEED_TO_37Q_OUTPUT_VALIDITY_POLICY_DESIGN`.

Do not proceed to a small diagnostic retry yet. Phase 37Q should define the
predeclared policy for invalid forecast rows/runs, canonical raw output,
optional visualization-only repair, allowed decoding/API settings, and criteria
for when Kronos should be parked versus rerun.

Phase 37Q completed that docs-only policy design in
`docs/03_research/external_model_kronos_output_validity_policy.md`. It requires
future Kronos diagnostics to apply explicit eval mode, use deterministic-ish
decoding as the default candidate, mark any run with invalid OHLC as
`INVALID_OUTPUT`, exclude invalid runs from signal-quality metrics, and preserve
repair only as optional visualization unless separately approved. The next
selected step is `PROCEED_TO_37R_OUTPUT_VALIDITY_POLICY_IMPLEMENTATION`.

Phase 37R implemented reusable output-validity helpers, and Phase 37S documents
the policy-compliant retry design in
`docs/03_research/external_model_kronos_policy_compliant_retry_design.md`. Any
future retry remains approval-gated and must use 37R helper-based
output-validity gating. No immediate retry is approved from this result.

No full Research200 run, production use, strategy integration, raw forecast
trading, threshold tuning, best-seed selection, decoding cherry-picking,
fine-tuning, or training is approved.
