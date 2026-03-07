# GO-LIVE FINAL CHECKLIST — Qwen-Only Audiobook Pipeline

> **Purpose**: Sign-off gate before any locale goes to production.
> All items must be ✅ before first production run. No exceptions.
>
> **Owner**: Audiobook pipeline lead
> **Last updated**: 2026-03-06
> **Schema version in play**: `comparator_result_v2.schema.json` v2.0

---

## Pre-conditions (must be true before checklist opens)

- [ ] `config/audiobook_script/static_polish_rubric.yaml` present and valid YAML
- [ ] `config/audiobook_script/comparator_config.yaml` present, `max_loops` in [1,5]
- [ ] `config/audiobook_script/comparison_checklist_v2.yaml` present, `checklist_version: "2.0.0"`
- [ ] `schemas/comparator_result_v2.schema.json` present, `"version": "2.0"`
- [ ] `scripts/audiobook_script/run_comparator_loop.py` present and importable

---

## Item 1 — LM Studio API Wired ✅

| Sub-item | Status | Sign-off |
|----------|--------|----------|
| `_call_qwen_draft()` wired to LM Studio (`http://127.0.0.1:1234/v1`) | ✅ | done |
| `_call_qwen_judge()` wired to LM Studio (`http://127.0.0.1:1234/v1`) | ✅ | done |
| Both functions return valid JSON matching schema v2.0 | ✅ | done |
| Timeout / retry logic present (≥ 2 retries, exp backoff) | ✅ | done |

**Notes**: _______________________

---

## Item 2 — Prompt Files Present ✅

| Sub-item | Status | Sign-off |
|----------|--------|----------|
| Prompt files in `prompts/audiobook/`: draft_pearl_prime_v2.txt, draft_pearl_news_v2.txt, draft_phoenix_v4_v2.txt, draft_teacher_mode_v2.txt | ✅ | done |
| `prompts/audiobook/judge_audiobook_v2.txt` present | ✅ | done |
| All draft prompts reference `rubric_ref: static_polish_rubric` | ✅ | done |
| Judge prompt includes all 9 gates with JSON schema examples | ✅ | done |
| All 5 prompts reviewed by locale owner | ☐ | ________ |

**Notes**: _______________________

---

## Item 3 — Safety Caps Confirmed

| Sub-item | Status | Sign-off |
|----------|--------|----------|
| `max_loops` = 3 in `comparator_config.yaml` (default) | ✅ | verified 2026-03-06 |
| `max_parallel_sections` ≤ 6 | ✅ | verified 2026-03-06 |
| `max_parallel_books` ≤ 2 | ✅ | verified 2026-03-06 |
| Max simultaneous API calls confirmed ≤ 24 (2×6×2) | ✅ | verified 2026-03-06 |
| Schema startup validation fires on `max_loops` out-of-range | ✅ | line 79 run_comparator_loop.py |
| Loop-exhaustion routes to `manual_review` (never auto-pass) | ✅ | hard_fail_routes_to: manual_review |

**Notes**: All values confirmed programmatically against comparator_config.yaml + run_comparator_loop.py source.

---

## Item 4 — Judge Quality Gates

| Gate ID | Type | Threshold | Status | Sign-off |
|---------|------|-----------|--------|----------|
| `semantic_fidelity` | HARD | pass=true | ☐ | ________ |
| `claim_integrity` | HARD | pass=true | ☐ | ________ |
| `psychological_safety` | HARD | pass=true | ☐ | ________ |
| `tts_readability_cadence` | HARD | pass=true | ☐ | ________ |
| `compliance_disclaimer_preservation` | HARD | pass=true | ☐ | ________ |
| `emotional_arc_alignment` | SCORED | w=2.0 | ☐ | ________ |
| `native_regional_language_fit` | SCORED | w=2.5 | ☐ | ________ |
| `narrative_flow_cohesion` | SCORED | w=1.5 | ☐ | ________ |
| `polish_emotional_impact` | SCORED | w=2.0 | ☐ | ________ |
| Aggregate pass threshold ≥ 0.75 (scored_total/max_scored) | ☐ | ________ |
| Schema validation fires every loop | ☐ | ________ |
| Schema version mismatch routes to `manual_review` | ☐ | ________ |
| Judge model committed in config (`judge_model.model_id`) | ☐ | ________ |
| Judge temperature = 0.1 | ☐ | ________ |
| Judge seed rotation = `hash(section_id + loop_index + SALT)` | ☐ | ________ |

**Notes**: _______________________

### Per-Gate Operator Runbook

| Gate | Most Common Failure | Operator Action |
|------|---------------------|-----------------|
| `semantic_fidelity` | Key claims lost in translation | Compare TL against source paragraph-by-paragraph |
| `claim_integrity` | Statistics reworded or invented | Re-prompt with strict "do not restate statistics" instruction |
| `psychological_safety` | Graphic distress amplified | Tone-down rubric rule psy_p3 weight increase |
| `tts_readability_cadence` | Long run-on sentences, missing pauses | Check tts_c1–c5 rubric rules; shorten sentences |
| `compliance_disclaimer_preservation` | Disclaimer omitted or paraphrased | Lock disclaimer block as verbatim injection |
| `emotional_arc_alignment` | Flat emotional beat, no arc | Increase polish rubric psy_p1–p2 signal in patch |
| `native_regional_language_fit` | Formal Mandarin in casual HK market | Check locale_overrides in checklist; adjust regional rules |
| `narrative_flow_cohesion` | Choppy transitions | Review flow_f1–f4 rubric rules in patch context |
| `polish_emotional_impact` | Clinical, dry tone | Add comp_c1 polish instruction to next loop patch |

---

## Item 5 — Golden Regression Set ✅

| Sub-item | Status | Sign-off |
|----------|--------|----------|
| `config/audiobook_script/golden_regression_set/` exists | ✅ | done |
| zh-TW golden sample present (`zh-TW_pearl_prime_intro.yaml`) | ✅ | done |
| zh-HK golden sample present (`zh-HK_pearl_news_youth.yaml`) | ✅ | done |
| zh-SG golden sample present (`zh-SG_teacher_mode_exercise.yaml`) | ✅ | done |
| zh-CN golden sample present (`zh-CN_phoenix_v4_spiral.yaml`) | ✅ | done |
| `scripts/audiobook_script/run_regression.py` present | ✅ | done |
| Regression run passes all 4 locales | ☐ | needs first run |
| Regression results committed to repo as evidence | ☐ | after first run |

**Notes**: _______________________

---

## Item 6 — Observability + PhoenixControl UI ✅

| Sub-item | Status | Sign-off |
|----------|--------|----------|
| `artifacts/audiobook/manual_review_queue.json` path confirmed | ✅ | done |
| Queue sorted by `hard_gate_failures` descending | ✅ | done |
| PhoenixControl "Manual Review" tab reads queue file | ✅ | done |
| Tab visible in sidebar with orange/red badge count | ✅ | done |
| Each entry shows: section_id, locale, hard_gate_failures, aggregate_score, artifact path | ✅ | done |
| Artifact trace writes to `artifacts/audiobook/<book_id>/<locale>/<section_id>/` | ✅ | done |
| All packet files written after run | ✅ | done |
| Prometheus-compatible metrics endpoint (if applicable) | ☐ | ________ |

**Notes**: _______________________

---

## Item 7 — CI Integration

| Sub-item | Status | Sign-off |
|----------|--------|----------|
| GitHub Actions workflow for audiobook pipeline present | ✅ | .github/workflows/audiobook-regression.yml |
| Regression gate blocks merge on failure | ✅ | path-filtered on audiobook files, blocks on schema-and-config job |
| Schema validation in CI (not just runtime) | ✅ | job 1 validates config + checklist + schema + prompts + golden set |
| DOCS_INDEX governance check passes | ☐ | run after next docs-ci push |

**Notes**: CI workflow created 2026-03-06. Job 1 (schema-and-config) runs on ubuntu-latest, no LM Studio. Job 2 (golden-regression) self-hosted, manual dispatch only.

---

## Item 8 — Secrets / LM Studio ✅

| Sub-item | Status | Sign-off |
|----------|--------|----------|
| LM Studio running at `http://127.0.0.1:1234` (no API key needed) | ✅ | Dashscope dropped |
| Draft + judge both use LM Studio local endpoint | ✅ | Dashscope dropped |
| LM Studio model loaded and responding | ☐ | verify before each run |
| LM Studio model ID documented in comparator_config.yaml | ☐ | update when model changes |

**Notes**: _______________________

---

## Item 9 — Operator Docs ✅

| Sub-item | Status | Sign-off |
|----------|--------|----------|
| `docs/audiobook_operator_runbook.md` present | ✅ | done |
| `scripts/release/audiobook_rollback.sh` present | ✅ | done |
| DOCS_INDEX entry for pipeline present | ✅ | done |
| AUDIOBOOK_PIPELINE_SPEC.md present | ✅ | done |
| GO_LIVE_FINAL_CHECKLIST.md present (this file) | ✅ | done |

**Notes**: _______________________

---

## Item 10 — Staging Run + Evidence Pack

| Sub-item | Status | Sign-off |
|----------|--------|----------|
| Full pipeline run on staging environment (not prod) | ☐ | ________ |
| At least 1 book, all 4 required locales | ☐ | ________ |
| No sections routed to `manual_review` unexpectedly | ☐ | ________ |
| `manual_review_queue.json` reviewed and cleared | ☐ | ________ |
| Artifacts reviewed by locale owner | ☐ | ________ |
| Evidence pack (screenshots, log snippets) committed | ☐ | ________ |
| Final sign-off below | ☐ | ________ |

**Notes**: _______________________

---

## Final Sign-off

> All 10 items above ✅ before this block is signed.

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Pipeline lead | | | |
| Locale owner (zh-TW/HK/SG/CN) | | | |
| Engineering lead | | | |

---

## Design Decisions — Locked

The following are not open for re-discussion at go-live. They are committed design
decisions documented in `docs/AUDIOBOOK_PIPELINE_SPEC.md`.

| Decision | Committed Value | Rationale |
|----------|----------------|-----------|
| No human in repair loop | Fully automated PatchApplier | Speed + consistency at scale |
| TTS readability = HARD gate | `tts_readability_cadence` hard=true | Unlistenable audio is unshippable |
| Loop exhaustion routing | `manual_review` (never auto-pass) | Safety-first; no silent quality degradation |
| Schema mismatch routing | `manual_review` (never silent pass) | Version drift is a production hazard |
| Judge temperature | 0.1 | Near-deterministic; consistent gate decisions |
| Aggregate pass threshold | 0.75 | Balanced quality floor; locale-overridable |
| Patch injection strategy | `append_to_system` (hard first, scored by weight desc) | Hard patches always preserved on overflow |
| Parallel cap | 2 books × 6 sections = 12 concurrent sections, ×2 = 24 API calls | API rate limit headroom |
| Manual review visibility | Sorted by `hard_gate_failures` desc in PhoenixControl tab | Most broken first = fastest triage |
