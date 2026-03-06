"""
Pearl News — resolve a named teacher (name, tradition, atoms) for a given article topic.
Reads pearl_news/config/teacher_news_roster.yaml and pearl_news/atoms/teacher_quotes_practices/topic_<topic>.yaml.
Returns one teacher deterministically per article (using article id hash, same logic as group-vs-single).
"""
from __future__ import annotations

import hashlib
import logging
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
    "teacher_id": None,
    "display_name": "a teacher from the United Spiritual Leaders Forum",
    "tradition": "interfaith",
    "attribution": "A teacher from the United Spiritual Leaders Forum teaches that",
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
