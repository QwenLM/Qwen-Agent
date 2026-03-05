"""
Pearl News — fetch RSS/Atom feeds from feeds.yaml and normalize entries to a common schema.

Each normalized item has: id, title, url, pub_date, summary, source_feed_id, source_feed_title,
and optionally images (list of {url, credit, source_url, caption}) for article featured image
and proper attribution.
Downstream: topic_sdg_classifier, template_selector, article_assembler consume this list.
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import feedparser
except ImportError:
    feedparser = None

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger(__name__)


def _parse_pub_date(entry: Any) -> str:
    """Return ISO-like pub date string from feed entry."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            t = entry.published_parsed
            dt = datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec, tzinfo=timezone.utc)
            return dt.isoformat()
        except Exception:
            pass
    if getattr(entry, "published", None):
        return str(entry.published)
    return datetime.now(timezone.utc).isoformat()


def _stable_id(feed_id: str, entry: Any) -> str:
    """Generate a stable id for a feed entry (for dedup and manifest)."""
    raw = f"{feed_id}:{getattr(entry, 'link', '')}:{getattr(entry, 'title', '')}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _image_content_type(typ: str) -> bool:
    """True if type looks like an image MIME type."""
    if not typ:
        return False
    t = typ.lower().strip()
    return t.startswith("image/") or t == "image"


def _first_img_url_from_html(html: str) -> str | None:
    """Extract first img src URL from HTML/summary. Returns None if none found."""
    if not html or not isinstance(html, str):
        return None
    # Match src="...", src='...', or unquoted URL in img tag
    m = re.search(r'<img[^>]+src\s*=\s*["\']?([^\s"\'<>]+)["\']?', html, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _extract_images_from_entry(entry: Any, feed_id: str, feed_title: str, article_url: str) -> list[dict[str, Any]]:
    """
    Extract image URLs and attribution from a feed entry.
    Tries: media_content, media_thumbnail, enclosures (image/*), first img in summary.
    Returns list of dicts with url, credit, source_url, caption (optional).
    """
    images: list[dict[str, Any]] = []
    seen: set[str] = set()
    credit = feed_title or feed_id
    source_url = article_url or ""

    def _add(url: str | None, caption: str | None = None) -> None:
        if not url or not url.startswith("http"):
            return
        url = url.split("?")[0].strip()
        if url in seen:
            return
        seen.add(url)
        images.append({
            "url": url,
            "credit": credit,
            "source_url": source_url,
            **({"caption": caption} if caption else {}),
        })

    # Media RSS: media_content (list of dicts with url)
    if getattr(entry, "media_content", None):
        for mc in entry.media_content:
            if isinstance(mc, dict) and mc.get("url"):
                _add(mc.get("url"), mc.get("caption") or None)
            elif getattr(mc, "url", None):
                _add(getattr(mc, "url", None), getattr(mc, "caption", None))

    # Media RSS: media_thumbnail
    if getattr(entry, "media_thumbnail", None):
        for mt in entry.media_thumbnail:
            u = mt.get("url") if isinstance(mt, dict) else getattr(mt, "url", None)
            _add(u)

    # Enclosures (RSS 2.0) — image types only
    for enc in getattr(entry, "enclosures", []) or []:
        href = enc.get("href") if isinstance(enc, dict) else getattr(enc, "href", None)
        typ = enc.get("type") if isinstance(enc, dict) else getattr(enc, "type", None)
        if href and _image_content_type(typ or ""):
            _add(href)

    # First <img> in summary/description
    summary = getattr(entry, "summary", None) or getattr(entry, "description", None)
    if summary:
        u = _first_img_url_from_html(str(summary))
        _add(u)

    return images


def load_feed_config(feeds_path: str | Path) -> list[dict[str, Any]]:
    """Load feeds list from feeds.yaml. Returns list of feed configs (id, url, type, description)."""
    path = Path(feeds_path)
    if not path.exists():
        raise FileNotFoundError(f"Feeds config not found: {path}")
    if yaml is None:
        raise RuntimeError("PyYAML is required; install with: pip install pyyaml")
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    return config.get("feeds") or []


def ingest_feeds(
    feeds_path: str | Path,
    limit: int | None = None,
    per_feed_limit: int | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch and normalize RSS/Atom feeds to a common article-ready schema.

    :param feeds_path: Path to feeds.yaml (list of feed configs with id, url).
    :param limit: Max total items to return across all feeds (None = no cap).
    :param per_feed_limit: Max items per feed (None = no cap).
    :return: List of normalized items. Each item has:
        id, title, url, pub_date, summary, source_feed_id, source_feed_title, raw_title, raw_summary,
        images (list of {url, credit, source_url, caption?}) for featured image and attribution.
    """
    if feedparser is None:
        raise RuntimeError("feedparser is required; install with: pip install feedparser")

    feed_configs = load_feed_config(feeds_path)
    if not feed_configs:
        logger.warning("No feeds defined in %s", feeds_path)
        return []

    all_items: list[dict[str, Any]] = []

    for fc in feed_configs:
        feed_id = fc.get("id") or fc.get("name") or "unknown"
        feed_url = fc.get("url")
        if not feed_url:
            logger.warning("Feed %s has no url, skipping", feed_id)
            continue
        try:
            parsed = feedparser.parse(feed_url)
            feed_title = getattr(parsed.feed, "title", None) or feed_id
        except Exception as e:
            logger.exception("Failed to fetch feed %s (%s): %s", feed_id, feed_url, e)
            continue

        entries = getattr(parsed, "entries", [])
        if per_feed_limit is not None:
            entries = entries[:per_feed_limit]

        for entry in entries:
            link = getattr(entry, "link", "") or ""
            title = getattr(entry, "title", "") or "(No title)"
            summary = ""
            if getattr(entry, "summary", None):
                summary = entry.summary
            elif getattr(entry, "description", None):
                summary = entry.description

            images = _extract_images_from_entry(entry, feed_id, feed_title, link)
            normalized = {
                "id": _stable_id(feed_id, entry),
                "title": title,
                "url": link,
                "pub_date": _parse_pub_date(entry),
                "summary": summary,
                "source_feed_id": feed_id,
                "source_feed_title": feed_title,
                "raw_title": title,
                "raw_summary": summary,
                "images": images,
            }
            all_items.append(normalized)

        if limit is not None and len(all_items) >= limit:
            break

    if limit is not None:
        all_items = all_items[:limit]

    logger.info("Ingested %d items from %s", len(all_items), feeds_path)
    return all_items
