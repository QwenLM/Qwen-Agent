#!/usr/bin/env python3
"""
Pearl News Article Judge — pearl_news_article_judge.py

Runs expanded Pearl News articles through a 4-gate quality judge (subset of
the 9-gate audiobook comparator). This gates Pearl News expansion output
to the same quality bar as Pearl Prime audiobook scripts.

Gates (from content_type_registry.yaml):
  1. semantic_fidelity (hard)            — facts preserved from draft
  2. native_regional_language_fit (2.5x) — reads as native writing
  3. narrative_flow_cohesion (1.5x)      — single story, not disconnected sections
  4. polish_emotional_impact (2.0x)      — sharp, specific, emotionally resonant

Architecture:
  - Can run standalone on an expanded article HTML file
  - Can be called from run_article_pipeline.py as an optional post-expansion gate
  - Results feed into native_prompts_eval_learn.py (EI V2 weekly cycle)
  - Uses same LLM config as Pearl News expansion (llm_expansion.yaml)

Usage:
  # Judge a single expanded article
  python scripts/pearl_news_article_judge.py \\
    --article artifacts/pearl_news/expanded/article_001.html \\
    --locale ja --template hard_news

  # Judge all articles in a batch directory
  python scripts/pearl_news_article_judge.py \\
    --batch-dir artifacts/pearl_news/expanded/batch_20260307/ \\
    --locale ja

  # Dry-run (validate config only)
  python scripts/pearl_news_article_judge.py --dry-run

  # Output JSON for EI V2 ingestion
  python scripts/pearl_news_article_judge.py \\
    --article article.html --locale ja --template hard_news \\
    --json-out artifacts/pearl_news/quality/article_001_judge.json
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger("article_judge")

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# ─── CONFIG ──────────────────────────────────────────────────────────────────

ARTICLE_GATES = [
    {"gate_id": "semantic_fidelity", "type": "hard", "weight": None},
    {"gate_id": "native_regional_language_fit", "type": "scored", "weight": 2.5},
    {"gate_id": "narrative_flow_cohesion", "type": "scored", "weight": 1.5},
    {"gate_id": "polish_emotional_impact", "type": "scored", "weight": 2.0},
]

# Word count minimums by template type
SECTION_MINIMUMS = {
    "hard_news": {"lede": 50, "news_summary": 120, "youth_impact": 100, "teacher_perspective": 90, "sdg_connection": 60, "forward_look": 50},
    "commentary": {"thesis": 100, "event_reference": 80, "teaching_interpretation": 150, "civic_recommendation": 100, "sdg_reference": 80, "closing_provocation": 60},
    "explainer": {"what_happened": 80, "historical_background": 120, "ethical_spiritual_dimension": 90, "youth_implications": 100, "sdg_policy_tie": 80, "future_outlook": 60},
    "youth_feature": {"youth_narrative": 150, "data_research": 120, "teacher_reflection": 90, "sdg_framework": 80, "solutions": 120},
    "interfaith": {"event_summary": 100, "leaders_present": 80, "themes_of_agreement": 150, "youth_commitments": 100, "sdg_alignment": 80, "next_steps": 50},
}

BANNED_PHRASES = [
    "young people around the world are feeling",
    "now more than ever",
    "in these uncertain times",
    "it remains to be seen",
    "many are saying",
    "as debates continue to rage",
]


def _load_yaml(path: Path) -> dict:
    if not path.exists() or yaml is None:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_llm_config() -> dict[str, Any]:
    for name in ["pearl_news/config/llm_expansion.yaml", "config/audiobook_script/comparator_config.yaml"]:
        path = REPO_ROOT / name
        if path.exists():
            cfg = _load_yaml(path)
            if cfg:
                return cfg
    raise RuntimeError("No LLM config found")


def _load_judge_prompt() -> str:
    path = REPO_ROOT / "prompts" / "article_judge" / "judge_pearl_news_v1.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    raise RuntimeError(f"Judge prompt not found: {path}")


def _load_content_type_registry() -> dict[str, Any]:
    return _load_yaml(REPO_ROOT / "config" / "content_type_registry.yaml")


# ─── RULE-BASED CHECKS (no LLM) ────────────────────────────────────────────

def run_article_checks(html: str, template: str, locale: str) -> dict[str, Any]:
    """Run rule-based article quality checks — no LLM needed."""
    # Strip HTML tags for word counting
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    words = text.split()
    word_count = len(words)

    checks: dict[str, Any] = {
        "word_count": word_count,
        "word_count_pass": word_count >= 600,
    }

    # Banned phrases
    lower_text = text.lower()
    found_banned = [bp for bp in BANNED_PHRASES if bp in lower_text]
    checks["banned_phrases_found"] = found_banned
    checks["banned_phrases_pass"] = len(found_banned) == 0

    # Source line
    checks["source_line_present"] = bool(re.search(r"<p><em>Source:.*</em></p>", html))

    # Teacher format — 3 separate <p> blocks in teacher section
    teacher_paragraphs = re.findall(r"<p>[^<]*(?:teaches|tradition|teaching|reflects|observes|holds)[^<]*</p>", html)
    checks["teacher_paragraph_count"] = len(teacher_paragraphs)
    checks["teacher_format_pass"] = len(teacher_paragraphs) >= 3

    # Localization bridge — check for country-specific reference patterns
    bridge_patterns = {
        "ja": r"(?:Japan|Japanese|Ministry of|Cabinet Office|MEXT|NHK)",
        "zh-CN": r"(?:China|Chinese|State Council|National Bureau|gaokao|tangping)",
        "zh-TW": r"(?:Taiwan|Taiwanese|Judicial Yuan|DGBAS|Mainland Affairs)",
        "en": r"(?:United States|US|UK|Australia|Department of)",
    }
    pattern = bridge_patterns.get(locale, r"")
    if pattern:
        checks["localization_bridge_found"] = bool(re.search(pattern, html))
    else:
        checks["localization_bridge_found"] = True  # Unknown locale — skip

    # SDG specificity — number + title + target
    sdg_match = re.search(r"SDG\s+\d+", html)
    sdg_target = re.search(r"Target\s+\d+\.\w+", html)
    checks["sdg_number_present"] = bool(sdg_match)
    checks["sdg_target_present"] = bool(sdg_target)

    return checks


# ─── LLM JUDGE ──────────────────────────────────────────────────────────────

def call_article_judge(
    html: str,
    template: str,
    locale: str,
    cfg: dict,
    article_id: str = "article_001",
) -> list[dict[str, Any]]:
    """Call LLM judge on an expanded Pearl News article."""
    try:
        import openai
    except ImportError:
        raise RuntimeError("openai package required")

    judge_prompt = _load_judge_prompt()
    model_cfg = cfg.get("judge_model", cfg.get("draft_model", cfg))
    base_url = model_cfg.get("base_url", "http://127.0.0.1:1234/v1")
    api_key = model_cfg.get("api_key", "lm-studio")
    model_id = model_cfg.get("model_id", model_cfg.get("model", "local-model"))
    timeout = float(model_cfg.get("timeout_seconds", model_cfg.get("timeout", 120)))

    user_msg = (
        f"ARTICLE ID: {article_id}\n"
        f"TEMPLATE: {template}\n"
        f"LOCALE: {locale}\n\n"
        f"=== EXPANDED ARTICLE HTML ===\n{html}\n\n"
        "Evaluate this expanded Pearl News article against all 4 gates. "
        "Return a JSON ARRAY only — no preamble, no markdown, no explanation."
    )

    client = openai.OpenAI(base_url=base_url, api_key=api_key)
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": judge_prompt},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.1,
        max_tokens=1500,
        timeout=timeout,
    )

    raw = response.choices[0].message.content or ""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        raw = raw.rsplit("```", 1)[0]

    try:
        results = json.loads(raw.strip())
        if not isinstance(results, list):
            results = [results]
        return results
    except json.JSONDecodeError as e:
        logger.error("Judge output not valid JSON: %s", e)
        return []


# ─── SCORING ────────────────────────────────────────────────────────────────

def score_article(gate_results: list[dict], rule_checks: dict) -> dict[str, Any]:
    """Score an article using both LLM gates and rule-based checks."""
    scored_total = 0.0
    max_scored = 0.0
    all_hard_passed = True
    gate_scores: dict[str, Any] = {}

    for g in gate_results:
        gid = g.get("gate_id", "")
        if gid == "article_checks":
            continue  # Skip the checks object
        gate_def = next((gd for gd in ARTICLE_GATES if gd["gate_id"] == gid), None)
        if not gate_def:
            continue

        passed = g.get("pass", False)
        if gate_def["type"] == "hard":
            if not passed:
                all_hard_passed = False
            gate_scores[gid] = {"pass": passed, "type": "hard"}
        else:
            score = g.get("score") or 0.0
            weight = gate_def["weight"] or 1.0
            scored_total += score * weight
            max_scored += weight
            gate_scores[gid] = {"pass": passed, "score": score, "weight": weight, "type": "scored"}

    aggregate = round(scored_total / max_scored, 4) if max_scored > 0 else 0.0

    # Combine with rule-based checks
    rule_passed = (
        rule_checks.get("word_count_pass", False)
        and rule_checks.get("banned_phrases_pass", False)
        and rule_checks.get("source_line_present", False)
    )

    return {
        "aggregate_score": aggregate,
        "all_hard_gates_passed": all_hard_passed,
        "all_rule_checks_passed": rule_passed,
        "overall_pass": all_hard_passed and rule_passed and aggregate >= 0.70,
        "gate_scores": gate_scores,
        "rule_checks": rule_checks,
    }


# ─── ARTICLE RESULT ────────────────────────────────────────────────────────

def judge_article(
    html: str,
    template: str,
    locale: str,
    cfg: dict,
    article_id: str = "article_001",
    use_llm: bool = True,
) -> dict[str, Any]:
    """Full article judgment — rule checks + optional LLM judge."""
    result: dict[str, Any] = {
        "article_id": article_id,
        "template": template,
        "locale": locale,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    # Rule-based checks (always)
    rule_checks = run_article_checks(html, template, locale)
    result["rule_checks"] = rule_checks

    # LLM judge (if enabled)
    if use_llm:
        try:
            gate_results = call_article_judge(html, template, locale, cfg, article_id)
            result["gate_results"] = gate_results
            result["scoring"] = score_article(gate_results, rule_checks)
        except Exception as e:
            logger.error("LLM judge failed: %s", e)
            result["gate_results"] = []
            result["scoring"] = {
                "aggregate_score": 0.0,
                "all_hard_gates_passed": False,
                "all_rule_checks_passed": rule_checks.get("word_count_pass", False),
                "overall_pass": False,
                "error": str(e),
            }
    else:
        result["gate_results"] = []
        result["scoring"] = {
            "aggregate_score": None,
            "all_hard_gates_passed": None,
            "all_rule_checks_passed": (
                rule_checks.get("word_count_pass", False)
                and rule_checks.get("banned_phrases_pass", False)
                and rule_checks.get("source_line_present", False)
            ),
            "overall_pass": None,
            "rule_only": True,
        }

    return result


# ─── CLI ────────────────────────────────────────────────────────────────────

def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    ap = argparse.ArgumentParser(description="Pearl News Article Judge — 4-gate quality evaluation")
    ap.add_argument("--article", default=None, help="Path to expanded article HTML file")
    ap.add_argument("--batch-dir", default=None, help="Directory of expanded articles")
    ap.add_argument("--locale", default="en", help="Article locale (en, ja, zh-CN, zh-TW)")
    ap.add_argument("--template", default="hard_news",
                    choices=["hard_news", "commentary", "explainer", "youth_feature", "interfaith"],
                    help="Article template type")
    ap.add_argument("--json-out", default=None, help="Write JSON results to file")
    ap.add_argument("--no-llm", action="store_true", help="Rule-based checks only (no LLM judge)")
    ap.add_argument("--dry-run", action="store_true", help="Validate config only")
    args = ap.parse_args()

    if args.dry_run:
        try:
            cfg = _load_llm_config()
            prompt = _load_judge_prompt()
            registry = _load_content_type_registry()
            ct_count = len(registry.get("content_types", {}))
            print(f"Config loaded: {len(cfg)} keys")
            print(f"Judge prompt: {len(prompt)} chars")
            print(f"Content type registry: {ct_count} types")
            print(f"Article gates: {[g['gate_id'] for g in ARTICLE_GATES]}")
            return 0
        except Exception as e:
            print(f"Config error: {e}")
            return 2

    if not args.article and not args.batch_dir:
        ap.print_help()
        return 0

    cfg = _load_llm_config()
    use_llm = not args.no_llm
    results: list[dict] = []

    if args.article:
        html = Path(args.article).read_text(encoding="utf-8")
        article_id = Path(args.article).stem
        result = judge_article(html, args.template, args.locale, cfg, article_id, use_llm)
        results.append(result)

        # Print summary
        scoring = result.get("scoring", {})
        print(f"\nArticle: {article_id}")
        print(f"  Locale: {args.locale}")
        print(f"  Template: {args.template}")
        print(f"  Word count: {result['rule_checks'].get('word_count', 0)}")
        print(f"  Rule checks: {'PASS' if scoring.get('all_rule_checks_passed') else 'FAIL'}")
        if use_llm:
            print(f"  Hard gates: {'PASS' if scoring.get('all_hard_gates_passed') else 'FAIL'}")
            print(f"  Aggregate score: {scoring.get('aggregate_score', 0):.3f}")
            print(f"  Overall: {'PASS' if scoring.get('overall_pass') else 'FAIL'}")
        banned = result['rule_checks'].get('banned_phrases_found', [])
        if banned:
            print(f"  Banned phrases: {banned}")

    if args.batch_dir:
        batch_path = Path(args.batch_dir)
        for html_file in sorted(batch_path.glob("*.html")):
            html = html_file.read_text(encoding="utf-8")
            result = judge_article(html, args.template, args.locale, cfg, html_file.stem, use_llm)
            results.append(result)
            scoring = result.get("scoring", {})
            status = "PASS" if scoring.get("overall_pass") else "FAIL"
            score = scoring.get("aggregate_score", 0)
            print(f"  {html_file.stem}: {status} (score={score:.3f})")

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nJSON results written to: {out_path}")

    # Exit code: 0 if all pass, 1 if any fail
    all_pass = all(r.get("scoring", {}).get("overall_pass", False) for r in results)
    return 0 if (all_pass or not use_llm) else 1


if __name__ == "__main__":
    sys.exit(main())
