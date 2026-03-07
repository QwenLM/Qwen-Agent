"""
Pearl News — Teacher Readiness Check.

Imported by run_article_pipeline.py at startup to assess whether all teachers
have sufficient approved atoms for the current run. Logs readiness status and
flags blocked teachers.

Usage (standalone):
    python -m pearl_news.pipeline.teacher_readiness

Usage (imported by pipeline):
    from pearl_news.pipeline.teacher_readiness import TeacherReadiness
    readiness = TeacherReadiness(config_root, atoms_root)
    print(readiness.report_pipeline_readiness())
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

ATOMS_PER_TEACHER = 10
MIN_ATOMS_FOR_SELECTION = 3  # Teacher resolver requires at least 3 atoms


class TeacherReadiness:
    """Assess whether teacher atom coverage is sufficient for pipeline runs."""

    def __init__(self, config_root: Path, atoms_root: Path):
        self.config_root = config_root
        self.atoms_root = atoms_root
        self._roster = self._load_roster()
        self._sdg_mapping = self._load_sdg_mapping()
        self._is_production = os.environ.get("PEARL_NEWS_ENV", "dev") == "production"

    def _load_roster(self) -> dict[str, Any]:
        path = self.config_root / "teacher_news_roster.yaml"
        if not path.exists() or yaml is None:
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _load_sdg_mapping(self) -> dict[str, Any]:
        path = self.config_root / "sdg_news_topic_mapping.yaml"
        if not path.exists() or yaml is None:
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _load_topic_atoms(self, topic: str) -> dict[str, Any]:
        p = self.atoms_root / f"topic_{topic}.yaml"
        if not p.exists() or yaml is None:
            return {}
        with open(p, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def check_readiness(self, topic: str, language: str = "en") -> dict[str, Any]:
        """
        For a given topic, classify each roster teacher as ready, partial, or blocked.

        In production mode, only APPROVED atoms count.
        In dev mode, all statuses count.

        Returns:
            {
                'topic': str,
                'language': str,
                'ready': [teacher_ids with >= ATOMS_PER_TEACHER usable atoms],
                'partial': [teacher_ids with MIN_ATOMS..ATOMS_PER_TEACHER-1 usable atoms],
                'blocked': [teacher_ids with < MIN_ATOMS usable atoms],
            }
        """
        roster_teachers = self._roster.get("teachers") or {}
        topic_data = self._load_topic_atoms(topic)
        topic_teachers = topic_data.get("teachers") or {}

        # Language → region mapping for filtering
        lang_map = {"en": "english", "zh-cn": "china", "ja": "japan", "zh": "china"}
        region = lang_map.get(language, "global")

        result: dict[str, Any] = {
            "topic": topic,
            "language": language,
            "ready": [],
            "partial": [],
            "blocked": [],
        }

        for teacher_id, teacher_info in roster_teachers.items():
            assigned_topics = teacher_info.get("news_topics") or []
            if topic not in assigned_topics:
                continue  # This teacher doesn't cover this topic

            # Region filter
            region_fit = teacher_info.get("region_fit") or ["global"]
            if region not in region_fit and "global" not in region_fit:
                continue

            # Get atom data
            atom_entry = topic_teachers.get(teacher_id) or {}
            atoms = atom_entry.get("atoms") or []
            status = atom_entry.get("status", "starter")

            # In production, only approved atoms count
            if self._is_production and status != "approved":
                usable_count = 0
            else:
                usable_count = len(atoms)

            if usable_count >= ATOMS_PER_TEACHER:
                result["ready"].append(teacher_id)
            elif usable_count >= MIN_ATOMS_FOR_SELECTION:
                result["partial"].append(teacher_id)
            else:
                result["blocked"].append(teacher_id)

        return result

    def report_pipeline_readiness(self) -> str:
        """
        Generate a summary report across all topics.
        Returns a formatted string suitable for logging.
        """
        topics = sorted((self._sdg_mapping.get("topic_to_sdg") or {}).keys())
        env_label = "PRODUCTION" if self._is_production else "DEV"
        lines = [
            f"TEACHER READINESS REPORT (env={env_label})",
            "-" * 50,
        ]

        all_ready = True
        for topic in topics:
            readiness = self.check_readiness(topic)
            n_ready = len(readiness["ready"])
            n_partial = len(readiness["partial"])
            n_blocked = len(readiness["blocked"])
            total = n_ready + n_partial + n_blocked

            if n_blocked > 0:
                status = "BLOCKED"
                all_ready = False
            elif n_partial > 0:
                status = "PARTIAL"
                all_ready = False
            else:
                status = "READY"

            detail = f"{n_ready}/{total} ready"
            if n_partial:
                detail += f", {n_partial} partial"
            if n_blocked:
                detail += f", {n_blocked} blocked"
                # List blocked teachers
                blocked_names = []
                for tid in readiness["blocked"]:
                    name = ((self._roster.get("teachers") or {}).get(tid) or {}).get("display_name", tid)
                    blocked_names.append(name)
                detail += f" ({', '.join(blocked_names)})"

            lines.append(f"  {topic:>20}: [{status:>7}] {detail}")

        lines.append("-" * 50)
        if all_ready:
            lines.append("All topics READY for pipeline run.")
        else:
            lines.append("Some topics have gaps. Blocked teachers will trigger fallback.")
            if self._is_production:
                lines.append("NOTE: Production mode — only APPROVED atoms counted.")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Standalone CLI
# ---------------------------------------------------------------------------
def main() -> int:
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    ap = argparse.ArgumentParser(description="Pearl News: Teacher Readiness Check")
    ap.add_argument("--topic", default=None, help="Check readiness for specific topic only")
    ap.add_argument("--language", default="en", help="Language for region filtering (en/ja/zh-cn)")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    config_root = root / "config"
    atoms_root = root / "atoms" / "teacher_quotes_practices"

    readiness = TeacherReadiness(config_root, atoms_root)

    if args.topic:
        result = readiness.check_readiness(args.topic, args.language)
        print(f"\nReadiness for {args.topic} ({args.language}):")
        for category in ["ready", "partial", "blocked"]:
            if result[category]:
                print(f"  {category}: {', '.join(result[category])}")
    else:
        print(readiness.report_pipeline_readiness())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
