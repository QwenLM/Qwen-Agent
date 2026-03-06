"""
Pearl News / EI V2 — Research KB retrieval module.
Reads artifacts/research/kb/ and returns the most relevant entries for a given topic/language.
Used by llm_expand.py to get research_excerpt, and by EI V2 research_loader.py.

Design:
  - Primary key: topic (maps to Pearl News topic keys)
  - Secondary key: region (inferred from language: en→english, ja→japan, zh-cn→china)
  - Sort: date descending (newest first), then confidence descending
  - Returns: formatted text excerpt (for LLM injection) or raw entry list (for programmatic use)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Location of KB files — relative to repo root
_KB_ENTRIES_FILENAME = "entries.jsonl"
_KB_INDEX_FILENAME = "index.json"

# Language → region key
_LANG_TO_REGION = {
    "en": "english",
    "ja": "japan",
    "zh-cn": "china",
    "zh": "china",
    "ja-jp": "japan",
}

# Cache: (kb_path_str) → (entries_list, index_dict)
_CACHE: dict[str, tuple[list, dict]] = {}


def _get_kb_dir(repo_root: Path | None = None) -> Path:
    if repo_root is None:
        # This file: pearl_news/research_kb/retrieval.py
        # parents[0] = pearl_news/research_kb/
        # parents[1] = pearl_news/
        # parents[2] = repo_root (phoenix_omega)
        repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "artifacts" / "research" / "kb"


def _load_kb(kb_dir: Path) -> tuple[list[dict], dict]:
    """Load entries + index from disk (with simple in-process cache)."""
    key = str(kb_dir)
    if key in _CACHE:
        return _CACHE[key]

    entries: list[dict] = []
    index: dict = {}

    entries_path = kb_dir / _KB_ENTRIES_FILENAME
    index_path = kb_dir / _KB_INDEX_FILENAME

    if entries_path.exists():
        with open(entries_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass

    if index_path.exists():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    logger.debug("Loaded %d KB entries from %s", len(entries), kb_dir)
    _CACHE[key] = (entries, index)
    return entries, index


def _invalidate_cache(kb_dir: Path | None = None) -> None:
    """Clear the in-process cache (call after kb_append)."""
    global _CACHE
    if kb_dir:
        _CACHE.pop(str(kb_dir), None)
    else:
        _CACHE.clear()


def query_kb(
    topic: str,
    language: str = "en",
    n: int = 3,
    repo_root: Path | None = None,
    include_global: bool = True,
) -> list[dict[str, Any]]:
    """
    Return top N KB entries for (topic, language/region), sorted by date then confidence.
    include_global=True: also include region=global entries.
    """
    kb_dir = _get_kb_dir(repo_root)
    entries, index = _load_kb(kb_dir)
    if not entries:
        return []

    region = _LANG_TO_REGION.get(language.lower(), "english")

    # Filter by topic
    topic_ids = set((index.get("by_topic") or {}).get(topic, []))
    if not topic_ids:
        # No index hit — fall back to scanning all entries for this topic
        relevant = [e for e in entries if topic in e.get("topics", [])]
    else:
        relevant = [e for e in entries if e.get("id") in topic_ids]

    # Filter by region (prefer region match, optionally include global)
    def region_score(entry: dict) -> int:
        regions = entry.get("regions") or []
        if region in regions:
            return 2  # exact region match
        if include_global and "global" in regions:
            return 1  # global match
        return 0

    relevant = [e for e in relevant if region_score(e) > 0]

    # Sort: region_score desc, then date desc, then confidence desc
    relevant.sort(
        key=lambda e: (
            region_score(e),
            e.get("date") or "0000",
            float(e.get("confidence") or 0),
        ),
        reverse=True,
    )

    return relevant[:n]


def format_excerpt(entries: list[dict], max_words: int = 400) -> str:
    """Format KB entries into a text excerpt for LLM injection."""
    if not entries:
        return ""
    lines = []
    total_words = 0
    for e in entries:
        claim = e.get("claim") or ""
        evidence = e.get("evidence") or ""
        citation = e.get("source_citation") or ""
        invisible = e.get("invisible_script") or ""
        contradiction = e.get("contradiction") or ""

        chunk_parts = []
        if claim:
            chunk_parts.append(f"Finding: {claim}")
            if evidence:
                chunk_parts.append(f"Evidence: {evidence}")
            if citation:
                chunk_parts.append(f"Source: {citation}")
            if invisible:
                chunk_parts.append(f"Invisible script: {invisible}")
            if contradiction:
                chunk_parts.append(f"Contradiction: {contradiction}")
        chunk = " | ".join(chunk_parts)
        chunk_words = len(chunk.split())
        if total_words + chunk_words > max_words and lines:
            break
        if chunk_parts:
            lines.append(chunk)
            total_words += chunk_words

    return "\n\n".join(lines)


def get_research_excerpt(
    topic: str,
    language: str = "en",
    n: int = 3,
    max_words: int = 400,
    repo_root: Path | None = None,
) -> str:
    """
    Main function: get formatted research excerpt for topic+language.
    Used by llm_expand.py as the primary source for research_excerpt.
    Returns empty string if KB is empty or unavailable (caller uses fallback).
    """
    entries = query_kb(topic, language=language, n=n, repo_root=repo_root)
    if not entries:
        logger.debug("KB: no entries for topic=%s language=%s", topic, language)
        return ""
    excerpt = format_excerpt(entries, max_words=max_words)
    logger.debug(
        "KB: %d entries → %d words for topic=%s language=%s",
        len(entries), len(excerpt.split()), topic, language,
    )
    return excerpt


def get_all_entries_for_ei_v2(
    topics: list[str] | None = None,
    repo_root: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Return all KB entries (or filtered by topic list) for EI V2 research loader.
    Does not apply region filter — EI V2 needs full corpus for persona/topic signal building.
    """
    kb_dir = _get_kb_dir(repo_root)
    entries, _ = _load_kb(kb_dir)
    if topics:
        topic_set = set(topics)
        entries = [e for e in entries if any(t in topic_set for t in e.get("topics", []))]
    return entries
