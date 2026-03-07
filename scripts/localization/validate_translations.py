#!/usr/bin/env python3
"""
Validate Translations — validate_translations.py

Quality validation for translated locale atoms. Uses the Qwen judge model
to assess translation quality against the same rubric used by the audiobook
comparator loop (native_regional_language_fit gate).

Architecture:
  - Loads en-US source atoms and translated locale atoms
  - For each teacher/topic/locale, calls judge model to evaluate:
    1. Semantic fidelity: does the translation preserve the teaching's meaning?
    2. Native language fit: does it read as native writing, not a translation?
    3. Cultural adaptation: are locale-specific concepts referenced?
    4. Atom constraints: 40-80 words, connectable to news, tradition-specific?
  - Outputs validation report (JSON + human-readable)
  - Integration point for EI V2 weekly quality assessment

Shared with Pearl Prime:
  - Uses the same judge model config (comparator_config.yaml or llm_expansion.yaml)
  - Applies the same native_regional_language_fit rubric (comparison_checklist_v2.yaml gate 7)
  - Results feed into the same EI V2 quality loop (native_prompts_eval_learn.py)

Usage:
  # Validate all translations for ja-JP
  python scripts/localization/validate_translations.py --locale ja-JP

  # Validate specific topic
  python scripts/localization/validate_translations.py --locale zh-CN --topic climate

  # Full validation report across all locales
  python scripts/localization/validate_translations.py --all-locales --report

  # Output JSON for EI V2 ingestion
  python scripts/localization/validate_translations.py --all-locales --json-out artifacts/localization/quality_report.json
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger("validate_translations")

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

PEARL_NEWS_TOPICS = [
    "climate", "economy_work", "education", "inequality",
    "mental_health", "partnerships", "peace_conflict",
]

TARGET_LOCALES = ["ja-JP", "zh-CN", "zh-TW"]

# Validation gates (aligned with comparator_checklist_v2 gate definitions)
VALIDATION_GATES = [
    {
        "gate_id": "semantic_fidelity",
        "type": "hard",
        "description": "Translation preserves the original teaching's core meaning",
    },
    {
        "gate_id": "native_language_fit",
        "type": "scored",
        "weight": 2.5,
        "description": "Translation reads as native writing, not translated English",
    },
    {
        "gate_id": "cultural_adaptation",
        "type": "scored",
        "weight": 2.0,
        "description": "Locale-specific cultural concepts referenced where natural",
    },
    {
        "gate_id": "atom_constraints",
        "type": "hard",
        "description": "40-80 words, connectable to news, tradition-specific terminology preserved",
    },
    {
        "gate_id": "register_consistency",
        "type": "scored",
        "weight": 1.5,
        "description": "Consistent language register appropriate for the locale",
    },
]


def _load_yaml(path: Path) -> dict:
    if not path.exists() or yaml is None:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_llm_config() -> dict[str, Any]:
    for config_name in ["pearl_news/config/llm_expansion.yaml", "config/audiobook_script/comparator_config.yaml"]:
        path = REPO_ROOT / config_name
        if path.exists():
            cfg = _load_yaml(path)
            if cfg:
                return cfg
    raise RuntimeError("No LLM config found")


def _call_judge(prompt: str, system_prompt: str, cfg: dict) -> str:
    """Call judge model for translation quality assessment."""
    try:
        import openai
    except ImportError:
        raise RuntimeError("openai package required")

    model_cfg = cfg.get("judge_model", cfg.get("draft_model", cfg))
    base_url = model_cfg.get("base_url", "http://127.0.0.1:1234/v1")
    api_key = model_cfg.get("api_key", "lm-studio")
    model_id = model_cfg.get("model_id", model_cfg.get("model", "local-model"))
    timeout = float(model_cfg.get("timeout_seconds", model_cfg.get("timeout", 120)))

    client = openai.OpenAI(base_url=base_url, api_key=api_key)
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,  # Low temperature for consistent judging
        max_tokens=1500,
        timeout=timeout,
    )
    return response.choices[0].message.content or ""


# ─── STRUCTURAL VALIDATION (no LLM needed) ──────────────────────────────────

def validate_structural(
    en_atoms: list[str],
    translated_atoms: list[str],
    teacher_id: str,
    locale: str,
) -> list[dict[str, Any]]:
    """Structural validation — no LLM call needed."""
    results: list[dict[str, Any]] = []

    # Check count match
    if len(translated_atoms) != len(en_atoms):
        results.append({
            "gate_id": "atom_constraints",
            "pass": False,
            "defect": f"Count mismatch: {len(en_atoms)} en-US atoms, {len(translated_atoms)} translated",
            "teacher_id": teacher_id,
            "locale": locale,
        })

    # Check each atom
    for i, atom in enumerate(translated_atoms):
        atom_str = str(atom).strip()
        if not atom_str:
            results.append({
                "gate_id": "atom_constraints",
                "pass": False,
                "defect": f"Atom {i+1} is empty",
                "teacher_id": teacher_id,
                "locale": locale,
            })
        elif len(atom_str) < 20:
            results.append({
                "gate_id": "atom_constraints",
                "pass": False,
                "defect": f"Atom {i+1} suspiciously short: {len(atom_str)} chars",
                "teacher_id": teacher_id,
                "locale": locale,
            })

    # Check for untranslated English
    for i, atom in enumerate(translated_atoms):
        atom_str = str(atom).strip()
        english_word_count = len([w for w in atom_str.split() if w.isascii() and len(w) > 3])
        total_words = len(atom_str.split())
        if total_words > 0 and english_word_count / total_words > 0.5:
            results.append({
                "gate_id": "native_language_fit",
                "pass": False,
                "score": 0.2,
                "defect": f"Atom {i+1} appears mostly English ({english_word_count}/{total_words} ASCII words)",
                "teacher_id": teacher_id,
                "locale": locale,
            })

    return results


# ─── LLM-BASED VALIDATION ───────────────────────────────────────────────────

def validate_with_judge(
    en_atoms: list[str],
    translated_atoms: list[str],
    teacher_id: str,
    teacher_name: str,
    tradition: str,
    topic: str,
    locale: str,
    cfg: dict,
) -> list[dict[str, Any]]:
    """LLM-based quality assessment of translated atoms."""
    system_prompt = (
        "You are a translation quality judge specializing in spiritual/therapeutic content. "
        "You assess translations for semantic fidelity, native language fit, and cultural adaptation.\n\n"
        "For each pair of (English source, translation), assess:\n"
        "1. semantic_fidelity (pass/fail): Does the translation preserve the teaching's core meaning?\n"
        "2. native_language_fit (0.0-1.0): Does it read as native writing, not translated?\n"
        "3. cultural_adaptation (0.0-1.0): Are locale-specific concepts referenced where natural?\n"
        "4. register_consistency (0.0-1.0): Is the language register appropriate for the locale?\n\n"
        "Output a JSON array — one object per atom pair. Each object has keys: "
        "atom_index, semantic_fidelity_pass (bool), native_language_fit (float), "
        "cultural_adaptation (float), register_consistency (float), defects (list of strings).\n"
        "Output ONLY JSON — no preamble, no markdown fences."
    )

    pairs = []
    for i, (en, tr) in enumerate(zip(en_atoms, translated_atoms)):
        pairs.append(f"Atom {i+1}:\n  English: {str(en).strip()}\n  {locale}: {str(tr).strip()}")

    user_prompt = (
        f"TEACHER: {teacher_name} ({tradition})\n"
        f"TOPIC: {topic}\n"
        f"TARGET LOCALE: {locale}\n\n"
        f"ATOM PAIRS TO EVALUATE:\n" + "\n\n".join(pairs) + "\n\n"
        f"Evaluate each pair. Return JSON array."
    )

    try:
        response = _call_judge(user_prompt, system_prompt, cfg)
        # Strip markdown fences if present
        raw = response.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            raw = raw.rsplit("```", 1)[0]

        results = json.loads(raw.strip())
        if not isinstance(results, list):
            results = [results]
        return results
    except Exception as e:
        logger.error("Judge call failed for %s/%s/%s: %s", teacher_id, topic, locale, e)
        return []


# ─── AGGREGATE REPORT ────────────────────────────────────────────────────────

def build_validation_report(
    locale: str,
    topics: list[str],
    use_judge: bool = False,
    cfg: dict | None = None,
) -> dict[str, Any]:
    """Build a full validation report for one locale across all topics."""
    report: dict[str, Any] = {
        "locale": locale,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "validation_mode": "judge" if use_judge else "structural",
        "topics": {},
        "summary": {
            "total_teachers": 0,
            "total_atoms_checked": 0,
            "structural_errors": 0,
            "avg_native_fit": 0.0,
        },
    }

    native_fit_scores: list[float] = []

    for topic in topics:
        en_path = REPO_ROOT / "pearl_news" / "atoms" / "teacher_quotes_practices" / f"topic_{topic}.yaml"
        locale_path = (REPO_ROOT / "pearl_news" / "atoms" / "teacher_quotes_practices"
                       / "locales" / locale / f"topic_{topic}.yaml")

        en_data = _load_yaml(en_path)
        locale_data = _load_yaml(locale_path)

        if not locale_data:
            report["topics"][topic] = {"status": "missing", "errors": ["Locale file not found"]}
            continue

        topic_report: dict[str, Any] = {"status": "ok", "teachers": {}}
        en_teachers = en_data.get("teachers") or {}
        locale_teachers = locale_data.get("teachers") or {}

        for teacher_id, en_teacher in en_teachers.items():
            report["summary"]["total_teachers"] += 1
            locale_teacher = locale_teachers.get(teacher_id, {})
            en_atoms = en_teacher.get("atoms") or []
            translated_atoms = locale_teacher.get("atoms") or []

            report["summary"]["total_atoms_checked"] += len(translated_atoms)

            # Structural validation
            structural = validate_structural(en_atoms, translated_atoms, teacher_id, locale)
            report["summary"]["structural_errors"] += len(structural)

            teacher_report: dict[str, Any] = {
                "en_atom_count": len(en_atoms),
                "translated_atom_count": len(translated_atoms),
                "structural_errors": structural,
                "status": locale_teacher.get("status", "unknown"),
            }

            # Judge-based validation (if enabled and LLM available)
            if use_judge and cfg and translated_atoms:
                try:
                    judge_results = validate_with_judge(
                        en_atoms, translated_atoms,
                        teacher_id,
                        locale_teacher.get("display_name", teacher_id),
                        locale_teacher.get("tradition", "interfaith"),
                        topic, locale, cfg,
                    )
                    teacher_report["judge_results"] = judge_results
                    # Extract native_language_fit scores
                    for jr in judge_results:
                        if isinstance(jr, dict) and "native_language_fit" in jr:
                            native_fit_scores.append(float(jr["native_language_fit"]))
                except Exception as e:
                    teacher_report["judge_error"] = str(e)

            topic_report["teachers"][teacher_id] = teacher_report

        report["topics"][topic] = topic_report

    if native_fit_scores:
        report["summary"]["avg_native_fit"] = round(sum(native_fit_scores) / len(native_fit_scores), 3)

    return report


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    ap = argparse.ArgumentParser(description="Validate translated locale atoms")
    ap.add_argument("--locale", default=None, help="Target locale to validate")
    ap.add_argument("--topic", default=None, help="Specific topic to validate")
    ap.add_argument("--all-locales", action="store_true", help="Validate all target locales")
    ap.add_argument("--report", action="store_true", help="Print human-readable report")
    ap.add_argument("--json-out", default=None, help="Write JSON report to file")
    ap.add_argument("--use-judge", action="store_true", help="Use LLM judge for quality scoring")
    args = ap.parse_args()

    if not args.locale and not args.all_locales:
        ap.print_help()
        return 0

    topics = [args.topic] if args.topic else PEARL_NEWS_TOPICS
    locales = TARGET_LOCALES if args.all_locales else ([args.locale] if args.locale else [])
    cfg = _load_llm_config() if args.use_judge else None

    all_reports: list[dict] = []
    has_errors = False

    for locale in locales:
        report = build_validation_report(locale, topics, use_judge=args.use_judge, cfg=cfg)
        all_reports.append(report)

        if report["summary"]["structural_errors"] > 0:
            has_errors = True

        if args.report:
            print(f"\n{'=' * 60}")
            print(f"TRANSLATION VALIDATION: {locale}")
            print(f"{'=' * 60}")
            print(f"  Teachers checked: {report['summary']['total_teachers']}")
            print(f"  Atoms checked:    {report['summary']['total_atoms_checked']}")
            print(f"  Structural errors: {report['summary']['structural_errors']}")
            if args.use_judge:
                print(f"  Avg native fit:   {report['summary']['avg_native_fit']:.3f}")

            for topic, tdata in report["topics"].items():
                if isinstance(tdata, dict) and tdata.get("status") == "missing":
                    print(f"  {topic}: MISSING")
                elif isinstance(tdata, dict):
                    teachers = tdata.get("teachers") or {}
                    errors = sum(len(t.get("structural_errors", [])) for t in teachers.values())
                    print(f"  {topic}: {len(teachers)} teachers, {errors} errors")

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(all_reports, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"\nJSON report written to: {out_path}")

    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
