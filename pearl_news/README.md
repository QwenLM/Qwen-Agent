# Pearl News

Editorial article pipeline for **Pearl News** (civic media: world news + spiritual leaders’ perspectives + youth + UN SDGs).

**Mode:** `pearl_news` — separate from v4 (book pipeline) and Pearl Prime (template books). Produces **articles**, not books.

**Authority:** [docs/PEARL_NEWS_ARCHITECTURE_SPEC.md](../docs/PEARL_NEWS_ARCHITECTURE_SPEC.md)  
**Writer spec:** [docs/PEARL_NEWS_WRITER_SPEC.md](../docs/PEARL_NEWS_WRITER_SPEC.md) — voice, atom types, 4-layer blend, quality gates.  
**Production:** [docs/PEARL_NEWS_PRODUCTION_NONNEGOTIABLES.md](../docs/PEARL_NEWS_PRODUCTION_NONNEGOTIABLES.md) — all 10 items required for production-grade.

## Structure

- **config/** — Article template index, SDG/news topic mapping, teacher expertise, feed URLs; **legal_boundary**, **editorial_firewall**, **template_diversity**, **quality_gates**, **llm_safety** (production non-negotiables §1–4, §7).
- **article_templates/** — Five locked templates (Hard News+Response, Youth Feature, Interfaith Report, Explainer, Commentary).
- **atoms/** — Reusable article building blocks: news summaries, youth impact, teacher quotes/practices, SDG/UN refs.
- **pipeline/** — Ingest → classify → template select → assemble → quality gates + QC (fail-hard); build manifests for audit (§6).
- **publish/** — WordPress REST API client; post articles to the blog (BlogSite). Credentials via env vars only. See [publish/README.md](publish/README.md).
- **governance/** — Canonical source for published governance page, editorial standards, corrections policy, conflict-of-interest policy (§9).
- **prompts/** — Prompts for LLM expansion (see **config/llm_expansion.yaml** and `--expand` below; §7).

## Quick start

```bash
# Ingest feeds and run full pipeline (draft articles to artifacts)
python -m pearl_news.pipeline.run_article_pipeline --feeds config/feeds.yaml --out-dir artifacts/pearl_news/drafts

# With LLM expansion to ~1000 words (Qwen / OpenAI-compatible API; set base_url in config/llm_expansion.yaml)
python -m pearl_news.pipeline.run_article_pipeline --feeds config/feeds.yaml --out-dir artifacts/pearl_news/drafts --expand
```

### One-command run (recommended)

```bash
scripts/pearl_news_do_it.sh
```

Run tests + pipeline + post first draft to WordPress (`draft`):

```bash
scripts/pearl_news_do_it.sh --post
```

## Publish to WordPress

To push stories to the Pearl News WordPress site (BlogSite theme), set env vars and use the posting script:

```bash
export WORDPRESS_SITE_URL="https://pearlnewsuna.org"
export WORDPRESS_USERNAME="Pearl_Prime"   # or your WP username
export WORDPRESS_APP_PASSWORD="xxxx xxxx xxxx xxxx xxxx xxxx"  # from WP Profile → Application Passwords

python scripts/pearl_news_post_to_wp.py --article artifacts/pearl_news/drafts/article.json --status draft
```

See **[pearl_news/publish/README.md](publish/README.md)** for credentials, article JSON format, and scheduling. Do not commit the app password.

`WORDPRESS_SITE_URL` accepts:
- `https://pearlnewsuna.org` (recommended)
- `pearlnewsuna.org` (auto-normalized to `https://...`)
- `https://pearlnewsuna.org/wp-admin` (auto-normalized to site root)

## Reuse vs v4 / Pearl Prime

- **Shared:** SDG/topic mapping, persona (youth) labels, teacher/forum metadata — config and data only.
- **Not shared:** Book atoms (`atoms/<persona>/<topic>/`), book formats (F001–F015), run_pipeline stages. Pearl News uses its own article atoms and templates.
