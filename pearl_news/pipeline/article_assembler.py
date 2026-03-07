"""
Pearl News — assemble full article from template + feed item + atoms (teacher, youth, SDG).
Fills section slots; uses placeholders when atom files are missing so pipeline always produces output.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger(__name__)


def _load_template(template_dir: Path, template_file: str) -> dict[str, Any]:
    path = template_dir / template_file
    if not path.exists() or yaml is None:
        return {"section_slots": []}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _is_uslf_group_article(item: dict[str, Any], config_root: Path) -> bool:
    """True if this article should use group/USLF voice (~5%); else single-teacher focus. Deterministic from item id."""
    ratio = 0.05
    if config_root.exists():
        path = config_root / "template_diversity.yaml"
        if path.exists() and yaml:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            ratio = float(data.get("uslf_group_article_ratio", 0.05))
    item_id = (item.get("id") or item.get("title") or "").encode("utf-8")
    h = int(hashlib.sha256(item_id).hexdigest(), 16) % 100
    return (h / 100.0) < ratio


def _resolve_slot(
    slot_name: str,
    source: str,
    item: dict[str, Any],
    atoms_root: Path,
    topic: str,
    primary_sdg: str,
    sdg_labels: dict,
    un_body: str,
    config_root: Path | None = None,
) -> str:
    """Return content for one slot based on source type."""
    if source == "news_event":
        # Summary only; title appears once as H1; source is appended at end of article
        summary = item.get("summary") or item.get("raw_summary") or ""
        return f"<p>{summary}</p>"

    if source == "youth_impact":
        # Try atoms/youth_impact/<topic>.md or .txt
        for ext in (".md", ".txt", ".yaml"):
            p = atoms_root / "youth_impact" / f"{topic}{ext}"
            if p.exists():
                return p.read_text(encoding="utf-8").strip()
        label = sdg_labels.get(primary_sdg, "sustainable development")
        return (
            f"<p>Young people are increasingly affected by global events in this area. Gen Z and Gen Alpha seek clarity and constructive responses aligned with sustainable development and well-being (SDG {primary_sdg}: {label}).</p>\n\n"
            f"<p>Research and reporting show that youth engagement—whether through education, advocacy, or community action—helps shape outcomes. Framing stories through a youth lens supports relevance and accountability.</p>\n\n"
            f"<p>Pearl News highlights how global challenges intersect with the lives of young people and the frameworks that support their resilience and participation.</p>"
        )

    if source == "teacher_quotes_practices":
        # Teacher section: produce a clean HTML placeholder.
        # The actual teacher content comes from _teacher_resolved (set after assembly)
        # and is injected into the LLM expansion prompt — NOT embedded as raw YAML.
        root = Path(__file__).resolve().parent.parent
        config_root = config_root or (root / "config")
        use_group = _is_uslf_group_article(item, config_root)

        if use_group:
            # Multi-teacher interfaith placeholder — LLM expansion will replace with
            # named teachers' convergence on positive aspects of the news story.
            teachers = item.get("_teachers_resolved") or []
            if teachers and len(teachers) >= 2:
                names_traditions = [
                    f"{t.get('display_name', '?')} ({t.get('tradition', '?')})"
                    for t in teachers
                ]
                teacher_list = ", ".join(names_traditions[:-1]) + " and " + names_traditions[-1]
                return (
                    f"<p>[INTERFAITH DIALOGUE — this section will be replaced during expansion "
                    f"showing where {teacher_list} CONVERGE on positive aspects of this news story "
                    f"for helping youth, using their approved teachings from the knowledge base.]</p>"
                )
            return (
                "<p>[INTERFAITH DIALOGUE — this section will be replaced during expansion "
                "with 2-3 teachers from different traditions agreeing on positive aspects "
                "of this news story for helping youth.]</p>"
            )
        # Single-teacher placeholder — LLM expansion will replace this with
        # the named teacher's 3 approved teachings from the TEACHER KNOWLEDGE BASE.
        return (
            "<p>[TEACHER PERSPECTIVE — this section will be replaced during expansion "
            "with the named teacher and three distinct insights from their tradition, "
            "each connecting specifically to this news story.]</p>"
        )

    if source in ("sdg_ref", "sdg_framework", "sdg_un_tie", "sdg_alignment", "sdg_policy_tie", "sdg_reference"):
        label = sdg_labels.get(primary_sdg) or "Sustainable Development"
        return (
            f"<p>This story relates to <strong>SDG {primary_sdg}: {label}</strong>. The {un_body} tracks progress and supports initiatives in this area.</p>\n\n"
            f"<p>Understanding how global goals connect to daily life helps readers see the relevance of international frameworks. Youth, educators, and community leaders often use SDG language to align local action with broader objectives.</p>\n\n"
            "<p>Pearl News is an independent nonprofit and is not affiliated with the United Nations.</p>"
        )

    if source == "generate" or source == "fixed":
        if "forward_look" in slot_name or "solutions" in slot_name or "next_steps" in slot_name:
            return (
                "<p>Constructive next steps and dialogue continue to shape how communities and youth engage with these challenges.</p>\n\n"
                "<p>Ongoing coverage will track developments and the role of multilateral dialogue, local initiatives, and youth-led responses.</p>"
            )
        if "headline" in slot_name:
            return (item.get("title") or item.get("raw_title") or "News update").strip()
        return ""

    return ""


def _render_article(
    template: dict,
    item: dict[str, Any],
    atoms_root: Path,
    config_root: Path | None = None,
) -> tuple[str, str]:
    """Build full HTML content and plain title from template slots."""
    root = Path(__file__).resolve().parent.parent
    config_root = config_root or (root / "config")
    slots = template.get("section_slots") or []
    topic = item.get("topic") or "partnerships"
    primary_sdg = item.get("primary_sdg") or "17"
    sdg_labels = item.get("sdg_labels") or {"17": "Partnerships for the Goals"}
    un_body = item.get("un_body") or "United Nations"

    parts = []
    title = ""
    for s in slots:
        slot_name = (s if isinstance(s, str) else s.get("slot")) or ""
        source = s.get("source", "generate") if isinstance(s, dict) else "generate"
        fixed_val = s.get("value") if isinstance(s, dict) else None
        if fixed_val and source == "fixed":
            parts.append(f"<p><strong>{fixed_val}</strong></p>")
            continue
        content = _resolve_slot(
            slot_name, source, item, atoms_root, topic, primary_sdg, sdg_labels, un_body, config_root
        )
        if not content and slot_name == "label" and "Commentary" in str(s):
            parts.append("<p><strong>Commentary</strong></p>")
            continue
        if slot_name == "headline":
            title = content.replace("<h2>", "").replace("</h2>", "").strip() or item.get("title", "")
            parts.append(f"<h1>{title}</h1>")
        elif content:
            if not content.startswith("<"):
                content = f"<p>{content}</p>"
            parts.append(content)

    body = "\n\n".join(parts)

    # Inject HTML comment section markers for reliable section detection by validator.
    # These survive LLM expansion because the prompt says "preserve all HTML tags from the draft."
    # Maps slot names to canonical section IDs used by gate_six_sections_present.
    _SLOT_TO_SECTION = {
        "lede": "lede", "headline": None,  # headline becomes <h1>, lede is first content slot
        "news_summary": "news_summary", "event_reference": "news_summary",
        "what_happened": "lede", "historical_background": "news_summary",
        "thesis": "lede", "event_summary": "lede", "leaders_present": "news_summary",
        "youth_impact": "youth_impact", "youth_narrative": "youth_impact",
        "youth_implications": "youth_impact", "youth_commitments": "youth_impact",
        "data_research": "news_summary", "civic_recommendation": "youth_impact",
        "teacher_perspective": "teacher_perspective", "teacher_reflection": "teacher_perspective",
        "teaching_interpretation": "teacher_perspective", "ethical_spiritual": "teacher_perspective",
        "themes_agreement": "teacher_perspective",
        "sdg_connection": "sdg_connection", "sdg_framework": "sdg_connection",
        "sdg_policy_tie": "sdg_connection", "sdg_reference": "sdg_connection",
        "sdg_alignment": "sdg_connection",
        "forward_look": "forward_look", "solutions": "forward_look",
        "next_steps": "forward_look", "future_outlook": "forward_look",
        "closing_provocation": "forward_look",
    }
    # Insert section markers before each section's content
    marked_parts = []
    for i, part in enumerate(parts):
        # Find which slot this part came from (by index in slots list)
        if i < len(slots):
            s = slots[i]
            slot_name = (s if isinstance(s, str) else s.get("slot")) or ""
            section_id = _SLOT_TO_SECTION.get(slot_name)
            if section_id:
                marked_parts.append(f"<!-- section: {section_id} -->")
        marked_parts.append(part)
    body = "\n\n".join(marked_parts)

    # Source at end of article (disclaimer is on site About, not repeated per article)
    url = item.get("url") or ""
    if url:
        display_url = url[:80] + "…" if len(url) > 80 else url
        body = body.rstrip() + "\n\n<p><em>Source: <a href=\"" + url + "\">" + display_url + "</a></em></p>"
    headline = title or item.get("title") or item.get("raw_title") or "Pearl News"
    return headline, body


def assemble_articles(
    items: list[dict[str, Any]],
    templates_dir: Path | None = None,
    atoms_root: Path | None = None,
) -> list[dict[str, Any]]:
    """
    For each item, load its template_id template, fill slots from item + atoms (or placeholders),
    set article title, content (HTML), and content_plain. Adds headline_sig, lede_sig for manifest.
    """
    root = Path(__file__).resolve().parent.parent
    templates_dir = templates_dir or (root / "article_templates")
    atoms_root = atoms_root or (root / "atoms")

    for item in items:
        template_id = item.get("template_id") or "hard_news_spiritual_response"
        template_file = item.get("template_file") or f"{template_id}.yaml"
        template = _load_template(templates_dir, template_file)

        headline, content = _render_article(template, item, atoms_root)

        item["article_title"] = headline
        item["content"] = content
        item["content_plain"] = headline + "\n\n" + content.replace("<p>", "\n").replace("</p>", "").replace("<h1>", "\n").replace("</h1>", "").replace("<h2>", "\n").replace("</h2>", "").strip()

        # Signatures for diversity/audit
        item["headline_sig"] = hashlib.sha256(headline.lower().encode("utf-8")).hexdigest()[:16]
        lede = content[:500] if content else ""
        item["lede_sig"] = hashlib.sha256(lede.encode("utf-8")).hexdigest()[:16]

    logger.info("Assembled %d articles", len(items))
    return items
