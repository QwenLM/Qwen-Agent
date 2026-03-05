#!/usr/bin/env python3
"""
Post a Pearl News article to WordPress (BlogSite) via REST API.

Requires env vars: WORDPRESS_SITE_URL, WORDPRESS_USERNAME, WORDPRESS_APP_PASSWORD.
Do not commit the app password. Generate it in WP Admin > Users > Your Profile > Application Passwords.

Usage:
  # From article JSON (e.g. pipeline draft output)
  python scripts/pearl_news_post_to_wp.py --article artifacts/pearl_news/drafts/article_001.json
  python scripts/pearl_news_post_to_wp.py --article draft.json --status publish

  # Inline
  python scripts/pearl_news_post_to_wp.py --title "Headline" --content "Body text or HTML..."

  # Dry run (validate env and payload, do not POST)
  python scripts/pearl_news_post_to_wp.py --article draft.json --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pearl_news.publish.wordpress_client import post_article, WordPressPublishError


def _slug_from_title(title: str) -> str:
    """Simple slug: lowercase, replace spaces with hyphens, strip non-alnum."""
    s = "".join(c if c.isalnum() or c in " -" else "" for c in title)
    return "-".join(s.lower().split())[:100]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Post Pearl News article to WordPress via REST API"
    )
    ap.add_argument(
        "--article",
        type=Path,
        default=None,
        help="Path to article JSON (keys: title, content; optional: slug, status, categories, tags)",
    )
    ap.add_argument("--title", default=None, help="Post title (when not using --article)")
    ap.add_argument("--content", default=None, help="Post content (when not using --article)")
    ap.add_argument(
        "--status",
        choices=("draft", "publish"),
        default="draft",
        help="Post status (default: draft for review)",
    )
    ap.add_argument(
        "--no-disclaimer",
        action="store_true",
        help="Do not append Pearl News disclaimer to content",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate env and payload only; do not send to WordPress",
    )
    args = ap.parse_args()

    if args.article is not None:
        if not args.article.exists():
            print(f"Error: article file not found: {args.article}", file=sys.stderr)
            return 1
        try:
            data = json.loads(args.article.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"Error: invalid JSON in {args.article}: {e}", file=sys.stderr)
            return 1
        title = data.get("title") or data.get("headline")
        content = data.get("content") or data.get("body") or data.get("text")
        slug = data.get("slug")
        author = data.get("author")  # WordPress user ID (teacher-assigned, alternate)
        categories = data.get("categories") or data.get("category_ids")
        tags = data.get("tags") or data.get("tag_ids")
        featured_image = data.get("featured_image")  # { url, credit, source_url, caption? }
        featured_image_url = data.get("featured_image_url")  # or plain URL
        featured_image_path = data.get("featured_image_path")  # path relative to repo (e.g. pearl_news/del_intake_pics/...)
        if featured_image_path:
            featured_image_path = REPO_ROOT / featured_image_path
        if not title or not content:
            print(
                "Error: article JSON must have title (or headline) and content (or body/text)",
                file=sys.stderr,
            )
            return 1
    else:
        if not args.title or not args.content:
            print(
                "Error: provide --article path or both --title and --content",
                file=sys.stderr,
            )
            return 1
        title = args.title
        content = args.content
        slug = None
        author = None
        categories = None
        tags = None
        featured_image = None
        featured_image_url = None
        featured_image_path = None

    if args.dry_run:
        try:
            from pearl_news.publish.wordpress_client import _get_credentials
            _get_credentials()
        except WordPressPublishError as e:
            print(f"Dry-run env check failed: {e}", file=sys.stderr)
            return 1
        print("Dry-run: env OK, payload prepared (not sent).")
        print(f"  title: {title[:60]}..." if len(title) > 60 else f"  title: {title}")
        print(f"  status: {args.status}")
        return 0

    try:
        result = post_article(
            title=title,
            content=content,
            status=args.status,
            slug=slug or _slug_from_title(title),
            author=author,
            categories=categories,
            tags=tags,
            append_disclaimer=False,  # Disclaimer on site About; not repeated per article
            featured_image=featured_image,
            featured_image_url=featured_image_url,
            featured_image_path=featured_image_path,
        )
    except WordPressPublishError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
