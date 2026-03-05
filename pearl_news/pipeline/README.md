# Pearl News pipeline

- **feed_ingest.py** — **Implemented.** Loads `feeds.yaml`, fetches RSS/Atom with `feedparser`, normalizes to schema (id, title, url, pub_date, summary, source_feed_id, source_feed_title). Requires `feedparser` (see repo `requirements.txt`).
- **run_article_pipeline.py** — Entry point. Full chain: ingest → classify → select → assemble → quality gates → QC. Writes `article_<id>.json`, `ingest_manifest.json`, `build_manifests.json` to `--out-dir`. Default: only QC-passed; use `--no-filter-qc` to output all.
- **topic_sdg_classifier.py** — **Implemented.** Maps item → topic, primary_sdg, sdg_labels, un_body via `sdg_news_topic_mapping.yaml` (keyword match).
- **template_selector.py** — **Implemented.** Picks 1 of 5 templates by topic/source from `article_templates_index.yaml`. Interfaith/group template (`interfaith_dialogue_report`) is assigned only ~5% of the time; rest use single-teacher-focused templates.
- **article_assembler.py** — **Implemented.** Fills template slots from feed item + atoms (or placeholders): news_event, youth_impact, teacher_perspective, sdg_ref; source at end; no per-article disclaimer (on site About). USLF balance: ~95% of articles use single-teacher voice (one teacher’s insight + youth relevance), ~5% use group/forum voice (see `template_diversity.yaml` → `uslf_group_article_ratio`).
- **quality_gates.py** — **Implemented.** Fail-hard: fact_check_completeness, youth_impact_specificity, sdg_un_accuracy, promotional_tone_detector, un_endorsement_detector (blocklist with negated-disclaimer allowance).
- **qc_checklist.py** — **Implemented.** Runs quality gates; filters to passed-only by default.

**Run full pipeline:**
```bash
python -m pearl_news.pipeline.run_article_pipeline --feeds pearl_news/config/feeds.yaml --out-dir artifacts/pearl_news/drafts --limit 10
```

**Output:**
- `--out-dir/article_<id>.json` — final article (title, content, author, featured_image/featured_image_url, article_type, topic, primary_sdg, qc_results)
- `--out-dir/ingest_manifest.json` — build_date, item_count, articles_output, items summary
- `--out-dir/build_manifests.json` — per-article audit (feed_item, template_id, qc_results, signatures)

**GO/NO-GO:** docs/PEARL_NEWS_GO_NO_GO_CHECKLIST.md

Optional: LLM step (local Qwen3 or API) for summarization or section expansion — see docs/PEARL_NEWS_ARCHITECTURE_SPEC.md §5.
