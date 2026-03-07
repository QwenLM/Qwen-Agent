# Audiobook Pipeline — Operator Runbook

> **Audience**: Pipeline operators and content leads who manage the PhoenixControl
> Manual Review queue. Engineering-level knowledge is NOT required.
> **LM Studio endpoint**: `http://127.0.0.1:1234` (must be running with Qwen model loaded)
> **Last updated**: 2026-03-06
> **Related**: `docs/AUDIOBOOK_PIPELINE_SPEC.md`, `docs/GO_LIVE_FINAL_CHECKLIST.md`

---

## Table of Contents

1. [Quick-start checklist](#1-quick-start-checklist)
2. [How the pipeline works (one-page version)](#2-how-the-pipeline-works-one-page-version)
3. [Per-gate triage guide](#3-per-gate-triage-guide)
4. [Working the Manual Review queue in PhoenixControl](#4-working-the-manual-review-queue-in-phoenixcontrol)
5. [How to re-run a section](#5-how-to-re-run-a-section)
6. [How to re-run the full book](#6-how-to-re-run-the-full-book)
7. [Config changes operators can safely make](#7-config-changes-operators-can-safely-make)
8. [Signs something is wrong (and what to do)](#8-signs-something-is-wrong-and-what-to-do)
9. [Escalation path](#9-escalation-path)

---

## 1. Quick-start checklist

Before running the pipeline:

- [ ] LM Studio is running with Qwen model loaded (`http://127.0.0.1:1234` responding)
- [ ] Prompt files present: `prompts/audiobook/draft_{content_type}_v2.txt` and `prompts/audiobook/judge_audiobook_v2.txt`
- [ ] Source content file(s) prepared in `artifacts/audiobook/source/`
- [ ] Locale confirmed (zh-TW, zh-HK, zh-SG, zh-CN, ja-JP, or ko-KR)
- [ ] Content type confirmed (pearl_prime, pearl_news, phoenix_v4, or teacher_mode)

Run a dry-run to verify setup:
```bash
python scripts/audiobook_script/run_comparator_loop.py \
  --batch-id test --locale zh-TW --dry-run
```

---

## 2. How the pipeline works (one-page version)

1. **You provide**: a source section (English text), a locale, a content type, and a book ID
2. **Draft**: Qwen writes a localized audiobook script using the appropriate draft prompt
3. **Judge**: A second Qwen call evaluates the draft against 9 quality gates
4. **Decision**: If all hard gates pass AND the scored aggregate ≥ 0.75 → **section passes**
5. **Repair**: If not, the judge's feedback is automatically injected into the next draft attempt
6. **Max loops**: After 3 loops (config default), if still failing → section goes to **manual review**
7. **Manual review**: You see it in PhoenixControl → Manual Review tab, sorted by severity

The pipeline writes these artifacts for every section:
```
artifacts/audiobook/<book_id>/<locale>/<section_id>/
├── best_draft.txt        ← highest-scoring automated attempt
├── final_draft.txt       ← last loop's output
├── defect_history.json   ← full judge verdicts per loop
├── review_summary.txt    ← plain-English summary of what failed
└── status.json           ← machine-readable: pass or manual_review
```

---

## 3. Per-gate triage guide

### Hard gates (ANY failure = section unshippable)

#### `semantic_fidelity` — Core content preserved

**What it means**: Key claims, research citations, and factual points must all be in the localized draft.

| Symptom | What to check | Fix direction |
|---------|---------------|---------------|
| Central argument of a paragraph is inverted | Compare source and draft paragraph-by-paragraph | Re-prompt: "Preserve the exact meaning of paragraph X — it was [source text]" |
| Named person or research is missing | Scan for all named entities in source | Add missing entity to patch instruction explicitly |
| TAKEAWAY or PIVOT content is omitted | Check TAKEAWAY and PIVOT slots specifically | Emphasize these in patch: "The TAKEAWAY in the original is [X] — it must appear in the script" |

#### `claim_integrity` — Statistics and numbers exact

**What it means**: Every number, percentage, date, and cited source must match the English original.

| Symptom | What to check | Fix direction |
|---------|---------------|---------------|
| Percentage changed (e.g., "13%" became "30%") | Compare all numbers in source vs draft | Add patch: "The statistic is exactly [X]% — do not approximate, round, or change this number" |
| Citation attributed to wrong source | Check all "according to [X]" clauses | Patch: "The citation '[stat]' is from [source] — keep this attribution exactly" |

#### `psychological_safety` — Distress not amplified

**What it means**: The adaptation must not add graphic detail, amplify trauma, or weaken safety disclaimers.

| Symptom | What to check | Fix direction |
|---------|---------------|---------------|
| Added graphic language not in source | Search for words in draft that don't appear in source | Patch: "Do not add any graphic or distressing detail beyond what is in the source" |
| Disclaimer weakened or removed | Check for disclaimer text in both versions | Patch: "The disclaimer '[verbatim text]' must appear word-for-word in the script" |

#### `tts_readability_cadence` — Speakable sentences

**What it means**: Every sentence must be spoken comfortably by TTS without run-ons.

| Symptom | What to check | Fix direction |
|---------|---------------|---------------|
| Run-on sentence (> 25 words without pause) | Count words between commas/periods | Patch: "Sentence starting '[X]' is too long — break it at '[natural clause boundary]'" |
| Em-dash mid-sentence | Search for "—" in draft | Patch: "Replace all em-dashes with commas or split into separate sentences" |
| Exercise instruction not imperative | Check EXERCISE atoms specifically | Patch: "Exercise instructions must use imperative present tense: 'Breathe in slowly. Hold for four counts.'" |

#### `compliance_disclaimer_preservation` — Disclaimers intact

**What it means**: Legal/safety disclaimers from the source must appear verbatim or functionally equivalent.

| Symptom | What to check | Fix direction |
|---------|---------------|---------------|
| Disclaimer missing from draft | Search for disclaimer text from source | Patch: "Include this disclaimer verbatim: '[full disclaimer text]'" |
| Disclaimer paraphrased in a way that weakens it | Compare disclaimer text exactly | Patch: "Use the exact words: '[verbatim disclaimer]' — do not paraphrase" |

---

### Scored gates (low score = try another loop; not unshippable alone)

#### `emotional_arc_alignment` (weight 2.0)

Low score means the emotional beats don't follow the source arc.
- Check PIVOT, TAKEAWAY, PERMISSION slots — are they landing with appropriate weight?
- Patch: "The PIVOT moment at [location] needs to feel like a shift — use shorter sentences, slower pace"

#### `native_regional_language_fit` (weight 2.5) — highest weight

Low score means the language feels translated, not native.
- This is the hardest gate to score well — requires genuine locale knowledge
- zh-HK: should feel like natural spoken Cantonese-influenced Mandarin, not formal writing
- zh-TW: softer literary Mandarin with natural spoken rhythm
- zh-SG: clean, direct, slightly more English-cadenced
- zh-CN: warm, accessible, broadcast-adjacent but personal
- Patch: "The phrasing '[X]' is written register, not spoken. A native [locale] speaker would say '[more natural equivalent]' instead"

#### `narrative_flow_cohesion` (weight 1.5)

Low score means choppy transitions between sections or atom types.
- Check the boundaries between HOOK→STORY, STORY→REFLECTION, REFLECTION→EXERCISE
- Patch: "Add a natural transition phrase between '[end of section A]' and '[start of section B]'"

#### `polish_emotional_impact` (weight 2.0)

Low score means the script feels mechanical or under-polished.
- This gate reflects overall listener experience — does it feel finished?
- Patch: "The section about [X] feels clinical/mechanical. Find the emotional texture in '[source passage]' and carry that into the script"

---

## 4. Working the Manual Review queue in PhoenixControl

The **Manual Review** tab is in the left sidebar of PhoenixControl. It appears after all other tabs. The badge count shows how many sections need attention. Red badge = hard gate failures present (highest priority).

**Queue order**: Sorted by `hard_gate_failures` descending, then `aggregate_score` ascending. Most broken sections are always at the top.

**For each entry you see**:
- Section ID, locale, book, hard gate failure count, best aggregate score, loops run
- Click to see the artifact packet: best draft + review summary + defect history

**Triage flow**:
1. Open the entry — read the Review Summary first (plain-English explanation of what failed)
2. Read the Defect History — shows which gates failed and the judge's specific feedback
3. Read the Best Draft — is it close? Is it wrong in a fundamental way?
4. Decide: re-run with current config, or adjust a prompt first (see §7)
5. Click **Re-run section** — the pipeline will run again with fresh loops
6. If it passes, it drops off the queue automatically on next refresh
7. If it's fundamentally broken (wrong locale? wrong content type?), escalate (see §9)

---

## 5. How to re-run a section

**Via PhoenixControl**: Click the section in Manual Review queue → "Re-run section" button.

**Via CLI** (when you need more control):
```bash
# Re-run a single section
python scripts/audiobook_script/run_comparator_loop.py \
  --section-id intro_001 \
  --locale zh-TW \
  --english-source artifacts/audiobook/source/<book_id>/intro_001.txt \
  --book-id <book_id> \
  --batch-id rerun_$(date +%Y%m%d) \
  --content-type pearl_prime

# Re-run with more loops (temporarily increase max_loops in config first)
# Edit config/audiobook_script/comparator_config.yaml: max_loops: 5
# Then re-run as above
```

---

## 6. How to re-run the full book

```bash
# Full book re-run (parallel sections, 6 at a time)
python scripts/audiobook_script/run_comparator_loop.py \
  --book-id <book_id> \
  --batch-id batch_$(date +%Y%m%d) \
  --sections-manifest artifacts/audiobook/source/<book_id>/manifest.json \
  --locale zh-TW \
  --content-type pearl_prime
```

The manifest.json should be:
```json
{
  "sections": [
    {"section_id": "intro_001", "source_file": "artifacts/audiobook/source/<book_id>/intro_001.txt"},
    {"section_id": "ch01_001",  "source_file": "artifacts/audiobook/source/<book_id>/ch01_001.txt"}
  ]
}
```

---

## 7. Config changes operators can safely make

All config lives in `config/audiobook_script/comparator_config.yaml`.

| Change | How | Notes |
|--------|-----|-------|
| Increase max loops for a difficult section | Set `loop_control.max_loops: 5` | Valid range: [1, 5]. Remember to revert after. |
| Relax locale threshold | Add/edit `locale_threshold_overrides.zh-HK.min_scored_pass_threshold: 0.70` | Useful if zh-HK consistently scores 0.72–0.74 |
| Change parallel sections | Set `parallel.max_parallel_sections: 4` | Lower if LM Studio is unstable |
| Switch content type prompt | Pass `--content-type` on CLI | No config change needed |

**Do NOT change without engineering review**:
- `judge_model.temperature` (must stay at 0.1)
- `scoring.pass_requires_all_hard_gates` (must stay true)
- `artifact_trace.manual_review_queue_file` path

---

## 8. Signs something is wrong (and what to do)

| Symptom | Likely cause | Action |
|---------|-------------|--------|
| All sections failing `tts_readability_cadence` | Draft prompt not loading correctly | Run `--dry-run` to verify prompts; check `prompts/audiobook/draft_*_v2.txt` exists |
| Judge returning invalid JSON every loop | LM Studio model not loaded or wrong model | Check LM Studio is running and a model is loaded at `http://127.0.0.1:1234` |
| `native_regional_language_fit` always 0.3–0.4 | Draft prompt locale guidance not strong enough | Add more explicit locale-specific examples to the draft prompt for that locale |
| 100% manual review rate | LM Studio unreachable or prompt missing | Check LM Studio; run dry-run; check prompt files |
| Queue not updating after re-run | PhoenixControl showing stale data | Click Refresh button in Manual Review tab |
| Same section failing same gate every loop | Gate requires human judgment or config change | Escalate to content lead; may need prompt tuning |

---

## 9. Escalation path

| Issue | Who to contact |
|-------|---------------|
| Hard gate failing despite 5 loops | Content lead — may need locale-specific prompt tuning |
| Judge model producing consistently low scores across all locales | Engineering — may be a model quality issue in LM Studio |
| LM Studio model producing garbled output | Engineering — model may need to be reloaded or swapped |
| Schema validation failures on every loop | Engineering — schema/checklist version mismatch |
| Content type misidentified (e.g., teacher_mode content ran as pearl_prime) | Pipeline lead — verify `--content-type` argument in the run command |
| Need to rollback a batch | Engineering — run `scripts/release/audiobook_rollback.sh` |
