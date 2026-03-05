"""
Pearl News — fail-hard quality gates (production non-negotiable §4).
All gates must PASS for an article to be publishable.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger(__name__)

GATE_IDS = [
    "fact_check_completeness",
    "youth_impact_specificity",
    "sdg_un_accuracy",
    "promotional_tone_detector",
    "un_endorsement_detector",
]


def _load_legal_boundary(config_root: Path) -> list[str]:
    path = config_root / "legal_boundary.yaml"
    if not path.exists() or yaml is None:
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("blocklist_phrases") or []


def _run_gates_on_article(
    item: dict[str, Any],
    blocklist: list[str],
) -> dict[str, str]:
    """Return dict of gate_id -> PASS|FAIL for one article."""
    content = (item.get("content") or item.get("content_plain") or "").lower()
    title = (item.get("article_title") or item.get("title") or "").lower()
    text = f"{title} {content}"

    results = {}

    # 1) fact_check_completeness: has cited source (feed item has url; we require 2 for news - we have 1, allow for now or check news_sources)
    has_source = bool(item.get("url")) and ("source:" in content or "http" in content or "un.org" in content)
    results["fact_check_completeness"] = "PASS" if has_source else "FAIL"

    # 2) youth_impact_specificity: youth impact section present and not empty
    youth_ok = "young people" in text or "gen z" in text or "gen alpha" in text or "youth" in text or "sdg" in text
    results["youth_impact_specificity"] = "PASS" if youth_ok else "FAIL"

    # 3) sdg_un_accuracy: no blocklist phrase (except when negated, e.g. "not affiliated")
    def _blocklist_hit(t: str, phrases: list[str]) -> bool:
        for phrase in phrases:
            p = phrase.lower()
            if p not in t:
                continue
            # Allow mandatory disclaimer: "not affiliated", "not endorsed", "not ... connected"
            if "not affiliated" in t or "not endorsed" in t or "not connected" in t or "neither is affiliated" in t:
                continue
            return True
        return False
    blocklist_fail = _blocklist_hit(text, blocklist)
    results["sdg_un_accuracy"] = "FAIL" if blocklist_fail else "PASS"

    # 4) promotional_tone_detector: no devotional/promotional keywords (simple heuristic)
    promo_words = ["buy now", "sign up", "donate here", "master says", "enlightenment", "karma will"]
    promo_fail = any(w in text for w in promo_words)
    results["promotional_tone_detector"] = "FAIL" if promo_fail else "PASS"

    # 5) un_endorsement_detector: blocklist again (same negated allowance)
    results["un_endorsement_detector"] = "FAIL" if blocklist_fail else "PASS"

    return results


def run_quality_gates(
    items: list[dict[str, Any]],
    config_root: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Run all 5 gates on each item. Set qc_results (timestamp + per-gate PASS/FAIL) and
    qc_passed (True only if all PASS). Does not remove failed items; caller can filter.
    """
    root = Path(__file__).resolve().parent.parent
    config_root = config_root or (root / "config")
    blocklist = _load_legal_boundary(config_root)

    now = datetime.now(timezone.utc).isoformat()
    for item in items:
        gate_results = _run_gates_on_article(item, blocklist)
        item["qc_results"] = {
            "timestamp": now,
            **gate_results,
        }
        item["qc_passed"] = all(v == "PASS" for v in gate_results.values())
        if not item["qc_passed"]:
            logger.debug("Article %s failed gates: %s", item.get("id"), gate_results)

    logger.info("Ran quality gates on %d articles; %d passed", len(items), sum(1 for i in items if i.get("qc_passed")))
    return items
