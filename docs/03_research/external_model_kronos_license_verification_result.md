# Phase 37E — Kronos License / Model-Card Verification Result

## 1. Status / Verdict

Phase 37E is docs-only. No installation is approved. No model download is
approved. No Hugging Face download is approved. No inference is approved. No
production use is approved.

Verification is based on repo-visible files and manual browser inspection of
Hugging Face model cards. This is not legal advice.

Kronos remains approved only for possible future offline diagnostic research,
subject to later execution approval.

## 2. Verification Date / Method

- Verification date: 2026-06-30.
- Verifier: project maintainer / Codex-assisted documentation.
- Method:
  - Inspected cloned repo files.
  - Manually inspected Hugging Face model cards in browser.
  - No downloads.
  - No scripts.
  - No installs.

Checked sources:

- Local repo license: `C:\Users\Shika\Desktop\Shaank\BuddhAditya\external_repos\Kronos\LICENSE`
- Local repo readme: `C:\Users\Shika\Desktop\Shaank\BuddhAditya\external_repos\Kronos\README.md`
- `https://huggingface.co/NeoQuasar/Kronos-Tokenizer-base`
- `https://huggingface.co/NeoQuasar/Kronos-small`
- `https://huggingface.co/NeoQuasar/Kronos-base`

## 3. Repo Code License

- License file path: `external_repos/Kronos/LICENSE`.
- License type: MIT License.
- Repo code appears permissive for internal research under the visible MIT
  license text.
- Visible attribution/notice requirement: preserve the copyright notice and
  permission notice in copies or substantial portions of the software.
- Repo README states the project is licensed under the MIT License.
- Repo README model zoo points to separate Hugging Face model/tokenizer cards;
  model weights should be treated as separate artifacts from repo code.
- Repo README includes fine-tuning and demo/backtesting examples, but these are
  not approved for Veridian use by this phase.

Repo verdict: `CLEAR_FOR_INTERNAL_RESEARCH`.

Production note: repo code appears permissive, but Phase 37E does not grant
production approval. Production use, redistribution, hosted serving, or bundled
model-weight use still requires separate review.

## 4. Model Card Verification Table

| Model identifier | Model type | Model-card license field | Usage restrictions visible | Redistribution restrictions visible | Attribution/notice requirement visible | Model revision/hash recorded? | Verification source | Verification verdict | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `NeoQuasar/Kronos-Tokenizer-base` | Tokenizer | `mit` | No additional restriction observed in visible model-card text beyond MIT/license/citation context. | No additional restriction observed in visible model-card text beyond MIT/license/citation context. | Model card includes citation request/reference to the Kronos paper; MIT notice preservation should be retained. | No; not yet pinned. | Hugging Face model card inspected manually in browser. | `CLEAR_FOR_INTERNAL_RESEARCH` | Internal offline diagnostic research appears clear enough to proceed to planning, subject to explicit download approval later. |
| `NeoQuasar/Kronos-small` | Model weights | `mit` | No additional restriction observed in visible model-card text beyond MIT/license/citation context. | No additional restriction observed in visible model-card text beyond MIT/license/citation context. | Model card includes citation request/reference to the Kronos paper; MIT notice preservation should be retained. | No; not yet pinned. | Hugging Face model card inspected manually in browser. | `CLEAR_FOR_INTERNAL_RESEARCH` | Preferred candidate for any future tiny smoke test because it is the smallest selected model. |
| `NeoQuasar/Kronos-base` | Model weights | `mit` | No additional restriction observed in visible model-card text beyond MIT/license/citation context. | No additional restriction observed in visible model-card text beyond MIT/license/citation context. | Model card includes citation request/reference to the Kronos paper; MIT notice preservation should be retained. | No; not yet pinned. | Hugging Face model card inspected manually in browser. | `CLEAR_FOR_INTERNAL_RESEARCH` | Larger than `Kronos-small`; not preferred for first laptop-safe smoke test. |

## 5. Model Revision / Pinning Notes

Exact model and tokenizer revisions should be pinned before any future model
download. Phase 37E did not record immutable model revisions or commit hashes,
so all selected model/tokenizer artifacts are `not yet pinned`.

Future smoke tests must record:

- Tokenizer revision/hash.
- Model revision/hash.
- Dependency versions.
- Data extraction window.
- Exact symbol/date rows.

No floating `latest` model version should be used for reproducible research.

## 6. Internal Research Use Verdict

Based on visible evidence, the cloned Kronos repo code and the selected Hugging
Face tokenizer/model cards appear clear enough for future internal offline
diagnostic research planning.

Components clear enough for future internal offline research planning:

- Repo code under visible MIT license.
- `NeoQuasar/Kronos-Tokenizer-base` with visible `mit` model-card license.
- `NeoQuasar/Kronos-small` with visible `mit` model-card license.
- `NeoQuasar/Kronos-base` with visible `mit` model-card license.

Components still not complete:

- Exact model/tokenizer revisions are not pinned.
- Production, redistribution, hosted serving, customer-facing use, bundled
  model-weight packaging, and external release terms are not production-cleared
  by this phase.

## 7. Production / Redistribution Caveats

- No production approval from Phase 37E.
- No redistribution approval unless model-card terms are explicitly reviewed
  and recorded for that purpose.
- Customer-facing product use requires separate review.
- Hosted/model-serving use requires separate review.
- Packaging model weights with Veridian requires separate review.
- Veridian should retain license notices, model-card references, and citation
  references if any future use is approved.

## 8. Remaining Blockers Before Any Install/Download

- User approval for installation.
- User approval for model/tokenizer download.
- Isolated environment path.
- Exact model/tokenizer selected.
- Pinned model/tokenizer revisions.
- Dependency pinning.
- Tiny smoke-test symbol/date set.
- Abort criteria.
- Output folder.
- No full Research200 run.
- No production use.

## 9. Decision

Phase 37E decision:

- License/model-card evidence recorded.
- No model download approved.
- No installation approved.
- No inference approved.
- No production approval.

Decision option selected:

- `PROCEED_TO_37F_TINY_SMOKE_TEST_IMPLEMENTATION_PLAN`

Rationale:

Visible repo and model-card license fields appear clear enough for internal
offline diagnostic research planning. Phase 37F may plan a tiny smoke-test
implementation, but it still must not install dependencies, download model
weights, or run inference unless a later phase explicitly approves those steps.

Phase 37F is documented in
`docs/03_research/external_model_kronos_tiny_smoke_test_implementation_plan.md`
as the next planning step after `CLEAR_FOR_INTERNAL_RESEARCH`. It does not
approve installation, model/tokenizer download, inference, or production use.

Phase 37G is documented in
`docs/03_research/external_model_kronos_execution_approval_checklist.md` as the
required exact approval gate before any Phase 37H execution. It also does not
approve installation, model/tokenizer download, inference, or production use.

## 10. Anti-Misuse Guardrails

- Do not download weights before approval.
- Do not install dependencies into the Veridian core environment.
- Do not use model cards as production approval.
- Do not run full Research200 first.
- Do not use smoke-test forecasts as signals.
- Do not redistribute weights.
- Do not fine-tune before leakage/split audit.
- Do not make production claims from license verification.
