"""
Pearl News — expand article content toward target word count using an LLM (Qwen / OpenAI-compatible API).
Allowed under llm_safety.yaml (expansion without full-article evaluation).
Environment override: QWEN_BASE_URL, QWEN_API_KEY, QWEN_MODEL (e.g. from GitHub Actions secrets on self-hosted runner).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger(__name__)


def _load_config(config_root: Path) -> dict[str, Any]:
    path = config_root / "llm_expansion.yaml"
    data: dict[str, Any] = {}
    if path.exists() and yaml:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    # Env override (e.g. GitHub Secrets on self-hosted runner with LM Studio)
    if os.environ.get("QWEN_BASE_URL"):
        data["base_url"] = os.environ.get("QWEN_BASE_URL", "").strip()
    if os.environ.get("QWEN_API_KEY") is not None:
        data["api_key"] = (os.environ.get("QWEN_API_KEY") or "").strip()
    if os.environ.get("QWEN_MODEL"):
        data["model"] = os.environ.get("QWEN_MODEL", "").strip()
    if os.environ.get("QWEN_BASE_URL") and data.get("enabled") is not True:
        data["enabled"] = True  # Enable expansion when QWEN_BASE_URL is set
    return data


def _load_system_prompt(prompts_root: Path) -> str:
    path = prompts_root / "expansion_system.txt"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return (
        "You are an editor for Pearl News. Expand the draft article to the target word count. "
        "Keep the same HTML structure and facts. Add detail by elaborating; do not invent. "
        "Output only the expanded HTML body, no preamble."
    )


def expand_article_with_llm(
    content: str,
    title: str,
    topic: str,
    primary_sdg: str,
    target_word_count: int,
    config: dict[str, Any],
) -> str | None:
    """
    Call OpenAI-compatible API to expand article HTML toward target_word_count.
    Returns expanded content or None on failure (caller keeps original).
    """
    base_url = (config.get("base_url") or "").strip()
    model = config.get("model") or "Qwen2.5-14B-Instruct"
    api_key = (config.get("api_key") or "lm-studio").strip()
    timeout = float(config.get("timeout") or 120)
    max_tokens = int(config.get("max_tokens") or 2048)
    temperature = float(config.get("temperature") or 0.5)

    if not base_url:
        logger.warning("LLM expansion: base_url not set; skipping")
        return None

    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("LLM expansion: openai package not installed; pip install openai")
        return None

    root = Path(__file__).resolve().parent.parent
    system_prompt = _load_system_prompt(root / "prompts")
    user_prompt = (
        f"Expand this article to approximately {target_word_count} words. "
        f"Title: {title}. Topic: {topic}. SDG: {primary_sdg}. "
        f"Keep the same structure and the Source line at the end.\n\n{content}"
    )

    client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    choice = resp.choices[0] if resp.choices else None
    if not choice or not getattr(choice, "message", None):
        return None
    raw = (choice.message.content or "").strip()
    # Drop markdown code fence if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)
    return raw if raw else None


def run_expansion(
    items: list[dict[str, Any]],
    config_root: Path | None = None,
) -> list[dict[str, Any]]:
    """
    For each item, if LLM expansion is enabled and config present, expand content toward target_word_count.
    Updates item["content"] and item["article_title"] if expansion succeeds. On failure, leaves content unchanged.
    """
    root = Path(__file__).resolve().parent.parent
    config_root = config_root or (root / "config")
    config = _load_config(config_root)
    if not config.get("enabled", False):
        logger.info("LLM expansion disabled or config missing; skipping")
        return items

    target = int(config.get("target_word_count") or 1000)
    for item in items:
        content = item.get("content") or ""
        if not content:
            continue
        title = item.get("article_title") or item.get("title") or ""
        topic = item.get("topic") or "partnerships"
        primary_sdg = item.get("primary_sdg") or "17"
        try:
            expanded = expand_article_with_llm(
                content=content,
                title=title,
                topic=topic,
                primary_sdg=primary_sdg,
                target_word_count=target,
                config=config,
            )
            if expanded:
                item["content"] = expanded
                wc = len(expanded.split())
                logger.info("Expanded article %s to ~%d words", item.get("id"), wc)
            else:
                logger.debug("Expansion returned empty for %s; keeping original", item.get("id"))
        except Exception as e:
            logger.warning("Expansion failed for %s: %s; keeping original", item.get("id"), e)

    return items
