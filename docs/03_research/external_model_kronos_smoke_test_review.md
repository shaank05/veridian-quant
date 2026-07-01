# Phase 37I — Kronos Tiny Smoke-Test Output Review

## 1. Status / Verdict

Phase 37I is review/docs only. No install, download, inference, backtest,
strategy integration, threshold tuning, or Kronos repository change is approved
by this phase.

Phase 37H technically passed: `Kronos-small` CPU inference succeeded on one
tiny HDFCBANK sample with a 400-session lookback and 5-session horizon.

This does not validate Kronos forecasting quality. This does not approve
production use. This does not approve strategy integration. This does not
approve full Research200 inference. This does not approve raw predicted-candle
trading.

## 2. Files / Artifacts Reviewed

Generated output folder reviewed:

- `reports/v2/external_models/kronos/smoke_test_20260630/`

Generated files reviewed:

- `kronos_smoke_test_metadata.json`
- `kronos_smoke_test_input_sample.csv`
- `kronos_smoke_test_forecast_paths.csv`
- `kronos_smoke_test_diagnostics.csv`
- `kronos_smoke_test_runtime_notes.txt`

Phase 37H `.gitignore` handling reviewed:

- `reports/v2/external_models/kronos/` is ignored by Git.

No expected generated Phase 37H file was missing during this review.

## 3. Environment Isolation Review

- Venv path:
  `C:\Users\Shika\Desktop\Shaank\BuddhAditya\external_repos\Kronos\.venv_kronos_smoke`
- Python version: `3.12.3`
- Installed dependencies:
  - `numpy 2.5.0`
  - `pandas 3.0.3`
  - `torch 2.12.1`
  - `einops 0.8.1`
  - `huggingface_hub 0.33.1`
  - `tqdm 4.67.1`
  - `safetensors 0.6.2`
- Install duration: `254.9` seconds.
- Veridian `.venv` was not used for Kronos dependency installation.
- Kronos dependencies were kept outside Veridian core.

Verdict: `PASS`.

## 4. Model / Tokenizer Review

- Tokenizer: `NeoQuasar/Kronos-Tokenizer-base`
- Tokenizer revision/hash: `0e0117387f39004a9016484a186a908917e22426`
- Model: `NeoQuasar/Kronos-small`
- Model revision/hash: `901c26c1332695a2a8f243eb2f37243a37bea320`
- Model-card license observed: `mit`
- `Kronos-base` was not downloaded.
- Download/load duration: `28.075` seconds.
- Cache path:
  `C:\Users\Shika\Desktop\Shaank\BuddhAditya\external_repos\Kronos\.hf_cache_kronos_smoke`
- Warnings/caveats:
  - Hugging Face cache used Windows non-symlink fallback.
  - `hf_xet` was not installed; regular HTTP fallback was used.

Verdict: `PASS_WITH_CAVEATS`.

## 5. Data Sample Review

- Symbol: `HDFCBANK`
- Liquidity bucket: `HIGH`
- Inference date: `2024-01-15`
- Market data existed on the inference date.
- Lookback sessions: `400`
- Input window: `2022-01-06` through `2024-01-15`
- Horizon: `5` sessions.
- Future sessions available: `452`
- Future evaluation dates: `2024-01-16`, `2024-01-17`, `2024-01-18`,
  `2024-01-19`, `2024-01-22`
- Sample size was within approval limits: 1 symbol and 1 inference date.
- Symbol/date/horizon were not changed after seeing output.

Verdict: `PASS`.

## 6. Execution Review

- CPU/GPU mode: `cpu`
- `torch_cuda_available`: `false`
- Inference runtime: `9.035` seconds.
- Total Kronos command runtime: `37.246` seconds.
- Laptop usability observation: no sluggish/unusable behavior observed from the
  command session.
- Memory telemetry caveat: detailed memory telemetry was not collected.
- Abort criteria triggered: no.

Verdict: `PASS_WITH_CAVEATS`.

## 7. Output Schema Review

- Forecast rows: `5`
- Diagnostics rows: `1`
- Output files written:
  - `kronos_smoke_test_metadata.json`
  - `kronos_smoke_test_input_sample.csv`
  - `kronos_smoke_test_forecast_paths.csv`
  - `kronos_smoke_test_diagnostics.csv`
  - `kronos_smoke_test_runtime_notes.txt`
- Required metadata fields were present for run ID, repo path/commit,
  tokenizer/model names and revisions, license observed, Python/dependency
  versions, OS, CPU/GPU mode, seed, decoding settings, selected symbol/date,
  lookback, horizon, output folder, runtime, laptop-impact notes, and caveats.
- Required diagnostics columns were present: `run_id`, `symbol`,
  `inference_date`, `horizon`, `pred_close_return`, `pred_direction`,
  `pred_high_low_range`, `pred_volatility_proxy`, `realized_forward_return`,
  `forecast_error`, and `notes`.
- The output schema is acceptable for designing a future small offline
  diagnostic experiment.

Verdict: `PASS`.

## 8. Forecast Sanity Review

Observed one-row diagnostic result:

- `pred_close_return`: `0.003514363982848989`
- `pred_direction`: `up`
- `realized_forward_return`: `-0.14995235826584086`
- `forecast_error`: `0.15346672224868985`

This is a single forecast only. It is not enough to judge model quality. This
row was directionally wrong. No profitability conclusion should be made. Do not
tune, filter, promote, or reject Kronos from one row.

## 9. Leakage / Misuse Review

Confirmed:

- No future rows in input.
- No future labels as model input.
- Realized return joined only after forecast generation.
- No horizon/date/symbol change after output.
- No trading rule created.
- No raw forecast trading.
- No threshold tuning.

Verdict: `PASS`.

## 10. Git / Artifact Handling Review

- `.gitignore` includes `reports/v2/external_models/kronos/`.
- Generated reports are ignored and not for commit.
- Model weights/cache are outside Veridian and not for commit.
- Only the `.gitignore` handling from Phase 37H should be retained as a
  repository change from execution.

Verdict: `PASS`.

## 11. Limitations

- One symbol.
- One date.
- One sampled path.
- One horizon.
- CPU-only.
- No memory telemetry.
- No repeated seed/stability check.
- No cross-sectional ranking.
- No year-by-year evaluation.
- No comparison against S1-S5.
- No comparison against liquidity/benchmark/VIX/drawdown inputs.
- No production inference path.

## 12. Decision

Decision: `PROCEED_TO_37J_SMALL_OFFLINE_DIAGNOSTIC_DESIGN`.

Reason:

- The technical smoke test passed.
- Environment isolation was acceptable.
- Model/tokenizer revisions were pinned and recorded.
- CPU inference completed within approved limits.
- Output schema is usable for future diagnostic design.

This decision is not based on forecast quality. The one observed forecast was
directionally wrong and is not enough evidence to judge Kronos as good or bad.
The next phase should be design-only. No new inference is approved yet.

Phase 37J is now documented in
`docs/03_research/external_model_kronos_small_diagnostic_experiment_design.md`.
It designs a 5-symbol x 6-date small offline diagnostic only; it does not
approve Phase 37K execution.

Later status update: Phase 37K executed only after separate user approval.
Phase 37L scrutinized the 30-forecast result and selected
`REDESIGN_SMALL_DIAGNOSTIC` because signal metrics were weak/negative and
17 / 150 forecast path rows had invalid OHLC relationships. Phase 37M now
designs a smaller stochastic reproducibility/output-validity diagnostic before
any broader Kronos run. This does not approve new inference.

## 13. Requirements for 37J

Phase 37J should design a small offline diagnostic experiment only. It should
not execute inference.

Design requirements:

- Predefine symbols, dates, and horizons.
- Use likely 5-10 symbols and limited dates only.
- No full Research200 run.
- No raw forecast trading.
- No threshold optimization.
- Decide whether repeated samples/seeds are needed.
- Decide compute, runtime, disk, and laptop-impact limits before execution.

Candidate metrics:

- Rank IC.
- Directional accuracy.
- Top/bottom rank spread.
- Forecast error.
- Agreement/disagreement with S1-S5.
- Behavior by liquidity, benchmark, VIX, and drawdown regime.

## 14. Anti-Misuse Guardrails

- No production claims from smoke test.
- No model-quality conclusion from one row.
- No raw predicted-candle execution.
- No full Research200 run.
- No strategy-rule creation.
- No threshold tuning.
- No symbol/date cherry-picking after seeing results.
- No fine-tuning before leakage/split audit.
- No committing model weights or generated reports.
- No cloud/GPU spend without approval.
