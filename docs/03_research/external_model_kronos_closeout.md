# Phase 37W — Kronos Closeout / Bi-Monthly Upstream Review

## 1. Status / Verdict

Verdict: `DOCS_ONLY_CLOSEOUT_AND_BIMONTHLY_REVIEW`.

The Kronos external-model lane is closed for now.

- No more Kronos inference is approved.
- No local Kronos patch is approved.
- No strategy integration is approved.
- No production use is approved.
- No Research200 scaling is approved.
- Upstream Kronos repo/issues/model cards should be reviewed every two months
  for maturity, fixes, and improved prediction/output-validity behavior.

This is a closeout decision, not a "park pending upstream fix" decision.

## 2. Why Kronos Is Closed For Now

Internal evidence is not strong enough to continue local Kronos work today:

- 37K invalid OHLC rows: 17 / 150 = 11.33%.
- 37N invalid OHLC rows: 16 / 90 = 17.78%.
- 37T invalid forecast runs: 3 / 30 = 10.00%.
- 37T invalid path rows: 4 / 150 = 2.666667%.
- 37T output validity status: `OUTPUT_VALIDITY_FAILED`.
- 37T valid-run directional accuracy: 11 / 27 = 40.740741%.
- 37T rank IC: -0.199634.
- 37T top1 spread: -0.039897.
- 37T top2 spread: -0.013160.

Therefore output validity and signal quality are both insufficient today.

## 3. What Worked

- Repository discovery succeeded.
- License/model-card research supported internal research planning.
- The isolated Kronos environment worked.
- The tiny smoke test executed.
- The 30-run small diagnostic executed.
- The reusable output-validity helper was implemented and tested.
- 37R tests passed: 22 passed.
- The policy-compliant retry generated usable artifacts.
- Leakage/misuse controls were respected.

## 4. What Failed / Blocked

- Invalid OHLC output appeared repeatedly.
- Invalids persisted after eval and deterministic-ish decoding.
- Deterministic-ish decoding reduced but did not eliminate invalids in 37T.
- 37T failed the 37Q validity policy.
- Valid-run signal metrics stayed weak/negative.
- Public issue review found no direct invalid-OHLC issue, no
  maintainer-confirmed fix, no official OHLC guarantee, and no official repair
  guidance.
- Broader generation-quality/reproducibility issues exist publicly, including
  a CPU/GPU output mismatch concern.

## 5. Public Issue Review Summary

Phase 37V reviewed:

- GitHub repo README/source/issues/PRs.
- Hugging Face Kronos-small/base/tokenizer/model cards/discussions.
- Paper/model-card references.

Findings:

- Direct invalid-OHLC issues found: 0.
- GitHub OHLC issue search results: 0.
- GitHub invalid issue search results: 0.
- Broader generation-failure issues found: 4.
- Maintainer-confirmed fix found: 0.
- Official OHLC guarantee found: no.
- Official repair guidance found: no.
- Useful confirmed workaround found: no.
- Local patch now: no.

Relevant broader public concerns:

- #229 implausible generated data.
- #319 A-share MAPE/quality concern.
- #156 long-horizon concern.
- #184 CPU/GPU output mismatch.

Eval plus `top_k=1` / `top_p=1.0` remains an internal/plausible mitigation,
not a confirmed public fix. It still failed the 37Q policy in 37T.

## 6. Local Patch Position

Do not patch local Kronos now.

Patching would create a separate "Veridian-patched Kronos" evidence bucket.
Any future patch experiment must:

- Use a separate Kronos branch.
- Record upstream commit and patched commit.
- Be separately approved.
- Not claim results as public Kronos.
- Not be used for production or strategy logic.
- Not mix patched and unpatched evidence.

## 7. Bi-Monthly Upstream Review Plan

Review Kronos upstream every two months.

Check:

- GitHub issues for invalid candles, generation quality, prediction accuracy,
  and CPU/GPU mismatch.
- Pull requests related to predictor, decoding, tokenizer, inverse
  normalization, output validity, OHLC repair, and deterministic decoding.
- Model-card updates for Kronos-small/base/tokenizer.
- New model/tokenizer revisions.
- Maintainer responses on generation failure or candle validity.
- Any official example/API change.

Record findings in docs before reopening experiments.

Do not rerun inference merely because time passed. Rerun only if there is
concrete upstream improvement or explicit user approval.

## 8. Revisit Conditions

Kronos can be revisited only if one or more occur:

- Upstream issue/PR/commit directly addresses generated OHLC validity.
- Official docs clarify expected output-validity handling.
- Maintainer suggests a confirmed decoding/API fix.
- New model/tokenizer revision claims improved candle validity or prediction
  quality.
- CPU/GPU reproducibility concern is clarified or fixed.
- Public evidence shows better predictive accuracy on comparable daily
  equities.
- User explicitly approves a close-only diagnostic design.
- User explicitly approves a separate patched-Kronos experiment design.

## 9. Explicitly Rejected / Not Approved

- No raw predicted-candle trading.
- No Research200 scaling.
- No strategy integration.
- No production use.
- No local patch now.
- No repair-and-trade.
- No close-only diagnostic by default.
- No threshold tuning.
- No best-seed or best-decoding cherry-picking.
- No fine-tuning before a separate leakage/split audit.

## 10. Future Options If Reopened

Possible future branches:

- Upstream fix validation design.
- Close-only diagnostic design.
- Patched Kronos experiment design.
- New model revision smoke test.
- Alternative external model lane.
- Return to internal strategy/risk branches.

## 11. Decision

Decision: `DOCS_ONLY_CLOSEOUT_AND_BIMONTHLY_REVIEW`.

Close the Kronos lane for now. Continue only a bi-monthly upstream maturity
review. Do not continue local inference, patch local Kronos, use Kronos in
strategy logic, scale to Research200, or use raw predicted candles.
