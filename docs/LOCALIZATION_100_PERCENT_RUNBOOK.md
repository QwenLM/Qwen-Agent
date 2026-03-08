# LOCALIZATION 100% RUNBOOK

> **Purpose**: Step-by-step procedure to take audiobook localization from "scaffolded" to "production-proven".
> **Prerequisite**: LM Studio running at `http://127.0.0.1:1234` with `qwen3-14b` loaded.
> **Do not skip steps. Do not claim done from scaffold/status alone.**

---

## 1. Freeze and sync

Pull latest `main`. Stop all parallel dev edits on audiobook/localization until this run finishes. Keep one runner job at a time.

---

## 2. Run max-safe parallel generation (content fill), not max-unsafe

Parallelize by **locale batches**, not unlimited jobs. Use max 3 concurrent locale workers on your current LM Studio host. Complete all missing atom translations first, then validate.

---

## 3. Mandatory command sequence

```bash
cd /Users/ahjan/phoenix_omega/Qwen-Agent

# A) Fill locale content
python3 scripts/localization/translate_atoms_all_locales.py --all-locales

# B) Structural + quality validation
python3 scripts/localization/validate_translations.py --all-locales --report

# C) Closed-loop learn/apply artifacts
python3 scripts/localization/native_prompts_eval_learn.py --weekly --system both
```

---

## 4. Regression in two phases (required)

```bash
# Phase 1: gate health (fast, should pass)
python3 scripts/audiobook_script/run_regression.py --smoke --verbose

# Phase 2: full quality proof (must run for 100%)
python3 scripts/audiobook_script/run_regression.py --verbose
```

If full run fails: fix cause, rerun full run until green.

---

## 5. Then run autonomous proof

GitHub Actions: `Audiobook scheduled (Qwen-only)` manual dispatch once. Confirm green + artifact upload.

---

## 6. Evidence pack (must capture)

| Evidence | Where to record |
|----------|----------------|
| Regression smoke run URL + artifact | GO_LIVE_FINAL_CHECKLIST.md Item 10 evidence table |
| Regression full-golden run URL + artifact | GO_LIVE_FINAL_CHECKLIST.md Item 10 evidence table |
| Scheduled run URL + artifact | GO_LIVE_FINAL_CHECKLIST.md Item 10 evidence table |
| `manual_review_queue.json` status (empty or explained) | GO_LIVE_FINAL_CHECKLIST.md Item 10 evidence table |
| Model ID used (`qwen3-14b` or chosen production model) | GO_LIVE_FINAL_CHECKLIST.md Item 10 evidence table |

---

## 7. Only then mark 100%

Update `docs/GO_LIVE_FINAL_CHECKLIST.md`:

- Item 5 full-golden pass = checked
- Item 10 staging/evidence = checked
- Final sign-off filled (lead + locale owner + eng)

---

## 8. Hard rules for "do it right"

- **No claiming done from scaffold/status alone.**
- **No "smoke only" as final proof.**
- **No parallel runs beyond host capacity.**
- **No doc sign-off without URLs/artifacts.**

---

## Quick reference: what's done vs what's pending

### Done (fixtures and scaffolding)

- 24/24 golden sample fixtures present
- Content-type registry/matrix complete
- Smoke regression gate passed
- All scripts created and syntax-verified
- `run_locale_batches.py`, `locale_max_agents.yml` in place

### Still pending (blocking 100%)

- Full translation generation + validation pass for all 6 CJK locales
- Full golden regression pass (not smoke) — all 24 samples green
- Staging + evidence/sign-off (Item 10)

### To complete it

```bash
cd /Users/ahjan/phoenix_omega/Qwen-Agent

# Content generation (needs LM Studio running)
python3 scripts/localization/run_locale_batches.py --max-agents 6

# Validation (second command must exit clean)
python3 scripts/localization/validate_translations.py --all-locales --report
```

When that second command exits clean, all-language content generation is complete. Then proceed to steps 4-7 above.
