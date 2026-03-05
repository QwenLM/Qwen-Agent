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
        # Try atoms/teacher_quotes_practices/ (one teacher per topic when available)
        teacher_dir = atoms_root / "teacher_quotes_practices"
        root = Path(__file__).resolve().parent.parent
        config_root = config_root or (root / "config")
        use_group = _is_uslf_group_article(item, config_root)

        if teacher_dir.exists():
            # Prefer one teacher's content for this topic when not group
            candidates = []
            for f in teacher_dir.rglob("*"):
                if f.suffix in (".md", ".txt", ".yaml"):
                    try:
                        text = f.read_text(encoding="utf-8")
                        if topic in text.lower():
                            candidates.append(text.strip())
                    except Exception:
                        continue
            if candidates:
                # Single-teacher: use one teacher's content. Group (5%): use group placeholder.
                if not use_group:
                    return candidates[0]
                return "<p>Leaders from the United Spiritual Leaders Forum emphasize reflection and resilience in the face of uncertainty, in line with ethical frameworks that support youth well-being and global goals.</p>"

        # No atoms: placeholders. 95% single-teacher (one teacher's insight + youth), 5% group USLF
        if use_group:
            return (
                "<p>Leaders from the United Spiritual Leaders Forum emphasize reflection and resilience in the face of uncertainty, in line with ethical frameworks that support youth well-being and global goals.</p>\n\n"
                "<p>Dialogue across traditions helps communities respond to crisis with clarity and compassion.</p>"
            )
        return (
            "<p>A teacher from the United Spiritual Leaders Forum offers perspective on this topic and its relevance to youth: reflection and resilience in the face of uncertainty, in line with ethical frameworks that support youth well-being and global goals.</p>\n\n"
            "<p>How spiritual and ethical traditions speak to young people in times of change—and how youth can draw on these insights for clarity and action—remains a focus of our coverage.</p>\n\n"
            "<p>We aim to present one voice at a time, so readers can engage with a clear perspective before exploring further.</p>"
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
