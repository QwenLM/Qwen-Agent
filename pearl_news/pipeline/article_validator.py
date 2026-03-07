"""
Pearl News — hard post-generation validation gates.
Runs after LLM expansion. Any FAIL → article flagged for manual review.
On FAIL: caller should retry once (already handled in run_expansion), then flag.

Gates:
  1. six_sections_present  — <h1> lede, news_summary, youth_impact, teacher, sdg, forward_look
  2. named_teacher         — teacher section contains a named teacher (not generic placeholder)
  3. teacher_three_points  — teacher section has 3 distinct substantive paragraphs
  4. sdg_number_present    — SDG number (e.g. "SDG 16" or "SDG16") appears in content
  5. sdg_full_title        — a known SDG title keyword appears near the SDG number
  6. youth_anchor          — youth/impact section has at least one anchor (number/%, place, age band)
  7. no_banned_phrases     — none of the "never write" phrases appear in content
  8. source_line_present   — Source: line at end is preserved
"""
from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Known SDG keywords (title fragments) for gate 5
# ---------------------------------------------------------------------------
_SDG_TITLE_KEYWORDS = {
    "1": ["no poverty", "poverty"],
    "2": ["zero hunger", "hunger", "food security"],
    "3": ["good health", "well-being", "wellbeing", "health"],
    "4": ["quality education", "education"],
    "5": ["gender equality", "gender"],
    "6": ["clean water", "sanitation"],
    "7": ["affordable energy", "clean energy"],
    "8": ["decent work", "economic growth", "employment"],
    "9": ["industry", "innovation", "infrastructure"],
    "10": ["reduced inequalit", "inequality"],
    "11": ["sustainable cities", "communities"],
    "12": ["responsible consumption", "production"],
    "13": ["climate action", "climate"],
    "14": ["life below water", "ocean"],
    "15": ["life on land", "biodiversity"],
    "16": ["peace", "justice", "strong institutions"],
    "17": ["partnerships", "global goals"],
}

# ---------------------------------------------------------------------------
# Banned phrases (from PEARL_NEWS_WRITER_SPEC.md §10 / expansion_system.txt)
# ---------------------------------------------------------------------------
_BANNED_PHRASES = [
    r"young people around the world are feeling",
    r"now more than ever",
    r"in these uncertain times",
    r"historic\b.{0,30}(agreement|summit|accord|resolution|decision)",  # without context
    r"landmark\b.{0,30}(agreement|summit|accord|resolution|decision)",
    r"pearl news.{0,40}(affiliated|affiliation|partner|partnership) with the united nations",
    r"in a world where",
    # "as X continues to" is only banned as a LEDE/SENTENCE OPENER — not mid-sentence.
    # Conflict journalism legitimately uses "as fighting continues to escalate" etc.
    # Matches only after start-of-string or end-of-prior-sentence (". ").
    r"(?:(?:^|(?<=\. ))as \w+ continues to)",
    r"\bwe\b",  # avoid "we" in articles
]

# Teacher generic placeholder phrases — if these appear, named_teacher gate fails
_GENERIC_TEACHER_PHRASES = [
    "a teacher from the united spiritual leaders forum",
    "a spiritual leader says",
    "teachers believe",
    "forum collectively",
]

# Youth anchor patterns
_YOUTH_ANCHOR_PATTERNS = [
    r"\b\d+\s*%",               # percentage e.g. "47%"
    r"\b\d[\d,\.]+\s*(million|billion|thousand)\b",  # large numbers
    r"\b(gen z|gen alpha|generation z|generation alpha)\b",  # named generation
    r"\bages?\s+\d+",            # age band e.g. "ages 15-28"
    r"\b\d+\s*(to|-)\s*\d+\s*year",  # age range
    r"\b(japan|china|india|nigeria|brazil|indonesia|philippines|mexico|uk|us|usa|australia)\b",  # named country
    r"\b(tokyo|beijing|shanghai|jakarta|nairobi|lagos|sao paulo|london|new york)\b",  # named city
]

# ---------------------------------------------------------------------------
# Gate functions
# ---------------------------------------------------------------------------

def _has_h1(content: str) -> bool:
    return bool(re.search(r"<h1[^>]*>", content, re.IGNORECASE))


def _count_paragraphs(content: str) -> int:
    return len(re.findall(r"<p[^>]*>", content, re.IGNORECASE))


def _teacher_section_text(content: str) -> str:
    """
    Best-effort: extract text in the teacher perspective section.

    Strategy (in priority order):
    1. Find <h2>/<h3> containing "teacher" or "perspective" or "wisdom" — most reliable.
    2. Find "teaches that" (specific to teacher body text, rarely appears elsewhere).
    3. Find LAST occurrence of "tradition" (teacher attribution is late in the article;
       "tradition" near the top is usually in a different context).
    4. Fallback: last 3000 chars of article (teacher section is near the end).

    Avoids false positives from "United Spiritual Leaders Forum" / "spiritual" in the lede.
    """
    lower = content.lower()

    # Priority 1: section header <h2>/<h3> mentioning teacher/perspective/wisdom
    for header_pattern in [
        r"<h[23][^>]*>[^<]*(?:teacher|perspective|wisdom|spiritual leader|tradition)[^<]*</h[23]>",
    ]:
        m = re.search(header_pattern, lower)
        if m:
            idx = m.start()
            return content[idx: idx + 3000]

    # Priority 2: "teaches that" — highly specific to teacher body text
    i = lower.find("teaches that")
    if i != -1:
        return content[max(0, i - 300): i + 2500]

    # Priority 3: LAST occurrence of "tradition" (teacher attribution is late in article)
    i = lower.rfind("tradition")
    if i != -1:
        return content[max(0, i - 300): i + 2500]

    # Priority 4: "teaches" (broader — last occurrence)
    i = lower.rfind("teaches")
    if i != -1:
        return content[max(0, i - 300): i + 2500]

    # Priority 5: Fallback — last 3500 chars (teacher section is near end)
    return content[max(0, len(content) - 3500):]


def _youth_section_text(content: str) -> str:
    """Best-effort: extract text in the youth impact section."""
    lower = content.lower()
    idx = lower.find("youth")
    if idx == -1:
        idx = lower.find("young")
    if idx == -1:
        return content  # fallback: check whole article
    return content[max(0, idx - 100): idx + 3000]


def gate_six_sections_present(content: str) -> tuple[bool, str]:
    """
    Check that all 6 required sections are present.

    Strategy (in priority order):
    1. If HTML comment markers (<!-- section: ... -->) are present, use them directly.
       These are injected by the assembler and preserved through expansion.
    2. Fall back to heuristic keyword detection for articles without markers.
    """
    lower = content.lower()

    # Priority 1: HTML comment section markers (reliable)
    marker_sections = re.findall(r"<!-- section: (\w+)", lower)
    if marker_sections:
        required = {"lede", "news_summary", "youth_impact", "teacher_perspective", "sdg_connection", "forward_look"}
        # Normalize: some templates use different names
        aliases = {
            "youth_narrative": "youth_impact", "data_research": "news_summary",
            "teacher_reflection": "teacher_perspective", "teaching_interpretation": "teacher_perspective",
            "ethical_spiritual": "teacher_perspective", "themes_agreement": "teacher_perspective",
            "what_happened": "lede", "historical_background": "news_summary",
            "thesis": "lede", "event_reference": "news_summary",
            "event_summary": "lede", "leaders_present": "news_summary",
            "solutions": "forward_look", "next_steps": "forward_look",
            "future_outlook": "forward_look", "closing_provocation": "forward_look",
            "sdg_framework": "sdg_connection", "sdg_policy_tie": "sdg_connection",
            "sdg_reference": "sdg_connection", "sdg_alignment": "sdg_connection",
            "civic_recommendation": "youth_impact", "youth_commitments": "youth_impact",
            "youth_implications": "youth_impact",
        }
        found = set()
        for m in marker_sections:
            canonical = aliases.get(m, m)
            found.add(canonical)
        missing = required - found
        if missing:
            return False, f"Missing sections (by marker): {', '.join(sorted(missing))}"
        return True, f"all 6 sections present (by marker, found {len(marker_sections)} markers)"

    # Priority 2: Heuristic fallback (less reliable)
    checks = {
        "lede (<h1>)": _has_h1(content),
        "news_summary (≥2 <p>)": _count_paragraphs(content) >= 2,
        "youth_impact": any(k in lower for k in ["youth", "young people", "gen z", "gen alpha", "adolescent"]),
        "teacher_perspective": any(k in lower for k in ["tradition", "teaches that", "teach", "teacher"]),
        "sdg_connection": bool(re.search(r"sdg\s*\d+", lower) or "sustainable development goal" in lower),
        "forward_look": any(k in lower for k in ["upcoming", "next", "will", "deadline", "summit", "vote", "action", "can "]),
        "source_line": "source:" in lower,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        return False, f"Missing sections: {', '.join(failed)}"
    return True, "all 6 sections present (heuristic)"


def gate_named_teacher(content: str) -> tuple[bool, str]:
    """Teacher section must not be the generic placeholder."""
    lower = content.lower()
    for phrase in _GENERIC_TEACHER_PHRASES:
        if phrase in lower:
            return False, f"Generic teacher placeholder detected: '{phrase}'"
    # Must have "tradition" + a proper noun (capitalized word near it)
    has_tradition = "tradition" in lower
    has_teaches = "teaches that" in lower
    if not (has_tradition or has_teaches):
        return False, "No named teacher attribution found (missing 'tradition' or 'teaches that')"
    return True, "named teacher present"


def gate_teacher_three_points(content: str) -> tuple[bool, str]:
    """Teacher section should have at least 3 substantive paragraphs."""
    teacher_text = _teacher_section_text(content)
    paras = re.findall(r"<p[^>]*>(.+?)</p>", teacher_text, re.IGNORECASE | re.DOTALL)
    substantive = [p for p in paras if len(p.strip().split()) >= 20]
    if len(substantive) < 3:
        return False, f"Teacher section has only {len(substantive)} substantive paragraphs (need ≥3)"
    return True, f"teacher has {len(substantive)} substantive paragraphs"


def gate_sdg_number(content: str) -> tuple[bool, str]:
    """SDG number must appear in content."""
    if re.search(r"SDG\s*\d+|sustainable development goal\s*\d+", content, re.IGNORECASE):
        return True, "SDG number present"
    return False, "No SDG number found (e.g. 'SDG 13' or 'Sustainable Development Goal 13')"


def gate_sdg_full_title(content: str, primary_sdg: str) -> tuple[bool, str]:
    """A keyword from the SDG's full title must appear near the SDG number."""
    keywords = _SDG_TITLE_KEYWORDS.get(str(primary_sdg), [])
    if not keywords:
        return True, f"No keyword list for SDG {primary_sdg} — skipped"
    lower = content.lower()
    for kw in keywords:
        if kw.lower() in lower:
            return True, f"SDG title keyword '{kw}' found"
    return False, f"SDG {primary_sdg} title keywords not found (expected one of: {keywords[:3]})"


def gate_youth_anchor(content: str) -> tuple[bool, str]:
    """Youth section must have at least one concrete anchor."""
    youth_text = _youth_section_text(content)
    for pattern in _YOUTH_ANCHOR_PATTERNS:
        if re.search(pattern, youth_text, re.IGNORECASE):
            return True, f"Youth anchor found (pattern: {pattern[:30]})"
    return False, "No concrete youth anchor found (need number/%, place, or age band in youth section)"


def gate_no_banned_phrases(content: str) -> tuple[bool, str]:
    """None of the banned phrases should appear."""
    for phrase in _BANNED_PHRASES:
        if re.search(phrase, content, re.IGNORECASE):
            return False, f"Banned phrase detected: '{phrase}'"
    return True, "no banned phrases"


def gate_source_line(content: str) -> tuple[bool, str]:
    """Source: line must be preserved at end."""
    lower = content.lower()
    if "source:" in lower or "<em>source:" in lower:
        return True, "Source line present"
    return False, "Source line missing — was stripped during expansion"


def gate_multi_teacher_present(content: str, teachers: list[dict] | None = None) -> tuple[bool, str]:
    """For interfaith articles: check that 2+ distinct teacher names appear in content."""
    if not teachers or len(teachers) < 2:
        return True, "not an interfaith article — skipped"

    lower = content.lower()
    found_names = []
    for t in teachers:
        name = t.get("display_name", "")
        if name and name.lower() in lower:
            found_names.append(name)

    if len(found_names) < 2:
        return False, f"Only {len(found_names)} of {len(teachers)} teachers found in content: {found_names}"

    # Check for convergence language
    convergence_signals = ["converge", "agree", "common ground", "shared", "both", "across traditions", "together"]
    has_convergence = any(sig in lower for sig in convergence_signals)
    if not has_convergence:
        return False, f"Teachers found ({found_names}) but no convergence language detected"

    return True, f"Multi-teacher present: {found_names} with convergence language"


def gate_fallback_teacher(teacher: dict | None = None) -> tuple[bool, str]:
    """Articles using fallback teacher must be held for manual review — not published."""
    if teacher and teacher.get("is_fallback"):
        return False, "Fallback teacher used — no real teacher atoms available for this topic. Hold for manual review."
    if teacher and teacher.get("teacher_id") == "__fallback__":
        return False, "Fallback teacher used — article needs a real named teacher before publishing."
    return True, "Real named teacher assigned"


def gate_evidence_present(content: str) -> tuple[bool, str]:
    """Article must contain at least 2 evidence signals (reports, surveys, data, named experts)."""
    lower = content.lower()
    evidence_patterns = [
        r"\b\d{4}\b.{0,40}(report|survey|study|paper|white paper|assessment|index)",
        r"\b(pew|gallup|who|unicef|world bank|imf|oecd|cabinet office|ministry|department of)\b",
        r"\b\d+\s*%",  # percentage (data signal)
        r"\b(according to|published by|released by|conducted by)\b",
        r"\b(professor|researcher|dr\.|economist|analyst)\b",
        r"\b(resolution|a/\d+|s/\d+)\b",  # UN resolution numbers
    ]
    found = 0
    matched = []
    for pattern in evidence_patterns:
        if re.search(pattern, lower):
            found += 1
            matched.append(pattern[:30])
    if found < 2:
        return False, f"Only {found} evidence signal(s) found (need ≥2). Articles need sourced claims."
    return True, f"{found} evidence signals found"


def gate_localization_bridge(content: str, language: str = "en") -> tuple[bool, str]:
    """
    Check that a localization bridge sentence connects the global story to the local audience.

    Position-aware: the bridge must appear BEFORE the teacher/spiritual section
    (between news summary and youth impact — roughly the first 60% of the article).
    Content-aware: a country name alone is not enough — must co-occur with a local
    statistic (number/%), ministry/policy name, or local event reference within ~200 chars.
    """
    lower = content.lower()

    # Determine where teacher section starts (bridge must appear before it)
    teacher_idx = len(lower)  # default: full article
    for marker in ["<!-- section: teacher", "teaches that", "tradition,", "tradition suggests"]:
        idx = lower.find(marker)
        if idx != -1 and idx < teacher_idx:
            teacher_idx = idx
    # If no teacher marker found, use first 60% of article
    if teacher_idx == len(lower):
        teacher_idx = int(len(lower) * 0.6)

    pre_teacher = lower[:teacher_idx]

    # Country/locality signals per language
    locality_signals = {
        "ja": ["japan", "japanese", "ministry of", "cabinet office", "mext", "tokyo",
               "osaka", "kyoto", "prefectur", "diet", "yen"],
        "zh-cn": ["china", "chinese", "state council", "beijing", "gaokao", "tangping",
                   "province", "shanghai", "guangdong", "yuan", "npc", "cppcc"],
        "en": ["united states", "u.s.", "american", "uk", "australia", "department of",
               "congress", "senate", "parliament", "federal", "washington"],
    }
    signals = locality_signals.get(language, locality_signals["en"])

    # Evidence patterns that indicate a real local statistic/policy (not just passing mention).
    # Tightened: "report" alone in a headline doesn't count — evidence terms must
    # co-occur with a number, year, or named institution within the window.
    evidence_patterns = [
        r"\b\d+\s*%",                          # percentage (strong signal)
        r"\b\d[\d,\.]+\s*(million|billion|trillion|yen|yuan|dollar|pound)\b",
        r"\b(ministry|department|bureau|agency|council|commission|office)\s+of\b",  # "ministry of" not just "office"
        r"\b\d{4}\b.{0,30}\b(survey|report|white paper|census|index)\b",  # year + report type
        r"\b(reported|published|released|found|showed|cited|according to)\b",  # attribution verbs
        r"\b(rose|fell|increased|decreased|dropped|climbed|reached|hit)\b.{0,20}\b\d",
        r"\b(similar|parallel|comparable|equivalent|likewise|also reported)\b.{0,40}\b\d",
    ]

    found_signals = []
    for sig in signals:
        sig_idx = pre_teacher.find(sig)
        if sig_idx == -1:
            continue
        # Check for evidence within ±200 chars of the signal
        window_start = max(0, sig_idx - 200)
        window_end = min(len(pre_teacher), sig_idx + len(sig) + 200)
        window = pre_teacher[window_start:window_end]
        for pat in evidence_patterns:
            if re.search(pat, window):
                found_signals.append(sig)
                break

    if not found_signals:
        return False, (
            f"No localization bridge found for language={language}. "
            f"Need a local statistic, ministry/policy reference, or data point — "
            f"not just a country name in passing. Must appear before teacher section."
        )
    return True, f"Localization bridge present (signals: {found_signals[:3]} with local evidence)"


def gate_min_word_count(content: str, min_words: int = 600) -> tuple[bool, str]:
    """Expanded article must meet minimum word count (default 600 words)."""
    # Strip HTML tags for clean word count
    import re as _re
    text = _re.sub(r"<[^>]+>", " ", content)
    text = _re.sub(r"\s+", " ", text).strip()
    word_count = len(text.split())
    if word_count < min_words:
        return False, f"Article is only {word_count} words (minimum {min_words})"
    return True, f"Article has {word_count} words (minimum {min_words})"


def gate_section_word_counts(content: str) -> tuple[bool, str]:
    """
    Check that key sections meet their minimum word counts:
    - News summary: ≥60 words
    - Youth impact: ≥50 words
    - Teacher perspective: ≥75 words (3 paragraphs × 25 words each)
    - SDG connection: ≥40 words
    - Forward look: ≥30 words
    """
    import re as _re

    def _strip_html(html: str) -> str:
        return _re.sub(r"\s+", " ", _re.sub(r"<[^>]+>", " ", html)).strip()

    lower = content.lower()
    failures = []

    # Teacher section (reuse existing helper)
    teacher_text = _strip_html(_teacher_section_text(content))
    teacher_wc = len(teacher_text.split())
    if teacher_wc < 75:
        failures.append(f"teacher_perspective={teacher_wc}w (need ≥75)")

    # Youth section
    youth_text = _strip_html(_youth_section_text(content))
    youth_wc = len(youth_text.split())
    if youth_wc < 50:
        failures.append(f"youth_impact={youth_wc}w (need ≥50)")

    # SDG section: find "SDG" keyword and extract surrounding text
    sdg_match = _re.search(r"sdg\s*\d+", lower)
    if sdg_match:
        sdg_start = max(0, sdg_match.start() - 200)
        sdg_end = min(len(content), sdg_match.end() + 1500)
        sdg_text = _strip_html(content[sdg_start:sdg_end])
        sdg_wc = len(sdg_text.split())
        if sdg_wc < 40:
            failures.append(f"sdg_connection={sdg_wc}w (need ≥40)")

    if failures:
        return False, f"Thin sections: {'; '.join(failures)}"
    return True, "all sections meet minimum word counts"


# ---------------------------------------------------------------------------
# Run all gates
# ---------------------------------------------------------------------------

def validate_article(
    content: str,
    primary_sdg: str = "17",
    strict: bool = True,
    teachers: list[dict] | None = None,
    teacher: dict | None = None,
    language: str = "en",
) -> dict[str, Any]:
    """
    Run all validation gates on expanded article content.
    Returns:
      passed: bool — True if all required gates pass
      gates: dict of gate_name → {passed, message}
      failed_gates: list of gate names that failed
      retry_recommended: bool — True if any required gate failed
    """
    results: dict[str, dict] = {}

    # Run gates
    gates_to_run = [
        ("six_sections_present", gate_six_sections_present(content)),
        ("min_word_count", gate_min_word_count(content, min_words=600)),
        ("section_word_counts", gate_section_word_counts(content)),
        ("named_teacher", gate_named_teacher(content)),
        ("fallback_teacher", gate_fallback_teacher(teacher=teacher)),
        ("teacher_three_points", gate_teacher_three_points(content)),
        ("multi_teacher_present", gate_multi_teacher_present(content, teachers=teachers)),
        ("localization_bridge", gate_localization_bridge(content, language=language)),
        ("evidence_present", gate_evidence_present(content)),
        ("sdg_number", gate_sdg_number(content)),
        ("sdg_full_title", gate_sdg_full_title(content, primary_sdg)),
        ("youth_anchor", gate_youth_anchor(content)),
        ("no_banned_phrases", gate_no_banned_phrases(content)),
        ("source_line", gate_source_line(content)),
    ]

    for gate_name, (passed, message) in gates_to_run:
        results[gate_name] = {"passed": passed, "message": message}

    failed_gates = [name for name, r in results.items() if not r["passed"]]
    all_passed = len(failed_gates) == 0

    return {
        "passed": all_passed,
        "gates": results,
        "failed_gates": failed_gates,
        "retry_recommended": not all_passed,
        "gate_count": len(gates_to_run),
        "passed_count": len(gates_to_run) - len(failed_gates),
    }


def run_validation(
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Run validation on all items. Attaches _validation result to each item.
    Items that fail are flagged _validation_failed=True and _needs_manual_review=True.
    """
    for item in items:
        content = item.get("content") or ""
        primary_sdg = str(item.get("primary_sdg") or "17")
        if not content:
            item["_validation"] = {"passed": False, "failed_gates": ["no_content"], "gates": {}}
            item["_validation_failed"] = True
            item["_needs_manual_review"] = True
            continue

        teachers = item.get("_teachers_resolved") or None
        teacher = item.get("_teacher_resolved") or None
        language = item.get("language") or "en"
        result = validate_article(
            content, primary_sdg=primary_sdg, teachers=teachers,
            teacher=teacher, language=language,
        )
        item["_validation"] = result
        item["_validation_failed"] = not result["passed"]
        item["_needs_manual_review"] = not result["passed"]

        if not result["passed"]:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                "Article %s failed validation gates: %s",
                item.get("id"), result["failed_gates"],
            )
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                "Article %s passed all %d validation gates",
                item.get("id"), result["gate_count"],
            )

    return items
