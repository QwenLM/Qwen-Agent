#!/usr/bin/env python3
"""
Pearl News — Teacher Onboarding CLI.

Detects gaps between the teacher roster and atom files, scaffolds missing atoms
via LLM (Qwen3 / OpenAI-compatible), and tracks atom lifecycle status.

Usage:
  # Audit: show all gaps and status distribution
  python -m pearl_news.pipeline.teacher_onboarding --audit

  # Scaffold: generate missing atoms via LLM (dry-run first!)
  python -m pearl_news.pipeline.teacher_onboarding --scaffold --dry-run
  python -m pearl_news.pipeline.teacher_onboarding --scaffold

  # Validate: check all roster teachers have 10 atoms per topic
  python -m pearl_news.pipeline.teacher_onboarding --validate
  python -m pearl_news.pipeline.teacher_onboarding --validate --strict

  # Fix status: batch-update atom status after human review
  python -m pearl_news.pipeline.teacher_onboarding --fix-status ahjan climate reviewed
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import textwrap
from collections import Counter
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ATOMS_PER_TEACHER = 10
VALID_STATUSES = {"starter", "reviewed", "approved"}
DEFAULT_STATUS = "starter"

# Sub-topic areas per topic (used in LLM prompt for variety)
TOPIC_SUBTOPICS: dict[str, list[str]] = {
    "climate": [
        "carbon emissions & net-zero targets",
        "renewable energy transition",
        "climate adaptation & resilience",
        "climate justice & equity",
        "youth climate activism",
        "biodiversity & ecosystem loss",
        "water scarcity & ocean health",
        "food security & agriculture",
        "corporate responsibility & greenwashing",
        "climate migration & displacement",
    ],
    "mental_health": [
        "social media & digital overload",
        "loneliness & isolation",
        "burnout & workplace stress",
        "grief & loss",
        "substance use & addiction",
        "identity & belonging",
        "trauma & healing",
        "intergenerational trauma",
        "anxiety & climate distress",
        "access to mental health care",
    ],
    "education": [
        "access & equity in education",
        "digital learning & AI in classrooms",
        "standardized testing & academic pressure",
        "teacher training & retention",
        "vocational & skills-based education",
        "education in conflict zones",
        "indigenous & culturally responsive education",
        "higher education affordability",
        "early childhood development",
        "civic & values education",
    ],
    "peace_conflict": [
        "armed conflict & civilian protection",
        "refugee & displacement crises",
        "peacebuilding & reconciliation",
        "nuclear disarmament & arms control",
        "youth in peacebuilding",
        "media & misinformation in conflict",
        "interfaith dialogue for peace",
        "transitional justice",
        "cybersecurity & digital conflict",
        "structural violence & systemic oppression",
    ],
    "economy_work": [
        "youth unemployment & underemployment",
        "gig economy & precarious work",
        "automation & AI job displacement",
        "housing affordability",
        "student & consumer debt",
        "entrepreneurship & innovation",
        "wage inequality & living wages",
        "remote work & work-life balance",
        "labour organizing & worker rights",
        "economic recovery & resilience",
    ],
    "inequality": [
        "income & wealth inequality",
        "racial & ethnic discrimination",
        "gender inequality & rights",
        "disability rights & inclusion",
        "LGBTQ+ rights & representation",
        "digital divide & tech access",
        "migration & citizenship rights",
        "housing & spatial inequality",
        "health disparities",
        "intergenerational inequality",
    ],
    "partnerships": [
        "multilateral & UN partnerships",
        "youth-led organization partnerships",
        "cross-sector collaboration",
        "funding & donor-recipient dynamics",
        "North-South & Global South partnerships",
        "technology transfer partnerships",
        "interfaith dialogue as partnership",
        "civil society coalition building",
        "data sharing & knowledge exchange",
        "accountability & monitoring frameworks",
    ],
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def _load_roster(config_root: Path) -> dict[str, Any]:
    """Load teacher_news_roster.yaml."""
    path = config_root / "teacher_news_roster.yaml"
    if not path.exists() or yaml is None:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_topic_atoms(atoms_root: Path, topic: str) -> dict[str, Any]:
    """Load topic_<topic>.yaml from atoms directory."""
    p = atoms_root / f"topic_{topic}.yaml"
    if not p.exists() or yaml is None:
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_sdg_mapping(config_root: Path) -> dict[str, Any]:
    """Load sdg_news_topic_mapping.yaml for topic context."""
    p = config_root / "sdg_news_topic_mapping.yaml"
    if not p.exists() or yaml is None:
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_llm_config(config_root: Path) -> dict[str, Any]:
    """Load llm_expansion.yaml for LLM connection details."""
    p = config_root / "llm_expansion.yaml"
    if not p.exists() or yaml is None:
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _all_topics(config_root: Path) -> list[str]:
    """Get list of all topic keys from SDG mapping."""
    sdg = _load_sdg_mapping(config_root)
    return sorted((sdg.get("topic_to_sdg") or {}).keys())


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------
def audit(config_root: Path, atoms_root: Path) -> dict[str, Any]:
    """
    Scan roster vs atom files and return a gap report.

    Returns dict with keys:
      - teachers: {teacher_id: {topics: {topic: {count, status}}, ...}}
      - gaps: [(teacher_id, topic, count_found)]
      - status_distribution: {starter: N, reviewed: N, approved: N}
      - total_atoms: int
      - target_atoms: int
    """
    roster = _load_roster(config_root)
    roster_teachers = roster.get("teachers") or {}
    topics = _all_topics(config_root)

    report: dict[str, Any] = {
        "teachers": {},
        "gaps": [],
        "status_distribution": Counter(),
        "total_atoms": 0,
        "target_atoms": 0,
    }

    for teacher_id, teacher_info in roster_teachers.items():
        assigned_topics = teacher_info.get("news_topics") or []
        teacher_report: dict[str, Any] = {"display_name": teacher_info.get("display_name", teacher_id), "topics": {}}

        for topic in assigned_topics:
            report["target_atoms"] += ATOMS_PER_TEACHER
            topic_data = _load_topic_atoms(atoms_root, topic)
            topic_teachers = topic_data.get("teachers") or {}
            entry = topic_teachers.get(teacher_id) or {}
            atoms = entry.get("atoms") or []
            status = entry.get("status", "unknown")
            count = len(atoms)
            report["total_atoms"] += count
            report["status_distribution"][status] += count

            teacher_report["topics"][topic] = {"count": count, "status": status}
            if count < ATOMS_PER_TEACHER:
                report["gaps"].append((teacher_id, topic, count))

        report["teachers"][teacher_id] = teacher_report

    return report


def print_audit_report(report: dict[str, Any]) -> None:
    """Pretty-print the audit report."""
    total = report["total_atoms"]
    target = report["target_atoms"]
    gaps = report["gaps"]

    print("\n" + "=" * 60)
    print("TEACHER ONBOARDING AUDIT REPORT")
    print("=" * 60)

    # Overall
    coverage = (total / target * 100) if target else 0
    print(f"\nTotal atoms: {total} / {target} target ({coverage:.0f}% coverage)")
    print(f"Gaps found: {len(gaps)}")

    # Status distribution
    print("\nStatus distribution:")
    for status, count in sorted(report["status_distribution"].items()):
        print(f"  {status:>10}: {count} atoms")

    # Per-teacher detail
    print("\nPer-teacher breakdown:")
    for teacher_id, info in sorted(report["teachers"].items()):
        name = info["display_name"]
        topics = info["topics"]
        all_ok = all(t["count"] >= ATOMS_PER_TEACHER for t in topics.values())
        marker = "OK" if all_ok else "GAP"
        print(f"\n  [{marker}] {name} ({teacher_id}):")
        for topic, detail in sorted(topics.items()):
            count = detail["count"]
            status = detail["status"]
            flag = " " if count >= ATOMS_PER_TEACHER else " *** MISSING ***"
            print(f"    {topic:>20}: {count:>2} atoms ({status}){flag}")

    # Gaps summary
    if gaps:
        print("\n" + "-" * 40)
        print("GAPS TO FILL:")
        for teacher_id, topic, count in gaps:
            need = ATOMS_PER_TEACHER - count
            print(f"  {teacher_id} / {topic}: has {count}, needs {need} more")

    print("\n" + "=" * 60)


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------
def validate(config_root: Path, atoms_root: Path, strict: bool = False) -> bool:
    """
    Check all roster teachers have 10 atoms per topic.
    If strict=True, also require all atoms to be APPROVED.
    Returns True if valid.
    """
    report = audit(config_root, atoms_root)
    gaps = report["gaps"]
    ok = True

    if gaps:
        logger.error("Validation FAILED: %d gaps found", len(gaps))
        for teacher_id, topic, count in gaps:
            logger.error("  %s / %s: %d atoms (need %d)", teacher_id, topic, count, ATOMS_PER_TEACHER)
        ok = False

    if strict:
        non_approved = {s: c for s, c in report["status_distribution"].items() if s != "approved" and c > 0}
        if non_approved:
            logger.error("Strict validation FAILED: non-approved atoms found: %s", dict(non_approved))
            ok = False

    if ok:
        mode = "strict" if strict else "standard"
        logger.info("Validation PASSED (%s): all %d atoms across %d teachers",
                     mode, report["total_atoms"], len(report["teachers"]))
    return ok


# ---------------------------------------------------------------------------
# Fix status
# ---------------------------------------------------------------------------
def fix_status(atoms_root: Path, teacher_id: str, topic: str, new_status: str) -> bool:
    """Update the status field for a teacher in a topic atom file."""
    if new_status not in VALID_STATUSES:
        logger.error("Invalid status '%s'. Must be one of: %s", new_status, VALID_STATUSES)
        return False

    path = atoms_root / f"topic_{topic}.yaml"
    if not path.exists():
        logger.error("Atom file not found: %s", path)
        return False

    # Read raw text to preserve formatting
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    # Find the teacher block and update status
    in_teacher = False
    found = False
    for i, line in enumerate(lines):
        # Detect teacher_id at indent level 2
        stripped = line.strip()
        if stripped == f"{teacher_id}:" and line.startswith("  ") and not line.startswith("    "):
            in_teacher = True
            continue
        if in_teacher:
            if stripped.startswith("status:"):
                lines[i] = f"    status: {new_status}"
                found = True
                break
            # If we hit atoms: or another teacher before finding status, insert it
            if stripped.startswith("atoms:") or (stripped.endswith(":") and not stripped.startswith("display_name") and not stripped.startswith("tradition") and not stripped.startswith("attribution")):
                lines.insert(i, f"    status: {new_status}")
                found = True
                break
            # If we hit next teacher at same indent level
            if line.startswith("  ") and not line.startswith("    ") and stripped.endswith(":"):
                lines.insert(i, f"    status: {new_status}")
                found = True
                break

    if not found:
        logger.error("Could not find teacher '%s' in %s", teacher_id, path)
        return False

    path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Updated %s/%s → status: %s", teacher_id, topic, new_status)
    return True


# ---------------------------------------------------------------------------
# Scaffold — LLM atom generation
# ---------------------------------------------------------------------------
def _build_scaffold_prompt(
    teacher_info: dict[str, Any],
    teacher_id: str,
    topic: str,
    sdg_number: str,
    sdg_label: str,
    subtopics: list[str],
    example_atoms: list[str],
    num_atoms: int = 10,
) -> str:
    """Build the LLM prompt for generating atoms."""
    name = teacher_info.get("display_name", teacher_id)
    tradition = teacher_info.get("tradition", "unknown")
    attribution = teacher_info.get("attribution_template", "")

    examples_block = ""
    if example_atoms:
        examples_block = "\n\nEXAMPLE ATOMS (for style/voice reference only — your atoms must be original):\n"
        for i, atom in enumerate(example_atoms[:3], 1):
            atom_text = str(atom).strip().replace("\n", " ").replace("  ", " ")
            examples_block += f"  {i}. {atom_text}\n"

    subtopics_block = "\n".join(f"  {i+1}. {st}" for i, st in enumerate(subtopics))

    return textwrap.dedent(f"""\
        You are an expert in spiritual traditions and their application to contemporary issues.

        Generate exactly {num_atoms} teaching statements (atoms) for use in Pearl News articles.

        TEACHER:
          Name: {name}
          Tradition: {tradition}
          Attribution: {attribution}

        TOPIC: {topic} (SDG {sdg_number}: {sdg_label})

        SUB-TOPICS TO COVER (one atom per sub-topic):
        {subtopics_block}
        {examples_block}
        CONSTRAINTS:
        1. Each atom MUST be 40-80 words (count carefully)
        2. Each atom MUST name a SPECIFIC teaching, concept, or practice from {tradition}
        3. Each atom MUST connect that teaching to a specific {topic} reality
        4. Each atom MUST be self-contained (usable in any news article about {topic})
        5. NO generic platitudes ("be mindful", "seek peace", "do good")
        6. NO repetition of the same concept across atoms
        7. Tone: precise, grounded, news-adjacent — NOT devotional or preachy

        OUTPUT FORMAT (exactly this YAML structure):
        atoms:
          - >
            [First atom, 40-80 words, names a {tradition} concept, connects to {topic}]
          - >
            [Second atom, 40-80 words, different concept]
          ... ({num_atoms} total)

        Generate exactly {num_atoms} atoms. Each must name a different {tradition} concept.
    """)


def _parse_scaffold_response(response_text: str) -> list[str]:
    """Extract atoms from LLM response text."""
    atoms: list[str] = []
    # Try YAML parsing first
    try:
        data = yaml.safe_load(response_text)
        if isinstance(data, dict) and "atoms" in data:
            return [str(a).strip() for a in data["atoms"] if a]
    except Exception:
        pass

    # Fallback: extract text blocks after "- >" or "- " markers
    # Split on atom markers
    parts = re.split(r"\n\s*-\s*>?\s*\n?", response_text)
    for part in parts[1:]:  # skip header
        text = part.strip().replace("\n", " ").replace("  ", " ")
        if len(text.split()) >= 20:  # at least 20 words
            atoms.append(text)

    return atoms


def _call_llm(prompt: str, llm_config: dict[str, Any]) -> str | None:
    """Call LLM via OpenAI-compatible API. Returns response text or None."""
    try:
        from openai import OpenAI
    except ImportError:
        logger.error("openai package not installed. Run: pip install openai --break-system-packages")
        return None

    base_url = os.environ.get("QWEN_BASE_URL") or llm_config.get("base_url", "http://localhost:1234/v1")
    api_key = os.environ.get("QWEN_API_KEY") or llm_config.get("api_key", "lm-studio")
    model = os.environ.get("QWEN_MODEL") or llm_config.get("model", "qwen3-14b")
    timeout = llm_config.get("timeout", 360)

    client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert on spiritual and philosophical traditions. Generate teaching atoms in the exact YAML format requested."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2000,
            temperature=0.6,
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return None


def _get_example_atoms(atoms_root: Path, teacher_id: str, exclude_topic: str) -> list[str]:
    """Get existing atoms from this teacher in other topics (for style reference)."""
    examples: list[str] = []
    import glob
    for path in sorted(Path(atoms_root).glob("topic_*.yaml")):
        if path.stem == f"topic_{exclude_topic}":
            continue
        data = _load_topic_atoms(atoms_root, path.stem.replace("topic_", ""))
        teachers = data.get("teachers") or {}
        entry = teachers.get(teacher_id)
        if entry and entry.get("atoms"):
            examples.extend(entry["atoms"][:2])
        if len(examples) >= 3:
            break
    return examples[:3]


def scaffold(
    config_root: Path,
    atoms_root: Path,
    dry_run: bool = False,
    teacher_filter: str | None = None,
    topic_filter: str | None = None,
) -> dict[str, int]:
    """
    For each gap found in audit, generate atoms via LLM and write to YAML.
    Returns dict with counts: {generated, failed, skipped}.
    """
    report = audit(config_root, atoms_root)
    gaps = report["gaps"]
    roster = _load_roster(config_root)
    sdg_mapping = _load_sdg_mapping(config_root)
    llm_config = _load_llm_config(config_root)
    topic_sdg = sdg_mapping.get("topic_to_sdg") or {}

    result = {"generated": 0, "failed": 0, "skipped": 0}

    if not gaps:
        logger.info("No gaps found — all teachers have %d atoms per topic.", ATOMS_PER_TEACHER)
        return result

    for teacher_id, topic, current_count in gaps:
        if teacher_filter and teacher_id != teacher_filter:
            result["skipped"] += 1
            continue
        if topic_filter and topic != topic_filter:
            result["skipped"] += 1
            continue

        need = ATOMS_PER_TEACHER - current_count
        teacher_info = (roster.get("teachers") or {}).get(teacher_id) or {}
        sdg_info = topic_sdg.get(topic) or {}
        sdg_number = sdg_info.get("primary_sdg", "?")
        sdg_labels = sdg_info.get("sdg_labels") or {}
        sdg_label = sdg_labels.get(sdg_number, topic.replace("_", " ").title())
        subtopics = TOPIC_SUBTOPICS.get(topic, [f"{topic} sub-topic {i+1}" for i in range(10)])

        logger.info("Scaffolding %s / %s: need %d atoms", teacher_id, topic, need)

        if dry_run:
            print(f"  [DRY RUN] Would generate {need} atoms for {teacher_id}/{topic}")
            result["skipped"] += 1
            continue

        example_atoms = _get_example_atoms(atoms_root, teacher_id, topic)
        prompt = _build_scaffold_prompt(
            teacher_info, teacher_id, topic, sdg_number, sdg_label,
            subtopics, example_atoms, num_atoms=need,
        )

        response = _call_llm(prompt, llm_config)
        if not response:
            logger.error("LLM returned no response for %s/%s", teacher_id, topic)
            result["failed"] += 1
            continue

        new_atoms = _parse_scaffold_response(response)
        if len(new_atoms) < need:
            logger.warning(
                "LLM returned %d atoms for %s/%s (needed %d); using what we got",
                len(new_atoms), teacher_id, topic, need,
            )

        if not new_atoms:
            result["failed"] += 1
            continue

        # Write atoms to file
        _append_atoms_to_file(atoms_root, teacher_id, topic, new_atoms, teacher_info)
        result["generated"] += len(new_atoms)
        logger.info("Added %d atoms for %s/%s", len(new_atoms), teacher_id, topic)

    return result


def _append_atoms_to_file(
    atoms_root: Path,
    teacher_id: str,
    topic: str,
    new_atoms: list[str],
    teacher_info: dict[str, Any],
) -> None:
    """Append new atoms to a teacher's section in the topic YAML file."""
    path = atoms_root / f"topic_{topic}.yaml"

    if not path.exists():
        # Create new file
        data = {
            "topic_key": topic,
            "teachers": {
                teacher_id: {
                    "display_name": teacher_info.get("display_name", teacher_id),
                    "tradition": teacher_info.get("tradition", ""),
                    "attribution": teacher_info.get("attribution_template", ""),
                    "status": "starter",
                    "atoms": new_atoms,
                }
            },
        }
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Pearl News — teacher atoms for topic: {topic}\n")
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, width=100)
        return

    # Load existing data
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    teachers = data.setdefault("teachers", {})
    if teacher_id in teachers:
        existing = teachers[teacher_id].get("atoms") or []
        existing.extend(new_atoms)
        teachers[teacher_id]["atoms"] = existing
        teachers[teacher_id].setdefault("status", "starter")
    else:
        teachers[teacher_id] = {
            "display_name": teacher_info.get("display_name", teacher_id),
            "tradition": teacher_info.get("tradition", ""),
            "attribution": teacher_info.get("attribution_template", ""),
            "status": "starter",
            "atoms": new_atoms,
        }

    # Write back with header preserved
    text = path.read_text(encoding="utf-8")
    header_lines = []
    for line in text.split("\n"):
        if line.startswith("#") or line.strip() == "":
            header_lines.append(line)
        else:
            break
    header = "\n".join(header_lines) + "\n" if header_lines else ""

    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, width=100)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Pearl News: Teacher Onboarding — audit, scaffold, validate atom files",
    )
    ap.add_argument("--audit", action="store_true", help="Scan roster vs atoms and report gaps")
    ap.add_argument("--scaffold", action="store_true", help="Generate missing atoms via LLM")
    ap.add_argument("--validate", action="store_true", help="Check all teachers have 10 atoms per topic")
    ap.add_argument("--fix-status", nargs=3, metavar=("TEACHER", "TOPIC", "STATUS"),
                     help="Update atom status: teacher_id topic new_status")
    ap.add_argument("--strict", action="store_true", help="With --validate: require all atoms APPROVED")
    ap.add_argument("--dry-run", action="store_true", help="With --scaffold: show what would be generated")
    ap.add_argument("--teacher", default=None, help="Filter scaffold to specific teacher_id")
    ap.add_argument("--topic", default=None, help="Filter scaffold to specific topic")
    ap.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
    )

    root = Path(__file__).resolve().parent.parent
    config_root = root / "config"
    atoms_root = root / "atoms" / "teacher_quotes_practices"

    if not any([args.audit, args.scaffold, args.validate, args.fix_status]):
        ap.print_help()
        return 1

    if args.audit:
        report = audit(config_root, atoms_root)
        print_audit_report(report)
        return 0

    if args.validate:
        ok = validate(config_root, atoms_root, strict=args.strict)
        return 0 if ok else 1

    if args.fix_status:
        teacher_id, topic, new_status = args.fix_status
        ok = fix_status(atoms_root, teacher_id, topic, new_status)
        return 0 if ok else 1

    if args.scaffold:
        result = scaffold(
            config_root, atoms_root,
            dry_run=args.dry_run,
            teacher_filter=args.teacher,
            topic_filter=args.topic,
        )
        print(f"\nScaffold complete: generated={result['generated']}, "
              f"failed={result['failed']}, skipped={result['skipped']}")
        return 0 if result["failed"] == 0 else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
