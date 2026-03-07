#!/usr/bin/env python3
"""
Scaffold Locale Atom Stubs — scaffold_locale_atom_stubs.py

Creates empty locale-specific atom YAML stubs for all non-en-US locales
defined in config/localization/locale_registry.yaml.

For Pearl News: creates pearl_news/atoms/teacher_quotes_practices/locales/<locale>/topic_<topic>.yaml
For Pearl Prime: creates atoms/<locale>/ directory structure matching content_roots_by_locale.yaml

Usage:
  # Audit what stubs are missing (dry-run)
  python scripts/localization/scaffold_locale_atom_stubs.py --audit

  # Create all missing stubs
  python scripts/localization/scaffold_locale_atom_stubs.py --scaffold

  # Scaffold for a specific locale only
  python scripts/localization/scaffold_locale_atom_stubs.py --scaffold --locale ja-JP

  # Scaffold for Pearl News only
  python scripts/localization/scaffold_locale_atom_stubs.py --scaffold --system pearl_news

  # Scaffold for Pearl Prime (audiobook) only
  python scripts/localization/scaffold_locale_atom_stubs.py --scaffold --system pearl_prime
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger("scaffold_locale_stubs")

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

# ─── LOCALE REGISTRY ─────────────────────────────────────────────────────────

# Locales that get Pearl News atom translations
PEARL_NEWS_LOCALES = ["ja-JP", "zh-CN", "zh-TW"]

# All 13 system locales (Pearl Prime audiobook)
ALL_LOCALES = [
    "zh-CN", "zh-TW", "zh-HK", "zh-SG",
    "ja-JP", "ko-KR",
    "es-US", "es-ES", "fr-FR", "de-DE", "it-IT", "hu-HU",
]

# Pearl News topics (from sdg_news_topic_mapping.yaml)
PEARL_NEWS_TOPICS = [
    "climate", "economy_work", "education", "inequality",
    "mental_health", "partnerships", "peace_conflict",
]


def _load_yaml(path: Path) -> dict:
    if not path.exists() or yaml is None:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_locale_registry() -> dict[str, Any]:
    """Load locale_registry.yaml from phoenix_omega root config."""
    # Try Qwen-Agent local path first, then parent phoenix_omega
    for base in [REPO_ROOT, REPO_ROOT.parent]:
        path = base / "config" / "localization" / "locale_registry.yaml"
        if path.exists():
            return _load_yaml(path)
    logger.warning("locale_registry.yaml not found")
    return {}


def _load_teacher_roster() -> dict[str, Any]:
    """Load Pearl News teacher roster."""
    return _load_yaml(REPO_ROOT / "pearl_news" / "config" / "teacher_news_roster.yaml")


def _load_en_topic_atoms(topic: str) -> dict[str, Any]:
    """Load English atom file for a topic."""
    return _load_yaml(
        REPO_ROOT / "pearl_news" / "atoms" / "teacher_quotes_practices" / f"topic_{topic}.yaml"
    )


# ─── PEARL NEWS STUBS ────────────────────────────────────────────────────────

def _pearl_news_locale_dir(locale: str) -> Path:
    return REPO_ROOT / "pearl_news" / "atoms" / "teacher_quotes_practices" / "locales" / locale


def _pearl_news_stub_path(locale: str, topic: str) -> Path:
    return _pearl_news_locale_dir(locale) / f"topic_{topic}.yaml"


def audit_pearl_news(locales: list[str] | None = None) -> dict[str, Any]:
    """Audit Pearl News locale atom coverage."""
    target_locales = locales or PEARL_NEWS_LOCALES
    results: dict[str, Any] = {"total_expected": 0, "total_existing": 0, "missing": [], "existing": []}

    for locale in target_locales:
        for topic in PEARL_NEWS_TOPICS:
            results["total_expected"] += 1
            stub_path = _pearl_news_stub_path(locale, topic)
            if stub_path.exists():
                results["total_existing"] += 1
                results["existing"].append(f"{locale}/{topic}")
            else:
                results["missing"].append(f"{locale}/{topic}")

    return results


def scaffold_pearl_news_stub(locale: str, topic: str, dry_run: bool = False) -> bool:
    """Create a Pearl News locale atom stub file for one locale/topic pair."""
    stub_path = _pearl_news_stub_path(locale, topic)
    if stub_path.exists():
        logger.debug("Already exists: %s", stub_path)
        return False

    # Load English atoms as template
    en_data = _load_en_topic_atoms(topic)
    en_teachers = en_data.get("teachers") or {}

    # Build stub with same teacher structure but empty atoms
    teachers_block: dict[str, Any] = {}
    for teacher_id, teacher_data in en_teachers.items():
        teachers_block[teacher_id] = {
            "display_name": teacher_data.get("display_name", teacher_id),
            "tradition": teacher_data.get("tradition", "interfaith"),
            "attribution": teacher_data.get("attribution", ""),
            "status": "stub",  # Not yet translated
            "source_locale": "en-US",
            "atoms": [],  # Empty — to be filled by translate_atoms_all_locales.py
        }

    stub_data = {
        "topic_key": topic,
        "locale": locale,
        "source_locale": "en-US",
        "translation_status": "stub",
        "description": f"Locale atom stubs for {locale} — topic: {topic}. Awaiting translation from en-US.",
        "teachers": teachers_block,
    }

    if dry_run:
        logger.info("[DRY RUN] Would create: %s (%d teachers)", stub_path, len(teachers_block))
        return True

    stub_path.parent.mkdir(parents=True, exist_ok=True)
    with open(stub_path, "w", encoding="utf-8") as f:
        yaml.dump(stub_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    logger.info("Created stub: %s (%d teachers)", stub_path, len(teachers_block))
    return True


def scaffold_all_pearl_news(locales: list[str] | None = None, dry_run: bool = False) -> int:
    """Scaffold all missing Pearl News locale atom stubs."""
    target_locales = locales or PEARL_NEWS_LOCALES
    created = 0
    for locale in target_locales:
        for topic in PEARL_NEWS_TOPICS:
            if scaffold_pearl_news_stub(locale, topic, dry_run=dry_run):
                created += 1
    return created


# ─── PEARL PRIME STUBS ───────────────────────────────────────────────────────

def _pearl_prime_locale_dir(locale: str) -> Path:
    """Pearl Prime atoms directory for a locale, per content_roots_by_locale.yaml convention."""
    return REPO_ROOT / "atoms" / locale


def audit_pearl_prime(locales: list[str] | None = None) -> dict[str, Any]:
    """Audit Pearl Prime locale atom directory existence."""
    target_locales = locales or ALL_LOCALES
    results: dict[str, Any] = {"total_expected": len(target_locales), "total_existing": 0, "missing": [], "existing": []}

    for locale in target_locales:
        locale_dir = _pearl_prime_locale_dir(locale)
        if locale_dir.exists() and any(locale_dir.iterdir()):
            results["total_existing"] += 1
            results["existing"].append(locale)
        else:
            results["missing"].append(locale)

    return results


def scaffold_pearl_prime_stub(locale: str, dry_run: bool = False) -> bool:
    """Create Pearl Prime locale atom directory stub with a README."""
    locale_dir = _pearl_prime_locale_dir(locale)
    readme_path = locale_dir / "README.md"

    if readme_path.exists():
        logger.debug("Already exists: %s", locale_dir)
        return False

    if dry_run:
        logger.info("[DRY RUN] Would create: %s/", locale_dir)
        return True

    locale_dir.mkdir(parents=True, exist_ok=True)
    readme_content = (
        f"# {locale} Atom Directory\n\n"
        f"Locale-specific atoms for `{locale}`.\n"
        f"Source locale: `en-US`\n"
        f"Translation status: **stub** — awaiting translation pipeline run.\n\n"
        f"Populated by: `scripts/localization/translate_atoms_all_locales.py`\n"
    )
    readme_path.write_text(readme_content, encoding="utf-8")
    logger.info("Created Pearl Prime stub: %s/", locale_dir)
    return True


def scaffold_all_pearl_prime(locales: list[str] | None = None, dry_run: bool = False) -> int:
    """Scaffold all missing Pearl Prime locale directories."""
    target_locales = locales or ALL_LOCALES
    created = 0
    for locale in target_locales:
        if scaffold_pearl_prime_stub(locale, dry_run=dry_run):
            created += 1
    return created


# ─── GOLDEN REGRESSION STUBS ────────────────────────────────────────────────

def audit_golden_regression() -> dict[str, Any]:
    """Check which locales have golden regression samples."""
    golden_dir = REPO_ROOT / "config" / "audiobook_script" / "golden_regression_set"
    results: dict[str, Any] = {"existing": [], "missing_priority": []}

    for locale in ALL_LOCALES:
        found = list(golden_dir.glob(f"{locale}_*.yaml")) if golden_dir.exists() else []
        if found:
            results["existing"].append({"locale": locale, "files": [f.name for f in found]})
        elif locale in ["ja-JP", "ko-KR"]:  # Priority locales for Phase 2-3
            results["missing_priority"].append(locale)

    return results


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    ap = argparse.ArgumentParser(description="Scaffold locale atom stubs for Pearl News and Pearl Prime")
    ap.add_argument("--audit", action="store_true", help="Audit missing stubs (no changes)")
    ap.add_argument("--scaffold", action="store_true", help="Create missing stubs")
    ap.add_argument("--locale", default=None, help="Target a specific locale (e.g., ja-JP)")
    ap.add_argument("--system", choices=["pearl_news", "pearl_prime", "both"], default="both",
                    help="Which system to scaffold (default: both)")
    ap.add_argument("--dry-run", action="store_true", help="Show what would be created")
    args = ap.parse_args()

    if not args.audit and not args.scaffold:
        ap.print_help()
        return 0

    locales = [args.locale] if args.locale else None

    if args.audit:
        print("=" * 60)
        print("LOCALE ATOM STUB AUDIT")
        print("=" * 60)

        if args.system in ("pearl_news", "both"):
            pn = audit_pearl_news(locales)
            print(f"\nPEARL NEWS: {pn['total_existing']}/{pn['total_expected']} stubs exist")
            if pn["missing"]:
                print(f"  Missing ({len(pn['missing'])}):")
                for m in pn["missing"]:
                    print(f"    - {m}")
            else:
                print("  All stubs present.")

        if args.system in ("pearl_prime", "both"):
            pp = audit_pearl_prime(locales)
            print(f"\nPEARL PRIME: {pp['total_existing']}/{pp['total_expected']} locale dirs exist")
            if pp["missing"]:
                print(f"  Missing ({len(pp['missing'])}):")
                for m in pp["missing"]:
                    print(f"    - {m}")
            else:
                print("  All locale dirs present.")

        if args.system in ("pearl_prime", "both"):
            gr = audit_golden_regression()
            print(f"\nGOLDEN REGRESSION: {len(gr['existing'])} locales have samples")
            for e in gr["existing"]:
                print(f"  {e['locale']}: {', '.join(e['files'])}")
            if gr["missing_priority"]:
                print(f"  Priority locales missing samples: {', '.join(gr['missing_priority'])}")

        print()
        return 0

    if args.scaffold:
        total_created = 0

        if args.system in ("pearl_news", "both"):
            n = scaffold_all_pearl_news(locales, dry_run=args.dry_run)
            total_created += n
            print(f"Pearl News: {'would create' if args.dry_run else 'created'} {n} stub files")

        if args.system in ("pearl_prime", "both"):
            n = scaffold_all_pearl_prime(locales, dry_run=args.dry_run)
            total_created += n
            print(f"Pearl Prime: {'would create' if args.dry_run else 'created'} {n} locale dirs")

        print(f"\nTotal: {total_created} {'(dry-run)' if args.dry_run else 'created'}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
