"""E2E test: Pearl News pipeline classify → select → assemble → quality gates → QC."""
from __future__ import annotations

from pathlib import Path

import pytest

from pearl_news.pipeline.topic_sdg_classifier import classify_sdgs
from pearl_news.pipeline.template_selector import select_templates
from pearl_news.pipeline.article_assembler import assemble_articles
from pearl_news.pipeline.quality_gates import run_quality_gates
from pearl_news.pipeline.qc_checklist import run_qc_checklist


def _make_fake_items(count: int = 3) -> list[dict]:
    """Create fake normalized feed items (as from ingest)."""
    items = []
    for i in range(count):
        items.append({
            "id": f"test_{i}",
            "title": "Climate carbon emissions" if i == 0 else f"Test article {i}",
            "url": f"https://example.com/source/{i}",
            "pub_date": "2026-03-03T12:00:00+00:00",
            "summary": "Summary text with source. UN report.",
            "source_feed_id": "test_feed",
            "source_feed_title": "Test",
            "raw_title": "Title",
            "raw_summary": "Summary",
            "images": [],
        })
    return items


class TestPipelineE2E:
    def test_classify_select_assemble_flow(self):
        """Full pipeline on fake items produces articles with required fields."""
        items = _make_fake_items(3)
        items = classify_sdgs(items)
        items = select_templates(items)
        articles = assemble_articles(items)
        assert len(articles) == 3

        art = articles[0]
        assert art.get("article_title") or art.get("title")
        assert "content" in art
        assert "template_id" in art
        assert "topic" in art
        assert "primary_sdg" in art
        assert "un_body" in art
        assert "pub_date" in art
        assert "headline_sig" in art
        assert "lede_sig" in art

    def test_quality_gates_add_qc_results(self):
        """Quality gates add qc_results and qc_passed to articles."""
        items = _make_fake_items(1)
        items = classify_sdgs(items)
        items = select_templates(items)
        articles = assemble_articles(items)
        articles = run_quality_gates(articles)
        assert "qc_results" in articles[0]
        assert "qc_passed" in articles[0]
        assert "fact_check_completeness" in articles[0]["qc_results"]
        assert "un_endorsement_detector" in articles[0]["qc_results"]

    def test_qc_checklist_filters_to_passed(self):
        """QC checklist with filter_to_passed returns only passed items."""
        items = _make_fake_items(2)
        items = classify_sdgs(items)
        items = select_templates(items)
        articles = assemble_articles(items)
        articles = run_quality_gates(articles)
        passed = run_qc_checklist(articles, filter_to_passed=True)
        all_items = run_qc_checklist(articles, filter_to_passed=False)
        assert len(all_items) == 2
        assert len(passed) <= 2
