"""
Pearl News — run quality gates and optionally filter to passed-only.
Final validation before output; attach checklist summary for audit.
"""
from __future__ import annotations

import logging
from typing import Any

from pearl_news.pipeline.quality_gates import run_quality_gates

logger = logging.getLogger(__name__)


def run_qc_checklist(
    items: list[dict[str, Any]],
    filter_to_passed: bool = True,
    config_root: Any = None,
) -> list[dict[str, Any]]:
    """
    Run quality gates on each item, then optionally keep only qc_passed=True.
    Returns list of items (all if filter_to_passed=False, else only passed).
    """
    items = run_quality_gates(items, config_root=config_root)
    if filter_to_passed:
        passed = [i for i in items if i.get("qc_passed")]
        logger.info("QC checklist: %d passed, %d failed (filtered)", len(passed), len(items) - len(passed))
        return passed
    return items
