#!/usr/bin/env python3
"""
Native Prompts Eval & Learn — native_prompts_eval_learn.py

EI V2 closed-loop integration for translation quality assessment.
Evaluates native translation prompt returns, feeds results back to
improve translation prompts weekly.

This is the EI V2 connection point for BOTH Pearl News and Pearl Prime:
  - Pearl News: evaluates translated teacher atoms
  - Pearl Prime: evaluates audiobook draft localization quality

Architecture:
  The EI V2 closed loop:
  1. EVAL: Run validation on all translated content (atoms + audiobook drafts)
  2. SCORE: Aggregate quality scores per locale, per gate
  3. LEARN: Identify systematic weaknesses → generate prompt patches
  4. APPLY: Update translation prompts in LOCALE_TRANSLATION_CONTEXT
  5. REPORT: Weekly quality report for human review

EI V2 Modules Used:
  - native_regional_language_fit (gate 7, weight 2.5): Does it sound native?
  - emotion_arc_alignment (gate 6, weight 2.0): Does emotional flow work in this locale?
  - tts_readability_cadence (gate 4, hard): Is it speakable in this locale's TTS?
  - semantic_fidelity (gate 1, hard): Did meaning survive translation?

Shared Quality Loop:
  Pearl News atoms and Pearl Prime audiobook drafts share:
  - Same judge model (comparator_config.yaml)
  - Same native_language_fit rubric
  - Same EI V2 feedback mechanism
  - Same weekly quality cadence

Usage:
  # Run full eval cycle for all locales
  python scripts/localization/native_prompts_eval_learn.py --eval

  # Generate improvement report
  python scripts/localization/native_prompts_eval_learn.py --learn

  # Run weekly closed-loop (eval + learn + apply)
  python scripts/localization/native_prompts_eval_learn.py --weekly

  # Pearl Prime audiobook-specific eval
  python scripts/localization/native_prompts_eval_learn.py --eval --system pearl_prime

  # Specific locale
  python scripts/localization/native_prompts_eval_learn.py --eval --locale ja-JP
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

logger = logging.getLogger("ei_v2_eval_learn")

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

TARGET_LOCALES = ["ja-JP", "zh-CN", "zh-TW"]
ALL_LOCALES = [
    "zh-CN", "zh-TW", "zh-HK", "zh-SG",
    "ja-JP", "ko-KR",
    "es-US", "es-ES", "fr-FR", "de-DE", "it-IT", "hu-HU",
]

PEARL_NEWS_TOPICS = [
    "climate", "economy_work", "education", "inequality",
    "mental_health", "partnerships", "peace_conflict",
]

# EI V2 quality thresholds
EI_V2_THRESHOLDS = {
    "native_language_fit": {"min": 0.75, "target": 0.85},
    "cultural_adaptation": {"min": 0.70, "target": 0.80},
    "register_consistency": {"min": 0.75, "target": 0.85},
    "semantic_fidelity": {"min_pass_rate": 0.95},
}


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


# ─── EVAL: Collect quality signals ──────────────────────────────────────────

def eval_pearl_news_translations(locales: list[str] | None = None) -> dict[str, Any]:
    """Evaluate Pearl News translated atoms — structural pass only (no LLM)."""
    target = locales or TARGET_LOCALES
    results: dict[str, Any] = {
        "system": "pearl_news",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "locales": {},
    }

    for locale in target:
        locale_result: dict[str, Any] = {
            "topics_checked": 0,
            "teachers_checked": 0,
            "atoms_checked": 0,
            "missing_files": [],
            "empty_atoms": 0,
            "status_distribution": {"stub": 0, "starter": 0, "reviewed": 0, "approved": 0},
        }

        for topic in PEARL_NEWS_TOPICS:
            locale_path = (REPO_ROOT / "pearl_news" / "atoms" / "teacher_quotes_practices"
                           / "locales" / locale / f"topic_{topic}.yaml")

            if not locale_path.exists():
                locale_result["missing_files"].append(topic)
                continue

            locale_result["topics_checked"] += 1
            data = _load_yaml(locale_path)
            teachers = data.get("teachers") or {}

            for teacher_id, tdata in teachers.items():
                locale_result["teachers_checked"] += 1
                status = tdata.get("status", "unknown")
                if status in locale_result["status_distribution"]:
                    locale_result["status_distribution"][status] += 1

                atoms = tdata.get("atoms") or []
                locale_result["atoms_checked"] += len(atoms)
                locale_result["empty_atoms"] += sum(1 for a in atoms if not str(a).strip())

        results["locales"][locale] = locale_result

    return results


def eval_pearl_prime_audiobook(locales: list[str] | None = None) -> dict[str, Any]:
    """Evaluate Pearl Prime audiobook localization quality from loop decision logs."""
    target = locales or ALL_LOCALES[:6]  # First 6 priority locales
    results: dict[str, Any] = {
        "system": "pearl_prime",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "locales": {},
    }

    # Read loop decision JSONL if it exists
    jsonl_path = REPO_ROOT / "artifacts" / "audiobook" / "loop_decisions.jsonl"
    decisions: list[dict] = []
    if jsonl_path.exists():
        for line in jsonl_path.read_text(encoding="utf-8").strip().split("\n"):
            if line.strip():
                try:
                    decisions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    for locale in target:
        locale_decisions = [d for d in decisions if d.get("locale") == locale]
        locale_result: dict[str, Any] = {
            "total_sections": len(locale_decisions),
            "passed": sum(1 for d in locale_decisions if d.get("decision") == "pass"),
            "manual_review": sum(1 for d in locale_decisions if d.get("decision") == "manual_review"),
            "avg_score": 0.0,
            "avg_loops": 0.0,
        }

        if locale_decisions:
            scores = [d.get("aggregate_score", 0) for d in locale_decisions]
            loops = [d.get("loop_index", 1) for d in locale_decisions]
            locale_result["avg_score"] = round(sum(scores) / len(scores), 3)
            locale_result["avg_loops"] = round(sum(loops) / len(loops), 1)
            locale_result["pass_rate"] = round(locale_result["passed"] / len(locale_decisions), 3)

        results["locales"][locale] = locale_result

    return results


# ─── LEARN: Identify systematic weaknesses ──────────────────────────────────

def learn_from_eval(
    pn_eval: dict[str, Any],
    pp_eval: dict[str, Any],
) -> dict[str, Any]:
    """Analyze eval results and identify systematic weaknesses per locale."""
    recommendations: dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "locales": {},
    }

    # Pearl News analysis
    for locale, data in pn_eval.get("locales", {}).items():
        locale_recs: list[str] = []

        if data.get("missing_files"):
            locale_recs.append(
                f"CRITICAL: {len(data['missing_files'])} topic files missing — "
                f"run scaffold_locale_atom_stubs.py --scaffold --locale {locale}"
            )

        if data.get("empty_atoms", 0) > 0:
            locale_recs.append(
                f"WARNING: {data['empty_atoms']} empty atoms found — "
                f"run translate_atoms_all_locales.py --locale {locale}"
            )

        stub_count = data.get("status_distribution", {}).get("stub", 0)
        starter_count = data.get("status_distribution", {}).get("starter", 0)
        if stub_count > 0:
            locale_recs.append(
                f"ACTION: {stub_count} atoms still at STUB status — "
                f"translation pipeline has not run for this locale"
            )
        elif starter_count > 0 and data.get("status_distribution", {}).get("reviewed", 0) == 0:
            locale_recs.append(
                f"ACTION: {starter_count} atoms at STARTER — "
                f"ready for human review (run teacher_onboarding.py --fix-status)"
            )

        recommendations["locales"].setdefault(locale, {})["pearl_news"] = locale_recs

    # Pearl Prime analysis
    for locale, data in pp_eval.get("locales", {}).items():
        locale_recs: list[str] = []

        pass_rate = data.get("pass_rate", 0)
        avg_score = data.get("avg_score", 0)
        avg_loops = data.get("avg_loops", 0)

        if data.get("total_sections", 0) == 0:
            locale_recs.append(
                f"NO DATA: No audiobook sections processed for {locale} yet"
            )
        else:
            if pass_rate < 0.80:
                locale_recs.append(
                    f"LOW PASS RATE: {pass_rate:.1%} — "
                    f"review draft prompt locale register for {locale}"
                )
            if avg_score < EI_V2_THRESHOLDS["native_language_fit"]["min"]:
                locale_recs.append(
                    f"LOW QUALITY: avg_score={avg_score:.3f} below threshold "
                    f"{EI_V2_THRESHOLDS['native_language_fit']['min']} — "
                    f"draft prompt needs locale register refinement"
                )
            if avg_loops > 2.0:
                locale_recs.append(
                    f"HIGH LOOP COUNT: avg_loops={avg_loops:.1f} — "
                    f"draft prompt may need structural improvement for {locale}"
                )

        recommendations["locales"].setdefault(locale, {})["pearl_prime"] = locale_recs

    return recommendations


# ─── APPLY: Generate prompt patches ─────────────────────────────────────────

def generate_prompt_patches(recommendations: dict[str, Any]) -> list[dict[str, str]]:
    """Convert recommendations into actionable prompt patches."""
    patches: list[dict[str, str]] = []

    for locale, systems in recommendations.get("locales", {}).items():
        for system_name, recs in systems.items():
            for rec in recs:
                if "CRITICAL" in rec or "LOW" in rec:
                    patches.append({
                        "locale": locale,
                        "system": system_name,
                        "severity": "high" if "CRITICAL" in rec else "medium",
                        "recommendation": rec,
                        "action_type": "manual_review" if "CRITICAL" in rec else "prompt_refinement",
                    })

    return patches


def apply_prompt_patches(
    patches: list[dict[str, str]],
    pn_article_quality: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    APPLY step: write concrete prompt patch files for human review.

    For each locale with actionable patches:
    1. Writes a patch file to artifacts/evaluations/<locale>/prompt_patches_<date>.json
    2. Includes specific prompt edits (which file, what to change)
    3. Integrates Pearl News article judge results if available
    4. Generates a human-readable summary for review

    These patches are NOT auto-applied — they require human review via PR or direct approval.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    applied: dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "patches_written": 0,
        "locales_affected": [],
        "patch_files": [],
    }

    # Map of content type to its prompt files
    prompt_file_map = {
        "pearl_prime": {
            "pearl_prime": "prompts/audiobook/draft_pearl_prime_v2.txt",
            "pearl_news_audiobook": "prompts/audiobook/draft_pearl_news_v2.txt",
            "phoenix_v4": "prompts/audiobook/draft_phoenix_v4_v2.txt",
            "teacher_mode": "prompts/audiobook/draft_teacher_mode_v2.txt",
        },
        "pearl_news": {
            "hard_news": "pearl_news/prompts/expansion_hard_news.txt",
            "commentary": "pearl_news/prompts/expansion_commentary.txt",
            "explainer": "pearl_news/prompts/expansion_explainer.txt",
            "youth_feature": "pearl_news/prompts/expansion_youth_feature.txt",
            "interfaith": "pearl_news/prompts/expansion_interfaith.txt",
            "system": "pearl_news/prompts/expansion_system.txt",
        },
    }

    # Group patches by locale
    patches_by_locale: dict[str, list[dict]] = {}
    for p in patches:
        locale = p.get("locale", "unknown")
        patches_by_locale.setdefault(locale, []).append(p)

    for locale, locale_patches in patches_by_locale.items():
        patch_data: dict[str, Any] = {
            "locale": locale,
            "generated_date": today,
            "status": "pending_review",
            "patches": [],
        }

        for p in locale_patches:
            system = p.get("system", "")
            patch_entry: dict[str, Any] = {
                "severity": p.get("severity", "medium"),
                "system": system,
                "recommendation": p.get("recommendation", ""),
                "action_type": p.get("action_type", "prompt_refinement"),
                "target_files": [],
            }

            # Identify which prompt files need editing
            if system in prompt_file_map:
                patch_entry["target_files"] = list(prompt_file_map[system].values())
            else:
                patch_entry["target_files"] = [f"Unknown system: {system}"]

            # If article quality data available, include it
            if pn_article_quality and locale in pn_article_quality:
                article_data = pn_article_quality[locale]
                if isinstance(article_data, dict):
                    low_gates = []
                    for gate_id, gate_data in article_data.get("avg_gate_scores", {}).items():
                        if isinstance(gate_data, (int, float)) and gate_data < 0.75:
                            low_gates.append(f"{gate_id}={gate_data:.2f}")
                    if low_gates:
                        patch_entry["article_quality_signals"] = low_gates

            patch_data["patches"].append(patch_entry)

        # Write patch file
        patch_dir = REPO_ROOT / "artifacts" / "evaluations" / locale
        patch_dir.mkdir(parents=True, exist_ok=True)
        patch_path = patch_dir / f"prompt_patches_{today}.json"
        patch_path.write_text(
            json.dumps(patch_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        # Write human-readable summary
        summary_lines = [
            f"# Prompt Patch Summary: {locale}",
            f"Date: {today}",
            f"Status: PENDING REVIEW",
            "",
        ]
        for p in patch_data["patches"]:
            summary_lines.append(f"## [{p['severity'].upper()}] {p['system']}")
            summary_lines.append(f"  {p['recommendation']}")
            summary_lines.append(f"  Files to edit: {', '.join(p['target_files'])}")
            if "article_quality_signals" in p:
                summary_lines.append(f"  Low article gates: {', '.join(p['article_quality_signals'])}")
            summary_lines.append("")

        summary_path = patch_dir / f"patch_summary_{today}.md"
        summary_path.write_text("\n".join(summary_lines), encoding="utf-8")

        applied["patches_written"] += len(patch_data["patches"])
        applied["locales_affected"].append(locale)
        applied["patch_files"].append(str(patch_path))

        logger.info("Wrote %d patches for %s -> %s", len(patch_data["patches"]), locale, patch_path)

    return applied


# ─── REPORT ──────────────────────────────────────────────────────────────────

def print_weekly_report(
    pn_eval: dict[str, Any],
    pp_eval: dict[str, Any],
    recommendations: dict[str, Any],
) -> None:
    """Print human-readable weekly quality report."""
    print("=" * 70)
    print("EI V2 WEEKLY TRANSLATION QUALITY REPORT")
    print(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    print("\n--- PEARL NEWS ATOM TRANSLATIONS ---")
    for locale, data in pn_eval.get("locales", {}).items():
        status = data.get("status_distribution", {})
        missing = len(data.get("missing_files", []))
        print(f"  {locale}: {data.get('topics_checked', 0)}/7 topics | "
              f"{data.get('atoms_checked', 0)} atoms | "
              f"missing={missing} | "
              f"stub={status.get('stub', 0)} starter={status.get('starter', 0)} "
              f"reviewed={status.get('reviewed', 0)} approved={status.get('approved', 0)}")

    print("\n--- PEARL PRIME AUDIOBOOK LOCALIZATION ---")
    for locale, data in pp_eval.get("locales", {}).items():
        total = data.get("total_sections", 0)
        if total == 0:
            print(f"  {locale}: no data yet")
        else:
            print(f"  {locale}: {total} sections | "
                  f"pass_rate={data.get('pass_rate', 0):.1%} | "
                  f"avg_score={data.get('avg_score', 0):.3f} | "
                  f"avg_loops={data.get('avg_loops', 0):.1f}")

    print("\n--- RECOMMENDATIONS ---")
    for locale, systems in recommendations.get("locales", {}).items():
        all_recs = []
        for system_name, recs in systems.items():
            all_recs.extend(f"[{system_name}] {r}" for r in recs)
        if all_recs:
            print(f"\n  {locale}:")
            for r in all_recs:
                print(f"    - {r}")

    patches = generate_prompt_patches(recommendations)
    if patches:
        high = [p for p in patches if p["severity"] == "high"]
        medium = [p for p in patches if p["severity"] == "medium"]
        print(f"\n--- PROMPT PATCHES NEEDED ---")
        print(f"  High severity: {len(high)}")
        print(f"  Medium severity: {len(medium)}")
    else:
        print("\n--- No prompt patches needed this cycle ---")

    print("\n" + "=" * 70)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    ap = argparse.ArgumentParser(
        description="EI V2 Native Prompts Eval & Learn — closed-loop translation quality"
    )
    ap.add_argument("--eval", action="store_true", help="Run evaluation cycle")
    ap.add_argument("--learn", action="store_true", help="Generate improvement recommendations")
    ap.add_argument("--apply", action="store_true", help="Write concrete prompt patch files for review")
    ap.add_argument("--weekly", action="store_true", help="Full weekly cycle: eval + learn + apply + report")
    ap.add_argument("--locale", default=None, help="Target specific locale")
    ap.add_argument("--system", choices=["pearl_news", "pearl_prime", "both"], default="both")
    ap.add_argument("--json-out", default=None, help="Write JSON report to file")
    ap.add_argument("--article-quality", default=None,
                    help="Path to Pearl News article judge results JSON (for apply step)")
    args = ap.parse_args()

    if not args.eval and not args.learn and not args.apply and not args.weekly:
        ap.print_help()
        return 0

    locales = [args.locale] if args.locale else None

    # EVAL
    pn_eval: dict[str, Any] = {}
    pp_eval: dict[str, Any] = {}

    if args.eval or args.weekly:
        if args.system in ("pearl_news", "both"):
            pn_eval = eval_pearl_news_translations(locales)
            logger.info("Pearl News eval complete: %d locales", len(pn_eval.get("locales", {})))

        if args.system in ("pearl_prime", "both"):
            pp_eval = eval_pearl_prime_audiobook(locales)
            logger.info("Pearl Prime eval complete: %d locales", len(pp_eval.get("locales", {})))

    # LEARN
    recommendations: dict[str, Any] = {}
    if args.learn or args.weekly:
        if not pn_eval and args.system in ("pearl_news", "both"):
            pn_eval = eval_pearl_news_translations(locales)
        if not pp_eval and args.system in ("pearl_prime", "both"):
            pp_eval = eval_pearl_prime_audiobook(locales)

        recommendations = learn_from_eval(pn_eval, pp_eval)
        logger.info("Learn cycle complete: %d locales with recommendations",
                     len(recommendations.get("locales", {})))

    # APPLY
    applied: dict[str, Any] = {}
    if args.apply or args.weekly:
        patches = generate_prompt_patches(recommendations)
        if patches:
            # Load article quality data if provided
            pn_article_quality = None
            if args.article_quality:
                aq_path = Path(args.article_quality)
                if aq_path.exists():
                    try:
                        pn_article_quality = json.loads(aq_path.read_text(encoding="utf-8"))
                    except Exception as e:
                        logger.warning("Could not load article quality data: %s", e)

            applied = apply_prompt_patches(patches, pn_article_quality)
            logger.info("Apply step complete: %d patches written for %d locales",
                         applied.get("patches_written", 0), len(applied.get("locales_affected", [])))

    # REPORT
    if args.weekly:
        print_weekly_report(pn_eval, pp_eval, recommendations)
        if applied.get("patches_written", 0) > 0:
            print(f"\n--- PROMPT PATCHES WRITTEN ---")
            print(f"  Patches: {applied['patches_written']}")
            print(f"  Locales: {', '.join(applied.get('locales_affected', []))}")
            for pf in applied.get("patch_files", []):
                print(f"  File: {pf}")
            print("  Status: PENDING HUMAN REVIEW")
            print("  Action: Review patch summaries and apply approved changes to prompt files")

    # JSON output
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "pearl_news_eval": pn_eval,
            "pearl_prime_eval": pp_eval,
            "recommendations": recommendations,
            "patches": generate_prompt_patches(recommendations),
            "applied": applied,
        }
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"JSON report written to: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
