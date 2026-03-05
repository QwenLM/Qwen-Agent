"""
Pearl News — WordPress REST API client for posting articles to the blog (BlogSite theme).

Credentials are read from environment variables only (never committed):
  WORDPRESS_SITE_URL   — e.g. https://pearlnewsuna.org (no trailing slash)
  WORDPRESS_USERNAME   — WP username (e.g. application user)
  WORDPRESS_APP_PASSWORD — Application password from WP Admin > Users > Profile > Application Passwords

Uses Basic Auth; posts to /wp-json/wp/v2/posts. Supports featured image: upload from URL or from local file path.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    requests = None


class WordPressPublishError(Exception):
    """Raised when WordPress API request fails."""
    pass


def _normalize_site_url(raw: str) -> str:
    """
    Normalize WP site URL from env.
    - Trims whitespace and trailing slash
    - Adds https:// when scheme is missing
    - Validates scheme + host
    """
    site = (raw or "").strip().rstrip("/")
    if not site:
        return site
    if "://" not in site:
        site = f"https://{site}"
    parsed = urlparse(site)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise WordPressPublishError(
            f"Invalid WORDPRESS_SITE_URL: {raw!r}. Expected e.g. https://pearlnewsuna.org"
        )
    # Canonicalize to origin only, so inputs like:
    # - https://example.org/wp-admin
    # - https://example.org/wp-json/wp/v2
    # still resolve to the correct base site URL.
    return f"{parsed.scheme}://{parsed.netloc}"


def _get_credentials() -> tuple[str, str, str]:
    site_url = _normalize_site_url(os.environ.get("WORDPRESS_SITE_URL", ""))
    username = os.environ.get("WORDPRESS_USERNAME", "")
    app_password = os.environ.get("WORDPRESS_APP_PASSWORD", "").replace(" ", "").strip()
    if not site_url or not username or not app_password:
        raise WordPressPublishError(
            "Set WORDPRESS_SITE_URL, WORDPRESS_USERNAME, and WORDPRESS_APP_PASSWORD in the environment. "
            "Do not commit the app password to the repo."
        )
    return site_url, username, app_password


def _auth_headers(username: str, app_password: str) -> dict[str, str]:
    credentials = f"{username}:{app_password}"
    token = base64.b64encode(credentials.encode()).decode("utf-8")
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


def _upload_media_from_url(
    site_url: str,
    username: str,
    app_password: str,
    image_url: str,
    caption: str | None = None,
    alt_text: str | None = None,
) -> int:
    """
    Download image from URL and upload to WordPress Media Library. Returns attachment ID.
    :raises WordPressPublishError: On download or upload failure.
    """
    if requests is None:
        raise WordPressPublishError("Install requests: pip install requests")
    resp = requests.get(image_url, timeout=15)
    resp.raise_for_status()
    data = resp.content
    # Derive filename from URL or use default
    filename = "pearl_news_image.jpg"
    if image_url.rstrip("/").split("/")[-1].split("?")[0]:
        candidate = image_url.rstrip("/").split("/")[-1].split("?")[0]
        if "." in candidate and len(candidate) < 200:
            filename = candidate
    files = {"file": (filename, data, "application/octet-stream")}
    upload_url = f"{site_url}/wp-json/wp/v2/media"
    headers = _auth_headers(username, app_password)
    # WP expects multipart; remove Content-Type so requests sets boundary
    headers.pop("Content-Type", None)
    r = requests.post(upload_url, headers=headers, files=files, timeout=30)
    if not r.ok:
        try:
            err = r.json()
        except Exception:
            err = {"message": r.text or r.reason}
        raise WordPressPublishError(f"WordPress media upload error {r.status_code}: {err}")
    media = r.json()
    att_id = media.get("id")
    if not att_id:
        raise WordPressPublishError("WordPress media upload returned no attachment id")
    # Optionally set caption/alt via PATCH
    if caption or alt_text:
        patch_url = f"{site_url}/wp-json/wp/v2/media/{att_id}"
        patch_body: dict[str, Any] = {}
        if caption:
            patch_body["caption"] = {"raw": caption}
        if alt_text:
            patch_body["alt_text"] = alt_text
        if patch_body:
            requests.patch(
                patch_url,
                headers={**_auth_headers(username, app_password), "Content-Type": "application/json"},
                json=patch_body,
                timeout=15,
            )
    return int(att_id)


def _upload_media_from_file(
    site_url: str,
    username: str,
    app_password: str,
    file_path: Path | str,
    caption: str | None = None,
    alt_text: str | None = None,
) -> int:
    """
    Upload image from local file to WordPress Media Library. Returns attachment ID.
    :raises WordPressPublishError: On file read or upload failure.
    """
    if requests is None:
        raise WordPressPublishError("Install requests: pip install requests")
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise WordPressPublishError(f"Featured image file not found: {path}")
    data = path.read_bytes()
    filename = path.name
    files = {"file": (filename, data, "application/octet-stream")}
    upload_url = f"{site_url}/wp-json/wp/v2/media"
    headers = _auth_headers(username, app_password)
    headers.pop("Content-Type", None)
    r = requests.post(upload_url, headers=headers, files=files, timeout=30)
    if not r.ok:
        try:
            err = r.json()
        except Exception:
            err = {"message": r.text or r.reason}
        raise WordPressPublishError(f"WordPress media upload error {r.status_code}: {err}")
    media = r.json()
    att_id = media.get("id")
    if not att_id:
        raise WordPressPublishError("WordPress media upload returned no attachment id")
    if caption or alt_text:
        patch_url = f"{site_url}/wp-json/wp/v2/media/{att_id}"
        patch_body: dict[str, Any] = {}
        if caption:
            patch_body["caption"] = {"raw": caption}
        if alt_text:
            patch_body["alt_text"] = alt_text
        if patch_body:
            requests.patch(
                patch_url,
                headers={**_auth_headers(username, app_password), "Content-Type": "application/json"},
                json=patch_body,
                timeout=15,
            )
    return int(att_id)


def post_article(
    title: str,
    content: str,
    *,
    status: str = "draft",
    slug: str | None = None,
    author: int | None = None,
    categories: list[int] | None = None,
    tags: list[int] | None = None,
    append_disclaimer: bool = False,
    disclaimer_text: str | None = None,
    featured_image: dict[str, Any] | None = None,
    featured_image_url: str | None = None,
    featured_image_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    Post a Pearl News article to WordPress via REST API.

    :param title: Post title.
    :param content: Post body (HTML or plain text).
    :param status: 'draft' or 'publish'. Default 'draft' for editorial review.
    :param slug: Optional URL slug; WP will derive from title if omitted.
    :param author: Optional WordPress user ID for post author (byline); alternates when set per article.
    :param categories: List of WordPress category IDs.
    :param tags: List of WordPress tag IDs.
    :param append_disclaimer: If True, append disclaimer to content (default False; disclaimer is on site About).
    :param disclaimer_text: Override disclaimer when append_disclaimer is True.
    :param featured_image: Optional dict with url, credit, source_url (and optional caption). Uploaded to Media and set as post thumbnail.
    :param featured_image_url: Optional image URL (no attribution). If featured_image not set, upload from this URL.
    :param featured_image_path: Optional path to local image file (e.g. pearl_news/del_intake_pics/...). Upload from file when no URL.
    :return: WordPress API response (post object or error payload).
    :raises WordPressPublishError: On missing credentials, missing requests, or API error.
    """
    if requests is None:
        raise WordPressPublishError("Install requests: pip install requests")

    site_url, username, app_password = _get_credentials()
    url = f"{site_url}/wp-json/wp/v2/posts"

    body = content
    if append_disclaimer:
        disc = disclaimer_text or (
            "Pearl News is an independent nonprofit civic media organization. "
            "We are not affiliated with, endorsed by, or officially connected to the United Nations unless explicitly stated in formal public documentation."
        )
        body = f"{content.rstrip()}\n\n<p><em>{disc}</em></p>"

    payload: dict[str, Any] = {
        "title": title,
        "content": body,
        "status": status,
        "slug": slug or None,
        "categories": categories or [],
        "tags": tags or [],
    }
    if author is not None:
        payload["author"] = int(author)
    # Omit null slug so WP generates from title
    if payload["slug"] is None:
        del payload["slug"]

    # Featured image: upload from URL, or from local file path, then set featured_media
    image_url = None
    caption = None
    alt_text = None
    if featured_image and featured_image.get("url"):
        image_url = featured_image["url"]
        credit = featured_image.get("credit") or "Source"
        source_url = featured_image.get("source_url") or ""
        caption = featured_image.get("caption") or f"Credit: {credit}"
        if source_url:
            caption = f"{caption} (Source: {source_url})"
        alt_text = f"Image for: {title}"
    elif featured_image_url:
        image_url = featured_image_url

    if image_url:
        att_id = _upload_media_from_url(
            site_url, username, app_password, image_url,
            caption=caption, alt_text=alt_text,
        )
        payload["featured_media"] = att_id
    elif featured_image_path:
        path = Path(featured_image_path)
        if path.exists():
            att_id = _upload_media_from_file(
                site_url, username, app_password, path,
                alt_text=f"Image for: {title}",
            )
            payload["featured_media"] = att_id

    headers = _auth_headers(username, app_password)
    response = requests.post(url, headers=headers, json=payload, timeout=30)

    if not response.ok:
        try:
            err = response.json()
            # Common WP REST errors: code + message are most helpful
            code = err.get("code", "")
            msg = err.get("message", err.get("data", {}).get("message", str(err)))
            detail = f"WordPress API error {response.status_code}: {code or response.reason} — {msg}"
        except Exception:
            err = {"message": response.text or response.reason}
            detail = f"WordPress API error {response.status_code}: {response.text or response.reason}"
        raise WordPressPublishError(detail)
    return response.json()
