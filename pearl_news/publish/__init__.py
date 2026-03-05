# Pearl News — publish to WordPress (REST API). Credentials via env vars only.

from pearl_news.publish.wordpress_client import post_article, WordPressPublishError

__all__ = ["post_article", "WordPressPublishError"]
