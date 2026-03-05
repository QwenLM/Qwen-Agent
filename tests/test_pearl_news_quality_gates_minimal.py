"""Minimal tests for Pearl News quality gates (fail-hard, blocklist, qc_results)."""
from __future__ import annotations

import pytest

from pearl_news.pipeline.quality_gates import run_quality_gates


def test_run_quality_gates_adds_qc_results():
    """run_quality_gates adds qc_results and qc_passed to each item."""
    items = [
        {"id": "a", "title": "Test", "content": "Content with youth and SDG.", "url": "https://un.org/news/1"},
    ]
    result = run_quality_gates(items)
    assert len(result) == 1
    assert "qc_results" in result[0]
    assert "qc_passed" in result[0]
    assert result[0]["qc_results"]["fact_check_completeness"] in ("PASS", "FAIL")
    assert result[0]["qc_results"]["un_endorsement_detector"] in ("PASS", "FAIL")


def test_blocklist_fails_gate():
    """Blocklist phrase in content causes sdg_un_accuracy and un_endorsement_detector FAIL."""
    items = [
        {"id": "b", "title": "UN partner story", "content": "We are UN partner in this.", "url": "https://example.com/1"},
    ]
    result = run_quality_gates(items)
    assert result[0]["qc_results"]["sdg_un_accuracy"] == "FAIL"
    assert result[0]["qc_results"]["un_endorsement_detector"] == "FAIL"
    assert result[0]["qc_passed"] is False


def test_clean_content_passes():
    """Clean content with source and youth mention can pass all gates."""
    items = [
        {
            "id": "c",
            "title": "Climate and youth",
            "content": "Young people are affected. Source: https://news.un.org/feed.",
            "url": "https://news.un.org/item",
        },
    ]
    result = run_quality_gates(items)
    assert result[0]["qc_passed"] is True
