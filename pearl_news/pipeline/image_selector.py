"""
Pearl News — rule-based featured image selection.
Reads pearl_news/config/image_catalog.yaml and selects the best image per article.
Priority: feed image (if quality threshold met) → template+topic match → topic match → template match → default.
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


def _load_catalog(config_root: Path) -> dict[str, Any]:
    path = config_root / "image_catalog.yaml"
    if not path.exists() or yaml is None:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def select_featured_image(
    item: dict[str, Any],
    config_root: Path | None = None,
) -> dict[str, Any] | None:
    """
    Select the best featured image for an article item.
    Returns a dict: {path, label, alt_text, caption, source} or None.
    """
    root = Path(__file__).resolve().parent.parent
    config_root = config_root or (root / "config")
    catalog = _load_catalog(config_root)
    if not catalog:
        return None

    policy = catalog.get("policy") or {}
    images = catalog.get("images") or {}
    default_id = catalog.get("default_image_id") or "global_update"

    template_id = (item.get("template_id") or "hard_news_spiritual_response").lower()
    topic = (item.get("topic") or "").lower()

    # 1. Feed image — if available and quality threshold met
    if policy.get("prefer_feed_image_if_available", True):
        threshold = float(policy.get("feed_image_quality_threshold") or 0.6)
        feed_images = item.get("images") or []
        for img in feed_images:
            if isinstance(img, dict) and img.get("url"):
                # Assign a basic quality score: has url + credit = 0.7, url only = 0.6
                feed_quality = 0.7 if img.get("credit") or img.get("caption") else 0.6
                if feed_quality >= threshold:
                    logger.info("Article %s: using feed image (quality=%.1f)", item.get("id"), feed_quality)
                    return {
                        "path": None,
                        "url": img["url"],
                        "label": "feed image",
                        "alt_text": img.get("caption") or f"Image from {item.get('article_title', 'article')}",
                        "caption": img.get("caption") or img.get("credit") or "",
                        "source": "feed",
                    }

    # 2. Score catalog images
    scored: list[tuple[float, str, dict]] = []
    for image_id, img_data in images.items():
        score = 0.0
        base_quality = float(img_data.get("quality_score") or 0.5)
        suggested_templates = [t.lower() for t in (img_data.get("suggested_templates") or [])]
        topic_tags = [t.lower() for t in (img_data.get("topic_tags") or [])]
        lang_risk = (img_data.get("language_text_risk") or "none").lower()

        # Template match: +0.4
        if template_id in suggested_templates:
            score += 0.4
        # Topic match: +0.3
        if topic in topic_tags:
            score += 0.3
        # Language text risk: -0.2 for "high", -0.1 for "low"
        if lang_risk == "high":
            score -= 0.2
        elif lang_risk == "low":
            score -= 0.1
        # Base quality contributes: * 0.3
        score += base_quality * 0.3

        scored.append((score, image_id, img_data))

    if not scored:
        return None

    # Sort descending by score; use default as final fallback
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_id, best_data = scored[0]

    # If best score is very low (no template/topic match), use default
    if best_score < 0.2 and default_id in images:
        best_id = default_id
        best_data = images[default_id]

    logger.info(
        "Article %s: selected image '%s' (score=%.2f, template=%s, topic=%s)",
        item.get("id"), best_id, best_score, template_id, topic,
    )
    return {
        "path": best_data.get("path"),
        "url": None,
        "label": best_data.get("label") or best_id,
        "alt_text": best_data.get("alt_default") or f"Image for {item.get('article_title', 'article')}",
        "caption": best_data.get("caption_default") or "",
        "source": "catalog",
        "catalog_id": best_id,
        "score": best_score,
    }


def run_image_selection(
    items: list[dict[str, Any]],
    config_root: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Select featured image for each item. Attaches _featured_image to each item.
    """
    root = Path(__file__).resolve().parent.parent
    config_root = config_root or (root / "config")
    for item in items:
        selected = select_featured_image(item, config_root=config_root)
        if selected:
            item["_featured_image"] = selected
        else:
            item["_featured_image"] = None
    return items
