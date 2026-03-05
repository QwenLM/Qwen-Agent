"""
Pearl News — classify feed items by topic and SDG using keyword rules from sdg_news_topic_mapping.yaml.
Assigns topic, primary_sdg, sdg_labels, un_body for downstream template selection and assembly.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger(__name__)

DEFAULT_TOPIC = "partnerships"
DEFAULT_SDG = "17"


def _load_mapping(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not path.exists() or yaml is None:
        return {}, []
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    topic_to_sdg = data.get("topic_to_sdg") or {}
    keyword_to_topic = data.get("keyword_to_topic") or []
    return topic_to_sdg, keyword_to_topic


def _classify_text(text: str, keyword_to_topic: list[dict]) -> str | None:
    """Return topic key if any keyword list matches (case-insensitive)."""
    if not text:
        return None
    lower = text.lower()
    for rule in keyword_to_topic:
        keywords = rule.get("keywords") or []
        topic = rule.get("topic")
        if not topic:
            continue
        for kw in keywords:
            if kw.lower() in lower:
                return topic
    return None


def classify_sdgs(
    items: list[dict[str, Any]],
    config_root: Path | None = None,
    config_path: Path | None = None,
) -> list[dict[str, Any]]:
    """
    For each item, set topic, primary_sdg, sdg_labels, un_body from sdg_news_topic_mapping.
    Uses title + summary for keyword matching; defaults to DEFAULT_TOPIC/DEFAULT_SDG if no match.
    """
    root = Path(__file__).resolve().parent.parent
    if config_path is not None:
        mapping_path = config_path
    else:
        config_root = config_root or (root / "config")
        mapping_path = config_root / "sdg_news_topic_mapping.yaml"
    topic_to_sdg, keyword_to_topic = _load_mapping(mapping_path)

    for item in items:
        title = item.get("title") or item.get("raw_title") or ""
        summary = item.get("summary") or item.get("raw_summary") or ""
        text = f"{title} {summary}"

        topic = _classify_text(text, keyword_to_topic) or "general"
        item["topic"] = topic

        mapping = (
            topic_to_sdg.get(topic)
            or topic_to_sdg.get("general")
            or topic_to_sdg.get(DEFAULT_TOPIC)
            or {}
        )
        primary_sdg = mapping.get("primary_sdg") or DEFAULT_SDG
        sdg_labels = mapping.get("sdg_labels") or {primary_sdg: "Partnerships for the Goals"}
        un_body = mapping.get("un_body") or "United Nations"

        item["primary_sdg"] = primary_sdg
        item["sdg_labels"] = sdg_labels
        item["un_body"] = un_body
        item["suggested_template"] = "hard_news_spiritual_response"

    logger.info("Classified %d items (topic/SDG)", len(items))
    return items
