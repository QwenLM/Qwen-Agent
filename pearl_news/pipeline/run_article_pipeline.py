#!/usr/bin/env python3
"""
Pearl News — full pipeline: feeds → ingest → classify → template select → assemble → quality gates → QC.
Output: final article drafts (title, content, metadata) to --out-dir; build manifests for audit.

Usage:
  python -m pearl_news.pipeline.run_article_pipeline --feeds pearl_news/config/feeds.yaml --out-dir artifacts/pearl_news/drafts
  python -m pearl_news.pipeline.run_article_pipeline --out-dir ./output --limit 10
  python -m pearl_news.pipeline.run_article_pipeline --no-filter-qc   # output all articles (including QC-failed)
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

from pearl_news.pipeline.feed_ingest import ingest_feeds
from pearl_news.pipeline.topic_sdg_classifier import classify_sdgs
from pearl_news.pipeline.template_selector import select_templates
from pearl_news.pipeline.article_assembler import assemble_articles
from pearl_news.pipeline.llm_expand import run_expansion
from pearl_news.pipeline.quality_gates import run_quality_gates
from pearl_news.pipeline.qc_checklist import run_qc_checklist

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def _build_manifest_item(item: dict[str, Any]) -> dict[str, Any]:
    """One entry for build manifest (audit trail)."""
    return {
        "article_id": item.get("id", ""),
        "feed_item": {
            "id": item.get("id", ""),
            "url": item.get("url", ""),
            "title": item.get("article_title") or item.get("title", ""),
            "published": item.get("pub_date", ""),
        },
        "template_id": item.get("template_id", ""),
        "atom_ids_used": {
            "news_event": [item.get("id", "")],
            "youth_impact": [],
            "teacher_quotes_practices": [],
            "sdg_refs": [item.get("primary_sdg", "")],
        },
        "model_used": "none",
        "prompt_version": "",
        "qc_results": item.get("qc_results") or {},
        "signatures": {
            "headline_sig": item.get("headline_sig", ""),
            "lede_sig": item.get("lede_sig", ""),
            "teacher_sig": "",
            "sdg_sig": item.get("primary_sdg", ""),
        },
        "built_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Pearl News: feeds → draft articles")
    ap.add_argument(
        "--feeds",
        default=None,
        help="Path to feeds.yaml (default: pearl_news/config/feeds.yaml)",
    )
    ap.add_argument(
        "--out-dir",
        default="artifacts/pearl_news/drafts",
        help="Output directory for drafts and build manifest",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of feed items to process (across all feeds)",
    )
    ap.add_argument(
        "--per-feed-limit",
        type=int,
        default=None,
        help="Max items per feed (before global --limit)",
    )
    ap.add_argument(
        "--no-filter-qc",
        action="store_true",
        help="Output all articles (including QC-failed); default is only QC-passed",
    )
    ap.add_argument(
        "--expand",
        action="store_true",
        help="Run LLM expansion to target word count (requires llm_expansion.yaml and Qwen/OpenAI-compatible API)",
    )
    ap.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose logging",
    )
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    feeds_path = Path(args.feeds) if args.feeds else root / "config" / "feeds.yaml"
    out_dir = Path(args.out_dir)

    if not feeds_path.exists():
        logger.error("Feeds config not found: %s", feeds_path)
        return 1

    if args.verbose:
        logging.getLogger("pearl_news").setLevel(logging.DEBUG)

    out_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Ingest
    try:
        items = ingest_feeds(feeds_path, limit=args.limit, per_feed_limit=args.per_feed_limit)
    except Exception as e:
        logger.exception("Feed ingest failed: %s", e)
        return 1
    logger.info("Ingested %d items", len(items))

    if not items:
        logger.warning("No items to process; writing empty manifest.")
        manifest = {"build_date": datetime.now(timezone.utc).isoformat(), "feeds_path": str(feeds_path), "item_count": 0, "articles_count": 0, "items": [], "build_manifests": []}
        (out_dir / "ingest_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return 0

    # Step 2: Classify (topic + SDG)
    items = classify_sdgs(items)
    # Step 3: Select template
    items = select_templates(items)
    # Step 4: Assemble (teacher + youth + SDG refs in content)
    items = assemble_articles(items)
    # Step 4b: Optional LLM expansion toward target word count (e.g. Qwen via GitHub/local)
    if args.expand:
        config_root = root / "config"
        items = run_expansion(items, config_root=config_root)
    # Step 5: Quality gates (sets qc_results, qc_passed on each)
    items = run_quality_gates(items)
    # Step 6: QC checklist (optionally filter to passed only)
    articles_to_output = run_qc_checklist(items, filter_to_passed=not args.no_filter_qc)

    # Ingest manifest (raw + summary)
    build_date = datetime.now(timezone.utc).isoformat()
    ingest_manifest = {
        "build_date": build_date,
        "feeds_path": str(feeds_path),
        "limit": args.limit,
        "per_feed_limit": args.per_feed_limit,
        "item_count": len(items),
        "articles_passed_qc": sum(1 for i in items if i.get("qc_passed")),
        "articles_output": len(articles_to_output),
        "items": [{"id": i.get("id"), "title": i.get("title"), "topic": i.get("topic"), "qc_passed": i.get("qc_passed")} for i in items],
    }
    (out_dir / "ingest_manifest.json").write_text(json.dumps(ingest_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Wrote %s", out_dir / "ingest_manifest.json")

    # Author rotation (teacher-assigned, alternate) and placeholder images by template
    config_root = root / "config"
    author_ids = [1]
    placeholder_by_template = {}
    placeholder_default = None
    if yaml and config_root.exists():
        aw_path = config_root / "wordpress_authors.yaml"
        if aw_path.exists():
            with open(aw_path, "r", encoding="utf-8") as f:
                aw = yaml.safe_load(f) or {}
            author_ids = list(aw.get("author_ids") or [1])
        site_path = config_root / "site.yaml"
        if site_path.exists():
            with open(site_path, "r", encoding="utf-8") as f:
                site = yaml.safe_load(f) or {}
            placeholder_by_template = site.get("placeholder_featured_image_by_template") or {}
            placeholder_default = site.get("placeholder_featured_image_default")

    # Build manifests (per-article audit) and final article JSON
    build_manifests = []
    for i, item in enumerate(articles_to_output):
        article_id = item.get("id", "")
        author_id = author_ids[i % len(author_ids)] if author_ids else None
        template_id = item.get("template_id") or "hard_news_spiritual_response"
        images = item.get("images") or []
        featured_image = None
        featured_image_url = None
        featured_image_path = None
        if images and isinstance(images[0], dict) and images[0].get("url"):
            featured_image = images[0]
        else:
            path = placeholder_by_template.get(template_id) or placeholder_default
            if path:
                featured_image_path = path

        # Final article output (for WordPress script and humans)
        article_payload = {
            "title": item.get("article_title") or item.get("title", ""),
            "content": item.get("content", ""),
            "slug": article_id,
            "author": author_id,
            "article_type": template_id,
            "topic": item.get("topic", ""),
            "primary_sdg": item.get("primary_sdg", ""),
            "un_body": item.get("un_body", ""),
            "url": item.get("url", ""),
            "pub_date": item.get("pub_date", ""),
            "source_feed_id": item.get("source_feed_id", ""),
            "qc_passed": item.get("qc_passed", False),
            "qc_results": item.get("qc_results", {}),
        }
        if featured_image:
            article_payload["featured_image"] = featured_image
        if featured_image_url:
            article_payload["featured_image_url"] = featured_image_url
        if featured_image_path:
            article_payload["featured_image_path"] = featured_image_path
        (out_dir / f"article_{article_id}.json").write_text(json.dumps(article_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        build_manifests.append(_build_manifest_item(item))

    (out_dir / "build_manifests.json").write_text(json.dumps(build_manifests, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Wrote %d article drafts and build_manifests.json", len(articles_to_output))

    logger.info("Pipeline complete. Output: %s (%d items → %d articles)", out_dir, len(items), len(articles_to_output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
