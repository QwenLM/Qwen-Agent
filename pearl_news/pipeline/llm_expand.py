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


# Template ID → prompt filename mapping
_TEMPLATE_PROMPT_MAP = {
    "hard_news_spiritual_response": "expansion_hard_news.txt",
    "youth_feature": "expansion_youth_feature.txt",
    "commentary": "expansion_commentary.txt",
    "explainer_context": "expansion_explainer.txt",
    "interfaith_dialogue_report": "expansion_interfaith.txt",
}


def _diagnose_short_sections(html_content: str) -> str:
    """Identify which sections are below minimum word count for targeted retry feedback."""
    import re as _re
    text = _re.sub(r"<[^>]+>", " ", html_content)
    text = _re.sub(r"\s+", " ", text).strip()
    total_wc = len(text.split())

    lower = html_content.lower()
    diagnostics = []

    # Teacher section
    teacher_markers = ["teaches that", "tradition", "reflects that", "observes that"]
    teacher_start = -1
    for marker in teacher_markers:
        idx = lower.find(marker)
        if idx != -1:
            teacher_start = max(0, idx - 300)
            break
    if teacher_start >= 0:
        teacher_text = _re.sub(r"<[^>]+>", " ", html_content[teacher_start:teacher_start + 2500])
        teacher_wc = len(teacher_text.split())
        if teacher_wc < 90:
            diagnostics.append(f"TEACHER section ~{teacher_wc}w (need ≥90)")

    # Youth section
    youth_start = lower.find("youth")
    if youth_start == -1:
        youth_start = lower.find("young")
    if youth_start >= 0:
        youth_text = _re.sub(r"<[^>]+>", " ", html_content[youth_start:youth_start + 2000])
        youth_wc = len(youth_text.split())
        if youth_wc < 100:
            diagnostics.append(f"YOUTH section ~{youth_wc}w (need ≥100)")

    # SDG section
    sdg_match = _re.search(r"sdg\s*\d+", lower)
    if sdg_match:
        sdg_text = _re.sub(r"<[^>]+>", " ", html_content[max(0, sdg_match.start() - 100):sdg_match.end() + 1000])
        sdg_wc = len(sdg_text.split())
        if sdg_wc < 60:
            diagnostics.append(f"SDG section ~{sdg_wc}w (need ≥60)")

    if diagnostics:
        return "SHORT SECTIONS: " + "; ".join(diagnostics)
    return f"Total only {total_wc}w — expand all sections with more specifics."


def _load_system_prompt(prompts_root: Path, template_id: str = "") -> str:
    """Load template-specific expansion prompt, falling back to generic."""
    # Try template-specific prompt first
    if template_id and template_id in _TEMPLATE_PROMPT_MAP:
        specific = prompts_root / _TEMPLATE_PROMPT_MAP[template_id]
        if specific.exists():
            logger.info("Loaded template-specific prompt: %s", specific.name)
            return specific.read_text(encoding="utf-8").strip()

    # Fallback to generic
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
    teacher: dict[str, Any] | None = None,
    teachers: list[dict[str, Any]] | None = None,
    language: str = "en",
    template_id: str = "hard_news_spiritual_response",
) -> str | None:
    """
    Call OpenAI-compatible API to expand article HTML toward target_word_count.
    For interfaith articles, pass teachers (plural) instead of teacher (singular).
    Returns expanded content or None on failure (caller keeps original).
    """
    base_url = (config.get("base_url") or "").strip()
    model = config.get("model") or "qwen3-14b"
    api_key = (config.get("api_key") or "lm-studio").strip()
    timeout = float(config.get("timeout") or 120)
    max_tokens = int(config.get("max_tokens") or 2048)
    temperature = float(config.get("temperature") or 0.5)
    disable_thinking = config.get("disable_thinking", True)

    if not base_url:
        logger.warning("LLM expansion: base_url not set; skipping")
        return None

    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("LLM expansion: openai package not installed; pip install openai")
        return None

    root = Path(__file__).resolve().parent.parent
    system_prompt = _load_system_prompt(root / "prompts", template_id=template_id)

    # Build teacher knowledge base block
    teacher_block = ""
    is_interfaith = template_id == "interfaith_dialogue_report"

    if is_interfaith and teachers:
        # Multi-teacher for interfaith articles
        try:
            from pearl_news.pipeline.teacher_resolver import format_multiple_teachers_for_prompt
            teacher_block = format_multiple_teachers_for_prompt(teachers)
        except ImportError:
            pass
    elif teacher and teacher.get("atoms"):
        # Single teacher for all other types
        try:
            from pearl_news.pipeline.teacher_resolver import format_teacher_atoms_for_prompt
            teacher_block = format_teacher_atoms_for_prompt(teacher)
        except ImportError:
            pass

    # Language → audience context
    language_labels = {"en": "English", "ja": "Japanese", "zh-cn": "Simplified Chinese"}
    lang_label = language_labels.get(language, "English")

    # Template label for user prompt
    template_labels = {
        "hard_news_spiritual_response": "HARD NEWS + SPIRITUAL RESPONSE",
        "youth_feature": "YOUTH FEATURE",
        "commentary": "COMMENTARY",
        "explainer_context": "EXPLAINER / CONTEXT",
        "interfaith_dialogue_report": "INTERFAITH DIALOGUE REPORT",
    }
    template_label = template_labels.get(template_id, "NEWS ARTICLE")

    # Framing question (editorial north star for the LLM)
    if is_interfaith and teachers:
        teacher_names = [t.get("display_name", "?") for t in teachers]
        framing = (
            f"FRAMING QUESTION (use as editorial north star, do not quote directly):\n"
            f"What does \"{title}\" mean for Gen Z and Gen Alpha in {lang_label}-speaking regions — "
            f"and where do {', '.join(teacher_names)} converge on what their traditions offer youth in response?\n"
        )
    else:
        teacher_name = teacher.get("display_name", "the teacher") if teacher else "the teacher"
        framing = (
            f"FRAMING QUESTION (use as editorial north star, do not quote directly):\n"
            f"What does \"{title}\" mean for Gen Z and Gen Alpha in {lang_label}-speaking regions — "
            f"and what does {teacher_name}'s tradition offer them in response?\n"
        )

    # Load SDG target data so the model doesn't have to guess target numbers
    sdg_target_block = ""
    try:
        sdg_targets_path = root / "config" / "sdg_targets.yaml"
        if sdg_targets_path.exists() and yaml:
            with open(sdg_targets_path, "r", encoding="utf-8") as f:
                sdg_data = yaml.safe_load(f) or {}
            topic_targets = (sdg_data.get("topic_sdg_targets") or {}).get(topic)
            if topic_targets:
                sdg_target_block = (
                    f"\nSDG TARGET REFERENCE (use this — do NOT guess target numbers):\n"
                    f"- SDG {topic_targets['sdg_number']}: {topic_targets['sdg_title']}\n"
                    f"- Primary Target: {topic_targets['primary_target']} — {topic_targets['target_description']}\n"
                    f"- Metric: {topic_targets.get('metric_example', '')}\n"
                    f"- Secondary Targets: {', '.join(topic_targets.get('secondary_targets', []))}"
                )
    except Exception:
        pass  # Non-critical — model falls back to its own knowledge

    # Assemble user prompt
    parts = [
        f"Expand and improve the following Pearl News draft article into a publication-ready "
        f"{target_word_count}-word {template_label} piece.",
        f"\nARTICLE METADATA:\n- Title: {title}\n- Topic: {topic}\n- SDG: {primary_sdg}"
        f"\n- Language: {lang_label}\n- Template: {template_label} (NOT a teacher profile)",
    ]
    if sdg_target_block:
        parts.append(sdg_target_block)
    if teacher_block:
        kb_label = "MULTI-TEACHER KNOWLEDGE BASE" if is_interfaith else "TEACHER KNOWLEDGE BASE"
        parts.append(f"\n{kb_label}:\n{teacher_block}")
    parts.append(f"\n{framing}")

    # Template-specific rules in user message
    if is_interfaith:
        parts.append(
            "\nRULES:\n"
            "- The UN RSS item is the news event that triggers this dialogue report.\n"
            "- Show where the teachers CONVERGE — not debate. Agreement, not conflict.\n"
            "- Each teacher must be named with their tradition.\n"
            "- Use at least 1 atom from each teacher in themes of agreement.\n"
            "- Output only the final HTML body. No preamble."
        )
    elif template_id == "commentary":
        parts.append(
            "\nRULES:\n"
            "- The UN RSS item triggers the commentary. The thesis interprets the event.\n"
            "- The word 'Commentary' must appear above the headline.\n"
            "- The teacher's tradition supports the ARGUMENT — not generic wisdom.\n"
            "- Output only the final HTML body. No preamble."
        )
    elif template_id == "youth_feature":
        parts.append(
            "\nRULES:\n"
            "- The UN RSS item is the trigger, but the youth narrative drives the story.\n"
            "- The teacher REFRAMES what the data reveals — does not instruct.\n"
            "- Open on a specific young person, cohort, or place — not 'young people globally.'\n"
            "- Output only the final HTML body. No preamble."
        )
    elif template_id == "explainer_context":
        parts.append(
            "\nRULES:\n"
            "- The UN RSS item is the trigger. Explain what happened, then build context.\n"
            "- The teacher asks a QUESTION — does not provide the answer.\n"
            "- Historical background must name at least 2 prior moments.\n"
            "- Output only the final HTML body. No preamble."
        )
    else:
        parts.append(
            "\nRULES:\n"
            "- The UN RSS item is the news event that triggers this article. "
            "The teacher does NOT drive the story — they respond to it.\n"
            "- Do not write a teacher profile. Write a news story that uses one teacher's "
            "wisdom as a lens on the news event.\n"
            "- Output only the final HTML body. No preamble."
        )

    parts.append(f"\nDRAFT TO EXPAND:\n{content}")
    user_prompt = "\n".join(parts)

    # Use httpx Timeout so connect/read/write all honour the full timeout value,
    # not just the default 5-second httpx socket timeout that was causing
    # "Client disconnected" at ~4 min even though timeout=360 was set.
    try:
        from httpx import Timeout as HttpxTimeout
        http_timeout = HttpxTimeout(timeout)
    except ImportError:
        http_timeout = timeout  # fallback: scalar still better than nothing

    client = OpenAI(base_url=base_url, api_key=api_key, timeout=http_timeout)

    # Build extra_body: disable Qwen3 thinking mode if configured
    extra_body = {}
    if disable_thinking:
        extra_body["enable_thinking"] = False

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        **({"extra_body": extra_body} if extra_body else {}),
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
    min_words = int(config.get("min_word_count") or 600)
    max_retries = int(config.get("expansion_retries") or 1)

    for item in items:
        content = item.get("content") or ""
        if not content:
            continue
        title = item.get("article_title") or item.get("title") or ""
        topic = item.get("topic") or "partnerships"
        primary_sdg = item.get("primary_sdg") or "17"
        teacher = item.get("_teacher_resolved") or {}
        teachers = item.get("_teachers_resolved") or []
        language = item.get("language") or "en"
        template_id = item.get("template_id") or "hard_news_spiritual_response"
        retries = 0
        current_content = content

        for attempt in range(1 + max_retries):
            try:
                expanded = expand_article_with_llm(
                    content=current_content,
                    title=title,
                    topic=topic,
                    primary_sdg=primary_sdg,
                    target_word_count=target,
                    config=config,
                    teacher=teacher,
                    teachers=teachers if teachers else None,
                    language=language,
                    template_id=template_id,
                )
                if expanded:
                    # Post-process: re-attach source line if LLM stripped it.
                    import re as _re
                    _source_pattern = r'<p[^>]*>\s*<em>\s*[Ss]ource\s*:.*?</em>\s*</p>'
                    original_source_match = _re.search(_source_pattern, content, _re.IGNORECASE | _re.DOTALL)
                    expanded_has_source = bool(_re.search(r'[Ss]ource\s*:', expanded))
                    if original_source_match and not expanded_has_source:
                        source_line = original_source_match.group(0).strip()
                        expanded = expanded.rstrip() + "\n" + source_line
                        logger.info(
                            "Re-attached source line to article %s (LLM had stripped it)",
                            item.get("id"),
                        )

                    # Check word count — retry if too short
                    text_only = _re.sub(r"<[^>]+>", " ", expanded)
                    wc = len(text_only.split())

                    if wc < min_words and attempt < max_retries:
                        retries += 1
                        # Diagnose which sections are short for targeted retry
                        section_feedback = _diagnose_short_sections(expanded)
                        logger.warning(
                            "Article %s expanded to only %d words (min %d); retrying (attempt %d/%d). %s",
                            item.get("id"), wc, min_words, attempt + 1, max_retries, section_feedback,
                        )
                        # Feed the short expansion back with specific guidance on what's thin
                        current_content = (
                            f"<!-- RETRY: This draft is only {wc} words (need {min_words}+). "
                            f"{section_feedback} "
                            f"Expand the SHORT sections with specifics — do not pad with filler. -->\n"
                            + expanded
                        )
                        continue

                    item["content"] = expanded
                    item["_expansion_retries"] = retries
                    logger.info("Expanded article %s to ~%d words (retries: %d)", item.get("id"), wc, retries)
                    break
                else:
                    logger.debug("Expansion returned empty for %s; keeping original", item.get("id"))
                    item["_expansion_retries"] = retries
                    break
            except Exception as e:
                logger.warning("Expansion failed for %s: %s; keeping original", item.get("id"), e)
                item["_expansion_failed"] = True
                item["_expansion_retries"] = retries
                break

    return items
