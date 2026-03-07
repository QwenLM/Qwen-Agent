# Pearl Prime Audiobook — Qwen-Agent Migration Checklist

## Canonical decision
- Canonical runtime repo: `Ahjan108/Qwen-Agent`
- Runtime model: Qwen-only via LM Studio local endpoint (`http://127.0.0.1:1234/v1`)
- No human in repair loop (manual review queue is exception handling only)

## What is now in Qwen-Agent
- `config/audiobook_script/`
- `prompts/audiobook/`
- `scripts/audiobook_script/`
- `schemas/comparator_result_v2.schema.json`
- `docs/AUDIOBOOK_PIPELINE_SPEC.md`
- `docs/GO_LIVE_FINAL_CHECKLIST.md`
- `docs/audiobook_operator_runbook.md`
- `.github/workflows/audiobook_scheduled.yml`
- `.github/workflows/audiobook_manual.yml`
- `.github/workflows/audiobook_regression.yml`

## Step-by-step cutover
1. Push `Qwen-Agent/main` with the audiobook files and workflows.
2. In GitHub repo secrets/vars, set runtime values if needed:
   - Optional vars: `QWEN_BASE_URL`, `QWEN_MODEL`
   - Local LM Studio default is already used by workflow env.
3. Ensure self-hosted runner is online on the machine that runs LM Studio.
4. In LM Studio, load the production Qwen model.
5. Trigger `Audiobook regression` (workflow_dispatch) and confirm green.
6. Trigger `Audiobook scheduled (Qwen-only)` manually once and confirm green.
7. Verify artifact upload:
   - `artifacts/audiobook/regression_report.json`
   - `artifacts/audiobook/**/status.json`
   - `artifacts/audiobook/manual_review_queue.json`
8. If green, keep schedule enabled (02:00 and 14:00 UTC).

## Autonomous runtime checks (must stay true)
- Golden regression remains green.
- Hard gate failures do not auto-pass after loop exhaustion.
- Manual review queue is generated when needed.
- Comparator schema version matches checklist schema version.

## Rollback
- Use: `scripts/release/audiobook_rollback.sh --batch-id <id> --dry-run`
- Then execute without `--dry-run` after review.
