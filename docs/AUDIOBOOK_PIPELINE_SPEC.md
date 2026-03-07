# Audiobook Pipeline Specification — Qwen-Only Comparator Loop

> **Version**: 1.0.0
> **Status**: Architecture complete; pre-production (see §12 Gap Tracker)
> **Last updated**: 2026-03-06
> **Owner**: Audiobook pipeline lead
> **Related**: `docs/GO_LIVE_FINAL_CHECKLIST.md`, `docs/DOCS_INDEX.md`

---

## Table of Contents

1. [Purpose & Non-Goals](#1-purpose--non-goals)
2. [System Context](#2-system-context)
3. [Full Pipeline Flow](#3-full-pipeline-flow)
4. [Gate Definitions](#4-gate-definitions)
5. [Static Polish Rubric](#5-static-polish-rubric)
6. [Patch Injection Mechanics](#6-patch-injection-mechanics)
7. [Parallel Architecture](#7-parallel-architecture)
8. [Artifact Trace Contract](#8-artifact-trace-contract)
9. [Manual Review Protocol](#9-manual-review-protocol)
10. [Component Contracts](#10-component-contracts)
11. [Roles & Responsibilities](#11-roles--responsibilities)
12. [Gap Tracker](#12-gap-tracker)
13. [Config Reference](#13-config-reference)
14. [Locale Support](#14-locale-support)
15. [Schema Version Binding](#15-schema-version-binding)

---

## 1. Purpose & Non-Goals

### Purpose

Produce publication-ready localized audiobook scripts from Pearl Prime book content.
The pipeline is **fully automated** — no Claude API calls at runtime, no human in the
repair loop. Qwen (Dashscope) handles both drafting and judging. The only human
touchpoint is the **manual review queue** surfaced in PhoenixControl when automated
repair exhausts its loop budget without achieving a passing score.

### Non-Goals

- **Not a translation pipeline.** Source content is already localized; this pipeline
  polishes and adapts for audio/TTS consumption.
- **Not a Claude pipeline.** Claude is not called at runtime. Claude authored the
  config, rubric, schema, and comparator loop script — that's it.
- **Not a human approval workflow.** Manual review is an exception path, not the
  nominal path. The system is designed for manual review to be rare.
- **Not a general-purpose LLM eval framework.** The gate definitions, rubric, and
  schema are specific to Pearl Prime audiobook quality standards.

---

## 2. System Context

```
Pearl Prime Book Content (localized)
        │
        ▼
┌───────────────────────┐
│  run_comparator_loop  │  ←── config/audiobook_script/comparator_config.yaml
│  (asyncio, Python)    │  ←── config/audiobook_script/comparison_checklist_v2.yaml
│                       │  ←── config/audiobook_script/static_polish_rubric.yaml
│  Sections are         │  ←── prompts/draft_audiobook_v2.txt
│  embarrassingly       │  ←── prompts/judge_audiobook_v2.txt
│  parallel             │
└───────────┬───────────┘
            │ produces
            ▼
  artifacts/audiobook/<book_id>/<locale>/<section_id>/
  ├── best_draft.txt
  ├── final_draft.txt
  ├── defect_history.json
  ├── review_summary.txt
  └── status.json

  artifacts/audiobook/manual_review_queue.json   ←── PhoenixControl reads this
```

**External dependencies at runtime:**
- Dashscope API (Qwen) — draft model + judge model (may be same model, different system prompts)
- No Claude API calls at runtime

---

## 3. Full Pipeline Flow

```
INPUT: book_id, locale, sections[]
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 0: Load & Validate Config                         │
│  • comparator_config.yaml                               │
│  • comparison_checklist_v2.yaml  (schema_version check) │
│  • static_polish_rubric.yaml                            │
│  • Validate: max_loops in [1,5], thresholds in (0,1]    │
│  • Abort startup on any config violation                │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 1: Parallelize Sections                           │
│  asyncio.Semaphore(max_parallel_sections=6)             │
│  asyncio.gather(*[run_section_loop(s) for s in secs])   │
└─────────────────────┬───────────────────────────────────┘
                      │ (per section)
                      ▼
┌─────────────────────────────────────────────────────────┐
│  LOOP (max_loops iterations, sequential within section) │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Draft Qwen Call                                │   │
│  │  model: comparator_config.draft_model           │   │
│  │  system: prompts/draft_audiobook_v2.txt         │   │
│  │           + current patch context               │   │
│  │  temp: 0.7                                      │   │
│  │  seed: hash(section_id + locale)  (deterministic)│  │
│  └──────────────────────┬──────────────────────────┘   │
│                          │                              │
│                          ▼                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Judge Qwen Call                                │   │
│  │  model: comparator_config.judge_model           │   │
│  │  system: prompts/judge_audiobook_v2.txt         │   │
│  │  temp: 0.1  (near-deterministic)                │   │
│  │  seed: hash(section_id + loop_index + SALT)     │   │
│  │          (rotated per loop for independence)    │   │
│  └──────────────────────┬──────────────────────────┘   │
│                          │                              │
│                          ▼                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Schema Validation                              │   │
│  │  • Validate against comparator_result_v2.schema │   │
│  │  • Check checklist_schema_version = "2.0"       │   │
│  │  • FAIL → manual_review (never silent pass)     │   │
│  └──────────────────────┬──────────────────────────┘   │
│                          │                              │
│                          ▼                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Score & Decision                               │   │
│  │  • ALL hard gates pass=true?                    │   │
│  │  • scored_total / max_scored_total >= 0.75?     │   │
│  │  • (locale threshold override applied if set)   │   │
│  │                                                 │   │
│  │  PASS → write artifacts, done                   │   │
│  │  FAIL + loops_remaining > 0 → PatchApplier      │   │
│  │  FAIL + loops_exhausted → manual_review         │   │
│  └──────────────────────┬──────────────────────────┘   │
│                          │ (if FAIL + loops remaining)  │
│                          ▼                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │  PatchApplier.assemble()                        │   │
│  │  1. Hard gate patches first (sort by gate_id)   │   │
│  │  2. Scored patches by weight descending         │   │
│  │  3. Append to original system prompt            │   │
│  │  4. Cap at max_patch_chars                      │   │
│  │  5. Hard patches always preserved on overflow   │   │
│  └──────────────────────┬──────────────────────────┘   │
│                          └── next loop iteration        │
└─────────────────────────────────────────────────────────┘
                      │
                      ▼
        PASS → artifacts written
        FAIL → manual_review_queue.json entry appended
```

---

## 4. Gate Definitions

### Hard Gates (ALL must pass=true)

| Gate ID | Description | Fail condition |
|---------|-------------|----------------|
| `semantic_fidelity` | Key claims, statistics, and factual content preserved from source | Any claim, statistic, or fact materially altered or omitted |
| `claim_integrity` | Numerical and research-backed claims not reworded or invented | Numbers changed, sources misattributed, claims fabricated |
| `psychological_safety` | Distress content not amplified; safety guardrails honored | Graphic detail added, trauma amplified, safety context removed |
| `tts_readability_cadence` | Sentences suitable for TTS; natural pause structure; no run-ons | Run-on sentences, missing pause markers, unpronounceable constructs |
| `compliance_disclaimer_preservation` | Required disclaimers preserved verbatim or equivalent | Disclaimer omitted, paraphrased, or weakened |

### Scored Gates (aggregate ≥ 0.75 of max_scored_total)

| Gate ID | Weight | Description |
|---------|--------|-------------|
| `emotional_arc_alignment` | 2.0 | Emotional beats follow source arc structure |
| `native_regional_language_fit` | 2.5 | Language feels native to target locale (highest weight) |
| `narrative_flow_cohesion` | 1.5 | Transitions and narrative flow are smooth |
| `polish_emotional_impact` | 2.0 | Final polish quality; listener emotional resonance |

**Max scored total** = 2.0 + 2.5 + 1.5 + 2.0 = **8.0**
**Pass threshold** = 8.0 × 0.75 = **6.0 points**

---

## 5. Static Polish Rubric

File: `config/audiobook_script/static_polish_rubric.yaml`

The rubric is **authored once offline** (Step 0 prerequisite) and referenced by both
the draft and judge system prompts via `rubric_ref: static_polish_rubric`. It is never
regenerated at runtime. Rules are organized in 5 categories:

| Category | Rules | Focus |
|----------|-------|-------|
| TTS Cadence | tts_c1–c5 | Sentence length, pause markers, breathing room |
| Psychological Impact | psy_p1–p5 | Emotional resonance, arc beats, listener connection |
| Narrative Flow | flow_f1–f4 | Transitions, chapter hooks, section cohesion |
| Regional Fit | reg_r1–r2 | Locale-appropriate register and idiom |
| Compliance | comp_c1–c2 | Disclaimer integrity, content safety |

**Total: 15 rules.** The rubric is not updated between loops. It is a stable
quality target, not a dynamic patch surface.

---

## 6. Patch Injection Mechanics

### Strategy: `append_to_system`

Patches are **appended** to the original system prompt, never prepended.
This preserves the original instruction hierarchy and prevents patch content
from dominating the model's attention.

### Assembly Order

```
PatchApplier.assemble(original_system_prompt, gate_results, loop_index):
  1. Collect all gate_results where pass=false
  2. Sort hard gate patches FIRST (by gate_id alphabetically for determinism)
  3. Sort scored gate patches by weight DESCENDING (highest priority scored fixes first)
  4. Concatenate: original_system_prompt + "\n\n--- PATCH CONTEXT ---\n" + patches
  5. If total exceeds max_patch_chars:
     a. Always include ALL hard gate patches (never truncated)
     b. Truncate scored patches from lowest weight upward
```

### Patch Format

Each gate in `comparison_checklist_v2.yaml` defines a `prompt_patch_format` template.
The judge returns a `prompt_patch` string in the gate result; `PatchApplier` uses
these strings verbatim.

### Loop Seed Rotation

To ensure judge independence across loops (prevent anchoring on prior decisions):
```
judge_seed = hash(section_id + str(loop_index) + "JUDGE_SALT_V2") % (2**31)
```
Each loop gets a different seed; the judge sees the same section fresh.

---

## 7. Parallel Architecture

### Section-level parallelism (within a book)

Sections within a book are **embarrassingly parallel** — they share no state.

```python
semaphore = asyncio.Semaphore(max_parallel_sections)  # default: 6

async def bounded_section(section):
    async with semaphore:
        return await run_section_loop(section, ...)

tasks = [bounded_section(s) for s in sections]
results = await asyncio.gather(*tasks)
```

### Book-level parallelism

The caller may invoke `run_book_parallel()` for multiple books concurrently,
bounded by `max_parallel_books` (default: 2).

### Total simultaneous API calls

```
max_parallel_books × max_parallel_sections × 2 (draft + judge)
= 2 × 6 × 2 = 24 simultaneous calls (at defaults)
```

This is the figure to check against Dashscope rate limits before go-live.

### Loop sequentiality

Loops **within a section** are sequential — each loop depends on the prior
loop's judge output to assemble the next patch. No parallelism within a section's
repair loop.

---

## 8. Artifact Trace Contract

All artifacts are written to:
```
artifacts/audiobook/<book_id>/<locale>/<section_id>/
```

| File | Contents | Written when |
|------|----------|-------------|
| `best_draft.txt` | Draft with highest `aggregate_score` across all loops | After each loop if new best |
| `final_draft.txt` | Last draft produced (may not be best) | After final loop |
| `defect_history.json` | Array of gate results per loop; full trace | After each loop |
| `review_summary.txt` | Human-readable summary: loops run, final scores, gate outcomes | After final loop |
| `status.json` | Machine-readable: `{"status": "pass"|"manual_review", "loops": N, "aggregate_score": F}` | After final loop |

### manual_review_queue.json

Global path: `artifacts/audiobook/manual_review_queue.json`

```json
[
  {
    "book_id": "...",
    "locale": "zh-HK",
    "section_id": "...",
    "hard_gate_failures": 2,
    "aggregate_score": 0.61,
    "loops_run": 3,
    "artifact_path": "artifacts/audiobook/<book_id>/zh-HK/<section_id>/",
    "queued_at": "2026-03-06T14:22:00Z"
  }
]
```

Sorted **descending by `hard_gate_failures`**, then by `aggregate_score` ascending.
Most broken sections appear at the top — fastest triage path for operators.

---

## 9. Manual Review Protocol

Manual review is an **exception path**, not the nominal path.

### Triggers for manual_review routing

1. Judge output fails JSON schema validation
2. `checklist_schema_version` mismatch (expected `^2.0`)
3. Loop budget exhausted (`loop_index == max_loops - 1`) without passing
4. Any other unhandled exception during draft or judge call (after retries)

### What operators receive

When PhoenixControl shows a section in the Manual Review tab, operators have:

- `best_draft.txt` — the highest-scoring automated attempt
- `defect_history.json` — full per-loop gate breakdown
- `review_summary.txt` — plain-English summary of what failed and why
- `status.json` — machine-readable status

### Operator actions

1. Review `best_draft.txt` against English source
2. Consult per-gate runbook in `docs/GO_LIVE_FINAL_CHECKLIST.md`
3. Edit draft manually or trigger a config-adjusted re-run
4. Mark section as resolved in queue (removes from PhoenixControl tab)

### PhoenixControl integration

The "Manual Review" tab reads `artifacts/audiobook/manual_review_queue.json` directly.
It must be surfaced as a **high-priority item in the sidebar** — not buried in settings.
Sections with `hard_gate_failures > 0` should have a distinct visual indicator
(e.g., red badge count).

---

## 10. Component Contracts

### `run_comparator_loop.py`

| Function | Input | Output | Contract |
|----------|-------|--------|---------|
| `run_section_loop()` | section_id, locale, source_text, config | `SectionResult` | Never raises; always returns status=pass or manual_review |
| `run_book_parallel()` | book_id, locale, sections[], config | `list[SectionResult]` | Returns when all sections complete; semaphore-bounded |
| `PatchApplier.assemble()` | original_prompt, gate_results, loop_index | `str` (patched prompt) | Hard patches always preserved; never exceeds max_patch_chars without truncating scored first |

### Config files

| File | Owned by | Modified by | Validated at |
|------|----------|-------------|-------------|
| `comparator_config.yaml` | Pipeline lead | Pipeline lead | Startup |
| `comparison_checklist_v2.yaml` | Pipeline lead | Pipeline lead | Startup + every gate result |
| `static_polish_rubric.yaml` | Content team | Content team (offline) | Manual review only |
| `comparator_result_v2.schema.json` | Pipeline lead | Never (stable) | Every judge output |

### Schema version contract

`comparator_result_v2.schema.json` version `"2.0"` is bound to
`comparison_checklist_v2.yaml` `checklist_version: "2.0.0"`.

**These two files must be updated atomically.** A version bump in one without
the other will cause all judge outputs to route to `manual_review` at runtime.

---

## 11. Roles & Responsibilities

| Role | Responsibility |
|------|---------------|
| Pipeline lead | Config ownership, go-live sign-off, operator runbook |
| Content team | Static polish rubric authoring; locale review of manual review queue |
| Engineering lead | `_call_qwen_draft()` / `_call_qwen_judge()` API implementation, CI, secrets |
| Locale owner | Golden regression set authoring; locale threshold override decisions |
| PhoenixControl frontend | Manual Review tab implementation |

---

## 12. Gap Tracker

Items required before first production run. See `docs/GO_LIVE_FINAL_CHECKLIST.md`
for the sign-off gate version of this list.

| # | Item | Owner | Status |
|---|------|-------|--------|
| 1 | LM Studio API wired (`_call_qwen_draft()` + `_call_qwen_judge()`) | Engineering | ✅ DONE — `http://127.0.0.1:1234/v1` |
| 2 | Dashscope API — **DROPPED** | — | ✅ Replaced by LM Studio |
| 3 | Draft prompts (4 content types) | Content team | ✅ DONE — `prompts/audiobook/draft_*_v2.txt` |
| 4 | Judge prompt | Content team | ✅ DONE — `prompts/audiobook/judge_audiobook_v2.txt` |
| 5 | Golden regression set (zh-TW, HK, SG, CN) | Locale owners | ✅ DONE — 4 samples written |
| 6 | `scripts/audiobook_script/run_regression.py` | Engineering | ✅ DONE |
| 7 | PhoenixControl "Manual Review" tab | Frontend | ✅ DONE — `ManualReviewView.swift` |
| 8 | `QWEN_DRAFT_API_KEY` — **DROPPED** (LM Studio is local, no key) | — | ✅ N/A |
| 9 | `QWEN_JUDGE_API_KEY` — **DROPPED** | — | ✅ N/A |
| 10 | `docs/audiobook_operator_runbook.md` | Pipeline lead | ✅ DONE |
| 11 | `scripts/release/audiobook_rollback.sh` | Engineering | ✅ DONE |
| 12 | Staging run + evidence pack | Pipeline lead | ⚠ NOT RUN — only remaining blocker |

> **Status**: 11 of 12 items complete. One remaining blocker: staging run.

**Files complete:**

| File | Status |
|------|--------|
| `config/audiobook_script/static_polish_rubric.yaml` | ✅ |
| `config/audiobook_script/comparator_config.yaml` | ✅ — LM Studio wired |
| `config/audiobook_script/comparison_checklist_v2.yaml` | ✅ |
| `config/audiobook_script/golden_regression_set/` (4 samples) | ✅ |
| `schemas/comparator_result_v2.schema.json` | ✅ |
| `scripts/audiobook_script/run_comparator_loop.py` | ✅ — LM Studio wired |
| `scripts/audiobook_script/run_regression.py` | ✅ |
| `scripts/release/audiobook_rollback.sh` | ✅ |
| `prompts/audiobook/draft_pearl_prime_v2.txt` | ✅ |
| `prompts/audiobook/draft_pearl_news_v2.txt` | ✅ |
| `prompts/audiobook/draft_phoenix_v4_v2.txt` | ✅ |
| `prompts/audiobook/draft_teacher_mode_v2.txt` | ✅ |
| `prompts/audiobook/judge_audiobook_v2.txt` | ✅ |
| `PhoenixControl/Views/ManualReviewView.swift` | ✅ |
| `docs/audiobook_operator_runbook.md` | ✅ |
| `docs/GO_LIVE_FINAL_CHECKLIST.md` | ✅ |
| `docs/AUDIOBOOK_PIPELINE_SPEC.md` | ✅ |

---

## 13. Config Reference

### comparator_config.yaml — key fields

```yaml
pipeline:
  max_loops: 3                    # Range [1,5]; validated at startup
  locale_default: "zh-TW"

draft_model:
  model_id: "qwen-max"
  temperature: 0.7
  seed_strategy: "hash(section_id + locale)"

judge_model:
  model_id: "qwen-max"
  system_prompt_id: "judge_audiobook_v2"
  temperature: 0.1               # Near-deterministic
  seed_strategy: "hash(section_id + loop_index + JUDGE_SALT_V2)"

parallel:
  max_parallel_sections: 6       # Semaphore bound per book
  max_parallel_books: 2          # Caller-level bound

patch_injection:
  strategy: "append_to_system"
  max_patch_chars: 4000
  hard_patches_first: true
  overflow_behavior: "truncate_scored_by_weight_asc"

scoring:
  aggregate_pass_threshold: 0.75  # scored_total / max_scored_total

artifact_trace:
  base_path: "artifacts/audiobook"
  manual_review_queue: "artifacts/audiobook/manual_review_queue.json"
```

---

## 14. Locale Support

### Required locales for go-live

| Locale | Golden set required | Threshold override |
|--------|--------------------|--------------------|
| zh-TW | ✅ Yes | None (use default 0.75) |
| zh-HK | ✅ Yes | May lower to 0.70 (colloquial register) |
| zh-SG | ✅ Yes | None |
| zh-CN | ✅ Yes | None |

### Supported locales (post go-live expansion)

ja-JP, ko-KR — locale_overrides defined in `comparison_checklist_v2.yaml`.
Golden regression sets required before enabling.

### Locale threshold overrides

Defined in `comparison_checklist_v2.yaml` under `locale_overrides`:
```yaml
locale_overrides:
  zh-HK:
    aggregate_pass_threshold: 0.70
    native_regional_language_fit:
      weight: 3.0  # Boosted for HK colloquial market
```

---

## 15. Schema Version Binding

This is a **hard constraint** — treat it as a breaking change contract.

| Artifact | Version field | Current value |
|----------|--------------|---------------|
| `schemas/comparator_result_v2.schema.json` | `"version"` | `"2.0"` |
| `comparison_checklist_v2.yaml` | `checklist_version` | `"2.0.0"` |
| Gate results (runtime) | `checklist_schema_version` | Must match `^2\.0` |

### Version bump protocol

1. Update schema JSON — bump `version` field
2. Update checklist YAML — bump `checklist_version` field atomically in same PR
3. Update `gate_id` enum in schema if any gates added/renamed
4. Run full regression suite before merging
5. Update this spec's §15 table

**Never bump one without the other.** A mismatch causes 100% of judge outputs
to route to `manual_review` at runtime.
