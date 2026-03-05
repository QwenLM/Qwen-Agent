"""
Pearl News — select one of the 5 article templates per feed item based on topic, SDG, and source.
Uses article_templates_index.yaml; applies simple rules for diversity.
USLF group template (interfaith_dialogue_report) only ~5% of the time; rest use single-teacher-focused templates.
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

TEMPLATE_IDS = [
    "hard_news_spiritual_response",
    "youth_feature",
    "interfaith_dialogue_report",
    "explainer_context",
    "commentary",
]

# Default topic → template; interfaith_dialogue_report is group/USLF style, used only ~5% (see below)
DEFAULT_TOPIC_TO_TEMPLATE = {
    "mental_health": "youth_feature",
    "education": "youth_feature",
    "peace_conflict": "hard_news_spiritual_response",  # was interfaith; single-teacher default
    "inequality": "explainer_context",
}


def _load_index(config_root: Path) -> dict[str, Any]:
    path = config_root / "article_templates_index.yaml"
    if not path.exists() or yaml is None:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _use_uslf_group_template(item: dict[str, Any], config_root: Path) -> bool:
    """True ~5% of the time (deterministic from item id); else use single-teacher template."""
    ratio = 0.05
    path = config_root / "template_diversity.yaml"
    if path.exists() and yaml:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        ratio = float(data.get("uslf_group_article_ratio", 0.05))
    item_id = (item.get("id") or item.get("title") or "").encode("utf-8")
    h = int(hashlib.sha256(item_id).hexdigest(), 16) % 100
    return (h / 100.0) < ratio


def select_templates(
    items: list[dict[str, Any]],
    config_root: Path | None = None,
    topic_to_template: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """
    Set template_id on each item.
    Priority:
    1) suggested_template from classifier
    2) caller override mapping (topic_to_template)
    3) config topic_to_template mapping (if present in article_templates_index.yaml)
    4) default topic mapping
    5) source heuristics
    6) hard_news_spiritual_response fallback
    """
    root = Path(__file__).resolve().parent.parent
    config_root = config_root or (root / "config")
    index = _load_index(config_root)
    templates = index.get("templates") or {}
    config_topic_map = index.get("topic_to_template") or {}
    merged_topic_map = dict(DEFAULT_TOPIC_TO_TEMPLATE)
    merged_topic_map.update(config_topic_map)
    if topic_to_template:
        merged_topic_map.update(topic_to_template)

    for i, item in enumerate(items):
        suggested = item.get("suggested_template")
        source = item.get("source_feed_id") or ""
        topic = item.get("topic") or ""

        if suggested and suggested in TEMPLATE_IDS:
            template_id = suggested
        elif topic in merged_topic_map and merged_topic_map[topic] in TEMPLATE_IDS:
            template_id = merged_topic_map[topic]
        elif source == "un_news_sdgs" and topic in ("education", "mental_health"):
            template_id = "youth_feature"
        elif source == "un_news_sdgs":
            template_id = "explainer_context"
        else:
            template_id = "hard_news_spiritual_response"

        # Group/USLF template (interfaith_dialogue_report): only ~5% of the time
        use_group = _use_uslf_group_template(item, config_root)
        if template_id == "interfaith_dialogue_report" and not use_group:
            template_id = "hard_news_spiritual_response"
        # For topics that suit group style (e.g. peace_conflict), assign interfaith ~5% of the time
        if template_id == "hard_news_spiritual_response" and topic in ("peace_conflict",) and use_group:
            template_id = "interfaith_dialogue_report"

        item["template_id"] = template_id
        if template_id in templates:
            item["template_file"] = templates[template_id].get("file") or f"{template_id}.yaml"
        else:
            item["template_file"] = f"{template_id}.yaml"

    logger.info("Selected templates for %d items", len(items))
    return items
