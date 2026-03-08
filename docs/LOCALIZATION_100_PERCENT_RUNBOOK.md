# LOCALIZATION 100% RUNBOOK

> **Purpose**: Step-by-step procedure to take audiobook localization from "scaffolded" to "production-proven".
> **Prerequisite**: LM Studio running at `http://127.0.0.1:1234` with `qwen3-14b` loaded.
> **Do not skip steps. Do not claim done from scaffold/status alone.**

---

## 1. Freeze and sync

Pull latest `main`. Stop all parallel dev edits on audiobook/localization until this run finishes. Keep one runner job at a time.

Before long runs, ensure runner watchdog is installed:

```bash
chmod +x scripts/runner/*.sh
scripts/runner/install_watchdog_launchd.sh
```

---

## 2. Run timeout-safe sharded generation (content fill)

Use the GitHub workflow `locale_max_agents.yml` (or the same script locally). It is now hardened:
- sharding by locale + topic
- per-topic hard timeout
- heartbeat progress logs
- LM Studio lock (light/medium/heavy) to avoid contention

**Safe defaults** (recommended):
- `locale_set=core`
- `max_agents=2`
- `timeout_sec=180`
- `mode=translate+validate`

---

## 3. Mandatory command sequence

1. GitHub Actions → **Locale max-agents run** (`workflow_dispatch`)
2. Run first probe:
   - `locale_set=core`
   - `max_agents=1`
   - `topics=climate`
   - `mode=translate+validate`
   - `timeout_sec=180`
3. If green, run full core:
   - `locale_set=core`
   - `max_agents=2`
   - `topics=` (blank = all 7)
   - `mode=translate+validate`
   - `timeout_sec=180`
4. Optional expansion to all locales:
   - `locale_set=all`
   - `max_agents=2`
   - `mode=translate+validate`
   - `timeout_sec=180` (raise to 240 only if needed)

---

## 4. Regression in two phases (required)

```bash
# Phase 1: gate health (fast, should pass)
python3 scripts/audiobook_script/run_regression.py --smoke --verbose

# Phase 2: full quality proof (must run for 100%)
# use locale-sharded full-golden workflow runs (#12–#17 evidence accepted)
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
- **If runner disconnects, follow `/Users/ahjan/phoenix_omega/Qwen-Agent/docs/RUNNER_TRIAGE_ONE_PAGER.md` before re-running.**
- **Localization heavy jobs are window-gated (UTC): 15:00–23:00.**

---

## Quick reference: what's done vs what's pending

### Done (fixtures + hardened runtime)

- 24/24 golden sample fixtures present
- Content-type registry/matrix complete
- Smoke regression gate passed
- All scripts created and syntax-verified
- `run_locale_batches.py`, `locale_max_agents.yml` hardened:
  - locale+topic sharding
  - per-topic timeout
  - heartbeat progress
  - LM Studio lock compatibility

### Still pending (blocking 100% sign-off)

- Any missing evidence rows in `GO_LIVE_FINAL_CHECKLIST.md` Item 10
- Final sign-off block completion (owners + dates)

### To complete it

When `locale_max_agents.yml` full-core run is green and Item 10 evidence is complete, localization is production-proven.
