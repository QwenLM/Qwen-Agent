# Pearl News — Complete Article Plan

## Mission

Pearl News reports global events through the intersection of public policy, youth reality, and the ethical insights of ancient wisdom traditions. Every article connects a real news event, the lived experience of young people, and a practical perspective drawn from a recognized spiritual teacher — framed within the UN Sustainable Development Goals where relevant.

Pearl News does not endorse any spiritual tradition or teacher. The teacher perspective is interpreted by the journalist, not quoted as authority. Teachers offer a lens — the reader decides what to do with it.

---

## Editorial Identity

Pearl News is not a spiritual magazine. It is not a UN press release. It is not a youth trends report. When it works, it is all three fused into one story. The editorial test: if the news event, the youth reality, or the teacher lens could be removed and the article would still make sense, that layer was decoration and the article has failed.

---

## Audience

Pearl News readers are Gen Z and Gen Alpha (ages 12–28) in Japan, China, Taiwan, and English-speaking countries. Pearl News is a civic journalism outlet of the United Spiritual Leaders Forum.

**Two audience segments** (articles should target one or both):

- **Students (12–18)**: Still in school. Encounter policy through education, family, and social media. Need context and explanation. Respond to concrete examples and named people their age.
- **Young Adults (18–28)**: Entering workforce, university, or civic life. Can engage with structural analysis. Respond to contradiction, data, and actionable recommendations.

When writing, default to the young adult register. When the topic is education, mental health, or digital safety, also address the student segment explicitly.

---

## The Five Article Types

Pearl News publishes five distinct article types. Each serves a different editorial purpose, uses a different structure, and asks a different question of the teacher layer. The editorial foundation is: news anchor + youth reality + teacher wisdom as lens. SDG framing is included where the news event clearly relates to a UN goal — it is not forced into every article.

| Type | When to Use | Teacher Role | Voice |
|------|-------------|-------------|-------|
| Hard News Analysis | Breaking news, climate event, conflict, AI/regulation, economic shift | Tradition suggests a different way to interpret this moment — 3 insights | Precise, urgent, grounded |
| Youth Reality Feature | Youth anxiety, education shift, climate activism, digital overload | Reframes what the data reveals — does not instruct | Intimate, humanizing |
| Commentary | Strong opinion needed; max 15% of output | Interpretive lens central to the argument — ONLY type where this is permitted | Confident, arguable thesis |
| Explainer | Complex issue needing depth, not breaking news | Asks a QUESTION the tradition raises — does NOT answer | Authoritative, accessible |
| Interfaith Forum Report | Forum gathering, multi-leader event, joint declaration | 2-3 teachers from different traditions CONVERGE (not debate) | Diplomatic, record of convergence |

---

## Quick Distinctions

**Hard News vs. Youth Feature**: Hard news leads with the sharpest fact from the news item. Youth feature opens on a specific young person, cohort, or place and builds the narrative outward.

**Hard News vs. Commentary**: Hard news is neutral reporting + teacher lens. Commentary has an arguable thesis and the teacher's tradition supports the argument. Commentary must be labeled "Commentary" above the headline.

**Explainer vs. Hard News**: Hard news reports what happened and moves on. The explainer goes deeper — historical background, structural causes, at least 2 prior moments that made this inevitable.

**Interfaith vs. single-teacher types**: Interfaith uses 2-3 teachers from different traditions who CONVERGE on what the news story means for youth. All other types use exactly one teacher. Interfaith shows agreement, not debate.

---

## Template Selection Logic

The pipeline selects templates through this priority chain:

1. `suggested_template` from the topic classifier
2. Caller override mapping
3. Config `topic_to_template` mapping from `article_templates_index.yaml`
4. Default topic mapping: `mental_health` and `education` → Youth Feature; `peace_conflict` → Hard News; `inequality` → Explainer
5. Source heuristics: `un_news_sdgs` + education/mental_health → Youth Feature; `un_news_sdgs` → Explainer
6. Fallback: Hard News + Spiritual Response

Interfaith Dialogue Report is now content-aware: the item's title/summary must contain interfaith signals (e.g. "interfaith", "dialogue", "faith leaders", "summit", "declaration") AND pass a 30% hash threshold. This prevents interfaith reports about unrelated topics like climate data or court rulings.

**Commentary frequency cap**: No more than 15% of articles in a single pipeline run can be commentary. Excess commentary articles are demoted to Hard News + Spiritual Response.

---

## Article Type 1: Hard News + Spiritual Response

**Template ID**: `hard_news_spiritual_response`
**Use for**: Breaking news, climate event, conflict, AI/regulation, economic shift
**Target length**: 800–1000 words
**Minimum total**: 600 words

### Section Flow

```
<h1>[Headline — neutral, from news event + topic, no devotional language]</h1>

LEDE (≥50 words)
  Sharpest fact, contradiction, or concrete scene.
  First sentence: one number OR one place name OR one age band.
  News peg first, then meaning.

NEWS SUMMARY (≥120 words)
  Who, what, where, when from the UN source.
  Name the UN body, resolution, or report by full name.
  One specific figure or date. No editorializing.

YOUTH IMPACT (≥100 words)
  How this affects the reading audience (ja/zh-cn/en Gen Z/Alpha).
  Every sentence needs an anchor: number, country/city, age band, or behavior.
  CONTRADICTION TEST: stated concern vs. actual behavior.
  Behavior over emotion.

TEACHER PERSPECTIVE (≥90 words — 3 paragraphs × ≥30 words each)
  Named teacher from Knowledge Base. Attributed by name AND tradition.
  Three separate <p> paragraphs — one insight per paragraph.
  Each insight connects to THIS specific news story.
  Teacher RESPONDS to the news — does not replace it.

SDG CONNECTION (≥60 words)
  SDG number + full title + specific target (e.g. "Target 16.3").
  Mechanism: how this story advances or threatens that target.
  Pearl News disclaimer.

FORWARD LOOK (≥50 words)
  One concrete upcoming event, vote, deadline, or action.
  One specific reader action (not "raise awareness").
  Close with question or provocation.

<p><em>Source: <a href="...">[RSS source]</a></em></p>
```

### Teacher Format (Hard News)

```html
<p>[Teacher name], drawing from the [tradition] tradition, teaches that
   [insight 1 connected to this story — ≥30 words].</p>
<p>A second teaching from [Teacher name]: [insight 2 — ≥30 words].</p>
<p>[Teacher name] also holds that [insight 3 — ≥30 words].</p>
```

### Editorial Rule

The UN RSS item is the news event that triggers this article. The teacher does NOT drive the story — they respond to it. Do NOT write a teacher profile. Write a news story that uses one teacher's wisdom as a lens on the news event.

---

## Article Type 2: Youth Feature

**Template ID**: `youth_feature`
**Use for**: Youth anxiety, education shift, climate activism, digital overload
**Target length**: 800–1000 words
**Minimum total**: 600 words

### Section Flow

```
<h1>[Headline]</h1>

YOUTH NARRATIVE (≥150 words)
  Open on a specific young person, named cohort, or concrete place.
  First sentence: one age, one location/institution, one behavior/decision.
  News event must appear in first 3 sentences.
  Name the tension or contradiction they are living.
  NOT "young people globally" — show, don't tell.

DATA / RESEARCH (≥120 words)
  Every claim needs a source or study name.
  CONTRADICTION TEST: stated values vs. actual behavior.
  At least 2 data points with source attribution.
  Merge with narrative — not a separate data dump.

TEACHER REFLECTION (≥90 words — 3 paragraphs × ≥30 words each)
  Teacher REFRAMES what the data reveals — does not instruct.
  NOT "you should meditate" → "the tradition distinguishes between
  paralysing despair and the urgency that precedes action."
  Three separate <p> paragraphs, each connected to specific data.

SDG FRAMEWORK (≥80 words)
  SDG number + full title + specific target.
  Structural link between youth reality and SDG target.
  Pearl News disclaimer.

SOLUTIONS (≥120 words)
  Three levels:
    Individual/practice (something a young person can do today)
    Community/organizational (a named program, org, or movement)
    Policy/systemic (a specific bill or institutional change)
  Close with provocation, not summary.

<p><em>Source: <a href="...">[RSS source]</a></em></p>
```

### Teacher Format (Youth Feature)

```html
<p>[Teacher name], drawing from the [tradition] tradition, reflects that
   [reframe 1 connected to a data point — ≥30 words].</p>
<p>[Teacher name] also observes that
   [reframe 2 connected to a behavior — ≥30 words].</p>
<p>From within [tradition], [Teacher name] holds that
   [reframe 3 connected to the youth narrative — ≥30 words].</p>
```

### Editorial Rule

The teacher REFRAMES what the data reveals. They do not instruct, preach, or provide solutions. The youth narrative drives the story — the teacher adds a different lens on the data, not a different story.

---

## Article Type 3: Commentary

**Template ID**: `commentary`
**Use for**: Strong opinion pieces (use sparingly)
**Target length**: 800–1000 words
**Minimum total**: 600 words

### Section Flow

```
<p><strong>Commentary</strong></p>    ← MANDATORY label above headline
<h1>[Headline]</h1>

THESIS (≥100 words)
  One arguable claim — a position a reasonable person could disagree with.
  State plainly in first paragraph. No hedging ("perhaps", "it could be argued").
  Structure: "[Event] is not just [mainstream reading]. It is [what it reveals].
  And until [actor] [action], [consequence] will continue."
  News event must appear in the thesis.

EVENT REFERENCE (≥80 words)
  The specific UN/US news item that triggered this.
  Name the body, resolution, date, one specific figure.
  Facts that support or complicate the thesis.
  No editorializing — save for thesis and teaching interpretation.

TEACHING INTERPRETATION (≥150 words — 3 paragraphs × ≥50 words each)
  The argumentative core. ONLY type where teacher's interpretive lens is central.
  Paragraph 1: What the tradition reveals about the structural/moral dimension.
  Paragraph 2: How the teaching reframes the mainstream interpretation.
  Paragraph 3: Historical precedent — what this tradition has done when confronted
  with this type of injustice or imbalance.
  Teacher CHALLENGES something specific about how the event is framed.

CIVIC RECOMMENDATION (≥100 words)
  One specific, concrete recommendation.
  Name WHO, WHAT, WHERE/mechanism, WHY (from the teaching interpretation).
  Actionable by a 20-year-old reader today.
  Address the young reader directly.

SDG REFERENCE (≥80 words)
  SDG as moral framework for the recommendation — not decoration.
  Specific target being threatened or advanced.
  One metric showing current status.
  Pearl News disclaimer.

CLOSING PROVOCATION (≥60 words)
  Reframe the entire article in one unexpected angle.
  End with a genuine, open question — not rhetorical.
  No summary. No "in conclusion."

<p><em>Source: <a href="...">[RSS source]</a></em></p>
```

### Teacher Format (Commentary)

```html
<p>[Teacher name], from the [tradition] tradition, reveals that
   [interpretive insight 1 — structural/moral dimension — ≥50 words].</p>
<p>[Teacher name]'s teaching specifically reframes this:
   [insight 2 — how the tradition challenges the mainstream reading — ≥50 words].</p>
<p>Historically, the [tradition] tradition has
   [insight 3 — historical precedent — ≥50 words].</p>
```

### Editorial Rule

This is the ONLY Pearl News article type where a teacher's interpretive framework can be explicitly named and argued from. The thesis must be arguable — not a truism. The teacher's tradition supports the ARGUMENT, not generic wisdom. Commentary is opinion grounded in news and tradition — not a sermon.

---

## Article Type 4: Explainer / Context

**Template ID**: `explainer_context`
**Use for**: Complex issues needing depth, not breaking news
**Target length**: 800–1000 words
**Minimum total**: 600 words

### Section Flow

```
<h1>[Headline]</h1>

WHAT HAPPENED (≥80 words)
  Sharpest fact first. Name the event, body, date in first two sentences.
  One sentence on why it matters — not how people feel about it.
  Name the specific body, bill, ruling, or event by full name.
  One specific figure: vote count, dollar amount, date, number affected.
  No editorializing, no background here.

HISTORICAL BACKGROUND (≥120 words)
  Why did this moment not come from nowhere?
  Go back far enough to be genuinely illuminating.
  At least 2 prior moments, decisions, or structural conditions.
  One named historian, researcher, or institutional report.
  Connect past to present with clear causal thread.
  Do not moralize — explain.

ETHICAL / SPIRITUAL DIMENSION (≥90 words — 3 paragraphs × ≥30 words each)
  Frame as the QUESTION the tradition asks — NOT the answer.
  Paragraph 1: What question does this tradition ask about this event?
  What does the tradition notice that the news coverage misses?
  Paragraph 2: How has this tradition historically engaged this type of question?
  Paragraph 3: What does this question reveal about the structural dimension
  that a purely policy analysis would miss?
  Do NOT resolve the question — leave it productively open.

YOUTH IMPLICATIONS (≥100 words)
  Anchored to age band, region, behavior.
  CONTRADICTION TEST.
  Split by audience where relevant (ja / zh-cn / en Gen Z).
  Connect youth reality to historical background.

SDG POLICY TIE (≥80 words)
  SDG number + full title + specific target number.
  One concrete metric: what is being measured, current data.
  Does this event advance or threaten the target — by what mechanism?
  Pearl News disclaimer.

FUTURE OUTLOOK (≥60 words)
  At least 2 concrete upcoming moments: vote, summit, deadline, court date.
  Name who is watching, deciding, and what the decision point is.
  One specific reader action.
  Close with question or provocation.

<p><em>Source: <a href="...">[RSS source]</a></em></p>
```

### Teacher Format (Explainer)

```html
<p>[Teacher name], from the [tradition] tradition, asks a question that the news
   coverage does not: [the question — ≥30 words].</p>
<p>Within [tradition], this type of moment has historically been met with
   [historical engagement or practice — ≥30 words].</p>
<p>What [Teacher name]'s question reveals is that
   [structural insight the policy analysis misses — ≥30 words].</p>
```

### Editorial Rule

The teacher asks a QUESTION — they do NOT provide the answer. The reader arrives confused or uninformed and leaves with a clear, usable model of what happened, why it matters, and what it means for their life. The ethical/spiritual dimension is the question the tradition asks, not the answer it gives.

---

## Article Type 5: Interfaith Dialogue Report

**Template ID**: `interfaith_dialogue_report`
**Use for**: Forum gathering, multi-leader event, joint declaration, youth peace forum
**Frequency**: ~5% of articles (hash-based selection)
**Target length**: 800–1000 words
**Minimum total**: 600 words

### Multi-Teacher System

Unlike all other article types (which use exactly one teacher), the Interfaith Dialogue Report uses 2-3 teachers from DIFFERENT spiritual traditions. The pipeline:

1. Loads all teachers from the topic's atom file (`topic_{topic}.yaml`)
2. Filters by language region fit
3. Groups candidates by tradition (first word of tradition name)
4. Picks one teacher per tradition using deterministic hash selection
5. Returns 2-3 teachers with their atoms

The article shows where these teachers CONVERGE — not debate. This is a record of agreement: where different traditions arrive at similar insights when faced with the same news event.

### Section Flow

```
<h1>[Headline]</h1>

EVENT SUMMARY (≥100 words)
  What happened — name the news event, UN body, forum, or decision.
  Include date, location, one specific figure or finding.
  Neutral, factual — a record, not interpretation.
  Name the source by full name.
  One sentence on why this matters for young people.

LEADERS PRESENT (≥80 words)
  Name EACH teacher by full name and tradition.
  One sentence per teacher: what their tradition brings to THIS specific story.
  Frame each teacher's presence in terms of what their tradition SEES
  about this event that other traditions might not.
  Do NOT use generic: "spiritual leaders" or "religious figures."

THEMES OF AGREEMENT (≥150 words)
  Heart of the article. Show WHERE the teachers CONVERGE.
  Use atoms from EACH teacher's Knowledge Base.

  For 2 teachers (min 2 convergence points):
    Paragraph 1: First theme — name both teachers, show how different
    reasoning arrives at the same insight.
    Paragraph 2: Second theme — a different convergence aspect.

  For 3 teachers (min 2 convergence points):
    Paragraph 1: First theme — all three traditions point the same direction.
    Paragraph 2: Second theme — at least 2 of 3 teachers contributing.

  CRITICAL: This is AGREEMENT, not debate.
  "Across traditions, these teachers find common ground on..."
  "Despite different starting points, both [A] and [B] arrive at..."
  Each convergence point must connect to a SPECIFIC aspect of the news event.

YOUTH COMMITMENTS (≥100 words)
  What this convergence MEANS for youth facing this challenge.
  COLLECTIVE offering — not individual teacher instruction.
  Anchored to specific age bands, places, behaviors.
  CONTRADICTION TEST.
  One concrete thing a young person can take from this convergence TODAY.
  Frame as commitment: "These traditions converge on an invitation to..."

SDG ALIGNMENT (≥80 words)
  SDG number + full title.
  Specific target if supported.
  How interfaith convergence ADVANCES this specific target.
  Name the mechanism: what does shared wisdom enable
  that a single perspective could not?
  Pearl News disclaimer.

NEXT STEPS (≥50 words)
  One concrete upcoming event, dialogue, or action.
  One specific thing a young reader can do.
  Close with question: what would it look like if this convergence
  became a practice, not just a conversation?

<p><em>Source: <a href="...">[RSS source]</a></em></p>
```

### Multi-Teacher Knowledge Base Format

The LLM expansion prompt receives the teacher data in this format:

```
TEACHER 1: [Name]
Tradition: [tradition]
Attribution: [attribution template]
Approved teachings (use at least 1 atom from this teacher in themes of agreement):
  1. [atom 1]
  2. [atom 2]
  3. [atom 3]

TEACHER 2: [Name]
Tradition: [tradition]
Attribution: [attribution template]
Approved teachings (use at least 1 atom from this teacher in themes of agreement):
  1. [atom 1]
  2. [atom 2]
  3. [atom 3]

CONVERGENCE TASK:
Show where [Teacher 1] and [Teacher 2] — from [tradition 1], [tradition 2]
traditions respectively — AGREE on positive aspects of this news story
for helping youth. Use at least 1 atom from each teacher. Find where
different reasoning arrives at the same insight.
```

### Editorial Rule

This is NOT a debate. It is a record of convergence: where different traditions arrive at similar insights when faced with the same news event. The news event triggers the dialogue. The teachers do not argue — they CONVERGE. Each teacher brings their tradition's distinct lens, and the article shows where those lenses point in the same direction.

---

## Rules That Apply to ALL Article Types

### Four-Layer Mission Test

Every article must pass all four layers before publication:

**LAYER 1 — NEWS ANCHOR**: Is there a specific, named, dated news event from a real source? If the article could exist without the news event, it fails.

**LAYER 2 — YOUTH REALITY**: Does every youth claim have an anchor (age band, place, statistic, or named behavior)? Is there at least one contradiction named? If vague or emotional only, it fails.

**LAYER 3 — TEACHER WISDOM AS LENS**: Is the teacher responding to THIS specific story — not giving generic wisdom? Could the teacher section be copy-pasted into a different article unchanged? If yes, it fails.

**LAYER 4 — SDG AS STRUCTURE** (when applicable): If the news event clearly relates to a UN Sustainable Development Goal, is the SDG named with number, full title, and specific target? Does it show a mechanism? SDG framing is included where relevant — not forced into every article. If SDG is included but mentioned only in passing without a structural link, it fails.

### Evidence Standard

Every article must include at least two of the following evidence types: an official report or resolution, peer-reviewed research, government data or survey, a named expert or institutional spokesperson, or an institutional dataset. This is a credibility floor — articles that rely entirely on the model's generated claims without sourced evidence should be flagged for review.

### The Contradiction Test

Strongly encouraged in youth sections — use wherever the data supports it. Where does this cohort's stated concern about an issue clash with their actual behavior or circumstances? Name it explicitly. This is the single rule that most separates Pearl News from spiritual content marketing.

Not every article will have a clean contradiction. When the data doesn't support one, skip it rather than forcing a false tension. But when it's there, it should be prominent.

Bad: "Young Japanese feel anxious about global conflict."
Good: "In a 2023 Cabinet Office survey, 47% of Japanese ages 18–29 cited global conflict as a top anxiety, yet Japan's defense budget reached its highest level since WWII that same year."

### Localization Bridge (REQUIRED — All Types)

Every article must include one sentence connecting the UN or US news event to a specific local statistic, policy, or parallel in the target audience's country. This bridge appears between the news summary and youth impact sections. Without it, the model writes for a generic global reader.

Examples:
- Japanese: "Japan's Ministry of Education reported a parallel trend: a 12% rise in school refusal cases in the same period."
- Chinese: "China's State Council issued a similar directive last month, though enforcement varies widely by province."
- English: "In the US, the Department of Education's own data shows a comparable gap, with only 37% of eighth graders reading at grade level."

The `gate_localization_bridge` validation gate is **position-aware** and **content-aware**:
- **Position**: The bridge must appear before the teacher section (roughly the first 60% of the article). A country name in the forward look section doesn't count.
- **Content**: A country name alone is not enough. The gate requires a local evidence signal (percentage, ministry name, policy reference, data verb like "rose/fell/increased") within ±200 characters of the country signal. "Japan" mentioned once in passing fails; "Japan's Ministry of Education reported a 12% rise" passes.

### Audience Registers

Apply based on article language — positioned BEFORE section instructions in expansion prompts so the model has them active while writing each section:

**Japanese (ja)**: Contemplative, understated. Reference juken, hikikomori, declining birthrate anxiety. Anchor to Japan-specific youth data. Indirect framing.

**Simplified Chinese (zh-CN)**: Collective framing, systemic lens. Reference tangping, gaokao, 996 contradiction. Name structural forces, not individual blame.

**Traditional Chinese / Taiwan (zh-TW)**: Civic identity, sovereignty awareness. Bridge to Taiwan civic context and democratic values.

**English (en)**: Direct, contradiction-forward. Reference social media behavior, mental health discourse, economic precarity. Name contradictions openly.

### Teacher Attribution Rule

Teacher insight must be interpreted by the journalist, not quoted as authority. The teacher's tradition *suggests* a perspective — the article doesn't present it as truth.

Preferred: "[Teacher]'s tradition suggests a different way to interpret this moment — that what looks like institutional failure may also be..."
Acceptable: "From within the [tradition] tradition, [Teacher] teaches that..."
Avoid: "[Teacher] says the answer is..." or "[Teacher] knows that..."

The teacher is a lens, not a source of truth. The reader decides what to do with the perspective.

### Voice Rules (All Types)

- Behavior over emotion. Show what people do, not what they feel.
- No passive-voice policy descriptions. Name who did what.
- No unnamed experts. If you cite a perspective, name the person or institution.
- No inspirational platitudes without evidence.
- One idea per sentence in ledes and forward looks.
- Teacher insight is interpreted by the journalist, not presented as authority.

### Banned Phrases (Never Write These)

- "Young people around the world are feeling..."
- "Now more than ever..."
- "In these uncertain times..."
- "It remains to be seen..."
- "Historic" or "landmark" without substantiation
- "Many are saying..."
- "As debates continue to rage..."
- "Both sides"
- "Complex issue" (name the complexity instead)
- Any phrase implying UN endorsement or Pearl News affiliation with the UN
- The word "we"

### Mission Drift Types (All Forbidden)

**TEACHER PROFILE DRIFT**: Writing a profile of a teacher that happens to mention a news event. The teacher is never the subject — the news event is.

**SPIRITUAL MAGAZINE DRIFT**: Writing about youth anxiety without a specific news peg. Every article needs a news trigger with date, body, decision.

**SDG DECORATION DRIFT**: Mentioning an SDG at the end as a tag. The SDG must show a mechanism — how the event advances or threatens a specific target.

**VAGUE YOUTH DRIFT**: Writing about "young people" without specifics. Every youth claim needs an anchor: age, place, statistic, or named behavior.

**COMFORT DRIFT**: Teacher wisdom that soothes rather than reframes. Teacher insight must change how the reader understands the news — not just how they feel about it.

---

## Source Diversity

Two layers of enforcement in `run_article_pipeline.py`:

1. **Per-run cap**: No more than 2 articles per pipeline run from the same RSS source feed.
2. **Rolling 7-day window**: No more than 6 articles from the same source across all runs in a 7-day period. The pipeline logs source usage to `.source_diversity_log.json` in the output directory, prunes entries older than 7 days, and checks cumulative counts before accepting items.

This prevents monoculture at both the run level and across daily runs — so a daily pipeline pulling from UN News SDGs won't dominate coverage across the week.

---

## Fact-Check Layer

Before publication, the pipeline runs `gate_evidence_present` to verify the article contains at least 2 evidence signals: named reports, surveys, institutions, or data points. This is a floor, not a ceiling — articles that contain no verifiable claims besides teacher wisdom should be held for manual fact review.

SDG target numbers are now sourced from `sdg_targets.yaml` rather than generated by the model. Teacher names are verified against the roster. Numbers and dates in the article that don't match the source RSS item are flagged as potential hallucinations in the manual review queue.

---

## Teacher System

### Single Teacher (Hard News, Youth Feature, Commentary, Explainer)

Each article uses exactly one teacher resolved from `teacher_news_roster.yaml` and `atoms/teacher_quotes_practices/topic_{topic}.yaml`. The teacher is selected deterministically by article ID hash, filtered by language region fit. Each teacher comes with 10 approved atoms (teachings); the LLM receives 3 selected atoms per article but the full bank of 10 gives variety across articles.

The teacher always has: `teacher_id`, `display_name`, `tradition`, `attribution` template, and `atoms` (10 per topic).

### Multiple Teachers (Interfaith Dialogue Report Only)

2-3 teachers from DIFFERENT traditions. Selected by grouping candidates by tradition and picking one per tradition using hash-based selection. The pipeline stores these in `item["_teachers_resolved"]` (plural).

### Fallback Teacher

When no teacher data is available for a topic/language combination, the pipeline uses a generic fallback: "a teacher from the United Spiritual Leaders Forum" with 3 generic interfaith atoms. **This fallback is marked `is_fallback: True` and the `gate_fallback_teacher` validation gate will FAIL it** — holding the article for manual review until a real named teacher is assigned. This prevents articles with generic teacher content from being published.

### Atom File Format

Each topic gets a `topic_{topic}.yaml` in `pearl_news/atoms/teacher_quotes_practices/`. An atom is a single approved teaching statement — 30-50 words, sourced from the teacher's actual works, specific enough to connect to a news event. See `ATOM_FORMAT.md` in that directory for the full spec. Each teacher now has 10 atoms per topic (expanded from the initial 3). All files are still marked STATUS: STARTER and need human review against actual doctrine.

### What Makes a Good Atom (Examples)

**Good atom** (climate, Ajahn Ahjan — Theravada Buddhist):
> "The destruction of forests reflects ignorance of interdependence; harming ecosystems harms ourselves. Recognizing this interconnection — a core Buddhist insight — transforms how we view climate action: not as sacrifice but as enlightened self-interest aligned with dependent origination and the precepts."

Why it works: 43 words, names a specific concept (dependent origination), connects to climate news (forest destruction), offers a reframe a journalist can use (sacrifice → self-interest).

**Good atom** (peace/conflict, Ma'at — Ancient Egyptian):
> "Ma'at — cosmic order and justice — requires that peace be built on accurate accounting, not denial or forgetting of harm. Injustice that is named and addressed restores Ma'at; injustice suppressed accumulates as cosmic debt. Young people in post-conflict societies need frameworks insisting truth precedes reconciliation."

Why it works: 47 words, names the tradition's core concept (Ma'at), connects to a news scenario (post-conflict reconciliation), offers a usable frame (truth before reconciliation).

**Bad atom**: "Peace is important and we should all strive for inner harmony." — Platitude, no tradition concept, no news connection, no reframe.

**Bad atom**: "Be mindful." — Too short, too generic, no journalist can embed this in a news story.

### WordPress Author Assignment

Teachers are mapped to WordPress author IDs in `wordpress_authors.yaml` via `teacher_author_map`. The pipeline checks this mapping first; if no match, it falls back to round-robin author rotation.

---

## Quality Gates (article_validator.py)

The pipeline validates every article against these gates before publication:

| # | Gate | Check | Applies To |
|---|------|-------|-----------|
| 1 | `gate_six_sections_present` | All 6 structural sections detected (prefers HTML comment markers, falls back to heuristic) | All |
| 2 | `gate_min_word_count` | Content ≥ 600 words (HTML stripped) | All |
| 3 | `gate_section_word_counts` | Teacher ≥75w, youth ≥50w, SDG ≥40w | All |
| 4 | `gate_named_teacher` | Named teacher (not generic placeholder) in content | All |
| 5 | `gate_fallback_teacher` | Real teacher assigned (not fallback) | All |
| 6 | `gate_teacher_three_points` | 3 substantive teacher paragraphs (≥20 words each) | All |
| 7 | `gate_multi_teacher_present` | 2+ teacher names + convergence language | Interfaith only |
| 8 | `gate_localization_bridge` | Position-aware: local statistic/policy/data point within ±200 chars of a country signal, appearing BEFORE teacher section | All |
| 9 | `gate_evidence_present` | ≥2 evidence signals: named reports, surveys, institutions, percentages, or attribution phrases | All |
| 10 | `gate_sdg_number` | SDG number appears in content (e.g. "SDG 13") | When SDG included |
| 11 | `gate_sdg_full_title` | SDG title keyword near SDG number | All |
| 12 | `gate_youth_anchor` | Concrete anchor (%, place, age band) in youth section | All |
| 13 | `gate_no_banned_phrases` | None of the banned phrases appear | All |
| 14 | `gate_source_line` | Source line preserved at end | All |

### Section Detection Strategy

The assembler injects HTML comment markers (`<!-- section: lede -->`, `<!-- section: teacher_perspective -->`, etc.) into the draft before LLM expansion. These markers survive expansion because the prompt instructs the model to "preserve all HTML tags from the draft." The validator checks for these markers first (reliable); if absent, it falls back to heuristic keyword detection (less reliable). This eliminates false positives from the old approach where any article with 6 paragraphs could pass.

### Expansion Retry Logic

If LLM expansion produces an article below the minimum word count (default 600), the pipeline diagnoses which specific sections are short (teacher, youth, SDG) and injects that feedback into the retry prompt as an HTML comment. The model sees "RETRY: This draft is only 450 words (need 600+). SHORT SECTIONS: TEACHER section ~60w (need ≥90); YOUTH section ~40w (need ≥100)" — so it knows exactly what to expand. Up to `expansion_retries` retries (default 1).

---

## Output Format (All Types)

- Return only the expanded HTML article body.
- Start with `<h1>` (or `<p><strong>Commentary</strong></p>` then `<h1>` for Commentary).
- The VERY LAST line MUST be the Source paragraph exactly as it appears in the draft: `<p><em>Source: <a href="...">[title]</a></em></p>`.
- Preserve all HTML tags from the draft. Do not add new section types.
- No preamble, explanation, or markdown fences.

---

## File Locations

| Purpose | Path |
|---------|------|
| Template definitions (YAML) | `pearl_news/article_templates/{template_id}.yaml` |
| Expansion prompts (per-type) | `pearl_news/prompts/expansion_{type}.txt` |
| Fallback expansion prompt | `pearl_news/prompts/expansion_system.txt` |
| Teacher roster | `pearl_news/config/teacher_news_roster.yaml` |
| Teacher atoms (per topic) | `pearl_news/atoms/teacher_quotes_practices/topic_{topic}.yaml` |
| Atom format spec | `pearl_news/atoms/teacher_quotes_practices/ATOM_FORMAT.md` |
| SDG targets reference | `pearl_news/config/sdg_targets.yaml` |
| LLM expansion config | `pearl_news/config/llm_expansion.yaml` |
| WordPress author mapping | `pearl_news/config/wordpress_authors.yaml` |
| Template selection logic | `pearl_news/pipeline/template_selector.py` |
| Teacher resolution | `pearl_news/pipeline/teacher_resolver.py` |
| LLM expansion engine | `pearl_news/pipeline/llm_expand.py` |
| Article assembly | `pearl_news/pipeline/article_assembler.py` |
| Article validation | `pearl_news/pipeline/article_validator.py` |
| Main pipeline | `pearl_news/pipeline/run_article_pipeline.py` |
| This plan document | `pearl_news/PEARL_NEWS_ARTICLE_PLAN.md` |

---

## LLM Expansion Configuration

Set in `pearl_news/config/llm_expansion.yaml` or via environment variables:

| Setting | Default | Env Override |
|---------|---------|-------------|
| `base_url` | (none) | `QWEN_BASE_URL` |
| `api_key` | `lm-studio` | `QWEN_API_KEY` |
| `model` | `qwen3-14b` | `QWEN_MODEL` |
| `timeout` | 120 | — |
| `max_tokens` | 2048 | — |
| `temperature` | 0.5 | — |
| `target_word_count` | 1000 | — |
| `min_word_count` | 600 | — |
| `expansion_retries` | 1 | — |
| `disable_thinking` | true | — |

When `QWEN_BASE_URL` is set, expansion is auto-enabled even if `enabled: false` in config.

---

## Pipeline Flow (per article)

```
RSS Feed Item
  ↓
Topic Classification (topic_classifier.py)
  ↓
Template Selection (template_selector.py)
  → Assigns template_id based on topic, source, hash
  ↓
Teacher Resolution (teacher_resolver.py)
  → Single teacher for hard_news/youth/commentary/explainer
  → Multiple teachers (2-3 from different traditions) for interfaith
  ↓
Article Assembly (article_assembler.py)
  → Fills section slots from template YAML
  → Generates placeholder content per section
  ↓
LLM Expansion (llm_expand.py)
  → Loads template-specific expansion prompt
  → Sends to Qwen/OpenAI-compatible API
  → Retries if word count below minimum
  ↓
Article Validation (article_validator.py)
  → Runs all applicable quality gates
  → Marks pass/fail per gate
  ↓
WordPress Publishing (wp_publish.py)
  → Assigns author from teacher_author_map or round-robin
  → Publishes to WordPress
```

---

## Teacher Onboarding Checklist

A complete teacher in Pearl News requires all of the following:

**1. Roster Entry** (`config/teacher_news_roster.yaml`): teacher_id (slug), display_name, tradition, tradition_short, region_fit (array: japan, china, english, global), news_topics (4-6 topics from the 7 available), attribution_template.

**2. Atom Coverage** (`atoms/teacher_quotes_practices/topic_*.yaml`): 10 atoms per teacher per topic they are assigned to. Each atom must be 40-80 words, tradition-specific, news-connectable. Format: YAML block scalar (`- >`). Status field tracks lifecycle (see below).

**3. WordPress Author Account**: Author ID in `config/wordpress_authors.yaml`. Bio, photo, and tradition label configured in WordPress. Linked to teacher_id for byline attribution.

**4. Attribution Consistency**: The attribution template in the roster must match the attribution field in each topic atom file. Teacher display_name must be identical across all references.

### Adding a New Teacher

1. Add entry to `teacher_news_roster.yaml` with all required fields
2. Run `python -m pearl_news.pipeline.teacher_onboarding --audit` to see gaps
3. Run `python -m pearl_news.pipeline.teacher_onboarding --scaffold` to auto-generate atoms via LLM
4. All generated atoms start as `status: starter` — they MUST be human-reviewed
5. After editorial review: `python -m pearl_news.pipeline.teacher_onboarding --fix-status teacher_id topic reviewed`
6. After final approval: `python -m pearl_news.pipeline.teacher_onboarding --fix-status teacher_id topic approved`
7. Add WordPress author ID to `wordpress_authors.yaml`
8. Run `python -m pearl_news.pipeline.teacher_onboarding --validate` to confirm completeness

---

## Atom Lifecycle

All atoms flow through three states:

```
STARTER (LLM-generated) → REVIEWED (editor verified) → APPROVED (production-ready)
```

**STARTER**: Auto-generated by `teacher_onboarding.py --scaffold` using Qwen3. Not used in production (`PEARL_NEWS_ENV=production` filters these out). Used in dev/test for rapid iteration. Requires human editorial review before advancing.

**REVIEWED**: Human editor has checked atom against: (a) accuracy to the teacher's actual published teachings, (b) tradition-specificity (no generic platitudes), (c) news-connectability (can a journalist use this in an article?), (d) word count (40-80 words). Still not used in production; marked for final approval.

**APPROVED**: Cleared for production use. Appears in published articles. The teacher resolver only selects teachers with APPROVED atoms when the pipeline runs in production mode.

### Pipeline behavior by status

| Environment | STARTER atoms | REVIEWED atoms | APPROVED atoms |
|-------------|--------------|----------------|----------------|
| Dev (default) | Used | Used | Used |
| Production | Skipped | Skipped | Used |

Set environment: `export PEARL_NEWS_ENV=production` before running pipeline.

### Readiness check

At pipeline startup, `teacher_readiness.py` scans all topics and logs:
- **READY**: all teachers have sufficient usable atoms
- **PARTIAL**: some teachers have fewer than 10 atoms
- **BLOCKED**: some teachers have fewer than 3 atoms (will trigger fallback teacher)
