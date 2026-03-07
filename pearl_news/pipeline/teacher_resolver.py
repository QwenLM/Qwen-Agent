"""
Pearl News — resolve a named teacher (name, tradition, atoms) for a given article topic.
Reads pearl_news/config/teacher_news_roster.yaml and pearl_news/atoms/teacher_quotes_practices/topic_<topic>.yaml.
Returns one teacher deterministically per article (using article id hash, same logic as group-vs-single).
"""
from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Policy: named teacher allowed for all templates when atoms are present.
# Spec ref: PEARL_NEWS_WRITER_SPEC.md §6 — updated to allow named teacher +
# 3 points across all templates when teacher atom file is populated.
# ---------------------------------------------------------------------------

FALLBACK_TEACHER = {
    "teacher_id": "__fallback__",
    "display_name": "a teacher from the United Spiritual Leaders Forum",
    "tradition": "interfaith",
    "attribution": "A teacher from the United Spiritual Leaders Forum teaches that",
    "is_fallback": True,  # Signals to validator: hold from publishing until real teacher assigned
    "atoms": [
        "reflection and resilience in the face of uncertainty support youth well-being and global goals.",
        "spiritual and ethical traditions speak to young people in times of change—offering clarity and a frame for action.",
        "presenting one voice at a time allows readers to engage with a clear perspective before exploring further.",
    ],
}


def _load_roster(config_root: Path) -> dict[str, Any]:
    path = config_root / "teacher_news_roster.yaml"
    if not path.exists() or yaml is None:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_topic_atoms(atoms_root: Path, topic: str) -> dict[str, Any]:
    """Load topic_<topic>.yaml from atoms/teacher_quotes_practices/."""
    p = atoms_root / f"topic_{topic}.yaml"
    if not p.exists() or yaml is None:
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _is_atom_status_usable(atom_entry: dict[str, Any]) -> bool:
    """Check if a teacher's atom status allows use in the current environment.

    Production (PEARL_NEWS_ENV=production): only 'approved' atoms.
    Dev (default): all statuses accepted (starter, reviewed, approved).
    Missing status field defaults to 'approved' for backward compatibility.
    """
    status = atom_entry.get("status", "approved")
    is_production = os.environ.get("PEARL_NEWS_ENV", "dev") == "production"
    if is_production and status != "approved":
        return False
    return True


def _pick_teacher_index(article_id: str, n: int) -> int:
    """Deterministic teacher selection from n candidates using article_id hash."""
    if n <= 0:
        return 0
    h = int(hashlib.sha256(article_id.encode("utf-8")).hexdigest(), 16)
    return h % n


def resolve_teacher(
    item: dict[str, Any],
    config_root: Path | None = None,
    atoms_root: Path | None = None,
) -> dict[str, Any]:
    """
    Return a teacher dict with keys:
      teacher_id, display_name, tradition, attribution, atoms (list of 3 strings)
    Falls back to FALLBACK_TEACHER if no real data available.
    """
    root = Path(__file__).resolve().parent.parent
    config_root = config_root or (root / "config")
    atoms_root = atoms_root or (root / "atoms" / "teacher_quotes_practices")

    topic = (item.get("topic") or "partnerships").lower()
    language = (item.get("language") or "en").lower()
    article_id = item.get("id") or item.get("title") or "default"

    # Load roster and topic atoms
    roster = _load_roster(config_root)
    topic_data = _load_topic_atoms(atoms_root, topic)

    if not topic_data or not roster:
        logger.debug("No atom file for topic=%s or no roster; using fallback teacher", topic)
        return FALLBACK_TEACHER

    topic_teachers = topic_data.get("teachers") or {}
    if not topic_teachers:
        logger.debug("No teachers in atom file for topic=%s; using fallback", topic)
        return FALLBACK_TEACHER

    # Filter: only teachers that exist in both the atom file AND the roster,
    # and whose region_fit includes the article language (en / china / japan) or "global"
    lang_map = {"en": "english", "zh-cn": "china", "ja": "japan", "zh": "china"}
    region = lang_map.get(language, "global")

    candidates: list[dict[str, Any]] = []
    for teacher_id, atom_entry in topic_teachers.items():
        # Status filter: skip non-approved atoms in production
        if not _is_atom_status_usable(atom_entry):
            logger.debug("Skipping %s for topic=%s: status=%s (not approved in production)",
                         teacher_id, topic, atom_entry.get("status", "?"))
            continue
        roster_entry = (roster.get("teachers") or {}).get(teacher_id)
        if not roster_entry:
            # Teacher in atom file but not in roster — use atom data only
            roster_entry = {}
        region_fit = roster_entry.get("region_fit") or ["global"]
        if region not in region_fit and "global" not in region_fit:
            continue  # skip — wrong language region
        atoms_list = atom_entry.get("atoms") or []
        if len(atoms_list) < 3:
            continue  # skip — insufficient atoms
        candidates.append({
            "teacher_id": teacher_id,
            "display_name": atom_entry.get("display_name") or roster_entry.get("display_name") or teacher_id,
            "tradition": atom_entry.get("tradition") or roster_entry.get("tradition") or "interfaith",
            "attribution": atom_entry.get("attribution") or roster_entry.get("attribution_template") or "",
            "atoms": atoms_list[:3],  # always exactly 3
        })

    if not candidates:
        logger.debug(
            "No region-matched candidates for topic=%s language=%s; trying any language",
            topic, language,
        )
        # Relax region filter — use any teacher with 3 atoms
        for teacher_id, atom_entry in topic_teachers.items():
            if not _is_atom_status_usable(atom_entry):
                continue
            roster_entry = (roster.get("teachers") or {}).get(teacher_id) or {}
            atoms_list = atom_entry.get("atoms") or []
            if len(atoms_list) < 3:
                continue
            candidates.append({
                "teacher_id": teacher_id,
                "display_name": atom_entry.get("display_name") or roster_entry.get("display_name") or teacher_id,
                "tradition": atom_entry.get("tradition") or roster_entry.get("tradition") or "interfaith",
                "attribution": atom_entry.get("attribution") or roster_entry.get("attribution_template") or "",
                "atoms": atoms_list[:3],
            })

    if not candidates:
        logger.debug("Still no candidates for topic=%s; using fallback", topic)
        return FALLBACK_TEACHER

    idx = _pick_teacher_index(article_id, len(candidates))
    chosen = candidates[idx]

    # Ensure attribution is non-empty
    if not chosen.get("attribution"):
        chosen["attribution"] = (
            f"From within the {chosen['tradition']} tradition, {chosen['display_name']} teaches that"
        )

    logger.info(
        "Resolved teacher for article %s topic=%s: %s (%s)",
        article_id, topic, chosen["display_name"], chosen["tradition"],
    )
    return chosen


def resolve_multiple_teachers(
    item: dict[str, Any],
    num_teachers: int = 3,
    config_root: Path | None = None,
    atoms_root: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Return 2-3 teachers from DIFFERENT traditions for the same topic.
    Used for interfaith_dialogue_report articles.
    Returns list of teacher dicts, each with teacher_id, display_name, tradition, attribution, atoms.
    Falls back to fewer teachers if not enough distinct traditions exist for the topic.
    """
    root = Path(__file__).resolve().parent.parent
    config_root = config_root or (root / "config")
    atoms_root = atoms_root or (root / "atoms" / "teacher_quotes_practices")

    topic = (item.get("topic") or "partnerships").lower()
    language = (item.get("language") or "en").lower()
    article_id = item.get("id") or item.get("title") or "default"

    roster = _load_roster(config_root)
    topic_data = _load_topic_atoms(atoms_root, topic)

    if not topic_data or not roster:
        logger.debug("No atom file for topic=%s or no roster; using fallback for multi-teacher", topic)
        return [FALLBACK_TEACHER]

    topic_teachers = topic_data.get("teachers") or {}
    if not topic_teachers:
        return [FALLBACK_TEACHER]

    # Build all candidates with region filtering
    lang_map = {"en": "english", "zh-cn": "china", "ja": "japan", "zh": "china"}
    region = lang_map.get(language, "global")

    candidates: list[dict[str, Any]] = []
    for teacher_id, atom_entry in topic_teachers.items():
        if not _is_atom_status_usable(atom_entry):
            continue
        roster_entry = (roster.get("teachers") or {}).get(teacher_id) or {}
        region_fit = roster_entry.get("region_fit") or ["global"]
        if region not in region_fit and "global" not in region_fit:
            continue
        atoms_list = atom_entry.get("atoms") or []
        if len(atoms_list) < 3:
            continue
        candidates.append({
            "teacher_id": teacher_id,
            "display_name": atom_entry.get("display_name") or roster_entry.get("display_name") or teacher_id,
            "tradition": atom_entry.get("tradition") or roster_entry.get("tradition") or "interfaith",
            "attribution": atom_entry.get("attribution") or roster_entry.get("attribution_template") or "",
            "atoms": atoms_list[:3],
        })

    if not candidates:
        # Relax region filter
        for teacher_id, atom_entry in topic_teachers.items():
            if not _is_atom_status_usable(atom_entry):
                continue
            roster_entry = (roster.get("teachers") or {}).get(teacher_id) or {}
            atoms_list = atom_entry.get("atoms") or []
            if len(atoms_list) < 3:
                continue
            candidates.append({
                "teacher_id": teacher_id,
                "display_name": atom_entry.get("display_name") or roster_entry.get("display_name") or teacher_id,
                "tradition": atom_entry.get("tradition") or roster_entry.get("tradition") or "interfaith",
                "attribution": atom_entry.get("attribution") or roster_entry.get("attribution_template") or "",
                "atoms": atoms_list[:3],
            })

    if not candidates:
        return [FALLBACK_TEACHER]

    # Group by tradition (tradition_short or tradition) for distinct-tradition selection
    from collections import OrderedDict
    tradition_groups: dict[str, list[dict]] = OrderedDict()
    for c in candidates:
        trad_key = c["tradition"].lower().split()[0]  # first word as group key
        tradition_groups.setdefault(trad_key, []).append(c)

    # Deterministic selection: pick one teacher per tradition using hash
    h = int(hashlib.sha256(article_id.encode("utf-8")).hexdigest(), 16)
    selected: list[dict[str, Any]] = []
    tradition_keys = list(tradition_groups.keys())

    # Shuffle tradition order deterministically
    tradition_keys.sort(key=lambda t: int(hashlib.sha256((article_id + t).encode()).hexdigest(), 16))

    for trad_key in tradition_keys:
        if len(selected) >= num_teachers:
            break
        group = tradition_groups[trad_key]
        idx = int(hashlib.sha256((article_id + trad_key).encode()).hexdigest(), 16) % len(group)
        teacher = group[idx]
        # Ensure attribution
        if not teacher.get("attribution"):
            teacher["attribution"] = (
                f"From within the {teacher['tradition']} tradition, {teacher['display_name']} teaches that"
            )
        selected.append(teacher)

    if len(selected) < 2:
        # Not enough distinct traditions — pad from remaining candidates
        used_ids = {t["teacher_id"] for t in selected}
        for c in candidates:
            if c["teacher_id"] not in used_ids and len(selected) < num_teachers:
                if not c.get("attribution"):
                    c["attribution"] = (
                        f"From within the {c['tradition']} tradition, {c['display_name']} teaches that"
                    )
                selected.append(c)
                used_ids.add(c["teacher_id"])

    logger.info(
        "Resolved %d teachers for interfaith article %s topic=%s: %s",
        len(selected), article_id, topic,
        [(t["display_name"], t["tradition"]) for t in selected],
    )
    return selected if selected else [FALLBACK_TEACHER]


def format_multiple_teachers_for_prompt(teachers: list[dict[str, Any]]) -> str:
    """
    Format 2-3 teachers for the multi-teacher interfaith expansion prompt.
    Shows each teacher's knowledge base, then convergence framing.
    """
    blocks = []
    for i, teacher in enumerate(teachers, 1):
        name = teacher.get("display_name", "a Forum teacher")
        tradition = teacher.get("tradition", "interfaith")
        atoms = teacher.get("atoms") or []
        lines = [
            f"TEACHER {i}: {name}",
            f"Tradition: {tradition}",
            f"Attribution: {teacher.get('attribution', '')}",
            f"Approved teachings (use at least 1 atom from this teacher in themes of agreement):",
        ]
        for j, atom in enumerate(atoms, 1):
            atom_text = str(atom).strip().replace("\n", " ").replace("  ", " ")
            lines.append(f"  {j}. {atom_text}")
        blocks.append("\n".join(lines))

    teacher_names = [t.get("display_name", "?") for t in teachers]
    tradition_names = [t.get("tradition", "?") for t in teachers]
    convergence_hint = (
        f"\nCONVERGENCE TASK:\n"
        f"Show where {' and '.join(teacher_names)} — from {', '.join(tradition_names)} traditions respectively — "
        f"AGREE on positive aspects of this news story for helping youth.\n"
        f"Use at least 1 atom from each teacher. Find where different reasoning arrives at the same insight."
    )

    return "\n\n".join(blocks) + "\n" + convergence_hint


def format_teacher_atoms_for_prompt(teacher: dict[str, Any]) -> str:
    """
    Format teacher data as a text block for injection into the LLM user message.
    """
    name = teacher.get("display_name", "a Forum teacher")
    tradition = teacher.get("tradition", "interfaith")
    atoms = teacher.get("atoms") or []
    lines = [
        f"Teacher: {name}",
        f"Tradition: {tradition}",
        f"Attribution: {teacher.get('attribution', '')}",
        "",
        "Approved teachings (use all three, one per paragraph, in the teacher perspective section):",
    ]
    for i, atom in enumerate(atoms, 1):
        # Normalize the atom text
        atom_text = str(atom).strip().replace("\n", " ").replace("  ", " ")
        lines.append(f"  {i}. {name.split()[0]} teaches that {atom_text}")
    return "\n".join(lines)
