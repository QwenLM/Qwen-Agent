#!/usr/bin/env python3
"""
Qwen-Only Audiobook Comparator Loop — run_comparator_loop.py

Pipeline: English source -> Qwen draft (LM Studio) -> Judge (LM Studio) -> [repair loop] -> pass or manual_review.
No human in the loop at any stage. All patch application, routing, and artifact persistence
are fully automated.

Architecture:
  - Section-level parallelism: asyncio.gather + Semaphore(max_parallel_sections)
    Sections within a book are embarrassingly parallel; loops within a section are sequential.
  - Patch injection: judge-returned prompt_patches assembled automatically by PatchApplier;
    appended to system prompt as REVISION INSTRUCTIONS block, hard gate patches first.
  - Manual review: sections exhausting max_loops write a full packet (best_draft, final_draft,
    defect_history, review_summary, status.json) and are added to manual_review_queue.json
    for PhoenixControl UI visibility (sorted by severity = hard_gate_failures desc).
  - Judge independence: separate system prompt, temperature 0.1, rotated seed per loop.
    Judge output JSON-schema validated every pass. Schema fail -> manual_review; never silent pass.

Config: config/audiobook_script/comparator_config.yaml  (LM Studio endpoint: http://127.0.0.1:1234/v1)
Checklist: config/audiobook_script/comparison_checklist_v2.yaml
Schema: schemas/comparator_result_v2.schema.json
Spec: docs/AUDIOBOOK_PIPELINE_SPEC.md

Usage:
  # Single section (debug/test)
  python scripts/audiobook_script/run_comparator_loop.py \\
    --section-id intro_001 --locale zh-TW \\
    --english-source artifacts/audiobook/source/intro_001.txt \\
    --book-id book_abc --batch-id batch_20260306

  # Full book (parallel sections)
  python scripts/audiobook_script/run_comparator_loop.py \\
    --book-id book_abc --batch-id batch_20260306 \\
    --sections-manifest artifacts/audiobook/source/book_abc/manifest.json \\
    --locale zh-TW

  # Dry-run (config/schema validation only; no API calls)
  python scripts/audiobook_script/run_comparator_loop.py --batch-id x --locale zh-TW --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger("comparator_loop")


# ─── CONFIG ───────────────────────────────────────────────────────────────────

def _load_yaml(path: Path) -> dict:
    try:
        import yaml
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error("Failed to load YAML %s: %s", path, e)
        return {}


def _load_config(repo: Path) -> dict:
    cfg = _load_yaml(repo / "config" / "audiobook_script" / "comparator_config.yaml")
    if not cfg:
        raise RuntimeError("comparator_config.yaml missing or empty")
    max_loops = cfg.get("loop_control", {}).get("max_loops", 3)
    if not (1 <= max_loops <= 5):
        raise ValueError(f"max_loops={max_loops} outside allowed range [1,5]")
    return cfg


def _load_checklist(repo: Path) -> dict:
    return _load_yaml(repo / "config" / "audiobook_script" / "comparison_checklist_v2.yaml")


def _load_result_schema(repo: Path) -> dict:
    p = repo / "schemas" / "comparator_result_v2.schema.json"
    if not p.exists():
        raise RuntimeError(f"Result schema missing: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


# ─── DATA STRUCTURES ──────────────────────────────────────────────────────────

@dataclass
class LoopTrace:
    run_id: str
    batch_id: str
    book_id: str
    section_id: str
    locale: str
    loop_index: int
    input_draft_hash: str
    prompt_patch: str
    rerun_prompt_hash: str
    aggregate_score: float
    hard_gates_passed: bool
    final_decision: str
    timestamp_utc: str
    gate_results: list[dict] = field(default_factory=list)


@dataclass
class SectionResult:
    section_id: str
    locale: str
    book_id: str
    batch_id: str
    decision: str
    loops_attempted: int
    best_loop_index: int
    best_aggregate_score: float
    best_draft: str
    final_draft: str
    loop_traces: list[LoopTrace] = field(default_factory=list)
    error: str | None = None


# ─── UTILITIES ────────────────────────────────────────────────────────────────

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _section_seed(section_id: str, locale: str) -> int:
    return int(hashlib.sha256(f"{section_id}:{locale}".encode()).hexdigest()[:8], 16)


def _judge_seed(section_id: str, loop_index: int) -> int:
    return int(hashlib.sha256(f"{section_id}:loop{loop_index}:JUDGE_SALT_V2".encode()).hexdigest()[:8], 16)


# ─── LM STUDIO API (OpenAI-compatible, http://127.0.0.1:1234) ─────────────────

def _lm_studio_client(model_cfg: dict):
    """Return an AsyncOpenAI client pointed at LM Studio."""
    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise RuntimeError(
            "openai package required: pip install openai --break-system-packages"
        )
    return AsyncOpenAI(
        base_url=model_cfg.get("base_url", "http://127.0.0.1:1234/v1"),
        api_key=model_cfg.get("api_key", "lm-studio"),
    )


async def _call_qwen_draft(section_text: str, locale: str, system_prompt: str, cfg: dict, seed: int) -> str:
    """
    Call local Qwen draft model via LM Studio (OpenAI-compatible API).
    Config: comparator_config.yaml > draft_model
    Endpoint: http://127.0.0.1:1234/v1  — whatever model is loaded in LM Studio.
    """
    draft_cfg = cfg.get("draft_model", {})
    client = _lm_studio_client(draft_cfg)
    model_id = draft_cfg.get("model_id", "local-model")
    temperature = float(draft_cfg.get("temperature", 0.7))
    max_tokens = int(draft_cfg.get("max_output_tokens", 3000))
    timeout = float(draft_cfg.get("timeout_seconds", 120))

    user_msg = (
        f"LOCALE: {locale}\n\n"
        f"SOURCE CONTENT:\n{section_text}\n\n"
        "Produce the localized audiobook script now. Output only the script — "
        "no preamble, no commentary, no headers."
    )

    try:
        response = await client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_msg},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            seed=seed,
            timeout=timeout,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        logger.error("LM Studio draft call failed (section_hash_seed=%d): %s", seed, e)
        raise


async def _call_qwen_judge(english_source: str, draft: str, locale: str,
                            judge_system_prompt: str, cfg: dict, seed: int) -> str:
    """
    Call local Qwen judge model via LM Studio (OpenAI-compatible API).
    Config: comparator_config.yaml > judge_model
    Returns JSON array conforming to schemas/comparator_result_v2.schema.json.
    Judge independence: temperature=0.1, rotated seed per loop.
    """
    judge_cfg = cfg.get("judge_model", {})
    client = _lm_studio_client(judge_cfg)
    model_id = judge_cfg.get("model_id", "local-model")
    temperature = float(judge_cfg.get("temperature", 0.1))
    max_tokens = int(judge_cfg.get("max_output_tokens", 1500))
    timeout = float(judge_cfg.get("timeout_seconds", 60))

    user_msg = (
        f"LOCALE: {locale}\n\n"
        f"=== ENGLISH SOURCE ===\n{english_source}\n\n"
        f"=== LOCALIZED DRAFT ===\n{draft}\n\n"
        "Evaluate the draft against ALL nine gates. "
        "Return a JSON ARRAY only — no preamble, no markdown, no explanation. "
        "Each element must conform to comparator_result_v2.schema.json."
    )

    try:
        response = await client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": judge_system_prompt},
                {"role": "user",   "content": user_msg},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            seed=seed,
            timeout=timeout,
        )
        raw = response.choices[0].message.content or ""
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            raw = raw.rsplit("```", 1)[0]
        return raw.strip()
    except Exception as e:
        logger.error("LM Studio judge call failed (loop_seed=%d): %s", seed, e)
        raise


# ─── SCHEMA VALIDATION ────────────────────────────────────────────────────────

def _validate_judge_output(raw_json: str, result_schema: dict,
                            checklist_version: str) -> tuple[bool, list[dict] | None, str]:
    """
    Validate judge JSON against comparator_result_v2.schema.json.
    Verifies checklist_schema_version binding on every gate result.
    Schema fail -> manual_review; never silent pass.
    """
    try:
        gate_results = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return False, None, f"Judge output not valid JSON: {e}"

    if not isinstance(gate_results, list):
        return False, None, "Judge output must be a JSON array"

    for item in gate_results:
        ver = item.get("checklist_schema_version", "")
        if not ver.startswith("2.0"):
            return False, None, (
                f"checklist_schema_version mismatch: got '{ver}', "
                "expected '2.0.x' (bound to comparison_checklist_v2.yaml)"
            )

    try:
        import jsonschema
        gate_schema = result_schema["definitions"]["GateResult"]
        for item in gate_results:
            jsonschema.validate(instance=item, schema=gate_schema)
    except ImportError:
        required = {"gate_id", "pass", "checklist_schema_version", "loop_index", "section_id", "locale"}
        for item in gate_results:
            missing = required - set(item.keys())
            if missing:
                return False, None, f"Gate result missing required fields: {missing}"
    except Exception as e:
        return False, None, f"Schema validation failed: {e}"

    return True, gate_results, ""


# ─── PATCH APPLIER ────────────────────────────────────────────────────────────

class PatchApplier:
    """
    Assembles judge-returned prompt_patches into the next Qwen system prompt.
    Fully automated — no human reviews the patch before injection.
    Hard gate patches first (by gate_id), then scored by weight desc.
    Appended to original system prompt (append_to_system strategy).
    Hard gate patches always preserved on overflow.
    """

    def __init__(self, cfg: dict, checklist: dict) -> None:
        pi = cfg.get("patch_injection", {})
        self.max_patch_chars = pi.get("max_patch_tokens", 600) * 4
        self.hard_prefix = pi.get("hard_gate_prefix", "[HARD — must fix]")
        self.scored_prefix = pi.get("scored_gate_prefix", "[IMPROVE]")
        self.header_template = pi.get(
            "revision_block_header",
            "## REVISION INSTRUCTIONS (Loop {loop_index})\n## Fix ALL issues below.\n"
        )
        self.include_defect = pi.get("include_defect_in_patch", True)
        self.overflow_strategy = pi.get("on_patch_overflow", "truncate_scored_keep_hard")
        self._gate_weights: dict[str, float] = {}
        self._gate_types: dict[str, str] = {}
        for g in (checklist.get("gates") or []):
            gid = g.get("gate_id", "")
            self._gate_weights[gid] = g.get("weight", 1.0)
            self._gate_types[gid] = g.get("type", "hard")

    def assemble(self, original_system_prompt: str, gate_results: list[dict], loop_index: int) -> str:
        failed = [g for g in gate_results if not g.get("pass", True) and g.get("prompt_patch")]
        if not failed:
            return original_system_prompt

        hard_patches = sorted(
            [g for g in failed if self._gate_types.get(g["gate_id"], "hard") == "hard"],
            key=lambda g: g["gate_id"]
        )
        scored_patches = sorted(
            [g for g in failed if self._gate_types.get(g["gate_id"], "hard") == "scored"],
            key=lambda g: -self._gate_weights.get(g["gate_id"], 1.0)
        )

        header = self.header_template.format(loop_index=loop_index)
        lines: list[str] = []
        for g in hard_patches:
            ctx = f" [Defect: {g['defect']}]" if (self.include_defect and g.get("defect")) else ""
            lines.append(f"{self.hard_prefix} {g['gate_id']}{ctx}: {g['prompt_patch']}")
        for g in scored_patches:
            ctx = f" [Defect: {g['defect']}]" if (self.include_defect and g.get("defect")) else ""
            lines.append(f"{self.scored_prefix} {g['gate_id']}{ctx}: {g['prompt_patch']}")

        patch_block = header + "\n".join(lines)

        if len(patch_block) > self.max_patch_chars and self.overflow_strategy == "truncate_scored_keep_hard":
            hard_only = header + "\n".join(
                f"{self.hard_prefix} {g['gate_id']}: {g['prompt_patch']}" for g in hard_patches
            )
            patch_block = hard_only[:self.max_patch_chars]
            logger.warning("Patch block truncated (kept hard gates only); loop=%d", loop_index)

        return original_system_prompt + "\n\n" + patch_block


# ─── SCORING ──────────────────────────────────────────────────────────────────

def _aggregate_score(gate_results: list[dict], checklist: dict) -> tuple[float, bool]:
    gate_map = {g["gate_id"]: g for g in (checklist.get("gates") or [])}
    scored_total = 0.0
    max_scored = 0.0
    all_hard_passed = True

    for r in gate_results:
        gid = r.get("gate_id", "")
        gdef = gate_map.get(gid, {})
        gtype = gdef.get("type", "hard")
        passed = r.get("pass", False)
        if gtype == "hard":
            if not passed:
                all_hard_passed = False
        else:
            w = gdef.get("weight", 1.0)
            s = r.get("score") or 0.0
            scored_total += s * w
            max_scored += w

    agg = round(scored_total / max_scored, 4) if max_scored > 0 else 1.0
    return agg, all_hard_passed


def _passes_threshold(agg: float, all_hard: bool, cfg: dict, locale: str) -> bool:
    if not all_hard:
        return False
    base = cfg.get("scoring", {}).get("min_scored_pass_threshold", 0.75)
    override = cfg.get("locale_threshold_overrides", {}).get(locale, {})
    threshold = override.get("min_scored_pass_threshold", base)
    return agg >= threshold


# ─── ARTIFACTS ────────────────────────────────────────────────────────────────

def _artifact_dir(repo: Path, cfg: dict, batch_id: str, book_id: str,
                   section_id: str, loop_index: int) -> Path:
    base = repo / cfg.get("artifact_trace", {}).get("base_path", "artifacts/audiobook")
    return base / batch_id / book_id / section_id / f"loop_{loop_index}"


def _write_loop_trace(repo: Path, cfg: dict, trace: LoopTrace) -> None:
    d = _artifact_dir(repo, cfg, trace.batch_id, trace.book_id, trace.section_id, trace.loop_index)
    d.mkdir(parents=True, exist_ok=True)
    (d / "trace.json").write_text(
        json.dumps({
            "run_id": trace.run_id, "batch_id": trace.batch_id, "book_id": trace.book_id,
            "section_id": trace.section_id, "locale": trace.locale,
            "loop_index": trace.loop_index, "input_draft_hash": trace.input_draft_hash,
            "prompt_patch": trace.prompt_patch, "rerun_prompt_hash": trace.rerun_prompt_hash,
            "aggregate_score": trace.aggregate_score, "hard_gates_passed": trace.hard_gates_passed,
            "final_decision": trace.final_decision, "timestamp_utc": trace.timestamp_utc,
            "gate_results": trace.gate_results,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    jsonl_path = repo / cfg.get("observability", {}).get("jsonl_log_path", "artifacts/audiobook/loop_decisions.jsonl")
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": trace.timestamp_utc, "run_id": trace.run_id,
            "section_id": trace.section_id, "locale": trace.locale,
            "loop_index": trace.loop_index, "decision": trace.final_decision,
            "aggregate_score": trace.aggregate_score, "hard_gates_passed": trace.hard_gates_passed,
        }, ensure_ascii=False) + "\n")


def _write_manual_review_packet(repo: Path, cfg: dict, result: SectionResult) -> None:
    artifact_cfg = cfg.get("artifact_trace", {})
    packet_dir = (
        repo / artifact_cfg.get("base_path", "artifacts/audiobook")
        / result.batch_id / result.book_id / result.section_id / "manual_review"
    )
    packet_dir.mkdir(parents=True, exist_ok=True)

    (packet_dir / "best_draft.txt").write_text(result.best_draft, encoding="utf-8")
    (packet_dir / "final_draft.txt").write_text(result.final_draft, encoding="utf-8")

    defect_history = [
        {"loop_index": t.loop_index, "gate_results": t.gate_results, "aggregate_score": t.aggregate_score}
        for t in result.loop_traces
    ]
    (packet_dir / "defect_history.json").write_text(
        json.dumps(defect_history, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    summary = [
        "MANUAL REVIEW REQUIRED", "=" * 40,
        f"section_id:      {result.section_id}",
        f"locale:          {result.locale}",
        f"book_id:         {result.book_id}",
        f"batch_id:        {result.batch_id}",
        f"loops_attempted: {result.loops_attempted}",
        f"best_score:      {result.best_aggregate_score:.3f} (loop {result.best_loop_index})",
        "", "Loop-by-loop summary:",
    ]
    for t in result.loop_traces:
        failed_gates = [g["gate_id"] for g in t.gate_results if not g.get("pass", True)]
        summary.append(
            f"  Loop {t.loop_index}: score={t.aggregate_score:.3f} "
            f"hard_passed={t.hard_gates_passed} failed={failed_gates or 'none'}"
        )
    summary += ["", "Fix: start from best_draft.txt; see defect_history.json for gate-level details."]
    (packet_dir / "review_summary.txt").write_text("\n".join(summary), encoding="utf-8")

    hard_fail_count = sum(
        1 for t in result.loop_traces for g in t.gate_results
        if not g.get("pass", True) and g.get("gate_type") == "hard"
    )
    status = {
        "requires_manual_review": True,
        "section_id": result.section_id, "locale": result.locale,
        "book_id": result.book_id, "batch_id": result.batch_id,
        "hard_gate_failures": hard_fail_count,
        "best_aggregate_score": result.best_aggregate_score,
        "loops_attempted": result.loops_attempted,
        "packet_path": str(packet_dir),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    (packet_dir / "status.json").write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")

    # Append to manual_review_queue.json — PhoenixControl UI feed
    queue_path = repo / artifact_cfg.get("manual_review_queue_file", "artifacts/audiobook/manual_review_queue.json")
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue: list[dict] = []
    if queue_path.exists():
        try:
            queue = json.loads(queue_path.read_text(encoding="utf-8"))
        except Exception:
            queue = []
    queue = [e for e in queue if not (
        e.get("section_id") == result.section_id
        and e.get("locale") == result.locale
        and e.get("batch_id") == result.batch_id
    )]
    queue.append({
        "section_id": result.section_id, "locale": result.locale,
        "book_id": result.book_id, "batch_id": result.batch_id,
        "hard_gate_failures": hard_fail_count,
        "aggregate_score_best": result.best_aggregate_score,
        "loops_attempted": result.loops_attempted,
        "packet_path": str(packet_dir),
        "timestamp_utc": status["timestamp_utc"],
    })
    queue.sort(key=lambda e: -e.get("hard_gate_failures", 0))
    queue_path.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.warning("MANUAL REVIEW: section=%s locale=%s batch=%s -> %s",
                   result.section_id, result.locale, result.batch_id, packet_dir)


# ─── SECTION LOOP ─────────────────────────────────────────────────────────────

async def run_section_loop(
    section_id: str, locale: str, book_id: str, batch_id: str,
    english_source: str, cfg: dict, checklist: dict, result_schema: dict,
    base_system_prompt: str, judge_system_prompt: str,
    repo: Path, semaphore: asyncio.Semaphore,
) -> SectionResult:
    """Run comparator loop for one section. Fully automated — no human in loop."""
    async with semaphore:
        max_loops = cfg.get("loop_control", {}).get("max_loops", 3)
        patch_applier = PatchApplier(cfg, checklist)
        loop_traces: list[LoopTrace] = []
        current_prompt = base_system_prompt
        best_draft = ""
        final_draft = ""
        best_score = -1.0
        best_loop_index = 1
        run_id = f"{batch_id}__{book_id}__{section_id}__{locale}"
        draft_seed = _section_seed(section_id, locale)

        for loop_index in range(1, max_loops + 1):
            ts = datetime.now(timezone.utc).isoformat()
            logger.info("Loop %d/%d: section=%s locale=%s", loop_index, max_loops, section_id, locale)

            # Draft
            try:
                draft_text = await asyncio.wait_for(
                    _call_qwen_draft(english_source, locale, current_prompt, cfg, draft_seed),
                    timeout=cfg.get("draft_model", {}).get("timeout_seconds", 60),
                )
            except (asyncio.TimeoutError, NotImplementedError):
                raise
            except Exception as e:
                logger.error("Draft failed: section=%s loop=%d err=%s", section_id, loop_index, e)
                break

            input_draft_hash = _sha256(draft_text)
            final_draft = draft_text

            # Judge
            judge_seed = _judge_seed(section_id, loop_index)
            try:
                judge_raw = await asyncio.wait_for(
                    _call_qwen_judge(english_source, draft_text, locale, judge_system_prompt, cfg, judge_seed),
                    timeout=cfg.get("judge_model", {}).get("timeout_seconds", 45),
                )
            except asyncio.TimeoutError:
                logger.error("Judge timeout: section=%s loop=%d -> manual_review", section_id, loop_index)
                trace = LoopTrace(
                    run_id=run_id, batch_id=batch_id, book_id=book_id,
                    section_id=section_id, locale=locale, loop_index=loop_index,
                    input_draft_hash=input_draft_hash, prompt_patch="",
                    rerun_prompt_hash="", aggregate_score=0.0,
                    hard_gates_passed=False, final_decision="manual_review",
                    timestamp_utc=ts,
                )
                loop_traces.append(trace)
                _write_loop_trace(repo, cfg, trace)
                break
            except NotImplementedError:
                raise
            except Exception as e:
                logger.error("Judge failed: section=%s loop=%d err=%s", section_id, loop_index, e)
                break

            # Schema validation — schema fail -> manual_review, never silent pass
            valid, gate_results, schema_err = _validate_judge_output(
                judge_raw, result_schema, checklist.get("schema_version", "2.0")
            )
            if not valid:
                logger.error("Judge schema fail: section=%s loop=%d err=%s -> manual_review",
                             section_id, loop_index, schema_err)
                trace = LoopTrace(
                    run_id=run_id, batch_id=batch_id, book_id=book_id,
                    section_id=section_id, locale=locale, loop_index=loop_index,
                    input_draft_hash=input_draft_hash, prompt_patch="",
                    rerun_prompt_hash="", aggregate_score=0.0,
                    hard_gates_passed=False, final_decision="manual_review",
                    timestamp_utc=ts, gate_results=[{"schema_error": schema_err}],
                )
                loop_traces.append(trace)
                _write_loop_trace(repo, cfg, trace)
                break

            # Score
            agg, all_hard = _aggregate_score(gate_results or [], checklist)
            if agg > best_score:
                best_score = agg
                best_draft = draft_text
                best_loop_index = loop_index

            # Decision
            if _passes_threshold(agg, all_hard, cfg, locale):
                decision = "pass"
            elif loop_index < max_loops:
                decision = "continue"
            else:
                decision = "manual_review"

            # Patch assembly for next loop
            patch_block = ""
            next_prompt_hash = ""
            if decision == "continue" and gate_results:
                next_prompt = patch_applier.assemble(current_prompt, gate_results, loop_index + 1)
                next_prompt_hash = _sha256(next_prompt)
                patch_block = next_prompt[len(current_prompt):]
                current_prompt = next_prompt

            trace = LoopTrace(
                run_id=run_id, batch_id=batch_id, book_id=book_id,
                section_id=section_id, locale=locale, loop_index=loop_index,
                input_draft_hash=input_draft_hash, prompt_patch=patch_block,
                rerun_prompt_hash=next_prompt_hash, aggregate_score=agg,
                hard_gates_passed=all_hard, final_decision=decision,
                timestamp_utc=ts, gate_results=gate_results or [],
            )
            loop_traces.append(trace)
            _write_loop_trace(repo, cfg, trace)

            if decision != "continue":
                break

        final_decision = loop_traces[-1].final_decision if loop_traces else "manual_review"
        result = SectionResult(
            section_id=section_id, locale=locale, book_id=book_id, batch_id=batch_id,
            decision=final_decision, loops_attempted=len(loop_traces),
            best_loop_index=best_loop_index, best_aggregate_score=best_score,
            best_draft=best_draft, final_draft=final_draft, loop_traces=loop_traces,
        )
        if final_decision == "manual_review":
            _write_manual_review_packet(repo, cfg, result)
        return result


# ─── BOOK PARALLEL RUNNER ─────────────────────────────────────────────────────

async def run_book_parallel(
    book_id: str, batch_id: str, locale: str, sections: list[dict],
    cfg: dict, checklist: dict, result_schema: dict,
    base_system_prompt: str, judge_system_prompt: str, repo: Path,
) -> list[SectionResult]:
    """Process all sections of a book in parallel, bounded by max_parallel_sections."""
    max_workers = cfg.get("parallel", {}).get("max_parallel_sections", 6)
    book_timeout = cfg.get("parallel", {}).get("batch_timeout_seconds", 7200)
    semaphore = asyncio.Semaphore(max_workers)

    tasks = [
        run_section_loop(
            section_id=s["section_id"], locale=locale, book_id=book_id, batch_id=batch_id,
            english_source=s["english_source_text"], cfg=cfg, checklist=checklist,
            result_schema=result_schema, base_system_prompt=base_system_prompt,
            judge_system_prompt=judge_system_prompt, repo=repo, semaphore=semaphore,
        )
        for s in sections
    ]

    try:
        results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=book_timeout)
    except asyncio.TimeoutError:
        logger.error("Book timeout: book=%s batch=%s", book_id, batch_id)
        return []

    processed: list[SectionResult] = []
    for i, r in enumerate(results):
        if isinstance(r, Exception) and not isinstance(r, NotImplementedError):
            sid = sections[i]["section_id"] if i < len(sections) else f"section_{i}"
            logger.error("Section %s exception: %s", sid, r)
            processed.append(SectionResult(
                section_id=sid, locale=locale, book_id=book_id, batch_id=batch_id,
                decision="manual_review", loops_attempted=0, best_loop_index=0,
                best_aggregate_score=0.0, best_draft="", final_draft="", error=str(r),
            ))
        else:
            if isinstance(r, Exception):
                raise r
            processed.append(r)
    return processed


def _write_batch_summary(repo: Path, cfg: dict, batch_id: str, results: list[SectionResult]) -> None:
    tpl = cfg.get("artifact_trace", {}).get("batch_summary_file", "artifacts/audiobook/{batch_id}/batch_summary.json")
    path = repo / tpl.format(batch_id=batch_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    passed = [r for r in results if r.decision == "pass"]
    manual = [r for r in results if r.decision == "manual_review"]
    summary = {
        "batch_id": batch_id, "total_sections": len(results),
        "passed": len(passed), "manual_review": len(manual),
        "pass_rate": round(len(passed) / len(results), 4) if results else 0.0,
        "manual_review_rate": round(len(manual) / len(results), 4) if results else 0.0,
        "sections": [
            {"section_id": r.section_id, "locale": r.locale, "book_id": r.book_id,
             "decision": r.decision, "loops_attempted": r.loops_attempted,
             "best_aggregate_score": r.best_aggregate_score}
            for r in results
        ],
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    mr_threshold = cfg.get("observability", {}).get("alert_on_manual_review_rate_above", 0.10)
    if summary["manual_review_rate"] > mr_threshold:
        logger.warning("ALERT: manual_review_rate=%.2f exceeds %.2f for batch=%s",
                       summary["manual_review_rate"], mr_threshold, batch_id)


def _load_prompt(repo: Path, prompt_id: str) -> str:
    """Load a prompt file. Checks prompts/audiobook/ first, then prompts/."""
    for subdir in ["prompts/audiobook", "prompts"]:
        p = repo / subdir / f"{prompt_id}.txt"
        if p.exists():
            return p.read_text(encoding="utf-8")
    logger.warning("Prompt not found: %s — using stub", prompt_id)
    return f"[STUB: implement prompt {prompt_id}]"


def _resolve_draft_prompt_id(cfg: dict, content_type: str | None) -> str:
    """
    Resolve draft system_prompt_id based on content_type.
    Routing table in comparator_config.yaml > draft_model.prompt_routing.
    Falls back to draft_model.system_prompt_id if no routing table.
    """
    routing = cfg.get("draft_model", {}).get("prompt_routing", {})
    if routing and content_type:
        return routing.get(content_type, routing.get("default", "draft_pearl_prime_v2"))
    return cfg.get("draft_model", {}).get("system_prompt_id", "draft_pearl_prime_v2")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    ap = argparse.ArgumentParser(description="Qwen-Only Audiobook Comparator Loop")
    ap.add_argument("--section-id")
    ap.add_argument("--locale", required=True)
    ap.add_argument("--book-id")
    ap.add_argument("--batch-id", required=True)
    ap.add_argument("--english-source")
    ap.add_argument("--sections-manifest")
    ap.add_argument("--content-type",
                    choices=["pearl_prime", "pearl_news", "phoenix_v4", "teacher_mode"],
                    default="pearl_prime",
                    help="Content type — selects the draft prompt variant")
    ap.add_argument("--repo", default=None)
    ap.add_argument("--dry-run", action="store_true", help="Validate config/schema only; no API calls")
    args = ap.parse_args()

    repo = Path(args.repo) if args.repo else REPO_ROOT
    cfg = _load_config(repo)
    checklist = _load_checklist(repo)
    result_schema = _load_result_schema(repo)

    if args.dry_run:
        print("Dry run: config, checklist, and schema loaded OK")
        print(f"  max_loops={cfg['loop_control']['max_loops']} (range [1,5] validated)")
        print(f"  max_parallel_sections={cfg['parallel']['max_parallel_sections']}")
        print(f"  min_scored_pass_threshold={cfg['scoring']['min_scored_pass_threshold']}")
        print(f"  judge_model={cfg['judge_model']['model_id']} temp={cfg['judge_model']['temperature']}")
        print(f"  gates={[g['gate_id'] for g in checklist.get('gates', [])]}")
        return 0

    draft_prompt = _load_prompt(repo, cfg["draft_model"]["system_prompt_id"])
    judge_prompt = _load_prompt(repo, cfg["judge_model"]["system_prompt_id"])

    if args.section_id and args.english_source:
        english_source = Path(args.english_source).read_text(encoding="utf-8")
        result = asyncio.run(run_section_loop(
            section_id=args.section_id, locale=args.locale,
            book_id=args.book_id or "unknown", batch_id=args.batch_id,
            english_source=english_source, cfg=cfg, checklist=checklist,
            result_schema=result_schema, base_system_prompt=draft_prompt,
            judge_system_prompt=judge_prompt, repo=repo,
            semaphore=asyncio.Semaphore(1),
        ))
        print(f"Section {result.section_id}: {result.decision} "
              f"(loops={result.loops_attempted}, score={result.best_aggregate_score:.3f})")
        return 0 if result.decision == "pass" else 1

    if args.sections_manifest:
        sections = json.loads(Path(args.sections_manifest).read_text(encoding="utf-8"))
        results = asyncio.run(run_book_parallel(
            book_id=args.book_id or "unknown", batch_id=args.batch_id,
            locale=args.locale, sections=sections, cfg=cfg, checklist=checklist,
            result_schema=result_schema, base_system_prompt=draft_prompt,
            judge_system_prompt=judge_prompt, repo=repo,
        ))
        _write_batch_summary(repo, cfg, args.batch_id, results)
        manual = [r for r in results if r.decision == "manual_review"]
        print(f"Book complete: {len(results)} sections, {len(manual)} manual_review")
        return 1 if manual else 0

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
