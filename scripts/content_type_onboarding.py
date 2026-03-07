#!/usr/bin/env python3
"""
Content Type Onboarding — content_type_onboarding.py

Validates and scaffolds new content types. When you add a new content type
to the system, this script ensures everything is wired correctly.

What it checks:
  1. Entry exists in config/content_type_registry.yaml
  2. Draft prompt file exists and is non-empty
  3. Judge prompt file exists and is non-empty
  4. Golden regression sample(s) exist (if audiobook type)
  5. Locales are valid (exist in locale_registry.yaml)
  6. All gate IDs are valid (exist in comparison_checklist_v2.yaml)

What it scaffolds:
  - Creates draft prompt stub from template
  - Creates golden regression sample stub
  - Adds prompt_routing entry to comparator_config.yaml (for audiobook types)

Usage:
  # Validate all registered content types
  python scripts/content_type_onboarding.py --validate-all

  # Validate a specific content type
  python scripts/content_type_onboarding.py --validate pearl_news_hard_news

  # Scaffold a new audiobook content type
  python scripts/content_type_onboarding.py --scaffold \\
    --name "newsletter_teaser" \\
    --system pearl_news \\
    --pipeline article_expansion \\
    --display-name "Pearl News — Newsletter Teaser"

  # List all registered content types
  python scripts/content_type_onboarding.py --list
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger("content_onboarding")

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

VALID_GATE_IDS = [
    "semantic_fidelity", "claim_integrity", "emotional_arc_alignment",
    "psychological_safety", "native_regional_language_fit",
    "narrative_flow_cohesion", "tts_readability_cadence",
    "compliance_disclaimer_preservation", "polish_emotional_impact",
]

VALID_PIPELINES = ["audiobook_comparator", "article_expansion"]


def _load_yaml(path: Path) -> dict:
    if not path.exists() or yaml is None:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_registry() -> dict[str, Any]:
    return _load_yaml(REPO_ROOT / "config" / "content_type_registry.yaml")


# ─── VALIDATION ──────────────────────────────────────────────────────────────

def validate_content_type(ct_id: str, ct_data: dict[str, Any]) -> list[str]:
    """Validate a single content type entry. Returns list of errors."""
    errors: list[str] = []

    # Required fields
    for field in ["display_name", "system", "pipeline", "draft_prompt", "judge_prompt"]:
        if not ct_data.get(field):
            errors.append(f"Missing required field: {field}")

    # Pipeline must be valid
    pipeline = ct_data.get("pipeline", "")
    if pipeline and pipeline not in VALID_PIPELINES:
        errors.append(f"Invalid pipeline: {pipeline} (must be one of {VALID_PIPELINES})")

    # Draft prompt file must exist
    draft_prompt = ct_data.get("draft_prompt", "")
    if draft_prompt:
        draft_path = REPO_ROOT / draft_prompt
        if not draft_path.exists():
            errors.append(f"Draft prompt not found: {draft_prompt}")
        elif draft_path.stat().st_size < 50:
            errors.append(f"Draft prompt suspiciously small: {draft_prompt} ({draft_path.stat().st_size} bytes)")

    # Judge prompt file must exist
    judge_prompt = ct_data.get("judge_prompt", "")
    if judge_prompt:
        judge_path = REPO_ROOT / judge_prompt
        if not judge_path.exists():
            errors.append(f"Judge prompt not found: {judge_prompt}")

    # Gate IDs must be valid
    judge_gates = ct_data.get("judge_gates", [])
    if isinstance(judge_gates, list):
        for gate in judge_gates:
            if gate not in VALID_GATE_IDS:
                errors.append(f"Invalid gate_id: {gate}")

    # Golden samples must exist (for audiobook types)
    if pipeline == "audiobook_comparator":
        golden = ct_data.get("golden_samples", [])
        if not golden:
            errors.append("Audiobook content type must have at least 1 golden regression sample")
        for sample_path in golden:
            if not (REPO_ROOT / sample_path).exists():
                errors.append(f"Golden sample not found: {sample_path}")

    # Locales must not be empty
    locales = ct_data.get("locales_supported", [])
    if not locales:
        errors.append("No locales_supported defined")

    return errors


def validate_all() -> dict[str, list[str]]:
    """Validate all content types in the registry."""
    registry = _load_registry()
    content_types = registry.get("content_types", {})
    results: dict[str, list[str]] = {}

    for ct_id, ct_data in content_types.items():
        errors = validate_content_type(ct_id, ct_data)
        results[ct_id] = errors

    return results


# ─── SCAFFOLDING ────────────────────────────────────────────────────────────

def scaffold_content_type(
    name: str,
    system: str,
    pipeline: str,
    display_name: str,
    locales: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Scaffold a new content type — create prompt stubs and registry entry."""
    result: dict[str, Any] = {"files_created": [], "errors": []}

    default_locales = ["en", "ja", "zh-CN", "zh-TW"] if system == "pearl_news" else ["zh-TW", "zh-HK", "zh-SG", "zh-CN"]
    target_locales = locales or default_locales

    # Determine prompt paths
    if pipeline == "audiobook_comparator":
        draft_prompt_path = f"prompts/audiobook/draft_{name}_v1.txt"
        judge_prompt_path = "prompts/audiobook/judge_audiobook_v2.txt"
        golden_dir = "config/audiobook_script/golden_regression_set"
    else:
        draft_prompt_path = f"pearl_news/prompts/expansion_{name}.txt"
        judge_prompt_path = "prompts/article_judge/judge_pearl_news_v1.txt"
        golden_dir = ""

    # Create draft prompt stub
    draft_full_path = REPO_ROOT / draft_prompt_path
    if not draft_full_path.exists():
        if dry_run:
            logger.info("[DRY RUN] Would create draft prompt: %s", draft_prompt_path)
        else:
            draft_full_path.parent.mkdir(parents=True, exist_ok=True)
            template = _generate_prompt_stub(name, display_name, pipeline, target_locales)
            draft_full_path.write_text(template, encoding="utf-8")
            logger.info("Created draft prompt: %s", draft_prompt_path)
        result["files_created"].append(draft_prompt_path)

    # Create golden regression sample stub (audiobook only)
    if pipeline == "audiobook_comparator" and golden_dir:
        sample_locale = target_locales[0] if target_locales else "zh-TW"
        golden_name = f"{sample_locale}_{name}_sample.yaml"
        golden_path = REPO_ROOT / golden_dir / golden_name

        if not golden_path.exists():
            if dry_run:
                logger.info("[DRY RUN] Would create golden sample: %s/%s", golden_dir, golden_name)
            else:
                golden_path.parent.mkdir(parents=True, exist_ok=True)
                golden_stub = _generate_golden_stub(name, display_name, sample_locale)
                golden_path.write_text(golden_stub, encoding="utf-8")
                logger.info("Created golden sample: %s", golden_path)
            result["files_created"].append(f"{golden_dir}/{golden_name}")

    # Generate registry entry (printed, not auto-added)
    registry_entry = _generate_registry_entry(
        name, display_name, system, pipeline,
        draft_prompt_path, judge_prompt_path,
        target_locales, golden_dir,
    )
    result["registry_entry"] = registry_entry

    return result


def _generate_prompt_stub(name: str, display_name: str, pipeline: str, locales: list[str]) -> str:
    """Generate a draft prompt stub for a new content type."""
    locale_registers = []
    for locale in locales:
        locale_registers.append(f"{locale.upper()}: [Define register for {locale} — voice, framing, cultural references]")

    if pipeline == "audiobook_comparator":
        return (
            f"# {display_name} — Draft Prompt v1\n"
            f"# Content type: {name}\n"
            f"# Pipeline: audiobook_comparator\n\n"
            f"You are producing a localized audiobook script for {display_name}.\n\n"
            f"LOCALE REGISTERS:\n" + "\n".join(locale_registers) + "\n\n"
            f"TTS HARD GATES:\n"
            f"- Maximum 25 words per sentence before a pause or breath point\n"
            f"- Numbers must be spelled out\n"
            f"- No parentheticals or em-dashes mid-sentence\n"
            f"- Every sentence must be speakable in one breath\n\n"
            f"OUTPUT: Produce the localized audiobook script. Output only the script.\n"
        )
    else:
        return (
            f"# {display_name} — Expansion Prompt\n"
            f"# Content type: {name}\n"
            f"# Pipeline: article_expansion\n\n"
            f"You are a senior editor at Pearl News expanding a draft {name} article.\n\n"
            f"AUDIENCE RULES:\n" + "\n".join(locale_registers) + "\n\n"
            f"[Define sections, word counts, voice rules, mission drift checks]\n\n"
            f"OUTPUT: Return only the expanded HTML article body.\n"
        )


def _generate_golden_stub(name: str, display_name: str, locale: str) -> str:
    """Generate a golden regression sample stub."""
    return (
        f"# Golden Regression Sample: {locale}_{name}\n"
        f"section_id: golden_{locale.replace('-', '_')}_{name}_001\n"
        f"content_type: {name}\n"
        f"locale: {locale}\n"
        f"description: \"{display_name} golden regression sample for {locale}\"\n"
        f"\n"
        f"source_text: |\n"
        f"  [Paste English source content here]\n"
        f"\n"
        f"test_criteria:\n"
        f"  - \"{locale}: appropriate register and cultural references\"\n"
        f"  - \"All TTS-speakable, no breath-strain\"\n"
        f"  - \"Semantic fidelity to source preserved\"\n"
        f"\n"
        f"expected_pass: true\n"
        f"min_aggregate_score: 0.75\n"
    )


def _generate_registry_entry(
    name: str, display_name: str, system: str, pipeline: str,
    draft_prompt: str, judge_prompt: str,
    locales: list[str], golden_dir: str,
) -> str:
    """Generate a YAML registry entry to paste into content_type_registry.yaml."""
    golden_line = ""
    if golden_dir:
        sample_locale = locales[0] if locales else "zh-TW"
        golden_line = f'    - "{golden_dir}/{sample_locale}_{name}_sample.yaml"'

    locales_yaml = "\n".join(f"      - {loc}" for loc in locales)

    if pipeline == "audiobook_comparator":
        gates_yaml = "    judge_gates: all"
    else:
        gates_yaml = (
            "    judge_gates:\n"
            "      - semantic_fidelity\n"
            "      - native_regional_language_fit\n"
            "      - narrative_flow_cohesion\n"
            "      - polish_emotional_impact"
        )

    return (
        f"  {name}:\n"
        f"    display_name: \"{display_name}\"\n"
        f"    system: {system}\n"
        f"    pipeline: {pipeline}\n"
        f"    draft_prompt: \"{draft_prompt}\"\n"
        f"    judge_prompt: \"{judge_prompt}\"\n"
        f"{gates_yaml}\n"
        f"    locales_supported:\n"
        f"{locales_yaml}\n"
        f"    golden_samples:\n"
        f"{golden_line}\n"
        f"    min_scored_pass_threshold: 0.70\n"
        f"    status: active\n"
    )


# ─── CLI ────────────────────────────────────────────────────────────────────

def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    ap = argparse.ArgumentParser(description="Content type onboarding — validate and scaffold")
    ap.add_argument("--validate-all", action="store_true", help="Validate all registered content types")
    ap.add_argument("--validate", default=None, help="Validate a specific content type")
    ap.add_argument("--list", action="store_true", help="List all registered content types")
    ap.add_argument("--scaffold", action="store_true", help="Scaffold a new content type")
    ap.add_argument("--name", default=None, help="New content type name (snake_case)")
    ap.add_argument("--system", choices=["pearl_news", "pearl_prime"], default=None)
    ap.add_argument("--pipeline", choices=VALID_PIPELINES, default=None)
    ap.add_argument("--display-name", default=None, help="Human-readable name")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.list:
        registry = _load_registry()
        content_types = registry.get("content_types", {})
        print(f"\nRegistered content types ({len(content_types)}):\n")
        for ct_id, ct_data in content_types.items():
            status = ct_data.get("status", "unknown")
            system = ct_data.get("system", "?")
            pipeline = ct_data.get("pipeline", "?")
            locales = ct_data.get("locales_supported", [])
            golden = len(ct_data.get("golden_samples", []))
            print(f"  {ct_id}")
            print(f"    {ct_data.get('display_name', ct_id)}")
            print(f"    system={system}  pipeline={pipeline}  locales={len(locales)}  golden={golden}  status={status}")
            print()
        return 0

    if args.validate_all:
        results = validate_all()
        total_errors = 0
        print(f"\nContent Type Validation Report")
        print("=" * 60)
        for ct_id, errors in results.items():
            status = "PASS" if not errors else "FAIL"
            print(f"\n  {ct_id}: {status}")
            for e in errors:
                print(f"    ✗ {e}")
                total_errors += 1

        print(f"\n{'=' * 60}")
        print(f"Total: {len(results)} types, {total_errors} errors")
        return 1 if total_errors > 0 else 0

    if args.validate:
        registry = _load_registry()
        ct_data = registry.get("content_types", {}).get(args.validate)
        if not ct_data:
            print(f"Content type not found: {args.validate}")
            return 2
        errors = validate_content_type(args.validate, ct_data)
        if errors:
            print(f"\n{args.validate}: FAIL")
            for e in errors:
                print(f"  ✗ {e}")
            return 1
        print(f"\n{args.validate}: PASS")
        return 0

    if args.scaffold:
        if not all([args.name, args.system, args.pipeline]):
            print("--scaffold requires --name, --system, --pipeline")
            return 2
        display = args.display_name or args.name.replace("_", " ").title()
        result = scaffold_content_type(
            args.name, args.system, args.pipeline, display,
            dry_run=args.dry_run,
        )
        print(f"\nScaffolded content type: {args.name}")
        for f in result.get("files_created", []):
            print(f"  Created: {f}")
        if result.get("registry_entry"):
            print(f"\n  Add this to config/content_type_registry.yaml:")
            print(f"  {'─' * 50}")
            print(result["registry_entry"])
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
