#!/usr/bin/env python3
"""
PatchApplier Lesson Extractor — patch_lesson_extractor.py

Extracts locale-specific quality lessons from Pearl Prime's audiobook
comparator loop (manual review packets + loop traces) and converts them
into Pearl News expansion prompt improvements.

Architecture:
  Pearl Prime's judge identifies locale-specific issues:
    - "formal written Mandarin → colloquial zh-HK needed"
    - "narrative flow breaks at teacher section transition"
    - "Japanese register too direct for contemplative section"

  These lessons live in:
    - artifacts/audiobook/{batch}/{book}/{section}/manual_review/defect_history.json
    - artifacts/audiobook/loop_decisions.jsonl

  This script:
    1. Reads all defect histories and loop traces
    2. Aggregates by locale and gate type
    3. Extracts recurring patterns (defects that appear 3+ times)
    4. Converts patterns into prompt guidance fragments
    5. Writes locale-specific addenda to pearl_news/prompts/locale_guidance/

  The guidance files are referenced by Pearl News expansion prompts to
  incorporate lessons from Pearl Prime's quality loop.

Usage:
  # Extract lessons from all audiobook artifacts
  python scripts/patch_lesson_extractor.py --extract

  # Extract for specific locale only
  python scripts/patch_lesson_extractor.py --extract --locale zh-HK

  # Dry-run (show what would be extracted)
  python scripts/patch_lesson_extractor.py --extract --dry-run

  # Show defect frequency report
  python scripts/patch_lesson_extractor.py --report
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger("patch_lessons")

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

# Gates most relevant for Pearl News prompt improvement
RELEVANT_GATES = [
    "native_regional_language_fit",
    "narrative_flow_cohesion",
    "emotional_arc_alignment",
    "polish_emotional_impact",
]


# ─── DATA COLLECTION ────────────────────────────────────────────────────────

def collect_defect_histories() -> list[dict[str, Any]]:
    """Read all defect histories from audiobook manual review packets."""
    artifacts_dir = REPO_ROOT / "artifacts" / "audiobook"
    if not artifacts_dir.exists():
        return []

    histories: list[dict] = []
    for defect_file in artifacts_dir.rglob("defect_history.json"):
        try:
            data = json.loads(defect_file.read_text(encoding="utf-8"))
            # Extract locale from path: artifacts/audiobook/{batch}/{book}/{section}/manual_review/
            parts = defect_file.parts
            section_idx = parts.index("manual_review") - 1 if "manual_review" in parts else -1
            section_id = parts[section_idx] if section_idx > 0 else "unknown"

            for loop in data:
                for gate in loop.get("gate_results", []):
                    if gate.get("defect") and not gate.get("pass", True):
                        histories.append({
                            "section_id": section_id,
                            "locale": gate.get("locale", "unknown"),
                            "gate_id": gate.get("gate_id", "unknown"),
                            "defect": gate["defect"],
                            "prompt_patch": gate.get("prompt_patch", ""),
                            "score": gate.get("score"),
                            "loop_index": loop.get("loop_index", 0),
                            "source_file": str(defect_file),
                        })
        except Exception as e:
            logger.warning("Could not parse %s: %s", defect_file, e)

    return histories


def collect_loop_decisions() -> list[dict[str, Any]]:
    """Read loop decisions from JSONL log."""
    jsonl_path = REPO_ROOT / "artifacts" / "audiobook" / "loop_decisions.jsonl"
    if not jsonl_path.exists():
        return []

    decisions: list[dict] = []
    for line in jsonl_path.read_text(encoding="utf-8").strip().split("\n"):
        if line.strip():
            try:
                decisions.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return decisions


# ─── PATTERN EXTRACTION ─────────────────────────────────────────────────────

def extract_patterns(
    histories: list[dict],
    min_frequency: int = 2,
    locale_filter: str | None = None,
) -> dict[str, Any]:
    """Extract recurring defect patterns by locale and gate."""
    if locale_filter:
        histories = [h for h in histories if h.get("locale") == locale_filter]

    # Group by locale → gate → defect keyword patterns
    locale_patterns: dict[str, dict[str, list]] = {}

    for h in histories:
        locale = h.get("locale", "unknown")
        gate_id = h.get("gate_id", "unknown")
        defect = h.get("defect", "")
        patch = h.get("prompt_patch", "")

        if gate_id not in RELEVANT_GATES:
            continue

        locale_patterns.setdefault(locale, {}).setdefault(gate_id, []).append({
            "defect": defect,
            "prompt_patch": patch,
        })

    # Find recurring patterns (defects with similar content)
    result: dict[str, Any] = {}
    for locale, gates in locale_patterns.items():
        locale_result: dict[str, Any] = {}
        for gate_id, defects in gates.items():
            # Count defect keywords
            defect_texts = [d["defect"] for d in defects]
            if len(defect_texts) >= min_frequency:
                # Extract the most common prompt patches as guidance
                patches = [d["prompt_patch"] for d in defects if d["prompt_patch"]]
                locale_result[gate_id] = {
                    "frequency": len(defect_texts),
                    "sample_defects": defect_texts[:5],  # First 5 examples
                    "suggested_guidance": patches[:3],  # Top 3 patches
                }

        if locale_result:
            result[locale] = locale_result

    return result


# ─── GUIDANCE GENERATION ────────────────────────────────────────────────────

def generate_locale_guidance(patterns: dict[str, Any]) -> dict[str, str]:
    """Convert defect patterns into prompt guidance text for Pearl News expansion."""
    guidance: dict[str, str] = {}

    for locale, gates in patterns.items():
        lines = [
            f"# Locale Guidance: {locale}",
            f"# Generated from Pearl Prime audiobook quality data",
            f"# Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            f"# Status: auto-generated — review before applying to prompts",
            "",
            f"LOCALE-SPECIFIC LESSONS FOR {locale.upper()}:",
            f"(Extracted from audiobook comparator judge feedback)",
            "",
        ]

        for gate_id, data in gates.items():
            freq = data.get("frequency", 0)
            lines.append(f"## {gate_id} ({freq} occurrences)")

            # Add sample defects as "avoid" guidance
            sample_defects = data.get("sample_defects", [])
            if sample_defects:
                lines.append("AVOID:")
                for d in sample_defects[:3]:
                    lines.append(f"  - {d}")

            # Add suggested patches as "prefer" guidance
            suggested = data.get("suggested_guidance", [])
            if suggested:
                lines.append("PREFER:")
                for s in suggested[:3]:
                    lines.append(f"  - {s}")

            lines.append("")

        guidance[locale] = "\n".join(lines)

    return guidance


def write_locale_guidance(guidance: dict[str, str], dry_run: bool = False) -> int:
    """Write locale guidance files to pearl_news/prompts/locale_guidance/."""
    guidance_dir = REPO_ROOT / "pearl_news" / "prompts" / "locale_guidance"
    written = 0

    for locale, text in guidance.items():
        out_path = guidance_dir / f"{locale}_guidance.txt"

        if dry_run:
            logger.info("[DRY RUN] Would write: %s (%d lines)", out_path, len(text.split("\n")))
            written += 1
            continue

        guidance_dir.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        logger.info("Wrote locale guidance: %s", out_path)
        written += 1

    return written


# ─── REPORT ──────────────────────────────────────────────────────────────────

def print_defect_report(histories: list[dict], decisions: list[dict]) -> None:
    """Print defect frequency report."""
    print("=" * 60)
    print("PATCHAPPLIER LESSON REPORT")
    print(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    if not histories and not decisions:
        print("\nNo audiobook data found in artifacts/audiobook/")
        print("Run the audiobook comparator loop first to generate quality data.")
        return

    print(f"\nTotal defect records: {len(histories)}")
    print(f"Total loop decisions: {len(decisions)}")

    # By locale
    locale_counts = Counter(h.get("locale", "unknown") for h in histories)
    print(f"\nDefects by locale:")
    for locale, count in locale_counts.most_common():
        print(f"  {locale}: {count}")

    # By gate
    gate_counts = Counter(h.get("gate_id", "unknown") for h in histories)
    print(f"\nDefects by gate:")
    for gate, count in gate_counts.most_common():
        relevant = "★" if gate in RELEVANT_GATES else " "
        print(f"  {relevant} {gate}: {count}")

    # Loop stats
    if decisions:
        pass_count = sum(1 for d in decisions if d.get("decision") == "pass")
        manual = sum(1 for d in decisions if d.get("decision") == "manual_review")
        total = len(decisions)
        print(f"\nLoop decision stats:")
        print(f"  Pass: {pass_count}/{total} ({pass_count/total:.1%})" if total else "  No decisions")
        print(f"  Manual review: {manual}/{total} ({manual/total:.1%})" if total else "")

    print("\n" + "=" * 60)


# ─── CLI ────────────────────────────────────────────────────────────────────

def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    ap = argparse.ArgumentParser(description="Extract PatchApplier lessons for Pearl News prompts")
    ap.add_argument("--extract", action="store_true", help="Extract and write locale guidance")
    ap.add_argument("--report", action="store_true", help="Print defect frequency report")
    ap.add_argument("--locale", default=None, help="Filter to specific locale")
    ap.add_argument("--dry-run", action="store_true", help="Show what would be written")
    ap.add_argument("--min-frequency", type=int, default=2,
                    help="Minimum defect frequency to include (default: 2)")
    args = ap.parse_args()

    if not args.extract and not args.report:
        ap.print_help()
        return 0

    histories = collect_defect_histories()
    decisions = collect_loop_decisions()

    if args.report:
        print_defect_report(histories, decisions)

    if args.extract:
        patterns = extract_patterns(histories, args.min_frequency, args.locale)

        if not patterns:
            print("No recurring patterns found (need more audiobook data).")
            print(f"Total defect records: {len(histories)}")
            print(f"Minimum frequency threshold: {args.min_frequency}")
            if not histories:
                print("Run the audiobook comparator loop to generate quality data first.")
            return 0

        guidance = generate_locale_guidance(patterns)
        written = write_locale_guidance(guidance, dry_run=args.dry_run)
        print(f"\n{'Would write' if args.dry_run else 'Wrote'} guidance for {written} locales")

    return 0


if __name__ == "__main__":
    sys.exit(main())
